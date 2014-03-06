# -*- mode: python -*-
# -*- coding: utf-8 -*-

##############################################################################
#
# Gestion scolarite IUT
#
# Copyright (c) 2001 - 2014 Emmanuel Viennet.  All rights reserved.
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

"""Génération des bulletins de note: super-classe pour les générateurs (HTML et PDF)

class BulletinGenerator:
 description
 supported_formats = [ 'pdf', 'html' ]
 .bul_title_pdf()
 .bul_table(format)
 .bul_part_below(format)
 .bul_signatures_pdf()

 .__init__ et .generate(format) methodes appelees par le client (sco_bulletin)

La préférence 'bul_class_name' donne le nom de la classe generateur.
La préférence 'bul_pdf_class_name' est obsolete (inutilisée).


"""

import sco_preferences
from notes_log import log
from sco_pdf import *
from odict import odict

BULLETIN_CLASSES = odict() # liste des types des classes de générateurs de bulletins PDF
def register_bulletin_class( klass ):
    log("registering bulletin class '%s'" % klass.__name__)
    BULLETIN_CLASSES[klass.__name__] = klass

def bulletin_class_descriptions():
    return [ x.description for x in BULLETIN_CLASSES.values() ]

def bulletin_class_names():
    return BULLETIN_CLASSES.keys()

def bulletin_default_class_name():
    return bulletin_class_names()[0]

def bulletin_get_class(class_name):
    return BULLETIN_CLASSES[class_name]

def bulletin_get_class_name_displayed(context, formsemestre_id):
    """Le nom du générateur utilisé, en clair"""
    bul_class_name =  context.get_preference('bul_class_name', formsemestre_id)
    try:
        gen_class = bulletin_get_class(bul_class_name)
        return gen_class.description
    except:
        return "invalide ! (voir paramètres)"



class BulletinGenerator:
    "Virtual superclass for PDF bulletin generators"""
    # Here some helper methods
    # see sco_bulletins_standard.BulletinGeneratorStandard subclass for real methods
    supported_formats = [] # should list supported formats, eg [ 'html', 'pdf' ]
    description = 'superclass for bulletins' # description for user interface
    
    def __init__(self, context, infos, authuser=None, version='long', filigranne=None, server_name=None):
        if not version in ('short','long','selectedevals'):
            raise ValueError('invalid version code !')
        self.context = context
        self.infos = infos
        self.authuser = authuser # nécessaire pour version HTML qui contient liens dépendant de l'utilisateur
        self.version = version
        self.filigranne = filigranne
        self.server_name = server_name
        # Store preferences for convenience:
        formsemestre_id = self.infos['formsemestre_id']
        self.preferences = context.get_preferences(formsemestre_id)
        self.diagnostic = None # error message if any problem
        # Common PDF styles:
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
        # Marges du document PDF
        self.margins = (self.preferences['left_margin'],
                        self.preferences['top_margin'],
                        self.preferences['right_margin'],
                        self.preferences['bottom_margin'])

    def get_filename(self):
        """Build a filename to be proposed to the web client"""
        sem = self.context.get_formsemestre(self.infos['formsemestre_id'])    
        dt = time.strftime( '%Y-%m-%d' )
        filename = 'bul-%s-%s-%s.pdf' % (sem['titre_num'], dt, self.infos['etud']['nom'])
        filename = unescape_html(filename).replace(' ','_').replace('&','')
        return filename
    
    def generate(self, format='', stand_alone=True):
        """Return bulletin in specified format
        """
        if not format in self.supported_formats:
            raise ValueError('unsupported bulletin format (%s)' % format)
        try:
            PDFLOCK.acquire() # this lock is necessary since reportlab is not re-entrant
            if format == 'html':
                return self.generate_html()
            elif format == 'pdf':
                return self.generate_pdf(stand_alone=stand_alone)
            else:
                raise ValueError('invalid bulletin format (%s)' % format)
        finally:
            PDFLOCK.release()
    
    def generate_html(self):
        """Return bulletin as an HTML string
        """
        H = [ '<div class="notes_bulletin">' ]
        H.append( self.bul_table(format='html') ) # table des notes
        H.append( self.bul_part_below(format='html') ) # infos sous la table     
        H.append('</div>')
        return '\n'.join(H)
        
    def generate_pdf(self, stand_alone=True):
        """Build PDF bulletin from distinct parts
        Si stand_alone, génère un doc PDF complet et renvoie une string
        Sinon, renvoie juste une liste d'objets PLATYPUS pour intégration
        dans un autre document.
        """
        formsemestre_id = self.infos['formsemestre_id']
        
        objects = self.bul_title_pdf()  # partie haute du bulletin
        objects += self.bul_table(format='pdf')      # table des notes
        objects += self.bul_part_below(format='pdf') # infos sous la table           
        objects += self.bul_signatures_pdf() # signatures

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
    
    def buildTableObject(self, P, pdfTableStyle, colWidths):
        """Utility used by some old-style generators.
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

# ---------------------------------------------------------------------------
def make_formsemestre_bulletinetud(context, infos,
                                   version='long', # short, long, selectedevals
                                   format = 'pdf', # html, pdf
                                   stand_alone=True,
                                   REQUEST=None):
    """Bulletin de notes

    Appelle une fonction générant le bulletin au format spécifié à partir des informations infos,
    selon les préférences du semestre.

    """
    if not version in ('short','long','selectedevals'):
        raise ValueError('invalid version code !')

    formsemestre_id = infos['formsemestre_id']
    bul_class_name =  context.get_preference('bul_class_name', formsemestre_id)
    try:
        gen_class = bulletin_get_class(bul_class_name)
    except:
        raise ValueError('Type de bulletin PDF invalide (paramètre: %s)' % bul_pdf_class_name)
    
    try:
        PDFLOCK.acquire()
        bul_generator = gen_class(context, infos,
                                  authuser=REQUEST.AUTHENTICATED_USER,
                                  version=version,
                                  filigranne=infos['filigranne'],
                                  server_name=REQUEST.BASE0)
        if format not in bul_generator.supported_formats:
            # use standard generator            
            log('Bulletin format %s not supported by %s, using %s' % (format, bul_class_name, bulletin_default_class_name()))
            bul_class_name = bulletin_default_class_name()
            gen_class = bulletin_get_class(bul_class_name)
            bul_generator = gen_class(context, infos,
                                  authuser=REQUEST.AUTHENTICATED_USER,
                                  version=version,
                                  filigranne=infos['filigranne'],
                                  server_name=REQUEST.BASE0)
        
        data = bul_generator.generate( format=format, stand_alone=stand_alone )
    finally:
        PDFLOCK.release()
    
    if bul_generator.diagnostic:
        log('bul_error: %s' % self.diagnostic )
        raise NoteProcessError(self.diagnostic)
    
    filename = bul_generator.get_filename()
    
    return data, filename



# ---------------------------------------------------------------------------

# Classes de bulletins:
import sco_bulletins_standard
import sco_bulletins_legacy
# import sco_bulletins_example # format exemple (à désactiver en production)

# ... ajouter ici vos modules ...
import sco_bulletins_ucac # format expérimental UCAC Cameroun


