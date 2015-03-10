# -*- mode: python -*-
# -*- coding: utf-8 -*-

##############################################################################
#
# Gestion scolarite IUT
#
# Copyright (c) 2001 - 2015 Emmanuel Viennet.  All rights reserved.
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

"""Rapports estimation coût de formation basé sur le programme pédagogique
   et les nombres de groupes.

   (coût théorique en heures équivalent TD)
"""
from notesdb import *
from sco_utils import *
from notes_log import log
from gen_tables import GenTable
import sco_excel, sco_pdf
from sco_pdf import SU
import sco_formsemestre_status
   
    
def formsemestre_table_estim_cost(context, formsemestre_id,
                                  n_group_td=1, n_group_tp=1,
                                  coef_tp=1, coef_cours=1.5,
                                  REQUEST=None):
    """
    Rapports estimation coût de formation basé sur le programme pédagogique
    et les nombres de groupes.
    Coût théorique en heures équivalent TD.
    Attention: ne prend en compte que les modules utilisés dans ce semestre.
    Attention: prend en compte _tous_ les modules utilisés dans ce semestre, ce qui
    peut conduire à une sur-estimation du coût s'il y a des modules optionnels
    (dans ce cas, retoucher le tableau excel exporté).
    """
    sem = context.get_formsemestre(formsemestre_id)
    sco_formsemestre_status.fill_formsemestre(context, sem, REQUEST=REQUEST)
    Mlist = context.do_moduleimpl_withmodule_list( args={ 'formsemestre_id' : formsemestre_id } )
    T = []
    for M in Mlist:
        Mod = M['module']
        T.append( {
            'code' : Mod['code'],
            'titre' :Mod['titre'],
            'heures_cours' : Mod['heures_cours'],
            'heures_td' : Mod['heures_td'] * n_group_td,
            'heures_tp' : Mod['heures_tp'] * n_group_tp,
            } )
    
    # calcul des heures:
    for t in T:
        t['HeqTD'] = t['heures_td'] + coef_cours*t['heures_cours'] + coef_tp*t['heures_tp']
    sum_cours = sum( [ t['heures_cours'] for t in T ] )
    sum_td = sum( [ t['heures_td'] for t in T ] )
    sum_tp = sum( [ t['heures_tp'] for t in T ] )
    sum_heqtd = sum_td + coef_cours*sum_cours + coef_tp*sum_tp
    assert abs(sum([ t['HeqTD'] for t in T ]) - sum_heqtd) < 0.01, '%s != %s' % (sum([ t['HeqTD'] for t in T ]), sum_heqtd)

    T.append( {
        'code' : 'TOTAL SEMESTRE',
        'heures_cours' : sum_cours,
        'heures_td' : sum_td,
        'heures_tp' : sum_tp,
        'HeqTD' : sum_heqtd
        })
    
    titles = {
        'code' : 'Code',
        'titre' : 'Titre',
        'heures_cours' : 'Cours',
        'heures_td' : 'TD',
        'heures_tp' : 'TP',
        'HeqTD' : 'HeqTD'
        }
    
    tab = GenTable( titles=titles,
                    columns_ids=('code', 'titre', 'heures_cours', 'heures_td', 'heures_tp', 'HeqTD'),
                    rows=T,
                    html_sortable=True,
                    preferences=context.get_preferences(formsemestre_id),
                    html_class='gt_table table_leftalign table_listegroupe',
                    xls_before_table = [
                        [ '%(titre)s %(num_sem)s %(modalitestr)s' % sem ],
                        [ 'Formation %(titre)s version %(version)s' % sem['formation'] ],
                        [],
                        [ '', 'TD', 'TP' ],
                        [ 'Nombre de groupes', n_group_td, n_group_tp ],
                        [],
                        []
                        ],
                    html_caption = """<div class="help">
                    Estimation du coût de formation basé sur le programme pédagogique
    et les nombres de groupes.<br/>
    Coût théorique en heures équivalent TD.<br/>
    Attention: ne prend en compte que les modules utilisés dans ce semestre.<br/>
    Attention: prend en compte <em>tous les modules</em> utilisés dans ce semestre, ce qui
    peut conduire à une sur-estimation du coût s'il y a des modules optionnels
    (dans ce cas, retoucher le tableau excel exporté).
    </div>
                    """,
                    origin = 'Généré par %s le ' % VERSION.SCONAME + timedate_human_repr() + '',
                    filename='EstimCout-S%s' % sem['semestre_id']
        )
    return tab


def formsemestre_estim_cost(context, formsemestre_id,
                            n_group_td=1, n_group_tp=1,
                            coef_tp=1, coef_cours=1.5,
                            format='html',
                            REQUEST=None):
    """Page (formulaire) estimation coûts"""

    n_group_td = int(n_group_td)
    n_group_tp = int(n_group_tp)
    coef_tp = float(coef_tp)
    coef_cours = float(coef_cours)
    
    tab = formsemestre_table_estim_cost(
        context, formsemestre_id, n_group_td=n_group_td, n_group_tp=n_group_tp,
        coef_tp=coef_tp, coef_cours=coef_cours,
        REQUEST=REQUEST)
    h = ("""
    <form name="f" method="get" action="%s">
    <input type="hidden" name="formsemestre_id" value="%s"></input>
    Nombre de groupes de TD: <input type="text" name="n_group_td" value="%s" onchange="document.f.submit()"/><br/>
    Nombre de groupes de TP: <input type="text" name="n_group_tp" value="%s" onchange="document.f.submit()"/>
    &nbsp;Coefficient heures TP: <input type="text" name="coef_tp" value="%s" onchange="document.f.submit()"/>
    <br/>
    </form>
    """
        % (REQUEST.URL0, formsemestre_id, n_group_td, n_group_tp, coef_tp)    
        )
    tab.html_before_table = h
    tab.base_url = '%s?formsemestre_id=%s&amp;n_group_td=%s&amp;n_group_tp=%s&amp;coef_tp=%s' % (
        REQUEST.URL0, formsemestre_id, n_group_td, n_group_tp, coef_tp)
    
    return tab.make_page(context, format=format, REQUEST=REQUEST)
