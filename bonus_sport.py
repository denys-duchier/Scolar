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

def bonus_colmar(notes_sport, coefs):
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

