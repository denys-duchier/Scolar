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
#   Emmanuel Viennet      emmanuel.viennet@gmail.com
#
##############################################################################

"""Generation bulletins de notes: exemple minimal pour les programmeurs
"""

# Quelques modules ScoDoc utiles:
from sco_pdf import *
import sco_preferences
from notes_log import log
import sco_bulletins_generator
import sco_bulletins_standard

class BulletinGeneratorExample(sco_bulletins_standard.BulletinGeneratorStandard):
    """Un exemple simple de bulletin de notes en version PDF seulement.
    Part du bulletin standard et red�fini la partie centrale.
    """
    description = 'exemple (ne pas utiliser)' # la description doit �tre courte: elle apparait dans le menu de param�trage
    supported_formats = [ 'pdf' ] # indique que ce g�n�rateur ne peut produire que du PDF (la version web sera donc celle standard de ScoDoc)

    # En g�n�ral, on veut d�finir un format de table sp�cial, sans changer le reste (titre, pied de page).
    # Si on veut changer le reste, surcharger les m�thodes:
    #  .bul_title_pdf(self)  : partie haute du bulletin
    #  .bul_part_below(self, format='') : infos sous la table
    #  .bul_signatures_pdf(self) : signatures

    def bul_table(self, format=''):
        """D�fini la partie centrale de notre bulletin PDF.
        Doit renvoyer une liste d'objets PLATYPUS
        """
        assert format == 'pdf' # garde fou
        return [
            Paragraph( SU("L'�tudiant %(nomprenom)s a une moyenne g�n�rale de %(moy_gen)s" % self.infos),
                       self.CellStyle # un style pdf standard
                       )
            ]

# D�clarer votre classe � ScoDoc:
sco_bulletins_generator.register_bulletin_class(BulletinGeneratorExample)

