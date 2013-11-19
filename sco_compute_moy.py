# -*- mode: python -*-
# -*- coding: utf-8 -*-

##############################################################################
#
# Gestion scolarite IUT
#
# Copyright (c) 2001 - 2011 Emmanuel Viennet.  All rights reserved.
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
import traceback

from sco_utils import *
from notesdb import *
from notes_log import log, sendAlarm
import sco_groups
import sco_evaluations
from sco_formulas import *
import ZAbsences

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
    """True si les notes de ce semestre dépendent des compteurs d'absences.
    Cela n'est normalement pas le cas, sauf si des formules utilisateur utilisent ces compteurs.
    """
    # check presence of 'nbabs' in expressions
    ab = 'nbabs' # chaine recherchée
    cnx = context.GetDBConnexion()
    # 1- moyennes d'UE:
    elist = formsemestre_ue_computation_expr_list(cnx, {'formsemestre_id':formsemestre_id})
    for e in elist:
        expr = e['computation_expr'].strip()
        if expr and expr[0] != '#' and ab in expr:
            return True
    # 2- moyennes de modules
    for mod in context.Notes.do_moduleimpl_list( args={ 'formsemestre_id':formsemestre_id } ):
        if moduleimpl_has_expression(context, mod) and ab in mod['computation_expr']:
            return True
    return False

_formsemestre_ue_computation_exprEditor = EditableTable(
        'notes_formsemestre_ue_computation_expr',
        'notes_formsemestre_ue_computation_expr_id',
        ('notes_formsemestre_ue_computation_expr_id', 'formsemestre_id', 'ue_id', 'computation_expr'),
        html_quote = False # does nt automatically quote
        )
formsemestre_ue_computation_expr_create=_formsemestre_ue_computation_exprEditor.create
formsemestre_ue_computation_expr_delete=_formsemestre_ue_computation_exprEditor.delete
formsemestre_ue_computation_expr_list=_formsemestre_ue_computation_exprEditor.list
formsemestre_ue_computation_expr_edit=_formsemestre_ue_computation_exprEditor.edit


def get_ue_expression(formsemestre_id, ue_id, cnx, html_quote=False):
    """Returns UE expression (formula), or None if no expression has been defined
    """
    el = formsemestre_ue_computation_expr_list(cnx, {'formsemestre_id':formsemestre_id, 'ue_id':ue_id})
    if not el:
        return None
    else:
        expr = el[0]['computation_expr'].strip()
        if expr and expr[0] != '#':
            if html_quote:
                expr = quote_html(expr)
            return expr
        else:
            return None

def compute_user_formula(context, formsemestre_id, etudid, 
                         moy, moy_valid, notes, coefs, coefs_mask, 
                         formula,
                         diag_info={} # infos supplementaires a placer ds messages d'erreur
                         ):
    """Calcul moyenne a partir des notes et coefs, en utilisant la formule utilisateur (une chaine).
    Retourne moy, et en cas d'erreur met à jour diag_info (msg)
    """
    AbsSemEtud = ZAbsences.getAbsSemEtud(context, formsemestre_id, etudid)
    nbabs = AbsSemEtud.CountAbs()
    nbabs_just = AbsSemEtud.CountAbsJust()
    try:
        moy_val = float(moy)
    except:
        moy_val = 0. # 0. when no valid value
    variables = {
        'cmask' : coefs_mask, # NoteVector(v=coefs_mask),
        'notes' : notes, #NoteVector(v=notes), 
        'coefs' : coefs, #NoteVector(v=coefs),
        'moy'   : moy,
        'moy_valid' : moy_valid, # deprecated, use moy_is_valid
        'moy_is_valid' : moy_valid, # True si moyenne numerique
        'moy_val' : moy_val,
        'nb_abs' : float(nbabs),
        'nb_abs_just' : float(nbabs_just),
        'nb_abs_nojust' : float(nbabs - nbabs_just)
        }
    try:
        formula = formula.replace('\n', '').replace('\r', '')
        #log('expression : %s\nvariables=%s\n' % (formula, variables)) # XXX debug
        user_moy = eval_user_expression(context, formula, variables)
        #log('user_moy=%s' % user_moy)
        if user_moy != 'NA0' and user_moy != 'NA':
            user_moy = float(user_moy)
            if (user_moy > 20) or (user_moy < 0):
                raise ScoException("valeur moyenne %s hors limite pour %s" % (user_moy, etudid))
    except:
        log('invalid expression : %s\nvariables=%s\n' % (formula, variables))
        tb = traceback.format_exc()
        log('Exception during evaluation:\n%s\n' % tb)
        diag_info.update({ 'msg' : tb.splitlines()[-1] })
        user_moy = 'ERR'

    # log('formula=%s\nvariables=%s\nmoy=%s\nuser_moy=%s' % (formula, variables, moy, user_moy))
    
    return user_moy

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
    diag_info = {} # message d'erreur formule
    moduleimpl_id = mod['moduleimpl_id']
    etudids = context.do_moduleimpl_listeetuds(moduleimpl_id) # tous, y compris demissions
    # Inscrits au semestre (pour traiter les demissions):
    inssem_set = Set( [x['etudid'] for x in
                       context.do_formsemestre_inscription_listinscrits(mod['formsemestre_id'])])
    insmod_set = inssem_set.intersection(etudids) # inscrits au semestre et au module
    evals = context.do_evaluation_list(args={ 'moduleimpl_id' : moduleimpl_id })
    evals.reverse() # la plus ancienne en tête
    user_expr = moduleimpl_has_expression(context, mod)
    attente = False
    # recupere les notes de toutes les evaluations
    eval_rattr = None
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
        if e['etat']['evalattente']:
            attente = True
        if e['evaluation_type'] == EVALUATION_RATTRAPAGE:
            if eval_rattr:
                # !!! plusieurs rattrapages !
                diag_info.update({ 'msg' : 'plusieurs évaluations de rattrapage !',
                                   'moduleimpl_id' : moduleimpl_id })
            eval_rattr = e
    
    # filtre les evals valides (toutes les notes entrées)        
    valid_evals = [ e for e in evals
                    if ((e['etat']['evalcomplete'] or e['etat']['evalattente']) and (e['note_max'] > 0)) ]
    # 
    R = {}
    for etudid in insmod_set: # inscrits au semestre et au module
        sum_notes = 0.
        sum_coefs = 0.
        nb_missing = 0
        for e in valid_evals:
            if e['evaluation_type'] != EVALUATION_NORMALE:
                continue
            if e['notes'].has_key(etudid):
                note = e['notes'][etudid]['value']
                if note is None: # ABSENT
                    note = 0            
                if note != NOTES_NEUTRALISE and note != NOTES_ATTENTE:
                    sum_notes += (note * 20. / e['note_max']) * e['coefficient']
                    sum_coefs += e['coefficient']
            else:
                # il manque une note ! (si publish_incomplete, cela peut arriver, on ignore)
                if e['coefficient'] > 0 and e['publish_incomplete'] == '0':
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
                if ((e['etat']['evalcomplete'] or e['etat']['evalattente']) and e['notes'].has_key(etudid)) and (e['note_max'] > 0):
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
                formula = unescape_html(mod['computation_expr'])
                user_moy = compute_user_formula(context, mod['formsemestre_id'], etudid, 
                                                R[etudid], moy_valid,
                                                notes, coefs, coefs_mask, formula,
                                                diag_info=diag_info)
                if diag_info:
                    diag_info['moduleimpl_id'] = moduleimpl_id
                R[etudid] = user_moy
        # Note de rattrapage ?
        if eval_rattr:
            if eval_rattr['notes'].has_key(etudid):
                note = eval_rattr['notes'][etudid]['value']
                if note != None and note != NOTES_NEUTRALISE and note != NOTES_ATTENTE:
                    if type(R[etudid]) != FloatType:
                        R[etudid] = note
                    elif note > R[etudid]:
                        R[etudid] = note
    
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
    valid_evals_per_mod = {} # { moduleimpl_id : eval }
    mods_att = []
    expr_diags = []
    for mod in mods:
        moduleimpl_id = mod['moduleimpl_id']
        assert not D.has_key(moduleimpl_id)
        D[moduleimpl_id], valid_evals_mod, attente, expr_diag = do_moduleimpl_moyennes(context, mod)
        valid_evals_per_mod[moduleimpl_id] = valid_evals_mod
        valid_evals += valid_evals_mod
        if attente:
            mods_att.append(mod)
        if expr_diag:
            expr_diags.append(expr_diag)
    #
    return D, mods, valid_evals_per_mod, valid_evals, mods_att, expr_diags
