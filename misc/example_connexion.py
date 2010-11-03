#!/usr/bin/env python

"""Exemple connexion sur ScoDoc et utilisation de l'API
"""

import urllib, urllib2

#BASEURL = 'https://notes.iutv.univ-paris13.fr/ScoDoc/RT/Scolarite'
BASEURL = 'https://localhost/ScoDoc/RT/Scolarite'

values = {'__ac_name' : 'viennet',
          '__ac_password' : 'xxxx',
          }

# Configure memorisation des cookies:
opener = urllib2.build_opener(urllib2.HTTPCookieProcessor())
urllib2.install_opener(opener)

data = urllib.urlencode(values)

req = urllib2.Request(BASEURL, data) # this is a POST http request
response = urllib2.urlopen(req)

# --- Use API

req = urllib2.Request(BASEURL+'/Notes/formation_list' )
response = urllib2.urlopen(req)
