{% raw %}

from twisted.internet import defer
from buildbot.worker import AbstractLatentWorker
from buildbot.data import resultspec
from buildbot.process.results import EXCEPTION
from buildbot.process.results import CANCELLED
import time

class WatchedWorker(AbstractLatentWorker):
    """
        Worker class that cancels builds if a worker times out
    """
    start_missing_on_startup = True
    def __init__(self, name, password, missing_timeout=120, **kwargs):
        self.triedstart = 0
        self.timedout = False
        super().__init__(name, password,
                         build_wait_timeout=-1,
                         missing_timeout=missing_timeout,
                         **kwargs)

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
            Mark any active builds on this worker as build exceptions
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
                yield build.buildException("cancelled because worker timeout")

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
            a flag set in messageReceivedFromWorker
        """
        self.missing_timer = None
        self.timedout = True
        if not self.parent:
            return
        self._cancelbuilds()

{% endraw %}