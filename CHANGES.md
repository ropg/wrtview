## 1.0.1

* More robust determination of network interface names
* Speeds now reported as rounded Mbps for rx, tx (and expected throughput if available)

## 1.0.0

* BREAKING CHANGE: networks and wifi-interfaces now with multiple `-n` and `-w` options
* Added ping script to ping entire networks from router
* Offline hosts are greyed, router itself in bold
* Fixed various bugs in presenting data
* More readable code parsing data out of command output
* More descriptive errors
* Updated vendors file for MAC->vendor lookup from IEEE with new (included) script
* Cleaner code

## 0.11.1

* Fixed bug that caused ARP-table to not read correctly
* Some minor code cleanup after pylint

## 0.11.0

* Uses `-o "BatchMode yes"` for ssh to prevent password login
* Added `--greppable` / `-g` for fixed number of fields in output
* Added a few help messages for command line options when invoked with `-h`

## 0.10.0

* Now has a `--identity` / `-i` command line option to supply an ssh identity file
* Detects if running on openwrt to execute command on, does not use ssh in that case
* More meaningful output if someting doesn't work with getting the data
* Fixed bug that yielded invalid addresses from ARP output

## 0.9.1 

* Took out f'strings' and capture_output feature of subprocess.run so we depend on Python 3.5 instead of 3.8.
* Replaced (untrue) Python 3.0 requirement by true 3.5

## 0.9.0

* Initial release
