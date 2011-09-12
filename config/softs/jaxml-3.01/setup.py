#! /usr/bin/env python
#
# jaxml
# (C) Jerome Alet <alet@librelogiciel.com> 2000-2001
# You're welcome to redistribute this software under the
# terms of the GNU General Public Licence version 2.0
# or, at your option, any higher version.
#
# You can read the complete GNU GPL in the file COPYING
# which should come along with this software, or visit
# the Free Software Foundation's WEB site http://www.fsf.org
#
# $Id: setup.py,v 1.6 2002/04/25 09:08:35 jerome Exp $

from distutils.core import setup

import jaxml

setup(name = "jaxml", version = jaxml.__version__,
      licence = "GNU GPL",
      description = "a Python module to generate XML easily",
      author = "Jerome Alet",
      author_email = "alet@librelogiciel.com",
      url = "http://www.librelogiciel.com/software/",
      py_modules = [ "jaxml" ])

