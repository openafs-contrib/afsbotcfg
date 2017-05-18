# This file is part of the OpenAFS buildbot configuration.

import os
from buildbot.plugins import worker

class Worker(worker.Worker):

    """This is a subclass of the standard buildbot Worker to provide defaults
    and to lookup the worker passwords from a file which is kept outside of source
    control."""

    def __init__(self, name, **kwargs):
        password = self._read_password(name)
        if 'contact' in kwargs:
            self.contact = kwargs.pop('contact')
        else:
            self.contact = 'Unknown'
        if not 'max_builds' in kwargs:
            kwargs['max_builds'] = 2
        worker.Worker.__init__(self, name, password, **kwargs)

    def _read_password(self, name):
        filename = os.path.join(os.path.dirname(__file__), "passwords")
        with open(filename, "r") as f:
            for line in f:
                (slave, password) = line.strip().split()
                if name == slave:
                    return password
        raise ValueError("Missing entry for '{0}' in file '{1}'.".format(name, filename))
