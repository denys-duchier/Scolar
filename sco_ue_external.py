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

"""Fonction de gestion des UE "externes" (effectuees dans un cursus exterieur)

On rapatrie (saisit) les notes (et crédits ECTS).

Contexte: les étudiants d'une formation gérée par ScoDoc peuvent
suivre un certain nombre d'UE à l'extérieur. L'établissement a reconnu
au préalable une forme d'équivalence entre ces UE et celles du
programme. Les UE effectuées à l'extérieur sont par nature variable
d'un étudiant à l'autre et d'une année à l'autre, et ne peuvent pas
être introduites dans le programme pédagogique ScoDoc sans alourdir
considérablement les opérations (saisie, affichage du programme,
gestion des inscriptions).
En outre, un  suivi détaillé de ces UE n'est pas nécessaire: il suffit
de pouvoir y associer une note et une quantité de crédits ECTS.

Solution proposée (nov 2014):
 - un nouveau type d'UE qui

    -  s'affichera à part dans le programme pédagogique
    et les bulletins
    - pas présentées lors de la mise en place de semestres
    - affichage sur bulletin des étudiants qui y sont inscrit
    - création en même temps que la saisie de la note
       (chaine creation: UE/matière/module, inscription étudiant, entrée valeur note)
       avec auto-suggestion du nom pour limiter la création de doublons
    - seront aussi présentées (à part) sur la page "Voir les inscriptions aux modules"

"""

from notesdb import *
from sco_utils import *
from notes_log import log
import sco_edit_ue
import sco_saisie_notes

def external_ue_create(context, 
                       formsemestre_id,                       
                       titre='', acronyme='', ue_type=UE_STANDARD, ects=0.,  
                       REQUEST=None
                       ):
    """Crée UE/matiere/module/evaluation puis saisie les notes
    """
    log('external_ue_create( formsemestre_id=%s, titre=%s )'%(formsemestre_id,titre))
    sem = context.get_formsemestre(formsemestre_id)
    # Contrôle d'accès:
    authuser = REQUEST.AUTHENTICATED_USER
    if not authuser.has_permission(ScoImplement,context):
        if not sem['resp_can_edit'] or str(authuser) != sem['responsable_id']:
            raise AccessDenied("vous n'avez pas le droit d'effectuer cette opération")
    #
    formation_id = sem['formation_id']
    log('creating external UE in %s: %s' % (formsemestre_id, acronyme))
    
    numero = sco_edit_ue.next_ue_numero(context, formation_id, semestre_id=sem['semestre_id'])
    ue_id = context.do_ue_create( {
        'formation_id' : formation_id,
        'titre' : titre, 
        'acronyme' : acronyme,
        'numero' : numero,
        'type' : ue_type,
        'ects' : ects,
        'is_external' : 1,
        }, REQUEST)

    matiere_id = context.do_matiere_create( { 'ue_id' : ue_id, 'titre' : titre, 'numero' : 1 }, REQUEST )
    module_id = context.do_module_create( 
        { 'titre' : titre, 
          'code' : acronyme,
          'coefficient' : 1.0, # tous les modules auront coef 1, et on utilisera les ECTS
          'ue_id' : ue_id,
          'matiere_id' : matiere_id,
          'formation_id' : formation_id,
          'semestre_id' : sem['semestre_id'], 
          }, REQUEST )

    moduleimpl_id = context.do_moduleimpl_create( {
        'module_id' : module_id,
        'formsemestre_id' : formsemestre_id,
        'responsable_id' :  sem['responsable_id']
        })

    return moduleimpl_id

def external_ue_inscrit_et_note(context, moduleimpl_id, formsemestre_id, notes_etuds, REQUEST=None):
    log('external_ue_inscrit_et_note(moduleimpl_id=%s, notes_etuds=%s)' % (moduleimpl_id, notes_etuds))
    # Inscription des étudiants
    context.do_moduleimpl_inscrit_etuds(moduleimpl_id, formsemestre_id, notes_etuds.keys(), REQUEST=REQUEST )
    
    # Création d'une évaluation
    evaluation_id = context.do_evaluation_create(REQUEST, {
        'moduleimpl_id' : moduleimpl_id,
        'note_max' : 20.,
        'coefficient' : 1.,
        'publish_incomplete' : 1,
        'evaluation_type' : 0,        
        'visibulletin' : 0, 
    } )
    # Saisie des notes
    nbchanged, nbsuppress, existing_decisions = sco_saisie_notes._notes_add(
        context, REQUEST.AUTHENTICATED_USER, evaluation_id, notes_etuds.items(), do_it=True )


def get_existing_external_ue(context, formation_id):
    "la liste de toutes les UE externes définies dans cette formation"
    return context.do_ue_list( args={ 'formation_id' : formation_id, 'is_external' : 1 } )

def get_external_moduleimpl_id(context, formsemestre_id, ue_id):
    "moduleimpl correspondant à l'UE externe indiquée de ce formsemestre"
    r = SimpleDictFetch(context, """
    SELECT moduleimpl_id FROM notes_moduleimpl mi, notes_modules mo
    WHERE mi.formsemestre_id = %(formsemestre_id)s
    AND mi.module_id = mo.module_id
    AND mo.ue_id = %(ue_id)s
    """, { 'ue_id' : ue_id, 'formsemestre_id' : formsemestre_id } )
    if r:
        return r[0]['moduleimpl_id']
    else:
        raise ScoValueError('aucun module externe ne correspond')

# Web function
def external_ue_create_form(context, formsemestre_id, etudid, REQUEST=None):
    """Formulaire création UE externe + inscription étudiant et saisie note
    - Demande UE: peut-être existante (liste les UE externes de cette formation), 
       ou sinon spécifier titre, acronyme, type, ECTS
    - Demande note à enregistrer.

    Note: pour l'édition éventuelle de ces informations, on utilisera les 
    fonctions standards sur les UE/modules/notes
    """
    # Contrôle d'accès:
    authuser = REQUEST.AUTHENTICATED_USER
    if not authuser.has_permission(ScoImplement,context):
        if not sem['resp_can_edit'] or str(authuser) != sem['responsable_id']:
            raise AccessDenied("vous n'avez pas le droit d'effectuer cette opération")
    
    sem = context.get_formsemestre(formsemestre_id)
    formation_id = sem['formation_id']
    F = context.formation_list( args={ 'formation_id' : formation_id } )[0]
    existing_external_ue = get_existing_external_ue(context, formation_id)

    
    H = [ context.html_sem_header(REQUEST, "Ajout d'une UE externe", sem,
                                  init_jquery_ui=True,
                                  javascripts=['js/sco_ue_external.js'],
                                  ) ]
    tf = TrivialFormulator(REQUEST.URL0, REQUEST.form, (
        ('formsemestre_id', { 'input_type' : 'hidden' }),
        ('etudid', { 'input_type' : 'hidden' }),
        ('existing_ue', {
            'input_type' : 'menu',
            'title' : 'UE externe existante:',
            'allowed_values' : [''] + [ ue['ue_id'] for ue in existing_external_ue ],
            'labels' :  ['(aucune)'] + [ '%s (%s)' % (ue['titre'], ue['acronyme']) for ue in existing_external_ue ],
            'attributes' : [ 'onchange="update_external_ue_form();"' ],
            'explanation' : 'inscrire cet étudiant dans cette UE'
            }),
        ('sep', { 'input_type' : 'separator', 'title' : 'Ou bien déclarer une nouvelle UE externe:', 'dom_id' : 'tf_extue_decl' }),
        # champs a desactiver si une UE existante est choisie
        ('titre', { 'size' : 30, 'explanation' : 'nom de l\'UE', 'dom_id' : 'tf_extue_titre' }),
        ('acronyme' , { 'size' : 8, 'explanation' : 'abbréviation', 'allow_null' : False, 'dom_id' : 'tf_extue_acronyme' }),
        ('ects', { 'size' : 4, 'type' : 'float', 'title' : 'ECTS', 'explanation' : 'nombre de crédits ECTS', 'dom_id' : 'tf_extue_ects' }),
        #
        ('note', { 'size' : 4, 'explanation' : 'note sur 20', 'dom_id' : 'tf_extue_note' }),
        ),
        submitlabel = 'Enregistrer',
        cancelbutton = 'Annuler',
        )

    bull_url = 'formsemestre_bulletinetud?formsemestre_id=%s&amp;etudid=%s' % (formsemestre_id,etudid)
    if  tf[0] == 0:
        return '\n'.join(H) + '\n' + tf[1] + context.sco_footer(REQUEST)
    elif tf[0] == -1:
        return REQUEST.RESPONSE.redirect(bull_url)
    else:
        note = tf[2]['note'].strip().upper()
        note_value, invalid = sco_saisie_notes.convert_note_from_string(note, 20.)
        if invalid:
            return '\n'.join(H) + '\n' + tf_error_message("valeur note invalide") + tf[1] + context.sco_footer(REQUEST)
        if tf[2]['existing_ue']:
            ue_id = tf[2]['existing_ue']
            moduleimpl_id = get_external_moduleimpl_id(context, formsemestre_id, ue_id)
        else:
            moduleimpl_id = external_ue_create(
                context, formsemestre_id, REQUEST=REQUEST,
                titre=tf[2]['titre'], 
                acronyme=tf[2]['acronyme'],
                ue_type=UE_STANDARD, # doit-on avoir le choix ? 
                ects=tf[2]['ects']  
                )
        
        external_ue_inscrit_et_note(context, moduleimpl_id, formsemestre_id, { etudid : note_value },
                                    REQUEST=REQUEST
            )
        return REQUEST.RESPONSE.redirect( bull_url + '&head_message=Ajout%20effectué' )
