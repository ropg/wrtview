#!/usr/local/opt/python/libexec/bin/python

import os, subprocess, re, ipaddress, sys, argparse, pkg_resources


hosts = []
stations = []

def main():
    global hosts
    global stations
    default_format = "{arp}{dhcp}{hosts}{ethers} {ip:13.13} {name:17.17} {mac:17.17} " + \
                     "{vendor:22.22}  {wifi alias} {wifi expected throughput}"

    whitespace = re.compile('\s+')


    # Parse command line arguments
    parser = argparse.ArgumentParser()
    parser.add_argument('--leases', default='/tmp/dhcp.leases', metavar='<leases-file>')
    parser.add_argument('--hosts', default='/etc/hosts', metavar='<hosts-file>')
    parser.add_argument('--ethers', default='/etc/ethers', metavar='<ethers-file>')
    parser.add_argument('--network', '-n', default='lan', metavar='<interface>')
    parser.add_argument('--wireless', '-w', default='wlan0,wlan1',
                        metavar='<interface>[@<host>][:<alias>]')
    parser.add_argument('--format', '-f', dest='format_str', default=default_format,
                        metavar='"<format string>"')
    parser.add_argument('--sort', '-s', nargs=1, default='ip_as_int',
                        metavar='<sort key>')
    parser.add_argument('--no-ghosts', dest='no_ghosts', action='store_true')
    parser.add_argument('--no-header', dest='no_header', action='store_true')
    parser.add_argument('--version', '-v', action='version',
                        version=pkg_resources.require('wrtview')[0].version)
    parser.add_argument('host', nargs='?', metavar='<name or ip>', default='192.168.1.1')
    args = parser.parse_args()

    networks = []
    for network in args.network.split(','):
        addr = get_output(args.host, 'uci get network.' + network + '.ipaddr')
        mask = get_output(args.host, 'uci get network.' + network + '.netmask')
        if addr == '' or mask == '':
            raise Exception("Network not found: " + network)
        networks.append({'name': network, 'addr': addr, 'mask': mask})

    # Read vendor database
    vendor_re = re.compile('^([0-9A-F]+)\s+(.*?)$')
    vendors = {}
    vendorsoutput = pkg_resources.resource_string("wrtview", "vendors").decode("utf-8")
    for line in vendorsoutput.splitlines():
        s = vendor_re.search(line)
        if s:
            vendors[s.group(1)] = s.group(2)
    # Once in memory is enough...
    del vendorsoutput

    # get all the global data we need from the target
    leaseoutput = get_output(args.host, 'cat ' + args.leases)
    hostsoutput = get_output(args.host, 'cat ' + args.hosts)
    ethersoutput = get_output(args.host, 'cat ' + args.ethers)
    arpoutput = get_output(args.host, 'ip -4 neigh')

    # Get the wireless station data
    station_re = re.compile('^Station ([0-9A-Fa-f:]+)')
    value_re = re.compile('\s+(.*?):\s*(.*)')
    for w in args.wireless.split(','):
        parts = w.split(":", 2)
        alias = parts[1] if len(parts) == 2 else parts[0]
        parts = parts[0].split('@', 2)
        iface = parts[0]
        whost = parts[1] if len(parts) == 2 else args.host
        iwoutput = get_output(whost, 'iw ' + iface + ' station dump')
        new_station = {}
        for line in iwoutput.splitlines():
            m = station_re.search(line)
            if m:
                if new_station != {}:
                    stations.append(new_station)
                    new_station = {}
                new_station['mac']= m.group(1).upper()
                new_station['wifi'] = 'W'
                new_station['wifi ap host'] = whost
                new_station['wifi ap interface'] = iface
                new_station['wifi alias'] = alias
            else:
                m = value_re.search(line)
                if m:
                    new_station['wifi ' + m.group(1)] = m.group(2)
        if new_station != {}:
            stations.append(new_station)

    # DHCP
    for line in leaseoutput.splitlines():
        expire, mac, ip, name, clientID = line.split(' ')
        host = find_host('ip', ip)
        if name != "*": host['name'] = name
        host['mac'] = mac.upper()
        host['expire'] = int(expire)
        if clientID != "*": host['clientID'] = clientID
        host['dhcp'] = 'D'

    # hosts
    for line in hostsoutput.splitlines():
        line = re.sub('#.*', '', line.strip())
        if line == '': continue
        ip, name, *_ = whitespace.split(line)
        host = find_host('ip', ip)
        host['name'] = name
        host['hosts'] = 'H';

    # ethers
    for line in ethersoutput.splitlines():
        line = re.sub('#.*', '', line.strip())
        if line == '': continue
        mac, name = whitespace.split(line)
        for host in hosts:
            if host.get('mac') == mac.upper():
                host['name'] == name
                host['ethers'] = 'E'
            if host.get('name') == name:
                host['mac'] = mac.upper()
                host['ethers'] = 'E'

    # ARP
    for line in arpoutput.splitlines():
        ip, _, _, _, mac, *_ = whitespace.split(line)
        host = find_host('ip', ip)
        host['mac'] = mac.upper()
        host['arp'] = 'A'

    # Merge in data from the wireless stations
    idx = 0
    for s in stations:
        mac = s['mac']
        found = False
        for host in hosts:
            if mac == host.get('mac'):
                found = True
                host.update(s)
        if not found:
            s['ip'] = "?"
            hosts.append(s)

    # Add in MAC vendor string from database
    for host in hosts:
        mac = host.get('mac')
        if not mac: continue
        if "26AE".find(mac[1]) != -1:
            host['vendor'] = 'locally administered'
        else:
            m = mac.replace(':', '')
            vendor = vendors.get(m[0:10], vendors.get(m[0:8], vendors.get(m[0:6], "unknown")))
            host['vendor'] = vendor

    # Fix up missing keys
    for host in hosts:
        # Make sure sort key exists for all hosts
        host[args.sort] = host.get(args.sort, ' ')
        # make sure the fields used in format_str are ' ' if they didn't exist
        for field in re.findall('\{(.*?)[\:\}]', args.format_str):
            host[field] = host.get(field, ' ');
        # add numeric ip for sorting
        host['ip_as_int'] = ip2int(host.get('ip', ''))

    # Sort
    sorted_hosts = sorted(hosts, key=lambda k: k[args.sort])

    # Print output for each network, sorted by args.sort column
    spacer = False
    for network in networks:
        if spacer: print ('\n')
        spacer = True
        if not args.no_header:
            print (f"Network '{network['name']}' on {args.host}:\n")
        for host in sorted_hosts:
            if in_same_subnet(host.get('ip', ''), network['addr'], network['mask']):
                print (args.format_str.format(**host))
                host['printed'] = True

    # Print the 'ghosts': wifi stations that were not found in the networks specified
    if not args.no_ghosts:
        header_printed = False
        for host in sorted_hosts:
            if host.get('wifi') and not host.get('printed'):
                if not header_printed:
                    if len(networks) == 1:
                        print (f"\nWiFi Stations not in this network:\n")
                    else:
                        print (f"\nWiFi Stations not in these networks:\n")
                    header_printed = True
                print (args.format_str.format(**host))



# return output from command at host as string
def get_output(host, command):
    return subprocess.run(['ssh', 'root@' + host, command],
                          capture_output = True, timeout = 5
                         ).stdout.decode('utf-8').strip()

def ip2int(ip):
    try:
        return int(ipaddress.IPv4Address(ip))
    except:
        return 0

def in_same_subnet(ip1, ip2, mask):
    return ip2int(ip1) & ip2int(mask) == ip2int(ip2) & ip2int(mask)

def find_host(k, v, add=True):
    global hosts
    for host in hosts:
        if host[k] == v:
            return host
    if add:
        new_item = { k: v }
        hosts.append(new_item)
        return hosts[-1]


if __name__ == "__main__":
    main()
