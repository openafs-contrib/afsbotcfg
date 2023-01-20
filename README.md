# OpenAFS Buildbot Configuration

## Introduction

This repo contains the Ansible playbook used by the OpenAFS Buildbot
administrators to deploy and manage the [OpenAFS][1] [Buildbot][2] coordinator.

In order to use this playbook, you will need ssh access to the Buildbot
coordinator and the ansible-vault key.

Local testing is made possible using Ansible Molecule. To use molecule, you
will need to install a virtualization provider, such as Vagrant.

### Playbook

The `openafs_buildbot.yaml` playbook is used to manage the buildbot
configuration.  This playbook imports buildbot roles from the OpenAFS [Buildbot
Collection][4] to install and configure the buildbot.

### Configuration

The buildbot configuration is maintained in yaml files located under the
`inventory` directory.  User and worker passwords are encrypted with
`ansible-vault`.

The buildbot `master.cfg` file is generated by Ansible from the yaml
configuration.

### Customization

Buildbot customization code is maintained in the `src` directory. The playbook
packages these files are packaged as the `afsbotcfg` python package and
installs that package in the Python virtualenv on the buildbot host.

## Setup

A one-time setup is required before running the playbook.

    $ git clone https://github.com/openafs-contrib/afsbotcfg.git
    $ cd afsbotcfg
    $ make setup

## Running the playbook

    $ . .venv/bin/activate
    $ ansible-playbook openafs_buildbot.yaml

## Running tests

Ansible Molecule scenarios are provided to run tests.  By default the setup
assumes you are using Vagrant as a virtualization provider.  If you are using a
different virtualization provider, update the file
`.config/molecule/config.yml` with the required Molecule driver settings for
your environment, and update the molecule.yml platforms section for your
virtual machine templates.

To run a molecule test:

    $ . .venv/bin/activate
    $ molecule test [-s <scenario>]


[1]: https://www.openafs.org/
[2]: https://buildbot.openafs.org/
[4]: https://galaxy.ansible.com/openafs_contrib/buildbot
