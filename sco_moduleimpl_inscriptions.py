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
import sco_groups

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
    H = [header, """<h2>Inscriptions au module <a href="moduleimpl_status?moduleimpl_id=%s">%s</a> (%s)</a></h2>
    <p class="help">Cette page permet d'éditer les étudiants inscrits à ce module
    (ils doivent évidemment être inscrits au semestre).
    Les étudiants cochés sont (ou seront) inscrits. Vous pouvez facilement inscrire ou
    désinscrire tous les étudiants d'un groupe à l'aide des menus "Ajouter" et "Enlever".
    </p>
    <p class="help">Aucune modification n'est prise en compte tant que l'on n'appuie pas sur le bouton
    "Appliquer les modifications".
    </p>
    """ % (moduleimpl_id, mod['titre'], mod['code'])]
    # Liste des inscrits à ce semestre
    inscrits = context.Notes.do_formsemestre_inscription_listinscrits(formsemestre_id)
    for ins in inscrits:
        etuds_info =  context.getEtudInfo(etudid=ins['etudid'], filled=1)
        if not etuds_info:
            log('moduleimpl_inscriptions_edit: incoherency for etudid=%s !'%ins['etudid'])
            raise ScoValueError("Etudiant %s inscrit mais inconnu dans la base !!!!!" %ins['etudid'])
        ins['etud'] = etuds_info[0]
    inscrits.sort( lambda x,y: cmp(x['etud']['nom'],y['etud']['nom']) )
    in_m = context.do_moduleimpl_inscription_list( args={ 'moduleimpl_id' : M['moduleimpl_id'] } )
    in_module= set( [ x['etudid'] for x in in_m ] )
    #
    partitions = sco_groups.get_partitions_list(context, formsemestre_id)
    #
    if not submitted:
        H.append("""<script type="text/javascript">
    function group_select(groupName, partitionIdx, check) {
    var nb_inputs_to_skip = 2; // nb d'input avant les checkbox !!!
    var elems = document.getElementById("mi_form").getElementsByTagName("input");

    for (var i =nb_inputs_to_skip; i < elems.length; i++) {
      var cells = elems[i].parentNode.parentNode.getElementsByTagName("td")[partitionIdx].childNodes;
      if (cells.length && cells[0].nodeValue == groupName) {
         elems[i].checked=check;
      }      
    }
    }
    </script>""")
        H.append("""<form method="post" id="mi_form" action="%s">"""%REQUEST.URL0)
        H.append("""        
        <input type="hidden" name="moduleimpl_id" value="%(moduleimpl_id)s"/>
        <input type="submit" name="submitted" value="Appliquer les modifications"/><p></p>
        """ % M )
        H.append(_make_menu(context, partitions, 'Ajouter', 'true'))
        H.append(_make_menu(context, partitions, 'Enlever', 'false'))        
        H.append("""<p><br/></p>
        <table class="sortable" id="mi_table"><tr>
        <th>Nom</th>""" % sem)
        for partition in partitions:
            if partition['partition_name']:
                H.append("<th>%s</th>" % partition['partition_name'])
        H.append('</tr>')

        for ins in inscrits:
            etud = ins['etud']
            if etud['etudid'] in in_module:
                checked = 'checked="checked"'
            else:
                checked = ''
            H.append("""<tr><td><input type="checkbox" name="etuds:list" value="%s" %s>"""
                             % (etud['etudid'], checked) )
            H.append("""<a class="discretelink" href="ficheEtud?etudid=%s">%s</a>""" % (
                        etud['etudid'], etud['nomprenom'] ))
            H.append("""</input></td>""")
            
            groups = sco_groups.get_etud_groups(context, etud['etudid'], sem)
            for partition in partitions:
                if partition['partition_name']:
                    gr_name = ''
                    for group in groups:
                        if group['partition_id'] == partition['partition_id']:
                            gr_name = group['group_name']
                            break
                    # gr_name == '' si etud non inscrit dans un groupe de cette partition
                    H.append('<td>%s</td>' % gr_name)
        H.append("""</table></form>""")
    else: # SUBMISSION
        # inscrit a ce module tous les etuds selectionnes 
        context.do_moduleimpl_inscrit_etuds(moduleimpl_id,formsemestre_id, etuds,
                                            reset=True,
                                            REQUEST=REQUEST)
        REQUEST.RESPONSE.redirect( "moduleimpl_status?moduleimpl_id=%s" %(moduleimpl_id))
    #
    H.append(footer)
    return '\n'.join(H)

def _make_menu(context, partitions, title='', check='true'):
    H = [ """<div class="barrenav"><ul class="nav">
    <li onmouseover="MenuDisplay(this)" onmouseout="MenuHide(this)"><a href="#" class="menu custommenu">%s</a><ul>""" % title
          ]
    
    p_idx = 0
    for partition in partitions:
        if partition['partition_name'] != None:
            p_idx += 1
            for group in sco_groups.get_partition_groups(context, partition):
                H.append("""<li><a href="#" onclick="group_select('%s', %s, %s)">%s %s</a></li>"""
                         % (group['group_name'], p_idx, check, partition['partition_name'], group['group_name'] ))
    
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
      tous sauf <liste d'au plus 7 noms>
      
    """
    sem = context.get_formsemestre(formsemestre_id)
    inscrits = context.do_formsemestre_inscription_list( args={ 'formsemestre_id' : formsemestre_id } )
    set_all = set( [ x['etudid'] for x in inscrits ] )
    partitions, partitions_etud_groups = sco_groups.get_formsemestre_groups(context, formsemestre_id)
    
    # Liste des modules
    Mlist = context.do_moduleimpl_withmodule_list( args={ 'formsemestre_id' : formsemestre_id } )
    # Decrit les inscriptions aux modules:
    commons = [] # modules communs a tous les etuds du semestre
    options = [] # modules ou seuls quelques etudiants sont inscrits
    for mod in Mlist:
        all, nb_inscrits, descr = descr_inscrs_module(context, sem, mod['moduleimpl_id'], set_all, partitions, partitions_etud_groups)
        if all:
            commons.append(mod)
        else:
            mod['descri'] = descr
            mod['nb_inscrits'] = nb_inscrits
            options.append(mod)
    # Page HTML:
    H = [context.html_sem_header(REQUEST, 'Inscriptions aux modules du semestre' )]
    
    H.append("""<p class="help">Cette page décrit les inscriptions actuelles. Vous pouvez changer (si vous en avez le droit) les inscrits dans chaque module via le lien "Gérer les inscriptions" dans le tableau de bord du module.</p>""")

    H.append('<h3>Inscrits au semestre: %d étudiants</h3>' % len(inscrits))

    if options:
        H.append('<h3>Modules auxquels tous les étudiants ne sont pas inscrits</h3>')
        H.append('<table class="formsemestre_status"><tr><th>UE</th><th>Code</th><th>Inscrits</th><th></th></tr>')
        for mod in options:
            H.append('<tr class="formsemestre_status"><td>%s</td><td class="formsemestre_status_code"><a href="moduleimpl_status?moduleimpl_id=%s">%s</a></td><td class="formsemestre_status_inscrits">%s</td><td>%s</td></tr>' % (mod['ue']['acronyme'], mod['moduleimpl_id'], mod['module']['code'], mod['nb_inscrits'], mod['descri']))
        H.append('</table>')
    else:
        H.append('<h3>Tous les étudiants sont inscrits à tous les modules</h3>')

    if commons:
        H.append('<h3>Modules communs (auxquels tous les étudiants sont inscrits)</h3>')
        H.append('<table class="formsemestre_status"><tr><th>UE</th><th>Code</th><th>Module</th></tr>')
        for mod in commons:
            H.append('<tr class="formsemestre_status_green"><td>%s</td><td class="formsemestre_status_code">%s</td><td>%s</td></tr>' % (mod['ue']['acronyme'], mod['module']['code'], mod['module']['titre']))
        H.append('</table>')

    # Etudiants "dispensés" d'une UE (capitalisée)
    UECaps = get_etuds_with_capitalized_ue(context, formsemestre_id)
    if UECaps:
        H.append('<h3>Etudiants avec UEs capitalisées</h3><ul>')        
        for ue_id in UECaps.keys():
            ue = context.do_ue_list({ 'ue_id' : ue_id })[0]
            H.append( '<li>%s: %s</li>' % (ue['acronyme'], _fmt_etud_set(context, UECaps[ue_id], max_list_size=50)))
        H.append('</ul>')
    
    H.append(context.sco_footer(REQUEST))
    return '\n'.join(H)

def descr_inscrs_module(context, sem, moduleimpl_id, set_all, partitions, partitions_etud_groups):
    """returns All, nb_inscrits, descr      All true si tous inscrits
    """
    ins = context.do_moduleimpl_inscription_list( args={ 'moduleimpl_id' : moduleimpl_id } )
    set_m = set( [ x['etudid'] for x in ins ] ) # ens. des inscrits au module
    non_inscrits = set_all - set_m
    if len(non_inscrits) == 0:
        return True, len(ins), '' # tous inscrits
    if len(non_inscrits) <= 7: # seuil arbitraire
        return False, len(ins), 'tous sauf ' + _fmt_etud_set(context,non_inscrits)
    # Cherche les groupes:
    gr = [] #  [ ( partition_name , [ group_names ] ) ]
    for partition in partitions:
        grp = [] # groupe de cette partition
        for group in sco_groups.get_partition_groups(context, partition):
            members = sco_groups.get_group_members(context, group['group_id'])
            set_g = set( [ m['etudid'] for m in members ] )
            if set_g.issubset(set_m):
                grp.append(group['group_name'])
                set_m = set_m - set_g
        gr.append( (partition['partition_name'], grp) )
    #
    d = []
    for (partition_name, grp) in gr:
        if grp:
            d.append( "groupes de %s: %s" % (partition_name, ', '.join(grp)) )
    r = []
    if d:
        r.append(', '.join(d))
    if set_m:
        r.append(_fmt_etud_set(context,set_m))
    #
    return False, len(ins), ' et '.join(r)

def _fmt_etud_set(context, ins, max_list_size=7):
    # max_list_size est l enombre max de noms d'etudiants listés
    # au delà, on indique juste le nombre, sans les noms.
    if len(ins) > max_list_size:
        return '%d étudiants' % len(ins)
    etuds = []
    for etudid in ins:
        etuds.append(context.getEtudInfo(etudid=etudid,filled=True)[0])
    etuds.sort( lambda x,y: cmp(x['nom'],y['nom']))
    return ', '.join( [ '<a class="discretelink" href="ficheEtud?etudid=%(etudid)s">%(nomprenom)s</a>' % etud for etud in etuds ] )


def get_etuds_with_capitalized_ue(context, formsemestre_id):
    """For each UE, computes list of students capitalizing the UE.
    returns { ue_id : set of etudid }
    """
    UECaps = DictDefault(defaultvalue=[])
    nt = context._getNotesCache().get_NotesTable(context, formsemestre_id)
    inscrits = context.do_formsemestre_inscription_list( args={ 'formsemestre_id' : formsemestre_id } )
    ues = nt.get_ues()
    for ue in ues:
        for etud in inscrits:
            status = nt.get_etud_ue_status(etud['etudid'], ue['ue_id'])
            if status['is_capitalized']:
                UECaps[ue['ue_id']].append(etud['etudid'])
    return UECaps

