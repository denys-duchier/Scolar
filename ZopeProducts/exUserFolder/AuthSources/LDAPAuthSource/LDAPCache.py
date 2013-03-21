import time

def urlNodeCompare(a, b):
	return cmp(a.url, b.url)

def searchNodeCompare(a, b):
	return cmp(a.username, b.username)

def compareNodeCompare(a, b):
	return ( cmp(a.dn, b.dn) == 0 and
			 cmp(a.attrib, b.attrib) == 0 and
			 cmp(a.value, b.value) == 0 )

def dnCompareNodeCompare(a, b):
	return cmp(a.reqdn, b.reqdn)

def connectionNodeCompare(a, b):
	return cmp(a.ldapConn, b.ldapConn)

class URLNode:
	def __init__(self, url, search, compare, dn_compare):
		self.url = url
		self.search_cache = search
		self.compare_cache = compare
		self.dn_compare_cache=dn_compare

class SearchNode:
	def __init__(self, username, dn, bindpw, lastbind):
		self.username = username
		self.dn = dn
		self.bindpw = bindpw
		self.lastbind = lastbind

class CompareNode:
	def __init__(self, dn, attrib, value, lastcompare):
		self.dn = dn
		self.attrib = attrib
		self.value = value
		self.lastcompare = lastcompare

class DNCompareNode:
	def __init__(self, reqdn, dn=''):
		self.dn=dn
		self.reqdn=reqdn

class CacheNode:
	def __init__(self, payload):
		self.payload = payload
		self.add_time = time.time()

	def __del__(self):
		del self.payload
	

class LDAPCache:
	def __init__(self, maxentries, cmpare=cmp, hashfunc=hash):

		self.maxentries = int(maxentries)

		self.size = self.maxentries / 3

		if self.size < 64:
			self.size = 64
			
		self.fullmark = self.maxentries / 4 * 3
		
		self.numentries = 0

		self.marktime=0.0
		self.cache_nodes={}
		self.numpurges = 0
		self.avg_purgetime=0.0
		self.last_purge = 0.0
		self.npurged = 0
		self.fetches = 0
		self.hits = 0
		self.inserts = 0
		self.removes = 0
		self.cmpare=cmpare
		self.hashfunc=hash

	def __del__(self):
		for p in self.cache_nodes.values():
			del p

	def fetch(self, payload):
		self.fetches = self.fetches + 1
		pHash = self.hashfunc(payload)

		entries = self.cache_nodes.get(pHash, [])
		for p in entries:
			if self.cmpare(payload, p.payload) == 0:
				return p.payload

	def insert(self, payload):
		pHash=self.hashfunc(payload)
		entries = self.cache_nodes.get(pHash, [])
		entries.append(CacheNode(payload))
		self.cache_nodes[pHash]=entries
		self.numentries = self.numentries + 1
		if self.numentries == self.fullmark:
			self.marktime = time.time()
		if self.numentries >= self.maxentries:
			self.purge()

	def purge(self):
		self.last_purge = time.time()
		self.npurged = 0
		self.numpurges = self.numpurges + 1

		for k,n in self.cache_nodes.items():
			index = 0
			indices=[]
			for p in n:
				if p.add_time < self.marktime:
					indices.append(index)

			indices.reverse()
			for i in indices:
				del n[i]
				self.numentries = self.numentries - 1
				self.npurged = self.npurged + 1
			self.cache_nodes[k]=n

		t = time.time()
		self.avg_purgetime = (
			(t - self.last_purge) +
			(self.avg_purgetime * (self.numpurges-1))) / self.numpurges

	def remove(self, payload):
		pHash = self.hashfunc(payload)
		entries = self.cache_nodes.get(pHash, [])
		index = 0
		for p in entries:
			if self.cmpare(payload, p.payload)==0:
				del entries[index]
				self.cache_nodes[pHash]=entries
				self.numentries = self.numentries - 1
				break
			index = index + 1
		
	
def LDAPCreateCache(maxentries, nodeCompare=cmp, nodeHash=hash):
	if maxentries <= 0:
		return None

	cache = LDAPCache(maxentries, nodeCompare, nodeHash)
	return cache

def LDAPDestoryCache(cache):
	del cache

def LDAPCacheFetch(cache, payload):
	return cache.fetch(payload)

def LDAPCacheInsert(cache, payload):
	return cache.insert(payload)

def LDAPCacheRemove(cache, payload):
	return cache.remove(payload)
