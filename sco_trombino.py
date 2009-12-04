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

"""Photos: trombinoscopes
"""

try: from cStringIO import StringIO
except: from StringIO import StringIO
from zipfile import ZipFile, BadZipfile
import xml
import tempfile

from notes_log import log
from sco_utils import *
from scolars import format_nom, format_prenom, format_sexe
import sco_photos
import sco_groups
import sco_portal_apogee
from sco_formsemestre_status import makeMenu
from sco_pdf import *
import ImportScolars
import sco_excel
from reportlab.lib import colors

NB_COLS = 5 # nb of columns of photo grid (should be a preference ?)

def trombino(context,REQUEST, group_id,
             etat=None,
             format = 'html', dialog_confirmed=False ):
    """Trombinoscope"""
    members, group, group_tit, sem, nbdem, other_partitions = sco_groups.get_group_infos(context, group_id, etat=etat)
    
    args='group_id=%s' % group_id
    if etat:
        args += '&etat=%s' % etat
    #
    if format != 'html' and not dialog_confirmed:
        # check that we have local copies of all images
        nb_missing = 0
        for t in members:
            etudid = t['etudid']
            url = sco_photos.etud_photo_url(context, t) # -> copy distant files if needed
            if not sco_photos.etud_photo_is_local(context, t):
                nb_missing += 1
        if nb_missing > 0:
            parameters = { 'group_id' : group_id, 'etat' : etat, 'format' : format }
            return context.confirmDialog(
                """<p>Attention: %d photos ne sont pas disponibles et ne peuvent pas être exportées.</p><p>Vous pouvez <a class="stdlink" href="trombino?%s&format=%s&dialog_confirmed=1">exporter seulement les photos existantes</a>""" % (nb_missing, args, format ),
                dest_url = 'trombino',
                OK = 'Exporter seulement les photos existantes',
                cancel_url="trombino?%s"%args,
                REQUEST=REQUEST, parameters=parameters )
    
    if format == 'zip':
        return _trombino_zip(context, members, REQUEST)
    elif format == 'pdf':
        return _trombino_pdf(context, sem, group_tit, members, REQUEST)
    else:
        return _trombino_html_header(context, REQUEST) + _trombino_html(context, group, members, REQUEST=REQUEST) + context.sco_footer(REQUEST)

def _trombino_html_header(context, REQUEST):
    return context.sco_header(REQUEST, javascripts=[ 'jQuery/jquery.js', 
                                                     'js/trombino.js' ])

def _trombino_html(context, group, members, REQUEST=None):
    "HTML snippet for trombino (with title and menu)"
    args='group_id=%(group_id)s' % group
    menuTrombi = [
        { 'title' : 'Version PDF (imprimable)',
          'url' : 'trombino?%s&format=pdf' % args,
          },
        { 'title' : 'Charger des photos...',
          'url' : 'photos_import_files_form?group_id=%(group_id)s' % group,
          },
        { 'title' : 'Obtenir archive Zip des photos',
          'url' : 'trombino?%s&format=zip' % args,
          },
        { 'title' : 'Recopier les photos depuis le portail',
          'url' : 'trombino_copy_photos?%s' % args,
          }
        ]
    
    if members:
        if group['group_name'] != None:
            ng = 'Groupe %s' % group['group_name']
        else:
            ng = 'Tous les étudiants'
    else:
        ng = "Aucun étudiant inscrit dans ce semestre !"
    H = [ '<table style="padding-top: 10px; padding-bottom: 10px;"><tr><td><span style="font-style: bold; font-size: 150%%; padding-right: 20px;">%s</span></td>' % (ng) ]
    if members:
        H.append( '<td>' + makeMenu( 'Photos', menuTrombi ) + '</td>' )
    H.append('</tr></table>')
    H.append('<div><table width="100%">')
    i = 0
    for t in members:
        if i % NB_COLS == 0:
            H.append('<tr>')
        H.append('<td align="center">')
        if sco_photos.has_photo(context, t, version=sco_photos.H90):
            foto = sco_photos.etud_photo_html(context, t, title='fiche de '+ t['nom'], REQUEST=REQUEST)
        else: # la photo n'est pas immédiatement dispo
            foto = '<span class="unloaded_img" id="%s"><img border="0" height="90" alt="en cours" src="/ScoDoc/static/photos/loading.jpg"/></span>' % t['etudid']
        H.append('<a href="ficheEtud?etudid='+t['etudid']+'">'+foto+'</a>')
        H.append('<br/>' + t['prenom'] + '<br/>' + t['nom'] )
        H.append('</td>')
        i += 1
        if i % NB_COLS == 0:
            H.append('</tr>')
    H.append('</table><div>')
    # H.append('<p style="font-size:50%%"><a href="trombino?%s">Archive zip des photos</a></p>' % args)
    return  '\n'.join(H)
    

def _trombino_zip(context, T, REQUEST ):
    "Send photos as zip archive"
    data = StringIO()
    Z = ZipFile( data, 'w' )                        
    # assume we have the photos (or the user acknowledged the fact)
    # Archive originals (not reduced) images, in JPEG
    for t in T:
        rel_path = sco_photos.has_photo(context, t)
        if not rel_path:
            continue
        path = SCO_SRCDIR + '/' + rel_path
        img = open(path).read()
        code_nip = t['code_nip']
        if code_nip:
            filename = code_nip + '.jpg'
        else:
            filename = t['nom'] + '_' + t['prenom'] + '_' + t['etudid'] + '.jpg'
        Z.writestr( filename, img )
    Z.close()
    size = data.tell()
    log('trombino_zip: %d bytes'%size)
    content_type = 'application/zip'
    REQUEST.RESPONSE.setHeader('Content-Disposition',
                               'attachement;filename="trombi.zip"'  )
    REQUEST.RESPONSE.setHeader('Content-Type', content_type)
    REQUEST.RESPONSE.setHeader('Content-Length', size)
    return data.getvalue()


# Copy photos from portal to ScoDoc
def trombino_copy_photos(context, group_id, REQUEST=None, dialog_confirmed=False):
    "Copy photos from portal to ScoDoc (overwriting local copy)"
    members, group, group_tit, sem, nbdem, other_partitions = sco_groups.get_group_infos(context, group_id, etat=None)
    if group['group_name'] != None:
        ng = 'Groupe %s' % group['group_name']
    else:
        ng = 'Tous les étudiants'
    portal_url = sco_portal_apogee.get_portal_url(context)
    header = context.sco_header(REQUEST, page_title='Chargement des photos') 
    footer = context.sco_footer(REQUEST)
    if not portal_url:
        return header + '<p>portail non configuré</p><p><a href="trombino?group_id=%s">Retour au trombinoscope</a></p>'%group_id + footer
    if not dialog_confirmed:
        return context.confirmDialog(
                """<h2>Copier les photos du portail vers ScoDoc ?</h2>
                <p>Les photos du groupe %s présentes dans ScoDoc seront remplacées par celles du portail (si elles existent).</p>
                <p>(les photos sont normalement automatiquement copiées lors de leur première utilisation, l'usage de cette fonction n'est nécessaire que si les photos du portail ont été modifiées)</p>
                """ % (ng),
                dest_url="", REQUEST=REQUEST,
                cancel_url="trombino?group_id=%s" % group_id,
                parameters={'group_id': group_id})
    
    msg = []
    nok = 0
    for etud in members:
        path, diag = sco_photos.copy_portal_photo_to_fs(context, etud)
        msg.append(diag)
        if path:
            nok += 1
    
    msg.append('<b>%d photos correctement chargées</b>' % nok )
    args='group_id=%s' % group_id
    if etat:
        args += '&etat=%s' % etat            

    return header + '<h2>Chargement des photos depuis le portail</h2><ul><li>' + '</li><li>'.join(msg) + '</li></ul>' + '<p><a href="trombino?%s">retour au trombinoscope</a>' % args + footer


def _trombino_pdf(context, sem, ng, T, REQUEST):
    "Send photos as pdf page"
    # Generate PDF page
    objects = []
    StyleSheet = styles.getSampleStyleSheet()
    report = StringIO() # in-memory document, no disk file
    filename = ('trombino-%s.pdf' % ng ).replace(' ', '_') # XXX should sanitize this filename
    objects.append(Paragraph(SU("Trombinoscope " + sem['titreannee'] + ' ' + ng ), StyleSheet["Heading3"]))
    PHOTOWIDTH = 3*cm
    COLWIDTH = 3.6*cm
    N_PER_ROW = 5 # XXX should be in ScoDoc preferences
    L = []
    n = 0
    currow = []
    for t in T:
        rel_path = sco_photos.has_photo(context, t, version=sco_photos.H90)
        if not rel_path:
            rel_path = sco_photos.unknown_image_path()
        path = SCO_SRCDIR + '/' + rel_path
        try:
            elem = Table(
                [ [ Image( path, width=PHOTOWIDTH ) ],
                  [ Paragraph(
                SU(format_sexe(t['sexe']) + ' ' + format_prenom(t['prenom'])
                   + ' ' + format_nom(t['nom'])), StyleSheet['Normal']) ] ],
                colWidths=[ PHOTOWIDTH ] )
        except:
            log('*** exception while processing photo of %s (%s) (path=%s)' % (t['nom'], t['etudid'], path))
            raise 
        currow.append( elem )
        if n == (N_PER_ROW-1):
            L.append(currow)
            currow = []
        n = (n+1) % N_PER_ROW
    if currow:
        currow += [' ']*(N_PER_ROW-len(currow))
        L.append(currow)
    # log(L)
    table = Table( L, colWidths=[ COLWIDTH ]*N_PER_ROW,
                   style = TableStyle( [
        # ('RIGHTPADDING', (0,0), (-1,-1), -5*mm),
        ('VALIGN', (0,0), (-1,-1), 'TOP'),
        ('GRID', (0,0), (-1,-1), 0.25, colors.grey)
        ] ) )
    objects.append(table)
    # Build document
    document = BaseDocTemplate(report)
    document.addPageTemplates(ScolarsPageTemplate(document, preferences=context.get_preferences(sem['formsemestre_id'])))
    document.build(objects)
    data = report.getvalue()
    
    return sendPDFFile(REQUEST, data, filename)

# ---------------------    Upload des photos de tout un groupe
def photos_generate_excel_sample(context, group_id=None, REQUEST=None):
    """Feuille excel pour import fichiers photos
    """    
    format = ImportScolars.sco_import_format()
    data = ImportScolars.sco_import_generate_excel_sample(
        format, context=context, group_id=group_id,
        only_tables=['identite'], 
        exclude_cols=[ 'date_naissance', 'lieu_naissance', 'nationalite', 'photo_filename' ],
        extra_cols = ['fichier_photo'])
    return sco_excel.sendExcelFile(REQUEST, data, 'ImportPhotos.xls')

def photos_import_files_form(context, group_id, REQUEST=None):
    """Formualaire pour importation photos
    """
    H = [context.sco_header(REQUEST, page_title='Import des photos des étudiants'),
         """<h2 class="formsemestre">Téléchargement des photos des étudiants</h2>
         <p><b>Vous pouvez aussi charger les photos individuellement via la fiche de chaque étudiant (menu "Etudiant" / "Changer la photo").</b></p>
         <p class="help">Cette page permet de charger en une seule fois les photos de plusieurs étudiants.<br/>
          Il faut d'abord remplir une feuille excel donnant les noms 
          des fichiers images (une image par étudiant).
         </p>
         <p class="help">Ensuite, réunir vos images dans un fichier zip, puis télécharger 
         simultanément le fichier excel et le fichier zip.
         </p>
        <ol>
        <li><a class="stdlink" href="photos_generate_excel_sample?group_id=%s">
        Obtenir la feuille excel à remplir</a>
        </li>
        <li style="padding-top: 2em;">
         """ % group_id]
    F = context.sco_footer(REQUEST)
    tf = TrivialFormulator(
        REQUEST.URL0, REQUEST.form,
        (('xlsfile', {'title' : 'Fichier Excel:', 'input_type' : 'file', 'size' : 40 }),
         ('zipfile', {'title' : 'Fichier zip:', 'input_type' : 'file', 'size' : 40 }),
         ('group_id', {'input_type' : 'hidden' }),
         ))
    
    if  tf[0] == 0:
        return '\n'.join(H) + tf[1] + '</li></ol>' + F
    elif tf[0] == -1:
        return REQUEST.RESPONSE.redirect( 'sco_trombino?group_id=' + group_id )
    else:
        return photos_import_files(context, group_id=tf[2]['group_id'],
                                   xlsfile=tf[2]['xlsfile'],
                                   zipfile=tf[2]['zipfile'],
                                   REQUEST=REQUEST)

def photos_import_files(context, group_id=None, xlsfile=None, zipfile=None, REQUEST=None):
    """Importation des photos
    """
    members, group, group_tit, sem, nbdem, other_partitions = sco_groups.get_group_infos(context, group_id)
    # 1- build mapping etudid -> filename
    exceldata = xlsfile.read()
    if not exceldata:
        raise ScoValueError("Fichier excel vide ou invalide")
    diag, data = sco_excel.Excel_to_list(exceldata)
    if not data: # probably a bug
        raise ScoValueError('Fichier excel vide !')
    # on doit avoir une colonne etudid et une colonne 'fichier_photo'
    titles = data[0]
    try:
        etudid_idx = titles.index('etudid')
        filename_idx = titles.index('fichier_photo')
    except:
        raise ScoValueError('Fichier excel incorrect (il faut une colonne etudid et une colonne fichier_photo) !')

    def normfilename(fn):
        "normalisation used to match filenames"
        fn = fn.replace('\\','/') # not sure if this is necessary ?
        fn = fn.lower().strip()
        fn = fn.split('/')[-1] # use only last component, not directories
        return fn

    Filename2Etud = {} # filename : etudid
    for l in data[1:]:
        filename = l[filename_idx].strip()
        if filename:
            Filename2Etud[normfilename(filename)] = l[etudid_idx]
        
    # 2- Ouvre le zip et 
    try:
        z = ZipFile(zipfile)
    except BadZipfile:
        raise ScoValueError('Fichier ZIP incorrect !')
    ignored_zipfiles = []
    stored = [] # [ (etud, filename) ]
    for name in z.namelist():
        if len(name) > 4 and name[-1] != '/' and '.' in name:
            data = z.read(name)
            # match zip filename with name given in excel
            normname = normfilename(name)
            if normname in Filename2Etud:
                etudid = Filename2Etud[normname]
                # ok, store photo
                try:
                    etud = context.getEtudInfo(etudid=etudid, filled=True)[0]
                    del Filename2Etud[normname]
                except:
                    raise ScoValueError('ID étudiant invalide: %s' % etudid)                
                sco_photos.store_photo(context, etud, data, REQUEST=REQUEST)
                stored.append( (etud, name) )
            else:
                log('zip: zip name %s not in excel !' % name)
                ignored_zipfiles.append(name)
        else:
            if name[-1] != '/':
                ignored_zipfiles.append(name)
            log('zip: ignoring %s' % name)
    if Filename2Etud:
        # lignes excel non traitées
        unmatched_files = Filename2Etud.keys()
    else:
        unmatched_files = []
    # 3- Result page
    H = [_trombino_html_header(context, REQUEST),
         """<h2 class="formsemestre">Téléchargement des photos des étudiants</h2>
         <h3>Opération effectuée</h3>
         """ ]
    if ignored_zipfiles:
        H.append('<h4>Fichiers ignorés dans le zip:</h4><ul>')
        for name in ignored_zipfiles:
            H.append('<li>%s</li>' % name)
        H.append('</ul>')
    if unmatched_files:
        H.append('<h4>Fichiers indiqués dans feuille mais non trouvés dans le zip:</h4><ul>')
        for name in unmatched_files:
            H.append('<li>%s</li>' % name)
        H.append('</ul>')
    if stored:
        H.append('<h4>Images chargées:</h4><ul>')
        for (etud, name) in stored:
            H.append('<li>%s: <tt>%s</tt></li>' % (etud['nomprenom'], name))
        H.append('</ul>')
    
    return '\n'.join(H) + _trombino_html(context, group, members, REQUEST=REQUEST) + context.sco_footer(REQUEST)
