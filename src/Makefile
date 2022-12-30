
help:
	@echo "usage: make <target>"
	@echo ""
	@echo "targets:"
	@echo "  lint       run linter"
	@echo "  test       run tests"
	@echo "  build      create source distribution"
	@echo "  clean      remove generated files"

lint:
	pyflakes afsbotcfg/*.py
	flake8 --ignore=E501 afsbotcfg/*.py

test: lint

build:
	python setup.py sdist

clean:
	rm -rf afsbotcfg/__pycache__
	rm -rf afsbotcfg.egg-info/
	rm -rf build/
	rm -rf dist/

distclean: clean
