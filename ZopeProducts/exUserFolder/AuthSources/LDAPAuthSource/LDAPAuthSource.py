import string, Acquisition, sys

from Globals import HTMLFile, MessageDialog, INSTANCE_HOME

from OFS.Folder import Folder

from Products.exUserFolder.exUserFolder import exUserFolder
from Products.exUserFolder.Plugins import PluginRegister

import ldap
import ldapurl
import sys
import time
import threading
import zLOG

bind_none = 1
bind_system = 2
bind_user = 3

LOG_STRING="XUF.LDAPAuthSource"

def manage_addLDAPAuthSource(self, REQUEST):
	""" Add a LDAP Auth Source """

	# Required
	url = REQUEST['LDAPUrl']
	compareDNOnServer = REQUEST['LDAPCompareDNOnServer']
	drefAliases = REQUEST['LDAPDereferenceAliases']
	startTLS = REQUEST['LDAPStartTLS']

	# Optional
	binddn = REQUEST.get('LDAPBindDN', '')
	bindPassword = REQUEST.get('LDAPBindPassword', '')

	certDBPath = REQUEST.get('LDAPCertDBPath', '')

	groupAttribute = REQUEST.get('LDAPGroupAttribute','')
	groupAttributeIsDn = REQUEST.get('LDAPGroupAttributeIsDN', 0)

	requireGroup = REQUEST.get('LDAPRequireGroup', [])
	requireUser = REQUEST.get('LDAPRequireUser', [])
	requireDN = REQUEST.get('LDAPRequireDN', '')
	
	defaultRole = REQUEST.get('LDAPDefaultRole', '')
	defaultManager = REQUEST.get('LDAPDefaultManager', '')
	searchCacheSize = REQUEST.get('LDAPSearchCacheSize', 0)
	compareCacheSize = REQUEST.get('LDAPCompareCacheSize', 0)
	searchCacheTTL = REQUEST.get('LDAPSearchCacheTTL', 0)
	compareCacheTTL = REQUEST.get('LDAPCompareCacheTTL', 0)	
	
	ob=LDAPAuthSource(url, compareDNOnServer, drefAliases, startTLS,
					  binddn, bindPassword, certDBPath, groupAttribute,
					  groupAttributeIsDn, defaultRole, searchCacheSize,
					  compareCacheSize, searchCacheTTL, compareCacheTTL,
					  defaultManager, requireUser, requireGroup, requireDN)

	self._setObject('LDAPAuthSource', ob, None, None, 0)
	self.currentAuthSource=ob       


manage_addLDAPAuthSourceForm=HTMLFile('manage_addLDAPAuthSourceForm', globals())
manage_editLDAPAuthSourceForm=HTMLFile('manage_editLDAPAuthSourceForm', globals())

from LDAPCache import *
from LDAPConnection import *

LDAP_CACHE = LDAPCreateCache(50, nodeCompare=urlNodeCompare)
CONN_CACHE = []

class LDAPAuthSource(Folder):
	meta_type='Authentication Source'
	id       ='LDAPAuthSource'
	title    ='LDAP Authentication'
	icon     ='misc_/exUserFolder/exUserFolderPlugin.gif'
	

	manage_editForm=manage_editLDAPAuthSourceForm
	manage_tabs = Acquisition.Acquired

	def __init__(self, url, compareDnOnServer, drefAliases, startTLS,
				 binddn='', bindPassword='', certDBPath='',
				 groupAttribute='', groupAttributeIsDN = 0,
				 defaultRole = '', searchCacheSize=0, compareCacheSize=0,
				 searchCacheTTL=0, compareCacheTTL=0, defaultManager='',
				 requireUser=[], requireGroup=[], requireDN=''):

		self.setParams(url, compareDnOnServer, drefAliases, startTLS,
					  binddn, bindPassword, certDBPath, groupAttribute,
					  groupAttributeIsDN, defaultRole, searchCacheSize,
					  compareCacheSize, searchCacheTTL, compareCacheTTL,
					  defaultManager, requireUser, requireGroup, requireDN
					   )
		

	def setParams(self,url, compareDnOnServer, drefAliases, startTLS,
				 binddn='', bindPassword='', certDBPath='',
				 groupAttribute='', groupAttributeIsDN = 0,
				 defaultRole = '', searchCacheSize=0, compareCacheSize=0,
				 searchCacheTTL=0, compareCacheTTL=0, defaultManager='',
				 requireUser=[], requireGroup=[], requireDN=''):
		self.url = url
		self.compareDNOnServer = compareDnOnServer
		self.dereferenceAliases = drefAliases
		self.startTLS = startTLS
		self.bindDN = binddn
		self.bindPassword = bindPassword
		self.certDBPath = certDBPath
		self.groupAttribute = groupAttribute
		self.groupAttributeIsDN = groupAttributeIsDN
		self.defaultRole = defaultRole
		self.searchCacheSize=searchCacheSize
		self.compareCacheSize=compareCacheSize
		self.searchCacheTTL=searchCacheTTL
		self.compareCacheTTL=compareCacheTTL
		self.defaultManager=defaultManager
		self.requireGroup=requireGroup
		self.requireUser=requireUser
		self.requireDN=requireDN

		result = ldapurl.LDAPUrl(self.url)
		self._basedn=result.dn
		self._filter=result.filterstr
		if not self._filter:
			self._filter='(objectClass=*)'
			
		self._scope=result.scope
		if not self._scope:
			self._scope = ldap.SCOPE_SUB
		self._attribute=result.attrs
		self._hostport=result.hostport
		self._urlscheme=result.urlscheme
		hostport=string.split(self._hostport, ':')
		self._host=hostport[0]
		if len(hostport) == 2:
			self._port = int(hostport[1])
		else:
			if self._urlscheme=='ldap':
				self._port=389
			elif self._urlscheme=='ldaps':
				self._port=636
			else:
				# Ack..
				self._port=0
		
				  
	def manage_editAuthSource(self, REQUEST):
		""" Handle Editing LDAP Auth Params """
		# Required
		url = REQUEST['LDAPUrl']
		compareDNOnServer = REQUEST['LDAPCompareDNOnServer']
		drefAliases = REQUEST['LDAPDereferenceAliases']
		startTLS = REQUEST['LDAPStartTLS']

		# Optional
		binddn = REQUEST.get('LDAPBindDN', '')
		bindPassword = REQUEST.get('LDAPBindPassword', '')

		certDBPath = REQUEST.get('LDAPCertDBPath', '')

		groupAttribute = REQUEST.get('LDAPGroupAttribute','')
		groupAttributeIsDN = REQUEST.get('LDAPGroupAttributeIsDN', 0)

		requireGroup = REQUEST.get('LDAPRequireGroup', [])
		requireUser = REQUEST.get('LDAPRequireUser', [])
		requireDN = REQUEST.get('LDAPRequireDN', '')
		
		defaultRole = REQUEST.get('LDAPDefaultRole', '')
		defaultManager = REQUEST.get('LDAPDefaultManager', '')
		searchCacheSize = REQUEST.get('LDAPSearchCacheSize', 0)
		compareCacheSize = REQUEST.get('LDAPCompareCacheSize', 0)
		searchCacheTTL = REQUEST.get('LDAPSearchCacheTTL', 0)
		compareCacheTTL = REQUEST.get('LDAPCompareCacheTTL', 0)	

		self.setParams(url, compareDNOnServer, drefAliases, startTLS,
					  binddn, bindPassword, certDBPath, groupAttribute,
					  groupAttributeIsDN, defaultRole, searchCacheSize,
					  compareCacheSize, searchCacheTTL, compareCacheTTL,
					  defaultManager, requireUser, requireGroup, requireDN)
		
		if REQUEST is not None:
			return self.MessageDialog(
				title = 'Edited',
				message = "Properties for %s changed." % self.id,
				action = 'manage_editLDAPAuthSourceForm')
		return ''

	def deleteUsers(self, userids):
		pass

	def createUser(self, username, password, roles):
		pass

	def updateUser(self, username, password, roles):
		self.currentPropSource.setUserProperty(username=username,
											   key='roles', value=roles)

	def listUserNames(self):
		return []

	def listUsers(self):
		return []

	def getUsers(self):
		return []

	def _ldap_createCaches(self):
		sCache = LDAPCreateCache(self.searchCacheSize, nodeCompare=searchNodeCompare)
		cCache = LDAPCreateCache(self.compareCacheSize, nodeCompare=compareNodeCompare)
		dnCache = LDAPCreateCache(self.compareCacheSize, nodeCompare=dnCompareNodeCompare)
		curl = URLNode(self.url, sCache, cCache, dnCache)

		LDAPCacheInsert(LDAP_CACHE, curl)
		return curl
		

	def _ldap_buildFilter(self, username):
		filter = "(&%s(%s=%s))"%(self._filter, self._attribute[0], username)
		return filter

	def listOneUser(self, username):

		l = self._ldap_Open()
		if not l:
			return []
		results = self._ldap_userExists(l, username)

		if not results:
			return []

		roles=[]
		if self.currentPropSource:
			roles = self.currentPropSource.getUserProperty(username=username, key='_roles', default=[])

		if not roles:
			roles=[]
		if self.defaultRole and self.defaultRole not in roles:
			roles.append(self.defaultRole)

		if self.defaultManager and self.defaultManager==username:
			roles.append('Manager')

		dn = results[0]
		data = results[1]
		self.currentPropSource.setUserProperty(username=username, key='dn', value=dn)
		for k,v in data.items():
			self.currentPropSource.setUserProperty(username=username, key=k, value=v)

		return [{'username':username, 'password':'', 'roles':roles},]

	def getConnections(self):
		return CONN_CACHE

	def addConnection(self, l):
		CONN_CACHE.append(l)

	def deleteConnection(self, l):
		index = 0
		for ll in self.getConnections:
			if l == ll:
				del CONN_CACHE[index]
				break
			index = index + 1

	def getLDAPCache(self, key):
		return LDAPCacheFetch(LDAP_CACHE, key)

	def _ldap_FindConnection(self):
		zLOG.LOG(LOG_STRING,
				 100,
				 "Entering _ldapFindConnection")
		connections = self.getConnections()
		l = None
		for l in connections:
			if ( l.port == self._port and
				 l.host == self._host ):
				zLOG.LOG(LOG_STRING,
						 100,
						 "Found a Cached One")
				break
		else:
			l = None

		if l:
			if ( (self.bindDN and not l.bounddn) or
				 (not self.bindDN and l.bounddn) or
				 ((self.bindDN and l.bounddn) and self.bindDN != l.bounddn)):
				l.boundas = bind_none
			else:
				l.boundas = bind_system
		else:
			lock=threading.Lock()
			l = LDAPConnection(None, lock, None, self._host, self._port, bind_none)
			self.addConnection(l)
		return l

	def _ldap_Open(self):
		l = self._ldap_FindConnection()
		connected = self._ldap_connectToServer(l)
		if not connected:
			return None
		return l
			
	def _ldap_userExists(self, l, username):
		
		result = []
		filter = self._ldap_buildFilter(username)

		zLOG.LOG(LOG_STRING, 100, "Filter: %s"%(filter))
		
		try:
			result = l.ldapConn.search_s(self._basedn, self._scope, filter)
		except:
			import traceback as tb
			zLOG.LOG(LOG_STRING, 100, string.join(
				tb.format_exception_only(sys.exc_type, sys.exc_value)))
			return None

		resultData = result

		if len(resultData) != 1:
			zLOG.LOG(LOG_STRING, 100, "Multiple Results: %d"%(len(resultData)))
			return None

		thisResult=resultData[0]

		curl = self.getLDAPCache(self.url)
		if not curl:
			curl = self._ldap_createCaches()

		dn = thisResult[0]
		if self.requireDN:
			if not dn:
				zLOG.LOG(LOG_STRING, 100,
						 "The User's DN has not been defined: failing auth")
				return None
			result = self._ldap_comparedn(l, dn, self.requireDN, curl)
			if result:
				return thisResult
			
		if self.requireUser:
			if not dn:
				zLOG.LOG(LOG_STRING, 100,
						 "The User's DN has not been defined: failing auth")
				return None
			for t in self.requireUser:
				if not t: # lines gives us one empty one..
					continue
				result = self._ldap_compare(l, dn, self._attribute, t, curl.compare_cache)
				if result:
					return thisResult

				for tt in string.split(t):
					result = self._ldap_compare(l, dn, self._attribute, tt, curl.compare_cache)
					if result:
						return thisResult
		if self.requireGroup:
			if self.groupAttributeIsDN:
				if not dn:
					zLOG.LOG(LOG_STRING, 100,
							 "The User's DN has not been defined: failing auth")
					return 0
			w = 'group'
			for t in self.requireGroup:
				if not t:
					continue
				zLOG.LOG(LOG_STRING, 100,
						 "testing for group membership in '%s'"%(t))
				for ent in self.groupAttribute:
					if not ent:
						continue
					zLOG.LOG(LOG_STRING, 100,
							 "testing for group membership in %s=%s"%(ent,
																	  [username,dn][self.groupAttributeIsDN]))
					result = self._ldap_compare(l, t, ent, 
												[username,dn][self.groupAttributeIsDN],
												curl.dn_compare_cache)
					if result:
						return thisResult
		
		return thisResult

	def _ldap_comparedn(self, ldc, dn, reqdn, curl):
		if not self.compareDNOnServer:
			return cmp(dn, reqdn) == 0

		newnode = DNCompareNode(reqdn)
		node = curl.dnCompareCache.fetch(newnode)
		if node:
			return 1
		
		try:
			ldc.lock.acquire()
			connected = self._ldap_connectToServer(ldc)
			if not connected:
				return 0
			try:
				result = ldc.ldapConn.search_ext_s(reqdn, ldap.SCOPE_BASE,
												   '(objectclass=*)',
												   None, 1)
			except:
				return 0
			if result != ldap.SUCCESS:
				return 0

			entry = result[0]
			searchdn=entry[0]
			if dn != searchdn:
				return 0
			newnode.dn = dn
			curl.dnCompareCache.insert(newnode)
			return 1
		finally:
			ldc.lock.release()
			

	def _ldap_compare(self, ldc, dn, attrib, value, cache):
		curtime = time.time()
		theCompareNode=CompareNode(dn, attrib, value, 0.0)
		compare_node = cache.fetch(theCompareNode)
		if compare_node:
			zLOG.LOG(LOG_STRING, 100,
					 "Found It...")
			if (curtime - compare_node.lastcompare) > self.compareCacheTTL:
				zLOG.LOG(LOG_STRING, 100,
						 "...but it's too old.")
				cache.remove(compare_node)
			else:
				zLOG.LOG(LOG_STRING, 100,
						 "...and it's good.")
				return 1
		try:
			ldc.lock.acquire()
			connected = self._ldap_connectToServer(ldc)
			if not connected:
				return 0

			zLOG.LOG(LOG_STRING, 100,
					 "Doing LDAP compare of %s=%s in entry %s"%(attrib, value, dn))
			zLOG.LOG(LOG_STRING, 100,
					 "LDAP OP: compare")

			try:
				result = ldc.ldapConn.compare_s(dn, attrib, value)
			except ldap.SERVER_DOWN:
				self.freeConnection(ldc, 1)
				return 0

			if result == ldap.COMPARE_TRUE:
				zLOG.LOG(LOG_STRING, 100,
						 "Compare succeeded; caching result")
				compare_node.lastcompare=curtime
				cache.insert(compare_node)
				return 1
			zLOG.LOG(LOG_STRING, 100,
					 "Compare failed")
			return 0
		finally:
			ldc.lock.release()
			
	def _ldap_connectToServer(self, l):

		zLOG.LOG(LOG_STRING, 100,
				 "Entering _ldap_connectToServer")
		
		if not l.ldapConn:
			l.boundas=bind_none
			if l.bounddn:
				l.bounddn = None

			zLOG.LOG(LOG_STRING, 100,
					 "Opening Connection to ldap server(s) '%s'"%(self._host))
			zLOG.LOG(LOG_STRING, 100,
					 "LDAP OP: init")

			l.init()			
			if not l.ldapConn:
				zLOG.LOG(LOG_STRING, 100,
						 "Could not connect to LDAP server")
				return 0

			try:
				result = l.ldapConn.set_option(ldap.OPT_REFERRALS, 0)
			except:
				zLOG.LOG(LOG_STRING, 100,
						 "Setting LDAP REFERRAL Option")
				return 0

			try:
				l.ldapConn.set_option(ldap.OPT_DEREF, self.dereferenceAliases)
			except:
				zLOG.LOG(LOG_STRING, 100,
						 "Setting LDAP dereference option failed")
				
			if self.startTLS and 0:
				version = ldap.VERSION3
				try:
					result = l.ldapConn.set_option(ldap.OPT_PROTOCOL_VERSION, version)
				except:
					zLOG.LOG(LOG_STRING, 100,
							 "Setting LDAP version option failed")
					return 0

				zLOG.LOG(LOG_STRING, 100,
						 "Starting TLS for this connection")
				l.withtls = 1
				try:
					l.ldapConn.start_tls_s()
				except:
					zLOG.LOG(LOG_STRING, 100,
							 "Start TLS Failed.")
					return 0
			else:
				l.withtls=0

		if l.boundas == bind_system:
			return 1

		zLOG.LOG(LOG_STRING, 100,
				 "Binding to server '%s' as %s/%s"%(self._host,
													self.bindDN,
													self.bindPassword))

		zLOG.LOG(LOG_STRING, 100,
				 "LDAP OP: simple bind")
		
		result = l.ldapConn.simple_bind(self.bindDN, self.bindPassword)

		zLOG.LOG(LOG_STRING, 100, "Simple Bind returned: %d"%(result))

		if result == ldap.SERVER_DOWN:
			zLOG.LOG(LOG_STRING, 100,
					 "Server Down: Could not bind to LDAP server '%s' as %s: %s"%(
				self._host,
				self.bindDN,
				self.bindPassword))
			self.freeConnection(l, 1)
			return 0

		if result != 1:
			self.freeConnection(l)
			zLOG.LOG(LOG_STRING, 100,
					 "Could not bind to LDAP server '%s' as %s: %s"%(self._host,
																	 self.bindDN,
																	 self.bindPassword))
			return 0

		l.bounddn = self.bindDN
		l.boundas = bind_system
		return 1

	def freeConnection(self, ldc, log=0):

		if log:
			zLOG.LOG(LOG_STRING, 100,
					 "Server is down")
		if ldc.ldapConn:
			zLOG.LOG(LOG_STRING, 100,
					 "Freeing connection to ldap server(s) '%s'"%(self._host))
			ldc.ldapConn.unbind_s()
			ldc.ldapConn=None
			ldc.boundas = bind_none
			if ldc.bounddn:
				ldc.bounddn=None

		self.deleteConnection(ldc)

	def remoteAuthMethod(self, username, password):

		zLOG.LOG(LOG_STRING, 100,
				 "Entering remoteAuthMethod")

		l = self._ldap_FindConnection()
		curl = self.getLDAPCache(self.url)
		if not curl:
			curl = self._ldap_createCaches()
		
		if not l:
			zLOG.LOG(LOG_STRING,
					 100, "Could not find/create LDAPConnection")
			return 0

		zLOG.LOG(LOG_STRING, 100,
				 "Using URL: %s"%(self.url))

		searchNode = curl.search_cache.fetch(username)
		if searchNode and searchNode.bindpw:
			zLOG.LOG(LOG_STRING, 100,
					 "Found entry in cache for '%s'..."%(username))
			curtime=time.time()
			if curtime == searchNode.lastBind > self.searchCacheTTL:
				zLOG.LOG(LOG_STRING, 100,
						 "... but entry is too old (%d seconds)"%(curtime-searchnode.lastbind))
				curl.search_cache.remove(username)
			elif searchNode.bindpw != password:
				zLOG.LOG(LOG_STRING, 100,
						 "... but entry password doesn't match")
				curl.search_cache.remove(username)
			else:
				zLOG.LOG(LOG_STRING, 100,
						 "... and entry is valid")
				return 1

		zLOG.LOG(LOG_STRING, 100,
				 "Entry for %s is not in the cache"%(username))

		filtbuf = self._ldap_buildFilter(username)
		try:
			l.lock.acquire()

			if not self._ldap_connectToServer(l):
				return 0

			zLOG.LOG(LOG_STRING, 100,
					 "Performing a search (scope = %d) with filter %s"%(
				self._scope, filtbuf))

			zLOG.LOG(LOG_STRING, 100,
					 "LDAP OP: search")

			result = None
			try:
				result = l.ldapConn.search_s(self._basedn, self._scope,
											 filtbuf)
			except ldap.SERVER_DOWN:
				self.freeConnection(l, 1)
				return 0
			except:
				zLOG.LOG(LOG_STRING, 100,
						 "LDAP search for %s failed: LDAP error: %s; URI %s"%(
					filtbuf, result, self.url))
				return 0

			resultData=result
			count = len(resultData)
			if count != 1:
				zLOG.LOG(LOG_STRING, 100,
						 "Search must return exactly 1 entry; found %s entries for search %s: URI %s"%(count, filtbuf, self.url))
				return 0

			
			entry=resultData[0]
			dn=entry[0]
			zLOG.LOG(LOG_STRING, 100,
					 "DN returned from search is %s"%(dn))

			if len(password) <= 0:
				zLOG.LOG(LOG_STRING, 100,
						 "Empty Password")

				return 0

			zLOG.LOG(LOG_STRING, 100,
					 "Validating user '%s' via bind"%(username))

			zLOG.LOG(LOG_STRING, 100,
					 "LDAP OP: simple bind")

			l.boundas = bind_user

			try:
				result = l.ldapConn.simple_bind_s(dn, password)
			except ldap.SERVER_DOWN:
				self.freeConnection(l, 1)
				return 0
			except e:
				zLOG.LOG(LOG_STRING, 100,
						 "User bind as %s failed: LDAP error: %s; URI %s"%(
					dn, e, self.url))
				return 0

			zLOG.LOG(LOG_STRING, 100,
					 "authenticate: accepting")

		finally:
			l.lock.release()

		zLOG.LOG(LOG_STRING, 100,
				 "Adding user '%s' to the cache"%(dn))

		sNode = SearchNode(username, dn, password, time.time())
		curl.search_cache.insert(sNode)
		return 1

LDAPAuthReg=PluginRegister('LDAPAuthSource', 'LDAP Authentication Source', LDAPAuthSource, manage_addLDAPAuthSourceForm, manage_addLDAPAuthSource, manage_editLDAPAuthSourceForm)
exUserFolder.authSources['LDAPAuthSource']=LDAPAuthReg
