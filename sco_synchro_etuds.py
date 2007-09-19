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

"""Synchronisation des listes d'�tudiants avec liste portail (Apog�e)
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

# Cl�s utilis�es pour la synchro
EKEY_APO = 'nip'
EKEY_SCO = 'code_nip'
EKEY_NAME = 'code NIP'

def synchronize_etuds(context, formsemestre_id, etuds=[], anneeapogee=None,
                      inscrire_non_inscrits=False, # declenche inscription des "aposco" non inscrits
                      submitted=False, dialog_confirmed=False,
                      REQUEST=None):
    """Synchronise les �tudiants de ce semestre avec ceux d'Apog�e.
    On a plusieurs cas de figure: L'�tudiant peut �tre
    1- pr�sent dans Apog�e et inscrit dans le semestre ScoDoc (etuds_ok)
    2- dans Apog�e, dans ScoDoc, mais pas inscrit dans le semestre (etuds_noninscrits)
    3- dans Apog�e et pas dans ScoDoc (etuds_a_importer)
    4- inscrit dans le semestre ScoDoc, mais pas trouv� dans Apog�e (sur la base du code NIP)
    
    Que faire ?
    Cas 1: rien � faire
    Cas 2: inscrire dans le semestre
    Cas 3: importer l'�tudiant (le cr�er)
            puis l'inscrire � ce semestre.
    Cas 4: lister les etudiants absents d'Apog�e (indiquer leur code NIP...)

    - pr�senter les diff�rents cas
    - l'utilisateur valide (cocher les �tudiants � importer/inscrire)
    - go

    etuds: apres selection par utilisateur, la liste des etudiants selectionnes
    que l'on va importer/inscrire
    """
    log('synchronize_etuds: formsemestre_id=%s' % formsemestre_id)
    sem = context.get_formsemestre(formsemestre_id)
    # -- check lock
    if sem['etat'] != '1':
        raise ScoValueError('op�ration impossible: semestre verrouille')
    if not sem['etape_apo']:
        raise ScoValueError("""op�ration impossible: ce semestre n'a pas de code �tape
        (voir "<a href="formsemestre_editwithmodules?formation_id=%(formation_id)s&formsemestre_id=%(formsemestre_id)s">Modifier ce semestre</a>")
        """ % sem )
    header = context.sco_header(REQUEST, page_title='Synchronisation �tudiants')
    footer = context.sco_footer(REQUEST)

    if type(etuds) == type(''):
        etuds = etuds.split(',') # vient du form de confirmation

    etuds_by_cat, etuds_a_importer, etudsapo_ident = list_synch(context, sem, anneeapogee=anneeapogee)    

    H = [ header ]
    if not submitted:
        H += build_page(context, sem, etuds_by_cat, anneeapogee)
    else:
        etuds_set = Set(etuds)
        etuds_a_importer = etuds_a_importer.intersection(etuds_set)
        if not dialog_confirmed:
            if not inscrire_non_inscrits:
                # Confirmation
                H.append('<h3>Etudiants � importer et inscrire</h3><ol>')
                for key in etuds_a_importer:
                    H.append('<li>%(fullname)s</li>' % etudsapo_ident[key] )
                H.append('</ol>')
            else:
                 H.append("""<h3>Etudiants � inscrire</h3>
                 <p>Ces �tudiants sont connus de ScoDoc et inscrits � l'�tape Apog�e
                 correspondant � ce semestre, mais pas encore inscrits au semestre dans ScoDoc</p><ol>""")
                 for etud in etuds_by_cat['etuds_noninscrits']['etuds']:
                     H.append('<li>%s</li>' % context.nomprenom(etud) )
                 H.append('</ol>')
            H.append( context.confirmDialog(
                dest_url="formsemestre_synchro_etuds",
                add_headers=False,
                cancel_url="formsemestre_synchro_etuds?formsemestre_id="+formsemestre_id,
                OK = "Effectuer l'op�ration",
                parameters = {'formsemestre_id' : formsemestre_id,
                              'etuds' : ','.join(etuds),
                              'submitted' : 1,
                              'inscrire_non_inscrits' : inscrire_non_inscrits
                              }) )            
        else:
            # OK, do it
            if inscrire_non_inscrits:
                do_synch_inscrits_etuds(context, sem, etuds_by_cat['etuds_noninscrits']['etuds'], REQUEST=REQUEST)
            do_import_etuds_from_portal(context, sem, etuds_a_importer, etudsapo_ident,
                                        REQUEST)
            H.append("""<h3>Op�ration effectu�e</h3>
            <ul>
                <li><a class="stdlink" href="formsemestre_status?formsemestre_id=%s">Tableau de bord du semestre</a></li>
                <li><a class="stdlink" href="affectGroupes?formsemestre_id=%s&groupType=TD&groupTypeName=%s">R�partir les groupes de %s</a></li>
                """ % (formsemestre_id,formsemestre_id,sem['nomgroupetd'],sem['nomgroupetd']))
    
    H.append(footer)    
    return '\n'.join(H)


def build_page(context, sem, etuds_by_cat, anneeapogee):
    year = time.localtime()[0]
    years_lab = ( str(year), str(year-1), 'tous' )
    years_vals = ( str(year), str(year-1), '' )
    if anneeapogee == str(year) or anneeapogee==None:
        sel = [ 'selected', '', '']
    elif anneeapogee == str(year-1):
        sel = [ '', 'selected', '']
    else:
        sel = [ '', '', 'selected']
    H = [
        """<h2>Synchronisation des �tudiants du semestre <a href="formsemestre_status?formsemestre_id=%(formsemestre_id)s">%(titreannee)s</a> avec Apog�e</h2>""" % sem,
        """<p>Actuellement <b>%d</b> inscrits dans ce semestre.</p>"""
        % (len(etuds_by_cat['etuds_ok']['etuds'])+len(etuds_by_cat['etuds_nonapogee']['etuds'])+len(etuds_by_cat['inscrits_without_key']['etuds'])),
        """<p>Code �tape Apog�e: %(etape_apo)s</p>
        <form method="post">
        """ % sem,
        """
        Ann�e Apog�e: <select id="anneeapogee" name="anneeapogee" onchange="document.location='formsemestre_synchro_etuds?formsemestre_id=%s&anneeapogee='+document.getElementById('anneeapogee').value">
        <option value="%s" ww %s>%s</option><option value="%s" %s>%s</option><option value="%s" %s>%s</option>
        </select>
        """ % (sem['formsemestre_id'], str(year),sel[0],str(year), str(year-1),sel[1],str(year-1), '*', sel[-1], 'toutes'),
        """
        <input type="hidden" name="formsemestre_id" value="%(formsemestre_id)s"/>
        <input type="submit" name="submitted" value="Importer et inscrire"/>
        &nbsp;<a href="#help">aide</a>
        """ % sem, # "
          
        sco_inscr_passage.etuds_select_boxes(context, etuds_by_cat, sel_inscrits=False),

        synchronize_etuds_help(sem),
        """</form>""",          
        ]
    return H

def list_synch(context, sem, anneeapogee=None):
    inscrits = sco_inscr_passage.list_inscrits(context, sem['formsemestre_id']) 
    # Tous les ensembles d'etudiants sont ici des ensembles de codes NIP (voir EKEY_SCO)
    inscrits_set = Set()
    inscrits_without_key = {} # etudid : etud sans code NIP
    for e in inscrits.values():
        if not e[EKEY_SCO]:
            inscrits_without_key[e['etudid']] = e
        else:
            inscrits_set.add(e[EKEY_SCO])
    etudsapo = sco_portal_apogee.get_inscrits_etape(context, sem['etape_apo'], anneeapogee=anneeapogee)
    etudsapo_set = Set( [ x[EKEY_APO] for x in etudsapo ] )
    etudsapo_ident = dict( [ (x[EKEY_APO], x) for x in etudsapo ] )
    # categories:
    etuds_ok = etudsapo_set.intersection(inscrits_set)
    etuds_aposco, etuds_a_importer, key2etudid = list_all(context, etudsapo_set)
    etuds_noninscrits = etuds_aposco - inscrits_set
    etuds_nonapogee = inscrits_set - etudsapo_set
    #
    cnx = context.GetDBConnexion()
    # Tri listes
    def set_to_sorted_list(etudset, valid_etudid=True):
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
        
        etuds = [ key2etud(x, valid_etudid) for x in etudset ]
        etuds.sort( lambda x,y: cmp(x['nom'], y['nom']) )
        return etuds    
    #
    r = {
        'etuds_ok' :
        { 'etuds' : set_to_sorted_list(etuds_ok),
          'infos' : { 'id' : 'etuds_ok',
                      'title' : 'Etudiants dans Apog�e et d�j� inscrits',
                      'title_target' : '',
                      'with_checkbox' : False }
          },
        'etuds_noninscrits' : 
        { 'etuds' : set_to_sorted_list(etuds_noninscrits), 
          'infos' : { 'id' : 'etuds_noninscrits',
                      'title' : 'Etudiants non inscrits dans ce semestre',
                      'comment' : """ dans ScoDoc et Apog�e, <br/>mais pas inscrits
                      dans ce semestre<br/>
                      <a href="formsemestre_synchro_etuds?formsemestre_id=%s&submitted=1&inscrire_non_inscrits=1" style="color:red; font-weight:bold">inscrire ces �tudiants</a>
                      """ % sem['formsemestre_id'],
                      'title_target' : '',
                      'with_checkbox' : False }
          },
        'etuds_a_importer' :
        { 'etuds' : set_to_sorted_list(etuds_a_importer, valid_etudid=False),
          'infos' : { 'id' : 'etuds_a_importer',
                      'title' : 'Etudiants dans Apog�e � importer',
                      'title_target' : '',
                      'etud_key' : EKEY_APO # cl� a stocker dans le formulaire html
                      },
          'nomprenoms' : etudsapo_ident
          },
        'etuds_nonapogee' :
        { 'etuds' : set_to_sorted_list(etuds_nonapogee),
          'infos' : { 'id' : 'etuds_nonapogee',
                      'title' : 'Etudiants ScoDoc inconnus dans Apog�e',
                      'title_target' : '',
                      'with_checkbox' : False }
          },
        'inscrits_without_key' :
        { 'etuds' : inscrits_without_key.values(),
          'infos' : { 'id' : 'inscrits_without_key',
                      'title' : 'Etudiants ScoDoc sans cl� Apog�e (NIP)',
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
    etuds_aposco = etudsapo_set.intersection(all_set) # a la fois dans Apogee et dans ScoDoc
    etuds_a_importer  = etudsapo_set - all_set # dans Apogee, mais inconnus dans ScoDoc
    return etuds_aposco, etuds_a_importer, key2etudid

def synchronize_etuds_help(sem):
    return """<div class="pas_help"><h3><a name="help">Explications</a></h3>
    <p>Cette page permet d'importer dans le semestre destination
    <a class="stdlink"
    href="formsemestre_status?formsemestre_id=(formsemestre_id)s">%(titreannee)s</a>
    les �tudiants inscrits dans l'�tape Apog�e correspondante (<b><tt>%(etape_apo)s</tt></b>) 
    </p>
    <p>Au d�part, tous les �tudiants d'Apog�e sont s�lectionn�s; vous pouvez 
    en d�selectionner certains.</p>

    <h4>Autres fonctions utiles</h4>
    <ul>
    <li><a href="check_group_apogee?formsemestre_id=%(formsemestre_id)s">v�rification
    des codes Apog�e</a> (des �tudiants d�j� inscrits)</li>
    <li>le <a href="formsemestre_inscr_passage?formsemestre_id=%(formsemestre_id)s">
    formulaire de passage</a> qui permet aussi de d�sinscrire des �tudiants
    en cas d'erreur, etc.</li>
    </ul>
    </div>""" % sem



def gender2sex(gender):
    """Le portail code en 'M', 'F', et SocDoc en 'MR', 'MME', 'MLLE'
    Les F sont ici cod�es en MLLE
    """
    if gender == 'M':
        return 'MR'
    elif gender == 'F':
        return 'MLLE'
    log('gender2sex: invalid value "%s", defaulting to "M"' % gender)
    return 'MR'

def do_import_etuds_from_portal(context, sem, etuds_a_importer, etudsapo_ident, REQUEST):
    """Inscrit les etudiants apogee dans ce semestre.
    """
    log('do_import_etuds_from_portal: etuds_a_importer=%s' % etuds_a_importer)
    cnx = context.GetDBConnexion()
    annee_courante = time.localtime()[0]
    created_etudids = []
    
    # Manque:
    #  2/ completer suivant WebService portail (adresse, sexe, ...)

    try: # --- begin DB transaction
        for key in etuds_a_importer:
            etud = etudsapo_ident[key] # on a ici toutes les infos renvoy�es par le portail

            # Traduit les infos portail en infos pour ScoDoc:
            address = etud['address'].strip()
            if address[-2:] == '\\n': # certains champs se terminent par \n
                address = address[:-2]
            args = { 'nom' : etud['nom'].strip(), 'prenom' : etud['prenom'].strip(),
                     'sexe' : gender2sex(etud['gender'].strip()),
                     'code_nip' :  etud['nip'],
                     'email' : etud['mail'].strip(),
                     'domicile' : address,
                     'codepostaldomicile' : etud['postalcode'].strip(),
                     'villedomicile' : etud['city'].strip(),
                     'paysdomicile' : etud['country'].strip(),
                     'telephone' :  etud.get('phone', '').strip(),
                     'typeadresse' : 'domicile',
                     'description' : 'infos portail'
                     }
            # Identite
            args['etudid'] = scolars.identite_create(cnx, args )
            created_etudids.append(args['etudid'])
            # Admissions
            args['annee'] = annee_courante
            adm_id = scolars.admission_create(cnx, args)
            # Adresse
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
                 text='Import Apog�e de %d �tudiants' % len(created_etudids) )
    

def do_synch_inscrits_etuds(context, sem, etuds, REQUEST=None):
    """inscrits ces etudiants (d�ja dans ScoDoc) au semestre"""
    log('do_synch_inscrits_etuds: inscription de %d etudiants'%len(etuds))
    for etud in etuds:
        args = { 'etat' : 'I', # etat insc. semestre
                 'groupetd' : 'A', # groupe par defaut
                 'formsemestre_id' : sem['formsemestre_id'],
                 'etudid' : etud['etudid']
                 }
        context.do_formsemestre_inscription_with_modules(
            args=args,
            REQUEST=REQUEST,
            method='synchro_apogee')
        
