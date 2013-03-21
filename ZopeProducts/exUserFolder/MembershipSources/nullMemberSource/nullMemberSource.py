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
# $Id: nullMemberSource.py,v 1.1 2004/11/10 14:15:55 akm Exp $
from Globals import HTMLFile, INSTANCE_HOME

from OFS.Folder import Folder

from Products.exUserFolder.exUserFolder import exUserFolder
from Products.exUserFolder.Plugins import PluginRegister
from Products.exUserFolder.nullPlugin import nullPlugin

def manage_addNullMemberSource(self, REQUEST):
	""" Add a Membership Source """
	self.currentMembershipSource=None
	return ''


manage_addNullMemberSourceForm=HTMLFile('manage_addNullPluginSourceForm',globals())
manage_editNullMemberSourceForm=None

		
nullMemberReg=PluginRegister('nullMemberSource',
							  'Null Membership Source',
							 nullPlugin,
							 manage_addNullMemberSourceForm,
							 manage_addNullMemberSource,
							 manage_editNullMemberSourceForm)
exUserFolder.membershipSources['nullMemberSource']=nullMemberReg

