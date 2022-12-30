
# Generated molecule.yml files.
AFSBOTCFG_MOLECULE_YML = \
  molecule/default/molecule.yml \
  molecule/master-with-vault/molecule.yml \
  molecule/unix-builder/molecule.yml

# Molecule settings and scenario name.
AFSBOTCFG_MOLECULE_JSON ?= molecule.json
AFSBOTCFG_MOLECULE_SCENARIO ?= master-with-vault
AFSBOTCFG_MOLECULE_HOST ?= afsbotcfg-master


.PHONY: help
help:
	@echo "Usage: make <target>"
	@echo ""
	@echo "Setup targets:"
	@echo "  setup              to setup the virtualenv and generate files"
	@echo ""
	@echo "Run targets:"
	@echo "  build              to build the afsbotcfg Python package"
	@echo "  lint               to run yaml and ansible lint checks"
	@echo "  test               to run molecule test"
	@echo "  check              to run molecule create, converge, verify"
	@echo "  play               to run the playbook to update the buildbot"
	@echo ""
	@echo "Cleanup targets:"
	@echo "  clean              to destroy the molecule instance and remove generated files"
	@echo "  reallyclean        to remove all non-project files"
	@echo ""
	@echo "Environment:"
	@echo "  AFSBOTCFG_MOLECULE_JSON         molecule driver config (default: molecule.json)"
	@echo "  AFSBOTCFG_MOLECULE_SCENARIO     make check/test molecule scenario (default: master-with-vault)"
	@echo ""

.venv/bin/activate: requirements.txt molecule-driver-requirements.txt
	@echo "Installing Anisble in virtualenv."
	test -d .venv || python3 -m venv .venv
	.venv/bin/pip install -U pip wheel
	.venv/bin/pip install -r requirements.txt
	.venv/bin/pip install -r molecule-driver-requirements.txt
	touch .venv/bin/activate
	@echo "Run 'source .venv/bin/activate' to activate the Python virtualenv."

.vault-afsbotcfg:
	@echo "Downloading vault key."
	scp buildbot.openafs.org:.vault-afsbotcfg .vault-afsbotcfg

collections: .venv/bin/activate requirements.yml
	@echo "Installing required Ansible collections."
	.venv/bin/ansible-galaxy collection install --force -p collections -r requirements.yml
	touch collections

# Support out of tree molecule.json files.
ifeq ($(AFSBOTCFG_MOLECULE_JSON), molecule.json)
molecule.json: molecule.json.sample
	cp molecule.json.sample molecule.json
	@echo "Please run 'make setup' after making any changes to 'molecule.json'."
endif

# Python oneliner to avoid jq dependency.
molecule-driver-requirements.txt: $(AFSBOTCFG_MOLECULE_JSON)
	@echo "Generating $@"
	python -c 'import json; print("\n".join(json.load(open("$(AFSBOTCFG_MOLECULE_JSON)"))["requirements"]))' >$@

%.yml : %.yml.j2 $(AFSBOTCFG_MOLECULE_JSON) .venv/bin/activate
	.venv/bin/python render.py molecule $(AFSBOTCFG_MOLECULE_JSON) $< $@

.PHONY: setup
setup: $(AFSBOTCFG_MOLECULE_YML)

.PHONY: lint
lint: .venv/bin/activate
	. .venv/bin/activate; $(MAKE) -C src lint
	. .venv/bin/activate; yamllint \
	     openafs_buildbot.yaml \
	     inventory/openafs/group_vars/openafs_buildbot_masters/master.yml \
	     molecule/*/*.yml
	. .venv/bin/activate; ansible-lint \
	    --exclude=inventory/openafs/group_vars/openafs_buildbot_masters/worker_passwords.yml \
	    --exclude=inventory/openafs/group_vars/openafs_buildbot_masters/admin_passwords.yml

.PHONY: build
build: .venv/bin/activate
	. .venv/bin/activate; $(MAKE) -C src build

.PHONY: test
test: lint .venv/bin/activate molecule/$(AFSBOTCFG_MOLECULE_SCENARIO)/molecule.yml
	rm -f .create
	. .venv/bin/activate; molecule test -s $(AFSBOTCFG_MOLECULE_SCENARIO)

.create: .venv/bin/activate molecule/$(AFSBOTCFG_MOLECULE_SCENARIO)/molecule.yml
	. .venv/bin/activate; molecule create -s $(AFSBOTCFG_MOLECULE_SCENARIO)
	@echo $(AFSBOTCFG_MOLECULE_SCENARIO) >.create

# Created once before converge. Run 'make clean' to destroy the instance.
.PHONY: check
check: .create .venv/bin/activate
	. .venv/bin/activate; molecule converge -s $(shell cat .create)
	. .venv/bin/activate; molecule verify -s $(shell cat .create)

.PHONY: login
login: .create .venv/bin/activate
	. .venv/bin/activate; molecule login -s $(shell cat .create) --host $(AFSBOTCFG_MOLECULE_HOST)

ifeq ($(AFSBOTCFG_MOLECULE_SCENARIO), master-with-vault)
test: .vault-afsbotcfg
.create: .vault-afsbotcfg
endif

.PHONY: play
play: collections .vault-afsbotcfg
	.venv/bin/ansible-playbook \
	  --inventory=inventory/openafs/hosts.ini \
	  --vault-password-file=.vault-afsbotcfg \
	  openafs_buildbot.yaml

.PHONY: clean
clean:
	$(MAKE) -C src clean
	if test -f .create; then \
	  . .venv/bin/activate; \
	  molecule destroy -s $(shell cat .create); \
	  rm .create; \
	fi
	rm -f $(AFSBOTCFG_MOLECULE_YML)

.PHONY: reallyclean distclean
reallyclean distclean: clean
	$(MAKE) -C src distclean
	rm -f molecule.json molecule-driver-requirements.txt .vault*
	rm -rf .config .venv collections
