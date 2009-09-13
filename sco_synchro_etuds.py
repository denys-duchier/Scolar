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
import sco_portal_apogee
import sco_inscr_passage
import scolars
import sco_news, sco_excel
from sco_news import NEWS_INSCR, NEWS_NOTE, NEWS_FORM, NEWS_SEM, NEWS_MISC

from sets import Set
import time

# Clés utilisées pour la synchro
EKEY_APO = 'nip'
EKEY_SCO = 'code_nip'
EKEY_NAME = 'code NIP'

def formsemestre_synchro_etuds(
    context, formsemestre_id, 
    etuds=[], # liste des codes NIP des etudiants a inscrire (ou deja inscrits)
    inscrits_without_key=[], # codes etudid des etudiants sans code NIP a laisser inscrits
    anneeapogee=None,
    submitted=False, dialog_confirmed=False,
    export_cat_xls=None,
    REQUEST=None ):
    """Synchronise les étudiants de ce semestre avec ceux d'Apogée.
    On a plusieurs cas de figure: L'étudiant peut être
    1- présent dans Apogée et inscrit dans le semestre ScoDoc (etuds_ok)
    2- dans Apogée, dans ScoDoc, mais pas inscrit dans le semestre (etuds_noninscrits)
    3- dans Apogée et pas dans ScoDoc (a_importer)
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
    log('formsemestre_synchro_etuds: formsemestre_id=%s' % formsemestre_id)
    sem = context.get_formsemestre(formsemestre_id)
    # -- check lock
    if sem['etat'] != '1':
        raise ScoValueError('opération impossible: semestre verrouille')
    if not sem['etape_apo']:
        raise ScoValueError("""opération impossible: ce semestre n'a pas de code étape
        (voir "<a href="formsemestre_editwithmodules?formation_id=%(formation_id)s&formsemestre_id=%(formsemestre_id)s">Modifier ce semestre</a>")
        """ % sem )
    header = context.sco_header(REQUEST, page_title='Synchronisation étudiants')
    footer = context.sco_footer(REQUEST)
    base_url = '%s?formsemestre_id=%s' % (REQUEST.URL0, formsemestre_id)
    if anneeapogee:
        base_url += '&anneeapogee=%s' % anneeapogee

    if type(etuds) == type(''):
        etuds = etuds.split(',') # vient du form de confirmation
    if type(inscrits_without_key) == type(''):
        inscrits_without_key = inscrits_without_key.split(',')
        
    etuds_by_cat, a_importer, a_inscrire, inscrits_set, inscrits_without_key_all, etudsapo_ident = list_synch(context, sem, anneeapogee=anneeapogee)    

    if export_cat_xls:
        filename = export_cat_xls
        xls = build_page(context, sem, etuds_by_cat, anneeapogee,
                         export_cat_xls=export_cat_xls, base_url=base_url )
        return sco_excel.sendExcelFile(REQUEST, xls, filename + '.xls' )
    
    H = [ header ]
    if not submitted:
        H += build_page(context, sem, etuds_by_cat, anneeapogee, base_url=base_url)
    else:
        etuds_set = Set(etuds)
        a_importer = a_importer.intersection(etuds_set)
        a_desinscrire = inscrits_set - etuds_set
        log('inscrits_without_key_all=%s'%Set(inscrits_without_key_all))
        log('inscrits_without_key=%s'%inscrits_without_key)
        a_desinscrire_without_key =  Set(inscrits_without_key_all) - Set(inscrits_without_key)
        log('a_desinscrire_without_key=%s'%a_desinscrire_without_key)
        inscrits_ailleurs = Set(sco_inscr_passage.list_inscrits_date(context, sem))
        a_inscrire = a_inscrire.intersection(etuds_set)
        
        if not dialog_confirmed:
            # Confirmation
            if a_importer:                
                H.append('<h3>Etudiants à importer et inscrire :</h3><ol>')
                for key in a_importer:
                    H.append('<li>%(fullname)s</li>' % etudsapo_ident[key] )
                H.append('</ol>')

            if a_inscrire:
                H.append('<h3>Etudiants à inscrire :</h3><ol>')
                for key in a_inscrire:
                    H.append('<li>%(fullname)s</li>' % etudsapo_ident[key] )
                H.append('</ol>')
            
            a_inscrire_en_double = inscrits_ailleurs.intersection(a_inscrire)
            if a_inscrire_en_double:
                H.append('<h3>dont étudiants déjà inscrits:</h3><ol>')
                for key in a_inscrire_en_double:
                    H.append('<li class="inscrailleurs">%(fullname)s</li>' % etudsapo_ident[key])
                H.append('</ol>')

            if a_desinscrire or a_desinscrire_without_key:
                H.append('<h3>Etudiants à désinscrire :</h3><ol>')
                for key in a_desinscrire:
                    etud = context.getEtudInfo(code_nip=key)[0]
                    H.append('<li class="desinscription">%s</li>' % context.nomprenom(etud) )
                for etudid in a_desinscrire_without_key:
                    etud = inscrits_without_key_all[etudid]
                    H.append('<li class="desinscription">%s</li>' % context.nomprenom(etud) )
                H.append('</ol>')

            if not a_importer and not a_inscrire and not a_desinscrire:
                H.append("""<h3>Il n'y a rien à modifier !</h3>""")

            H.append( context.confirmDialog(
                dest_url="formsemestre_synchro_etuds",
                add_headers=False,
                cancel_url="formsemestre_synchro_etuds?formsemestre_id="+formsemestre_id,
                OK = "Effectuer l'opération",
                parameters = {'formsemestre_id' : formsemestre_id,
                              'etuds' : ','.join(etuds),
                              'inscrits_without_key' : ','.join(inscrits_without_key),
                              'submitted' : 1,
                              'anneeapogee' : anneeapogee
                              }) )            
        else:
            # OK, do it

            # Conversions des listes de codes NIP en listes de codes etudid
            def nip2etudid(code_nip):
                etud = context.getEtudInfo(code_nip=code_nip)[0]
                return etud['etudid']
            etudids_a_inscrire = [ nip2etudid(x) for x in a_inscrire ]
            etudids_a_desinscrire = [ nip2etudid(x) for x in a_desinscrire ]
            etudids_a_desinscrire += a_desinscrire_without_key
            #
            do_import_etuds_from_portal(context, sem, a_importer, etudsapo_ident, REQUEST)
            sco_inscr_passage.do_inscrit(context, sem, etudids_a_inscrire, REQUEST)
            sco_inscr_passage.do_desinscrit(context, sem, etudids_a_desinscrire, REQUEST)
            
            H.append("""<h3>Opération effectuée</h3>
            <ul>
                <li><a class="stdlink" href="formsemestre_synchro_etuds?formsemestre_id=%s">Continuer la synchronisation</a></li>
                <li><a class="stdlink" href="affectGroupes?formsemestre_id=%s&groupType=TD&groupTypeName=%s">Répartir les groupes de %s</a></li>
                """ % (formsemestre_id,formsemestre_id,sem['nomgroupetd'],sem['nomgroupetd']))
    
    H.append(footer)    
    return '\n'.join(H)


def build_page(context, sem, etuds_by_cat, anneeapogee,
               export_cat_xls=None, base_url=''):
    if export_cat_xls:
        return sco_inscr_passage.etuds_select_boxes(context, etuds_by_cat,
                                                    export_cat_xls=export_cat_xls,
                                                    base_url=base_url)
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
        """<h2 class="formsemestre">Synchronisation des étudiants du semestre avec Apogée</h2>""",
        """<p>Actuellement <b>%d</b> inscrits dans ce semestre.</p>"""
        % (len(etuds_by_cat['etuds_ok']['etuds'])+len(etuds_by_cat['etuds_nonapogee']['etuds'])+len(etuds_by_cat['inscrits_without_key']['etuds'])),
        """<p>Code étape Apogée: %(etape_apo)s</p>
        <form method="post">
        """ % sem,
        """
        Année Apogée: <select id="anneeapogee" name="anneeapogee" onchange="document.location='formsemestre_synchro_etuds?formsemestre_id=%s&anneeapogee='+document.getElementById('anneeapogee').value">
        <option value="%s" ww %s>%s</option><option value="%s" %s>%s</option><option value="%s" %s>%s</option>
        </select>
        """ % (sem['formsemestre_id'], str(year),sel[0],str(year), str(year-1),sel[1],str(year-1), '*', sel[-1], 'toutes'),
        """
        <input type="hidden" name="formsemestre_id" value="%(formsemestre_id)s"/>
        <input type="submit" name="submitted" value="Appliquer les modifications"/>
        &nbsp;<a href="#help">aide</a>
        """ % sem, # "
          
        sco_inscr_passage.etuds_select_boxes(context, etuds_by_cat,
                                             sel_inscrits=False,
                                             show_empty_boxes=True,
                                             base_url=base_url),
        """<p/><input type="submit" name="submitted" value="Appliquer les modifications"/>""",

        formsemestre_synchro_etuds_help(sem),
        """</form>""",          
        ]
    return H

def list_synch(context, sem, anneeapogee=None):
    inscrits = sco_inscr_passage.list_inscrits(context, sem['formsemestre_id'], with_dems=True)
    # Tous les ensembles d'etudiants sont ici des ensembles de codes NIP (voir EKEY_SCO)
    # (sauf inscrits_without_key)
    inscrits_set = Set()
    inscrits_without_key = {} # etudid : etud sans code NIP
    for e in inscrits.values():
        if not e[EKEY_SCO]:
            inscrits_without_key[e['etudid']] = e
            e['inscrit'] = True # checkbox state 
        else:
            inscrits_set.add(e[EKEY_SCO])
#     allinscrits_set = Set() # tous les inscrits scodoc avec code_nip, y compris les demissionnaires
#     for e in inscrits.values():
#         if e[EKEY_SCO]:
#             allinscrits_set.add(e[EKEY_SCO])
    
    etudsapo = sco_portal_apogee.get_inscrits_etape(context, sem['etape_apo'], anneeapogee=anneeapogee)
    etudsapo_set = Set( [ x[EKEY_APO] for x in etudsapo ] )
    etudsapo_ident = dict( [ (x[EKEY_APO], x) for x in etudsapo ] )
    # categories:
    etuds_ok = etudsapo_set.intersection(inscrits_set)
    etuds_aposco, a_importer, key2etudid = list_all(context, etudsapo_set)
    etuds_noninscrits = etuds_aposco - inscrits_set
    etuds_nonapogee = inscrits_set - etudsapo_set
    #
    cnx = context.GetDBConnexion()
    # Tri listes
    def set_to_sorted_list(etudset, etud_apo=False, is_inscrit=False):
        def key2etud(key, etud_apo=False ):
            if not etud_apo:
                etudid = key2etudid[key]
                etud = scolars.identite_list(cnx, {'etudid' : etudid})[0]
                etud['inscrit'] = is_inscrit # checkbox state
                return etud
            else:
                # etudiant Apogee
                etud = etudsapo_ident[key]
                etud['etudid'] = ''
                etud['sexe'] = etud.get('sexe', '')
                etud['inscrit'] = is_inscrit # checkbox state
                return etud
        
        etuds = [ key2etud(x, etud_apo) for x in etudset ]
        etuds.sort( lambda x,y: cmp(x['nom'], y['nom']) )
        return etuds    
    #
    r = {
        'etuds_ok' :
        { 'etuds' : set_to_sorted_list(etuds_ok, is_inscrit=True),
          'infos' : { 'id' : 'etuds_ok',
                      'title' : 'Etudiants dans Apogée et déjà inscrits',
                      'help' : 'Ces etudiants sont inscrits dans le semestre ScoDoc et sont présents dans Apogée: tout est donc correct. Décocher les étudiants que vous souhaitez désinscrire.',
                      'title_target' : '',
                      'with_checkbox' : True,
                      'etud_key' : EKEY_SCO
                      }
          },
        'etuds_noninscrits' : 
        { 'etuds' : set_to_sorted_list(etuds_noninscrits, is_inscrit=True), 
          'infos' : { 'id' : 'etuds_noninscrits',
                      'title' : 'Etudiants non inscrits dans ce semestre',
                      'help' : """Ces étudiants sont déjà connus par ScoDoc, sont inscrits dans cette étape Apogée mais ne sont pas inscrits à ce semestre ScoDoc. Cochez les étudiants à inscrire.""",
                      'comment' : """ dans ScoDoc et Apogée, <br/>mais pas inscrits
                      dans ce semestre""",
                      'title_target' : '',
                      'with_checkbox' : True,
                      'etud_key' : EKEY_SCO
                      }
          },
        'etuds_a_importer' :
        { 'etuds' : set_to_sorted_list(a_importer, is_inscrit=True, etud_apo=True),
          'infos' : { 'id' : 'etuds_a_importer',
                      'title' : 'Etudiants dans Apogée à importer',
                      'help' : """Ces étudiants sont inscrits dans cette étape Apogée mais ne sont pas connus par ScoDoc: cocher les noms à importer et inscrire puis appuyer sur le bouton "Appliquer".""",
                      'title_target' : '',
                      'with_checkbox' : True,
                      'etud_key' : EKEY_APO # clé à stocker dans le formulaire html
                      },
          'nomprenoms' : etudsapo_ident
          },
        'etuds_nonapogee' :
        { 'etuds' : set_to_sorted_list(etuds_nonapogee, is_inscrit=True),
          'infos' : { 'id' : 'etuds_nonapogee',
                      'title' : 'Etudiants ScoDoc inconnus dans cette étape Apogée',
                      'help' : """Ces étudiants sont inscrits dans ce semestre ScoDoc, ont un code NIP, mais ne sont pas inscrits dans cette étape Apogée. Soit ils sont en retard pour leur inscription, soit il s'agit d'une erreur: vérifiez avec le service Scolarité de votre établissement. Autre possibilité: votre code étape semestre (%s) est incorrect ou vous n'avez pas choisi la bonne année d'inscription.""" % sem['etape_apo'],
                      'comment' : ' à vérifier avec la Scolarité',
                      'title_target' : '',
                      'with_checkbox' : True,
                      'etud_key' : EKEY_SCO
                      }
          },
        'inscrits_without_key' :
        { 'etuds' : inscrits_without_key.values(),
          'infos' : { 'id' : 'inscrits_without_key',
                      'title' : 'Etudiants ScoDoc sans clé Apogée (NIP)',
                      'help' : """Ces étudiants sont inscrits dans ce semestre ScoDoc, mais n'ont pas de code NIP: on ne peut pas les mettre en correspondance avec Apogée. Utiliser le lien 'Changer les données identité' dans le menu 'Etudiant' sur leur fiche pour ajouter cette information.""",
                      'title_target' : '',
                      'with_checkbox' : True,
                      'checkbox_name' : 'inscrits_without_key'
                      }
        }
        }
    return r, a_importer, etuds_noninscrits, inscrits_set, inscrits_without_key, etudsapo_ident

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
    a_importer  = etudsapo_set - all_set # dans Apogee, mais inconnus dans ScoDoc
    return etuds_aposco, a_importer, key2etudid

def formsemestre_synchro_etuds_help(sem):
    return """<div class="pas_help"><h3><a name="help">Explications</a></h3>
    <p>Cette page permet d'importer dans le semestre destination
    <a class="stdlink"
    href="formsemestre_status?formsemestre_id=%(formsemestre_id)s">%(titreannee)s</a>
    les étudiants inscrits dans l'étape Apogée correspondante (<b><tt>%(etape_apo)s</tt></b>) 
    </p>
    <p>Au départ, tous les étudiants d'Apogée sont sélectionnés; vous pouvez 
    en déselectionner certains. Tous les étudiants cochés seront inscrits au semestre ScoDoc, 
    les autres seront si besoin désinscrits. Aucune modification n'est effectuée avant 
    d'appuyer sur le bouton "Appliquer les modifications".</p>

    <h4>Autres fonctions utiles</h4>
    <ul>
    <li><a href="check_group_apogee?formsemestre_id=%(formsemestre_id)s">vérification
    des codes Apogée</a> (des étudiants déjà inscrits)</li>
    <li>le <a href="formsemestre_inscr_passage?formsemestre_id=%(formsemestre_id)s">
    formulaire de passage</a> qui permet aussi de désinscrire des étudiants
    en cas d'erreur, etc.</li>
    </ul>
    </div>""" % sem



def gender2sex(gender):
    """Le portail code en 'M', 'F', et ScoDoc en 'MR', 'MME', 'MLLE'
    Les F sont ici codées en MLLE
    """
    if gender == 'M':
        return 'MR'
    elif gender == 'F':
        return 'MLLE'
    log('gender2sex: invalid value "%s", defaulting to "M"' % gender)
    return 'MR'

def get_opt_str(etud,k):
    v = etud.get(k,None)
    if not v:
        return v
    return v.strip()

def get_annee_naissance(ddmmyyyyy): # stokee en dd/mm/yyyy dans le XML portail
    if not ddmmyyyyy:
        return None
    try:
        return int(ddmmyyyyy.split('/')[2])
    except:
        return None

def do_import_etuds_from_portal(context, sem, a_importer, etudsapo_ident, REQUEST):
    """Inscrit les etudiants apogee dans ce semestre.
    """
    log('do_import_etuds_from_portal: a_importer=%s' % a_importer)
    cnx = context.GetDBConnexion()
    created_etudids = []
        
    try: # --- begin DB transaction
        for key in a_importer:
            etud = etudsapo_ident[key] # on a ici toutes les infos renvoyées par le portail

            # Traduit les infos portail en infos pour ScoDoc:
            address = etud['address'].strip()
            if address[-2:] == '\\n': # certains champs se terminent par \n
                address = address[:-2]
            args = { 'nom' : etud['nom'].strip(), 
                     'prenom' : etud['prenom'].strip(),
                     'sexe' : gender2sex(etud['gender'].strip()),
                     'annee_naissance' : get_annee_naissance(etud['naissance']),
                     'code_nip' :  etud['nip'],
                     'email' : etud['mail'].strip(),
                     'domicile' : address,
                     'codepostaldomicile' : etud['postalcode'].strip(),
                     'villedomicile' : etud['city'].strip(),
                     'paysdomicile' : etud['country'].strip(),
                     'telephone' :  etud.get('phone', '').strip(),
                     'typeadresse' : 'domicile',
                     'description' : 'infos portail',                     
                     }
            # Identite
            args['etudid'] = scolars.identite_create(cnx, args )
            created_etudids.append(args['etudid'])
            # Admissions
            do_import_etud_admission(context, cnx, args['etudid'], etud)
            
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
        context._inval_cache()
        raise

    sco_news.add(REQUEST, cnx, typ=NEWS_INSCR,
                 text='Import Apogée de %d étudiants' % len(created_etudids) )
    
def do_import_etud_admission(context, cnx, etudid, etud, import_naissance=False, import_identite=False):
    """Importe les donnees admission pour cet etud.
    etud est un dictionnaire traduit du XML portail
    """
    annee_courante = time.localtime()[0]
    serie_bac, spe_bac = get_bac(etud)
    args = {
        'etudid' : etudid,
        'annee' : get_opt_str(etud,'inscription') or annee_courante,
        'bac' : serie_bac,
        'specialite' : spe_bac,
        'annee_bac' : get_opt_str(etud,'anneebac'),
        'codelycee' : get_opt_str(etud,'lycee')
        }
    log('do_import_etud_admission: etud=%s' % etud)
    al = scolars.admission_list(cnx, args={'etudid':etudid})
    if not al:
        adm_id = scolars.admission_create(cnx, args)
    else:
        # existing data: merge
        e = al[0]
        if get_opt_str(etud,'inscription'):
            e['annee'] = args['annee']
        keys = args.keys()
        for k in keys:
            if not args[k]:
                del args[k]
        e.update(args)
        scolars.admission_edit( cnx, e )
    # Traite cas particulier de la date de naissance pour anciens etudiants IUTV
    if import_naissance:
        annee_naissance = get_annee_naissance(etud['naissance'])
        if annee_naissance:
            scolars.identite_edit_nocheck(cnx, 
                                          { 'etudid' : etudid, 'annee_naissance' : annee_naissance })
    # Reimport des identités
    if import_identite:
        args = { 'etudid' : etudid }
        annee_naissance = get_annee_naissance(etud['naissance'])
        if annee_naissance:
            args['annee_naissance'] = annee_naissance
        nom = etud.get('nom', '').strip()
        if nom:
            args['nom'] = nom
        prenom = etud.get('prenom', '').strip()
        if prenom:
            args['prenom'] = prenom
        sexe = gender2sex(etud['gender'].strip())
        if sexe:
            args['sexe'] = sexe
        scolars.identite_edit_nocheck(cnx, args)


def get_bac(etud):
    bac = get_opt_str(etud,'bac')
    if not bac:
        return None, None
    serie_bac = bac.split('-')[0]
    if len(serie_bac) < 8:
        spe_bac = bac[len(serie_bac)+1:]
    else:
        serie_bac = bac
        spe_bac = None
    return serie_bac, spe_bac

def formsemestre_import_etud_admission(context, formsemestre_id, import_identite=True):
    """Tente d'importer les données admission depuis le portail 
    pour tous les étudiants du semestre.
    Si  import_identite==True, recopie l'identité (nom/prenom/sexe/annee_naissance)
    de chaque étudiant depuis le portail.
    N'affecte pas les etudiants inconnus sur le portail. 
    """
    sem = context.get_formsemestre(formsemestre_id)
    ins = context.do_formsemestre_inscription_list( { 'formsemestre_id' : formsemestre_id } )
    log('formsemestre_import_etud_admission: %s (%d etuds)' % (formsemestre_id, len(ins)))
    no_nip = [] # liste d'etudids sans code NIP
    unknowns = [] # etudiants avec NIP mais inconnus du portail
    cnx = context.GetDBConnexion()
    for i in ins:
        etudid = i['etudid']
        info = context.getEtudInfo(etudid=etudid, filled=1)[0]
        code_nip = info['code_nip']
        if not code_nip:
            no_nip.append(etudid)
        else:
            etud = sco_portal_apogee.get_etud_apogee(context, code_nip)
            if etud:
                do_import_etud_admission(context, cnx, etudid, etud, import_naissance=True, import_identite=import_identite)
            else:
                unknowns.append(code_nip)
    return no_nip, unknowns


def do_synch_inscrits_etuds(context, sem, etuds, REQUEST=None):
    """inscrits ces etudiants (déja dans ScoDoc) au semestre"""
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
        
