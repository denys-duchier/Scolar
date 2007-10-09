#!/usr/bin/env python

"""Ajout des photos a posteriori
   depuis un fichier CSV (avec code (etudid ou NIP) et photo)
"""

import pdb,os,sys,psycopg
import csv


CSVFILENAME = '/tmp/S1.csv'
#CSVFILENAME = '/tmp/ferhan2.csv'

DBCNXSTRING = 'host=localhost user=scoinfo dbname=SCOXXX password=XXX'

idx_nip = 0
idx_photo = 1

code_type = 'etudid'

DO_IT =  False
#DO_IT = True

# en general, pas d'accents dans le CSV
SCO_ENCODING = 'iso8859-15'

reader = csv.reader(open( CSVFILENAME, "rb"), delimiter='\t')
photos = {}
for row in reader:
    if row[0][0] != '#':
        nip = row[idx_nip]
        if photos.has_key(nip):
            raise ValueError, 'duplicate key: %s' % nip
        if row[idx_photo]:
            s = row[idx_photo]
            s = s.split('.')[0] + '.h90.jpg'
            photos[nip] = s

cnx = psycopg.connect( DBCNXSTRING )


def set_photo(nip, photo): # change toujours
    cursor = cnx.cursor()
    print "update identite set foto=%(foto)s where %(code_type)s=%(code)s" % { 'code_type' : code_type, 'code':nip, 'foto' : photo }
    if DO_IT:
        r = "update identite set foto=%%(foto)s where %s=%%(code)s" % code_type
        cursor.execute( r, { 'code':nip, 'foto' : photo })
    return True



for nip in photos.keys():
    set_photo(nip, photos[nip])

cnx.commit()

print '%d etudiants changed' % len(photos)

