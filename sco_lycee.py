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

"""Rapports sur lycées d'origine des étudiants d'un  semestre.
  - statistiques decisions
  - suivi cohortes
"""

import tempfile, urllib, re

from notesdb import *
from sco_utils import *
from notes_log import log
import scolars
import sco_groups
import sco_report
from gen_tables import GenTable

def formsemestre_table_etuds_lycees(context, formsemestre_id, group_lycees=True, only_primo=False):
    """Récupère liste d'etudiants avec etat et decision.
    """
    sem = context.get_formsemestre(formsemestre_id)
    etuds = sco_report.tsp_etud_list(context, formsemestre_id, only_primo=only_primo)
    if only_primo:
        primostr='primo-entrants du '
    else:
        primostr='du '
    title = 'Lycées des étudiants %ssemestre '%primostr + sem['titreannee']
    return _table_etuds_lycees(context, etuds, group_lycees, title, context.get_preferences(formsemestre_id))


def scodoc_table_etuds_lycees(context, format='html', REQUEST=None):
    """Table avec _tous_ les étudiants des semestres non verrouillés de _tous_ les départements.
    """
    semdepts = scodoc_get_all_unlocked_sems(context)
    etuds = []
    for (sem, deptcontext) in semdepts:
        etuds += sco_report.tsp_etud_list(deptcontext, sem['formsemestre_id'])
    
    tab, etuds_by_lycee = _table_etuds_lycees(context, etuds, False, 'Lycées de TOUS les étudiants',
                                              context.get_preferences(), no_links=True)
    tab.base_url = REQUEST.URL0
    t = tab.make_page(context, format=format, with_html_headers=False, REQUEST=REQUEST)
    if format != 'html':
        return t
    H = [ context.sco_header(REQUEST, page_title=tab.page_title,
                             init_google_maps=True,
                             init_jquery_ui=True,
                             init_qtip = True,
                             javascripts=[
                                 'js/etud_info.js',
                                 'js/map_lycees.js'
                                 ], ),
          """<h2 class="formsemestre">Lycées d'origine des %d étudiants (%d semestres)</h2>""" % (len(etuds),len(semdepts)),
          t,
          """<div id="lyc_map_canvas"></div>          
          """,
          js_coords_lycees(etuds_by_lycee),
          context.sco_footer(REQUEST)
          ]
    return '\n'.join(H)


def scodoc_get_all_unlocked_sems(context):
    """Liste de tous les semestres non verrouillés de tous les départements"""
    depts = context.list_depts()
    log('depts=%s' % depts)
    semdepts = []
    for dept in depts:
        semdepts += [ (sem, dept.Scolarite.Notes) for sem in dept.Scolarite.Notes.do_formsemestre_list() if sem['etat'] == '1' ]        
    return semdepts

def _table_etuds_lycees(context, etuds, group_lycees, title, preferences, no_links=False):
    etuds = [ scolars.etud_add_lycee_infos(e) for e in etuds ]
    etuds_by_lycee = group_by_key(etuds, 'codelycee')
    # 
    if group_lycees:        
        L = [ etuds_by_lycee[codelycee][0] for codelycee in etuds_by_lycee ]
        for l in L:
            l['nbetuds'] = len(etuds_by_lycee[l['codelycee']])
        # L.sort( key=operator.itemgetter('codepostallycee', 'nomlycee') ) argh, only python 2.5+ !!!
        L.sort( cmp=lambda x,y: cmp( (x['codepostallycee'],x['nomlycee']), (y['codepostallycee'],y['nomlycee']) ) )
        columns_ids = ('nbetuds', 'codelycee', 'codepostallycee', 'villelycee', 'nomlycee')
        bottom_titles =  { 'nbetuds' : len(etuds),
                           'nomlycee' : '%d lycées' % len([x for x in etuds_by_lycee if etuds_by_lycee[x][0]['codelycee']]) } 
    else:
        L = etuds
        columns_ids = ('sexe', 'nom', 'prenom', 'codelycee', 'codepostallycee', 'villelycee', 'nomlycee')
        bottom_titles = None
        if not no_links:
            for etud in etuds:
                etud['_nom_target'] = 'ficheEtud?etudid=' + etud['etudid']
                etud['_prenom_target'] = 'ficheEtud?etudid=' + etud['etudid']
                etud['_nom_td_attrs'] = 'id="%s" class="etudinfo"' % (etud['etudid'])
            
    tab = GenTable(columns_ids=columns_ids, rows=L,
                   titles={ 
                       'nbetuds' : "Nb d'étudiants",
                       'sexe' : '', 'nom' : 'Nom', 'prenom':'Prénom',
                       'etudid' : 'etudid',
                       'codelycee' : 'Code Lycée',
                       'codepostallycee' : 'Code postal',
                       'nomlycee' : 'Lycée',
                       'villelycee' : 'Commune'
                       },
                   origin = 'Généré par %s le ' % VERSION.SCONAME + timedate_human_repr() + '',
                   caption = title,
                   page_title = "Carte lycées d'origine",
                   html_sortable=True,
                   html_class='gt_table table_leftalign table_listegroupe',
                   bottom_titles = bottom_titles,
                   preferences=preferences
                   )
    return tab, etuds_by_lycee

def formsemestre_etuds_lycees(context, formsemestre_id, format='html',
                              only_primo=False, no_grouping=False,
                              REQUEST=None):
    """Table des lycées d'origine"""
    sem = context.get_formsemestre(formsemestre_id)
    tab, etuds_by_lycee = formsemestre_table_etuds_lycees(context, formsemestre_id, only_primo=only_primo, group_lycees=not no_grouping)
    tab.base_url = '%s?formsemestre_id=%s' % (REQUEST.URL0, formsemestre_id)
    if only_primo:
        tab.base_url += '&only_primo=1'
    if no_grouping:
        tab.base_url += '&no_grouping=1'
    t = tab.make_page(context, format=format, with_html_headers=False, REQUEST=REQUEST)
    if format != 'html':
        return t
    F = [ sco_report.tsp_form_primo_group(REQUEST, only_primo, no_grouping, formsemestre_id, format) ]    
    H = [ context.sco_header(REQUEST, page_title=tab.page_title,
                             init_google_maps=True,
                             init_jquery_ui=True,
                             init_qtip = True,
                             javascripts=[
                                 'js/etud_info.js',
                                 'js/map_lycees.js'
                                 ], ),
          """<h2 class="formsemestre">Lycées d'origine des étudiants</h2>""",
          '\n'.join(F),
          t,
          """<div id="lyc_map_canvas"></div>          
          """,
          js_coords_lycees(etuds_by_lycee),
          context.sco_footer(REQUEST)
          ]
    return '\n'.join(H)

def qjs(txt): # quote for JS
    return txt.replace("'", r"\'").replace('"', r'\"')

def js_coords_lycees(etuds_by_lycee):
    """Formatte liste des lycees en JSON pour Google Map"""
    L = []
    for codelycee in etuds_by_lycee:
        if codelycee:
            lyc = etuds_by_lycee[codelycee][0]            
            if not lyc.get('positionlycee', False):
                continue
            listeetuds = '<br/>%d étudiants: ' % len(etuds_by_lycee[codelycee]) + ', '.join(
                [ '<a class="discretelink" href="ficheEtud?etudid=%s" title="">%s</a>'
                  % (e['etudid'], qjs(e['nomprenom']))
                  for e in etuds_by_lycee[codelycee] ] )
            pos = qjs(lyc['positionlycee'])
            legend = '%s %s' % (qjs('%(nomlycee)s (%(villelycee)s)' % lyc), listeetuds)
            L.append( "{'position' : '%s', 'name' : '%s', 'number' : %d }"
                      % (pos, legend, len(etuds_by_lycee[codelycee])))
    
    return """<script type="text/javascript">
          var lycees_coords = [%s];
          </script>""" % ','.join(L)
