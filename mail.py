# This file is part of the OpenAFS buildbot configuration.

import os

def getMailAddresses(name):
    addrs = []
    try:
        filename = os.path.join(os.path.dirname(__file__), name)
        with open(filename, 'r') as f:
            for line in f.read().splitlines():
                line = line.strip()
                if line and not line.startswith('#'):
                    addrs.append(line)
    except Exception:
        addrs = []
    return addrs

