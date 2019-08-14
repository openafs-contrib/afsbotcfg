#!/usr/bin/python3

import argparse
import getpass
import os
import sys
import requests
from configparser import ConfigParser

def die(msg):
    sys.stderr.write('%s\n' % msg)
    sys.exit(1)

def main():
    config = ConfigParser()
    config.read([os.path.expanduser('~/.buildbotrc')])

    parser = argparse.ArgumentParser(
        description='Force Gerrit Builds',
        epilog='Default values are read from the ~/.buildbotrc file, if it exists.')
    parser.add_argument('-u', '--username', metavar='<username>', default=config.get('login','username',fallback=None))
    parser.add_argument('-p', '--password', metavar='<password>', default=config.get('login','password',fallback=None))
    parser.add_argument('number', type=int)
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
        'changenumber': '%d' % args.number,
        'patchsetnumber': ''
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
    print(rsp)
    print(rsp.text)
    if rsp.status_code == 200:
        code = 0
    else:
        code = 1
    return code

if __name__ == '__main__':
    sys.exit(main())
