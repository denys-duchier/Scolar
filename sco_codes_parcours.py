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

def code_semestre_validant(code):
    "Vrai si ce CODE entraine la validation du semestre"
    return code[:2] == 'AD'

# codes actions
REDOANNEE = 'REDOANNEE'
REDOSEM   = 'REDOSEM'
RA_OR_NEXT= 'RA_OR_NEXT'
RA_OR_RS  = 'RA_OR_RS'
RS_OR_NEXT= 'RS_OR_NEXT'
NEXT='NEXT'
REO='REO'
BUG='BUG'

ALL='ALL'

CODES_EXPL = {
    ADM : 'Admis',
    ADC : 'Admis par compensation',
    ADJ : 'Admis par le Jury',
    ATT : 'D�cision en attente du semestre suivant (faute d\'atteindre la moyenne)',
    ATB : 'D�cision en attente du semestre suivant (une UE n\'atteint pas la barre)',
    ATJ : 'D�cision en attente du semestre suivant (assiduit� insuffisante)',
    AJ  : 'Ajourn� (�chec)',
    NAR : 'Echec, non autoris� � redoubler'
    }

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

# Nombre max de sem DUT (a placer dans notes_formations ?)
DUT_NB_SEM = 4
NO_SEMESTRE_ID = -1 # code semestre si pas de semestres

# Regles gestion parcours
class DUTRule:
    def __init__(self, premise, conclusion ):
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

