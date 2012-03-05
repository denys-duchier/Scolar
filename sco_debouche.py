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
#   Emmanuel Viennet      emmanuel.viennet@gmail.com
#
##############################################################################

"""
Rapport (table) avec dernier semestre fréquenté et débouché de chaque étudiant
"""

from odict import odict

from notesdb import *
from sco_utils import *
from notes_log import log
from gen_tables import GenTable
import sco_groups

def report_debouche_date(context, start_year=None, format='html', REQUEST=None):
    """Rapport (table) pour les débouchés des étudiants sortis à partir de la l'année indiquée.
    """
    if not start_year:
        return report_debouche_ask_date(context, REQUEST=REQUEST)
    
    etudids = get_etudids_with_debouche(context, start_year)
    tab = table_debouche_etudids(context, etudids)

    tab.filename = make_filename('debouche_scodoc_%s' % start_year)
    tab.origin = 'Généré par %s le ' % VERSION.SCONAME + timedate_human_repr() + ''
    tab.caption = "Récapitulatif débouchés à partir du 1/1/%s." % start_year
    tab.base_url = '%s?start_year=%s' % (REQUEST.URL0, start_year)
    return tab.make_page(
        context, 
        title =  """<h2 class="formsemestre">Débouchés étudiants </h2>""",
        javascripts=['jQuery/jquery.js', 
                     'libjs/qtip/jquery.qtip.js',
                     'js/etud_info.js'
                     ],
        format=format, REQUEST=REQUEST, with_html_headers=True)

def get_etudids_with_debouche(context, start_year):
    """Liste des etudids de tous les semestres terminant
    à partir du 1er janvier de start_year
    et ayant un 'debouche' renseigné.
    """
    start_date = str(start_year) + '-01-01'
    # Recupere tous les etudid avec un debouché renseigné et une inscription dans un semestre
    # posterieur à la date de depart:
    r = SimpleDictFetch(context,
                        """SELECT DISTINCT i.etudid
                        FROM notes_formsemestre_inscription i, admissions adm, notes_formsemestre s
                        WHERE adm.debouche is not NULL
                        AND i.etudid = adm.etudid AND i.formsemestre_id = s.formsemestre_id
                        AND s.date_fin >= %(start_date)s
                        """,
                        {'start_date' : start_date })
    
    return [ x['etudid'] for x in r ]

def table_debouche_etudids(context, etudids):
    """Rapport pour ces etudiants
    """
    L = []
    for etudid in etudids:
        etud = context.getEtudInfo(filled=1, etudid=etudid)[0]
        # retrouve le "dernier" semestre (au sens de la date de fin)
        sems = etud['sems']
        es = [ (sems[i]['date_fin_iso'], i) for i in range(len(sems)) ]
        imax = max(es)[1]
        last_sem = sems[imax]
        nt = context._getNotesCache().get_NotesTable(context, last_sem['formsemestre_id'])
        L.append( {
            'etudid' : etudid,
            'sexe' : etud['sexe'],
            'nom' : etud['nom'],
            'prenom' : etud['prenom'],
            '_nom_target' : 'ficheEtud?etudid=' + etud['etudid'],
            '_prenom_target' : 'ficheEtud?etudid=' + etud['etudid'],
            '_nom_td_attrs' : 'id="%s" class="etudinfo"' % (etud['etudid']),
            'debouche' : etud['debouche'],
            'moy' : nt.get_etud_moy_gen(etudid),
            'rang' : nt.get_etud_rang(etudid),
            'effectif' : len(nt.T),
            'semestre_id' : last_sem['semestre_id'],
            'semestre' : last_sem['titre'],
            'date_debut': last_sem['date_debut'],
            'date_fin' : last_sem['date_fin'],
            'periode' : '%s - %s' % (last_sem['mois_debut'], last_sem['mois_fin'])
            } )

    titles = {
        'sexe' : '', 'nom' : 'Nom', 'prenom' : 'Prénom',
        'semestre' : 'Dernier semestre', 'semestre_id' : 'S',
        'periode' : 'Dates',
        'moy' : 'Moyenne', 'rang' :'Rang', 'effectif': 'Eff.', 'debouche' : 'Débouché'
        }
    tab = GenTable(
        columns_ids=('sexe', 'nom', 'prenom',
                     'semestre', 'semestre_id', 'periode', 'moy', 'rang', 'effectif', 'debouche'),
        titles=titles,
        rows=L,
        # lines_titles=lines_titles,
        # html_col_width='4em',
        html_sortable=True,
        html_class='gt_table table_leftalign table_listegroupe',
        preferences=context.get_preferences() )
    return tab


def report_debouche_ask_date(context, REQUEST=None):
    """Formulaire demande date départ
    """
    return (context.sco_header(REQUEST)
            + """<form method="GET">
            Date de départ de la recherche: <input type="text" name="start_year" value="" size=10/>
            </form>"""
            +  context.sco_footer(REQUEST))


