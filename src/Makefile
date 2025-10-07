#
# afsbotcfg python package
#

IMAGE_REGISTRY := ghcr.io
IMAGE_NAME := docker://$(IMAGE_REGISTRY)/openafs-contrib/afsbotcfg-package:latest

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
	podman run -ti --rm -v $(CURDIR):/app/src $(IMAGE_NAME) lint

.PHONY: build
build:
	podman run -ti --rm -v $(CURDIR):/app/src $(IMAGE_NAME) build

.PHONY: clean
clean:
	rm -rf afsbotcfg/__pycache__
	rm -rf afsbotcfg.egg-info/
	rm -rf build/

.PHONY: distclean
distclean: clean
	rm -rf dist/
