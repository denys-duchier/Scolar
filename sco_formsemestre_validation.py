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

"""Semestres: valisation semestre et UE dans parcours
"""
import urllib, time, datetime

from notesdb import *
from sco_utils import *
from notes_log import log
from notes_table import *

import sco_parcours_dut

_scolar_formsemestre_validation_editor = EditableTable(
    'scolar_formsemestre_validation',
    'formsemestre_validation_id',
    ('etudid', 'formsemestre_id', 'ue_id', 'code', 'event_date'),
    output_formators = { 'event_date' : DateISOtoDMY },
    input_formators  = { 'event_date' : DateDMYtoISO }
)


def formsemestre_validate_sem(cnx, formsemestre_id, etudid, code):
    "Ajoute ou change validation semestre"
    # check if exists
    # update or insert
    XXX
    
def formsemestre_validate_ue(cnx, formsemestre_id, etudid, ue_id, code):
    "Ajoute ou change validation UE"
    # check if exists
    # update or insert
    XXX

def formsemestre_get_etud_validation(cnx, formsemestre_id, etudid):
    "(code, { ue_id : code } )"
    XXX



