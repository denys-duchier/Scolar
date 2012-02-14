# -*- mode: python -*-
# -*- coding: iso8859-15 -*-

##############################################################################
#
# Gestion scolarite IUT
# 
# Copyright (c) 2001 - 2011 Emmanuel Viennet.  All rights reserved.
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

import time, string, glob, re, inspect
import urllib, urllib2, cgi, xml
try: from cStringIO import StringIO
except: from StringIO import StringIO
from zipfile import ZipFile
import os.path, glob

import psycopg

from email.MIMEMultipart import MIMEMultipart
from email.MIMEText import MIMEText
from email.MIMEBase import MIMEBase
from email.Header import Header
from email import Encoders

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
    def ScoDocURL(self): # XXX unused
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

    def _fix_users_folder(self):
        """removes docLogin and docLogout dtml methods from exUserFolder, so that we use ours.
        (called each time be index_html, to fix old ScoDoc installations.)
        """
        try:
            self.acl_users.manage_delObjects(ids=[ 'docLogin', 'docLogout' ])
        except: 
            pass
        # add missing getAuthFailedMessage (bug in exUserFolder ?)
        try:
            x = self.getAuthFailedMessage
        except:
            log('adding getAuthFailedMessage to Zope install')
            parent = self.aq_parent
            from OFS.DTMLMethod import addDTMLMethod
            addDTMLMethod(parent, 'getAuthFailedMessage', file='Identification')

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
    def delete_dept(self, REQUEST=None, DeptId='', force=False):
        """Supprime un departement (de Zope seulement, ne touche pas la BD)
        """
        e = self._check_admin_perm(REQUEST)
        if e:
            return e
        
        if not force and DeptId not in [ x.id for x in self.list_depts() ]:
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
        self._fix_users_folder() # fix our exUserFolder
        isAdmin = not self._check_admin_perm(REQUEST)
        try:
            admin_password_initialized = self.admin_password_initialized
        except:
            admin_password_initialized = '0'
        if isAdmin and admin_password_initialized != '1':
            REQUEST.RESPONSE.redirect( "ScoDoc/change_admin_user_form?message=Le%20mot%20de%20passe%20administrateur%20doit%20etre%20change%20!")

        # Si l'URL indique que l'on est dans un folder, affiche page login du departement
        try:
            deptfoldername = REQUEST.URL0.split('ScoDoc')[1].split('/')[1]
            if deptfoldername in [ x.id for x in self.list_depts() ]:
                return self.index_dept(deptfoldername=deptfoldername, REQUEST=REQUEST)
        except:
            pass
        
        H = [ self._html_begin % 
              { 'page_title' : 'ScoDoc: bienvenue',
                'encoding' : SCO_ENCODING },
              self._top_level_css,
              """</head><body>""",
              CUSTOM_HTML_HEADER_CNX,
              self._check_users_folder(REQUEST=REQUEST), # ensure setup is done
              self._check_icons_folder(REQUEST=REQUEST) ]
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
             if isAdmin:
                 dest_folder = '/Scolarite'
             else:
                 dest_folder = ''
             for deptFolder in self.list_depts():
                 H.append('<li><a class="stdlink" href="%s%s">Scolarité département %s</a>'
                          % (deptFolder.absolute_url(), dest_folder, deptFolder.id))
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

        try:
            img = self.icons.firefox_fr.tag(border='0')
        except:
            img = '' # icons folder not yet available
        H.append("""
<div id="scodoc_attribution">
<p><a href="%s">ScoDoc</a> est un logiciel libre de suivi de la scolarité des étudiants conçu par 
E. Viennet (Université Paris 13).</p>

<p>Ce logiciel est conçu pour un navigateur récent et <em>ne s'affichera pas correctement avec un logiciel
ancien</em>. Utilisez par exemple Firefox (libre et gratuit).</p>
<a href="http://www.mozilla-europe.org/fr/products/firefox/">%s</a>
</div>
</div>""" % (SCO_WEBSITE,img) )

        H.append("""</body></html>""")
        return '\n'.join(H)

    security.declareProtected('View', 'index_dept')
    def index_dept(self, deptfoldername='', REQUEST=None):
        """Page d'accueil departement"""
        authuser = REQUEST.AUTHENTICATED_USER
        try:
            dept = getattr(self, deptfoldername)
            if authuser.has_permission(ScoView,dept):
                return REQUEST.RESPONSE.redirect('ScoDoc/%s/Scolarite'%deptfoldername)
        except:
            log('*** problem in index_dept (%s) user=%s' % (deptfoldername,str(authuser)))
        
        H = [ self.standard_html_header(self),
              """<div style="margin: 1em;">

<h2>Scolarité du département %s</h2>
<p>

Ce site est 
<font color="#FF0000"><b>réservé au personnel du département</b></font>.
</p>


<!-- login -->
<form action="doLogin" method="post">
   <input type="hidden" name="destination" value="Scolarite">
<p>
 <table border="0" cellpadding="3">
    <tr>
      <td><b>Nom:</b></td>
      <td><input type="text" name="__ac_name" size="20"></td>
    </tr><tr>
      <td><b>Mot de passe:</b></td>
      <td><input type="password" name="__ac_password" size="20"></td>
      <td><input type="submit" value="OK "></td>
    </tr>
 </table>
</form>


<p>Pour quitter, <a href="acl_users/logout">logout</a>

<p>Ce site est conçu pour un navigateur récent et <em>ne s'affichera pas correctement avec un logiciel
ancien</em>. Utilisez par exemple Firefox (gratuit et respectueux des normes).</p>
<a href="http://www.mozilla-europe.org/fr/products/firefox/">%s</a>

</div>
""" % (deptfoldername, self.icons.firefox_fr.tag(border='0')),
              self.standard_html_footer(self)]
        return '\n'.join(H)

    security.declareProtected('View', 'doLogin')
    def doLogin(self, REQUEST=None, destination=None):
        "redirect to destination after login"
        if destination:
            return REQUEST.RESPONSE.redirect( destination )

    security.declareProtected('View', 'docLogin')
    docLogin = DTMLFile('dtml/docLogin', globals())
    security.declareProtected('View', 'docLogout')
    docLogout = DTMLFile('dtml/docLogout', globals())
    
    security.declareProtected('View', 'query_string_to_form_inputs')
    def query_string_to_form_inputs(self, query_string=''):
        """Return html snippet representing the query string as POST form hidden inputs.
        This is useful in conjonction with exUserfolder to correctly redirect the response
        after authentication.
        """
        H = []
        for a in query_string.split('&'):
            if a:
                nv = a.split('=')
                if len(nv) == 2:
                    name, value = nv
                    H.append( '<input type="hidden" name="' + name 
                              +'" value="' + value + '"/>' )

        return '<!-- query string -->\n' +  '\n'.join(H)
    
    security.declareProtected('View', 'standard_html_header')
    def standard_html_header(self, REQUEST=None):
        """Standard HTML header for pages outside depts"""
        # not used in ZScolar, see sco_header
        return """<!DOCTYPE HTML PUBLIC "-//W3C//DTD HTML 4.01//EN" "http://www.w3.org/TR/html4/strict.dtd">
<html><head>
<title>ScoDoc: accueil</title>
<META http-equiv="Content-Type" content="text/html; charset=%s">
<META http-equiv="Content-Style-Type" content="text/css">
<META name="LANG" content="fr">
<META name="DESCRIPTION" content="ScoDoc: gestion scolarite">

<link HREF="/ScoDoc/static/css/scodoc.css" rel="stylesheet" type="text/css"/>

</head><body>%s""" % (SCO_ENCODING, CUSTOM_HTML_HEADER_CNX)

    security.declareProtected('View', 'standard_html_footer')
    def standard_html_footer(self, REQUEST=None):
        return """<p class="footer">
Problème de connexion (identifiant, mot de passe): <em>contacter votre responsable ou chef de département</em>.<br/>
Probl&egrave;mes et suggestions sur le logiciel: <a href="mailto:emmanuel.viennet@univ-paris13.fr">emmanuel.viennet@univ-paris13.fr</a>
ou <a href="mailto:%s">%s</a>
</p>
</body></html>""" % (SCO_USERS_LIST, SCO_USERS_LIST)

    # sendEmail is not used through the web
    def sendEmail(self,msg):
        # sends an email to the address using the mailhost, if there is one
        try:
            mail_host = self.MailHost
        except:
            log('warning: sendEmail: no MailHost found !')
            return
        # a failed notification shouldn't cause a Zope error on a site.
        try:
            mail_host.send(msg.as_string())
            log('sendEmail: ok')
        except:
            log('sendEmail: exception while sending message')
            pass

    def sendEmailFromException(self,msg):
        # Send email by hand, as it seems to be not possible to use Zope Mail Host
        # from an exception handler (see https://bugs.launchpad.net/zope2/+bug/246748)
        log('sendEmailFromException')
        try:
            p = os.popen("sendmail -t", 'w') # old brute force method
            p.write(msg.as_string())
            exitcode = p.close()
            if exitcode:
                log('sendmail exit code: %s' % exitcode)
        except:
            log('an exception occurred sending mail')

    security.declareProtected('View', 'standard_error_message')
    def standard_error_message(self, error_value=None, error_message=None, error_type=None,
                               error_traceback=None, error_tb=None, **kv): 
        "Recuperation des exceptions Zope"
        sco_dev_mail = SCO_DEV_MAIL
        
        # neat (or should I say dirty ?) hack to get REQUEST
        # in fact, our caller (probably SimpleItem.py) has the REQUEST variable
        # that we'd like to use for our logs, but does not pass it as an argument.
        try:
            frame = inspect.currentframe()
            REQUEST = frame.f_back.f_locals['REQUEST']
        except:
            REQUEST = {}
        
        # Authentication uses exceptions, pass them up
        HTTP_X_FORWARDED_FOR = REQUEST.get('HTTP_X_FORWARDED_FOR', '')
        if error_type == 'LoginRequired':
            #    raise 'LoginRequired', ''  # copied from exuserFolder (beurk, old style exception...)        
            log('LoginRequired from %s' % HTTP_X_FORWARDED_FOR)
            self.login_page = error_value
            return error_value
        elif error_type == 'Unauthorized':
            log('Unauthorized from %s' % HTTP_X_FORWARDED_FOR)
            return self.acl_users.docLogin(self, REQUEST=REQUEST)
        
        log('exception caught: %s' % error_type)
        if error_type == 'ScoGenError':
            return '<p>' + str(error_value) + '</p>'
        elif error_type == 'ScoValueError':
            # Not a bug, presents a gentle message to the user:
            H = [ self.standard_html_header(self),
                  """<h2>Erreur !</h2><p>%s</p>""" % error_value ]
            if error_value.dest_url:
                H.append('<p><a href="%s">Continuer</a></p>' % error_value.dest_url )
            H.append(self.standard_html_footer(self))
            return '\n'.join(H)
        else: # Other exceptions, try carefully to build an error page...
            #log('exc A')
            H = []
            try:
                H.append( self.standard_html_header(self) )
            except:
                pass
            if error_message:
                H.append( str(error_message) )
            else:
                H.append("""<table border="0" width="100%%"><tr valign="top">
<td width="10%%" align="center"></td>
<td width="90%%"><h2>Erreur !</h2>
  <p>Une erreur est survenue</p>
  <p>
  <strong>Error Type: %(error_type)s</strong><br>
  <strong>Error Value: %(error_value)s</strong><br> 
  </p>
  <hr noshade>
  <p>L'URL est peut-etre incorrecte ?</p>

  <p>Si l'erreur persiste, contactez Emmanuel Viennet:
   <a href="mailto:%(sco_dev_mail)s">%(sco_dev_mail)s</a>
    en copiant ce message d'erreur et le contenu du cadre bleu ci-dessous si possible.
  </p>
</td></tr>
</table>        """ % vars() )
                # display error traceback (? may open a security risk via xss attack ?)
                #log('exc B')
                txt_html = self._report_request(REQUEST, format='html')
                H.append("""<h4>Zope Traceback (à envoyer par mail à <a href="mailto:%(sco_dev_mail)s">%(sco_dev_mail)s</a>)</h4><div style="background-color: rgb(153,153,204); border: 1px;">
%(error_tb)s
<p><b>Informations:</b><br/>
%(txt_html)s
</p>
</div>

<p>Merci de votre patience !</p>
""" % vars() )
                try:
                    H.append( self.standard_html_footer(self) )
                except:
                    log('no footer found for error page')
                    pass
        # --- Mail:
        error_traceback_txt = scodoc_html2txt(error_tb)
        txt = """
ErrorType: %(error_type)s

%(error_traceback_txt)s
""" % vars()

        self.send_debug_alert(txt, REQUEST=REQUEST)
        # ---
        log('done processing exception')
        log( '\n page=\n' + '\n'.join(H) )
        return '\n'.join(H)

    def _report_request(self, REQUEST, format='txt'):
        """string describing current request for bug reports"""
        AUTHENTICATED_USER = REQUEST.get('AUTHENTICATED_USER', '')
        dt = time.asctime()
        URL = REQUEST.get('URL', '')
        QUERY_STRING = REQUEST.get('QUERY_STRING', '')
        if QUERY_STRING:
            QUERY_STRING = '?' + QUERY_STRING
        REFERER = REQUEST.get('HTTP_REFERER', '')
        form = REQUEST.get('form', '')
        HTTP_X_FORWARDED_FOR = REQUEST.get('HTTP_X_FORWARDED_FOR', '')
        HTTP_USER_AGENT = REQUEST.get('HTTP_USER_AGENT', '')
        svn_version = get_svn_version(self.file_path)

        txt = """
User:    %(AUTHENTICATED_USER)s
Date:    %(dt)s
URL:     %(URL)s%(QUERY_STRING)s

REFERER: %(REFERER)s
Form: %(form)s
Origin: %(HTTP_X_FORWARDED_FOR)s
Agent: %(HTTP_USER_AGENT)s

subversion: %(svn_version)s
""" % vars()
        if format == 'html':
            txt = txt.replace('\n', '<br/>')
        return txt

    security.declareProtected(ScoSuperAdmin, 'send_debug_alert')# not called through the web 
    def send_debug_alert(self, txt, REQUEST=None):
        """Send an alert email (bug report) to ScoDoc developpers"""
        if not SCO_DEV_MAIL:
            log('send_debug_alert: email disabled')
            return
        if REQUEST:
            txt = self._report_request(REQUEST) + txt            
            URL = REQUEST.get('URL', '')
        else:
            URL = 'send_debug_alert'
        msg = MIMEMultipart()
        subj = Header( '[scodoc] exc %s' % URL,  SCO_ENCODING )
        msg['Subject'] = subj
        recipients = [ SCO_DEV_MAIL ]
        msg['To'] = ' ,'.join(recipients)
        msg['From'] = 'scodoc-alert'
        msg.epilogue = ''
        msg.attach(MIMEText( txt, 'plain', SCO_ENCODING ))
        self.sendEmailFromException(msg)
        log('Sent mail alert:\n' + txt)
    
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

        # Autres opérations
        H.append("""<h4>Autres opérations</h4>
<ul>
<li><a href="build_icons_folder">Reconstruire les icônes</a></li>
</ul>
""")


        H.append("""</body></html>""")
        return '\n'.join(H)

    def _list_depts_ids(self):
        """Liste de id de departements definis par create_dept.sh
        (fichiers depts/*.cfg)
        """
        filenames = glob.glob( self.file_path + '/config/depts/*.cfg')
        ids = [ os.path.split(os.path.splitext(f)[0])[1] for f in filenames ]
        return ids
    
    def _check_icons_folder(self,REQUEST=None): # not published
        """Vérifie icons folder Zope et le crée s'il le faut
        XXX deprecated: on utilisera maintenant les images statiques via sco_utils.icontag()
        """
        try:
            icons = self.icons
            plus = self.icons.plus_img # upgrade jul 2008
            arrow_up = self.icons.arrow_up # nov 2009
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
        return self.do_build_icons_folder(REQUEST=REQUEST)
    
    security.declareProtected('View', 'do_build_icons_folder')
    def do_build_icons_folder(self,REQUEST=None): # not published
        # Build folder with Zope images
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
        # Create Zope images instances for each file in .../static/icons/*
        path = self.file_path + '/static/icons/'
        add_method = folder.manage_addProduct['OFSP'].manage_addImage
        for filename in os.listdir(path):
            if filename != '.svn':
                iid = os.path.splitext(filename)[0]
                log('adding image %s as %s' % (filename,iid))
                add_method( iid, open(path+'/'+filename) )
        
        return 'ok'

    security.declareProtected('View', 'http_expiration_date')
    def http_expiration_date(self):
        "http expiration date for cachable elements (css, ...)"
        d = datetime.timedelta(minutes=10)
        return (datetime.datetime.utcnow() + d).strftime("%a, %d %b %Y %H:%M:%S GMT")

    security.declareProtected('View', 'get_etud_dept')
    def get_etud_dept(self, REQUEST=None):
        """Returns the dept id (eg "GEII") of an etud (identified by etudid, INE or NIP in REQUEST).
        Warning: This function is inefficient and its result should be cached.
        """
        depts = self.list_depts()
        for dept in depts:
            etud = dept.Scolarite.getEtudInfo(REQUEST=REQUEST)
            if etud:
                return dept.id
        return '' # not found

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
