IMAGE_NAME := openafs-contrib/afsbotcfg-package
SRCDIR := $(abspath $(CURDIR)/../../src)
CMD := help

.PHONY: help
help:
	@echo "usage: make TARGET"
	@echo "targets:"
	@echo "    build     to build the podman image"
	@echo "    check     to run the container"

.PHONY: build
build:
	podman build -t $(IMAGE_NAME):latest .

.PHONY: check
check:
	podman run -ti --rm -v $(SRCDIR):/app/src $(IMAGE_NAME) $(CMD)
