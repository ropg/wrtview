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
