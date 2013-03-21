#
# Extensible User Folder
# 
# Null Membership Source for exUserFolder
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
# $Id: nullPropSource.py,v 1.1 2004/11/10 14:15:56 akm Exp $
from Globals import HTMLFile, INSTANCE_HOME

from OFS.Folder import Folder

from Products.exUserFolder.exUserFolder import exUserFolder
from Products.exUserFolder.Plugins import PluginRegister
from Products.exUserFolder.nullPlugin import nullPlugin

def manage_addNullPropSource(self, REQUEST):
	""" Add a Property Source """
	self.currentPropSource=None
	return ''


manage_addNullPropSourceForm=HTMLFile('manage_addNullPluginSourceForm',globals())
manage_editNullPropSourceForm=None

		
nullPropReg=PluginRegister('nullPropSource',
						   'Null Property Source',
						   nullPlugin,
						   manage_addNullPropSourceForm,
						   manage_addNullPropSource,
						   manage_editNullPropSourceForm)

exUserFolder.propSources['nullPropSource']=nullPropReg

