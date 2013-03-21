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
# 2. Redistributions in binary form must reproduce the above
#    copyright notice, this list of conditions, and the following
#    disclaimer in the documentation and/or other materials
#    provided with the distribution.
# 
# 3. Any use, including use of the Zope software to operate a
#    website, must either comply with the terms described below
#    under "Attribution" or alternatively secure a separate
#    license from Digital Creations.
# 
# 4. All advertising materials, documentation, or technical papers
#    mentioning features derived from or use of this software must
#    display the following acknowledgement:
# 
#      "This product includes software developed by Digital
#      Creations for use in the Z Object Publishing Environment
#      (http://www.zope.org/)."
# 
# 5. Names associated with Zope or Digital Creations must not be
#    used to endorse or promote products derived from this
#    software without prior written permission from Digital
#    Creations.
# 
# 6. Redistributions of any form whatsoever must retain the
#    following acknowledgment:
# 
#      "This product includes software developed by Digital
#      Creations for use in the Z Object Publishing Environment
#      (http://www.zope.org/)."
# 
# 7. Modifications are encouraged but must be packaged separately
#    as patches to official Zope releases.  Distributions that do
#    not clearly separate the patches from the original work must
#    be clearly labeled as unofficial distributions.
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
# Attribution
# 
#   Individuals or organizations using this software as a web site
#   must provide attribution by placing the accompanying "button"
#   and a link to the accompanying "credits page" on the website's
#   main entry point.  In cases where this placement of
#   attribution is not feasible, a separate arrangment must be
#   concluded with Digital Creations.  Those using the software
#   for purposes other than web sites must provide a corresponding
#   attribution in locations that include a copyright using a
#   manner best suited to the application environment.
# 
# This software consists of contributions made by Digital
# Creations and many individuals on behalf of Digital Creations.
# Specific attributions are listed in the accompanying credits
# file.
# 
##############################################################################
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
# $Id: etcAuthSource.py,v 1.2 2004/12/14 05:34:40 akm Exp $
"""User Db product

Authenticates off of an /etc/passwd like file.  This file must be in
the etcUsers directory in the top level Zope directory.  etcUserFolder 
only uses the first two columns of a password file, so files generated 
by htpasswd should work also.  The format must be:

uid:crypted_password

"""

import os, string, Acquisition

from Globals import HTMLFile, MessageDialog, INSTANCE_HOME
from string import join,strip,split,lower,upper,find

from OFS.Folder import Folder

try:
	from crypt import crypt
except:
	from Products.exUserFolder.fcrypt.fcrypt import crypt

from Products.exUserFolder.exUserFolder import exUserFolder
from Products.exUserFolder.Plugins import PluginRegister

path_split=os.path.split
path_join=os.path.join
exists=os.path.exists

def manage_addetcAuthSource(self, REQUEST):

	""" """
	pwfile=REQUEST['etcauth_pwfile']
	default_role=REQUEST['etcauth_default_role']
	ob=etcAuthSource(pwfile=pwfile, default_role=default_role)
	self._setObject('etcAuthSource', ob, None, None, 0)
	self.currentAuthSource=ob	

manage_addetcAuthSourceForm=HTMLFile('manage_addetcAuthSourceForm', globals())
manage_editetcAuthSourceForm=HTMLFile('manage_editetcAuthSourceForm', globals())

class etcAuthSource(Folder):
	""" """

	meta_type='Authentication Source'
	id		 ='etcAuthSource'
	title	 ='File System Authentication'
	icon ='misc_/exUserFolder/exUserFolderPlugin.gif'

	manage_properties=HTMLFile('properties', globals())

	manage_editForm=manage_editetcAuthSourceForm
	manage_tabs=Acquisition.Acquired

	#
	# You can define this to go off and do the authentication instead of
	# using the basic one inside the User Object
	#
	remoteAuthMethod=None

	def __init__(self, default_role, pwfile='etcUsers'):
		self.pwfile=pwfile
		self.default_role=default_role

	def manage_editAuthSource(self, REQUEST):

		""" """
		self.pwfile=REQUEST['etcauth_pwfile']
		self.default_role=REQUEST['etcauth_default_role']

	def cryptPassword_old(self, username, password):
		u=self.listOneUser(username)
		if not u:
			salt = username[:2]
		else:
			salt = u[0]['password'][:2]
		secret = crypt(password, salt)
		return secret

	#
	# We don't let you delete, create, or edit users
	#
	def deleteUsers(self, userids):
		pass

	def createUser(self, username, password, roles):
		pass

	def updateUser(self, username, password, roles):
		if roles.count(self.default_role):
			roles.remove(self.default_role)
		self.currentPropSource.setUserProperty(username=username, key='_roles',
											   value=roles)
	def listUserNames(self):
		users = []
		pf = open(getPath('exUsers', self.pwfile), 'r')
		while 1:
			n = pf.readline()
			username=string.split(n,':')[0]
			if not n:
				break
			users.append(username)
		return users
		
	def listUsers(self):
		users = []
		un=self.listUserNames()
		for username in un:
			for user in self.listOneUser(username):
				users.append(user)
		return users

	def listOneUser(self, username):
		users = []
		pf = open(getPath('exUsers', self.pwfile), 'r')
		while 1:
			n = pf.readline()
			if not n:
				break
			n=string.strip(n) # Kill the cr/lf
			fields=string.split(n,':')
			lUsername=fields[0]
			if username!=lUsername:
				continue
			password=fields[1]

			roles=[]
			if self.currentPropSource:
				roles=self.currentPropSource.getUserProperty(username=username, key='_roles')

			if roles and self.default_role:
				if not roles.count(self.default_role):
					roles=roles.append(self.default_role)
			elif self.default_role:
				roles=[self.default_role,]
			else:
				roles=[]
			
			users.append({'username':username,
						  'password':password,
						  'roles':roles})
		return users
		
etcAuthReg=PluginRegister('etcAuthSource', 'File Based Authentication Source',
						  etcAuthSource, manage_addetcAuthSourceForm,
						  manage_addetcAuthSource,
						  manage_editetcAuthSourceForm)
exUserFolder.authSources['etcAuthSource']=etcAuthReg



def _getPath(home, prefix, name, suffixes):

	d=path_join(home, prefix)

	if d==prefix: raise ValueError, (
		'The prefix, %s, should be a relative path' % prefix)
	d=path_join(d,name)
	if d==name: raise ValueError, ( # Paranoia
		'The file name, %s, should be a simple file name' % name)
	for s in suffixes:
		if s: s="%s.%s" % (d, s)
		else: s=d
		if exists(s): return s

def getPath(prefix, name, checkProduct=1, suffixes=('',)):
	"""Find a file in one of several relative locations

	Arguments:

	  prefix -- The location, relative to some home, to look for the
				file

	  name -- The name of the file.	 This must not be a path.

	  checkProduct -- a flag indicating whether product directories
		should be used as additional hope ares to be searched. This
		defaults to a true value.

		If this is true and the name contains a dot, then the
		text before the dot is treated as a product name and
		the product package directory is used as anothe rhome.

	  suffixes -- a sequences of file suffixes to check.
		By default, the name is used without a suffix.

	The search takes on multiple homes which are INSTANCE_HOME,
	the directory containing the directory containing SOFTWARE_HOME, and
	possibly product areas.		
	"""
	d,n = path_split(name)
	if d: raise ValueError, (
		'The file name, %s, should be a simple file name' % name)

	sw=path_split(path_split(SOFTWARE_HOME)[0])[0]
	for home in (INSTANCE_HOME, sw):
		if checkProduct:
			l=find(name, '.')
			if l > 0:
				p=name[:l]
				n=name[l+1:]
				r=_getPath(home, "Products/%s/%s/" % (p,prefix),
						   n, suffixes)

				if r is not None: return r
		r=_getPath(home, prefix, name, suffixes)
		if r is not None: return r
