#!/bin/bash

set -e
set -x

# Generate client ssh key pair for test runs.
mkdir -p /root/.ssh
chmod 0700 /root/.ssh
ssh-keygen -t rsa -f /root/.ssh/id_rsa -q -N ""
cp /root/.ssh/id_rsa.pub /root/.ssh/authorized_keys

# Generate host keys and allow root login.
mkdir -p /var/run/sshd
sed -i 's/#PermitRootLogin .*/PermitRootLogin yes/' /etc/ssh/sshd_config
ssh-keygen -A

# Run ssh server
exec /usr/sbin/sshd -D
