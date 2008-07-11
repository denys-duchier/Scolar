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

"""Feuille excel pour preparation des jurys
"""


from notesdb import *
from sco_utils import *
from notes_log import log
import notes_table
import sco_excel
import sco_parcours_dut, sco_codes_parcours



def feuille_preparation_jury(znotes, formsemestre_id, REQUEST):
    "Feuille excel pour preparation des jurys"
    nt = znotes._getNotesCache().get_NotesTable(znotes, formsemestre_id)
    etudids = nt.get_etudids( sorted=True ) # tri par moy gen
    sem= znotes.do_formsemestre_list( args={ 'formsemestre_id' : formsemestre_id } )[0]

    prev_moy_ue = DictDefault(defaultvalue={}) # ue_acro : { etudid : moy ue }
    prev_moy = {} # moyennes gen sem prec
    moy_ue = DictDefault(defaultvalue={}) # ue_acro : moyennes { etudid : moy ue }
    moy = {} # moyennes gen
    code = {} # decision existantes s'il y en a
    autorisations = {}
    prev_code = {} # decisions sem prec
    assidu = {}
    parcours = {} # etudid : parcours, sous la forme S1, S2, S2, S3
    groupestd = {}
    for etudid in etudids:
        etud = znotes.getEtudInfo(etudid=etudid, filled=True)[0]
        Se = sco_parcours_dut.SituationEtudParcours(znotes, etud, formsemestre_id)
        if Se.prev:
            ntp = znotes._getNotesCache().get_NotesTable(znotes, Se.prev['formsemestre_id'])
            for ue in ntp.get_ues(filter_sport=True):
                ue_status = ntp.get_etud_ue_status(etudid, ue['ue_id'])
                prev_moy_ue[ue['acronyme']][etudid] = ue_status['moy_ue']
            prev_moy[etudid] = ntp.get_etud_moy_gen(etudid)
            prev_decision = ntp.get_etud_decision_sem(etudid)
            if prev_decision:
                prev_code[etudid] = prev_decision['code']
                if prev_decision['compense_formsemestre_id']:
                    prev_code[etudid] += '+' # indique qu'il a servi a compenser
        moy[etudid] = nt.get_etud_moy_gen(etudid)
        for ue in nt.get_ues(filter_sport=True):
            ue_status = nt.get_etud_ue_status(etudid, ue['ue_id'])
            moy_ue[ue['acronyme']][etudid] = ue_status['moy_ue']
        decision = nt.get_etud_decision_sem(etudid)
        if decision:
            code[etudid] = decision['code']
            if decision['compense_formsemestre_id']:
                code[etudid] += '+' # indique qu'il a servi a compenser
            assidu[etudid] = {0 : 'Non', 1 : 'Oui'}.get(decision['assidu'], '')
        aut_list = sco_parcours_dut.formsemestre_get_autorisation_inscription(
            znotes, etudid, formsemestre_id)
        autorisations[etudid] = ', '.join([ 'S%s' % x['semestre_id'] for x in aut_list ])
        # parcours:
        sems = Se.get_semestres()
        p = []
        for s in sems:
            if s['ins']['etat'] == 'D':
                dem = ' (dem.)'
            else:
                dem = ''
            if s['semestre_id'] >= 0:
                p.append( 'S%d%s' % (s['semestre_id'],dem) )
            else:
                p.append( 'A%d%s' % (s['semestre_id'],dem) )
        parcours[etudid] = ', '.join(p)
        # groupe td
        groupestd[etudid] = ''
        for s in etud['sems']:
            if s['formsemestre_id'] == formsemestre_id:                
                groupestd[etudid] = s['ins']['groupetd']
    # Construit table
    L = [ [] ]
    all_ues =  znotes.do_ue_list(args={ 'formation_id' : sem['formation_id']})
    ue_prev_acros = [] # celles qui sont utilisees ici
    for ue in all_ues:
        if prev_moy_ue.has_key(ue['acronyme']):
            ue_prev_acros.append(ue['acronyme'])
    
    ue_acros = [] # celles qui sont utilisees ici
    for ue in all_ues:
        if moy_ue.has_key(ue['acronyme']):
            ue_acros.append(ue['acronyme'])

    sid = sem['semestre_id']
    sn = sp = ''
    if sid >= 0:
        sn = 'S%s' % sid
        if prev_moy: # si qq chose dans precedent
            sp = 'S%s' % (sid-1)
    
    titles = ['', 'etudid', 'Nom', 'Année', 'Parcours', 'Groupe' ]
    if prev_moy: # si qq chose dans precedent
        titles += ue_prev_acros + ['Moy %s'% sp, 'Décision %s' % sp]
    titles += ue_acros + ['Moy %s' % sn]
    if code:
        titles.append('Décision %s' % sn)
    if autorisations:
        titles.append('Autorisations')
    titles.append('Assidu')
    L.append(titles)

    def fmt(x):
        "reduit les notes a deux chiffres"
        x = notes_table.fmt_note(x, keep_numeric=False)
        try:
            return float(x)
        except:
            return x

    i = 1 # numero etudiant
    for etudid in etudids:
        l = [ str(i), etudid, znotes.nomprenom(nt.identdict[etudid]),
             nt.identdict[etudid]['annee_naissance'],
             parcours[etudid], groupestd[etudid] ]
        i += 1
        if prev_moy:
            for ue_acro in ue_prev_acros:
                l.append(fmt(prev_moy_ue.get(ue_acro, {}).get(etudid,'')))
            l.append(fmt(prev_moy.get(etudid,'')))
            l.append(prev_code.get(etudid,''))
        for ue_acro in ue_acros:
            l.append(fmt(moy_ue.get(ue_acro, {}).get(etudid,'')))
        l.append(fmt(moy.get(etudid,'')))
        if code:
            l.append(code.get(etudid, ''))
        if autorisations:
            l.append(autorisations.get(etudid, ''))
        l.append(assidu.get(etudid, ''))
        L.append(l)
    #
    L.append( [''] )
    # Explications des codes
    codes = sco_codes_parcours.CODES_EXPL.keys()
    codes.sort()
    L.append(['Explication des codes'])
    for code in codes:
        L.append([ '', code, sco_codes_parcours.CODES_EXPL[code] ])
    L.append([ '', 'ADM+', 'indique que le semestre a déjà servi à en compenser un autre'])    
    #
    L.append( [''] )
    L.append( ['Préparé par %s le %s sur %s pour %s' %
               (VERSION.SCONAME, time.strftime('%d/%m/%Y'),
                REQUEST.BASE0, REQUEST.AUTHENTICATED_USER) ] )
    xls = sco_excel.Excel_SimpleTable(
        titles=('Feuille préparation Jury %s' %
                unescape_html(sem['titreannee']),),
        lines=L, SheetName='Prepa Jury %s' % sn )
    return sco_excel.sendExcelFile(REQUEST, xls, 'PrepaJury%s.xls' % sn )
