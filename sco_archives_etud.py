# -*- mode: python -*-
# -*- coding: iso8859-15 -*-

##############################################################################
#
# Gestion scolarite IUT
#
# Copyright (c) 2001 - 2012 Emmanuel Viennet.  All rights reserved.
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

"""ScoDoc : gestion des fichiers archiv�s associ�s aux �tudiants
     Il s'agit de fichiers quelconques, g�n�ralement utilis�s pour conserver
     les dossiers d'admission et autres pi�ces utiles. 
"""

from sco_utils import *
from notes_log import log

from sco_archives import BaseArchiver

class EtudsArchiver(BaseArchiver):
    def __init__(self):
        BaseArchiver.__init__(self, archive_type='docetuds')

EtudsArchive = EtudsArchiver()

def can_edit_etud_archive(context, authuser):
    """True si l'utilisateur peut modifier les archives etudiantes
    """
    return authuser.has_permission(ScoEtudAddAnnotations, context)

def etud_list_archives_html(context, REQUEST, etudid):
    """HTML snippet listing archives
    """
    can_edit = can_edit_etud_archive(context, REQUEST.AUTHENTICATED_USER)
    L = []
    for archive_id in EtudsArchive.list_obj_archives(context, etudid):
        a = { 'archive_id' : archive_id, 
              'description' : EtudsArchive.get_archive_description(archive_id),
              'date' : EtudsArchive.get_archive_date(archive_id),
              'content' : EtudsArchive.list_archive(archive_id) }
        L.append(a)
    delete_icon = icontag('delete_small_img', title="Supprimer fichier", alt="supprimer")
    delete_disabled_icon = icontag('delete_small_dis_img', title="Suppression non autoris�e")
    H = ['<div class="etudarchive"><ul>']
    for a in L:
        archive_name = EtudsArchive.get_archive_name(a['archive_id'])
        H.append("""<li><span class ="etudarchive_descr" title="%s">%s</span>"""
                 % (a['date'].strftime('%d/%m/%Y %H:%M'), a['description']))
        for filename in a['content']:
            H.append("""<a class="stdlink etudarchive_link" href="etud_get_archived_file?etudid=%s&archive_name=%s&filename=%s">%s</a>"""
                     % (etudid, archive_name, filename, filename))
        if not a['content']:
            H.append('<em>aucun fichier !</em>')
        if can_edit:
            H.append('<span class="deletudarchive"><a class="smallbutton" href="etud_delete_archive?etudid=%s&archive_name=%s">%s</a></span>'
                     % (etudid, archive_name, delete_icon))
        else:
            H.append('<span class="deletudarchive">' + delete_disabled_icon + '</span>')
        H.append('</li>')
    if can_edit:
        H.append('<li class="addetudarchive"><a class="stdlink" href="etud_upload_file_form?etudid=%s">ajouter un fichier</a></li>' % etudid)
    H.append('</ul></div>')
    return ''.join(H)

def etud_upload_file_form(context, REQUEST, etudid):
    """Page with a form to choose and upload a file, with a description.
    """
    # check permission
    if not can_edit_etud_archive(context, REQUEST.AUTHENTICATED_USER):
        raise AccessDenied('op�ration non autoris�e pour %s' % str(REQUEST.AUTHENTICATED_USER))
    etud = context.getEtudInfo(filled=1, REQUEST=REQUEST)[0]
    H = [context.sco_header(REQUEST, page_title="Chargement d'un document associ� � %(nomprenom)s" % etud),
         """<h2>Chargement d'un document associ� � %(nomprenom)s</h2>                     
         """ % etud,
         """<p>Le fichier ne doit pas d�passer %sMo.</p>             
         """ % (CONFIG.ETUD_MAX_FILE_SIZE/(1024*1024))]
    tf = TrivialFormulator(
        REQUEST.URL0, REQUEST.form, 
        ( ('etudid',  { 'default' : etudid, 'input_type' : 'hidden' }),
          ('datafile', { 'input_type' : 'file', 'title' : 'Fichier', 'size' : 30 }),
          ('description', { 'input_type' : 'textarea', 'rows' : 4, 'cols' : 77,
                            'title' : 'Description' }),
          ),
        submitlabel = 'Valider', cancelbutton='Annuler'
        )
    if  tf[0] == 0:
        return '\n'.join(H) + tf[1] + context.sco_footer(REQUEST)
    elif tf[0] == -1:
        return REQUEST.RESPONSE.redirect( REQUEST.URL1 + '/ficheEtud?etudid=' + etudid )
    else:
        data = tf[2]['datafile'].read()
        descr= tf[2]['description']
        filename = tf[2]['datafile'].filename
        _store_etud_file_to_new_archive(context, REQUEST, etudid, data, filename, description=descr)
        return REQUEST.RESPONSE.redirect( REQUEST.URL1 + '/ficheEtud?etudid=' + etudid )

def _store_etud_file_to_new_archive(context, REQUEST, etudid, data, filename, description=''):
    """Store data to new archive.
    """
    filesize = len(data)
    if filesize < 10 or filesize > CONFIG.ETUD_MAX_FILE_SIZE:
        return 0, 'Fichier image de taille invalide ! (%d)' % filesize
    archive_id = EtudsArchive.create_obj_archive(context, etudid, description)
    EtudsArchive.store(archive_id, filename, data )
    

def etud_delete_archive(context, REQUEST, etudid, archive_name, dialog_confirmed=False):
    """Delete an archive
    """
    # check permission
    if not can_edit_etud_archive(context, REQUEST.AUTHENTICATED_USER):
        raise AccessDenied('op�ration non autoris�e pour %s' % str(REQUEST.AUTHENTICATED_USER))
    etud = context.getEtudInfo(filled=1, REQUEST=REQUEST)[0]
    archive_id = EtudsArchive.get_id_from_name(context, etudid, archive_name)
    dest_url = "ficheEtud?etudid=%s" % etudid
    if not dialog_confirmed:
        return context.confirmDialog(
            """<h2>Confirmer la suppression des fichiers ?</h2>
            <p>Fichier associ� le %s � l'�tudiant %s</p>
               <p>La suppression sera d�finitive.</p>"""
            % (EtudsArchive.get_archive_date(archive_id).strftime('%d/%m/%Y %H:%M'),
               etud['nomprenom']),
            dest_url="", REQUEST=REQUEST, cancel_url=dest_url, 
            parameters={'etudid' : etudid, 'archive_name' : archive_name })
    
    EtudsArchive.delete_archive(archive_id)
    return REQUEST.RESPONSE.redirect(dest_url+'&head_message=Archive%20supprim�e')

def etud_get_archived_file(context, REQUEST, etudid, archive_name, filename):
    """Send file to client.
    """
    return EtudsArchive.get_archived_file(context, REQUEST, etudid, archive_name, filename)

