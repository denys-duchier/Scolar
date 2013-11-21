#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Import direct des notes

(utilise pour JCD Nov 2006)

Les evaluations doivent avoir été créées au préalable.

On part d'un fichier CSV avec:
EVALUATION_ID   ETUDID    NOTE_VALUE
"""

import pdb,os,sys,psycopg
import csv

CSVFILENAME = '/tmp/notesjcd.csv'

DBCNXSTRING = 'XXX'

COMMENT = "notes importees de l'ancien logiciel"

# Constantes copiees de ../notes_table
NOTES_MIN = 0.       # valeur minimale admise pour une note
NOTES_MAX = 100.
NOTES_NEUTRALISE=-1000.

cnx = psycopg.connect( DBCNXSTRING )
cursor = cnx.cursor()

reader = csv.reader(open( CSVFILENAME, "rb"), delimiter='\t')
reader.next() # skip titles
n = 0
for row in reader:
    evaluation_id = row[0]
    etudid = row[1]
    value = row[2].replace(',','.').strip().upper()
    try:
        value = float(value)
    except:
        if value == 'ABS':
            value = 0
        elif value[:3] == 'EXC' or value[:3] == 'NEU':
            value = NOTES_NEUTRALISE
        else:
            raise ValueError('invalid value: %s' % value)
    n += 1
    cursor.execute("insert into notes_notes (etudid, evaluation_id, value, comment, uid) values (%(etudid)s,%(evaluation_id)s,%(value)s,%(comment)s,%(uid)s)",
                   {'etudid':etudid, 'evaluation_id' : evaluation_id,
                    'value' : value,
                    'comment' : COMMENT,
                    'uid' : 'admin' } )

cnx.commit()

print 'inserted %d values' % n
 insert into scolar_news values (authenticated_user, type, object, text, url)

