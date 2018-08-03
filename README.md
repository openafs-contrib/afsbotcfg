OpenAFS Buildbot Master Configuration
=====================================

This is the [buildbot master][1] configuration for [OpenAFS][2]. This
configuration is compatible with buildbot version 1.3.

**Note: We are transitioning from the deprecated buildbot version 0.8 to the
currently supported version 1.x. This will allow modern buildbot workers (as
well as old, existing buildbot slaves) to connect to the buildbot master.  The
old master instance will continue to run during this transition period. New
workers should be configured to use port 9986 to connect to the new master.**

Buildbot master setup
---------------------

The following instructions describe how to use `pip` to install the buildbot
master in a Python virtual environment.  With sudo/root access, install Python3
and the development packages for it on the system to host the buildbot master.
Ensure TCP ports 9986 and 8011 are open. (These are the ports used during the
transition.) Create a `buildbot` user on the system.  The remaining steps to
not require sudo access and should be run as the `buildbot` user.

Create a Python virtual environment:

    mkdir buildbot13
    cd buildbot13
    python3 -m venv venv
    source venv/bin/activate

Install buildbot and it's dependencies:

    pip install --upgrade pip
    pip install 'buildbot[bundle]'

Create the buildbot master instance:

    buildbot create-master master
    deactivate

Configuration setup
-------------------

Download the buildbot master configuration:

    git clone https://github.com/openafs-contrib/afsbotcfg.git
    cd afsbotcfg
    git checkout buildbot-13x
    cd ..

Create a symlink to the `Makefile` as a convenience to start and stop the
buildbot master.

    ln -s afsbotcfg/Makefile

Create a symlink to the `master.cfg` file in the master's base directory.

    cd master
    ln -s ../afsbotcfg/master.cfg
    cd ..

Create a file called `settings.ini` in the master's base directory to store
info which is not tracked with git. The `settings.ini` file has the following
sections:

* local - settings specific to the local environment
* admins - the list of user emails and passwords for authenticated access
* workers - the list of worker names and passwords

Example:

    cat master/settings.ini
    [local]
    buildbotURL = http://buildbot.openafs.org:8011/
    
    [admins]
    tycobb@yoyodyne.com = password
    
    [workers]
    example-worker1 = secret1
    example-worker2 = secret2

Starting the master
-------------------

Check the buildbot master configuration with the command:

    make check

Start the buildbot master with the command:

    make start

Stop the buildbot master with the command:

    make stop

[1]: http://buildbot.openafs.org:8011
[2]: https://openafs.org
