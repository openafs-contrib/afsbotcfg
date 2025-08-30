IMAGE_NAME := openafs-contrib/afsbotcfg-ansible
AFSBOTCFG_DIRECTORY := $(abspath $(CURDIR)/../../.)
SSH_CONFIG_DIRECTORY := $(HOME)/.ssh
AFSBOTCFG_VAULT_FILE  := $(CURDIR)/.vault-afsbotcfg
SECRET := afsbotcfg-vault
CMD := "help"


.PHONY: help
help:
	@echo "usage: make <target>"
	@echo ""
	@echo "targets:"
	@echo "    build               to build the podman image"
	@echo "    secret              to the vault password to podman secrets"
	@echo "    clean               to remove the podman secret"
	@echo "    run CMD=\"...\"       to run the container"
	@echo ""
	@echo "examples:"
	@echo "  make secret"
	@echo "  make run CMD=\"ansible -i inventory/prod/hosts.ini all -m ping\""
	@echo "  make run CMD=\"ansible-lint afsbotcfg.yml\""
	@echo "  make run CMD=\"ansible-vault encrypt hello.txt\""
	@echo "  make run CMD=\"ansible-playbook -i inventory/prod/hosts.ini afsbotcfg.yml\""
	@echo "  make clean"

.PHONY: build
build:
	podman build -t $(IMAGE_NAME):latest .

.PHONY: secret
secret:
ifndef AFSBOTCFG_PASS_NAME
	podman secret create $(SECRET) $(AFSBOTCFG_VAULT_FILE)
else
	pass $(AFSBOTCFG_PASS_NAME) | podman secret create $(SECRET) -
endif


.PHONY: clean
clean:
	podman secret rm $(SECRET)

.PHONY: run
run:
	podman run -ti --rm \
        -v $(AFSBOTCFG_DIRECTORY):/app/afsbotcfg \
        -v $(SSH_CONFIG_DIRECTORY):/root/.ssh:ro \
        -v $(SSH_AUTH_SOCK):/root/ssh-agent.socket \
        --secret $(SECRET),type=mount,target=/root/vault \
        $(IMAGE_NAME) \
        $(CMD)
