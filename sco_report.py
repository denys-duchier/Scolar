# -*- mode: python -*-
# -*- coding: iso8859-15 -*-

##############################################################################
#
# Gestion scolarite IUT
#
# Copyright (c) 2001 - 2008 Emmanuel Viennet.  All rights reserved.
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

"""Rapports suivi:
  - statistiques decisions
  - suivi cohortes
"""
from notesdb import *
from sco_utils import *
from notes_log import log
from gen_tables import GenTable
import sco_excel, sco_pdf
import sco_codes_parcours
import VERSION

def formsemestre_etuds_stats(context, sem):
    """Récupère liste d'etudiants avec etat et decision.
    """
    nt = context._getNotesCache().get_NotesTable(context, sem['formsemestre_id'])
    T = nt.get_table_moyennes_triees()
    # Construit liste d'étudiants du semestre avec leur decision
    etuds = []
    for t in T:
        etudid = t[-1]
        etud= nt.identdict[etudid].copy()
        decision = nt.get_etud_decision_sem(etudid)
        if decision:
            etud['codedecision'] = decision['code']
        etud['etat'] = nt.get_etud_etat(etudid)
        if etud['etat'] == 'D':
            etud['codedecision'] = 'DEM'
        if not etud.has_key('codedecision'):
            etud['codedecision'] = '(nd)' # pas de decision jury
        etuds.append(etud)
    return etuds

def _results_by_category(etuds, category='', result='', category_name=None):
    """Construit table: categories (eg types de bacs) en ligne, décisions jury en colonnes

    etuds est une liste d'etuds (dicts) et category doit etre une cle de etud
    """
    if category_name is None:
        category_name = category
    # types de bacs differents:
    categories = {}
    for etud in etuds:
        categories[etud[category]] = True
    categories = categories.keys()
    categories.sort()
    #
    Count = {} # { bac : { decision : nb_avec_ce_bac_et_ce_code } }
    results = {} # { result_value : True }
    for etud in etuds:
        results[etud[result]] = True
        if Count.has_key(etud[category]):
            Count[etud[category]][etud[result]] += 1
        else:            
            Count[etud[category]] = DictDefault( kv_dict={ etud[result] : 1 } )
    # conversion en liste de dict
    C = [ Count[cat] for cat in categories ]
    # 
    codes = results.keys()
    codes.sort()
    # Totaux par lignes et colonnes
    tot = 0
    for l in C:
        l['sum'] = sum(l.values())
        tot += l['sum']
    
    if C:
        s = {}
        for code in codes:
            s[code] = sum([ l[code] for l in C])
        s['sum'] = tot
        C.append(s)
    #
    codes.append('sum')
    titles = {}
    # on veut { 'ADM' : 'ADM' }, peu elegant en python 2.3:
    map( lambda x,titles=titles: titles.__setitem__(x[0],x[1]), zip(codes,codes) )
    titles['sum'] = 'Total'
    titles['DEM'] = 'Dém.' # démissions
    for i in range(len(categories)):
        if categories[i] == '':
            categories[i] = '?'
    lines_titles = [category_name] + categories + ['Total']
    return GenTable( titles=titles, columns_ids=codes, rows=C, lines_titles=lines_titles,
                     html_col_width='4em' )


# pages
def formsemestre_report_bacs(context, formsemestre_id, format='html', REQUEST=None):
    """
    Tableau sur résultats par type de bac
    """
    sem = context.get_formsemestre(formsemestre_id)
    etuds = formsemestre_etuds_stats(context, sem)
    #
    tab_dec_par_bacs = _results_by_category(etuds, category='bac', category_name='Bac',
                                            result='codedecision')
    #
    title = 'Statistiques bacs ' + sem['titreannee']
    filename = make_filename('stats ' + sem['titreannee'])
    
    tab_dec_par_bacs.origin = 'Généré par %s le ' % VERSION.SCONAME + timedate_human_repr() + ''
    tab_dec_par_bacs.caption = 'Répartition des résultats par bac, semestre %s' % sem['titreannee']
    tab_dec_par_bacs.html_caption = "Répartition des résultats par type de bac."
    tab_dec_par_bacs.base_url = '%s?formsemestre_id=%s' % (REQUEST.URL0, formsemestre_id)

    if format == 'html':
        H = [
            context.sco_header(REQUEST, page_title=title),
            """<h2>Résultats de <a href="formsemestre_status?formsemestre_id=%(formsemestre_id)s">%(titreannee)s</a></h2>""" % sem,
            tab_dec_par_bacs.html(),
            context.sco_footer(REQUEST) ]
        return '\n'.join(H)
    elif format == 'pdf':
        tpdf = tab_dec_par_bacs.pdf()
        doc = sco_pdf.pdf_basic_page( [tpdf], title=title )
        return sendPDFFile(REQUEST, doc, filename + '.pdf' )   
    elif format == 'xls':
        xls = tab_dec_par_bacs.excel()
        return sco_excel.sendExcelFile(REQUEST, xls, filename + '.xls' )
    else:
        raise ValueError('formsemestre_report_bacs: invalid format')

