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

"""Classes to support manually forced builds."""

import json

from twisted.python import log
from twisted.internet import defer

from twisted.internet.utils import getProcessOutputAndValue

from buildbot.plugins import schedulers
from buildbot.plugins import util
from buildbot.util import bytes2unicode
from buildbot.schedulers.forcesched import ValidationErrorCollector
from buildbot.schedulers.forcesched import ValidationError


class Force(schedulers.ForceScheduler):

    def __init__(self, builder, workers):
        super().__init__(
            name='force-%s' % builder,
            buttonName='Force build',
            label='Force build on %s' % builder,
            builderNames=[builder],
            reason=util.StringParameter(
                name='reason',
                label='Reason:',
                default='force build',
                required=True,
                size=80,
            ),
            codebases=[
                util.CodebaseParameter(
                    '',
                    label='Repository',
                    # Generate just the branch entry in the form, but revision,
                    # repository, and project are needed by buildbot scheduling
                    # system so we need to pass an empty value ("") for those.
                    # Note: branch value may be a gerrit change id branch.
                    branch=util.StringParameter(
                        name='branch',
                        label='Branch:',
                        default='master',
                        required=True,
                        size=80,
                    ),
                    revision=util.FixedParameter(name='revision', default=''),
                    repository=util.FixedParameter(name='repository', default=''),
                    project=util.FixedParameter(name='project', default=''),
                ),
            ],
            properties=[
                util.WorkerChoiceParameter(
                    label='Worker:',
                    default=workers[0],
                    choices=workers,
                ),
            ],
        )


class GerritForceScheduler(schedulers.ForceScheduler):

    class LocalValidationErrorCollector(ValidationErrorCollector):
        """
            Allow setting a fieldname to collect errors on
        """
        def setFieldName(self, name):
            self.fieldname = name

        def setError(self, errormsg):
            if self.fieldname not in self.errors:
                self.errors[self.fieldname] = errormsg
            else:
                self.errors[self.fieldname] = self.errors[self.fieldname] + '\n' + errormsg

    class GerritCMD(object):
        """
            Connection to a gerrit command line interface
        """
        gerrit_server = None
        gerrit_username = None
        gerrit_port = None
        gerrit_identity_file = None

        def __init__(
                self,
                gerritserver=None,
                gerritport=29418,
                username=None,
                identity_file=None):

            self.gerrit_server = gerritserver
            self.gerrit_port = gerritport
            self.gerrit_username = username
            self.gerrit_identity_file = identity_file

        def _gerritCmd(self, *args):
            '''Construct a command as a list of strings suitable for
            :func:`subprocess.call`.
            '''
            if self.gerrit_identity_file is not None:
                options = ['-i', self.gerrit_identity_file]
            else:
                options = []
            return ['ssh'] + options + [
                '@'.join((self.gerrit_username, self.gerrit_server)),
                '-p', str(self.gerrit_port),
                'gerrit'
            ] + list(args)

        @defer.inlineCallbacks
        def query(self, changenumber):
            """
                Run gerrit query and return the data result
            """
            cmd = self._gerritCmd("query --format json --patch-sets limit:1 change:%s" % (changenumber,))
            result = yield getProcessOutputAndValue(cmd[0], cmd[1:])
            (out, err, status) = result

            if status != 0:
                log.msg("forcegerritrebuild: gerrit status error: %d %s" % (status, err))
                raise ValidationError("Error response from Gerrit %s" % (self.gerrit_server,))
            try:
                out = out.strip()
                reslist = [json.loads(bytes2unicode(_.strip())) for _ in out.split(b"\n")]

                qstatus = reslist[-1]
                if qstatus['rowCount'] != 1:
                    return None

                dataresult = reslist[0]
            except Exception as e:
                raise ValidationError("Error processing response from Gerrit: %s" % (e, ))
            return dataresult

    def __init__(
            self,
            name,
            gerritserver=None,
            gerritport=29418,
            username=None,
            identity_file=None,
            gerriturl=None,
            branchbuilders=None):
        builderNames = set()
        for names in branchbuilders.values():
            builderNames.update(set(names))

        builderNames = list(builderNames)

        self.branchbuilders = branchbuilders
        self.gerrit = self.GerritCMD(gerritserver=gerritserver,
                                     gerritport=gerritport,
                                     username=username,
                                     identity_file=identity_file)

        self.gerrit_url = gerriturl
        super().__init__(
            name,
            builderNames,
            label='Force gerrit build',
            reason=util.StringParameter(
                name='reason',
                label='Reason',
                default='force build',
                required=True,
                size=80),
            codebases=[
                util.CodebaseParameter(
                    '',
                    branch=util.FixedParameter(name='branch', default=''),
                    revision=util.FixedParameter(name='revision', default=''),
                    repository=util.FixedParameter(name='repository', default=''),
                    project=util.FixedParameter(name='project', default=''),
                )
            ],
            properties=[
                util.StringParameter(
                    name='changenumber',
                    label='Gerrit Change#',
                    default='', size=40, regex=r'^\d+$',
                    required=True),
                util.StringParameter(
                    name='patchsetnumber',
                    label='Gerrit patchset# (defaults to latest)',
                    default='', size=40, regex=r'^(\d*)$')])

    #  Process the paramters given in the web form
    #    query gerrit for addition information
    #
    @defer.inlineCallbacks
    def force(self, owner, builderNames=None, builderid=None, **kwargs):
        """
        We check the parameters, and launch the build, if everything is correct
        """

        # Currently the validation code expects all kwargs to be lists
        # I don't want to refactor that now so much sure we comply...
        kwargs = dict((k, [v]) if not isinstance(v, list) else (k, v)
                      for k, v in kwargs.items())

        # probably need to clean that out later as the IProperty is already a
        # validation mechanism
        collector = self.LocalValidationErrorCollector()
        reason = yield collector.collectValidationErrors(self.reason.fullName,
                                                         self.reason.getFromKwargs, kwargs)
        if owner is None or owner == "anonymous":
            owner = yield collector.collectValidationErrors(self.username.fullName,
                                                            self.username.getFromKwargs, kwargs)

        properties, changeids, sourcestamps = yield self.gatherPropertiesAndChanges(
            collector, **kwargs)

        try:
            # Retrieve the gerrit change
            collector.setFieldName("changenumber")
            UI_changenum = str(properties.getProperty("changenumber"))

            gerritinfo = yield self.gerrit.query(UI_changenum)

            if gerritinfo is None or str(gerritinfo['number']) != UI_changenum:
                raise ValidationError("Unable to retrieve gerrit issue %s" % (UI_changenum,))

            # Get the requested patchset
            collector.setFieldName("patchsetnumber")
            UI_patchset = properties.getProperty("patchsetnumber")
            patchsets = gerritinfo['patchSets']
            patchset = max(patchsets, key=lambda item: int(item['number']))

            if UI_patchset is not None and UI_patchset != '':
                patchset = None
                UI_patchset = int(UI_patchset)
                for ps in gerritinfo['patchSets']:
                    if int(ps['number']) == UI_patchset:
                        patchset = ps

                if patchset is None:
                    raise ValidationError("Invalid patchset '%d'" % (UI_patchset,))

            # Prepare the values needed for the GerritStatusPush reporter
            collector.setFieldName("changenumber")
            branch = gerritinfo['branch']
            changeid = gerritinfo['id']
            project = gerritinfo['project']

            # Make sure there are some workers available to build this branch
            if branch not in self.branchbuilders:
                log.msg("forcegerritbuild: branch %s does not have any configured builders" % (branch, ))
                raise ValidationError("Branch %s does not have any configured builders" % (branch,))

            builderNames = self.branchbuilders[branch]
            if not builderNames:
                log.msg("forcegerritbuild: empty builders for branch: %s" % (branch,))
                raise ValidationError("Empty builders for branch %s" % (branch,))

            # Set the properties neede by GerritStatusPush reporter
            properties.setProperty("event.change.id", changeid, "ForceGerritBuild")
            properties.setProperty("event.patchSet.number", str(patchset['number']), "ForceGerritBuild")
            properties.setProperty("event.change.project", project, "ForceGerritBuild")
            properties.setProperty("event.patchSet.revision", patchset['revision'], "ForceGerritBuild")

            if self.gerrit_url:
                url = self.gerrit_url % {
                    "project": project,
                    "changenumber": str(gerritinfo['number']),
                    "patchsetnumber": str(patchset['number'])
                }
                properties.setProperty("event.change.url", url, "GerritForceBuild")

        except Exception as e:
            collector.setError(str(e))

        collector.maybeRaiseCollectedErrors()

        properties.setProperty("reason", reason, "ForceGerritBuild")
        properties.setProperty("owner", owner, "ForceGerritBuild")

        reason = self.reasonString % {'owner': owner, 'reason': reason}

        # Create the sourcestamps
        sourcestamps = [{
            'codebase': '',
            'repository': '',
            'branch': patchset['ref'],
            'revision': patchset['revision'],
            'project': project
        }]
        log.msg("forcegerritbuild: rebuilding branch[%s] revision[%s] project[%s] event.change.id[%s] patchset[%s]" %
                (patchset['ref'], patchset['revision'], project, changeid, str(patchset['number'])))
        # everything is set and validated, we can create our source stamp, and
        # buildrequest
        res = yield self.addBuildsetForSourceStampsWithDefaults(
            reason=reason,
            sourcestamps=sourcestamps,
            properties=properties,
            builderNames=builderNames,
        )

        return res
