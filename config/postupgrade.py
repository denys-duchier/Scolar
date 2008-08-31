#!/usr/bin/env python

"""
ScoDoc post-upgrade script.

This script is runned by upgrade.sh after each SVN update.

Runned as "root" with Zope shutted down and postgresql up.

E. Viennet, june 2008
"""

from scodocutils import *


if os.getuid() != 0:
    log('postupgrade.py: must be run as root')
    sys.exit(1)

# ---

# add here actions to perform...

# ---
sys.exit(0)
