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

"""Semestres: Codes gestion parcours (constantes)
"""
from types import ListType, TupleType

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
    ADM : 'Admis',
    ADC : 'Admis par compensation',
    ADJ : 'Admis par le Jury',
    ATT : 'Décision en attente du semestre suivant (faute d\'atteindre la moyenne)',
    ATB : 'Décision en attente du semestre suivant (une UE n\'atteint pas la barre)',
    ATJ : 'Décision en attente du semestre suivant (assiduité insuffisante)',
    AJ  : 'Ajourné (échec)',
    NAR : 'Echec, non autorisé à redoubler'
    }

CODES_SEM_VALIDES = { 'ADM' : True, 'ADC' : True, 'ADJ' : True } # semestre validé

CODES_SEM_REO = { 'NAR':1 } # reorientation

def code_semestre_validant(code):
    "Vrai si ce CODE entraine la validation du semestre"
    return CODES_SEM_VALIDES.get(code, False)

DEVENIR_EXPL = {
    NEXT      : 'Passage au semestre suivant',
    REDOANNEE : 'Redoublement année',
    REDOSEM   : 'Redoublement semestre',
    RA_OR_NEXT: 'Passage, ou redoublement année',
    RA_OR_RS  : 'Redoublement année, ou redoublement semestre', # slt si sems decales
    RS_OR_NEXT: 'Passage, ou redoublement semestre',
    REO       : 'Réorientation'
}

# Devenirs autorises dans les cursus sans semestres décalés:
DEVENIRS_STD = { NEXT:1, REDOANNEE:1, RA_OR_NEXT:1, REO:1 }

# Devenis autorises dans les cursus en un seul semestre, semestre_id==-1 (licences ?)
DEVENIRS_MONO = { REDOANNEE:1, REO:1 }

# Nombre max de sem DUT (a placer dans notes_formations ?)
DUT_NB_SEM = 4
NO_SEMESTRE_ID = -1 # code semestre si pas de semestres

# Passage: autorise-t-on les sauts de semestres ?
ALLOW_SEM_SKIP = False

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

