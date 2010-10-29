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
from types import StringType, IntType, FloatType, UnicodeType, ListType, TupleType
import operator
import thread
import urllib, time, datetime, cgi
from sets import Set
import xml.sax.saxutils
from PIL import Image as PILImage

# XML generation package (apt-get install jaxml)
import jaxml
import simplejson as json
from SuppressAccents import suppression_diacritics
from sco_exceptions import *
from sco_permissions import *
from TrivialFormulator import TrivialFormulator, TF, tf_error_message


# ----- CALCUL ET PRESENTATION DES NOTES
NOTES_PRECISION=1e-4 # evite eventuelles erreurs d'arrondis
NOTES_MIN = 0.       # valeur minimale admise pour une note
NOTES_MAX = 100.
NOTES_NEUTRALISE=-1000. # notes non prises en comptes dans moyennes
NOTES_SUPPRESS=-1001.   # note a supprimer
NOTES_ATTENTE=-1002.    # note "en attente" (se calcule comme une note neutralisee)

NOTES_BARRE_GEN_TH = 10. # barre sur moyenne générale
#NOTES_BARRE_UE_TH = 8.      # barre sur UE 
#NOTES_BARRE_VALID_UE_TH=10. # seuil pour valider UE

NOTES_TOLERANCE = 0.00499999999999 # si note >= (BARRE-TOLERANCE), considere ok
                                   # (permet d'eviter d'afficher 10.00 sous barre alors que la moyenne vaut 9.999)
NOTES_BARRE_GEN = NOTES_BARRE_GEN_TH-NOTES_TOLERANCE # barre sur moyenne generale
#NOTES_BARRE_UE = NOTES_BARRE_UE_TH-NOTES_TOLERANCE   # barre sur UE
#NOTES_BARRE_VALID_UE = NOTES_BARRE_VALID_UE_TH-NOTES_TOLERANCE # seuil pour valider UE

UE_STANDARD = 0
UE_SPORT = 1
UE_STAGE_LP = 2 # ue "projet tuteuré et stage" dans les Lic. Pro.
UE_TYPE_NAME = { UE_STANDARD : 'Standard', 
                 UE_SPORT : 'Sport/Culture (points bonus)', 
                 UE_STAGE_LP : "Projet tuteuré et stage (Lic. Pro.)" }


def fmt_note(val, note_max=None, keep_numeric=False):
    """conversion note en str pour affichage dans tables HTML ou PDF.
    Si keep_numeric, laisse les valeur numeriques telles quelles (pour export Excel)
    """
    if val is None:
        return 'ABS'
    if val == NOTES_NEUTRALISE:
        return 'EXC' # excuse, note neutralise
    if val == NOTES_ATTENTE:
        return 'ATT' # attente, note neutralisee
    if type(val) == type(0.0) or type(val) == type(1):
        if note_max != None:
            val = val * 20. / note_max
        if keep_numeric:
            return val
        else:
            s = '%2.2f' % round(float(val),2) # 2 chiffres apres la virgule
            s = '0'*(5-len(s)) + s
            return s
    else:
        return val.replace('NA0', '-')  # notes sans le NA0

def fmt_coef(val):
    """Conversion valeur coefficient (float) en chaine
    """
    if val < 0.01:
        return '%g' % val # unusually small value
    return '%g' % round(val,2)

def fmt_abs(val):
    """ Conversion absences en chaine. val est une list [nb_abs_total, nb_abs_justifiees
    """
    return "%s / %s" % (val[1], val[0] - val[1])


# ----- Global lock for critical sections (except notes_tables caches)
GSL = thread.allocate_lock() # Global ScoDoc Lock

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
    sys.stderr.write('sco_utils: error in configuration file %s' %  _config_filename )
    raise

if CONFIG.CUSTOM_HTML_HEADER:
    CUSTOM_HTML_HEADER = open(CONFIG.CUSTOM_HTML_HEADER).read()
else:
    CUSTOM_HTML_HEADER = ''

if CONFIG.CUSTOM_HTML_HEADER_CNX:
    CUSTOM_HTML_HEADER_CNX = open(CONFIG.CUSTOM_HTML_HEADER_CNX).read()
else:
    CUSTOM_HTML_HEADER_CNX = ''

if CONFIG.CUSTOM_HTML_FOOTER:
    CUSTOM_HTML_FOOTER = open(CONFIG.CUSTOM_HTML_FOOTER).read()
else:
    CUSTOM_HTML_FOOTER = ''

if CONFIG.CUSTOM_HTML_FOOTER_CNX:
    CUSTOM_HTML_FOOTER_CNX = open(CONFIG.CUSTOM_HTML_FOOTER_CNX).read()
else:
    CUSTOM_HTML_FOOTER_CNX = ''

SCO_ENCODING = 'iso-8859-1' # used by Excel, XML, PDF, ...
# Attention: encodage lié au codage Zope et aussi à celui de postgresql
#            et aussi a celui des fichiers sources Python (comme celui-ci).

#def to_utf8(s):
#    return unicode(s, SCO_ENCODING).encode('utf-8')


SCO_DEFAULT_SQL_USER='www-data' # should match Zope process UID
SCO_DEFAULT_SQL_PORT='5432' # warning: 5433 for postgresql-8.1 on Debian if 7.4 also installed !
SCO_DEFAULT_SQL_USERS_CNX='dbname=SCOUSERS port=%s' % SCO_DEFAULT_SQL_PORT

# Valeurs utilisées pour affichage seulement, pas de requetes ni de mails envoyés:
SCO_WEBSITE  = 'https://www-rt.iutv.univ-paris13.fr/ScoDoc'
SCO_DEVEL_LIST = 'scodoc-devel@rt.iutv.univ-paris13.fr'
SCO_USERS_LIST = 'notes@rt.iutv.univ-paris13.fr'

# Mails avec exceptions (erreurs) anormales envoyés à cette adresse:
# mettre '' pour désactiver completement l'envois de mails d'erreurs.
# (ces mails sont précieux pour corriger les erreurs, ne les désactiver que si 
#  vous avez de bonnes raisons de le faire: vous pouvez me contacter avant)
SCO_DEV_MAIL = 'emmanuel.viennet@gmail.com'


CSV_FIELDSEP = ';'
CSV_LINESEP  = '\n'
CSV_MIMETYPE = 'text/comma-separated-values'
XLS_MIMETYPE = 'application/vnd.ms-excel'
PDF_MIMETYPE = 'application/pdf'
XML_MIMETYPE = 'text/xml'
JSON_MIMETYPE= 'application/json'

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

class WrapDict:
    """Wrap a dict so that getitem returns '' when values are None"""
    def __init__(self, adict, NoneValue=''):
        self.dict = adict
        self.NoneValue = NoneValue
    def __getitem__(self,key):
        value = self.dict[key]
        if value is None:
            return self.NoneValue
        else:
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
    """Escape &, <, >, quotes and double quotes"""
    return xml.sax.saxutils.escape( str(data),
                                    { "'" : '&apos;', '"' : '&quot;' } )

def dict_quote_xml_attr( d, fromhtml=False ):
    if fromhtml:
        # passe d'un code HTML a un code XML
        return dict( [ (k,quote_xml_attr(unescape_html(v))) for (k,v) in d.items() ] )
    else:
        # passe d'une chaine non quotée a du XML
        return  dict( [ (k,quote_xml_attr(v)) for (k,v) in d.items() ] )

def simple_dictlist2xml(dictlist, doc=None, tagname=None):
    """Represent a dict as XML data.
    All keys with string or numeric values are attributes (numbers converted to strings).
    All list values converted to list of childs (recursively).
    *** all other values are ignored ! ***
    """
    if not tagname:
        raise ValueError('invalid empty tagname !')
    if not doc:
        doc = jaxml.XML_document( encoding=SCO_ENCODING )
    scalar_types = [StringType, UnicodeType, IntType, FloatType]
    for d in dictlist:
        doc._push()
        d_scalar = dict( [ (k, quote_xml_attr(v)) for (k,v) in d.items() if type(v) in scalar_types ] )
        getattr(doc, tagname)(**d_scalar)
        d_list = dict( [ (k,v) for (k,v) in d.items() if type(v) == ListType ] )
        if d_list:
            for (k,v) in d_list.items():
                simple_dictlist2xml(v, doc=doc, tagname=k)
        doc._pop()
    return repr(doc)
        
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
    """Try to convert name to a reasonnable filename"""
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
    if REQUEST:
        REQUEST.RESPONSE.setHeader('Content-type', PDF_MIMETYPE)
        REQUEST.RESPONSE.setHeader('Content-Disposition', 'attachment; filename=%s' % filename)
    return data

def sendJSON(REQUEST, data):
    js = json.dumps(data, encoding=SCO_ENCODING)
    if REQUEST:
        REQUEST.RESPONSE.setHeader('Content-type', JSON_MIMETYPE)
    return js

def sendXML(REQUEST, data, tagname=None):
    if type(data) != ListType:
        data = [ data ] # always list-of-dicts
    xml = simple_dictlist2xml(data, tagname=tagname)
    if REQUEST:
        REQUEST.RESPONSE.setHeader('Content-type', XML_MIMETYPE)
    return xml

def sendResult(REQUEST, data, name=None, format=None):
    if format is None:
        return data
    elif format == 'xml': # name is outer tagname        
        return sendXML(REQUEST, data, tagname=name)
    elif format == 'json':
        return sendJSON(REQUEST, data)
    else:
        raise ValueError('invalid format: %s' % format)    

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

def annee_scolaire_repr(year, month):
    """representation de l'annee scolaire : '2009 - 2010'
    à partir d'une date.
    """
    if month > 8: # after september, 1 ?
        return '%s - %s' % (year, year + 1)
    else:
        return '%s - %s' % (year - 1, year)
    

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

def is_valid_mail(email):
    """True if well-formed email address"""
    return re.match( "^.+@.+\..{2,3}$", email)

ICONSIZES = {} # name : (width, height) cache image sizes
def icontag(name, file_format='png', **attrs):
    """tag HTML pour un icone.
    (dans les versions anterieures on utilisait Zope)
    Les icones sont des fichiers PNG dans .../static/icons
    Si la taille (width et height) n'est pas spécifiée, lit l'image 
    pour la mesurer (et cache le résultat).
    """
    if ('width' not in attrs) or ('height' not in attrs):
        if name not in ICONSIZES:
            img_file = SCO_SRCDIR + '/static/icons/%s.%s' % (name, file_format)
            im = PILImage.open(img_file)
            width, height = im.size[0], im.size[1]
            ICONSIZES[name] = (width, height) # cache
        else:
            width, height = ICONSIZES[name]
        attrs['width'] = width
        attrs['height'] = height
    if 'border' not in attrs:
        attrs['border'] = 0
    s = ' '.join([ '%s="%s"' % (k, attrs[k]) for k in attrs ])
    return '<img %s src="/ScoDoc/static/icons/%s.%s" />' % (s, name, file_format)
