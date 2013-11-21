#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Affiche nombre d'inscriptions aux semestres pour chaque etudiant

   et supprime les etudiants jamais inscrits ayant un homonyme exact
   (erreur passage GEA, fev 2007)
"""

import pdb,os,sys,psycopg
import csv

DBCNXSTRING = 'host=localhost user=scogea dbname=SCOXXXX password=XXXXX'

SCO_ENCODING = 'utf-8'

cnx = psycopg.connect( DBCNXSTRING )

cursor = cnx.cursor()
cursor.execute("select * from identite i order by nom")
R = cursor.dictfetchall()

nzero = 0
nhomonoins = 0
print 'etudid, nom, prenom, nb_inscriptions'
for e in R:
    cursor.execute("select count(*) from notes_formsemestre_inscription where etudid=%(etudid)s", { 'etudid' : e['etudid'] } )
    nbins = cursor.fetchone()[0]
    if nbins == 0:
        nzero += 1
        # recherche homonyme
        cursor.execute("select * from identite i where nom=%(nom)s and prenom=%(prenom)s", e )
        H = cursor.dictfetchall()
        if len(H) == 2:
            nhomonoins += 1            
            print e['etudid'], e['nom'], e['prenom'], nbins
            # etudiant non inscrit ayant un homonyme exact:
            #  il doit etre supprimé !!!            
            #cursor.execute("delete from admissions where etudid=%(etudid)s", e)
            #cursor.execute("delete from identite where etudid=%(etudid)s", e)

cnx.commit()

print '= %d etudiants, %d jamais inscrits, %d avec homo' % (len(R), nzero, nhomonoins)
