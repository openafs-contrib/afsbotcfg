
from buildbot.plugins import steps
from buildbot.plugins import util


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
