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
# $Id: User.py,v 1.10 2004/12/14 05:30:29 akm Exp $

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
from AccessControl.User import BasicUser
from string import join,strip,split,lower,upper,find

class XUFUser(BasicUser):

	icon='misc_/exUserFolder/exUser.gif'

	# cacheable is a dict that must contain at least name, password,
	# roles, and domains -- unless you're working with your own User class,
	# in which case you need to override __init__ and define it yourself.
	def __init__(self, cacheable, propSource, cryptPassword, authSource,
				 groupSource=None):
		self.name   =cacheable['name']
		self.__     =cacheable['password']
		if cacheable['roles']:
			self.roles = filter(None, cacheable['roles'])
		else:
			self.roles = []
		# domains may be passed as a string or a list
		if type(cacheable['domains']) == type(''):
			self.domains=filter(None, map(strip,
										  split(cacheable['domains'], ',')))
		else:
			self.domains=cacheable['domains']
		self._authSource=authSource
		self._propSource=propSource
		self._groupSource=groupSource		
		self.cryptPassword=cryptPassword

	def getUserName(self):
		return self.name

	def _getPassword(self):
		return self.__

	def getRoles(self):
		return tuple(self.roles) + ('Authenticated',)
    
	def getDomains(self):
		return self.domains

	# Ultra generic way of getting, checking and setting properties
	def getProperty(self, property, default=None):
		if self._propSource:
			return self._propSource.getUserProperty(property, self.name, default)

	def hasProperty(self, property):
		if self._propSource:
			return self._propSource.hasProperty(property)

	def setProperty(self, property, value):
		if property[0]=='_':
			return
		if self._propSource:
			return self._propSource.setUserProperty(property, self.name, value)

	def setTempProperty(self, property, value):
		if property[0]=='_':
			return
		if self._propSource:
			return self._propSource.setTempProperty(property, value)

	def flushTempProperties(self):
		if self._propSource:
			return self._propSource.flushTempProperties()

	def delProperty(self, property):
		if property[0]=='_':
			return
		if self._propSource:
			return self._propSource.delUserProperty(property, self.name)
		
	def listProperties(self):
		if self._propSource:
			return self._propSource.listUserProperties(self.name)

	# Try to allow User['property'] -- won't work for password d;)
	def __getitem__(self, key):
		# Don't return 'private' keys
		if key[0] != '_':
			if hasattr(self, key):
				return getattr(self, key)
			if self._propSource and self._propSource.hasProperty(key):

				return self._propSource.getUserProperty(key, self.name)
		raise KeyError, key

	def __setitem__(self, key, value):
		if key[0]=='_':
			return
		if self._propSource:
			self._propSource.setUserProperty(key, self.name, value)
		
	# List one user is supplied by the Auth Source...
	
	def authenticate(self, listOneUser, password, request, remoteAuth=None):
		result=listOneUser(username=self.name)
		for people in result:
			if remoteAuth:
				return remoteAuth(self.name, password)
			else:
				secret=self.cryptPassword(self.name, password)
				return secret==people['password']
		return None

	# You can set logout times or whatever here if you want to, the
	# property source is still active.
	def notifyCacheRemoval(self):
		if self._propSource:
			self._propSource.flushTempProperties()

	# You must override this and __init__ if you are subclassing
	# the user object, or your user object may not be reconstructed
	# properly!  All values in this dict must be non-Persistent objects
	# or types, and may not hold any references to Persistent objects,
	# or the cache will break.
	def _getCacheableDict(self):
		return {'name':		self.name,
				'password':	self.__,
				'roles':	self.roles,
				'domains':	self.domains}

	def getGroups(self):
		if self._groupSource:
			return self._groupSource.getGroupsOfUser(self.name)
		else:
			return ()


	def _setGroups(self, groupnames):
		if self._groupSource:
			return self._groupSource.setGroupsOfUser(groupnames, self.name)


	def _addGroups(self, groupnames):
		if self._groupSource:
			return self._groupSource.addGroupsToUser(groupnames, self.name)

	def _delGroups(self, groupnames):
		if self._groupSource:
			return self._groupSource.delGroupsFromUser(groupnames, self.name)

	def getId(self):
		if self._propSource and self._propSource.getUserProperty('userid', self.name):
			return self._propSource.getUserProperty('userid', self.name)
		return self.name


#
# An Anonymous User for session tracking...
# Can set and get properties just like a normal user.
#
# These objects live in the cache, so, we have a __del__ method to
# clean ourselves up.
#

class XUFAnonUser(XUFUser):
	def __init__(self, name, roles, propSource):
		self.name   =name
		self.__     =''
		self.roles  =filter(None, roles)
		self._propSource=propSource

	def getRoles(self):
		return tuple(self.roles) + ('Anonymous',)

	def authenticate(self, listOneUser, password, request, remoteAuth=None):
		return 1
	
	def notifyCacheRemoval(self):
		if self._propSource:
			self._propSource.deleteUsers([self.name,])

# We now set up a dummy classes so that people can extend the User objects
# or override stuff with much less pain --akm

class User(XUFUser):
	pass

class AnonUser(XUFAnonUser):
	pass

