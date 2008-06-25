#!/usr/bin/env python

"""Change un etudid

Suite a de fausses manips, il arrive que l'on est des "doublons":
le m�me �tudiant est enregistr� sous deux "etudid" diff�rents !

Normalement, l'utilisation d'imports bas�s sur le code NIP (Apog�e)
�vite le probl�me (qui ne se pose qu'en cas d'inscriptions manuelles
mal g�r�es).

Ce script permet de changer un etudid, typiquement pour associer � un
etudiant le code d'un autre �tudiant (son doublon).

Ne traite que les inscriptions, les notes, absences, annotations, mais
�videmment pas les tables uniques (identit�, adresse, admission).

Emmanuel Viennet, 2007
"""

import pdb,os,sys,psycopg


DBCNXSTRING = 'host=localhost user=XXX dbname=XXX password=XXX'

OLD_ETUDID = 'EID1512'
NEW_ETUDID = '10500686'

cnx = psycopg.connect( DBCNXSTRING )

cursor = cnx.cursor()
req = "update %s set etudid=%%(new_etudid)s where etudid=%%(old_etudid)s"
args = { 'old_etudid' : OLD_ETUDID, 'new_etudid' : NEW_ETUDID }

tables = ( 'absences',
           'scolog',
           'etud_annotations',
           'entreprise_contact',
           'notes_formsemestre_inscription',
           'notes_moduleimpl_inscription',
           'notes_notes', 'notes_notes_log',
           'scolar_events',
           'scolar_formsemestre_validation',
           'scolar_autorisation_inscription',
           'notes_appreciations',
           # nouvelles absences
           #'abs_absences',
           #'abs_presences',
           #'abs_justifs',
           )

for table in tables:
    cursor.execute(req % table, args)
    print 'table %s:  %s' % (table, cursor.statusmessage)

cnx.commit()



