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
import ZAbsences
from notes_log import log, sendAlarm
import sco_groups
import sco_evaluations

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
    'ifelse'  : ternary_op,
    'geomean' : geometrical_mean
}

# v = NoteVector(1,2)
# eval("max(4,5)", {'__builtins__': formula_builtins, {'x' : 1, 'v' : NoteVector(1,2) }, {})

def eval_user_expression(context, expression, variables):
    """Evalue l'expression (formule utilisateur) avec les variables (dict) données.
    """
    variables['__builtins__'] = formula_builtins
    # log('Evaluating %s with %s' % (expression, variables))
    # may raise exception if user expression is invalid
    return eval( expression, variables, {} ) # this should be safe

def moduleimpl_has_expression(context, mod):
    "True if we should use a user-defined expression"
    expr = mod['computation_expr']
    if not expr:
        return False
    expr = expr.strip()
    if not expr or expr[0] == '#':
        return False
    return True

def do_moduleimpl_moyennes(context, mod):
    """Retourne dict { etudid : note_moyenne } pour tous les etuds inscrits
    au moduleimpl mod, la liste des evaluations "valides" (toutes notes entrées
    ou en attente), et att (vrai s'il y a des notes en attente dans ce module).
    La moyenne est calculée en utilisant les coefs des évaluations.
    Les notes NEUTRES (abs. excuses) ne sont pas prises en compte.
    Les notes ABS sont remplacées par des zéros.
    S'il manque des notes et que le coef n'est pas nul,
    la moyenne n'est pas calculée: NA
    Ne prend en compte que les evaluations où toutes les notes sont entrées.
    Le résultat est une note sur 20.
    """
    moduleimpl_id = mod['moduleimpl_id']
    etudids = context.do_moduleimpl_listeetuds(moduleimpl_id) # tous, y compris demissions
    # Inscrits au semestre (pour traiter les demissions):
    inssem_set = Set( [x['etudid'] for x in
                       context.do_formsemestre_inscription_listinscrits(mod['formsemestre_id'])])
    insmod_set = inssem_set.intersection(etudids) # inscrits au semestre et au module
    evals = context.do_evaluation_list(args={ 'moduleimpl_id' : moduleimpl_id })
    user_expr = moduleimpl_has_expression(context, mod)
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
        e['etat'] = sco_evaluations.do_evaluation_etat(context, e['evaluation_id'])
        if e['nb_att']:
            attente = True
    # filtre les evals valides (toutes les notes entrées)        
    valid_evals = [ e for e in evals
                    if (e['etat']['evalcomplete'] or e['etat']['evalattente']) ]
    
    # 
    expr_diag = '' # message d'erreur formule
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
                moy_valid = True
            else:
                R[etudid] = 'na'
                moy_valid = False
        else:
            R[etudid] = 'NA%d' % nb_missing
            moy_valid = False
        
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
                AbsSemEtud = ZAbsences.getAbsSemEtud(context, mod['formsemestre_id'], etudid)
                nbabs = AbsSemEtud.CountAbs()
                nbabs_just = AbsSemEtud.CountAbsJust()
                variables = {
                        'cmask' : NoteVector(v=coefs_mask),
                        'notes' : NoteVector(v=notes), 
                        'coefs' : NoteVector(v=coefs),
                        'moy'   : R[etudid],
                        'moy_valid' : moy_valid, # True si moyenne numerique
                        'nbabs' : float(nbabs),
                        'nbabs_just' : float(nbabs_just),
                        'nbabs_nojust' : float(nbabs - nbabs_just)
                        }
                try:
                    user_moy = eval_user_expression(context, mod['computation_expr'], variables)                    
                    if user_moy > 20 or user_moy < 0:
                        raise ScoException("valeur moyenne %s hors limite pour %s" % (user_moy, etudid))
                except:
                    log('invalid expression !')
                    tb = traceback.format_exc()
                    log('Exception during evaluation:\n%s\n' % tb)
                    expr_diag = { 'moduleimpl_id' : moduleimpl_id, 'msg' : tb.splitlines()[-1] }
                    user_moy = 'ERR'
                R[etudid] = user_moy
    
    return R, valid_evals, attente, expr_diag


def do_formsemestre_moyennes(context, formsemestre_id):
    """retourne dict { moduleimpl_id : { etudid, note_moyenne_dans_ce_module } },
    la liste des moduleimpls, la liste des evaluations valides,
    liste des moduleimpls  avec notes en attente.
    """
    sem = context.get_formsemestre(formsemestre_id)
    inscr = context.do_formsemestre_inscription_list(
        args = { 'formsemestre_id' : formsemestre_id })
    etudids = [ x['etudid'] for x in inscr ]
    mods = context.do_moduleimpl_list( args={ 'formsemestre_id' : formsemestre_id})
    # recupere les moyennes des etudiants de tous les modules
    D = {}
    valid_evals = []
    mods_att = []
    expr_diags = []
    for mod in mods:
        assert not D.has_key(mod['moduleimpl_id'])
        D[mod['moduleimpl_id']], valid_evals_mod, attente, expr_diag =\
            do_moduleimpl_moyennes(context, mod)
        valid_evals += valid_evals_mod
        if attente:
            mods_att.append(mod)
        if expr_diag:
            expr_diags.append(expr_diag)
    #
    return D, mods, valid_evals, mods_att, expr_diags
