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
#   Emmanuel Viennet      emmanuel.viennet@viennet.net
#
##############################################################################

"""Photos: trombinoscopes - Version IUT Tours
   Code contribué par Jérôme Billoue, IUT de Tours, 2014
"""

try: from cStringIO import StringIO
except: from StringIO import StringIO
from zipfile import ZipFile, BadZipfile
import xml
import tempfile

from notes_log import log
from sco_utils import *
import scolars
import sco_photos
import sco_groups
import sco_groups_view

import sco_trombino
from sco_pdf import *
from reportlab.lib import colors

# Paramétrage de l'aspect graphique:
PHOTOWIDTH = 2.8*cm
COLWIDTH = 3.4*cm
N_PER_ROW = 5

    
def pdf_trombino_tours(
        context, 
        group_ids=[], # liste des groupes à afficher
        formsemestre_id=None, # utilisé si pas de groupes selectionné
        REQUEST=None):
    """Generation du trombinoscope en fichier PDF
    """
    # Informations sur les groupes à afficher:
    groups_infos = sco_groups_view.DisplayedGroupsInfos(context, group_ids, formsemestre_id=formsemestre_id, REQUEST=REQUEST)
    
    DeptName = context.get_preference('DeptName')
    DeptFullName = context.get_preference('DeptFullName')
    UnivName = context.get_preference('UnivName')
    InstituteName = context.get_preference('InstituteName')
    # Generate PDF page
    StyleSheet = styles.getSampleStyleSheet()
    objects = []
    
    T = Table([ 
        [ Paragraph(SU(InstituteName), StyleSheet["Heading3"]) ],
        [ Paragraph(SU('Département ' + DeptFullName), StyleSheet["Heading3"]) ],
        [ Paragraph(SU('Date ............ / ............ / ......................'), StyleSheet["Normal"]),
          Paragraph(SU('Discipline .......................................................'), StyleSheet["Normal"]) ],
        [ Paragraph(SU('de ............h............ à ............h............'), StyleSheet["Normal"]),
          Paragraph(SU('Enseignant .......................................................'), StyleSheet["Normal"]) ],
        ],
        colWidths = (COLWIDTH*N_PER_ROW)/2,
        style = TableStyle([ ('ALIGN', (0,0), (-1,-1), 'LEFT'),
                             ('SPAN', (0,1), (1,1)),
                             ('BOTTOMPADDING', (0, -1), (-1, -1), 10),
                             ('BOX', (0,0), (-1,-1), 0.75, black)
                             ] )
        )
    
    objects.append(T)
    
    groups = ''
    
    for group_id in groups_infos.group_ids:
        if group_id != "None":
            members, group, group_tit, sem, nbdem, other_partitions = sco_groups.get_group_infos(context, group_id, 'I')
            groups += ' %s' % group_tit
            L = []
            currow = []

            if sem['semestre_id'] != -1:
                currow = [ Paragraph(SU('<para align=center>Semestre %s</para>' % sem['semestre_id'] ), StyleSheet["Normal"]) ]
            currow += [' ']*(N_PER_ROW-len(currow)-1)
            currow += [ Paragraph(SU('<para align=center>%s</para>' % sem['anneescolaire'] ), StyleSheet["Normal"]) ]
            L.append(currow)
            currow = [' ']*N_PER_ROW
            L.append(currow)
    
            currow = []
            currow.append( Paragraph(SU('<para align=center><b>' + group_tit + '</b></para>'), StyleSheet["Heading3"]) )
            n = 1
            for m in members:
                img = sco_trombino._get_etud_platypus_image(context, m, image_width=PHOTOWIDTH )
                elem = Table(
                    [ [ img ],
                      [ Paragraph(
                          SU('<para align=center><font size=8>' + scolars.format_prenom(m['prenom'])
                             + ' ' + scolars.format_nom(m['nom']) + '</font></para>'), StyleSheet['Normal']) ] ],
                      colWidths=[ COLWIDTH ],
                      style = TableStyle( [
                    ('ALIGN', (0,0), (-1,-1), 'CENTER')
                    ] ) )
                currow.append( elem )
                if n == (N_PER_ROW-1):
                    L.append(currow)
                    currow = []
                n = (n+1) % N_PER_ROW
            if currow:
                currow += [' ']*(N_PER_ROW-len(currow))
                L.append(currow)
            if not L:
                T = Paragraph( SU('Aucune photo à exporter !'),  StyleSheet['Normal'])
            else:
                T = Table( L, colWidths=[ COLWIDTH ]*N_PER_ROW,
                               style = TableStyle( [
                    ('LEFTPADDING', (0,0), (-1,-1), 0),
                    ('RIGHTPADDING', (0,0), (-1,-1), 0),
                    ('BOTTOMPADDING', (0,0), (-1,-1), 0),
                    ('TOPPADDING', (0,1), (-1,-1), 0),
                    ('TOPPADDING', (0,0), (-1,0), 10),
                    ('LINEBELOW', (1,0), (-2,0), 0.75, black),
                    ('VALIGN', (0,0), (-1,1), 'MIDDLE'),
                    ('VALIGN', (0,2), (-1,-1), 'TOP'),
                    ('VALIGN', (0,2), (0,2), 'MIDDLE'),
                    ('SPAN', (0,0), (0,1)),
                    ('SPAN', (-1,0), (-1,1))
                    ] )
                    )
    
            objects.append(T)

    # Réduit sur une page
    objects = [KeepInFrame(0,0,objects,mode='shrink')]    
    # Build document
    report = StringIO() # in-memory document, no disk file
    filename = ('trombino-%s%s.pdf' %(DeptName, groups) ).replace(' ', '_')
    document = BaseDocTemplate(report)
    document.addPageTemplates(ScolarsPageTemplate(document, preferences=context.get_preferences()))
    document.build(objects)
    data = report.getvalue()
    
    return sendPDFFile(REQUEST, data, filename)
