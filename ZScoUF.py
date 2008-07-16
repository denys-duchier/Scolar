
# projet: User Folder specialise pour Zope

class ScoUserFolder(BasicUserFolder):
    
    """ScoDoc User Folder
    """
    id       ='acl_users'
    title    ='ScoDoc User Folder'

    def __init__(self):
        pass # should create db connexion ???

    def getUserNames(self):
        """Return a list of usernames"""
        # TODO

    def getUsers(self):
        """Return a list of user objects"""
        # TODO

    def getUser(self, name):
        """Return the named user object or None"""
        # TODO

    def hasUsers(self):
        return True # we lie

    # validate (in super) calls
    # in turn: identify, authenticate, authorize (wrt object and roles)

    def identify(self, auth):
        """Identify the username and password.
        Use only our cookie mode
        """
        # see exUserFolder decodeAdvancedCookie  
        # c'est lui qui fait 
        #   raise 'LoginRequired', self.docLogin(self, request)
        return name, password

    # authenticate(name, password) retrouve le user avec getUser()
    # et appelle user.authenticate(password, request) 
