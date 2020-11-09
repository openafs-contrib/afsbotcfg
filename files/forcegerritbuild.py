# Copyright (c) 2019 Sine Nomine Associates
#
# This file copies/extends portions of Buildbot forcescheduler.
# This software is available at no charge under the terms
# of the GNU General Public License version 2 (GPLv2) as
# available from the OSI(Open Software Initiative) website.

# THE SOFTWARE IS PROVIDED 'AS IS' AND THE AUTHOR DISCLAIMS ALL WARRANTIES
# WITH REGARD TO THIS SOFTWARE INCLUDING ALL IMPLIED WARRANTIES OF
# MERCHANTABILITY AND FITNESS. IN NO EVENT SHALL THE AUTHOR BE LIABLE FOR
# ANY SPECIAL, DIRECT, INDIRECT, OR CONSEQUENTIAL DAMAGES OR ANY DAMAGES
# WHATSOEVER RESULTING FROM LOSS OF USE, DATA OR PROFITS, WHETHER IN AN
# ACTION OF CONTRACT, NEGLIGENCE OR OTHER TORTIOUS ACTION, ARISING OUT OF
# OR IN CONNECTION WITH THE USE OR PERFORMANCE OF THIS SOFTWARE.

import json

from twisted.python import log
from twisted.internet import defer

from twisted.internet.utils import getProcessOutputAndValue

from buildbot.plugins import schedulers
from buildbot.plugins import util
from buildbot.util import bytes2unicode
from buildbot.schedulers.forcesched import ValidationErrorCollector
from buildbot.schedulers.forcesched import ValidationError

class ForceGerritBuild(schedulers.ForceScheduler):

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

        def __init__(self,
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

    def __init__(self, name, gerritserver=None, gerritport=29418, username=None, identity_file=None,
                 gerriturl=None, branchbuilders=None, **kwargs):

        builderNames = set()
        for _ in branchbuilders.values():
            builderNames.update(set(_))

        builderNames = list(builderNames)

        self.branchbuilders = branchbuilders
        self.gerrit = self.GerritCMD(gerritserver=gerritserver,
                                  gerritport=gerritport,
                                  username=username,
                                  identity_file=identity_file)

        self.gerrit_url = gerriturl

        super().__init__(name, builderNames, **kwargs)

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
                    if ps['number'] == UI_patchset:
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
                log.msg("forcegerritbuild: empty builders for branch: %s" (branch,))
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
                properties.setProperty("event.change.url", url, "GerritForceBuild" )

        except Exception as e:
            collector.setError(str(e))

        collector.maybeRaiseCollectedErrors()

        properties.setProperty("reason", reason, "ForceGerritBuild")
        properties.setProperty("owner", owner, "ForceGerritBuild")

        reason = self.reasonString % {'owner': owner, 'reason': reason}

        # Create the sourcestamps
        sourcestamps = [ {
                'codebase': '',
                'repository': '',
                'branch': patchset['ref'],
                'revision': patchset['revision'],
                'project': project
            }
        ]
        log.msg("forcegerritbuild: rebuilding branch[%s] revision[%s] project[%s] event.change.id[%s] patchset[%d]" %
                (patchset['ref'], patchset['revision'], project, changeid, patchset['number']))
        # everything is set and validated, we can create our source stamp, and
        # buildrequest
        res = yield self.addBuildsetForSourceStampsWithDefaults(
            reason=reason,
            sourcestamps=sourcestamps,
            properties=properties,
            builderNames=builderNames,
        )

        return res
