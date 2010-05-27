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
from notesdb import *
import ZAbsences
from notes_log import log, sendAlarm
import sco_groups
import sco_evaluations

class NoteVector:
    """Vecteur de notes (ou coefficients) utilis� pour les formules d�finies par l'utilisateur.
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

# Les builtins autoris�es dans les formules utilisateur:
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
    """Evalue l'expression (formule utilisateur) avec les variables (dict) donn�es.
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

def formsemestre_expressions_use_abscounts(context, formsemestre_id):
    """True si les notes de ce semestre d�pendnent des compteurs d'absences.
    Cela n'est normalement pas le cas, sauf si des formules utilisateur utilisent ces compteurs.
    """
    # check presence of 'nbabs' in expressions
    ab = 'nbabs' # chaine recherch�e
    cnx = context.GetDBConnexion()
    # 1- moyennes d'UE:
    elist = formsemestre_ue_computation_expr_list(cnx, {'formsemestre_id':formsemestre_id})
    for e in elist:
        expr = e['computation_expr'].strip()
        if expr and expr[0] != '#' and ab in expr:
            return True
    # 2- moyennes de modules
    for mod in self.do_moduleimpl_list( args={ 'formsemestre_id':formsemestre_id } ):
        if moduleimpl_has_expression(context, mod) and ab in mod['computation_expr']:
            return True
    return False

_formsemestre_ue_computation_exprEditor = EditableTable(
        'notes_formsemestre_ue_computation_expr',
        'notes_formsemestre_ue_computation_expr_id',
        ('notes_formsemestre_ue_computation_expr_id', 'formsemestre_id', 'ue_id', 'computation_expr'),
        )
formsemestre_ue_computation_expr_create=_formsemestre_ue_computation_exprEditor.create
formsemestre_ue_computation_expr_delete=_formsemestre_ue_computation_exprEditor.delete
formsemestre_ue_computation_expr_list=_formsemestre_ue_computation_exprEditor.list
formsemestre_ue_computation_expr_edit=_formsemestre_ue_computation_exprEditor.edit


def get_ue_expression(formsemestre_id, ue_id, cnx):
    """Returns UE expression (formula), or None if no expression has been defined
    """
    el = formsemestre_ue_computation_expr_list(cnx, {'formsemestre_id':formsemestre_id, 'ue_id':ue_id})
    if not el:
        return None
    else:
        expr = el[0]['computation_expr'].strip()
        if expr and expr[0] != '#':
            return expr
        else:
            return None

def compute_user_formula(context, formsemestre_id, etudid, 
                         moy, moy_valid, notes, coefs, coefs_mask, 
                         formula,
                         diag_info={} # infos supplementaires a placer ds messages d'erreur
                         ):
    """Calcul moyenne a partir des notes et coefs, en utilisant la formule utilisatuer (une chaine).
    Retourne moy, et en cas d'erreur met � jour diag_info (msg)
    """
    AbsSemEtud = ZAbsences.getAbsSemEtud(context, formsemestre_id, etudid)
    nbabs = AbsSemEtud.CountAbs()
    nbabs_just = AbsSemEtud.CountAbsJust()
    variables = {
            'cmask' : NoteVector(v=coefs_mask),
            'notes' : NoteVector(v=notes), 
            'coefs' : NoteVector(v=coefs),
            'moy'   : moy,
            'moy_valid' : moy_valid, # True si moyenne numerique
            'nbabs' : float(nbabs),
            'nbabs_just' : float(nbabs_just),
            'nbabs_nojust' : float(nbabs - nbabs_just)
            }
    try:
        user_moy = eval_user_expression(context, formula, variables)                    
        if user_moy > 20 or user_moy < 0:
            raise ScoException("valeur moyenne %s hors limite pour %s" % (user_moy, etudid))
    except:
        log('invalid expression !')
        tb = traceback.format_exc()
        log('Exception during evaluation:\n%s\n' % tb)
        diag_info.update({ 'msg' : tb.splitlines()[-1] })
        user_moy = 'ERR'

    # log('formula=%s\nvariables=%s\nmoy=%s\nuser_moy=%s' % (formula, variables, moy, user_moy))
    
    return user_moy

def do_moduleimpl_moyennes(context, mod):
    """Retourne dict { etudid : note_moyenne } pour tous les etuds inscrits
    au moduleimpl mod, la liste des evaluations "valides" (toutes notes entr�es
    ou en attente), et att (vrai s'il y a des notes en attente dans ce module).
    La moyenne est calcul�e en utilisant les coefs des �valuations.
    Les notes NEUTRES (abs. excuses) ne sont pas prises en compte.
    Les notes ABS sont remplac�es par des z�ros.
    S'il manque des notes et que le coef n'est pas nul,
    la moyenne n'est pas calcul�e: NA
    Ne prend en compte que les evaluations o� toutes les notes sont entr�es.
    Le r�sultat est une note sur 20.
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
        # restreint aux �tudiants encore inscrits � ce module        
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
    # filtre les evals valides (toutes les notes entr�es)        
    valid_evals = [ e for e in evals
                    if (e['etat']['evalcomplete'] or e['etat']['evalattente']) ]
    
    # 
    diag_info = {} # message d'erreur formule
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
            coefs_mask = [] # 0/1, 0 si coef a ete annul�
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
                user_moy = compute_user_formula(context, mod['formsemestre_id'], etudid, 
                                                R[etudid], moy_valid,
                                                notes, coefs, coefs_mask, mod['computation_expr'],
                                                diag_info=diag_info)
                if diag_info:
                    diag_info['moduleimpl_id'] = moduleimpl_id
                R[etudid] = user_moy
    
    return R, valid_evals, attente, diag_info


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
