# -*- mode: python -*-
# -*- coding: iso8859-15 -*-

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

"""Form. pour inscription rapide des etudiants d'un semestre dans un autre
   Utilise les autorisations d'inscription délivrées en jury.
"""

from notesdb import *
from sco_utils import *
from notes_log import log
import sco_codes_parcours
import sco_pvjury
import sco_formsemestre_inscriptions
from sets import Set
from gen_tables import GenTable
import sco_groups

def list_authorized_etuds_by_sem(context, sem, delai=274):
    """Liste des etudiants autorisés à s'inscrire dans sem.
    delai = nb de jours max entre la date de l'autorisation et celle de debut du semestre cible.
    """
    src_sems = list_source_sems(context, sem, delai=delai)
    inscrits = list_inscrits(context, sem['formsemestre_id'])
    r = {}
    candidats = {} # etudid : etud (tous les etudiants candidats)
    nb=0 # debug
    for src in src_sems:
        liste = list_etuds_from_sem(context, src, sem)
        liste_filtree = []
        for e in liste:
            # Filtre ceux qui se sont déjà inscrit dans un semestre APRES le semestre src
            auth_used = False # autorisation deja utilisée ?
            etud = context.getEtudInfo(etudid=e['etudid'], filled=True)[0]
            for isem in etud['sems']:
                if DateDMYtoISO(isem['date_debut']) >= DateDMYtoISO(src['date_fin']):
                    auth_used = True
            if not auth_used:
                candidats[e['etudid']] = e
                liste_filtree.append(e)
                nb+=1        
        r[src['formsemestre_id']] = {
            'etuds' : liste_filtree,
            'infos' : { 'id' : src['formsemestre_id'],
                        'title' : src['titreannee'],
                        'title_target' : 'formsemestre_status?formsemestre_id=%s' % src['formsemestre_id']
                        }
            }
        # ajoute attribut inscrit qui indique si l'étudiant est déjà inscrit dans le semestre dest.
        for e in r[src['formsemestre_id']]['etuds']:
            e['inscrit'] = inscrits.has_key(e['etudid'])

    # Ajoute liste des etudiants actuellement inscrits  
    for e in inscrits.values():
        e['inscrit'] = True
    r[sem['formsemestre_id']] = {
        'etuds' : inscrits.values(),
        'infos' : { 'id' : sem['formsemestre_id'],
                    'title' : 'Semestre cible: ' + sem['titreannee'],
                    'title_target' : 'formsemestre_status?formsemestre_id=%s' % sem['formsemestre_id'],
                    'comment' : ' actuellement inscrits dans ce semestre',
                    'help' : 'Ces étudiants sont actuellement inscrits dans ce semestre. Si vous les décochez, il seront désinscrits.'
                    }
        }
    
    return r, inscrits, candidats

def list_inscrits(context, formsemestre_id, with_dems=False):
    """Etudiants déjà inscrits à ce semestre
    { etudid : etud }
    """
    if not with_dems:
        ins = context.Notes.do_formsemestre_inscription_listinscrits(formsemestre_id) # optimized
    else:
        args = {  'formsemestre_id' : formsemestre_id }        
        ins = context.Notes.do_formsemestre_inscription_list(args=args)
    inscr={}
    for i in ins:
        etudid = i['etudid']
        inscr[etudid] = context.getEtudInfo(etudid=etudid,filled=True)[0]
    return inscr

def list_etuds_from_sem(context, src, dst):
    """Liste des etudiants du semestre src qui sont autorisés à passer dans le semestre dst.
    """
    target = dst['semestre_id']
    dpv = sco_pvjury.dict_pvjury(context, src['formsemestre_id'])
    if not dpv:
        return []
    return [ x['identite'] for x in dpv['decisions']
             if target in [ a['semestre_id'] for a in x['autorisations'] ] ]

def list_inscrits_date(context, sem):
    """Liste les etudiants inscrits dans n'importe quel semestre
    SAUF sem à la date de début de sem.
    """    
    cnx = context.GetDBConnexion()
    cursor = cnx.cursor()
    sem['date_debut_iso'] = DateDMYtoISO(sem['date_debut'])
    cursor.execute("""select I.etudid
                      from notes_formsemestre_inscription I, notes_formsemestre S
                      where I.formsemestre_id = S.formsemestre_id
                      and I.formsemestre_id != %(formsemestre_id)s
                      and S.date_debut <= %(date_debut_iso)s
                      and S.date_fin >= %(date_debut_iso)s""", sem)
    return [ x[0] for x in cursor.fetchall() ]
                      
def do_inscrit(context, sem, etudids, REQUEST):
    """Inscrit ces etudiants dans ce semestre
    (la liste doit avoir été vérifiée au préalable)
    """
    log('do_inscrit: %s' % etudids)
    for etudid in etudids:
        sco_formsemestre_inscriptions.do_formsemestre_inscription_with_modules(
            context, sem['formsemestre_id'], etudid,
            etat = 'I',
            REQUEST = REQUEST,
            method = 'formsemestre_inscr_passage' )

def do_desinscrit(context, sem, etudids, REQUEST):
    log('do_desinscrit: %s' % etudids)
    for etudid in etudids:
        context.do_formsemestre_desinscription(etudid, sem['formsemestre_id'], REQUEST=REQUEST)


def list_source_sems(context, sem, delai=None):
    """Liste des semestres sources
    sem est le semestre destination
    """
    # liste des semestres débutant a moins
    # de 123 jours (4 mois) de la date de fin du semestre d'origine.
    sems = context.do_formsemestre_list()
    othersems = []
    d,m,y = [ int(x) for x in sem['date_debut'].split('/') ]
    date_debut_dst = datetime.date(y,m,d)
    d,m,y = [ int(x) for x in sem['date_fin'].split('/') ]
    date_fin_dst = datetime.date(y,m,d)
    
    delais = datetime.timedelta(delai)
    for s in sems:
        #pdb.set_trace()
        #if s['etat'] != '1':
        #    continue # saute semestres pas ouverts
        if s['formsemestre_id'] == sem['formsemestre_id']:
            continue # saute le semestre destination
        if s['date_fin']:
            d,m,y = [ int(x) for x in s['date_fin'].split('/') ]
            date_fin = datetime.date(y,m,d)            
            if date_debut_dst - date_fin  > delais:
                continue # semestre trop ancien            
            if date_fin > date_debut_dst: 
                continue # semestre trop récent
        # Elimine les semestres de formations speciales (sans parcours)
        if s['semestre_id'] == sco_codes_parcours.NO_SEMESTRE_ID:
            continue
        #
        F = context.formation_list(args={ 'formation_id' :s['formation_id']})[0]
        parcours = sco_codes_parcours.get_parcours_from_code(F['type_parcours'])
        if not parcours.ALLOW_SEM_SKIP:
            if s['semestre_id'] < (sem['semestre_id']-1):
                continue
        othersems.append(s)
    return othersems

def formsemestre_inscr_passage(context, formsemestre_id, etuds=[],
                               submitted=False, dialog_confirmed=False,
                               REQUEST=None):
    """Form. pour inscription des etudiants d'un semestre dans un autre
    (donné par formsemestre_id).
    Permet de selectionner parmi les etudiants autorisés à s'inscrire.
    Principe:
    - trouver liste d'etud, par semestre
    - afficher chaque semestre "boites" avec cases à cocher
    - si l'étudiant est déjà inscrit, le signaler (gras, nom de groupes): il peut être désinscrit
    - on peut choisir les groupes TD, TP, TA
    - seuls les etudiants non inscrits changent (de groupe)
    - les etudiants inscrit qui se trouvent décochés sont désinscrits
    - Confirmation: indiquer les étudiants inscrits et ceux désinscrits, le total courant.    

    """
    #log('formsemestre_inscr_passage: formsemestre_id=%s submitted=%s, dialog_confirmed=%s len(etuds)=%d'
    #    % (formsemestre_id, submitted, dialog_confirmed, len(etuds)) )
    cnx = context.GetDBConnexion()
    sem = context.get_formsemestre(formsemestre_id)
    # -- check lock
    if sem['etat'] != '1':
        raise ScoValueError('opération impossible: semestre verrouille')
    header = context.sco_header(REQUEST, page_title='Passage des étudiants')
    footer = context.sco_footer(REQUEST)
    H = [header]
    if type(etuds) == type(''):
        etuds = etuds.split(',') # vient du form de confirmation
    
    auth_etuds_by_sem, inscrits, candidats = list_authorized_etuds_by_sem(context, sem)
    etuds_set = Set(etuds)
    candidats_set = Set(candidats)
    inscrits_set = Set(inscrits)
    candidats_non_inscrits = candidats_set - inscrits_set
    inscrits_ailleurs = Set(list_inscrits_date(context, sem))

    def set_to_sorted_etud_list(etudset):
        etuds = [ candidats[etudid] for etudid in etudset ]
        etuds.sort( lambda x,y: cmp(x['nom'], y['nom']) )
        return etuds

    if submitted:
        a_inscrire = etuds_set.intersection(candidats_set) - inscrits_set
        a_desinscrire = inscrits_set - etuds_set
    else:
        a_inscrire = a_desinscrire = []    
    #log('formsemestre_inscr_passage: a_inscrire=%s' % str(a_inscrire) )
    #log('formsemestre_inscr_passage: a_desinscrire=%s' % str(a_desinscrire) )
    
    if not submitted:
        H += build_page(context, REQUEST, sem, auth_etuds_by_sem,
                        inscrits, candidats_non_inscrits,
                        inscrits_ailleurs)
    else:
        if not dialog_confirmed:
            # Confirmation
            if a_inscrire:
                H.append('<h3>Etudiants à inscrire</h3><ol>')
                for etud in set_to_sorted_etud_list(a_inscrire):
                    H.append('<li>%s</li>' % context.nomprenom(etud))
                H.append('</ol>')
            a_inscrire_en_double = inscrits_ailleurs.intersection(a_inscrire)
            if a_inscrire_en_double:
                H.append('<h3>dont étudiants déjà inscrits:</h3><ul>')
                for etud in set_to_sorted_etud_list(a_inscrire_en_double):
                    H.append('<li class="inscrailleurs">%s</li>' % context.nomprenom(etud))
                H.append('</ul>')
            if a_desinscrire:
                H.append('<h3>Etudiants à désinscrire</h3><ol>')
                for etudid in a_desinscrire:
                    H.append('<li class="desinscription">%s</li>' % context.nomprenom(inscrits[etudid]))
                H.append('</ol>')
            if not a_inscrire and not a_desinscrire:
                H.append("""<h3>Il n'y a rien à modifier !</h3>""")
            H.append( context.confirmDialog( dest_url="formsemestre_inscr_passage",
                                             add_headers=False,
                                             cancel_url="formsemestre_inscr_passage?formsemestre_id="+formsemestre_id,
                                             OK = "Effectuer l'opération",
                                             parameters = {'formsemestre_id' : formsemestre_id,
                                                           'etuds' : ','.join(etuds),
                                                           'submitted' : 1, 
                                                           }) )
        else:
            # OK, do it
            do_inscrit(context, sem, a_inscrire, REQUEST)
            do_desinscrit(context, sem, a_desinscrire, REQUEST)
            
            H.append("""<h3>Opération effectuée</h3>
            <ul><li><a class="stdlink" href="formsemestre_inscr_passage?formsemestre_id=%s">Continuer les inscriptions</a></li>
                <li><a class="stdlink" href="formsemestre_status?formsemestre_id=%s">Tableau de bord du semestre</a></li>""" % (formsemestre_id,formsemestre_id))
            partition = sco_groups.formsemestre_get_main_partition(context, formsemestre_id)
            if partition['partition_id'] != sco_groups.formsemestre_get_main_partition(context, formsemestre_id)['partition_id']: # il y a au moins une vraie partition
                H.append("""<li><a class="stdlink" href="affectGroups?partition_id=%s">Répartir les groupes de %s</a></li>
                """ % (partition['partition_id'],partition['partition_name']))
            
    #
    H.append(footer)
    return '\n'.join(H)


def build_page(context, REQUEST, sem, auth_etuds_by_sem, inscrits,
               candidats_non_inscrits, inscrits_ailleurs ):
    H = [ context.html_sem_header(REQUEST, 'Passages dans le semestre', sem, with_page_header=False),
          """<form method="post" action="%s">""" % REQUEST.URL0,
          """<input type="hidden" name="formsemestre_id" value="%(formsemestre_id)s"/>
    <input type="submit" name="submitted" value="Appliquer les modifications"/>
    &nbsp;<a href="#help">aide</a>
    """ % sem, # "

        """<div class="pas_recap">Actuellement <span id="nbinscrits">%s</span> inscrits
        et %d candidats supplémentaires
        </div>""" % (len(inscrits), len(candidats_non_inscrits)),
        
          etuds_select_boxes(context, auth_etuds_by_sem, inscrits_ailleurs ),
        
          """<p/><input type="submit" name="submitted" value="Appliquer les modifications"/>""",

          formsemestre_inscr_passage_help(sem),
          """</form>"""
        ]

    # Semestres sans etudiants autorisés
    empty_sems = []
    for formsemestre_id in auth_etuds_by_sem.keys():
        if not auth_etuds_by_sem[formsemestre_id]['etuds']:
            empty_sems.append(auth_etuds_by_sem[formsemestre_id]['infos'])
    if empty_sems:
        H.append("""<div class="pas_empty_sems"><h3>Autres semestres sans candidats :</h3><ul>""")
        for infos in empty_sems:
            H.append("""<li><a href="%(title_target)s">%(title)s</a></li>""" % infos)
        H.append("""</ul></div>""")

    return H

def formsemestre_inscr_passage_help(sem):
    return """<div class="pas_help"><h3><a name="help">Explications</a></h3>
    <p>Cette page permet d'inscrire des étudiants dans le semestre destination
    <a class="stdlink"
    href="formsemestre_status?formsemestre_id=%(formsemestre_id)s">%(titreannee)s</a>, 
    et d'en désincrire si besoin.
    </p>
    <p>Les étudiants sont groupés par semestres d'origines. Ceux qui sont en caractères
    <span class="inscrit">gras</span> sont déjà inscrits dans le semestre destination.
    Ceux qui sont en <span class"inscrailleurs">gras et en rouge</span> sont inscrits
    dans un <em>autre</em> semestre.</p>
    <p>Au départ, les étudiants déjà inscrits sont sélectionnés; vous pouvez ajouter d'autres
    étudiants à inscrire dans le semestre destination.</p>
    <p>Si vous dé-selectionnez un étudiant déjà inscrit (en gras), il sera désinscrit.</p>
    <p class="help">Aucune action ne sera effectuée si vous n'appuyez pas sur le bouton "Appliquer les modifications" !</p>
    </div>""" % sem 


def etuds_select_boxes(context, auth_etuds_by_cat,
                       inscrits_ailleurs={}, sel_inscrits=True,
                       show_empty_boxes=False,
                       export_cat_xls=None, base_url=''
                       ):
    """Boites pour selection étudiants par catégorie
    auth_etuds_by_cat = { category : { 'info' : {}, 'etuds' : ... }
    inscrits_ailleurs =
    sel_inscrits= 
    export_cat_xls =
    """
    if export_cat_xls:
        return etuds_select_box_xls(context,auth_etuds_by_cat[export_cat_xls])
    
    H = [ """<script type="text/javascript">
    function sem_select(formsemestre_id, state) {
    var elems = document.getElementById(formsemestre_id).getElementsByTagName("input");
    for (var i =0; i < elems.length; i++) { elems[i].checked=state; }
    }
    function sem_select_inscrits(formsemestre_id) {
    var elems = document.getElementById(formsemestre_id).getElementsByTagName("input");
    for (var i =0; i < elems.length; i++) {
      if (elems[i].parentNode.className.indexOf('inscrit') >= 0) {
         elems[i].checked=true;
      } else {
         elems[i].checked=false;
      }      
    }
    }
    </script>
    <div class="etuds_select_boxes">""",
          ] # "

    for src_cat in auth_etuds_by_cat.keys():
        infos = auth_etuds_by_cat[src_cat]['infos']
        infos['comment'] = infos.get('comment', '') # commentaire dans sous-titre boite
        help = infos.get('help', '')
        etuds = auth_etuds_by_cat[src_cat]['etuds']
        with_checkbox = auth_etuds_by_cat[src_cat]['infos'].get('with_checkbox', True)
        checkbox_name = auth_etuds_by_cat[src_cat]['infos'].get('checkbox_name', 'etuds')
        etud_key = auth_etuds_by_cat[src_cat]['infos'].get('etud_key', 'etudid')
        if etuds or show_empty_boxes: 
            infos['nbetuds'] = len(etuds)
            H.append("""<div class="pas_sembox" id="%(id)s">
                <div class="pas_sembox_title"><a href="%(title_target)s" """ % infos)
            if help: # bubble
                H.append('title="%s"' % help)
            H.append(""">%(title)s</a></div>
                <div class="pas_sembox_subtitle">(%(nbetuds)d étudiants%(comment)s)""" % infos )
            if with_checkbox:
                H.append(""" (Select.
                <a href="#" onclick="sem_select('%(id)s', true);">tous</a>
                <a href="#" onclick="sem_select('%(id)s', false );">aucun</a>""" # "
                     % infos )
            if sel_inscrits:
                H.append("""<a href="#" onclick="sem_select_inscrits('%(id)s');">inscrits</a>"""
                         % infos)
            if with_checkbox or sel_inscrits:
                H.append(')')
            if base_url and etuds:
                H.append('<a href="%s&export_cat_xls=%s">%s</a>&nbsp;' % (base_url, src_cat, ICON_XLS))
            H.append('</div>' )
            for etud in etuds:
                if etud.get('inscrit', False):
                    c = ' inscrit'
                    checked = 'checked="checked"'
                else:
                    checked = ''
                    if etud['etudid'] in inscrits_ailleurs:
                        c = ' inscrailleurs'
                    else:
                        c = ''
                if etud['etudid']:
                    elink = """<a class="discretelink %s" href="ficheEtud?etudid=%s">%s</a>""" % (
                        c, etud['etudid'], context.nomprenom(etud))
                else:
                    elink = context.nomprenom(etud)
                if not etud.get('paiementinscription', True):
                    elink = '<span class="paspaye">' + elink + ' (non paiement)</span>'
                H.append("""<div class="pas_etud%s">""" % c )
                if with_checkbox:
                    H.append("""<input type="checkbox" name="%s:list" value="%s" %s>"""
                             % (checkbox_name, etud[etud_key], checked) )
                H.append(elink)
                if with_checkbox:
                     H.append("""</input>""")
                H.append('</div>')
            H.append('</div>')
    
    H.append('</div>')
    return '\n'.join(H)

def etuds_select_box_xls(context, src_cat):
    "export a box to excel"
    etuds = src_cat['etuds']
    columns_ids = [ 'etudid', 'sexe', 'nom', 'prenom' ]
    titles = {}
    map( lambda x,titles=titles: titles.__setitem__(x[0],x[1]), zip(columns_ids,columns_ids) )
    # Ajoute colonne paiement inscription
    columns_ids.append('paiementinscription_str')
    titles['paiementinscription_str'] = 'paiement inscription'
    for e in etuds:
        if not e.get('paiementinscription', True):
            e['paiementinscription_str'] = 'NON'
        else:
            e['paiementinscription_str'] = '-'
    tab = GenTable( titles=titles, columns_ids=columns_ids, rows=etuds,
                    caption='%(title)s. %(help)s' % src_cat['infos'],
                    preferences=context.get_preferences()
                    )
    return tab.excel()
