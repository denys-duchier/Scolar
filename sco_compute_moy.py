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

"""Calcul des moyennes de module
"""

from sets import Set
import operator
import traceback
from types import FloatType, IntType, LongType

from sco_utils import *
from notes_log import log, sendAlarm
from notes_table import *
import sco_groups

class NoteVector:
    """Vecteur de notes (ou coefficients) utilisé pour les formules définies par l'utilisateur.
    """
    def __init__(self, *args, **kwargs):
        if args:
            self.v = map( float, args ) # cast to list of float
        elif 'v' in kwargs:
            self.v = kwargs['v']
    
    def __len__(self):
        return len(self.v)
    
    def __getitem__(self,i):
        return self.v[i]
    
    def __repr__(self):
        return "NVector(%s)" % str(self.v)
        
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
    'if'  : ternary_op,
    'geomean' : geometrical_mean
}

# v = NoteVector(1,2)
# eval("max(4,5)", {'__builtins__': formula_builtins, {'x' : 1, 'v' : NoteVector(1,2) }, {})

def eval_user_expression(context, expression, notes, coefs, cmask ):
    envir = { '__builtins__': formula_builtins,
              'cmask' : NoteVector(v=cmask),
              'notes' : NoteVector(v=notes), 
              'coefs' : NoteVector(v=coefs) 
              }
    # may raise exception if user expression is invalid
    return eval( expression, envir, {} ) # this should be safe

def moduleimpl_has_expression(context, mod):
    "True if we should use a user-defined expression"
    expr = mod['computation_expr']
    if not expr:
        return False
    expr = expr.strip()
    if not expr or expr[0] == '#':
        return False
    return True

def do_moduleimpl_moyennes(context, moduleimpl_id):
    """Retourne dict { etudid : note_moyenne } pour tous les etuds inscrits
    à ce module, la liste des evaluations "valides" (toutes notes entrées
    ou en attente), et att (vrai s'il y a des notes en attente dans ce module).
    La moyenne est calculée en utilisant les coefs des évaluations.
    Les notes NEUTRES (abs. excuses) ne sont pas prises en compte.
    Les notes ABS sont remplacées par des zéros.
    S'il manque des notes et que le coef n'est pas nul,
    la moyenne n'est pas calculée: NA
    Ne prend en compte que les evaluations où toutes les notes sont entrées.
    Le résultat est une note sur 20.
    """
    M = context.do_moduleimpl_list(args={ 'moduleimpl_id' : moduleimpl_id })[0]
    etudids = context.do_moduleimpl_listeetuds(moduleimpl_id) # tous, y compris demissions
    # Inscrits au semestre (pour traiter les demissions):
    inssem_set = Set( [x['etudid'] for x in
                       context.do_formsemestre_inscription_listinscrits(M['formsemestre_id'])])
    insmod_set = inssem_set.intersection(etudids) # inscrits au semestre et au module
    evals = context.do_evaluation_list(args={ 'moduleimpl_id' : moduleimpl_id })
    user_expr = moduleimpl_has_expression(context, M)
    attente = False
    # recupere les notes de toutes les evaluations
    for e in evals:
        e['nb_inscrits'] = len(
            sco_groups.do_evaluation_listeetuds_groups(context, e['evaluation_id'],
                                                       getallstudents=True))
        NotesDB = context._notes_getall(e['evaluation_id']) # toutes, y compris demissions
        # restreint aux étudiants encore inscrits à ce module        
        notes = [ NotesDB[etudid]['value'] for etudid in NotesDB 
                  if (etudid in insmod_set) ]
        e['nb_notes'] = len(notes)
        e['nb_abs'] = len( [ x for x in notes if x is None ] )
        e['nb_neutre'] = len( [ x for x in notes if x == NOTES_NEUTRALISE ] )
        e['nb_att'] = len( [ x for x in notes if x == NOTES_ATTENTE ] )
        e['notes'] = NotesDB
        e['etat'] = context.do_evaluation_etat(e['evaluation_id'])[0]
        if e['nb_att']:
            attente = True
    # filtre les evals valides (toutes les notes entrées)        
    valid_evals = [ e for e in evals
                    if (e['etat']['evalcomplete'] or e['etat']['evalattente']) ]
    # 
    R = {}
    for etudid in insmod_set: # inscrits au semestre et au module
        sum_notes = 0.
        sum_coefs = 0.
        nb_missing = 0
        for e in valid_evals:
            if e['notes'].has_key(etudid):
                note = e['notes'][etudid]['value']
                if note is None: # ABSENT
                    note = 0            
                if note != NOTES_NEUTRALISE and note != NOTES_ATTENTE:
                    sum_notes += (note * 20. / e['note_max']) * e['coefficient']
                    sum_coefs += e['coefficient']
            else:
                # il manque une note !
                if e['coefficient'] > 0:
                    nb_missing += 1
        if nb_missing == 0 and sum_coefs > 0:
            if sum_coefs > 0:
                R[etudid] = sum_notes / sum_coefs
            else:
                R[etudid] = 'na'
        else:
            R[etudid] = 'NA%d' % nb_missing
        if user_expr:
            # (experimental) recalcule la moyenne en utilisant la formule utilisateur
            notes = []
            coefs = []
            coefs_mask = [] # 0/1, 0 si coef a ete annulé
            nb_notes = 0 # nombre de notes valides
            for e in evals:                
                if (e['etat']['evalcomplete'] or e['etat']['evalattente']) and e['notes'].has_key(etudid):
                    note = e['notes'][etudid]['value']
                    if note is None:
                        note = 0
                    if note != NOTES_NEUTRALISE and note != NOTES_ATTENTE:
                        notes.append( note * 20. / e['note_max'] )
                        coefs.append(e['coefficient'])
                        coefs_mask.append(1)
                        nb_notes += 1
                    else:
                        notes.append(0.)
                        coefs.append(0.)
                        coefs_mask.append(0)
                else:
                    notes.append(0.)
                    coefs.append(0.)
                    coefs_mask.append(0)
            if nb_notes > 0:
                try:
                    log('notes=%s' % notes)
                    log('coefs=%s' % coefs)
                    user_moy = eval_user_expression(context, M['computation_expr'], notes, coefs, coefs_mask)
                    if user_moy > 20 or user_moy < 0:
                        raise ScoException("valeur moyenne %s hors limite pour %s" % (user_moy, etudid))
                except:
                    log('invalid expression !')
                    log('Exception during evaluation:\n%s\n' % traceback.format_exc())
                    user_moy = 'ERR'
                R[etudid] = user_moy
    
    return R, valid_evals, attente


