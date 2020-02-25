#!/usr/bin/python3
#
# Take worker attendance.
#
# List the workers and the connection status. Show the offline
# workers by default, or all the workers when run with the --all option.
# This is an unauthenticated request.
#

import argparse
import sys
import requests

WORKERS = (
    'centos73-x86_64',
    'centos7-arm64',
    'debian87-x86_64',
    'debian9-amd64',
    'fedora22-x86_64',
    'fedora23-x86_64',
    'fedora24-x86_64',
    'fedora25-x86_64',
    'fedora26-x86_64',
    'fedora27-x86_64',
    'fedora28-x86_64',
    'fedora29-x86_64',
    'fedora30-x86_64',
    'fedora31-x86_64',
    'gentoo-amd64',
    'gentoo-gcc-amd64',
    'linux-rc-x86_64',
    'macos10-13-x86_64',
    'macos10-14-x86_64',
    'macos10-15-x86_64',
    'opensuse12-x86_64',
    'opensuse13-arm',
    'opensuse-tumbleweed-i386',
    'opensuse-tumbleweed-x86_64',
    'sol11sparc',
    'sun510_x86',
    'sun511_x86',
    'ubuntu1610-x86_64',
    'ubuntu1804-amd64',
    'win7-amd64',
)

class RCError(Exception):
    pass

def print_worker(w):
    fields = (w['status'], w['name'], w['admin'], w['host'])
    sep = ':'
    print(sep.join(fields))

def roll_call(showall=False):

    session = requests.Session()
    rsp = session.get('https://buildbot.openafs.org/api/v2/workers')
    if rsp.status_code != 200:
        raise RCError('GET failed: %s' % rsp.text)

    workers = {}
    for worker in rsp.json()['workers']:
        name = worker['name']
        if name == '__Janitor':  # Skip the internal janitor service.
            continue
        status = 'online' if worker['connected_to'] else 'offline'
        admin = worker['workerinfo'].get('admin')
        if admin is None:
            admin = ''
        host = worker['workerinfo'].get('host')
        if host is None:
            host = ''
        admin = admin.replace('\n', ' ').replace(':', ' ').strip()
        host = host.replace('\n', ' ').replace(':', ' ').strip()
        workers[name] = {'name':name, 'status':status, 'admin':admin, 'host':host}

    # List the status of the known workers. The returned list may also contain
    # old workers (which should be offine).
    num_offline = 0
    for name in sorted(WORKERS):
        w = workers.get(name)
        if w is None:
            raise RCError('Missing worker: %s' % name)
        if showall:
            print_worker(w)
        elif w['status'] == 'offline':
            print_worker(w)
        if w['status'] == 'offline':
            num_offline += 1

    # Be sure our list is up to date.
    for name, worker in workers.items():
        if worker['status'] == 'online' and not name in WORKERS:
            raise RCError('Unknown worker is online: %s' % name)

    return num_offline

def main():
    parser = argparse.ArgumentParser(description='Take worker attendance')
    parser.add_argument('-a', '--all', action='store_true', help='Show all workers')
    args = parser.parse_args()
    try:
        count = roll_call(showall=args.all)
    except RCError as e:
        sys.stderr.write('Error: %s\n' % e)
        return 1
    rc = 1 if count > 0 else 0
    return rc

if __name__ == '__main__':
    sys.exit(main())
