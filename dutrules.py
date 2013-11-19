# -*- coding: utf-8 -*-
#
# Generated by csv2rules.py    *** DO NOT EDIT ***
#
# Command: csv2rules.py misc/parcoursDUT.csv
# 
from sco_codes_parcours import *

rules_source_file='misc/parcoursDUT.csv'

DUTRules = [ DUTRule(rid, p, c) for (rid, p,c) in (
# Id	Prev.	Assiduité	Moy Gen	Barres UE	Comp prev/cur	Suivant	Code SEM	Codes UE	Code prev. (si modifié)	Devenir	Action	Explication
# Semestre prec. validé:
( '10', ((None, ADM, ADC, ADJ), True, True, True, ALL, ALL),
  (ADM, (ADM,), None, NEXT, None, 'Passage normal') ),
( '20', ((None, ADM, ADC, ADJ), True, False, True, ALL, True),
  (ATT, (ADM,), None, NEXT, None, 'Pas moy: attente suivant pour compenser') ),
( '30', ((None, ADM, ADC, ADJ), True, ALL, False, ALL, ALL),
  (ATB, (ADM, AJ), None, NEXT, None, 'Pas barre UE') ),
( '40', ((None, ADM, ADC, ADJ), False, ALL, ALL, ALL, True),
  (ATJ, (AJ,), None, NEXT, None, 'Pb assiduité, passe sans valider pour l\'instant') ),
( '50', ((ADM, ADJ, ADC), True, False, ALL, True, ALL),
  (ADC, (ADM, CMP), None, NEXT, None, 'Compense avec semestre précédent') ),
# Semestre prec. ATJ (pb assiduité):
( '60', ((ATJ,), False, ALL, ALL, ALL, ALL),
  (NAR, (AJ,), AJ, REO, None, 'Pb assiduité persistant: réorientation') ),
( '70', ((ATJ,), False, ALL, ALL, ALL, ALL),
  (AJ, (AJ,), AJ, REDOANNEE, None, 'Pb assiduité persistant: redoublement année') ),
( '80', ((ALL,), False, ALL, ALL, ALL, ALL),
  (AJ, (), ADM, REO, None, 'Pb assiduité, étudiant en échec.') ),
# Semestre prec. ATT (pb moy gen):
( '90', ((ATT,), True, True, True, True, ALL),
  (ADM, (ADM,), ADC, NEXT, None, 'Passage, et compense précédent') ),
( '100', ((ATT,), True, True, True, ALL, ALL),
  (ADM, (ADJ,), ADJ, NEXT, None, 'Passage, le jury valide le précédent') ),
( '110', ((ATT,), False, True, True, ALL, True),
  (ATJ, (AJ,), ADJ, NEXT, None, 'Passage, le jury valide le précédent, pb assiduité') ),
( '120', ((ATT,), True, False, ALL, ALL, ALL),
  (AJ, (AJ,), AJ, REDOANNEE, None, 'Redoublement année') ),
( '130', ((ATT,), ALL, True, True, False, ALL),
  (AJ, (AJ,), AJ, REDOANNEE, None, 'Pas de compensation ni validation du précédent') ),
( '140', ((ATT,), True, False, True, ALL, ALL),
  (ATT, (), ADJ, NEXT, None, 'Pas moy, le jury valide le précédent, semestre en attente pour compenser') ),
# Semestre prec. ATB (pb barre UE):
( '200', ((ATB,), ALL, ALL, ALL, ALL, ALL),
  (AJ, (ADM, AJ), AJ, REDOANNEE, None, 'Le précédent ne peut pas être validé, redoublement année') ),
( '210', ((ATB,), ALL, ALL, ALL, ALL, ALL),
  (NAR, (ADM, AJ), NAR, REO, None, 'Le précédent ne peut pas être validé, réorientation') ),
( '220', ((ATB,), True, True, True, ALL, ALL),
  (ADM, (ADM,), ADJ, NEXT, None, 'Le jury valide le précédent') ),
( '230', ((ATB,), True, False, True, ALL, True),
  (ATT, (ADM, AJ), ADJ, NEXT, None, 'Le jury valide le précédent, pas moyenne gen., attente suivant') ),
( '240', ((ATB,), True, ALL, False, ALL, True),
  (ATB, (ADM, AJ), ADJ, NEXT, None, 'Le jury valide le précédent, pb barre UE, attente') ),
( '250', ((ATB,), False, ALL, ALL, ALL, True),
  (ATJ, (AJ,), ADJ, NEXT, None, 'Le jury valide le précédent, mais probleme assiduité.') ),
( '260', ((ATB,ATT), ALL, True, True, ALL, ALL),
  (ADJ, (), AJ, REDOANNEE, None, 'Le jury valide ce semestre, et fait recommencer le précédent.') ),
# Semestre prec. AJ (ajourné):
( '300', ((AJ,), True, False, ALL, ALL, ALL),
  (AJ, (), AJ, REDOANNEE, None, 'Echec de 2 semestres, redouble année') ),
( '310', ((AJ,), True, True, False, ALL, ALL),
  (AJ, (), AJ, REDOANNEE, None, 'Echec de 2 semestres, redouble année') ),
( '320', ((AJ,), False, ALL, ALL, ALL, ALL),
  (NAR, (), None, REO, None, 'Echec, pas assidu: réorientation') ),
( '330', ((AJ,), True, True, True, ALL, ALL),
  (ADM, (ADM,), None, REDOANNEE, None, 'Valide, mais manque le précédent: redouble') ),
# Décisions du jury:
( '400', ((ALL,), True, False, ALL, ALL, ALL),
  (ADJ, (ADM,CMP), None, NEXT, None, 'Le jury décide de valider') ),
( '410', ((ATT,ATB), True, False, ALL, ALL, ALL),
  (ADJ, (ADM,CMP), ADJ, NEXT, None, 'Le jury décide de valider ce semestre et le précédent') ),
( '420', ((ALL,), True, True, False, ALL, ALL),
  (ADJ, (ADM,CMP), None, NEXT, None, 'Le jury décide de valider') ),
( '430', ((ATT,ATB), True, True, False, ALL, ALL),
  (ADJ, (ADM,CMP), ADJ, NEXT, None, 'Le jury décide de valider ce semestre et le précédent') ),
( '450', ((ATT,ATB), False, False, True, ALL, True),
  (ATT, (ADM, AJ), ADJ, NEXT, None, 'Pb moy: attente, mais le jury valide le précédent') ),
# Semestres "décales" (REDOSEM)
( '500', ((None, ADM, ADC, ADJ,ATT,ATB), True, False, ALL, False, ALL),
  (AJ, (), None, REDOSEM, None, 'Pas moy: redouble ce semestre') ),
( '510', ((None, ADM, ADC, ADJ,ATT,ATB), True, True, False, False, ALL),
  (AJ, (), None, REDOSEM, None, 'Pas barre UE: redouble ce semestre') ),
( '520', ((None, ADM, ADC, ADJ,ATB,ATT), False, ALL, ALL, ALL, ALL),
  (AJ, (), None, REDOSEM, None, 'Pb assiduité: redouble ce semestre') ),
# Nouvelles regles avec plusieurs devenirs en semestres decales:
( '550', ((ATT,ATB), ALL, False, ALL, False, ALL),
  (AJ, (), None, RA_OR_RS, None, 'Deux semestres ratés, choix de recommencer le premier ou le second') ),
( '560', ((ATT,ATB), ALL, True, False, False, ALL),
  (AJ, (), None, RA_OR_RS, None, 'Deux semestres ratés, choix de recommencer le premier ou le second') ),
( '570', ((None,ADM,ADJ,ADC), ALL, False, True, False, ALL),
  (ATT, (), None, RS_OR_NEXT, None, 'Semestre raté, choix de redoubler le semestre ou de continuer pour éventuellement compenser.') ),
( '580', ((None,ADM,ADJ,ADC), ALL, ALL, False, False, ALL),
  (ATB, (), None, RS_OR_NEXT, None, 'Semestre raté, choix de redoubler ou de s\'en remettre au jury du semestre suivant.') ),
# Exclusion (art. 22): si precedent non valide et pas les barres dans le courant, on peut ne pas autoriser a redoubler:
# (le cas ATB est couvert plus haut)
( '600', ((AJ,ATT,NAR), True, False, ALL, ALL, ALL),
  (NAR, (), NAR, REO, None, 'Non autorisé à redoubler') ),
( '610', ((AJ,ATT,NAR), True, True, False, ALL, ALL),
  (NAR, (), NAR, REO, None, 'Non autorisé à redoubler') ),
)]
