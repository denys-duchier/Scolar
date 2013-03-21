# Zope User Folder for ScoDoc
# Adapte de l'Extensible User Folder
# simplifie pour les besoins de ScoDoc.
# Emmanuel Viennet 2013

#
# Extensible User Folder
#
# (C) Copyright 2000,2001 The Internet (Aust) Pty Ltd
# ACN: 082 081 472  ABN: 83 082 081 472
# All Rights Reserved
#
# THIS SOFTWARE IS PROVIDED BY THE AUTHOR AND CONTRIBUTORS ``AS IS'' AND
# ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE
# IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE
# ARE DISCLAIMED.  IN NO EVENT SHALL THE AUTHOR OR CONTRIBUTORS BE LIABLE
# FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL
# DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS
# OR SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION)
# HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT
# LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY
# OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF
# SUCH DAMAGE.
#
# Author: Andrew Milton <akm@theinternet.com.au>
# $Id: exUserFolder.py,v 1.93 2004/11/10 14:15:33 akm Exp $

##############################################################################
#
# Zope Public License (ZPL) Version 0.9.4
# ---------------------------------------
# 
# Copyright (c) Digital Creations.  All rights reserved.
# 
# Redistribution and use in source and binary forms, with or
# without modification, are permitted provided that the following
# conditions are met:
# 
# 1. Redistributions in source code must retain the above
#    copyright notice, this list of conditions, and the following
#    disclaimer.
# 
# 6. Redistributions of any form whatsoever must retain the
#    following acknowledgment:
# 
#      "This product includes software developed by Digital
#      Creations for use in the Z Object Publishing Environment
#      (http://www.zope.org/)."
# 
# Disclaimer
# 
#   THIS SOFTWARE IS PROVIDED BY DIGITAL CREATIONS ``AS IS'' AND
#   ANY EXPRESSED OR IMPLIED WARRANTIES, INCLUDING, BUT NOT
#   LIMITED TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND
#   FITNESS FOR A PARTICULAR PURPOSE ARE DISCLAIMED.  IN NO EVENT
#   SHALL DIGITAL CREATIONS OR ITS CONTRIBUTORS BE LIABLE FOR ANY
#   DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR
#   CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED TO,
#   PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF USE,
#   DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND
#   ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT
#   LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING
#   IN ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF
#   THE POSSIBILITY OF SUCH DAMAGE.
#
##############################################################################

# Portions Copyright (c) 2002 Nuxeo SARL <http://nuxeo.com>,
#          Copyright (c) 2002 Florent Guillaume <mailto:fg@nuxeo.com>.
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions are
# met:
#
# 1. Redistributions of source code must retain the above copyright
#    notice, this list of conditions and the following disclaimer.
#
# 2. Redistributions in binary form must reproduce the above copyright
#    notice, this list of conditions and the following disclaimer in
#    the documentation and/or other materials provided with the
#    distribution.
# 
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS
# IS" AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED
# TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A
# PARTICULAR PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT
# OWNER OR CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL,
# SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT
# LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF USE,
# DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON ANY
# THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT
# (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE
# OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.

import Globals, App.Undo, socket, os, string, sha, whrandom, sys, zLOG

from Globals import DTMLFile, PersistentMapping
from string import join,strip,split,lower,upper,find

from OFS.Folder import Folder
from OFS.CopySupport import CopyContainer

from base64 import decodestring, encodestring
from urllib import quote, unquote

from Acquisition import aq_base
from AccessControl import ClassSecurityInfo
from AccessControl.Role import RoleManager
from AccessControl.User import BasicUser, BasicUserFolder, readUserAccessFile
from AccessControl.PermissionRole import PermissionRole
from AccessControl.ZopeSecurityPolicy import _noroles
from OFS.DTMLMethod import DTMLMethod
from time import time
from OFS.ObjectManager import REPLACEABLE
from Persistence import Persistent

from PropertyEditor import *

from User import User, AnonUser
from UserCache.UserCache import GlobalUserCache, GlobalNegativeUserCache, GlobalAdvancedCookieCache, SessionExpiredException

from LoginRequiredMessages import LoginRequiredMessages

from AccessControl import Unauthorized



# If there is no NUG Product just define a dummy class
try:
	from Products.NuxUserGroups.UserFolderWithGroups import BasicGroupFolderMixin, _marker
except ImportError:
	class BasicGroupFolderMixin:
		pass
	_marker = None

# Little function to create temp usernames
def createTempName():
	t=time()
	t1=time()
	t2=time()
	t3 = 0.0
	t3 = (t + t1 + t2) / 3
	un = "Anonymous %.0f"%(t3)
	return(un)


manage_addexUserFolderForm=DTMLFile('dtml/manage_addexUserFolder', globals(), __name__='manage_addexUserFolderForm')



def manage_addexUserFolder(self, authId, propId, memberId,
						   cookie_mode=0, session_length=0,
						   not_session_length=0,
						   sessionTracking=None, idleTimeout=None,
						   REQUEST={}, groupId=None, cryptoId=None):
	""" """
	if hasattr(self.aq_base, 'acl_users'):
		return Globals.MessageDialog(self,REQUEST,
			title  ='Item Exists',
			message='This object already contains a User Folder',
			action ='%s/manage_main' % REQUEST['URL1'])
	ob=exUserFolder(authId, propId, memberId, groupId, cryptoId, cookie_mode,
					session_length, sessionTracking, idleTimeout,
					not_session_length)
			
	self._setObject('acl_users', ob, None, None, 0)
	self.__allow_groups__=self.acl_users
	ob=getattr(self, 'acl_users')
	ob.postInitialisation(REQUEST)

	if REQUEST:
		return self.manage_main(self, REQUEST)
	return ''

#
# Module level caches
#
XUFUserCache=GlobalUserCache()
XUFNotUserCache=GlobalNegativeUserCache()
XUFCookieCache=GlobalAdvancedCookieCache()

class exUserFolder(Folder,BasicUserFolder,BasicGroupFolderMixin,
				   CopyContainer):
	""" """

	# HACK! We use this meta_type internally so we can be pasted into
	# the root. We registered with 'exUserFolder' meta_type however, so
	# our constructors work.
	meta_type='User Folder'
	id       ='acl_users'
	title    ='Extensible User Folder'
	icon     ='misc_/exUserFolder/exUserFolder.gif'

	isPrincipiaFolderish=1
	isAUserFolder=1
	__allow_access_to_unprotected_subobjects__=1
	authSources={}
	propSources={}
	cryptoSources={}
	membershipSources={}
	groupSources={} # UNUSED by ScoDoc

	manage_options=(
		{'label':'Users',      'action':'manage_main'},
		{'label':'Groups',	   'action':'manage_userGroups'},
		{'label':'Parameters', 'action':'manage_editexUserFolderForm'},
		{'label':'Authentication Source','action':'manage_editAuthSourceForm'},
		{'label':'Properties Source','action':'manage_editPropSourceForm'},
		{'label':'Membership Source', 'action':'manage_editMembershipSourceForm'},
		{'label':'Cache Data', 'action':'manage_showCacheData'},
		{'label':'Security',   'action':'manage_access'},
		{'label':'Contents',   'action':'manage_contents'},
		{'label':'Ownership',  'action':'manage_owner'},
		{'label':'Undo',       'action':'manage_UndoForm'},
		)

	__ac_permissions__=(
		('View management screens', ('manage','manage_menu','manage_main',
									 'manage_copyright', 'manage_tabs',
									 'manage_properties', 'manage_UndoForm',
									 'manage_edit', 'manage_contents',
									 'manage_cutObjects','manage_copyObjects',
									 'manage_pasteObjects',
									 'manage_renameForm',
									 'manage_renameObject',
									 'manage_renameObjects', ),
		 ('Manager',)),
		
		('Undo changes',            ('manage_undo_transactions',),
		 ('Manager',)),
		
		('Change permissions',      ('manage_access',),
		 ('Manager',)),
		
		('Manage users',            ('manage_users', 'manage_editUserForm',
									 'manage_editUser', 'manage_addUserForm',
									 'manage_addUser', 'manage_userActions',
									 'userFolderAddGroup',
									 'userFolderDelGroups',
									 'getGroupNames',
					                                 'getGroupById',
								         'manage_userGroups',
									 'manage_addGroup',
									 'manage_showGroup',),
		 ('Manager',)),
		
		('Change exUser Folders',   ('manage_edit',),
		 ('Manager',)),
		
		('View',                    ('manage_changePassword',
									 'manage_forgotPassword', 'docLogin','docLoginRedirect',
									 'docLogout', 'logout', 'DialogHeader',
									 'DialogFooter', 'manage_signupUser',
									 'MessageDialog', 'redirectToLogin','manage_changeProps'),
		 ('Anonymous', 'Authenticated', 'Manager')),
		
		('Manage properties',       ('manage_addProperty',
									 'manage_editProperties',
									 'manage_delProperties',
									 'manage_changeProperties',
									 'manage_propertiesForm',
									 'manage_propertyTypeForm',
									 'manage_changePropertyTypes',
									 ),
		 ('Manager',)),
		('Access contents information', ('hasProperty', 'propertyIds',
										 'propertyValues','propertyItems',
										 'getProperty', 'getPropertyType',
										 'propertyMap', 'docLogin','docLoginRedirect',
										 'DialogHeader', 'DialogFooter',
										 'MessageDialog', 'redirectToLogin',),
		 ('Anonymous', 'Authenticated', 'Manager')),
		)
	manage_access=DTMLFile('dtml/access',globals())
	manage_tabs=DTMLFile('common/manage_tabs',globals())
	manage_properties=DTMLFile('dtml/properties', globals())
	manage_main=DTMLFile('dtml/mainUser', globals())
	manage_contents=Folder.manage_main
	manage_showCacheData=DTMLFile('dtml/manage_showCacheData', globals())

	# This is going away soon...
	docLoginRedirect=DTMLFile('dtml/docLoginRedirect', globals())	

	# Stupid crap
	try:
		manage_contents._setName('manage_contents')
	except AttributeError:
		pass


	MessageDialog=DTMLFile('common/MessageDialog', globals())
	MessageDialog.__replaceable__ = REPLACEABLE
	
	manage_addUserForm=DTMLFile('dtml/manage_addUserForm',globals())
	manage_editUserForm=DTMLFile('dtml/manage_editUserForm',globals())

	DialogHeader__roles__=()
	DialogHeader=DTMLFile('common/DialogHeader',globals())
	DialogFooter__roles__=()
	DialogFooter=DTMLFile('common/DialogFooter',globals())

	manage_editAuthSourceForm=DTMLFile('dtml/manage_editAuthSourceForm',globals())
	manage_editPropSourceForm=DTMLFile('dtml/manage_editPropSourceForm',globals())
	manage_editMembershipSourceForm=DTMLFile('dtml/manage_editMembershipSourceForm', globals())

	manage_addPropertyForm=DTMLFile('dtml/manage_addPropertyForm', globals())
	manage_createPropertyForm=DTMLFile('dtml/manage_createPropertyForm', globals())
	manage_editUserPropertyForm=DTMLFile('dtml/manage_editUserPropertyForm', globals())

	manage_editexUserFolderForm=DTMLFile('dtml/manage_editexUserFolderForm', globals())

	manage_userGroups=DTMLFile('dtml/mainGroup',globals())


	# Use pages from NUG if it's there, otherwise no group support
	try:
		manage_addGroup = BasicGroupFolderMixin.manage_addGroup
		manage_showGroup = BasicGroupFolderMixin.manage_showGroup
	except:
		manage_addGroup = None
		manage_showGroup = None

	# No more class globals
	
	# sessionLength=0 # Upgrading users should get no caching.
	# notSessionLength=0 # bad cache limit
	# cookie_mode=0
	# sessionTracking=None # Or session tracking.
	# idleTimeout=0
	
	def __init__(self, authId, propId, memberId, groupId, cryptoId,
				 cookie_mode=0, session_length=0, sessionTracking=None,
				 idleTimeout=0, not_session_length=0):
		self.cookie_mode=cookie_mode
		self.sessionLength=session_length
		self.notSessionLength=not_session_length
		self.sessionTracking=sessionTracking
		self.idleTimeout=idleTimeout
		
		_docLogin=DTMLFile('dtml/docLogin',globals())
		_docLogout=DTMLFile('dtml/docLogout',globals())

		docLogin=DTMLMethod(__name__='docLogin')
		docLogin.manage_edit(data=_docLogin, title='Login Page')
		self._setObject('docLogin', docLogin, None, None, 0)

		docLogout=DTMLMethod(__name__='docLogout')
		docLogout.manage_edit(data=_docLogout, title='Logout Page')
		self._setObject('docLogout', docLogout, None, None, 0)

		postUserCreate=DTMLMethod(__name__='postUserCreate')
		postUserCreate.manage_edit(data=_postUserCreate, title='Post User Creation methods')
		self._setObject('postUserCreate', postUserCreate, None, None, 0)

		self.manage_addAuthSource=self.authSources[authId].manage_addMethod
		self.manage_addPropSource=self.propSources[propId].manage_addMethod
		self.manage_addMembershipSource=self.membershipSources[memberId].manage_addMethod

		self.manage_addGroupSource=None # UNUSED by ScoDoc
		self.currentGroupsSource=None

		if cryptoId:
			self.cryptoId = cryptoId
		else:
			self.cryptoId = 'Crypt'
			
	def __setstate__(self, state):
		Persistent.__setstate__(self, state)
		if not hasattr(self, 'currentGroupSource'):
			self.currentGroupSource = None
		if not hasattr(self, 'sessionLength'):
			self.sessionLength = 0
		if not hasattr(self, 'notSessionLength'):
			self.notSessionLength = 0
		if not hasattr(self, 'cookie_mode'):
			self.cookie_mode = 0
		if not hasattr(self, 'sessionTraining'):
			self.sessionTracking = None
		if not hasattr(self, 'idleTimeout'):
			self.idleTimeout=0

	def manage_beforeDelete(self, item, container):
		zLOG.LOG("exUserFolder", zLOG.BLATHER, "Attempting to delete an exUserFolder instance")
		if item is self:
			try:
				self.cache_deleteCache()
				self.xcache_deleteCache()
				zLOG.LOG("exUserFolder", zLOG.BLATHER, "-- Caches deleted")
			except:
				#pass
				zLOG.LOG("exUserFolder", zLOG.BLATHER, "-- Cache deletion failed")

			try:
				del container.__allow_groups__
				zLOG.LOG("exUserFolder", zLOG.BLATHER, "-- container.__allow_groups_ deleted")
			except:
				#pass
				zLOG.LOG("exUserFolder", zLOG.BLATHER, "-- container.__allow_groups_ deletion failed")


	def manage_afterAdd(self, item, container):
		zLOG.LOG("exUserFolder", zLOG.BLATHER, "Adding an exUserFolder")
                         
		if item is self:
			if hasattr(self, 'aq_base'): self=self.aq_base
			container.__allow_groups__=self

	def manage_editPropSource(self, REQUEST):
		""" Edit Prop Source """
		if self.currentPropSource:
			self.currentPropSource.manage_editPropSource(REQUEST)
		return self.manage_main(self, REQUEST)

	def manage_editAuthSource(self, REQUEST):
		""" Edit Auth Source """
		self.currentAuthSource.manage_editAuthSource(REQUEST)
		return self.manage_main(self, REQUEST)

	def manage_editMembershipSource(self, REQUEST):
		""" Edit Membership Source """
		if self.currentMembershipSource:
			return self.currentMembershipSource.manage_editMembershipSource(REQUEST)

	def postInitialisation(self, REQUEST):
		self.manage_addAuthSource(self=self,REQUEST=REQUEST)
		self.manage_addPropSource(self=self,REQUEST=REQUEST)
		self.manage_addMembershipSource(self=self,REQUEST=REQUEST)
		self.currentGroupSource = None
	
	def addAuthSource(self, REQUEST={}):
		return self.manage_addAuthSourceForm(self, REQUEST)

	def addPropSource(self, REQUEST={}):
		return self.manage_addPropSourceForm(self, REQUEST)

	def addMembershipSource(self, REQUEST={}):
		return self.manage_editMembershipSourceForm(self, REQUEST)

	def listUserProperties(self, username):
		if self.currentPropSource:
			return self.currentPropSource.listUserProperties(username=username)

	def getUserProperty(self, username, key):
		if self.currentPropSource:
			return self.currentPropSource.getUserProperty(key=key, username=username)
	
	def reqattr(self, request, attr, default=None):
		try:    return request[attr]
		except: return default

	def getAuthFailedMessage(self, code):
		""" Return a code """
		if LoginRequiredMessages.has_key(code):
			return LoginRequiredMessages[code]
		return 'Login Required'

	# Called when we are deleted
	def cache_deleteCache(self):
		pp = string.join(self.getPhysicalPath(), '/')
		XUFUserCache.deleteCache(pp)
		
	def cache_addToCache(self, username, password, user):
		if not self.sessionLength:
			return
		# fix by emmanuel
		if username == self._emergency_user.getUserName():
			return
		# /fix
		pp = string.join(self.getPhysicalPath(), '/')
		x = XUFUserCache.getCache(pp)
		if not x:
			x = XUFUserCache.createCache(pp, self.sessionLength)
		x.addToCache(username, password, user)

	def cache_getUser(self, username, password, checkpassword=1):
		if not self.sessionLength:
			return None
		pp = string.join(self.getPhysicalPath(), '/')
		x = XUFUserCache.getCache(pp)
		if not x:
			return None
		u = x.getUser(self, username, password, checkpassword)
		if u is not None:
			u = u.__of__(self)
		return u

	def cache_removeUser(self, username):
		if not self.sessionLength:
			return
		pp = string.join(self.getPhysicalPath(), '/')
		x = XUFUserCache.getCache(pp)
		if x:
			x.removeUser(username)

	def cache_getCacheStats(self):
		pp = string.join(self.getPhysicalPath(), '/')
		x = XUFUserCache.getCache(pp)
		if not x:
			x = XUFUserCache.createCache(pp, self.sessionLength)			
		if x:
			return x.getCacheStats()

	def cache_getCurrentUsers(self):
		pp = string.join(self.getPhysicalPath(), '/')
		x = XUFUserCache.getCache(pp)
		if x:
			return x.getCurrentUsers(self)

	# negative cache functions
	def xcache_deleteCache(self):
		pp = string.join(self.getPhysicalPath(), '/')
		XUFNotUserCache.deleteCache(pp)
		
	def xcache_addToCache(self, username):
		if not self.notSessionLength:
			return
		pp = string.join(self.getPhysicalPath(), '/')
		x = XUFNotUserCache.getCache(pp)
		if not x:
			x = XUFNotUserCache.createCache(pp, self.notSessionLength)
		x.addToCache(username)

	def xcache_getUser(self, username):
		if not self.notSessionLength:
			return None
		pp = string.join(self.getPhysicalPath(), '/')
		x = XUFNotUserCache.getCache(pp)
		if not x:
			return None
		return x.getUser(username)

	def xcache_removeUser(self, username):
		if not self.notSessionLength:
			return
		pp = string.join(self.getPhysicalPath(), '/')
		x = XUFNotUserCache.getCache(pp)
		if x:
			x.removeUser(username)

	# Cookie Cache Functions
	def cache_deleteCookieCache(self):
		pp = string.join(self.getPhysicalPath(), '/')
		XUFCookieCache.deleteCache(pp)

	def cache_addToCookieCache(self, username, password, key):
		pp = string.join(self.getPhysicalPath(), '/')
		c = XUFCookieCache.getCache(pp)
		if not c:
			c = XUFCookieCache.createCache(pp, 86400)
		c.addToCache(username, password, key)

	def cache_getCookieCacheUser(self, key):
		pp = string.join(self.getPhysicalPath(), '/')
		c = XUFCookieCache.getCache(pp)
		if not c:
			return None
		return c.getUser(key)

	def cache_removeCookieCacheUser(self, key):
		pp = string.join(self.getPhysicalPath(), '/')
		c = XUFCookieCache.getCache(pp)
		if c:
			c.removeUser(key)
    
	def manage_editUser(self, username, REQUEST={}): # UNUSED by ScoDoc
 		""" Edit a User """
		# username=self.reqattr(REQUEST,'username')
		password=self.reqattr(REQUEST,'password')
		password_confirm=self.reqattr(REQUEST,'password_confirm')
		roles=self.reqattr(REQUEST,'roles', [])
		groups=self.reqattr(REQUEST, 'groupnames', [])
        
		if not username:
			return self.MessageDialog(self,REQUEST=REQUEST,
				title  ='Illegal value', 
				message='A username must be specified',
				action ='manage_main')

		if (password or password_confirm) and (password != password_confirm):
			return self.MessageDialog(self,REQUEST=REQUEST,
				title  ='Illegal value', 
				message='Password and confirmation do not match',
				action ='manage_main')
		
		self._doChangeUser(username, password, roles, domains='', groups=groups, REQUEST=REQUEST)
		
		return self.MessageDialog(self,REQUEST=REQUEST,
			title = 'User Updated',
			message= 'User %s was updated.'%(username),
			action = 'manage_main')
    
    
    # Methode special pour ScoDoc: evite le code inutile dans notre contexte
    # et accede a la BD via le curseur psycopg2 fournie
    # (facilitera la separation de Zope)
	def scodoc_editUser(self, cursor, username, password=None, roles=[]):
		"""Edit a ScoDoc user"""
		roles = list(roles)
		rolestring= ','.join(roles)
		# Don't change passwords if it's null
		if password:
			secret=self.cryptPassword(username, password)
			# Update just the password:			   
			# self.sqlUpdateUserPassword(username=username, password=secret)
			cursor.execute("UPDATE sco_users SET passwd=%(secret)s WHERE user_name=%(username)s",
						   { 'secret':secret, 'username': username } )
		
		#self.sqlUpdateUser(username=username, roles=rolestring)
		cursor.execute("UPDATE sco_users SET roles=%(rolestring)s WHERE user_name=%(username)s",
					   { 'rolestring':rolestring, 'username': username } )
		
		self._v_lastUser={} # ? zope/exUserFolder specific		   
		
		# We may have updated roles or passwords... flush the user...
		self.cache_removeUser(username)
		self.xcache_removeUser(username)
    
	#
	# Membership helper
	#
	def goHome(self, REQUEST, RESPONSE):
		""" Go to home directory """
		if self.currentMembershipSource:
			self.currentMembershipSource.goHome(REQUEST, RESPONSE)


	# 
	# Membership method of changing user properties
	# 

	def manage_changeProps(self, REQUEST):
		""" Change Properties """
		if self.currentMembershipSource:
			return self.currentMembershipSource.changeProperties(REQUEST)
		else:
			
			return self.MessageDialog(self,REQUEST,
				title = 'This is a test',
				message= 'This was a test',
				action = '..')
 

	#
	# Membership method of adding a new user.
	# If everything goes well the membership plugin calls manage_addUser()
	#
	
	def manage_signupUser(self, REQUEST):
		""" Signup a new user """
		""" This is seperate so you can add users using the normal """
		""" interface w/o going through membership policy """

		username=self.reqattr(REQUEST,'username')
		roles=self.reqattr(REQUEST,'roles')

		if not username:
			return self.MessageDialog(self,REQUEST=REQUEST,
				title  ='Illegal value', 
				message='A username must be specified',
				action ='manage_main')

		if (self.getUser(username) or
			(self._emergency_user and
			 username == self._emergency_user.getUserName())):
			return self.MessageDialog(self,REQUEST=REQUEST,
				title  ='Illegal value', 
				message='A user with the specified name already exists',
				action ='manage_main')

		if self.currentMembershipSource:
			return self.currentMembershipSource.createUser(REQUEST)

	#
	# Membership method of changing passwords
	#
	def manage_changePassword(self, REQUEST):
		""" Change a password """
		if self.currentMembershipSource:
			return self.currentMembershipSource.changePassword(REQUEST)
		
	#
	# User says they can't remember their password
	#
	def manage_forgotPassword(self, REQUEST):
		""" So something about forgetting your password """
		if self.currentMembershipSource:
			return self.currentMembershipSource.forgotPassword(REQUEST)
		
	def __creatable_by_emergency_user__(self): return 1

	def manage_addUser(self, REQUEST):
		""" Add a New User """
		username=self.reqattr(REQUEST,'username')
		password=self.reqattr(REQUEST,'password')
		password_confirm=self.reqattr(REQUEST,'password_confirm')
		roles=self.reqattr(REQUEST,'roles')
		groups=self.reqattr(REQUEST, 'groupnames', [])

		if not username:
			return self.MessageDialog(self,REQUEST=REQUEST,
				title  ='Illegal value', 
				message='A username must be specified',
				action ='manage_main')

		if not password or not password_confirm:
			return self.MessageDialog(self,REQUEST=REQUEST,
				title  ='Illegal value', 
				message='Password and confirmation must be specified',
				action ='manage_main')

		if (self.getUser(username) or
			(self._emergency_user and
			 username == self._emergency_user.getUserName())):
			return self.MessageDialog(self,REQUEST=REQUEST,
				title  ='Illegal value', 
				message='A user with the specified name already exists',
				action ='manage_main')

		if (password or password_confirm) and (password != password_confirm):
			return self.MessageDialog(self,REQUEST=REQUEST,
				title  ='Illegal value', 
				message='Password and confirmation do not match',
				action ='manage_main')

		self._doAddUser(username, password, roles, domains='', groups=groups, REQUEST=REQUEST)
		#
		# Explicitly check our contents, do not just acquire postUserCreate
		#
		if 'postUserCreate' in self.objectIds():
			self.postUserCreate(self, REQUEST)
		
		return self.MessageDialog(self,REQUEST=REQUEST,
			title = 'User Created',
			message= 'User %s was created.'%(username),
			action = 'manage_main')

	def _doAddUser(self, name, password, roles, domains='', groups=(), **kw):
		""" For programatically adding simple users """
		self.currentAuthSource.createUser(name, password, roles)
		if self.currentPropSource:
			# copy items not in kw from REQUEST
			REQUEST = kw.get('REQUEST', self.REQUEST)
			map(kw.setdefault, REQUEST.keys(), REQUEST.values())
			self.currentPropSource.createUser(name, kw)

	def _doChangeUser(self, name, password, roles, domains='', groups=(), **kw):
		self.currentAuthSource.updateUser(name, password, roles)
		if self.currentPropSource:
			# copy items not in kw from REQUEST
			REQUEST = kw.get('REQUEST', self.REQUEST)
			map(kw.setdefault, REQUEST.keys(), REQUEST.values())
			self.currentPropSource.updateUser(name, kw)
		# We may have updated roles or passwords... flush the user...
		self.cache_removeUser(name)
		self.xcache_removeUser(name)
		
	def _doDelUsers(self, names):
		self.deleteUsers(names)

	def _createInitialUser(self):
		if len(self.getUserNames()) <= 1:
			info = readUserAccessFile('inituser')
			if info:
				name, password, domains, remote_user_mode = info
				self._doAddUser(name, password, ('Manager',), domains)


	def getUsers(self):
		"""Return a list of user objects or [] if no users exist"""
		data=[]
		try:
			items=self.listUsers()
			for people in items:
				user=User({'name':		people['username'],
						   'password':	people['password'],
						   'roles':		people['roles'], 
						   'domains':	''},
						  self.currentPropSource,
						  self.cryptPassword,
						  self.currentAuthSource,
						  self.currentGroupSource)
				data.append(user)
		except:
			import traceback
			traceback.print_exc()
			pass
			
		return data

	getUsers__roles__=('Anonymous','Authenticated')
	
	def getUser(self, name):
		"""Return the named user object or None if no such user exists"""
		user = self.cache_getUser(name, '', 0)
		if user:
			return user
		try:
			items=self.listOneUser(name)
		except:
			zLOG.LOG("exUserFolder", zLOG.ERROR,
                                 "error trying to list user %s" % name,
                                 '',
                                 sys.exc_info())
			return None

		if not items:
			return None
		
		for people in items:
			user =  User({'name':    people['username'],
						  'password':people['password'],
						  'roles':   people['roles'],
						  'domains':	''},
						 self.currentPropSource,
						 self.cryptPassword,
						 self.currentAuthSource,
						 self.currentGroupSource)
			return user
		return None
		
	def manage_userActions(self, submit=None, userids=None, REQUEST={}):
		""" Do things to users """
		if submit==' Add ':
			if hasattr(self.currentAuthSource,'manage_addUserForm'):
				return self.currentAuthSource.manage_addUserForm(self, REQUEST)
			else:
				return self.manage_addUserForm(self, REQUEST)
		if submit==' Delete ':
			self.deleteUsers(userids)
			return self.MessageDialog(self,REQUEST=REQUEST,
				title  ='Users Deleted',
				message='Selected Users have been deleted',
				action =REQUEST['URL1']+'/manage_main',
				target ='manage_main')

		if REQUEST:
			return self.manage_main(self,REQUEST)
		return ''

	def identify(self, auth):
		# Identify the username and password.  This is where new modes should
		# be called from, and if pluggable modes ever take shape, here ya go!

		if self.cookie_mode and not auth:
			# The identify signature does not include the request, sadly.
			# I think that's dumb.
			request = self.REQUEST
			response = request.RESPONSE
	
			if request.has_key('__ac_name') and request.has_key('__ac_password'):
				return request['__ac_name'], request['__ac_password']
			elif request.has_key('__ac') and self.cookie_mode == 1:
				return self.decodeBasicCookie(request, response)
			elif request.has_key('__aca') and self.cookie_mode == 2:
				return self.decodeAdvancedCookie(request, response)

		if auth and lower(auth[:6]) == 'basic ':
				return tuple(split(decodestring(split(auth)[-1]), ':', 1))

		return None, None

	def decodeUserCookie(self, request, response):
		return self.identify('')

	def validate(self, request, auth='', roles=_noroles):
		"""
		Perform identification, authentication, and authorization.
		"""

		v = request['PUBLISHED']
		a, c, n, v = self._getobcontext(v, request)

		name, password = self.identify(auth)
		zLOG.LOG('exUserFolder', zLOG.DEBUG, 'identify returned %s, %s' % (name, password))

		response = request.RESPONSE
		if name is not None:
			try:
				xcached_user = self.xcache_getUser(name)
				if xcached_user:
					return None
			except:
				zLOG.LOG('exUserFolder', zLOG.ERROR,
						 "error while looking up '%s' on the xcache" % name,
						 '',
						 sys.exc_info())

			user = self.authenticate(name, password, request)
			if user is None:
				# If it's none, because there's no user by that name,
				# don't raise a login, allow it to go higher...
				# This kinda breaks for people putting in the wrong username
				# when the Folder above uses a different auth method.
				# But it doesn't lock Manager users out inside Zope.
				# Perhaps this should be a tunable.

				# modified by Emmanuel
				try:
					lou = self.listOneUser(name) 
				except:
					lou = None
				if lou:
					self.challenge(request, response, 'login_failed', auth)
				return None
			self.remember(name, password, request)
			self.cache_addToCache(name, password, user)
			emergency = self._emergency_user
			if emergency and user is emergency:
				if self._isTop():
					return emergency.__of__(self)
				else:
					return None
			if self.authorize(user, a, c, n, v, roles):
				return user.__of__(self)
			if self._isTop() and self.authorize(self._nobody, a, c, n, v, roles):
				return self._nobody.__of__(self)
			self.challenge(request, response, 'unauthorized')
			return None
		else:
			if self.sessionTracking and self.currentPropSource:
				user = self.createAnonymousUser(request, response)
				if self.authorize(user, a, c, n, v, roles):
					return user.__of__(self)
			if self.authorize(self._nobody, a, c, n, v, roles):
				if self._isTop():
					return self._nobody.__of__(self)
				else:
					return None
			else:
				self.challenge(request, response, None, auth)
				return None
	
	def authenticate(self, name, password, request):
		emergency = self._emergency_user
		if emergency and name == emergency.getUserName():
			return emergency
		try:
			user = self.cache_getUser(name, password)
			if user:
				return user
		except SessionExpiredException:
			if self.idleTimeout:
				self.logout(request)
				self.challenge(request, request.RESPONSE, 'session_expired')
				return None
		user = self.getUser(name)
		if user is not None:
			if user.authenticate(self.currentAuthSource.listOneUser,
								 password,
								 request,
								 self.currentAuthSource.remoteAuthMethod):
				return user
		return None

	def challenge(self, request, response, reason_code='unauthorized',
				  auth=''):
		# Give whatever mode we're in a chance to challenge the validation
		# failure.  We do this to preserve LoginRequired behavior.  The
		# other thing we could do is let the None propagate on up and patch
		# the request's unauthorized method to 

		if self.cookie_mode and not auth:
			zLOG.LOG('exUserFolder', zLOG.DEBUG, 'raising LoginRequired for %s' % reason_code)
			if reason_code == 'login_failed':
				response.expireCookie('__ac', path='/')
				response.expireCookie('__aca', path='/')
			if reason_code:
				request.set('authFailedCode', reason_code)
			raise 'LoginRequired', self.docLogin(self, request)
		else:
			zLOG.LOG('exUserFolder', zLOG.DEBUG, 'not raising LoginRequired for %s' % reason_code)

	def remember(self, name, password, request):
		response = request.RESPONSE
		if self.cookie_mode == 1:
			self.setBasicCookie(name, password, request, response)
		elif self.cookie_mode == 2:
			self.setAdvancedCookie(name, password, request, response)

		if self.cookie_mode:
			try:
				del request.form['__ac_name']
				del request.form['__ac_password']
			except KeyError:
				pass

	def makeRedirectPath(self):
		REQUEST=self.REQUEST
		if not REQUEST.has_key('destination'):
			script=REQUEST['SCRIPT_NAME']
			pathinfo=REQUEST['PATH_INFO']
			redirectstring=script+pathinfo
			if REQUEST.has_key('QUERY_STRING'):
				querystring='?'+quote(REQUEST['QUERY_STRING'])
				redirectstring=redirectstring+querystring

			REQUEST['destination']=redirectstring
		
	def redirectToLogin(self, REQUEST):
		""" Allow methods to call from Web """
		script=''
		pathinfo=''
		querystring=''
		redirectstring=''
		authFailedCode=''
		
		if not REQUEST.has_key('destination'):
			if self.currentMembershipSource:
				redirectstring = self.currentMembershipSource.getLoginDestination(REQUEST)
			else:
				script=REQUEST['SCRIPT_NAME']
				pathinfo=REQUEST['PATH_INFO']
				redirectstring=script+pathinfo
				if REQUEST.has_key('QUERY_STRING'):
					querystring='?'+REQUEST['QUERY_STRING']
					redirectstring=redirectstring+querystring

			REQUEST['destination']=redirectstring

		
		if REQUEST.has_key('authFailedCode'):
			authFailedCode='&authFailedCode='+REQUEST['authFailedCode']
		
			
			
		if self.currentMembershipSource and self.currentMembershipSource.loginPage:
			try:
				REQUEST.RESPONSE.redirect('%s/%s?destination=%s%s'%(self.currentMembershipSource.baseURL, self.currentMembershipSource.loginPage,REQUEST['destination'],authFailedCode))				
				return
			except:
				pass
		return self.docLogin(self,REQUEST)

	def decodeBasicCookie(self, request, response):
		c=request['__ac']
		c=unquote(c)
		try:
			c=decodestring(c)
		except:
			response.expireCookie('__ac', path='/')
			raise 'LoginRequired', self.docLogin(self, request)
		
		name,password=tuple(split(c, ':', 1))
		return name, password
		
	def decodeAdvancedCookie(self, request, response):
		c = ''
		try:
			c = request['__aca']
			c = unquote(c)
		except:
			response.expireCookie('__aca', path='/')
			response.expireCookie('__ac', path='/')	# Precaution
			response.flush()
			raise 'LoginRequired', self.docLogin(self, request)

		u = self.cache_getCookieCacheUser(c)
		if u:
			return u

		response.expireCookie('__aca', path='/')
		response.expireCookie('__ac', path='/')	# Precaution
		response.flush()
		raise 'LoginRequired', self.docLogin(self, request)

	def setBasicCookie(self, name, password, request, response):
		token='%s:%s' % (name, password)
		token=encodestring(token)
		token=quote(token)
		response.setCookie('__ac', token, path='/')
		request['__ac']=token
		
	def setAdvancedCookie(self, name, password, request, response):
		xufid = self._p_oid
		hash = encodestring(sha.new('%s%s%f%f%s'%(
			name, password, time(), whrandom.random(), str(request))).digest())
		token=quote(hash)
		response.setCookie('__aca', token, path='/')
		response.flush()
		request['__aca']=token
		self.cache_addToCookieCache(name, password, hash)
		
	def setAnonCookie(self, name, request, resp):
		token='%s:%s' % (name, '')
		token=encodestring(token)
		token=quote(token)
		resp.setCookie('__ac', token, path='/')
		request['__ac']=token

	def createAnonymousUser(self, request, resp):
		aName=createTempName()
		bogusREQUEST={}
		bogusREQUEST['user_realname']='Guest User'
		self.currentPropSource.createUser(aName, bogusREQUEST)
		ob = AnonUser(aName, [], self.currentPropSource)
		ob = ob.__of__(self)
		self.cache_addToCache(aName, '', ob)			
		self.setAnonCookie(aName, request, resp)
		return ob
		
	def manage_edit(self, cookie_mode, session_length, sessionTracking=None,
					idleTimeout=0, not_session_length=0,
			                title=None,
					REQUEST=None):
		"""Change properties"""

		self.cookie_mode=cookie_mode
		self.sessionLength=session_length
		self.notSessionLength=not_session_length
		self.sessionTracking=sessionTracking
		self.idleTimeout=idleTimeout
		if title:
			self.title = title
		
		if REQUEST:
			return self.MessageDialog(self,REQUEST=REQUEST,
				title  ='exUserFolder Changed',
				message='exUserFolder properties have been updated',
				action =REQUEST['URL1']+'/manage_main',
				target ='manage_main')

	def logout(self, REQUEST):
		"""Logout"""
		try:
			self.cache_removeUser(REQUEST['AUTHENTICATED_USER'].getUserName())
		except:
			pass
		
		REQUEST['RESPONSE'].expireCookie('__ac', path='/')
		REQUEST.cookies['__ac']=''
		try:
			acc = REQUEST['__aca']
			self.cache_removeCookieCacheUser(acc)
			REQUEST.cookies['__aca']=''
		except:
			pass
		REQUEST['RESPONSE'].expireCookie('__aca', path='/')

		
		
		return self.docLogout(self, REQUEST)

	#
	# Methods to be supplied by Auth Source
	#
	def deleteUsers(self, userids):
		self.currentAuthSource.deleteUsers(userids)

		# Comment out to use Andreas' pgSchema
		if self.currentPropSource:
			self.currentPropSource.deleteUsers(userids)

		if self.currentGroupSource:
			self.currentGroupSource.deleteUsers(userids)
			

	def listUsers(self):
		return self.currentAuthSource.listUsers()

	def user_names(self):
		return self.currentAuthSource.listUserNames()
	
	def getUserNames(self):
		return self.currentAuthSource.listUserNames()

	def listOneUser(self,username):
		return self.currentAuthSource.listOneUser(username)

	def cryptPassword(self, username, password):
		if hasattr(aq_base(self.currentAuthSource), 'cryptPassword'):
			return self.currentAuthSource.cryptPassword(username, password)

		if hasattr(self, 'cryptoId'):
			return self.cryptoSources[self.cryptoId].plugin(self, username, password)
		return self.cryptoSources['Crypt'].plugin(self, username, password)

	def PropertyEditor(self):
		""" """
		if self.REQUEST.has_key(self.REQUEST['propName']):
			return PropertyEditor.EditMethods[self.REQUEST['propType']](self.REQUEST['propName'], self.REQUEST[self.REQUEST['propName']])
		return PropertyEditor.EditMethods[self.REQUEST['propType']](self.REQUEST['propName'], None)

	def PropertyView(self):
		""" """
		if self.REQUEST.has_key(self.REQUEST['propName']):
			return PropertyEditor.ViewMethods[self.REQUEST['propType']](self.REQUEST['propName'], self.REQUEST[self.REQUEST['propName']])
		return PropertyEditor.ViewMethods[self.REQUEST['propType']](self.REQUEST['propName'], None)

	def manage_addUserProperty(self, username, propName, propValue, REQUEST):
		""" add a new property """
		self.currentPropSource.setUserProperty(propName, username, propValue)
		if hasattr(self.currentAuthSource,'manage_editUserForm'):
			return self.currentAuthSource.manage_editUserForm(self, REQUEST)
		else:
			return self.manage_editUserForm(self,REQUEST)

	def getUserCacheStats(self):
		""" Stats """
		if self.sessionLength:
			if self.cache_getCacheStats()['attempts']:
				return self.cache_getCacheStats()
		return None

	def getUserCacheUsers(self):
		""" Current Users """
		if self.sessionLength:
			return self.cache_getCurrentUsers()
		return None

	def userFolderAddGroup(self, groupname, title='', **kw):
		"""Creates a group"""
		if self.currentGroupSource:
			apply(self.currentGroupSource.addGroup, (groupname, title), kw)
	
	def userFolderDelGroups(self, groupnames):
		"""Deletes groups"""
		if self.currentGroupSource:
			for groupname in groupnames:
				self.currentGroupSource.delGroup(groupname)

	def getGroupNames(self):
		"""Returns a list of group names"""
		if self.currentGroupSource:
			return self.currentGroupSource.listGroups()
		else:
			return []


	def getGroupById(self, groupname, default=_marker):
		"""Returns the given group"""
		if self.currentGroupSource:
			group = self.currentGroupSource.getGroup(groupname, default)
			if group:
				return group.__of__(self)
			else:
				return None

	def setUsersOfGroup(self, usernames, groupname):
		"""Sets the users of the group"""
		if self.currentGroupSource:
			return self.currentGroupSource.setUsersOfGroup(usernames, groupname)

	def addUsersToGroup(self, usernames, groupname):
		"""Adds users to a group"""
		if self.currentGroupSource:
			return self.currentGroupSource.addUsersToGroup(usernames, groupname)

	def delUsersFromGroup(self, usernames, groupname):
		"""Deletes users from a group"""
		if self.currentGroupSource:
			return self.currentGroupSource.delUsersFromGroup(usernames, groupname)

	def setGroupsOfUser(self, groupnames, username):
		"""Sets the groups of a user"""
		if self.currentGroupSource:
			return self.currentGroupSource.setGroupsOfUser(groupnames, username)

	def addGroupsOfUser(self, groupnames, username):
		"""Add groups to a user"""
		if self.currentGroupSource:
			return self.currentGroupSource.addGroupsToUser(groupnames, username)

	def delGroupsOfUser(self, groupnames, username):
		"""Deletes groups from a user"""
		if self.currentGroupSource:
			return self.currentGroupSource.delGroupsFromUser(groupnames, username)

	# We lie.
	def hasUsers(self):
		return 1


def doAuthSourceForm(self,authId):
	""" la de da """
	return exUserFolder.authSources[authId].manage_addForm

def doPropSourceForm(self,propId):
	""" la de da """
	return exUserFolder.propSources[propId].manage_addForm

def doMembershipSourceForm(self, memberId):
	""" doot de doo """
	return exUserFolder.membershipSources[memberId].manage_addForm

#def doGroupSourceForm(self,groupId):
#	""" la de da """
#	return exUserFolder.groupSources[groupId].manage_addForm

def getAuthSources(self):
	""" Hrm I need a docstring """
	l=[]
	for o in exUserFolder.authSources.keys():
		l.append(
			exUserFolder.authSources[o]
			)
	return l

def getPropSources(self):
	""" Hrm I need a docstring """
	l=[]
	for o in exUserFolder.propSources.keys():
		l.append(
			exUserFolder.propSources[o]
			)
	return l

def getMembershipSources(self):
	""" Hrm I need a docstring """
	l=[]
	for o in exUserFolder.membershipSources.keys():
		l.append(
			exUserFolder.membershipSources[o]
			)
	return l

def getGroupSources(self):
	""" Hrm I need a docstring """
	return [] # UNUSED by ScoDoc: empty

def getCryptoSources(self):
	""" Doc String """
	l = []
	for o in exUserFolder.cryptoSources.keys():
		l.append(
			exUserFolder.cryptoSources[o]
			)
	return l

def MailHostIDs(self):
    """Find SQL database connections in the current folder and above

    This function return a list of ids.
    """
    return [] # UNUSED BY SCODOC

from types import ListType, IntType, LongType, FloatType, NoneType, DictType, StringType

def getVariableType(self, o):

	if type(o) == ListType:
		return 'List'
	if type(o) == IntType:
		return 'Int'
	if type(o) == LongType:
		return 'Long'
	if type(o) == FloatType:
		return 'Float'
	if type(o) == NoneType:
		return 'None'
	if type(o) == DictType:
		return 'Dict'
	if type(o) == StringType:
		return 'String'
	return 'Unknown or Restricted'

_postUserCreate='''
<dtml-comment>
Replace this method with whatever you want to do
when a user is created, you can use a Python Script,
or External Method, or keep it as a DTML Method if you
want to
</dtml-comment>
'''
