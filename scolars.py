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

# XXXXXXXXX HACK: zope 2.7.7 bug turaround ?
import locale
locale.setlocale(locale.LC_ALL, ('en_US', 'ISO8859-15') )

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
    convert_null_outputs_to_empty=True )

identite_create = _identiteEditor.create
identite_delete = _identiteEditor.delete
identite_list   = _identiteEditor.list
identite_edit   = _identiteEditor.edit

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
      'formsemestre_id', 'event_type' ),
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
