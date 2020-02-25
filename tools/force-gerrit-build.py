#!/usr/bin/python
#
# Manually schedule builds of gerrits by number.
#
# This tool can be used to trigger gerrit verification builds by gerrit number.
# This can be handy when retrying a build because a worker was down. By
# default, the buildbot master will schedule the most recent patchset to be
# built. You may specify an older patchset number if for some reason you want
# to build an older patchset.
#
# Setup
# -----
#
# 1. Install required packages:
#
#    $ pip install -r requirements.txt
#
# 2. Copy this script to a location in your PATH, for example:
#
#    $ cp force-gerrit-build.py ~/.local/bin
#
# 3. Optionally, put your buildbot credentials in the ~/.buildbotrc file.
#    force-gerrit-build.py will prompt for your credentials otherwise.
#
#      [login]
#      username = tycobb@yoyodyne.com
#      password = secret
#
# Examples
# --------
#
#    $ force-gerrit-build.py 12345
#

import argparse
import getpass
import os
import sys
import requests
try:
    from configparser import ConfigParser
except ImportError:
    from ConfigParser import ConfigParser

def die(msg):
    sys.stderr.write('%s\n' % msg)
    sys.exit(1)

def main():
    config = ConfigParser()
    config.read([os.path.expanduser('~/.buildbotrc')])
    try:
        login = dict(config.items('login'))
    except:
        login = {}

    parser = argparse.ArgumentParser(
        description='Force Gerrit Builds',
        epilog='Default values are read from the ~/.buildbotrc file, if it exists.')
    parser.add_argument('-u', '--username', metavar='<username>', default=login.get('username',None))
    parser.add_argument('-p', '--password', metavar='<password>', default=login.get('password',None))
    parser.add_argument('number', type=int)
    parser.add_argument('patchset', type=int, nargs='?')
    args = parser.parse_args()

    if not args.username:
        args.username = getpass.getuser()
    if not args.password:
        args.password = getpass.getpass()

    payload = {
      'id': 1,
      'jsonrpc': '2.0',
      'method': 'force',
      'params': {
        'builderid': '2',
        'username': '',
        'reason': 'Force Gerrit Build',
        'branch': '',
        'project': 'test',
        'repository': '',
        'revision': '',
        'changenumber': str(args.number),
        'patchsetnumber': str(args.patchset) if args.patchset else '',
      }
    }

    session = requests.Session()
    session.auth = (args.username, args.password)
    print('Logging in as %s' % args.username)
    auth = session.get('https://buildbot.openafs.org/auth/login')
    if auth.status_code != 200:
        print('Login failed', auth.text)
        return 1
    print('Login ok')

    rsp = session.post('https://buildbot.openafs.org/api/v2/forceschedulers/ForceGerritBuild', json=payload)
    if rsp.status_code != 200:
        print('Post failed', rsp.text)
        return 1
    print('Verfication builds for gerrit %d requested.' % args.number)

if __name__ == '__main__':
    sys.exit(main())
