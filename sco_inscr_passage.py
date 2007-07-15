# -*- mode: python -*-
# -*- coding: iso8859-15 -*-

##############################################################################
#
# Gestion scolarite IUT
#
# Copyright (c) 2001 - 2007 Emmanuel Viennet.  All rights reserved.
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
   Utilise les autorisations d'inscription d�livr�es en jury.
"""

from notesdb import *
from sco_utils import *
from notes_log import log
import sco_codes_parcours
import sco_pvjury
from sets import Set

def list_authorized_etuds_by_sem(context, sem, delai=274):
    """Liste des etudiants autoris�s � s'inscrire dans sem.
    delai = nb de jours max entre la date de l'autorisation et celle de debut du semestre cible.
    """
    src_sems = list_source_sems(context, sem, delai=delai)
    inscrits = list_inscrits(context, sem['formsemestre_id'])
    r = {}
    candidats = {} # etudid : etud (tous les etudiants candidats)
    for src in src_sems:
        liste = list_etuds_from_sem(context, src, sem)
        for e in liste:
            candidats[e['etudid']] = e
        r[src['formsemestre_id']] = { 'sem' : src,
                                      'etuds' : liste
                                      }
        # ajoute attribut inscrit qui indique si l'�tudiant est d�j� inscrit dans le semestre dest.
        for e in r[src['formsemestre_id']]['etuds']:
            e['inscrit'] = inscrits.has_key(e['etudid'])
    return r, inscrits, candidats

def list_inscrits(context, formsemestre_id):
    """Etudiants d�j� inscrits � ce semestre
    { etudid : i }
    """
    ins = context.Notes.do_formsemestre_inscription_list(
        args={  'formsemestre_id' : formsemestre_id, 'etat' : 'I' } )
    inscr={}
    for i in ins:
        etudid = i['etudid']
        inscr[etudid] = context.getEtudInfo(etudid=etudid,filled=1)[0]
    return inscr

def list_etuds_from_sem(context, src, dst):
    """Liste des etudiants du semestre src qui sont autoris�s � passer dans le semestre dst.
    """
    target = dst['semestre_id']
    dpv = sco_pvjury.dict_pvjury(context, src['formsemestre_id'])
    if not dpv:
        return []
    return [ x['identite'] for x in dpv['decisions']
             if target in [ a['semestre_id'] for a in x['autorisations'] ] ]

def do_inscrit(context, sem, etudids, REQUEST):
    """Inscrit ces etudiants dans ce semestre
    (la liste doit avoir �t� v�rifi�e au pr�alable)
    """
    log('do_inscrit: %s' % etudids)
    for etudid in etudids:
        args={ 'formsemestre_id' : sem['formsemestre_id'],
               'etudid' : etudid,
               'groupetd' : 'A', # groupe par d�faut
               'etat' : 'I'
               }
        context.do_formsemestre_inscription_with_modules(
            args = args, 
            REQUEST = REQUEST,
            method = 'formsemestre_inscr_passage' )

def do_desinscrit(context, sem, etudids, REQUEST):
    log('do_desinscrit: %s' % etudids)
    for etudid in etudids:
        context.do_formsemestre_desinscription(etudid, sem['formsemestre_id'])


def list_source_sems(context, sem, delai=None):
    """Liste des semestres sources
    sem est le semestre destination
    """
    # liste des semestres d�butant a moins
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
                continue # semestre trop r�cent
        # Elimine les semestres de formations speciales (sans parcours)
        if s['semestre_id'] == sco_codes_parcours.NO_SEMESTRE_ID:
            continue
        #
        if not sco_codes_parcours.ALLOW_SEM_SKIP:
            if s['semestre_id'] < (sem['semestre_id']-1):
                continue
        othersems.append(s)
    return othersems


def formsemestre_inscr_passage(context, formsemestre_id, etuds=[],
                               submitted=False, dialog_confirmed=False,
                               REQUEST=None):
    """Form. pour inscription des etudiants d'un semestre dans un autre
    (donn� par formsemestre_id).
    Permet de selectionner parmi les etudiants autoris�s � s'inscrire.
    Principe:
    - trouver liste d'etud, par semestre
    - afficher chaque semestre "boites" avec cases � cocher
    - si l'�tudiant est d�j� inscrit, le signaler (gras, nom de groupes): il peut �tre d�sinscrit
    - on peut choisir les groupes TD, TP, TA
    - seuls les etudiants non inscrits changent (de groupe)
    - les etudiants inscrit qui se trouvent d�coch�s sont d�sinscrits
    - Confirmation: indiquer les �tudiants inscrits et ceux d�sinscrits, le total courant.    

    """
    log('formsemestre_inscr_passage: formsemestre_id=%s submitted=%s, dialog_confirmed=%s'
        % (formsemestre_id, submitted, dialog_confirmed) )
    cnx = context.GetDBConnexion()
    sem = context.get_formsemestre(formsemestre_id)
    # -- check lock
    if sem['etat'] != '1':
        raise ScoValueError('op�ration impossible: semestre verrouille')
    header = context.sco_header(REQUEST, page_title='Passage des �tudiants')
    footer = context.sco_footer(REQUEST)
    H = [header]
    if type(etuds) == type(''):
        etuds = etuds.split(',') # vient du form de confirmation
    
    sem = context.get_formsemestre(formsemestre_id)
    auth_etuds_by_sem, inscrits, candidats = list_authorized_etuds_by_sem(context, sem)
    etuds_set = Set(etuds)
    candidats_set = Set(candidats)
    inscrits_set = Set(inscrits)
    candidats_non_inscrits = candidats_set - inscrits_set
    if submitted:
        a_inscrire = etuds_set.intersection(candidats_set) - inscrits_set
        a_desinscrire = inscrits_set.intersection(candidats_set) - etuds_set
    else:
        a_inscrire = a_desinscrire = []    
    log('formsemestre_inscr_passage: a_inscrire=%s' % str(a_inscrire) )
    log('formsemestre_inscr_passage: a_desinscrire=%s' % str(a_desinscrire) )
    
    if not submitted:
        H.append( build_page(context, sem, auth_etuds_by_sem, inscrits, candidats_non_inscrits) )
    else:
        if not dialog_confirmed:
            # Confirmation
            if a_inscrire:
                H.append('<h3>Etudiants � inscrire</h3><ol>')
                for etudid in a_inscrire:
                    H.append('<li>%s</li>' % context.nomprenom(candidats[etudid]))
                H.append('</ol>')
            if a_desinscrire:
                H.append('<h3>Etudiants � d�sinscrire</h3><ol>')
                for etudid in a_desinscrire:
                    H.append('<li>%s</li>' % context.nomprenom(candidats[etudid]))
                H.append('</ol>')
            if not a_inscrire and not a_desinscrire:
                H.append("""<h3>Il n'y a rien � modifier !</h3>""")
            H.append( context.confirmDialog( dest_url="formsemestre_inscr_passage",
                                             add_headers=False,
                                             cancel_url="formsemestre_inscr_passage?formsemestre_id="+formsemestre_id,
                                             OK = "Effectuer l'op�ration",
                                             parameters = {'formsemestre_id' : formsemestre_id,
                                                           'etuds' : ','.join(etuds),
                                                           'submitted' : 1, 
                                                           }) )
        else:
            # OK, do it
            do_inscrit(context, sem, a_inscrire, REQUEST)
            do_desinscrit(context, sem, a_desinscrire, REQUEST)
            
            H.append("""<h3>Op�ration effectu�e</h3>
            <ul><li><a class="stdlink" href="formsemestre_inscr_passage?formsemestre_id=%s">Continuer les inscriptions</a></li>
                <li><a class="stdlink" href="formsemestre_status?formsemestre_id=%s">Tableau de bord du semestre</a></li>
                <li><a class="stdlink" href="affectGroupes?formsemestre_id=%s&groupType=TD&groupTypeName=%s">R�partir les groupes de %s</a></li>
                """ % (formsemestre_id,formsemestre_id,formsemestre_id,sem['nomgroupetd'],sem['nomgroupetd']))
            
    #
    H.append(footer)
    return '\n'.join(H)



def build_page(context, sem, auth_etuds_by_sem, inscrits, candidats_non_inscrits):
    "code HTML"
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
    </script>""",
        """<h2>Inscriptions dans le semestre <a href="formsemestre_status?formsemestre_id=%(formsemestre_id)s">%(titreannee)s</a></h2>
    <form method="post">
    <input type="hidden" name="formsemestre_id" value="%(formsemestre_id)s"/>
    <input type="submit" name="submitted" value="Appliquer les modifications"/>
    &nbsp;<a href="#help">aide</a>
    """ % sem ] # "
    # nombre total d'inscrits
    H.append("""<div class="pas_recap">Actuellement <span id="nbinscrits">%s</span> inscrits
    et %d candidats suppl�mentaires
    </div>""" % (len(inscrits), len(candidats_non_inscrits)) )

    empty_sems = []
    for src_formsemestre_id in auth_etuds_by_sem.keys():
        src = auth_etuds_by_sem[src_formsemestre_id]['sem']
        etuds = auth_etuds_by_sem[src_formsemestre_id]['etuds']
        if etuds:
            src['nbetuds'] = len(etuds)
            H.append("""<div class="pas_sembox" id="%(formsemestre_id)s">
                <div class="pas_sembox_title"><a href="formsemestre_status?formsemestre_id=%(formsemestre_id)s">%(titreannee)s</a></div>
                <div class="pas_sembox_subtitle">(%(nbetuds)d �tudiants) (Select.
                <a href="#" onclick="sem_select('%(formsemestre_id)s', true);">tous</a>
                <a href="#" onclick="sem_select('%(formsemestre_id)s', false );">aucun</a>
                <a href="#" onclick="sem_select_inscrits('%(formsemestre_id)s');">inscrits</a>
                     )</div>""" % src ) # "
            for etud in etuds:
                if etud['inscrit']:
                    c = ' inscrit'
                    checked = 'checked="checked"'
                else:
                    c = ''
                    checked = ''
                H.append("""<div class="pas_etud%s">""" % c )
                H.append("""<input type="checkbox" name="etuds" value="%s" %s><a class="discretelink" href="ficheEtud?etudid=%s">%s</a></input></div>"""
                         % (etud['etudid'], checked, etud['etudid'], context.nomprenom(etud)) )
            H.append('</div>')
        else:
            empty_sems.append(src)
            
    # Semestres sans etudiants autoris�s
    if empty_sems:
        H.append("""<div class="pas_empty_sems"><H3>Autres semestres sans candidats :</h3><ul>""")
        for src in empty_sems:
            H.append("""<li><a href="formsemestre_status?formsemestre_id=(formsemestre_id)s">
            %(titreannee)s</a></li>""" % src)
        H.append("""</ul></div>""")
    
    H.append("""</form>""")
    H.append("""<div class="pas_help"><h3><a name="help">Explications</a></h3>
    <p>Cette page permet d'inscrire des �tudiants dans le semestre destination
    <a class="stdlink" href="formsemestre_status?formsemestre_id=(formsemestre_id)s">%(titreannee)s</a>.</p>
    <p>Les �tudiants sont group�s par semestre d'origine. Ceux qui sont en caract�res <b>gras</b> sont
    d�j� inscrits dans le semestre destination.</p>
    <p>Au d�part, les �tudiants d�j� inscrits sont s�lectionn�s; vous pouvez ajouter d'autres
    �tudiants � inscrire dans le semestre destination.</p>
    <p>Si vous d�-selectionnez un �tudiant d�j� inscrit (en gras), il sera d�sinscrit.</p>
    </div>""" % sem )
    return '\n'.join(H)
