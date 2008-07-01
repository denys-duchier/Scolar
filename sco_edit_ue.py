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

"""Ajout/Modification/Supression UE
(portage from DTML)
"""
from notesdb import *
from sco_utils import *
from notes_log import log
from TrivialFormulator import TrivialFormulator, TF

def ue_create(context, formation_id=None, REQUEST=None):
    """Creation d'une UE
    """
    Fo = context.do_formation_list( args={ 'formation_id' : formation_id } )[0]
    H = [ context.sco_header(REQUEST, page_title="Création d'une UE"),
          """
          <h2>Ajout d'une UE dans la formation %(acronyme)s, version %(version)s</h2>

<p class="help">Les UE sont des groupes de modules dans une formation donnée, utilisés pour l'évaluation (on calcule des moyennes par UE et applique des seuils ("barres")). 
</p>

<p class="help">Note: L'UE n'a pas de coefficient associé. Seuls les <em>modules</em> ont des coefficients.
</p>"""
          % Fo ]
    
    tf = TrivialFormulator(REQUEST.URL0, REQUEST.form, ( 
        ('titre'    , { 'size' : 30, 'explanation' : 'nom de l\'UE' }),
        ('acronyme' , { 'size' : 8, 'explanation' : 'abbréviation', 'allow_null' : False }),
        ('numero',    { 'size' : 2, 'explanation' : 'numéro (1,2,3,4) de l\'UE pour l\'ordre d\'affichage',
                        'type' : 'int' }),
        ('type', { 'explanation': 'type d\'UE (normal, sport&culture)',
                   'input_type' : 'menu',
                   'allowed_values': ('0','1'),
                   'labels' : ('Normal', 'Sport&Culture (règle de calcul IUT)')}),
        ('formation_id', { 'input_type' : 'hidden', 'default' : formation_id }),
        ), submitlabel = 'Créer cette UE')
    
    if tf[0] == 0:
        return '\n'.join(H) + tf[1] + context.sco_footer(REQUEST)
    else:
        ue_id = context.do_ue_create(tf[2],REQUEST)
        return REQUEST.RESPONSE.redirect( REQUEST.URL1 + '/ue_list?formation_id=' + str(formation_id))


def ue_edit(context, ue_id=None, REQUEST=None):
    """Modification d'une UE
    """
    U = context.do_ue_list( args={ 'ue_id' : ue_id } )[0]
    Fo = context.do_formation_list( args={ 'formation_id' : U['formation_id'] } )[0]
    H = [ context.sco_header(REQUEST, page_title="Modification d'une UE"),          
          "<h2>Modification de l'UE %(titre)s" % U,
          '(formation %(acronyme)s, version %(version)s)</h2>' % Fo,
          """
<p class="help">Les UE sont des groupes de modules dans une formation donnée, utilisés pour l'évaluation (on calcule des moyennes par UE et applique des seuils ("barres")). 
</p>

<p class="help">Note: L'UE n'a pas de coefficient associé. Seuls les <em>modules</em> ont des coefficients.
</p>""" ]
    
    tf = TrivialFormulator(REQUEST.URL0, REQUEST.form, (
         ('ue_id', { 'input_type' : 'hidden' }),
         ('titre'    , { 'size' : 30, 'explanation' : 'nom de l\'UE' }),
         ('acronyme' , { 'size' : 8, 'explanation' : 'abbréviation', 'allow_null' : False }),
         ('numero',    { 'size' : 2, 'explanation' : 'numéro (1,2,3,4) de l\'UE pour l\'ordre d\'affichage',
                         'type' : 'int' }),
         ('type', { 'explanation': 'type d\'UE (normal, sport&culture)',
                    'input_type' : 'menu',
                    'allowed_values': ('0','1'),
                    'labels' : ('Normal', 'Sport&Culture (règle de calcul IUT)')}),
         ('ue_code', { 'size' : 12, 'title' : 'Code UE', 'explanation' : 'code interne. Toutes les UE partageant le même code (et le même code de formation) sont compatibles (compensation de semestres, capitalisation d\'UE).' }),
         ),
                            initvalues = U,
                            submitlabel = 'Modifier les valeurs' )
    if tf[0] == 0:
        return '\n'.join(H) + tf[1] + context.sco_footer(REQUEST)
    else:
        ue_id = context.do_ue_edit(tf[2])
        return REQUEST.RESPONSE.redirect( REQUEST.URL1 + '/ue_list?formation_id=' + str(U['formation_id']))


def ue_delete(context, ue_id=None, REQUEST=None):
    """Delete an UE"""
    F = context.do_ue_list( args={ 'ue_id' : ue_id } )[0]
    H = [ context.sco_header(REQUEST, page_title="Suppression d'une UE"),
          "<h2>Suppression de l'UE %(titre)s (%(acronyme)s))</h2>" % F ]
    tf = TrivialFormulator( REQUEST.URL0, REQUEST.form, (
        ('ue_id', { 'input_type' : 'hidden' }),
        ),
                            initvalues = F,
                            submitlabel = 'Confirmer la suppression',
                            cancelbutton = 'Annuler'
                            )
    if tf[0] == 0:
        return '\n'.join(H) + tf[1] + context.sco_footer(REQUEST)
    elif tf[0] == -1:
        return REQUEST.RESPONSE.redirect( REQUEST.URL1 )
    else:
        context.do_ue_delete( ue_id, REQUEST )
        return REQUEST.RESPONSE.redirect( REQUEST.URL1 + '/ue_list?formation_id=' + str(F['formation_id']))


def ue_list(context, formation_id=None, msg='', REQUEST=None):
    """Liste des matières (dans une formation)
    """
    authuser = REQUEST.AUTHENTICATED_USER

    F = context.do_formation_list( args={ 'formation_id' : formation_id } )[0]
    locked = context.formation_has_locked_sems(formation_id)

    perm_change = authuser.has_permission(ScoChangeFormation,context)
    editable = (not locked) and perm_change

    if locked:
        lockicon = context.icons.lock32_img.tag(title="verrouillé", border='0')
    else:
        lockicon = ''
    H = [ context.sco_header(REQUEST, page_title="Programme %s" % F['acronyme']),
          """<h2>Formation %(titre)s (%(acronyme)s) [version %(version)s] code %(formation_code)s""" % F,
          lockicon, '</h2>' ]
    if locked:
        H.append( """<p class="help">Cette formation est verrouillée car %d semestres verrouillés s'y réferent.
Si vous souhaitez modifier cette formation (par exemple pour y ajouter un module), vous devez:
</p>
<ul class="help">
<li>soit créer une nouvelle version de cette formation pour pouvoir l'éditer librement;</li>
<li>soit déverrouiler le ou les semestres qui s'y réfèrent (attention, en principe ces semestres sont archivés 
    et ne devraient pas être modifiés).</li>
</ul>""" % len(locked))
    if msg:
        H.append('<p class="msg">' + msg + '</p>' )

    H.append('<ul class="notes_ue_list">')
    ue_list = context.do_ue_list( args={ 'formation_id' : formation_id } )
    for UE in ue_list:
        H.append('<li class="notes_ue_list">%(acronyme)s %(titre)s (code %(ue_code)s)' % UE)
        if editable:
            H.append('<a class="stdlink" href="ue_edit?ue_id=%(ue_id)s">modifier</a>' % UE)
        H.append('<ul class="notes_matiere_list">')
        Matlist = context.do_matiere_list( args={ 'ue_id' : UE['ue_id'] } )
        for Mat in Matlist:
            H.append('<li class="notes_matiere_list">%(titre)s' % Mat)
            if editable:
                H.append('<a class="stdlink" href="matiere_edit?matiere_id=%(matiere_id)s">modifier</a>' % Mat)
            H.append('<ul class="notes_module_list">')
            Modlist = context.do_module_list( args={ 'matiere_id' : Mat['matiere_id'] } )
            for Mod in Modlist:
                Mod['nb_moduleimpls'] = context.module_count_moduleimpls(Mod['module_id'])
                H.append('<li class="notes_module_list">')
                if editable:
                    H.append('<a class="discretelink" title="Modifier le module numéro %(numero)s, utilisé par %(nb_moduleimpls)d semestres" href="module_edit?module_id=%(module_id)s">' % Mod)
                H.append('%(code)s %(titre)s (semestre %(semestre_id)s) (%(heures_cours)s/%(heures_td)s/%(heures_tp)s, coef. %(coefficient)s)' % Mod)
                if editable:
                    H.append('</a>')
                    if Mod['nb_moduleimpls'] == 0:
                        H.append(' <a class="discretelink" href="module_delete?module_id=%(module_id)s">supprimer ce module</a> (inutilisé)' % Mod)
                
                H.append('</li>')
            if not Modlist:
                H.append('<li>Aucun module dans cette matière !')
                if editable:
                    H.append('<a class="stdlink" href="matiere_delete?matiere_id=%(matiere_id)s">supprimer cette matière</a>' % Mat)
                H.append('</li>')
            if editable:
                H.append('<li> <a class="stdlink" href="module_create?matiere_id=%(matiere_id)s">créer un module</a></li>' % Mat)            
            H.append('</ul>')
            H.append('</li>')
        if not Matlist:
            H.append('<li>Aucune matière dans cette UE ! ')
            if editable:
                H.append("""<a class="stdlink" href="ue_delete?ue_id=%(ue_id)s">supprimer l'UE</a>""" % UE)
            H.append('</li>')
        if editable:
            H.append('<li><a class="stdlink" href="matiere_create?ue_id=%(ue_id)s">créer une matière</a> </li>' % UE)
        H.append('</ul>')
    if editable:
        H.append('<a class="stdlink" href="ue_create?formation_id=%s">Ajouter une UE</a></li>' % formation_id)
    H.append('</ul>')

    H.append("""    
<p>
<ul>
<li><a class="stdlink" href="formation_create_new_version?formation_id=%(formation_id)s">Créer une nouvelle version (non verrouillée)</a></li>
<li><a class="stdlink" href="module_list?formation_id=%(formation_id)s">Liste détaillée des modules de la formation</a> (debug) </li>
<li><a class="stdlink" href="formation_export_xml?formation_id=%(formation_id)s">Export XML de la formation</a> (permet de la sauvegarder pour l'échanger avec un autre site)</li>
</ul>
</p>""" % F )
    if perm_change:
        H.append("""
        <h3>Semestres ou sessions de cette formation</h3>
        <p><ul>""")
        for sem in context.do_formsemestre_list(args={ 'formation_id' : formation_id } ):
            H.append('<li><a class="stdlink" href="formsemestre_editwithmodules?formation_id=%(formation_id)s&formsemestre_id=%(formsemestre_id)s">Modifier le semestre %(titreannee)s</a></li>' % sem)
        H.append('</ul>')
    
    if authuser.has_permission(ScoImplement,context):
        H.append("""<ul>
        <li><a class="stdlink" href="formsemestre_createwithmodules?formation_id=%(formation_id)s&semestre_id=1">Mettre en place un nouveau semestre de formation %(acronyme)s</a>
 </li>

  <li>(debug) <a class="stdlink" href="check_form_integrity?formation_id=%(formation_id)s">Vérifier cohérence</a></li>

</ul>""" % F)

    H.append(context.sco_footer(REQUEST))
    return '\n'.join(H)
