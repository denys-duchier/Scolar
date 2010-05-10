# -*- mode: python -*-
# -*- coding: iso8859-15 -*-

##############################################################################
#
# Gestion scolarite IUT
#
# Copyright (c) 2001 - 2010 Emmanuel Viennet.  All rights reserved.
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

"""Système de notification par mail des excès d'absences
(see ticket #147)
"""


from notesdb import *
from sco_utils import *
from notes_log import log
import sco_groups
from scolars import format_nom, format_prenom, format_sexe, format_lycee
from ZAbsences import getAbsSemEtud

def abs_notify(context, etudid, nbabs, nbabsjust):
    """Given new counts of absences, check if notifications are requested and send them.
    """
    pass # not implemented

