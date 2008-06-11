# -*- mode: python -*-
# -*- coding: iso8859-15 -*-

#
# Configuration globale de ScoDoc
#
# Ce fichier est peu utilisé: la plupart des réglages sont stoqués en base de donnée
# et accessibles via le web, ou bien gérés comme des propriétés Zope.
#
# Il y a aussi des réglages dans sco_utils.py, mais ils nécessite souvent de comprendre
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

# Pour pieds de pages Procès verbaux:
#  (markup leger reportlab supporté, par ex. <b>blah blah</b>)
CONFIG.INSTITUTION_NAME="<b>Institut Universitaire de Technologie - Université Paris 13</b>"
CONFIG.INSTITUTION_ADDRESS="Web <b>www.iutv.univ-paris13.fr</b> - 99 avenue Jean-Baptiste Clément - F 93430 Villetaneuse"

CONFIG.INSTITUTION_CITY="Villetaneuse"

# Le logo en pied des PV
CONFIG.PV_FONTNAME = 'Times-Roman'
# Taille du l'image logo: largeur/hauteur  (ne pas oublier le . !!!)
CONFIG.LOGO_FOOTER_ASPECT = 326/96. # W/H    XXX provisoire: utilisera PIL pour connaitre la taille de l'image
CONFIG.LOGO_FOOTER_HEIGHT = 10 # taille dans le document en millimetres

CONFIG.LOGO_HEADER_ASPECT = 744 / 374. # XXX logo IUTV
CONFIG.LOGO_HEADER_HEIGHT = 15 # taille verticale dans le document en millimetres

# Marges additionnelles des PV individuels PDF,
#   en mm, dans l'ordre (left,top,right, bottom):
CONFIG.INDIVIDUAL_LETTER_MARGINS = (0,0,0,0)

# Pied de page PDF : un format Python, %(xxx)s est remplacé par la variable xxx.
# Les variables définies sont:
#   day   : Day of the month as a decimal number [01,31]
#   month : Month as a decimal number [01,12].
#   year  : Year without century as a decimal number [00,99].
#   Year  : Year with century as a decimal number.
#   hour  : Hour (24-hour clock) as a decimal number [00,23].
#   minute: Minute as a decimal number [00,59].
#   
#   server_url: URL du serveur ScoDoc
#   scodoc_name: le nom du logiciel (ScoDoc actuellement, voir VERSION.py)
        
CONFIG.DEFAULT_PDF_FOOTER_TEMPLATE = "Edité par %(scodoc_name)s le %(day)s/%(month)s/%(year)s à %(hour)sh%(minute)s sur %(server_url)s"



#
#   ------------- Calcul bonus modules optionnels (sport, culture...) -------------
#
from bonus_sport import *

CONFIG.compute_bonus = bonus_iutv

#
#   ------------- Capitalisation des UEs -------------
# Deux écoles:
#   - règle "DUT": capitalisation des UE obtenues avec moyenne UE >= 10 ET de toutes les UE
#                   des semestres validés (ADM, ADC, AJ). (conforme à l'arrêté d'août 2005)
#
#   - règle "LMD": capitalisation uniquement des UE avec moy. > 10

CONFIG.CAPITALIZE_ALL_UES = True # si vrai, capitalise toutes les UE des semestres validés (règle "LMD").
