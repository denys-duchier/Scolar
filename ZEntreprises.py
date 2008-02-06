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

""" Gestion des relations avec les entreprises
"""
import urllib

from OFS.SimpleItem import Item # Basic zope object
from OFS.PropertyManager import PropertyManager # provide the 'Properties' tab with the
                                # 'manage_propertiesForm' method
from OFS.ObjectManager import ObjectManager
from AccessControl.Role import RoleManager # provide the 'Ownership' tab with
                                # the 'manage_owner' method
from AccessControl import ClassSecurityInfo
import Globals
from Globals import DTMLFile # can use DTML files
from Globals import Persistent
from Acquisition import Implicit

# where we exist on the file system
file_path = Globals.package_home(globals())

# ---------------

from notesdb import *
from notes_log import log
from scolog import logdb
from sco_exceptions import *
from sco_utils import *
import html_sidebar

from ScolarRolesNames import *
from TrivialFormulator import TrivialFormulator, TF
import scolars
import string, re
import time, calendar 

def _format_nom(nom):
    "formatte nom (filtre en entree db) d'une entreprise"
    if not nom:
        return nom
    return nom[0].upper() + nom[1:]


class EntreprisesEditor(EditableTable):
    def delete(self, cnx, oid):
        "delete correspondants and contacts, then self"
        # first, delete all correspondants and contacts
        cursor = cnx.cursor()
        cursor.execute('delete from entreprise_contact where entreprise_id=%(entreprise_id)d',
                       { 'entreprise_id' : oid } )    
        cursor.execute('delete from entreprise_correspondant where entreprise_id=%(entreprise_id)d',
                       { 'entreprise_id' : oid } )
        cnx.commit()
        EditableTable.delete(self, cnx, oid)
        
    def list(self, cnx, args={},
             operator = 'and', test='=', sortkey=None,
             sort_on_contact=False, ZEntrepriseInstance=None ):
        # list, then sort on date of last contact
        R = EditableTable.list(self, cnx, args=args,
                               operator=operator, test=test, sortkey=sortkey)
        if sort_on_contact:
            for r in R:
                c = ZEntrepriseInstance.do_entreprise_contact_list(
                    args={ 'entreprise_id' : r['entreprise_id'] },
                    disable_formatting=True)
                if c:
                    r['date'] = max( [ x['date'] for x in c ] )
                else:
                    r['date'] = None
            # sort
            R.sort( lambda r1, r2: cmp(r2['date'],r1['date']) )
            for r in R:
                r['date'] = DateISOtoDMY(r['date'])
        return R

    def list_by_etud(self, cnx, args={},
                     sort_on_contact=False, disable_formatting=False):
        "cherche rentreprise ayant eu contact avec etudiant"
        cursor = cnx.cursor()
        cursor.execute('select E.*, I.nom as etud_nom, I.prenom as etud_prenom, C.date from entreprises E, entreprise_contact C, identite I where C.entreprise_id = E.entreprise_id and C.etudid = I.etudid and I.nom ~* %(etud_nom)s ORDER BY E.nom',
                       args )
        titles, res = [ x[0] for x in cursor.description ], cursor.fetchall()
        R = []
        for r in res:
            d = {}
            for i in range(len(titles)):
                v = r[i]
                # format value 
                if not disable_formatting and self.output_formators.has_key(titles[i]):
                    v = self.output_formators[titles[i]](v)
                d[titles[i]] = v
            R.append(d)
        # sort
        if sort_on_contact:
            R.sort( lambda r1, r2: cmp(r2['date'],r1['date']) )
        for r in R:
            r['date'] = DateISOtoDMY(r['date'])
        return R

_entreprisesEditor = EntreprisesEditor(
    'entreprises',
    'entreprise_id',
    ('entreprise_id',
     'nom',
     'adresse', 'ville', 'codepostal', 'pays',
     'contact_origine',
     'secteur', 'privee', 'localisation', 'qualite_relation', 'plus10salaries',
     'note', 'date_creation'),
    sortkey = 'nom',
    input_formators = { 'nom' : _format_nom },
    )

# -----------  Correspondants
_entreprise_correspEditor = EditableTable(
    'entreprise_correspondant',
    'entreprise_corresp_id',
    ('entreprise_corresp_id', 'entreprise_id',
     'civilite', 'nom', 'prenom', 'fonction',
     'phone1', 'phone2', 'mobile', 'fax', 'mail1', 'mail2',
     'note'),
    sortkey = 'nom' )
    

# -----------  Contacts
_entreprise_contactEditor = EditableTable(
    'entreprise_contact',
    'entreprise_contact_id',
    ('entreprise_contact_id', 'date',
     'type_contact', 'entreprise_id', 'entreprise_corresp_id',
     'etudid', 'description', 'enseignant'),
    sortkey = 'date',
    output_formators = { 'date' : DateISOtoDMY },
    input_formators  = { 'date' : DateDMYtoISO }
    )

# ---------------

class ZEntreprises(ObjectManager,
                   PropertyManager,
                   RoleManager,
                   Item,
                   Persistent,
                   Implicit
                   ):

    "ZEntreprises object"

    meta_type = 'ZEntreprises'
    security=ClassSecurityInfo()

    # This is the list of the methods associated to 'tabs' in the ZMI
    # Be aware that The first in the list is the one shown by default, so if
    # the 'View' tab is the first, you will never see your tabs by cliquing
    # on the object.
    manage_options = (
        ( {'label': 'Contents', 'action': 'manage_main'}, )
        + PropertyManager.manage_options # add the 'Properties' tab
        + (
# this line is kept as an example with the files :
#     dtml/manage_editZScolarForm.dtml
#     html/ZScolar-edit.stx
#	{'label': 'Properties', 'action': 'manage_editForm',},
	{'label': 'View',       'action': 'index_html'},
        )
        + Item.manage_options            # add the 'Undo' & 'Owner' tab 
        + RoleManager.manage_options     # add the 'Security' tab
        )

    # no permissions, only called from python
    def __init__(self, id, title):
	"initialise a new instance"
        self.id = id
	self.title = title    
    
    # The form used to edit this object
    def manage_editZEntreprises(self, title, RESPONSE=None):
        "Changes the instance values"
        self.title = title
        self._p_changed = 1
        RESPONSE.redirect('manage_editForm')

    # Ajout (dans l'instance) d'un dtml modifiable par Zope
    def defaultDocFile(self,id,title,file):
        f=open(file_path+'/dtml-editable/'+file+'.dtml')     
        file=f.read()     
        f.close()     
        self.manage_addDTMLMethod(id,title,file)

    security.declareProtected(ScoEntrepriseView, 'entreprise_header')
    def entreprise_header(self,REQUEST):
        "common header for all Entreprises pages"
        authuser = REQUEST.AUTHENTICATED_USER
        # _read_only is used to modify pages properties (links, buttons)
        # Python methods (do_xxx in this class) are also protected individualy)
        if authuser.has_permission(ScoEntrepriseChange,self):
            REQUEST.set( '_read_only', False )
        else:
            REQUEST.set( '_read_only', True )
        return self.sco_header(REQUEST, container=self)

    security.declareProtected(ScoEntrepriseView, 'entreprise_footer')
    def entreprise_footer(self,REQUEST):
        "common entreprise footer"
        return self.sco_footer(REQUEST) 

    security.declareProtected(ScoEntrepriseView, 'sidebar')
    def sidebar(self, REQUEST):
        "barre gauche (overide std sco sidebar)"
        # rewritten from legacy DTML code
        context = self
        params = {
            'ScoURL' : context.ScoURL(),
        }
        
        H = [
            """<div id="sidebar-container">
            <div class="sidebar">""",
            html_sidebar.sidebar_common(context, REQUEST),
            """<h2 class="insidebar"><a href="%(ScoURL)s/Entreprises" class="sidebar">Entreprises</a></h2>
<ul class="insidebar">""" % params ]
        if not REQUEST['_read_only']:
            H.append("""<li class="insidebar"><a href="%(ScoURL)s/Entreprises/entreprise_create" class="sidebar">Nouvelle entreprise</a> </li>""" % params )
        
        H.append("""<li class="insidebar"><a href="%(ScoURL)s/Entreprises/entreprise_contact_list" class="sidebar">Contacts</a> </li></ul> """ % params )

        # --- entreprise selectionnée:
        if REQUEST.form.has_key('entreprise_id'):
            entreprise_id = REQUEST.form['entreprise_id']
            E = context.do_entreprise_list( args={ 'entreprise_id' : entreprise_id } )[0]
            params.update(E)
            H.append("""<div class="entreprise-insidebar">
  <h3 class="insidebar"><a href="%(ScoURL)s/Entreprises/entreprise_edit?entreprise_id=%(entreprise_id)s" class="sidebar">%(nom)s</a></h2>
  <ul class="insidebar">
  <li class="insidebar"><a href="%(ScoURL)s/Entreprises/entreprise_correspondant_list?entreprise_id=%(entreprise_id)s" class="sidebar">Corresp.</a></li>""" % params ) # """
            if not REQUEST['_read_only']:
                H.append("""<li class="insidebar"><a href="%(ScoURL)s/Entreprises/entreprise_correspondant_create?entreprise_id=%(entreprise_id)s" class="sidebar">Nouveau Corresp.</a></li>""" % params )
            H.append("""<li class="insidebar"><a href="%(ScoURL)s/Entreprises/entreprise_contact_list?entreprise_id=%(entreprise_id)s" class="sidebar">Contacts</a></li>""" % params )
            if not REQUEST['_read_only']:
                H.append("""<li class="insidebar"><a href="%(ScoURL)s/Entreprises/entreprise_contact_create?entreprise_id=%(entreprise_id)s" class="sidebar">Nouveau "contact"</a></li>""" % params )
            H.append('</ul></div>')

        #
        H.append("""<br><br>%s""" % context.scodoc_img.entreprise_side_img.tag() )
        if REQUEST['_read_only']:
            H.append("""<br><em>(Lecture seule)</em>""")
        H.append("""</div> </div> <!-- end of sidebar -->""")
        return ''.join(H)
    
    # --------------------------------------------------------------------
    #
    #   Entreprises : Methodes en DTML
    #
    # --------------------------------------------------------------------
    # used to view content of the object
    security.declareProtected(ScoEntrepriseView, 'index_html')
    index_html = DTMLFile('dtml/entreprises/index_html', globals())

    #security.declareProtected(ScoEntrepriseView, 'sidebar')
    #sidebar = DTMLFile('dtml/entreprises/sidebar', globals())
  
    security.declareProtected(ScoEntrepriseView, 'entreprise_contact_list')
    entreprise_contact_list = DTMLFile('dtml/entreprises/entreprise_contact_list',globals())
    security.declareProtected(ScoEntrepriseView, 'entreprise_correspondant_list')
    entreprise_correspondant_list = DTMLFile('dtml/entreprises/entreprise_correspondant_list',globals())
    # les methodes "edit" sont aussi en ScoEntrepriseView car elles permettent
    # la visualisation (via variable _read_only positionnee dans entreprise_header)
    security.declareProtected(ScoEntrepriseView, 'entreprise_contact_edit')
    entreprise_contact_edit = DTMLFile('dtml/entreprises/entreprise_contact_edit',globals())
    security.declareProtected(ScoEntrepriseView, 'entreprise_correspondant_edit')
    entreprise_correspondant_edit = DTMLFile('dtml/entreprises/entreprise_correspondant_edit',globals())
    security.declareProtected(ScoEntrepriseView, 'entreprise_edit')
    entreprise_edit = DTMLFile('dtml/entreprises/entreprise_edit',globals())
    
    # Acces en modification:
    security.declareProtected(ScoEntrepriseChange, 'entreprise_contact_create')
    entreprise_contact_create = DTMLFile('dtml/entreprises/entreprise_contact_create',globals())
    security.declareProtected(ScoEntrepriseChange, 'entreprise_contact_delete')
    entreprise_contact_delete = DTMLFile('dtml/entreprises/entreprise_contact_delete',globals())
    security.declareProtected(ScoEntrepriseChange, 'entreprise_correspondant_create')
    entreprise_correspondant_create = DTMLFile('dtml/entreprises/entreprise_correspondant_create',globals())
    security.declareProtected(ScoEntrepriseChange, 'entreprise_correspondant_delete')
    entreprise_correspondant_delete = DTMLFile('dtml/entreprises/entreprise_correspondant_delete',globals())
    security.declareProtected(ScoEntrepriseChange, 'entreprise_create')
    entreprise_create = DTMLFile('dtml/entreprises/entreprise_create',globals())
    security.declareProtected(ScoEntrepriseChange, 'entreprise_delete')
    entreprise_delete = DTMLFile('dtml/entreprises/entreprise_delete',globals())

    # --------------------------------------------------------------------
    #
    #   Entreprises : Methodes en Python
    #
    # --------------------------------------------------------------------
    security.declareProtected(ScoEntrepriseChange, 'do_entreprise_create')
    def do_entreprise_create(self, args):
        "entreprise_create"
        cnx = self.GetDBConnexion()
        r = _entreprisesEditor.create(cnx, args)
        return r

    security.declareProtected(ScoEntrepriseChange, 'do_entreprise_delete')
    def do_entreprise_delete(self, oid):
        "entreprise_delete"
        cnx = self.GetDBConnexion()
        _entreprisesEditor.delete(cnx, oid)
        
    security.declareProtected(ScoEntrepriseView, 'do_entreprise_list')
    def do_entreprise_list(self, **kw):
        "entreprise_list"
        cnx = self.GetDBConnexion()
        kw['ZEntrepriseInstance'] = self
        return _entreprisesEditor.list( cnx, **kw )

    security.declareProtected(ScoEntrepriseView, 'do_entreprise_list_by_etud')
    def do_entreprise_list_by_etud(self, **kw):
        "entreprise_list_by_etud"
        cnx = self.GetDBConnexion()
        return _entreprisesEditor.list_by_etud( cnx, **kw )

    security.declareProtected(ScoEntrepriseView, 'do_entreprise_edit')
    def do_entreprise_edit(self, *args, **kw):
        "entreprise_edit"
        cnx = self.GetDBConnexion()
        _entreprisesEditor.edit( cnx, *args, **kw )


    security.declareProtected(ScoEntrepriseChange, 'do_entreprise_correspondant_create')
    def do_entreprise_correspondant_create(self, args):
        "entreprise_correspondant_create"
        cnx = self.GetDBConnexion()
        r = _entreprise_correspEditor.create(cnx, args)
        return r

    security.declareProtected(ScoEntrepriseChange, 'do_entreprise_correspondant_delete')
    def do_entreprise_correspondant_delete(self, oid):
        "entreprise_correspondant_delete"
        cnx = self.GetDBConnexion()
        _entreprise_correspEditor.delete(cnx, oid)
        
    security.declareProtected(ScoEntrepriseView, 'do_entreprise_correspondant_list')
    def do_entreprise_correspondant_list(self, **kw):
        "entreprise_correspondant_list"
        cnx = self.GetDBConnexion()
        return _entreprise_correspEditor.list( cnx, **kw )

    security.declareProtected(ScoEntrepriseView, 'do_entreprise_correspondant_edit')
    def do_entreprise_correspondant_edit(self, *args, **kw):
        "entreprise_correspondant_edit"
        cnx = self.GetDBConnexion()
        _entreprise_correspEditor.edit( cnx, *args, **kw )

    def do_entreprise_correspondant_listnames(self, args={}):
        "-> liste des noms des correspondants (pour affichage menu)"
        cnx = self.GetDBConnexion()
        C = self.do_entreprise_correspondant_list(args=args)    
        return [ (x['prenom'] + ' ' + x['nom'],
                  str(x['entreprise_corresp_id'])) for x in C ]
    
    
    security.declareProtected(ScoEntrepriseChange, 'do_entreprise_contact_create')
    def do_entreprise_contact_create(self, args):
        "entreprise_contact_create"
        cnx = self.GetDBConnexion()
        r = _entreprise_contactEditor.create(cnx, args)
        return r

    security.declareProtected(ScoEntrepriseChange, 'do_entreprise_contact_delete')
    def do_entreprise_contact_delete(self, oid):
        "entreprise_contact_delete"
        cnx = self.GetDBConnexion()
        _entreprise_contactEditor.delete(cnx, oid)
        
    security.declareProtected(ScoEntrepriseView, 'do_entreprise_contact_list')
    def do_entreprise_contact_list(self, **kw):
        "entreprise_contact_list"
        cnx = self.GetDBConnexion()
        return _entreprise_contactEditor.list( cnx, **kw )

    security.declareProtected(ScoEntrepriseView, 'do_entreprise_contact_edit')
    def do_entreprise_contact_edit(self, *args, **kw):
        "entreprise_contact_edit"
        cnx = self.GetDBConnexion()
        _entreprise_contactEditor.edit( cnx, *args, **kw )
   
    #
    security.declareProtected(ScoEntrepriseView, 'do_entreprise_check_etudiant')
    def do_entreprise_check_etudiant(self, etudiant):
        """Si etudiant est vide, ou un ETUDID valide, ou un nom unique,
        retourne (1, ETUDID).
        Sinon, retourne (0, 'message explicatif')
        """
        etudiant = etudiant.strip()
        if not etudiant:
            return 1, None
        cnx = self.GetDBConnexion()
        cursor = cnx.cursor()
        cursor.execute('select etudid, nom, prenom from identite where upper(nom) ~ upper(%(etudiant)s) or etudid=%(etudiant)s',
                       { 'etudiant' : etudiant } )
        r = cursor.fetchall()
        if len(r) < 1:
            return 0, 'Aucun etudiant ne correspond à "%s"' % etudiant
        elif len(r) > 10:
            return 0, '<b>%d etudiants</b> correspondent à ce nom (utilisez le code)'%len(r)
        elif len(r) > 1:
            e = [ '<ul class="entreprise_etud_list">' ]
            for x in r:
                e.append( '<li>%s %s (code %s)</li>' % (x[1].upper(),x[2],x[0].strip()) )
            e.append('</ul>')
            return 0, 'Les étudiants suivants correspondent: préciser le nom complet ou le code\n' + '\n'.join(e) 
        else: # une seule reponse !
            return 1, r[0][0].strip()

    security.declareProtected(ScoEntrepriseView, 'do_entreprise_list_by_contact')
    def do_entreprise_list_by_contact(self, args={},
                                      operator = 'and', test='=', sortkey=None ):
        """Recherche dans entreprises, avec date de contact"""
        # (fonction ad-hoc car requete sur plusieurs tables)
        raise NotImplementedError
        # XXXXX fonction non achevee , non testee...
        cnx = self.GetDBConnexion()
        cursor = cnx.cursor()
        vals = dictfilter(args, self.dbfields)
        # DBSelect    
        what=['*']
        operator = ' ' + operator + ' '
        cond = ' E.entreprise_id = C.entreprise_id '
        if vals:     
            cond += ' where ' + operator.join( ['%s%s%%(%s)s' %(x,test,x) for x in vals.keys() if vals[x] != None ])
            cnuls = ' and '.join( ['%s is NULL' % x for x in vals.keys() if vals[x] is None ])
            if cnuls:
                cond = cond + ' and ' + cnuls
        else:
            cond += ''
        cursor.execute('select distinct' + ', '.join(what) + ' from entreprises E,  entreprise_contact C '+cond+orderby, vals )
        titles, res = [ x[0] for x in cursor.description ], cursor.fetchall()
        #
        R = []
        for r in res:
            d = {}
            for i in range(len(titles)):
                v = r[i]
                # value not formatted ! (see EditableTable.list())
                d[titles[i]] = v
            R.append(d)
        return R

    # --- Misc tools.... ------------------
    security.declareProtected(ScoEntrepriseView, 'str_abbrev')
    def str_abbrev(self, s, maxlen):
        "abreviation"
        if s == None:
            return '?'
        if len(s) < maxlen:
            return s
        return s[:maxlen-3] + '...'

    security.declareProtected(ScoEntrepriseView, 'setPageSizeCookie')
    def setPageSizeCookie(self, REQUEST=None):
        "set page size cookie"
        RESPONSE =  REQUEST.RESPONSE
        #
        if REQUEST.form.has_key('entreprise_page_size'):
            RESPONSE.setCookie( 'entreprise_page_size',
                                REQUEST.form['entreprise_page_size'],
                                path='/', expires='Wed, 31-Dec-2025 23:55:00 GMT' )
        RESPONSE.redirect( REQUEST.form['target_url'] )
        
    security.declareProtected(ScoEntrepriseView,'make_link_create_corr')
    def make_link_create_corr(self, entreprise_id):
        "yet another stupid code snippet"
        return '<a href="entreprise_correspondant_create?entreprise_id='+str(entreprise_id)+'">créer un nouveau correspondant</a>'
    

# --------------------------------------------------------------------
#
# Zope Product Administration
#
# --------------------------------------------------------------------
def manage_addZEntreprises(self, id= 'id_ZEntreprises', title='The Title for ZEntreprises Object', REQUEST=None):
   "Add a ZEntreprises instance to a folder."
   self._setObject(id, ZEntreprises(id, title))
   if REQUEST is not None:
        return self.manage_main(self, REQUEST)
        #return self.manage_editForm(self, REQUEST)

# The form used to get the instance id from the user.
#manage_addZAbsencesForm = DTMLFile('dtml/manage_addZAbsencesForm', globals())


    

