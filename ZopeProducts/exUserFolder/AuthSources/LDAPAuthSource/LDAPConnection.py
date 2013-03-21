import ldap
import threading

class LDAPConnection:
	def __init__(self, ldapConn, lock, bounddn, host, port, boundas):
		self.ldapConn = ldapConn
		self.lock = lock
		self.bounddn = bounddn
		self.host = host
		self.port = port
		self.boundas = boundas


	def init(self):
		try:
			self.ldapConn = ldap.open(self.host, self.port)
			
		except:
			import traceback as tb
			zLOG.LOG(LOG_STRING, 100, string.join(
				tb.format_exception_only(sys.exc_type, sys.exc_value)))

			self.ldapConn = None


