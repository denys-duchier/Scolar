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

"""Various HTML generation functions
"""

def horizontal_bargraph( value, mark ):
    """html drawing an horinzontal bar and a mark
    used to vizualize the relative level of a student
    """
    tmpl = """
    <span class="graph">
    <span class="bar" style="width: %(value)d%%;"></span>
    <span class="mark" style="left: %(mark)d%%; "></span>
    </span>
    """ 
    return tmpl % { 'value' : int(value), 'mark' : int(value) }

    
