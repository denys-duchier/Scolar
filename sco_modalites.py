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

"""Modalites des semestres

La "modalite" est utilisee pour organiser les listes de semestres sur la page d'accueil.

Elle n'est pas utilisée pour les parcours, ni pour rien d'autre 
(c'est donc un attribut "cosmétique").

"""
from notesdb import *
from sco_utils import *
from notes_log import log
from TrivialFormulator import TrivialFormulator, TF
import sco_codes_parcours

def list_formsemestres_modalites(context, sems):
    """Liste ordonnée des modalités présentes dans ces formsemestres
    """
    modalites = {}
    for sem in sems:
        if sem['modalite'] not in modalites:
            m = do_modalite_list(context, args={'modalite':sem['modalite']})[0]
            modalites[m['modalite']] = m
    modalites = modalites.values()
    modalites.sort(key=lambda x: x['numero'])
    return modalites

def group_sems_by_modalite(context, sems):
    """Given e list of fromsemestre, group them by modalite,
    sorted in each one by semestre id and date
    """
    sems_by_mod = DictDefault(defaultvalue=[])
    modalites = list_formsemestres_modalites(context, sems)
    for modalite in modalites:
        for sem in sems:
            if sem['semestre_id'] < 0: # formations en un semestre
                sem['sortkey'] = (-100*sem['semestre_id'],sem['dateord'])
            else:
                sem['sortkey'] = (sem['semestre_id'],sem['dateord'])
            if sem['modalite'] == modalite['modalite']:
                sems_by_mod[modalite['modalite']].append(sem)
    # tri dans chaque modalité par indice de semestre et date debut
    for modalite in modalites:
        sems_by_mod[modalite['modalite']].sort(key=lambda x: x['sortkey'])
    
    return sems_by_mod, modalites

# ------ Low level interface (database) ------

_modaliteEditor = EditableTable(
    'notes_form_modalites',
    'form_modalite_id',
    ('form_modalite_id', 'modalite', 'titre', 'numero'),
    sortkey='numero',
    output_formators = { 'numero' : int_null_is_zero },
    )

def do_modalite_list(context, *args, **kw):
    """Liste des modalites
    """
    cnx = context.GetDBConnexion()
    return _modaliteEditor.list(cnx, *args, **kw)

def do_modalite_create(context, args, REQUEST):
    "create a modalite"
    cnx = self.GetDBConnexion()
    r = _modaliteEditor.create(cnx, args)
    return r

def do_modalite_delete(context, oid, REQUEST=None):
    "delete a modalite"
    cnx = self.GetDBConnexion()
    log('do_modalite_delete: form_modalite_id=%s' % oid)
    _modaliteEditor.delete(cnx, oid)

def do_modalite_edit(context,  *args, **kw ):
    "edit a modalite"
    cnx = self.GetDBConnexion()
    # check
    m = do_modalite_list(context, { 'form_modalite_id' :args[0]['form_modalite_id']})[0]
    _modaliteEditor.edit( cnx, *args, **kw )


