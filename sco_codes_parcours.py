# -*- mode: python -*-
# -*- coding: iso8859-15 -*-

##############################################################################
#
# Gestion scolarite IUT
#
# Copyright (c) 2001 - 2010 Emmanuel Viennet.  All rights reserved.
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

# Codes propos�s par ADIUT / Apogee
ADM='ADM' # moyenne gen., barres UE, assiduit�: sem. valid�
ADC='ADC' # admis par compensation (eg moy(S1, S2) > 10)
ADJ='ADJ' # admis par le jury
ATT='ATT' # 
ATJ='ATJ' # pb assiduit�: d�cision repouss�e au semestre suivant
ATB='ATB'
AJ ='AJ'
CMP='CMP' # utile pour UE seulement
NAR='NAR'
RAT='RAT' # en attente rattrapage, pas dans Apog�e

# codes actions
REDOANNEE = 'REDOANNEE'  # redouble annee (va en Sn-1)
REDOSEM   = 'REDOSEM'    # redouble semestre (va en Sn)
RA_OR_NEXT= 'RA_OR_NEXT' # redouble annee ou passe en Sn+1
RA_OR_RS  = 'RA_OR_RS'   # redouble annee ou semestre
RS_OR_NEXT= 'RS_OR_NEXT' # redouble semestre ou passe en Sn+1
NEXT='NEXT'
REO='REO'
BUG='BUG'

ALL='ALL'

CODES_EXPL = {
    ADM : 'Valid�',
    ADC : 'Valid� par compensation',
    ADJ : 'Valid� par le Jury',
    ATT : 'D�cision en attente d\'un autre semestre (faute d\'atteindre la moyenne)',
    ATB : 'D�cision en attente d\'un autre semestre (une UE n\'atteint pas la barre)',
    ATJ : 'D�cision en attente d\'un autre semestre (assiduit� insuffisante)',
    AJ  : 'Ajourn� (�chec)',
    NAR : 'Echec, non autoris� � redoubler',
    RAT : "En attente d'un rattrapage",
    }

CODES_SEM_VALIDES = { 'ADM' : True, 'ADC' : True, 'ADJ' : True } # semestre valid�

CODES_SEM_REO = { 'NAR':1 } # reorientation

def code_semestre_validant(code):
    "Vrai si ce CODE entraine la validation du semestre"
    return CODES_SEM_VALIDES.get(code, False)

DEVENIR_EXPL = {
    NEXT      : 'Passage au semestre suivant',
    REDOANNEE : 'Redoublement ann�e',
    REDOSEM   : 'Redoublement semestre',
    RA_OR_NEXT: 'Passage, ou redoublement ann�e',
    RA_OR_RS  : 'Redoublement ann�e, ou redoublement semestre', # slt si sems decales
    RS_OR_NEXT: 'Passage, ou redoublement semestre',
    REO       : 'R�orientation'
}

# Devenirs autorises dans les cursus sans semestres d�cal�s:
DEVENIRS_STD = { NEXT:1, REDOANNEE:1, RA_OR_NEXT:1, REO:1 }

# Devenirs autorises dans les cursus en un seul semestre, semestre_id==-1 (licences ?)
DEVENIRS_MONO = { REDOANNEE:1, REO:1 }

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
    TYPE_PARCOURS = None # id, utilis� par notes_formation.type_parcours
    NAME = None # required
    NB_SEM = 1 # Nombre de semestres
    COMPENSATION_UE = True
    BARRE_MOY = 10.
    BARRE_UE_DEFAULT = 8.
    BARRE_UE = {}
    NOTES_BARRE_VALID_UE_TH = 10. # seuil pour valider UE
    NOTES_BARRE_VALID_UE = 10. - NOTES_TOLERANCE   # barre sur UE
    ALLOW_SEM_SKIP = False # Passage: autorise-t-on les sauts de semestres ?
    def check(self, formation=None):
        return True, '' # status, diagnostic_message
    def get_barre_ue(self, ue_type, tolerance=True):
        """Barre pour cette UE (la valeur peut d�pendre du type d'UE).
        Si tolerance, diminue de epsilon pour �viter les effets d'arrondis.
        """
        if tolerance:
            t = NOTES_TOLERANCE
        else:
            t = 0.
        return self.BARRE_UE.get(ue_type, self.BARRE_UE_DEFAULT) - t

TYPES_PARCOURS = odict() # liste des parcours d�finis (instances de sous-classes de TypeParcours)
def register_parcours(Parcours):
    TYPES_PARCOURS[Parcours.TYPE_PARCOURS] = Parcours

class ParcoursDUT(TypeParcours):
    """DUT selon l'arr�t� d'ao�t 2005"""
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

# Ajouter ici vos parcours, le TYPE_PARCOURS devant �tre unique au monde
# (avisez sur la liste de diffusion)


# ...


# -------------------------
FORMATION_PARCOURS_DESCRS =  [ p.__doc__ for p in TYPES_PARCOURS.values() ]
FORMATION_PARCOURS_TYPES =   [ p.TYPE_PARCOURS for p in TYPES_PARCOURS.values() ] 

def get_parcours_from_code(code_parcours):
    return TYPES_PARCOURS[code_parcours]
