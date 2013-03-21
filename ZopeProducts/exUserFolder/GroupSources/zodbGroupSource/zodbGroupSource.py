#
# Extensible User Folder
# 
# ZODB Group Source for exUserFolder
#
# Author: Brent Hendricks <mh@users.sourceforge.net>
# $Id: zodbGroupSource.py,v 1.1 2004/11/10 14:15:54 akm Exp $
from Globals import HTMLFile, MessageDialog, INSTANCE_HOME,Acquisition, PersistentMapping

from OFS.Folder import Folder

from Products.ZSQLMethods.SQL import SQL

from Products.exUserFolder.exUserFolder import exUserFolder
from Products.exUserFolder.Plugins import PluginRegister
from Products.NuxUserGroups.UserFolderWithGroups import Group, _marker

import time
import zLOG
import sys

manage_addGroupSourceForm=HTMLFile('manage_addzodbGroupSourceForm', globals())

def manage_addzodbGroupSource(self, REQUEST):
	""" Add a ZODB Group Source """

	o = zodbGroupSource()
	self._setObject('zodbGroupSource', o, None, None, 0)
	o = getattr(self, 'zodbGroupSource')

	# Allow Prop Source to setup default users...
	if hasattr(o, 'postInitialisation'):
		o.postInitialisation(REQUEST)
	self.currentGroupSource=o

manage_addzodbGroupSourceForm=HTMLFile('manage_addzodbGroupSourceForm', globals())
manage_editzodbGroupSourceForm=HTMLFile('manage_editzodbGroupSourceForm', globals())

#
# Very very simple thing, used as an example of how to write a property source
# Not recommended for large scale production sites...
#

class zodbGroupSource(Folder):
	""" Store Group Data inside ZODB, the simplistic way """

	meta_type='Group Source'
	title='Simplistic ZODB Groups'
	icon ='misc_/exUserFolder/exUserFolderPlugin.gif'	
	manage_editForm=manage_editzodbGroupSourceForm
	manage_tabs=Acquisition.Acquired
	
	def __init__(self):
		self.id='zodbGroupSource'
		self.groups=PersistentMapping()


	def addGroup(self, groupname, title='', users=(), **kw):
		"""Creates a group"""
		if self.groups.has_key(groupname):
			raise ValueError, 'Group "%s" already exists' % groupname
		a = 'before: groupname %s groups %s' % (groupname, self.groups)
		group = apply(Group, (groupname,), kw)
		group.setTitle(title)
		group._setUsers(users)
		self.groups[groupname] = group


	def getGroup(self, groupname, default=_marker):
		"""Returns the given group"""
		try:
			group = self.groups[groupname]
		except KeyError:
			if default is _marker: raise
			return default
		return group

	
	def delGroup(self, groupname):
		"""Deletes the given group"""
		usernames = self.groups[groupname].getUsers()
		#self.delUsersFromGroup(usernames, groupname)
		del self.groups[groupname]

	
	def listGroups(self):
		"""Returns a list of group names"""
		return tuple(self.groups.keys())
	

	def getGroupsOfUser(self, username):
		"Get a user's groups"
		groupnames = []
		allnames = self.listGroups()
		groupnames = filter(lambda g, u=username, self=self: u in self.groups[g].getUsers(), allnames)
		return tuple(groupnames)

	
	def setGroupsOfUser(self, groupnames, username):
		"Set a user's groups"
		oldGroups = self.getGroupsOfUser(username)
		self.delGroupsFromUser(oldGroups, username)
		self.addGroupsToUser(groupnames, username)


	def addGroupsToUser(self, groupnames, username):
		"Add groups to a user"
		for name in groupnames:
			group = self.groups[name]
			if not username in group.getUsers():
				group._addUsers([username])


	def delGroupsFromUser(self, groupnames, username):
		"Delete groups from a user"
		for name in groupnames:
			group = self.groups[name]
			if username in group.getUsers():
				group._delUsers([username])
		
	
	def getUsersOfGroup(self, groupname):
		"Get the users in a group"
		return self.groups[groupname].getUsers()

	
	def setUsersOfGroup(self, usernames, groupname):
		"Set the users in a group"
		# uniquify
		dict = {}
		for u in usernames: dict[u] = None
		usernames = dict.keys()

		self.groups[groupname]._setUsers(usernames)


	def addUsersToGroup(self, usernames, groupname):
		"Add users to a group"
		# uniquify
		dict = {}
		for u in usernames: dict[u] = None
		usernames = dict.keys()

		self.groups[groupname]._addUsers(usernames)
		

	def delUsersFromGroup(self, usernames, groupname):
		"Delete users from a group"
		# uniquify
		dict = {}
		for u in usernames: dict[u] = None
		usernames = dict.keys()

		self.groups[groupname]._delUsers(usernames)


	def deleteUsers(self, usernames):
		"Delete a list of users"
		for user in usernames:
			groups = self.getGroupsOfUser(user)
			self.delGroupsFromUser(groups, user)


	def postInitialisation(self, REQUEST):
		pass


        def manage_beforeDelete(self, item, container):
                # Notify the exUserFolder that it doesn't have a group source anymore
                container.currentGroupSource=None


zodbGroupReg=PluginRegister('zodbGroupSource','Simplistic ZODB Group Source',
						   zodbGroupSource, manage_addzodbGroupSourceForm,
						   manage_addzodbGroupSource,
						   manage_editzodbGroupSourceForm)
exUserFolder.groupSources['zodbGroupSource']=zodbGroupReg
