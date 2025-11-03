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

"""Generate build summary report to be posted to Gerrit."""

from buildbot.plugins import util

from twisted.python import log


def summaryCB(buildInfoList, results, status, arg):
    """Generate the build summary report.

    This callback is invoked by the buildbot master after the builders finished
    to generate a human readable summary and the Gerrit verification (yes or
    no) for the change.

    Args:
        buildInfoList:  List of build information.
        results:        Not used
        status:         Not used
        arg:            Report header lines

    Returns:
        A dict with the messages and the Gerrit verified label.
    """

    def report_build_status(buildlist, finalstatus=None):
        for info in buildlist:
            msg = "    Builder %(name)s" % info
            link = info.get('url', None)
            if link:
                msg += " - " + link
            if finalstatus:
                msg += "\n       Final build status %(resultText)s" % finalstatus[info['name']]
            yield msg

    msgs = list(arg)   # summaryArg contains the message headers.

    # sort buildinfo by builder and completed build time
    # we want to get the final result of any particular builder
    # in case there was a retry that ended up with a successful build
    buildInfoList.sort(
        key=lambda buildinfo: (buildinfo['name'], buildinfo['build']['complete_at']))

    builderFinalStatus = dict()
    for buildInfo in buildInfoList:
        builderFinalStatus[buildInfo['name']] = buildInfo
        # Fix up the final status
        if buildInfo['result'] == util.CANCELLED:
            if buildInfo['text'] == 'build failed due to worker timeout':
                builderFinalStatus[buildInfo['name']]['result'] = util.FAILURE
                builderFinalStatus[buildInfo['name']]['resultText'] = "cancelled"
            elif buildInfo['text'] == 'build skipped due to worker timeout':
                builderFinalStatus[buildInfo['name']]['result'] = util.SKIPPED
                builderFinalStatus[buildInfo['name']]['resultText'] = "cancelled"
        elif buildInfo['result'] == util.SUCCESS:
            buildername = buildInfo['name']
            workername, _ = buildInfo['build']['properties']['workername']
            if workername == "dummy":
                log.msg(f"afsbotcfg: summaryCB: setting skipped build: buildername={buildername} workername={workername}")
                builderFinalStatus[buildInfo['name']]['result'] = util.SKIPPED
                builderFinalStatus[buildInfo['name']]['resultText'] = "skipped"

    # Possible results: SUCCESS WARNINGS FAILURE SKIPPED EXCEPTION RETRY CANCELLED
    successfulBuilds = [
        fstatus for fstatus in builderFinalStatus.values() if fstatus['result'] == util.SUCCESS
    ]
    failedBuilds = [
        fstatus for fstatus in builderFinalStatus.values() if fstatus['result'] != util.SUCCESS
        and fstatus['result'] != util.SKIPPED
    ]
    skippedBuilds = [
        fstatus for fstatus in builderFinalStatus.values() if fstatus['result'] == util.SKIPPED
    ]

    # typically retries or interrupted builds
    restartedBuilds = [
        buildinfo for buildinfo in buildInfoList if buildinfo not in successfulBuilds
        and buildinfo not in failedBuilds
        and buildinfo not in skippedBuilds
    ]

    msgs.append("Final Build Status (failed=%d succeeded=%d skipped=%d):" %
                (len(failedBuilds), len(successfulBuilds), len(skippedBuilds)))

    if len(failedBuilds) > 0:
        msgs.append("\n Failed Builds:")
        msgs.extend(report_build_status(failedBuilds))

    if len(successfulBuilds) > 0:
        msgs.append("\n Successful Builds:")
        msgs.extend(report_build_status(successfulBuilds))

    if len(restartedBuilds) > 0:
        msgs.append("\n Restarted Builds:")
        msgs.extend(report_build_status(restartedBuilds, finalstatus=builderFinalStatus))

    if len(skippedBuilds) > 0:
        msgs.append("\n Skipped Builds:")
        msgs.extend(report_build_status(skippedBuilds))

    message = '\n'.join(msgs)

    if len(successfulBuilds) != 0 and len(failedBuilds) == 0:
        verified = 1
    else:
        verified = 0

    return dict(message=message, labels={'Verified': verified})
