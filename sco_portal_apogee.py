# -*- mode: python -*-
# -*- coding: iso8859-15 -*-

##############################################################################
#
# Gestion scolarite IUT
#
# Copyright (c) 2001 - 2006 Emmanuel Viennet.  All rights reserved.
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA  02111-1307  USA
#
#   Emmanuel Viennet      emmanuel.viennet@viennet.net
#
##############################################################################

"""Liaison avec le portail ENT (qui donne accès aux infos Apogée)
"""

PORTAL_URL='https://portail.cevif.univ-paris13.fr/'

import urllib, urllib2, xml

from notes_log import log
from sco_exceptions import *
from sco_utils import *
from SuppressAccents import suppression_diacritics

def get_inscrits_etape(code_etape):
    """Liste des inscrits à une étape Apogée
    Result = list of dicts
    """
    req = PORTAL_URL + 'getEtud.php?' + urllib.urlencode((('etape', code_etape),))
    doc = query_portal(req)
    return xml_to_list_of_dicts(doc)

def query_apogee_portal(nom, prenom):
    """Recupere les infos sur les etudiants nommés
    (nom et prenom matchent des parties de noms)
    """
    req = PORTAL_URL + 'getEtud.php?' + urllib.urlencode((('nom', nom), ('prenom', prenom)))
    doc = query_portal(req)
    return xml_to_list_of_dicts(doc)

def query_portal(req):
    try:
        f = urllib2.urlopen(req) # XXX ajouter timeout (en Python 2.6 !)
    except:
        log("query_apogee_portal: can't connect to Apogee portal")
        return []
    return f.read()

def xml_to_list_of_dicts(doc):
    dom = xml.dom.minidom.parseString(doc)
    infos = []
    try:
        if dom.childNodes[0].nodeName != u'etudiants':
            raise ValueError
        etudiants = dom.getElementsByTagName('etudiant')
        for etudiant in etudiants:
            d = {}
            # recupere toutes les valeurs <valeur>XXX</valeur>
            for e in etudiant.childNodes:
                if e.nodeType == e.ELEMENT_NODE:
                    d[str(e.nodeName)] = e.childNodes[0].nodeValue.encode(SCO_ENCODING)
            infos.append(d)
    except:
        raise ValueError('invalid XML response from getEtud Web Service\n%s' % req)
    return infos


def get_infos_apogee_allaccents(nom, prenom):
    "essai recup infos avec differents codages des accents"
    if nom:
        unom = unicode(nom, SCO_ENCODING)
        nom_noaccents = str(suppression_diacritics(unom))
        nom_utf8 = unom.encode('utf-8')            
    else:
        nom_noaccents = nom
        nom_utf8 = nom
        
    if prenom:
        uprenom = unicode(prenom, SCO_ENCODING)
        prenom_noaccents = str(suppression_diacritics(uprenom))
        prenom_utf8 = uprenom.encode('utf-8')
    else:
        prenom_noaccents = prenom
        prenom_utf8 = prenom
    
    # avec accents
    infos = query_apogee_portal(nom, prenom)
    # sans accents
    if nom != nom_noaccents or prenom != prenom_noaccents:
        infos += query_apogee_portal(nom_noaccents,prenom_noaccents)
    # avec accents en UTF-8
    if nom_utf8 != nom_noaccents or prenom_utf8 != prenom_noaccents:
        infos += query_apogee_portal(nom_utf8,prenom_utf8)
    return infos


def get_infos_apogee(nom, prenom):
    """recupere les codes Apogee en utilisant le web service CRIT
    """
    if (not nom) and (not prenom):
        return []
    # essaie plusieurs codages: tirets, accents
    infos = get_infos_apogee_allaccents(nom, prenom)
    nom_st = nom.replace('-', ' ')
    prenom_st = prenom.replace('-', ' ')
    if nom_st != nom or prenom_st != prenom:
        infos += get_infos_apogee_allaccents(nom_st, prenom_st)
    # si pas de match et nom ou prenom composé, essaie en coupant
    if not infos:
        nom1 = nom.split()[0]
        prenom1 = prenom.split()[0]
        if nom != nom1 or prenom != prenom1:
            infos += get_infos_apogee_allaccents(nom1, prenom1)
    return infos
