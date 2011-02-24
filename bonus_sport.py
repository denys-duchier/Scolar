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
#   Emmanuel Viennet      emmanuel.viennet@viennet.net
#
##############################################################################

from operator import mul
import pprint

def bonus_iutv(notes_sport, coefs, infos=None):
    """Calcul bonus modules optionels (sport, culture), r�gle IUT Villetaneuse

    Les �tudiants de l'IUT peuvent suivre des enseignements optionnels
    de l'Universit� Paris 13 (sports, musique, deuxi�me langue,
    culture, etc) non rattach�s � une unit� d'enseignement. Les points
    au-dessus de 10 sur 20 obtenus dans chacune des mati�res
    optionnelles sont cumul�s et 5% de ces points cumul�s s'ajoutent �
    la moyenne g�n�rale du semestre d�j� obtenue par l'�tudiant.
    """
    sumc = sum(coefs) # assumes sum. coefs > 0
    note_sport = sum(map(mul, notes_sport, coefs)) / sumc # moyenne pond�r�e
    bonus = sum( [ (x - 10) / 20. for x in notes_sport if x > 10 ])
    return bonus

def bonus_colmar(notes_sport, coefs, infos=None):
    """Calcul bonus modules optionels (sport, culture), r�gle IUT Colmar.

    Les �tudiants de l'IUT peuvent suivre des enseignements optionnels
    de l'U.H.A.  (sports, musique, deuxi�me langue, culture, etc) non
    rattach�s � une unit� d'enseignement. Les points au-dessus de 10
    sur 20 obtenus dans chacune des mati�res optionnelles sont cumul�s
    dans la limite de 10 points. 5% de ces points cumul�s s'ajoutent �
    la moyenne g�n�rale du semestre d�j� obtenue par l'�tudiant.
    
    """
    # les coefs sont ignor�s
    points = sum( [ x - 10 for x in notes_sport if x > 10 ])
    points = min( 10, points) # limite total � 10
    bonus = points / 20. # 5%
    return bonus

def bonus_iutva(notes_sport, coefs, infos=None):
    """Calcul bonus modules optionels (sport, culture), r�gle IUT Ville d'Avray

    Les �tudiants de l'IUT peuvent suivre des enseignements optionnels
    de l'Universit� Paris 10 (C2I) non rattach�s � une unit� d'enseignement.
    Si la note est >= 10 et < 12, bonus de 0.1 point
    Si la note est >= 12 et < 16, bonus de 0.2 point
    Si la note est >= 16, bonus de 0.3 point
    Ce bonus s'ajoute � la moyenne g�n�rale du semestre d�j� obtenue par
    l'�tudiant.
    """
    sumc = sum(coefs) # assumes sum. coefs > 0
    note_sport = sum(map(mul, notes_sport, coefs)) / sumc # moyenne pond�r�e
    if note_sport >= 16.0:
        return 0.3
    if note_sport >= 12.0:
        return 0.2
    if note_sport >= 10.0:
        return 0.1
    return 0

def bonus_iut1grenoble_v0(notes_sport, coefs, infos=None):
    """Calcul bonus sport IUT Grenoble sr moyenne g�n�rale

    La note de sport de nos �tudiants va de 0 � 5 points. 
    Chaque point correspond � un % qui augmente la moyenne de chaque UE et la moyenne g�n�rale.
    Par exemple : note de sport 2/5 : chaque UE sera augment�e de 2%, ainsi que la moyenne g�n�rale.

    Calcul ici du bonus sur moyenne g�n�rale et moyennes d'UE non capitalis�es.
    """
    #open('/tmp/log','a').write( '\n---------------\n' + pprint.pformat(infos) + '\n' )
    # les coefs sont ignor�s
    # notes de 0 � 5
    points = sum( [ x for x in notes_sport ])
    factor = (points/4.)/100.
    bonus = infos['moy'] * factor
    # Modifie les moyennes de toutes les UE:
    for ue_id in infos['moy_ues']:
        ue_status = infos['moy_ues'][ue_id]
        if ue_status['sum_coefs'] > 0:
            # modifie moyenne UE ds semestre courant
            ue_status['cur_moy_ue'] = ue_status['cur_moy_ue'] * (1. + factor)
            if not ue_status['is_capitalized']:
                # si non capitalisee, modifie moyenne prise en compte
                ue_status['moy'] = ue_status['cur_moy_ue']
    
        #open('/tmp/log','a').write( pprint.pformat(ue_status) + '\n\n' )    
    return bonus
