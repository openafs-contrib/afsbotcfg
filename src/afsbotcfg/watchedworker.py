# Copyright (c) 2023 Sine Nomine Associates
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


from twisted.internet import defer
from buildbot.worker import AbstractLatentWorker
from buildbot.process.results import CANCELLED
from twisted.python import log
import time


class WatchedWorker(AbstractLatentWorker):
    """
    Worker class that cancels builds if a worker times out.

    To enable for a worker

        c['workers'].append(afsbotcfg.watchedworker.WatchedWorker(name, password,
                            notify_on_missing=workeradmins.get_admin(name)),
                            missing_timeout=900,
                            stall_timeout=300,
                            critical=True)

    missing_timeout is the initial timeout period (in seconds) stall_timeout is
    the subsequent timeout period (in seconds) critical is True | False.  If
    True, the vote will be set to failed if a stall is detected, otherwise the
    vote will be skipped.
    """

    start_missing_on_startup = True

    def __init__(self, name, password, missing_timeout=900,
                 stall_timeout=300, critical=True, **kwargs):
        self.triedstart = 0
        self.timedout = False
        self.missing_email_sent = False
        self.stall_timeout = stall_timeout
        self.critical = critical
        new_kwargs = dict(**kwargs)
        new_kwargs.pop("stall_timeout", None)
        new_kwargs.pop("missing_timeout", None)
        super().__init__(name, password,
                         build_wait_timeout=-1,
                         missing_timeout=missing_timeout,
                         **new_kwargs)

    @defer.inlineCallbacks
    def start_instance(self, build):
        """
        Creating new worker instance
        """
        self.timedout = False
        self.triedstart += 1
        ret = yield True
        return ret

    def stop_instance(self, fast=False):
        """
        Shutting down a worker instance
        """
        self.stopMissingTimer()
        self.timedout = False
        self.triedstart = 0
        return True

    @defer.inlineCallbacks
    def _cancelbuilds(self):
        """
        Mark any active builds on this worker as cancelled
        """
        if not self.timedout and self.triedstart <= 2:
            return

        self.stopMissingTimer()
        self.timedout = False
        self.triedstart = 0
        self.quarantine_timeout = self.quarantine_initial_timeout

        # cancel all buildrequests for this worker because it's not available
        for wfb in self.workerforbuilders.values():
            for build in wfb.builder.building:
                log.err("build cancelled because worker timeout")
                if self.critical:
                    yield build.buildFinished(["build", "failed due to worker timeout"], CANCELLED)
                else:
                    yield build.buildFinished(["build", "skipped due to worker timeout"], CANCELLED)

        for wfb in self.workerforbuilders.values():
            yield wfb.buildFinished()
        yield self.botmaster.maybeStartBuildsForWorker(self.name)

    def buildStarted(self, wfb):
        """
        When a build starts, start the watchdog
        """
        self.startMissingTimer()
        return super().buildStarted(wfb)

    def messageReceivedFromWorker(self):
        """
        Any response from the worker cancels the timeout

        If we want cancel a build when a step within a worker has
        "stopped" or gotten hung up, we can change this around to keep
        the watchdog timer going and just have a flag here that is reset.
        """
        self.stopMissingTimer()
        self.timedout = False
        self.triedstart = 0
        return super().messageReceivedFromWorker()

    def _missing_timer_fired(self):
        """
        Timeout fired .. cancel any active builds for this worker.

        If we want to cancel a build when a step within a builder has
        "stopped" or gotten hung up, we can change this around to watch
        for a flag set in messageReceivedFromWorker
        """
        self.missing_timer = None
        self.timedout = True
        if not self.parent:
            return

        if not self.missing_email_sent:
            last_connection = time.ctime(time.time() - self.missing_timeout)
            self.master.data.updates.workerMissing(
                workerid=self.workerid,
                masterid=self.master.masterid,
                last_connection=last_connection,
                notify=self.notify_on_missing
            )
            self.missing_timeout = self.stall_timeout
            self.email_sent = True

        self._cancelbuilds()
