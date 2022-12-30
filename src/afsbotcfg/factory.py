
from buildbot.plugins import steps
from buildbot.plugins import util

import afsbotcfg.steps


class Checkout(util.BuildFactory):
    """
    Build step factory to checkout source code from gerrit git repo.
    """

    gerrit_lock = util.MasterLock("gerrit")
    gerrit_lock_count = 1  # Max number of concurrent checkouts.

    def _create_delay_step(self, seconds):
        """
        Delay for some time after the gerrit event is received until we start
        the checkout to workaround races in gerrit.  Subclasses can override
        this method to provide a different method to sleep.
        """
        return steps.ShellCommand(
            name='sleep',
            command=['sleep', seconds])

    def __init__(
            self,
            repo='git://git.openafs.org/openafs.git',
            start_delay=0,
            **kwargs):
        """
        Checkout source code from gerrit.
        """
        super().__init__(**kwargs)

        if start_delay:
            # TODO: add random value to stagger checkouts?
            self.addStep(self._create_delay_step(start_delay))

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


class UnixBuild(Checkout):
    """
    Build step factory to build OpenAFS using the regular configure and make commands.
    """
    def __init__(
            self,
            extra_configure=None,
            jobs=4,
            target='all',
            **kwargs):
        """
        Checkout the code then run regen.sh, configure, and make.
        """
        super().__init__(**kwargs)
        try:
            jobs = int(jobs)
        except ValueError:
            jobs = 1

        regen = ['/bin/sh', 'regen.sh']
        self.addStep(steps.ShellCommand(
            name='regen.sh',
            command=regen))

        configure = ['./configure']
        configure.extend(self.getConfigureOptions(extra_configure))
        self.addStep(steps.Configure(
            command=configure,
            logfiles={'config.log': 'config.log'}))

        self.addMakeStep(jobs, target)

    def getConfigureOptions(self, extra_configure):
        """
        Assemble the configure options for the configure step.
        """
        options = [
            '--enable-warnings',
            '--enable-checking',
            '--enable-supergroups',
            '--enable-namei-fileserver',
            '--enable-pthreaded-ubik',
            '--enable-pthreaded-bos',
        ]
        if extra_configure:
            options.extend(' '.split(extra_configure))
        return options

    def addMakeStep(self, jobs, target):
        """
        Add the make step.
        """
        make = ['make']
        if jobs > 1:
            make.append('-j')
            make.append('%d' % jobs)
        make.append(target)
        self.addStep(steps.Compile(command=make))


class UnixBuildIgnoreWarnings(UnixBuild):

    def __init__(
            self,
            **kwargs):
        """
        Checkout the code then run regen.sh, configure, and make.
        """
        super().__init__(**kwargs)

    def getConfigureOptions(self, extra_configure):
        options = super().getConfigureOptions(extra_configure)
        if '--enable-checking' in options:
            options.remove('--enable-checking')
        options.append('--disable-checking')
        return options


class UnixBuildAndTest(UnixBuild):
    """
    Build step factory to build OpenAFS then run the unit tests.
    """
    def __init__(
            self,
            verbose=True,
            **kwargs):
        """
        Build then run the ctap unit tests.
        """
        self.verbose = verbose
        super().__init__(**kwargs)

    def addMakeStep(self, jobs, target):
        if self.verbose:
            self.addStep(afsbotcfg.steps.BuildTests())
            self.addStep(afsbotcfg.steps.VerboseRunTestsStep())
        else:
            self.addStep(afsbotcfg.steps.RunTestsStep())


class UnixBuildDocs(UnixBuild):
    def __init__(
            self,
            **kwargs):
        super().__init__(**kwargs)

    def addMakeStep(self, jobs, target):
        self.addStep(steps.Compile(command=['make', 'config'], name='make config'))
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
    def _create_delay_step(self, seconds):
        """
        We use 'ping' on windows since the sleep command is not available on
        Windows by default.
        """
        return steps.ShellCommand(
            name='sleep',
            command=['ping', '-n', seconds, 'localhost'])

    def __init__(
            self,
            arch='amd64',
            variant='free',
            **kwargs):
        """
        Checkout the source then run the build script.
        """
        super().__init__(**kwargs)
        self.addStep(steps.ShellCommand(
            name='build-openafs',
            command=['build-openafs.cmd', arch, variant]))


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
    def __init__(
            self,
            linux='rc',
            test=True,
            **kwargs):
        super().__init__(**kwargs)
        build = [
            'virt-run-build.sh',
            '--branch', util.Property('branch', default='master'),
            '--linux', linux,
        ]
        if test:
            build.append('--smoke-test')
        self.addStep(steps.ShellCommand(name='virt-run-build', command=build))
