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
    """R�cup�re liste d'etudiants avec etat et decision.
    """
    nt = context._getNotesCache().get_NotesTable(context, sem['formsemestre_id'])
    T = nt.get_table_moyennes_triees()
    # Construit liste d'�tudiants du semestre avec leur decision
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
        # Ajout cl� 'bac-specialite'
        bs = []
        if etud['bac']:
            bs.append(etud['bac'])
        if etud['specialite']:
            bs.append(etud['specialite'])
        etud['bac-specialite'] = ' '.join(bs)
        #
        etuds.append(etud)
    return etuds


def _categories_and_results(etuds, category, result):
    categories = {}
    results = {}
    for etud in etuds:
        categories[etud[category]] = True
        results[etud[result]] = True
    categories = categories.keys()
    categories.sort()
    results = results.keys()
    results.sort()
    return categories, results

def _results_by_category(etuds, category='', result='', category_name=None):
    """Construit table: categories (eg types de bacs) en ligne, d�cisions jury en colonnes

    etuds est une liste d'etuds (dicts).
    category et result sont des cl�s de etud (category d�finie les lignes, result les colonnes).

    Retourne une table.
    """
    if category_name is None:
        category_name = category
    # types de bacs differents:
    categories, results = _categories_and_results(etuds, category, result)
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
    # pourcentages sur chaque total de ligne
    for l in C:
        l['sumpercent'] = '%2.1f%%' % ((100. * l['sum']) / tot)
    if C: # ligne du bas avec totaux:
        s = {}
        for code in codes:
            s[code] = sum([ l[code] for l in C])
        s['sum'] = tot
        s['sumpercent'] = '100%'
        s['_css_row_class'] = 'sortbottom'
        C.append(s)
    #
    codes.append('sum')
    codes.append('sumpercent')
    titles = {}
    # on veut { 'ADM' : 'ADM' }, peu elegant en python 2.3:
    map( lambda x,titles=titles: titles.__setitem__(x[0],x[1]), zip(codes,codes) )
    titles['sum'] = 'Total'
    titles['sumpercent'] = '%'
    titles['DEM'] = 'D�m.' # d�missions
    for i in range(len(categories)):
        if categories[i] == '':
            categories[i] = '?'
    lines_titles = [category_name] + categories + ['Total']
    return GenTable( titles=titles, columns_ids=codes, rows=C, lines_titles=lines_titles,
                     html_col_width='4em', html_sortable=True )


# pages
def formsemestre_report(context, formsemestre_id, etuds, REQUEST=None,
                        category='bac', result='codedecision', 
                        category_name='', result_name='',
                        title='Statistiques'):    
    """
    Tableau sur r�sultats (result) par type de category bac
    """
    sem = context.get_formsemestre(formsemestre_id)
    if not category_name:
        category_name = category
    if not result_name:
        result_name = result
    if result_name == 'codedecision':
        result_name = 'r�sultats'
    #
    tab = _results_by_category(etuds, category=category, category_name=category_name,
                               result=result)
    #
    tab.filename = make_filename('stats ' + sem['titreannee'])
    
    tab.origin = 'G�n�r� par %s le ' % VERSION.SCONAME + timedate_human_repr() + ''
    tab.caption = 'R�partition des r�sultats par %s, semestre %s' % (category_name, sem['titreannee'])
    tab.html_caption = "R�partition des r�sultats par %s." % category_name
    tab.base_url = '%s?formsemestre_id=%s' % (REQUEST.URL0, formsemestre_id)
    return tab



# def formsemestre_report_bacs(context, formsemestre_id, format='html', REQUEST=None):
#     """
#     Tableau sur r�sultats par type de bac
#     """
#     sem = context.get_formsemestre(formsemestre_id)
#     title = 'Statistiques bacs ' + sem['titreannee']
#     etuds = formsemestre_etuds_stats(context, sem)
#     tab = formsemestre_report(context, formsemestre_id, etuds, REQUEST=REQUEST,
#                               category='bac', result='codedecision',
#                               category_name='Bac',
#                               title=title)
#     return tab.make_page(
#         context, 
#         title =  """<h2>R�sultats de <a href="formsemestre_status?formsemestre_id=%(formsemestre_id)s">%(titreannee)s</a></h2>""" % sem,
#         format=format, page_title = title, REQUEST=REQUEST )

def formsemestre_report_counts(context, formsemestre_id, format='html', REQUEST=None,
                               category='bac', result='codedecision', allkeys=False):
    """
    Tableau comptage avec choix des categories
    """
    sem = context.get_formsemestre(formsemestre_id)
    category_name = category.capitalize()
    title = "Comptages " + category_name
    etuds = formsemestre_etuds_stats(context, sem)
    tab = formsemestre_report(context, formsemestre_id, etuds, REQUEST=REQUEST,
                              category=category, result=result,
                              category_name=category_name,
                              title=title)
    if etuds:
        if allkeys:
            keys = etuds[0].keys()
        else:
            # cl�s pr�sent�es � l'utilisateur:
            keys = ['annee_bac', 'annee_naissance', 'bac', 'specialite', 'bac-specialite',
                    'codedecision', 'etat', 'sexe', 'qualite', 'villelycee' ]
        keys.sort()
        F = [ """<form name="f" method="get"><p>
              Colonnes: <select name="result" onChange="document.f.submit()">""" ]
        for k in keys:
            if k == result:
                selected = 'selected'
            else:
                selected = ''
            F.append('<option value="%s" %s>%s</option>' % (k,selected,k))
        F.append('</select>')
        F.append(' Lignes: <select name="category" onChange="document.f.submit()">')
        for k in keys:
            if k == category:
                selected = 'selected'
            else:
                selected = ''
            F.append('<option value="%s" %s>%s</option>' % (k,selected,k))
        F.append('</select>')
        F.append('<input type="hidden" name="formsemestre_id" value="%s"/>' % formsemestre_id)        
        F.append('<input type="submit" value="OK"/>')
        F.append('</p></form>')

    t = tab.make_page(
        context, 
        title =  """<h2>Statistiques de <a href="formsemestre_status?formsemestre_id=%(formsemestre_id)s">%(titreannee)s</a></h2>""" % sem,
        format=format, REQUEST=REQUEST, with_html_headers=False)
    if format!='html':
        return t    
    H = [ context.sco_header(REQUEST, page_title=title),
          t, '\n'.join(F),
          context.sco_footer(REQUEST)
          ]
    return '\n'.join(H)

# --------------------------------------------------------------------------
def formsemestre_suivi_cohorte(context, formsemestre_id, format='html', REQUEST=None):
    """
    Tableau indicant le nombre d'etudiants de la cohorte dans chaque �tat:
    Etat     date_debut_Sn     date_fin_Sn  date_debut2 date_fin2 ...
    S_n       #inscrits en Sn
    S_n+1
    ...
    S_last
    Diplome
    Sorties

    Determination des dates:
    on suit chaque etudiant (parcours): liste [Sn, Sp, Sq, ...]
    on obtient alors une liste des semestres "suivant" Sn: {Sp tq Sp suit Sn pour un etudiant}

    Etat d'un etudiant � une date t ?
    """
    raise NotImplementedError
