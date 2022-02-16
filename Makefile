# Compatibility for us old-timers.

PHONY: check clean develop install test

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
	$(PYTHON) ./setup.py develop

#: Install package locally without the verbiage
install:
	$(PYTHON) ./setup.py install
