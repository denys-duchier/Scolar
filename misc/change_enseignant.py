#!/usr/bin/env python

"""Change un identifiant d'enseignant (pour corriger une erreur ?)


Emmanuel Viennet, 2007
"""

import pdb,os,sys,psycopg


DBCNXSTRING = 'host=localhost user=XXX dbname=XXX password=XXX'

OLD_ID = 'CLARC'
NEW_ID = 'larcher'

cnx = psycopg.connect( DBCNXSTRING )

cursor = cnx.cursor()
req = "update %s set %s=%%(new_id)s where %s=%%(old_id)s"
args = { 'old_id' : OLD_ID, 'new_id' : NEW_ID }

tables_attr = {
    'notes_formsemestre' : 'responsable_id',
    'entreprise_contact' : 'enseignant',
    'admissions' : 'rapporteur',
    'notes_moduleimpl' : 'responsable_id',
    'notes_modules_enseignants' : 'ens_id',
    'notes_notes' : 'uid',
    'notes_notes_log' : 'uid',
    'notes_appreciations' : 'author',           
    }

for (table, attr) in tables_attr.items():
    cursor.execute(req, args)
    print 'table %s:  %s' % (table, cursor.statusmessage)

cnx.commit()



