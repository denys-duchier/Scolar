# -*- mode: python -*-
# -*- coding: iso8859-15 -*-

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

"""Ajout/Modification/Supression matieres
(portage from DTML)
"""
from notesdb import *
from sco_utils import *
from notes_log import log
from TrivialFormulator import TrivialFormulator, TF

def matiere_create(context, ue_id=None, REQUEST=None):
    """Creation d'une matiere
    """
    UE = context.do_ue_list( args={ 'ue_id' : ue_id } )[0]
    H = [ context.sco_header(REQUEST, page_title="Cr�ation d'une mati�re"),
          """<h2>Cr�ation d'une mati�re dans l'UE %(titre)s (%(acronyme)s)</h2>""" % UE,
          """<p class="help">Les mati�res sont des groupes de modules dans une UE
d'une formation donn�e. Les mati�res servent surtout pour la
pr�sentation (bulletins, etc) mais <em>n'ont pas de r�le dans le calcul
des notes.</em>
</p> 

<p class="help">Si votre formation n'utilise pas la notion de
"mati�res", cr�ez une mati�re par UE, et donnez lui le m�me nom que l'UE
(en effet, tout module doit appartenir � une mati�re).
</p>

<p class="help">Comme les UE, les mati�res n'ont pas de coefficient
associ�.
</p>"""]    
    tf = TrivialFormulator(REQUEST.URL0, REQUEST.form, ( 
        ('ue_id', { 'input_type' : 'hidden', 'default' : ue_id }),
        ('titre'    , { 'size' : 30, 'explanation' : 'nom de la mati�re.' }),
        ('numero',    { 'size' : 2, 'explanation' : 'num�ro (1,2,3,4...) pour affichage',
                        'type' : 'int' }),
        ),
                           submitlabel = 'Cr�er cette mati�re')

    dest_url = REQUEST.URL1 + '/ue_list?formation_id=' + UE['formation_id']

    if tf[0] == 0:
        return '\n'.join(H) + tf[1] + context.sco_footer(REQUEST)
    elif tf[0] == -1:
        return REQUEST.RESPONSE.redirect(dest_url)
    else:
        # check unicity
        mats = context.do_matiere_list(args={ 'ue_id' : ue_id, 'titre' : tf[2]['titre'] } )
        if mats:
            return '\n'.join(H) + tf_error_message('Titre de mati�re d�j� existant dans cette UE') + tf[1] + context.sco_footer(REQUEST)
        matiere_id = context.do_matiere_create( tf[2], REQUEST )
        return REQUEST.RESPONSE.redirect(dest_url)


def matiere_delete(context, matiere_id=None, REQUEST=None):
    """Delete an UE"""
    M = context.do_matiere_list(args={ 'matiere_id' : matiere_id } )[0]
    UE = context.do_ue_list( args={ 'ue_id' : M['ue_id'] } )[0]
    H = [ context.sco_header(REQUEST, page_title="Suppression d'une mati�re"),
          "<h2>Suppression de la mati�re %(titre)s" % M,
          " dans l'UE (%(acronyme)s))</h2>" % UE ]
    
    tf = TrivialFormulator( REQUEST.URL0, REQUEST.form, (
        ('matiere_id', { 'input_type' : 'hidden' }),
        ),
                            initvalues = M,
                            submitlabel = 'Confirmer la suppression',
                            cancelbutton = 'Annuler'
                            )
    if tf[0] == 0:
        return '\n'.join(H) + tf[1] + context.sco_footer(REQUEST)
    elif tf[0] == -1:
        return REQUEST.RESPONSE.redirect( REQUEST.URL1 )
    else:
        context.do_matiere_delete( matiere_id, REQUEST )
        return REQUEST.RESPONSE.redirect( REQUEST.URL1 + '/ue_list?formation_id=' + str(UE['formation_id']))


def matiere_edit(context, matiere_id=None, REQUEST=None):
    """Edit matiere"""
    F = context.do_matiere_list(args={ 'matiere_id' : matiere_id } )
    if not F:
        raise ScoValueError('Mati�re inexistante !')
    F = F[0]
    U = context.do_ue_list( args={ 'ue_id' : F['ue_id'] } )
    if not F:
        raise ScoValueError('UE inexistante !')
    U = U[0]
    Fo= context.formation_list( args={ 'formation_id' : U['formation_id'] } )[0]

    ues = context.do_ue_list( args={ 'formation_id' : U['formation_id'] } )
    ue_names = [ '%(acronyme)s (%(titre)s)' % u for u in ues ]
    ue_ids = [ u['ue_id'] for u in ues ]
    H = [context.sco_header(REQUEST, page_title="Modification d'une mati�re"),
         """<h2>Modification de la mati�re %(titre)s""" % F,
         """(formation %(acronyme)s, version %(version)s)</h2>""" % Fo ]
    help = """<p class="help">Les mati�res sont des groupes de modules dans une UE
d'une formation donn�e. Les mati�res servent surtout pour la
pr�sentation (bulletins, etc) mais <em>n'ont pas de r�le dans le calcul
des notes.</em>
</p> 

<p class="help">Si votre formation n'utilise pas la notion de
"mati�res", cr�ez une mati�re par UE, et donnez lui le m�me nom que l'UE
(en effet, tout module doit appartenir � une mati�re).
</p>

<p class="help">Comme les UE, les mati�res n'ont pas de coefficient
associ�.
</p>"""
    tf = TrivialFormulator( REQUEST.URL0, REQUEST.form, (
        ('matiere_id', { 'input_type' : 'hidden' }),
        ('ue_id', { 'input_type' : 'menu', 'allowed_values' : ue_ids, 'labels' : ue_names }),
        ('titre'    , { 'size' : 30, 'explanation' : 'nom de cette mati�re' }),
        ('numero',    { 'size' : 2, 'explanation' : 'num�ro (1,2,3,4...) pour affichage',
                        'type' : 'int' }),
        ),
                            initvalues = F,
                            submitlabel = 'Modifier les valeurs')
    
    dest_url = REQUEST.URL1 + '/ue_list?formation_id=' + U['formation_id']

    if tf[0] == 0:
        return '\n'.join(H) + tf[1] + help + context.sco_footer(REQUEST)
    elif tf[0] == -1:
        return REQUEST.RESPONSE.redirect(dest_url)
    else:
        # check unicity
        mats = context.do_matiere_list(args={ 'ue_id' : tf[2]['ue_id'], 'titre' : tf[2]['titre'] } )
        if len(mats) > 1 or (len(mats) == 1 and mats[0]['matiere_id'] != matiere_id):
            return '\n'.join(H) + tf_error_message('Titre de mati�re d�j� existant dans cette UE') + tf[1] + context.sco_footer(REQUEST)
        
        # changement d'UE ?
        if tf[2]['ue_id'] != F['ue_id']:
            log('attaching mat %s to new UE %s' % (matiere_id, tf[2]['ue_id']) )
            SimpleQuery( context, "UPDATE notes_modules SET ue_id = %(ue_id)s WHERE matiere_id=%(matiere_id)s",
                         { 'ue_id' :  tf[2]['ue_id'], 'matiere_id' : matiere_id } )
        
        context.do_matiere_edit( tf[2] )
        
        return REQUEST.RESPONSE.redirect(dest_url)


