# -*- mode: python -*-
# -*- coding: utf-8 -*-

##############################################################################
#
# Gestion scolarite IUT
#
# Copyright (c) 2001 - 2015 Emmanuel Viennet.  All rights reserved.
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

"""Une classe "vecteur" pour les formules utilisateurs de calcul des moyennes
"""

from sets import Set
import operator
import traceback
from types import FloatType, IntType, LongType, StringType

from sco_utils import *
from notes_log import log

class NoteVector:
    """Vecteur de notes (ou coefficients) utilisé pour les formules définies par l'utilisateur.
    Les éléments sont accessibles soit par index v[i], soit par leur nom v['nom'] s'il en ont un.
    Les éléments sont toujours numériques (float). Les valeurs non numériques ('NI', ...) sont
    considérées comme nulles (0.0).
    """
    def __init__(self, *args, **kwargs):
        if args:
            self.v = map( float, args ) # cast to list of float
        elif 'v' in kwargs:
            v = kwargs['v']
            if not isinstance(v, NoteVector):
                # replace all non-numeric values by zeroes: (formulas should check cmask !)
                for i in range(len(v)):
                    try:
                        v[i] = float(v[i])
                    except:
                        v[i] = 0.
            self.v = v
        else:
            self.v = []
        self.name_idx = {} # { name : index in vector }
    
    def __len__(self):
        return len(self.v)
    
    def __getitem__(self,i):
        try:
            return self.v[i]
        except:
            if type(i) == StringType:
                return self.v[self.name_idx[i]]
            else:
                raise IndexError('index %s out of range' % i)
    
    def append(self, value, name=None):
        """Append a value to the vector."""
        try:
            v = float(value)
        except:
            v = 0.
        self.v.append(v)
        if name:
            self.name_idx[name] = len(self.v) - 1
        
    def __repr__(self):
        return "NVector(%s, name_idx=%s)" % (str(self.v), self.name_idx)
        
    def __add__(self, x):
        return binary_op(self.v, x, operator.add)
    __radd__ = __add__        
    def __sub__(self, x):
        return binary_op(self.v, x, operator.sub)
    def __rsub__(self, x):
        return binary_op(x, self.v, operator.sub)
    def __mul__(self, x):
        return binary_op(self.v, x, operator.mul)
    __rmul__ = __mul__
    def __div__(self, x):
        return binary_op(self.v, x, operator.div)
    def __rdiv__(self, x):
        return binary_op(x, self.v, operator.div)

def isScalar(x):
    return isinstance(x, FloatType) or isinstance(x, IntType) or isinstance(x, LongType)

def binary_op(x, y, op):
    if isScalar(x):
        if isScalar(y):
            x, y = [x], [y]
        else:
            x = [x]*len(y)
    if isScalar(y):
        y = [y]*len(x)
    
    if len(x) != len(y):
        raise ValueError("vectors sizes don't match")
    
    return NoteVector(v=[ op(a,b) for (a,b) in zip(x,y) ])

def dot(u,v):
    """Dot product between 2 lists or vectors"""
    return sum([ x*y for (x,y) in zip(u,v) ])

def ternary_op(cond, a, b):    
    if cond:
        return a
    else:
        return b

def geometrical_mean(v, w=None):
    """Geometrical mean of v, with optional weights w"""
    if w is None:
        return pow(reduce(operator.mul, v), 1./len(v))
    else:
        if len(w) != len(v):
            raise ValueError("vectors sizes don't match")
        vw = [ pow(x,y) for (x,y) in zip(v,w) ]
        return pow(reduce(operator.mul, vw), 1./sum(w))

# Les builtins autorisées dans les formules utilisateur:
formula_builtins = {
    'V' : NoteVector,
    'dot' : dot, 
    'max' : max,
    'min' : min,
    'abs' : abs,
    'cmp' : cmp,
    'len' : len,
    'map' : map,
    'pow' : pow,
    'reduce' : reduce,
    'round' : round,
    'sum' : sum,
    'ifelse'  : ternary_op,
    'geomean' : geometrical_mean
}

# v = NoteVector(1,2)
# eval("max(4,5)", {'__builtins__': formula_builtins, {'x' : 1, 'v' : NoteVector(1,2) }, {})

def eval_user_expression(context, expression, variables):
    """Evalue l'expression (formule utilisateur) avec les variables (dict) donnÃ©es.
    """
    variables['__builtins__'] = formula_builtins
    # log('Evaluating %s with %s' % (expression, variables))
    # may raise exception if user expression is invalid
    return eval( expression, variables, {} ) # this should be safe
