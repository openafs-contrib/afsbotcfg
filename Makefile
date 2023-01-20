.PHONY: help init vault collections lint test clean distclean

help:
	@echo "usage: make <target>"
	@echo ""
	@echo "setup targets:"
	@echo "  setup              to run all setup targets"
	@echo "  setup-venv         to create the Python virtual environment (optional)"
	@echo "  setup-vault        to download the vault key file (ssh creds are required)"
	@echo "  setup-collections  to install the required Ansible collections"
	@echo ""
	@echo "run targets: (activate the venv first)"
	@echo "  build              to build the afsbotcfg Python package"
	@echo "  lint               to run lint check"
	@echo "  test               to run molecule test"
	@echo "  run                to run ansible-playbook"
	@echo ""
	@echo "cleanup targets:"
	@echo "  clean              to remove generated files"
	@echo "  distclean          to remove all generated and downloaded files"

.envrc:
	echo export ANSIBLE_INVENTORY=inventory/openafs/hosts.ini >.envrc
	echo export ANSIBLE_VAULT_IDENTITY_LIST=afsbotcfg@.vault-afsbotcfg >>.envrc

.venv/bin/activate: .envrc requirements.txt
	test -d .venv || python3 -m venv .venv
	.venv/bin/pip install -U pip wheel
	.venv/bin/pip install -r requirements.txt
	echo "test -f .envrc && source .envrc" >> .venv/bin/activate

.config/molecule/config.yml:
	@echo Creating default molecule base configuration.
	mkdir -p .config/molecule
	echo "driver:" > .config/molecule/config.yml
	echo "  name: vagrant" >> .config/molecule/config.yml

setup: setup-venv setup-vault setup-collections

setup-venv: .envrc .venv/bin/activate .config/molecule/config.yml

setup-vault:
	scp buildbot.openafs.org:.vault-afsbotcfg .vault-afsbotcfg

setup-collections:
	ansible-galaxy collection install --force -p collections -r requirements.yml

lint:
	$(MAKE) -C src lint
	yamllint openafs_buildbot.yaml
	ansible-lint

test:
	molecule test

build:
	$(MAKE) -C src build

run:
	ansible-playbook openafs_buildbot.yaml

clean:
	$(MAKE) -C src clean

distclean: clean
	$(MAKE) -C src distclean
	rm -rf .envrc .venv .vault-afsbotcfg
