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

"""ScoDoc : gestion des archives des PV et bulletins


 Archives are plain files, stored in 
    .../var/scodoc/archives/deptid/formsemestre_id/YYYY-MM-DD-HH-MM-SS
"""

from mx.DateTime import DateTime as mxDateTime
import mx.DateTime
import shutil

from sco_utils import *
from notesdb import *
import glob

import sco_pvjury, sco_excel, sco_pvpdf
from sco_recapcomplet import make_formsemestre_recapcomplet

class Archiver:
    def __init__(self):
        dirs = [ os.environ['INSTANCE_HOME'], 'var', 'scodoc', 'archives' ]
        self.root = os.path.join(*dirs)
        log('initialized archiver, path='+self.root)
        path = dirs[0]
        for dir in dirs[1:]:
            path = os.path.join(path, dir)
            if not os.path.isdir(path):
                log('creating directory %s' % path)
                os.mkdir(path)
    
    def get_formsemestre_dir(self, context, formsemestre_id):
        """Returns path to directory of archives for this dept.
        If directory does not yet exist, create it.
        """
        dept_dir = os.path.join(self.root, context.DeptId())
        if not os.path.isdir(dept_dir):
            log('creating directory %s' % dept_dir)
            os.mkdir(dept_dir)
        formsemestre_dir = os.path.join(dept_dir, formsemestre_id)
        if not os.path.isdir(formsemestre_dir):
            log('creating directory %s' % formsemestre_dir)
            os.mkdir(formsemestre_dir)
        return formsemestre_dir

    def list_formsemestre_archives(self, context, formsemestre_id):
        """Returns a list of archive identifiers for this formsemestre
        (paths to non empty dirs)
        """
        base = self.get_formsemestre_dir(context, formsemestre_id)+os.path.sep
        dirs = glob.glob( base
                          +'[0-9][0-9][0-9][0-9]-[0-9][0-9]-[0-9][0-9]-[0-9][0-9]-[0-9][0-9]-[0-9][0-9]')
        dirs = [ os.path.join(base,d) for d in dirs ]
        dirs = [ d for d in dirs if os.path.isdir(d) and os.listdir(d) ] # non empty dirs
        dirs.sort()
        return dirs

    def delete_formsemestre_archive(self, archive_id):
        """Delete (forever) this archive"""
        shutil.rmtree(archive_id, ignore_errors=True)
            
    def get_archive_date(self, archive_id):
        """Returns date (as a DateTime object) of an archive"""
        dt = [int(x) for x in os.path.split(archive_id)[1].split('-')]
        return mxDateTime( *dt )

    def list_archive(self, archive_id):
        """Return list of filenames (without path) in archive"""
        files = os.listdir(archive_id)
        files.sort()
        return [ f for f in files if f and f[0] != '_' ]

    def get_archive_name(self, archive_id):
        """name identifying archive, to be used in web URLs"""
        return os.path.split(archive_id)[1]

    def is_valid_archive_name(self, archive_name):
        """check if name is valid."""
        return re.match('^[0-9]{4}-[0-9]{2}-[0-9]{2}-[0-9]{2}-[0-9]{2}-[0-9]{2}$', archive_name)

    def get_id_from_name(self, context, formsemestre_id, archive_name):
        """returns archive id (check that name is valid)"""
        if not self.is_valid_archive_name(archive_name):
            raise ValueError('invalid archive name')
        archive_id = os.path.join( self.get_formsemestre_dir(context, formsemestre_id), archive_name)
        if not os.path.isdir(archive_id):
            raise ValueError('invalid archive name')
        return archive_id
    
    def get_archive_description(self, archive_id):
        """Return description of archive"""
        return open(os.path.join(archive_id, '_description.txt')).read()
    
    def create_formsemestre_archive(self, context, formsemestre_id, description):
        """Creates a new archive for this formsemestre
        and returns its id."""
        archive_id = self.get_formsemestre_dir(context, formsemestre_id) + os.path.sep + '-'.join([ '%02d'%x for x in time.localtime()[:6] ])
        log('creating archive: %s' % archive_id)
        os.mkdir(archive_id) # if exists, raises an OSError
        self.store( archive_id, '_description.txt', description ) 
        return archive_id

    valid_cars = '-abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789_.' # no / !
    valid_cars_set = Set(valid_cars)
    valid_exp = re.compile('^['+valid_cars+']+$')
    def sanitize_filename(self, filename):
        """Keep only valid cars"""
        sane = ''.join( [ c for c in filename if c in self.valid_cars_set ] )
        if len(sane) < 2:
            sane = time.time() + '-' + sane
        return sane
    def is_valid_filename(self, filename):
        """True if filename is safe"""
        return self.valid_exp.match(filename)

    def store(self, archive_id, filename, data):
        """Store data in archive, under given filename. 
        Filename may be modified (sanitized): return used filename
        The file is created or replaced.
        """
        filename = self.sanitize_filename(filename)
        log("storing %s (%d bytes) in %s" % (filename, len(data), archive_id))
        fname = os.path.join(archive_id, filename)
        f = open(fname, 'w')
        f.write(data)
        f.close()
        return filename

    def get(self, archive_id, filename):
        """Retreive data"""
        if not self.is_valid_filename(filename):
            log('Archiver.get: invalid filename "%s"' % filename)
            raise ValueError('invalid filename')
        fname = os.path.join(archive_id, filename)
        return open(fname).read()

Archive = Archiver()


# ----------------------------------------------------------------------------

def do_formsemestre_archive(context, REQUEST, formsemestre_id, description='', 
                            dateJury='', signature=None, # pour lettres indiv
                            dateCommission=None, numeroArrete=None, showTitle=False
                            ):
    """Make and store new archive for this formsemestre.
    Store:
    - tableau recap (xls)
    """
    archive_id = Archive.create_formsemestre_archive(context, formsemestre_id, description)
    date = Archive.get_archive_date(archive_id).strftime('%d/%m/%Y à %H:%M')
    # Tableau recap notes en XLS
    data, filename, format = make_formsemestre_recapcomplet(
        context, REQUEST, formsemestre_id, format='xls')
    if data:
        Archive.store(archive_id, 'Tableau_moyennes.xls', data)
    # Tableau recap notes en HTML
    data,  filename, format = make_formsemestre_recapcomplet(
        context, REQUEST, formsemestre_id, format='html', disable_etudlink=True)
    if data:
        data = '\n'.join([ 
                context.sco_header(REQUEST, page_title='Moyennes archivées le %s' % date,
                                   head_message='Moyennes archivées le %s' % date,
                                   no_side_bar=True),
                '<h2 class="fontorange">Valeurs archivées le %s</h2>' % date, 
                '<style type="text/css">table.notes_recapcomplet tr {  color: rgb(185,70,0); }</style>',
                data,
                context.sco_footer(REQUEST) ])
        Archive.store(archive_id, 'Tableau_moyennes.html', data)
    
    # Bulletins en XML
    data, filename, format = make_formsemestre_recapcomplet(
        context, REQUEST, formsemestre_id, format='xml', xml_with_decisions=True )
    if data:
        Archive.store(archive_id, 'Bulletins.xml', data)
    # Decisions de jury, en XLS
    data = sco_pvjury.formsemestre_pvjury(context, formsemestre_id, format='xls', REQUEST=REQUEST, publish=False)
    if data:
        Archive.store(archive_id, 'Decisions_Jury.xls', data)
    # Classeur bulletins (PDF)
    data, filename = context._get_formsemestre_bulletins_pdf(formsemestre_id, REQUEST, 
                                                             version='long' ) # pourrait etre param
    if data:
        Archive.store(archive_id, 'Bulletins.pdf', data )
    # Lettres individuelles (PDF):
    data = sco_pvpdf.pdf_lettres_individuelles(context, formsemestre_id,
                                               dateJury=dateJury, signature=signature)
    if data:
        Archive.store(archive_id, 'CourriersDecisions.pdf', data )
    # PV de jury (PDF):
    dpv = sco_pvjury.dict_pvjury(context, formsemestre_id, with_prev=True)
    data = sco_pvpdf.pvjury_pdf(context, dpv, REQUEST, 
                                dateCommission=dateCommission, numeroArrete=numeroArrete, 
                                dateJury=dateJury, showTitle=showTitle)
    if data:
        Archive.store(archive_id, 'PV_Jury.pdf', data )

def formsemestre_archive(context, REQUEST, formsemestre_id):
    """Make and store new archive for this formsemestre.
    """
    sem = context.get_formsemestre(formsemestre_id)
    H = [context.html_sem_header(REQUEST, 'Archiver les PV et résultats du semestre', sem),
         """<p class="help">Cette page permet de générer et d'archiver tous
les documents résultant de ce semestre: PV de jury, lettres individuelles, 
tableaux récapitulatifs.</p><p class="help">Les documents archivés sont 
enregistrés et non modifiables, on peut les retrouver ultérieurement.
</p><p class="help">On peut archiver plusieurs versions des documents (avant et après le jury par exemple).
</p>
         """
         ]
    F = [ """<p><em>Note: les documents sont aussi affectés par les réglages sur la page "<a href="edit_preferences">Paramétrage</a>" (accessible à l'administrateur du département).</em>
        </p>""",
        context.sco_footer(REQUEST) ]
    
    descr = [
        ('description', { 'input_type' : 'textarea', 'rows' : 4, 'cols' : 77,
                          'title' : 'Description' }),
        ('sep', { 'input_type' : 'separator', 'title' : 'Informations sur PV de jury'}),
        ]
    descr += sco_pvjury.descrform_pvjury(sem)
    descr += [
        ('signature',  {'input_type' : 'file', 'size' : 30, 'explanation' : 'optionnel: image scannée de la signature pour les lettres individuelles'}),
        ]
    tf = TrivialFormulator( REQUEST.URL0, REQUEST.form, descr,
                            cancelbutton = 'Annuler', method='POST',
                            submitlabel = 'Générer et archiver les documents', 
                            name='tf' )
    if  tf[0] == 0:
        return '\n'.join(H) + '\n' + tf[1] +  '\n'.join(F)
    elif tf[0] == -1:
        msg = 'Opération%20annulée'
    else:
        # submit
        sf = tf[2]['signature']
        signature = sf.read() # image of signature
        do_formsemestre_archive(context, REQUEST, formsemestre_id, description=tf[2]['description'],
                                dateJury=tf[2]['dateJury'], dateCommission=tf[2]['dateCommission'],
                                signature=signature, 
                                numeroArrete=tf[2]['numeroArrete'], showTitle=tf[2]['showTitle'])
        msg = 'Nouvelle%20archive%20créée'
    
    # submitted or cancelled:
    return REQUEST.RESPONSE.redirect( "formsemestre_list_archives?formsemestre_id=%s&head_message=%s" %(formsemestre_id, msg))

def formsemestre_list_archives(context, REQUEST, formsemestre_id):
    """Page listing archives
    """
    L = []
    for archive_id in Archive.list_formsemestre_archives(context, formsemestre_id):
        a = { 'archive_id' : archive_id, 
              'description' : Archive.get_archive_description(archive_id),
              'date' : Archive.get_archive_date(archive_id),
              'content' : Archive.list_archive(archive_id) }
        L.append(a)
    
    sem = context.get_formsemestre(formsemestre_id)
    H = [context.html_sem_header(REQUEST, 'Archive des PV et résultats ', sem)]
    if not L:
        H.append('<p>aucune archive enregistrée</p>')
    else:
        H.append('<ul>')
        for a in L:
            archive_name = Archive.get_archive_name(a['archive_id'])
            H.append('<li>%s : <em>%s</em> (<a href="formsemestre_delete_archive?formsemestre_id=%s&archive_name=%s">supprimer</a>)<ul>' % (a['date'].strftime('%d/%m/%Y %H:%M'), a['description'], formsemestre_id, archive_name))
            for filename in a['content']:
                H.append('<li><a href="formsemestre_get_archived_file?formsemestre_id=%s&archive_name=%s&filename=%s">%s</a></li>' % (formsemestre_id, archive_name, filename, filename))
            if not a['content']:
                H.append('<li><em>aucun fichier !</em></li>')
            H.append('</ul></li>')
        H.append('</ul>')
    
    return '\n'.join(H) + context.sco_footer(REQUEST)

def formsemestre_get_archived_file(context, REQUEST, formsemestre_id, archive_name, filename):
    """Send file to client.
    """
    sem = context.get_formsemestre(formsemestre_id)
    archive_id = Archive.get_id_from_name(context, formsemestre_id, archive_name)
    data = Archive.get(archive_id, filename)
    ext = os.path.splitext(filename)[1].lower()
    if ext == '.html' or ext == '.htm':
        return data
    elif ext == '.xml':
        REQUEST.RESPONSE.setHeader('Content-type', XML_MIMETYPE)
        return data
    elif ext == '.xls':
        return sco_excel.sendExcelFile(REQUEST,data,filename)
    elif ext == '.csv':
        return sendCSVFile(REQUEST, data, filename )
    elif ext == '.pdf':
        return sendPDFFile(REQUEST, data, filename )
    
    return data # should set mimetype...

def formsemestre_delete_archive(context, REQUEST, formsemestre_id, archive_name, dialog_confirmed=False):
    """Delete an archive
    """
    sem = context.get_formsemestre(formsemestre_id) # check formsemestre_id
    archive_id = Archive.get_id_from_name(context, formsemestre_id, archive_name)

    dest_url = "formsemestre_list_archives?formsemestre_id=%s" %(formsemestre_id)

    if not dialog_confirmed:
        return context.confirmDialog(
            """<h2>Confirmer la suppression de l'archive du %s ?</h2>
               <p>La suppression sera définitive.</p>""" % Archive.get_archive_date(archive_id).strftime('%d/%m/%Y %H:%M'),
            dest_url="", REQUEST=REQUEST, cancel_url=dest_url, 
            parameters={'formsemestre_id' : formsemestre_id, 'archive_name' : archive_name })
    
    Archive.delete_formsemestre_archive(archive_id)
    return REQUEST.RESPONSE.redirect(dest_url+'&head_message=Archive%20supprimée')
