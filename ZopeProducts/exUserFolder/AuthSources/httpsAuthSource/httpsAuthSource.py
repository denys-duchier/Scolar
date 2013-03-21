"""
 HTTPS Authentication Source for exUserFolder

 This class only authenticates users against an https service
 It stores roles in the prop source

 This plugin requires that ssl support be compiled into the python interpreter
 
 $Header: /cvsroot/exuserfolder/exUserFolder/AuthSources/httpsAuthSource/httpsAuthSource.py,v 1.1 2004/11/10 14:15:34 akm Exp $
"""

import string, re
import httplib, urllib, urlparse

import Acquisition

from Globals import HTMLFile, MessageDialog, InitializeClass

from OFS.Folder import Folder

from Products.exUserFolder.exUserFolder import exUserFolder
from Products.exUserFolder.Plugins import PluginRegister
from AccessControl import ClassSecurityInfo

from time import time

from zLOG import LOG, ERROR, DEBUG

def manage_addhttpsAuthSource(self, REQUEST):
    """ Add an https Auth Source """

    obj = httpsAuthSource(REQUEST)
    self._setObject('httpsAuthSource', obj, None, None, 0)
    obj = getattr(self, 'httpsAuthSource')
    
    self.currentAuthSource = obj
    return ''
manage_addhttpsAuthSourceForm=HTMLFile('manage_addhttpsAuthSourceForm', globals())
manage_edithttpsAuthSourceForm=HTMLFile('manage_edithttpsAuthSourceForm', globals())

class httpsAuthSource(Folder):
    """ Authenticate Users against an HTTPS service """

    meta_type= 'Authentication Source'
    id   = 'httpsAuthSource'
    title= 'HTTPS Authentication'
    icon = 'misc_/exUserFolder/exUserFolderPlugin.gif'

    ROLES_KEY = '_roles'

    manage_editForm = manage_edithttpsAuthSourceForm
    manage_properties=HTMLFile('properties', globals())
    manage_tabs=Acquisition.Acquired


    # Cache successful auths so we don't make N network requests per page
    _v_authenticCache = {}

    # Cache unauthorized users since this acl folder needs to fail before checking higher ones
    _v_unAuthenticCache = {}

    CACHE_TIMEOUT = 60  # how long we store auth in the cache.  (in seconds)
    UNAUTH_CACHE_MAXSIZE = 50 # limit the size that the unauthenticated cache can grow

    def __init__(self, REQUEST):
	self._setProps(REQUEST)

    def manage_editAuthSource(self, REQUEST):
	""" Handle output of manage_main"""
	self._setProps(REQUEST)

        self.clearAuthCache()
        
	if REQUEST is not None:
	    return self.MessageDialog(self,
				      REQUEST=REQUEST,
				      title = 'Edited',
				      message = "Properties for %s changed." % self.id,
				      action = 'manage_editAuthSourceForm')


    def _setProps(self,REQUEST):
	self.defaultRole = REQUEST.get('defaultRole', 'Member')
	self.serviceUrl    = REQUEST['serviceUrl']		

	self.userNameParam = REQUEST['userNameParam']
	self.passwdParam   = REQUEST['passwdParam']
        self.authResponse  = REQUEST['authResponse']
        self.authResponsePattern = re.compile(self.authResponse)
	
    #
    # Don't allow for creation - this happens automatically upon first login
    # 
    def createUser(self, username, password, roles):
	pass

    # we don't store the password - just pass it in the remoteAuthentication
    def cryptPassword_old(self, username, password):
	pass
	
    def deleteUsers(self, userids):
	"""delete user from the prop source"""
	self.currentPropSource.deleteUsers(userids)

    def updateUser(self, username, password, roles):
	"""Update a user's roles
	   Passwords are managed on the other end, not here"""

	self.currentPropSource.setUserProperty(username=username,
					       key=self.ROLES_KEY,
					       value=roles)

    def listUserNames(self):
	"""Return a list of usernames"""
	return self.currentPropSource.listUsers()

    # Return a list of user dictionaries the same as listOnUser
    def listUsers(self):
	pass

    # Return one user matching the username
    # Should be a dictionary;
    # {'username':username, 'password':cryptedPassword, 'roles':list_of_roles}
    def listOneUser(self, username):
	roles=[]

	# Attempt to aq the roles from the parent, this code
	# works inside a cmfsite but is not general case
	try:
	    portal   = self.portal_url.getPortalObject()
	    acl_users = portal.aq_parent.acl_users
	    roles += acl_users.getUser(username).getRolesInContext(portal)
	except:
	    pass

	# We store site specific roles in the prop source - only tested with zodbBTreeProps source
	xufRoles = self.currentPropSource.getUserProperty(username=username,
							  key=self.ROLES_KEY,
							  default=[])
	# getUserProperty returns None if user has no props
	if xufRoles:
	    roles += xufRoles

	# this happens when listOneUser is called before authenticate (?)
	if not roles:
	    roles = ['Anonymous']

	# LOG(self.id, DEBUG, username)
	# LOG(self.id, DEBUG, roles)
	return [{'username':username,
		 'password':'*****',
		 'roles':roles}]

    def authenticate(self, username, passwd):
	"""Authenticate a username/password combination
	against the HTTPS service"""


        ## Emergency override - uncomment this if you get locked out of your site
        ## return 1 
    
        # first check the authorization cache to minimize network traffic
        if self.isAuthenticCached(username, passwd):
            return 1
        elif self.isUnAuthenticCached(username, passwd):
            return 0
        
        
	auth = 0		
	# LOG(self.id, ERROR, "%s %s" % (username, passwd))

	params = urllib.urlencode({self.userNameParam: username,
                                   self.passwdParam: passwd})

        # by passing in params, this POSTs
        response = urllib.urlopen(self.serviceUrl, params)
        
	auth = self._parseResponse(response.read())
	
	# Everyone gets 'Authenticated' and the defaultRole
	# This also insures that user ends up in prop list upon first login
	if auth and not self.currentPropSource.getUserProperty(key=self.ROLES_KEY,
							       username=username,
							       default=None):
	    roles = ['Authenticated', self.defaultRole]
	    self.currentPropSource.setUserProperty(username=username,
						   key=self.ROLES_KEY,
						   value=roles)
        # store auth results in cache
        if auth:
            self.cacheAuth(username, passwd)
        else:
            self.cacheUnAuth(username, passwd)

	return auth

    # tell xuf to use our authenticate method
    remoteAuthMethod = authenticate

    def _parseResponse(self, response):
        """ Try to match the expected authorization regex against the response
            If its found, they're in"""

	# LOG(self.id, DEBUG, response)

	retVal = 0
	try:
            if self.authResponsePattern.match(response):
		retVal = 1
	    else:
		retVal = 0
	except Exception, e:
	    ERROR("%s: Could not parse the response. (response=%s, auth pattern=%s)" %
                  (e, response, self.authResponse))
	    retVal = 0

	return retVal


    #
    # cacheing methods
    #
    def isAuthenticCached(self, username, passwd):
        key = (username, passwd)
        now = time()
        if (self._v_authenticCache.has_key(key) and
            (now - self._v_authenticCache[key]) < self.CACHE_TIMEOUT):
            # LOG(self.id, ERROR, "Cached authentic user")
            return 1
        else:
            return 0

    def isUnAuthenticCached(self, username, passwd):
        key = (username, passwd)
        now = time()
        if (self._v_unAuthenticCache.has_key(key) and
            (now - self._v_unAuthenticCache[key]) < self.CACHE_TIMEOUT):
            # LOG(self.id, ERROR, "Cached UN-Authentic user")
            return 1
        else:
            return 0
        
    def cacheAuth(self, username, passwd):
        """Store successful auth attempts"""
        key = (username, passwd)
        timestamp = time()
        self._v_authenticCache[key] = timestamp


    def cacheUnAuth(self, username, passwd):
        """Store failed auth attempts"""
        # don't let the unauth cache grow unbounded
        if len(self._v_unAuthenticCache) > self.UNAUTH_CACHE_MAXSIZE:
            self._v_unAuthenticCache = {}

        key = (username, passwd)
        timestamp = time()
        self._v_unAuthenticCache[key] = timestamp

    def clearAuthCache(self):
        """clear the user cache"""
        self._v_authenticCache.clear()
        self._v_unAuthenticCache.clear()        


#
# Register the plugin and it's manage forms
#
httpsAuthReg=PluginRegister('httpsAuthSource',
			    'HTTPS Authentication Source',
			    httpsAuthSource,
			    manage_addhttpsAuthSourceForm,
			    manage_addhttpsAuthSource,
			    manage_edithttpsAuthSourceForm)
exUserFolder.authSources['httpsAuthSource']=httpsAuthReg

