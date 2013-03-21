#
# Extensible User Folder
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
# $Id: UserCache.py,v 1.16 2003/07/10 21:11:26 akm Exp $

# Module Level Caches for Various User Operations

from time import time
from BTrees.OOBTree import OOBTree
import threading
from Acquisition import aq_inner
from Products.exUserFolder.User import User

class UserCacheItem:
	lastAccessed=0
	def __init__(self, username, password, cacheable):
		self.username=username
		self.password=password
		self.cacheable=cacheable
		self.lastAccessed=time()

	def touch(self):
		self.lastAccessed=time()
		
	def __repr__(self):
		return self.username

class NegativeUserCacheItem(UserCacheItem):
	def __init__(self, username):
		self.username=username
		self.lastAccessed=time()

class AdvancedCookieCacheItem(UserCacheItem):
	lastAccessed=0
	def __init__(self, username, password):
		self.username=username
		self.password=password
		self.lastAccessed=time()

SessionExpiredException='User Session Expired'
class UserCache:
	def __init__(self, sessionLength):
		self.sessionLength=sessionLength
		self.cache=OOBTree()
		self.hits=0
		self.fail=0
		self.nouser=0
		self.attempts=0
		self.timeouts=0
		self.cacheStarted=time()
		self.lock=threading.Lock()
		
	def addToCache(self, username, password, User):
		self.lock.acquire()		
		try:
			if not self.sessionLength:
				return

			try:
				u = self.cache.items(username)
				if u:
					for x in self.cache[username]:
						self.cache.remove(x)
			except:
				pass

			u = UserCacheItem(username, password, User._getCacheableDict())
			self.cache[username]=u
		finally:
			self.lock.release()

	def getUser(self, caller, username, password, checkpassword=1):
		self.lock.acquire()
		try:
			if not self.sessionLength:
				return None

			self.attempts=self.attempts+1

			u = None
			try:
				u = self.cache[username]
			except KeyError:
				self.nouser=self.nouser+1
				return None

			now = time()
			if u:
				if checkpassword and (u.password != password):
					self.fail=self.fail+1
					del self.cache[u.username]
				elif self.sessionLength and (
					(now - u.lastAccessed) > self.sessionLength):
					del self.cache[u.username]
					self.timeouts=self.timeouts+1
					user_object=User(u.cacheable,
									 caller.currentPropSource,
									 caller.cryptPassword,
									 caller.currentAuthSource,
									 caller.currentGroupSource)
					user_object.notifyCacheRemoval()
					del u
					raise SessionExpiredException
				else:
					u.touch()
					self.hits=self.hits+1
					return User(u.cacheable,
								caller.currentPropSource,
								caller.cryptPassword,
								caller.currentAuthSource,
								caller.currentGroupSource)

			self.nouser=self.nouser+1
			return None
		finally:
			self.lock.release()

	def removeUser(self, username):
		self.lock.acquire()
		try:
			if not self.sessionLength:
				return
			try:
				if self.cache[username]:
					del self.cache[username]
			except:
				pass
		finally:
			self.lock.release()

	def getCacheStats(self):
		self.lock.acquire()
		try:
			return (
				{'attempts':self.attempts,
				 'hits':self.hits,
				 'fail':self.fail,
				 'misses':self.nouser,
				 'cachesize':len(self.cache),
				 'time':self.cacheStarted,
				 'timeouts':self.timeouts,
				 'length':self.sessionLength})
		finally:
			self.lock.release()
		
	def getCurrentUsers(self, caller):
		self.lock.acquire()
		try:
			x=[]
			now = time()		
			for z in self.cache.keys():
				u = self.cache[z]
				if self.sessionLength and (
					(now - u.lastAccessed) > self.sessionLength):
					del self.cache[u.username]
					self.timeouts=self.timeouts+1
					user_object=User(u.cacheable,
									 caller.currentPropSource,
									 caller.cryptPassword,
									 caller.currentAuthSource,
									 caller.currentGroupSource)
					user_object.notifyCacheRemoval()
					del u
				else:
					x.append({'username':u.username,
							  'lastAccessed':u.lastAccessed})
			return x
		finally:
			self.lock.release()

class NegativeUserCache:
	def __init__(self, sessionLength):
		self.sessionLength=sessionLength
		self.cache=OOBTree()
		self.hits=0
		self.cacheStarted=time()
		self.lock=threading.Lock()
		
	def addToCache(self, username):
		self.lock.acquire()		
		try:
			if not self.sessionLength:
				return

			try:
				u = self.cache.items(username)
				if u:
					for x in self.cache[username]:
						self.cache.remove(x)
			except:
				pass

			u = NegativeUserCacheItem(username)
			self.cache[username]=u
		finally:
			self.lock.release()

	def getUser(self, username):
		self.lock.acquire()
		try:
			if not self.sessionLength:
				return 0

			u = None
			try:
				u = self.cache[username]
			except KeyError:
				return 0

			now = time()
			if u:
				if self.sessionLength and (
					(now - u.lastAccessed) > self.sessionLength):
					del self.cache[u.username]
				else:
					# We don't touch negative user caches
					# u.touch()
					self.hits=self.hits+1
					return 1
			return 0
		finally:
			self.lock.release()

	def removeUser(self, username):
		self.lock.acquire()
		try:
			if not self.sessionLength:
				return
			try:
				del self.cache[username]
			except:
				pass
		finally:
			self.lock.release()					

class CookieCache:
	def __init__(self, sessionLength):
		self.sessionLength=sessionLength
		self.cache=OOBTree()
		self.hits=0
		self.cacheStarted=time()
		self.lock=threading.Lock()
		
	def addToCache(self, username, password, key):
		self.lock.acquire()		
		try:
			if not self.sessionLength:
				return

			try:
				u = self.cache.items(key)
				if u:
					for x in self.cache[key]:
						self.cache.remove(x)
			except:
				pass
			u = AdvancedCookieCacheItem(username, password)
			self.cache[key]=u
		finally:
			self.lock.release()

	def getUser(self, key):
		self.lock.acquire()
		try:
			if not self.sessionLength:
				return None

			u = None
			try:
				u = self.cache[key]
			except KeyError:
				return None

			now = time()
			if u:
				if self.sessionLength and (
					(now - u.lastAccessed) > self.sessionLength):
					del self.cache[key]
				else:
					# We don't touch negative user caches
					# u.touch()
					self.hits=self.hits+1
					return u.username, u.password
			return None
		finally:
			self.lock.release()

	def removeUser(self, key):
		self.lock.acquire()
		try:
			if not self.sessionLength:
				return
			try:
				del self.cache[key]
			except:
				pass
		finally:
			self.lock.release()

class GlobalUserCache:
	caches={}
	def __init__(self):
		self.lock = threading.Lock()

	def createCache(self, who, sessionLength):
		self.lock.acquire()
		try:
			self.caches[who]=UserCache(sessionLength)
			return self.caches[who]
		finally:
			self.lock.release()

	def getCache(self, who):
		self.lock.acquire()
		try:
			if self.caches.has_key(who):
				return self.caches[who]
			else:
				return None
		finally:
			self.lock.release()
			
	def deleteCache(self, who):
		self.lock.acquire()
		try:
			del self.caches[who]
		finally:
			self.lock.release()

class GlobalNegativeUserCache:
	caches={}
	def __init__(self):
		self.lock = threading.Lock()

	def createCache(self, who, sessionLength):
		self.lock.acquire()
		try:
			self.caches[who]=NegativeUserCache(sessionLength)
			return self.caches[who]
		finally:
			self.lock.release()

	def getCache(self, who):
		self.lock.acquire()
		try:
			if self.caches.has_key(who):
				return self.caches[who]
			else:
				return None
		finally:
			self.lock.release()
			
	def deleteCache(self, who):
		self.lock.acquire()
		try:
			del self.caches[who]
		finally:
			self.lock.release()

class GlobalAdvancedCookieCache:
	caches={}
	def __init__(self):
		self.lock = threading.Lock()

	def createCache(self, who, sessionLength):
		self.lock.acquire()
		try:
			self.caches[who]=CookieCache(sessionLength)
			return self.caches[who]
		finally:
			self.lock.release()

	def getCache(self, who):
		self.lock.acquire()
		try:
			if self.caches.has_key(who):
				return self.caches[who]
			else:
				return None
		finally:
			self.lock.release()
			
	def deleteCache(self, who):
		self.lock.acquire()
		try:
			del self.caches[who]
		finally:
			self.lock.release()
	
