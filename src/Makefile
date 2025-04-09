
# afsbotcfg package version
ifdef AFSBOTCFG_VERSION
VERSION=$(AFSBOTCFG_VERSION)
else
VERSION=25.4.9rc2
endif

# afsbotcfg package source files
SOURCE=\
  afsbotcfg/factory.py \
  afsbotcfg/gerrit.py \
  afsbotcfg/master.py \
  afsbotcfg/schedulers.py \
  afsbotcfg/steps.py

# Default flake8 ignore list.
FLAKE8_IGNORE = E121,E123,E126,E226,E24,E704,W503,W504

help:
	@echo "usage: make <target>"
	@echo ""
	@echo "targets:"
	@echo "  lint       run linter"
	@echo "  test       run tests"
	@echo "  build      create source distribution"
	@echo "  clean      remove generated files"
	@echo "  distclean  remove dist and generated files"
	@echo ""
	@echo "VERSION=$(VERSION)"

lint:
	pyflakes afsbotcfg/*.py
	flake8 --ignore=E501,$(FLAKE8_IGNORE) afsbotcfg/*.py

test: lint

afsbotcfg/__init__.py: Makefile
	echo "__version__ = '$(VERSION)'" >afsbotcfg/__init__.py

dist/afsbotcfg-$(VERSION).tar.gz: $(SOURCE) Makefile
	echo "__version__ = '$(VERSION)'" >afsbotcfg/__init__.py
	python setup.py sdist
	@echo "Wrote $@"

build: dist/afsbotcfg-$(VERSION).tar.gz

clean:
	rm -rf afsbotcfg/__init__.py
	rm -rf afsbotcfg/__pycache__
	rm -rf afsbotcfg.egg-info/
	rm -rf build/

distclean: clean
	rm -rf dist/
