
from buildbot.plugins import steps
from buildbot.plugins import util

import afsbotcfg.steps


class Checkout(util.BuildFactory):
    """
    Base class to checkout source code from a git repo.
    """

    gerrit_lock = util.MasterLock("gerrit")
    gerrit_lock_count = 1  # Max number of concurrent checkouts.

    def __init__(self, repo=None, start_delay=0, **kwargs):
        """
        Checkout source code from gerrit.
        """
        super().__init__(**kwargs)
        if not repo:
            repo = 'git://git.openafs.org/openafs.git'

        if start_delay:
            self.add_delay_step(start_delay)

        self.addStep(steps.Gerrit(
            repourl=repo,
            mode='full',
            method='fresh',
            retryFetch=True,
            timeout=3600,
            locks=[self.gerrit_lock.access('counting', self.gerrit_lock_count)]))

        self.addStep(steps.ShellCommand(
            name='git show',
            command=['git', 'log', '-n', '1', '--stat']))

        self.addStep(steps.ShellCommand(
            name='git gc',
            command=['git', 'gc', '--auto']))

    def add_delay_step(self, seconds):
        """ Use sleep to delay by default. """
        self.addStep(steps.ShellCommand(name='sleep', command=['sleep', seconds]))


class UnixBuild(Checkout):
    """
    Build step factory to build OpenAFS using the regular configure and make commands.
    """
    def __init__(self, configure=None, jobs=4, target='all', **kwargs):
        super().__init__(**kwargs)
        self.addStep(afsbotcfg.steps.RegenStep())
        self.addStep(afsbotcfg.steps.Configure(configure))
        self.addStep(afsbotcfg.steps.Make(jobs, target))


class UnixBuildAndTest(UnixBuild):
    """
    Build step factory to build OpenAFS then run the unit tests.
    """
    def __init__(self, verbose=True, **kwargs):
        """
        Build then run the ctap unit tests.
        """
        super().__init__(**kwargs)
        if verbose:
            self.addStep(afsbotcfg.steps.BuildTests())
            self.addStep(afsbotcfg.steps.VerboseRunTestsStep())
        else:
            self.addStep(afsbotcfg.steps.RunTestsStep())


class UnixBuildDocs(Checkout):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.addStep(afsbotcfg.steps.RegenStep())
        self.addStep(afsbotcfg.steps.Configure())
        self.addStep(afsbotcfg.steps.Make(target='config'))
        self.addStep(afsbotcfg.steps.BuildDoc('AdminGuide'))
        self.addStep(afsbotcfg.steps.BuildDoc('AdminRef'))
        self.addStep(afsbotcfg.steps.BuildDoc('QuickStartUnix'))
        self.addStep(afsbotcfg.steps.BuildDoc('UserGuide'))


class WinBuild(Checkout):
    """
    Build step factory to build OpenAFS on Windows.

    The 'build-openafs.cmd' helper script must already be installed on the
    worker.  This is normally done as part of the buildbot worker setup.
    """
    def __init__(self, arch='amd64', variant='free', **kwargs):
        """
        Checkout the source then run the build script.
        """
        super().__init__(**kwargs)
        self.addStep(steps.ShellCommand(
            name='build-openafs',
            command=['build-openafs.cmd', arch, variant]))

    def add_delay_step(self, seconds):
        """
        Use 'ping' on windows since the sleep command is not available.
        """
        self.addStep(steps.ShellCommand(
            name='sleep',
            command=['ping', '-n', seconds, 'localhost']))


class BuildRPMs(Checkout):
    """
    Build step factory to build OpenAFS RPM packages.
    """
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

        self.addStep(steps.ShellCommand(
            name='Create source distribution tarballs',
            command=['build-tools/make-release', '--dir=packages', 'HEAD']))

        self.addStep(steps.FileDownload(
            name='Download make-rpm-workspace script',
            mastersrc='build-scripts/make-rpm-workspace.sh',
            workerdest='packages/make-rpm-workspace.sh',
            mode=0o755))

        self.addStep(steps.ShellCommand(
            name='Create rpmbuild directory',
            command=['packages/make-rpm-workspace.sh']))

        self.addStep(steps.RpmBuild(
            specfile='packages/rpmbuild/SPECS/openafs.spec',
            topdir='`pwd`/packages/rpmbuild',
            builddir='`pwd`/packages/rpmbuild/BUILD',
            rpmdir='`pwd`/packages/rpmbuild/RPMS',
            sourcedir='`pwd`/packages/rpmbuild/SOURCES',
            srcrpmdir='`pwd`/packages/rpmbuild/SRPMS'))

        self.addStep(steps.FileDownload(
            name='Download unpack-dkms-rpm script',
            mastersrc='build-scripts/unpack-dkms-rpm.sh',
            workerdest='packages/unpack-dkms-rpm.sh',
            mode=0o755))

        self.addStep(steps.ShellCommand(
            name='Unpack dkms-openafs rpm',
            command=['packages/unpack-dkms-rpm.sh']))

        self.addStep(steps.Configure(
            command=['./configure', '--with-linux-kernel-packaging'],
            workdir='build/packages/dkms/usr/src/openafs',
            logfiles={'config.log': 'config.log'}))

        self.addStep(steps.Compile(
            command=['make', '-j', '4', 'V=0'],
            workdir='build/packages/dkms/usr/src/openafs'))


class VirtRunBuild(util.BuildFactory):
    """
    Build step factory to start an ephemeral virtual machine to install a linux
    kernel version and then build and optionally test.

    The 'virt-run-build.sh' script and hypervisor setup is required before using
    this factory.
    """
    def __init__(self, linux='rc', test=True, **kwargs):
        super().__init__(**kwargs)
        build = [
            'virt-run-build.sh',
            '--branch', util.Property('branch', default='master'),
            '--linux', linux,
        ]
        if test:
            build.append('--smoke-test')
        self.addStep(steps.ShellCommand(name='virt-run-build', command=build))
