import os


def write_pid():
    """
    Write the buildbot master PID to a file when $BUILDBOT_PIDFILE is defined.

    Unfortunately, the twistd.pid file created by the buildbot process is not
    placed into a run directory, so will be stale after a reboot. So as a
    workaround, we create this extra pid file when the master.cfg is loaded.

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
