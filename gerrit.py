# This file is part of the OpenAFS buildbot configuration.

from buildbot.plugins import util

def gerritSummaryCB(buildInfoList, results, status, arg):
    """Format the gerrit update after all the builders have finished."""
    success = False
    failure = False
    msgs = []
    for buildInfo in buildInfoList:
        msg = 'Builder %(name)s %(resultText)s (%(text)s)' % buildInfo
        link = buildInfo.get('url', None)
        if link:
            msg += ' - ' + link
        else:
            msg += '.'
        msgs.append(msg)
        if buildInfo['result'] == util.SUCCESS:
            success = True
        else:
            failure = True
    msg = '\n\n'.join(msgs)
    if success and not failure:
        verified = 1
    else:
        verified = 0
    reviewed = 0
    return (msg, verified, reviewed)
