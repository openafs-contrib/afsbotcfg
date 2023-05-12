# Copyright (c) 2023 Sine Nomine Associates
#
# This file copies/extends portions of Buildbot forcescheduler.
# This software is available at no charge under the terms
# of the GNU General Public License version 2 (GPLv2) as
# available from the OSI(Open Software Initiative) website.

# THE SOFTWARE IS PROVIDED 'AS IS' AND THE AUTHOR DISCLAIMS ALL WARRANTIES
# WITH REGARD TO THIS SOFTWARE INCLUDING ALL IMPLIED WARRANTIES OF
# MERCHANTABILITY AND FITNESS. IN NO EVENT SHALL THE AUTHOR BE LIABLE FOR
# ANY SPECIAL, DIRECT, INDIRECT, OR CONSEQUENTIAL DAMAGES OR ANY DAMAGES
# WHATSOEVER RESULTING FROM LOSS OF USE, DATA OR PROFITS, WHETHER IN AN
# ACTION OF CONTRACT, NEGLIGENCE OR OTHER TORTIOUS ACTION, ARISING OUT OF
# OR IN CONNECTION WITH THE USE OR PERFORMANCE OF THIS SOFTWARE.

from twisted.internet import defer
from buildbot.worker import AbstractLatentWorker
from buildbot.process.results import CANCELLED
from twisted.python import log
import time


class WatchedWorker(AbstractLatentWorker):
    """
        Worker class that cancels builds if a worker times out

        To enable for a worker
            c['workers'].append(afsbotcfg.watchedworker.WatchedWorker(name, password,
                              notify_on_missing=workeradmins.get_admin(name)),
                              missing_timeout=900,
                              stall_timeout=300,
                              stall_fail=False)

        missing_timeout is the initial timeout period (in seconds)
        stall_timeout is the subsequent timeout period (in seconds)
        stall_fail is True | False.  If True, the vote will be set
        to failed, otherwise the stall will be reported as skipped

    """

    start_missing_on_startup = True

    def __init__(self, name, password, missing_timeout=900,
                 stall_timeout=300, stall_fail=False, **kwargs):
        self.triedstart = 0
        self.timedout = False
        self.missing_email_sent = False
        self.stall_timeout = stall_timeout
        self.stall_fail = stall_fail
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
                if self.stall_fail is True:
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
