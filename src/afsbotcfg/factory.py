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


"""OpenAFS buildbot build factories.

This module provides the factories which create the OpenAFS build steps.
Build factories are specified by class name in the master.cfg.j2 template.

Classes:

    GerritCheckoutFactory: Base class for our build factories.

    UnixBuildFactory:      Build with autoconf and make. Optionally
                           render documents and run TAP unit tests.

    WindowsBuildFactory:   Build on Windows using a preinstalled script.

    ELRpmBuildFactory:     Build RPM packages on a RedHat-like builder.
                           This factory also builds the kernel module from the
                           generated DMKS package to verify the DKMS package.
"""


from buildbot.plugins import steps
from buildbot.plugins import util

from afsbotcfg.steps import (
    Delay,
    Regen,
    Configure,
    Make,
    MakeDocs,
    RunTests,
    GitStatusCheck,
)


def isRealWorker(step):
    if step.worker.name == 'dummy':
        return False
    return True


def str2bool(s):
    if isinstance(s, bool):
        return s
    return s.lower() in ["1", "yes", "true"]


class GerritCheckoutFactory(util.BuildFactory):
    """Base class build factory.

    This build factory adds the common steps to checkout source from the gerrit
    git repo.
    """

    gerrit_lock = util.MasterLock("gerrit")
    gerrit_lock_count = 3  # Max number of concurrent checkouts.

    def __init__(self, repo=None, start_delay=0, tags=None, workdir='build', **kwargs):
        """Checkout source code from the Gerrit repository.

        Checkout the source using a lock to prevent too much load on the
        Gerrit server.

        Args:
            repo:        The Gerrit git repo URL.
            start_delay: The number of seconds to delay before checkout.
                         This delay allows the gerrit server
            workdir:     The directory to checkout source files.
        """
        delay = 30  # seconds
        retries = 120
        self.checkout_workdir = workdir

        super().__init__(**kwargs)

        if start_delay:
            self.addStep(Delay(start_delay, doStepIf=isRealWorker))

        self.addStep(
            steps.Gerrit(
                workdir=self.checkout_workdir,
                repourl=repo,
                mode='full',
                method='fresh',
                retry=(delay, retries),
                retryFetch=True,
                timeout=300,
                doStepIf=isRealWorker))

        self.addStep(
           steps.ShellSequence(
               name='show commit',
               workdir=self.checkout_workdir,
               commands=[
                   # The clean and reset were attempts at work arounds, and should not be needed here.
                   # util.ShellArg(command=['git', 'clean', '-f', '-x', '-d'], logname='git clean'),
                   # util.ShellArg(command=['git', 'reset', '--hard', 'HEAD'], logname='git reset'),
                   util.ShellArg(command=['git', 'log', '-n', '1', '--stat'], logname='git log')],
               doStepIf=isRealWorker))

    def addCleanupStep(self):
        self.addStep(
           steps.ShellSequence(
               name='git cleanup',
               workdir=self.checkout_workdir,
               commands=[
                   util.ShellArg(command=['git', 'clean', '-f', '-x', '-d'], logname='git clean'),
                   util.ShellArg(command=['git', 'gc', '--auto'], logname='git gc')],
               doStepIf=isRealWorker))


class UnixBuildFactory(GerritCheckoutFactory):
    """Build with autoconf and make.

    Build OpenAFS on Unix-like systems with autoconf and make. Optionally
    render the documentation and run the TAP unit tests.
    """

    def __init__(self,
                 tags=None,
                 objdir='false',
                 configure=None,
                 make='make',
                 pretty='false',
                 jobs='4',
                 shuffle='false',
                 target='all',
                 tests=True,
                 docs=False,
                 **kwargs):
        """Create a UnixBuildFactory instance.

        Args:
            tags          Builder tags (list of strings)
            objdir:       Build in separate directory when true (boolean)
            configure:    configure options (string)
            make:         make command (string)
            pretty:       Pretty make output (boolean string)
            jobs:         Number of make jobs (int string)
            shuffle:      Shuffle make file targets (boolean string)
            target:       The top level makefile target (string)
            tests:        Also run the TAP unit tests (bool)
            docs:         Also render the docs when true (bool)
        """
        if tags is None:
            tags = []
        objdir = str2bool(objdir)
        pretty = str2bool(pretty)
        shuffle = str2bool(shuffle)
        tests = str2bool(tests)
        docs = str2bool(docs)

        try:
            jobs = int(jobs)
        except ValueError:
            jobs = 0

        # Use separate source and build directories in objdir mode.
        if objdir:
            checkoutdir = 'source'
            builddir = 'build'
            cf = '../source/configure'
        else:
            checkoutdir = 'build'
            builddir = 'build'
            cf = './configure'

        super().__init__(workdir=checkoutdir, **kwargs)

        if builddir != checkoutdir:
            self.addStep(steps.RemoveDirectory(dir=builddir, doStepIf=isRealWorker))
            self.addStep(steps.MakeDirectory(dir=builddir, doStepIf=isRealWorker))

        self.addStep(Regen(workdir=checkoutdir, doStepIf=isRealWorker))
        self.addStep(Configure(configure=cf, options=configure, doStepIf=isRealWorker))
        self.addStep(Make(make=make, jobs=jobs, pretty=pretty, shuffle=shuffle, target=target, doStepIf=isRealWorker))

        if docs:
            self.addStep(
                MakeDocs(
                    make=make,
                    warnOnFailure=('docs-failing' in tags),
                    doStepIf=isRealWorker))

        if not objdir:
            self.addStep(
                GitStatusCheck(
                    prefix='post build ',
                    warnOnFailure=('git-status-failing' in tags),
                    doStepIf=isRealWorker))

        if tests:
            self.addStep(
                RunTests(
                    make=make,
                    warnOnFailure=('tests-failing' in tags),
                    doStepIf=isRealWorker))
            if not objdir:
                self.addStep(
                    GitStatusCheck(
                        prefix='post test ',
                        warnOnFailure=('git-status-failing' in tags),
                        doStepIf=isRealWorker))

        self.addCleanupStep()


class WindowsBuildFactory(GerritCheckoutFactory):
    """Build on Windows with a script.

    The 'build-openafs.cmd' script must be manually installed on the
    Windows buildbot worker.
    """
    def __init__(self, arch='amd64', variant='free', **kwargs):
        super().__init__(**kwargs)

        self.addStep(steps.ShellCommand(
            name='build-openafs',
            command=['build-openafs.cmd', arch, variant],
            doStepIf=isRealWorker))

        self.addStep(GitStatusCheck(doStepIf=isRealWorker))

        self.addCleanupStep()


class ELRpmBuildFactory(GerritCheckoutFactory):
    """Build OpenAFS RPM packages on a RHEL-like system.

    Build the RPM packages on a RHEL-like system from a git checkout.  After
    the packages are built, unpack the OpenAFS DKMS package and build the
    OpenAFS kernel module to verify the DKMS package is usable.

    This build factory downloads and runs several scripts to build the RPM
    packages. The scripts are downloaded from the build-tools directory on the
    buildbot master.  The in-tree `make-srpm.pl` script is avoided by the build
    factory since it is far too fragile.

    Scripts:
        make-rpm-workspace.sh   Create and populate the rpmbuild/SOURCES.
        unpack-dkms-rpm.sh      Unpack the DKMS package.

    Args:
        build_dkms_source
    """

    def __init__(self, build_dkms_source="false", **kwargs):
        super().__init__(**kwargs)
        build_dkms_source = str2bool(build_dkms_source)
        self.addStep(
            steps.MakeDirectory(
                name="mkdir build/packages",
                dir='build/packages',
                doStepIf=isRealWorker))
        self.addStep(
            steps.FileDownload(
                name='download make-rpm-workspace.sh',
                mastersrc='build-scripts/make-rpm-workspace.sh',
                workerdest='packages/make-rpm-workspace.sh',
                mode=0o755,
                doStepIf=isRealWorker))
        self.addStep(
            steps.FileDownload(
                name='download unpack-dkms-rpm.sh',
                mastersrc='build-scripts/unpack-dkms-rpm.sh',
                workerdest='packages/unpack-dkms-rpm.sh',
                mode=0o755,
                doStepIf=isRealWorker))
        self.addStep(
            steps.ShellCommand(
                name='make-release',
                command=['build-tools/make-release', '--dir=packages', 'HEAD'],
                doStepIf=isRealWorker))
        self.addStep(
            steps.ShellCommand(
                name='make-rpm-workspace.sh',
                command=['packages/make-rpm-workspace.sh'],
                doStepIf=isRealWorker))
        self.addStep(
            steps.RpmBuild(
                specfile='packages/rpmbuild/SPECS/openafs.spec',
                topdir='`pwd`/packages/rpmbuild',
                builddir='`pwd`/packages/rpmbuild/BUILD',
                rpmdir='`pwd`/packages/rpmbuild/RPMS',
                sourcedir='`pwd`/packages/rpmbuild/SOURCES',
                srcrpmdir='`pwd`/packages/rpmbuild/SRPMS',
                doStepIf=isRealWorker))

        if build_dkms_source:
            self.addStep(
                steps.ShellCommand(
                    name='unpack-dkms-rpm.sh',
                    command=['packages/unpack-dkms-rpm.sh'],
                    doStepIf=isRealWorker))
            self.addStep(
                steps.Configure(
                    command=['./configure', '--with-linux-kernel-packaging'],
                    workdir='build/packages/dkms/usr/src/openafs',
                    logfiles={'config.log': 'config.log'},
                    doStepIf=isRealWorker))
            self.addStep(
                steps.Compile(
                    command=['make', '-j', '4', 'V=0'],
                    workdir='build/packages/dkms/usr/src/openafs',
                    doStepIf=isRealWorker))

        self.addCleanupStep()
