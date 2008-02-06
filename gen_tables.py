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

"""Generation de tables aux formats XHTML, PDF et Excel
"""

import sco_excel
from sco_pdf import *
import random

class GenTable:
    """Simple 2D tables with export to HTML, PDF, Excel.
    Can be sub-classed to generate fancy formats.
    """
    def __init__(self,
                 rows=[{}], # liste de dict { column_id : value }
                 columns_ids=[], # id des colonnes a afficher, dans l'ordre
                 titles={},  # titres (1ere ligne)
                 bottom_titles={}, # titres derniere ligne (optionnel)
                 lines_titles=[], # liste de titres de ligne (1ere colonne) (incluant titres top et bottom)
                 
                 caption=None,
                 page_title='', # titre fenetre html

                 html_id=None,
                 html_class='gt_table',
                 html_sortable=False,
                 html_highlight_n=2, # une ligne sur 2 de classe "gt_hl"
                 html_col_width=None, # force largeur colonne
                 html_title = '', # avant le tableau en html
                 html_caption=None, # override caption if specified

                 base_url = None,
                 origin=None, # string added to excel version
                 filename='table', # filename, without extension

                 xls_sheet_name='feuille',
                 pdf_title='', # au dessus du tableau en pdf
                 pdf_table_style=None,
                 pdf_col_widths=None,
                 ):
        self.rows = rows # [ { col_id : value } ]
        self.columns_ids = columns_ids # ordered list of col_id
        self.titles = titles # { col_id : title }
        self.bottom_titles = bottom_titles
        self.lines_titles = lines_titles
        self.origin = origin
        self.base_url = base_url
        self.filename = filename
        self.caption = caption
        self.page_title = page_title
        # HTML parameters:
        if not html_id: # random id
            self.html_id = 'gt_' + str(random.randint(0, 1000000))
        else:
            self.html_id = html_id
        self.html_title = html_title
        self.html_caption = html_caption
        self.html_class = html_class
        self.sortable = html_sortable
        self.html_highlight_n = html_highlight_n
        self.html_col_width = html_col_width
        # XLS parameters
        self.xls_sheet_name = xls_sheet_name
        # PDF parameters
        self.pdf_table_style = pdf_table_style
        self.pdf_col_widths = pdf_col_widths
        self.pdf_title = pdf_title

    def get_nb_cols(self):
        return len(self.columns_ids)

    def get_data_list(self, with_titles=False, with_lines_titles=True, with_bottom_titles=True):
        "table data as a list of lists (rows)"
        T = []
        line_num = 0
        if with_titles and self.titles:
            if with_lines_titles and self.lines_titles:
                l = [ self.lines_titles[line_num] ]
            else:
                l = []
            T.append( l + [self.titles.get(cid,'') for cid in self.columns_ids ] )

        for row in self.rows:
            line_num += 1
            if with_lines_titles and self.lines_titles:
                l = [ self.lines_titles[line_num] ]
            else:
                l = []
            T.append( l + [ row.get(cid,'') for cid in self.columns_ids ])

        if with_bottom_titles and self.bottom_titles:
            line_num += 1
            if with_lines_titles and self.lines_titles:
                l = [ self.lines_titles[line_num] ]
            else:
                l = []
            T.append( l + [self.bottom_titles.get(cid,'') for cid in self.columns_ids ] )

        return T

    def get_titles_list(self):
        "list of titles"
        if self.lines_titles:
            l = [ self.lines_titles[0] ]
        else:
            l = []
        return l + [ self.titles.get(cid,'') for cid in self.columns_ids ]

    def gen(format='html', columns_ids=None):
        "Build representation of the table in the specified format."
        if format == 'html':
            return self.html()
        elif format == 'xls':
            return self.excel()
        elif format == 'pdf':
            return self.pdf()
        raise ValueError('GenTable: invalid format: %s' % format)

    def html(self):
        "Simple HTML representation of the table"
        hid = ' id="%s"' % self.html_id
        tablclasses = []
        if self.html_class:
            tablclasses.append(self.html_class)
        if self.sortable:
            tablclasses.append("sortable")
        if tablclasses:
            cls = ' class="%s"' % ' '.join(tablclasses)
        else:
            cls = ''
        
        if self.html_col_width:
            std = ' style="width:%s;"' % self.html_col_width
        else:
            std = ''
        H = ['<table%s%s>' % (hid, cls)]

        line_num = 0
        if self.titles:
            cla = self.titles.get('_css_row_class', '')
            H.append('<tr class="gt_firstrow %s">' % cla)
            if self.lines_titles:
                H.append('<th>%s</th>' % self.lines_titles[line_num])
            H.append( '<th>' + '</th><th>'.join([
                str(self.titles.get(cid,'')) for cid in self.columns_ids ]) + '</th></tr>' )
        
        for row in self.rows:
            line_num += 1
            cla = row.get('_css_row_class', '')
            if line_num % self.html_highlight_n:
                cls = ' class="gt_hl %s"' % cla
            else:
                if cla:
                    cls = ' class="%s"' % cla
                else:
                    cls = ''
            H.append('<tr%s>' % cls)
            if self.lines_titles:
                H.append('<th class="gt_linetit">%s</th>' % self.lines_titles[line_num])
            if row:
                #H.append( '<td%s>'%std + ('</td><td%s>'%std).join([
                #    str(row.get(cid,'')) for cid in self.columns_ids ]) + '</td></tr>' )
                r = []
                for cid in self.columns_ids:
                    content = str(row.get(cid,''))
                    help = row.get('_%s_help'%cid, None)
                    if help:
                        content = '<a class="discretelink" href="" title="%s">%s</a>' % (help, content)
                    r.append( '<td%s %s>%s</td>' % (std, row.get('_%s_td_attrs'%cid,''),content))
                H.append(''.join(r))
            elif not self.lines_titles:
                H.append('<tr></tr>') # empty row
            
        if self.bottom_titles:
            line_num += 1
            H.append('<tr class="gt_lastrow">')
            if self.lines_titles:
                H.append('<th class="gt_linetit">%s</th>' % self.lines_titles[line_num])
            H.append( '<th>' + '</th><th>'.join([
                str(self.bottom_titles.get(cid,'')) for cid in self.columns_ids ]) + '</th></tr>' )
        
        H.append('</table>')

        caption = self.html_caption or self.caption
        if caption or self.base_url:
            H.append('<p class="gt_caption">')
            if caption:
                H.append(caption)
            if self.base_url:
                H.append(' <a href="%s&format=xls">export tableur</a>&nbsp;&nbsp;<a href="%s&format=pdf">version pdf</a>' % (self.base_url,self.base_url))
            H.append('</p>')
        return '\n'.join(H)
        
    def excel(self):
        "Simple Excel representation of the table"
        lines = [ [ str(x) for x in line ] for line in self.get_data_list()]
        if self.caption:
            lines.append( [] ) # empty line  
            lines.append( [self.caption] )
        
        if self.origin:
            lines.append( [] ) # empty line        
            lines.append( [self.origin] )
        log('lines=%s'%lines)
        return sco_excel.Excel_SimpleTable(
            titles=self.get_titles_list(),
            lines=lines,
            SheetName=self.xls_sheet_name)            
    
    def pdf(self):
        "PDF representation: returns a ReportLab's platypus Table instance"
        if not self.pdf_table_style:
            LINEWIDTH = 0.5
            self.pdf_table_style= [ ('FONTNAME', (0,0), (-1,0), SCOLAR_FONT),
                                    ('LINEBELOW', (0,0), (-1,0), LINEWIDTH, Color(0,0,0)),
                                    ('GRID', (0,0), (-1,-1), LINEWIDTH, Color(0,0,0)),
                                    ('VALIGN', (0,0), (-1,-1), 'TOP') ]
        nb_cols = len(self.columns_ids)
        if self.lines_titles:
            nb_cols += 1
        if not self.pdf_col_widths:
            self.pdf_col_widths = (None,) * nb_cols
        #
        CellStyle = styles.ParagraphStyle( {} )
        CellStyle.fontSize= SCOLAR_FONT_SIZE
        CellStyle.fontName= SCOLAR_FONT
        CellStyle.leading = 1.*SCOLAR_FONT_SIZE # vertical space
        LINEWIDTH = 0.5
        #
        titles = [ '<para><b>%s</b></para>' % x for x in self.get_titles_list() ]
        Pt = [ [Paragraph(SU(str(x)),CellStyle) for x in line ]
               for line in (self.get_data_list(with_titles=True))]
        T = Table( Pt, repeatRows=1, colWidths = self.pdf_col_widths, style=self.pdf_table_style )

        objects = []
        if self.pdf_title:
            StyleSheet = styles.getSampleStyleSheet()
            objects.append(Paragraph(SU(self.pdf_title), StyleSheet["Heading3"]))
        objects.append(T)
        return objects
    
    def make_page(self, context, title='', format='html', page_title='',
                  filename=None, REQUEST=None,
                  with_html_headers=True ):
        """
        Build page at given format
        This is a simple page with only a title and the table.
        """
        if not filename:
            filename = self.filename
        page_title = page_title or self.page_title
        html_title = title or self.html_title
        if format == 'html':
            H = []
            if with_html_headers:
                H.append(context.sco_header(REQUEST, page_title=page_title))
            if html_title:
                H.append(html_title)
            H.append(self.html())
            if with_html_headers:
                H.append(context.sco_footer(REQUEST))
            return '\n'.join(H)
        elif format == 'pdf':
            objects = self.pdf()
            doc = pdf_basic_page( objects, title=title )
            return sendPDFFile(REQUEST, doc, filename + '.pdf' )   
        elif format == 'xls':
            xls = self.excel()
            return sco_excel.sendExcelFile(REQUEST, xls, filename + '.xls' )
        else:
            raise ValueError('_make_page: invalid format')
