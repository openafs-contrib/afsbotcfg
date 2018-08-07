from os import getcwd
from os.path import abspath, join

topdir = abspath(join(getcwd(), '..'))
makefile = open('Makefile.in').read().replace('@TOPDIR@', topdir)
open('Makefile', 'w').write(makefile)
