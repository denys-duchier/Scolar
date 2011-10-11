# -*- mode: python -*-
# -*- coding: iso8859-15 -*-

##############################################################################
#
# Gestion scolarite IUT
#
# Copyright (c) 2001 - 2011 Emmanuel Viennet.  All rights reserved.
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

import urllib, urllib2, xml, xml.dom.minidom

from notes_log import log
from sco_utils import *
from SuppressAccents import suppression_diacritics

def has_portal(context):
    "True if we are connected to a portal"
    return get_portal_url(context)

class PortalInterface:
    def __init__(self):
        self.warning = False
    def get_portal_url(self, context):
        "URL of portal"
        portal_url = context.get_preference('portal_url')
        if not self.warning:
            if portal_url:
                log('Portal URL=%s' % portal_url)
            else:
                log('Portal not configured')
            self.warning = True
        return portal_url

_PI = PortalInterface()
get_portal_url = _PI.get_portal_url

def get_inscrits_etape(context, code_etape, anneeapogee=None):
    """Liste des inscrits à une étape Apogée
    Result = list of dicts
    """
    log('get_inscrits_etape: code=%s anneeapogee=%s' % (code_etape, anneeapogee))
    if anneeapogee is None:
        anneeapogee = str(time.localtime()[0])
    
    portal_url = get_portal_url(context)
    if not portal_url:
        return []
    req = portal_url + 'getEtud.php?' + urllib.urlencode((('etape', code_etape),))
    doc = query_portal(req)
    if not doc:
        raise ScoValueError('pas de réponse du portail !')
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
            return False # ??? pas d'annee d'inscription dans la réponse
    if anneeapogee != '*':
        etuds = [ e for e in etuds if check_inscription(e) ]
    return etuds

def query_apogee_portal(context, **args):
    """Recupere les infos sur les etudiants nommés
    args: non, prenom, code_nip
    (nom et prenom matchent des parties de noms)
    """
    portal_url = get_portal_url(context)
    if not portal_url:
        return []
    req = portal_url + 'getEtud.php?' + urllib.urlencode(args.items())
    doc = query_portal(req)
    return xml_to_list_of_dicts(doc, req=req)

def query_portal(req):
    log('query_portal: %s' % req )
    try:
        f = urllib2.urlopen(req) # XXX ajouter timeout (en Python 2.6 !)
    except:
        log("query_apogee_portal: can't connect to Apogee portal")
        return ''
    return f.read()

def xml_to_list_of_dicts(doc, req=None):
    if not doc:
        return []
    try:
        dom = xml.dom.minidom.parseString(doc)
    except:
        # catch bug: log and re-raise exception
        log('xml_to_list_of_dicts: exception in XML parseString\ndoc:\n%s\n(end xml doc)\n' % doc)
        raise
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
    infos = query_apogee_portal(context, nom=nom, prenom=prenom)
    # sans accents
    if nom != nom_noaccents or prenom != prenom_noaccents:
        infos += query_apogee_portal(context, nom=nom_noaccents, prenom=prenom_noaccents)
    # avec accents en UTF-8
    if nom_utf8 != nom_noaccents or prenom_utf8 != prenom_noaccents:
        infos += query_apogee_portal(context, nom=nom_utf8, prenom=prenom_utf8)
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
    # si pas de match et nom ou prenom composé, essaie en coupant
    if not infos:
        if nom:
            nom1 = nom.split()[0]
        else:
            nom1 = nom
        if prenom:
            prenom1 = prenom.split()[0]
        else:
            prenom1 = prenom
        if nom != nom1 or prenom != prenom1:
            infos += get_infos_apogee_allaccents(context, nom1, prenom1)
    return infos

def get_etud_apogee(context, code_nip):
    """Informations à partir du code NIP.
    None si pas d'infos sur cet etudiant.
    Exception si reponse invalide.
    """
    if not code_nip:
        return {}
    portal_url = get_portal_url(context)
    if not portal_url:
        return {}
    req = portal_url + 'getEtud.php?' + urllib.urlencode((('nip', code_nip),))
    doc = query_portal(req)
    d = xml_to_list_of_dicts(doc, req=req)
    if not d:
        return None
    if len(d) > 1:
        raise ValueError('invalid XML response from getEtud Web Service\n%s' % doc)
    return d[0]

def get_default_etapes(context):
    """Liste par défaut: devrait etre lue d'un fichier de config
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
    Demande la liste au portail, ou si échec utilise liste
    par défaut
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
    portal_dept_name = context.get_preference('portal_dept_name')
    log('get_etapes_apogee_dept: portal_dept_name="%s"' % portal_dept_name)

    infos = get_etapes_apogee(context)
    if portal_dept_name and not infos.has_key(portal_dept_name):
        log("get_etapes_apogee_dept: pas de section '%s' dans la reponse portail" %  portal_dept_name)
        return []
    if portal_dept_name:
        etapes = infos[portal_dept_name].items()
    else:
        # prend toutes les etapes
        etapes = []
        for k in infos.keys():
            etapes += infos[k].items()
    
    etapes.sort() # tri sur le code etape
    return etapes

def check_paiement_etuds(context, etuds):
    """Interroge le portail pour vérifier l'état de "paiement"
    et renseigne l'attribut booleen 'paiementinscription' dans chaque etud.
    Seuls les etudiants avec code NIP sont renseignés.
    En sortie, 'paiementinscription' vaut True, False ou None
    """
    # interrogation séquentielle longue...
    for etud in etuds:
        if not etud.has_key('code_nip'):
            etud['paiementinscription'] = None
            etud['paiementinscription_str'] = '(pas de code)'
        else:
            infos = get_etud_apogee(context, etud['code_nip'])
            if infos and infos.has_key('paiementinscription'):
                etud['paiementinscription'] = (infos['paiementinscription'].lower() == 'true')
                if etud['paiementinscription']:
                    etud['paiementinscription_str'] = 'ok'
                else:
                    etud['paiementinscription_str'] = 'Non'
            else:
                etud['paiementinscription'] = None
                etud['paiementinscription_str'] = '?'

    
