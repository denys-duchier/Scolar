#!/usr/bin/env python

__doc__ = '''
$Id: ZRadius.py,v 1.1 2004/11/10 14:15:36 akm Exp $

Extremly basic RADIUS authentication. Bare minimum required to authenticate
a user, yet remain RFC2138 compliant (I hope).

(c) 1999 Stuart Bishop <zen@cs.rmit.edu.au>
'''

__version__ = '$Revision: 1.1 $'

from Globals import HTMLFile,MessageDialog,Persistent
import OFS.SimpleItem
import Acquisition
import AccessControl.Role

from radius import Radius

manage_addZRadiusForm = HTMLFile('manage_addZRadiusForm',globals())

def manage_addZRadius(self,id,title,host,port,secret,retries,timeout,\
	REQUEST=None):
    'Create a new ZRadius instance'
    self._setObject(id, ZRadius(id,title,host,port,secret,retries,timeout))
    if REQUEST is not None:
	return self.manage_main(self,REQUEST)

class ZRadius(
    OFS.SimpleItem.Item,
    Persistent,
    Acquisition.Implicit,
    AccessControl.Role.RoleManager):
    'A Radius Authenticator'

    meta_type = 'ZRadius'

    manage_options = (
	    {'label':'Test',		'action':''},
	    {'label':'Properties',	'action':'manage_main'},
	    {'label':'Security',	'action':'manage_access'}
	)

    __ac_permissions__ = (
	    ('ZRadius authenticate',
		('authenticate', 'manage_test', 'index_html','__call__')),
	    ('Manage properties',
		('manage_main','host','port','retries','timeout',
		 'manage_edit')),
	)

    _v_radius = None

    def __init__(self,id,title,host,port,secret,retries,timeout):
	self.id = id
	self.title = title

	self.manage_main = HTMLFile('manage_main',globals())
	self.index_html = HTMLFile('index',globals())

	self._host = host
	self._port = port
	self._secret = secret

	self._retries = int(retries)
	self._timeout = float(timeout)
    
    def host(self): return self._host
    def port(self): return self._port
    def retries(self): return self._retries
    def timeout(self): return self._timeout

    def manage_edit(self,title,REQUEST=None):
	'''Handle output of manage_main - change ZRadius instance properties.
	    If REQUEST.secret is None, old secret will be used.'''

	self.title = title
	self._host = REQUEST.host
	self._port = int(REQUEST.port)
	if hasattr(REQUEST,'secret') and len(REQUEST.secret) > 0: 
	    # So we don't code it in form source
	    self._secret = REQUEST.secret 
	self._retries = int(REQUEST.retries)
	self._timeout = float(REQUEST.timeout)

	# Reset the Radius object so new values take effect. This is
	# why we don't allow direct access to the attributes
	self._v_radius = None

	if REQUEST is not None:
	    return self.MessageDialog(self,REQUEST=REQUEST,
		title = 'Edited',
		message = "Properties for %s changed." % self.id,
		action = './manage_main')

    def manage_test(self,REQUEST):
	'Handle submission from index_html'
	username = REQUEST.username
	password = REQUEST.password
	if self.authenticate(username,password):
	    return self.MessageDialog(self,REQUEST=REQUEST,
		title = 'Succeded',
		message = "Successfully authenticated '%s'" % username,
		action = './index_html')
	else:
	    return self.MessageDialog(self,REQUEST=REQUEST,
		title = 'Failed',
		message = "Failed to authenticate '%s'" % username,
		action = './index_html')

    def __call__(self,username,password):
	'Call authenticate'
	return self.authenticate(username,password)

    def authenticate(self,username,password):
	'Authenticate a username/password combination against the Radius server'

	if self._v_radius is None:
	    self._v_radius = Radius(self._secret,self._host,self._port)
	    self._v_radius.retries = int(self._retries)
	    self._v_radius.timeout = self._timeout

	return self._v_radius.authenticate(username,password)

