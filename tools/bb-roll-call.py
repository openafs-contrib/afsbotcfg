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

def main():
    parser = argparse.ArgumentParser(description='Take worker attendance')
    parser.add_argument('-a', '--all', action='store_true', help='Show all workers')
    args = parser.parse_args()

    session = requests.Session()
    rsp = session.get('https://buildbot.openafs.org/api/v2/workers')
    if rsp.status_code != 200:
        print('GET failed', rsp.text)
        return 1

    for worker in rsp.json()['workers']:
        name = worker['name']
        if name == '__Janitor':  # Skip the internal janitor service.
            continue
        status = 'online' if worker['connected_to'] else 'offline'
        admin = worker['workerinfo'].get('admin')
        if admin is None:
            admin = ''
        admin = admin.replace('\n', ' ')
        host = worker['workerinfo'].get('host')
        if host is None:
            host = ''
        host = host.replace('\n', ' ')

        fields = [status, name, admin, host]
        if args.all:
            print('\t'.join(fields))
        elif status == 'offline':
            print('\t'.join(fields))

if __name__ == '__main__':
    sys.exit(main())
