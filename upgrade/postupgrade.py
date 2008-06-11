#!/usr/bin/env python

"""
ScoDoc post-upgrade script.

This script is runned by upgrade.sh after each SVN update.

Runned as "root" with Zope shutted down and postgresql up.

E. Viennet, june 2008
"""

import sys

sys.path.append('..')

