#!/usr/bin/env python

"""
ScoDoc post-upgrade script: databases housekeeping

This script is runned by upgrade.sh after each SVN update.

Runned as "www-data" with Zope shutted down and postgresql up.


Useful to update databse schema (eg add new tables or columns to 
existing scodoc instances).

E. Viennet, june 2008
"""

from scodocutils import *

for dept in get_depts():
    log('\nChecking database for dept %s' % dept)
    cnx = psycopg.connect( get_dept_cnx_str(dept) )
    cursor = cnx.cursor()
    # Apply upgrades:
    
    # SVN 564 -> 565
    # add resp_can_edit to notes_formsemestre:
    check_field(cnx, 'notes_formsemestre', 'resp_can_edit',
                ['alter table notes_formsemestre add column resp_can_edit int default 0',
                 'update notes_formsemestre set resp_can_edit=0'])

# The end.
sys.exit(0)
