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

"""Generation de PDF: définitions diverses et gestion du verro

    reportlab n'est pas réentrante: il ne faut qu'une seule opération PDF au même moment.
    Tout accès à ReportLab doit donc être précédé d'un PDFLOCK.acquire()
    et terminé par un PDFLOCK.release()
"""
import time, cStringIO

import reportlab
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Frame, PageBreak
from reportlab.platypus import Table, TableStyle, Image, KeepInFrame
from reportlab.platypus.flowables import Flowable
from reportlab.platypus.doctemplate import PageTemplate, BaseDocTemplate
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.rl_config import defaultPageSize
from reportlab.lib.units import inch, cm, mm
from reportlab.lib.colors import pink, black, red, blue, green, magenta, red
from reportlab.lib.colors import Color
from reportlab.lib.enums import TA_LEFT, TA_RIGHT, TA_CENTER, TA_JUSTIFY
from reportlab.lib import styles
from reportlab.lib.pagesizes import letter, A4, landscape

from sco_utils import *
from notes_log import log
from sco_pagebulletin import formsemestre_pagebulletin_get
from SuppressAccents import suppression_diacritics
from VERSION import SCOVERSION, SCONAME

PAGE_HEIGHT=defaultPageSize[1]
PAGE_WIDTH=defaultPageSize[0]

SCOLAR_FONT = CONFIG.SCOLAR_FONT 
SCOLAR_FONT_SIZE = CONFIG.SCOLAR_FONT_SIZE
SCOLAR_FONT_SIZE_FOOT = CONFIG.SCOLAR_FONT_SIZE_FOOT


DEFAULT_PDF_FOOTER_TEMPLATE = CONFIG.DEFAULT_PDF_FOOTER_TEMPLATE

def SU(s):
    "convert s from SCO default encoding to UTF8"
    # Mis en service le 4/11/06, passage à ReportLab 2.0
    return unicode(s, SCO_ENCODING, 'replace').encode('utf8')

def _splitPara(txt):
    "split a string, returns a list of <para > ... </para>"
    L = []
    closetag = '</para>'
    l = len(closetag)
    start = 0
    while 1:
        b = txt.find('<para',start)
        if b < 0:
            break
        e = txt.find(closetag,b)
        if e < 0:
            raise ValueError('unbalanced para tags')
        L.append( txt[b:e+l] )
        start = e        
    return L

def makeParas(txt, style):
    """Returns a list of Paragraph instances from a text
    with one or more <para> ... </para>
    """
    return [ Paragraph( SU(s), style ) for s in _splitPara(txt) ]


class ScolarsPageTemplate(PageTemplate) :
    """Our own page template."""
    def __init__(self, document, pagesbookmarks={},
                 author=None, title=None, subject=None,
                 margins = (0,0,0,0), # additional margins in mm (left,top,right, bottom)
                 server_name = '',
                 footer_template = DEFAULT_PDF_FOOTER_TEMPLATE ):
        """Initialise our page template."""
        self.pagesbookmarks = pagesbookmarks
        self.pdfmeta_author = author
        self.pdfmeta_title = title
        self.pdfmeta_subject = subject
        self.server_name = server_name
        self.footer_template = footer_template
        # Our doc is made of a single frame
        left, top, right, bottom = margins
        content = Frame(0.75 * inch + left*mm, 0.5 * inch + bottom*mm,
                        document.pagesize[0] - 1.25 * inch - left*mm-right*mm,
                        document.pagesize[1] - 1.5 * inch - top*mm - bottom*mm)
        PageTemplate.__init__(self, "ScolarsPageTemplate", [content])
        self.logo = None
        
    def beforeDrawPage(self, canvas, doc) :
        """Draws a logo and an contribution message on each page.

        day   : Day of the month as a decimal number [01,31]
        month : Month as a decimal number [01,12].
        year  : Year without century as a decimal number [00,99].
        Year  : Year with century as a decimal number.
        hour  : Hour (24-hour clock) as a decimal number [00,23].
        minute: Minute as a decimal number [00,59].

        server_url: URL du serveur ScoDoc
        
        """
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
            key = bm
            txt = SU(bm)
            canvas.bookmarkPage(key)
            canvas.addOutlineEntry(txt,bm)
        # ---- Footer
        canvas.setFont(SCOLAR_FONT, SCOLAR_FONT_SIZE_FOOT)
        d = _makeTimeDict()
        d['scodoc_name'] = VERSION.SCONAME
        d['server_url'] = self.server_name
        footer_str = SU( self.footer_template % d )
        canvas.drawString(2*cm, 0.25 * inch, footer_str )
        canvas.restoreState()


def _makeTimeDict():
    # ... suboptimal but we don't care
    return { 'day' :  time.strftime('%d' ),
             'month' :  time.strftime('%m' ),
             'year' : time.strftime('%y' ),
             'Year' : time.strftime('%Y' ),
             'hour' : time.strftime('%H' ),
             'minute' : time.strftime('%M' )
             }

def pdf_basic_page( objects, title='' ):
    """Simple convenience fonction: build a page from a list of platypus objects,
    adding a title if specified.
    """
    StyleSheet = styles.getSampleStyleSheet()
    report = cStringIO.StringIO() # in-memory document, no disk file
    document = BaseDocTemplate(report)
    document.addPageTemplates(
        ScolarsPageTemplate(document,
                            title=title,
                            author='%s %s (E. Viennet)' % (SCONAME, SCOVERSION),
                            footer_template="Edité par %(scodoc_name)s le %(day)s/%(month)s/%(year)s à %(hour)sh%(minute)s"
                            ))
    if title:
        head = Paragraph(SU(title), StyleSheet["Heading3"])
        objects = [ head ] + objects
    document.build(objects)
    data = report.getvalue()
    return data

# Gestion du lock pdf
import threading, time, Queue, thread

class PDFLock:
    def __init__(self, timeout=15):
        self.Q = Queue.Queue(1)
        self.timeout = timeout
        self.current_thread = None
        self.nref = 0
    
    def release(self):        
        "Release lock. Raise Empty if not acquired first"
        if self.current_thread == thread.get_ident():
            self.nref -= 1
            if self.nref == 0:
                log('PDFLock: release from %s' % self.current_thread)
                self.current_thread = None
                self.Q.get(False)
            return
        else:
            self.Q.get(False)
    
    def acquire(self): 
        "Acquire lock. Raise ScoGenError if can't lock after timeout."
        if self.current_thread == thread.get_ident():
            self.nref += 1
            return # deja lock pour ce thread
        try:
            self.Q.put(1, True, self.timeout )
        except Queue.Full:
            raise ScoGenError(msg="Traitement PDF occupé: ré-essayez")
        self.current_thread = thread.get_ident()
        self.nref = 1
        log('PDFLock: granted to %s' % self.current_thread)

PDFLOCK = PDFLock()
