# -*- coding: iso8859-15 -*-
#
# Generated by csv2rules.py    *** DO NOT EDIT ***
#
# Command: ./csv2rules.py misc/parcoursDUT.csv
# 
from sco_codes_parcours import *

rules_source_file='misc/parcoursDUT.csv'

DUTRules = [ DUTRule(p, c) for (p,c) in (
# Prev.	Assiduit�	Moy Gen	Barres UE	Comp prev/cur	Suivant	Code SEM	Codes UE	Code prev. (si modifi�)	Devenir	Action	Explication
# Semestre prec. valid�:
( ((None, ADM, ADC, ADJ), True, True, True, ALL, ALL),
  (ADM, (ADM,), None, NEXT, None, 'Passage normal') ),
( ((None, ADM, ADC, ADJ), True, False, True, ALL, True),
  (ATT, (ADM,), None, NEXT, None, 'Pas moy: attente suivant pour compenser') ),
( ((None, ADM, ADC, ADJ), True, ALL, False, ALL, ALL),
  (ATB, (ADM, AJ), None, NEXT, None, 'Pas barre UE') ),
( ((None, ADM, ADC, ADJ), False, ALL, ALL, ALL, True),
  (ATJ, (AJ,), None, NEXT, None, 'Pb assiduit�, passe sans valider pour l\'instant') ),
( ((ADM, ADJ, ADC), True, False, ALL, True, ALL),
  (ADC, (ADM, CMP), None, NEXT, None, 'Compense avec semestre pr�c�dent') ),
# Semestre prec. ATJ (pb assiduit�):
( ((ATJ,), False, ALL, ALL, ALL, ALL),
  (NAR, (AJ,), AJ, REO, None, 'Pb assiduit� persistant: r�orientation') ),
( ((ATJ,), False, ALL, ALL, ALL, ALL),
  (AJ, (AJ,), AJ, REDOANNEE, None, 'Pb assiduit� persistant: redoublement ann�e') ),
( ((ALL,), False, ALL, ALL, ALL, ALL),
  (AJ, (), ADM, REO, None, 'Pb assiduit�, �tudiant en �chec.') ),
# Semestre prec. ATT (pb moy gen):
( ((ATT,), True, True, True, True, ALL),
  (ADM, (ADM,), ADC, NEXT, None, 'Passage, et compense pr�c�dent') ),
( ((ATT,), True, True, True, ALL, ALL),
  (ADM, (ADJ,), ADJ, NEXT, None, 'Passage, le jury valide le pr�c�dent') ),
( ((ATT,), False, True, True, ALL, True),
  (ATJ, (AJ,), ADJ, NEXT, None, 'Passage, le jury valide le pr�c�dent, pb assiduit�') ),
( ((ATT,), True, False, ALL, ALL, ALL),
  (AJ, (AJ,), AJ, REDOANNEE, None, 'Redoublement ann�e') ),
( ((ATT,), ALL, True, True, False, ALL),
  (AJ, (AJ,), AJ, REDOANNEE, None, 'Pas de compensation ni validation du pr�c�dent') ),
# Semestre prec. ATB (pb barre UE):
( ((ATB,), ALL, ALL, ALL, ALL, ALL),
  (AJ, (ADM, AJ), AJ, REDOANNEE, None, 'Le pr�c�dent ne peut pas �tre valid�, redoublement ann�e') ),
( ((ATB,), ALL, ALL, ALL, ALL, ALL),
  (NAR, (ADM, AJ), NAR, REO, None, 'Le pr�c�dent ne peut pas �tre valid�, r�orientation') ),
( ((ATB,), True, True, True, ALL, ALL),
  (ADM, (ADM,), ADJ, None, None, 'Le jury valide le pr�c�dent') ),
( ((ATB,), True, False, True, ALL, True),
  (ATT, (ADM, AJ), ADJ, None, None, 'Le jury valide le pr�c�dent, pas moyenne gen., attente suivant') ),
( ((ATB,), True, ALL, False, ALL, True),
  (ATB, (ADM, AJ), ADJ, None, None, 'Le jury valide le pr�c�dent, pb barre UE, attente') ),
( ((ATB,), False, ALL, ALL, ALL, True),
  (ATJ, (AJ,), ADJ, None, None, 'Le jury valide le pr�c�dent, mais probleme assiduit�.') ),
# Semestre prec. AJ (ajourn�):
( ((AJ,), True, False, ALL, ALL, ALL),
  (AJ, (), AJ, REDOANNEE, None, 'Echec de 2 semestres, redouble ann�e') ),
( ((AJ,), True, True, False, ALL, ALL),
  (AJ, (), AJ, REDOANNEE, None, 'Echec de 2 semestres, redouble ann�e') ),
( ((AJ,), False, ALL, ALL, ALL, ALL),
  (NAR, (), None, REO, None, 'Echec, pas assidu: r�orientation') ),
# D�cisions du jury:
( ((ALL,), True, False, ALL, ALL, ALL),
  (ADJ, (ADM,CMP), None, NEXT, None, 'Le jury d�cide de valider') ),
( ((ATT,ATB), True, False, ALL, ALL, ALL),
  (ADJ, (ADM,CMP), ADJ, NEXT, None, 'Le jury d�cide de valider ce semestre et le pr�c�dent') ),
( ((ALL,), True, True, False, ALL, ALL),
  (ADJ, (ADM,CMP), None, NEXT, None, 'Le jury d�cide de valider') ),
( ((ATT,ATB), True, True, False, ALL, ALL),
  (ADJ, (ADM,CMP), ADJ, NEXT, None, 'Le jury d�cide de valider ce semestre et le pr�c�dent') ),
( ((ATT,ATB), False, False, True, ALL, True),
  (ATT, (ADM, AJ), ADJ, NEXT, None, 'Pb moy: attente, mais le jury valide le pr�c�dent') ),
# Semestres "d�cales" (REDOSEM)
( ((None, ADM, ADC, ADJ), True, False, ALL, False, ALL),
  (AJ, (), None, REDOSEM, None, 'Pas moy: redouble ce semestre') ),
( ((None, ADM, ADC, ADJ), True, True, False, False, ALL),
  (AJ, (), None, REDOSEM, None, 'Pas barre UE: redouble ce semestre') ),
( ((None, ADM, ADC, ADJ), False, ALL, ALL, ALL, ALL),
  (AJ, (), None, REDOSEM, None, 'Pb assiduit�: redouble ce semestre') ),
# Exclusion (art. 22): si precedent non valide et pas les barres dans le courant, on peut ne pas autoriser a redoubler:
# (le cas ATB est couvert plus haut)
( ((AJ,ATT,NAR), True, False, ALL, ALL, ALL),
  (NAR, (), NAR, REO, None, 'Non autoris� � redoubler') ),
( ((AJ,ATT,NAR), True, True, False, ALL, ALL),
  (NAR, (), NAR, REO, None, 'Non autoris� � redoubler') ),
)]
