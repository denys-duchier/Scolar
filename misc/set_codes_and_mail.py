#!/usr/bin/env python

"""Ajout des codes NIP et INE, et du mail, a posteriori
   depuis un fichier CSV (fourni par CRI/Apogee)
"""

import pdb,os,sys,psycopg
import csv


CSVFILENAME = '/tmp/viennet-20061025-1033.csv'

#DBCNXSTRING = 'host=localhost user=scogea dbname=SCOGEA password=R&Totoro'
DBCNXSTRING = 'host=localhost user=zopeuser dbname=SCOGTR password=R&Totoro'

idx_dept = 0
idx_prenom = 1
idx_nom = 2
idx_nip = 3
idx_ine = 4
idx_mail = 6

DO_IT =  False
#DO_IT = True

# en general, pas d'accents dans le CSV
SCO_ENCODING = 'iso8859-15'
from SuppressAccents import suppression_diacritics
def suppr_acc_and_ponct(s):
    s = s.replace('-', ' ')    
    return str(suppression_diacritics( unicode(s, SCO_ENCODING) ))

def make_key(nom, prenom):
    nom = suppr_acc_and_ponct(nom).upper()
    prenom = suppr_acc_and_ponct(prenom).upper()
    return nom + ' ' + prenom[:4]

reader = csv.reader(open( CSVFILENAME, "rb"))
noms = {}
for row in reader:
    key = make_key( row[idx_nom], row[idx_prenom])
    if noms.has_key(key):
        raise ValueError, 'duplicate key: %s' % key
    noms[key] = row

cnx = psycopg.connect( DBCNXSTRING )

def fix_email(etudid, email): # ne change que s'il n'y a pas deja un mail
    cursor = cnx.cursor()
    cursor.execute("select email from adresse where etudid=%(etudid)s",
                   { 'etudid' : etudid } )
    r = cursor.fetchone()
    if not r:
        # pas d'email, insere le notre
        if DO_IT:
            cursor.execute("insert into adresse (etudid, email) values (%(etudid)s, %(email)s", { 'etudid' : etudid, 'email' : email })
        return True
    elif not r[0]:
        # email vide, met a jour avec le notre
        if DO_IT:
            cursor.execute("update adresse set email=%(email)s where etudid=%(etudid)s",
                           { 'etudid' : etudid, 'email' : email })
        return True
    return False

def fix_codes(etudid, ine, nip): # change toujours
    cursor = cnx.cursor()
    cursor.execute("select code_ine, code_nip from identite where etudid=%(etudid)s",
                   { 'etudid' : etudid } )
    r = cursor.fetchone()
    if not r:
        raise ValueError('invalid etudid: %s' % etudid)
    print "update identite set code_ine=%(ine)s, code_nip=%(nip)s where etudid=%(etudid)s" % { 'etudid' : etudid, 'ine':ine, 'nip':nip }
    if DO_IT:
        cursor.execute("update identite set code_ine=%(ine)s, code_nip=%(nip)s where etudid=%(etudid)s",
                       { 'etudid' : etudid, 'ine':ine, 'nip':nip })
    return True

cursor = cnx.cursor()
cursor.execute("select * from identite i, notes_formsemestre_inscription ins where i.etudid = ins.etudid and ins.formsemestre_id = 'SEM2567'")
R = cursor.dictfetchall()

nok=0
for e in R:
    key = make_key(e['nom'], e['prenom'])
    if not noms.has_key(key):
        print '** no match for %s (%s)' % (key, e['etudid'])
    else:
        info = noms[key]
        print '* %s %s: ine=%s   %s' % (key, e['prenom'], info[idx_ine], info[idx_prenom])
        nok+=1
        email = info[idx_mail] + '@iutv.univ-paris13.fr' 
        if fix_email( e['etudid'], email ):
            print '\temail set to %s' % email
        ine, nip = info[idx_ine], info[idx_nip]
        if fix_codes(e['etudid'], ine, nip):
            print '\tcodes set: ine=%s, nip=%s' % (ine, nip)

cnx.commit()

print '%d etudiants, %d ok' % (len(R), nok)
