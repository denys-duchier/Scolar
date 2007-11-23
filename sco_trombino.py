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
from zipfile import ZipFile
import urllib, urllib2, xml
import tempfile

from notes_log import log
from sco_exceptions import *
from sco_utils import *
from scolars import format_nom, format_prenom, format_sexe

import sco_portal_apogee
from sco_formsemestre_status import makeMenu
from sco_pdf import *
from reportlab.lib import colors

def trombino(self,REQUEST,formsemestre_id,
             groupetd=None, groupetp=None, groupeanglais=None,
             etat=None, nbcols=5,
             format = 'html', dialog_confirmed=False ):
    """Trombinoscope"""
    T, nomgroupe, ng, sem, nbdem = self._getlisteetud(formsemestre_id,
                                                      groupetd,groupetp,groupeanglais,etat )
    args='formsemestre_id=%s' % formsemestre_id
    if groupetd:
        args += '&groupetd=%s' % groupetd
    if groupetp:
        args += '&groupetp=%s' % groupetp
    if groupeanglais:
        args += '&groupeanglais=%s' % groupeanglais
    if etat:
        args += '&etat=%s' % etat
    #
    if format != 'html' and not dialog_confirmed:
        # check that we have local copies of all images
        for t in T:
            etudid = t['etudid']
            if not self.etudfoto_islocal(etudid):
                parameters = { 'formsemestre_id' : formsemestre_id, 'etat' : etat, 'format' : format }
                if groupetd:
                    parameters['groupetd'] = groupetd
                if groupetp:
                    parameters['groupetp'] = groupetp
                if groupeanglais:
                    parameters['groupeanglais'] = groupeanglais
                return self.confirmDialog(
                    """<p>Attention: certaines photos ne sont pas stockées dans ScoDoc et ne peuvent pas être exportées.</p><p>Vous pouvez <a href="trombino_copy_photos?%s">copier les photos du portail dans ScoDoc</a> ou bien <a href="trombino?%s&format=zip&dialog_confirmed=1">exporter seulement les photos existantes</a>""" % (args, args),
                    dest_url = 'trombino',
                    OK = 'Exporter seulement les photos existantes',
                    cancel_url="trombino?%s"%args,
                    REQUEST=REQUEST, parameters=parameters )
    if format == 'zip':
        return _trombino_zip(self, T, REQUEST)
    elif format == 'pdf':
        return _trombino_pdf(self, sem, ng, T, REQUEST)
    else:
        menuTrombi = [
            { 'title' : 'Version PDF (imprimable)',
              'url' : 'trombino?%s&format=pdf' % args,
              },
            { 'title' : 'Archive Zip des photos',
              'url' : 'trombino?%s&format=zip' % args,
              },
            { 'title' : 'Copier les photos du portail',
              'url' : 'trombino_copy_photos?%s' % args,
              }
            ]
        nbcols = int(nbcols)
        H = [ '<table style="padding-top: 10px; padding-bottom: 10px;"><tr><td><span style="font-style: bold; font-size: 150%%; padding-right: 20px;"><a href="Notes/formsemestre_status?formsemestre_id=%s">%s %s</a></span></td>' % (formsemestre_id, sem['titre_num'], ng) ]            
        H.append( '<td>' + makeMenu( 'Photos', menuTrombi ) + '</td></tr></table>' )

        H.append('<div><table width="100%">')
        i = 0
        for t in T:
            if i % nbcols == 0:
                H.append('<tr>')
            H.append('<td align="center">')
            foto = self.etudfoto(t['etudid'],fototitle='fiche de '+ t['nom'],
                                 foto=t['foto'] )
            H.append('<a href="ficheEtud?etudid='+t['etudid']+'">'+foto+'</a>')
            H.append('<br>' + t['prenom'] + '<br>' + t['nom'] )
            H.append('</td>')
            i += 1
            if i % nbcols == 0:
                H.append('</tr>')
        H.append('</table><div>')
        # H.append('<p style="font-size:50%%"><a href="trombino?%s">Archive zip des photos</a></p>' % args)
        return self.sco_header(REQUEST)+'\n'.join(H)+self.sco_footer(REQUEST)

def _trombino_zip(self, T, REQUEST ):
    "Send photos as zip archive"
    data = StringIO()
    Z = ZipFile( data, 'w' )                        
    # assume we have the photos (or the user acknowledged the fact)
    for t in T:
        fotoimg=self.etudfoto_img(t['etudid'],foto=t['foto'])
        code_nip = t['code_nip']
        if code_nip:
            filename = code_nip + '.jpg'
        else:
            filename = t['nom'] + '_' + t['prenom'] + '_' + t['etudid'] + '.jpg'
        Z.writestr( filename, fotoimg.data )
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
def trombino_copy_photos(self, formsemestre_id,
             groupetd=None, groupetp=None, groupeanglais=None,
             etat=None,REQUEST=None):
    "Copy photos from portal to ScoDoc (only if we don't have a local copy)"
    T, nomgroupe, ng, sem, nbdem = self._getlisteetud(formsemestre_id,
                                                      groupetd,groupetp,groupeanglais,etat )
    portal_url = sco_portal_apogee.get_portal_url(self)
    header = self.sco_header(REQUEST, page_title='Chargement des photos') 
    footer = self.sco_footer(REQUEST)
    if not portal_url:
        return header + '<p>portail non configuré</p>' + footer
    msg = []
    nok = 0
    for etud in T:
        etudid = etud['etudid']
        if not self.etudfoto_islocal(etudid):
            if not etud['code_nip']:
                msg.append('%s: pas de code NIP' % self.nomprenom(etud))
            else:
                url = portal_url + '/getPhoto.php?nip=' + etud['code_nip']
                f = None
                try:
                    f = urllib2.urlopen( url )
                except:
                    msg.append('%s: erreur chargement de %s' % (self.nomprenom(etud), url))
                if f:
                    # Store file in Zope
                    buf = StringIO()
                    buf.write( f.read() )
                    buf.seek(0)
                    status, diag = self.doChangePhoto( etudid, buf, REQUEST, suppress=True )
                    if status == 1:
                        msg.append('%s: photo chargée' % self.nomprenom(etud))
                        nok += 1
                    else:
                        msg.append('%s: <b>%s</b>' % (self.nomprenom(etud), diag))
    msg.append('<b>%d photos correctement chargées</b>' % nok )
    args='formsemestre_id=%s' % formsemestre_id
    if groupetd:
        args += '&groupetd=%s' % groupetd
    if groupetp:
        args += '&groupetp=%s' % groupetp
    if groupeanglais:
        args += '&groupeanglais=%s' % groupeanglais
    if etat:
        args += '&etat=%s' % etat            

    return header + '<h2>Chargement des photos depuis le portail</h2><ul><li>' + '</li><li>'.join(msg) + '</li></ul>' + '<p><a href="trombino?%s">retour au trombinoscope</a>' % args + footer


def _trombino_pdf(self, sem, ng, T, REQUEST ):
    "Send photos as pdf page"
    # 1-- Dump all images in a temp directory
    # this is necessary because reportlab expects a filename,
    # and our photos are stored in Zope ZODB (this could (or should ?) change in the futur
    tmpdir = tempfile.mkdtemp(dir='/tmp')
    files = []
    for t in T:
        fotoimg=self.etudfoto_img(t['etudid'],foto=t['foto'])
        filename = tmpdir + '/' + t['etudid'] + '.jpg'
        files.append(filename)
        f = open(filename, 'w')
        f.write(fotoimg.data)
        f.close()
    # 2-- Generate PDF page
    objects = []
    StyleSheet = styles.getSampleStyleSheet()
    report = StringIO() # in-memory document, no disk file
    filename = ('trombino-%s.pdf' % ng ).replace(' ', '_') # XXX should sanitize this filename
    objects.append(Paragraph(SU("Trombinoscope " + sem['titre_num'] + ' ' + ng ), StyleSheet["Heading3"]))
    PHOTOWIDTH = 3*cm
    COLWIDTH = 3.6*cm
    N_PER_ROW = 5 # XXX should be in ScoDoc preferences
    L = []
    n = 0
    currow = []
    for t in T:
        elem = Table(
            [ [ Image( tmpdir + '/' + t['etudid'] + '.jpg', width=PHOTOWIDTH ) ],
              [ Paragraph(
            SU(format_sexe(t['sexe']) + ' ' + format_prenom(t['prenom'])
            + ' ' + format_nom(t['nom'])), StyleSheet['Normal']) ] ],
            colWidths=[ PHOTOWIDTH ] )
        currow.append( elem )
        if n == (N_PER_ROW-1):
            L.append(currow)
            currow = []
        n = (n+1) % N_PER_ROW
    if currow:
        currow += [' ']*(N_PER_ROW-len(currow))
        L.append(currow)
    log(L)
    table = Table( L, colWidths=[ COLWIDTH ]*N_PER_ROW,
                   style = TableStyle( [
        # ('RIGHTPADDING', (0,0), (-1,-1), -5*mm),
        ('VALIGN', (0,0), (-1,-1), 'TOP'),
        ('GRID', (0,0), (-1,-1), 0.25, colors.grey)
        ] ) )
    objects.append(table)
    # Build document
    document = BaseDocTemplate(report)
    document.addPageTemplates(ScolarsPageTemplate(document))
    document.build(objects)
    data = report.getvalue()
    # Clean temporary files
    for f in files:
        os.remove(f)
    os.rmdir(tmpdir)
    return sendPDFFile(REQUEST, data, filename)
