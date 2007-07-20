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

"""Synchronisation des listes d'étudiants avec liste portail (Apogée)
"""


from sco_utils import *
from notes_log import log
from sco_exceptions import *
import sco_portal_apogee
import sco_inscr_passage
import scolars
import sco_news
from sco_news import NEWS_INSCR, NEWS_NOTE, NEWS_FORM, NEWS_SEM, NEWS_MISC

from sets import Set
import time

# Clés utilisées pour la synchro
EKEY_APO = 'nip'
EKEY_SCO = 'code_nip'
EKEY_NAME = 'code NIP'

def synchronize_etuds(context, formsemestre_id, etuds=[],
                               submitted=False, dialog_confirmed=False,
                               REQUEST=None):
    """Synchronise les étudiants de ce semestre avec ceux d'Apogée.
    On a plusieurs cas de figure: L'étudiant peut être
    1- présent dans Apogée et inscrit dans le semestre ScoDoc (etuds_ok)
    2- dans Apogée, dans ScoDoc, mais pas inscrit dans le semestre (etuds_noninscrits)
    3- dans Apogée et pas dans ScoDoc (etuds_a_importer)
    4- inscrit dans le semestre ScoDoc, mais pas trouvé dans Apogée (sur la base du code NIP)
    
    Que faire ?
    Cas 1: rien à faire
    Cas 2: inscrire dans le semestre
    Cas 3: importer l'étudiant (le créer)
            puis l'inscrire à ce semestre.
    Cas 4: lister les etudiants absents d'Apogée (indiquer leur code NIP...)

    - présenter les différents cas
    - l'utilisateur valide (cocher les étudiants à importer/inscrire)
    - go

    etuds: apres selection par utilisateur, la liste des etudiants selectionnes
    que l'on va importer/inscrire
    """
    log('synchronize_etuds: formsemestre_id=%s' % formsemestre_id)
    sem = context.get_formsemestre(formsemestre_id)
    # -- check lock
    if sem['etat'] != '1':
        raise ScoValueError('opération impossible: semestre verrouille')
    if not sem['etape_apo']:
        raise ScoValueError("""opération impossible: ce semestre n'a pas de code étape
        (voir "<a href="formsemestre_editwithmodules?formation_id=%(formation_id)s&formsemestre_id=%(formsemestre_id)s">Modifier ce semestre</a>")
        """ % sem )
    header = context.sco_header(REQUEST, page_title='Synchronisation étudiants') \
             + """<p style="color: red;"><b>Attention: fonction inachevée: manque de sinformations XML</b></p>"""
    footer = context.sco_footer(REQUEST)

    if type(etuds) == type(''):
        etuds = etuds.split(',') # vient du form de confirmation

    etuds_by_cat, etuds_a_importer, etudsapo_ident = list_synch(context, sem)    

    H = [ header ]
    if not submitted:
        H += build_page(context, sem, etuds_by_cat)
    else:
        etuds_set = Set(etuds)
        etuds_a_importer = etuds_a_importer.intersection(etuds_set)
        if not dialog_confirmed:
            # Confirmation
            H.append('<h3>Etudiants à importer et inscrire</h3><ol>')
            for key in etuds_a_importer:
                H.append('<li>%(fullname)s</li>' % etudsapo_ident[key] )
            H.append('</ol>')
            H.append( context.confirmDialog(
                dest_url="formsemestre_synchro_etuds",
                add_headers=False,
                cancel_url="formsemestre_synchro_etuds?formsemestre_id="+formsemestre_id,
                OK = "Effectuer l'opération",
                parameters = {'formsemestre_id' : formsemestre_id,
                              'etuds' : ','.join(etuds),
                              'submitted' : 1, 
                              }) )            
        else:
            # OK, do it
            do_import_etuds_from_portal(context, sem, etuds_a_importer, etudsapo_ident,
                                        REQUEST)
            H.append("""<h3>Opération effectuée</h3>
            <ul>
                <li><a class="stdlink" href="formsemestre_status?formsemestre_id=%s">Tableau de bord du semestre</a></li>
                <li><a class="stdlink" href="affectGroupes?formsemestre_id=%s&groupType=TD&groupTypeName=%s">Répartir les groupes de %s</a></li>
                """ % (formsemestre_id,formsemestre_id,sem['nomgroupetd'],sem['nomgroupetd']))
    
    H.append(footer)    
    return '\n'.join(H)


def build_page(context, sem, etuds_by_cat):
    H = [
        """<h2>Synchronisation des étudiants du semestre <a href="formsemestre_status?formsemestre_id=%(formsemestre_id)s">%(titreannee)s</a> avec Apogée</h2>
        <p>Code étape Apogée: %(etape_apo)s</p>
        <form method="post">
        <input type="hidden" name="formsemestre_id" value="%(formsemestre_id)s"/>
        <input type="submit" name="submitted" value="Importer et inscrire"/>
        &nbsp;<a href="#help">aide</a>
        """ % sem, # "
          
        sco_inscr_passage.etuds_select_boxes(context, etuds_by_cat, sel_inscrits=False),

        synchronize_etuds_help(sem),
        """</form>""",          
        ]
    return H

def list_synch(context, sem):
    inscrits = sco_inscr_passage.list_inscrits(context, sem['formsemestre_id']) 
    # Tous les ensembles d'etudiants sont ici des ensembles de codes NIP (voir EKEY_SCO)
    inscrits_set = Set()
    inscrits_without_key = {} # etudid : etud sans code NIP
    for e in inscrits.values():
        if not e[EKEY_SCO]:
            inscrits_without_key[e['etudid']] = e
        else:
            inscrits_set.add(e[EKEY_SCO])
    etudsapo = sco_portal_apogee.get_inscrits_etape(sem['etape_apo'])
    etudsapo_set = Set( [ x[EKEY_APO] for x in etudsapo ] )
    etudsapo_ident = dict( [ (x[EKEY_APO], x) for x in etudsapo ] )
    # categories:
    etuds_ok = etudsapo_set.intersection(inscrits_set)
    etuds_noninscrits, etuds_a_importer, key2etudid = list_all(context, etudsapo_set)
    etuds_nonapogee = inscrits_set - etudsapo_set
    #
    cnx = context.GetDBConnexion()
    def key2etud(key, valid_etudid=True ):
        if valid_etudid:
            etudid = key2etudid[key]
            etud = scolars.identite_list(cnx, {'etudid' : etudid})[0]
            return etud
        else:
            # etudiant Apogee
            etud = etudsapo_ident[key]
            etud['etudid'] = ''
            etud['sexe'] = etud.get('sexe', '')
            etud['inscrit'] = True # => checkbox checked
            return etud

    #
    r = {
        'etuds_ok' :
        { 'etuds' : [ key2etud(x) for x in etuds_ok ],
          'infos' : { 'id' : 'etuds_ok',
                      'title' : 'Etudiants dans Apogée et déjà inscrits',
                      'title_target' : '',
                      'with_checkbox' : False }
          },
        'etuds_noninscrits' : 
        { 'etuds' : [ key2etud(x) for x in  etuds_noninscrits ],
          'infos' : { 'id' : 'etuds_noninscrits',
                      'title' : 'Etudiants non inscrits dans ce semestre',
                      'title_target' : '',
                      'with_checkbox' : False }
          },
        'etuds_a_importer' :
        { 'etuds' : [ key2etud(x, valid_etudid=False) for x in etuds_a_importer ],
          'infos' : { 'id' : 'etuds_a_importer',
                      'title' : 'Etudiants dans Apogée à importer',
                      'title_target' : '',
                      'etud_key' : EKEY_APO # clé a stocker dans le formulaire html
                      },
          'nomprenoms' : etudsapo_ident
          },
        'etuds_nonapogee' :
        { 'etuds' : [ key2etud(x) for x in etuds_nonapogee ],
          'infos' : { 'id' : 'etuds_nonapogee',
                      'title' : 'Etudiants ScoDoc inconnus dans Apogée',
                      'title_target' : '',
                      'with_checkbox' : False }
          },
        'inscrits_without_key' :
        { 'etuds' : inscrits_without_key.values(),
          'infos' : { 'id' : 'inscrits_without_key',
                      'title' : 'Etudiants ScoDoc sans clé Apogée (NIP)',
                      'title_target' : '',
                      'with_checkbox' : False }
        }
        }
    return r, etuds_a_importer, etudsapo_ident

def list_all(context, etudsapo_set):
    """Cherche le sous-ensemble des etudiants Apogee de ce semestre
    qui existent dans ScoDoc.
    """
    # on charge TOUS les etudiants (au pire qq 100000 ?)
    # si tres grosse base, il serait mieux de faire une requete
    # d'interrogation par etudiant.
    cnx = context.GetDBConnexion()
    cursor = cnx.cursor()
    cursor.execute( 'select ' + EKEY_SCO + ', etudid from identite' )
    key2etudid = dict( [ (x[0], x[1]) for x in cursor.fetchall() ] )
    all_set = Set(key2etudid.keys())
    
    # ne retient que ceux dans Apo
    etuds_noninscrits = etudsapo_set.intersection(all_set)
    etuds_a_importer  = etudsapo_set - all_set
    return etuds_noninscrits, etuds_a_importer, key2etudid

def synchronize_etuds_help(sem):
    return """<div class="pas_help"><h3><a name="help">Explications</a></h3>
    <p>Cette page permet d'importer dans le semestre destination
    <a class="stdlink"
    href="formsemestre_status?formsemestre_id=(formsemestre_id)s">%(titreannee)s</a>
    les étudiants inscrits dans l'étape Apogée correspondante (<b><tt>%(etape_apo)s</tt></b>) 
    </p>
    <p>Au départ, tous les étudiants d'Apogée sont sélectionnés; vous pouvez 
    en déselectionner certains.</p>

    <h4>Autres fonctions utiles</h4>
    <ul>
    <li><a href="check_group_apogee?formsemestre_id=%(formsemestre_id)s">vérification
    des codes Apogée</a> (des étudiants déjà inscrits)</li>
    <li>le <a href="formsemestre_inscr_passage?formsemestre_id=%(formsemestre_id)s">
    formulaire de passage</a> qui permet aussi de désinscrire des étudiants
    en cas d'erreur, etc.</li>
    </ul>
    </div>""" % sem

def do_import_etuds_from_portal(context, sem, etuds_a_importer, etudsapo_ident, REQUEST):
    """Inscrit les etudiants apogee dans ce semestre.
    """
    log('do_import_etuds_from_portal: etuds_a_importer=%s' % etuds_a_importer)
    cnx = context.GetDBConnexion()
    annee_courante = time.localtime()[0]
    created_etudids = []
    raise NotImplementedError
    # Manque:
    #  1/ gestion separee des inscriptions et des imports+inscription
    #  2/ completer suivant WebService portail (adresse, sexe, ...)

    try: # --- begin DB transaction
        for key in etuds_a_importer:
            etud = etudsapo_ident[key] # on a ici toutes les infos renvoyées par le portail
            # XXX pour l'instant il manque les coordonnées (adresses) des etudiants

            args = { 'nom' : etud['nom'], 'prenom' : etud['prenom'],
                     'sexe' : 'M.', # XXX manque dans le XML portal
                     'code_nip' :  etud['nip']
                     }
            # Identite
            args['etudid'] = scolars.identite_create(cnx, args )
            created_etudids.append(args['etudid'])
            # Admissions
            args['annee'] = annee_courante
            adm_id = scolars.admission_create(cnx, args)
            # Adresse
            args['typeadresse'] = 'domicile'
            args['description'] = '(infos admission)'
            adresse_id = scolars.adresse_create(cnx,args)

            # Inscription au semestre
            args['etat'] = 'I' # etat insc. semestre
            args['groupetd'] = 'A' # groupe par defaut
            args['formsemestre_id'] = sem['formsemestre_id']

            context.do_formsemestre_inscription_with_modules(
                args=args,
                REQUEST=REQUEST,
                method='synchro_apogee')
    except:
        cnx.rollback()
        log('do_import_etuds_from_portal: aborting transaction !')
        # Nota: db transaction is sometimes partly commited...
        # here we try to remove all created students
        cursor = cnx.cursor()
        for etudid in created_etudids:
            log('scolars_import_excel_file: deleting etudid=%s'%etudid)
            cursor.execute('delete from notes_moduleimpl_inscription where etudid=%(etudid)s', { 'etudid':etudid })
            cursor.execute('delete from notes_formsemestre_inscription where etudid=%(etudid)s', { 'etudid':etudid })
            cursor.execute('delete from scolar_events where etudid=%(etudid)s', { 'etudid':etudid })
            cursor.execute('delete from adresse where etudid=%(etudid)s', { 'etudid':etudid })
            cursor.execute('delete from admissions where etudid=%(etudid)s', { 'etudid':etudid })
            cursor.execute('delete from identite where etudid=%(etudid)s', { 'etudid':etudid })
        cnx.commit()
        log('do_import_etuds_from_portal: re-raising exception')
        raise
        
    sco_news.add(REQUEST, cnx, typ=NEWS_INSCR,
                 text='Import Apogée de %d étudiants' % len(created_etudids) )
    
