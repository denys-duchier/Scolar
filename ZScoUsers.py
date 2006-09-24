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

""" Gestion des utilisateurs (table SQL pour Zope User Folder)
"""

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
#import notes_users
from ScolarRolesNames import *
from TrivialFormulator import TrivialFormulator, TF
import string, re
import time
import md5, base64

# ----------------- password checking
import crack
def pwdFascistCheck( cleartxt ):
    "returns None if OK"
    try:
        x = crack.FascistCheck( cleartxt )
        return None
    except ValueError, m:
        return m

# ---------------

class ZScoUsers(ObjectManager,
                PropertyManager,
                RoleManager,
                Item,
                Persistent,
                Implicit
                ):

    "ZScousers object"

    meta_type = 'ZScoUsers'
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
    def manage_editZScousers(self, title, RESPONSE=None):
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

    security.declareProtected('Change DTML Documents', 'GetUsersDBConnexion')
    def GetUsersDBConnexion(self,new=False):
        # not published
        try:
            # a database adaptor called UsersDB must exists
            cnx = self.UsersDB().db 
        except:
            # backward compat: try to use same DB
            cnx = self.GetDBConnexion() 
        cnx.commit() # sync !
        return cnx

    # --------------------------------------------------------------------
    #
    #   Users (top level)
    #
    # --------------------------------------------------------------------
    # used to view content of the object
    security.declareProtected(ScoAdminUsers, 'index_html')
    def index_html(self, REQUEST):
        "gestion utilisateurs..."
        H = [self.sco_header(self,REQUEST,page_title='Gestion des utilisateurs')]
        n = len(self.user_list())
        H.append('<h1>Gestion des utilisateurs</h1>')
        H.append( self.list_users() )
        F = self.sco_footer(self,REQUEST)
        return '\n'.join(H) + F

    _userEditor = EditableTable(
        'sco_users',
        'user_id',
        ('user_id', 'user_name','passwd','roles',
         'date_modif_passwd','nom','prenom'),
        output_formators = { 'date_modif_passwd' : DateISOtoDMY }
        )
    security.declareProtected(ScoAdminUsers, 'user_list')
    def user_list(self, **kw):
        "list info sur utilisateur(s)"
        cnx = self.GetUsersDBConnexion()        
        return self._userEditor.list( cnx, **kw )

    def user_info(self, user_name):
        "donne infos sur l'utilisateur (qui peut ne pas etre dans notre base)"
        infos = self.user_list( args={'user_name':user_name} )
        if not infos:
            return { 'user_name' : user_name,
                     'nom' : user_name, 'prenom' : '', 'email' : '', 'dept' : '' }
        else:
            info = infos[0]
            if info['prenom']:
                p = info['prenom'][:1].upper() + '. '
            else:
                p = ''
            if info['nom']:
                n = info['nom'].lower().capitalize()
            else:
                n = user_name
            info['nomprenom'] = p + n
            return info

    security.declareProtected(ScoView, 'change_password')
    def change_password(self, user_name, password, password2, REQUEST):
        "change a password"
        H = [self.sco_header(self,REQUEST)]
        F = self.sco_footer(self,REQUEST)
        # Check access permission
        authuser = REQUEST.AUTHENTICATED_USER
        if authuser.has_permission(ScoAdminUsers,self) or str(authuser) == user_name:
            # check password
            if password != password2:
                H.append( """<p>Les deux mots de passes saisis sont différents !</p>
                <p><a href="form_change_password">Recommencer</a></p>""")
            else:                
                if pwdFascistCheck(password):
                    H.append( """<p><b>ce mot de passe n\'est pas assez compliqué !</b><br>(oui, il faut un mot de passe vraiment compliqué !)</p>
                    <p><a href="form_change_password">Recommencer</a></p>
                    """ )
                else:
                    # ok, strong password
                    # MD5 hash
                    digest = md5.new()
                    digest.update(password)
                    digest = digest.digest()
                    md5pwd = string.strip(base64.encodestring(digest))
                    #
                    cnx = self.GetUsersDBConnexion()
                    cursor = cnx.cursor()
                    cursor.execute( 'select count(*) from sco_users where user_name=%(user_name)s', { 'user_name' : user_name } )
                    r = cursor.fetchall()
                    assert len(r) <= 1, 'database insconsistency: len(r)=%d'%len(r)
                    if len(r) != 1:
                        H.append( """<p>Cet utilisateur (%s) n'est pas défini dans ce module. Nous ne pouvons modifier son mot de passe ici.</p>""" % user_name )
                    else:
                        cursor.execute('update sco_users set passwd=%(md5pwd)s, date_modif_passwd=now() where user_name=%(user_name)s', { 'md5pwd' : md5pwd, 'user_name' : user_name } )
                        cnx.commit()
                        log("change_password: change ok for %s" % user_name)
                        H.append("<h2>Changement effectué !</h2><p>Ne notez pas ce mot de passe, mais mémorisez le !</p><p>Rappel: il est <b>interdit</b> de communiquer son mot de passe à un tiers, même si c'est un collègue de confiance !</p><p><b>Le système va vous redemander votre login et nouveau mot de passe au prochain accès, c'est normal.</b></p>")
        else:
            # access denied
            log("change_password: access denied (authuser=%s, user_name=%s, ip=%s)"
                % (authuser, user_name, REQUEST.REMOTE_ADDR) )
            raise AccessDenied("vous n'avez pas la permission de changer ce mot de passe")
        return '\n'.join(H) + F
    
    security.declareProtected(ScoView, 'form_change_password')
    def form_change_password(self, REQUEST, user_name=None):
        """Formulaire changement mot de passe
        Un utilisateur peut toujours changer son mot de passe"""
        authuser = REQUEST.AUTHENTICATED_USER
        if not user_name:
            user_name = str(authuser)
        H = [self.sco_header(self,REQUEST)]
        F = self.sco_footer(self,REQUEST)
        # check access
        if (not authuser.has_permission(ScoAdminUsers,self)) and (str(authuser) != user_name):
            return '\n'.join(H)+"<p>Vous n'avez pas la permission de changer ce mot de passe</p>" + F
        #
        H.append("""<h2>Changement du mot de passe de <font color="#FF0000">%(user_name)s</font></h2>
        <p>
        <form action="change_password" method="post"><table>
        <tr><td>Nouveau mot de passe:</td><td><input type="password" size="14" name="password"/></td></tr>
        <tr><td>Confirmation: </td><td><input type="password" size="14" name="password2" /></td></tr>
        </table>
        <input type="hidden" value="%(user_name)s" name="user_name">
        <input type="submit" value="Changer">
        """ % {'user_name' : user_name} )
        return '\n'.join(H)+F
        # "
    security.declareProtected(ScoView, 'userinfo')
    def userinfo(self, REQUEST):
        "display page of info about connected user"
        authuser = REQUEST.AUTHENTICATED_USER
        user_name = str(authuser)
        H = [self.sco_header(self,REQUEST)]
        F = self.sco_footer(self,REQUEST)
        H.append('<h2>Utilisateur: %s</h2>' % authuser )
        info = self.user_list( args= { 'user_name' : user_name })
        if not info:
            H.append("<p>L' utilisateur '%s' n'est pas défini dans ce module.</p>" % user_name )
        else:
            H.append("""<p>
            <b>Login :</b> %(user_name)s<br>
            <b>Nom :</b> %(nom)s<br>
            <b>Prénom :</b> %(prenom)s<br>
            <b>Mail :</b> %(email)s<br>
            <b>Roles :</b> %(roles)s<br>
            <b>Dernière modif mot de passe:</b> %(date_modif_passwd)s
            """ % info[0])
            H.append('<p><ul><li><a href="form_change_password">changer le mot de passe</a></li><li>Se déconnecter: <a href="acl_users/logout">logout</a></li></ul>')
            
        return '\n'.join(H)+F
        
#     security.declareProtected(ScoAdminUsers, 'create_user_form')
#     def create_user_form(self, REQUEST, edit=False):
#         "form. creation ou edit utilisateur"
#         H = [self.sco_header(self,REQUEST)]
#         F = self.sco_footer(self,REQUEST)
#         H.append("<h1>Création d'un utilisateur</h1>")
#         if not edit:
#             initvalues = {}
#             submitlabel = 'Créer utilisateur'
#         else:
#             raise NotImplementedError
#             # XXX resta a faire: modif formulaire (pas punmier passwd)
#             # + remise en forme valeurq (pas changer user_name, gestion passwd)
#             initvalues = self.user_list( args={'user_name': REQUEST.get('user_name')})[0]
#             submitlabel = 'Modifier infos'
#         descr = [
#             ('nom', { 'title' : 'Nom',
#                       'size' : 20, 'allow_null' : False }),
#             ('prenom', { 'title' : 'Prénom',
#                       'size' : 20, 'allow_null' : False }),
#             ('user_name', { 'title' : 'Pseudo (login)',
#                             'size' : 20, 'allow_null' : False }),
#             ('passwd', { 'title' : 'Mot de passe',
#                          'input_type' : 'password',
#                          'size' : 14, 'allow_null' : False }),
#             ('passwd2', { 'title' : 'Confirmer mot de passe',
#                          'input_type' : 'password',
#                          'size' : 14, 'allow_null' : False }),
#             ('email', { 'title' : 'e-mail',
#                          'input_type' : 'text',
#                          'size' : 20, 'allow_null' : True }),
#             ]
#         tf = TrivialFormulator( REQUEST.URL0, REQUEST.form, descr,
#                                 initvalues = initvalues,
#                                 submitlabel = submitlabel )
#         if tf[0] == 0:
#             return '\n'.join(H) + '\n' + tf[1] + F
#         elif tf[0] == -1:
#             return REQUEST.RESPONSE.redirect( REQUEST.URL1 )
#         else:
#             vals = tf[2]
#             # check passwords
#             if vals['passwd'] != vals['passwd2']:
#                 msg = '<ul class="tf-msg"><li>Les deux mots de passes ne correspondent pas !</li></ul>'
#                 return '\n'.join(H) + msg + '\n' + tf[1] + F
#             if not self.is_valid_passwd(vals['passwd']):
#                 msg = '<ul class="tf-msg"><li>Mot de passe trop simple, recommencez !</li></ul>'
#                 return '\n'.join(H) + msg + '\n' + tf[1] + F
#             # ok, go
#             self.create_user(self, args=vals, REQUEST=REQUEST)
        
#     security.declareProtected(ScoAdminUsers, 'create_user')
#     def create_user(self, args, REQUEST=None):
#         "creation utilisateur zope"
#         cnx = self.GetUsersDBConnexion()
#         r = self._userEditor.create(cnx, args)
#         if REQUEST:
#             return REQUEST.RESPONSE.redirect( REQUEST.URL1 )

    security.declareProtected(ScoAdminUsers, 'list_users')
    def list_users(self,REQUEST=None):
        "liste des utilisateurs"
        r = self.user_list()
        if REQUEST:
            H = [self.sco_header(self,REQUEST)]
            F = self.sco_footer(self,REQUEST)
        else:
            H = []
            F = ''
        H.append('<h3>%d utilisateurs</h3>' % len(r))
        H.append('<table><tr><th>Login</th><th>Nom</th><th>Prénom</th><th>Roles</th><th>Modif. passwd</th><th>email</th></tr>')
        for u in r:
            H.append('<tr><td><a href="form_change_password?user_name=%(user_name)s">%(user_name)s</a></td><td>%(nom)s</td><td>%(prenom)s</td><td>%(roles)s</td><td>%(date_modif_passwd)s</td><td>%(email)s</td></tr>' % u)
        H.append('</table>')
        return '\n'.join(H) + F

    

# --------------------------------------------------------------------
#
# Zope Product Administration
#
# --------------------------------------------------------------------
def manage_addZScoUsers(self, id= 'id_ZScousers', title='The Title for ZScoUsers Object', REQUEST=None):
   "Add a ZScoUsers instance to a folder."
   self._setObject(id, ZScoUsers(id, title))
   if REQUEST is not None:
        return self.manage_main(self, REQUEST)
        #return self.manage_editForm(self, REQUEST)

# The form used to get the instance id from the user.
#manage_addZAbsencesForm = DTMLFile('dtml/manage_addZAbsencesForm', globals())


    

