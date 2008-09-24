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
import VERSION
import pdb
import os, sys, copy, re
import urllib, time, datetime, cgi
from sets import Set
import xml.sax.saxutils
# XML generation package (apt-get install jaxml)
import jaxml
from SuppressAccents import suppression_diacritics
from sco_exceptions import *
from sco_permissions import *
from TrivialFormulator import TrivialFormulator, TF, tf_error_message

# ----- Lecture du fichier de configuration
SCO_SRCDIR = os.path.split(VERSION.__file__)[0]

try:
    _config_filename = SCO_SRCDIR + '/config/scodoc_config.py'
    _config_text = open(_config_filename).read()
except:
    sys.stderr.write('sco_utils: cannot open configuration file %s' %  _config_filename )
    raise

try:
    exec( _config_text )
except:
    sys.stderr.write('sco_utils: error in configuartion file %s' %  _config_filename )
    raise


SCO_ENCODING = 'iso-8859-1' # used by Excel I/O
# Attention: encodage lié au codage Zope et aussi à celui de postgresql
#            et aussi a celui des fichiers sources Python (comme celui-ci).

#def to_utf8(s):
#    return unicode(s, SCO_ENCODING).encode('utf-8')


SCO_DEFAULT_SQL_USER='www-data' # should match Zope process UID
SCO_DEFAULT_SQL_PORT='5432' # warning: 5433 for postgresql-8.1 on Debian if 7.4 also installed !
SCO_DEFAULT_SQL_USERS_CNX='dbname=SCOUSERS port=%s' % SCO_DEFAULT_SQL_PORT

SCO_WEBSITE  = 'https://www-rt.iutv.univ-paris13.fr/ScoDoc'
SCO_DEVEL_LIST = 'scodoc-devel@rt.iutv.univ-paris13.fr'
# Mails avec exceptions (erreurs) anormales envoyés à cette adresse:
SCO_DEV_MAIL = 'emmanuel.viennet@gmail.com'

CSV_FIELDSEP = ';'
CSV_LINESEP  = '\n'
CSV_MIMETYPE = 'text/comma-separated-values'
XLS_MIMETYPE = 'application/vnd.ms-excel'
PDF_MIMETYPE = 'application/pdf'
XML_MIMETYPE = 'text/xml'


ICON_PDF = '<img src="icons/pdficon16x20_img" border="0" title="Version PDF"/>'
ICON_XLS = '<img src="icons/xlsicon_img" border="0" title="Version tableur"/>'

class DictDefault(dict):
    """A dictionnary with default value for all keys
    Each time a non existent key is requested, it is added to the dict.
    (used in python 2.4, can't use new __missing__ method)
    """
    defaultvalue = 0
    def __init__(self, defaultvalue=0, kv_dict = {}):
        dict.__init__(self)
        self.defaultvalue = defaultvalue
        self.update(kv_dict)
    def  __getitem__(self, k):
        if self.has_key(k):
            return self.get(k)        
        value = copy.copy(self.defaultvalue)
        self[k] = value
        return value


MODALITY_NAMES = DictDefault(
    kv_dict = { 'FI' : 'Formations Initiales',
                'FC' : 'Formations Continues',
                'FAP': 'Formations en Apprentissage',
                },
    defaultvalue = 'Autres formations' )

MODALITY_ORDER = DictDefault(
    kv_dict={ 'FI':10, 'FAP' : 20, 'FC' : 30 }, defaultvalue = 100 )


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
    s = str(s).strip().replace( '&amp;', '&' )
    s = s.replace('&lt;','<')
    s = s.replace('&gt;','>')
    return s


def quote_xml_attr( data ):
    """Escape &, <, >, quotes and doule quotes"""
    return xml.sax.saxutils.escape( str(data),
                                    { "'" : '&apos;', '"' : '&quot;' } )

def dict_quote_xml_attr( d, fromhtml=False ):
    if fromhtml:
        # passe d'un code HTML a un code XML
        return dict( [ (k,quote_xml_attr(unescape_html(v))) for (k,v) in d.items() ] )
    else:
        # passe d'une chaine non quotée a du XML
        return  dict( [ (k,quote_xml_attr(v)) for (k,v) in d.items() ] )

def strnone(s):
    "convert s to string, '' if s is false"
    if s:
        return str(s)
    else:
        return ''

def stripquotes(s):
    "strip s from spaces and quotes"
    s = s.strip()
    if s and ((s[0] == '"' and s[-1] == '"') or (s[0] == "'" and s[-1] == "'")):
        s = s[1:-1]
    return s

def suppress_accents(s):
    "s is an ordinary string, encoding given by SCO_ENCODING"
    return str(suppression_diacritics(unicode(s, SCO_ENCODING)))

def make_filename(name):
    "try to convert name to a reasonnable filename"""
    return suppress_accents(name).replace(' ', '_')

def sendCSVFile(REQUEST,data,filename):
    """publication fichier.
    (on ne doit rien avoir émis avant, car ici sont générés les entetes)
    """
    filename = unescape_html(suppress_accents(filename)).replace('&','').replace(' ','_')
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
    filename = unescape_html(suppress_accents(filename)).replace('&','').replace(' ','_')
    REQUEST.RESPONSE.setHeader('Content-type', PDF_MIMETYPE)
    REQUEST.RESPONSE.setHeader('Content-Disposition', 'attachment; filename=%s' % filename)
    return data

# Get SVN version
def get_svn_version(path):
    if os.path.exists('/usr/bin/svnversion'):
        try:
            return os.popen('svnversion ' + path).read().strip()
        except:
            return 'non disponible (erreur de lecture)'
    else:
        return 'non disponible'

def abbrev_prenom(prenom):
    "Donne l'abreviation d'un prenom"
    # un peu lent, mais espère traiter tous les cas
    # Jean -> J.
    # Charles -> Ch.
    # Jean-Christophe -> J.-C.
    # Marie Odile -> M. O.
    prenom = prenom.replace('.', ' ').strip()
    if not prenom:
        return prenom
    d = prenom[:3].upper()
    if d == 'CHA':
        abrv = 'Ch.' # 'Charles' donne 'Ch.'
        i = 3
    else:
        abrv = prenom[0].upper() + '.'
        i = 1
    n = len(prenom)
    while i < n:
        c = prenom[i]
        if c == ' ' or c == '-' and i < n-1:
            sep = c
            i += 1
            # gobbe tous les separateurs
            while i < n and  (prenom[i] == ' ' or prenom[i] == '-'):
                if prenom[i] == '-':
                    sep = '-'
                i += 1
            if i < n:
                abrv += sep + prenom[i].upper() + '.'
        i += 1
    return abrv

#
def timedate_human_repr():
    "representation du temps courant pour utilisateur: a localiser"
    return time.strftime('%d/%m/%Y à %Hh%M')

# Graphes (optionnel pour ne pas accroitre les dependances de ScoDoc)
try:
    import pydot
    WITH_PYDOT = True
except:
    WITH_PYDOT = False


from sgmllib import SGMLParser

class html2txt_parser(SGMLParser):
  """html2txt()
  """
  def reset(self):
    """reset() --> initialize the parser"""
    SGMLParser.reset(self)
    self.pieces = []
  
  def handle_data(self, text):
    """handle_data(text) --> appends the pieces to self.pieces
    handles all normal data not between brackets "<>"
    """
    self.pieces.append(text)
  
  def handle_entityref(self, ref):
    """called for each entity reference, e.g. for "&copy;", ref will be
    "copy"
    Reconstruct the original entity reference.
    """
    if ref=='amp':
      self.pieces.append("&")
  
  def output(self):
    """Return processed HTML as a single string"""
    return " ".join(self.pieces)

def scodoc_html2txt(html):
  parser = html2txt_parser()
  parser.reset()
  parser.feed(html)
  parser.close()
  return parser.output()
