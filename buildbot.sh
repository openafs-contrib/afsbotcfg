#!/bin/sh

TOPDIR=$HOME/buildbot
VENV=$TOPDIR/venv-1.8.1
BUILDBOT=$VENV/bin/buildbot
MASTER=$TOPDIR/master
BOS=$HOME/openafs/bin/bos
BOSSERVER=$HOME/openafs/sbin/bosserver
PIDFILES=$HOME/openafs/var/openafs
BOSSERVER_RUNNING=

# Check the pidfile to see if the bosserver
# is already running.
check_bosserver() {
    if [ ! -f $PIDFILES/bosserver.pid ]; then
        BOSSERVER_RUNNING="no"
    else
        pid0=`cat $PIDFILES/bosserver.pid`
        pid1=`pidof bosserver`
        if [ "x$pid0" != "x$pid1" ]; then
            BOSSERVER_RUNNING="no"
        else
            BOSSERVER_RUNNING="yes"
        fi
    fi
}

case "$1" in
    init)
        check_bosserver
        if [ "$BOSSERVER_RUNNING" = "yes" ]; then
            echo "bosserver is already running."
        else
            echo "starting bosserver."
            $BOSSERVER -pidfiles -user
        fi
        ;;
    start)
        $BOS start localhost buildbot -localauth
        ;;
    stop)
        $BOS stop localhost buildbot -localauth
        ;;
    restart)
        $BOS stop localhost buildbot -localauth
        sleep 5
        $BOS start localhost buildbot -localauth
        ;;
    status)
        $BOS status localhost -localauth
        ;;
    checkconfig)
        echo 'checking config'
        $BUILDBOT checkconfig $MASTER
        ;;
    *)
        echo "usage: buildbot.sh init|start|stop|restart|status|checkconfig"
        ;;
esac
