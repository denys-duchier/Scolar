# -*- mode: python -*-
# -*- coding: utf-8 -*-

##############################################################################
#
# Gestion scolarite IUT
#
# Copyright (c) 2001 - 2014 Emmanuel Viennet.  All rights reserved.
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

"""Recherche d'étudiants
"""

from sco_utils import *
import xml.dom.minidom

from notesdb import *
from notes_log import log
from gen_tables import GenTable

import scolars
import sco_groups

def form_search_etud(context, REQUEST=None, 
    dest_url=None, 
    parameters=None, parameters_keys=None, 
    title='Rechercher un &eacute;tudiant par nom&nbsp;: ', 
    add_headers = False, # complete page
    ):
    "form recherche par nom"
    H = []
    if title:
        H.append('<h2>%s</h2>'%title)
    H.append( """<form action="search_etud_in_dept" method="POST">
    <b>%s</b>
    <input type="text" name="expnom" width=12 value="">
    <input type="submit" value="Chercher">
    <br/>(entrer une partie du nom)
    """ % title)
    if dest_url:
        H.append('<input type="hidden" name="dest_url" value="%s"/>' % dest_url)
    if parameters:
        for param in parameters.keys():
            H.append('<input type="hidden" name="%s" value="%s"/>'
                     % (param, parameters[param]))
        H.append('<input type="hidden" name="parameters_keys" value="%s"/>'%(','.join(parameters.keys())))
    elif parameters_keys:
        for key in parameters_keys.split(','):
            v = REQUEST.form.get(key,False)
            if v:
                H.append('<input type="hidden" name="%s" value="%s"/>'%(key,v))
        H.append('<input type="hidden" name="parameters_keys" value="%s"/>'%parameters_keys)
    H.append('</form>')

    if add_headers:
        return context.sco_header(REQUEST, page_title='Choix d\'un étudiant') + '\n'.join(H) + context.sco_footer(REQUEST)
    else:
        return '\n'.join(H)

# was chercheEtud()
def search_etud_in_dept(context, 
    expnom = None,
    dest_url = 'ficheEtud',
    parameters = {},
    parameters_keys = '',
    add_headers = True, # complete page
    title = None,
    REQUEST = None
    ):
    """Page recherche d'un etudiant
    expnom est un regexp sur le nom
    dest_url est la page sur laquelle on sera redirigé après choix
    parameters spécifie des arguments additionnels à passer à l'URL (en plus de etudid)
    """
    if type(expnom) == ListType:
        expnom = expnom[0]
    q = []
    if parameters:
        for param in parameters.keys():
            q.append( '%s=%s' % (param, parameters[param]))
    elif parameters_keys:
        for key in parameters_keys.split(','):
            v = REQUEST.form.get(key,False)
            if v:
                q.append( '%s=%s' % (key,v) )
    query_string = '&amp;'.join(q)

    no_side_bar = True
    H = []
    if title:
        H.append('<h2>%s</h2>'%title)
    if expnom:
        etuds = search_etuds_infos(context, expnom=expnom,REQUEST=REQUEST)
    else:
        etuds = []
    if len(etuds) == 1:
        # va directement a la destination
        return REQUEST.RESPONSE.redirect( dest_url + '?etudid=%s&amp;' % etuds[0]['etudid'] + query_string )

    if len(etuds) > 0:
        # Choix dans la liste des résultats:
        H.append("""<h2>%d résultats pour "%s": choisissez un étudiant:</h2>""" % (len(etuds),expnom))
        H.append(form_search_etud(context, dest_url=dest_url,
                                  parameters=parameters, parameters_keys=parameters_keys, 
                                  REQUEST=REQUEST, title="Autre recherche"))
        
        for e in etuds:
            target = dest_url + '?etudid=%s&amp;' % e['etudid'] + query_string
            e['_nomprenom_target'] = target
            e['inscription_target'] = target
            e['_nomprenom_td_attrs'] = 'id="%s" class="etudinfo"' % (e['etudid'])
            sco_groups.etud_add_group_infos(context, e, e['cursem'])

        tab = GenTable( columns_ids=('nomprenom', 'inscription', 'groupes'),
                        titles={ 'nomprenom' : 'Etudiant',
                                 'inscription' : 'Inscription', 
                                 'groupes' : 'Groupes' },
                        rows = etuds,
                        html_sortable=True,
                        html_class='gt_table table_leftalign',
                        preferences=context.get_preferences())
        H.append(tab.html())            
        if len(etuds) > 20: # si la page est grande
            H.append(form_search_etud(context, dest_url=dest_url,
                                      parameters=parameters, parameters_keys=parameters_keys, 
                                      REQUEST=REQUEST, title="Autre recherche"))

    else:
        H.append('<h2 style="color: red;">Aucun résultat pour "%s".</h2>' % expnom )
        add_headers = True
        no_side_bar = False
    H.append("""<p class="help">La recherche porte sur tout ou partie du NOM de l'étudiant</p>""")
    if add_headers:
        return context.sco_header(REQUEST, page_title='Choix d\'un étudiant', 
                               init_qtip = True,
                               javascripts=['js/etud_info.js'],
                               no_side_bar=no_side_bar
                               ) + '\n'.join(H) + context.sco_footer(REQUEST)
    else:
        return '\n'.join(H)

# Was chercheEtudsInfo()
def search_etuds_infos(context, expnom, REQUEST):
    """recherche les étudiants correspondants à expnom
    et ramene liste de mappings utilisables en DTML.        
    """
    cnx = context.GetDBConnexion()
    expnom = strupper(expnom) # les noms dans la BD sont en uppercase
    etuds = scolars.etudident_list(cnx, args={'nom':expnom}, test='~' )        
    context.fillEtudsInfo(etuds)
    return etuds

# ---------- Recherche sur plusieurs département

def form_search_etud_in_accessible_depts(context, REQUEST):
    """Form recherche etudiants pour page accueil ScoDoc
    """
    authuser = REQUEST.AUTHENTICATED_USER
    # present form only to authenticated users
    if not authuser.has_role('Authenticated'):
        return ''
    return """<form action="table_etud_in_accessible_depts" method="POST">
    <b>Chercher étudiant:</b>
    <input type="text" name="expnom" width=12 value="">
    <input type="submit" value="Chercher">
    <br/>(entrer une partie du nom, cherche dans tous les départements autorisés)
    """

def can_view_dept(context, REQUEST):
    """True if auth user can access (View) this context"""
    authuser = REQUEST.AUTHENTICATED_USER
    return authuser.has_permission(ScoView,context)

def search_etud_in_accessible_depts(context, expnom = None, REQUEST = None):
    """
    context est le ZScoDoc
    result is a list of (sorted) etuds, one list per dept.
    """
    result = []
    accessible_depts = []
    deptList = context.list_depts() # definis dans Zope
    for dept in deptList:
        #log('%s searching %s' % (str(REQUEST.AUTHENTICATED_USER),dept))
        if can_view_dept(dept, REQUEST):
            if expnom:
                accessible_depts.append(dept.Scolarite.DeptId())
                etuds = search_etuds_infos(dept.Scolarite, expnom=expnom, REQUEST=REQUEST)
            else:
                etuds = []
            result.append(etuds)
    return result, accessible_depts

def table_etud_in_accessible_depts(context, expnom = None, REQUEST = None):
    """
    Page avec table étudiants trouvés, dans tous les departements.
    Attention: nous sommes ici au niveau de ScoDoc, pas dans un département
    """
    result, accessible_depts = search_etud_in_accessible_depts(context, expnom, REQUEST)
    H = [ """<div class="table_etud_in_accessible_depts">""",
          """<h3>Recherche multi-département de "<tt>%s</tt>"</h3>""" % expnom 
          ]
    for etuds in result:
        if etuds:
            DeptId = etuds[0]['dept']            
            #H.append('<h3>Département %s</h3>' % DeptId)
            dest_url = DeptId + '/Scolarite/ficheEtud'
            for e in etuds:
                target = dest_url + '?etudid=%s' % e['etudid']
                e['_nomprenom_target'] = target
                e['_nomprenom_td_attrs'] = 'id="%s" class="etudinfo"' % (e['etudid'])
            
            tab = GenTable( 
                titles={
                    'nomprenom' : 'Etudiants en ' + DeptId,
                    },
                columns_ids=('nomprenom', ),
                rows = etuds,
                html_sortable=True,
                html_class='gt_table table_leftalign'
                )

            H.append('<div class="table_etud_in_dept">')
            H.append(tab.html())
            H.append('</div>')
    if len(accessible_depts)>1:
        ss = 's'
    else:
        ss=''
    H.append("""<p>(recherche menée dans le%s département%s: %s)</p><p>
    <a href=".." class="stdlink">Retour à l'accueil</a></p>""" % (ss, ss, ', '.join(accessible_depts)))
    H.append('</div>')
            
    return context.scodoc_top_html_header(REQUEST, page_title='Choix d\'un étudiant') + '\n'.join(H) + context.standard_html_footer(REQUEST)
