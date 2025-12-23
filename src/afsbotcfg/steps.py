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

from twisted.python import log
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
            self.command.append('--output-sync=target')
        if shuffle:
            self.command.append('--shuffle=reverse')

        self.command.append(target)

        if pretty:
            self.command.append('V=0')
        else:
            self.command.append('V=1')

        if target.startswith('install'):
            destdir = util.Interpolate('DESTDIR=%(prop:builddir)s/build/packages')
            self.command.append(destdir)


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


class TapState:
    def __init__(self, observer, *args, **kwargs):
        self.observer = observer

    def next(self, name):
        return self.observer.getNextState(name)

    def start(self, line):
        pass

    def consume(self, line):
        return None

    def end(self):
        pass


class TapInitialState(TapState):
    def consume(self, line):
        if re.match(r"Running all tests listed in TESTS.", line):
            return self.next("starting")
        return None


class TapStartingState(TapState):
    def consume(self, line):
        if re.match(r"([a-z]+/[a-z0-9_\-]+)$", line):
            return self.next("suite")

        if re.match(r"All tests successful.", line):
            return self.next("final")

        if re.match(r"All tests successful, (\d+) tests skipped.", line):
            return self.next("final")

        if re.match(r"Failed Set", line):
            return self.next("final")

        return None


class TapSuiteState(TapState):
    def start(self, line):
        self.name = line.rstrip()
        self.error = False
        self.passed = 0
        self.failed = 0

    def end(self):
        if self.error:
            self.observer.setError(self.name)
        else:
            self.observer.setResults(self.name, self.passed, self.failed)

    def consume(self, line):
        # Skip blank lines.
        if re.match(r"#", line) or re.match(r"\s*$", line):
            return None

        # Check tests for pass and fail for each test case.
        if re.match(r"ok (\d+)", line):
            self.passed += 1
            return None

        if re.match(r"not ok (\d+)", line):
            self.failed += 1
            return None

        # Checks for end of the test suite.
        if re.match(r"ok$", line):
            return self.next("starting")

        if re.match(r"FAILED ", line):
            return self.next("starting")

        if re.match(r"MISSED ", line):
            self.error = True
            return self.next("starting")

        if re.match(r"skipped$", line):
            return self.next("starting")

        if re.match(r"skipped \(.*\)$", line):
            return self.next("starting")

        # Just in case the end of the test suite was not found, check for the
        # next suite and the end of the tests.
        if re.match(r"[a-z]+/[a-z0-9_\-]+$", line):
            return self.next("suite")

        if re.match(r"All tests successful.", line):
            return self.next("final")

        if re.match(r"All tests successful, (\d+) tests skipped.", line):
            return self.next("final")

        if re.match(r"Failed Set", line):
            return self.next("final")

        return None


class TapFinalState(TapState):
    pass


class TapObserver(util.LogLineObserver):
    """Count passed and failed TAP tests."""
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.states = {
            "initial": TapInitialState(self),
            "starting": TapStartingState(self),
            "suite": TapSuiteState(self),
            "final": TapFinalState(self),
        }
        self.state = self.states["initial"]
        self.tests = {}
        self.error = False
        self.passed = 0
        self.failed = 0

    def getNextState(self, name):
        return self.states[name]

    def setResults(self, name, passed, failed):
        self.passed += passed
        self.failed += failed
        self.tests[name] = (passed, failed)

    def setError(self, name):
        self.error = True
        self.tests[name] = None

    def outLineReceived(self, line):
        try:
            next_state = self.state.consume(line)
            if next_state:
                self.state.end()
                next_state.start(line)
                self.state = next_state
        except Exception as e:
            log.msg("TapObserver exception: " + str(e))

    def getSummary(self):
        summary = []
        if self.error:
            summary.append("ERROR")
            summary.append("Unable to run tests.")
        else:
            if self.failed:
                summary.append("FAILED")
            else:
                summary.append("PASSED")
            summary.append("passed {0:5}".format(self.passed))
            summary.append("failed {0:5}".format(self.failed))
        return "\n".join(summary)


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
        if cmd.didFail() or self.tap.failed > 0 or self.tap.error:
            if self.warnOnFailure:
                return util.WARNINGS
            else:
                return util.FAILURE
        else:
            return util.SUCCESS

    def createSummary(self):
        """Create a summary with number of tests passed and failed."""
        self.addCompleteLog('summary', self.tap.getSummary())


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


class LwpObserver(util.LogLineObserver):

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.lwp_files = []

    def outLineReceived(self, line):
        """
        Parse the nm -A output to get the LWP threaded executable names.

        example line:
            packages/usr/local/sbin/volinfo:00000000004484f6 T LWP_CreateProcess

        saved as:
            usr/local/sbin/volinfo
        """
        if 'LWP_CreateProcess' in line:
            file = line.split(':')[0].replace('packages/', '')
            self.lwp_files.append(file)


class LwpCheck(steps.WarningCountingShellCommand):
    """
    Warn if LWP threaded binaries are found in the install tree.

    This check should be run after 'make install', which non-stripped
    binaries. The DESTDIR must be 'packages', which is set in the Make
    step.
    """

    name = 'LWP check'
    workdir = 'build'
    command = (
        r"find packages -type f -exec file {} \;"
        " | grep ': ELF'"
        " | sed 's/: ELF.*//'"
        " | xargs nm -A"
        " | grep LWP_CreateProcess"
    )

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

        self.haltOnFailure = False
        self.flunkOnWarnings = False
        self.flunkOnFailure = False
        self.warnOnWarnings = False
        self.warnOnFailure = False

        self.observer = LwpObserver()
        self.addLogObserver('stdio', self.observer)

    def createSummary(self):
        lwp_files = self.observer.lwp_files
        summary = "Found {0} LWP threaded binaries.\n".format(len(lwp_files))
        summary += "\n".join(lwp_files)
        self.addCompleteLog('lwp', summary)

    def evaluateCommand(self, cmd):
        if self.observer.lwp_files:
            return util.WARNINGS
        return util.SUCCESS
