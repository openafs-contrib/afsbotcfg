IMAGE_NAME := openafs-contrib/afsbotcfg-test
CONTAINER_NAME := buildbot-test
SRCDIR := $(abspath $(CURDIR)/../../src)
SSH_AUTHORIZED_KEY := $(HOME)/.ssh/id_rsa.pub


.PHONY: help
help:
	@echo "usage: make TARGET"
	@echo "targets:"
	@echo "    build     to build the podman image"
	@echo "    start     to create and run the container"
	@echo "    stop      to stop and remove the container"

.PHONY: build
build:
	podman build -t $(IMAGE_NAME):latest .

.PHONY: start
start:
	podman run -ti \
		--detach \
		--volume $(SSH_AUTHORIZED_KEY):/root/.ssh/authorized_keys:ro \
		--name $(CONTAINER_NAME) \
		-p 2222:22 \
		-p 8011:8011 \
		$(IMAGE_NAME)

.PHONY: stop
stop:
	podman stop $(CONTAINER_NAME)
	podman rm $(CONTAINER_NAME)

