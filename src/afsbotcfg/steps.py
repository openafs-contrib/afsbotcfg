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


import shlex
import re
import os

from twisted.internet import defer
from buildbot.plugins import steps
from buildbot.plugins import util


class Regen(steps.ShellCommand):
    """Run the regen script to generate configure."""

    name = 'regen'

    def __init__(self, workdir='build', manpages=False, **kwargs):
        """Create a regen step.

        Args:
            workdir:   Directory to run regen.sh
            manpages:  Also render the manpages if true
        """
        super().__init__(**kwargs)
        self.workdir = workdir
        self.command = ['/bin/sh', 'regen.sh']
        if not manpages:
            self.command.append('-q')


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

    def __init__(self, make='make', jobs=1, pretty=False, target='all', **kwargs):
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

    name = 'render docs'

    def __init__(self, docs, make='make', **kwargs):
        """Create a step to render a docbook document.

        Args:
            doc:  The docbook name.
            make: The make program to run.
        """
        super().__init__(**kwargs)
        self.commands = []
        for doc in docs:
            workdir = os.path.join('doc/xml', doc)
            self.commands.append(util.ShellArg(
                command=[make, '-C', workdir, 'all'],
                logname=doc,
                haltOnFailure=True))


class MakeManPages(steps.ShellSequence):
    """Render the manpages from the POD source."""

    def __init__(self, **kwargs):
        """Create a step to generate the man pages."""
        super().__init__(**kwargs)
        self.name = 'render man pages'
        self.workdir = 'build/doc/man-pages'
        self.commands = [
            util.ShellArg(
                command='/usr/bin/perl merge-pod pod*/*.in',
                logname='merge-pod',
                haltOnFailure=True),
            util.ShellArg(
                command=['./generate-man'],
                logname='generate-man',
                haltOnFailure=True),
        ]


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


class Test(steps.WarningCountingShellCommand):
    """Run the TAP unit tests."""

    name = 'test'
    workdir = 'build/tests'
    warnOnFailure = 1

    def __init__(self, make='make', **kwargs):
        """Create the test step.

        Run the make check command in the tests directory. Attach an
        observer instance to count the passed and failed tests.

        Args:
            make:  The make program to be run.
        """
        super().__init__(**kwargs)
        self.command = [make, 'check', 'V=1']
        self.tap = TapObserver()
        self.addLogObserver('stdio', self.tap)

    def evaluateCommand(self, cmd):
        """Determine if the test failed or succeeded."""
        if cmd.didFail():
            return util.FAILURE
        if self.tap.failed > 0:
            return util.FAILURE
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
        """Create a step to generate the man pages."""
        super().__init__(**kwargs)
        self.changed = []

    def outLineReceived(self, line):
        self.changed.append(line)


class GitStatus(steps.WarningCountingShellCommand):
    """
    Run git status to check for untracked changes.

    This step is intended to check for new untracked artifacts.  This can
    happen if a commit adds a new artifact, but the developer missed updating
    the .gitignore file(s).
    """

    name = 'git status'
    workdir = 'build'
    command = ['git', 'status', '--porcelain']

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.observer = GitStatusObserver()
        self.addLogObserver('stdio', self.observer)

    def evaluateCommand(self, cmd):
        if self.observer.changed:
            return util.FAILURE
        return util.SUCCESS

    def createSummary(self):
        if self.observer.changed:
            changed = "\n".join(self.observer.changed)
            self.addCompleteLog('changed', changed)
