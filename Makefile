.PHONY: help init vault collections lint check test clean distclean

help:
	@echo "usage: make <target>"
	@echo ""
	@echo "targets:"
	@echo "  init         to create a Python virtual environment"
	@echo "  vault        to download vault file (ssh creds required)"
	@echo "  collections  to install ansible collections"
	@echo "  lint         to run lint check"
	@echo "  check        to run buildbot checkconfig"
	@echo "  test         to run molecule test"
	@echo "  clean        to remove generated files"
	@echo "  distclean    to remove generated files and virtual environment"

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

.check: files/email_templates.py files/forcegerritbuild.py files/master.cfg files/passwords.ini
	mkdir -p .check
	for f in email_templates.py forcegerritbuild.py master.cfg; do cp files/$$f .check; done
	ansible-vault decrypt --output .check/passwords.ini files/passwords.ini
	echo "buildbotURL='http://localhost'" > .check/settings.py
	echo "www_port=8010" >> .check/settings.py

init: .envrc .venv/bin/activate

vault:
	scp buildbot.openafs.org:.vault-afsbotcfg .vault-afsbotcfg

collections:
	ansible-galaxy collection install openafs_contrib.buildbot
	ansible-galaxy collection install openafs_contrib.openafs

lint:
	yamllint openafs_buildbot.yaml
	ansible-lint

check: .check
	buildbot checkconfig .check

test:
	molecule test

clean:
	rm -rf .check

distclean: clean
	rm -rf .envrc .venv .vault-afsbotcfg
