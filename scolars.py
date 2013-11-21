# -*- mode: python -*-
# -*- coding: utf-8 -*-

##############################################################################
#
# Gestion scolarite IUT
#
# Copyright (c) 2001 - 2013 Emmanuel Viennet.  All rights reserved.
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

monthsnames = [ 'janvier', 'février', 'mars', 'avril', 'mai', 'juin',
                'juillet', 'aout', 'septembre', 'octobre', 'novembre',
                'décembre' ]                

def format_etud_ident(etud):
    """Format identite de l'étudiant (modifié en place)
    nom, prénom et formes associees
    """
    etud['nom'] = format_nom(etud['nom'])
    if 'nom_usuel' in etud:
        etud['nom_usuel'] =  format_nom(etud['nom_usuel'])
    else:
        etud['nom_usuel'] = ''
    etud['prenom'] = format_prenom(etud['prenom'])
    etud['sexe'] = format_sexe(etud['sexe'])
    # Nom à afficher:
    if etud['nom_usuel']:
        etud['nom_disp'] = etud['nom_usuel']
        if etud['nom']:
            etud['nom_disp'] += ' (' + etud['nom'] + ')'
    else:
        etud['nom_disp'] = etud['nom']

    etud['nomprenom'] = format_nomprenom(etud) # M. Pierre DUPONT
    if etud['sexe'] == 'M.':
        etud['ne'] = ''
    else:
        etud['ne'] = 'e'
    if 'email' in etud and etud['email']:
        etud['emaillink'] = '<a class="stdlink" href="mailto:%s">%s</a>'%(etud['email'],etud['email'])
    else:
        etud['emaillink'] = '<em>(pas d\'adresse e-mail)</em>'



def force_uppercase(s):
    if s:
        s = s.upper()
    return s

def format_nomprenom(etud):
    "formatte sexe/nom/prenom pour affichages"
    return ' '.join([ format_sexe(etud['sexe']), format_prenom(etud['prenom']), etud['nom_disp']])

def format_prenom(s):
    "formatte prenom etudiant pour affichage"
    # XXX locale.setlocale(locale.LC_ALL, ('en_US', 'ISO8859-15') )
    if not s:
        return ''
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
    if not s:
        return ''
    return s.upper()

def format_sexe(sexe):
    sexe = sexe.lower()
    if sexe == 'mr':
        return 'M.'
    else:
        return 'Mme'

def normalize_sexe(sexe):
    "returns 'MR' ou 'MME'"
    sexe = sexe.upper().strip()
    if sexe in ('M.', 'M', 'MR', 'H'):
        return 'MR'
    elif sexe in ('MLLE', 'MLLE.', 'MELLE', 'MME', 'F'):
        return 'MME'
    raise ValueError('valeur invalide pour le sexe: %s' % sexe)
    
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
    ('etudid', 'nom', 'nom_usuel', 'prenom', 'sexe',
     'date_naissance', 'lieu_naissance',
     'nationalite', 
     'statut',
     'foto', 'photo_filename', 'code_ine', 'code_nip'),
    sortkey = 'nom',
    input_formators = { 'nom' : force_uppercase,
                        'prenom' : force_uppercase,
                        'sexe' : force_uppercase,
                        'date_naissance' : DateDMYtoISO
                        },
    output_formators = { 'date_naissance' : DateISOtoDMY },
    convert_null_outputs_to_empty=True,
    allow_set_id = True # car on specifie le code Apogee a la creation
    )

identite_delete = _identiteEditor.delete

def identite_list(cnx, *a, **kw):
    "list, add 'annee_naissance'"
    objs = _identiteEditor.list(cnx,*a,**kw)
    for o in objs:
        if o['date_naissance']:
            o['annee_naissance'] = int(o['date_naissance'].split('/')[2])
        else:
            o['annee_naissance'] = o['date_naissance']
    return objs

def identite_edit_nocheck(cnx, args):
    """Modifie les champs mentionnes dans args, sans verification ni notification.
    """
    _identiteEditor.edit(cnx, args)

def check_nom_prenom(cnx, nom='', prenom='', etudid=None):
    """Check if nom and prenom are valid.
    Also check for duplicates (homonyms), excluding etudid : 
    in general, homonyms are allowed, but it may be useful to generate a warning.
    Returns:
    True | False, NbHomonyms
    """
    if not nom or (not prenom and not CONFIG.ALLOW_NULL_PRENOM):
        return False, 0
    if prenom:
        prenom = prenom.lower().strip()
    # Don't allow some special cars (eg used in sql regexps)
    if FORBIDDEN_CHARS_EXP.search(nom) or FORBIDDEN_CHARS_EXP.search(prenom):
        return False, 0
    # Now count homonyms:
    cursor = cnx.cursor(cursor_factory=ScoDocCursor)
    req = 'select etudid from identite where lower(nom) ~ %(nom)s and lower(prenom) ~ %(prenom)s'
    if etudid:
        req += '  and etudid <> %(etudid)s'
    cursor.execute(req, { 'nom' : nom.lower().strip(), 'prenom' : prenom, 'etudid' : etudid } )
    res = cursor.dictfetchall()
    return True, len(res)

def _check_duplicate_code(cnx, args, code_name, context, REQUEST=None):
    etudid = args.get('etudid', None)        
    if args.get(code_name, None):
        etuds = identite_list(cnx, {code_name : args[code_name]})
        log('etuds=%s'%etuds)
        if len(etuds) and (not etudid or (len(etuds) > 1 or etuds[0]['etudid'] != etudid)):
            listh = [] # liste des doubles
            for e in etuds:
                listh.append( """Autre étudiant: <a href="ficheEtud?etudid=%(etudid)s">%(nom)s %(prenom)s</a>""" % e )
            if etudid:
                OK = 'retour à la fiche étudiant'
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
                    message="""<h3>Code étudiant (%s) dupliqué !</h3>""" % code_name,
                    helpmsg="""Le %s %s est déjà utilisé: un seul étudiant peut avoir ce code. Vérifier votre valeur ou supprimer l'autre étudiant avec cette valeur.<p><ul><li>""" % (code_name, args[code_name])+ '</li><li>'.join(listh) + '</li></ul><p>',
                    OK=OK, dest_url=dest_url, parameters=parameters,
                    REQUEST=REQUEST )
            else:
                err_page = """<h3>Code étudiant (%s) dupliqué !</h3>""" % code_name
            raise ScoGenError(err_page)

def identite_edit(cnx, args, context=None, REQUEST=None):
    """Modifie l'identite d'un étudiant.
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
    
    identite_edit_nocheck(cnx, args)

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
            raise ScoValueError('Code identifiant (etudid) déjà utilisé ! (%s)' % etudid)
    return _identiteEditor.create(cnx, args)


def notify_etud_change(context, email_addr, etud, before, after, subject):
    """Send email notifying changes to etud
    before and after are two dicts, with values before and after the change.
    """
    txt = [
        'Code NIP:' + etud['code_nip'],
        'Genre: ' + etud['sexe'],
        'Nom: ' + etud['nom'],
        'Prénom: ' + etud['prenom'],
        'Etudid: ' + etud['etudid'],
        '\n',
        'Changements effectués:'
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
    msg['From'] = context.get_preference('email_from_addr')
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
    """Modifie l'adresse d'un étudiant.
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
      'nomlycee', 'villelycee', 'codepostallycee', 'codelycee',
      'debouche',
      ),
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
        res.sort( lambda x,y: cmp(x['nom']+x['prenom'],y['nom']+y['prenom']) )
        return res
    def edit(self, cnx, args, context=None, REQUEST=None):
        identite_edit( cnx, args, context, REQUEST )
        admission_edit( cnx, args )

_etudidentEditor = EtudIdentEditor()
etudident_list   = _etudidentEditor.list
etudident_edit   = _etudidentEditor.edit
etudident_create = _etudidentEditor.create

def make_etud_args(etudid=None, code_nip=None, REQUEST=None, raise_exc=True):
    """forme args dict pour requete recherche etudiant
    On peut specifier etudid
    ou bien cherche dans REQUEST.form: etudid, code_nip, code_ine
    (dans cet ordre).
    """
    args = None
    if etudid:
        args = { 'etudid' : etudid }
    elif code_nip:
        args = { 'code_nip' : code_nip }
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

def add_annotations_to_etud_list(context, etuds):
    """Add key 'annotations' describing annotations of etuds
    (used to list all annotations of a group)
    """
    cnx = context.GetDBConnexion()
    for etud in etuds:
        l = []
        for a in etud_annotations_list(cnx, args={ 'etudid' : etud['etudid'] }): 
            l.append( '%(comment)s (%(date)s)' % a)
        etud['annotations_str'] = ', '.join(l)

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


# -------- Noms des Lycées à partir du code
def read_etablissements():
    filename = SCO_SRCDIR + '/' + CONFIG.ETABL_FILENAME
    log('reading %s' % filename)
    f = open(filename)
    L = [ x[:-1].split(';') for x in f ]
    E = {}
    for l in L[1:]:
        E[l[0]] = { 'name' : l[1],
                    'address' : l[2],
                    'codepostal' : l[3],
                    'commune' : l[4],
                    'position' : l[5]+','+l[6]}
    return E

ETABLISSEMENTS = None
def get_etablissements():
    global ETABLISSEMENTS
    if ETABLISSEMENTS is None:
        ETABLISSEMENTS = read_etablissements()
    return ETABLISSEMENTS

def get_lycee_infos(codelycee):
    E = get_etablissements()
    return E.get(codelycee, None)

def format_lycee_from_code(codelycee):
    "Description lycee à partir du code"
    E = get_etablissements()
    if codelycee in E:
        e = E[codelycee]
        nomlycee = e['name']
        return '%s (%s)' % (nomlycee, e['commune'])
    else:
        return '%s (établissement inconnu)' % codelycee

def etud_add_lycee_infos(etud):
    """Si codelycee est renseigné, ajout les champs au dict"""
    if etud['codelycee']:
        il = get_lycee_infos(etud['codelycee'])
        if il:
            if not etud['codepostallycee']:
                etud['codepostallycee'] = il['codepostal']
            if not etud['nomlycee']:
                etud['nomlycee'] = il['name']
            if not etud['villelycee']:
                etud['villelycee'] = il['commune']
            if not etud.get('positionlycee', None):
                if il['position'] != '0.0,0.0':
                    etud['positionlycee'] = il['position']
    return etud

""" Conversion fichier original:
f = open('etablissements.csv')
o = open('etablissements2.csv', 'w')
o.write( f.readline() )
for l in f:
    fs = l.split(';')
    nom = ' '.join( [ x.capitalize() for x in fs[1].split() ] )
    adr = ' '.join( [ x.capitalize() for x in fs[2].split() ] )
    ville=' '.join( [ x.capitalize() for x in fs[4].split() ] )
    o.write( '%s;%s;%s;%s;%s\n' % (fs[0], nom, adr, fs[3], ville))

o.close()
"""
