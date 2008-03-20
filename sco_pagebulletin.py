# -*- mode: python -*-
# -*- coding: iso8859-15 -*-

##############################################################################
#
# Gestion scolarite IUT
#
# Copyright (c) 2001 - 2006 Emmanuel Viennet.  All rights reserved.
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

"""Mise en page des bulletins de notes (pdf)
"""

from notesdb import *
from notes_log import log
from sco_utils import SCO_ENCODING
from TrivialFormulator import TrivialFormulator, TF

_notes_formsemestre_pagebulletin_editor = EditableTable(
    'notes_formsemestre_pagebulletin',
    'formsemestre_id', # meme cle
    ('formsemestre_id',
     'left_margin', 'top_margin', 'right_margin', 'bottom_margin',
     'title', 'intro_mail' ),
    allow_set_id=True # car on utilise le formsemestre_id comme clé
    )


notes_formsemestre_pagebulletin_create = _notes_formsemestre_pagebulletin_editor.create
notes_formsemestre_pagebulletin_list = _notes_formsemestre_pagebulletin_editor.list
notes_formsemestre_pagebulletin_edit = _notes_formsemestre_pagebulletin_editor.edit


def formsemestre_pagebulletin_get(context, formsemestre_id):
    "dict with pagebulletin values"
    cnx = context.GetDBConnexion()
    vals = notes_formsemestre_pagebulletin_list(cnx, {'formsemestre_id' : formsemestre_id})
    if vals:
        return vals[0]
    else:
        vals =_notes_formsemestre_pagebulletin_editor.get_sql_default_values(cnx)
        return vals
        
# ---- Parameters setting dialog
def formsemestre_pagebulletin_dialog(context, REQUEST=None,
                                     formsemestre_id=None):
    """
    If no existing values, create a new object with default, else edit existing
    """
    assert formsemestre_id
    cnx = context.GetDBConnexion()
    initvalues = notes_formsemestre_pagebulletin_list(cnx, {'formsemestre_id' : formsemestre_id})
    if initvalues:
        initvalues = initvalues[0]
        create = False
    else:
        initvalues = _notes_formsemestre_pagebulletin_editor.get_sql_default_values(cnx)
        create = True
    #    
    form = [
        ('formsemestre_id', { 'input_type' : 'hidden' }),
        ('sep', { 'input_type' : 'separator',
                  'title' : '<h3>Marges <em>additionnelles</em>, en millimètres</h3><p class="help">Le tableau est toujours redimensionné pour occuper l\'espace disponible entre les marges.</p>' }),
        ('left_margin', {'size' : 20, 'title' : 'Marge gauche' }),
        ('top_margin', {'size' : 20, 'title' : 'Marge haute' }),
        ('right_margin', {'size' : 20, 'title' : 'Marge droite' }),
        ('bottom_margin', {'size' : 20, 'title' : 'Marge basse' }),
        ('sep', { 'input_type' : 'separator',
                  'title' : '<h3>Titre des bulletins</h3>' }),
        ('title', {'size' : 70, 'title' : '', 'explanation' : '<tt>%(DeptName)s</tt> est remplacé par le nom du département' }),
        ('sep', { 'input_type' : 'separator',
                  'title' : '<h3>Envoi des bulletins par e-mail : message d\'accompagnement</h3>' }),
        ('intro_mail', { 'input_type' : 'textarea',
                         'title' : '',
                         'explanation' : '<tt>%(DeptName)s</tt> est remplacé par le nom du département, <tt>%(nomprenom)s</tt> par les noms et prénoms de l\'étudiant, <tt>%(dept)s</tt> par le nom du département, et <tt>%(webmaster)s</tt> par l\'adresse mail du Webmaster.',
                         'rows' : 18,
                         'cols' : 85 })
        ]
    tf = TrivialFormulator( REQUEST.URL0, REQUEST.form, form,
                            submitlabel = 'OK',
                            cancelbutton = 'Annuler',
                            initvalues = initvalues)
    if tf[0] == 0:
        header = context.sco_header(REQUEST,
                                    page_title='Mise en page des bulletins')
        footer = context.sco_footer(REQUEST)
        sem = context.do_formsemestre_list({'formsemestre_id':formsemestre_id})[0]
        H = [ '<h2>Ces paramètres affectent les bulletins en PDF ("version papier") du semestre <em>%s</em> uniquement.</h2>' % sem['titreannee']
              ]
        return header + '\n'.join(H) + tf[1] + footer # formulaire HTML
    elif tf[0] == -1:
        # Annulation
        return REQUEST.RESPONSE.redirect('formsemestre_status?formsemestre_id=%s' % formsemestre_id)
    else:
        if create:
            log('tf2=' + str(tf[2]))
            oid = notes_formsemestre_pagebulletin_create(cnx, tf[2])
        else: # edit existing
            notes_formsemestre_pagebulletin_edit(cnx, tf[2])
        # ceci affecte les PDF cachés:
        context._inval_cache(formsemestre_id=formsemestre_id,pdfonly=True)
        return REQUEST.RESPONSE.redirect('formsemestre_status?formsemestre_id=%s' % formsemestre_id)

