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


import os
import random
import re
import shlex

from twisted.internet import defer
from buildbot.plugins import steps
from buildbot.plugins import util


run_tests_lock = util.WorkerLock("tap-tests")


class Delay(steps.MasterShellCommand):
    """
    Delay a random time to stagger git traffic.
    """
    def __init__(self, seconds, **kwargs):
        seconds += random.randint(1, 20)
        command = ["sleep", str(seconds)]
        name = "Delay {0} seconds".format(seconds)
        super().__init__(name=name, command=command, **kwargs)


class Regen(steps.ShellCommand):
    """Run the regen script to generate configure."""

    name = 'regen'

    def __init__(self, workdir='build', **kwargs):
        """Create a regen step.

        Args:
            workdir:   Directory to run regen.sh
        """
        super().__init__(**kwargs)
        self.workdir = workdir
        self.command = ['/bin/sh', 'regen.sh']


class Configure(steps.ShellCommand):
    """Run the autoconf configure script."""

    name = "configure"
    haltOnFailure = 1
    flunkOnFailure = 1
    description = "configuring"
    descriptionDone = "configure"
    logfiles = {'config.log': 'config.log'}

    def __init__(self, configure='./configure', options=None, **kwargs):
        """Create the configure step.

        Args:
            configure  The configure script, relative to the workdir.
            options:   The configure options, as a string
        """
        super().__init__(**kwargs)
        self.command = [configure]
        if options is not None:
            self.command.extend(shlex.split(options))

    @defer.inlineCallbacks
    def run(self):
        cmd = yield self.makeRemoteShellCommand()
        yield self.addCompleteLog("command", " ".join(self.command))
        yield self.runCommand(cmd)
        return cmd.results()


class Make(steps.Compile):
    """Run make."""

    name = 'make'

    def __init__(self, make='make', jobs=1, pretty=False, shuffle=False, target='all', **kwargs):
        """Create the make step.

        Args:
            make:   The make program to be run.
            jobs:   The number of make jobs to be run when make is GNU make.
            target: The top level make target.
        """
        super().__init__(**kwargs)
        self.command = [make]
        if jobs > 1:
            self.command.append('-j')
            self.command.append('%d' % jobs)
        if shuffle:
            self.command.append('--shuffle=reverse')
        if pretty:
            self.command.append('V=0')
        else:
            self.command.append('V=1')
        self.command.append(target)


class MakeDocs(steps.ShellSequence):
    """Render DocBook documents.

    The OpenAFS make file does not provide a top level target to render
    the documents, but does provide a makefile for each docbook document.
    """

    name = 'make docs'

    def __init__(self, make='make', warnOnFailure=True, **kwargs):
        """Create a step to render a docbook document.

        Args:
            doc:  The docbook name.
            make: The make program to run.
        """
        super().__init__(**kwargs)
        self.warnOnFailure = warnOnFailure
        self.flunkOnFailure = not warnOnFailure
        self.commands = []
        for doc in ['AdminGuide', 'AdminRef', 'QuickStartUnix', 'UserGuide']:
            workdir = os.path.join('doc/xml', doc)
            self.commands.append(
                util.ShellArg(
                    command=[make, '-C', workdir, 'all'],
                    logname=doc,
                    haltOnFailure=False,
                    warnOnFailure=warnOnFailure,
                    flunkOnFailure=not warnOnFailure))


class TapObserver(util.LogLineObserver):
    """Count passed and failed TAP tests."""

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.running = False
        self.tests = []
        self._current = None
        self.passed = 0
        self.failed = 0

    def outLineReceived(self, line):
        """
        Scan the TAP output for passed and failed test results.
        """
        if line.startswith("Running all tests listed in TESTS."):
            self.running = True
            return
        if line.startswith("test program with runtests -o to see more details."):
            return
        if not self.running:
            return
        m = re.match(r"[a-z]+/[a-z0-9_\-]+$", line)
        if m:
            if self._current:
                self.tests.append(self._current)
            self._current = {
                "name": line,
                "passed": 0,
                "failed": 0,
            }
            return
        m = re.match(r"ok \d+", line)
        if m:
            self.passed += 1
            if self._current:
                self._current["passed"] += 1
            return
        m = re.match(r"not ok \d+", line)
        if m:
            self.failed += 1
            if self._current:
                self._current["failed"] += 1
            return
        m = re.match(r"Files=\d+,", line)
        if m:
            if self._current:
                self.tests.append(self._current)
            self._current = None


class RunTests(steps.WarningCountingShellCommand):
    """
    Run the TAP unit tests.
    """

    name = 'run tests'
    workdir = 'build/tests'

    def __init__(self, make='make', warnOnFailure=False, **kwargs):
        """Create the test step.

        Run the make check command in the tests directory. Attach an observer
        instance to count the passed and failed tests.

        A worker lock is used to ensure the tests for different builders do not
        run at the same time on the same worker. This is needed since some of
        the tests run client server programs on fixed ports and so tests are
        not isolated.

        Args:
            make:  The make program to be run.
        """
        super().__init__(**kwargs)
        self.warnOnFailure = warnOnFailure
        self.command = [make, 'check', 'V=1']
        self.tap = TapObserver()
        self.addLogObserver('stdio', self.tap)
        self.locks = [run_tests_lock.access('exclusive')]

    def evaluateCommand(self, cmd):
        """Determine if the test failed or succeeded."""
        if cmd.didFail() or self.tap.failed > 0:
            if self.warnOnFailure:
                return util.WARNINGS
            else:
                return util.FAILURE
        else:
            return util.SUCCESS

    def createSummary(self):
        """Create a summary with number of tests passed and failed."""
        summary = []
        summary.append("Test Summary")
        if self.tap.failed > 0:
            summary.append("FAILED {0} tests".format(self.tap.failed))
        else:
            summary.append("PASSED all tests.")
        summary.append("")
        summary.append("{name:<24} {passed}/{failed}".format(name="test", passed="pass", failed="fail"))
        for test in self.tap.tests:
            summary.append("{name:<24} {passed}/{failed}".format(**test))
        self.addCompleteLog('summary', "\n".join(summary))


class GitStatusObserver(util.LogLineObserver):
    """
    Gather git status output.
    """

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.changed = []

    def outLineReceived(self, line):
        self.changed.append(line)


class GitStatusCheck(steps.WarningCountingShellCommand):
    """
    Run git status to check for untracked changes.

    This step is intended to check for new untracked artifacts.  This can
    happen if a commit adds a new artifact, but the developer missed updating
    the .gitignore file(s).
    """

    workdir = 'build'
    command = ['git', 'status', '--porcelain']

    def __init__(self, prefix='', warnOnFailure=False, **kwargs):
        super().__init__(**kwargs)
        self.name = prefix + 'git status check'
        self.warnOnFailure = warnOnFailure
        self.observer = GitStatusObserver()
        self.addLogObserver('stdio', self.observer)

    def evaluateCommand(self, cmd):
        if self.observer.changed:
            if self.warnOnFailure:
                return util.WARNINGS
            else:
                return util.FAILURE
        else:
            return util.SUCCESS

    def createSummary(self):
        if self.observer.changed:
            changed = "\n".join(self.observer.changed)
            self.addCompleteLog('changed', changed)
