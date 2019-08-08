
import requests
import sys

username = sys.argv[1]
password = sys.argv[2]
changenumber = sys.argv[3]

payload = {
  "id": 1,
  "jsonrpc": "2.0",
  "method": "force",
  "params": {
    "builderid": "2",
    "username": "",
    "reason": "Force Gerrit Build",
    "branch": "",
    "project": "test",
    "repository": "",
    "revision": "",
    "changenumber": changenumber,
    "patchsetnumber": ""
  }
}

session = requests.Session()
session.auth = (username, password)
auth = session.get('https://buildbot.openafs.org/auth/login')
print('auth:', auth)
print(auth.text)

rsp = session.post('https://buildbot.openafs.org/api/v2/forceschedulers/ForceGerritBuild', json=payload)
print('rsp:', rsp)
print(rsp.text)
