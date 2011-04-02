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
#   Emmanuel Viennet      emmanuel.viennet@gmail.com
#
##############################################################################

"""Generation bulletins de notes en PDF (avec reportlab)

Les templates utilisent les XML markup tags de ReportLab
 (voir ReportLab user guide, page 70 et suivantes), dans lesquels les balises
de la forme %(XXX)s sont remplacées par la valeur de XXX, pour XXX dans:

- preferences du semestre (ou globales) (voir sco_preferences.py)
- champs de formsemestre: titre, date_debut, date_fin, responsable, anneesem
- champs de l'etudiant s(etud, décoré par getEtudInfo)
- demission ("DEMISSION" ou vide)
- situation ("Inscrit le XXX")

Balises img: actuellement interdites.

"""
from sco_pdf import *
import sco_preferences
import traceback, re
from notes_log import log
import sco_groups


def process_field(context, field, cdict, style, suppress_empty_pars=False):
    """Process a field given in preferences, returns list of Platypus objects
    Substitutes all %()s markup    
    Remove potentialy harmful <img> tags
    Replaces <logo name="header" width="xxx" height="xxx">
     by <img src=".../logos/logo_header" width="xxx" height="xxx">
    """
    try:
        text = field % WrapDict(cdict) # note that None values are mapped to empty strings
    except:
        log('process_field: invalid format=%s' % field)
        text = '<para><i>format invalide !<i></para><para>' + traceback.format_exc() + '</para>'    
    # remove unhandled or dangerous tags:
    text = re.sub( r'<\s*img', '', text)
    # handle logos:
    image_dir = context.file_path + '/logos'
    text = re.sub( r'<(\s*)logo(.*?)src\s*=\s*(.*?)>', r'<\1logo\2\3>', text) # remove forbidden src attribute
    text = re.sub(r'<\s*logo(.*?)name\s*=\s*"(\w*?)"(.*?)/?>', 
                  r'<img\1src="%s/logo_\2.jpg"\3/>' % image_dir, text)
    # nota: le match sur \w*? donne le nom du logo et interdit les .. et autres 
    # tentatives d'acceder à d'autres fichiers !
    
    #log('field: %s' % (text))
    return makeParas(text, style, suppress_empty=suppress_empty_pars)

def essaipdf(REQUEST): # XXX essais...
    PDFLOCK.acquire()
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
    PDFLOCK.release()
    return sendPDFFile(REQUEST, data, filename)


def pdfbulletin_etud(I, sem, P, TableStyle,
                     stand_alone=True,
                     filigranne=None,
                     server_name=None,
                     context=None       # required for preferences
                     ):
    """Genere le PDF pour un bulletin
    P et PdfStyle specifient la table principale (en format PLATYPUS)
    Si stand_alone, génère un doc PDF complet et renvoie une string
    Sinon, renvoie juste une liste d'objets PLATYPUS pour intégration
    dans un autre document.
    """
    formsemestre_id = sem['formsemestre_id']
    infos = I # XXXXXXX ['infos_jury']
    etud = I['etud']
    #log('pdfbulletin_etud: P=' + str(P))
    #log('pdfbulletin_etud: style=' + str(TableStyle))
    objects = []

    diag = '' # diagnostic (empty == ok)
    StyleSheet = styles.getSampleStyleSheet()
    # Paramètres de mise en page
    margins = (context.get_preference('left_margin', formsemestre_id),
               context.get_preference('top_margin', formsemestre_id),
               context.get_preference('right_margin', formsemestre_id),
               context.get_preference('bottom_margin', formsemestre_id))    
    titletmpl = context.get_preference('bul_title',  formsemestre_id) or ''
    
    # Make a new cell style and put all cells in paragraphs    
    CellStyle = styles.ParagraphStyle( {} )
    CellStyle.fontSize= context.get_preference('SCOLAR_FONT_SIZE', formsemestre_id)
    CellStyle.fontName= context.get_preference('SCOLAR_FONT', formsemestre_id)
    CellStyle.leading = 1.*context.get_preference('SCOLAR_FONT_SIZE', formsemestre_id) # vertical space
    try:
        Pt = [ [Paragraph(SU(x),CellStyle) for x in line ] for line in P ]
    except:        
        # enquête sur exception intermittente...
        log('*** bug in pdfbulletin_etud:')
        log('P=%s' % P )
        # compris: reportlab is not thread safe !
        #   see http://two.pairlist.net/pipermail/reportlab-users/2006-June/005037.html
        # (donc maintenant protégé dans ScoDoc par un Lock global)
        diag = 'erreur lors de la génération du PDF<br/>'
        diag += '<pre>' + traceback.format_exc() + '</pre>'
        return [], diag

    FieldStyle = styles.ParagraphStyle( {} )
    FieldStyle.fontName= context.get_preference('SCOLAR_FONT_BUL_FIELDS', formsemestre_id)
    FieldStyle.fontSize= context.get_preference('SCOLAR_FONT_SIZE', formsemestre_id)
    FieldStyle.firstLineIndent = 0

    infos['situation_inscr'] = infos['situation'] # inscription actuelle de l'étudiant
    
    # --- Build doc using ReportLab's platypus
    # Title
    objects += process_field(context, context.get_preference('bul_pdf_title', formsemestre_id), 
                                 infos, FieldStyle)
    objects.append(Spacer(1, 5*mm))
    # customize table style
    TableStyle.append( ('BOX', (0,0), (-1,-1), 0.4, blue) )
    colWidths = [None, 5*cm, 6*cm, 2*cm, 1.2*cm]
    if len(P[0]) > 5:
        colWidths.append( 1.5*cm ) # absences/modules
    objects.append( Table( Pt,
                           colWidths = colWidths,
                           style=TableStyle ) )

    # ----- ABSENCES
    if context.get_preference('bul_show_abs', formsemestre_id):
        nbabs = I['nbabs']
        nbabsjust = I['nbabsjust']
        objects.append( Spacer(1, 2*mm) )
        if nbabs:
            objects.append( Paragraph(
                    SU("%d absences (1/2 journées), dont %d justifiées." % (I['nbabs'], I['nbabsjust'])), CellStyle ) )
        else:
            objects.append( Paragraph(SU("Pas d'absences signalées."), CellStyle) )
    
    # ----- APPRECIATIONS
    if infos.get('appreciations', False):
        objects.append( Spacer(1, 3*mm) )
        objects.append( Paragraph(SU('Appréciation : ' + '\n'.join(infos['appreciations'])),
                                  CellStyle) )
    
    # ----- DECISION JURY
    if context.get_preference('bul_show_decision', formsemestre_id):
        objects += process_field(context, context.get_preference('bul_pdf_caption', formsemestre_id), 
                                 infos, FieldStyle)

    # ----- SIGNATURES GAUCHE ET DROITE
    show_left = context.get_preference('bul_show_sig_left', formsemestre_id)
    show_right = context.get_preference('bul_show_sig_right', formsemestre_id)
    if show_left or show_right:
        if show_left:
            L = [[process_field(context, context.get_preference('bul_pdf_sig_left', formsemestre_id), 
                                infos, FieldStyle)]]
        else:
            L = [['']]
        if show_right:
            L[0].append(process_field(context, context.get_preference('bul_pdf_sig_right', formsemestre_id), infos, FieldStyle))
        else:
            L[0].append('')
        t = Table(L)
        t._argW[0] = 10*cm
        objects.append( Spacer(1, 1.5*cm) )
        objects.append(t)
    
    # reduit sur une page
    objects = [KeepInFrame(0,0,objects,mode='shrink')]    
    
    #
    if not stand_alone:
        objects.append( PageBreak() ) # insert page break at end
        return objects, diag
    else:
        # generation du document PDF
        report = cStringIO.StringIO() # in-memory document, no disk file
        document = BaseDocTemplate(report)
        document.addPageTemplates(
            ScolarsPageTemplate(document,
                                author='%s %s (E. Viennet)' % (SCONAME, SCOVERSION),
                                title='Bulletin %s de %s' % (sem['titremois'],etud['nomprenom']),
                                subject='Bulletin de note',
                                margins=margins,
                                server_name = server_name,
                                filigranne=filigranne,
                                preferences=context.get_preferences(formsemestre_id)))
        document.build(objects)
        data = report.getvalue()
        return data, diag

def pdfassemblebulletins( formsemestre_id,
                          objects, sem, infos, pagesbookmarks, 
                          filigranne=None,
                          server_name='', context=None ):
    "generate PDF document from a list of PLATYPUS objects"
    if not objects:
        return ''
    # Paramètres de mise en page
    margins = (context.get_preference('left_margin', formsemestre_id),
               context.get_preference('top_margin', formsemestre_id),
               context.get_preference('right_margin', formsemestre_id),
               context.get_preference('bottom_margin', formsemestre_id)) 
    
    report = cStringIO.StringIO() # in-memory document, no disk file
    document = BaseDocTemplate(report)
    document.addPageTemplates(
        ScolarsPageTemplate(document,
                            author='%s %s (E. Viennet)' % (SCONAME, SCOVERSION),
                            title='Bulletin %s' % (sem['titremois']),
                            subject='Bulletin de note',
                            server_name=server_name,
                            margins=margins,
                            pagesbookmarks=pagesbookmarks,
                            filigranne=filigranne,
                            preferences=context.get_preferences(formsemestre_id)))
    document.build(objects)
    data = report.getvalue()
    return data

