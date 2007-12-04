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

"""Liaison avec le portail ENT (qui donne acc�s aux infos Apog�e)
"""

import urllib, urllib2, xml, xml.dom.minidom

from notes_log import log
from sco_exceptions import *
from sco_utils import *
from SuppressAccents import suppression_diacritics

def get_portal_url(context):
    try:
        return context.portal_url # Zope property
    except:
        log('get_portal_url: undefined property "portal_url"')
        return None

def get_inscrits_etape(context, code_etape, anneeapogee=None):
    """Liste des inscrits � une �tape Apog�e
    Result = list of dicts
    """
    if anneeapogee is None:
        anneeapogee = str(time.localtime()[0])
    
    portal_url = get_portal_url(context)
    if not portal_url:
        return []
    req = portal_url + 'getEtud.php?' + urllib.urlencode((('etape', code_etape),))
    doc = query_portal(req)
    etuds = xml_to_list_of_dicts(doc, req=req)
    # Filtre sur annee inscription Apogee:
    def check_inscription(e):
        if e.has_key('inscription'):
            if e['inscription'] == anneeapogee:
                return True
            else:
                return False
        else:
            log('get_inscrits_etape: pas inscription dans code_etape=%s e=%s' %
                (code_etape, e))
            return False # ??? pas d'annee d'inscription dans la r�ponse
    if anneeapogee != '*':
        etuds = [ e for e in etuds if check_inscription(e) ]
    return etuds

def query_apogee_portal(context, nom, prenom):
    """Recupere les infos sur les etudiants nomm�s
    (nom et prenom matchent des parties de noms)
    """
    portal_url = get_portal_url(context)
    if not portal_url:
        return []
    req = portal_url + 'getEtud.php?' + urllib.urlencode((('nom', nom), ('prenom', prenom)))
    doc = query_portal(req)
    return xml_to_list_of_dicts(doc, req=req)

def query_portal(req):
    log('query_portal: %s' % req )
    try:
        f = urllib2.urlopen(req) # XXX ajouter timeout (en Python 2.6 !)
    except:
        log("query_apogee_portal: can't connect to Apogee portal")
        return []
    return f.read()

def xml_to_list_of_dicts(doc, req=None):
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
                    childs = e.childNodes
                    if len(childs):
                        d[str(e.nodeName)] = childs[0].nodeValue.encode(SCO_ENCODING)
            infos.append(d)
    except:
        log('*** invalid XML response from getEtud Web Service')
        log('req=%s' % req)
        log('doc=%s' % doc)
        raise ValueError('invalid XML response from getEtud Web Service\n%s' % doc)
    return infos


def get_infos_apogee_allaccents(context, nom, prenom):
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
    infos = query_apogee_portal(context, nom, prenom)
    # sans accents
    if nom != nom_noaccents or prenom != prenom_noaccents:
        infos += query_apogee_portal(context, nom_noaccents,prenom_noaccents)
    # avec accents en UTF-8
    if nom_utf8 != nom_noaccents or prenom_utf8 != prenom_noaccents:
        infos += query_apogee_portal(context, nom_utf8,prenom_utf8)
    return infos


def get_infos_apogee(context, nom, prenom):
    """recupere les codes Apogee en utilisant le web service CRIT
    """
    if (not nom) and (not prenom):
        return []
    # essaie plusieurs codages: tirets, accents
    infos = get_infos_apogee_allaccents(context, nom, prenom)
    nom_st = nom.replace('-', ' ')
    prenom_st = prenom.replace('-', ' ')
    if nom_st != nom or prenom_st != prenom:
        infos += get_infos_apogee_allaccents(context, nom_st, prenom_st)
    # si pas de match et nom ou prenom compos�, essaie en coupant
    if not infos:
        nom1 = nom.split()[0]
        prenom1 = prenom.split()[0]
        if nom != nom1 or prenom != prenom1:
            infos += get_infos_apogee_allaccents(context, nom1, prenom1)
    return infos

def get_default_etapes(context):
    """Liste par d�faut: devrait etre lue d'un fichier de config
    """
    filename = context.file_path + '/config/default-etapes.txt'
    log('get_default_etapes: reading %s' % filename )
    f = open( filename )
    etapes = {}
    for line in f.readlines():
        line = line.strip()
        if line and line[0] != '#':
            dept, code, intitule = [ x.strip() for x in line.split(':') ]
            if dept and code:
                if etapes.has_key(dept):
                    etapes[dept][code] = intitule
                else:
                    etapes[dept] = { code : intitule }
    return etapes

def get_etapes_apogee(context):
    """Liste des etapes apogee
    { departement : { code_etape : intitule } }
    Demande la liste au portail, ou si �chec utilise liste
    par d�faut
    """
    portal_url = get_portal_url(context)
    if not portal_url:
        return {}
    req = portal_url + 'getEtapes.php'
    doc = query_portal(req)
    # parser XML
    try:
        dom = xml.dom.minidom.parseString(doc)
        infos = {}
        if dom.childNodes[0].nodeName != u'etapes':
            raise ValueError
        for d in dom.childNodes[0].childNodes:
            if d.nodeType == d.ELEMENT_NODE:
                dept = d.nodeName.encode(SCO_ENCODING)
                for e in d.childNodes:
                    if e.nodeType == e.ELEMENT_NODE:
                        intitule = e.childNodes[0].nodeValue.encode(SCO_ENCODING)
                        code = e.attributes['code'].value.encode(SCO_ENCODING)
                        if infos.has_key(dept):
                            infos[dept][code] = intitule
                        else:
                            infos[dept] = { code : intitule }
    except:
        log('invalid XML response from getEtapes Web Service\n%s' % req)
        return get_default_etapes(context)
    return infos

def get_etapes_apogee_dept(context):
    """Liste des etapes apogee pour ce departement.
    Utilise la propriete 'portal_dept_name' pour identifier le departement.
    Returns [ ( code, intitule) ], ordonnee
    """
    try:
        portal_dept_name = context.portal_dept_name
    except:
        log('get_etapes_apogee_dept: no portal_dept_name property')
        return []
    infos = get_etapes_apogee(context)
    if not infos.has_key(portal_dept_name):
        log("get_etapes_apogee_dept: pas de section '%s' dans la reponse portail" %  portal_dept_name)
        return []
    etapes = infos[portal_dept_name].items()
    etapes.sort() # tri sur le code etape
    return etapes
