## Buildbot Builder Tags

The [OpenAFS Buildbot][1] uses tags to help organize and categorize builders on
the web interface. These tags provide context about what each builder does and
its current status. You can filter builders based on tags in various views in
the buildbot web interface.

This document outlines the tags currently in use and their meanings.

### Core Tags

**verify**: Builders with this tag are responsible for verifying Gerrit code
changes submitted by developers. These builders verify the build completes
without errors.  After the build completes on each builder for the given
branch, the buildbot marks the changes as verifed in the [OpenAFS Gerrit code
review system][2].

**checking**: These builders are specifically configured to **check for
compiler warnings**. On these builders, compiler warnings are treated as errors
to prevent potential issues from going unnoticed.

**tests**: Builders with the `tests` tag execute the TAP unit tests for the
project.  These tests are designed to verify the functionality of individual
components of the codebase.

**docs**: Builders tagged with `docs` check that proposed code changes do not
break the project documentation generation.

**package**: Builders tagged with `package` check that proposed code changes do
not break a packaging process. They ensure that the changes will not prevent
the creation of valid packages. The release packages are not created by
Buildbot at this time.

### Known Issues Tags

**deactived**: These builders are temporarily or permanently excluded from
receiving build requests. This is because they may be experiencing problems, be
outdated, or be undergoing setup and are not yet ready for use.

**tests-failing**: Builders with this tag are known to have pre-existing issues
that cause some unit tests to fail. While the tests are still executed, the
test step is configured to report a warning instead of a failure. This
indicates that these failures are acknowledged and are likely being tracked,
but haven't been resolved yet. Developers should be aware of these known
failing tests when reviewing results from these builders.

**git-status-failing**: Builders with this tag are known to have problems with
the git status check. This tag indicates that discrepancies in the reported Git
status from these builders might be expected and are under investigation. While
the `git status` check is still executed, the step is configured to report a
warning instead of a failure.

**docs-failing**: Builders with this tag are have known issues related to
documentation generation. This could mean that the worker is missing a
dependency to generate the documentation, or fails due to an identified problem
that is yet to be fixed.

### Branch Name Tags

**master**: Builders with this tag are configured to build the development branch
of the OpenAFS project.

**openafs-stable-1\_8\_x**: Builders with this tag are configured to build
the current stable branch of the OpenAFS project.

**openafs-stable-1\_6\_x**: This tag indicates builders that are set up to
build the old stable branch of the OpenAFS project.


[1]: https://buildbot.openafs.org
[2]: https://gerrit.openafs.org
