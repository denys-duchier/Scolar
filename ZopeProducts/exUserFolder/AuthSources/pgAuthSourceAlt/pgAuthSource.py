#
# Extensible User Folder
# 
# Postgres Authentication Source for exUserFolder
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
# $Id: pgAuthSource.py,v 1.1 2004/11/10 14:15:36 akm Exp $
#
# This class only authenticates users, it stores no properties.
#

import string,Acquisition,md5

from Globals import HTMLFile, MessageDialog, INSTANCE_HOME

from OFS.Folder import Folder

from Products.ZSQLMethods.SQL import SQL

from Products.exUserFolder.exUserFolder import exUserFolder
from Products.exUserFolder.Plugins import PluginRegister

try:
	from crypt import crypt
except:
	from Products.exUserFolder.fcrypt.fcrypt import crypt


def manage_addpgAuthSource(self, REQUEST):
	""" Add a Postgres Auth Source """

	connection=REQUEST['pgauth_connection']
	userTable=REQUEST['pgauth_userTable']
	usernameColumn=REQUEST['pgauth_usernameColumn']
	passwordColumn=REQUEST['pgauth_passwordColumn']
	roleTable=REQUEST['pgauth_roleTable']
	roleColumn=REQUEST['pgauth_roleColumn']
	o = pgAuthSource(connection, userTable, usernameColumn, passwordColumn,
					 roleTable, roleColumn)
	self._setObject('pgAuthSource', o, None, None, 0)
	o=getattr(self,'pgAuthSource')
	if hasattr(o, 'postInitialisation'):
		o.postInitialisation(REQUEST)
	
	self.currentAuthSource=o
	return ''

manage_addpgAuthSourceForm=HTMLFile('manage_addpgAuthSourceForm', globals())
manage_editpgAuthSourceForm=HTMLFile('manage_editpgAuthSourceForm', globals())

class pgAuthSource(Folder):
	""" Authenticate Users against a Postgres Database """

	meta_type='Authentication Source'
	title='Advanced Postgresql Authentication'

	icon ='misc_/exUserFolder/exUserFolderPlugin.gif'

	manage_tabs=Acquisition.Acquired

	manage_editForm=manage_editpgAuthSourceForm

	#
	# You can define this to go off and do the authentication instead of
	# using the basic one inside the User Object
	#
	remoteAuthMethod=None
	
	def __init__(self, connection, userTable, usernameColumn, passwordColumn,
				 roleTable, roleColumn):
		self.id='pgAuthSource'
		self.connection=connection
		self.userTable=userTable
		self.usernameColumn=usernameColumn
		self.passwordColumn=passwordColumn
		self.roleTable=roleTable
		self.roleColumn=roleColumn
		self.addSQLQueries()

	def manage_editAuthSource(self, REQUEST):
		""" Edit a Postgres Auth Source """

		self.connection=REQUEST['pgauth_connection']
		self.userTable=REQUEST['pgauth_userTable']
		self.usernameColumn=REQUEST['pgauth_usernameColumn']
		self.passwordColumn=REQUEST['pgauth_passwordColumn']
		self.roleTable=REQUEST['pgauth_roleTable']
		self.roleColumn=REQUEST['pgauth_roleColumn']
		self.delSQLQueries()
		self.addSQLQueries() # Re-add queries with new parameters

	def createUser(self, username, password, roles):
		""" Add A Username """

		if type(roles) != type([]):
			if roles:
				roles=list(roles)
			else:
				roles=[]

		secret=self.cryptPassword(username, password)
		self.sqlInsertUser(username=username, password=secret)

		for n in roles:
			self.insertUserRole(username, n)


	def insertUserRole(self, username, rolename):
		""" Add User Role """

		self.sqlInsertUserRole(username=username, rolename=rolename)

	def deleteUserRoles(self, username):
		""" Delete User Roles """

		self.sqlDeleteUserRoles(username=username)

	def updateUser(self, username, password, roles):
		if type(roles) != type([]):
			if roles:
				roles=list(roles)
			else:
				roles=[]
		
		# Don't change passwords if it's null
		if password:
			secret=self.cryptPassword(username, password)
			self.sqlUpdateUserPassword(username=username, password=secret)

		self.deleteUserRoles(username)

		for n in roles:
			self.insertUserRole(username, n)
			
	def delSQLQueries(self):
		sqllist=self.objectIds('Z SQL Method')
		self.manage_delObjects(ids=sqllist)

	def addSQLQueries(self):
		sqlListUsers=SQL(
			'sqlListUsers',
			'List All Users',
			self.connection,
			'userTable=%s'%(self.userTable),
			_sqlListUsers)

		self._setObject('sqlListUsers', sqlListUsers)
	
		sqlListOneUser=SQL(
			'sqlListOneUser',
			'List ONE User',
			self.connection,
			'userTable=%s usernameColumn=%s username:string'%(
			self.userTable, self.usernameColumn),
			_sqlListOneUser)

		self._setObject('sqlListOneUser', sqlListOneUser)

		sqlListUserRoles=SQL(
			'sqlListUserRoles',
			'List User Roles',
			self.connection,
			'roleTable=%s usernameColumn=%s username:string'%(
			self.roleTable, self.usernameColumn),
			_sqlListUserRoles)

		self._setObject('sqlListUserRoles', sqlListUserRoles)

		sqlDeleteOneUser=SQL(
			'sqlDeleteOneUser',
			'Delete One User',
			self.connection,
			'userTable=%s usernameColumn=%s username:string'%(
			self.userTable,self.usernameColumn),
			_sqlDeleteOneUser)

		self._setObject('sqlDeleteOneUser', sqlDeleteOneUser)

		sqlDeleteUserRoles=SQL(
			'sqlDeleteUserRoles',
			'Delete User Roles',
			self.connection,
			'roleTable=%s usernameColumn=%s username:string'%(
			self.roleTable,self.usernameColumn),
			_sqlDeleteUserRoles)

		self._setObject('sqlDeleteUserRoles', sqlDeleteUserRoles)

		sqlInsertUser=SQL(
			'sqlInsertUser',
			'Insert One User',
			self.connection,
			'userTable=%s usernameColumn=%s passwordColumn=%s username:string password:string'%(
			self.userTable, self.usernameColumn, self.passwordColumn),
			_sqlInsertUser)

		self._setObject('sqlInsertUser', sqlInsertUser)

		sqlInsertUserRole=SQL(
			'sqlInsertUserRole',
			'Insert User Role',
			self.connection,
			'roleTable=%s usernameColumn=%s roleColumn=%s username:string rolename:string'%(
			self.roleTable, self.usernameColumn, self.roleColumn),
			_sqlInsertUserRole)

		self._setObject('sqlInsertUserRole', sqlInsertUserRole)

		sqlUpdateUserPassword=SQL(
			'sqlUpdateUserPassword',
			'Update just the password',
			self.connection,
			'userTable=%s usernameColumn=%s passwordColumn=%s username:string password:string'%(self.userTable, self.usernameColumn, self.passwordColumn),
			_sqlUpdateUserPassword)

		self._setObject('sqlUpdateUserPassword', sqlUpdateUserPassword)

# Original cryptPassword function

	def cryptPassword_old(self, username, password):
		salt =username[:2]
		secret = crypt(password, salt)
		return secret

# Alternate cryptPassword function, returns md5 hash of the password
#	def cryptPassword_old(self, username, password):
#		passhash = md5.new(password)
#		secret = passhash.hexdigest()
#		return secret

# Alternate cryptPassword function, returns plain text of the password.
#	def cryptPassword_old(self, username, password):
#		return password

	def deleteUsers(self, userids):
		for uid in userids:
			self.sqlDeleteUserRoles(username=uid)
			self.sqlDeleteOneUser(username=uid)

	def listUserNames(self):
		"""Returns a real list of user names """
		users = []
		result=self.sqlListUsers()
		for n in result:
			username=sqlattr(n,self.usernameColumn)
			users.append(username)
		return users

	def listUsers(self):
		"""Returns a list of user names or [] if no users exist"""
		users = []
		result=self.sqlListUsers()
		for n in result:
			username=sqlattr(n,self.usernameColumn)
			N={'username':username}
			users.append(N)
		return users

	def listOneUser(self,username):
		users = []
		result=self.sqlListOneUser(username=username)
		for n in result:
			username=sqlattr(n,self.usernameColumn)
			password=sqlattr(n,self.passwordColumn)
			roles=self.listUserRoles(username)
			N={'username':username, 'password':password, 'roles':roles}
			users.append(N)
		return users

	def listUserRoles(self,username):
		roles = []
		result = self.sqlListUserRoles(username=username)
		for n in result:
			role=sqlattr(n, self.roleColumn)
			N=role
			roles.append(N)
		return roles

	def getUsers(self):
		"""Return a list of user objects or [] if no users exist"""
		data=[]
		try:    items=self.listusers()
		except: return data
		for people in items:
			roles=string.split(people['roles'],',')
			user=User(people['username'], roles, '')
			data.append(user)
		return data

	def postInitialisation(self, REQUEST):
		pass

pgAuthReg=PluginRegister('pgAuthSourceAdv', 'Advanced Postgresql Authentication Source',
						 pgAuthSource, manage_addpgAuthSourceForm,
						 manage_addpgAuthSource,
						 manage_editpgAuthSourceForm)
exUserFolder.authSources['pgAuthSourceAdv']=pgAuthReg

from string import upper, lower
import Missing
mt=type(Missing.Value)

def typeconv(val):
    if type(val)==mt:
        return ''
    return val

def sqlattr(ob, attr):
    name=attr
    if hasattr(ob, attr):
        return typeconv(getattr(ob, attr))
    attr=upper(attr)
    if hasattr(ob, attr):
        return typeconv(getattr(ob, attr))
    attr=lower(attr)
    if hasattr(ob, attr):
        return typeconv(getattr(ob, attr))
    raise NameError, name

_sqlListUsers="""
SELECT * FROM <dtml-var userTable>
"""

_sqlListOneUser="""
SELECT * FROM <dtml-var userTable>
where <dtml-var usernameColumn>=<dtml-sqlvar username type=string>
"""

_sqlListUserRoles="""
SELECT * FROM <dtml-var roleTable>
where <dtml-var usernameColumn>=<dtml-sqlvar username type=string>
"""

_sqlDeleteOneUser="""
DELETE FROM <dtml-var userTable>
where <dtml-var usernameColumn>=<dtml-sqlvar username type=string>
"""

_sqlDeleteUserRoles="""
DELETE FROM <dtml-var roleTable>
where <dtml-var usernameColumn>=<dtml-sqlvar username type=string>
"""

_sqlInsertUser="""
INSERT INTO <dtml-var userTable> (<dtml-var usernameColumn>, <dtml-var passwordColumn>)
VALUES (<dtml-sqlvar username type=string>, <dtml-sqlvar password type=string>)
"""

_sqlInsertUserRole="""
INSERT INTO <dtml-var roleTable> (<dtml-var usernameColumn>, <dtml-var roleColumn>)
VALUES (<dtml-sqlvar username type=string>, <dtml-sqlvar rolename type=string>)
"""

_sqlUpdateUserPassword="""
UPDATE <dtml-var userTable> set <dtml-var passwordColumn>=<dtml-sqlvar password type=string>
WHERE <dtml-var usernameColumn>=<dtml-sqlvar username type=string>
"""
