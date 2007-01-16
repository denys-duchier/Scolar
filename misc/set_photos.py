#!/usr/bin/env python

"""Ajout des photos a posteriori
   depuis un fichier CSV (avec NIP et photo)
"""

import pdb,os,sys,psycopg
import csv


CSVFILENAME = '/tmp/aaa.csv'
#CSVFILENAME = '/tmp/ferhan2.csv'

DBCNXSTRING = 'host=localhost user=scoinfo dbname=SCOINFO password=R&Totoro'

idx_nip = 1
idx_photo = 0


#DO_IT =  False
DO_IT = True

# en general, pas d'accents dans le CSV
SCO_ENCODING = 'iso8859-15'

reader = csv.reader(open( CSVFILENAME, "rb"), delimiter=',')
photos = {}
for row in reader:
    if row[0][0] != '#':
        nip = row[idx_nip]
        if photos.has_key(nip):
            raise ValueError, 'duplicate key: %s' % nip
        photos[nip] = row[idx_photo]

cnx = psycopg.connect( DBCNXSTRING )


def set_photo(nip, photo): # change toujours
    cursor = cnx.cursor()
    print "update identite set foto=%(foto)s where code_nip=%(nip)s" % { 'nip':nip, 'foto' : photo }
    if DO_IT:
        cursor.execute("update identite set foto=%(foto)s where code_nip=%(nip)s", { 'nip':nip, 'foto' : photo })
    return True



for nip in photos.keys():
    set_photo(nip, photos[nip])

cnx.commit()

print '%d etudiants changed' % len(photos)

