IMAGE_NAME := openafs-contrib/afsbotcfg-fake-worker

.PHONY: help
help:
	@echo "usage: make <target>"
	@echo ""
	@echo "targets:"
	@echo "    build      to build the image"
	@echo "    run        to run the container"
	@echo ""
	@echo "examples:"

.PHONY: build
build:
	podman build -t $(IMAGE_NAME):latest .

.PHONY: run
run:
	podman run -ti --rm $(IMAGE_NAME)
