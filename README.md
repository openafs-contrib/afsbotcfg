afsbotcfg - OpenAFS buildbot master configuration
=================================================

This is the [buildbot master][1] configuration for [OpenAFS][2]. This
configuration is compatible with buildbot version 1.3.

**Note: We are transitioning from the obsolete buildbot version 0.8 to the
current supported version 1.3. This will allow new buildbot 1.x workers to
participate as builders as well as existing 0.8 version build slaves.  The old
master will continue to run during this transition period. New workers should
be configured to use port 9986 to connect to the new master.**

Buildbot master setup
---------------------

The following instructions describe how to use `pip` to install the buildbot
master in a Python virtual environment.  First, with sudo access, install
Python3 and the development packages for it on the system to host the buildbot
master. Ensure TCP ports 9986 and 8011 are open. (These are the ports used
during the transition.) Create a `buildbot` user on the system.  The remaining
steps to not require sudo access and should be run as the `buildbot` user.

Create a Python virtual environment:

    mkdir buildbot13
    cd buildbot13
    python3 -m venv venv

Install buildbot and it's dependencies:

    source venv/bin/activate
    pip install --upgrade pip
    pip install 'buildbot[bundle]'
    deactivate

Create the buildbot master instance:

    venv/bin/buildbot create-master master

Download the buildbot master configuration:

    git clone https://github.com/openafs-contrib/afsbotcfg.git
    cd afsbotcfg
    git checkout buildbot-13x
    cd ..
    ln -s afsbotcfg/Makefile

Create a symlink to the master.cfg file in the master's base directory.

    cd master
    ln -s ../afsbotcfg/master.cfg
    cd ..

Create the `passwords` file in the master's base directory. The `passwords`
file should contain one worker name and password per line, separated by a space
character. This file not stored in git.

    cd master
    echo "example-worker pass" >>passwords
    cd ..

Check the buildbot master configuration with the command:

    make check

The buildbot master can be started and stopped with:

    make start

Check the log file `master/twisted.log` to verify the buildbot master started.
The master can be stopped with the command:

    make stop

Adding buildbot workers
-----------------------

todo

Changing the master configuration
---------------------------------

todo


[1]: http://buildbot.openafs.org:8011
[2]: https://openafs.org
