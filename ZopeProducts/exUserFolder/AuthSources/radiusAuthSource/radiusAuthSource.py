#
# Extensible User Folder
# 
# Postgres Authentication Source for exUserFolder
#
# (C) Copyright 2000,2001 The Internet (Aust) Pty Ltd
# ACN: 082 081 472	ABN: 83 082 081 472
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
# $Id: radiusAuthSource.py,v 1.1 2004/11/10 14:15:36 akm Exp $

# This code based on ZRadius by Stuart Bishop
# Copyright 1999 Stuart Bishop zen@cs.rmit.edu.au

import string,Acquisition

from Globals import HTMLFile, MessageDialog, INSTANCE_HOME

from OFS.Folder import Folder

from Products.exUserFolder.exUserFolder import exUserFolder
from Products.exUserFolder.Plugins import PluginRegister

from radius import Radius

def manage_addradiusAuthSource(self, REQUEST):
	""" Add a radius Auth Source """

	host=REQUEST['radiusauth_host']
	port=REQUEST['radiusauth_port']
	secret=REQUEST['radiusauth_secret']

	retries=REQUEST['radiusauth_retries']
	timeout=REQUEST['radiusauth_timeout']

	ob=radiusAuthSource(host, int(port), secret, int(retries), float(timeout))
	self._setObject('radiusAuthSource', ob, None, None, 0)
	self.currentAuthSource=ob	


manage_addradiusAuthSourceForm=HTMLFile('manage_addradiusAuthSourceForm', globals())
manage_editradiusAuthSourceForm=HTMLFile('manage_editradiusAuthSourceForm', globals())


class radiusAuthSource(Folder):
	""" """

	meta_type='Authentication Source'
	id		 ='radiusAuthSource'
	title	 ='RADIUS Authentication'
	icon ='misc_/exUserFolder/exUserFolderPlugin.gif'

	manage_editForm=manage_editradiusAuthSourceForm
	manage_tabs=Acquisition.Acquired

	_v_radius = None

	def __init__(self,host,port,secret,retries,timeout):

		self._host = host
		self._port = int(port)
		self._secret = secret

		self._retries = int(retries)
		self._timeout = float(timeout)


	def manage_editAuthSource(self,REQUEST):
		'''Handle output of manage_main - change ZRadius instance properties.
		If REQUEST.secret is None, old secret will be used.'''

		self._host = REQUEST['host']
		self._port = int(REQUEST['port'])
		if hasattr(REQUEST,'secret') and len(REQUEST['secret']) > 0: 
			# So we don't code it in form source
			self._secret = REQUEST['secret']

		self._retries = int(REQUEST['retries'])
		self._timeout = float(REQUEST['timeout'])

		# Reset the Radius object so new values take effect. This is
		# why we don't allow direct access to the attributes
		self._v_radius = None

		if REQUEST is not None:
			return self.MessageDialog(self,
				REQUEST=REQUEST,
				title = 'Edited',
				message = "Properties for %s changed." % self.id,
				action = 'manage_editAuthSourceForm')
		
	#
	# We don't let you delete, create, or edit users
	#
	def deleteUsers(self, userids):
		pass

	def createUser(self, username, password, roles):
		pass


	def updateUser(self, username, password, roles):
		self.currentPropSource.setUserProperty(username=username, key='_roles',
											   value=roles)
	
	def listUserNames(self):
		pass

	def listUsers(self):
		pass

	def listOneUser(self, username):
		roles=[]
		if self.currentPropSource:
			roles=self.currentPropSource.getUserProperty(username=username, key='_roles', default=[])

		return [{'username':username, 'password':'',
				 'roles':roles}]

	def getUsers(self):
		pass
	
	def authenticate(self,username,password):
		'Authenticate a username/password combination against the Radius server'

		if self._v_radius is None:
			self._v_radius = Radius(self._secret,self._host,self._port)
			self._v_radius.retries = int(self._retries)
			self._v_radius.timeout = self._timeout

		return self._v_radius.authenticate(username,password)
	
	remoteAuthMethod=authenticate
	
	def host(self): return self._host
	def port(self): return self._port
	def retries(self): return self._retries
	def timeout(self): return self._timeout


radiusAuthReg=PluginRegister('radiusAuthSource',
							 'RADIUS Authentication Source',
							 radiusAuthSource, manage_addradiusAuthSourceForm,
							 manage_addradiusAuthSource,
							 manage_editradiusAuthSourceForm)
exUserFolder.authSources['radiusAuthSource']=radiusAuthReg
