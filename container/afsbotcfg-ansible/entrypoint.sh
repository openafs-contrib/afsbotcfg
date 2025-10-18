#!/bin/bash

set -e

usage() {
    echo "usage: podman run -ti --rm"
    echo "         -v AFSBOTCFG_DIRECTORY:/app/afsbotcfg[:ro]"
    echo "         -v SSH_CONFIG_DIRECTORY:/root/.ssh:ro"
    echo "         -v SSH_AUTH_SOCK:/root/ssh-agent.socket"
    echo "         --secret afsbotcfg-vault,type=mount,target=/root/vault"
    echo "         IMAGE_NAME"
    echo "         CMDLINE"
    echo ""
    echo "where:"
    echo "AFSBOTCFG_DIRECTORY    path to the afsbotcfg playbook and files"
    echo "SSH_CONFIG_DIRECTORY   path to the ssh config files, keys, and known hosts"
    echo "SSH_AUTH_SOCK          path of the ssh-agent socket on the host"
    echo "IMAGE_NAME             image name"
    echo "CMD                    Ansible command line to execute."
    echo ""
    echo "Supported commands are:"
    echo "  ansible"
    echo "  ansible-lint"
    echo "  ansible-playbook"
    echo "  ansible-vault"
}

if [ ! -d /app/afsbotcfg ]; then
    echo "Missing /app/afsbotcfg" >&2
    exit 1
fi

cd afsbotcfg

cmd="${1:-help}"
shift
case "$cmd" in
ansible)
    set -x
    exec ansible "$@"
    ;;
ansible-lint)
    set -x
    exec ansible-lint "$@"
    ;;
ansible-playbook)
    set -x
    exec ansible-playbook "$@"
    ;;
ansible-vault)
    set -x
    exec ansible-vault "$@"
    ;;
help)
    usage
    ;;
# shell)
#    exec /bin/bash
#    ;;
*)
    usage
    exit 1
    ;;
esac
