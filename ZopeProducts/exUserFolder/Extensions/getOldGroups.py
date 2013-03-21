# This script interrogates the old-skool NuxUserGroups_support_branch
# group structure and outputs a tab-delimited file you can send to
# loadOldGroups.  Just in case anyone is using it. :-)
#
# Matt Behrens <matt.behrens@kohler.com>

def getOldGroups(self):
    "Reconstruct a group list from the old-style _groups property"
    from string import join
    props = self.currentPropSource.userProperties
    groups = {}
    for username in props.keys():
	for groupname in props[username].getProperty('_groups', ()):
	    if not groups.has_key(groupname):
		groups[groupname] = []
	    groups[groupname].append(username)
    out = ''
    for groupname in groups.keys():
	out = out + '%s	%s\n' % (groupname, join(groups[groupname], '	'))
    return out
