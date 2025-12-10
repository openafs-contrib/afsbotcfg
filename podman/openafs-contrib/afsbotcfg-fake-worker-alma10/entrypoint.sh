#!/bin/bash

set -x

worker=$1
password=$2
if [ "x$worker" == "x" ]; then
    echo "worker name is required"
    exit 1
fi
if [ "x$password" == "x" ]; then
    echo "password is required"
    exit 1
fi

/usr/local/bin/buildbot-worker create-worker /app localhost:9989 "${worker}" "${password}"
/usr/local/bin/buildbot-worker start --nodaemon /app/
