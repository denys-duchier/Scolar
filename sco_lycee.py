# -*- mode: python -*-
# -*- coding: iso8859-15 -*-

##############################################################################
#
# Gestion scolarite IUT
#
# Copyright (c) 2001 - 2012 Emmanuel Viennet.  All rights reserved.
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
    etuds = [ scolars.etud_add_lycee_infos(e) for e in etuds ]
    # 
    if group_lycees:
        etuds_by_lycee = group_by_key(etuds, 'codelycee')
        L = [ etuds_by_lycee[codelycee][0] for codelycee in etuds_by_lycee ]
        for l in L:
            l['nbetuds'] = len(etuds_by_lycee[l['codelycee']])
        # L.sort( key=operator.itemgetter('codepostallycee', 'nomlycee') ) argh, only python 2.5+ !!!
        L.sort( cmp=lambda x,y: cmp( (x['codepostallycee'],x['nomlycee']), (y['codepostallycee'],y['nomlycee']) ) )
        columns_ids = ('nbetuds', 'codelycee', 'codepostallycee', 'villelycee', 'nomlycee')
        bottom_titles =  { 'nbetuds' : len(etuds),
                           'nomlycee' : '%d lycées' % len([x for x in etuds_by_lycee if etuds_by_lycee[x][0]['codelycee']]) } 
    else:
        # tri par code postal puis nom:
        L = etuds
        # L.sort( key=operator.itemgetter('codepostallycee', 'nom') ) argh, only python 2.5+ !!!
        #L.sort( cmp=lambda x,y: cmp( (x['codepostallycee'],x['nom']), (y['codepostallycee'],y['nom']) ) )
        columns_ids = ('sexe', 'nom', 'prenom', 'codelycee', 'codepostallycee', 'villelycee', 'nomlycee')
        bottom_titles = None
        for etud in etuds:
            etud['_nom_target'] = 'ficheEtud?etudid=' + etud['etudid']
            etud['_prenom_target'] = 'ficheEtud?etudid=' + etud['etudid']
            etud['_nom_td_attrs'] = 'id="%s" class="etudinfo"' % (etud['etudid'])
            
    if only_primo:
        primostr='primo-entrants du '
    else:
        primostr='du '
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
                   caption = 'Lycées des étudiants %ssemestre '%primostr + sem['titreannee'],
                   page_title = 'Parcours ' + sem['titreannee'],
                   html_sortable=True,
                   html_class='gt_table table_leftalign table_listegroupe',
                   bottom_titles = bottom_titles,
                   preferences=context.get_preferences(formsemestre_id)
                   )
    return tab

def formsemestre_etuds_lycees(context, formsemestre_id, format='html',
                              only_primo=False, no_grouping=False,
                              REQUEST=None):
    """Table des lycées d'origine"""
    sem = context.get_formsemestre(formsemestre_id)
    tab = formsemestre_table_etuds_lycees(context, formsemestre_id, only_primo=only_primo, group_lycees=not no_grouping)
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
                             javascripts=['jQuery/jquery.js', 
                                          'libjs/qtip/jquery.qtip.js',
                                          'js/etud_info.js'
                                          ], ),
          """<h2 class="formsemestre">Lycées d'origine des étudiants</h2>""",
          '\n'.join(F),
          t, 
          context.sco_footer(REQUEST)
          ]
    return '\n'.join(H)
