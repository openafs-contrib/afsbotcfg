IMAGE_NAME := openafs-contrib/$(notdir $(CURDIR))

.PHONY: image
image:
	podman build -t $(IMAGE_NAME):latest .
