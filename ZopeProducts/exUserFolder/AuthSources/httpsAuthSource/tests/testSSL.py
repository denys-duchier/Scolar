
#
# Not a real unit test.
# Just a test to make sure that ssl works inside your python
# Make sure to test using your Zope's python
#
from httplib import HTTPSConnection

HOSTNAME = 'mail.yahoo.com'  # or any other secure server..

conn = HTTPSConnection(HOSTNAME)
conn.putrequest('GET', '/')
conn.endheaders()
response = conn.getresponse()
print response.read()
