# -*- mode: python -*-
# -*- coding: iso8859-15 -*-

##############################################################################
#
# Gestion scolarite IUT
#
# Copyright (c) 2001 - 2007 Emmanuel Viennet.  All rights reserved.
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

"""Opérations d'inscriptions aux modules (interface pour gérer options ou parcours)
"""


from notesdb import *
from sco_utils import *
from notes_log import log
from notes_table import *
from ScolarRolesNames import *
from sco_exceptions import *
from sets import Set

def moduleimpl_inscriptions_edit(context, moduleimpl_id, etuds=None,
                                 submitted=False, REQUEST=None):
    """Formulaire inscription des etudiants a ce module
    * Gestion des inscriptions
         Nom          TD     TA    TP  (triable)
     [x] M. XXX YYY   -      -     -
     
     
     ajouter TD A, TD B, TP 1, TP 2 ...
     supprimer TD A, TD B, TP 1, TP 2 ...
     
     * Si pas les droits: idem en readonly
    """
    M = context.do_moduleimpl_list( args={ 'moduleimpl_id':moduleimpl_id } )[0]
    formsemestre_id = M['formsemestre_id']
    mod = context.do_module_list( args={ 'module_id':M['module_id'] } )[0]
    sem = context.get_formsemestre(formsemestre_id)
    # -- check lock
    if sem['etat'] != '1':
        raise ScoValueError('opération impossible: semestre verrouille')
    header = context.sco_header(REQUEST, page_title='Inscription au module')
    footer = context.sco_footer(REQUEST)
    H = [header, """<h2>Inscriptions au module <a href="moduleimpl_status?moduleimpl_id=%s">%s</a> (%s) du semestre <a href="formsemestre_status?formsemestre_id=%s">%s</a></h2>
    <p class="help">Cette page permet d'éditer les étudiants inscrits à ce module
    (ils doivent évidemment être inscrits au semestre).
    Les étudiants cochés sont (ou seront) inscrits. Vous pouvez facilement inscrire ou
    désinscrire tous les étudiants d'un groupe à l'aide des menus "Ajouter" et "Enlever".
    </p>
    <p class="help">Aucune modification n'est prise en compte tant que l'on n'appuie pas sur le bouton
    "Appliquer les modifications".
    </p>
    """ % (moduleimpl_id, mod['titre'], mod['code'], formsemestre_id, sem['titreannee'])]
    # Liste des inscrits à ce semestre
    inscrits = context.Notes.do_formsemestre_inscription_list(
        args={  'formsemestre_id' : formsemestre_id, 'etat' : 'I' } )
    in_m = context.do_moduleimpl_inscription_list( args={ 'moduleimpl_id' : M['moduleimpl_id'] } )
    in_module= Set( [ x['etudid'] for x in in_m ] )
    log('in_module=%s' % in_module)
    #
    if not submitted:
        H.append("""<script type="text/javascript">
    function group_select(groupName, groupIdx, check) {
    var nb_inputs_to_skip = 2; // nb d'input avant les checkbox !!!
    var elems = document.getElementById("mi_form").getElementsByTagName("input");

    for (var i =nb_inputs_to_skip; i < elems.length; i++) {
      var cells = elems[i].parentNode.parentNode.getElementsByTagName("td")[groupIdx].childNodes;
      if (cells.length && cells[0].nodeValue == groupName) {
         elems[i].checked=check;
      }      
    }
    }
    </script>""")
        H.append("""
        <form method="post" id="mi_form">
        <input type="hidden" name="moduleimpl_id" value="%(moduleimpl_id)s"/>
        <input type="submit" name="submitted" value="Appliquer les modifications"/>
        """ % M )
        H.append(_make_menu(context, sem, 'Ajouter', 'true'))
        H.append(_make_menu(context, sem, 'Enlever', 'false'))
        H.append("""
        <table class="sortable" id="mi_table"><tr>
        <th>Nom</th>
        <th>%(nomgroupetd)s</th><th>%(nomgroupeta)s</th><th>%(nomgroupetp)s</th></tr>""" % sem )

        for ins in inscrits:
            etud = context.getEtudInfo(etudid=ins['etudid'],filled=1)[0]
            if etud['etudid'] in in_module:
                checked = 'checked="checked"'
            else:
                checked = ''
            H.append("""<tr><td><input type="checkbox" name="etuds" value="%s" %s>"""
                             % (etud['etudid'], checked) )
            H.append("""<a class="discretelink" href="ficheEtud?etudid=%s">%s</a>""" % (
                        etud['etudid'], etud['nomprenom'] ))
            H.append("""</input></td>""")
            H.append("""<td>%(groupetd)s</td><td>%(groupeanglais)s</td><td>%(groupetp)s</td></tr>"""
                     % ins )        
        H.append("""</table></form>""")
    else: # SUBMISSION
        # inscrit a ce module tous les etuds selectionnes 
        context.do_moduleimpl_inscrit_etuds(moduleimpl_id,formsemestre_id, etuds,
                                            REQUEST=REQUEST)
        REQUEST.RESPONSE.redirect( "formsemestre_status?formsemestre_id=%s" %(formsemestre_id))
    #
    H.append(footer)
    return '\n'.join(H)

def _make_menu(context, sem, title='', check='true'):
    H = [ """<div class="barrenav"><ul class="nav">
    <li onmouseover="MenuDisplay(this)" onmouseout="MenuHide(this)"><a href="#" class="menu custommenu">%s</a><ul>""" % title
          ]

    gr_td,gr_tp,gr_anglais = context.Notes.do_formsemestre_inscription_listegroupes(formsemestre_id=sem['formsemestre_id'])
    for (groupeTypeName, idx, groupNames) in (('groupetd', 1, gr_td),
                                              ('groupeta', 2, gr_anglais),
                                              ('groupetp', 3, gr_tp)):
        for groupName in groupNames:
            H.append("""<li><a href="#" onclick="group_select('%s', %s, %s)">%s %s</a></li>"""
                     % (groupName, idx, check, sem['nom'+groupeTypeName], groupName))

    H.append('</ul></ul></div>')
    
    return ''.join(H)
