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

"""Site ScoDoc pour plusieurs departements: 
      gestion de l'installation et des creation de départements.

   Chaque departement est géré par un ZScolar sous ZScoDoc.
"""

import time, string, glob, re
import urllib, urllib2, cgi, xml
try: from cStringIO import StringIO
except: from StringIO import StringIO
from zipfile import ZipFile
import os.path, glob

import psycopg

# Zope modules:
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
from Globals import INSTANCE_HOME
from Acquisition import Implicit

try:
    import Products.ZPsycopgDA.DA as ZopeDA
except:
    import ZPsycopgDA.DA as ZopeDA # interp.py

from sco_utils import *
from notes_log import log
from ZScoUsers import pwdFascistCheck

class ZScoDoc(ObjectManager,
              PropertyManager,
              RoleManager,
              Item,
              Persistent,
              Implicit
              ):

    "ZScoDoc object"

    meta_type = 'ZScoDoc'
    security=ClassSecurityInfo()
    file_path = Globals.package_home(globals())

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


    def __init__(self, id, title):
        "Initialise a new instance of ZScoDoc"
        self.id = id
	self.title = title
        self.manage_addProperty('admin_password_initialized', '0', 'string')

    security.declareProtected(ScoView, 'ScoDocURL')
    def ScoDocURL(self):
        "base URL for this instance (top level for ScoDoc site)"
        return self.absolute_url()


    def _check_admin_perm(self, REQUEST):
        """Check if user has permission to add/delete departements
        """
        authuser = REQUEST.AUTHENTICATED_USER
        if authuser.has_role('manager') or authuser.has_permission(ScoSuperAdmin,self):
            return ''
        else:
            return """<h2>Vous n'avez pas le droit d'accéder à cette page</h2>"""

    
    def _check_users_folder(self, REQUEST=None):
        """Vérifie UserFolder et le crée s'il le faut
        """
        try:
            udb = self.UsersDB
            return '<!-- uf ok -->'
        except:
            e = self._check_admin_perm(REQUEST)
            if not e: # admin permissions:
                self.create_users_cnx(REQUEST)
                self.create_users_folder(REQUEST)
                return '<div class="head_message">Création du connecteur utilisateurs réussie</div>'
            else:
                return """<div class="head_message">Installation non terminée: connectez vous avec les droits d'administrateur</div>"""
            
    security.declareProtected('View','create_users_folder')
    def create_users_folder(self, REQUEST=None):
        """Create Zope user folder
        """
        e = self._check_admin_perm(REQUEST)
        if e:
            return e
        
        if REQUEST is None:
            REQUEST = {}
        
        REQUEST.form['pgauth_connection']='UsersDB'
        REQUEST.form['pgauth_table']='sco_users'
        REQUEST.form['pgauth_usernameColumn']='user_name'
        REQUEST.form['pgauth_passwordColumn']='passwd'
        REQUEST.form['pgauth_rolesColumn']='roles'

        add_method = self.manage_addProduct['OFSP'].manage_addexUserFolder
        log('create_users_folder: in %s' % self.id)
        return add_method(
            authId='pgAuthSource', 
            propId='nullPropSource', 
            memberId='nullMemberSource', 
            groupId='nullGroupSource', 
            cryptoId='MD51',
            # doAuth='1', doProp='1', doMember='1', doGroup='1', allDone='1',
            cookie_mode=2,
            session_length=500,
            not_session_length=0,
            REQUEST=REQUEST
            )

    security.declareProtected('View','create_users_cnx')
    def create_users_cnx(self, REQUEST=None):
        """Create Zope connector to UsersDB

        Note: la connexion est fixée (SCOUSERS) (base crée par l'installeur) !
        Les utilisateurs avancés pourront la changer ensuite.
        """
        oid = 'UsersDB'
        log('create_users_cnx: in %s' % self.id)
        da = ZopeDA.Connection(
            oid, 'Cnx bd utilisateurs',
            SCO_DEFAULT_SQL_USERS_CNX,
            False,
            check=1, tilevel=2, encoding='iso8859-15')
        self._setObject(oid, da)
        
    security.declareProtected('View', 'change_admin_user')
    def change_admin_user(self, password, REQUEST=None):
        """Change password of admin user"""
        # note: controle sur le role et non pas sur une permission
        # (non definies au top level)
        if not REQUEST.AUTHENTICATED_USER.has_role('Manager'):
            log('user %s is not Manager' % REQUEST.AUTHENTICATED_USER)
            log('roles=%s' % REQUEST.AUTHENTICATED_USER.getRolesInContext(self))
            raise AccessDenied("vous n'avez pas le droit d'effectuer cette opération")
        log("trying to change admin password")
        # 1-- check strong password
        if pwdFascistCheck(password) != None:
            log("refusing weak password")
            return REQUEST.RESPONSE.redirect("change_admin_user_form?message=Mot%20de%20passe%20trop%20simple,%20recommencez")
        # 2-- change password for admin user
        username = 'admin'
        acl_users = self.aq_parent.acl_users
        user=acl_users.getUser(username)
        r = acl_users._changeUser(username, password, password ,user.roles,user.domains)
        if not r:
            # OK, set property to indicate we changed the password
            log('admin password changed successfully')
            self.manage_changeProperties(admin_password_initialized='1')
        return r or REQUEST.RESPONSE.redirect("index_html")
    
    security.declareProtected('View', 'change_admin_user_form')
    def change_admin_user_form(self, message='', REQUEST=None):
        """Form allowing to change the ScoDoc admin password"""
        # note: controle sur le role et non pas sur une permission
        # (non definies au top level)
        if not REQUEST.AUTHENTICATED_USER.has_role('Manager'):
            raise AccessDenied("vous n'avez pas le droit d'effectuer cette opération")
        H = [ self._html_begin % 
              { 'page_title' : 'ScoDoc: changement mot de passe',
                'encoding' : SCO_ENCODING },
              self._top_level_css,
              """</head><body>"""
              ]
        if message:
            H.append('<div id="message">%s</div>' % message )
        H.append("""<h2>Changement du mot de passe administrateur (utilisateur admin)</h2>
        <p>
        <form action="change_admin_user" method="post"><table>
        <tr><td>Nouveau mot de passe:</td><td><input type="password" size="14" name="password"/></td></tr>
        <tr><td>Confirmation: </td><td><input type="password" size="14" name="password2" /></td></tr>
        </table>
        <input type="submit" value="Changer">
"""
        )
        H.append("""</body></html>""")
        return '\n'.join(H)
    
    security.declareProtected('View','list_depts')
    def list_depts(self, REQUEST=None):
        """List departments folders
        (returns a list of Zope folders containing a ZScolar instance)
        """
        folders = self.objectValues('Folder')
        # select folders with Scolarite object:
        r = []
        for folder in folders:
            try:
                s = folder.Scolarite
                r.append(folder)
            except:
                pass
        return r

    security.declareProtected('View','create_dept')
    def create_dept(self, REQUEST=None, DeptId='', pass2=False):
        """Creation (ajout) d'un site departement
        (instance ZScolar + dossier la contenant)
        """
        e = self._check_admin_perm(REQUEST)
        if e:
            return e
        
        if not DeptId:
            raise ValueError('nom de departement invalide')
        if not pass2:
           # 1- Creation de repertoire Dept
           add_method = self.manage_addProduct['OFSP'].manage_addFolder
           add_method( DeptId, title='Site dept. ' + DeptId )

        DeptFolder = self[DeptId]

        if not pass2:
            # 2- Creation du repertoire Fotos
            add_method = DeptFolder.manage_addProduct['OFSP'].manage_addFolder
            add_method( 'Fotos', title='Photos identites ' + DeptId )

        # 3- Creation instance ScoDoc
        add_method = DeptFolder.manage_addProduct['ScoDoc'].manage_addZScolarForm
        return add_method( DeptId, REQUEST=REQUEST )

    security.declareProtected('View','delete_dept')
    def delete_dept(self, REQUEST=None, DeptId=''):
        """Supprime un departement (de Zope seulement, ne touche pas la BD)
        """
        e = self._check_admin_perm(REQUEST)
        if e:
            return e
        
        if DeptId not in [ x.id for x in self.list_depts() ]:
            raise ValueError('nom de departement invalide')
        
        self.manage_delObjects(ids=[ DeptId ])
    
        return '<p>Département ' + DeptId + """ supprimé du serveur web (la base de données n'est pas affectée)!</p><p><a href="%s">Continuer</a></p>""" % REQUEST.URL1

    _top_level_css = """
    <style type="text/css">
div.maindiv {
   margin: 1em;
}
ul.main {
   list-style-type: square;
}

ul.main li {
   padding-bottom: 2ex;
}

#scodoc_attribution p {
   font-size:75%;
}

div.head_message {
   margin-top: 2px;
   margin-bottom: 0px;
   padding:  0.1em;
   margin-left: auto;
   margin-right: auto;
   background-color: #ffff73;
   -moz-border-radius: 8px;
   -khtml-border-radius: 8px;
   border-radius: 8px;
   font-family : arial, verdana, sans-serif ;
   font-weight: bold;
   width: 40%;
   text-align: center;
   
}

#scodoc_admin {
   background-color: #EEFFFF;
}

h4 {
   padding-top: 20px;
   padding-bottom: 0px;
}

#message {
   margin-top: 2px;
   margin-bottom: 0px;
   padding:  0.1em;
   margin-left: auto;
   margin-right: auto;
   background-color: #ffff73;
   -moz-border-radius: 8px;
   -khtml-border-radius: 8px;
   border-radius: 8px;
   font-family : arial, verdana, sans-serif ;
   font-weight: bold;
   width: 40%;
   text-align: center;
   color: red;
}

.help {
  font-style: italic; 
  color: red;
}

</style>"""

    _html_begin = """<?xml version="1.0" encoding="%(encoding)s"?>
<!DOCTYPE html PUBLIC "-//W3C//DTD XHTML 1.0 Transitional//EN" "http://www.w3.org/TR/xhtml1/DTD/xhtml1-transitional.dtd">
<html xmlns="http://www.w3.org/1999/xhtml">
<head>
<title>%(page_title)s</title>
<meta http-equiv="Content-Type" content="text/html; charset=%(encoding)s" />
<meta http-equiv="Content-Style-Type" content="text/css" />
<meta name="LANG" content="fr" />
<meta name="DESCRIPTION" content="ScoDoc" />"""

    security.declareProtected('View', 'index_html')
    def index_html(self, REQUEST=None, message=None):
        """Top level page for ScoDoc
        """
        authuser = REQUEST.AUTHENTICATED_USER
        deptList = self.list_depts()  
        isAdmin = not self._check_admin_perm(REQUEST)
        try:
            admin_password_initialized = self.admin_password_initialized
        except:
            admin_password_initialized = '0'
        if isAdmin and admin_password_initialized != '1':
            REQUEST.RESPONSE.redirect( "ScoDoc/change_admin_user_form?message=Le%20mot%20de%20passe%20administrateur%20doit%20etre%20change%20!")
        
        H = [ self._html_begin % 
              { 'page_title' : 'ScoDoc: bienvenue',
                'encoding' : SCO_ENCODING },
              self._top_level_css,
              """</head><body>""",
              self._check_users_folder(REQUEST=REQUEST), # ensure setup is done
              self.check_icons_folder(REQUEST=REQUEST) ]
        if message:
            H.append('<div id="message">%s</div>' % message )
        
        if isAdmin and not message:
            H.append('<div id="message">Attention: connecté comme administrateur</div>' )
            
        H.append("""
              <div class="maindiv">
        <h2>ScoDoc: gestion scolarité</h2>
        <p>
        Ce site est <font color="red"><b>réservé au personnel autorisé</b></font>.
        </p>                 
        """)
        
        
        if not deptList:
            H.append('<em>aucun département existant !</em>')
            # si pas de dept et pas admin, propose lien pour loger admin
            if not isAdmin:
                H.append("""<p><a href="/force_admin_authentication">Identifiez vous comme administrateur</a> (au début: nom 'admin', mot de passe 'scodoc')</p>""")
        else:
             H.append('<ul class="main">')
             for deptFolder in self.list_depts():
                 H.append('<li><a class="stdlink" href="%s/Scolarite">Scolarité département %s</a>'
                          % (deptFolder.absolute_url(), deptFolder.id))
                 # check if roles are initialized in this depts, and do it if necessary
                 if deptFolder.Scolarite.roles_initialized == '0':
                     if isAdmin:
                         deptFolder.Scolarite._setup_initial_roles_and_permissions()
                     else:
                         H.append(' (non initialisé, connectez vous comme admin)')
                 H.append('</li>')
             H.append('</ul>')


        if isAdmin:
            H.append('<p><a href="scodoc_admin">Administration de ScoDoc</a></p>')
        else:
            H.append('<p><a href="%s/force_admin_authentication">Se connecter comme administrateur</a></p>' % REQUEST.BASE0)

        H.append("""
<div id="scodoc_attribution">
<p><a href="https://www-rt.iutv.univ-paris13.fr/ScoDoc/">ScoDoc</a> est un logiciel libre de suivi de la scolarité des étudiants conçu par 
E. Viennet (Université Paris 13).</p>

<p>Ce logiciel est conçu pour un navigateur récent et <em>ne s'affichera pas correctement avec un logiciel
ancien</em>. Utilisez par exemple Firefox (libre et gratuit).</p>
<a href="http://www.mozilla-europe.org/fr/products/firefox/">%s</a>
</div>
</div>""" % self.icons.firefox_fr.tag(border='0') )

        H.append("""</body></html>""")
        return '\n'.join(H)


    # sendEmail is not used through the web
    def sendEmail(self,msg):
        # sends an email to the address using the mailhost, if there is one
        if not self.mail_host:
            log('warning: sendEmail: no mail_host found !')
            return
        # a failed notification shouldn't cause a Zope error on a site.
        try:
            mhost=getattr(self,self.mail_host)
            mhost.send(msg.as_string())
            log('sendEmail')
        except:
            pass
    
#     security.declareProtected('View', 'standard_error_message')
#     #standard_error_message = DTMLFile('dtml/standard_error_message', globals())
#     def standard_error_message(self, **kv): 
#         "Recuperation des exceptions Zope"
#         #error_value=None, error_type=None,
#         #error_traceback=None, error_tb=None, error_message=None,
#         #error_log_url=None, **kv):
        
#         # Authentication uses exceptions, pass them up
#         if kv['error_type'] == 'LoginRequired':
#             raise 'LoginRequired', ''  # copied from exuserFolder (beurk)
#         log('exception caught !')
#         log('kv=%s'%kv)
#         if kv['error_type'] == 'ScoGenError':
#             return '<p>' + kv.get('error_value','') + '</p>'
#         elif kv['error_type'] == 'ScoValueError':
#             # XXX todo
#        return 'exception !'

    security.declareProtected('View', 'scodoc_admin')
    def scodoc_admin(self, REQUEST=None):
        """Page Operations d'administration
        """
        e = self._check_admin_perm(REQUEST)
        if e:
            return e
        
        H = [ self._html_begin % 
              { 'page_title' : 'ScoDoc: bienvenue',
                'encoding' : SCO_ENCODING },
              self._top_level_css,
              """</head>
              <body>
              
<h3>Administration ScoDoc</h3>

<p><a href="change_admin_user_form">changer le mot de passe super-administrateur</a></p>
<p><a href="%s">retour à la page d'accueil</a></p>

<h4>Création d'un département</h4>
<p class="help">Le département doit avoir été créé au préalable sur le serveur en utilisant le script
<tt>create_dept.sh</tt> (à lancer comme <tt>root</tt> dans le répertoire <tt>config</tt> de ScoDoc).
</p>""" % self.absolute_url()]

        deptList = [ x.id for x in self.list_depts() ] # definis dans Zope
        deptIds = Set(self._list_depts_ids()) # definis sur le filesystem
        existingDepts = Set(deptList)
        addableDepts = deptIds - existingDepts
        
        if not addableDepts:
            # aucun departement defini: aide utilisateur
            H.append("<p>Aucun département à ajouter !</p>")
        else:
            H.append("""<form action="create_dept"><select name="DeptId"/>""")
            for deptId in addableDepts:
                H.append("""<option value="%s">%s</option>""" % (deptId,deptId))
            H.append("""</select>
            <input type="submit" value="Créer département">
            </form>""" )
            
        if deptList:
            H.append("""
<h4>Suppression d'un département</h4>
<p>Ceci permet de supprimer le site web associé à un département, mais n'affecte pas la base de données 
(le site peut donc être recréé sans perte de données).
</p>
<form action="delete_dept">
<select name="DeptId">
              """)
            for deptFolder in self.list_depts():
                H.append('<option value="%s">%s</option>'
                         % (deptFolder.id, deptFolder.id) )
            H.append("""</select>
<input type="submit" value="Supprimer département">

</form>""")

        H.append("""</body></html>""")
        return '\n'.join(H)

    def _list_depts_ids(self):
        """Liste de id de departements definis par create_dept.sh
        (fichiers depts/*.cfg)
        """
        filenames = glob.glob( self.file_path + '/config/depts/*.cfg')
        ids = [ os.path.split(os.path.splitext(f)[0])[1] for f in filenames ]
        return ids
    

    security.declareProtected('View', 'check_icons_folder')
    def check_icons_folder(self,REQUEST=None):
        """Vérifie icons folder et le crée s'il le faut
        """
        try:
            icons = self.icons
            return '<!-- icons ok -->'
        except:
            e = self._check_admin_perm(REQUEST)
            if not e: # admin permissions:
                self.build_icons_folder(REQUEST)
                return '<div class="head_message">Création du dossier icons réussie</div>'
            else:
                return """<div class="head_message">Installation non terminée: connectez vous avec les droits d'administrateur</div>"""
    
    security.declareProtected('View', 'build_icons_folder')
    def build_icons_folder(self,REQUEST=None):
        """Build folder with Zope images
        """
        e = self._check_admin_perm(REQUEST)
        if e:
            return e
        path = self.file_path + '/icons'
        id = 'icons'
        try:
            o = self[id]
            exists = True
        except:
            exists = False
        # If folder exists, destroy it !
        if exists:
            log('build_image_folder: destroying existing folder !')
            self.manage_delObjects(ids=[ id ])
        # Create Zope folder
        log('build_image_folder: building new %s folder' % id )
        self.manage_addProduct['OFSP'].manage_addFolder(id, title='ScoDoc icons')
        folder = self[id]
        # Create Zope images instances for each file in .../icons/*        
        path = self.file_path + '/icons/'
        add_method = folder.manage_addProduct['OFSP'].manage_addImage
        for filename in os.listdir(path):
            if filename != '.svn':
                iid = os.path.splitext(filename)[0]
                log('adding image %s as %s' % (filename,iid))
                add_method( iid, open(path+'/'+filename) )
        
        return 'ok'




def manage_addZScoDoc(self, id= 'ScoDoc',
                      title='Site ScoDoc',
                      REQUEST=None):
   "Add a ZScoDoc instance to a folder."
   log('==============   creating a new ScoDoc instance =============')
   zscodoc = ZScoDoc(id, title) # ne cree (presque rien), tout se passe lors du 1er accès
   self._setObject(id,zscodoc)
   if REQUEST is not None:
       REQUEST.RESPONSE.redirect('%s/manage_workspace' % REQUEST.URL1)
   return id
