.PHONY: help clean install install-dev

help:
	@echo "install - install"
	@echo "install-dev - install also development dependencies"
	@echo "clean - clean all below"

install:
	python -m pip install pipenv
	pipenv install

install-dev:
	python -m pip install pipenv
	pipenv install --dev

clean: clean-pyc

clean-pyc:
	find . -name '*~' -exec rm -f {} +
	find . -name '*.log*' -delete
	find . -name '*_cache' -exec rm -rf {} +
	find . -name '*.egg-info' -exec rm -rf {} +
	find . -name '*.pyc' -exec rm -f {} +
	find . -name '*.pyo' -exec rm -f {} +
	find . -name '__pycache__' -exec rm -rf {} +

clean-results:
	find . -name 'tito_*.csv' -delete
	rm -rf certificates
	mkdir certificates

	rm -rf stamped
	mkdir stamped

	rm -rf blank
	mkdir blank
