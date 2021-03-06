#
# Extensible User Folder
# 
# MySQL Authentication Source for exUserFolder
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
# Author: Clint Brubakken <cabrubak@acm.org> adapted from pgPropSource by Andrew Milton <akm@theinternet.com.au>
# $Id: mysqlAuthSource.py,v 1.1 2004/11/10 14:15:35 akm Exp $

#
# This class only authenticates users, it stores no properties.
#

import string,Acquisition

from Globals import HTMLFile, MessageDialog, INSTANCE_HOME

from OFS.Folder import Folder

from Products.ZSQLMethods.SQL import SQL

from Products.exUserFolder.exUserFolder import exUserFolder
from Products.exUserFolder.Plugins import PluginRegister

try:
	from crypt import crypt
except:
	from Products.exUserFolder.fcrypt.fcrypt import crypt


def manage_addmysqlAuthSource(self, REQUEST):
	""" Add a MySQL Auth Source """

	connection=REQUEST['mysqlauth_connection']
	table=REQUEST['mysqlauth_table']
	usernameColumn=REQUEST['mysqlauth_usernameColumn']
	passwordColumn=REQUEST['mysqlauth_passwordColumn']
	rolesColumn=REQUEST['mysqlauth_rolesColumn']
	o = mysqlAuthSource(connection, table, usernameColumn, passwordColumn,
					 rolesColumn)
	self._setObject('mysqlAuthSource', o, None, None, 0)
	o=getattr(self,'mysqlAuthSource')
	if hasattr(o, 'postInitialisation'):
		o.postInitialisation(REQUEST)
	
	self.currentAuthSource=o
	return ''

manage_addmysqlAuthSourceForm=HTMLFile('manage_addmysqlAuthSourceForm', globals())
manage_editmysqlAuthSourceForm=HTMLFile('manage_editmysqlAuthSourceForm', globals())

class mysqlAuthSource(Folder):
	""" Authenticate Users against a MySQL Database """

	meta_type='Authentication Source'
	title='MySQL Authentication'

	icon ='misc_/exUserFolder/exUserFolderPlugin.gif'

	manage_tabs=Acquisition.Acquired

	manage_editForm=manage_editmysqlAuthSourceForm

	#
	# You can define this to go off and do the authentication instead of
	# using the basic one inside the User Object
	#
	remoteAuthMethod=None
	
	def __init__(self, connection, table, usernameColumn, passwordColumn,
				 rolesColumn):
		self.id='mysqlAuthSource'
		self.connection=connection
		self.table=table
		self.usernameColumn=usernameColumn
		self.passwordColumn=passwordColumn
		self.rolesColumn=rolesColumn
		self.addSQLQueries()

	def manage_editAuthSource(self, REQUEST):
		""" Edit a MySQL Auth Source """

		self.connection=REQUEST['mysqlauth_connection']
		self.table=REQUEST['mysqlauth_table']
		self.usernameColumn=REQUEST['mysqlauth_usernameColumn']
		self.passwordColumn=REQUEST['mysqlauth_passwordColumn']
		self.rolesColumn=REQUEST['mysqlauth_rolesColumn']
		self.delSQLQueries()
		self.addSQLQueries() # Re-add queries with new parameters

	def createUser(self, username, password, roles):
		""" Add A Username """

		if type(roles) != type([]):
			if roles:
				roles=list(roles)
			else:
				roles=[]

		rolestring=''
		for role in roles:
			rolestring=rolestring+role+','

		rolestring=rolestring[:-1]
		secret=self.cryptPassword(username, password)
		self.sqlInsertUser(username=username,
						   password=secret,
						   roles=rolestring)

	def updateUser(self, username, password, roles):
		if type(roles) != type([]):
			if roles:
				roles=list(roles)
			else:
				roles=[]
		
		rolestring=''
		for role in roles:
			print role
			rolestring=rolestring+role+','

		rolestring=rolestring[:-1]

		# Don't change passwords if it's null
		if password:
			secret=self.cryptPassword(username, password)
			self.sqlUpdateUserPassword(username=username,
									   password=secret)
			
		self.sqlUpdateUser(username=username,
						   roles=rolestring)

	def delSQLQueries(self):
		sqllist=self.objectIds('Z SQL Method')
		self.manage_delObjects(ids=sqllist)

	def addSQLQueries(self):
		sqlListUsers=SQL(
			'sqlListUsers',
			'List All Users',
			self.connection,
			'table=%s'%(self.table),
			_sqlListUsers)

		self._setObject('sqlListUsers', sqlListUsers)

		sqlListOneUser=SQL(
			'sqlListOneUser',
			'List ONE User',
			self.connection,
			'table=%s usernameColumn=%s username:string'%(
			self.table, self.usernameColumn),
			_sqlListOneUser)

		self._setObject('sqlListOneUser', sqlListOneUser)

		sqlDeleteOneUser=SQL(
			'sqlDeleteOneUser',
			'Delete One User',
			self.connection,
			'table=%s usernameColumn=%s username:string'%(
			self.table,self.usernameColumn),
			_sqlDeleteOneUser)

		self._setObject('sqlDeleteOneUser', sqlDeleteOneUser)

		sqlInsertUser=SQL(
			'sqlInsertUser',
			'Insert One User',
			self.connection,
			'table=%s usernameColumn=%s passwordColumn=%s rolesColumn=%s username:string password:string roles:string'%(
			self.table, self.usernameColumn, self.passwordColumn, self.rolesColumn),
			_sqlInsertUser)

		self._setObject('sqlInsertUser', sqlInsertUser)

		sqlUpdateUser=SQL(
			'sqlUpdateUser',
			'Update User',
			self.connection,
			'table=%s rolesColumn=%s username:string roles:string'%(self.table, self.rolesColumn),
			_sqlUpdateUser)

		self._setObject('sqlUpdateUser', sqlUpdateUser)

		sqlUpdateUserPassword=SQL(
			'sqlUpdateUserPassword',
			'Update just the password',
			self.connection,
			'table=%s usernameColumn=%s passwordColumn=%s username:string password:string'%(self.table, self.usernameColumn, self.passwordColumn),
			_sqlUpdateUserPassword)

		self._setObject('sqlUpdateUserPassword', sqlUpdateUserPassword)

	def cryptPassword_old(self, username, password):
			salt =username[:2]
			secret = crypt(password, salt)
			return secret

	def deleteUsers(self, userids):
		for uid in userids:
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
			roles=[]
			username=sqlattr(n,self.usernameColumn)
			if sqlattr(n, self.rolesColumn):
				roles=string.split(sqlattr(n,self.rolesColumn),',')
			password=sqlattr(n, self.passwordColumn)
			N={'username':username, 'password':password, 'roles':roles}
			users.append(N)
		return users

	def listOneUser(self,username):
		users = []
		result=self.sqlListOneUser(username=username)
		for n in result:
			roles=[]
			username=sqlattr(n,self.usernameColumn)
			password=sqlattr(n,self.passwordColumn)
			if sqlattr(n, self.rolesColumn):
				roles=string.split(sqlattr(n,self.rolesColumn),',')  #Andreas
			N={'username':username, 'password':password, 'roles':roles}
			users.append(N)
		return users
	
	def postInitialisation(self, REQUEST):
		pass

mysqlAuthReg=PluginRegister('mysqlAuthSource', 'MySQL Authentication Source',
						 mysqlAuthSource, manage_addmysqlAuthSourceForm,
						 manage_addmysqlAuthSource,
						 manage_editmysqlAuthSourceForm)
exUserFolder.authSources['mysqlAuthSource']=mysqlAuthReg

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
SELECT * FROM <dtml-var table>
"""

_sqlListOneUser="""
SELECT * FROM <dtml-var table>
where <dtml-var usernameColumn>=<dtml-sqlvar username type=string>
"""

_sqlDeleteOneUser="""
DELETE FROM <dtml-var table>
where <dtml-var usernameColumn>=<dtml-sqlvar username type=string>
"""

_sqlInsertUser="""
INSERT INTO <dtml-var table> (<dtml-var usernameColumn>, <dtml-var passwordColumn>, <dtml-var rolesColumn>)
VALUES (<dtml-sqlvar username type=string>,
        <dtml-sqlvar password type=string>,
		<dtml-sqlvar roles type=string>)
"""

_sqlUpdateUserPassword="""
UPDATE <dtml-var table> set <dtml-var passwordColumn>=<dtml-sqlvar password type=string>
WHERE <dtml-var usernameColumn>=<dtml-sqlvar username type=string>
"""

_sqlUpdateUser="""
UPDATE <dtml-var table> set <dtml-var rolesColumn>=<dtml-sqlvar roles type=string>
WHERE <dtml-var usernameColumn>=<dtml-sqlvar username type=string>
"""
