#
# afsbotcfg python package
#

.PHONY: help
help:
	@echo "usage: make <target>"
	@echo ""
	@echo "targets:"
	@echo "  lint       run linter"
	@echo "  build      create source distribution"
	@echo "  clean      remove generated files"
	@echo "  distclean  remove dist and generated files"

.PHONY: lint
lint:
	pyflakes afsbotcfg/*.py
	flake8 afsbotcfg/*.py

.PHONY: build
build:
	python -m build .

.PHONY: clean
clean:
	rm -rf afsbotcfg/__pycache__
	rm -rf afsbotcfg.egg-info/
	rm -rf build/

.PHONY: distclean
distclean: clean
	rm -rf dist/
