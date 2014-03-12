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


""" Common definitions
"""
from VERSION import SCOVERSION
import VERSION
import pdb
import os, sys, copy, re
import pprint
from types import StringType, IntType, FloatType, UnicodeType, ListType, TupleType
import operator, bisect
import thread
import urllib
import urllib2
import socket
import xml.sax.saxutils
import xml, xml.dom.minidom
import time, datetime, cgi

from sets import Set

from PIL import Image as PILImage

# XML generation package (apt-get install jaxml)
import jaxml

import json
from SuppressAccents import suppression_diacritics
from sco_exceptions import *
from sco_permissions import *
from TrivialFormulator import TrivialFormulator, TF, tf_error_message
from notes_log import log

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
#UE_FONDAMENTALE = 3 # ue dite "fondamentale" dans certains parcours (eg UCAC)
#UE_OPTIONNELLE  = 4 # ue dite "optionnelle" dans certains parcours (eg UCAC)

UE_TYPE_NAME = { UE_STANDARD : 'Standard', 
                 UE_SPORT : 'Sport/Culture (points bonus)', 
                 UE_STAGE_LP : "Projet tuteuré et stage (Lic. Pro.)",
#                 UE_FONDAMENTALE : '"Fondamentale" (eg UCAC)',
#                 UE_OPTIONNELLE : '"Optionnelle" (UCAC)'
                 }

# Couleurs RGB (dans [0.,1.]) des UE pour les bulletins:
UE_DEFAULT_COLOR = (150/255.,200/255.,180/255.)
UE_COLORS = { UE_STANDARD : UE_DEFAULT_COLOR, 
              UE_SPORT : (0.40, 0.90, 0.50),
              UE_STAGE_LP : (0.80, 0.90, 0.90)
              }

# borne supérieure de chaque mention
NOTES_MENTIONS_TH = (NOTES_TOLERANCE, 7., 10., 12., 14., 16., 18., 20.+NOTES_TOLERANCE)
NOTES_MENTIONS_LABS=('Nul', 'Faible', 'Insuffisant', 'Passable', 'Assez bien', 'Bien', 'Très bien', 'Excellent')

EVALUATION_NORMALE = 0
EVALUATION_RATTRAPAGE = 1

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
        if note_max != None and note_max > 0:
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


def get_mention(moy):
    """Texte "mention" en fonction de la moyenne générale"""
    try:
        moy = float(moy)
    except:
        return ''
    return NOTES_MENTIONS_LABS[bisect.bisect_right(NOTES_MENTIONS_TH, moy)]

# ----- Global lock for critical sections (except notes_tables caches)
GSL = thread.allocate_lock() # Global ScoDoc Lock

# ----- Lecture du fichier de configuration
SCO_SRCDIR = os.path.split(VERSION.__file__)[0]
if SCO_SRCDIR:
    SCO_SRCDIR += '/'
try:
    _config_filename = SCO_SRCDIR + 'config/scodoc_config.py'
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

SCO_ENCODING = 'utf-8' # used by Excel, XML, PDF, ...
# Attention: encodage lié au codage Zope et aussi à celui de postgresql
#            et aussi a celui des fichiers sources Python (comme celui-ci).

#def to_utf8(s):
#    return unicode(s, SCO_ENCODING).encode('utf-8')


SCO_DEFAULT_SQL_USER='www-data' # should match Zope process UID
SCO_DEFAULT_SQL_PORT='5432' # warning: 5433 for postgresql-8.1 on Debian if 7.4 also installed !
SCO_DEFAULT_SQL_USERS_CNX='dbname=SCOUSERS port=%s' % SCO_DEFAULT_SQL_PORT

# Valeurs utilisées pour affichage seulement, pas de requetes ni de mails envoyés:
SCO_WEBSITE  = 'https://trac.lipn.univ-paris13.fr/projects/scodoc/wiki'
SCO_ANNONCES_WEBSITE = 'https://www-rt.iutv.univ-paris13.fr/mailman/listinfo/scodoc-annonces'
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

def group_by_key(d, key) :
    g = DictDefault(defaultvalue=[])
    for e in d:
        g[e[key]].append(e)
    return g


# Admissions des étudiants
# Différents types de voies d'admission:
# (stocké en texte libre dans la base, mais saisie par menus pour harmoniser)
TYPE_ADMISSION_DEFAULT='Inconnue'
TYPES_ADMISSION=(TYPE_ADMISSION_DEFAULT, 'APB', 'APB-PC', 'CEF', 'Direct')

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

# test if obj is iterable (but not a string)
isiterable = lambda obj: getattr(obj, '__iter__', False)

def unescape_html_dict(d):
    """un-escape all dict values, recursively"""
    try:        
        indices = d.keys()
    except:
        indices = range(len(d))
    for k in indices:
        v = d[k]
        if type(v) == StringType:
            d[k] = unescape_html(v)
        elif isiterable(v):
            unescape_html_dict(v)
    
def quote_xml_attr( data ):
    """Escape &, <, >, quotes and double quotes"""
    return xml.sax.saxutils.escape( str(data),
                                    { "'" : '&apos;', '"' : '&quot;' } )

def dict_quote_xml_attr( d, fromhtml=False ):
    """Quote XML entities in dict values.
    Non recursive (but probbaly should be...).
    Returns a new dict.
    """
    if fromhtml:
        # passe d'un code HTML a un code XML
        return dict( [ (k,quote_xml_attr(unescape_html(v))) for (k,v) in d.items() ] )
    else:
        # passe d'une chaine non quotée a du XML
        return  dict( [ (k,quote_xml_attr(v)) for (k,v) in d.items() ] )

def simple_dictlist2xml(dictlist, doc=None, tagname=None, quote=False):
    """Represent a dict as XML data.
    All keys with string or numeric values are attributes (numbers converted to strings).
    All list values converted to list of childs (recursively).
    *** all other values are ignored ! ***
    Values (xml entities) are not quoted, except if requested by quote argument.

    Exemple:
     simple_dictlist2xml([ { 'id' : 1, 'ues' : [{'note':10},{}] } ], tagname='infos')

    <?xml version="1.0" encoding="utf-8"?>
    <infos id="1">
      <ues note="10" />
      <ues />
    </infos>
    
    """
    if not tagname:
        raise ValueError('invalid empty tagname !')
    if not doc:
        doc = jaxml.XML_document( encoding=SCO_ENCODING )
    scalar_types = [StringType, UnicodeType, IntType, FloatType]
    for d in dictlist:
        doc._push()
        if quote:
            d_scalar = dict( [ (k, quote_xml_attr(v)) for (k,v) in d.items() if type(v) in scalar_types ] )
        else:
            d_scalar = dict( [ (k, v) for (k,v) in d.items() if type(v) in scalar_types ] )
        getattr(doc, tagname)(**d_scalar)
        d_list = dict( [ (k,v) for (k,v) in d.items() if type(v) == ListType ] )
        if d_list:
            for (k,v) in d_list.items():
                simple_dictlist2xml(v, doc=doc, tagname=k, quote=quote)
        doc._pop()
    return doc

# Expression used to check noms/prenoms
FORBIDDEN_CHARS_EXP = re.compile( r'[*\|~\(\)\\]' )

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
    REQUEST.RESPONSE.setHeader('content-type', CSV_MIMETYPE)
    REQUEST.RESPONSE.setHeader('content-disposition', 'attachment; filename="%s"' % filename)
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
        REQUEST.RESPONSE.setHeader('content-type', PDF_MIMETYPE)
        REQUEST.RESPONSE.setHeader('content-disposition', 'attachment; filename="%s"' % filename)
    return data

def sendJSON(REQUEST, data):
    js = json.dumps(data, encoding=SCO_ENCODING, indent=1)
    if REQUEST:
        REQUEST.RESPONSE.setHeader('content-type', JSON_MIMETYPE)
    return js

def sendXML(REQUEST, data, tagname=None, force_outer_xml_tag=True):
    if type(data) != ListType:
        data = [ data ] # always list-of-dicts
    if force_outer_xml_tag:
        root_tagname = tagname + '_list'
        doc = jaxml.XML_document( encoding=SCO_ENCODING )
        getattr(doc, root_tagname)()
        doc._push()
    else:
        doc = None
    doc = simple_dictlist2xml(data, doc=doc, tagname=tagname)
    if force_outer_xml_tag:
        doc._pop()
    if REQUEST:
        REQUEST.RESPONSE.setHeader('content-type', XML_MIMETYPE)
    return repr(doc)

def sendResult(REQUEST, data, name=None, format=None, force_outer_xml_tag=True):
    if format is None:
        return data
    elif format == 'xml': # name is outer tagname        
        return sendXML(REQUEST, data, tagname=name, force_outer_xml_tag=force_outer_xml_tag)
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


# Simple string manipulations
# on utf-8 encoded python strings
# (yes, we should only use unicode strings, but... we use only strings)
def strupper(s):
    return s.decode(SCO_ENCODING).upper().encode(SCO_ENCODING)

def strlower(s):
    return s.decode(SCO_ENCODING).lower().encode(SCO_ENCODING)

def strcapitalize(s):
    return s.decode(SCO_ENCODING).capitalize().encode(SCO_ENCODING)

def abbrev_prenom(prenom):
    "Donne l'abreviation d'un prenom"
    # un peu lent, mais espère traiter tous les cas
    # Jean -> J.
    # Charles -> Ch.
    # Jean-Christophe -> J.-C.
    # Marie Odile -> M. O.    
    prenom = prenom.decode(SCO_ENCODING).replace('.', ' ').strip()
    if not prenom:
        return ''
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
    return abrv.encode(SCO_ENCODING)

#
def timedate_human_repr():
    "representation du temps courant pour utilisateur: a localiser"
    return time.strftime('%d/%m/%Y à %Hh%M')

def annee_scolaire_repr(year, month):
    """representation de l'annee scolaire : '2009 - 2010'
    à partir d'une date.
    """
    if month > 7: # apres le 1er aout
        return '%s - %s' % (year, year + 1)
    else:
        return '%s - %s' % (year - 1, year)

def annee_scolaire_debut(year, month):
    """Annee scolaire de debut (septembre): heuristique pour l'hémisphère nord..."""
    if int(month) > 7:
        return int(year)
    else:
        return int(year) - 1

# Graphes (optionnel pour ne pas accroitre les dependances de ScoDoc)
try:
    import pydot
    WITH_PYDOT = True
except:
    WITH_PYDOT = False

if WITH_PYDOT:
    # check API (incompatible change after pydot version 0.9.10: scodoc install may use old or new version)
    junk_graph = pydot.Dot('junk')
    junk_graph.add_node(pydot.Node('a'))
    n = junk_graph.get_node('a')
    if type(n) == type([]):
        def pydot_get_node(g, name):
            r = g.get_node(name)
            if not r:
                return r
            else:
                return r[0]
    else:
        def pydot_get_node(g, name):
            return g.get_node(name)


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
    if 'alt' not in attrs:
        attrs['alt'] = 'logo %s' % name
    s = ' '.join([ '%s="%s"' % (k, attrs[k]) for k in attrs ])
    return '<img %s src="/ScoDoc/static/icons/%s.%s" />' % (s, name, file_format)

ICON_PDF = icontag('pdficon16x20_img', title="Version PDF")
ICON_XLS = icontag('xlsicon_img', title="Version tableur")

def sort_dates(L, reverse=False):
    """Return sorted list of dates, allowing None items (they are put at the beginning)"""
    mindate = datetime.datetime(datetime.MINYEAR, 1, 1)
    try:
        return sorted(L, key=lambda x: x or mindate, reverse=reverse)
    except:
        # Helps debugging 
        log('sort_dates( %s )' % L )
        raise


def query_portal(req, msg='Apogee', timeout=3):
    """retreive external data using http request
    (used to connect to Apogee portal, or ScoDoc server)
    """
    log('query_portal: %s' % req )
    # band aid for Python 2.4: must use GLOBAL socket timeout
    orig_timeout = socket.getdefaulttimeout()
    try:        
        socket.setdefaulttimeout(timeout) #  seconds / request
        f = urllib2.urlopen(req) # XXX ajouter timeout (en Python 2.6 !)
    except:
        log("query_portal: can't connect to %s" % msg)
        return ''
    socket.setdefaulttimeout(orig_timeout)
    return f.read()
