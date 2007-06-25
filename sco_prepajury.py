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
    prev_code = {} # decisions sem prec
    assidu = {}
    parcours = {} # etudid : parcours, sous la forme S1, S2, S2, S3
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

        # parcours:
        sems = Se.get_semestres()
        p = []
        for s in sems:
            p.append( 'S%d' % s['semestre_id'] )
        parcours[etudid] = ', '.join(p)
    
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
    
    titles = ['Nom', 'Ann�e', 'Parcours']
    if prev_moy: # si qq chose dans precedent
        titles += ue_prev_acros + ['Moy %s'% sp, 'D�cision %s' % sp]
    titles += ue_acros + ['Moy %s' % sn]
    if code:
        titles.append('D�cision %s' % sn)
    titles.append('Assidu')
    L.append(titles)

    def fmt(x):
        "reduit les notes a deux chiffres"
        x = notes_table.fmt_note(x, keep_numeric=False)
        try:
            return float(x)
        except:
            return x
    
    for etudid in etudids:
        l = [znotes.nomprenom(nt.identdict[etudid]),
             nt.identdict[etudid]['annee_naissance'],
             parcours[etudid]]
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
        l.append(assidu.get(etudid, ''))
        L.append(l)
    #
    L.append( [''] )
    L.append( ['Pr�par� par %s le %s sur %s pour %s' %
               (VERSION.SCONAME, time.strftime('%d/%m/%Y'),
                REQUEST.BASE0, REQUEST.AUTHENTICATED_USER) ] )
    xls = sco_excel.Excel_SimpleTable(
        titles=('Feuille pr�paration Jury %s' %
                unescape_html(sem['titreannee']),),
        lines=L, SheetName='Prepa Jury %s' % sn )
    return sco_excel.sendExcelFile(REQUEST, xls, 'PrepaJury%s.xls' % sn )
