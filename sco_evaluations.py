# -*- mode: python -*-
# -*- coding: iso8859-15 -*-

##############################################################################
#
# Gestion scolarite IUT
#
# Copyright (c) 2001 - 2010 Emmanuel Viennet.  All rights reserved.
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
#   Emmanuel Viennet      emmanuel.viennet@gmail.com
#
##############################################################################

"""Evaluations
"""
from sets import Set

from notes_log import log
from sco_utils import *
import sco_news
import sco_groups
import ZAbsences

# --------------------------------------------------------------------
#
#    MISC AUXILIARY FUNCTIONS
#
# --------------------------------------------------------------------
def notes_moyenne_median(notes):
    "calcule moyenne et mediane d'une liste de valeurs (floats)"
    notes = [ x for x in notes if (x != None) and (x != NOTES_NEUTRALISE) and (x != NOTES_ATTENTE) ]
    n = len(notes)
    if not n:
        return None, None
    moy = sum(notes) / n
    median = ListMedian(notes)
    return moy, median

def ListMedian( L ):
    """Median of a list L"""
    n = len(L)
    if not n:
	raise ValueError, 'empty list'
    L.sort()
    if n % 2:
	return L[n/2]
    else:
	return (L[n/2] + L[n/2-1])/2 

# --------------------------------------------------------------------

def do_evaluation_delete(context, REQUEST, evaluation_id):
    "delete evaluation"
    the_evals = context.do_evaluation_list( 
            {'evaluation_id' : evaluation_id})
    if not the_evals:
        raise ValueError("evaluation inexistante !")

    NotesDB = context._notes_getall(evaluation_id) # { etudid : value }
    notes = [ x['value'] for x in NotesDB.values() ]
    if notes:
        raise ScoValueError("Impossible de supprimer cette évaluation: il reste des notes")

    moduleimpl_id = the_evals[0]['moduleimpl_id']
    context._evaluation_check_write_access( REQUEST, moduleimpl_id=moduleimpl_id)
    cnx = context.GetDBConnexion()

    context._evaluationEditor.delete(cnx, evaluation_id)
    # inval cache pour ce semestre
    M = context.do_moduleimpl_list( args={ 'moduleimpl_id':moduleimpl_id } )[0]
    context._inval_cache(formsemestre_id=M['formsemestre_id']) #> eval delete
    # news
    mod = context.do_module_list( args={ 'module_id':M['module_id'] } )[0]
    mod['moduleimpl_id'] = M['moduleimpl_id']
    mod['url'] = "Notes/moduleimpl_status?moduleimpl_id=%(moduleimpl_id)s"%mod
    sco_news.add(REQUEST, cnx, typ=sco_news.NEWS_NOTE, object=moduleimpl_id,
                 text='Suppression d\'une évaluation dans <a href="%(url)s">%(titre)s</a>' % mod,
                 url=mod['url'])


def do_evaluation_etat(context, evaluation_id, partition_id=None, select_first_partition=False):
    """donne infos sur l'etat du evaluation
    { nb_inscrits, nb_notes, nb_abs, nb_neutre, nb_att, moyenne, mediane,
    date_last_modif, gr_complets, gr_incomplets, evalcomplete }
    evalcomplete est vrai si l'eval est complete (tous les inscrits
    à ce module ont des notes)
    evalattente est vrai s'il ne manque que des notes en attente
    """
    #log('do_evaluation_etat: evaluation_id=%s  partition_id=%s' % (evaluation_id, partition_id))
    nb_inscrits = len(sco_groups.do_evaluation_listeetuds_groups(context, evaluation_id,getallstudents=True))
    NotesDB = context._notes_getall(evaluation_id) # { etudid : value }
    notes = [ x['value'] for x in NotesDB.values() ]
    nb_abs = len( [ x for x in notes if x is None ] )
    nb_neutre = len( [ x for x in notes if x == NOTES_NEUTRALISE ] )
    nb_att = len( [ x for x in notes if x == NOTES_ATTENTE ] )
    moy, median = notes_moyenne_median(notes)
    if moy is None:
        median, moy = '',''
    else:
        median = fmt_note(median) # '%.3g' % median
        moy = fmt_note(moy) # '%.3g' % moy
    # cherche date derniere modif note
    if len(NotesDB):
        t = [ x['date'] for x in NotesDB.values() ]
        last_modif = max(t)
    else:
        last_modif = None
    # ---- Liste des groupes complets et incomplets
    E = context.do_evaluation_list( args={ 'evaluation_id' : evaluation_id } )[0]
    M = context.do_moduleimpl_list( args={ 'moduleimpl_id' : E['moduleimpl_id']})[0]
    formsemestre_id = M['formsemestre_id']
    # Si partition_id is None, prend 'all' ou bien la premiere:
    if partition_id is None:
        if select_first_partition:
            partitions = sco_groups.get_partitions_list(context, formsemestre_id)
            partition = partitions[0]
        else:
            partition = sco_groups.get_default_partition(context, formsemestre_id)
        partition_id = partition['partition_id']

    # Il faut considerer les inscription au semestre
    # (pour avoir l'etat et le groupe) et aussi les inscriptions
    # au module (pour gerer les modules optionnels correctement)
    insem = context.do_formsemestre_inscription_listinscrits(formsemestre_id)
    insmod = context.do_moduleimpl_inscription_list(
        args={ 'moduleimpl_id' : E['moduleimpl_id'] } )
    insmodset = Set( [ x['etudid'] for x in insmod ] )
    # retire de insem ceux qui ne sont pas inscrits au module
    ins = [ i for i in insem if i['etudid'] in insmodset ]
    
    # Nombre de notes valides d'étudiants inscrits au module
    # (car il peut y avoir des notes d'étudiants désinscrits depuis l'évaluation)
    nb_notes = len( insmodset.intersection(NotesDB) )
    nb_notes_total = len(NotesDB)
    
    # On considere une note "manquante" lorsqu'elle n'existe pas
    # ou qu'elle est en attente (ATT)
    GrNbMissing = DictDefault() # group_id : nb notes manquantes
    GrNotes = DictDefault(defaultvalue=[]) # group_id: liste notes valides
    TotalNbMissing = 0
    TotalNbAtt = 0
    groups = {} # group_id : group
    etud_groups = sco_groups.get_etud_groups_in_partition(context, partition_id)

    for i in ins:
        group = etud_groups.get( i['etudid'], None )
        if group and not group['group_id'] in groups:
            groups[group['group_id']] = group
        # 
        isMissing = False
        if NotesDB.has_key(i['etudid']):
            val = NotesDB[i['etudid']]['value']
            if val == NOTES_ATTENTE:
                isMissing = True
                TotalNbAtt += 1
            if group:
                GrNotes[group['group_id']].append( val )
        else:
            if group:
                junk = GrNotes[group['group_id']] # create group
            isMissing = True
        if isMissing:
            TotalNbMissing += 1
            if group:
                GrNbMissing[group['group_id']] += 1

    gr_incomplets = [ x for x in GrNbMissing.keys() ]
    gr_incomplets.sort()
    if TotalNbMissing > 0:
        complete = False
    else:
        complete = True            
    if TotalNbMissing > 0 and TotalNbMissing == TotalNbAtt:
        evalattente = True
    else:
        evalattente = False
    # calcul moyenne dans chaque groupe de TD
    gr_moyennes = [] # group : {moy,median, nb_notes}
    for group_id in GrNotes.keys():
        notes = GrNotes[group_id]
        gr_moy, gr_median = notes_moyenne_median(notes)
        gr_moyennes.append(
            {'group_id':group_id, 
             'group_name' : groups[group_id]['group_name'],
             'gr_moy' : fmt_note(gr_moy),
             'gr_median':fmt_note(gr_median),
             'gr_nb_notes': len(notes),
             'gr_nb_att' : len([ x for x in notes if x == NOTES_ATTENTE ])
             } )
    gr_moyennes.sort(key=operator.itemgetter('group_name'))
    #log('gr_moyennes=%s' % gr_moyennes) 
    # retourne mapping
    return {
        'evaluation_id' : evaluation_id,
        'nb_inscrits':nb_inscrits, 
        'nb_notes':nb_notes, # nb notes etudiants inscrits
        'nb_notes_total' : nb_notes_total, # nb de notes (incluant desinscrits)
        'nb_abs':nb_abs, 'nb_neutre':nb_neutre, 'nb_att' : nb_att,
        'moy':moy, 'median':median,
        'last_modif':last_modif,
        'gr_incomplets':gr_incomplets,
        'gr_moyennes' : gr_moyennes,
        'groups' : groups,
        'evalcomplete' : complete,
        'evalattente' : evalattente }


def do_evaluation_list_in_sem(context, formsemestre_id):
    """Liste des evaluations pour un semestre (dans tous les modules de ce semestre).
    Donne pour chaque eval son état (voir do_evaluation_etat)
    { evaluation_id,nb_inscrits, nb_notes, nb_abs, nb_neutre, moy, median, last_modif ... }
    """
    req = "select evaluation_id from notes_evaluation E, notes_moduleimpl MI where MI.formsemestre_id = %(formsemestre_id)s and MI.moduleimpl_id = E.moduleimpl_id"
    cnx = context.GetDBConnexion()
    cursor = cnx.cursor()    
    cursor.execute( req, { 'formsemestre_id' : formsemestre_id } )
    res = cursor.fetchall()
    evaluation_ids = [ x[0] for x in res ]
    #
    R = []
    for evaluation_id in evaluation_ids:
        R.append( do_evaluation_etat(context, evaluation_id) )
    return R 

def formsemestre_evaluations_list(context, formsemestre_id):
    """Liste des evals pour ce semestre"""
    req = "select E.* from notes_evaluation E, notes_moduleimpl MI where MI.formsemestre_id = %(formsemestre_id)s and MI.moduleimpl_id = E.moduleimpl_id"
    cnx = context.GetDBConnexion()
    cursor = cnx.cursor()    
    cursor.execute( req, { 'formsemestre_id' : formsemestre_id } )
    return cursor.dictfetchall()

def _eval_etat(evals):
    """evals: list of mappings (etats)
    -> nb_eval_completes, nb_evals_en_cours,
    nb_evals_vides, date derniere modif

    Une eval est "complete" ssi tous les etudiants *inscrits* ont une note.

    """
    nb_evals_completes, nb_evals_en_cours, nb_evals_vides = 0,0,0
    dates = []
    for e in evals:
        if e['evalcomplete']:
            nb_evals_completes += 1
        elif e['nb_notes'] == 0: # nb_notes == 0
            nb_evals_vides += 1
        else:
            nb_evals_en_cours += 1
        dates.append(e['last_modif'])
    dates.sort()
    if len(dates):
        last_modif = dates[-1] # date de derniere modif d'une note dans un module
    else:
        last_modif = ''

    return { 'nb_evals_completes':nb_evals_completes,
             'nb_evals_en_cours':nb_evals_en_cours,
             'nb_evals_vides':nb_evals_vides,
             'last_modif':last_modif }

def do_evaluation_etat_in_sem(context, formsemestre_id, REQUEST=None):
    """-> nb_eval_completes, nb_evals_en_cours, nb_evals_vides,
    date derniere modif, attente"""
    evals = do_evaluation_list_in_sem(context, formsemestre_id)
    etat = _eval_etat(evals)
    # Ajoute information sur notes en attente
    nt = context._getNotesCache().get_NotesTable(context, formsemestre_id) #> liste moduleimpl en attente
    etat['attente'] = len(nt.get_moduleimpls_attente()) > 0
    return etat

def do_evaluation_etat_in_mod(context, moduleimpl_id, REQUEST=None):
    evals = context.do_evaluation_list( { 'moduleimpl_id' : moduleimpl_id } )
    evaluation_ids = [ x['evaluation_id'] for x in evals ]
    R = []
    for evaluation_id in evaluation_ids:
        R.append( do_evaluation_etat(context, evaluation_id) )
    etat = _eval_etat(R)
    # Ajoute information sur notes en attente
    M = context.do_moduleimpl_list( args={ 'moduleimpl_id' : moduleimpl_id})[0]
    formsemestre_id = M['formsemestre_id']
    nt = context._getNotesCache().get_NotesTable(context, formsemestre_id)

    etat['attente'] = moduleimpl_id in [
        m['moduleimpl_id'] for m in nt.get_moduleimpls_attente() ] #> liste moduleimpl en attente
    return etat



def formsemestre_evaluations_cal(context, formsemestre_id, REQUEST=None):
    """Page avec calendrier de toutes les evaluations de ce semestre"""
    sem = context.get_formsemestre(formsemestre_id)
    evals = formsemestre_evaluations_list(context, formsemestre_id)
    nb_evals = len(evals)

    color_incomplete = '#FF6060'
    color_complete   = '#A0FFA0'
    color_futur      = '#70E0FF'
    
    today = time.strftime('%Y-%m-%d')
    
    year = int(sem['annee_debut'])
    if sem['mois_debut_ord'] < 8:
        year -= 1 # calendrier septembre a septembre
    events = {} # (day, halfday) : event
    for e in evals:
        etat = do_evaluation_etat(context, e['evaluation_id'])
        if not e['jour']:
            continue
        day = e['jour'].strftime('%Y-%m-%d')
        mod = context.do_moduleimpl_withmodule_list({'moduleimpl_id':e['moduleimpl_id']})[0]
        txt = mod['module']['code'] or mod['module']['abbrev'] or 'eval'
        if e['heure_debut']:
            debut = e['heure_debut'].strftime('%Hh%M')
        else:
            debut = '?'
        if e['heure_fin']:
            fin = e['heure_fin'].strftime('%Hh%M')
        else:
            fin = '?'
        description = '%s, de %s à %s' % (mod['module']['titre'],  debut,  fin)
        if etat['evalcomplete']:
            color = color_complete
        else:
            color = color_incomplete
        if day > today:
            color = color_futur
        href = 'moduleimpl_status?moduleimpl_id=%s' % e['moduleimpl_id']
        #if e['heure_debut'].hour < 12:
        #    halfday = True
        #else:
        #    halfday = False
        if not day in events:
            #events[(day,halfday)] = [day, txt, color, href, halfday, description, mod]
            events[day] = [day, txt, color, href, description, mod]
        else:
            e = events[day]
            if e[-1]['moduleimpl_id'] != mod['moduleimpl_id']:
                # plusieurs evals de modules differents a la meme date
                e[1] += ', ' + txt
                e[4] += ', ' + description
                if not etat['evalcomplete']:
                    e[2] = color_incomplete
            
    CalHTML = ZAbsences.YearTable(context.Absences, year, events=events.values(), halfday=False, pad_width=None )

    H = [ context.html_sem_header(REQUEST, 'Evaluations du semestre', sem, cssstyles=['calabs.css']),
          '<div class="cal_evaluations">',
          CalHTML,
          '</div>',
          '<p>soit %s évaluations planifiées;' % nb_evals,
          """<ul><li>en <span style="background-color: %s">rouge</span> les évaluations passées auxquelles il manque des notes</li>
          <li>en <span style="background-color: %s">vert</span> les évaluations déjà notées</li>
          <li>en <span style="background-color: %s">bleu</span> les évaluations futures</li></ul></p>"""
          % (color_incomplete, color_complete, color_futur),
          context.sco_footer(REQUEST) ]
    return '\n'.join(H)

    
