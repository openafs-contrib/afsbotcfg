.PHONY: help
help:
	@echo "Usage: make <target>"
	@echo ""
	@echo "Setup targets:"
	@echo "  setup              to setup the virtualenv and generate files"
	@echo "  build              to build the afsbotcfg Python package"
	@echo ""
	@echo "Run targets:"
	@echo "  buildbot           to run the playbook to create/update the buildbot"
	@echo ""
	@echo "Test targets:"
	@echo "  lint               to run yaml and ansible lint checks"
	@echo "  test               to run molecule test"
	@echo "  check              to run molecule create, converge, verify"
	@echo "  login              to run molecule login"
	@echo "  destroy            to run molecule destroy"
	@echo ""
	@echo "Cleanup targets:"
	@echo "  clean              to destroy the molecule instance and remove generated files"
	@echo "  reallyclean        to remove all non-project files"
	@echo ""
	@echo "Environment:"
	@echo "  AFSBOTCFG_PYTHON                python interpreter path (default: python)"
	@echo "  AFSBOTCFG_MOLECULE_JSON         molecule driver config (default: molecule.json)"
	@echo "  AFSBOTCFG_MOLECULE_SCENARIO     make check/test molecule scenario (default: master-with-vault)"
	@echo "  AFSBOTCFG_MOLECULE_HOST         make login host (default: afsbotcfg-master)"
	@echo "  NO_COLOR                        disable Makefile color output"
	@echo ""

#--------------------------------------------------------------------------------------------------------
# Definitions
#

# Environment
AFSBOTCFG_PYTHON ?= python
AFSBOTCFG_MOLECULE_JSON ?= molecule.json
AFSBOTCFG_MOLECULE_SCENARIO ?= master-with-vault
AFSBOTCFG_MOLECULE_HOST ?= afsbotcfg-master

# Generated molecule.yml files.
AFSBOTCFG_MOLECULE_YML = \
  molecule/default/molecule.yml \
  molecule/master-with-vault/molecule.yml \
  molecule/unix-builder/molecule.yml

YAML_FILES=\
  *.yml \
  inventory/openafs/group_vars/openafs_buildbot_masters/master.yml \
  molecule/*/*.yml

LINT_OPTIONS=\
  --exclude=inventory/openafs/group_vars/openafs_buildbot_masters/worker_passwords.yml \
  --exclude=inventory/openafs/group_vars/openafs_buildbot_masters/admin_passwords.yml

PLAYBOOK=afsbotcfg.yml
INVENTORY=inventory/openafs/hosts.ini
VAULT_KEYFILE=.vault-afsbotcfg

ifndef VIRTUAL_ENV
VENV=.venv
PIP=$(VENV)/bin/pip
ACTIVATE=$(VENV)/bin/activate
ACTIVATED=. $(ACTIVATE);
endif

ifndef NO_COLOR
RED=\033[0;31m
GREEN=\033[0;32m
YELLOW=\033[0;33m
START_COLOR=$(GREEN)
END_COLOR=\033[0m
endif

INFO=@printf "$(START_COLOR)==> %s <==$(END_COLOR)\n"

#--------------------------------------------------------------------------------------------------------
# Setup targets
#
.PHONY: setup
setup: $(ACTIVATE) $(AFSBOTCFG_MOLECULE_YML) build

.PHONY: build
build: $(ACTIVATE)
	$(INFO) "Building afsbotcfg python package"
	$(ACTIVATED) $(MAKE) -C src build

#--------------------------------------------------------------------------------------------------------
# Run targets
#
.PHONY: buildbot
buildbot: $(ACTIVATE) $(VAULT_KEYFILE) collections build
	$(INFO) "Running playbook"
	$(ACTIVATED) ansible-playbook --inventory=$(INVENTORY) --vault-password-file=$(VAULT_KEYFILE) $(PLAYBOOK)

#--------------------------------------------------------------------------------------------------------
# Test targets
#
.PHONY: lint
lint: $(ACTIVATE)
	$(INFO) "Running lint checks"
	$(ACTIVATED) $(MAKE) -C src lint
	$(ACTIVATED) yamllint $(YAML_FILES)
	$(ACTIVATED) ansible-lint $(LINT_OPTIONS)

.PHONY: test
test: $(ACTIVATE) lint build molecule/$(AFSBOTCFG_MOLECULE_SCENARIO)/molecule.yml
	$(INFO) "Running molecule test"
	$(ACTIVATED) molecule test -s $(AFSBOTCFG_MOLECULE_SCENARIO)
	@rm -f .create  # Cleanup in case 'make check' was run before 'make test'.

.PHONY: check
check: $(ACTIVATE) .create build
	$(INFO) "Running playbook on molecule instance(s)"
	$(ACTIVATED) molecule converge -s $(shell cat .create)
	$(ACTIVATED) molecule verify -s $(shell cat .create)

.PHONY: login
login: $(ACTIVATE) .create
	$(INFO) "Logging into molecule instance"
	$(ACTIVATED) molecule login -s $(shell cat .create) --host $(AFSBOTCFG_MOLECULE_HOST)

.create: $(ACTIVATE) molecule/$(AFSBOTCFG_MOLECULE_SCENARIO)/molecule.yml
	$(INFO) "Creating molecule instance(s)"
	$(ACTIVATED) molecule create -s $(AFSBOTCFG_MOLECULE_SCENARIO)
	@echo $(AFSBOTCFG_MOLECULE_SCENARIO) >.create

.PHONY: destroy
destroy:   # empty
	$(INFO) "Destroying molecule instance(s)"
	if test -f .create; then \
	  $(ACTIVATED) molecule destroy -s $(shell cat .create); \
	  rm -f .create; \
	fi

# Try to destroy the instance even if the .create file is gone.
.PHONY: force_destroy
force_destroy: $(ACTIVATE) molecule/$(AFSBOTCFG_MOLECULE_SCENARIO)/molecule.yml
	$(INFO) "Destroying molecule instance(s)"
	$(ACTIVATED) molecule destroy -s $(AFSBOTCFG_MOLECULE_SCENARIO)

#------------------------------------------------------------------------------
# Cleanup targets
#
.PHONY: clean
clean: destroy
	$(INFO) "Cleanup files"
	$(MAKE) -C src clean
	rm -f $(AFSBOTCFG_MOLECULE_YML)

.PHONY: reallyclean
reallyclean: clean
	$(INFO) "Cleanup project directory"
	$(MAKE) -C src distclean
	rm -f molecule.json molecule-requirements.txt $(VAULT_KEYFILE)
	rm -rf .config .venv collections .direnv

#------------------------------------------------------------------------------
# Dependencies
#
$(VAULT_KEYFILE):
	$(INFO) "Downloading vault key"
	scp buildbot.openafs.org:$(VAULT_KEYFILE) $(VAULT_KEYFILE)

collections: $(ACTIVATE) requirements.yml
	$(INFO) "Installing required Ansible collections"
	$(ACTIVATED) ansible-galaxy collection install --force -p collections -r requirements.yml
	touch collections

$(ACTIVATE): $(PIP) requirements.txt molecule-requirements.txt
	$(INFO) "Installing python packages"
	$(PIP) install -U -r requirements.txt
	$(PIP) install -U -r molecule-requirements.txt
	touch $(ACTIVATE)
	$(INFO) "Run '. $(ACTIVATE)' to activate the Python virtualenv"

$(PIP): $(VENV)
	$(INFO) "Updating pip"
	$(PIP) install -U pip
	touch $(PIP)

$(VENV):
	$(INFO) "Creating python virtualenv"
	$(AFSBOTCFG_PYTHON) -m venv .venv
	touch $(VENV)

molecule-requirements.txt: $(AFSBOTCFG_MOLECULE_JSON)
	$(INFO) "Generating molecule driver requirements file"
	$(AFSBOTCFG_PYTHON) -c 'import json; print("\n".join(json.load(open("$<"))["requirements"]))' >$@

ifeq ($(AFSBOTCFG_MOLECULE_JSON), molecule.json)
# Conditional to support out of tree molecule.json files.
molecule.json: molecule.json.sample
	$(INFO) "Creating molecule.json file"
	cp molecule.json.sample molecule.json
	$(INFO) "Please run 'make setup' after making any changes to 'molecule.json'"
endif

ifeq ($(AFSBOTCFG_MOLECULE_SCENARIO), master-with-vault)
# Conditional to support testing without the vault key.
test: $(VAULT_KEYFILE)
.create: $(VAULT_KEYFILE)
endif

%.yml : %.yml.j2 $(ACTIVATE) $(AFSBOTCFG_MOLECULE_JSON) render.py
	$(INFO) "Generating molecule file $@"
	$(ACTIVATED) python render.py molecule $(AFSBOTCFG_MOLECULE_JSON) $< $@
