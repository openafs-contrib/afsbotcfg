from os import getcwd
from os.path import abspath, join

topdir = getcwd()
buildbot = abspath(join(topdir, '../venv/bin/buildbot'))
master = abspath(join(topdir, '../master'))
makefile = \
    open('Makefile.in')\
    .read()\
    .replace('@TOPDIR@', topdir)\
    .replace('@BUILDBOT@', buildbot)\
    .replace('@MASTER@', master)
open('Makefile', 'w').write(makefile)
