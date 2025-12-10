REGISTRY := ghcr.io/
IMAGE_NAME := $(REGISTRY)openafs-contrib/$(notdir $(CURDIR))

.PHONY: image
image:
	podman build -t $(IMAGE_NAME):latest .
