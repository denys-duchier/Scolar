# -*- mode: python -*-
# -*- coding: utf-8 -*-

##############################################################################
#
# Gestion scolarite IUT
#
# Copyright (c) 2001 - 2013 Emmanuel Viennet.  All rights reserved.
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

"""Import / Export de formations
"""

from sco_utils import *
import xml.dom.minidom

from notesdb import *
from notes_log import log

def formation_export(context, formation_id, export_ids=False, format=None, REQUEST=None):
    """Get a formation, with UE, matieres, modules
    in desired format
    """
    F = context.formation_list(args={ 'formation_id' : formation_id})[0]
    ues = context.do_ue_list({ 'formation_id' : formation_id })
    F['ue'] = ues
    for ue in ues:
        ue_id = ue['ue_id']
        if not export_ids:
            del ue['ue_id']
            del ue['formation_id']
        if ue['ects'] is None:
            del ue['ects']
        mats = context.do_matiere_list({ 'ue_id' : ue_id })
        ue['matiere'] = mats
        for mat in mats:
            matiere_id = mat['matiere_id']
            if not export_ids:
                del mat['matiere_id']
                del mat['ue_id']
            mods = context.do_module_list({ 'matiere_id' : matiere_id })
            mat['module'] = mods
            for mod in mods:
                if not export_ids:
                    del mod['ue_id']
                    del mod['matiere_id']
                    del mod['module_id']
                    del mod['formation_id']
                if mod['ects'] is None:
                    del mod['ects']
        
    return sendResult(REQUEST, F, name='formation', format=format, force_outer_xml_tag=False)

ELEMENT_NODE = 1
TEXT_NODE = 3
def XMLToDicts(element, encoding):
    """Represent dom element as a dict
    Example:
       <foo x="1" y="2"><bar z="2"/></foo>
    will give us:
       ('foo', {'y': '2', 'x': '1'}, [('bar', {'z': '2'}, [])])
    """
    d = {}
    # attributes
    if element.attributes:
        for i in range(len(element.attributes)):
            a = element.attributes.item(i).nodeName.encode(encoding)
            v = element.getAttribute( element.attributes.item(i).nodeName )
            d[a] = v.encode(encoding)
    # descendants
    childs = []
    for child in element.childNodes:
        if child.nodeType == ELEMENT_NODE:
            childs.append( XMLToDicts(child, encoding) )
    return (element.nodeName.encode(encoding), d, childs)


def formation_import_xml(context, REQUEST, doc, encoding=SCO_ENCODING):
    """Create a formation from XML representation
    (format dumped by formation_export( format='xml' ))
    """
    log('formation_import_xml: doc=%s' % doc )
    try:
        dom = xml.dom.minidom.parseString(doc)
    except:
        log('formation_import_xml: invalid XML data')
        raise ScoValueError('Fichier XML invalide')
    
    f = dom.getElementsByTagName('formation')[0] # or dom.documentElement
    D = XMLToDicts(f,encoding)
    assert D[0] == 'formation'
    F = D[1]
    F_quoted = F.copy()
    log('F=%s' % F )
    quote_dict(F_quoted)
    log('F_quoted=%s' % F_quoted )
    # find new version number
    cnx = context.GetDBConnexion()
    cursor = cnx.cursor(cursor_factory=ScoDocCursor)
    log('select max(version) from notes_formations where acronyme=%(acronyme)s and titre=%(titre)s' % F_quoted)
    cursor.execute('select max(version) from notes_formations where acronyme=%(acronyme)s and titre=%(titre)s', F_quoted)
    res = cursor.fetchall()
    try:
        version = int(res[0][0]) + 1
    except:
        version = 1
    F['version'] = version
    # create formation
    #F_unquoted = F.copy()
    #unescape_html_dict(F_unquoted)
    formation_id = context.do_formation_create(F, REQUEST)
    log('formation %s created' % formation_id)
    ues_old2new = {} # xml ue_id : new ue_id
    modules_old2new = {} # xml module_id : new module_id
    # (nb: mecanisme utilise pour cloner semestres seulement, pas pour I/O XML)
    # -- create UEs    
    for ue_info in D[2]:
        assert ue_info[0] == 'ue'
        ue_info[1]['formation_id'] = formation_id
        if 'ue_id' in ue_info[1]:
            xml_ue_id = ue_info[1]['ue_id']
            del  ue_info[1]['ue_id']
        else:
            xml_ue_id = None            
        ue_id = context.do_ue_create(ue_info[1], REQUEST)
        if xml_ue_id:
            ues_old2new[xml_ue_id] = ue_id
        # -- create matieres
        for mat_info in ue_info[2]:
            assert mat_info[0] == 'matiere'
            mat_info[1]['ue_id'] = ue_id
            mat_id = context.do_matiere_create(mat_info[1], REQUEST)
            # -- create modules            
            for mod_info in mat_info[2]:
                assert mod_info[0] == 'module'
                if 'module_id' in mod_info[1]:
                    xml_module_id = mod_info[1]['module_id']
                    del  mod_info[1]['module_id']
                else:
                    xml_module_id = None
                mod_info[1]['formation_id'] = formation_id
                mod_info[1]['matiere_id'] = mat_id
                mod_info[1]['ue_id'] = ue_id
                mod_id = context.do_module_create(mod_info[1], REQUEST)
                if xml_module_id:
                    modules_old2new[xml_module_id] = mod_id
    
    return formation_id, modules_old2new, ues_old2new

