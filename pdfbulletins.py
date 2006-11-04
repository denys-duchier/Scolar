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

"""Generation documents PDF (reportlab)
"""
import time, cStringIO

from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Frame, PageBreak
from reportlab.platypus import Table, TableStyle, Image, KeepInFrame
from reportlab.platypus.flowables import Flowable
from reportlab.platypus.doctemplate import PageTemplate, BaseDocTemplate
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.rl_config import defaultPageSize
from reportlab.lib.units import inch, cm, mm
from reportlab.lib.colors import pink, black, red, blue, green, magenta, red
from reportlab.lib.colors import Color
from reportlab.lib import styles

from sco_utils import *
from notes_log import log
from VERSION import SCOVERSION, SCONAME

PAGE_HEIGHT=defaultPageSize[1]
PAGE_WIDTH=defaultPageSize[0]

SCOLAR_FONT = 'Helvetica'
SCOLAR_FONT_SIZE = 10
SCOLAR_FONT_SIZE_FOOT = 6


def SU(s):
    "convert s from SCO default encoding to UTF8"
    # XXX mis en service le 4/11/06, passage à ReportLab 2.0
    return unicode(s, SCO_ENCODING, 'replace').encode('utf8')


class ScolarsPageTemplate(PageTemplate) :
    """Our own page template."""
    def __init__(self, document, pagesbookmarks={},
                 author=None, title=None, subject=None,
                 server_name = '' ):
        """Initialise our page template."""
        self.pagesbookmarks = pagesbookmarks
        self.pdfmeta_author = author
        self.pdfmeta_title = title
        self.pdfmeta_subject = subject
        self.server_name = server_name
        # Our doc is made of a single frame
        content = Frame(0.75 * inch, 0.5 * inch,
                        document.pagesize[0] - 1.25 * inch,
                        document.pagesize[1] - (1.5 * inch))
        PageTemplate.__init__(self, "ScolarsPageTemplate", [content])
        self.logo = None
        
    def beforeDrawPage(self, canvas, doc) :
        """Draws a logo and an contribution message on each page."""
        canvas.saveState()
        if self.logo is not None :
            # draws the logo if it exists
            ((width, height), image) = self.logo
            canvas.drawImage(image, inch, doc.pagesize[1] - inch, width, height)
        # ---- Add some meta data and bookmarks
        if self.pdfmeta_author:
            canvas.setAuthor(SU(self.pdfmeta_author))
        if self.pdfmeta_title:
            canvas.setTitle(SU(self.pdfmeta_title))
        if self.pdfmeta_subject:
            canvas.setSubject(SU(self.pdfmeta_subject))
        bm = self.pagesbookmarks.get(doc.page,None)
        if bm != None:
            canvas.bookmarkPage(bm)
            canvas.addOutlineEntry(bm,bm)
        # ---- Footer
        canvas.setFont(SCOLAR_FONT, SCOLAR_FONT_SIZE_FOOT)
        dt = time.strftime('%d/%m/%Y à %Hh%M')
        if self.server_name:
            s = ' sur %s' % self.server_name
        else:
            s = ''
        canvas.drawString(2*cm, 0.25 * inch,
                          SU("Edité par %s le %s%s" % (VERSION.SCONAME,dt,s)) )
        canvas.restoreState()


def essaipdf(REQUEST):
    filename = 'essai.pdf'
    report = cStringIO.StringIO() # in-memory document, no disk file
    document = BaseDocTemplate(report)
    document.addPageTemplates(ScolarsPageTemplate(document))
    objects = []
    # get the default style sheet
    StyleSheet = styles.getSampleStyleSheet()
    # then build a simple doc with ReportLab's platypus
    sometext = SU("A sample script to show how to use ReportLab from within Zope")
    objects.append(Paragraph(SU("Using ReportLab from within Zope"),
                             StyleSheet["Heading3"]))
    objects.append(Spacer(0, 10))
    objects.append(Paragraph(SU("Hélène à Bla bla blo blilllll auhih jhi"),
                             StyleSheet['Normal']))
    objects.append(Paragraph('<b>URL0</b>=%s' % REQUEST.URL0, StyleSheet['Normal']))
    objects.append(Spacer(0, 40))
    objects.append(Paragraph("If possible, this report will be automatically saved as : %s" % filename, StyleSheet['Normal']))
    
    # generation du document PDF
    document.build(objects)
    data = report.getvalue()
    return sendPDFFile(REQUEST, data, filename)


def pdfbulletin_etud(etud, sem, P, TableStyle, infos,
                     stand_alone=True,
                     filigranne='', appreciations=[], situation='',
                     server_name=None
                     ):
    """Genere le PDF pour un bulletin
    P et PdfStyle specifient la table principale (en format PLATYPUS)
    Si stand_alone, génère un doc PDF complet et renvoie une string
    Sinon, renvoie juste une liste d'objets PLATYPUS pour intégration
    dans un autre document.
    """
    #log('pdfbulletin_etud: P=' + str(P))
    #log('pdfbulletin_etud: style=' + str(TableStyle))
    objects = []
    StyleSheet = styles.getSampleStyleSheet()
    # Make a new cell style and put all cells in paragraphs    
    CellStyle = styles.ParagraphStyle( {} )
    CellStyle.fontSize= SCOLAR_FONT_SIZE
    CellStyle.fontName= SCOLAR_FONT    
    CellStyle.leading = 1.*SCOLAR_FONT_SIZE # vertical space
    Pt = [ [Paragraph(SU(x),CellStyle) for x in line ] for line in P ]
    # Build doc using ReportLab's platypus
    objects.append(Paragraph(SU("Université Paris 13 - IUT de Villetaneuse - Département %(DeptName)s" % infos),
                            StyleSheet["Heading2"]) )
    objects.append(Paragraph(SU("Relevé de notes de %s (%s %s) %s" % (etud['nomprenom'], sem['titre'], sem['date_debut'].split('/')[2], filigranne)), StyleSheet["Heading3"]))
    objects.append(Spacer(0, 10))
    # customize table style
    TableStyle.append( ('BOX', (0,0), (-1,-1), 0.4, blue) )
    objects.append( Table( Pt,
                           colWidths = (1.5*cm, 5*cm, 6*cm, 2*cm, 1*cm),
                           style=TableStyle ) )
    if etud.has_key('nbabs'):
        objects.append( Spacer(0, 0.4*cm) )
        objects.append( Paragraph(
            SU("%d absences (1/2 journées), dont %d justifiées." % (etud['nbabs'], etud['nbabsjust'])), CellStyle ) )
    #
    if appreciations:
        objects.append( Spacer(0, 0.2*cm) )
        objects.append( Paragraph(SU('Appréciation : ' + '\n'.join(appreciations)),
                                  CellStyle) )
    if situation:
        objects.append( Spacer(0, 0.5*cm) )
        objects.append( Paragraph( SU(situation), StyleSheet["Heading3"] ) )
    #
    if not stand_alone:
        objects.append( PageBreak() ) # insert page break at end
        return objects
    else:
        # generation du document PDF
        report = cStringIO.StringIO() # in-memory document, no disk file
        document = BaseDocTemplate(report)
        document.addPageTemplates(
        ScolarsPageTemplate(document,
                            author='Scolars %s (E. Viennet)' % SCOVERSION,
                            title='Bulletin %s de %s' % (sem['titre'],etud['nomprenom']),
                            subject='Bulletin de note',
                            server_name = server_name))
        # reduit sur une page
        objects = [KeepInFrame(0,0,objects,mode='shrink')]
        document.build(objects)
        data = report.getvalue()
        return data

def pdfassemblebulletins( objects, sem, infos, pagesbookmarks, server_name='' ):
    "generate PDF document from a list of PLATYPUS objects"
    report = cStringIO.StringIO() # in-memory document, no disk file
    document = BaseDocTemplate(report)
    document.addPageTemplates(
        ScolarsPageTemplate(document,
                            author='%s %s (E. Viennet)' % (SCONAME, SCOVERSION),
                            title='Bulletin %s' % (sem['titre']),
                            subject='Bulletin de note',
                            server_name = server_name,
                            pagesbookmarks=pagesbookmarks))
    document.build(objects)
    data = report.getvalue()
    return data

# -------------- Trombinoscope
def pdftrombino( sem, etudfotos, server_name='' ):
    """generate PDF trombinoscope
    etudfotos = [ (etud, foto), ... ]
    """
    objects = []
    objects.append( Image("/tmp/viennet.jpg") )
    # generation du document PDF
    report = cStringIO.StringIO() # in-memory document, no disk file
    document = BaseDocTemplate(report)
    document.addPageTemplates(
    ScolarsPageTemplate(document,
                        author='%s %s (E. Viennet)' % (SCONAME, SCOVERSION),
                        title='Bulletin %s de %s' % (sem['titre'],etud['nomprenom']),
                        subject='Bulletin de note',
                        server_name = server_name))
    
    document.build(objects)
    data = report.getvalue()
    return data
