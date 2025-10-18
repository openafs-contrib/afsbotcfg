#
# Run the OpenAFS buildbot playbook.
#

# Playbook
AFSBOTCFG_REGISTRY      := ghcr.io
AFSBOTCFG_IMAGE_NAME    := docker://$(AFSBOTCFG_REGISTRY)/openafs-contrib/afsbotcfg-ansible:latest
AFSBOTCFG_SECRET_NAME   := vault-afsbotcfg
AFSBOTCFG_VAULT_FILE    := $(CURDIR)/.vault-afsbotcfg
AFSBOTCFG_SSH_DIRECTORY := $(HOME)/.ssh

# Testing
TEST_IMAGE_NAME         := docker://$(AFSBOTCFG_REGISTRY)/openafs-contrib/afsbotcfg-test
TEST_CONTAINER_NAME     := buildbot-test
TEST_AUTHORIZED_KEY     := $(HOME)/.ssh/id_rsa.pub

# Mount the ssh-agent socket if available, otherwise ssh will prompt for
# a password.
ifdef SSH_AUTH_SOCK
VOLUME_SSH_AGENT_SOCKET := --volume $(SSH_AUTH_SOCK):/root/ssh-agent.socket
endif

# For colorized info messages.  Define NO_COLOR to disable.
ifndef NO_COLOR
RED = \033[0;31m
GREEN = \033[0;32m
YELLOW = \033[0;33m
START_COLOR = $(GREEN)
END_COLOR = \033[0m
endif
INFO := @printf "$(START_COLOR)==> %s <==$(END_COLOR)\n"

.PHONY: help
help:
	@echo "Usage: make <target>"
	@echo ""
	@echo "setup targets:"
	@echo "  images               to create the Podman container images"
	@echo "  package              to create the Python afsbotcfg package"
	@echo "  secret               to setup the vault key secret"
	@echo "  encrypt FILE=<path>  to encrypt a file with the vault key"
	@echo ""
	@echo "test targets:"
	@echo "  lint                 to run static checks"
	@echo "  create               to create the local test container"
	@echo "  converge             to run the playbook on the local test container"
	@echo "  destroy              to destroy the local test container"
	@echo "  test                 to run create, converge, destroy"
	@echo ""
	@echo "deployment targets:"
	@echo "  ping                 to check connectivity to the buildbot server"
	@echo "  deploy               to run the buildbot playbook"

.PHONY: package
package:
	$(INFO) "Building Python package afsbotcfg"
	$(MAKE) --no-print-directory -C src build

.PHONY: images
images:
	$(INFO) "Building podman images"
	$(MAKE) --no-print-directory -C container build

.PHONY: secret
secret:
	$(INFO) "Setting secret '$(AFSBOTCFG_SECRET_NAME)'"
ifndef AFSBOTCFG_PASS_NAME
	podman secret create $(AFSBOTCFG_SECRET_NAME) $(AFSBOTCFG_VAULT_FILE)
else
	pass $(AFSBOTCFG_PASS_NAME) | podman secret create $(AFSBOTCFG_SECRET_NAME) -
endif

.PHONY: encrypt
encrypt:
	$(INFO) "Encrypting '$(FILE)'"
	@podman run -ti --rm \
        --volume $(CURDIR):/app/afsbotcfg \
        --secret $(AFSBOTCFG_SECRET_NAME),type=mount,target=/root/vault \
        $(AFSBOTCFG_IMAGE_NAME) \
	    ansible-vault encrypt $(FILE)

.PHONY: lint
lint:
	$(INFO) "Running lint checks"
	podman run -ti --rm \
        --volume $(CURDIR):/app/afsbotcfg:ro \
        --secret $(AFSBOTCFG_SECRET_NAME),type=mount,target=/root/vault \
        $(AFSBOTCFG_IMAGE_NAME) \
		ansible-lint afsbotcfg.yml

.PHONY: ping
ping:
	$(INFO) "Pinging buildbot"
	podman run -ti --rm \
        --volume $(CURDIR):/app/afsbotcfg:ro \
        --volume $(AFSBOTCFG_SSH_DIRECTORY):/root/.ssh:ro \
        $(VOLUME_SSH_AGENT_SOCKET) \
        --secret $(AFSBOTCFG_SECRET_NAME),type=mount,target=/root/vault \
        $(AFSBOTCFG_IMAGE_NAME) \
        ansible -i inventory/prod/hosts.ini all -m ping

.PHONY: create
create: .test_container
.test_container:
	podman run --detach -p 2222:22 -p 8011:8011 -p 9989:9989 \
        --volume $(TEST_AUTHORIZED_KEY):/root/.ssh/authorized_keys:ro \
        --name $(TEST_CONTAINER_NAME) \
        $(TEST_IMAGE_NAME)
	podman ps --quiet --noheading --filter name=$(TEST_CONTAINER_NAME) >$@

.PHONY: converge
converge: create
	$(INFO) "Running buildbot playbook test"
	podman run -ti --rm \
        --volume $(CURDIR):/app/afsbotcfg:ro \
        --volume $(AFSBOTCFG_SSH_DIRECTORY):/root/.ssh:ro \
        $(VOLUME_SSH_AGENT_SOCKET) \
        --secret $(AFSBOTCFG_SECRET_NAME),type=mount,target=/root/vault \
        $(AFSBOTCFG_IMAGE_NAME) \
        ansible-playbook -i inventory/test/hosts.ini afsbotcfg.yml
	$(INFO) "Listening on http://localhost:8011"

.PHONY: destroy
destroy:
	podman stop $(TEST_CONTAINER_NAME)
	podman rm $(TEST_CONTAINER_NAME)
	rm -f .test_container

.PHONY: test
test: create converge destroy

.PHONY: deploy
deploy:
	$(INFO) "Running buildbot playbook"
	podman run -ti --rm \
        --volume $(CURDIR):/app/afsbotcfg:ro \
        --volume $(AFSBOTCFG_SSH_DIRECTORY):/root/.ssh:ro \
        $(VOLUME_SSH_AGENT_SOCKET) \
        --secret $(AFSBOTCFG_SECRET_NAME),type=mount,target=/root/vault \
        $(AFSBOTCFG_IMAGE_NAME) \
        ansible-playbook -i inventory/prod/hosts.ini afsbotcfg.yml
