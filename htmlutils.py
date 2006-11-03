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
    return tmpl % { 'value' : int(value), 'mark' : int(mark) }


import listhistogram

def histogram_notes( notes ):
    "HTML code drawing histogram"
    bins, H = listhistogram.ListHistogram( notes, 21, minmax=(0,20) )
    D = ['<ul id="vhist-q-graph"><li class="vhist-qtr" id="vhist-q1"><ul>']
    left=5
    colwidth = 16 # must match #q-graph li.bar width in stylesheet
    hfactor = 95./max(H) # garde une marge de 5% pour l'esthetique
    for i in range(len(H)):
        if H[i] >= 0:
            x=left + i*(4+colwidth)
            heightpercent = H[i] * hfactor
            if H[i] > 0:
                nn = '<p>%d</p>' % H[i]
            else:
                nn = ''
            D.append('<li class="vhist-bar" style="left:%dpx;height:%f%%">%s<p class="leg">%d</p></li>'
                     % (x,heightpercent, nn, i))
    D.append('</ul></li></ul>')
    return '\n'.join(D)
