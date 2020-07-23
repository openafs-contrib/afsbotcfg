OpenAFS Buildbot Master Configuration and Playbooks
===================================================

This is the [buildbot master][1] configuration and Ansible playbooks
for [OpenAFS][2].

Buildbot master installation
----------------------------

The following instructions describe how to use `pip` to install the buildbot
master in a Python virtual environment.  With sudo/root access, install Python3
and the development packages for it.

Ensure TCP ports 9989 and 8010 are open. Create a `buildbot` user on the
system.  The remaining steps do not require sudo access and should be run as
the `buildbot` user.

Create a Python virtual environment:

    $ mkdir -p ~/.venv
    $ python3 -m venv ~/.venv/buildbot-<yyyymmdd>

Activate the virtual environment for the installation:

    $ source ~/.venv/buildbot-<yyyymmdd>/bin/activate

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
sample `passwords.ini` file:

    $ python configure.py
    $ make install

Make a link to the makefile in the top level directory:

    $ cd ..
    $ ln -s afsbotcfg/Makefile

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

[1]: https://buildbot.openafs.org/
[2]: https://openafs.org
[3]: https://gerrit.openafs.org/
