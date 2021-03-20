# wrtview

[![PyPI version](https://img.shields.io/pypi/v/wrtview.svg)](https://pypi.python.org/pypi/wrtview/)
[![PyPI pyversions](https://img.shields.io/pypi/pyversions/klipz.svg)](https://pypi.python.org/pypi/wrtview/)
[![MIT license](https://img.shields.io/badge/License-MIT-blue.svg)](https://github.com/ropg/wrtview/blob/master/LICENSE)
[![commits since last](https://img.shields.io/github/commits-since/ropg/wrtview/latest.svg)](https://github.com/ropg/wrtview/commits/main)

`wrtview` compactly displays data about hosts on a network centered around an OpenWRT router by combining data from various files and the output of commands on the OpenWRT. It is typically ran on a computer connected to a network that is built around an OpenWRT device, not on the OpenWRT device itself.

## Installation

wrtview is a python package on [PyPI](https://pypi.org/project/wrtview). If you have python 3.5 or newer installing is easy: 

```
python -m pip install wrtview
```

Alternatively, you can install the latest development version directly from the GitHub repository:

```
python -m pip install git+https://github.com/ropg/wrtview.git
```

## Setting up the access point for pubkey ssh access

For wrtview to work, you will need to set up ssh to provide pubkey (passwordless) access to your openwrt device. If you have a Mac or a linux machine, this is done by entering ...

```
scp ~/.ssh/id_rsa.pub root@<router>:/etc/dropbear/authorized_keys
```

... replacing `<router>` with the name or ip-address of your router. If you type your password one last time you should now be able to log into your router without a pasword by just typing `ssh root@<router>`. As soon as that works you are all set up to use wrtview.

## Using wrtview

If your router is at 192.168.1.1, all you need to do is enter `wrtview` and you'll see output like this:

```
Network 'lan' on 192.168.1.1:

  H  192.168.1.1   openwrt         
ADHE 192.168.1.100 MacbookPro        F0:18:98:36:06:73  Apple, Inc.             wlan1 493.286Mbps
ADHE 192.168.1.101 MacbookPro-wired  00:50:B6:98:C4:29  GOOD WAY IND. CO., LTD
ADHE 192.168.1.105 iPad              26:5A:90:A8:52:73  locally administered    wlan1 380.493Mbps
ADHE 192.168.1.130 JessicaPhone      EA:24:8C:29:DA:12  locally administered    wlan1 429.656Mbps
AD   192.168.1.151                   76:2A:A6:21:85:EC  locally administered       
ADHE 192.168.1.160 OldMacbookPro     20:C9:D0:84:02:D6  Apple, Inc.             wlan0 120.208Mbps
  HE 192.168.1.182 MacookAir         D0:E1:40:91:88:1E  Apple, Inc.                
ADHE 192.168.1.188 iPhone-John       2E:73:1F:31:B0:1D  locally administered    wlan1 456.389Mbps
ADHE 192.168.1.200 lights-gw         00:17:88:26:0A:26  Philips Lighting BV        
ADHE 192.168.1.201 tv                10:4F:A8:03:00:8C  Sony Corporation           
ADHE 192.168.1.212 printer           3C:2A:F4:42:24:A2  Brother Industries, LT     
AD   192.168.1.228                   2E:73:1F:31:B0:1D  locally administered    wlan1 456.389Mbps
ADHE 192.168.1.254 switch            00:1F:28:E2:66:82  HPN Supply Chain
```

As you can see, this network has a router called 'openwrt'. By default, all the hosts on the 'lan' network on the router are displayed. In the first column you can see whether a host is in the router's ARP table (`A`), whether it was given a DHCP lease (`D`) and whether it is in the hosts (`H`) and ethers (`E`) files. Then there's the host's IP-address and name (the latter either from hosts, ethers or DHCP lease). After that there's the MAC-address and the manufacturer from the vendor database.

Then if the MAC-address is found in the output of `iw <interface> station dump` for either wlan0 or wlan1, that interface is displayed with the expected throughput. You can merge in data from other access points that are serving the same network elsewere in the building, see below for details.

> As you can see the wlan0 interface is slower than wlan1, because in this case the former is on 2.4 GHz and the latter is on 5 GHz. Also, Apple handheld products randomize their MAC-addresses by default to prevent tracking, so they show up as 'locally administered', meaning they invented their own MAC-address. The Macbook Air is not on, and the stations with addresses ending in 151 and 228 have connected, but they are not in the hosts or ethers files. 

## Command line options

`--network`, `-n`

By default, wrtview will display clients in the 'lan' network on the openwrt, but you can set a different network here. To specify multiple networks, separate them with commas, without any added spaces. They will be listed one after the other with their own headers.

&nbsp;

`--wireless`, `-w`

By default, wrtview checks for clients on 'wlan0' and 'wlan1'. But you can specify any set of wireless interfaces that you would like to check for clients on, separating them with commas without any added spaces. Interfaces should be provided in the format `<interface>[@<host>][:<alias>]`. The hostname part allows you to check for clients on a different OpenWRT that may be serving a different part of a building. So for instance:

```
wrtview -w wlan0:S2,wlan1:S5,wlan0@192.168.0.4:N2,wlan1@192.168.0.4:N5 192.168.0.2
```

will cause wrtview to connect to 192.168.0.2 for the DHCP, hosts, ethers and ARP information, and show the 'wlan0' and 'wlan1' interfaces on that system as 'S2' and 'S5' respectively. Addtionally, this will cause wrtview to connect to 192.168.0.4 for data on clients to its 'wlan0' and 'wlan1' interfaces, marking their wifi connections 'N2' and 'N5' respectively in the output.

> Note that you also need to set up passwordless ssh access like detailed above for any additional wifi access points that you want queried in this way.

&nbsp;

`--leases`, `--hosts`, `--ethers`

These options can be used to specify alternative location for the DHCP leases file, the hosts file and the ethers files. The defaults should be fine though.

&nbsp;

`--format`, `-f`

Specify (in quotes) your own output format. If not specified, wrtview uses the following default format:

```
{arp}{dhcp}{hosts}{ethers} {ip:13.13} {name:17.17} {mac:17.17} {vendor:22.22}  {wifi alias} {wifi expected throughput}
```

The first four fields in this format string are set to either hold a space or an A, D, H or E respectively. The fields with the numbers after them are padded with spaces and cut at the specified length so that the output lines up nicely. Apart from the fields listed in the default format, you can use `wifi` (either 'W' or ' '), `clientID`, `wifi ap host`, `wifi ap interface` and every field from the output of `iw station dump <interface>`, prepended with `wifi `.

> More information on how the format string works can be found [here](https://www.programiz.com/python-programming/methods/string/format).

&nbsp;

`--sort`, `-s`

By default, the output is sorted by IP-address. Use this option to specify any field name from above to sort on. For example:

```
wrtview -s name 192.168.0.2
```

will sort the output on hostname.

&nbsp;

`--no-ghosts`

By default, wrtview will print any wifi stations that were found associated with probed wireless interfaces (such as 'wlan1') that were not part of any logical networks (such as 'lan') that you indicated. `--no-ghosts` suppresses this behaviour.

&nbsp;

`--no-header`

Suppresses headers like `Network 'lan' on 192.168.1.1:`

&nbsp;

`--identity`, `-i`

Use this to supply an ssh identity other than the default (which is usually `~/.ssh/id_rsa`).

&nbsp;

`--greppable`, `-g` 

This will replace all empty fields with a minus sign to make sure the number of space-separated fields in the output is the same for each line.

&nbsp;

`--version`, `-v`

Shows the version number. 

&nbsp;

## Known bugs, problems, limitations

### Running wrtview on the OpenWRT station itself

Currently wrtview is not really made to run on the OpenWRT router itself. It does try to detect if it is about to execute a command on itself and leaves off the ssh connection. But it would need python3 (which is large) installed and does things in memory that should be done differently in a memory-constrained environment. If people want this on OpenWRT it would probably be best to re-write it in Lua. Presently this is out of scope.

### IPv6

At present, wrtview does not support IPv6. It would need an additional default layout for IPv6 networks and some other changes. This is definitely on the agenda.
