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

"""PV Jury IUTV 2006: on d�taillait 8 cas:
Jury de semestre n
    On a 8 types de d�cisions:
    Passages:
    1. passage de ceux qui ont valid�s Sn-1
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

def descr_decisions_ues(znotes, decisions_ue):
    "r�sum� textuel des d�cisions d'UE"
    if not decisions_ue:
        return ''
    uelist = []
    for ue_id in decisions_ue.keys():
        if decisions_ue[ue_id]['code'] == 'ADM':
            ue = znotes.do_ue_list( args={ 'ue_id' : ue_id } )[0]
            uelist.append(ue)
    uelist.sort( lambda x,y: cmp(x['numero'],y['numero']) )
    ue_acros = ', '.join( [ ue['acronyme'] for ue in uelist ] )
    
    return ue_acros

def descr_decision_sem(znotes, etat, decision_sem):
    "r�sum� textuel de la d�cision de semestre"
    if etat == 'D':
        decision = 'D�mission'
    else:
        if decision_sem:
            cod = decision_sem['code']
            decision = sco_codes_parcours.CODES_EXPL.get(cod,'') #+ ' (%s)' % cod
        else:
            decision = ''
    return decision

def descr_decision_sem_abbrev(znotes, etat, decision_sem):
    "r�sum� textuel tres court (code) de la d�cision de semestre"
    if etat == 'D':
        decision = 'D�mission'
    else:
        if decision_sem:
            decision = decision_sem['code']
        else:
            decision = ''
    return decision

def descr_autorisations(znotes, autorisations):
    "r�sum� texturl des autorisations d'inscription (-> 'S1, S3' )"
    alist = []
    for aut in autorisations:
        alist.append( 'S' + str(aut['semestre_id']) )
    return ', '.join(alist)


def dict_pvjury( znotes, formsemestre_id, etudids=None, with_prev=False ):
    """Donn�es pour �dition jury
    etudids == None => tous les inscrits, sinon donne la liste des ids
    Si with_prev: ajoute infos sur code jury semestre precedent
    R�sultat:
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
                        'prev_code' : code (calcul� slt si with_prev)
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
        d['etat'] = nt.get_etud_etat(etudid) # I|D  (inscription ou d�mission)
        d['decision_sem'] = nt.get_etud_decision_sem(etudid)
        d['decisions_ue'] = nt.get_etud_decision_ues(etudid)
        # Versions "en fran�ais":
        d['decisions_ue_descr'] = descr_decisions_ues(znotes, d['decisions_ue'])
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
            obs += 'Compens� par %s' % csem['titreannee']
        
        if d['decision_sem'] and d['decision_sem']['compense_formsemestre_id']:
            compensed = znotes.get_formsemestre(d['decision_sem']['compense_formsemestre_id'])
            obs += ' Compense %s' % compensed['titreannee']
        
        d['observation'] = obs
        
        # Cherche la date de decision (sem ou UE) la plus r�cente:
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
    """List of tuples"""
    sem = dpv['formsemestre']
    if sem['semestre_id'] >= 0:
        id_cur = ' S%s' % sem['semestre_id']
    else:
        id_cur = ''

    titles = ['etudid', 'Nom']
    if dpv['has_prev']:
        id_prev = sem['semestre_id'] - 1 # numero du semestre precedent
        titles += ['D�cision S%s' % id_prev]
        
    titles += ['D�cision' + id_cur, 'UE' + id_cur + ' capitalis�es',
               'Devenir', 'Observations']
    lines = []
    for e in dpv['decisions']:
        if dpv['has_prev']:
            lines.append( (e['identite']['etudid'],
                           znotes.nomprenom(e['identite']),
                           descr_decision_sem_abbrev(znotes, None, e['prev_decision_sem']),
                           descr_decision_sem_abbrev(znotes, e['etat'], e['decision_sem']),
                           e['decisions_ue_descr'],
                           e['autorisations_descr'],
                           unquote(e['observation'])
                           )
                          )
        else:
            lines.append( (e['identite']['etudid'],
                           znotes.nomprenom(e['identite']),
                           descr_decision_sem_abbrev(znotes, e['etat'], e['decision_sem']),
                           e['decisions_ue_descr'],
                           e['autorisations_descr'],
                           unquote(e['observation'])
                           )
                          )
    return titles, lines


def pvjury_excel(znotes, dpv):
    """Tableau Excel r�capitulant les d�cisions de jury
    dpv: result of dict_pvjury
    """
    if not dpv:
        return ''
    sem = dpv['formsemestre']
    
    titles, lines = pvjury_table(znotes, dpv)
    return sco_excel.Excel_SimpleTable(
        titles=titles, lines=lines,
        SheetName='Jury %s' % unquote(sem['titreannee']) )
    
def pvjury_html(znotes, dpv, REQUEST):
    """Page HTML r�capitulant les d�cisions de jury
    dpv: result of dict_pvjury
    """
    header = znotes.sco_header(REQUEST)
    footer = znotes.sco_footer(REQUEST)

    if not dpv:
        return header + '<h2>Aucune information disponible !</h2>' + footer

    sem = dpv['formsemestre']
    formsemestre_id = sem['formsemestre_id']
    if sem['semestre_id'] >= 0:
        id_cur = ' S%s' % sem['semestre_id']
    else:
        id_cur = ''
    
    H = [ """<h2>D�cisions du jury pour le semestre <a href="formsemestre_status?formsemestre_id=%s">%s</a></h2>
    <p>(derni�re modif le %s)   <a href="formsemestre_pvjury?formsemestre_id=%s&format=xls">Version Excel</a></p><p>
    <table class="tablegrid"><tr><th>Nom</th>"""
          % (formsemestre_id, sem['titreannee'], dpv['date'], formsemestre_id) ]
    if dpv['has_prev']:
        id_prev = sem['semestre_id'] - 1 # numero du semestre precedent
        H.append('<th>D�cision S%s</th>' % id_prev )
    H.append('<th>D�cision%s</th><th>UE capitalis�es</th><th>Autorisations</th><th></th></tr>' % id_cur )
    #
    for e in dpv['decisions']:
        cod = descr_decision_sem_abbrev(znotes, e['etat'], e['decision_sem'])
        H.append( '<tr><td><a href="%s/ficheEtud?etudid=%s">%s</a></td>'
                  % (znotes.ScoURL(), e['identite']['etudid'],
                     znotes.nomprenom(e['identite'])))
        if dpv['has_prev']:
            H.append('<td>%s</td>' %
                     descr_decision_sem_abbrev(znotes,None,e['prev_decision_sem']))
        H.append( '<td>%s</td><td>%s</td>' % (cod, e['decisions_ue_descr']))

        H.append('<td>%s</td><td>%s</td></tr>' % (e['autorisations_descr'], e['observation']))
    H.append('</table></p>')

    #
    H.append('<ul><li><a class="stdlink" href="formsemestre_lettres_individuelles?formsemestre_id=%s">Courriers individuels (classeur pdf)</a></li>' % formsemestre_id)
    H.append('<li><a class="stdlink" href="formsemestre_pvjury_pdf?formsemestre_id=%s">PV officiel (pdf)</a></li></ul>' % formsemestre_id)
    
    # L�gende des codes
    codes = sco_codes_parcours.CODES_EXPL.keys()
    codes.sort()
    H.append('<h3>Explication des codes</h3><p><table class="expl_codes">')
    for code in codes:
        H.append('<tr><td>%s</td><td>%s</td></tr>' %
                 (code, sco_codes_parcours.CODES_EXPL[code]))
    H.append('</table>')

    return header + '\n'.join(H) + footer
