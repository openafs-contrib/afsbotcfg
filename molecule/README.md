# Testing

Molecule / ansible are used to perform testing.  Two molecule
scenarios are provided, the *default* creates a buildbot master
system and 2 workers.   The *master-only* creates only the buildbot
master.

## Basic test

The default testing configuration will match the configuration used
in the buildbot.openafs.org system with the exception of skipping
notifications to the admins of the workers.  This configuration works
well for performing a quick smoke test, but cannot perform a full
functional test.

Simply do a `make test`

## Functional tests

To perform a more through test, access to a test gerrit system that is
aware of the test buildbot will be needed.

To prepare the test gerrit system requires a clone of the openafs repo,
a "service" account that buildbot can use along with the permissions to
access the repo via the gerrit ssh interface and authority to update the
gerrit "Verified" label for that repo.

Create an environment yaml file that contains the connection information
to access the alternate gerrit system.

    GERRIT_SERVER: *<hostname for the gerrit system>*
    GERRIT_URL: *<url for the gerrit system>*
    GERRIT_REPO: *<url for the repository*>
    GERRIT_USER: *<service account name for buildbot>*
    GERRIT_IDENT: *<full filespec to the private key to when accessing gerrit ssh api>*

The public key associated with GERRIT_IDENT must be set in the gerrit
system for the GERRIT_USER. Access can be tested via the following command:

    ssh -p 29418 -i ${GERRIT_IDENT} ${GERRIT_USER}@{GERRIT_SERVER}

The GERRIT_URL is used to set the change url when performing a ForceGerritRebuild.

The GERRIT_REPO must specify a url that can be used to clone the repo from
gerrit.

Example, create the file test/mygerritenv.yml:

    GERRIT_SERVER: mygerrit.example.com
    GERRIT_URL: http://mygerrit.example.com:8080
    GERRIT_REPO: http://mygerrit.example.com:8080/openafs.git
    GERRIT_USER: test_bot
    GERRIT_IDENT: /home/me/asfbotcfg/test/test_bot

And run:

    molecule -e test/mygerritenv.yml create
    molecule -e test/mygerritenv.yml converge

Then you can manually exercise the interaction between the test master
and the gerrit system