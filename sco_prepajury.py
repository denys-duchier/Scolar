# -*- mode: python -*-
# -*- coding: utf-8 -*-

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

"""Feuille excel pour preparation des jurys
"""


from notesdb import *
from sco_utils import *
from notes_log import log
import notes_table
import sco_groups
import sco_excel
import sco_parcours_dut, sco_codes_parcours
from scolars import format_nom, format_prenom, format_sexe, format_lycee
from ZAbsences import getAbsSemEtud


def feuille_preparation_jury(context, formsemestre_id, REQUEST):
    "Feuille excel pour preparation des jurys"
    nt = context._getNotesCache().get_NotesTable(context, formsemestre_id) #> get_etudids, get_etud_moy_gen, get_ues, get_etud_ue_status, get_etud_decision_sem, identdict, 
    etudids = nt.get_etudids( sorted=True ) # tri par moy gen
    sem= context.do_formsemestre_list( args={ 'formsemestre_id' : formsemestre_id } )[0]

    etud_groups = sco_groups.formsemestre_get_etud_groupnames(context, formsemestre_id)
    main_partition_id = sco_groups.formsemestre_get_main_partition(context, formsemestre_id)['partition_id']

    prev_moy_ue = DictDefault(defaultvalue={}) # ue_code_s : { etudid : moy ue }
    prev_ue_acro = {} # ue_code_s : acronyme (à afficher)
    prev_moy = {} # moyennes gen sem prec
    moy_ue = DictDefault(defaultvalue={}) # ue_acro : moyennes { etudid : moy ue }
    ue_acro = {} #  ue_code_s : acronyme (à afficher)
    moy = {} # moyennes gen
    moy_inter = {} # moyenne gen. sur les 2 derniers semestres
    code = {} # decision existantes s'il y en a
    autorisations = {}
    prev_code = {} # decisions sem prec
    assidu = {}
    parcours = {} # etudid : parcours, sous la forme S1, S2, S2, S3
    groupestd = {}# etudid : nom groupe principal
    nbabs = {}
    nbabsjust = {}
    for etudid in etudids:
        info = context.getEtudInfo(etudid=etudid, filled=True)
        if not info:
            continue # should not occur...
        etud = info[0]
        Se = sco_parcours_dut.SituationEtudParcours(context, etud, formsemestre_id)
        if Se.prev:
            ntp = context._getNotesCache().get_NotesTable(context, Se.prev['formsemestre_id']) #> get_ues, get_etud_ue_status, get_etud_moy_gen, get_etud_decision_sem
            for ue in ntp.get_ues(filter_sport=True):
                ue_status = ntp.get_etud_ue_status(etudid, ue['ue_id'])
                ue_code_s = ue['ue_code'] + '_%s' % ntp.sem['semestre_id'] # code indentifiant l'UE
                prev_moy_ue[ue_code_s][etudid] = ue_status['moy']
                prev_ue_acro[ue_code_s] = (ue['numero'], ue['acronyme'])
            prev_moy[etudid] = ntp.get_etud_moy_gen(etudid)
            prev_decision = ntp.get_etud_decision_sem(etudid)
            if prev_decision:
                prev_code[etudid] = prev_decision['code']
                if prev_decision['compense_formsemestre_id']:
                    prev_code[etudid] += '+' # indique qu'il a servi a compenser
        
        moy[etudid] = nt.get_etud_moy_gen(etudid)
        for ue in nt.get_ues(filter_sport=True):
            ue_status = nt.get_etud_ue_status(etudid, ue['ue_id'])
            ue_code_s = ue['ue_code'] + '_%s' % nt.sem['semestre_id']
            moy_ue[ue_code_s][etudid] = ue_status['moy']
            ue_acro[ue_code_s] = (ue['numero'], ue['acronyme'])
        
        if Se.prev:
            try:
                moy_inter[etudid] = (moy[etudid]+prev_moy[etudid]) / 2.
            except:
                pass
        
        decision = nt.get_etud_decision_sem(etudid)
        if decision:
            code[etudid] = decision['code']
            if decision['compense_formsemestre_id']:
                code[etudid] += '+' # indique qu'il a servi a compenser
            assidu[etudid] = {0 : 'Non', 1 : 'Oui'}.get(decision['assidu'], '')
        aut_list = sco_parcours_dut.formsemestre_get_autorisation_inscription(
            context, etudid, formsemestre_id)
        autorisations[etudid] = ', '.join([ 'S%s' % x['semestre_id'] for x in aut_list ])
        # parcours:
        parcours[etudid] = Se.get_parcours_descr() 
        # groupe principal (td)
        groupestd[etudid] = ''
        for s in etud['sems']:
            if s['formsemestre_id'] == formsemestre_id:       
                groupestd[etudid] = etud_groups.get(etudid, {}).get(main_partition_id, '')        
        # absences:
        AbsEtudSem = getAbsSemEtud(context, formsemestre_id, etudid)
        nbabs[etudid] = AbsEtudSem.CountAbs()
        nbabsjust[etudid] = AbsEtudSem.CountAbsJust()
    
    # Codes des UE "semestre précédent":
    ue_prev_codes = prev_moy_ue.keys()
    ue_prev_codes.sort( lambda x,y, prev_ue_acro=prev_ue_acro: cmp( prev_ue_acro[x], prev_ue_acro[y]) )
    # Codes des UE "semestre courant":
    ue_codes = moy_ue.keys()
    ue_codes.sort( lambda x,y, ue_acro=ue_acro: cmp( ue_acro[x], ue_acro[y]) )

    sid = sem['semestre_id']
    sn = sp = ''
    if sid >= 0:
        sn = 'S%s' % sid
        if prev_moy: # si qq chose dans precedent
            sp = 'S%s' % (sid-1)
    
    L = sco_excel.ScoExcelSheet( sheet_name='Prepa Jury %s' % sn )
    L.append( ['Feuille préparation Jury %s' % unescape_html(sem['titreannee']) ] )
    L.append( [] ) # empty line 
    
    titles = ['', 'etudid', 'Civ.', 'Nom', 'Prénom', 'Naissance', 'Bac', 'Spe', 'Parcours', 'Groupe' ]
    if prev_moy: # si qq chose dans precedent
        titles += [ prev_ue_acro[x][1] for x in ue_prev_codes] + ['Moy %s'% sp, 'Décision %s' % sp]
    titles += [ue_acro[x][1] for x in ue_codes] + ['Moy %s' % sn]
    if moy_inter:
        titles += ['Moy %s-%s' % (sp,sn)]
    titles += [ 'Abs', 'Abs Just.' ]
    if code:
        titles.append('Décision %s' % sn)
    if autorisations:
        titles.append('Autorisations')
    titles.append('Assidu')
    L.append(titles)
    style_bold = sco_excel.Excel_MakeStyle(bold=True)
    style_moy  = sco_excel.Excel_MakeStyle(bold=True, bgcolor='lightyellow')
    style_note = sco_excel.Excel_MakeStyle(halign='right')
    style_note_bold = sco_excel.Excel_MakeStyle(halign='right',bold=True)
    if prev_moy:
        col_prev_moy = 7
        col_prev_moy += len(ue_prev_codes) + 1
        col_moy = col_prev_moy + len(ue_codes) + 2
    else:
        col_moy = 8 + len(ue_codes)
    L.set_style( style_bold, li=0)
    L.set_style( style_bold, li=2)
    def fmt(x):
        "reduit les notes a deux chiffres"
        x = notes_table.fmt_note(x, keep_numeric=False)
        try:
            return float(x)
        except:
            return x

    i = 1 # numero etudiant
    for etudid in etudids:
        etud = nt.identdict[etudid]
        l = [ str(i), etudid, 
              format_sexe(etud['sexe']), format_nom(etud['nom']), format_prenom(etud['prenom']),
              etud['date_naissance'],
              etud['bac'], etud['specialite'],
              parcours[etudid], groupestd[etudid] ]
        co = len(l)
        if prev_moy:
            for ue_acro in ue_prev_codes:
                l.append(fmt(prev_moy_ue.get(ue_acro, {}).get(etudid,'')))
                L.set_style(style_note, li=i+2, co=co)
                co += 1
            l.append(fmt(prev_moy.get(etudid,'')))
            l.append(prev_code.get(etudid,''))
            L.set_style(style_bold, li=i+2, co=col_prev_moy) # moy gen prev
            L.set_style(style_moy,  li=i+2, co=col_prev_moy+1) # decision prev
            co += 2

        for ue_acro in ue_codes:
            l.append(fmt(moy_ue.get(ue_acro, {}).get(etudid,'')))
            L.set_style(style_note, li=i+2, co=co)
            co += 1
        l.append(fmt(moy.get(etudid,'')))
        L.set_style(style_note_bold, li=i+2, co=col_moy) # moy gen
        co += 1
        if moy_inter:
            l.append(fmt(moy_inter.get(etudid,'')))
            L.set_style(style_note, li=i+2, co=co)
        l.append(fmt(str(nbabs.get(etudid,''))))
        l.append(fmt(str(nbabsjust.get(etudid,''))))
        if code:
            l.append(code.get(etudid, ''))
        if autorisations:
            l.append(autorisations.get(etudid, ''))
        l.append(assidu.get(etudid, ''))
        L.append(l)
        i += 1
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
    
    xls = L.gen_workbook()
    
    return sco_excel.sendExcelFile(REQUEST, xls, 'PrepaJury%s.xls' % sn )
