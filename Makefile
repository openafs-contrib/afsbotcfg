#
# Run the OpenAFS buildbot playbook.
#

REGISTRY := ghcr.io/

# Playbook
AFSBOTCFG_SECRET_NAME   := vault-afsbotcfg
AFSBOTCFG_VAULT_FILE    := $(CURDIR)/.vault-afsbotcfg
AFSBOTCFG_SSH_DIRECTORY := $(HOME)/.ssh

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
	@echo "  test                 to run the playbook on the local container"
	@echo "  clean                to stop and remove the test container"
	@echo "  reallyclean          to remove containers, images, and built packages"
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
	$(MAKE) --no-print-directory -C podman images

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
        $(REGISTRY)openafs-contrib/afsbotcfg-ansible:latest \
	    ansible-vault encrypt --vault-password-file=/root/vault $(FILE)

.PHONY: lint
lint:
	$(INFO) "Running lint checks"
	podman run -ti --rm \
        --volume $(CURDIR):/app/afsbotcfg:ro \
        --secret $(AFSBOTCFG_SECRET_NAME),type=mount,target=/root/vault \
        $(REGISTRY)openafs-contrib/afsbotcfg-ansible:latest \
		ansible-lint afsbotcfg.yml

.PHONY: ping
ping:
	$(INFO) "Pinging buildbot"
	podman run -ti --rm \
        --volume $(CURDIR):/app/afsbotcfg:ro \
        --volume $(AFSBOTCFG_SSH_DIRECTORY):/root/.ssh:ro \
        $(VOLUME_SSH_AGENT_SOCKET) \
        --secret $(AFSBOTCFG_SECRET_NAME),type=mount,target=/root/vault \
        $(REGISTRY)openafs-contrib/afsbotcfg-ansible:latest \
        ansible -i inventory/prod/hosts.ini all -m ping

WORKERS := $(subst files/workers/,,$(wildcard files/workers/*))
.PHONY: pod
pod: .pod
.pod:
	$(INFO) "Creating test containers"
	podman volume create afsbotcfg
	podman pod create --name afsbotcfg --infra-name=afsbotcfg-infra \
      -p 8011:8011 -p 8000:8000 --volume afsbotcfg:/root/.ssh
	podman inspect afsbotcfg-infra | \
      grep '"ImageName":' | \
      sed 's/  *"ImageName":  *"//' | \
      sed 's/",//' >.afsbotcfg-infra
	podman run --name fake-gerrit --pod afsbotcfg --detach \
      $(REGISTRY)openafs-contrib/afsbotcfg-fake-gerrit:latest
	podman run --name fake-buildbot-master --pod afsbotcfg --detach \
      $(REGISTRY)openafs-contrib/afsbotcfg-fake-master:latest
	@for w in $(WORKERS); do \
      if [ "$(TEST_BUILDS)" = yes ]; then \
        case "$$w" in \
        alma10-*) img="$(REGISTRY)openafs-contrib/afsbotcfg-fake-worker-alma10:latest" ;; \
        *) img="$(REGISTRY)openafs-contrib/afsbotcfg-fake-worker:latest" ;; \
        esac; \
      else \
        img="$(REGISTRY)openafs-contrib/afsbotcfg-fake-worker:latest" ; \
      fi; \
      podman run --name fake-buildbot-worker-$$w --pod afsbotcfg --detach $$img $$w secret; \
    done
	touch .pod

.PHONY: check test
check test: package .pod
	$(INFO) "Running buildbot playbook test"
	podman run --pod afsbotcfg -ti --rm \
      --volume $(CURDIR):/app/afsbotcfg:ro \
      $(REGISTRY)openafs-contrib/afsbotcfg-ansible:latest \
      ansible-playbook \
        -i inventory/test/hosts.ini \
        -e afsbotcfg_passwords=test_passwords \
        afsbotcfg.yml
	$(INFO) "fake-gerrit           listening on http://localhost:8000"
	$(INFO) "fake-buildbot-master  listening on http://localhost:8011"

.PHONY: clean
clean:
	-podman pod kill afsbotcfg
	-podman pod rm afsbotcfg
	-podman volume rm afsbotcfg
	rm -rf .pod

.PHONY: reallyclean
reallyclean: clean
	$(MAKE) --no-print-directory -C src clean
	-podman rmi openafs-contrib/afsbotcfg-fake-gerrit:latest
	-podman rmi openafs-contrib/afsbotcfg-fake-worker:latest
	-podman rmi openafs-contrib/afsbotcfg-package:latest
	-podman rmi openafs-contrib/afsbotcfg-ansible:latest
	-podman rmi openafs-contrib/afsbotcfg-fake-master:latest
	-( test -f .afsbotcfg-infra && podman rmi $(file < .afsbotcfg-infra) )
	rm -f .afsbotcfg-infra

.PHONY: deploy
deploy:
	$(INFO) "Running buildbot playbook"
	podman run -ti --rm \
        --volume $(CURDIR):/app/afsbotcfg:ro \
        --volume $(AFSBOTCFG_SSH_DIRECTORY):/root/.ssh:ro \
        $(VOLUME_SSH_AGENT_SOCKET) \
        --secret $(AFSBOTCFG_SECRET_NAME),type=mount,target=/root/vault \
        $(REGISTRY)openafs-contrib/afsbotcfg-ansible:latest \
        ansible-playbook \
          -i inventory/prod/hosts.ini \
          --vault-password-file=/root/vault \
          afsbotcfg.yml
