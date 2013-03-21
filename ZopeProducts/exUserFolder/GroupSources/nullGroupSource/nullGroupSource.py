#
# Extensible User Folder
# 
# Null Group Source for exUserFolder
#
# Author: Brent Hendricks <bmh@users.sourceforge.net>
# $Id: nullGroupSource.py,v 1.1 2004/11/10 14:15:53 akm Exp $
from Globals import HTMLFile, INSTANCE_HOME

from OFS.Folder import Folder

from Products.exUserFolder.exUserFolder import exUserFolder
from Products.exUserFolder.Plugins import PluginRegister
from Products.exUserFolder.nullPlugin import nullPlugin

def manage_addNullGroupSource(self, REQUEST):
	""" Add a Group Source """
	self.currentGroupSource=None
	return ''


manage_addNullGroupSourceForm=HTMLFile('manage_addNullPluginSourceForm',globals())
manage_editNullGroupSourceForm=None

		
nullGroupReg=PluginRegister('nullGroupSource',
						   'Null Group Source',
						   nullPlugin,
						   manage_addNullGroupSourceForm,
						   manage_addNullGroupSource,
						   manage_editNullGroupSourceForm)

exUserFolder.groupSources['nullGroupSource']=nullGroupReg

