#!/usr/local/opt/python/libexec/bin/python

import os, subprocess, socket, re, ipaddress, sys, argparse, pkg_resources, traceback


def main():
    global hosts, args
    default_format = "{ping}{arp}{dhcp}{hosts}{ethers} {ip:13.13} {name:17.17} {mac:17.17} " + \
                     "{vendor:22.22}  {wifi alias} {wifi expected throughput}"

    # Parse command line arguments
    parser = argparse.ArgumentParser()
    parser.add_argument('--leases', default='/tmp/dhcp.leases', metavar='<leases-file>')
    parser.add_argument('--hosts', default='/etc/hosts', metavar='<hosts-file>')
    parser.add_argument('--ethers', default='/etc/ethers', metavar='<ethers-file>')
    parser.add_argument('--network', '-n', metavar='<network>', action='append',
                        help='logical network names (e.g. \'lan\') to list')
    parser.add_argument('--wireless', '-w', action='append',
                        metavar='<interface>[@<host>][:<alias>]',
                        help='wireless interfaces, see README.md')
    parser.add_argument('--format', '-f', dest='format_str', default=default_format,
                        metavar='"<format string>"')
    parser.add_argument('--sort', '-s', default='ip_as_int', metavar='<sort key>')
    parser.add_argument('--no-ghosts', action='store_true')
    parser.add_argument('--no-header', action='store_true')
    parser.add_argument('--no-ping', action='store_true',
                        help='Prevents pinging of whole network from the target OpenWRT')
    parser.add_argument('--max-ping', metavar='<#>', type=int, default=254,
                        help='Maximum number of simultaneous pings')
    parser.add_argument('--identity', '-i', metavar='<file>')
    parser.add_argument('--greppable', '-g', action='store_const', const='-', default = ' ',
                        help='fixed number of space-separated output fields')
    parser.add_argument('--version', '-v', action='version',
                        version=pkg_resources.require('wrtview')[0].version)
    parser.add_argument('router', nargs='?', metavar='<name or ip>', default='192.168.1.1')
    args = parser.parse_args()

    # argparse cannot properly have defaults of lists somehow
    if not args.wireless:
        args.wireless = ['wlan0', 'wlan1']
    if not args.network:
        args.network = ['lan']

    # get data on the network names (specified with --network / -n)
    networks = []
    for network in args.network:
        nonet = "Problem reading network information for network '" + network + "'"
        addr  = remote_cmd('uci get network.' + network + '.ipaddr', err=nonet)
        mask  = remote_cmd('uci get network.' + network + '.netmask', err=nonet)
        m = re.search(r'HWaddr\s+([0-9A-Fa-f:]+)', remote_cmd('ifconfig ' + network, err=nonet))
        mac = m.group(1) if m else None
        networks.append({'name': network, 'addr': addr, 'mask': mask, 'mac': mac})

    # Print it just once, not once for each ssh command
    if args.identity and not os.path.isfile(args.identity):
        sys.stderr.write('Warning: Identity file ' + args.identity +
                         ' not accessible: No such file or directory.\n')

    # Read vendor database
    # This is the files installed in /usr/share/arp-scan when package 'arp-scan-database'
    # is installed on an openwrt box, all concatenated into the file called vendors.
    vendors = {}
    for prefix, vendor in re.findall(r'^([0-9A-F]+)\s+(.*?)$',
     pkg_resources.resource_string('wrtview', 'vendors').decode('utf-8'), re.MULTILINE):
        vendors[prefix] = vendor

    # Get the wireless station data
    stations = []
    for w in args.wireless:
        parts = w.split(":", 2)
        alias = parts[1] if len(parts) == 2 else parts[0]
        parts = parts[0].split('@', 2)
        iface = parts[0]
        whost = parts[1] if len(parts) == 2 else args.router
        new_station = {}
        for line in remote_cmd('iw ' + iface + ' station dump', whost).splitlines():
            m = re.search(r'^Station ([0-9A-Fa-f:]+)', line)
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
                m = re.search(r'\s+(.*?):\s*(.*)', line)
                if m:
                    new_station['wifi ' + m.group(1)] = m.group(2)
        if new_station != {}:
            stations.append(new_station)

    hosts = []

    # DHCP
    for line in remote_cmd('cat ' + args.leases, on_err='').splitlines():
        expire, mac, ip, name, clientID = line.split(' ')
        host = find_host('ip', ip)
        if name != "*":
            host['name'] = name
        host['mac'] = mac.upper()
        host['expire'] = int(expire)
        if clientID != "*":
            host['clientID'] = clientID
        host['dhcp'] = 'D'

    # hosts
    for ip, name in re.findall(r'^\s*([\d\.]+?)\s+([\w-]+)',
                               remote_cmd('cat ' + args.hosts, on_err=''), re.MULTILINE):
        host = find_host('ip', ip)
        host['name'] = name
        host['hosts'] = 'H'

    # Ping scan.
    if not args.no_ping:
        # upload our pingall script
        pingall = pkg_resources.resource_filename('wrtview', 'pingall')
        identity = ' -i ' + args.identity if args.identity else ''
        local_cmd('scp' + identity + ' -B ' + pingall + ' root@' + args.router + ':/tmp/pingall')
        remote_cmd('chmod a+x /tmp/pingall')
        # gather all ip numbers to be pinged
        ping_ips = []
        for net in networks:
            ping_ips += list(ipaddress.IPv4Interface(net['addr'] + '/' +
                                                     net['mask']).network.hosts())
        # ping them in batches of --max-ping
        while ping_ips:
            ping_now, ping_ips = ping_ips[:args.max_ping], ping_ips[args.max_ping:]
            ping_output = remote_cmd('/tmp/pingall ' + ' '.join([str(i) for i in ping_now]))
            for ip in ping_output.splitlines():
                find_host('ip', ip)['ping'] = 'P'
        remote_cmd('rm /tmp/pingall')

    # ARP
    for ip, mac in re.findall(r'^([\d\.]+?) dev \S+? lladdr ([0-9A-Fa-f:]+?) ',
                              remote_cmd('ip -4 neigh'), re.MULTILINE):
        host = find_host('ip', ip)
        host['mac'] = mac.upper()
        host['arp'] = 'A'

    # ethers
    for mac, name in re.findall(r'^([\dA-Fa-f:]+?)\s+([\w-]+)',
                                remote_cmd('cat ' + args.ethers, on_err=''), re.MULTILINE):
        for host in hosts:
            if host.get('mac') == mac.upper():
                host['name'] = host.get('name', '(' + name + ')')
                host['ethers'] = 'E'
            if host.get('name') == name:
                if not host.get('mac'):
                    host['mac'] = mac.upper()
                    host['mac_down'] = True
                host['ethers'] = 'E'

    # Merge in data from the wireless stations
    for s in stations:
        mac = s['mac']
        found = False
        for host in hosts:
            if mac == host.get('mac') and not host.get('mac_down'):
                found = True
                host.update(s)
        if not found:
            s['ip'] = "?"
            hosts.append(s)

    # Add info about router itself
    for network in networks:
        host = find_host('ip', network['addr'])
        host['mac'] = host.get('mac', network['mac'])
        host['is_router'] = 'R'

    # Add in MAC vendor string from database
    for host in hosts:
        mac = host.get('mac')
        if mac:
            if "26AE".find(mac[1]) != -1:
                host['vendor'] = 'locally administered'
            else:
                m = mac.replace(':', '')
                vendor = vendors.get(m[0:10], vendors.get(m[0:8], vendors.get(m[0:6], "unknown")))
                host['vendor'] = vendor

    # Fix up missing keys
    for host in hosts:
        # Make sure sort key exists for all hosts
        host[args.sort] = host.get(args.sort, args.greppable)
        # make sure the fields used in format_str are ' ' (or '-' if greppable) if they didn't exist
        for field in re.findall(r'\{(.*?)[\:\}]', args.format_str):
            host[field] = host.get(field, args.greppable)
        # add numeric ip for sorting
        host['ip_as_int'] = ip2int(host.get('ip', ''))
        # determine if host is online
        if host.get('ping') == 'P' or host.get('arp') == 'A' or host.get('wifi'):
            host['online'] = 'O'

    # Sort
    sorted_hosts = sorted(hosts, key=lambda k: k[args.sort])

    # Set ANSI control sequences if we're on a tty
    if sys.stdout.isatty():
        bold   = '\u001b[1m'
        faint  = '\u001b[2m'
        normal = '\u001b[0m'
    else:
        bold = normal = faint = ''

    # Print output for each network, sorted by args.sort column
    spacer = False
    for network in networks:
        if spacer: print ('\n')
        spacer = True
        if not args.no_header:
            print ("Network '" + network['name'] + "' on " + args.router + ":\n")
        for host in sorted_hosts:
            if in_same_subnet(host.get('ip', ''), network['addr'], network['mask']):
                if not host.get('online'):
                    print (faint, end='')
                if host.get('is_router'):
                    print (bold, end='')
                print (args.format_str.format(**host) + normal)
                host['printed'] = True

    # Print the 'ghosts': wifi stations that were not found in the networks specified
    if not args.no_ghosts:
        header_printed = False
        for host in sorted_hosts:
            if host.get('wifi') and not host.get('printed'):
                if not header_printed:
                    if len(networks) == 1:
                        print ('\nWiFi Stations not in this network:\n')
                    else:
                        print ('\nWiFi Stations not in these networks:\n')
                    header_printed = True
                print (args.format_str.format(**host))


# return output from command at router as string, defaults to args.router
#
# err:    optional more human-readable string to describe what went wrong
# on_err: optional string to return instead of raising exception when error
def remote_cmd(command, router=None, err=None, on_err=False):
    global args
    if not router:
        router = args.router
    # See that router is indeed remote
    if router != socket.gethostname() and router != socket.gethostbyname(socket.gethostname()):
        identity = ' -i ' + args.identity if args.identity else ''
        command = 'ssh' + identity + ' -o "BatchMode yes" root@' + router + ' ' + command
    return local_cmd(command, err, on_err)

# Execute command locally
def local_cmd(shell_command, err=None, on_err=None):
    try:
        return subprocess.run(shell_command, shell=True, timeout=5, check=True,
                              stdout=subprocess.PIPE, stderr=subprocess.PIPE
                             ).stdout.decode('utf-8').strip()
    except Exception as e:
        if on_err:
            return on_err
        else:
            if err:
                sys.stderr.write(err + '\n\n')
            sys.stderr.write(str(e))
            if e.stderr:
                sys.stderr.write(' (' + e.stderr.strip().decode('utf-8') + ')')
            sys.stderr.write('\n')
            sys.exit(1)


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
        hosts.append({ k: v })
        return hosts[-1]
    return None


if __name__ == "__main__":
    main()
