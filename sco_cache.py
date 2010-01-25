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
import thread, time

# Cache data
class simpleCache:
    def __init__(self):
        self.inval_cache() #>
    
    def inval_cache(self, key=None): #>
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

class expiringCache(simpleCache):
    """A simple cache wich cache data for a most "duration" seconds.

    This is used for users (whch may be updated from external 
    information systems)
    """
    def __init__(self, max_validity=60):
        simpleCache.__init__(self)
        self.max_validity = max_validity
    
    def set(self, key, data):
        simpleCache.set(self, key, (data, time.time()))
    
    def get(self,key):
        info = simpleCache.get(self, key)
        if info:
            data, t = info
            if time.time() - t < self.max_validity:
                return data
            else:
                # expired
                self.inval_cache(key) #>
                return None
        else:
            return None # not in cache

