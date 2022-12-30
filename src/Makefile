
# afsbotcfg package version
VERSION=1.0.3

# afsbotcfg package source files
SOURCE=\
  afsbotcfg/factory.py \
  afsbotcfg/gerrit.py \
  afsbotcfg/master.py \
  afsbotcfg/schedulers.py \
  afsbotcfg/steps.py

help:
	@echo "usage: make <target>"
	@echo ""
	@echo "targets:"
	@echo "  lint       run linter"
	@echo "  test       run tests"
	@echo "  build      create source distribution"
	@echo "  clean      remove generated files"
	@echo "  distclean  remove dist and generated files"

lint:
	pyflakes afsbotcfg/*.py
	flake8 --ignore=E501 afsbotcfg/*.py

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
