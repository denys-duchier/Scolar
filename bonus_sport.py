# -*- mode: python -*-
# -*- coding: utf-8 -*-

##############################################################################
#
# Gestion scolarite IUT
#
# Copyright (c) 2001 - 2014 Emmanuel Viennet.  All rights reserved.
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
    """Calcul bonus sport IUT Grenoble sur la moyenne générale
    
    La note de sport de nos étudiants va de 0 à 5 points. 
    Chaque point correspond à un % qui augmente la moyenne de chaque UE et la moyenne générale.
    Par exemple : note de sport 2/5 : chaque UE sera augmentée de 2%, ainsi que la moyenne générale.
    
    Calcul ici du bonus sur moyenne générale et moyennes d'UE non capitalisées.
    """
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

# Bonus sport IUT Tours
def bonus_tours(notes_sport, coefs, infos=None):
    """Calcul bonus sport & culture IUT Tours sur moyenne generale

    La note de sport & culture de nos etudiants va de 0 ? 0,5 points.
    Le bonus est applique sur la moyenne generale.
    """
    sumc = sum(coefs) # assumes sum. coefs > 0
    moy_notes = sum(map(mul, notes_sport, coefs)) / sumc # moyenne ponderee sur 20
    bonus = moy_notes / 40 # bonus sur 0,5
    return bonus

def bonus_iutr(notes_sport, coefs, infos=None):
    """Calcul du bonus , regle de l'IUT de Roanne (contribuée par Raphael C., nov 2012)

       Le bonus est compris entre 0 et 0.35 point.
       cette procédure modifie la moyenne de chaque UE capitalisable.

    """
    #modifie les moyennes de toutes les UE:
    # le bonus est le minimum entre 0.35 et la somme de toutes les bonifs
    bonus = min(0.35,sum([x for x in notes_sport]))    
    for ue_id in infos['moy_ues']:
        #open('/tmp/log','a').write( ue_id +  infos['moy_ues'] + '\n\n' )    
        ue_status = infos['moy_ues'][ue_id]
        if ue_status['sum_coefs'] > 0:
            #modifie moyenne UE dans semestre courant
            ue_status['cur_moy_ue'] = ue_status['cur_moy_ue'] + bonus
            if not ue_status['is_capitalized']:
                ue_status['moy'] = ue_status['cur_moy_ue']
    return bonus

def bonus_iutam(notes_sport, coefs, infos=None):
    """Calcul bonus modules optionels (sport), regle IUT d'Amiens.
    Les etudiants de l'IUT peuvent suivre des enseignements optionnels.
    Si la note est de 10.00 a 10.49 -> 0.50% de la moyenne
    Si la note est de 10.50 a 10.99 -> 0.75%
    Si la note est de 11.00 a 11.49 -> 1.00%
    Si la note est de 11.50 a 11.99 -> 1.25%
    Si la note est de 12.00 a 12.49 -> 1.50%
    Si la note est de 12.50 a 12.99 -> 1.75%
    Si la note est de 13.00 a 13.49 -> 2.00%
    Si la note est de 13.50 a 13.99 -> 2.25%
    Si la note est de 14.00 a 14.49 -> 2.50%
    Si la note est de 14.50 a 14.99 -> 2.75%
    Si la note est de 15.00 a 15.49 -> 3.00%
    Si la note est de 15.50 a 15.99 -> 3.25%
    Si la note est de 16.00 a 16.49 -> 3.50%
    Si la note est de 16.50 a 16.99 -> 3.75%
    Si la note est de 17.00 a 17.49 -> 4.00%
    Si la note est de 17.50 a 17.99 -> 4.25%
    Si la note est de 18.00 a 18.49 -> 4.50%
    Si la note est de 18.50 a 18.99 -> 4.75%
    Si la note est de 19.00 a 20.00 -> 5.00%
    Ce bonus s'ajoute a la moyenne generale du semestre de l'etudiant.
    """
    # une seule note
    note_sport = notes_sport[0]
    if note_sport < 10.:
        return 0
    prc = min( (int(2*note_sport-20.)+2)*0.25, 5 )
    bonus = infos['moy'] * prc/100
    return bonus

def bonus_saint_etienne(notes_sport, coefs, infos=None):
    """IUT de Saint-Etienne (jan 2014)
    Nous avons différents types de bonification
    bonfication Sport / Associations
    coopératives de département / Bureau Des Étudiants 
    / engagement citoyen / Langues optionnelles
    Nous ajoutons sur le bulletin une bonification qui varie entre 0,1 et 0,3 ou 0,35 pour chaque item
    la bonification totale ne doit pas excéder les 0,6 point.
    Sur le bulletin nous ne mettons pas une note sur 20 mais directement les bonifications.


    Dans ScoDoc: on a déclarer une UE "sport&culture" dans laquelle on aura des modules
    pour chaque activité (Sport, Associations, ...)
    avec à chaque fois une note (ScoDoc l'affichera comme une note sur 20, mais en fait ce sera la
    valeur de la bonification: entrer 0,1/20 signifiera un bonus de 0,1 point la moyenne générale)
    """
    bonus = min(0.6,sum([x for x in notes_sport]))  # plafonnement à 0.6 points
    
    return bonus
    
def bonus_demo(notes_sport, coefs, infos=None):
    """Fausse fonction "bonus" pour afficher les informations disponibles
    et aider les développeurs.
    Les informations sont placées dans le fichier /tmp/scodoc_bonus.log    
    qui est ECRASE à chaque appel.
    *** Ne pas utiliser en production !!! ***
    """
    f = open('/tmp/scodoc_bonus.log','w') # mettre 'a' pour ajouter en fin
    f.write( '\n---------------\n' + pprint.pformat(infos) + '\n' )
    # Statut de chaque UE
    # for ue_id in infos['moy_ues']:
    #    ue_status = infos['moy_ues'][ue_id]
    #   #open('/tmp/log','a').write( pprint.pformat(ue_status) + '\n\n' )    
    
    return 0.
