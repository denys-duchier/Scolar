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

"""Edition des PV de jury
"""

import sco_parcours_dut
import sco_codes_parcours
import sco_excel
from notesdb import *
from sco_utils import *
from gen_tables import GenTable

"""PV Jury IUTV 2006: on détaillait 8 cas:
Jury de semestre n
    On a 8 types de décisions:
    Passages:
    1. passage de ceux qui ont validés Sn-1
    2. passage avec compensation Sn-1, Sn
    3. passage sans validation de Sn avec validation d'UE
    4. passage sans validation de Sn sans validation d'UE

    Redoublements:
    5. redoublement de Sn-1 et Sn sans validation d'UE pour Sn
    6. redoublement de Sn-1 et Sn avec validation d'UE pour Sn

    Reports
    7. report sans validation d'UE

    8. non validation de Sn-1 et Sn et non redoublement
"""

def descr_decisions_ues(znotes, decisions_ue, decision_sem):
    "résumé textuel des décisions d'UE"
    if not decisions_ue:
        return ''
    uelist = []
    for ue_id in decisions_ue.keys():
        if decisions_ue[ue_id]['code'] == 'ADM' \
           or (CONFIG.CAPITALIZE_ALL_UES and sco_codes_parcours.code_semestre_validant(decision_sem['code'])):
            ue = znotes.do_ue_list( args={ 'ue_id' : ue_id } )[0]
            uelist.append(ue)
    uelist.sort( lambda x,y: cmp(x['numero'],y['numero']) )
    ue_acros = ', '.join( [ ue['acronyme'] for ue in uelist ] )
    return ue_acros

def descr_decision_sem(znotes, etat, decision_sem):
    "résumé textuel de la décision de semestre"
    if etat == 'D':
        decision = 'Démission'
    else:
        if decision_sem:
            cod = decision_sem['code']
            decision = sco_codes_parcours.CODES_EXPL.get(cod,'') #+ ' (%s)' % cod
        else:
            decision = ''
    return decision

def descr_decision_sem_abbrev(znotes, etat, decision_sem):
    "résumé textuel tres court (code) de la décision de semestre"
    if etat == 'D':
        decision = 'Démission'
    else:
        if decision_sem:
            decision = decision_sem['code']
        else:
            decision = ''
    return decision

def descr_autorisations(znotes, autorisations):
    "résumé texturl des autorisations d'inscription (-> 'S1, S3' )"
    alist = []
    for aut in autorisations:
        alist.append( 'S' + str(aut['semestre_id']) )
    return ', '.join(alist)


def dict_pvjury( znotes, formsemestre_id, etudids=None, with_prev=False ):
    """Données pour édition jury
    etudids == None => tous les inscrits, sinon donne la liste des ids
    Si with_prev: ajoute infos sur code jury semestre precedent
    Résultat:
    {
    'date' : date de la decision la plus recente,
    'formsemestre' : sem,
    'formation' : { 'acronyme' :, 'titre': ... }
    'decisions' : { [ { 'identite' : {'nom' :, 'prenom':,  ...,},
                        'etat' : I ou D
                        'decision' : {'code':, 'code_prev': },
                        'ues' : {  ue_id : { 'code' : ADM|CMP|AJ, 'event_date' :,
                                             'acronyme', 'numero': } },
                        'autorisations' : [ { 'semestre_id' : { ... } }
                        'prev_code' : code (calculé slt si with_prev)
                    ]
                  }
    }    
    """
    nt = znotes._getNotesCache().get_NotesTable(znotes, formsemestre_id)
    if etudids is None:
        etudids = nt.get_etudids()
    if not etudids:
        return {}
    cnx = znotes.GetDBConnexion()
    sem = znotes.get_formsemestre(formsemestre_id)
    max_date = '0000-01-01'
    has_prev = False # vrai si au moins un etudiant a un code prev    
    # construit un Se pour savoir si le semestre est terminal:
    etud = znotes.getEtudInfo(etudid=etudids[0], filled=True)[0]
    Se = sco_parcours_dut.SituationEtudParcours(znotes, etud, formsemestre_id) 
    L = []
    for etudid in etudids:
        d = {}
        d['identite'] = nt.identdict[etudid]
        d['etat'] = nt.get_etud_etat(etudid) # I|D  (inscription ou démission)
        d['decision_sem'] = nt.get_etud_decision_sem(etudid)
        d['decisions_ue'] = nt.get_etud_decision_ues(etudid)
        # Versions "en français":
        d['decisions_ue_descr'] = descr_decisions_ues(znotes, d['decisions_ue'], d['decision_sem'])
        d['decision_sem_descr'] = descr_decision_sem(znotes, d['etat'], d['decision_sem'])

        d['autorisations'] = sco_parcours_dut.formsemestre_get_autorisation_inscription(
            znotes, etudid, formsemestre_id)
        d['autorisations_descr'] = descr_autorisations(znotes, d['autorisations'])
        # Observations sur les compensations:
        obs = ''
        compensators = sco_parcours_dut.scolar_formsemestre_validation_list(
            cnx, 
            args={'compense_formsemestre_id': formsemestre_id,
                  'etudid' : etudid })
        for compensator in compensators:
            # nb: il ne devrait y en avoir qu'un !
            csem = znotes.get_formsemestre(compensator['formsemestre_id'])
            obs += 'Compensé par %s' % csem['titreannee']
        
        if d['decision_sem'] and d['decision_sem']['compense_formsemestre_id']:
            compensed = znotes.get_formsemestre(d['decision_sem']['compense_formsemestre_id'])
            obs += ' Compense %s' % compensed['titreannee']
        
        d['observation'] = obs
        
        # Cherche la date de decision (sem ou UE) la plus récente:
        if d['decision_sem']:
            date = DateDMYtoISO(d['decision_sem']['event_date'])
            if date > max_date: # decision plus recente
                max_date = date
        if d['decisions_ue']:
            for dec_ue in d['decisions_ue'].values():
                if dec_ue:
                    date = DateDMYtoISO(dec_ue['event_date'])
                    if date > max_date: # decision plus recente
                        max_date = date
        # Code semestre precedent
        if with_prev: # optionnel car un peu long...
            etud = znotes.getEtudInfo(etudid=etudid, filled=True)[0]
            Se = sco_parcours_dut.SituationEtudParcours(znotes, etud, formsemestre_id)
            if Se.prev and Se.prev_decision:
                d['prev_decision_sem'] = Se.prev_decision
                d['prev_code'] = Se.prev_decision['code']
                d['prev_code_descr'] = descr_decision_sem(znotes, 'I', Se.prev_decision)
                d['prev'] = Se.prev
                has_prev = True
            else:
                d['prev_decision_sem'] = None
                d['prev_code'] = ''
                d['prev_code_descr'] = ''
            d['Se'] = Se
        
        L.append(d)
    return { 'date' : DateISOtoDMY(max_date),
             'formsemestre' : sem, 
             'has_prev' : has_prev,
             'semestre_non_terminal' : Se.semestre_non_terminal,
             'formation' : znotes.do_formation_list(args={'formation_id':sem['formation_id']})[0],
             'decisions' : L }


def pvjury_table(znotes, dpv):
    """idem mais rend list de dicts
    """
    sem = dpv['formsemestre']
    if sem['semestre_id'] >= 0:
        id_cur = ' S%s' % sem['semestre_id']
    else:
        id_cur = ''
    titles = {'etudid' : 'etudid', 'nomprenom' : 'Nom',
              'decision' : 'Décision' + id_cur,
              'ue_cap' : 'UE' + id_cur + ' capitalisées',
              'devenir' : 'Devenir', 'observations' : 'Observations'
              }
    columns_ids = ['nomprenom', 'decision', 'ue_cap', 'devenir', 'observations']
    if dpv['has_prev']:
        id_prev = sem['semestre_id'] - 1 # numero du semestre precedent
        titles['prev_decision'] = 'Décision S%s' % id_prev
        columns_ids[1:1] = ['prev_decision']
    lines = []
    for e in dpv['decisions']:
        l = { 'etudid' : e['identite']['etudid'],
              'nomprenom' : znotes.nomprenom(e['identite']),
              '_nomprenom_target' : '%s/ficheEtud?etudid=%s' % (znotes.ScoURL(),e['identite']['etudid']),
              'decision' : descr_decision_sem_abbrev(znotes, e['etat'], e['decision_sem']),
              'ue_cap' : e['decisions_ue_descr'],
              'devenir' : e['autorisations_descr'],
              'observations' : unquote(e['observation']) }        
        if dpv['has_prev']:
            l['prev_decision'] = descr_decision_sem_abbrev(znotes, None, e['prev_decision_sem'])
        lines.append(l)
    return lines, titles, columns_ids

    
def formsemestre_pvjury(context, formsemestre_id, format='html', REQUEST=None):
    """Page récapitulant les décisions de jury
    dpv: result of dict_pvjury
    """
    header = context.sco_header(REQUEST)
    footer = context.sco_footer(REQUEST)
    dpv = dict_pvjury(context, formsemestre_id, with_prev=True)
    if not dpv:
        return header + '<h2>Aucune information disponible !</h2>' + footer

    sem = dpv['formsemestre']
    formsemestre_id = sem['formsemestre_id']

    rows, titles, columns_ids = pvjury_table(context, dpv)
    if format != 'html' and format != 'pdf':
        columns_ids=['etudid'] + columns_ids
    
    tab = GenTable(rows=rows, titles=titles,
                   columns_ids=columns_ids,
                   filename=make_filename('decisions ' + sem['titreannee']),
                   origin = 'Généré par %s le ' % VERSION.SCONAME + timedate_human_repr() + '',
                   caption = 'Décisions jury pour ' + sem['titreannee'],
                   html_class='gt_table table_pvjury',
                   html_sortable=True
                   )
    if format != 'html':
        return tab.make_page(context, format=format, with_html_headers=False, REQUEST=REQUEST)
    tab.base_url = '%s?formsemestre_id=%s' % (REQUEST.URL0, formsemestre_id)
    H = [ """<h2>Décisions du jury pour le semestre <a href="formsemestre_status?formsemestre_id=%s">%s</a></h2>
    <p>(dernière modif le %s)</p>""" 
          % (formsemestre_id, sem['titreannee'], dpv['date']) ]

    #
    H.append('<ul><li><a class="stdlink" href="formsemestre_lettres_individuelles?formsemestre_id=%s">Courriers individuels (classeur pdf)</a></li>' % formsemestre_id)
    H.append('<li><a class="stdlink" href="formsemestre_pvjury_pdf?formsemestre_id=%s">PV officiel (pdf)</a></li></ul>' % formsemestre_id)

    H.append( tab.html() )
    
    # Légende des codes
    codes = sco_codes_parcours.CODES_EXPL.keys()
    codes.sort()
    H.append('<h3>Explication des codes</h3><p><table class="expl_codes">')
    for code in codes:
        H.append('<tr><td>%s</td><td>%s</td></tr>' %
                 (code, sco_codes_parcours.CODES_EXPL[code]))
    H.append('</table>')

    return header + '\n'.join(H) + footer
