SHELL := bash

all:
	@echo "make <config | testdns | testdhcp | testpxe | clearcache | clean>"

config: lib/settings.py

lib/settings.py:
	@echo "DnsMasqBinPath = \"$$(read -p "Enter path for dnsmasq binary [/usr/sbin/dnsmasq]: " tgt; [[ -z "$$tgt" ]] && echo "/usr/sbin/dnsmasq" || echo "$$tgt")\"" > lib/settings.py

clean: clearcache
	@if test -f lib/settings.py; then rm -v lib/settings.py; fi

testdhcp: clearcache
	echo "dhcp testing coming"

testdns: clearcache
	@echo -n "Testing base functionality..."
	@python3 -c 'from tests.dns import svr'
	@echo "success"

clearcache:
	@if ls *conf 2> /dev/null > /dev/null > /dev/null; then rm -v *conf; fi
	@if ls *json 2> /dev/null > /dev/null; then rm -v *json; fi
	@if ls *db 2> /dev/null > /dev/null; then rm -v *db; fi
	@if ls *log.gz 2> /dev/null > /dev/null; then rm -v *log.gz; fi
	@find -type d | grep '__pycache__$$' | while read dir; do rm -v -rf "$$dir"; done
