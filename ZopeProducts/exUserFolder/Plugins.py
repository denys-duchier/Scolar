#
#
# (C) Copyright 2001 The Internet (Aust) Pty Ltd
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
# $Id: Plugins.py,v 1.5 2004/11/10 14:15:33 akm Exp $

import App, Globals, OFS
import string
import time

from Globals import ImageFile, HTMLFile, HTML, MessageDialog, package_home
from OFS.Folder import Folder

class PluginRegister:
	def __init__(self, name, description, pluginClass,
				 pluginStartForm, pluginStartMethod,
				 pluginEditForm=None, pluginEditMethod=None):
		self.name=name #No Spaces please...
		self.description=description
		self.plugin=pluginClass
		self.manage_addForm=pluginStartForm
		self.manage_addMethod=pluginStartMethod
		self.manage_editForm=pluginEditForm
		self.manage_editMethod=pluginEditMethod

class CryptoPluginRegister:
	def __init__(self, name, crypto, description, pluginMethod):
		self.name = name #No Spaces please...
		self.cryptoMethod = crypto 
		self.description = description
		self.plugin = pluginMethod
