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

    # SVN 580 -> 581
    # add resp_can_change_ens to notes_formsemestre:
    check_field(cnx, 'notes_formsemestre', 'resp_can_change_ens',
                ['alter table notes_formsemestre add column resp_can_change_ens int default 1',
                 'update notes_formsemestre set resp_can_change_ens=1'])
    
    # SVN 635
    # add bul_show_rangs to to notes_formsemestre:
    check_field(cnx, 'notes_formsemestre', 'bul_show_rangs',
                ['alter table notes_formsemestre add column bul_show_rangs int default 1',
                 'update notes_formsemestre set bul_show_rangs=1'])

    # SVN 651
    # Nouvelles donnees d'admission
    check_field(cnx, 'admissions', 'codelycee',
                ['alter table admissions add column codelycee text',
                 ])
    check_field(cnx, 'admissions', 'codepostallycee',
                ['alter table admissions add column codepostallycee text',
                 ])
    # Add here actions to performs after upgrades:

# The end.
sys.exit(0)
