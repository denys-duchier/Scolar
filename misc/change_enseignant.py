#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""Change un identifiant d'enseignant (pour corriger une erreur, typiquement un doublon)

(à lancer en tant qu'utilisateur postgres)
Emmanuel Viennet, 2007 - 2014
"""

import pdb, os, sys
import psycopg2


if len(sys.argv) != 4:
    print 'Usage: %s database ancien_utilisateur nouvel_utilisateur' % sys.argv[0]
    print 'Exemple: change_enseignant.py SCOGEII toto tata'
    sys.exit(1)

dbname = sys.argv[1]
OLD_ID = sys.argv[2]
NEW_ID = sys.argv[3]

DBCNXSTRING = 'dbname=%s' % dbname

# Confirmation
ans = raw_input("Remplacer le l'utilisateur %s par %s dans toute la base du departement %s ?"
                % (OLD_ID, NEW_ID, dbname)).strip()
if not ans or ans[0].lower() not in 'oOyY':
    print 'annulation'
    sys.exit(-1)


cnx = psycopg2.connect( DBCNXSTRING )

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
    cursor.execute(req % (table, attr, attr), args)
    print 'table %s:  %s' % (table, cursor.statusmessage)

cnx.commit()



