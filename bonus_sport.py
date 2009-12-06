# -*- mode: python -*-
# -*- coding: iso8859-15 -*-

##############################################################################
#
# Gestion scolarite IUT
#
# Copyright (c) 2001 - 2006 Emmanuel Viennet.  All rights reserved.
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

def bonus_iutv(notes_sport, coefs):
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

def bonus_colmar(notes_sport, coefs):
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

def bonus_iutva(notes_sport, coefs):
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
