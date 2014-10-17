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

from ZScolar import ZScolar, manage_addZScolarForm, manage_addZScolar
# from ZNotes  import ZNotes, manage_addZNotesForm, manage_addZNotes

from ZScoDoc import ZScoDoc, manage_addZScoDoc

# from sco_zope import *
# from notes_log import log
# log.set_log_directory( INSTANCE_HOME + '/log' )


__version__ = '1.0.0'

    
def initialize(context):
    """initialize the Scolar products"""
    # called at each startup (context is a ProductContext instance, basically useless)
    
    # --- ZScolars
    context.registerClass(
        ZScolar,
	constructors = (
	    manage_addZScolarForm, # this is called when someone adds the product
	    manage_addZScolar
	),
        icon = 'static/icons/sco_icon.png'
    )

    #context.registerHelp()
    #context.registerHelpTitle("ZScolar")

    # --- ZScoDoc
    context.registerClass(
        ZScoDoc,
	constructors = (
	    manage_addZScoDoc,
	),
        icon = 'static/icons/sco_icon.png'
    )


    # --- ZNotes
    #context.registerClass(
    #   ZNotes,
    #	constructors = (
    #	    manage_addZNotesForm,                                   
    #	    manage_addZNotes
    #	),
    #  icon = 'static/icons/notes_icon.png'
    #)

    #context.registerHelp()
    #context.registerHelpTitle("ZNotes")
    
