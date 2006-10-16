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

""" Acces donnees etudiants
"""

import pdb,os,sys

from notesdb import *
from TrivialFormulator import TrivialFormulator
import safehtml
from scolog import logdb
from notes_table import *

# XXXXXXXXX HACK: zope 2.7.7 bug turaround ?
import locale
locale.setlocale(locale.LC_ALL, ('en_US', 'ISO8859-15') )


abbrvmonthsnames = [ 'Jan ', 'Fev ', 'Mars', 'Avr ', 'Mai ', 'Juin', 'Jul ',
                     'Aout', 'Sept', 'Oct ', 'Nov ', 'Dec ' ]

monthsnames = [ 'janvier', 'février', 'mars', 'avril', 'mai', 'juin',
                'juillet', 'aout', 'septembre', 'octobre', 'novembre',
                'décembre' ]                

def force_uppercase(s):
    if s:
        s = s.upper()
    return s

def format_prenom(s):
    "formatte prenom etudiant pour affichage"
    locale.setlocale(locale.LC_ALL, ('en_US', 'ISO8859-15') )
    
    frags = s.split()
    r = []
    for frag in frags:
        fs = frag.split('-')
        r.append( '-'.join( [ x.lower().capitalize() for x in fs ] ) )
    return ' '.join(r)


#    s = ' '.join( [ x.lower().capitalize() for x in frags ] )
#    frags = s.split('-')
#    return '-'.join( [ x.lower().capitalize() for x in frags ] )

def format_nom(s):
    return s.upper()

def format_sexe(sexe):
    sexe = sexe.lower()
    if sexe == 'mr':
        return 'M.'
    else:
        return sexe.capitalize()

def format_lycee(nomlycee):
    nomlycee = nomlycee.strip()
    s = nomlycee.lower()
    if s[:5] == 'lycee' or s[:5] == 'lycée':
        return nomlycee[5:]
    else:
        return nomlycee

def format_telephone(n):
    if n is None:
        return ''
    if len(n) < 7:
        return n
    else:
        n = n.replace(' ','').replace('.','')
        i = 0
        r = ''
        j = len(n) - 1
        while j >= 0:
            r = n[j] + r
            if i % 2 == 1 and j != 0:
                r = ' ' + r
            i += 1
            j -= 1
        if len(r) == 13 and r[0] != '0':
            r = '0' + r
        return r

def format_pays(s):
    "laisse le pays seulement si != FRANCE"
    if s.upper() != 'FRANCE':
        return s
    else:
        return ''

PIVOT_YEAR = 70

def pivot_year(y):
    if y == '' or y is None:
        return None
    y = int(y)
    if y >= 0 and y < 100:
        if y < PIVOT_YEAR:
            y = y + 2000
        else:
            y = y + 1900
    return y


_identiteEditor = EditableTable(
    'identite',
    'etudid',
    ('etudid','nom','prenom','sexe','annee_naissance','nationalite','foto'),
    sortkey = 'nom',
    input_formators = { 'nom' : force_uppercase,
                        'prenom' : force_uppercase,
                        'sexe' : force_uppercase,
                        'annee_naissance' : pivot_year,
                        },
    convert_null_outputs_to_empty=True,
    allow_set_id = True # car on specifie le code Apogee a la creation
    )

identite_delete = _identiteEditor.delete
identite_list   = _identiteEditor.list
identite_edit   = _identiteEditor.edit

def identite_create( cnx, args ):
    "check unique etudid, then create"
    etudid = args['etudid']
    r = identite_list(cnx, {'etudid' : etudid})
    if r:
        raise ScoValueError('Code identifiant (INE) déjà utilisé ! (%s)' % etudid)
    return _identiteEditor.create(cnx, args)

# --------
# Note: la table adresse n'est pas dans dans la table "identite"
#       car on prevoit plusieurs adresses par etudiant (ie domicile, entreprise)

_adresseEditor = EditableTable(
    'adresse',
    'adresse_id',
    ( 'adresse_id','etudid','email',
      'domicile','codepostaldomicile','villedomicile','paysdomicile',
      'telephone','telephonemobile','fax',
      'typeadresse','entreprise_id','description' ),
    convert_null_outputs_to_empty=True )

adresse_create = _adresseEditor.create
adresse_delete = _adresseEditor.delete
adresse_list   = _adresseEditor.list
adresse_edit   = _adresseEditor.edit

def getEmail(cnx,etudid):
    "get email etudiant (si plusieurs adresses, prend le premier non null"
    adrs = adresse_list(cnx, {'etudid' : etudid})
    for adr in adrs:
        if adr['email']:
            return adr['email']
    return ''

# ---------
_admissionEditor = EditableTable(
    'admissions',
    'adm_id',
    ( 'adm_id', 'etudid',
      'annee', 'bac', 'specialite', 'annee_bac', 
      'math', 'physique', 'anglais', 'francais',  
      'rang', 'qualite', 'rapporteur',
      'decision', 'score', 'commentaire',
      'nomlycee', 'villelycee' ),
    input_formators = { 'annee' : pivot_year,
                        'bac' : force_uppercase,
                        'specialite' : force_uppercase,
                        'annee_bac' : pivot_year,
                        },
    convert_null_outputs_to_empty=True )

admission_create = _admissionEditor.create
admission_delete = _admissionEditor.delete
admission_list   = _admissionEditor.list
admission_edit   = _admissionEditor.edit

# Edition simultanee de identite et admission
class EtudIdentEditor:
    def create(self, cnx, args ):
        etudid = identite_create( cnx, args )        
        args['etudid'] = etudid
        admission_create( cnx, args )
        return etudid
    
    def list(self, *args, **kw ):
        R = identite_list( *args, **kw )
        Ra = admission_list( *args, **kw )
        #print len(R), len(Ra)
        # merge: add admission fields to identite
        A = {}
        for r in Ra:
            A[r['etudid']] = r
        res = []
        for i in R:
            if A.has_key(i['etudid']):
                # merge
                res.append(i)
                res[-1].update(A[i['etudid']])
            else: # pas d'etudiant trouve
                #print "*** pas d'info admission pour %s" % str(i)
                pass
        # tri par nom
        res.sort( lambda x,y: cmp(x['nom'],y['nom']) )
        return res
    def edit(self, uid, args):
        identite_edit( uid, args )
        admission_edit( uid, args )

_etudidentEditor = EtudIdentEditor()
etudident_list   = _etudidentEditor.list
etudident_edit   = _etudidentEditor.edit
etudident_create = _etudidentEditor.create

# ---------- "EVENTS"
_scolar_eventsEditor = EditableTable(
    'scolar_events',
    'event_id',
    ( 'event_id','etudid','event_date',
      'formsemestre_id', 'ue_id', 'event_type' ),
    sortkey = 'event_date',
    convert_null_outputs_to_empty=True,
    output_formators = { 'event_date' : DateISOtoDMY },
    input_formators  = { 'event_date' : DateDMYtoISO }
    )

#scolar_events_create = _scolar_eventsEditor.create
scolar_events_delete = _scolar_eventsEditor.delete
scolar_events_list   = _scolar_eventsEditor.list
scolar_events_edit   = _scolar_eventsEditor.edit

def scolar_events_create( cnx, args ):
    # several "events" may share the same values
    _scolar_eventsEditor.create( cnx, args, has_uniq_values=False )

def scolar_get_validated( cnx, etudid, formsemestre_id ):
    """None ou event si semestre valide, echec, liste de ue_id valides."""
    events = scolar_events_list(
        cnx, args={'etudid':etudid,
                   'formsemestre_id':formsemestre_id,
                   'event_type' : 'VALID_SEM' })
    if events:
        evt_valid_sem = events[0]
    else:
        evt_valid_sem = None
    events = scolar_events_list(
        cnx, args={'etudid':etudid,
                   'formsemestre_id':formsemestre_id,
                   'event_type' : 'ECHEC_SEM' })
    if events:
        evt_echec_sem = events[0]
    else:
        evt_echec_sem = None
    events = scolar_events_list(
        cnx, args={'etudid':etudid,
                   'formsemestre_id':formsemestre_id,
                   'event_type' : 'VALID_UE' })
    #uelist = [ evt['ue_id'] for evt in events ]
    return evt_valid_sem, evt_echec_sem, events


def scolar_validate_sem( cnx, etudid, formsemestre_id, valid=True,
                         event_date=None, REQUEST=None ):
    """Si valid==True, valide ce semestre, sinon echec"""
    logdb(REQUEST,cnx,method='valid_sem (valid=%s)'%valid, etudid=etudid)
    log('scolar_validate_sem: etudid=%s formsemestre_id=%s valid=%s'
        % (etudid, formsemestre_id, valid))
    if valid:
        code = 'VALID_SEM'
    else:
        code = 'ECHEC_SEM'
    # verifie si deja events et les supprime
    events = scolar_events_list(
        cnx, args={'etudid':etudid,
                   'formsemestre_id':formsemestre_id,
                   'event_type' : 'VALID_SEM' })
    for event in events:
        log('scolar_validate_sem: deleting previous VALID_SEM')
        scolar_events_delete(cnx, event['event_id'])

    events = scolar_events_list(
        cnx, args={'etudid':etudid,
                   'formsemestre_id':formsemestre_id,
                   'event_type' : 'ECHEC_SEM' })
    for event in events:
        log('scolar_validate_sem: deleting previous ECHEC_SEM')
        scolar_events_delete(cnx, event['event_id'])
    
    # nouvel event
    scolar_events_create( cnx, args = {
        'etudid' : etudid,
        'event_date' : event_date,
        'formsemestre_id' : formsemestre_id,
        'event_type' : code } )

def scolar_validate_ues( znotes, cnx, etudid, formsemestre_id,
                         ue_ids=[],
                         event_date=None, REQUEST=None,
                         suppress_previously_validated=True ):
    """Valide ces UE (attention: supprime les UE deja validees !)
    Ne valide jamais les UE de type SPORT
    """
    logdb(REQUEST,cnx,method='valid_ue', etudid=etudid)
    log('scolar_validate_ues: etudid=%s formsemestre_id=%s ue_ids=%s'
        % (etudid, formsemestre_id, str(ue_ids)))
    # verifie si deja events et les supprime
    if suppress_previously_validated:
        events = scolar_events_list(
            cnx, args={'etudid':etudid, 
                       'formsemestre_id':formsemestre_id,
                       'event_type' : 'VALID_UE' })
        for event in events:
            log('scolar_validate_ues: deleting previous VALID_UE (%s)' % event['ue_id'])
            scolar_events_delete(cnx, event['event_id'])
    #
    for ue_id in ue_ids:
        ue = znotes.do_ue_list( args={ 'ue_id' : ue_id } )[0]
        if ue['type'] == UE_SPORT:
            continue # skip UE sport
        scolar_events_create( cnx, args = {
            'etudid' : etudid,
            'event_date' : event_date,
            'formsemestre_id' : formsemestre_id,
            'ue_id' : ue_id,
            'event_type' : 'VALID_UE' } )


# --------
_etud_annotationsEditor = EditableTable(
    'etud_annotations',
    'id',
    ('id', 'date', 'etudid', 'author', 'comment',
     'zope_authenticated_user', 'zope_remote_addr' ),
    sortkey = 'date desc',
    convert_null_outputs_to_empty=True,
    output_formators = { 'comment' : safehtml.HTML2SafeHTML,
                         'date' : DateISOtoDMY }
    )


etud_annotations_create = _etud_annotationsEditor.create
etud_annotations_delete = _etud_annotationsEditor.delete
etud_annotations_list   = _etud_annotationsEditor.list
etud_annotations_edit   = _etud_annotationsEditor.edit

# -------- APPRECIATIONS (sur bulletins) -------------------
# Les appreciations sont dans la table postgres notes_appreciations
_appreciationsEditor = EditableTable(
    'notes_appreciations',
    'id',
    ('id', 'date', 'etudid', 'formsemestre_id', 'author', 'comment',
     'zope_authenticated_user', 'zope_remote_addr' ),
    sortkey = 'date desc',
    convert_null_outputs_to_empty=True,
    output_formators = { 'comment' : safehtml.HTML2SafeHTML,
                         'date' : DateISOtoDMY }
    )

appreciations_create = _appreciationsEditor.create
appreciations_delete = _appreciationsEditor.delete
appreciations_list   = _appreciationsEditor.list
appreciations_edit   = _appreciationsEditor.edit

