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

""" Gestion des relations avec les entreprises
"""
import urllib

from sco_zope import *

# ---------------

from notesdb import *
from notes_log import log
from scolog import logdb
from sco_utils import *
import html_sidebar

from TrivialFormulator import TrivialFormulator, TF
import scolars
import string, re
import time, calendar 

def _format_nom(nom):
    "formatte nom (filtre en entree db) d'une entreprise"
    if not nom:
        return nom
    nom = nom.decode(SCO_ENCODING)
    return (nom[0].upper() + nom[1:]).encode(SCO_ENCODING)


class EntreprisesEditor(EditableTable):
    def delete(self, cnx, oid):
        "delete correspondants and contacts, then self"
        # first, delete all correspondants and contacts
        cursor = cnx.cursor(cursor_factory=ScoDocCursor)
        cursor.execute('delete from entreprise_contact where entreprise_id=%(entreprise_id)s',
                       { 'entreprise_id' : oid } )    
        cursor.execute('delete from entreprise_correspondant where entreprise_id=%(entreprise_id)s',
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
                    r['date'] = max( [ x['date'] or datetime.date.min for x in c ] )
                else:
                    r['date'] = datetime.date.min
            # sort
            R.sort( lambda r1, r2: cmp(r2['date'], r1['date']) )
            for r in R:
                r['date'] = DateISOtoDMY(r['date'])
        return R

    def list_by_etud(self, cnx, args={},
                     sort_on_contact=False, disable_formatting=False):
        "cherche rentreprise ayant eu contact avec etudiant"
        cursor = cnx.cursor(cursor_factory=ScoDocCursor)
        cursor.execute('select E.*, I.nom as etud_nom, I.prenom as etud_prenom, C.date from entreprises E, entreprise_contact C, identite I where C.entreprise_id = E.entreprise_id and C.etudid = I.etudid and I.nom ~* %(etud_nom)s ORDER BY E.nom',
                       args )
        titles, res = [ x[0] for x in cursor.description ], cursor.dictfetchall()
        R = []
        for r in res:
            r['etud_prenom'] = r['etud_prenom'] or ''
            d = {}
            for key in r:
                v = r[key]
                # format value 
                if not disable_formatting and self.output_formators.has_key(key):
                    v = self.output_formators[key](v)
                d[key] = v
            R.append(d)
        # sort
        if sort_on_contact:
            R.sort( lambda r1, r2: cmp(r2['date'] or datetime.date.min, r1['date'] or datetime.date.min) )
        for r in R:
            r['date'] = DateISOtoDMY(r['date'] or datetime.date.min)
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
    def entreprise_header(self,REQUEST=None,page_title=''):
        "common header for all Entreprises pages"
        authuser = REQUEST.AUTHENTICATED_USER
        # _read_only is used to modify pages properties (links, buttons)
        # Python methods (do_xxx in this class) are also protected individualy)
        if authuser.has_permission(ScoEntrepriseChange,self):
            REQUEST.set( '_read_only', False )
        else:
            REQUEST.set( '_read_only', True )
        return self.sco_header(REQUEST, container=self, page_title=page_title)

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
            E = context.do_entreprise_list( args={ 'entreprise_id' : entreprise_id } )
            if E:
                E = E[0]
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
        H.append("""<br/><br/>%s""" % icontag('entreprise_side_img'))
        if REQUEST['_read_only']:
            H.append("""<br/><em>(Lecture seule)</em>""")
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
    
    # Acces en modification:
    security.declareProtected(ScoEntrepriseChange, 'entreprise_contact_create')
    entreprise_contact_create = DTMLFile('dtml/entreprises/entreprise_contact_create',globals())
    security.declareProtected(ScoEntrepriseChange, 'entreprise_contact_delete')
    entreprise_contact_delete = DTMLFile('dtml/entreprises/entreprise_contact_delete',globals())
    security.declareProtected(ScoEntrepriseChange, 'entreprise_correspondant_create')
    entreprise_correspondant_create = DTMLFile('dtml/entreprises/entreprise_correspondant_create',globals())
    security.declareProtected(ScoEntrepriseChange, 'entreprise_correspondant_delete')
    entreprise_correspondant_delete = DTMLFile('dtml/entreprises/entreprise_correspondant_delete',globals())
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
        etudiant = etudiant.strip().translate(None, "'()") # suppress parens and quote from name
        if not etudiant:
            return 1, None
        cnx = self.GetDBConnexion()
        cursor = cnx.cursor(cursor_factory=ScoDocCursor)
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
                e.append( '<li>%s %s (code %s)</li>' % (strupper(x[1]), x[2] or '', x[0].strip()) )
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
        cursor = cnx.cursor(cursor_factory=ScoDocCursor)
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

    # -------- Formulaires: traductions du DTML
    security.declareProtected(ScoEntrepriseChange, 'entreprise_create')
    def entreprise_create(self, REQUEST=None):
        """Form. création entreprise"""
        context = self
        H = [ self.entreprise_header(REQUEST, page_title="Création d'une entreprise"),
              """<h2 class="entreprise_new">Création d'une entreprise</h2>""" ]
        tf = TrivialFormulator(REQUEST.URL0, REQUEST.form, (
            ('nom',       { 'size' : 25, 'title' : 'Nom de l\'entreprise' }),
            ('adresse',   { 'size' : 30, 'title' : 'Adresse', 'explanation' : '(numéro, rue)' }),
            ('codepostal',   { 'size' : 8, 'title' : 'Code Postal', }),
            ('ville',     { 'size' : 30, 'title' : 'Ville' }),
            ('pays',      { 'size' : 30, 'title' : 'Pays', 'default' : 'France' }),
            ('localisation', { 'input_type' : 'menu', 
                               'labels' : ['Ile de France', 'Province', 'Etranger'],
                               'allowed_values' : ['IDF', 'Province', 'Etranger'] }),
            
            ('secteur',     { 'size' : 30, 'title' : 'Secteur d\'activités' }),
            ('privee',   { 'input_type' : 'menu', 'title' : 'Statut',
                           'labels' : ['Entreprise privee', 'Entreprise Publique', 'Association' ],
                           'allowed_values' : ['privee', 'publique', 'association'] }),
    
            ('plus10salaries',  { 'title' : 'Masse salariale', 'type' : 'integer','input_type' : 'menu',
                                  'labels' : ['10 salariés ou plus', 'Moins de 10 salariés', 'Inconnue' ],
                                  'allowed_values' : [ 1, 0, -1 ] }),
            ('qualite_relation', { 'title' : 'Qualité relation IUT/Entreprise',
                                   'input_type' : 'menu', 'default' : '-1',
                                   'labels' : ['Très bonne', 'Bonne','Moyenne', 'Mauvaise', 'Inconnue' ],                       
                                   'allowed_values' : [ '100', '75', '50', '25', '-1' ] }),
            ('contact_origine',     { 'size' : 30, 'title' : 'Origine du contact' }),
            ('note',     { 'input_type' : 'textarea', 'rows' : 3, 'cols': 40, 'title' : 'Note' }),
            ),
                               cancelbutton='Annuler',
                               submitlabel = 'Ajouter cette entreprise', readonly = REQUEST['_read_only']
                               )
        if tf[0] == 0:
            return '\n'.join(H) + tf[1] + context.entreprise_footer(REQUEST)
        elif tf[0] == -1:
            return REQUEST.RESPONSE.redirect( REQUEST.URL1 )
        else:
            self.do_entreprise_create( tf[2] )
            return REQUEST.RESPONSE.redirect( REQUEST.URL1 )

    security.declareProtected(ScoEntrepriseView, 'entreprise_edit')
    def entreprise_edit(self, entreprise_id,  REQUEST=None, start=1):
        """Form. edit entreprise"""
        context = self
        authuser = REQUEST.AUTHENTICATED_USER
        readonly = not authuser.has_permission(ScoEntrepriseChange,self)
        F = self.do_entreprise_list( args={ 'entreprise_id' : entreprise_id } )[0]
        H = [ self.entreprise_header(REQUEST, page_title="Entreprise"),
              """<h2 class="entreprise">%(nom)s</h2>""" % F ]
        tf = TrivialFormulator( REQUEST.URL0, REQUEST.form, (
            ('entreprise_id', { 'default' : entreprise_id, 'input_type' : 'hidden' }),
            ('start', { 'default' : 1, 'input_type' : 'hidden' }),

            ('date_creation', { 'default' : time.strftime( '%Y-%m-%d' ), 'input_type' : 'hidden' }),

            ('nom',       { 'size' : 25, 'title' : 'Nom de l\'entreprise' }),
            ('adresse',   { 'size' : 30, 'title' : 'Adresse', 'explanation' : '(numéro, rue)' }),
            ('codepostal',   { 'size' : 8, 'title' : 'Code Postal', }),
            ('ville',     { 'size' : 30, 'title' : 'Ville' }),
            ('pays',      { 'size' : 30, 'title' : 'Pays', 'default' : 'France' }),
            ('localisation', { 'input_type' : 'menu', 
                               'labels' : ['Ile de France', 'Province', 'Etranger'],
                               'allowed_values' : ['IDF', 'Province', 'Etranger'] }),

            ('secteur',     { 'size' : 30, 'title' : 'Secteur d\'activités' }),
            ('privee',   { 'input_type' : 'menu', 'title' : 'Statut',
                           'labels' : ['Entreprise privee', 'Entreprise Publique', 'Association' ],
                           'allowed_values' : ['privee', 'publique', 'association'] }),

            ('plus10salaries',  { 'title' : 'Masse salariale', 'input_type' : 'menu',
                                  'labels' : ['10 salariés ou plus', 'Moins de 10 salariés', 'Inconnue' ],
                                  'allowed_values' : [ '1', '0', '-1' ] }),
            ('qualite_relation', { 'title' : 'Qualité relation IUT/Entreprise',
                                   'input_type' : 'menu', 
                                   'labels' : ['Très bonne', 'Bonne','Moyenne', 'Mauvaise', 'Inconnue' ],                       
                                   'allowed_values' : [ '100', '75', '50', '25', '-1' ] }),
            ('contact_origine',     { 'size' : 30, 'title' : 'Origine du contact' }),
            ('note',     { 'input_type' : 'textarea', 'rows' : 3, 'cols': 40, 'title' : 'Note' }),                ),
            cancelbutton = 'Annuler',
            initvalues = F,
            submitlabel = 'Modifier les valeurs', 
            readonly = readonly )
    
        if tf[0] == 0:
            H.append(tf[1])
            Cl = self.do_entreprise_correspondant_list(
                args={ 'entreprise_id' : F['entreprise_id'] })
            Cts = self.do_entreprise_contact_list( args={ 'entreprise_id' : F['entreprise_id'] })
            if not readonly:
                H.append("""<p>%s&nbsp;<a class="entreprise_delete" href="entreprise_delete?entreprise_id=%s">Supprimer cette entreprise</a> </p>""" % (icontag('delete_img', title='delete', border='0'), F['entreprise_id']))
            if len(Cl):
                H.append("""<h3>%d correspondants dans l'entreprise %s (<a href="entreprise_correspondant_list?entreprise_id=%s">liste complète</a>) :</h3>
<ul>""" % (len(Cl), F['nom'], F['entreprise_id']))
                for c in Cl:
                    H.append("""<li><a href="entreprise_correspondant_edit?entreprise_corresp_id=%s">""" % c['entreprise_corresp_id'])
                    if c['nom']:
                        nom = c['nom'].decode(SCO_ENCODING).lower().capitalize().encode(SCO_ENCODING)
                    else:
                        nom = ''
                    if c['prenom']:
                        prenom = c['prenom'].decode(SCO_ENCODING).lower().capitalize().encode(SCO_ENCODING)
                    else:
                        prenom = ''
                    H.append("""%s %s</a>&nbsp;(%s)</li>""" % (nom,prenom,c['fonction']))
                H.append('</ul>')
            if len(Cts):
                H.append("""<h3>%d contacts avec l'entreprise %s (<a href="entreprise_contact_list?entreprise_id=%s">liste complète</a>) :</h3><ul>""" % (len(Cts),F['nom'],F['entreprise_id']))
                for c in Cts:
                    H.append("""<li><a href="entreprise_contact_edit?entreprise_contact_id=%s">%s</a>&nbsp;&nbsp;&nbsp;""" % (c['entreprise_contact_id'],c['date']))
                    if c['type_contact']:
                        H.append(c['type_contact'])
                    if c['etudid']:
                        etud = self.getEtudInfo(etudid=c['etudid'], filled=1)
                        if etud:
                            etud = etud[0]
                            H.append("""<a href="%s/ficheEtud?etudid=%s">%s</a>"""%(self.ScoURL(), c['etudid'], etud['nomprenom']))
                    if c['description']:
                        H.append('(%s)' % c['description'])
                    H.append('</li>')
                H.append('</ul>')                
            return '\n'.join(H) + context.entreprise_footer(REQUEST)
        elif tf[0] == -1:
            return REQUEST.RESPONSE.redirect(REQUEST.URL1+'?start='+start)
        else:
            self.do_entreprise_edit(tf[2])
            return REQUEST.RESPONSE.redirect(REQUEST.URL1+'?start='+start)
    
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


    

