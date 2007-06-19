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
from sco_pdf import *

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
    objects.append(Paragraph(SU("H�l�ne � Bla bla blo blilllll auhih jhi"),
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
                     server_name=None,
                     context=None
                     ):
    """Genere le PDF pour un bulletin
    P et PdfStyle specifient la table principale (en format PLATYPUS)
    Si stand_alone, g�n�re un doc PDF complet et renvoie une string
    Sinon, renvoie juste une liste d'objets PLATYPUS pour int�gration
    dans un autre document.
    """
    #log('pdfbulletin_etud: P=' + str(P))
    #log('pdfbulletin_etud: style=' + str(TableStyle))
    objects = []
    StyleSheet = styles.getSampleStyleSheet()
    # Param�tres de mise en page
    if context:
        fmt = formsemestre_pagebulletin_get(context, sem['formsemestre_id'])
        margins = (fmt['left_margin'], fmt['top_margin'],
                   fmt['right_margin'], fmt['bottom_margin'])
        titletmpl = fmt['title']
    else:
        margins = (0,0,0,0)
        titletmpl=''

    # Make a new cell style and put all cells in paragraphs    
    CellStyle = styles.ParagraphStyle( {} )
    CellStyle.fontSize= SCOLAR_FONT_SIZE
    CellStyle.fontName= SCOLAR_FONT    
    CellStyle.leading = 1.*SCOLAR_FONT_SIZE # vertical space
    Pt = [ [Paragraph(SU(x),CellStyle) for x in line ] for line in P ]
    # --- Build doc using ReportLab's platypus
    # Title
    objects.append(Paragraph(SU(titletmpl % infos),
                             StyleSheet["Heading2"]) )
    annee_debut = sem['date_debut'].split('/')[2]
    annee_fin = sem['date_fin'].split('/')[2]
    if annee_debut != annee_fin:
        annee = '%s - %s' % (annee_debut, annee_fin)
    else:
        annee = annee_debut
    objects.append(Paragraph(SU("Relev� de notes de %s (%s %s) %s"
                                % (etud['nomprenom'], sem['titre_num'],
                                   annee,
                                   filigranne)),
                             StyleSheet["Heading3"]))
    objects.append(Spacer(0, 10))
    # customize table style
    TableStyle.append( ('BOX', (0,0), (-1,-1), 0.4, blue) )
    objects.append( Table( Pt,
                           colWidths = (1.5*cm, 5*cm, 6*cm, 2*cm, 1*cm),
                           style=TableStyle ) )
    if etud.has_key('nbabs'):
        objects.append( Spacer(0, 0.4*cm) )
        objects.append( Paragraph(
            SU("%d absences (1/2 journ�es), dont %d justifi�es." % (etud['nbabs'], etud['nbabsjust'])), CellStyle ) )
    #
    if appreciations:
        objects.append( Spacer(0, 0.2*cm) )
        objects.append( Paragraph(SU('Appr�ciation : ' + '\n'.join(appreciations)),
                                  CellStyle) )
    if situation:
        objects.append( Spacer(0, 0.5*cm) )
        objects.append( Paragraph( SU(situation), StyleSheet["Heading3"] ) )
    # reduit sur une page
    objects = [KeepInFrame(0,0,objects,mode='shrink')]    
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
                                title='Bulletin %s de %s' % (sem['titre_num'],etud['nomprenom']),
                                subject='Bulletin de note',
                                margins=margins,
                                server_name = server_name))
        document.build(objects)
        data = report.getvalue()
        return data

def pdfassemblebulletins( formsemestre_id,
                          objects, sem, infos, pagesbookmarks,
                          top_margin=0, # additional top margin in mm
                          server_name='', context=None ):
    "generate PDF document from a list of PLATYPUS objects"
    # Param�tres de mise en page
    if context:
        fmt = formsemestre_pagebulletin_get(context, formsemestre_id)
        margins = (fmt['left_margin'], fmt['top_margin'],
                   fmt['right_margin'], fmt['bottom_margin'])
    else:
        margins = (0,0,0,0)
    report = cStringIO.StringIO() # in-memory document, no disk file
    document = BaseDocTemplate(report)
    document.addPageTemplates(
        ScolarsPageTemplate(document,
                            author='%s %s (E. Viennet)' % (SCONAME, SCOVERSION),
                            title='Bulletin %s' % (sem['titre_num']),
                            subject='Bulletin de note',
                            server_name=server_name,
                            margins=margins,
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
                        title='Bulletin %s de %s' % (sem['titre_num'],etud['nomprenom']),
                        subject='Bulletin de note',
                        server_name = server_name))
    
    document.build(objects)
    data = report.getvalue()
    return data
