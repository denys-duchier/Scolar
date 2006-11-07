#!/usr/bin/env python

"""Ajout des annees naissances 
"""

import pdb,os,sys,psycopg
import csv


CSVFILENAME = '/tmp/nipan.csv'

DBCNXSTRING = 'host=localhost user= dbname= password='

#DO_IT =  False
DO_IT = True


reader = csv.reader(open( CSVFILENAME, "rb"))
reader.next() # skip titles

L = []
for row in reader:
    L.append( (row[0], row[1]) )
    
cnx = psycopg.connect( DBCNXSTRING )

cursor = cnx.cursor()
for (nip, annee_naissance) in L:    
    req = "update identite set annee_naissance=%(a)s where code_nip=%(nip)s"
    args = { 'nip' : nip, 'a' : annee_naissance }
    if DO_IT:
        cursor.execute(req,args)
        print cursor.statusmessage
    else:
        print req % args

cnx.commit()



