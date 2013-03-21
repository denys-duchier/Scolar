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
# $Id: usAuthSourceMethods.py,v 1.3 2001/12/01 08:40:04 akm Exp $
#
########################################################################
#
# This is an example of an Extension Module to provide User Supplied 
# Authentication Methods.
# 
# It mimics the behaviour of the pgAuthSource Module, and the sql queries
# Used here would be added as ZSQLMethods in the usAuthSource Folder.
# (you can basically cut and paste them from the bottom of this .py file
# into the ZSQL Method Template Area
#
# It's not complete, but, you do get the idea...
#
# Each function becomes usFunctionName
#
# e.g. listOneUser -> usListOneUser
#
import string
from crypt import crypt

def listOneUser(self,username):
	users = []
	result=self.sqlListOneUser(username=username)
	for n in result:
		username=sqlattr(n,'username')
		password=sqlattr(n,'password')
		roles=string.split(sqlattr(n,'roles'))
		N={'username':username, 'password':password, 'roles':roles}
		users.append(N)
	return users

def listUsers(self):
	"""Returns a list of user names or [] if no users exist"""		
	users = []
	result=self.sqlListUsers()
	for n in result:
		username=sqlattr(n,'username')
		N={'username':username}
		users.append(N)
	return users	

def getUsers(self):
	"""Return a list of user objects or [] if no users exist"""
	data=[]
	try:    items=self.listusers()
	except: return data
	for people in items:
		roles=string.split(people['roles'],',')
		user=User(people['username'], roles, '')
		data.append(user)
	return data

def cryptPassword(self, username, password):
		salt =username[:2]
		secret = crypt(password, salt)
		return secret

def deleteUsers(self, userids):
	for uid in userids:
		self.sqlDeleteOneUser(userid=uid)


# Helper Functions...
from string import upper, lower
import Missing
mt=type(Missing.Value)

def typeconv(val):
    if type(val)==mt:
        return ''
    return val

def sqlattr(ob, attr):
    name=attr
    if hasattr(ob, attr):
        return typeconv(getattr(ob, attr))
    attr=upper(attr)
    if hasattr(ob, attr):
        return typeconv(getattr(ob, attr))
    attr=lower(attr)
    if hasattr(ob, attr):
        return typeconv(getattr(ob, attr))
    raise NameError, name


########################################################################
# SQL METHODS USED ABOVE
# PASTE INTO ZSQL METHODS
# take note of what parameters are used in each query
########################################################################

_sqlListUsers="""
SELECT * FROM passwd
"""

_sqlListOneUser="""
SELECT * FROM passwd
where username=<dtml-sqlvar username type=string>
"""

_sqlDeleteOneUser="""
DELETE FROM passwd
where uid=<dtml-sqlvar userid type=int>
"""

_sqlInsertUser="""
INSERT INTO passwd (username, password, roles)
VALUES (<dtml-sqlvar username type=string>,
        <dtml-sqlvar password type=string>,
		<dtml-sqlvar roles type=string>)
"""

_sqlUpdateUserPassword="""
UPDATE passwd set password=<dtml-sqlvar password type=string>
WHERE username=<dtml-sqlvar username type=string>
"""

_sqlUpdateUser="""
UPDATE passwd set roles=<dtml-sqlvar roles type=string>
WHERE username=<dtml-sqlvar username type=string>
"""

