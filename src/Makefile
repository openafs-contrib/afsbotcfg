
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
	flake8 afsbotcfg/*.py

test: lint

.PHONY: build
build:
	python -m build .

clean:
	rm -rf afsbotcfg/__pycache__
	rm -rf afsbotcfg.egg-info/
	rm -rf build/

distclean: clean
	rm -rf dist/
