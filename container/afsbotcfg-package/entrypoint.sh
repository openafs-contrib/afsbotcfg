#!/bin/bash

set -e

usage() {
    echo "usage: podman run -ti --rm -v AFSBOTCFG_SRC_DIRECTORY:/app/src IMAGE CMD"
    echo ""
    echo "where CMD is one of:"
    echo "  build  build afsbotcfg package"
    echo "  lint   run lint checks"
    echo "  shell  interactive shell"
    echo "  help   print help"
}

cmd="$1"
shift
case "$cmd" in
build)
    cd /app/src
    pyflakes afsbotcfg/*.py
    flake8 afsbotcfg/*.py
    python3 setup.py sdist
    ;;
lint)
    cd /app/src
    pyflakes afsbotcfg/*.py
    flake8 afsbotcfg/*.py
    ;;
shell)
    /bin/bash
    ;;
help)
    usage
    ;;
*)
    usage
    exit 1
    ;;
esac
