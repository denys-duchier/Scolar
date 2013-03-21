#
# Extensible User Folder
# 
# NIS Authentication Source for exUserFolder
#

# Author: Jason Gibson <jason.gibson@sbcglobal.net>

#
# This class only authenticates users, it stores no properties.
#

import string
import nis

from Globals import HTMLFile, MessageDialog, INSTANCE_HOME, DTMLFile

from OFS.Folder import Folder

from ZODB.PersistentMapping import PersistentMapping

from Products.exUserFolder.exUserFolder import exUserFolder
from Products.exUserFolder.Plugins import PluginRegister

try:
    from crypt import crypt
except:
    from Products.exUserFolder.fcrypt.fcrypt import crypt

def manage_addnisAuthSource(self, REQUEST):
    """ Add a nis Auth Source """
    try:
        if nis.cat('passwd.byname'):
            default_role=REQUEST['nisauth_default_role']
            NoLocalRoles=REQUEST.has_key('nisauth_NoLocalRoles')
            o = nisAuthSource(default_role,NoLocalRoles)
            self._setObject('nisAuthSource', o, None, None, 0)
            o=getattr(self,'nisAuthSource')
            if hasattr(o, 'postInitialisation'):
                o.postInitialisation(REQUEST)
            self.currentAuthSource=o
            return ''
        else:
            return self.MessageDialog(self,REQUEST=REQUEST,
                                    title  ='NIS Error', 
                                    message='No users in passwd.byname',
                                    action ='manage_main')
    except nis.error:        
         return self.MessageDialog(self,REQUEST=REQUEST,
                                    title  ='NIS Error', 
                                    message='NIS server unreachable',
                                    action ='manage_main')


manage_addnisAuthSourceForm=HTMLFile('manage_addnisAuthSourceForm', globals())
manage_editnisAuthSourceForm=HTMLFile('manage_editnisAuthSourceForm', globals())

class nisAuthSource(Folder):
    """ Authenticate Users against NIS 
    
    This folder has 2 modes:
    1. Authenticates only those users for which you add a local role
    2. Authenticates without local roles.  
    
    Since #1 uses local roles, it should play nice with Prop sources and memberships, 
    where #2 will not. """

    meta_type='Authentication Source'
    title='NIS Authentication'
    icon ='misc_/exUserFolder/exUserFolderPlugin.gif'
    manage_editForm=manage_editnisAuthSourceForm
        
    def __init__(self,default_role,NoLocalRoles):
        self.id='nisAuthSource'
        self.default_role=default_role
        self.NoLocalRoles=NoLocalRoles
        self.data=PersistentMapping()
        self.manage_addUserForm=DTMLFile('manage_addNISUserForm',globals())
        self.manage_editUserForm=DTMLFile('manage_editNISUserForm',globals()) #not used.  No way to plug it into exUserFolder.py
    
    def manage_editAuthSource(self,REQUEST):
        """ """
        self.default_role=REQUEST['nisauth_default_role']
        self.NoLocalRoles=REQUEST.has_key('nisauth_NoLocalRoles')

    # Create a User to store local roles
    def createUser(self, username, password, roles):
        import pdb
        pdb.set_trace()
        """ Add A Username """
        if self.NoLocalRoles:
            return self.MessageDialog(self,REQUEST=REQUEST,
                        title  ='Create Error', 
                        message='Cannot create user.  No local roles allowed',
                        action ='manage_main')
        else:
            if self._listOneNISUser(username) and (not self.data.has_key(username)):
                if type(roles) != type([]):
                    if roles:
                        roles=list(roles)
                    else:
                        roles=[self.default_role]
                self.data[username]=PersistentMapping()
                self.data[username].update({'username': username,
                                            'roles': roles})
            else:
                return self.MessageDialog(self,REQUEST=REQUEST,
                            title  ='Create Error', 
                            message='Cannot create user.  Username not in NIS',
                            action ='manage_main')

    # Update a user's roles
    # Passwords are managed via the users NIS unix accounts, not here
    def updateUser(self, username, password, roles):
        if self.NoLocalRoles:
            return self.MessageDialog(self,REQUEST=REQUEST,
                        title  ='Create Error', 
                        message='Cannot create user.  No local roles allowed',
                        action ='manage_main')
        else:
            self.data[username].update({'roles':roles})

    # Encrypt a password
    def cryptPassword_old(self, username, password):
        NISuser=self._listOneNISUser(username)
        if self.NoLocalRoles:
            user=NISuser
        else:
            user=self.listOneUser(username)
        salt = NISuser['password'][:2]
        secret = crypt(password, salt)
        return secret

    # Delete a set of local users
    def deleteUsers(self, userids):
        if self.NoLocalRoles:
            return self.MessageDialog(self,REQUEST=REQUEST,
                        title  ='Create Error', 
                        message='Cannot create user.  No local roles allowed',
                        action ='manage_main')
        for name in userids:
            del self.data[name]

    # Return a list of usernames
    def listUserNames(self,listNIS=None):
        if self.NoLocalRoles or listNIS:
            usernames=self._listNISUserNames()
        else:
            usernames=self.data.keys()
            usernames.sort()
        return usernames
        
    # Return one user matching the username
    # Should be a dictionary;
    # {'username':username, 'password':cryptedPassword, 'roles':list_of_roles}
    def listOneUser(self, username):
        users = []
        udata={}
        NISuser=self._listOneNISUser(username)
        if NISuser and len(NISuser)>0:
            if self.NoLocalRoles:
                udata=NISuser
            else:
                udata['username'] = username
                udata['password']=NISuser['password']
                udata['roles']=self.data[username]['roles']
            if udata is not None:
                users.append(udata)
        return users

    # Return a list of user dictionaries the same as listOneUser
    def listUsers(self):
        if self.NoLocalRoles:
            users=self._listNISUsers()
        else:
            NISusers=self._listNISUsers()
            NISusers_dict={}
            for user in NISusers:
                NISusers_dict[ user['username'] ]=user
            users=self.data.values()
            for num in range(0,len(users)):
                username=users[num]['username']
                users[num]['password']=NISusers_dict[username]['password']
        return users

    def _listNISUserNames(self):
        nis_users=nis.cat('passwd.byname')
        usernames=nis_users.keys()
        usernames.sort()
        return usernames

    def _listOneNISUser(self,username):
        roles=[self.default_role]
        try:
            nis_user=nis.match(username,'passwd.byname')
            username,passwd,other=string.split(nis_user,':',2)
            data={'username':username,
                  'password':passwd,
                  'roles':roles}
        except nis.error:
            data=None
        return data
        
    def _listNISUsers(self):
        users=[]
        roles=[self.default_role]
        try:
            nis_users=nis.cat('passwd.byname')
            userlist=nis_users.keys()
            userlist.sort()
            for user in userlist:
                username,passwd,other=string.split(nis_users[user],':',2)
                data={'username':username,
                      'password':passwd,
                      'roles':roles}
                users.append(data)
        except nis.error:
            data=None
        
        return users
    
    
    #
    # You can define this to go off and do the authentication instead of
    # using the basic one inside the User Object
    #
    remoteAuthMethod=None

    def postInitialisation(self, REQUEST):
        pass
        

nisAuthReg=PluginRegister('nisAuthSource', 'NIS Authentication Source',
                         nisAuthSource, manage_addnisAuthSourceForm,
                         manage_addnisAuthSource,
                         manage_editnisAuthSourceForm)
exUserFolder.authSources['nisAuthSource']=nisAuthReg
