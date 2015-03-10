# -*- mode: python -*-
# -*- coding: utf-8 -*-

##############################################################################
#
# Gestion scolarite IUT
#
# Copyright (c) 2001 - 2015 Emmanuel Viennet.  All rights reserved.
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
import pprint, traceback

from notes_table import *
import sco_bulletins

from sco_pdf import *


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



def process_field(context, field, cdict, style, suppress_empty_pars=False, format='pdf'):
    """Process a field given in preferences, returns
    - if format = 'pdf': a list of Platypus objects
    - if format = 'html' : a string
    
    Substitutes all %()s markup    
    Remove potentialy harmful <img> tags
    Replaces <logo name="header" width="xxx" height="xxx">
    by <img src=".../logos/logo_header" width="xxx" height="xxx">

    If format = 'html', replaces <para> by <p>. HTML does not allow logos. 
    """
    try:
        text = field % WrapDict(cdict) # note that None values are mapped to empty strings
    except:
        log('process_field: invalid format=%s' % field)
        text = '<para><i>format invalide !<i></para><para>' + traceback.format_exc() + '</para>'    
    # remove unhandled or dangerous tags:
    text = re.sub( r'<\s*img', '', text)
    if format == 'html':
        # convert <para>
        text = re.sub(r'<\s*para(\s*)(.*?)>', r'<p>', text)        
        return text
    # --- PDF format:
    # handle logos:
    image_dir = context.file_path + '/logos'
    text = re.sub( r'<(\s*)logo(.*?)src\s*=\s*(.*?)>', r'<\1logo\2\3>', text) # remove forbidden src attribute
    text = re.sub(r'<\s*logo(.*?)name\s*=\s*"(\w*?)"(.*?)/?>', 
                  r'<img\1src="%s/logo_\2.jpg"\3/>' % image_dir, text)
    # nota: le match sur \w*? donne le nom du logo et interdit les .. et autres 
    # tentatives d'acceder à d'autres fichiers !
    
    #log('field: %s' % (text))
    return makeParas(text, style, suppress_empty=suppress_empty_pars)



