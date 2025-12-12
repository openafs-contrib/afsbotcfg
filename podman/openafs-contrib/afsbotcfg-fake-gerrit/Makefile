REGISTRY := ghcr.io/
IMAGE_NAME := $(REGISTRY)openafs-contrib/$(notdir $(CURDIR))

.PHONY: image
image:
	podman build -t $(IMAGE_NAME):latest .

.PHONY: run
run: image
	podman run --rm -p 8000:8000 --name fake-gerrit $(IMAGE_NAME):latest
