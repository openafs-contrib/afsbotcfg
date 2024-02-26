# Copyright (c) 2019 Sine Nomine Associates
#
# This program is free software; you can redistribute it and/or
# modify it under the terms of the GNU General Public License
# as published by the Free Software Foundation; either version 2
# of the License, or (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.


"""Functions to help manage the buildbot master process."""


import os


def write_pid():
    """Write the buildbot master PID to a file when $BUILDBOT_PIDFILE is defined.

    Unfortunately the twistd.pid file created by the buildbot process is not
    placed into a run directory, so will be stale after a reboot. As a
    workaround, create this extra pid file when the master.cfg is loaded.

    The BUILDBOT_PIDFILE environment variable *must not* be set when running
    the `buildbot checkconfig` command, but *must be* set when running the
    `buildbot start` command.

    Example:

        $ buildbot checkconfig master/example_project
        $ BUILDBOT_PIDFILE=/var/run/buildbot.pid buildbot start master/example_project

    """
    filename = os.environ.get('BUILDBOT_PIDFILE', None)
    if filename:
        with open(filename, 'w') as f:
            f.write('%d\n' % os.getpid())
