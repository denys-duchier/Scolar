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
locale.setlocale(locale.LC_ALL, ('en_US', SCO_ENCODING) )

from email.MIMEMultipart import MIMEMultipart
from email.MIMEText import MIMEText
from email.MIMEBase import MIMEBase
from email.Header import Header
from email import Encoders

abbrvmonthsnames = [ 'Jan ', 'Fev ', 'Mars', 'Avr ', 'Mai ', 'Juin', 'Jul ',
                     'Aout', 'Sept', 'Oct ', 'Nov ', 'Dec ' ]

monthsnames = [ 'janvier', 'f�vrier', 'mars', 'avril', 'mai', 'juin',
                'juillet', 'aout', 'septembre', 'octobre', 'novembre',
                'd�cembre' ]                

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
    if s[:5] == 'lycee' or s[:5] == 'lyc�e':
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
    y = int(round(float(y)))
    if y >= 0 and y < 100:
        if y < PIVOT_YEAR:
            y = y + 2000
        else:
            y = y + 1900
    return y


_identiteEditor = EditableTable(
    'identite',
    'etudid',
    ('etudid','nom','prenom','sexe','annee_naissance','nationalite',
     'foto', 'code_ine', 'code_nip'),
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


def _check_duplicate_code(cnx, args, code_name, context, REQUEST=None):
    etudid = args.get('etudid', None)        
    if args.get(code_name, None):
        etuds = identite_list(cnx, {code_name : args[code_name]})
        log('etuds=%s'%etuds)
        if len(etuds) and (not etudid or (len(etuds) > 1 or etuds[0]['etudid'] != etudid)):
            listh = [] # liste des doubles
            for e in etuds:
                listh.append( """Autre �tudiant: <a href="ficheEtud?etudid=%(etudid)s">%(nom)s %(prenom)s</a>""" % e )
            if etudid:
                OK = 'retour � la fiche �tudiant'
                dest_url='ficheEtud'
                parameters = { 'etudid' : etudid }
            else:
                if args.has_key('tf-submitted'):
                    del args['tf-submitted']
                    OK = 'Continuer'
                    dest_url = 'etudident_create_form'
                    parameters = args
                else:
                    OK = 'Annuler'
                    dest_url = ''
                    parameters = {}
            if context:
                err_page = context.confirmDialog(
                    message="""<h3>Code �tudiant (%s) dupliqu� !</h3>""" % code_name,
                    helpmsg="""Le %s %s est d�j� utilis�: un seul �tudiant peut avoir ce code. V�rifier votre valeur ou supprimer l'autre �tudiant avec cette valeur.<p><ul><li>""" % (code_name, args[code_name])+ '</li><li>'.join(listh) + '</li></ul><p>',
                    OK=OK, dest_url=dest_url, parameters=parameters,
                    REQUEST=REQUEST )
            else:
                err_page = """<h3>Code �tudiant (%s) dupliqu� !</h3>""" % code_name
            raise ScoGenError(err_page)

def identite_edit(cnx, args, context=None, REQUEST=None):
    """Modifie l'identite d'un �tudiant.
    Si context et notification et difference, envoie message notification.
    """
    _check_duplicate_code(cnx, args, 'code_nip', context, REQUEST)
    _check_duplicate_code(cnx, args, 'code_ine', context, REQUEST)
    notify_to = None
    if context:
        try:
            notify_to = context.get_preference('notify_etud_changes_to')
        except:
            pass
    if notify_to:
        # etat AVANT edition pour envoyer diffs
        before = identite_list(cnx, {'etudid':args['etudid']})[0]

    _identiteEditor.edit(cnx, args)

    # Notification du changement par e-mail:
    if notify_to:
        etud = context.getEtudInfo(etudid=args['etudid'],filled=True)[0]
        after = identite_list(cnx, {'etudid':args['etudid']})[0]
        notify_etud_change(context, notify_to, etud, before, after,
                           'Modification identite %(nomprenom)s' % etud)

def identite_create( cnx, args, context=None, REQUEST=None ):
    "check unique etudid, then create"
    _check_duplicate_code(cnx, args, 'code_nip', context, REQUEST)
    _check_duplicate_code(cnx, args, 'code_ine', context, REQUEST)

    if args.has_key('etudid'):
        etudid = args['etudid']
        r = identite_list(cnx, {'etudid' : etudid})
        if r:
            raise ScoValueError('Code identifiant (etudid) d�j� utilis� ! (%s)' % etudid)
    return _identiteEditor.create(cnx, args)


def notify_etud_change(context, email_addr, etud, before, after, subject):
    """Send email notifying changes to etud
    before and after are two dicts, with values before and after the change.
    """
    txt = [
        'Code NIP:' + etud['code_nip'],
        'Genre: ' + etud['sexe'],
        'Nom: ' + etud['nom'],
        'Pr�nom: ' + etud['prenom'],
        'Etudid: ' + etud['etudid'],
        '\n',
        'Changements effectu�s:'
        ]
    n = 0
    for key in after.keys():
        if before[key] != after[key]:
            txt.append('%s: %s' % (key, after[key]) )
            n += 1
    if not n:
        return # pas de changements
    txt = '\n'.join(txt)
    # build mail
    log('notify_etud_change: sending notification to %s' % email_addr)
    msg = MIMEMultipart()
    subj = Header( '[ScoDoc] ' + subject,  SCO_ENCODING )
    msg['Subject'] = subj
    msg['From'] = 'scodoc_noreply'
    msg['To'] = email_addr
    txt = MIMEText( txt, 'plain', SCO_ENCODING )
    msg.attach(txt)
    context.sendEmail(msg)
    

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

def adresse_edit(cnx, args, context=None):
    """Modifie l'adresse d'un �tudiant.
    Si context et notification et difference, envoie message notification.
    """
    notify_to = None
    if context:
        try:
            notify_to = context.get_preference('notify_etud_changes_to')
        except:
            pass
    if notify_to:
        # etat AVANT edition pour envoyer diffs
        before = adresse_list(cnx, {'etudid':args['etudid']})[0]

    _adresseEditor.edit(cnx, args)

    # Notification du changement par e-mail:
    if notify_to:
        etud = context.getEtudInfo(etudid=args['etudid'],filled=True)[0]
        after = adresse_list(cnx, {'etudid':args['etudid']})[0]
        notify_etud_change(context, notify_to, etud, before, after,
                           'Modification adresse %(nomprenom)s' % etud)


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
    def create(self, cnx, args, context=None, REQUEST=None ):
        etudid = identite_create( cnx, args, context, REQUEST )        
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
    def edit(self, cnx, args, context=None, REQUEST=None):
        identite_edit( cnx, args, context, REQUEST )
        admission_edit( cnx, args )

_etudidentEditor = EtudIdentEditor()
etudident_list   = _etudidentEditor.list
etudident_edit   = _etudidentEditor.edit
etudident_create = _etudidentEditor.create

def make_etud_args(etudid=None, REQUEST=None, raise_exc=True):
    """forme args dict pour requete recherche etudiant
    On peut specifier etudid
    ou bien cherche dans REQUEST.form: etudid, code_nip, code_ine
    (dans cet ordre).
    """
    args = None
    if etudid:
        args = {'etudid':etudid}
    elif REQUEST:
        if REQUEST.form.has_key('etudid'):
            args = {'etudid':REQUEST.form['etudid'] }
        elif REQUEST.form.has_key('code_nip'):
            args = { 'code_nip' : REQUEST.form['code_nip'] }
        elif REQUEST.form.has_key('code_ine'):
            args = { 'code_ine' : REQUEST.form['code_ine'] }
    if not args and raise_exc:
        raise ValueError('getEtudInfo: no parameter !')
    return args

# ---------- "EVENTS"
_scolar_eventsEditor = EditableTable(
    'scolar_events',
    'event_id',
    ( 'event_id','etudid','event_date',
      'formsemestre_id', 'ue_id', 'event_type',
      'comp_formsemestre_id' ),
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

