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
import string, re
import time
import md5, base64
from sets import Set

import jaxml

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
from sco_utils import *
from scolars import format_prenom
import sco_import_users, sco_excel
from TrivialFormulator import TrivialFormulator, TF
from gen_tables import GenTable
import scolars
import sco_cache

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
# cache global: chaque instance,  rep�r�e par son URL, a un cache
# qui est recr�� � la demande
# On cache ici la liste des utilisateurs, pour une duree limitee
# (une minute).

CACHE_userlist = {}

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
            # a database adaptor called UsersDB must exist
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
    security.declareProtected(ScoUsersView, 'index_html')
    def index_html(self, REQUEST, all=0, format='html'):
        "gestion utilisateurs..."
        all = int(all)
        # Controle d'acces
        authuser = REQUEST.AUTHENTICATED_USER
        user_name = str(authuser)
        #log('user: %s roles: %s'%(user_name,authuser.getRolesInContext(self)))
        user = self._user_list( args={'user_name':user_name} )        
        if not user:
            zope_roles = authuser.getRolesInContext(self)
            if ('Manager' in zope_roles) or ('manage' in zope_roles):
                dept = '' # special case for zope admin
            else:
                raise AccessDenied("Vous n'avez pas la permission de voir cette page")
        else:
            dept = user[0]['dept']
        
        H = [self.sco_header(REQUEST,page_title='Gestion des utilisateurs')]
        H.append('<h2>Gestion des utilisateurs</h2>')        
        
        if authuser.has_permission(ScoUsersAdmin,self):
            H.append('<p><a href="create_user_form" class="stdlink">Ajouter un utilisateur</a>')
            H.append('&nbsp;&nbsp; <a href="import_users_form" class="stdlink">Importer des utilisateurs</a></p>')
        if all:
            checked = 'checked'
        else:
            checked = ''
        H.append("""<p><form name="f" action="%s"><input type="checkbox" name="all" value="1" onchange="document.f.submit();" %s>Montrer tous les d�partements</input></form></p>""" % (REQUEST.URL0,checked))

        L = self.list_users( dept, all=all, format=format,
                             REQUEST=REQUEST, with_links=authuser.has_permission(ScoUsersAdmin,self) )
        if format != 'html':
            return L
        H.append(L) 
        
        F = self.sco_footer(REQUEST)
        return '\n'.join(H) + F

    _userEditor = EditableTable(
        'sco_users',
        'user_id',
        ('user_id', 'user_name','passwd','roles',
         'date_modif_passwd','nom','prenom', 'email', 'dept', 'passwd_temp'),
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
        self.get_userlist_cache().inval_cache() #>

    def _user_delete(self, user_name):
        # delete user
        cnx = self.GetUsersDBConnexion()
        user_id = self._user_list( args={'user_name':user_name} )[0]['user_id']
        self._userEditor.delete( cnx, user_id )
        self.get_userlist_cache().inval_cache() #>

    def _all_roles(self):
        "ensemble de tous les roles attribu�s ou attribuables"
        roles = Set(self.DeptUsersRoles())
        cnx = self.GetUsersDBConnexion()
        L = self._userEditor.list( cnx, {} )
        for l in L:
            roles.update( [x.strip() for x in l['roles'].split(',')] )            
        return roles

    security.declareProtected(ScoUsersAdmin, 'user_info')
    def user_info(self, user_name=None, user=None, REQUEST=None):        
        """Donne infos sur l'utilisateur (qui peut ne pas etre dans notre base).
        Si user_name est specifie, interroge la BD. Sinon, user doit etre un dict.        
        XXX REQUEST is not used
        """
        if user_name:
            infos = self._user_list( args={'user_name':user_name} )
        else:
            infos = [user.copy()]
            user_name=user['user_name']
        
        if not infos:
            # special case: user is not in our database
            return { 'user_name' : user_name,
                     'nom' : user_name, 'prenom' : '',
                     'email' : '', 'dept' : '',
                     'nomprenom' : user_name,
                     'prenomnom' : user_name,
                     'nomcomplet': user_name,
                     'nomplogin' : user_name,
                     'nomnoacc'  : suppress_accents(user_name),
                     'passwd_temp' : 0
                     }
        else:
            info = infos[0]
            # always conceal password !
            del info['passwd'] # always conceal password !
            #
            if info['prenom']:
                p = format_prenom(info['prenom'])
            else:
                p = ''
            if info['nom']:
                n = info['nom'].lower().capitalize()
            else:
                n = user_name
            prenom_abbrv = abbrev_prenom(p)
            # nomprenom est le nom capitalis� suivi de l'initiale du pr�nom
            info['nomprenom'] = (n + ' ' + prenom_abbrv).strip()
            # prenomnom est l'initiale du pr�nom suivie du nom
            info['prenomnom'] = (prenom_abbrv + ' ' + n).strip()
            # nomcomplet est le prenom et le nom complets
            info['nomcomplet'] = scolars.format_prenom(p) + ' ' + scolars.format_nom(n)
            # nomplogin est le nom en majuscules suivi du pr�nom et du login
            # e.g. Dupont Pierre (dupont)
            info['nomplogin'] = '%s %s (%s)' % (n.upper(), p, info['user_name'])
            # nomnoacc est le nom en minuscules sans accents
            info['nomnoacc'] = suppress_accents(info['nom'].lower())
            return info

    def _can_handle_passwd(self, authuser, user_name, allow_admindepts=False):
        """true if authuser can see or change passwd of user_name.
        If allow_admindepts, allow Admin from all depts (so they can view users from other depts
        and add roles to them).
        authuser is a Zope user object. user_name is a string.
        """
        # Is authuser a zope admin ?
        zope_roles = authuser.getRolesInContext(self)
        if ('Manager' in zope_roles) or ('manage' in zope_roles):
            return True
        # Anyone can change its own passwd (or see its informations)
        if str(authuser) == user_name:
            return True
        # has permission ?
        if not authuser.has_permission(ScoUsersAdmin,self):
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
        if auth_dept == user[0]['dept'] or allow_admindepts:
            return True
        else:
            return False

    def _is_valid_passwd(self, passwd):
        "check if passwd is secure enough"
        return not pwdFascistCheck(passwd)

    def do_change_password(self, user_name, password):
        user = self._user_list( args={'user_name':user_name} )
        assert len(user) == 1, 'database inconsistency: len(r)=%d'%len(r)
        # should not occur, already tested in _can_handle_passwd
        cnx = self.GetUsersDBConnexion()
        cursor = cnx.cursor()
        cursor.execute('update sco_users set date_modif_passwd=now(), passwd_temp=0 where user_name=%(user_name)s',
                       { 'user_name' : user_name } )
        cnx.commit()
        req = { 'password' : password,
                'password_confirm' : password,
                'roles' : [user[0]['roles']] }

        # Laisse le exUserFolder modifier les donnees
        self.acl_users.manage_editUser( user_name, req )
        
        log("change_password: change ok for %s" % user_name)
        self.get_userlist_cache().inval_cache() #>

    security.declareProtected(ScoView, 'change_password')
    def change_password(self, user_name, password, password2, REQUEST):
        "change a password"
        # ScoUsersAdmin: modif tous les passwd de SON DEPARTEMENT
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
                H.append( """<p><b>ce mot de passe n\'est pas assez compliqu� !</b><br/>(oui, il faut un mot de passe vraiment compliqu� !)</p>
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
        H = [self.sco_header(REQUEST, user_check=False)]
        F = self.sco_footer(REQUEST)
        # check access
        if not self._can_handle_passwd(authuser, user_name):
            return '\n'.join(H)+"<p>Vous n'avez pas la permission de changer ce mot de passe</p>" + F
        #
        H.append("""<h2>Changement du mot de passe de <font color="red">%(user_name)s</font></h2>
        <p>
        <form action="change_password" method="post" action="%(url)s"><table>
        <tr><td>Nouveau mot de passe:</td><td><input type="password" size="14" name="password"/></td></tr>
        <tr><td>Confirmation: </td><td><input type="password" size="14" name="password2" /></td></tr>
        </table>
        <input type="hidden" value="%(user_name)s" name="user_name">
        <input type="submit" value="Changer">
        </p>
        <p>Vous pouvez aussi: <a class="stdlink" href="reset_password_form?user_name=%(user_name)s">renvoyer un mot de passe al�atoire temporaire par mail � l'utilisateur</a>
""" % {'user_name' : user_name, 'url' : REQUEST.URL0} )
        return '\n'.join(H) + F

    security.declareProtected(ScoView, 'userinfo')
    def userinfo(self, user_name=None, REQUEST=None):
        "display page of info about connected user"        
        authuser = REQUEST.AUTHENTICATED_USER
        if not user_name:
            user_name = str(authuser)
        # peut on divulguer ces infos ?
        if not self._can_handle_passwd(REQUEST.AUTHENTICATED_USER, user_name, allow_admindepts=True):
            raise AccessDenied("Vous n'avez pas la permission de voir cette page")
        H = [self.sco_header(REQUEST, page_title='Utilisateur %s'%user_name)]
        F = self.sco_footer(REQUEST)
        H.append('<h2>Utilisateur: %s</h2>' % user_name )
        info = self._user_list( args= { 'user_name' : user_name })
        if not info:
            H.append("<p>L' utilisateur '%s' n'est pas d�fini dans ce module.</p>" % user_name )
            if authuser.has_permission(ScoEditAllNotes,self):
                H.append("<p>(il peut modifier toutes les notes)</p>")
            if authuser.has_permission(ScoEditAllEvals,self):
                H.append("<p>(il peut modifier toutes les �valuations)</p>")                
            if authuser.has_permission(ScoImplement,self):
                H.append("<p>(il peut creer des formations)</p>")
        else:
            H.append("""<p>
            <b>Login :</b> %(user_name)s<br/>
            <b>Nom :</b> %(nom)s<br/>
            <b>Pr�nom :</b> %(prenom)s<br/>
            <b>Mail :</b> %(email)s<br/>
            <b>Roles :</b> %(roles)s<br/>
            <b>Dept :</b> %(dept)s<br/>
            <b>Derni�re modif mot de passe:</b> %(date_modif_passwd)s
            <p><ul>
             <li><a class="stdlink" href="form_change_password?user_name=%(user_name)s">changer le mot de passe</a></li>""" % info[0])
            if authuser.has_permission(ScoUsersAdmin,self):
                H.append("""
             <li><a  class="stdlink" href="create_user_form?user_name=%(user_name)s&edit=1">modifier cet utilisateur</a></li>
             <li><a  class="stdlink" href="delete_user_form?user_name=%(user_name)s">supprimer cet utilisateur</a> <em>(� n'utiliser qu'en cas d'erreur !)</em></li>
             """ % info[0])
                
            H.append('</ul>')
            
            if str(authuser) == user_name:
                H.append('<p><b>Se d�connecter: <a class="stdlink" href="acl_users/logout">logout</a></b></p>')
            # Liste des permissions
            H.append('<div class="permissions"><p>Permission de cet utilisateur:</p><ul>')
            permissions = self.ac_inherited_permissions(1)
            scoperms = [ p for p in permissions if p[0][:3] == 'Sco' ]
            try:
                thisuser = self.acl_users.getUser(user_name)
            except:
                # expired from cache ? retry...
                thisuser = self.acl_users.getUser(user_name)
            for p in scoperms:
                permname, value = p[:2]
                if thisuser.has_permission(permname,self):
                    b = 'oui'
                else:
                    b = 'non'
                H.append('<li>%s : %s</li>' % (permname,b)) 
            H.append('</ul></div>')
        if authuser.has_permission(ScoUsersAdmin,self):
            H.append('<p><a class="stdlink" href="%s/Users">Liste de tous les utilisateurs</a></p>' % self.ScoURL())
        return '\n'.join(H)+F
        
    security.declareProtected(ScoUsersAdmin, 'create_user_form')
    def create_user_form(self, REQUEST, user_name=None, edit=0):
         "form. creation ou edit utilisateur"
         # Get authuser info
         authuser = REQUEST.AUTHENTICATED_USER
         auth_name = str(authuser)
         authuser_info = self._user_list( args={'user_name':auth_name} )
         
         # Access control
         zope_roles = authuser.getRolesInContext(self)
         if not authuser_info and not ('Manager' in zope_roles) and not ('manage' in zope_roles):
             # not admin, and not in database
             raise AccessDenied('invalid user (%s)' % auth_name)
         if authuser_info:
             auth_dept = authuser_info[0]['dept']
         else:
             auth_dept = ''
         #
         edit = int(edit)
         H = [self.sco_header(REQUEST)]
         F = self.sco_footer(REQUEST)             
         if edit:
             if not user_name:
                 raise ValueError('missing argument: user_name')
             H.append("<h1>Modification d'un utilisateur</h1>")
         else:
             H.append("<h1>Cr�ation d'un utilisateur</h1>")

         if authuser.has_permission(ScoSuperAdmin,self):
             H.append("<p>Vous �tes super administrateur !</p>")
         
         # Noms de roles pouvant etre attribues aux utilisateurs via ce dialogue
         # si pas SuperAdmin, restreint aux r�les EnsX, SecrX, DeptX
         # 
         if authuser.has_permission(ScoSuperAdmin,self):
             log('create_user_form called by %s (super admin)' %(auth_name, ))
             editable_roles = Set(self._all_roles())
         else:
             editable_roles = Set(self.DeptUsersRoles())
         #log('create_user_form: editable_roles=%s' % editable_roles)
         #         
         if not edit:
             initvalues = {}
             submitlabel = 'Cr�er utilisateur'
             orig_roles = Set()
         else:
             submitlabel = 'Modifier utilisateur'
             initvalues = self._user_list( args={'user_name': user_name})[0]
             initvalues['roles'] = initvalues['roles'].split(',')
             orig_roles = Set(initvalues['roles'])
         # add existing user roles
         displayed_roles = list(editable_roles.union(orig_roles))
         displayed_roles.sort()
         disabled_roles = {} # pour desactiver les role que l'on ne peut pas editer
         for i in range(len(displayed_roles)):
             if displayed_roles[i] not in editable_roles:
                 disabled_roles[i] = True
         
         #log('create_user_form: displayed_roles=%s' % displayed_roles)
         
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
                 ('user_name', {'input_type':'hidden', 'default' : initvalues['user_name'] }),
                 ('user_id', {'input_type':'hidden', 'default' : initvalues['user_id'] })
                 ]
         descr += [
             ('email', { 'title' : 'e-mail',
                         'input_type' : 'text',
                         'explanation' : "vivement recommand�: utilis� pour contacter l'utilisateur",
                         'size' : 20, 'allow_null' : True }),
             ]
         
         if not auth_dept:
             # si auth n'a pas de departement (admin global)
             # propose de choisir le dept du nouvel utilisateur
             # sinon, il sera cr�� dans le m�me d�partement que auth
             descr.append(('dept',
                          { 'title' : 'D�partement',
                            'input_type' : 'text',
                            'size' : 12,
                            'allow_null' : True,
                            'explanation' : """d�partement d\'appartenance de l\'utilisateur (s'il s'agit d'un administrateur, laisser vide si vous voulez qu'il puisse cr�er des utilisateurs dans d'autres d�partements)"""
                            }))
             can_choose_dept = True
         else:
             can_choose_dept = False
             descr.append(('d', {'input_type' : 'separator',
                                'title' : 'L\'utilisateur  sera cr�e dans le d�partement %s' % auth_dept}))
         
         descr += [
             ('roles', {'title' : 'R�les', 'input_type' : 'checkbox', 'vertical' : True,
                        'allowed_values' : displayed_roles, 
                        'disabled_items' : disabled_roles,
                        }),
             
             ('force', {'title' : 'Ignorer les avertissements', 'input_type' : 'checkbox',
                        'explanation' : 'passer outre les avertissements (homonymes, etc)',
                        'labels' : ('',), 'allowed_values' : ('1',)})
             ]

         if 'tf-submitted' in REQUEST.form and not 'roles' in REQUEST.form:
             REQUEST.form['roles'] = ''
         tf = TrivialFormulator( REQUEST.URL0, REQUEST.form, descr,
                                 initvalues = initvalues,
                                 submitlabel = submitlabel )
         if tf[0] == 0:             
             return '\n'.join(H) + '\n' + tf[1] + F
         elif tf[0] == -1:
             return REQUEST.RESPONSE.redirect( REQUEST.URL1 )
         else:
             vals = tf[2]
             roles = set(vals['roles']).intersection(editable_roles)
             if REQUEST.form.has_key('edit'):
                 edit = int(REQUEST.form['edit'])
             else:
                 edit = 0
             try:
                 force = int(vals['force'][0])
             except:
                 force = 0
             
             if edit:
                 user_name = initvalues['user_name']
             else:
                 user_name = vals['user_name']
             # ce login existe ?
             err = None
             users = self._user_list( args={'user_name':user_name} )  
             if edit and not users: # safety net, le user_name ne devrait pas changer
                 err = "identifiant %s inexistant" % user_name
             if not edit and users:
                 err = "identifiant %s d�j� utilis�" % user_name
             if err:
                 H.append(tf_error_message("""Erreur: %s""" % err))
                 return '\n'.join(H) + '\n' + tf[1] + F
             
             if not force:
                 ok, msg = self._check_modif_user(
                     edit, user_name=user_name,
                     nom=vals['nom'], prenom=vals['prenom'],
                     email=vals['email'], roles=vals['roles'] )
                 if not ok:
                     H.append(tf_error_message("""Attention: %s (vous pouvez forcer l'op�ration en cochant "<em>Ignorer les avertissements</em>")""" % msg))

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
                 for role in orig_roles:
                     if not role in editable_roles:
                         roles.add(role)

                 vals['roles'] = ','.join(roles)
                 
                 # ok, edit
                 log('sco_users: editing %s by %s' % (user_name, auth_name))
                 #log('sco_users: previous_values=%s' % initvalues)                 
                 #log('sco_users: new_values=%s' % vals)
                 self._user_edit(vals)
                 return REQUEST.RESPONSE.redirect( REQUEST.URL1 )
             else: # creation utilisateur
                 vals['roles'] = ','.join(vals['roles'])
                 # check passwords
                 if vals['passwd'] != vals['passwd2']:
                     msg = tf_error_message("""Les deux mots de passes ne correspondent pas !""")
                     return '\n'.join(H) + msg + '\n' + tf[1] + F
                 if not self._is_valid_passwd(vals['passwd']):
                     msg = tf_error_message("""Mot de passe trop simple, recommencez !""")
                     return '\n'.join(H) + msg + '\n' + tf[1] + F
                 if not can_choose_dept:
                     vals['dept'] = auth_dept
                 # ok, go
                 log('sco_users: new_user %s by %s' % (vals['user_name'], auth_name ))
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

    security.declareProtected(ScoUsersAdmin, 'import_users_form')
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
        help = """<p class="help">
        Lors de la creation des utilisateurs, les op�rations suivantes sont effectu�es:
        </p>
        <ol class="help">
        <li>v�rification des donn�es;</li>
        <li>g�n�ration d'un mot de passe al�toire pour chaque utilisateur;</li>
        <li>cr�ation de chaque utilisateur;</li>
        <li>envoi � chaque utilisateur de son <b>mot de passe initial par mail</b>.</li>
        </ol>"""
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
            return '\n'.join(H) + tf[1] + '</li></ol>' + help + F
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
            return '\n'.join(H) + help + F
    
    security.declareProtected(ScoUsersAdmin, 'import_users_generate_excel_sample')
    def import_users_generate_excel_sample(self, REQUEST):
        "une feuille excel pour importation utilisateurs"
        data = sco_import_users.generate_excel_sample()
        return sco_excel.sendExcelFile(REQUEST,data,'ImportUtilisateurs.xls')    
    
    security.declareProtected(ScoUsersAdmin, 'create_user')
    def create_user(self, args, REQUEST=None):
        "creation utilisateur zope"
        cnx = self.GetUsersDBConnexion()        
        passwd = args['passwd']
        args['passwd'] = 'undefined'
        if 'passwd2' in args:
            del args['passwd2']
        log('create_user: args=%s' % args) # log apres supr. du mot de passe !
        r = self._userEditor.create(cnx, args)
        self.get_userlist_cache().inval_cache() #>
        # call exUserFolder to set passwd
        args['password'] = passwd
        args['password_confirm'] = passwd
        args['roles'] = args['roles'].split(',')
        junk = self.acl_users.manage_editUser( args['user_name'], args )
        #log('create_user: junk=%s\n' % junk )
        if REQUEST:
            return REQUEST.RESPONSE.redirect( REQUEST.URL1 )

    security.declareProtected(ScoUsersAdmin, 'delete_user_form')
    def delete_user_form(self, REQUEST, user_name, dialog_confirmed=False):
        "delete user"
        authuser = REQUEST.AUTHENTICATED_USER
        if not self._can_handle_passwd(authuser, user_name):
            return self.sco_header(REQUEST, user_check=False)+"<p>Vous n'avez pas la permission de supprimer cet utilisateur</p>" + self.sco_footer(REQUEST)
        
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
        
    def list_users(self, dept, all=False,
                   format='html', with_links=True, 
                   REQUEST=None):
        "List users"
        authuser = REQUEST.AUTHENTICATED_USER
        if dept and not all:                        
            r = self.get_userlist(dept=dept)
            comm = '(dept. %s)' % dept
        else:
            r = self.get_userlist()
            comm = '(tous)'

        # -- Add some information and links:
        for u in r:
            # Can current user modify this user ?
            can_modify = self._can_handle_passwd(authuser,u['user_name'],allow_admindepts=True)
            
            # Add links
            if with_links and can_modify:
                target = 'userinfo?user_name=%(user_name)s' % u
                u['_user_name_target'] = target
                u['_nom_target'] = target
                u['_prenom_target'] = target
            
            # Hide passwd modification date (depending on rights wrt user)
            if not can_modify:
                u['date_modif_passwd'] = '(non visible)'
                
            # Add spaces between roles to ease line wrap
            if u['roles']:
                u['roles'] = ', '.join(u['roles'].split(','))

            # Convert dates to ISO if XML output
            if format=='xml' and u['date_modif_passwd'] != 'NA':
                u['date_modif_passwd'] = DateDMYtoISO(u['date_modif_passwd']) or ''
        
        title = 'Utilisateurs d�finis dans ScoDoc'
        tab = GenTable(
            rows = r,
            columns_ids = ('user_name', 'nom', 'prenom', 'email', 'dept', 'roles', 'date_modif_passwd', 'passwd_temp'),
            titles = {'user_name':'Login', 'nom':'Nom', 'prenom':'Pr�nom', 'email' : 'Mail',
                    'dept' : 'Dept.', 'roles' : 'R�les', 'date_modif_passwd' : 'Modif. mot de passe' , 'passwd_temp' : 'Temp.' },
            caption = title, page_title = 'title',
            html_title = """<h2>%d utilisateurs %s</h2>
            <p class="help">Cliquer sur un nom pour changer son mot de passe</p>""" % (len(r), comm),
            html_class = 'gt_table table_leftalign list_users',
            html_with_td_classes = True,
            html_sortable = True,
            base_url = '%s?all=%s' % (REQUEST.URL0, all),
            pdf_link=False, # table is too wide to fit in a paper page => disable pdf
            preferences=self.get_preferences()
            )
        
        return tab.make_page(self, format=format, with_html_headers=False, REQUEST=REQUEST)

    def get_userlist_cache(self):
        url = self.ScoURL()
        if CACHE_userlist.has_key(url):
            return CACHE_userlist[url]
        else:
            log('get_userlist_cache: new simpleCache')
            CACHE_userlist[url] = sco_cache.expiringCache(max_validity=60)
            return CACHE_userlist[url]

    security.declareProtected(ScoView, 'get_userlist')
    def get_userlist(self, dept=None):
        """Returns list of users.
        If dept, select users from this dept,
        else return all users.
        """
        cache = self.get_userlist_cache()
        r = cache.get(dept)
        if r != None:
            return r
        else:
            if dept != None:
                r = self._user_list( args={ 'dept' : dept } )
            else:
                r = self._user_list() # all users
            l = []
            for user in r:
                l.append(self.user_info(user=user))
            cache.set(dept, l)
            return l

    security.declareProtected(ScoView, 'get_userlist_xml')
    def get_userlist_xml(self, dept=None, start='', limit=25, REQUEST=None):
        """Returns XML list of users with name (nomplogin) starting with start.
        Used for forms auto-completion."""
        # log('get_userlist_xml: start="%s" (%s)' % (start, repr(start)) )
        userlist = self.get_userlist(dept=dept)
        
        start = suppression_diacritics(unicode(start, 'utf-8'))
        start = str(start).lower()        
        
        userlist = [ user for user in userlist if user['nomnoacc'].startswith(start) ]
        if REQUEST:
            REQUEST.RESPONSE.setHeader('Content-type', XML_MIMETYPE)
        doc = jaxml.XML_document( encoding=SCO_ENCODING )
        doc.results()
        for user in userlist[:limit]:
            doc._push()
            doc.rs(user['nomplogin'], id=user['user_id'], info='')
            doc._pop()
        return doc

    security.declareProtected(ScoView, 'get_user_name_from_nomplogin')
    def get_user_name_from_nomplogin(self, nomplogin):
        """Returns user_name (login) from nomplogin
        """
        m = re.match(r'.*\((.*)\)', nomplogin.strip() )
        if m:
            return m.group(1)
        else:
            return None

    security.declareProtected(ScoView, 'reset_password_form')
    def reset_password_form(self, user_name=None, dialog_confirmed=False, REQUEST=None):
        """Form to reset a password"""
        if not dialog_confirmed:
            return self.confirmDialog(
                """<h2>R�-initialiser le mot de passe de %s ?</h2>
<p>Le mot de passe de %s va �tre choisi au hasard et lui �tre envoy� par mail.
Il devra ensuite se connecter et le changer.
</p>
                """ % (user_name, user_name),
                parameters={'user_name':user_name}
                )
        self.reset_password(user_name=user_name, REQUEST=REQUEST)
        return REQUEST.RESPONSE.redirect( REQUEST.URL1 + '?head_message=mot%20de%20passe%20de%20' + user_name + '%20reinitialise' )
        
    security.declareProtected(ScoView, 'reset_password')
    def reset_password(self, user_name=None, REQUEST=None):
        """Reset a password:
        - set user's passwd_temp to 1
        - set roles to 'ScoReset'
        - generate a random password and mail it
        """
        authuser = REQUEST.AUTHENTICATED_USER
        auth_name = str(authuser)
        if not user_name:
            user_name = auth_name
        # Access control        
        if not self._can_handle_passwd(authuser, user_name):
            raise AccessDenied("vous n'avez pas la permission de changer ce mot de passe")
        log('reset_password: %s' % user_name)
        # Check that user has valid mail
        info = self.user_info(user_name=user_name)
        if not is_valid_mail(info['email']):
            raise Exception("pas de mail valide associ� � l'utilisateur")
        # Generate random password
        password = sco_import_users.generate_password()
        self.do_change_password(user_name, password)
        # Flag it as temporary:
        cnx = self.GetUsersDBConnexion()
        cursor = cnx.cursor()
        ui = { 'user_name' : user_name }
        cursor.execute("update sco_users set passwd_temp=1 where user_name='%(user_name)s'" % ui)

        # Send email
        info['passwd'] = password
        sco_import_users.mail_password(info, context=self, reset=True)

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


    

