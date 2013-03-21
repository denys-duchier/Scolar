#
# Extensible User Folder
#
# (C) Copyright 2000-2004 The Internet (Aust) Pty Ltd
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
# $Id: pass_crypt.py,v 1.3 2004/11/18 09:24:46 akm Exp $

from Products.exUserFolder.exUserFolder import exUserFolder
from Products.exUserFolder.Plugins import CryptoPluginRegister

try:
	from crypt import crypt
except:
	from fcrypt.fcrypt import crypt


def cryptPassword(authSource, username, password):
	u = authSource.listOneUser(username)
	if not u:
		salt = username[:2]
	else:
		salt=u[0]['password'][:2]

	secret = crypt(password, salt)
	return secret
	

CryptPlugin=CryptoPluginRegister('Crypt', 'crypt', 'Crypt', cryptPassword)
exUserFolder.cryptoSources['Crypt']=CryptPlugin
