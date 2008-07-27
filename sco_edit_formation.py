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

"""Ajout/Modification/Supression formations
(portage from DTML)
"""
from notesdb import *
from sco_utils import *
from notes_log import log
from TrivialFormulator import TrivialFormulator, TF

def formation_create(context, REQUEST=None):
    """Creation d'une formation
    """
    H = [ context.sco_header(REQUEST, page_title="Cr�ation d'une formation"),
          """<h2>Cr�ation d'une formation</h2>

<p class="help">Une "formation" d�crit une fili�re, comme un DUT ou un Licence. La formation se subdivise en unit�s p�dagogiques (UE, mati�res, modules). Elle peut se diviser en plusieurs semestres (ou sessions), qui seront mis en place s�par�ment.
</p>

<p>Le <tt>titre</tt> est le nom complet, parfois adapt� pour mieux distinguer les modalit�s ou versions de programme p�dagogique. Le <tt>titre_officiel</tt> est le nom complet du dipl�me, qui apparaitra sur certains PV de jury de d�livrance du dipl�me.
</p>
"""]
    tf = TrivialFormulator(REQUEST.URL0, REQUEST.form, (
        ('acronyme',  { 'size' : 12, 'explanation' : 'identifiant de la formation (par ex. DUT R&T)', 'allow_null' : False }),
        ('titre'    , { 'size' : 80, 'explanation' : 'nom complet de la formation (ex: DUT R�seaux et T�l�communications)', 'allow_null' : False }),
        ('titre_officiel'    , { 'size' : 80, 'explanation' : 'nom officiel (pour les PV de jury)', 'allow_null' : False }),
        ('formation_code', { 'size' : 12, 'title' : 'Code formation', 'explanation' : 'code interne. Toutes les formations partageant le m�me code sont compatibles (compensation de semestres, capitalisation d\'UE).' }),
        ),
                           cancelbutton = 'Annuler',
                           submitlabel = 'Cr�er cette formation')
    if tf[0] == 0:
        return '\n'.join(H) + tf[1] + context.sco_footer(REQUEST)
    elif tf[0] == -1:
        return REQUEST.RESPONSE.redirect( REQUEST.URL1 )
    else:
        formation_id = context.do_formation_create( tf[2], REQUEST )
        return REQUEST.RESPONSE.redirect( REQUEST.URL1 )

def formation_delete(context, formation_id=None, dialog_confirmed=False, REQUEST=None):
    """Delete a formation
    """
    F = context.do_formation_list( args={ 'formation_id' : formation_id } )[0]
    
    H = [ context.sco_header(REQUEST, page_title="Suppression d'une formation"),          
          """<h2>Suppression de la formation %(titre)s (%(acronyme)s)</h2>""" % F ]

    sems = context.do_formsemestre_list( {'formation_id' : formation_id })
    if sems:
        H.append("""<p class="warning">Impossible de supprimer cette formation, car les sessions suivantes l'utilisent:</p>
<ul>""")
        for sem in sems:
            H.append('<li><a href="formsemestre_status?formsemestre_id=%(formsemestre_id)s">%(titremois)s</a></li>' % sem)
        H.append('</ul><p><a href="%s">Revenir</a></p>' % REQUEST.URL1)
    else:
        if not dialog_confirmed:
            return context.confirmDialog(
                """<h2>Confirmer la suppression de la formation %(titre)s (%(acronyme)s) ?</h2>
    <p><b>Attention:</b> la suppression d'une formation est <b>irr�versible</b> et implique la supression de toutes les UE, mati�res et modules de la formation !
</p>
                """ % F, REQUEST=REQUEST,
                OK="Supprimer cette formation",
                cancel_url=REQUEST.URL1, parameters={'formation_id':formation_id})
        else:
            context.do_formation_delete( F['formation_id'], REQUEST )
            H.append("""<p>OK, formation supprim�e.</p>
    <p><a class="stdlink" href="%s">continuer</a></p>""" % REQUEST.URL1)

    H.append(context.sco_footer(REQUEST))
    return '\n'.join(H)



def formation_edit(context, formation_id=None, REQUEST=None):
    """Edit a formation
    """
    F = context.do_formation_list( args={ 'formation_id' : formation_id } )[0]
    H = [ context.sco_header(REQUEST, page_title="Modification d'une formation"),
          """<h2>Modification de la formation %(acronyme)s</h2>""" % F ]
    tf = TrivialFormulator(REQUEST.URL0, REQUEST.form, (
        ('formation_id', { 'default' : formation_id, 'input_type' : 'hidden' }),
        ('acronyme',  { 'size' : 12, 'explanation' : 'identifiant de la formation (par ex. DUT R&T)',  'allow_null' : False }),
        ('titre'    , { 'size' : 80, 'explanation' : 'nom complet de la formation (ex: DUT R�seaux et T�l�communications',  'allow_null' : False }),
        ('titre_officiel'    , { 'size' : 80, 'explanation' : 'nom officiel (pour les PV de jury)', 'allow_null' : False }),
        ('formation_code', { 'size' : 12, 'title' : 'Code formation', 'explanation' : 'code interne. Toutes les formations partageant le m�me code sont compatibles (compensation de semestres, capitalisation d\'UE).' }),
        ),
                           initvalues = F,
                           submitlabel = 'Modifier les valeurs')
    if tf[0] == 0:
        return '\n'.join(H) + tf[1] + context.sco_footer(REQUEST)
    elif tf[0] == -1:
        return REQUEST.RESPONSE.redirect( REQUEST.URL1 )
    else:
        context.do_formation_edit(tf[2])
        return REQUEST.RESPONSE.redirect( REQUEST.URL1 )
