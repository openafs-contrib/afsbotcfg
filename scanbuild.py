#
# This is a custom build step to run the clang analyzer with the scan-build
# front-end.  The output directory should be accessible from http.  This build
# step follows the stdout of scan-build to get the bug count and the path of
# the generated reports, which are timestamped. Show the bug count and the url
# to the reports on the buildbot waterfall.
#

import re
from urlparse import urljoin
from buildbot.steps.shell import ShellCommand
from buildbot.process.buildstep import LogLineObserver
from buildbot.status.results import SUCCESS, FAILURE

class ScanBuildObserver(LogLineObserver):
    _bugs_re = re.compile(r'^scan-build: (\d+) bugs? found\.$')
    _report_dir_re = re.compile(r"^scan-build: Emitting reports for this run to '(.*)'\.")

    def __init__(self, step, **kwargs):
        self.step = step
        LogLineObserver.__init__(self, **kwargs)

    def outLineReceived(self, line):
        m = self._bugs_re.search(line)
        if m:
            self.step.bugs = int(m.group(1))
            return
        m = self._report_dir_re.search(line)
        if m:
            self.step.report_dir = m.group(1)
            return

class ScanBuild(ShellCommand):
    name = "scan-build"
    haltOnFailure = 1
    flunkOnFailure = 1
    description = ["scanning"]
    descriptionDone = ["scanned"]

    def __init__(self, output=None, make=None, docroot=None, baseurl=None, **kwargs):
        ShellCommand.__init__(self, **kwargs) # must precede addLogObserver()
        self.bugs = None
        self.report_dir = None
        self.docroot = docroot
        self.baseurl = baseurl
        self.observer = ScanBuildObserver(self)
        self.addLogObserver('stdio', self.observer)
        command = ["scan-build", "-v"]
        if output:
            command.append(["-o", output])
        if make:
            command.append(make)
        else:
            command.append(["make", "all"])
        self.setCommand(command)

    def addReportURL(self):
        if self.report_dir and self.docroot and self.baseurl:
            path = self.report_dir
            if path.startswith(self.docroot):
                path = path.replace(self.docroot, "")
            url = urljoin(self.baseurl, path)
            self.addURL("report", url)

    def finished(self, result):
        if result == SUCCESS:
            self.addReportURL()
        ShellCommand.finished(self, result)

    def describe(self, done=False):
        desc = ShellCommand.describe(self, done)[:]
        if done:
            if self.bugs is not None:
                desc.append("%d bugs found" % self.bugs)
        return desc
