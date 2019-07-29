
# BosServer Setup

A version of the OpenAFS bosserver has been locally built for running the
buildbot master process. This was done so the buildbot would be automatically
restared in the event of a crash.

The bosserver was patched to allow it to run as a regular user. Normally, the
bosserver refuses to start when it is not running as root, since the OpenAFS
processes require root, and fail with unhelpful messages if started as a
regular user.  The patch simply removes that check on startup. The patch
is available in gerrit 13723.

The following shows the steps I used to build and run the bosserver.

## Getting the source.

    $ mkdir ~/src
    $ cd ~/src
    $ wget https://openafs.org/dl/openafs/1.8.3/openafs-1.8.3-src.tar.gz
    $ wget https://openafs.org/dl/openafs/1.8.3/openafs-1.8.3-doc.tar.gz
    $ cd openafs-1.8.3
    $ patch -p1 < $HOME/0001-bozo-add-the-user-option.patch

## Build

    $ mkdir ~/openafs
    $ ./configure --disable-shared --disable-kernel-module --prefix=$HOME/openafs
    $ make install


## Create a random service key

We create a random service key so we can run bos commands with -localauth,
instead of running in -noauth mode and assuming the firewall prevents packets
from reaching the bosserver.  I used a python script to generate this key and
save it in a keytab file.

    $ pip install --user afsutil
    $ export PATH=$HOME/.local/bin:$PATH
    $ afsutil ktcreate --keytab $HOME/openafs/etc/openafs/server/rxkad.keytab --cell localcell --realm LOCALREALM

Use the regular akeyconvert to write the OpenAFS key files.

    $ ~/openafs/bin/akeyconvert
    Wrote 1 keys

# Running the bosserver

The bosserver is started with the site-local '-user' option so it will not
refuse to run as a regular user. (I suppose I could have made that a configure
time option.)

    $ ~/openafs/sbin/bosserver -pidfiles -user

Create the buildbot bnode.

    $ ~/openafs/bin/bos create \
      localhost \
      buildbot simple \
      -cmd "$HOME/buildbot/venv-1.8.1/bin/python3 /home/buildbot/buildbot/venv-1.8.1/bin/buildbot start --nodaemon master" \
      -localauth

Check the status.

    $ ~/openafs/bin/bos status localhost -localauth

# Starting and stopping the buildbot

Now regular bos commands (with -localauth) can be used to stop and
start the buildbot.

    $ ~/openafs/bin/bos status localhost -localauth

    $ ~/openafs/bin/bos restart localhost buildbot -localauth

    $ ~/openafs/bin/bos start localhost buildbot -localauth

    $ ~/openafs/bin/bos stop localhost buildbot -localauth

