
import shlex
import os

from buildbot.plugins import steps
from buildbot.plugins import util


class RegenStep(steps.ShellCommand):
    name = 'regen.sh'
    command = ['/bin/sh', 'regen.sh']

    def __init__(self, workdir='build'):
        super().__init__(workdir=workdir)


class Configure(steps.Configure):
    name = 'configure'
    logfiles = {
        'config.log': 'config.log',
    }

    def __init__(self, configure=None, sourcedir='.'):
        super().__init__()
        command = os.path.join(sourcedir, 'configure')
        if configure:
            options = shlex.split(configure)
        else:
            options = []
        self.command = [command] + options


class Make(steps.Compile):
    def __init__(self, jobs=1, target='all'):
        super().__init__()
        self.command = ['make']
        try:
            jobs = int(jobs)
        except ValueError:
            jobs = 1
        if jobs > 1:
            self.command.append('-j')
            self.command.append('%d' % jobs)
        self.command.append(target)


class RunTestsStep(steps.Compile):
    name = 'test'
    warnOnFailure = 1
    description = ['testing']
    descriptionDone = ['test']
    command = ['make', 'check']


class BuildTests(steps.Compile):
    name = 'build tests'
    command = 'cd tests && make all'


class TapObserver(util.LogLineObserver):
    passed = 0
    failed = 0

    def outLineReceived(self, line):
        if line.startswith('ok'):
            self.passed += 1
        if line.startswith('not ok'):
            self.failed += 1


class VerboseRunTestsStep(steps.ShellCommand):
    name = 'run tests'
    command = 'cd tests && cat TESTS | while read t; do echo "# Test $t"; '\
              'MAKECHECK=1 ./libwrap ../lib ./runtests -o $t; done'

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.tap = TapObserver()
        self.addLogObserver('stdio', self.tap)

    def evaluateCommand(self, cmd):
        if cmd.didFail():
            return util.FAILURE
        if self.tap.failed != 0:
            return util.FAILURE
        return util.SUCCESS

    def createSummary(self, log):
        summary = 'passed %d\nfailed %d\n' % (self.tap.passed, self.tap.failed)
        self.addCompleteLog('summary', summary)


class BuildDoc(steps.Compile):
    def __init__(self, doc, *args, **kwargs):
        kwargs['command'] = ['make']
        kwargs['workdir'] = 'build/doc/xml/%s' % doc
        kwargs['name'] = 'generate %s' % doc
        super().__init__(*args, **kwargs)
