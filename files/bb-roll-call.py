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

class RollCallError(Exception):
    pass

def worker_roster():
    """Read the list of known workers from the buildbot master config."""
    parser = ConfigParser()
    if not parser.read([os.path.expanduser('~/.buildbotrc')]):
        raise RollCallError('Unable to read .buildbotrc')
    option = parser.get('rollcall', 'workers')
    workers = option.split()
    return workers

def roll_call(roster):
    """Retrieve connection status of workers.

    Returns an dictionary of workers by name. The values include the connection
    status and worker admin info.  Raises exceptions if the workers info cannot
    be retrieve, an entry is missing, or an unexpected entry is found.
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
        if name not in roster:
            if status == 'online':
                raise RollCallError('Unknown worker: %s' % name)
            else:
                continue # Ingore offline old workers. Buildbot keeps these around.

        workers[name] = {'name':name, 'status':status, 'admin':admin, 'host':host}

    # Verify we did not miss any.
    for name in roster:
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
    for name in ('server', 'from', 'to'):
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

    if c['server'] == 'local':
        with smtplib.SMTP('localhost') as server:
            server.send_message(msg)
    else:
        for name in ('port', 'userid', 'password'):
            if not name in c:
                raise RollCallError('Missing email %s option in .buildbotrc' % name)
        context = ssl.create_default_context()
        with smtplib.SMTP_SSL(c['server'], c['port'], context=context) as server:
            server.login(c['userid'], c['password'])
            server.send_message(msg)

def main():
    parser = argparse.ArgumentParser(description='Take worker attendance')
    parser.add_argument('-a', '--all', action='store_true', help='Show all workers')
    parser.add_argument('-m', '--mail', action='store_true', help='Send email')
    parser.add_argument('-q', '--quiet', action='store_true', help='Quiet mode')
    args = parser.parse_args()
    try:
        roster = worker_roster()
        workers = roll_call(roster)
        text = as_text(workers, all_=args.all)
        if text:
            if args.mail:
                if not args.quiet:
                    sys.stdout.write('Sending Mail:\n %s\n' % text)
                sendmail('Buildbot roll call', text)
            elif not args.quiet:
                sys.stdout.write('%s\n' % text)
    except RollCallError as e:
        text = 'Error: %s\n' % e
        sys.stderr.write(text)
        if args.mail:
            sendmail('Buildbot roll call error', text)
        return 1
    return 0

if __name__ == '__main__':
    sys.exit(main())
