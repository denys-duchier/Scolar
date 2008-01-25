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

"""Opérations d'inscriptions aux modules (interface pour gérer options ou parcours)
"""


from notesdb import *
from sco_utils import *
from notes_log import log
from notes_table import *
from ScolarRolesNames import *
from sco_exceptions import *
from sets import Set

def moduleimpl_inscriptions_edit(context, moduleimpl_id, etuds=[],
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
        <input type="submit" name="submitted" value="Appliquer les modifications"/><p></p>
        """ % M )
        H.append(_make_menu(context, sem, 'Ajouter', 'true'))
        H.append(_make_menu(context, sem, 'Enlever', 'false'))        
        H.append("""<p><br/></p>
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
                                            reset=True,
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


def moduleimpl_inscriptions_stats(context, formsemestre_id, REQUEST=None):
    """Affiche quelques informations sur les inscriptions
    aux modules de ce semestre.

    Inscrits au semestre: <nb>

    Modules communs (tous inscrits): <liste des modules (codes)

    Autres modules: (regroupés par UE)
    UE 1
    <code du module>: <nb inscrits> (<description en termes de groupes>)
    ...


    descriptions:
      groupes de TD A, B et C
      tous sauf groupe de TP Z (?)
      tous sauf <liste des noms de  moins de 10% de la promo>
      
    """
    sem = context.get_formsemestre(formsemestre_id)
    inscrits = context.do_formsemestre_inscription_list( args={ 'formsemestre_id' : formsemestre_id } )
    set_all = Set( [ x['etudid'] for x in inscrits ] )
    sets_td, sets_ta, sets_tp = _get_groups_sets(inscrits)
    # Liste des modules
    Mlist = context.do_moduleimpl_withmodule_list( args={ 'formsemestre_id' : formsemestre_id } )
    # Decrit les inscriptions aux modules:
    commons = [] # modules communs a tous les etuds du semestre
    options = [] # modules ou seuls quelques etudiants sont inscrits
    for mod in Mlist:
        all, nb_inscrits, descr = descr_inscrs_module(context, sem, mod['moduleimpl_id'], set_all, sets_td, sets_ta, sets_tp)
        if all:
            commons.append(mod)
        else:
            mod['descri'] = descr
            mod['nb_inscrits'] = nb_inscrits
            options.append(mod)
    # Page HTML:
    H = [context.sco_header(REQUEST, page_title='Inscriptions aux modules' )]
    H.append("""<h2>Inscriptions aux modules du semestre <a href="formsemestre_status?formsemestre_id=%s">%s</a></h2>""" % (formsemestre_id, sem['titreannee']))

    H.append("""<p class="help">Cette page décrit les inscriptions actuelles. Vous pouvez changer (si vous en avez le droit) les inscrits dans chaque module via le lien "Gérer les inscriptions" dans le tableau de bord du module.</p>""")

    H.append('<h3>Inscrits au semestre: %d étudiants</h3>' % len(inscrits))

    if options:
        H.append('<h3>Modules où tous les étudiants ne sont pas inscrits</h3>')
        H.append('<table class="formsemestre_status"><tr><th>UE</th><th>Code</th><th>Inscrits</th><th></th></tr>')
        for mod in options:
            H.append('<tr class="formsemestre_status"><td>%s</td><td class="formsemestre_status_code"><a href="moduleimpl_status?moduleimpl_id=%s">%s</a></td><td class="formsemestre_status_inscrits">%s</td><td>%s</td></tr>' % (mod['ue']['acronyme'], mod['moduleimpl_id'], mod['module']['code'], mod['nb_inscrits'], mod['descri']))
        H.append('</table>')
    else:
        H.append('<h3>Tous les étudiants sont inscrits à tous les modules</h3>')

    if commons:
        H.append('<h3>Modules communs (où tous les étudiants sont inscrits)</h3>')
        H.append('<table class="formsemestre_status"><tr><th>UE</th><th>Code</th><th>Module</th></tr>')
        for mod in commons:
            H.append('<tr class="formsemestre_status_green"><td>%s</td><td class="formsemestre_status_code">%s</td><td>%s</td></tr>' % (mod['ue']['acronyme'], mod['module']['code'], mod['module']['titre']))
        H.append('</table>')

    H.append(context.sco_footer(REQUEST))
    return '\n'.join(H)


def _get_groups_sets(inscrits):
    """inscrits: liste d'inscriptions au semestre
    construit 3 dicts { groupe : set of etudids }
    """
    sets_td, sets_ta, sets_tp = {}, {}, {}
    for ins in inscrits:
        gr = ins['groupetd']
        if gr:
            if sets_td.has_key(gr):
                sets_td[gr].add(ins['etudid'])
            else:
                sets_td[gr] = Set([ins['etudid']])
        gr = ins['groupeanglais']
        if gr:
            if sets_ta.has_key(gr):
                sets_ta[gr].add(ins['etudid'])
            else:
                sets_ta[gr] = Set([ins['etudid']])
        gr = ins['groupetp']
        if gr:
            if sets_tp.has_key(gr):
                sets_tp[gr].add(ins['etudid'])
            else:
                sets_tp[gr] = Set([ins['etudid']])
    
    return sets_td, sets_ta, sets_tp

def descr_inscrs_module(context, sem, moduleimpl_id, set_all, sets_td, sets_ta, sets_tp):
    """returns All, nb_inscrits, descr      All true si tous inscrits
    """
    ins = context.do_moduleimpl_inscription_list( args={ 'moduleimpl_id' : moduleimpl_id } )
    set_m = Set( [ x['etudid'] for x in ins ] )
    non_inscrits = set_all - set_m
    if len(non_inscrits) == 0:
        return True, len(ins), '' # tous inscrits
    if len(non_inscrits) < (len(set_all)/10): # seuil arbitraire
        return False, len(ins), 'tous sauf ' + _fmt_etud_set(context,non_inscrits)
    # Cherche les groupes de TD:
    if sem['nomgroupetd']:
        gr_td = []
        for (gr, set_g) in sets_td.items():
            if set_g.issubset(set_m):
                gr_td.append(gr)
                set_m = set_m - set_g
    # TA
    gr_ta = []
    if sem['nomgroupeta']:
        for (gr, set_g) in sets_ta.items():
            if set_g.issubset(set_m):
                gr_ta.append(gr)
                set_m = set_m - set_g
    # TP
    gr_tp = []
    if sem['nomgroupetp']:
        for (gr, set_g) in sets_tp.items():
            if set_g.issubset(set_m):
                gr_tp.append(gr)
                set_m = set_m - set_g
    #
    d = []
    if gr_td:
        d.append( "groupes de %s: %s" % (sem['nomgroupetd'], ', '.join(gr_td)) )
    if gr_ta:
        d.append( "groupes de %s: %s" % (sem['nomgroupeta'], ', '.join(gr_ta)) )
    if gr_tp:
        d.append( "groupes de %s: %s" % (sem['nomgroupetp'], ', '.join(gr_tp)) )    
    r = []
    if d:
        r.append(', '.join(d))
    if set_m:
        r.append(_fmt_etud_set(context,set_m))
    #
    return False, len(ins), ' et '.join(r)

def _fmt_etud_set(context, ins):
    if len(ins) > 7: # seuil arbitraire
        return '%d etudiants' % len(ins)
    etuds = []
    for etudid in ins:
        etuds.append(context.getEtudInfo(etudid=etudid,filled=True)[0])
    etuds.sort( lambda x,y: cmp(x['nom'],y['nom']))
    return ', '.join( [ '<a class="discretelink" href="ficheEtud?etudid=%(etudid)s">%(nomprenom)ss</a>' % etud for etud in etuds ] )
