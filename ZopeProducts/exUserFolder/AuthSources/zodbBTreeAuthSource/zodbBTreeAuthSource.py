# $Id: zodbBTreeAuthSource.py,v 1.1 2004/11/10 14:15:52 akm Exp $

import Acquisition

from Globals import HTMLFile, MessageDialog, INSTANCE_HOME, Persistent, PersistentMapping

from OFS.Folder import Folder
try:
	from crypt import crypt
except:
	from Products.exUserFolder.fcrypt.fcrypt import crypt

from Products.exUserFolder.exUserFolder import exUserFolder
from Products.exUserFolder.Plugins import PluginRegister

from BTrees.OOBTree import OOBTree
from AccessControl.User import User


def manage_addzodbBTreeAuthSource(self, REQUEST):

	""" Add a ZODB Auth Source"""
	o = zodbBTreeAuthSource()
	self._setObject('zodbBTreeAuthSource',o)
	o=getattr(self,'zodbBTreeAuthSource')
	if hasattr(o,'postInitialisation'):
		o.postInitialisation(REQUEST)
	
	self.currentAuthSource=o
	return ''

manage_addzodbBTreeAuthSourceForm=HTMLFile('manage_addzodbBTreeAuthSourceForm', globals())
manage_editzodbBTreeAuthSourceForm=HTMLFile('manage_editzodbBTreeAuthSourceForm', globals())

class zodbUser(Persistent):
	# I don't really need to specify these here, but, it does state
	# the intention of the class.
	username=''
	password=''
	roles=[]

class zodbBTreeAuthSource(Folder):
	""" Authenticate users against a ZODB BTree """

	meta_type='Authentication Source'
	title	 ='ZODB BTree Authentication'
	icon ='misc_/exUserFolder/exUserFolderPlugin.gif'

	manage_properties=HTMLFile('properties', globals())

	manage_editForm=manage_editzodbBTreeAuthSourceForm
	manage_tabs=Acquisition.Acquired

	#
	# You can define this to go off and do the authentication instead of
	# using the basic one inside the User Object
	#
	remoteAuthMethod=None

	def __init__(self):
		self.id = 'zodbBTreeAuthSource'
		self.userBTree=OOBTree()

	def cryptPassword_old(self, username, password):
			salt = username[:2]
			secret = crypt(password, salt)
			return secret

	def deleteUsers(self, userids):
		for name in userids:
			del self.userBTree[name]

	def createUser(self, username, password, roles=[]):
		""" Add a Username """
		if type(roles) != type([]):
			if roles:
				roles=list(roles)
			else:
				roles=[]

		secret=self.cryptPassword(username, password)			
		myUser=zodbUser()
		myUser.username=username
		myUser.password=secret
		myUser.roles=roles
		self.userBTree[username]=myUser

	def updateUser(self, username, password, roles):
		if type(roles) != type([]):
			if roles:
				roles=list(roles)
			else:
				roles=[]
		
		self.userBTree[username].roles = roles
		if password:
			secret = self.cryptPassword(username, password)
			self.userBTree[username].password = secret

	def listUserNames(self):
		return self.userBTree.keys()

	def listUsers(self):
		""" return a list of users or [] if no users exist"""
		users=[]
		for u in self.userBTree.keys():
			n = self.userBTree[u]
			N={'username':n.username, 'password':n.password, 'roles':n.roles}
			users.append(N)
		return users

	def listOneUser(self, username):
		users = []
		try:
			n = self.userBTree[username]
			N={'username':n.username, 'password':n.password, 'roles':n.roles}
			users.append(N)
		except:
			pass
		return users

	def postInitialisation(self, REQUEST):
		pass

zodbBTreeAuthReg=PluginRegister('zodbBTreeAuthSource', 'ZODB BTree Authentication Source',
						   zodbBTreeAuthSource, manage_addzodbBTreeAuthSourceForm,
						   manage_addzodbBTreeAuthSource,
						   manage_editzodbBTreeAuthSourceForm)
exUserFolder.authSources['zodbBTreeAuthSource']=zodbBTreeAuthReg
