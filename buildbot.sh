#!/bin/sh

TOPDIR=/home/buildbot/buildbot
VENV=$TOPDIR/venv-1.8.1
BUILDBOT=$VENV/bin/buildbot
MASTER=$TOPDIR/master
BOS=/home/buildbot/openafs/bin/bos

case "$1" in
    start)
        $BOS start localhost buildbot -localauth
        ;;
    stop)
        $BOS stop localhost buildbot -localauth
        ;;
    restart)
        $BOS restart localhost buildbot -localauth
        ;;
    status)
        $BOS status localhost -localauth
        ;;
    checkconfig)
        echo 'checking config'
        $BUILDBOT checkconfig $MASTER
        ;;
    *)
        echo "usage: buildbot.sh start|stop|restart|status|checkconfig"
        ;;
esac
