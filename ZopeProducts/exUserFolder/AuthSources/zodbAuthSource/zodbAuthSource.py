# $Id: zodbAuthSource.py,v 1.1 2004/11/10 14:15:52 akm Exp $

import Acquisition

from Globals import HTMLFile, MessageDialog, INSTANCE_HOME, Persistent, PersistentMapping

from OFS.Folder import Folder
try:
	from crypt import crypt
except:
	from Products.exUserFolder.fcrypt.fcrypt import crypt

from Products.exUserFolder.exUserFolder import exUserFolder
from Products.exUserFolder.Plugins import PluginRegister

from AccessControl.User import User


def manage_addzodbAuthSource(self, REQUEST):

	""" Add a ZODB Auth Source"""
	o = zodbAuthSource()
	self._setObject('zodbAuthSource',o)
	o=getattr(self,'zodbAuthSource')
	if hasattr(o,'postInitialisation'):
		o.postInitialisation(REQUEST)
	
	self.currentAuthSource=o
	return ''

manage_addzodbAuthSourceForm=HTMLFile('manage_addzodbAuthSourceForm', globals())
manage_editzodbAuthSourceForm=HTMLFile('manage_editzodbAuthSourceForm', globals())

class zodbAuthSource(Folder):
	""" Authenticate users against a ZODB dictionary"""

	meta_type='Authentication Source'
	title	 ='ZODB Authentication'
	icon ='misc_/exUserFolder/exUserFolderPlugin.gif'

	manage_properties=HTMLFile('properties', globals())

	manage_editForm=manage_editzodbAuthSourceForm
	manage_tabs=Acquisition.Acquired

	#
	# You can define this to go off and do the authentication instead of
	# using the basic one inside the User Object
	#
	remoteAuthMethod=None

	def __init__(self):
		self.id = 'zodbAuthSource'
		self.data=PersistentMapping()

	def cryptPassword_old(self, username, password):
			salt = username[:2]
			secret = crypt(password, salt)
			return secret

	def deleteUsers(self, userids):
		for name in userids:
			del self.data[name]

	def createUser(self, username, password, roles=[]):
		""" Add a Username """
		if type(roles) != type([]):
			if roles:
				roles=list(roles)
			else:
				roles=[]
			
			
		secret=self.cryptPassword(username, password)
		self.data[username]=PersistentMapping()
		self.data[username].update({ 
					'username': username,	
					'password': secret, 
					'roles': roles })

	def updateUser(self, username, password, roles):
		if type(roles) != type([]):
			if roles:
				roles=list(roles)
			else:
				roles=[]
		
		self.data[username]['roles'] = roles
		if password:
			secret = self.cryptPassword(username, password)
			self.data[username]['password'] = secret

	def listUserNames(self):
		return list(self.data.keys())

	def listUsers(self):
		""" return a list of user names or [] if no users exist"""
		return self.data.values()

	def listOneUser(self, username):
		users = []
		data = self.data.get(username)
		if data is not None:
			users.append(data)
		return users

	def postInitialisation(self, REQUEST):
		pass

zodbAuthReg=PluginRegister('zodbAuthSource', 'ZODB Authentication Source',
						   zodbAuthSource, manage_addzodbAuthSourceForm,
						   manage_addzodbAuthSource,
						   manage_editzodbAuthSourceForm)
exUserFolder.authSources['zodbAuthSource']=zodbAuthReg
