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

"""Génération des bulletins de notes en format PDF

On peut installer plusieurs classes générant des bulletins de formats différents.
La préférence (par semestre) 'bul_pdf_class_name' conserve le nom de la classe Python
utilisée pour générer les bulletins en PDF. Elle doit être une sous-classe de PDFBulletinGenerator
et définir les méthodes fabriquant les éléments PDF:
 gen_part_title
 gen_table
 gen_part_below
 gen_signatures

Les éléments PDF sont des objets PLATYPUS de la bibliothèque Reportlab.
Voir la documentation (Reportlab's User Guide), chapitre 5 et suivants.

Pour définir un nouveau type de bulletin:
 - créer un fichier source sco_bulletins_pdf_xxxx.py où xxxx est le nom (court) de votre type;
 - dans ce fichier, sous-classer PDFBulletinGenerator ou PDFBulletinGeneratorDefault
    (s'inspirer de sco_bulletins_pdf_default);
 - en fin du fichier sco_bulletins_pdf.py, ajouter la ligne
    import sco_bulletins_pdf_xxxx
 - votre type sera alors (après redémarrage de ScoDoc) proposé dans le formulaire de paramètrage ScoDoc.

Chaque semestre peut si nécessaire utiliser un type de bulletin différent.

"""
import htmlutils, time
import pprint
from odict import odict

from notes_table import *
import sco_bulletins

from sco_pdf import *
from sco_pdf import PDFLOCK

BULLETIN_PDF_CLASSES = odict() # liste des types des classes de générateurs de bulletins PDF
def register_pdf_bulletin_class( klass ):
    BULLETIN_PDF_CLASSES[klass.__name__] = klass

def pdf_bulletin_class_descriptions():
    return [ x.description for x in BULLETIN_PDF_CLASSES.values() ]

def pdf_bulletin_class_names():
    return BULLETIN_PDF_CLASSES.keys()

def pdf_bulletin_default_class_name():
    return pdf_bulletin_class_names()[0]

def pdf_bulletin_get_class(class_name):
    return BULLETIN_PDF_CLASSES[class_name]

def make_formsemestre_bulletinetud_pdf(context, infos,
                                       version='long', # short, long, selectedevals
                                       format = 'pdf', # pdf or pdfpart
                                       REQUEST=None):
    """Bulletin en PDF

    Appelle une fonction générant le PDF à partir des informations "bulletin",
    selon les préférences du semestre.

    """
    if not version in ('short','long','selectedevals'):
        raise ValueError('invalid version code !')

    formsemestre_id = infos['formsemestre_id']
    bul_pdf_class_name =  context.get_preference('bul_pdf_class_name', formsemestre_id)
    try:
        gen_class = pdf_bulletin_get_class(bul_pdf_class_name)
    except:
        raise ValueError('Type de bulletin PDF invalide (paramètre: %s)' % bul_pdf_class_name)
    
    try:
        PDFLOCK.acquire()
        pdf_generator = gen_class(context, infos, version=version)
        pdf_data = pdf_generator.generate( stand_alone=(format != 'pdfpart'))
    finally:
        PDFLOCK.release()
    
    if pdf_generator.diagnostic:
        log('pdf_error: %s' % self.diagnostic )
        raise NoteProcessError(self.diagnostic)
    
    filename = pdf_generator.get_filename()
    
    return pdf_data, filename



class PDFBulletinGenerator:
    "Virtual superclass for PDF bulletin generators"""
    # Here some helper methods
    # see PDFBulletinGeneratorDefault subclass for real methods

    def __init__(self, context, infos, version='long', filigranne=None, server_name=None):
        self.context = context
        self.infos = infos
        self.version = version
        self.filigranne = filigranne
        self.server_name = server_name
        # Store preferences for convenience:
        formsemestre_id = self.infos['formsemestre_id']
        self.preferences = context.get_preferences(formsemestre_id)
        self.diagnostic = None # error message if any problem
        # Common styles:
        #  - Pour tous les champs du bulletin sauf les cellules de table:
        self.FieldStyle = reportlab.lib.styles.ParagraphStyle( {} )
        self.FieldStyle.fontName = self.preferences['SCOLAR_FONT_BUL_FIELDS']
        self.FieldStyle.fontSize = self.preferences['SCOLAR_FONT_SIZE']
        self.FieldStyle.firstLineIndent = 0
        #  - Pour les cellules de table:
        self.CellStyle = reportlab.lib.styles.ParagraphStyle( {} )
        self.CellStyle.fontSize = self.preferences['SCOLAR_FONT_SIZE']
        self.CellStyle.fontName = self.preferences['SCOLAR_FONT']
        self.CellStyle.leading  = 1.*self.preferences['SCOLAR_FONT_SIZE'] # vertical space
        # Marges du document
        self.margins = (self.preferences['left_margin'],
                        self.preferences['top_margin'],
                        self.preferences['right_margin'],
                        self.preferences['bottom_margin'])
    
    def buildTableObject(self, P, pdfTableStyle, colWidths):
        """
        Build a platypus Table instance from a nested list of cells, style and widths.
        P: table, as a list of lists
        PdfTableStyle: commandes de style pour la table (reportlab)
        """        
        try:
            # put each table cell in a Paragraph
            Pt = [ [Paragraph(SU(x), self.CellStyle) for x in line ] for line in P ]
        except:
            # enquête sur exception intermittente...
            log('*** bug in PDF buildTableObject:')
            log('P=%s' % P )
            # compris: reportlab is not thread safe !
            #   see http://two.pairlist.net/pipermail/reportlab-users/2006-June/005037.html
            # (donc maintenant protégé dans ScoDoc par un Lock global)
            self.diagnostic = 'erreur lors de la génération du PDF<br/>'
            self.diagnostic += '<pre>' + traceback.format_exc() + '</pre>'
            return []
        return Table( Pt, colWidths=colWidths, style=pdfTableStyle )

    def get_filename(self):
        """Build a filename to be proposed to the web client"""
        sem = self.context.get_formsemestre(self.infos['formsemestre_id'])    
        dt = time.strftime( '%Y-%m-%d' )
        filename = 'bul-%s-%s-%s.pdf' % (sem['titre_num'], dt, self.infos['etud']['nom'])
        filename = unescape_html(filename).replace(' ','_').replace('&','')
        return filename

    def generate(self, stand_alone=True):
        """Build PDF bulletin from distinct parts
        Si stand_alone, génère un doc PDF complet et renvoie une string
        Sinon, renvoie juste une liste d'objets PLATYPUS pour intégration
        dans un autre document.
        """
        formsemestre_id = self.infos['formsemestre_id']
        
        objects = self.gen_part_title()  # partie haute du bulletin
        objects += self.gen_table()      # table des notes
        objects += self.gen_part_below() # infos sous la table           
        objects += self.gen_signatures() # signatures

        # Réduit sur une page
        objects = [KeepInFrame(0,0,objects,mode='shrink')]    
        #
        if not stand_alone:
            objects.append( PageBreak() ) # insert page break at end
            return objects
        else:
            # Generation du document PDF
            sem = self.context.get_formsemestre(formsemestre_id)
            report = cStringIO.StringIO() # in-memory document, no disk file
            document = BaseDocTemplate(report)
            document.addPageTemplates(
                ScolarsPageTemplate(document,
                                    author='%s %s (E. Viennet) [%s]' % (SCONAME, SCOVERSION, self.description),
                                    title='Bulletin %s de %s' % (sem['titremois'], self.infos['etud']['nomprenom']),
                                    subject='Bulletin de note',
                                    margins = self.margins,
                                    server_name = self.server_name,
                                    filigranne  = self.filigranne,
                                    preferences = self.context.get_preferences(formsemestre_id)))
            document.build(objects)
            data = report.getvalue()
        return data

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

# ---------------------------------------------------------------------------

# Classes de bulletins:
import sco_bulletins_pdf_default
# ... ajouter ici vos modules ...

