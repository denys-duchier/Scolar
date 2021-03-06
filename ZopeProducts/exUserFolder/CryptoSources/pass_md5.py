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
# $Id: pass_md5.py,v 1.1 2004/11/10 14:15:52 akm Exp $

import md5, base64, string

from Products.exUserFolder.exUserFolder import exUserFolder
from Products.exUserFolder.Plugins import CryptoPluginRegister

# Simple digest
def cryptPassword(authSource, username, password):
	digest = md5.new()
	digest.update(password)
	digest = digest.digest()
	secret = string.strip(base64.encodestring(digest))
	return secret

# Digest includes username
# So two passwords for different users hash differently
def cryptPassword2(authSource, username, password):
	newPass = username+':'+password
	return cryptPassword(authSource, username, newPass)


MD5Plugin1=CryptoPluginRegister('MD51', 'MD5', 'MD5 Password Only', cryptPassword)
exUserFolder.cryptoSources['MD51']=MD5Plugin1

MD5Plugin2=CryptoPluginRegister('MD52', 'MD5', 'MD5 Username + Password', cryptPassword2)
exUserFolder.cryptoSources['MD52']=MD5Plugin2
