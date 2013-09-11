#
# This is a utility to extract the build slaves passwords from the
# master.cfg file. Use this to create the initial `passwords' file.
# It will not overwrite the `passwords' file if it already exists.
#
# To create the initial passwords file, run this in the buildbot
# basedir (the directory which contains the master.cfg).
#
#   $ cd $basedir
#   $ python afsbotcfg/extract_passwords.py
#

import sys
import os

def get_slaves(filename):
    localDict = {}
    f = open(filename, "r")
    exec f in localDict
    f.close()
    config_dict = localDict['BuildmasterConfig']
    return config_dict['slaves']

def extract_passwords(slaves):
    filename = os.path.join(os.path.dirname(__file__), "passwords")
    if os.path.exists(filename):
        sys.stderr.write("Output file '%s' already exists!\n" % filename)
        sys.exit(1)
    f = open(filename, "w+")
    for slave in slaves:
        f.write("%s %s\n" % (slave.slavename, slave.password))
    f.close()

if __name__ == "__main__":
    extract_passwords(get_slaves("master.cfg"))
