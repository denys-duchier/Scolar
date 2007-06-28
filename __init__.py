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

import ZScolar, ZNotes

__version__ = '0.0.0'


def initialize(context):
    """initialize the Scolar products"""

    # --- ZScolars
    context.registerClass(
        ZScolar.ZScolar,
	constructors = (
	    ZScolar.manage_addZScolarForm, # this is called when
                                    # someone adds the product
	    ZScolar.manage_addZScolar
	),
        icon = 'icons/sco_icon.png'
    )

    #context.registerHelp()
    #context.registerHelpTitle("ZScolar")

    # --- ZNotes
    context.registerClass(
        ZNotes.ZNotes,
	constructors = (
	    ZNotes.manage_addZNotesForm, # this is called when
                                    # someone adds the product
	    ZNotes.manage_addZNotes
	),
      icon = 'icons/notes_icon.png'
    )

    #context.registerHelp()
    #context.registerHelpTitle("ZNotes")
    
