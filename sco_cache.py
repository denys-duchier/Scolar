# -*- mode: python -*-
# -*- coding: iso8859-15 -*-

##############################################################################
#
# Gestion scolarite IUT
#
# Copyright (c) 2001 - 2008 Emmanuel Viennet.  All rights reserved.
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

"""Cache simple par etudiant

"""

from notes_log import log
import thread

# Cache donnees sur un etudiant (compte abs, arbre intervalles...)
class simpleCache:
    def __init__(self):
        self.inval_cache()
    
    def inval_cache(self, key=None):
        if key:
            if key in self.cache:
                del self.cache[key]
        else:
            # clear all entries
            self.cache = {} # key : data
        
    def set(self, key, data):
        self.cache[key] = data

    def get(self, key):
        """returns None if not in cache"""
        return self.cache.get(key, None)
