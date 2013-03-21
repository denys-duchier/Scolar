# This takes 'old_groups.txt' from var (create it using getOldGroups)
# and sets up all the groups therein using NuxUserGroups calls.  This
# will load a group source if you need to do such a thing.
#
# Matt Behrens <matt.behrens@kohler.com>

def loadOldGroups(self):
    from os.path import join as pathJoin
    from string import split, strip

    groups_file = open(pathJoin(CLIENT_HOME, 'old_groups.txt'), 'r')
    out = ''
    for group_line in groups_file.readlines():
	group_line_elements = split(strip(group_line), '	')
	group_name = group_line_elements[0]
	group_members = group_line_elements[1:]

	if self.getGroupById(group_name, default=None) is None:
	    out = out + 'adding group %s\n' % group_name
	    self.userFolderAddGroup(group_name)

	out = out + 'setting group %s membership to %s\n' % (group_name, group_members)
	self.setUsersOfGroup(group_members, group_name)

    return out

