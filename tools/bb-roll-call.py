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
import smtplib
import ssl
import os
from email.message import EmailMessage
from email.utils import formatdate, make_msgid
try:
    from configparser import ConfigParser
except ImportError:
    from ConfigParser import ConfigParser

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
    #'opensuse13-arm',
    'opensuse15-arm64',
    'opensuse-tumbleweed-i386',
    'opensuse-tumbleweed-x86_64',
    'sol11sparc',
    'solaris114_x86_1',
    'sun510_x86',
    'sun511_x86',
    'ubuntu1610-x86_64',
    'ubuntu1804-amd64',
    'wins2019-amd64',
)

class RollCallError(Exception):
    pass

def roll_call():
    """Retreive connection status of workers.

    Returns an dictionary of workers by name. The values include the connection
    status and worker admin info.  Raises exceptions if the workers info cannot
    be retreive, an entry is missing, or an unexcepted entry is found.
    """
    session = requests.Session()
    rsp = session.get('https://buildbot.openafs.org/api/v2/workers')
    if rsp.status_code != 200:
        raise RollCallError('Request failed: %s' % rsp.text)

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

        # Verify we know about this worker if it is online.
        if name not in WORKERS:
            if status == 'online':
                raise RollCallError('Unknown worker: %s' % name)
            else:
                continue # Ingore offline old workers. Buildbot keeps these around.

        workers[name] = {'name':name, 'status':status, 'admin':admin, 'host':host}

    # Verify we did not miss any.
    for name in WORKERS:
        if not name in workers:
            raise RollCallError('No information for worker: %s' % name)

    return workers

def as_text(workers, all_=True):
    """Format the output as a text string."""
    lines = []
    for name in sorted(workers.keys()):
        w = workers[name]
        if all_ or w['status'] == 'offline':
            line = '%-8s %-28s %s' % (w['status'], w['name'], w['admin'])
            lines.append(line)
    return '\n'.join(lines)

def sendmail(subject, text):
    """Send an email."""
    parser = ConfigParser()
    parser.read([os.path.expanduser('~/.buildbotrc')])
    try:
        c = dict(parser.items('email'))
    except KeyError:
        raise RollCallError('Missing email section in .buildbotrc')
    for name in ('server', 'port', 'userid', 'password', 'from', 'to'):
        if not name in c:
            raise RollCallError('Missing email %s option in .buildbotrc' % name)

    msg = EmailMessage()
    msg['From'] = c['from']
    msg['To'] = c['to'].split(',')
    msg['Subject'] = subject
    msg['Date'] = formatdate()
    msg['Message-ID'] = make_msgid()
    if 'epilog' in c:
        msg.set_content(text + "\n\n" + c['epilog'])
    else:
        msg.set_content(text)

    context = ssl.create_default_context()
    with smtplib.SMTP_SSL(c['server'], c['port'], context=context) as server:
        server.login(c['userid'], c['password'])
        server.send_message(msg)

def main():
    parser = argparse.ArgumentParser(description='Take worker attendance')
    parser.add_argument('-a', '--all', action='store_true', help='Show all workers')
    parser.add_argument('-m', '--mail', action='store_true', help='Send email')
    args = parser.parse_args()
    try:
        workers = roll_call()
        text = as_text(workers, all_=args.all)
        if text:
            sys.stdout.write('%s\n' % text)
            if args.mail:
                sendmail('Buildbot roll call', text)
    except RollCallError as e:
        text = 'Error: %s\n' % e
        sys.stderr.write(text)
        if args.mail:
            sendmail('Buildbot roll call error', text)
        return 1
    return 0

if __name__ == '__main__':
    sys.exit(main())
