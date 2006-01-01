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


""" Common definitions
"""
from VERSION import SCOVERSION
import os

SCO_ENCODING = 'iso8859-15' # used by Excel I/O, but should be used elsewhere !
# (attention: lié au codage Zope et aussi à celui de postgresql)

CSV_FIELDSEP = ';'
CSV_LINESEP  = '\n'
CSV_MIMETYPE = 'text/comma-separated-values';
XLS_MIMETYPE = 'application/vnd.ms-excel';
PDF_MIMETYPE = 'application/pdf'

""" Simple python utilities
"""

def simplesqlquote(s,maxlen=50):
    """simple SQL quoting to avoid most SQL injection attacks.
    Note: we use this function in the (rare) cases where we have to
    construct SQL code manually"""
    s = s[:maxlen] 
    s.replace("'", r"\'")
    s.replace(";", r"\;")
    for bad in ("select", "drop", ";", "--", "insert", "delete", "xp_"):
        s = s.replace(bad,'')
    return s

def unescape_html(s):
    """un-escape html entities"""
    s = s.strip().replace( '&amp;', '&' )
    s = s.replace('&lt;','<')
    s = s.replace('&gt;','>')
    return s


def sendCSVFile(REQUEST,data,filename):
    """publication fichier.
    (on ne doit rien avoir émis avant, car ici sont générés les entetes)
    """
    filename = unescape_html(filename)
    REQUEST.RESPONSE.setHeader('Content-type', CSV_MIMETYPE)
    REQUEST.RESPONSE.setHeader('Content-Disposition', 'attachment; filename=%s' % filename)
    return data
#    head = """Content-type: %s; name="%s"
#Content-disposition: filename="%s"
#Title: %s
#
#""" % (CSV_MIMETYPE,filename,filename,title)
#    return head + str(data)

def sendPDFFile(REQUEST, data, filename):
    filename = unescape_html(filename)
    REQUEST.RESPONSE.setHeader('Content-type', PDF_MIMETYPE)
    REQUEST.RESPONSE.setHeader('Content-Disposition', 'attachment; filename=%s' % filename)
    return data

# Get SVN version
def get_svn_version(path):
    if os.path.exists('/usr/bin/svnversion'):
        return os.popen('svnversion ' + path).read().strip()
    else:
        return 'non disponible'
