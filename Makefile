.PHONY: help init vault collections lint test clean distclean

MOLECULE_DESTROY ?= always

help:
	@echo "usage: make <target>"
	@echo ""
	@echo "targets:"
	@echo "  init         to create a Python virtual environment"
	@echo "  vault        to download vault file (ssh creds required)"
	@echo "  collections  to install ansible collections"
	@echo "  lint         to run lint check"
	@echo "  test         to run molecule test"
	@echo "  clean        to remove generated files"
	@echo "  distclean    to remove generated files and virtual environment"
	@echo ""
	@echo "environment:"
	@echo "  MOLECULE_DRIVER=<driver-name>"
	@echo "..MOLECULE_DESTROY='always' | 'never'"

.envrc:
	echo export ANSIBLE_INVENTORY=inventory/openafs/hosts.ini >.envrc
	echo export ANSIBLE_VAULT_IDENTITY_LIST=afsbotcfg@.vault-afsbotcfg >>.envrc

.venv/bin/activate: .envrc
	test -d .venv || python3 -m venv .venv
	.venv/bin/pip install -U pip
	.venv/bin/pip install wheel
	.venv/bin/pip install SQLAlchemy==1.3.17
	.venv/bin/pip install buildbot[bundle]==2.8.2
	.venv/bin/pip install ansible ansible-lint yamllint pyflakes
	.venv/bin/pip install molecule molecule-vagrant molecule-virtup
	echo "test -f .envrc && source .envrc" >> .venv/bin/activate

.config/molecule/config.yml:
	@echo Creating default molecule base configuration.
	mkdir -p .config/molecule
	echo "driver:" > .config/molecule/config.yml
	echo "  name: vagrant" >> .config/molecule/config.yml

init: .envrc .venv/bin/activate .config/molecule/config.yml

vault:
	scp buildbot.openafs.org:.vault-afsbotcfg .vault-afsbotcfg

collections:
	ansible-galaxy collection install openafs_contrib.buildbot
	ansible-galaxy collection install openafs_contrib.openafs

lint:
	yamllint openafs_buildbot.yaml
	ansible-lint

test:
	molecule test --destroy $(MOLECULE_DESTROY)

clean:

distclean: clean
	rm -rf .envrc .venv .vault-afsbotcfg
