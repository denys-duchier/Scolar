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

"""Ajout/Modification/Supression formations
(portage from DTML)
"""
from notesdb import *
from sco_utils import *
from notes_log import log
from TrivialFormulator import TrivialFormulator, TF
import sco_codes_parcours

def formation_delete(context, formation_id=None, dialog_confirmed=False, REQUEST=None):
    """Delete a formation
    """
    F = context.formation_list( args={ 'formation_id' : formation_id } )
    if not F:
        raise ScoValueError("formation inexistante !")
    F = F[0]
    
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


def formation_create(context, REQUEST=None):
    """Creation d'une formation
    """
    return formation_edit(context, create=True, REQUEST=REQUEST) 

def formation_edit(context, formation_id=None, create=False, REQUEST=None):
    """Edit or create a formation
    """
    if create:
        H = [ context.sco_header(REQUEST, page_title="Cr�ation d'une formation"),
          """<h2>Cr�ation d'une formation</h2>

<p class="help">Une "formation" d�crit une fili�re, comme un DUT ou une Licence. La formation se subdivise en unit�s p�dagogiques (UE, mati�res, modules). Elle peut se diviser en plusieurs semestres (ou sessions), qui seront mis en place s�par�ment.
</p>

<p>Le <tt>titre</tt> est le nom complet, parfois adapt� pour mieux distinguer les modalit�s ou versions de programme p�dagogique. Le <tt>titre_officiel</tt> est le nom complet du dipl�me, qui apparaitra sur certains PV de jury de d�livrance du dipl�me.
</p>
"""]
        submitlabel = 'Cr�er cette formation'
        initvalues = {}
    else:
        # edit an existing formation
        F = context.formation_list( args={ 'formation_id' : formation_id } )
        if not F:
            raise ScoValueError('formation inexistante !')
        initvalues = F[0]
        submitlabel = 'Modifier les valeurs'
        H = [ context.sco_header(REQUEST, page_title="Modification d'une formation"),
              """<h2>Modification de la formation %(acronyme)s</h2>""" % initvalues ]
    
    tf = TrivialFormulator(REQUEST.URL0, REQUEST.form, (
        ('formation_id', { 'default' : formation_id, 'input_type' : 'hidden' }),
        ('acronyme',  { 'size' : 12, 'explanation' : 'identifiant de la formation (par ex. DUT R&T)',  'allow_null' : False }),
        ('titre'    , { 'size' : 80, 'explanation' : 'nom complet de la formation (ex: DUT R�seaux et T�l�communications',  'allow_null' : False }),
        ('titre_officiel'    , { 'size' : 80, 'explanation' : 'nom officiel (pour les PV de jury)', 'allow_null' : False }),
        ('type_parcours', { 'input_type' : 'menu',
                            'title' : 'Type de parcours',
                            'type' : 'int',
                            'allowed_values' : sco_codes_parcours.FORMATION_PARCOURS_TYPES,
                            'labels' : sco_codes_parcours.FORMATION_PARCOURS_DESCRS,
                            'explanation' : "d�termine notamment le nombre de semestres et les r�gles de validation d'UE et de semestres (barres)",
                            }),
        ('formation_code', { 'size' : 12, 'title' : 'Code formation', 'explanation' : 'code interne. Toutes les formations partageant le m�me code sont compatibles (compensation de semestres, capitalisation d\'UE).  Laisser vide si vous ne savez pas, ou entrer le code d\'une formation existante.' }),
        ),
                           initvalues = initvalues,
                           submitlabel = submitlabel)
    if tf[0] == 0:
        return '\n'.join(H) + tf[1] + context.sco_footer(REQUEST)
    elif tf[0] == -1:
        return REQUEST.RESPONSE.redirect( REQUEST.URL1 )
    else:
        # check unicity : constraint UNIQUE(acronyme,titre,version)
        if create:
            version = 1
        else:
            version = initvalues['version']
        args = { 'acronyme' : tf[2]['acronyme'],
                 'titre' :  tf[2]['titre'],
                 'version' : version }
        quote_dict(args)
        others = context.formation_list( args = args )
        if others and ((len(others) > 1) or others[0]['formation_id'] != formation_id):
            return '\n'.join(H) + tf_error_message("Valeurs incorrectes: il existe d�j� une formation avec m�me titre, acronyme et version.") + tf[1] + context.sco_footer(REQUEST)
        #
        if create:
            formation_id = context.do_formation_create(tf[2], REQUEST)
        else:
            do_formation_edit(context, tf[2])
        return REQUEST.RESPONSE.redirect( 'ue_list?formation_id=%s' % formation_id )

def do_formation_edit(context, args):
    "edit a formation"
    log('do_formation_edit( args=%s )'%args)
    
    #if context.formation_has_locked_sems(args[0]['formation_id']):
    #    raise ScoLockedFormError()
    # nb: on autorise finalement la modif de la formation meme si elle est verrouillee
    # car cela ne change que du cosmetique, (sauf eventuellement le code formation ?)

    # On ne peut pas supprimer le code formation:
    if args.has_key('formation_code') and not args['formation_code']:
        del args['formation_code']
    
    cnx = context.GetDBConnexion()
    context._formationEditor.edit( cnx, args )
    
    # Invalide les semestres utilisant cette formation:
    for sem in context.do_formsemestre_list(args={ 'formation_id' : args['formation_id'] } ):
        context._inval_cache(formsemestre_id=sem['formsemestre_id']) #> formation modif.     
