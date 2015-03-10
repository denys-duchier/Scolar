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

"""Ajout/Modification/Supression UE
(portage from DTML)
"""
from notesdb import *
from sco_utils import *
from notes_log import log
import sco_codes_parcours
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
    if not matiere_id:
        raise ScoValueError('invalid matiere !')
    M = context.do_matiere_list( args={'matiere_id' : matiere_id} )[0]
    UE = context.do_ue_list( args={'ue_id' : M['ue_id']} )[0]
    Fo = context.formation_list( args={ 'formation_id' : UE['formation_id'] } )[0]
    parcours = sco_codes_parcours.get_parcours_from_code(Fo['type_parcours'])
    semestres_indices = range(1, parcours.NB_SEM+1)
    H = [ context.sco_header(REQUEST, page_title="Création d'un module"),
          """<h2>Création d'un module dans la matière %(titre)s""" % M,
          """ (UE %(acronyme)s)</h2>""" % UE,
          _MODULE_HELP
          ]
    # cherche le numero adequat (pour placer le module en fin de liste)
    Mods = context.do_module_list(args={ 'matiere_id' :  matiere_id } )
    if Mods:
        default_num = max([ m['numero'] for m in Mods ]) + 10
    else:
        default_num = 10
    tf = TrivialFormulator(REQUEST.URL0, REQUEST.form, (
        ('code'    , { 'size' : 10, 'explanation' : 'code du module (doit être unique dans la formation)', 'allow_null' : False,
                       'validator' : lambda val, field, formation_id=Fo['formation_id']: check_module_code_unicity(val, field, formation_id, context),
                       }),
        ('titre'    , { 'size' : 30, 'explanation' : 'nom du module' }),
        ('abbrev'    , { 'size' : 20, 'explanation' : 'nom abrégé (pour bulletins)' }),

        ('heures_cours' , { 'size' : 4, 'type' : 'float', 'explanation' : 'nombre d\'heures de cours' }),
        ('heures_td'    , { 'size' : 4, 'type' : 'float', 'explanation' : 'nombre d\'heures de Travaux Dirigés' }),
        ('heures_tp'    , { 'size' : 4, 'type' : 'float', 'explanation' : 'nombre d\'heures de Travaux Pratiques' }),
        
        ('coefficient'  , { 'size' : 4, 'type' : 'float', 'explanation' : 'coefficient dans la formation (PPN)', 'allow_null' : False }),
        #('ects', { 'size' : 4, 'type' : 'float', 'title' : 'ECTS', 'explanation' : 'nombre de crédits ECTS (inutilisés: les crédits sont associés aux UE)' }),

        ('formation_id', { 'default' : UE['formation_id'], 'input_type' : 'hidden' }),
        ('ue_id', { 'default' : M['ue_id'], 'input_type' : 'hidden' }),
        ('matiere_id', { 'default' : M['matiere_id'], 'input_type' : 'hidden' }),
        
        ('semestre_id', { 'input_type' : 'menu',  'type' : 'int',
                          'title' : strcapitalize(parcours.SESSION_NAME), 
                          'explanation' : '%s de début du module dans la formation standard' % parcours.SESSION_NAME,
                          'labels' : [ str(x) for x in semestres_indices ], 'allowed_values' : semestres_indices }),
        ('numero',    { 'size' : 2, 'explanation' : 'numéro (1,2,3,4...) pour ordre d\'affichage',
                        'type' : 'int', 'default': default_num }),
        ),
                           submitlabel = 'Créer ce module')
    if tf[0] == 0:
        return '\n'.join(H) + tf[1] + context.sco_footer(REQUEST)
    else:
        moduleid = context.do_module_create( tf[2], REQUEST )
        return REQUEST.RESPONSE.redirect( REQUEST.URL1 + '/ue_list?formation_id=' + UE['formation_id'])


def module_delete(context, module_id=None, REQUEST=None):
    """Delete a module"""
    if not module_id:
        raise ScoValueError('invalid module !')
    Mods = context.do_module_list(args={ 'module_id' : module_id } )
    if not Mods:
        raise ScoValueError('Module inexistant !')
    Mod = Mods[0]
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

def check_module_code_unicity(code, field, formation_id, context, module_id=None):
    "true si code module unique dans la formation"
    Mods = context.do_module_list( args={ 'code' : code, 'formation_id' : formation_id } )
    if module_id: # edition: supprime le module en cours
        Mods = [ m for m in Mods if m['module_id'] != module_id ]
    
    return len(Mods) == 0

    
def module_edit(context, module_id=None, REQUEST=None):
    """Edit a module"""
    if not module_id:
        raise ScoValueError('invalid module !')
    Mod= context.do_module_list( args={ 'module_id' : module_id } )
    if not Mod:
        raise ScoValueError('invalid module !')
    Mod = Mod[0]
    unlocked = not context.module_is_locked(module_id)
    Fo = context.formation_list( args={ 'formation_id' : Mod['formation_id'] } )[0]
    parcours = sco_codes_parcours.get_parcours_from_code(Fo['type_parcours'])
    M  = SimpleDictFetch(context, "SELECT ue.acronyme, mat.* FROM notes_matieres mat, notes_ue ue WHERE mat.ue_id = ue.ue_id AND ue.formation_id = %(formation_id)s ORDER BY ue.numero, mat.numero", {'formation_id' : Mod['formation_id']})
    Mnames = [ '%s / %s' % (x['acronyme'], x['titre']) for x in M ]
    Mids = [ '%s!%s' % (x['ue_id'], x['matiere_id']) for x in M ]
    Mod['ue_matiere_id'] = '%s!%s' % (Mod['ue_id'], Mod['matiere_id'])

    semestres_indices = range(1, parcours.NB_SEM+1)
    
    dest_url = REQUEST.URL1 + '/ue_list?formation_id=' + Mod['formation_id']

    H = [ context.sco_header(REQUEST, page_title="Modification du module %(titre)s" % Mod),
          """<h2>Modification du module %(titre)s""" % Mod,
          """ (formation %(acronyme)s, version %(version)s)</h2>""" % Fo,
          _MODULE_HELP ]
    if not unlocked:
        H.append("""<div class="ue_warning"><span>Formation verrouillée, seuls certains éléments peuvent être modifiés</span></div>""")
    
    tf = TrivialFormulator(REQUEST.URL0, REQUEST.form, (
        ('code'    , { 'size' : 10, 'explanation' : 'code du module (doit être unique dans la formation)', 'allow_null' : False, 
                       'validator' : lambda val, field, formation_id=Mod['formation_id']: check_module_code_unicity(val, field, formation_id, context, module_id=module_id),
                       }),
        ('titre'    , { 'size' : 30, 'explanation' : 'nom du module' }),
        ('abbrev'    , { 'size' : 20, 'explanation' : 'nom abrégé (pour bulletins)' }),

        ('heures_cours' , { 'size' : 4, 'type' : 'float', 'explanation' : 'nombre d\'heures de cours' }),
        ('heures_td'    , { 'size' : 4, 'type' : 'float', 'explanation' : 'nombre d\'heures de Travaux Dirigés' }),
        ('heures_tp'    , { 'size' : 4, 'type' : 'float', 'explanation' : 'nombre d\'heures de Travaux Pratiques' }),
        
        ('coefficient'    , { 'size' : 4, 'type' : 'float', 'explanation' : 'coefficient dans la formation (PPN)', 'allow_null' : False, 'enabled' : unlocked }),
        #('ects', { 'size' : 4, 'type' : 'float', 'title' : 'ECTS', 'explanation' : 'nombre de crédits ECTS',  'enabled' : unlocked }),
        ('formation_id', { 'input_type' : 'hidden' }),
        ('ue_id',        { 'input_type' : 'hidden' }),
        ('module_id',    { 'input_type' : 'hidden' }),
        
        ('ue_matiere_id', { 'input_type' : 'menu', 'title' : 'Matière', 
                            'explanation' : 'un module appartient à une seule matière.',
                            'labels' : Mnames, 'allowed_values' : Mids, 'enabled' : unlocked }),

        ('semestre_id', { 'input_type' : 'menu', 'type' : 'int',
                          'title' : parcours.SESSION_NAME.capitalize(), 
                          'explanation' : '%s de début du module dans la formation standard' % parcours.SESSION_NAME,
                          'labels' : [ str(x) for x in semestres_indices ] , 'allowed_values' : semestres_indices,  'enabled' : unlocked }),
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
        # l'UE peut changer
        tf[2]['ue_id'], tf[2]['matiere_id'] = tf[2]['ue_matiere_id'].split('!')
        # Check unicité code module dans la formation
        
        context.do_module_edit(tf[2])
        return REQUEST.RESPONSE.redirect(dest_url)

def module_list(context, formation_id, REQUEST=None):
    """Liste des modules de la formation
    (XXX inutile ou a revoir)
    """
    if not formation_id:
        raise ScoValueError('invalid formation !')
    F = context.formation_list( args={ 'formation_id' : formation_id } )[0]
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
