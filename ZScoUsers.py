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
import sco_import_users, sco_excel
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
            log('warning: ZScoUsers using Sco DB connexion')
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
    def index_html(self, REQUEST, all=0):
        "gestion utilisateurs..."
        all = int(all)
        # Controle d'acces
        authuser = REQUEST.AUTHENTICATED_USER
        user_name = str(authuser)
        #log('user: %s roles: %s'%(user_name,authuser.getRolesInContext(self)))
        user = self._user_list( args={'user_name':user_name} )        
        if not user:
            zope_roles = authuser.getRolesInContext(self)
            if 'Manager' in zope_roles:
                dept = '' # special case for zope admin
            else:
                raise AccessDenied("Vous n'avez pas la permission de voir cette page")
        else:
            dept = user[0]['dept']
        #
        H = [self.sco_header(REQUEST,page_title='Gestion des utilisateurs')]
        H.append('<h1>Gestion des utilisateurs</h1>')        
        # 
        if authuser.has_permission(ScoAdminUsers,self):
            H.append('<p><a href="create_user_form" class="stdlink">Ajouter un utilisateur</a>')
            H.append('&nbsp;&nbsp; <a href="import_users_form" class="stdlink">Importer des utilisateurs</a></p>')
        #
        H.append( self.list_users( dept, all=all ) )
        #
        if all:
            checked = 'checked'
        else:
            checked = ''
        H.append("""<p><form name="f" action="."><input type="checkbox" name="all" value="1" onchange="document.f.submit();" %s>Montrer tous les d�partements</input></form></p>""" % checked)
        F = self.sco_footer(REQUEST)
        return '\n'.join(H) + F

    _userEditor = EditableTable(
        'sco_users',
        'user_id',
        ('user_id', 'user_name','passwd','roles',
         'date_modif_passwd','nom','prenom', 'email', 'dept'),
        output_formators = { 'date_modif_passwd' : DateISOtoDMY },
        sortkey = 'nom'
        )

    def _user_list(self, **kw):
        # list info sur utilisateur(s)
        cnx = self.GetUsersDBConnexion()        
        return self._userEditor.list( cnx, **kw )

    def _user_edit(self, *args, **kw ):
        # edit user
        cnx = self.GetUsersDBConnexion()
        self._userEditor.edit( cnx, *args, **kw )

    def _user_delete(self, user_name):
        # delete user
        cnx = self.GetUsersDBConnexion()
        user_id = self._user_list( args={'user_name':user_name} )[0]['user_id']
        self._userEditor.delete( cnx, user_id )

    security.declareProtected(ScoAdminUsers, 'user_info')
    def user_info(self, user_name, REQUEST):        
        "donne infos sur l'utilisateur (qui peut ne pas etre dans notre base)"
        infos = self._user_list( args={'user_name':user_name} )
        if not infos:
            # special case: user is not in our database
            return { 'user_name' : user_name,
                     'nom' : user_name, 'prenom' : '',
                     'email' : '', 'dept' : '',
                     'nomprenom' : user_name }
        else:
            info = infos[0]
            # peut on divulguer ces infos ?
            if not self._can_handle_passwd(REQUEST.AUTHENTICATED_USER, user_name):
                info['date_modif_passwd'] = 'NA'
            del info['passwd'] # always conceal password !
            #
            if info['prenom']:
                p = info['prenom']
            else:
                p = ''
            if info['nom']:
                n = info['nom'].lower().capitalize()
            else:
                n = user_name
            info['nomprenom'] = (abbrev_prenom(p) + ' ' + n).strip()

            return info

    def _can_handle_passwd(self, authuser, user_name):
        """true if authuser can see or change passwd of user_name.
        authuser is a Zope user object. user_name is a string.
        """
        # Is authuser a zope admin ?
        zope_roles = authuser.getRolesInContext(self)
        if 'Manager' in zope_roles:
            return True
        # Anyone can change its own passwd (or see its informations)
        if str(authuser) == user_name:
            return True
        # has permission ?
        if not authuser.has_permission(ScoAdminUsers,self):
            return False
        # Ok, now check that authuser can manage users from this departement
        # Get user info
        user = self._user_list( args={'user_name':user_name} )  
        if not user:
            return False # we don't have infos on this user !
        # Get authuser info
        auth_name = str(authuser)
        authuser_info = self._user_list( args={'user_name':auth_name} )  
        if not authuser_info:
            return False # not admin, and not in out database
        auth_dept = authuser_info[0]['dept']
        if not auth_dept:
            return True # if no dept, can access users from all depts !
        if auth_dept == user[0]['dept']:
            return True
        else:
            return False

    def _is_valid_passwd(self, passwd):
        "check if passwd is secure enough"
        return not pwdFascistCheck(passwd)

    def do_change_password(self, user_name, password):
        user = self._user_list( args={'user_name':user_name} )
        assert len(user) == 1, 'database insconsistency: len(r)=%d'%len(r)
        # should not occur, already tested in _can_handle_passwd
        cnx = self.GetUsersDBConnexion()
        cursor = cnx.cursor()
        cursor.execute('update sco_users set date_modif_passwd=now() where user_name=%(user_name)s',
                       { 'user_name' : user_name } )
        cnx.commit()
        req = { 'password' : password,
                'password_confirm' : password,
                'roles' : [user[0]['roles']] }
        # Laisse le exUserFolder modifier les donnees
        self.acl_users.manage_editUser( user_name, req )
        log("change_password: change ok for %s" % user_name)

    security.declareProtected(ScoView, 'change_password')
    def change_password(self, user_name, password, password2, REQUEST):
        "change a password"
        # ScoAdminUsers: modif tous les passwd de SON DEPARTEMENT
        # sauf si pas de dept (admin global)
        H = []
        F = self.sco_footer(REQUEST)
        # Check access permission
        if not self._can_handle_passwd( REQUEST.AUTHENTICATED_USER, user_name):
            # access denied
            log("change_password: access denied (authuser=%s, user_name=%s, ip=%s)"
                % (authuser, user_name, REQUEST.REMOTE_ADDR) )
            raise AccessDenied("vous n'avez pas la permission de changer ce mot de passe")
        # check password
        if password != password2:
            H.append( """<p>Les deux mots de passes saisis sont diff�rents !</p>
            <p><a href="form_change_password?user_name=%s" class="stdlink">Recommencer</a></p>""" % user_name )
        else:
            if not self._is_valid_passwd(password):
                H.append( """<p><b>ce mot de passe n\'est pas assez compliqu� !</b><br>(oui, il faut un mot de passe vraiment compliqu� !)</p>
                <p><a href="form_change_password?user_name=%s" class="stdlink">Recommencer</a></p>
                """ % user_name )
            else:
                # ok, strong password
                # MD5 hash (now computed by exUserFolder)
                #digest = md5.new()
                #digest.update(password)
                #digest = digest.digest()
                #md5pwd = string.strip(base64.encodestring(digest))
                #
                self.do_change_password(user_name, password)
                # 
                # ici page simplifiee car on peut ne plus avoir
                # le droit d'acceder aux feuilles de style
                H.append("<h2>Changement effectu� !</h2><p>Ne notez pas ce mot de passe, mais m�morisez le !</p><p>Rappel: il est <b>interdit</b> de communiquer son mot de passe � un tiers, m�me si c'est un coll�gue de confiance !</p><p><b>Si vous n'�tes pas administrateur, le syst�me va vous redemander votre login et nouveau mot de passe au prochain acc�s.</b></p>")
                return """<?xml version="1.0" encoding="iso-8859-15"?>
<!DOCTYPE html PUBLIC "-//W3C//DTD XHTML 1.0 Transitional//EN" "http://www.w3.org/TR/xhtml1/DTD/xhtml1-transitional.dtd">
<html>
<head>
<title>Mot de passe chang�</title>
<meta http-equiv="Content-Type" content="text/html; charset=iso-8859-15" />
<body><h1>Mot de passe chang� !</h1>
""" + '\n'.join(H) + '<a href="%s"  class="stdlink">Continuer</a></body></html>' % self.ScoURL()
        return self.sco_header(REQUEST) + '\n'.join(H) + F
    
    security.declareProtected(ScoView, 'form_change_password')
    def form_change_password(self, REQUEST, user_name=None):
        """Formulaire changement mot de passe
        Un utilisateur peut toujours changer son mot de passe"""
        authuser = REQUEST.AUTHENTICATED_USER
        if not user_name:
            user_name = str(authuser)
        H = [self.sco_header(REQUEST)]
        F = self.sco_footer(REQUEST)
        # check access
        if not self._can_handle_passwd(authuser, user_name):
            return '\n'.join(H)+"<p>Vous n'avez pas la permission de changer ce mot de passe</p>" + F
        #
        H.append("""<h2>Changement du mot de passe de <font color="red">%(user_name)s</font></h2>
        <p>
        <form action="change_password" method="post"><table>
        <tr><td>Nouveau mot de passe:</td><td><input type="password" size="14" name="password"/></td></tr>
        <tr><td>Confirmation: </td><td><input type="password" size="14" name="password2" /></td></tr>
        </table>
        <input type="hidden" value="%(user_name)s" name="user_name">
        <input type="submit" value="Changer">
""" % {'user_name' : user_name} )
        return '\n'.join(H) + F

    security.declareProtected(ScoView, 'userinfo')
    def userinfo(self, user_name=None, REQUEST=None):
        "display page of info about connected user"        
        authuser = REQUEST.AUTHENTICATED_USER
        if not user_name:
            user_name = str(authuser)
        # peut on divulguer ces infos ?
        if not self._can_handle_passwd(REQUEST.AUTHENTICATED_USER, user_name):
            raise AccessDenied("Vous n'avez pas la permission de voir cette page")
        H = [self.sco_header(REQUEST, page_title='Utilisateur %s'%user_name)]
        F = self.sco_footer(REQUEST)
        H.append('<h2>Utilisateur: %s</h2>' % user_name )
        info = self._user_list( args= { 'user_name' : user_name })
        if not info:
            H.append("<p>L' utilisateur '%s' n'est pas d�fini dans ce module.</p>" % user_name )
            if authuser.has_permission(ScoEditAllNotes,self):
                H.append("<p>(il peut modifier toutes les notes)</p>")
            if authuser.has_permission(ScoImplement,self):
                H.append("<p>(il peut creer des formations)</p>")
        else:
            H.append("""<p>
            <b>Login :</b> %(user_name)s<br>
            <b>Nom :</b> %(nom)s<br>
            <b>Pr�nom :</b> %(prenom)s<br>
            <b>Mail :</b> %(email)s<br>
            <b>Roles :</b> %(roles)s<br>
            <b>Dept :</b> %(dept)s<br>
            <b>Derni�re modif mot de passe:</b> %(date_modif_passwd)s
            <p><ul>
             <li><a class="stdlink" href="form_change_password?user_name=%(user_name)s">changer le mot de passe</a></li>""" % info[0])
            if authuser.has_permission(ScoAdminUsers,self):
                H.append("""
             <li><a  class="stdlink" href="create_user_form?user_name=%(user_name)s&edit=1">modifier cet utilisateur</a></li>
             <li><a  class="stdlink" href="delete_user_form?user_name=%(user_name)s">supprimer cet utilisateur</a> <em>(� n'utiliser qu'en cas d'erreur !)</em></li>
             """ % info[0])
                
            H.append('</ul>')
            
            if str(authuser) == user_name:
                H.append('<p><b>Se d�connecter: <a class="stdlink" href="acl_users/logout">logout</a></b></p>')
            # Liste des permissions
            H.append('<div class="permissions">')
            permissions = self.ac_inherited_permissions(1)
            scoperms = [ p for p in permissions if p[0][:3] == 'Sco' ]
            thisuser = self.acl_users.getUser(user_name)
            for p in scoperms:
                permname, value = p[:2]
                if thisuser.has_permission(permname,self):
                    b = 'oui'
                else:
                    b = 'non'
                H.append('%s : %s<br/>' % (permname,b)) 
            H.append('</div>')
        if authuser.has_permission(ScoAdminUsers,self):
            H.append('<p><a class="stdlink" href="%s/Users">Liste de tous les utilisateurs</a></p>' % self.ScoURL())
        return '\n'.join(H)+F
        
    security.declareProtected(ScoAdminUsers, 'create_user_form')
    def create_user_form(self, REQUEST, user_name=None, edit=0):
         "form. creation ou edit utilisateur"
         # Get authuser info
         authuser = REQUEST.AUTHENTICATED_USER
         auth_name = str(authuser)
         authuser_info = self._user_list( args={'user_name':auth_name} )
         if not user_name:
             user_name = auth_name
         #
         edit = int(edit)
         H = [self.sco_header(REQUEST)]
         F = self.sco_footer(REQUEST)             
         if edit:
             H.append("<h1>Modification d'un utilisateur</h1>")
         else:
             H.append("<h1>Cr�ation d'un utilisateur</h1>")
         # Noms de roles pouvant etre attribues aux nouveaux utilisateurs
         # ! NE PAS INCLURE DE ROLES PRIVILEGIES !
         # (normalement: EnsDept, SecrDept)
         valid_roles = [ x.strip()
                         for x in self.DeptCreatedUsersRoles.split(',') ]
         #
         if not edit:
             initvalues = {}
             submitlabel = 'Cr�er utilisateur'
         else:
             # controle d'access
             initvalues = self._user_list( args={'user_name': user_name})[0]
             submitlabel = 'Modifier utilisateur'
         descr = [
             ('edit', {'input_type' : 'hidden', 'default' : edit }),
             ('nom', { 'title' : 'Nom',
                       'size' : 20, 'allow_null' : False }),
             ('prenom', { 'title' : 'Pr�nom',
                       'size' : 20, 'allow_null' : False }),
             ]
         if not edit:
             descr += [
                 ('user_name', { 'title' : 'Pseudo (login)',
                                 'size' : 20, 'allow_null' : False,
                                 'explanation' : 'nom utilis� pour la connexion. Doit �tre unique parmi tous les utilisateurs.'}),
                 ('passwd', { 'title' : 'Mot de passe',
                              'input_type' : 'password',
                              'size' : 14, 'allow_null' : False }),
                 ('passwd2', { 'title' : 'Confirmer mot de passe',
                               'input_type' : 'password',
                               'size' : 14, 'allow_null' : False }) ]
         else:
             descr += [
                 ('user_id', {'input_type' : 'hidden', 'default' : initvalues['user_id'] })
                 ]
         descr += [
             ('email', { 'title' : 'e-mail',
                         'input_type' : 'text',
                         'size' : 20, 'allow_null' : True }),
             ('roles', {'title' : 'Roles', 'input_type' : 'checkbox',
                        'allowed_values' : valid_roles})
             ]
         # Access control
         zope_roles = authuser.getRolesInContext(self)
         if not authuser_info and not ('Manager' in zope_roles):
             # not admin, and not in database
             raise AccessDenied('invalid user (%s)' % auth_name)
         if authuser_info:
             auth_dept = authuser_info[0]['dept']
         else:
             auth_dept = ''
         if not auth_dept:
             # si auth n'a pas de departement (admin global)
             # propose de choisir le dept du nouvel utilisateur
             # sinon, il sera cr�� dans le m�me d�partement que auth
             descr.append(('dept',
                          { 'title' : 'Dept',
                            'input_type' : 'text',
                            'size' : 12,
                            'allow_null' : True,
                            'explanation' : 'd�partement d\'appartenance de l\'utilisateur'
                            }))
             can_choose_dept = True
         else:
             can_choose_dept = False
             descr.append(('d', {'input_type' : 'separator',
                                'title' : 'L\'utilisateur  sera cr�e dans le d�partement %s' % auth_dept}))
         descr.append(('force', {'title' : 'Ignorer les avertissements', 'input_type' : 'checkbox', 'labels' : ('',), 'allowed_values' : ('1',)}))
         tf = TrivialFormulator( REQUEST.URL0, REQUEST.form, descr,
                                 initvalues = initvalues,
                                 submitlabel = submitlabel )
         if tf[0] == 0:
             return '\n'.join(H) + '\n' + tf[1] + F
         elif tf[0] == -1:
             return REQUEST.RESPONSE.redirect( REQUEST.URL1 )
         else:
             vals = tf[2]
             for role in vals['roles']:
                 if not role in valid_roles:
                     raise ScoValueError('Invalid role for new user: %s' % role)
               
             if REQUEST.form.has_key('edit'):
                 edit = int(REQUEST.form['edit'])
             else:
                 edit = 0
             try:
                 force = int(vals['force'][0])
             except:
                 force = 0
             #log('create_user_form: force=%s, vals=%s' % (force,str(vals)))
             if not force:
                 if edit:
                     user_name = initvalues['user_name']
                 else:
                     user_name = vals['user_name']
                 ok, msg = self._check_modif_user(
                     edit, user_name=user_name,
                     nom=vals['nom'], prenom=vals['prenom'],
                     email=vals['email'], roles=vals['roles'] )
                 if not ok:
                     H.append('<ul class="tf-msg"><li class="tf-msg">Attention: '+msg+""" (vous pouvez forcer l'op�ration en cochant "<em>Ignorer les avertissements</em>")'</li></ul>""")
                     return '\n'.join(H) + '\n' + tf[1] + F
             if edit: # modif utilisateur (mais pas passwd)
                 if (not can_choose_dept) and vals.has_key('dept'):
                     del vals['dept']
                 if vals.has_key('passwd'):
                     del vals['passwd']
                 if vals.has_key('date_modif_passwd'):
                     del vals['date_modif_passwd']
                 if vals.has_key('user_name'):
                     del vals['user_name']
                 # traitement des roles: ne doit pas affecter les roles
                 # que l'on en controle pas:
                 orig_roles = initvalues['roles'].split(',')
                 for role in orig_roles:
                     if not role in valid_roles:
                         vals['roles'].append(role)
                 vals['roles'] = ','.join(vals['roles'])
                 # ok, edit
                 self._user_edit(vals)
                 return REQUEST.RESPONSE.redirect( REQUEST.URL1 )
             else: # creation utilisateur
                 vals['roles'] = ','.join(vals['roles'])
                 # check passwords
                 if vals['passwd'] != vals['passwd2']:
                     msg = '<ul class="tf-msg"><li>Les deux mots de passes ne correspondent pas !</li></ul>'
                     return '\n'.join(H) + msg + '\n' + tf[1] + F
                 if not self._is_valid_passwd(vals['passwd']):
                     msg = '<ul class="tf-msg"><li>Mot de passe trop simple, recommencez !</li></ul>'
                     return '\n'.join(H) + msg + '\n' + tf[1] + F
                 if not can_choose_dept:
                     vals['dept'] = auth_dept
                 # ok, go
                 self.create_user(vals, REQUEST=REQUEST)

    def _check_modif_user(self, edit, user_name='', nom='', prenom='',
                          email='', roles=[]):
        """V�rifie que et utilisateur peut etre cr�e (edit=0) ou modifi� (edit=1)
        Cherche homonymes.
        returns (ok, msg)
          - ok : si vrai, peut continuer avec ces parametres
          - msg: message warning a presenter l'utilisateur
        """
        if not user_name or not nom or not prenom:
            return False, 'champ requis vide'
        # ce login existe ?
        users = self._user_list( args={'user_name':user_name} )  
        if edit and not users: # safety net, le user_name ne devrait pas changer
            return False, "identifiant %s inexistant" % user_name
        if not edit and users:
            return False, "identifiant %s d�j� utilis�" % user_name

        # Des noms/pr�noms semblables existent ?            
        cnx = self.GetUsersDBConnexion()
        cursor = cnx.cursor()
        cursor.execute('select * from sco_users where lower(nom) ~ %(nom)s and lower(prenom) ~ %(prenom)s;', { 'nom' : nom.lower().strip(), 'prenom' : prenom.lower().strip() } )
        res = cursor.dictfetchall()
        if edit:
            minmatch = 1
        else:
            minmatch = 0
        if len(res) > minmatch:
            return False, "des utilisateurs proches existent: " + ', '.join([  '%s %s (pseudo=%s)' % (x['prenom'], x['nom'], x['user_name']) for x in res ])
        # Roles ?
        if not roles:
            return False, "aucun r�le s�lectionn�, �tes vous s�r ?"
        # ok
        return True, ''

    security.declareProtected(ScoAdminUsers, 'import_users_form')
    def import_users_form(self, REQUEST, user_name=None, edit=0):
        """Import utilisateurs depuis feuille Excel"""
        head = self.sco_header(REQUEST, page_title='Import utilisateurs')
        H = [head,
             """<h2>T�l�chargement d'une nouvelle liste d'utilisateurs</h2>
             <p style="color: red">A utiliser pour importer de <b>nouveaux</b> utilisateurs (enseignants ou secr�taires)
             </p>
             <p>
             L'op�ration se d�roule en deux �tapes. Dans un premier temps,
             vous t�l�chargez une feuille Excel type. Vous devez remplir
             cette feuille, une ligne d�crivant chaque utilisateur. Ensuite,
             vous indiquez le nom de votre fichier dans la case "Fichier Excel"
             ci-dessous, et cliquez sur "T�l�charger" pour envoyer au serveur
             votre liste.
             </p>
             """]
        H.append("""<ol><li><a class="stdlink" href="import_users_generate_excel_sample">
        Obtenir la feuille excel � remplir</a></li><li>""")
        F = self.sco_footer(REQUEST)
        tf = TrivialFormulator(
            REQUEST.URL0, REQUEST.form, 
            (('xlsfile', {'title' : 'Fichier Excel:', 'input_type' : 'file',
                          'size' : 40 }),
             ('formsemestre_id', {'input_type' : 'hidden' }), 
             ), submitlabel = 'T�l�charger')
        if  tf[0] == 0:            
            return '\n'.join(H) + tf[1] + '</li></ol>' + F
        elif tf[0] == -1:
            return REQUEST.RESPONSE.redirect( REQUEST.URL1 )
        else:
            # IMPORT
            diag = sco_import_users.import_excel_file(tf[2]['xlsfile'],
                                                      REQUEST=REQUEST, context=self)
            H = [head]
            H.append('<p>Import excel: %s</p>'% diag)
            H.append('<p>OK, import termin� !</p>')
            H.append('<p><a class="stdlink" href="%s">Continuer</a></p>' % REQUEST.URL1)
            return '\n'.join(H) + F
    
    security.declareProtected(ScoAdminUsers, 'import_users_generate_excel_sample')
    def import_users_generate_excel_sample(self, REQUEST):
        "une feuille excel pour importation utilisateurs"
        data = sco_import_users.generate_excel_sample()
        return sco_excel.sendExcelFile(REQUEST,data,'ImportUtilisateurs.xls')    
    
    security.declareProtected(ScoAdminUsers, 'create_user')
    def create_user(self, args, REQUEST=None):
        "creation utilisateur zope"
        cnx = self.GetUsersDBConnexion()        
        passwd = args['passwd']
        args['passwd'] = 'undefined'
        log('create_user: args=%s' % args) # log apres supr. du mot de passe !
        r = self._userEditor.create(cnx, args)
        # call exUserFolder to set passwd
        args['password'] = passwd
        args['password_confirm'] = passwd
        args['roles'] = args['roles'].split(',')
        junk = self.acl_users.manage_editUser( args['user_name'], args )
        #log('create_user: junk=%s\n' % junk )
        if REQUEST:
            return REQUEST.RESPONSE.redirect( REQUEST.URL1 )

    security.declareProtected(ScoAdminUsers, 'delete_user_form')
    def delete_user_form(self, REQUEST, user_name, dialog_confirmed=False):
        "delete user"
        r = self._user_list( args={'user_name' : user_name})
        if len(r) != 1:
            return ScoValueError('utilisateur %s inexistant' % user_name)
        if not dialog_confirmed:
            return self.confirmDialog(
                """<h2>Confirmer la suppression de l\'utilisateur %s ?</h2>
                <p>En g�n�ral, il est d�conseill� de supprimer un utilisateur, son
                identit� �tant r�f�renc� dans les modules de formation. N'utilisez
                cette fonction qu'en cas d'erreur (cr�ation de doublons, etc).
                </p>
                """% user_name,
                dest_url="", REQUEST=REQUEST,
                cancel_url=REQUEST.URL1,
                parameters={'user_name':user_name})
        self._user_delete(user_name)
        REQUEST.RESPONSE.redirect( REQUEST.URL1 )
        
    security.declareProtected(ScoAdminUsers, 'list_users')
    def list_users(self, dept, all=False, REQUEST=None):
        "liste des utilisateurs"
        if dept and not all:            
            r = self._user_list( args={ 'dept' : dept } )
            comm = '(dept. %s)' % dept
        else:
            r = self._user_list() # all users
            comm = '(tous)'
        if REQUEST:
            H = [self.sco_header(REQUEST)]
            F = self.sco_footer(REQUEST)
        else:
            H = []
            F = ''
        H.append('<h3>%d utilisateurs %s</h3>' % (len(r), comm))
        H.append('<p>Cliquer sur un nom pour changer son mot de passe</p>')
        H.append('<table><tr><th>Login</th><th>Nom</th><th>Pr�nom</th><th>Roles</th><th>Modif. passwd</th><th>email</th><th>Dept.</th></tr>')
        for u in r:
            H.append('<tr><td><a class="stdlink" href="userinfo?user_name=%(user_name)s">%(user_name)s</a></td><td>%(nom)s</td><td>%(prenom)s</td><td>%(roles)s</td><td>%(date_modif_passwd)s</td><td>%(email)s</td><td>%(dept)s</td></tr>' % u)
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


    

