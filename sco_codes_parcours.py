# -*- mode: python -*-
# -*- coding: iso8859-15 -*-

##############################################################################
#
# Gestion scolarite IUT
#
# Copyright (c) 2001 - 2011 Emmanuel Viennet.  All rights reserved.
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
#   Emmanuel Viennet      emmanuel.viennet@univ-paris13.fr
#
##############################################################################

"""Semestres: Codes gestion parcours (constantes)
"""
from types import ListType, TupleType
from odict import odict

from sco_utils import *

# Codes proposés par ADIUT / Apogee
ADM='ADM' # moyenne gen., barres UE, assiduité: sem. validé
ADC='ADC' # admis par compensation (eg moy(S1, S2) > 10)
ADJ='ADJ' # admis par le jury
ATT='ATT' # 
ATJ='ATJ' # pb assiduité: décision repoussée au semestre suivant
ATB='ATB'
AJ ='AJ'
CMP='CMP' # utile pour UE seulement
NAR='NAR'
RAT='RAT' # en attente rattrapage, pas dans Apogée

# codes actions
REDOANNEE = 'REDOANNEE'  # redouble annee (va en Sn-1)
REDOSEM   = 'REDOSEM'    # redouble semestre (va en Sn)
RA_OR_NEXT= 'RA_OR_NEXT' # redouble annee ou passe en Sn+1
RA_OR_RS  = 'RA_OR_RS'   # redouble annee ou semestre
RS_OR_NEXT= 'RS_OR_NEXT' # redouble semestre ou passe en Sn+1
NEXT_OR_NEXT2='NEXT_OR_NEXT2' # passe en suivant (Sn+1) ou sur-suivant (Sn+2)
NEXT='NEXT'
REO='REO'
BUG='BUG'

ALL='ALL'

CODES_EXPL = {
    ADM : 'Validé',
    ADC : 'Validé par compensation',
    ADJ : 'Validé par le Jury',
    ATT : 'Décision en attente d\'un autre semestre (faute d\'atteindre la moyenne)',
    ATB : 'Décision en attente d\'un autre semestre (une UE n\'atteint pas la barre)',
    ATJ : 'Décision en attente d\'un autre semestre (assiduité insuffisante)',
    AJ  : 'Ajourné (échec)',
    NAR : 'Echec, non autorisé à redoubler',
    RAT : "En attente d'un rattrapage",
    }

CODES_SEM_VALIDES = { ADM : True, ADC : True, ADJ : True } # semestre validé
CODES_SEM_ATTENTES = { ATT : True, ATB : True, ATJ : True } # semestre en attente

CODES_SEM_REO = { 'NAR':1 } # reorientation

def code_semestre_validant(code):
    "Vrai si ce CODE entraine la validation du semestre"
    return CODES_SEM_VALIDES.get(code, False)

def code_semestre_attente(code):
    "Vrai si ce CODE est un code d'attente (semestre validable plus tard par jury ou compensation)"
    return CODES_SEM_ATTENTES.get(code, False)

DEVENIR_EXPL = {
    NEXT      : 'Passage au semestre suivant',
    REDOANNEE : 'Redoublement année',
    REDOSEM   : 'Redoublement semestre',
    RA_OR_NEXT: 'Passage, ou redoublement année',
    RA_OR_RS  : 'Redoublement année, ou redoublement semestre', # slt si sems decales
    RS_OR_NEXT: 'Passage, ou redoublement semestre',
    NEXT_OR_NEXT2 : "Passage en semestre suivant ou à celui d'après",
    REO       : 'Réorientation'
}

# Devenirs autorises dans les cursus sans semestres décalés:
DEVENIRS_STD = { NEXT:1, REDOANNEE:1, RA_OR_NEXT:1, REO:1 }

# Devenirs autorises dans les cursus en un seul semestre, semestre_id==-1 (licences ?)
DEVENIRS_MONO = { REDOANNEE:1, REO:1 }

# Devenirs supplementaires (en mode manuel) pour les cursus avec semestres decales
DEVENIRS_DEC = { REDOSEM:1, RS_OR_NEXT:1 }

# Devenirs en n+2 (sautant un semestre)  (si semestres décalés et s'il ne manque qu'un semestre avant le n+2)
DEVENIRS_NEXT2 = { NEXT_OR_NEXT2: 1 }

NO_SEMESTRE_ID = -1 # code semestre si pas de semestres

# Regles gestion parcours
class DUTRule:
    def __init__(self, rule_id, premise, conclusion ):
        self.rule_id = rule_id
        self.premise = premise
        self.conclusion = conclusion
        #self.code, self.codes_ue, self.devenir, self.action, self.explication = conclusion
        
    def match(self, state):
        "True if state match rule premise"
        assert len(state) == len(self.premise)
        for i in range(len(state)):
            prem = self.premise[i]
            if type(prem) == ListType or type(prem) == TupleType:
                if not state[i] in prem:
                    return False
            else:
                if prem != ALL and prem != state[i]:
                    return False
        return True

# Types de parcours
class TypeParcours:
    TYPE_PARCOURS = None # id, utilisé par notes_formation.type_parcours
    NAME = None # required
    NB_SEM = 1 # Nombre de semestres
    COMPENSATION_UE = True
    BARRE_MOY = 10.
    BARRE_UE_DEFAULT = 8.
    BARRE_UE = {}
    NOTES_BARRE_VALID_UE_TH = 10. # seuil pour valider UE
    NOTES_BARRE_VALID_UE = NOTES_BARRE_VALID_UE_TH - NOTES_TOLERANCE   # barre sur UE
    ALLOW_SEM_SKIP = False # Passage: autorise-t-on les sauts de semestres ?
    SESSION_NAME = 'semestre'
    def check(self, formation=None):
        return True, '' # status, diagnostic_message
    def get_barre_ue(self, ue_type, tolerance=True):
        """Barre pour cette UE (la valeur peut dépendre du type d'UE).
        Si tolerance, diminue de epsilon pour éviter les effets d'arrondis.
        """
        if tolerance:
            t = NOTES_TOLERANCE
        else:
            t = 0.
        return self.BARRE_UE.get(ue_type, self.BARRE_UE_DEFAULT) - t

TYPES_PARCOURS = odict() # liste des parcours définis (instances de sous-classes de TypeParcours)
def register_parcours(Parcours):
    TYPES_PARCOURS[Parcours.TYPE_PARCOURS] = Parcours

class ParcoursDUT(TypeParcours):
    """DUT selon l'arrêté d'août 2005"""
    TYPE_PARCOURS = 100
    NAME = "DUT"
    NB_SEM = 4 
    COMPENSATION_UE = True

register_parcours(ParcoursDUT())

class ParcoursDUT4(ParcoursDUT):
    """DUT (en 4 semestres sans compensations)"""
    TYPE_PARCOURS = 110
    NAME = "DUT4"
    COMPENSATION_UE = False

register_parcours(ParcoursDUT4())


class ParcoursLP(TypeParcours):
    """Licence Pro (en un "semestre")"""
    TYPE_PARCOURS = 200
    NAME = "LP"
    NB_SEM = 1
    COMPENSATION_UE = False
    BARRE_UE = { UE_STAGE_LP : 10. }

register_parcours(ParcoursLP())


class ParcoursMono(TypeParcours):
    """Formation en une session"""
    TYPE_PARCOURS = 300
    NAME = "Mono"
    NB_SEM = 1
    COMPENSATION_UE = False

register_parcours(ParcoursMono())


class ParcoursLegacy(TypeParcours):
    """DUT (ancien ScoDoc, ne plus utiliser)"""
    TYPE_PARCOURS = 0
    NAME = "DUT"
    NB_SEM = 4
    COMPENSATION_UE = None # backward compat: defini dans formsemestre

register_parcours(ParcoursLegacy())

class ParcoursUCAC(TypeParcours):
    """Règles de validation UCAC"""
    SESSION_NAME = "année"
    COMPENSATION_UE = False
    BARRE_MOY = 12.
    NOTES_BARRE_VALID_UE_TH = 12. # seuil pour valider UE
    NOTES_BARRE_VALID_UE = NOTES_BARRE_VALID_UE_TH - NOTES_TOLERANCE   # barre sur UE
    BARRE_UE_DEFAULT = NOTES_BARRE_VALID_UE_TH # il faut valider tt les UE pour valider l'année
    
class ParcoursLicenceUCAC3(ParcoursUCAC):
    """Licence UCAC en 3 sessions d'un an"""
    TYPE_PARCOURS = 501
    NAME = "Licence UCAC en 3 sessions d'un an"
    NB_SEM = 3

register_parcours(ParcoursLicenceUCAC3())

class ParcoursMasterUCAC2(ParcoursUCAC):
    """Master UCAC en 2 sessions d'un an"""
    TYPE_PARCOURS = 502
    NAME = "Master UCAC en 2 sessions d'un an"
    NB_SEM = 2

register_parcours(ParcoursMasterUCAC2())

class ParcoursMonoUCAC(ParcoursUCAC):
    """Formation UCAC en 1 session de durée variable"""
    TYPE_PARCOURS = 503
    NAME = "Formation UCAC en 1 session de durée variable"
    NB_SEM = 1

register_parcours(ParcoursMonoUCAC())

class Parcours6Sem(TypeParcours):
    """Parcours générique en 6 semestres"""
    TYPE_PARCOURS = 600
    NAME = "Formation en 6 semestres"
    NB_SEM = 6
    COMPENSATION_UE = True

register_parcours(Parcours6Sem)

# # En cours d'implémentation:
# class ParcoursLicenceLMD(TypeParcours):
#     """Licence standard en 6 semestres dans le LMD"""
#     TYPE_PARCOURS = 401
#     NAME = "Licence LMD"
#     NB_SEM = 6
#     COMPENSATION_UE = True

# register_parcours(ParcoursLicenceLMD())

# class ParcoursMasterLMD(TypeParcours):
#     """Master standard en 4 semestres dans le LMD"""
#     TYPE_PARCOURS = 402
#     NAME = "Master LMD"
#     NB_SEM = 4
#     COMPENSATION_UE = True

# register_parcours(ParcoursMasterLMD())



# Ajouter ici vos parcours, le TYPE_PARCOURS devant être unique au monde
# (avisez sur la liste de diffusion)


# ...


# -------------------------
FORMATION_PARCOURS_DESCRS =  [ p.__doc__ for p in TYPES_PARCOURS.values() ]
FORMATION_PARCOURS_TYPES =   [ p.TYPE_PARCOURS for p in TYPES_PARCOURS.values() ] 

def get_parcours_from_code(code_parcours):
    return TYPES_PARCOURS[code_parcours]
