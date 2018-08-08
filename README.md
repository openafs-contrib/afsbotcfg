OpenAFS Buildbot Master Configuration
=====================================

This is the [buildbot master][1] configuration for [OpenAFS][2]. This
configuration is compatible with buildbot version 1.3.

**Note: We are transitioning from the deprecated buildbot version 0.8 to the
currently supported version 1.x. This will allow modern buildbot workers (as
well as old, existing buildbot slaves) to connect to the buildbot master.  The
old master instance will continue to run during this transition period. New
workers should be configured to use port 9986 to connect to the new master.**

Buildbot master installation
----------------------------

The following instructions describe how to use `pip` to install the buildbot
master in a Python virtual environment.  With sudo/root access, install Python3
and the development packages for it.

Ensure TCP ports 9986 and 8011 are open. (These are the ports used during the
transition.) Create a `buildbot` user on the system.  The remaining steps to
not require sudo access and should be run as the `buildbot` user.

Optionally create a project level directory, for example:

    $ mkdir openafs-buildbot
    $ cd openafs-buildbot

Create a Python virtual environment:

    $ python3 -m venv venv

Activate the virtual environment for the installation:

    $ source venv/bin/activate

Install buildbot and it's dependencies:

    $ pip install --upgrade pip
    $ pip install 'buildbot[bundle]'

Create the buildbot master instance:

    $ buildbot create-master master

The virtual environment can now be deactivated:

    $ deactivate

Master configuration
--------------------

Download the buildbot master configuration:

    $ git clone https://github.com/openafs-contrib/afsbotcfg.git
    $ cd afsbotcfg

Create the `Makefile` and deploy the buildbot `master.cfg` and
sample `settings.ini` file:

    $ python configure.py
    $ make install

Make a link to the makefile in the top level directory:

    $ cd ..
    $ ln -s afsbotcfg/Makefile

Master settings
---------------

Edit the `settings.ini` file in the `master` directory. This file stores
information we do not track with git, such as the buildbot worker passwords.
The `settings.ini` file is an INI-style file with the following sections:

* local - settings specific to the local environment
* admins - the list of user emails and passwords for authenticated access
* workers - the list of worker names and passwords

Example:

    $ cat master/settings.ini
    [local]
    buildbotURL = http://buildbot.openafs.org:8011/
    
    [admins]
    tycobb@yoyodyne.com = password
    
    [workers]
    example-worker1 = secret1
    example-worker2 = secret2

Gerrit account
--------------

The buildbot master needs an account on the [OpenAFS Gerrit][3] to listen for
Gerrit events and to report verified changes on successful builds.  The name of
the account is `buildbot`. Place the ssh keys for the buildbot's Gerrit account
in the `.ssh` directory under the home directory of the local account running
the buildbot master. The key file name should match the ones defined in the
`master.cfg` file.

Starting the master
-------------------

Check the buildbot master configuration with the command:

    $ make check

Start the buildbot master with the command:

    $ make start

Stop the buildbot master with the command:

    $ make stop

[1]: http://buildbot.openafs.org:8011
[2]: https://openafs.org
[3]: https://gerrit.openafs.org/
