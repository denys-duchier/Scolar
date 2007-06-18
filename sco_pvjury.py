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

# XML generation package (apt-get install jaxml)
import jaxml

import sco_parcours_dut
import sco_codes_parcours
from notesdb import *

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

def descr_decisions_ues(znotes, decisions_ue):
    "résumé textuel des décisions d'UE"
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
    "résumé textuel de la décision de semestre"
    if etat == 'D':
        decision = 'démission'
    else:
        if decision_sem:
            cod = decision_sem['code']
            decision = sco_codes_parcours.CODES_EXPL.get(cod,'') + ' (%s)' % cod
        else:
            decision = ''
    return decision

def descr_autorisations(znotes, autorisations):
    "résumé texturl des autorisations d'inscription (-> 'S1, S3' )"
    alist = []
    for aut in autorisations:
        alist.append( 'S' + str(aut['semestre_id']) )
    return ', '.join(alist)


def dict_pvjury( znotes, formsemestre_id, etudids=None ):
    """Données pour édition jury
    etudids == None => tous les inscrits, sinon donne la liste des ids
    Résultat:
    {
    'date' : date de la decision la plus recente,
    'decisions' : { [ { 'identite' : {'nom' :, 'prenom':,  ...,},
                        'etat' : I ou D
                        'decision' : {'code':, 'code_prev': },
                        'ues' : {  ue_id : { 'code' : ADM|CMP|AJ, 'event_date' :,
                                             'acronyme', 'numero': } },
                        'autorisations' : [ { 'semestre_id' : { ... } } ]
                  }
    }    
    """
    nt = znotes._getNotesCache().get_NotesTable(znotes, formsemestre_id)
    if etudids is None:
        etudids = nt.get_etudids()
    sem = znotes.do_formsemestre_list(args={ 'formsemestre_id' : formsemestre_id } )[0]
    max_date = '0000-01-01'
    L = []
    for etudid in etudids:
        d = {}
        d['identite'] = nt.identdict[etudid]
        d['etat'] = nt.get_etud_etat(etudid) # I|D  (inscription ou démission)
        d['decision_sem'] = nt.get_etud_decision_sem(etudid)
        d['decisions_ue'] = nt.get_etud_decision_ues(etudid)
        # Versions "en français":
        d['decisions_ue_descr'] = descr_decisions_ues(znotes, d['decisions_ue'])
        d['decision_sem_descr'] = descr_decision_sem(znotes, d['etat'], d['decision_sem'])

        d['autorisations'] = sco_parcours_dut.formsemestre_get_autorisation_inscription(
            znotes, etudid, formsemestre_id)
        d['autorisations_descr'] = descr_autorisations(znotes, d['autorisations'])
        
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
        
        L.append(d)
    return { 'date' : DateISOtoDMY(max_date), 'decisions' : L }

