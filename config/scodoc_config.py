# -*- mode: python -*-
# -*- coding: iso8859-15 -*-

#
# Configuration globale de ScoDoc
#
# Ce fichier est peu utilis�: la plupart des r�glages sont stoqu�s en base de donn�e
# et accessibles via le web, ou bien g�r�s comme des propri�t�s Zope.
#
# Il y a aussi des r�glages dans sco_utils.py, mais ils n�cessite souvent de comprendre
# le code qui les utilise pour ne pas faire d'erreur: attention.


class CFG :
    pass

CONFIG = CFG()


#
#   ------------- Documents PDF -------------
#
CONFIG.SCOLAR_FONT = 'Helvetica'
CONFIG.SCOLAR_FONT_SIZE = 10
CONFIG.SCOLAR_FONT_SIZE_FOOT = 6

# Pied de page PDF : un format Python, %(xxx)s est remplac� par la variable xxx.
# Les variables d�finies sont:
#   day   : Day of the month as a decimal number [01,31]
#   month : Month as a decimal number [01,12].
#   year  : Year without century as a decimal number [00,99].
#   Year  : Year with century as a decimal number.
#   hour  : Hour (24-hour clock) as a decimal number [00,23].
#   minute: Minute as a decimal number [00,59].
#   
#   server_url: URL du serveur ScoDoc
#   scodoc_name: le nom du logiciel (ScoDoc actuellement, voir VERSION.py)
        
CONFIG.DEFAULT_PDF_FOOTER_TEMPLATE = "Edit� par %(scodoc_name)s le %(day)s/%(month)s/%(year)s � %(hour)sh%(minute)s sur %(server_url)s"



#
#   ------------- Calcul bonus modules optionnels (sport, culture...) -------------
#
from bonus_sport import *

CONFIG.compute_bonus = bonus_iutv

#
#   ------------- Capitalisation des UEs -------------
# Deux �coles:
#   - r�gle "DUT": capitalisation uniquement des UE obtenues avec moyenne UE >= 10 ET des de toutes les UE
#                   des semestres valid�s (ADM, ADC, AJ). (conforme � l'arr�t� d'ao�t 2005
#
#   - r�gle "LMD": capitalisation uniquement des UE avec moy. > 10

CONFIG.CAPITALIZE_ALL_UES = True # si vrai, capitalise toutes les UE des semestres valid�s (r�gle "LMD").
