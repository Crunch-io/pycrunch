# "make" compatibility for us old-timers.

PHONY: check clean develop install test

PYTHON ?= python

#: Same as "check"
test: check

#: Run all (py)tests
check:
	pytest tests

#: Clean up temporary files
clean:
	$(PYTHON) ./setup.py $@

#: Set to run from source
develop:
	$(PYTHON) ./setup.py $@

#: Install this gem
install:
	$(PYTHON) ./setup.py $@
