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
    """Calcul bonus modules optionels (sport, culture), règle IUT Villetaneuse

    Les étudiants de l'IUT peuvent suivre des enseignements optionnels
    de l'Université Paris 13 (sports, musique, deuxième langue,
    culture, etc) non rattachés à une unité d'enseignement. Les points
    au-dessus de 10 sur 20 obtenus dans chacune des matières
    optionnelles sont cumulés et 5% de ces points cumulés s'ajoutent à
    la moyenne générale du semestre déjà obtenue par l'étudiant.
    """
    #open('/tmp/log','a').write( pprint.pformat(infos) + '\n\n' )    
    sumc = sum(coefs) # assumes sum. coefs > 0
    note_sport = sum(map(mul, notes_sport, coefs)) / sumc # moyenne pondérée
    bonus = sum( [ (x - 10) / 20. for x in notes_sport if x > 10 ])
    return bonus

def bonus_colmar(notes_sport, coefs, infos=None):
    """Calcul bonus modules optionels (sport, culture), règle IUT Colmar.

    Les étudiants de l'IUT peuvent suivre des enseignements optionnels
    de l'U.H.A.  (sports, musique, deuxième langue, culture, etc) non
    rattachés à une unité d'enseignement. Les points au-dessus de 10
    sur 20 obtenus dans chacune des matières optionnelles sont cumulés
    dans la limite de 10 points. 5% de ces points cumulés s'ajoutent à
    la moyenne générale du semestre déjà obtenue par l'étudiant.
    
    """
    # les coefs sont ignorés
    points = sum( [ x - 10 for x in notes_sport if x > 10 ])
    points = min( 10, points) # limite total à 10
    bonus = points / 20. # 5%
    return bonus

def bonus_iutva(notes_sport, coefs, infos=None):
    """Calcul bonus modules optionels (sport, culture), règle IUT Ville d'Avray

    Les étudiants de l'IUT peuvent suivre des enseignements optionnels
    de l'Université Paris 10 (C2I) non rattachés à une unité d'enseignement.
    Si la note est >= 10 et < 12, bonus de 0.1 point
    Si la note est >= 12 et < 16, bonus de 0.2 point
    Si la note est >= 16, bonus de 0.3 point
    Ce bonus s'ajoute à la moyenne générale du semestre déjà obtenue par
    l'étudiant.
    """
    sumc = sum(coefs) # assumes sum. coefs > 0
    note_sport = sum(map(mul, notes_sport, coefs)) / sumc # moyenne pondérée
    if note_sport >= 16.0:
        return 0.3
    if note_sport >= 12.0:
        return 0.2
    if note_sport >= 10.0:
        return 0.1
    return 0

def bonus_iut1grenoble_v0(notes_sport, coefs, infos=None):
    """Calcul bonus sport IUT Grenoble sr moyenne générale

    La note de sport de nos étudiants va de 0 à 5 points. 
    Chaque point correspond à un % qui augmente la moyenne de chaque UE et la moyenne générale.
    Par exemple : note de sport 2/5 : chaque UE sera augmentée de 2%, ainsi que la moyenne générale.

    Calcul ici du bonus sur moyenne générale et moyennes d'UE non capitalisées.
    """
    #open('/tmp/log','a').write( '\n---------------\n' + pprint.pformat(infos) + '\n' )
    # les coefs sont ignorés
    # notes de 0 à 5
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

def bonus_lille(notes_sport, coefs, infos=None):
    """calcul bonus modules optionels (sport, culture), règle IUT Villeneuve d'Ascq

    Les étudiants de l'IUT peuvent suivre des enseignements optionnels
    de l'Université Lille 1 (sports,etc) non rattachés à une unité d'enseignement. Les points
    au-dessus de 10 sur 20 obtenus dans chacune des matières
    optionnelles sont cumulés et 4% (2% avant aout 2010) de ces points cumulés s'ajoutent à
    la moyenne générale du semestre déjà obtenue par l'étudiant.
    """
    sumc = sum(coefs) # assumes sum. coefs > 0
    note_sport = sum(map(mul, notes_sport, coefs)) / sumc # moyenne pondérée
    if (infos['sem']['date_debut_iso'] > '2010-08-01'):  # changement de regle en aout 2010.
        return sum( [ (x - 10) /25. for x in notes_sport if x > 10 ])
    return sum( [ (x - 10) /50. for x in notes_sport if x > 10 ])

# Fonction Le Havre, par Dom. Soud.
def bonus_iutlh(notes_sport, coefs, infos=None):
    """Calcul bonus sport IUT du Havre sur moyenne générale et UE

    La note de sport de nos étudiants va de 0 à 20 points. 
	          m2=m1*(1+0.005*((10-N1)+(10-N2))
   m2 : Nouvelle moyenne de l'unité d'enseignement si note de sport et/ou de langue supérieure à 10
   m1 : moyenne de l'unité d'enseignement avant bonification
   N1 : note de sport si supérieure à 10
   N2 : note de seconde langue si supérieure à 10
    Par exemple : sport 15/20 et langue 12/20 : chaque UE sera multipliée par 1+0.005*7, ainsi que la moyenne générale.
    Calcul ici de la moyenne générale et moyennes d'UE non capitalisées.
    """
    #open('/tmp/log','a').write( '\n---------------\n' + pprint.pformat(infos) + '\n' )
    # les coefs sont ignorés
    points = sum( [ x - 10 for x in notes_sport if x > 10 ])
    points = min( 10, points) # limite total à 10
    factor = (1. + (0.005 * points))
	# bonus nul puisque les moyennes sont directement modifiées par factor
    bonus = 0
    # Modifie la moyenne générale
    infos['moy'] = infos['moy'] * factor
    # Modifie les moyennes de toutes les UE:
    for ue_id in infos['moy_ues']:
        ue_status = infos['moy_ues'][ue_id]
        if ue_status['sum_coefs'] > 0:
            # modifie moyenne UE ds semestre courant
            ue_status['cur_moy_ue'] = ue_status['cur_moy_ue'] * factor
            if not ue_status['is_capitalized']:
                # si non capitalisee, modifie moyenne prise en compte
                ue_status['moy'] = ue_status['cur_moy_ue']  

        #open('/tmp/log','a').write( pprint.pformat(ue_status) + '\n\n' )    
    return bonus
