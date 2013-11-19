# -*- mode: python -*-
# -*- coding: utf-8 -*-

##############################################################################
#
# Gestion scolarite IUT
#
# Copyright (c) 2001 - 2013 Emmanuel Viennet.  All rights reserved.
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

"""Gestion rudimentaire de cache pour Notes


  NOTA: inutilisable dans une instance Zope (can't pickle functions)
"""

from notes_log import log

class CacheFunc:
    """gestion rudimentaire de cache pour une fonction
    func doit etre sans effet de bord, et sans arguments nommés
    """
    def __init__(self, func):
        log('new CacheFunc for %s' % str(func))
        self.func = func
        self.cache = {} # { arguments : function result }
    
    def __call__(self, *args):
        if self.cache.has_key(args):
            #log('cache hit %s' % str(args))
            return self.cache[args]
        else:
            val = self.func(*args)
            self.cache[args] = val
            log('caching %s(%s)' % (str(self.func),str(args)))
            return val
    
    def inval_cache_entry(self, *args): #>
        "expire cache for these args"
        log('inval_cache_entry %s(%s)' % (str(self.func),str(args))) #>
        del self.cache[args]

    def inval_cache(self): #>
        "clear whole cache"
        log('inval_cache %s(%s)' % (str(self.func),str(args))) #>
        self.cache = {}

