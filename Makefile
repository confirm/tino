#
# Settings
#

SOURCE_DIRS = confirm/typr
BUILD_DIR = build
LINTER_CONFIGS = https://gitlab.confirm.ch/confirm/dev-configs/-/raw/main/linter
PYPI_INDEX = https://pypi.confirm.ch/

.PHONY: build docs vendor-js

#
# Cleanup
#

clean: clean-cache clean-test clean-build clean-venv

clean-cache:
	find . -name '__pycache__' -delete

clean-test:
	rm -vf .coverage .coveragerc .isort.cfg .pylintrc tox.ini

clean-build:
	rm -vrf $(BUILD_DIR) .eggs *.egg-info

clean-venv:
	rm -vrf .venv

#
# Install
#

venv:
	python3 -m venv .venv

develop-python:
	pip3 install -U -i $(PYPI_INDEX) -e .[develop]

develop-node:
	npm install

develop: develop-python develop-node

install:
	pip3 install -i $(PYPI_INDEX) .

#
# Development
#

isort:
	curl -sSfLo .isort.cfg $(LINTER_CONFIGS)/isort.cfg
	isort $(SOURCE_DIRS)

server:
	uvicorn confirm.typr:create_app --factory --port 8000 --reload

#
# Test
#

test-commits:
	git tools validate

test-isort:
	curl -sSfLo .isort.cfg $(LINTER_CONFIGS)/isort.cfg
	isort -c --diff $(SOURCE_DIRS)

test-pycodestyle:
	curl -sSfLo tox.ini $(LINTER_CONFIGS)/tox.ini
	pycodestyle $(SOURCE_DIRS)

test-pylint:
	curl -sSfLo .pylintrc $(LINTER_CONFIGS)/pylintrc
	pylint $(SOURCE_DIRS)

test-eslint:
	curl -sSfo eslint.config.mjs $(LINTER_CONFIGS)/eslint.config.mjs
	npx eslint $(SOURCE_DIRS)/static/js/*.js

test-stylelint:
	curl -sSfLo .stylelintrc.yml $(LINTER_CONFIGS)/stylelintrc.yml
	npx stylelint $(SOURCE_DIRS)/static/css/*.css

test: test-commits test-isort test-pycodestyle test-pylint test-eslint test-stylelint

#
# Build
#

package:
	python3 -mbuild -o $(BUILD_DIR)

docs:
	sphinx-build docs $(BUILD_DIR)/docs

autodocs:
	sphinx-autobuild --open-browser --port 8888 --watch confirm docs $(BUILD_DIR)/docs

vendor-js:
	npm run build

build: vendor-js package docs
