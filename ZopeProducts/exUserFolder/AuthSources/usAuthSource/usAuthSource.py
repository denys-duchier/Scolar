#
# Extensible User Folder
# 
# User Supplied Authentication Source for exUserFolder
#
# (C) Copyright 2001 The Internet (Aust) Pty Ltd
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
# $Id: usAuthSource.py,v 1.1 2004/11/10 14:15:52 akm Exp $

#
# This class only authenticates users, it stores no properties.
#

import string

from Globals import HTMLFile, MessageDialog, INSTANCE_HOME

from OFS.Folder import Folder

from Products.ZSQLMethods.SQL import SQL

from Products.exUserFolder.exUserFolder import exUserFolder
from Products.exUserFolder.Plugins import PluginRegister

try:
	from crypt import crypt
except:
	from Products.exUserFolder.fcrypt.fcrypt import crypt

def manage_addusAuthSource(self, REQUEST):
	""" Add a Postgres Auth Source """

	o = usAuthSource()
	self._setObject('usAuthSource', o, None, None, 0)
	o=getattr(self,'usAuthSource')
	if hasattr(o, 'postInitialisation'):
		o.postInitialisation(REQUEST)
	
	self.currentAuthSource=o
	return ''

manage_addusAuthSourceForm=HTMLFile('manage_addusAuthSourceForm', globals())
manage_editusAuthSourceForm=HTMLFile('manage_editusAuthSourceForm', globals())

#
# This is a pretty good example of what functionality is required in order
# to provide an Authentication Source -- of course it leaves it as an exercise
# for the reader to provide that functionality.
#

class usAuthSource(Folder):
	""" Authenticate Users against a User Supplied Set of Methods """

	meta_type='Authentication Source'
	title='User Supplied Authentication'
	icon ='misc_/exUserFolder/exUserFolderPlugin.gif'
	manage_editForm=manage_editusAuthSourceForm
		
	def __init__(self):
		self.id='usAuthSource'

	# Create a User to authenticate against
	# username, password and roles
	def createUser(self, username, password, roles):
		""" Add A Username """
		if type(roles) != type([]):
			if roles:
				roles=list(roles)
			else:
				roles=[]
		if 'usCreateUser' in self.objectIds():
			self.usCreateUser(username, password, roles)

	# Update a user's roles and password
	# An empty password means do not change passwords...
	def updateUser(self, username, password, roles):
		if type(roles) != type([]):
			if roles:
				roles=list(roles)
			else:
				roles=[]
		if 'usUpdateUser' in self.objectIds():
			self.usUpdateUser(username, password, roles)

	# Encrypt a password
	# If no 'crypt' method is supplied return the
	# Password -- i.e. plaintext password
	def cryptPassword_old(self, username, password):
		if 'usCryptPassword' in self.objectIds():
			return self.usCryptPassword(username, password)
		else:
			return password

	# Delete a set of users
	def deleteUsers(self, userids):
		if 'usDeleteUsers' in self.objectIds():
			self.usDeleteUsers(userids)


	# Return a list of usernames
	def listUserNames(self):
		if 'usListUserNames' in self.objectIds():
			return self.usListUserNames()
		else:
			return []
		
	# Return one user matching the username
	# Should be a list of dictionaries (because we may allow multiple matching
	# users at some point)
	# [{'username':username, 'password':cryptedPassword, 'roles':list_of_roles},]
	def listOneUser(self,username):
		if 'usListOneUser' in self.objectIds():
			return self.usListOneUser(username)

	# Return a list of user dictionaries the same as listOnUser
	def listUsers(self):
		if 'usListUsers' in self.objectIds():
			return self.usListUsers()
		else:
			return []

	#
	# You can define this to go off and do the authentication instead of
	# using the basic one inside the User Object
	#
	remoteAuthMethod=None

##	def remoteAuthMethod(self, username, password):
##		""" Perform authentication 'our' way """
##		if 'usRemoteAuthMethod' in self.objectIds():
##			return self.usRemoteAuthMethod(username, password)
		
		

	def postInitialisation(self, REQUEST):
		pass

usAuthReg=PluginRegister('usAuthSource', 'User Supplied Authentication Source',
						 usAuthSource, manage_addusAuthSourceForm,
						 manage_addusAuthSource,
						 manage_editusAuthSourceForm)
exUserFolder.authSources['usAuthSource']=usAuthReg
