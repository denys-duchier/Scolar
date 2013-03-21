#
# Extensible User Folder
# 
# Null Group Source for exUserFolder
#
# Author: Brent Hendricks <bmh@users.sourceforge.net>
# $Id: GroupSource.py,v 1.1 2002/12/02 23:20:49 bmh Exp $
from Globals import DTMLFile


manage_addGroupSourceForm=DTMLFile('manage_addGroupSourceForm', globals(), __name__='manage_addGroupSourceForm')


def manage_addGroupSource(dispatcher, REQUEST):
	""" Add a Group Source """

	# Get the XUF object we're being added to
	xuf = dispatcher.Destination()
	
	groupId = REQUEST.get('groupId', None)
	if groupId:
		# Invoke the add method for this plugin
		xuf.groupSources[groupId].manage_addMethod(xuf, REQUEST)
	else:
		raise "BadRequest", "Required parameter 'groupId' omitted"

	dispatcher.manage_main(dispatcher, REQUEST)
	

class GroupSource:
	pass

