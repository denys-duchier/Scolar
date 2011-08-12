#!/usr/bin/env python
# -*- mode: python -*-
# -*- coding: iso8859-15 -*-

"""Exemple connexion sur ScoDoc et utilisation de l'API
"""

import urllib, urllib2

#BASEURL = 'https://notes.iutv.univ-paris13.fr/ScoDoc/RT/Scolarite'
#BASEURL = 'https://localhost/ScoDoc/RT/Scolarite'
BASEURL = 'https://scodoc.viennet.net/ScoDoc/RT/Scolarite'

values = {'__ac_name' : 'XXXviennet',
          '__ac_password' : 'xxxx',
          }

# Configure memorisation des cookies:
opener = urllib2.build_opener(urllib2.HTTPCookieProcessor())
urllib2.install_opener(opener)

data = urllib.urlencode(values)

req = urllib2.Request(BASEURL, data) # this is a POST http request
response = urllib2.urlopen(req)

# --- Use API

# Affiche la liste des formations en format XML
req = urllib2.Request(BASEURL+'/Notes/formation_list?format=xml' )
response = urllib2.urlopen(req)
print response.read()[:100] # limite aux 100 premiers caracteres...

# Recupere la liste de tous les semestres:
req = urllib2.Request(BASEURL+'/Notes/formsemestre_list?format=json') # format json
response = urllib2.urlopen(req)
js_data = response.read()

# Plus amusant: va retrouver le bulletin de notes du premier etudiant (au hasard donc) du premier semestre (au hasard aussi)
try:
    import json # Attention: ceci demande Python >= 2.6
except:
    import simplejson as json # python2.4 with simplejson installed

data = json.loads(js_data) # decode la reponse JSON
if not data:
    print "Aucun semestre !"
else:
    formsemestre_id = str(data[0]['formsemestre_id'])
    # Obtient la liste des groupes:
    req = urllib2.Request(BASEURL+'/Notes/formsemestre_partition_list?format=json&formsemestre_id='+formsemestre_id) # format json
    response = urllib2.urlopen(req) 
    js_data = response.read()
    data = json.loads(js_data)
    group_id = data[0]['group'][0]['group_id'] # premier groupe (normalement existe toujours)
    # Liste les étudiants de ce groupe:
    req = urllib2.Request(BASEURL+'/Notes/group_list?format=json&with_codes=1&group_id='+group_id) # format json
    response = urllib2.urlopen(req) 
    js_data = response.read()
    data = json.loads(js_data)
    # Le code du premier étudiant:
    if not data:
        print "pas d'etudiants dans ce semestre !"
    else:
        etudid = data[0]['etudid']
        # Récupère bulletin de notes:
        req = urllib2.Request(BASEURL+'/Notes/formsemestre_bulletinetud?formsemestre_id='+formsemestre_id+'&etudid=' + etudid + '&format=xml') # format XML ici !
        response = urllib2.urlopen(req)
        xml_bulletin = response.read()
        print '----- Bulletin de notes en XML:'
        print xml_bulletin
        # Récupère la moyenne générale:
        import xml.dom.minidom
        doc = xml.dom.minidom.parseString(xml_bulletin)
        moy = doc.getElementsByTagName('note')[0].getAttribute('value') # une chaine unicode
        print '\nMoyenne generale: ', moy
    
