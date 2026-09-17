SHELL := bash

all:
	@echo "make <config | clearcache | clean | testdns | testdhcp | testpxe | testtftp>"

config: lib/settings.py

lib/settings.py:
	@echo "DnsMasqBinPath = \"$$(read -p "Enter path for dnsmasq binary [/usr/sbin/dnsmasq]: " tgt; [[ -z "$$tgt" ]] && echo "/usr/sbin/dnsmasq" || echo "$$tgt")\"" > lib/settings.py

clean: clearcache
	@if test -f lib/settings.py; then rm -v lib/settings.py; fi

testtftp: clearcache
	@echo -n "Testing PXE functionality..."
	@python3 -c 'from tests.tftp import svr'
	@echo "success"

testpxe: clearcache
	@echo -n "Testing PXE functionality..."
	@python3 -c 'from tests.pxe import svr'
	@echo "success"

testdhcp: clearcache
	@echo -n "Testing DHCP functionality..."
	@python3 -c 'from tests.dhcp import svr'
	@echo "success"

testdns: clearcache
	@echo -n "Testing DNS functionality..."
	@python3 -c 'from tests.dns import svr'
	@echo "success"

clearcache:
	@if ls *conf 2> /dev/null > /dev/null > /dev/null; then rm -v *conf; fi
	@if ls *pid 2> /dev/null > /dev/null > /dev/null; then rm -v *pid; fi
	@if ls *log 2> /dev/null > /dev/null > /dev/null; then rm -v *log; fi
	@find -type d | grep '__pycache__$$' | while read dir; do rm -v -rf "$$dir"; done
