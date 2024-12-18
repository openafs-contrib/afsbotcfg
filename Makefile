.PHONY: help
help:
	@echo "Usage: make <target>"
	@echo ""
	@echo "Setup targets:"
	@echo "  setup              to setup the virtualenv and generate files"
	@echo "  build              to build the afsbotcfg Python package"
	@echo ""
	@echo "Run targets:"
	@echo "  deploy             to run the playbook to create/update the buildbot server"
	@echo "  ping               to check connectivity to the buildbot server"
	@echo "  getlog             to download the buildbot server log"
	@echo ""
	@echo "Cleanup targets:"
	@echo "  clean              to remove generated files"
	@echo "  reallyclean        to remove all non-project files"
	@echo ""
	@echo "Environment:"
	@echo "  AFSBOTCFG_PYTHON                python interpreter path (default: python)"
	@echo "  AFSBOTCFG_LOGDIR                ansible play log directory (default: logs)"
	@echo "  NO_COLOR                        disable Makefile color output"
	@echo ""

#--------------------------------------------------------------------------------------------------------
# Definitions
#

# Environment
AFSBOTCFG_HOST ?= buildbot.openafs.org
AFSBOTCFG_PYTHON ?= python
AFSBOTCFG_LOGDIR ?= logs

YAML_FILES=\
  *.yml \
  inventory/group_vars/openafs_buildbot_masters/master.yml

LINT_OPTIONS=\
  --exclude=inventory/group_vars/openafs_buildbot_masters/worker_passwords.yml \
  --exclude=inventory/group_vars/openafs_buildbot_masters/admin_passwords.yml

PLAYBOOK=afsbotcfg.yml
INVENTORY=inventory/hosts.ini
VAULT_KEYFILE=.vault-afsbotcfg

PACKAGES=.packages
ifdef VIRTUAL_ENV
PIP=$(VIRTUAL_ENV)/bin/pip
ACTIVATED=ANSIBLE_COLLECTIONS_PATH=$(CURDIR)/collections
else
VENV=.venv
PIP=$(VENV)/bin/pip
ACTIVATE=$(VENV)/bin/activate
ACTIVATED=. $(ACTIVATE); ANSIBLE_COLLECTIONS_PATH=$(CURDIR)/collections
endif

ifndef NO_COLOR
RED=\033[0;31m
GREEN=\033[0;32m
YELLOW=\033[0;33m
START_COLOR=$(GREEN)
END_COLOR=\033[0m
endif

INFO=@printf "$(START_COLOR)==> %s <==$(END_COLOR)\n"

ifdef AFSBOTCFG_LOGDIR
LOGFILE=$(AFSBOTCFG_LOGDIR)/buildbot-$(shell date "+%Y%m%dT%H%M").log
LOG=ANSIBLE_LOG_PATH="$(LOGFILE)"
LOGINFO=$(INFO) "Wrote $(LOGFILE)"
endif

#--------------------------------------------------------------------------------------------------------
# Setup targets
#
.PHONY: setup
setup: $(PACKAGES) build collections

.PHONY: build
build: $(PACKAGES)
	$(INFO) "Building afsbotcfg python package"
	$(ACTIVATED) $(MAKE) --no-print-directory -C src lint build

#--------------------------------------------------------------------------------------------------------
# Run targets
#
.PHONY: ping
ping: $(PACKAGES) $(VAULT_KEYFILE)
	$(INFO) "Pinging buildbot"
	$(ACTIVATED) ansible --inventory=$(INVENTORY) --vault-password-file=$(VAULT_KEYFILE) all -m ping

.PHONY: deploy buildbot
deploy buildbot: $(PACKAGES) $(VAULT_KEYFILE) collections build $(AFSBOTCFG_LOGDIR)
	$(INFO) "Running buildbot playbook"
	$(ACTIVATED) $(LOG) ansible-playbook --inventory=$(INVENTORY) --vault-password-file=$(VAULT_KEYFILE) $(PLAYBOOK)
	$(LOGINFO)

.PHONY: getlog
getlog: $(AFSBOTCFG_LOGDIR)
	$(INFO) "Downloading buildbot log"
	scp $(AFSBOTCFG_HOST):master/openafs/twistd.log $(AFSBOTCFG_LOGDIR)/twistd-$(shell date "+%Y%m%dT%H%M").log

#------------------------------------------------------------------------------
# Cleanup targets
#
.PHONY: clean
clean:
	$(INFO) "Cleanup files"
	$(MAKE) -C src clean
	rm logs/*

.PHONY: reallyclean
reallyclean: clean
	$(INFO) "Cleanup project directory"
	$(MAKE) -C src distclean
	rm -rf .config .venv collections .direnv

#------------------------------------------------------------------------------
# Dependencies
#
$(AFSBOTCFG_LOGDIR):
	mkdir -p $(AFSBOTCFG_LOGDIR)

$(VAULT_KEYFILE):
	$(INFO) "Downloading vault key"
	scp $(AFSBOTCFG_HOST):$(VAULT_KEYFILE) $(VAULT_KEYFILE)

collections: $(PACKAGES) requirements.yml
	$(INFO) "Installing required Ansible collections"
	$(ACTIVATED) ansible-galaxy collection install --force -p collections -r requirements.yml
	touch collections

$(PACKAGES): $(PIP) requirements.txt
	$(INFO) "Installing python packages"
	$(PIP) install -U -r requirements.txt
	touch $(PACKAGES)

$(PIP): $(VENV)
	$(INFO) "Updating pip"
	$(PIP) install -U pip wheel
	touch $(PIP)

$(VENV):
	$(INFO) "Creating python virtualenv"
	$(AFSBOTCFG_PYTHON) -m venv .venv
	touch $(VENV)
