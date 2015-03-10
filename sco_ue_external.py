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
from sco_utils import *
from notes_log import log
import sco_edit_ue
import sco_saisie_notes

def external_ue_create(context, 
                       formsemestre_id,                       
                       titre='', acronyme='', ue_type=0, ects=0.,  
                       notes_etuds={}, # { etudid : note } (optionnel)
                       REQUEST=None
                       ):
    """Crée UE/matiere/module/evaluation puis saisie les notes
    """
    sem = context.get_formsemestre(formsemestre_id)
    # Contrôle d'accès:
    authuser = REQUEST.AUTHENTICATED_USER
    if not authuser.has_permission(ScoImplement,context):
        if not sem['resp_can_edit'] or str(authuser) != sem['responsable_id']:
            raise AccessDenied("vous n'avez pas le droit d'effectuer cette opération")
    #
    formation_id = sem['formation_id']
    log('creating external UE in %s: %s' % (formsemestre_id, acronyme))
    
    numero = sco_edit_ue.next_ue_numero(context, formation_id, semestre_id=sem['semestre_id']):
    ue_id = context.do_ue_create( {
        'formation_id' : formation_id,
        'titre' : titre, 
        'acronyme' : acronyme,
        'numero' : numero,
        'type' : ue_type,
        'ects' : ects,        
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
        context, authuser, evaluation_id, notes_etuds.items(), do_it=True )


def external_ue_create_form(context, formsemestre_id, etudid, REQUEST=None):
    """Formulaire création UE externe + inscription étudiant et saisie note
    - Demande UE: peut-être existante (liste les UE externes de cette formation), 
       ou sinon spécifier titre, acronyme, type, ECTS
    - Demande note à enregistrer.

    Note: pour l'édition éventuelle de ces informations, on utilisera les 
    fonctions standards sur les UE/modules/notes
    """
    sem = context.get_formsemestre(formsemestre_id)
    F = context.formation_list( args={ 'formation_id' : sem['formation_id'] } )[0]
    existing_external_ue = context.do_ue_list( args={ 'formation_id' : formation_id, 'is_external' : 1 } )

    
    H = [ context.html_sem_header(REQUEST, "Ajout d'une UE externe", sem,
                                  init_jquery_ui=True,
                                  javascripts=['libjs/AutoSuggest.js'],
                                  cssstyles=['css/autosuggest_inquisitor.css'], 
                                  bodyOnLoad="init_tf_form('')"
                                  ) ]
    tf = TrivialFormulator(REQUEST.URL0, REQUEST.form, (
        ('existing_ue', {
            'input_type' : 'menu',
            'title' : 'UE externe existante:',
            'allowed_values' : [''] + [ ue[''] for ue_id in existing_external_ue ],
            'labels' :  ['(aucune)'] + [ '%s (%s)' % (ue['titre'], ue['acronyme']) for ue in existing_external_ue ],
            'explanation' : 'inscrire cet étudiant dans '
            }),
        ('sep', { 'input_type' : 'separator', 'title' : 'Ou bien déclarer une nouvelle UE externe:' }),
        ('titre', { 'size' : 30, 'explanation' : 'nom de l\'UE' }),
        ('acronyme' , { 'size' : 8, 'explanation' : 'abbréviation', 'allow_null' : False }),
        ('note', { 'size' : 4 }),
        ),
        submitlabel = 'Enregistrer',
        cancelbutton = 'Annuler',
        )
     
    return '\n'.join(H) + context.sco_footer(REQUEST)
