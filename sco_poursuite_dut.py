# -*- mode: python -*-
# -*- coding: iso8859-15 -*-

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
#   Emmanuel Viennet      emmanuel.viennet@gmail.com
#
##############################################################################

"""Extraction de données pour poursuites d'études

Recapitule tous les semestres validés dans une feuille excel.
"""

from odict import odict

from notesdb import *
from sco_utils import *
from notes_log import log
from gen_tables import GenTable
import sco_groups
from sco_codes_parcours import code_semestre_validant, code_semestre_attente

def etud_get_poursuite_info(context, sem, etud):
    """{ 'nom' : ..., 'semlist' : [ { 'semestre_id': , 'moy' : ... }, {}, ...] }
    """
    I = {}
    I.update(etud) # copie nom, prenom, sexe, ...
    
    # Now add each semester, starting from the first one
    semlist = []
    current_id = sem['semestre_id']
    for sem_id in range(1, current_id+1):
        sem_descr = None
        for s in etud['sems']:
            if s['semestre_id'] == sem_id:
                etudid = etud['etudid']
                nt = context._getNotesCache().get_NotesTable(context, s['formsemestre_id'])
                dec = nt.get_etud_decision_sem(etudid)
                if (dec
                    and (code_semestre_validant(dec['code']) or code_semestre_attente(dec['code']))
                    and nt.get_etud_etat(etudid) == 'I'):
                    sem_descr = odict( data=(
                        ('moy', nt.get_etud_moy_gen(etudid)),
                        ('rang', nt.get_etud_rang(etudid)),
                        ('effectif', len(nt.T)),
                        ('date_debut', s['date_debut']),
                        ('date_fin', s['date_fin']),
                        ('periode', '%s - %s' % (s['mois_debut'], s['mois_fin']))
                        ))
        if not sem_descr:
            sem_descr = odict( data=(('moy',''), ('rang',''), ('effectif', ''),
                               ('date_debut', ''), ('date_fin', ''), ('periode', '')))
        sem_descr['semestre_id'] = sem_id
        semlist.append(sem_descr)

    I['semlist'] = semlist
    return I

def _flatten_info(info):
    # met la liste des infos semestres "a plat"
    # S1_moy, S1_rang, ..., S2_moy, ...
    ids = []
    for s in info['semlist']:
        for k, v in s.items():
            if k != 'semestre_id':
                label = 'S%s_%s' % (s['semestre_id'], k)
                info[label] = v
                ids.append(label)
    return ids

def formsemestre_poursuite_report(context, formsemestre_id, format='html', REQUEST=None):
    """Table avec informations "poursuite"
    """
    sem = context.get_formsemestre(formsemestre_id)
    nt = context._getNotesCache().get_NotesTable(context, formsemestre_id)
    etuds = context.getEtudInfoGroupe(sco_groups.get_default_group(context, formsemestre_id))
    
    infos = []
    ids = []
    for etud in etuds:
        etud['_nom_target'] = 'ficheEtud?etudid=' + etud['etudid']
        etud['_prenom_target'] = 'ficheEtud?etudid=' + etud['etudid']
        etud['_nom_td_attrs'] = 'id="%s" class="etudinfo"' % (etud['etudid'])
        info = etud_get_poursuite_info(context, sem, etud)
        ids =  _flatten_info(info)
        infos.append(info)
    #
    column_ids = ('sexe', 'nom', 'prenom', 'annee') + tuple(ids) + ('debouche',)
    titles = {}
    for c in column_ids:
        titles[c] = c
    tab = GenTable( titles=titles,
                    columns_ids=column_ids,
                    rows=infos,
                    # lines_titles=lines_titles,
                    # html_col_width='4em',
                    html_sortable=True,
                    html_class='gt_table table_leftalign table_listegroupe',
                    pdf_link=False, # pas d'export pdf
                    preferences=context.get_preferences(formsemestre_id) )
    tab.filename = make_filename('poursuite ' + sem['titreannee'])
    
    tab.origin = 'Généré par %s le ' % VERSION.SCONAME + timedate_human_repr() + ''
    tab.caption = "Récapitulatif %s." % sem['titreannee']
    tab.html_caption = "Récapitulatif %s." % sem['titreannee']
    tab.base_url = '%s?formsemestre_id=%s' % (REQUEST.URL0, formsemestre_id)
    return tab.make_page(
        context, 
        title =  """<h2 class="formsemestre">Poursuite d'études</h2>""",
        init_qtip = True,
        javascripts=['js/etud_info.js'],
        format=format, REQUEST=REQUEST, with_html_headers=True)

