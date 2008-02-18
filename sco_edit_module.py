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

_MODULE_HELP = """<p class="help">
Les modules sont décrits dans le programme pédagogique. Un module est pour ce 
logiciel l'unité pédagogique élémentaire. On va lui associer une note 
à travers des <em>évaluations</em>. <br/>
Cette note (moyenne de module) sera utilisée pour calculer la moyenne
générale (et la moyenne de l'UE à laquelle appartient le module). Pour
cela, on utilisera le <em>coefficient</em> associé au module.
</p>

<p class="help">Un module possède un enseignant responsable
(typiquement celui qui dispense le cours magistral). On peut associer
au module une liste d'enseignants (typiquement les chargés de TD).
Tous ces enseignants, plus le responsable du semestre, pourront
saisir et modifier les notes de ce module.
</p> """ 


def module_create(context, matiere_id=None, REQUEST=None):
    """Creation d'un module
    """
    M = context.do_matiere_list( args={'matiere_id' : matiere_id} )[0]
    UE = context.do_ue_list( args={'ue_id' : M['ue_id']} )[0]
    H = [ context.sco_header(REQUEST, page_title="Création d'un module"),
          """<h2>Création d'un module dans la matière %(titre)s""" % M,
          """ (UE %(acronyme)s)</h2>""" % UE,
          _MODULE_HELP
          ]
    tf = TrivialFormulator(REQUEST.URL0, REQUEST.form, (
        ('code'    , { 'size' : 10, 'explanation' : 'code du module' }),
        ('titre'    , { 'size' : 30, 'explanation' : 'nom du module' }),
        ('abbrev'    , { 'size' : 20, 'explanation' : 'nom abrégé (pour bulletins)' }),

        ('heures_cours' , { 'size' : 4, 'type' : 'float', 'explanation' : 'nombre d\'heures de cours' }),
        ('heures_td'    , { 'size' : 4, 'type' : 'float', 'explanation' : 'nombre d\'heures de Travaux Dirigés' }),
        ('heures_tp'    , { 'size' : 4, 'type' : 'float', 'explanation' : 'nombre d\'heures de Travaux Pratiques' }),
        
        ('coefficient'  , { 'size' : 4, 'type' : 'float', 'explanation' : 'coefficient dans la formation (PPN)', 'allow_null' : False }),

        ('formation_id', { 'default' : UE['formation_id'], 'input_type' : 'hidden' }),
        ('ue_id', { 'default' : M['ue_id'], 'input_type' : 'hidden' }),
        ('matiere_id', { 'default' : M['matiere_id'], 'input_type' : 'hidden' }),
        
        ('semestre_id', { 'input_type' : 'menu', 'title' : 'Semestre', 
                          'explanation' : 'semestre de début du module dans la formation standard',
                          'labels' : ('1','2','3','4'), 'allowed_values' : ('1','2','3','4') }),
        ('numero',    { 'size' : 2, 'explanation' : 'numéro (1,2,3,4...) pour ordre d\'affichage',
                        'type' : 'int', 'default':10 }),
        ),
                           submitlabel = 'Créer ce module')
    if tf[0] == 0:
        return '\n'.join(H) + tf[1] + context.sco_footer(REQUEST)
    else:
        moduleid = context.do_module_create( tf[2], REQUEST )
        return REQUEST.RESPONSE.redirect( REQUEST.URL1 + '/ue_list?formation_id=' + UE['formation_id'])


def module_delete(context, module_id=None, REQUEST=None):
    """Delete a module"""
    Mod = context.do_module_list(args={ 'module_id' : module_id } )[0]
    H = [ context.sco_header(REQUEST, page_title="Suppression d'un module"),
          """<h2>Suppression du module %(titre)s (%(code)s)</h2>""" % Mod ]

    dest_url = REQUEST.URL1 + '/ue_list?formation_id=' + Mod['formation_id']
    tf = TrivialFormulator(REQUEST.URL0, REQUEST.form, (
        ('module_id', { 'input_type' : 'hidden' }),
        ),
                           initvalues = Mod,
                           submitlabel = 'Confirmer la suppression',
                           cancelbutton = 'Annuler')
    if tf[0] == 0:
        return '\n'.join(H) + tf[1] + context.sco_footer(REQUEST)
    elif tf[0] == -1:
        return REQUEST.RESPONSE.redirect(dest_url)
    else:
        context.do_module_delete( module_id, REQUEST )
        return REQUEST.RESPONSE.redirect(dest_url)

def module_edit(context, module_id=None, REQUEST=None):
    """Edit a module"""
    Mod= context.do_module_list( args={ 'module_id' : module_id } )[0]
    Fo = context.do_formation_list( args={ 'formation_id' : Mod['formation_id'] } )[0]
    M  = context.do_matiere_list( args={'ue_id' : Mod['ue_id']} )
    Mnames = [ x['titre'] for x in M ]
    Mids = [ x['matiere_id'] for x in M ]
    dest_url = REQUEST.URL1 + '/ue_list?formation_id=' + Mod['formation_id']

    H = [ context.sco_header(REQUEST, page_title="Modification du module %(titre)s" % Mod),
          """<h2>Modification du module %(titre)s""" % Mod,
          """ (formation %(acronyme)s, version %(version)s)</h2>""" % Fo,
          _MODULE_HELP ]
    tf = TrivialFormulator(REQUEST.URL0, REQUEST.form, (
        ('code'    , { 'size' : 10, 'explanation' : 'code du module' }),
        ('titre'    , { 'size' : 30, 'explanation' : 'nom du module' }),
        ('abbrev'    , { 'size' : 20, 'explanation' : 'nom abrégé (pour bulletins)' }),

        ('heures_cours' , { 'size' : 4, 'type' : 'float', 'explanation' : 'nombre d\'heures de cours' }),
        ('heures_td'    , { 'size' : 4, 'type' : 'float', 'explanation' : 'nombre d\'heures de Travaux Dirigés' }),
        ('heures_tp'    , { 'size' : 4, 'type' : 'float', 'explanation' : 'nombre d\'heures de Travaux Pratiques' }),
        
        ('coefficient'    , { 'size' : 4, 'type' : 'float', 'explanation' : 'coefficient dans la formation (PPN)', 'allow_null' : False }),
        
        ('formation_id', { 'input_type' : 'hidden' }),
        ('ue_id',        { 'input_type' : 'hidden' }),
        ('module_id',    { 'input_type' : 'hidden' }),
        
        ('matiere_id', { 'input_type' : 'menu', 'title' : 'Matière', 
                         'explanation' : 'un module appartient à une seule matière.',
                         'labels' : Mnames, 'allowed_values' : Mids }),

        ('semestre_id', { 'input_type' : 'menu', 'title' : 'Semestre', 'type' : 'int',
                          'explanation' : 'semestre de début du module dans la formation standard',
                          'labels' : ('1','2','3','4'), 'allowed_values' : (1,2,3,4) }),
        ('numero',    { 'size' : 2, 'explanation' : 'numéro (1,2,3,4...) pour ordre d\'affichage',
                        'type' : 'int' }),        
        ),
                           initvalues = Mod,
                           submitlabel = 'Modifier ce module')
    if tf[0] == 0:
        return '\n'.join(H) + tf[1] + context.sco_footer(REQUEST)
    elif tf[0] == -1:
        return REQUEST.RESPONSE.redirect(dest_url)
    else:
        context.do_module_edit(tf[2])
        return REQUEST.RESPONSE.redirect(dest_url)

def module_list(context, formation_id, REQUEST=None):
    """Liste des modules de la formation
    (XXX inutile ou a revoir)
    """
    F = context.do_formation_list( args={ 'formation_id' : formation_id } )[0]
    H = [ context.sco_header(REQUEST, page_title="Liste des modules de %(titre)s" % F),
          """<h2>Listes des modules dans la formation %(titre)s (%(acronyme)s)</h2>""" % F,
          '<ul class="notes_module_list">' ]
    editable = REQUEST.AUTHENTICATED_USER.has_permission(ScoChangeFormation,context)
    
    for Mod in context.do_module_list( args={ 'formation_id' : formation_id } ):
        H.append('<li class="notes_module_list">%s' % Mod )
        if editable:
            H.append('<a href="module_edit?module_id=%(module_id)s">modifier</a>' % Mod)
            H.append('<a href="module_delete?module_id=%(module_id)s">supprimer</a>' % Mod)
        H.append('</li>')
    H.append('</ul>')
    H.append(context.sco_footer(REQUEST))
    return '\n'.join(H)
