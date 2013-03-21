#!/usr/bin/env python

# distutils setup script for fcrypt.
#
# Copyright (C) 2000, 2001  Carey Evans  <careye@spamcop.net>

from distutils.core import setup

setup( name = 'fcrypt',
       version = '1.2',
       description = 'The Unix password crypt function.',
       author = 'Carey Evans',
       author_email = 'careye@spamcop.net',
       url = 'http://home.clear.net.nz/pages/c.evans/sw/',
       licence = 'BSD',
       long_description = """\
A pure Python implementation of the Unix DES password crypt function,
based on Eric Young's fcrypt.c.  It works with any version of Python
from version 1.5 or higher, and because it's pure Python it doesn't
need a C compiler to install it.""",

       py_modules = ['fcrypt'] )
