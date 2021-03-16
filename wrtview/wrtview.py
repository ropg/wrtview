#!/usr/local/opt/python/libexec/bin/python

import os, subprocess, re, ipaddress, sys, argparse, pkg_resources


def main():
    default_format = "{arp}{dhcp}{hosts}{ethers} {ip:13.13} {name:17.17} {mac:17.17} " + \
                     "{vendor:22.22}  {wifi alias} {wifi expected throughput}"

    whitespace = re.compile('\s+')
    hosts = {}
    stations = []

    # Parse command line arguments
    parser = argparse.ArgumentParser()
    parser.add_argument('--leases', default='/tmp/dhcp.leases', metavar='<leases-file>')
    parser.add_argument('--hosts', default='/etc/hosts', metavar='<hosts-file>')
    parser.add_argument('--ethers', default='/etc/ethers', metavar='<ethers-file>')
    parser.add_argument('--network', '-n', default='lan', metavar='<interface>')
    parser.add_argument('--wireless', '-w', nargs='*', default=['wlan0', 'wlan1'],
                        metavar='<interface>[@<host>][:<alias>]')
    parser.add_argument('--format', '-f', dest='format_str', default=default_format,
                        metavar='<format string>')
    parser.add_argument('host', nargs='?', default="192.168.1.1", metavar='<name or ip>')
    args = parser.parse_args()

    net_addr = get_output(args.host, 'uci get network.' + args.network + '.ipaddr')
    net_mask = get_output(args.host, 'uci get network.' + args.network + '.netmask')

    # Read vendor database
    vendor_re = re.compile('^([0-9A-F]+)\s+(.*?)$')
    vendors = {}
    vendorsoutput = pkg_resources.resource_string("wrtview", "vendors").decode("utf-8")
    for line in vendorsoutput.splitlines():
        s = vendor_re.search(line)
        if s:
            vendors[s.group(1)] = s.group(2)

    # Get the wireless station data
    for w in args.wireless:
        e = w.split(":", 2)
        part1 = alias = e[0]
        if len(e) == 2:
            alias = e[1]
        e = part1.split('@', 2)
        iface = e[0]
        if len(e) == 2:
            whost = e[1]
        else:
            whost = args.host
        stations.extend(wireless_stations(whost, iface, alias))

    # DHCP
    leaseoutput = get_output(args.host, 'cat /tmp/dhcp.leases')
    for line in leaseoutput.splitlines():
        expire, mac, ip, name, clientID = line.split(' ')
        if in_same_subnet(ip, net_addr, net_mask):
            ii = ip2int(ip)
            hosts[ii] = {}
            hosts[ii]['ip'] = ip
            if name != "*": hosts[ii]['name'] = name
            hosts[ii]['mac'] = mac.upper()
            hosts[ii]['expire'] = int(expire)
            if clientID != "*": hosts[ii]['clientID'] = clientID
            hosts[ii]['dhcp'] = 'D'

    # hosts
    hostsoutput = get_output(args.host, 'cat /etc/hosts')
    for line in hostsoutput.splitlines():
        line = re.sub('#.*', '', line.strip())
        if line == '': continue
        ip, name, *_ = whitespace.split(line)
        if in_same_subnet(ip, net_addr, net_mask):
            ii = ip2int(ip)
            if not ii in hosts: hosts[ii] = {}
            hosts[ii]['ip'] = ip
            hosts[ii]['name'] = name
            hosts[ii]['hosts'] = 'H';

    # ethers
    ethersoutput = get_output(args.host, 'cat /etc/ethers')
    for line in ethersoutput.splitlines():
        line = re.sub('#.*', '', line.strip())
        if line == '': continue
        mac, name = whitespace.split(line)
        for host in hosts.values():
            if host.get('mac') == mac.upper():
                host['name'] == name
                host['in_ethers'] = True
            if host.get('name') == name:
                host['mac'] = mac.upper()
                host['ethers'] = 'E'

    # ARP
    arpoutput = get_output(args.host, 'ip neigh')
    for line in arpoutput.splitlines():
        ip, _, _, _, mac, *_ = whitespace.split(line)
        if in_same_subnet(ip, net_addr, net_mask):
            ii = ip2int(ip)
            if not ii in hosts: hosts[ii] = {}
            hosts[ii]['ip'] = ip
            hosts[ii]['mac'] = mac.upper()
            hosts[ii]['arp'] = 'A'

    # Merge in data from the wireless stations
    idx = 0
    for s in stations:
        mac = s['mac']
        found = False
        for _, host in hosts.items():
            if mac == host.get('mac'):
                found = True
                host.update(s)
        if not found:
            hosts[idx] = s
            hosts[idx]['ip'] = '?'
            idx += 1

    # Add in MAC vendor string from database
    for host in hosts.values():
        mac = host.get('mac')
        if not mac: continue
        if "26AE".find(mac[1]) != -1:
            host['vendor'] = 'locally administered'
        else:
            m = mac.replace(':', '')
            vendor = vendors.get(m[0:10], vendors.get(m[0:8], vendors.get(m[0:6], "unknown")))
            host['vendor'] = vendor

    # Print output sorted by IP
    for _, host in sorted(hosts.items()):
        # make sure the fields used in format_str are ' ' if they didn't exist
        for field in re.findall('\{(.*?)[\:\}]', args.format_str):
            host[field] = host.get(field, ' ');
        print (args.format_str.format(**host))




# return output from command at host as string
def get_output(host, command):
    return subprocess.run(['ssh', 'root@' + host, command],
                          stdout=subprocess.PIPE,
                          timeout = 5
                         ).stdout.decode('utf-8').strip()

def ip2int(ip):
    try:
        return int(ipaddress.IPv4Address(ip))
    except:
        return 0

def in_same_subnet(ip1, ip2, mask):
    return ip2int(ip1) & ip2int(mask) == ip2int(ip2) & ip2int(mask)

# append data from one wireless interface to stations[]
def wireless_stations(host, interface, alias):
    stations = []
    station_re = re.compile('^Station ([0-9A-Fa-f:]+)')
    value_re = re.compile('\s+(.*?):\s*(.*)')
    iwoutput = get_output(host, 'iw ' + interface + ' station dump')
    s = {}
    for line in iwoutput.splitlines():
        m = station_re.search(line)
        if m:
            if s != {}:
                stations.append(s)
                s = {}
            s['mac']= m.group(1).upper()
            s['wifi ap host'] = host
            s['wifi ap interface'] = interface
            s['wifi alias'] = alias
        else:
            m = value_re.search(line)
            if m:
                s['wifi ' + m.group(1)] = m.group(2)
    if s != {}:
        stations.append(s)
    return stations


if __name__ == "__main__":
    main()
