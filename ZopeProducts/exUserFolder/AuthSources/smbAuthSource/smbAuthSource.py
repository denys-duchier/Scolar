#
# Extensible User Folder
# 
# SMB Authentication Source for exUserFolder
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
# $Id: smbAuthSource.py,v 1.1 2004/11/10 14:15:51 akm Exp $

# Uses pysmb
# Copyright (C) 2001 Michael Teo <michaelteo@bigfoot.com>

import string, Acquisition

from Globals import HTMLFile, MessageDialog, INSTANCE_HOME

from OFS.Folder import Folder

from Products.exUserFolder.exUserFolder import exUserFolder
from Products.exUserFolder.Plugins import PluginRegister

import smb, nmb, socket
from smb import SessionError
import sys

import zLOG

def manage_addsmbAuthSource(self, REQUEST):
	""" Add a smb Auth Source """

	host=REQUEST['smbauth_host']
	domain=REQUEST['smbauth_domain']
	winsserver=REQUEST['smbauth_winsserver']

	ob=smbAuthSource(host, domain, winsserver)
	self._setObject('smbAuthSource', ob, None, None, 0)
	self.currentAuthSource=ob


manage_addsmbAuthSourceForm=HTMLFile('manage_addsmbAuthSourceForm', globals())
manage_editsmbAuthSourceForm=HTMLFile('manage_editsmbAuthSourceForm', globals())


class smbAuthSource(Folder):
	""" """

	meta_type = 'Authentication Source'
	id = 'smbAuthSource'
	title = 'SMB Authentication'
	icon = 'misc_/exUserFolder/exUserFolderPlugin.gif'

	manage_editForm=manage_editsmbAuthSourceForm
	manage_tabs=Acquisition.Acquired

	_v_smb=None
	_v_netbios=None
	_v_address=None

	def __init__(self, host, domain, winsserver):

		self._setSMBData(host, domain, winsserver)

	def manage_editAuthSource(self, REQUEST):
		'''Handle output of manage_main - change ZSmb instance properties.
		If REQUEST.secret is None, old secret will be used.'''

		host=REQUEST['host']
		domain=REQUEST['domain']
		winsserver=REQUEST['winsserver']

		self._setSMBData(host, domain, winsserver)

		if REQUEST is not None:
			return self.MessageDialog(self,REQUEST=REQUEST,
				title = 'Edited',
				message = "Properties for %s changed." % self.id,
				action = 'manage_editAuthSourceForm')
		
	#
	# We don't let you delete, create, or edit users
	#
	def deleteUsers(self, userids):
		pass

	def createUser(self, username, password, roles, groups=[]):
		pass


	def updateUser(self, username, password, roles, groups=[]):
		self.currentPropSource.setUserProperty(username=username, key='_roles', value=roles)
		self.currentPropSource.setUserProperty(username=username, key='_groups', value=groups)
	
	def listUserNames(self):
		return []

	def listUsers(self):
		return []

	def listOneUser(self, username):
		roles=[]
		groups=[]

		username = string.lower(username)		

		if self.currentPropSource:
			roles=self.currentPropSource.getUserProperty(username=username, key='_roles', default=[])
			groups=self.currentPropSource.getUserProperty(username=username, key='_groups', default=[])

		if not roles:
			roles=[] # make sure it's a list...
		if not groups:
			groups=[]

		zLOG.LOG('smbAuthSource',
				 zLOG.DEBUG,
				 "listOneUser returning {username: '%s', password: '', roles: %s}" % (username, roles)
				)
		return [{'username':username,
				 'password':'',
				 'roles':	roles,
				 'groups':	groups},]

	def getUsers(self):
		return []
	
	def authenticate(self, username, password):
		'Authenticate a username/password combination against the Smb server'
		if username == '':
			zLOG.LOG('smbAuthSource',
				 zLOG.DEBUG,
				 'got null username; auth failed' )
			return 0
	
		# Please don't try to make retries a knob without
		# checking _authenticate_retry -- we assume it's 3 in
		# there when we log retry-related events.  It shouldn't
		# break anything, but it will make log entries
		# inaccurate. --mb

		return self._authenticate_retry(username, password, 3)

	def _authenticate_retry(self, username, password, retries):
		try:
			self._getSMB().login(username, password, self._domain)
			if retries < 3:
				zLOG.LOG('smbAuthSource', zLOG.BLATHER,
						 'authenticated %s\%s after %d retries' % (self.domain(), username, (3 - retries)) )
			return 1

		except SessionError, e:
			# Happens when server answers "Authentication failed", at least under Win32
			zLOG.LOG('smbAuthSource',
				 zLOG.BLATHER,
				 'SessionError (%s) for %s\%s (usually means login failure); auth failed' % (e, self.domain(), username),
				 '\n',
				 sys.exc_info() )
			return 0

		except (nmb.NetBIOSError, nmb.NetBIOSTimeout), e:
			zLOG.LOG('smbAuthSource', zLOG.ERROR,
					 'NetBIOS error (%s) for %s\%s; auth failed' % (e, self.domain(), username),
					 '\n', sys.exc_info() )
			return 0

		except socket.error, (errno, strerror):
			zLOG.LOG('smbAuthSource',
				 zLOG.DEBUG,
				 'socket error %s (%s) for %s\%s' % (errno, strerror, self.domain(), username),
				 '\n',
				 sys.exc_info() )
			# TODO: It would be nice to check for appropriate errnos for different platforms.
			# As for now, we just won't worry about it and act the same whatever happens
			if retries > 0:
				self._resetSMB()
				return self._authenticate_retry(username, password, retries - 1)
			else:
				zLOG.LOG('smbAuthSource',
					 zLOG.ERROR,
					 'socket error %s (%s) for %s\%s; auth failed' % (errno, strerror, self.domain(), username),
					 '\n',
					 sys.exc_info() )
				return 0 
	
	remoteAuthMethod=authenticate

	def host(self): return self._host
	def domain(self): return self._domain
	def port(self): return self._port
	def retries(self): return self._retries
	def timeout(self): return self._timeout
	def winsserver(self): return self._winsserver

	def _getNetBIOS(self):
		if not self._v_netbios:
			self._v_netbios = nmb.NetBIOS()
			# check if we should use WINS
			if self._winsserver:
				self._v_netbios.set_nameserver(self._winsserver)
		return self._v_netbios

	def _getAddress(self):
		if not self._v_address:
			addressList = self._getNetBIOS().gethostbyname(self._host)

			# it seems lookup with a WINS server does not
			# raise an error when not found, it just returns
			# an empty list, so we fake an error --rochael
			if not addressList:
				raise nmb.NetBIOSError("smbAuthorization: Authentication server '%s' is not known to WINS server '%s'" %
						       (self._host, self._winsserver) )
                        self._v_address = addressList[0].get_ip()
		return self._v_address

	def _getSMB(self):
		if not self._v_smb:
			self._v_smb = smb.SMB(self._host, self._getAddress())
		return self._v_smb
		
	def _setSMBData(self, host, domain, winsserver):

		self._host = host
		self._domain = domain
		self._winsserver = winsserver

		# Reset Smb objects so new values take effect. This is
		# why we don't allow direct access to the attributes
		self._resetSMB()

	def _resetSMB(self):
		self._v_netbios = None
		self._v_smb = None
		self._v_address = None

		# if this doesn't raise an Exception, the smb data is valid
		return self._getSMB()


smbAuthReg=PluginRegister('smbAuthSource',
			  'SMB Authentication Source',
			  smbAuthSource, manage_addsmbAuthSourceForm,
			  manage_addsmbAuthSource,
			  manage_editsmbAuthSourceForm)

exUserFolder.authSources['smbAuthSource']=smbAuthReg
