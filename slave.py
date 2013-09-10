
from buildbot.buildslave import BuildSlave
import os

class OpenAFSBuildSlave(BuildSlave):
    def get_password(self, name):
        filename = os.path.join(os.path.dirname(__file__), "passwords")
        passwords = open(filename, "r")
        for line in passwords:
	    (slave, password) = line.strip().split()
	    if name == slave:
		passwords.close()
                return password
        raise ValueError("Missing password entry in file '%s' for slave '%s'" % (filename, name))

    def __init__(self, name, **kwargs):
        password = self.get_password(name)
        BuildSlave.__init__(self, name, password, **kwargs)


