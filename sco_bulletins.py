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

"""Génération des bulletins de notes

"""
from email.MIMEMultipart import MIMEMultipart
from email.MIMEText import MIMEText
from email.MIMEBase import MIMEBase
from email.Header import Header
from email import Encoders

import htmlutils, time
from reportlab.lib.colors import Color
import pprint

from notes_table import *
import sco_pvjury
import sco_formsemestre_status
import sco_photos
import ZAbsences
import sco_abs_views
import sco_preferences
import sco_bulletins_generator
import sco_bulletins_xml
import sco_bulletins_json


def make_context_dict(context, sem, etud):
    """Construit dictionnaire avec valeurs pour substitution des textes
    (preferences bul_pdf_*)
    """
    C = sem.copy()
    C['responsable'] = context.Users.user_info(user_name=sem['responsable_id'])['prenomnom']
    annee_debut = sem['date_debut'].split('/')[2]
    annee_fin = sem['date_fin'].split('/')[2]
    if annee_debut != annee_fin:
        annee = '%s - %s' % (annee_debut, annee_fin)
    else:
        annee = annee_debut
    C['anneesem'] = annee
    C.update(etud)
    # copie preferences
    for name in sco_preferences.PREFS_NAMES:
        C[name] = context.get_preference(name, sem['formsemestre_id'])

    # ajoute groupes et group_0, group_1, ...
    sco_groups.etud_add_group_infos(context, etud, sem)
    C['groupes'] = etud['groupes']
    n = 0
    for partition_id in etud['partitions']:
        C['group_%d' % n] = etud['partitions'][partition_id]['group_name']
        n += 1

    # ajoute date courante
    t = time.localtime()
    C['date_dmy'] = time.strftime("%d/%m/%Y",t)
    C['date_iso'] = time.strftime("%Y-%m-%d",t)
    
    return C

def formsemestre_bulletinetud_dict(context, formsemestre_id, etudid, version='long', REQUEST=None):
    """Collecte informations pour bulletin de notes
    Retourne un dictionnaire (avec valeur par défaut chaine vide).
    Le contenu du dictionnaire dépend des options (rangs, ...) 
    et de la version choisie (short, long, selectedevals).

    Cette fonction est utilisée pour les bulletins HTML et PDF, mais pas ceux en XML.
    """
    if not version in ('short','long','selectedevals'):
        raise ValueError('invalid version code !')
    
    I = DictDefault(defaultvalue='')
    I['etudid'] = etudid
    I['formsemestre_id'] = formsemestre_id
    if REQUEST:
        I['server_name'] = REQUEST.BASE0
    else:
        I['server_name'] = ''

    prefs = context.get_preferences(formsemestre_id)
    nt = context._getNotesCache().get_NotesTable(context, formsemestre_id) #> toutes notes
    
    # Infos sur l'etudiant
    I['etud'] = context.getEtudInfo(etudid=etudid,filled=1)[0] 
    I['descr_situation'] = I['etud']['inscriptionstr']
    if I['etud']['inscription_formsemestre_id']:
        I['descr_situation_html'] = """<a href="formsemestre_status?formsemestre_id=%s">%s</a>""" % (I['etud']['inscription_formsemestre_id'], I['descr_situation'])
    else:
        I['descr_situation_html'] = I['descr_situation']
    # Groupes:
    partitions = sco_groups.get_partitions_list(context, formsemestre_id, with_default=False)
    partitions_etud_groups = {} # { partition_id : { etudid : group } }
    for partition in partitions:
        pid=partition['partition_id']
        partitions_etud_groups[pid] = sco_groups.get_etud_groups_in_partition(context, pid)
    # --- Absences
    AbsSemEtud = ZAbsences.getAbsSemEtud(context, formsemestre_id, etudid)
    I['nbabs'] =  AbsSemEtud.CountAbs()
    I['nbabsjust'] = AbsSemEtud.CountAbsJust()
    
    # --- Decision Jury
    infos, dpv = etud_descr_situation_semestre(
        context, etudid, formsemestre_id,
        format='html',
        show_date_inscr=prefs['bul_show_date_inscr'],
        show_decisions=prefs['bul_show_decision'],
        show_uevalid=prefs['bul_show_uevalid'],
        show_mention=prefs['bul_show_mention'])    
    
    if dpv:
        I['decision_sem'] = dpv['decisions'][0]['decision_sem']
    else:
        I['decision_sem'] = ''
    I.update(infos)
    
    I['etud_etat_html'] = nt.get_etud_etat_html(etudid)
    I['etud_etat'] = nt.get_etud_etat(etudid)
    I['filigranne'] = ''    
    I['demission'] = ''
    if I['etud_etat'] == 'D':
        I['demission'] = '(Démission)'
        I['filigranne'] = 'Démission'
    elif (prefs['bul_show_temporary'] and not I['decision_sem']) or prefs['bul_show_temporary_forced']:
        I['filigranne'] = prefs['bul_temporary_txt']
    
    # --- Appreciations
    cnx = context.GetDBConnexion()   
    apprecs = scolars.appreciations_list(
        cnx,
        args={'etudid':etudid, 'formsemestre_id' : formsemestre_id } )
    I['appreciations_list'] = apprecs 
    I['appreciations_txt'] = [ x['date'] + ': ' + x['comment'] for x in apprecs ]
    I['appreciations'] = I['appreciations_txt'] # deprecated / keep it for backward compat in templates

    # --- Notes
    ues = nt.get_ues()
    modimpls = nt.get_modimpls()
    moy_gen = nt.get_etud_moy_gen(etudid)
    I['nb_inscrits'] = len(nt.rangs)
    I['moy_gen'] = fmt_note(moy_gen)
    I['moy_min'] = fmt_note(nt.moy_min)
    I['moy_max'] = fmt_note(nt.moy_max)
    if dpv and dpv['decisions'][0]['decision_sem']:
        I['mention'] = get_mention(moy_gen)
    else:
        I['mention'] = ''
    I['moy_moy'] = fmt_note(nt.moy_moy) # moyenne des moyennes generales
    if type(moy_gen) != StringType and type(nt.moy_moy) != StringType:
        I['moy_gen_bargraph_html'] = '&nbsp;' + htmlutils.horizontal_bargraph(moy_gen*5, nt.moy_moy*5)
    else:
        I['moy_gen_bargraph_html'] = ''
    
    if prefs['bul_show_rangs']:
        rang = str(nt.get_etud_rang(etudid))
    else:        
        rang = ''
        
    rang_gr, ninscrits_gr, gr_name = get_etud_rangs_groups(
        context, etudid, formsemestre_id, partitions, partitions_etud_groups, nt)
    
    if nt.get_moduleimpls_attente():
        # n'affiche pas le rang sur le bulletin s'il y a des
        # notes en attente dans ce semestre
        rang = '(attente)'
        rang_gr = DictDefault(defaultvalue='(attente)')
    I['rang'] = rang
    I['rang_gr'] = rang_gr
    I['gr_name'] = gr_name
    I['ninscrits_gr'] = ninscrits_gr
    I['nbetuds'] = len(nt.rangs)
    if prefs['bul_show_rangs']:
        I['rang_nt'] =  '%s / %d' % (rang, I['nbetuds']-nt.nb_demissions)
        I['rang_txt'] = 'Rang ' + I['rang_nt']
    else:
        I['rang_nt'], I['rang_txt'] = '', ''
    I['note_max'] = 20. # notes toujours sur 20
    I['bonus_sport_culture'] = nt.bonus[etudid]
    # Liste les UE / modules /evals
    I['ues'] = []
    I['matieres_modules'] = {}
    I['matieres_modules_capitalized'] = {}
    for ue in ues:
        u = ue.copy()
        ue_status = nt.get_etud_ue_status(etudid, ue['ue_id'])
        u['ue_status'] = ue_status # { 'moy', 'coef_ue', ...}
        if ue['type'] != UE_SPORT:
            u['cur_moy_ue_txt'] = fmt_note(ue_status['cur_moy_ue'])
        else:
            u['cur_moy_ue_txt'] = 'bonus de %s points' % nt.bonus[etudid]
        u['moy_ue_txt']  = fmt_note(ue_status['moy'])
        u['coef_ue_txt'] = fmt_coef(ue_status['coef_ue'])
        
        modules, ue_attente = _ue_mod_bulletin(context, etudid, formsemestre_id, ue['ue_id'], modimpls, nt, version)
        #
        u['modules'] = modules # detail des modules de l'UE (dans le semestre courant)
        # auparavant on filtrait les modules sans notes
        #   si ue_status['cur_moy_ue'] != 'NA' alors u['modules'] = [] (pas de moyenne => pas de modules)
        
        u['modules_capitalized'] = [] # modules de l'UE capitalisée (liste vide si pas capitalisée)
        if ue_status['is_capitalized']:
            sem_origin = context.get_formsemestre(ue_status['formsemestre_id'])
            u['ue_descr_txt'] =  'Capitalisée le %s' % DateISOtoDMY(ue_status['event_date'])
            u['ue_descr_html'] = '<a href="formsemestre_bulletinetud?formsemestre_id=%s&etudid=%s" title="%s" class="bull_link">%s</a>' % (sem_origin['formsemestre_id'], etudid, sem_origin['titreannee'], u['ue_descr_txt'])
            # log('cap details   %s' % ue_status['moy'])
            if ue_status['moy'] != 'NA' and ue_status['formsemestre_id']:
                # detail des modules de l'UE capitalisee
                nt_cap = context._getNotesCache().get_NotesTable(context, ue_status['formsemestre_id']) #> toutes notes
                
                u['modules_capitalized'], junk = _ue_mod_bulletin(context, etudid, formsemestre_id, ue_status['capitalized_ue_id'], nt_cap.get_modimpls(), nt_cap, version)
                I['matieres_modules_capitalized'].update(_sort_mod_by_matiere(u['modules_capitalized'], nt_cap, etudid))
        else:
            if prefs['bul_show_ue_rangs'] and ue['type'] != UE_SPORT:
                if ue_attente: # nt.get_moduleimpls_attente():
                     u['ue_descr_txt'] = '(attente)/%s' % (nt.ue_rangs[ue['ue_id']][1]-nt.nb_demissions)
                else:
                    u['ue_descr_txt'] = '%s/%s' % (nt.ue_rangs[ue['ue_id']][0][etudid], nt.ue_rangs[ue['ue_id']][1]-nt.nb_demissions)
                u['ue_descr_html'] = u['ue_descr_txt']
            else:
                u['ue_descr_txt'] = u['ue_descr_html'] = ''        
        
        if ue_status['is_capitalized'] or modules:
            I['ues'].append(u) # ne montre pas les UE si non inscrit

        # Accès par matieres
        I['matieres_modules'].update(_sort_mod_by_matiere(modules, nt, etudid))

    #
    sem = context.get_formsemestre(formsemestre_id)
    C = make_context_dict(context, sem, I['etud'])
    C.update(I)
    #
    # log( 'C = \n%s\n' % pprint.pformat(C) ) # tres pratique pour voir toutes les infos dispo
    return C

def _sort_mod_by_matiere(modlist, nt, etudid):
    matmod = {} # { matiere_id : [] }
    for mod in modlist: 
        matiere_id = mod['module']['matiere_id']
        if matiere_id not in matmod:
            moy = nt.get_etud_mat_moy(matiere_id, etudid)
            matmod[matiere_id] = {
                'titre' : mod['mat']['titre'],
                'modules' : mod,
                'moy' : moy,
                'moy_txt' : fmt_note(moy)
                } 
    return matmod

def _ue_mod_bulletin(context, etudid, formsemestre_id, ue_id, modimpls, nt, version):
    """Infos sur les modules (et évaluations) dans une UE
    (ajoute les informations aux modimpls)
    Result: liste de modules de l'UE avec les infos dans chacun (seulement ceux où l'étudiant est inscrit).
    """
    bul_show_mod_rangs = context.get_preference('bul_show_mod_rangs', formsemestre_id)
    bul_show_abs_modules = context.get_preference('bul_show_abs_modules', formsemestre_id)
    if bul_show_abs_modules:
        sem = context.Notes.get_formsemestre(formsemestre_id)
        debut_sem = DateDMYtoISO(sem['date_debut'])
        fin_sem = DateDMYtoISO(sem['date_fin'])
    
    ue_modimpls = [ mod for mod in modimpls if mod['module']['ue_id'] == ue_id ]
    mods = [] # result
    ue_attente = False # true si une eval en attente dans cette UE
    for modimpl in ue_modimpls:
        mod_attente = False
        mod = modimpl.copy()
        mod_moy = nt.get_etud_mod_moy(modimpl['moduleimpl_id'], etudid)  # peut etre 'NI'
        if bul_show_abs_modules:
            mod_abs = [context.Absences.CountAbs(etudid=etudid, debut=debut_sem, fin=fin_sem, moduleimpl_id=modimpl['moduleimpl_id']), context.Absences.CountAbsJust(etudid=etudid, debut=debut_sem, fin=fin_sem, moduleimpl_id=modimpl['moduleimpl_id'])]
            mod['mod_abs_txt'] = fmt_abs(mod_abs)
        else:
            mod['mod_abs_txt'] = ''
        
        mod['mod_moy_txt'] = fmt_note(mod_moy)
        if mod['mod_moy_txt'][:2] == 'NA':
            mod['mod_moy_txt'] = '-'
        mod['mod_coef_txt']= fmt_coef(modimpl['module']['coefficient'])
        
        if mod['mod_moy_txt'] != 'NI': # ne montre pas les modules 'non inscrit'
            mods.append(mod)
            mod['stats'] = nt.get_mod_stats(modimpl['moduleimpl_id'])
            mod['mod_descr_txt'] = 'Module %s, coef. %s (%s)' % (
                modimpl['module']['titre'],
                fmt_coef(modimpl['module']['coefficient']),
                context.Users.user_info(modimpl['responsable_id'])['nomcomplet'])
            link_mod = '<a class="bull_link" href="moduleimpl_status?moduleimpl_id=%s" title="%s">' % (
                modimpl['moduleimpl_id'], mod['mod_descr_txt'])
            if context.get_preference('bul_show_codemodules', formsemestre_id):
                mod['code'] = modimpl['module']['code']
                mod['code_html'] = link_mod + mod['code'] + '</a>'
            else:
                mod['code'] = mod['code_html'] = ''
            mod['name'] = modimpl['module']['abbrev'] or modimpl['module']['titre'] or ''
            mod['name_html'] = link_mod + mod['name'] + '</a>'
            
            mod_descr = 'Module %s, coef. %s (%s)' % (
                modimpl['module']['titre'],
                fmt_coef(modimpl['module']['coefficient']),
                context.Users.user_info(modimpl['responsable_id'])['nomcomplet'])
            link_mod = '<a class="bull_link" href="moduleimpl_status?moduleimpl_id=%s" title="%s">' % (modimpl['moduleimpl_id'], mod_descr)
            if context.get_preference('bul_show_codemodules', formsemestre_id):
                mod['code_txt'] = modimpl['module']['code']
                mod['code_html'] = link_mod + mod['code_txt'] + '</a>'
            else:
                mod['code_txt'] = ''
                mod['code_html'] = ''
            # Evaluations: notes de chaque eval
            evals = nt.get_evals_in_mod(modimpl['moduleimpl_id'])
            mod['evaluations'] = []
            for e in evals:
                e = e.copy()
                mod['evaluations'].append(e)
                if e['visibulletin'] == '1' or version == 'long':
                    e['name'] = e['description'] or 'le %s' % e['jour']
                e['target_html'] = 'evaluation_listenotes?evaluation_id=%s&format=html&tf-submitted=1' % e['evaluation_id']
                e['name_html'] = '<a class="bull_link" href="%s">%s</a>' % (e['target_html'], e['name'])
                val = e['notes'].get(etudid, {'value':'NP'})['value'] # NA si etud demissionnaire
                if val == 'NP':
                    e['note_txt'] = 'nd'
                    e['note_html'] = '<span class="note_nd">nd</span>'
                    e['coef_txt'] = ''
                else:
                    e['note_txt'] = fmt_note(val, note_max=e['note_max'])
                    e['note_html'] = e['note_txt']
                    e['coef_txt'] = fmt_coef(e['coefficient'])
                if e['evaluation_type'] == EVALUATION_RATTRAPAGE:
                    e['coef_txt'] = 'rat.'
                if e['etat']['evalattente']:
                    mod_attente = True # une eval en attente dans ce module
            # Evaluations incomplètes ou futures:
            mod['evaluations_incompletes'] = []
            if context.get_preference('bul_show_all_evals', formsemestre_id):
                complete_eval_ids = Set( [ e['evaluation_id'] for e in evals ] )
                all_evals = context.do_evaluation_list(args={ 'moduleimpl_id' : modimpl['moduleimpl_id'] })
                all_evals.reverse() # plus ancienne d'abord
                for e in all_evals:
                    if e['evaluation_id'] not in complete_eval_ids:
                        e = e.copy()                        
                        mod['evaluations_incompletes'].append(e)
                        e['name'] = (e['description'] or '') + ' (%s)' % e['jour']
                        e['target_html'] = 'evaluation_listenotes?evaluation_id=%s&format=html&tf-submitted=1' % e['evaluation_id']
                        e['name_html'] = '<a class="bull_link" href="%s">%s</a>' % (e['target_html'], e['name'])
                        e['note_txt'] = e['note_html'] = ''
                        e['coef_txt'] = fmt_coef(e['coefficient'])
            # Classement
            if bul_show_mod_rangs and mod['mod_moy_txt'] != '-':
                rg = nt.mod_rangs[modimpl['moduleimpl_id']]
                if mod_attente: # nt.get_moduleimpls_attente():
                    mod['mod_rang'] = '(attente)'
                else:
                    mod['mod_rang'] = rg[0][etudid]
                mod['mod_eff']   = rg[1] # effectif dans ce module
                mod['mod_rang_txt'] = '%s/%s' % (mod['mod_rang'], mod['mod_eff'])                    
            else:
                mod['mod_rang_txt'] = ''
        if mod_attente:
            ue_attente = True
    return mods, ue_attente


def get_etud_rangs_groups(context, etudid, formsemestre_id, 
                           partitions, partitions_etud_groups, 
                           nt):
    """Ramene rang et nb inscrits dans chaque partition
    """
    rang_gr, ninscrits_gr, gr_name = {}, {}, {}
    for partition in partitions:
        if partition['partition_name'] != None:
            partition_id = partition['partition_id']

            if etudid in partitions_etud_groups[partition_id]:
                group = partitions_etud_groups[partition_id][etudid]
            
                rang_gr[partition_id], ninscrits_gr[partition_id] =\
                    nt.get_etud_rang_group(etudid, group['group_id'])
                gr_name[partition_id] = group['group_name']
            else: # etudiant non present dans cette partition
                rang_gr[partition_id], ninscrits_gr[partition_id] = '', ''
                gr_name[partition_id] = ''

    return rang_gr, ninscrits_gr, gr_name


def etud_descr_situation_semestre(context, etudid, formsemestre_id, ne='',
                                   format='html', # currently unused
                                   show_decisions=True,
                                   show_uevalid=True,
                                   show_date_inscr=True,
                                   show_mention=False
                                  ):
    """Dict décrivant la situation de l'étudiant dans ce semestre.
    Si format == 'html', peut inclure du balisage html (actuellement inutilisé)

    situation : chaine résumant en français la situation de l'étudiant.
                Par ex. "Inscrit le 31/12/1999. Décision jury: Validé. ..."
    
    date_inscription : (vide si show_date_inscr est faux)
    date_demission   : (vide si pas demission ou si show_date_inscr est faux)
    descr_inscription : "Inscrit" ou "Pas inscrit[e]"
    descr_demission   : "Démission le 01/02/2000" ou vide si pas de démission
    decision_jury     :  "Validé", "Ajourné", ... (code semestre)
    descr_decision_jury : "Décision jury: Validé" (une phrase)
    decisions_ue        : noms (acronymes) des UE validées, séparées par des virgules.
    descr_decisions_ue  : ' UE acquises: UE1, UE2', ou vide si pas de dec. ou si pas show_uevalid
    descr_mention : 'Mention Bien', ou vide si pas de mention ou si pas show_mention
    """
    cnx = context.GetDBConnexion()
    infos = DictDefault(defaultvalue='')
    
    # --- Situation et décisions jury

    # demission/inscription ?
    events = scolars.scolar_events_list(
        cnx, args={'etudid':etudid, 'formsemestre_id':formsemestre_id} )
    date_inscr = None
    date_dem = None
    date_echec = None
    for event in events:
        event_type = event['event_type']
        if event_type == 'INSCRIPTION':
            if date_inscr:
                # plusieurs inscriptions ???
                #date_inscr += ', ' +   event['event_date'] + ' (!)'
                # il y a eu une erreur qui a laissé un event 'inscription'
                # on l'efface:
                log('etud_descr_situation_semestre: removing duplicate INSCRIPTION event !')
                scolars.scolar_events_delete( cnx, event['event_id'] )
            else:
                date_inscr = event['event_date']
        elif event_type == 'DEMISSION':
            # assert date_dem == None, 'plusieurs démissions !'
            if date_dem: # cela ne peut pas arriver sauf bug (signae a Evry 2013?)
                log('etud_descr_situation_semestre: removing duplicate DEMISSION event !')
                scolars.scolar_events_delete( cnx, event['event_id'] )
            else:
                date_dem = event['event_date']
    if show_date_inscr: 
        if not date_inscr:
            infos['date_inscription'] = ''
            infos['descr_inscription'] = 'Pas inscrit%s.' % ne            
        else:
            infos['date_inscription'] = date_inscr            
            infos['descr_inscription'] = 'Inscrit%s le %s.' % (ne, date_inscr)
    else:
        infos['date_inscription'] = ''
        infos['descr_inscription'] = ''

    infos['situation'] = infos['descr_inscription']
    if date_dem:
        infos['descr_demission'] = 'Démission le %s.' % date_dem
        infos['date_demission'] = date_dem
        infos['descr_decision_jury'] = 'Démission'
        infos['situation'] += ' ' + infos['descr_demission']
        return infos, None # ne donne pas les dec. de jury pour les demissionnaires
    
    dpv = sco_pvjury.dict_pvjury(context, formsemestre_id, etudids=[etudid])

    if not show_decisions:
        return infos, dpv

    # Decisions de jury:
    pv = dpv['decisions'][0]
    dec = ''
    if pv['decision_sem_descr']:
        infos['decision_jury'] = pv['decision_sem_descr']
        infos['descr_decision_jury'] = 'Décision jury: ' + pv['decision_sem_descr'] + '. ' 
        dec = infos['descr_decision_jury']
    else:
        infos['descr_decision_jury'] = ''
    
    if pv['decisions_ue_descr'] and show_uevalid:
        infos['decisions_ue'] = pv['decisions_ue_descr']
        infos['descr_decisions_ue'] = ' UE acquises: ' + pv['decisions_ue_descr'] + '. '
        dec += infos['descr_decisions_ue']
    else:
        # infos['decisions_ue'] = None
        infos['descr_decisions_ue'] = ''
        

    infos['mention'] = pv['mention']
    if pv['mention'] and show_mention:
        dec += 'Mention ' + pv['mention'] + '. '
    
    infos['situation'] += ' ' + dec
    if not pv['validation_parcours']: # parcours non terminé
        if pv['autorisations_descr']:
            infos['situation'] += " Autorisé à s'inscrire en %s." % pv['autorisations_descr']
    else:
        infos['situation'] += " Diplôme obtenu."
    return infos, dpv



# ------ Page bulletin
def formsemestre_bulletinetud(
        context, etudid=None, formsemestre_id=None,
        format='html', version='long',
        xml_with_decisions=False,
        force_publishing=False, # force publication meme si semestre non publie sur "portail"
        REQUEST=None):
    "page bulletin de notes"
    try:
        etud = context.getEtudInfo(filled=1, REQUEST=REQUEST)[0]
        etudid = etud['etudid']
    except:
        return context.log_unknown_etud(REQUEST, format=format)
    
    sem = context.get_formsemestre(formsemestre_id)

    R = []
    if format == 'html' or format == 'pdfmail':
        R.append( _formsemestre_bulletinetud_header_html(context, etud, etudid, sem,
                                                   formsemestre_id, format, version, REQUEST) )
    
    R.append( do_formsemestre_bulletinetud(context, formsemestre_id, etudid,
                                           format=format, version=version,
                                           xml_with_decisions=xml_with_decisions,
                                           force_publishing=force_publishing,
                                           REQUEST=REQUEST)[0])
    
    if format == 'html' or format == 'pdfmail':
        R.append("""<p>Situation actuelle: """)
        if etud['inscription_formsemestre_id']:
            R.append("""<a href="formsemestre_status?formsemestre_id=%s">"""
                     % etud['inscription_formsemestre_id'])
        R.append(etud['inscriptionstr'])
        if etud['inscription_formsemestre_id']:
            R.append("""</a>""")
        R.append("""</p>""")

        # Place du diagramme radar
        R.append("""<form id="params">
        <input type="hidden" name="etudid" id="etudid" value="%s"/>
        <input type="hidden" name="formsemestre_id" id="formsemestre_id" value="%s"/>
        </form>""" % (etudid, formsemestre_id))
        R.append('<div id="radar_bulletin"></div>')
        
        # --- Pied de page
        R.append( context.sco_footer(REQUEST) )

    return ''.join(R)

def can_send_bulletin_by_mail(context, formsemestre_id, REQUEST):
    """True if current user is allowed to send a bulletin by mail
    """
    authuser = REQUEST.AUTHENTICATED_USER
    sem = context.get_formsemestre(formsemestre_id)
    return (context.get_preference('bul_mail_allowed_for_all', formsemestre_id)
            or authuser.has_permission(ScoImplement, context)
            or sem['responsable_id'] == str(authuser))



def do_formsemestre_bulletinetud(context, formsemestre_id, etudid,
                                 version='long', # short, long, selectedevals
                                 format='html',
                                 REQUEST=None,
                                 nohtml=False,
                                 xml_with_decisions=False, # force decisions dans XML
                                 force_publishing=False # force publication meme si semestre non publie sur "portail"
                                 ):
    """Génère le bulletin au format demandé.
    Retourne: (bul, filigranne)
    où bul est au format demandé (html, pdf, pdfmail, pdfpart, xml)
    et filigranne est un message à placer en "filigranne" (eg "Provisoire").
    """
    if format == 'xml':        
        bul = repr(sco_bulletins_xml.make_xml_formsemestre_bulletinetud(
            context, formsemestre_id,  etudid, REQUEST=REQUEST,
            xml_with_decisions=xml_with_decisions, force_publishing=force_publishing,
            version=version))
        return bul, ''
    
    elif format == 'json':
        bul = sco_bulletins_json.make_json_formsemestre_bulletinetud(
            context, formsemestre_id,  etudid, REQUEST=REQUEST,
            xml_with_decisions=xml_with_decisions, force_publishing=force_publishing,
            version=version)
        return bul, ''
    
    I = formsemestre_bulletinetud_dict(context, formsemestre_id, etudid, REQUEST=REQUEST)
    etud = I['etud']
        
    if format == 'html':            
        htm, junk = sco_bulletins_generator.make_formsemestre_bulletinetud(
            context, I, version=version, format='html', REQUEST=REQUEST)
        return htm, I['filigranne']
    
    elif format == 'pdf' or format == 'pdfpart':
        bul, filename = sco_bulletins_generator.make_formsemestre_bulletinetud(context, I, version=version, format='pdf', stand_alone=(format != 'pdfpart'), REQUEST=REQUEST)
        if format == 'pdf':
            return sendPDFFile(REQUEST, bul, filename), I['filigranne'] # unused ret. value
        else:
            return bul, I['filigranne']
    
    elif format == 'pdfmail':
        # format pdfmail: envoie le pdf par mail a l'etud, et affiche le html
        # check permission
        if not can_send_bulletin_by_mail(context, formsemestre_id, REQUEST):
            raise AccessDenied("Vous n'avez pas le droit d'effectuer cette opération !")
        
        if nohtml:
            htm = '' # speed up if html version not needed
        else:
            htm, junk = sco_bulletins_generator.make_formsemestre_bulletinetud(
                context, I, version=version, format='html', REQUEST=REQUEST)
        
        pdfdata, filename = sco_bulletins_generator.make_formsemestre_bulletinetud(
            context, I, version=version, format='pdf', REQUEST=REQUEST)

        if not etud['email']:
            return ('<div class="boldredmsg">%s n\'a pas d\'adresse e-mail !</div>'
                    % etud['nomprenom']) + htm, I['filigranne']
        #
        mail_bulletin(context, formsemestre_id, I, pdfdata, filename)
        
        return ('<div class="head_message">Message mail envoyé à %s</div>'
                % (etud['emaillink'])) + htm, I['filigranne']
    
    else:
        raise ValueError("do_formsemestre_bulletinetud: invalid format (%s)" % format)


def mail_bulletin(context, formsemestre_id, I, pdfdata, filename):
    """Send bulletin by email to etud
    If bul_mail_list_abs pref is true, put list of absences in mail body (text).
    """
    etud = I['etud']
    webmaster = context.get_preference('bul_mail_contact_addr', formsemestre_id)
    dept = unescape_html(context.get_preference('DeptName',formsemestre_id))
    copy_addr = context.get_preference('email_copy_bulletins',formsemestre_id)            
    intro_mail = context.get_preference('bul_intro_mail', formsemestre_id)
    
    if intro_mail:
        hea = intro_mail % { 'nomprenom' : etud['nomprenom'], 'dept':dept, 'webmaster':webmaster }
    else:
        hea = ''

    if context.get_preference('bul_mail_list_abs'):
        hea += '\n\n' + sco_abs_views.ListeAbsEtud(context,
                                                   etud['etudid'], with_evals=False, format='text')
    
    msg = MIMEMultipart()
    subj = Header( 'Relevé de notes de %s' % etud['nomprenom'],  SCO_ENCODING )
    recipients = [ etud['email'] ] 
    msg['Subject'] = subj
    msg['From'] = context.get_preference('email_from_addr',formsemestre_id)
    msg['To'] = ' ,'.join(recipients)
    if copy_addr:
        msg['Bcc'] = copy_addr.strip()
    # Guarantees the message ends in a newline
    msg.epilogue = ''
    # Text
    txt = MIMEText( hea, 'plain', SCO_ENCODING )
    # log('hea:\n' + hea)
    msg.attach(txt)
    # Attach pdf
    att = MIMEBase('application', 'pdf')
    att.add_header('Content-Disposition', 'attachment', filename=filename)
    att.set_payload( pdfdata )
    Encoders.encode_base64(att)
    msg.attach(att)
    log('mail bulletin a %s' % msg['To'] )
    context.sendEmail(msg)


def _formsemestre_bulletinetud_header_html(context, etud, etudid, sem,
                                           formsemestre_id=None, format=None, version=None, REQUEST=None):
    authuser = REQUEST.AUTHENTICATED_USER
    uid = str(authuser)
    H = [ context.sco_header(page_title='Bulletin de %(nomprenom)s' % etud, REQUEST=REQUEST,
                             javascripts=['jQuery/jquery.js',
                                          'js/bulletin.js',
                                          'libjs/d3.v2.min.js',
                                          'js/radar_bulletin.js'
                                          ],
                             cssstyles=['radar_bulletin.css']
                                          ),
          """<table class="bull_head"><tr><td>
          <h2><a class="discretelink" href="ficheEtud?etudid=%(etudid)s">%(nomprenom)s</a></h2>
          """ % etud,
          """
          <form name="f" method="GET" action="%s">"""%REQUEST.URL0,
          """Bulletin <span class="bull_liensemestre"><a href="formsemestre_status?formsemestre_id=%(formsemestre_id)s">
          %(titremois)s</a></span> 
          <br/>""" % sem,
          """<table><tr>""",
          """<td>établi le %s (notes sur 20)</td>""" % time.strftime('%d/%m/%Y à %Hh%M'),
          """<td><span class="rightjust">
             <input type="hidden" name="formsemestre_id" value="%s"></input>""" % formsemestre_id,
          """<input type="hidden" name="etudid" value="%s"></input>""" % etudid,
          """<input type="hidden" name="format" value="%s"></input>""" % format,
          """<select name="version" onchange="document.f.submit()" class="noprint">""",
          ]
    for (v,e) in ( ('short', 'Version courte'),
                   ('selectedevals', 'Version intermédiaire'),
                   ('long', 'Version complète')):
        if v == version:
            selected = ' selected'
        else:
            selected = ''
        H.append('<option value="%s"%s>%s</option>' % (v, selected, e))
    H.append("""</select></td>""")
    # Menu
    url = REQUEST.URL0
    qurl = urllib.quote_plus( url + '?' + REQUEST.QUERY_STRING )
    
    menuBul = [
        { 'title' : 'Réglages bulletins',
          'url' : 'formsemestre_edit_options?formsemestre_id=%s&target_url=%s' % (formsemestre_id, qurl),
          'enabled' : (uid == sem['responsable_id']) or authuser.has_permission(ScoImplement, context),
          },
        { 'title' : 'Version papier (pdf, format "%s")' % sco_bulletins_generator.bulletin_get_class_name_displayed(context, formsemestre_id),
          'url' : url + '?formsemestre_id=%s&etudid=%s&format=pdf&version=%s' % (formsemestre_id,etudid,version),
          },
        { 'title' : "Envoi par mail à l'étudiant",
          'url' : url + '?formsemestre_id=%s&etudid=%s&format=pdfmail&version=%s' % (formsemestre_id,etudid,version),
          'enabled' : etud['email'] and can_send_bulletin_by_mail(context, formsemestre_id, REQUEST) # possible slt si on a un mail...
          },
        { 'title' : 'Version XML',
          'url' : url + '?formsemestre_id=%s&etudid=%s&format=xml&version=%s' % (formsemestre_id,etudid,version),
          },
        { 'title' : 'Ajouter une appréciation',
          'url' : 'appreciation_add_form?etudid=%s&formsemestre_id=%s' % (etudid, formsemestre_id),
          'enabled' : ((authuser == sem['responsable_id'])
                       or (authuser.has_permission(ScoEtudInscrit,context)))
          },
        { 'title' : "Enregistrer une validation d'UE antérieure",
          'url' : 'formsemestre_validate_previous_ue?etudid=%s&formsemestre_id=%s' % (etudid, formsemestre_id),
          'enabled' : context.can_validate_sem(REQUEST, formsemestre_id)
          },
        { 'title' : 'Entrer décisions jury',
          'url' : 'formsemestre_validation_etud_form?formsemestre_id=%s&etudid=%s'%(formsemestre_id,etudid),
          'enabled' : context.can_validate_sem(REQUEST, formsemestre_id)
        },
        { 'title' : 'Editer PV jury',
          'url' : 'formsemestre_pvjury_pdf?formsemestre_id=%s&etudid=%s' % (formsemestre_id,etudid),
          'enabled' : True
          }
        ]
    
    H.append("""<td class="bulletin_menubar"><div class="bulletin_menubar">""")
    H.append( sco_formsemestre_status.makeMenu( 'Autres opérations', menuBul) )
    H.append("""</div></td>""")
    H.append('<td> <a href="%s">%s</a></td>'%(url + '?formsemestre_id=%s&etudid=%s&format=pdf&version=%s'% (formsemestre_id,etudid,version),ICON_PDF))
    H.append("""</tr></table>""")
    #
    H.append("""</form></span></td><td class="bull_photo">
    <a href="%s/ficheEtud?etudid=%s">%s</a>
    """ % (context.ScoURL(), etudid, sco_photos.etud_photo_html(context, etud, title='fiche de '+etud['nom'], REQUEST=REQUEST)))
    H.append("""</td></tr>
    </table>
    """)
    
    return ''.join(H)


def formsemestre_bulletins_choice(context, REQUEST, formsemestre_id, 
                                  title='', explanation=''):
    """Choix d'une version de bulletin
    """
    sem = context.get_formsemestre(formsemestre_id)
    H = [context.html_sem_header(REQUEST, title, sem),
         """
      <form name="f" method="GET" action="%s">
      <input type="hidden" name="formsemestre_id" value="%s"></input>
      <select name="version" class="noprint">""" % (REQUEST.URL0,formsemestre_id),
         ]
    for (v,e) in ( ('short', 'Version courte'),
                   ('selectedevals', 'Version intermédiaire'),
                   ('long', 'Version complète')):
        H.append('<option value="%s">%s</option>' % (v, e))
    H.append("""</select>&nbsp;&nbsp;<input type="submit" value="Générer"/></form><p class="help">""" + explanation + '</p>',)

    return '\n'.join(H) + context.sco_footer(REQUEST)

expl_bull = """Versions des bulletins:<ul><li><bf>courte</bf>: moyennes des modules</li><li><bf>intermédiaire</bf>: moyennes des modules et notes des évaluations sélectionnées</li><li><bf>complète</bf>: toutes les notes</li><ul>"""

def formsemestre_bulletins_pdf_choice(context, REQUEST, formsemestre_id, version=None):
    """Choix version puis envois classeur bulletins pdf"""
    if version:
        return context.formsemestre_bulletins_pdf(formsemestre_id, REQUEST, version=version)
    return formsemestre_bulletins_choice(
        context, REQUEST, formsemestre_id, 
        title='Choisir la version des bulletins à générer',
        explanation = expl_bull)

def formsemestre_bulletins_mailetuds_choice(context, REQUEST, formsemestre_id, version=None, dialog_confirmed=False):
    """Choix version puis envois classeur bulletins pdf"""
    if version:
        return context.formsemestre_bulletins_mailetuds(formsemestre_id, REQUEST, version=version, dialog_confirmed=dialog_confirmed)
    return formsemestre_bulletins_choice(
        context, REQUEST, formsemestre_id, 
        title='Choisir la version des bulletins à envoyer par mail',
        explanation = 'Chaque étudiant ayant une adresse mail connue de ScoDoc recevra une copie PDF de son bulletin de notes, dans la version choisie.</p><p>' + expl_bull)
