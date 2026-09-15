SHELL := bash

all:
	@echo "usage to come"

tests: clean
	@echo -n "Testing base functionality..."
	@python3 -c 'from tests.full import svr'
	@echo "success"

clean:
	@if [ -f *db ]; then rm -v *db; fi
	@if [ -f *log.gz ]; then rm -v *log.gz; fi
	@find -type d | grep '__pycache__$$' | while read dir; do rm -v -rf "$$dir"; done
