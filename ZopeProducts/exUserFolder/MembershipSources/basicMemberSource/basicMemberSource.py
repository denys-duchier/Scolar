#
# Extensible User Folder
# 
# Basic Membership Source for exUserFolder
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
# $Id: basicMemberSource.py,v 1.1 2004/11/10 14:15:55 akm Exp $

#
# Basically membership is a layer between the signup/login form, and
# the authentication layer, it uses the prop source of the users to
# store additional information about a user i.e. doesn't impact on the
# authentication source.
#
# Some membership features imply some extra properties for the user will
# be available; specifically at this time an email property.
#
# You also need a MailHost setup and ready to go for emailing stuff to users
#

import string,Acquisition
from random import choice
	

from Globals import HTMLFile, INSTANCE_HOME

from OFS.Folder import Folder
from OFS.DTMLMethod import DTMLMethod

from Products.exUserFolder.exUserFolder import exUserFolder
from Products.exUserFolder.Plugins import PluginRegister

from base64 import encodestring
from urllib import quote

import zLOG

"""
Password Policy enforcement (min/max length, caps etc)
Create Password, or User Chooses.
Timing out of passwords...
Empty Password force change on login...
Create Home Directory
Copy files from Skelton Directory
EMail password hint to user (forgot my password)
Reset password and email user (needs plugin?)
Redirect on login to fixed or varying per username location.
Automatically add users, or manually approve of users.
"""

# Stupid little things for making a password
# Don't hassle me, it's supposed to be basic.

nouns=['ace', 'ant', 'arc', 'arm', 'axe',
	   'bar', 'bat', 'bee', 'bib', 'bin',
	   'can', 'cap', 'car', 'cat', 'cob',
	   'day', 'den', 'dog', 'dot', 'dux',
	   'ear', 'eel', 'egg', 'elf', 'elk',
	   'fad', 'fan', 'fat', 'fig', 'fez',
	   'gag', 'gas', 'gin', 'git', 'gum',
	   'hag', 'hat', 'hay', 'hex', 'hub']

pastConjs = [ 'did', 'has', 'was' ]
suffixes  = [ 'ing', 'es', 'ed', 'ious', 'ily']

def manage_addBasicMemberSource(self, REQUEST):
	""" Add a Membership Source """

	pvfeatures=[]
	minLength=0
	passwordPolicy=''
	createHomedir=0
	homeRoot=''
	copyFilesFrom=''
	postLogin=''
	postSignup=''
	forgottenPasswords=''
	defaultRoles=[]
	usersCanChangePasswords=0
	baseURL=''
	loginPage=''
	signupPage=''
	passwordPage=''
	mailHost=''
	fixedDest=''
	
	if REQUEST.has_key('basicmember_pvfeatures'):
		pvfeatures=REQUEST['basicmember_pvfeatures']

	if REQUEST.has_key('basicmember_roles'):
		defaultRoles=REQUEST['basicmember_roles']

	if not defaultRoles:
		defaultRoles=['Member']

	if 'minlength' in pvfeatures:
		minLength=REQUEST['basicmember_minpasslen']

	if REQUEST.has_key('basicmember_passwordpolicy'):
		passwordPolicy=REQUEST['basicmember_passwordpolicy']

	if REQUEST.has_key('basicmember_createhomedir'):
		homeRoot=REQUEST['basicmember_homeroot']
		createHomedir=1

	if REQUEST.has_key('basicmember_copyfiles'):
		copyFilesFrom=REQUEST['basicmember_copyfiles']

	if REQUEST.has_key('basicmember_changepasswords'):
		usersCanChangePasswords=1

	if REQUEST.has_key('basicmember_fixeddest'):
		fixedDest=''

	forgottenPasswords=REQUEST['basicmember_forgottenpasswords']
	postLogin=REQUEST['basicmember_postlogin']

	baseURL=REQUEST['basicmember_baseurl']
	loginPage=REQUEST['basicmember_loginpage']
	signupPage=REQUEST['basicmember_signuppage']
	passwordPage=REQUEST['basicmember_passwordpage']
	siteEmail=REQUEST['basicmember_siteemail']
	siteName=REQUEST['basicmember_sitename']

	mailHost=REQUEST['basicmember_mailhost']
	
	# postSignup=REQUEST['basicmember_postsignup']

	#
	# Yep this is obscene
	#
	o = BasicMemberSource(pvfeatures, minLength, passwordPolicy,
						  createHomedir, copyFilesFrom, postLogin,
						  homeRoot, forgottenPasswords, defaultRoles,
						  usersCanChangePasswords, baseURL, loginPage,
						  signupPage, passwordPage, mailHost,
						  siteName, siteEmail, fixedDest)

	self._setObject('basicMemberSource', o, None, None, 0)
	o = getattr(self, 'basicMemberSource')

	if hasattr(o, 'postInitialisation'):
		o.postInitialisation(REQUEST)

	self.currentMembershipSource=o
	return ''


manage_addBasicMemberSourceForm=HTMLFile('manage_addBasicMemberSourceForm',
										 globals())
manage_editBasicMemberSourceForm=HTMLFile('manage_editBasicMemberSourceForm',
										 globals())

#
# Crap, I don't know why I called this basic, I'd hate to see a
# complicated one.
#
class BasicMemberSource(Folder):
	""" Provide High Level User Management """
	meta_type="Membership Source"
	title="Basic Membership Source"
	icon ='misc_/exUserFolder/exUserFolderPlugin.gif'
	manage_tabs=Acquisition.Acquired
	manage_editForm=manage_editBasicMemberSourceForm

	# Ugh...
	def __init__(self, pvFeatures=[], minLength=0, passwordPolicy='',
				 createHomeDir=0, copyFilesFrom='', postLogin='', homeRoot='',
				 forgottenPasswords='', defaultRoles=[], usersCanChangePasswords=0,
				 baseURL='', loginPage='', signupPage='', passwordPage='',
				 mailHost='', siteName='', siteEmail='', fixedDest=''):
		
		self.id='basicMemberSource'
		self.pvFeatures=pvFeatures
		self.minLength=int(minLength)
		self.passwordPolicy=passwordPolicy
		self.createHomeDir=createHomeDir
		self.copyFilesFrom=copyFilesFrom
		self.postLogin=postLogin
		self.homeRoot=homeRoot
		self.forgottenPasswords=forgottenPasswords
		self.defaultRoles=defaultRoles
		self.usersCanChangePasswords=usersCanChangePasswords
		self.baseURL=baseURL
		self.loginPage=loginPage
		self.signupPage=signupPage
		self.passwordPage=passwordPage
		self.siteName=siteName
		self.siteEmail=siteEmail
		self.fixedDest=fixedDest
		
		_SignupForm=HTMLFile('SignupForm', globals())
		SignupForm=DTMLMethod()
		SignupForm.manage_edit(data=_SignupForm, title='Signup Form')
		self._setObject('SignupForm', SignupForm)

		_PasswordForm=HTMLFile('PasswordForm', globals())
		PasswordForm=DTMLMethod()
		PasswordForm.manage_edit(data=_PasswordForm,
								 title='Change Password')
		self._setObject('PasswordForm', PasswordForm)

		self.mailHost=mailHost

		_newPasswordEmail=HTMLFile('newPasswordEmail', globals())
		newPasswordEmail=DTMLMethod()
		newPasswordEmail.manage_edit(data=_newPasswordEmail,
									 title='Send New Password')
		self._setObject('newPasswordEmail', newPasswordEmail)

		_forgotPasswordEmail=HTMLFile('forgotPasswordEmail', globals())
		forgotPasswordEmail=DTMLMethod()
		forgotPasswordEmail.manage_edit(data=_forgotPasswordEmail,
										title='Send Forgotten Password')
		self._setObject('forgotPasswordEmail', forgotPasswordEmail)

		_passwordHintEmail=HTMLFile('passwordHintEmail', globals())
		passwordHintEmail=DTMLMethod()
		passwordHintEmail.manage_edit(data=_passwordHintEmail,
										title='Send Forgotten Password Hint')
		self._setObject('passwordHintEmail', passwordHintEmail)

	def postInitialisation(self, REQUEST):
		if self.createHomeDir and self.homeRoot:
			self.findHomeRootObject()
		else:
			self.homeRootObj=None
			
		if self.copyFilesFrom:
			self.findSkelRootObject()
		else:
			self.homeSkelObj=None

		# The nice sendmail tag doesn't allow expressions for
		# the mailhost
		self.mailHostObject=getattr(self, self.mailHost)

	def manage_editMembershipSource(self, REQUEST):
		""" Edit a basic Membership Source """
		if REQUEST.has_key('pvfeatures'):
			self.pvFeatures=REQUEST['pvfeatures']
		else:
			self.pvFeatures=[]
			
		if REQUEST.has_key('minpasslength'):
			self.minLength=REQUEST['minpasslength']

		if REQUEST.has_key('createhomedir'):
			createHomeDir=1
		else:
			createHomeDir=0

		if createHomeDir:
			self.copyFilesFrom=REQUEST['copyfiles']
			if self.copyFilesFrom:
				self.findSkelRootObject()
			else:
				self.homeRoot=REQUEST['homeroot']
			self.findHomeRootObject()
		
		if REQUEST.has_key('memberroles'):
			self.defaultRoles=REQUEST['memberroles']
		if REQUEST.has_key('changepasswords'):
			self.usersCanChangePasswords=1
		else:
			self.usersCanChangePasswords=0

		self.postLogin=REQUEST['postlogin']
		if REQUEST.has_key('fixeddest'):
			self.fixedDest=REQUEST['fixeddest']

		self.baseURL=REQUEST['baseurl']
		self.loginPage=REQUEST['loginpage']
		self.signupPage=REQUEST['signuppage']
		self.passwordPage=REQUEST['passwordpage']
		self.siteName=REQUEST['sitename']
		self.siteEmail=REQUEST['siteemail']
		return self.MessageDialog(self,
				title  ='Updated!', 
				message="Membership was Updated",
				action ='manage_editMembershipSourceForm',
				REQUEST=REQUEST)

		

	def forgotPassword(self, REQUEST):
		username=REQUEST['username']
		curUser=self.getUser(username)
		if not curUser:
			return self.MessageDialog(self,
				title  ='No such user', 
				message="No users matching that username were found.",
				action ='%s/%s'%(self.baseURL, self.loginPage),
				REQUEST=REQUEST)			

			
		userEmail=curUser.getProperty('email')
		userName=curUser.getProperty('realname')
		if self.forgottenPasswords == "hint":
			passwordHint=curUser.getProperty('passwordhint')
			self.passwordHintEmail(self,
								   REQUEST=REQUEST,
								   username=username,
								   hint=passwordHint,
								   realname=userName,
								   email=userEmail)
		else:
			# make a new password, and mail it to the user
			password = self.generatePassword()
			curCrypt=self.currentAuthSource.cryptPassword(username,password)

			# Update the user
			bogusREQUEST={}
			#bogusREQUEST['username']=username
			bogusREQUEST['password']=password
			bogusREQUEST['password_confirm']=password
			bogusREQUEST['roles']=curUser.roles
			self.manage_editUser(username, bogusREQUEST)
			
			self.forgotPasswordEmail(self,
									REQUEST=REQUEST,
									username=username,
									password=password,
									realname=userName,
									email=userEmail)
		return self.MessageDialog(self,
				title  ='Sent!', 
				message="Password details have been emailed to you",
				action ='%s/%s'%(self.baseURL, self.loginPage),
				REQUEST=REQUEST)			


	def changeProperties(self, REQUEST):
 
		curUser=self.listOneUser(REQUEST['AUTHENTICATED_USER'].getUserName())
		curUser=curUser[0]
		if not curUser:
			return self.MessageDialog(self,
				title  ='Erm!', 
				message="You don't seem to be logged in",
				action ='%s/%s'%(self.baseURL, self.passwordPage),
				REQUEST=REQUEST)
			

		
		self.currentPropSource.updateUser(curUser['username'],REQUEST)
		
		return self.MessageDialog(self,
				   title  ='Properties updated',
				   message="Your properties have been updated",
				   action =self.baseURL,
				   REQUEST=REQUEST,
				   )

	
	def changePassword(self, REQUEST):
		if not self.usersCanChangePasswords:
			return ''

		curUser=self.listOneUser(REQUEST['AUTHENTICATED_USER'].getUserName())
		curUser=curUser[0]
		if not curUser:
			return self.MessageDialog(
				title  ='Erm!', 
				message="You don't seem to be logged in",
				action ='%s/%s'%(self.baseURL, self.passwordPage),
				REQUEST=REQUEST)
			
		curCrypt=self.currentAuthSource.cryptPassword(curUser['username'],REQUEST['current_password'])
		if curCrypt != curUser['password']:
			return self.MessageDialog(self,
				title  ='Password Mismatch', 
				message="Password is incorrect",
				action ='%s/%s'%(self.baseURL, self.passwordPage),
				REQUEST=REQUEST)

		if REQUEST['password'] != REQUEST['password_confirm']:
			return self.MessageDialog(self,
				title  ='Password Mismatch', 
				message="Passwords do not match",
				action ='%s/%s'%(self.baseURL, self.passwordPage),
				REQUEST=REQUEST)

		# OK the old password matches the one the user provided
		# Both new passwords match...
		# Time to validate against our normal set of rules...
		#
		if not self.validatePassword(REQUEST['password'], curUser['username']):
			return self.MessageDialog(self,
				title  ='Password problem', 
				message="Your password is invalid, please choose another",
				action ='%s/%s'%(self.baseURL, self.passwordPage),
				REQUEST=REQUEST)

		if self.passwordPolicy=='hint':
			if not hasattr(REQUEST,'user_passwordhint'):
				return self.MessageDialog(self,
					title  ='Password requires hint', 
					message='You must choose a password hint',
					action ='%s/%s'%(self.baseURL, self.passwordPage),
					REQUEST=REQUEST)		

		bogusREQUEST={}

		bogusREQUEST['password']=REQUEST['password']
		bogusREQUEST['password_confirm']=REQUEST['password']
		bogusREQUEST['roles']=curUser['roles']
		self.manage_editUser(curUser['username'],bogusREQUEST)
		# update the cookie so he doesnt have to re-login:
		if self.cookie_mode:
			token='%s:%s' %(curUser['username'], REQUEST['password'])
			token=encodestring(token)
			token=quote(token)
			REQUEST.response.setCookie('__ac', token, path='/')
			REQUEST['__ac']=token

		return self.MessageDialog(self,
			title  ='Password updated', 
			message="Your password has been updated",
			action =self.baseURL,
			REQUEST=REQUEST)
		

	def goHome(self, REQUEST, RESPONSE):
		redirectstring="%s/%s/%s/manage_main"%(self.baseURL, self.homeRoot, REQUEST.AUTHENTICATED_USER.getUserName())
		RESPONSE.redirect(redirectstring)
		return ''
	
	# Tell exUserFolder where we want to go...
	def getLoginDestination(self, REQUEST):
		script=''
		pathinfo=''
		querystring=''
		redirectstring=''
		if self.postLogin=="destination":
			script=REQUEST['SCRIPT_NAME']
			pathinfo=REQUEST['PATH_INFO']
		elif self.postLogin=="varied":
			script=self.baseURL
			pathinfo="/acl_users/goHome"
			
		elif self.postLogin=="fixed":
			pathinfo="%s"%(self.fixedDest)

		if REQUEST.has_key('QUERY_STRING'):
			querystring='?'+REQUEST['QUERY_STRING']

		redirectstring=script+pathinfo
		if querystring:
			redirectstring=redirectstring+querystring		

		return redirectstring
	
	def validatePassword(self, password, username):
		if 'minlength' in self.pvFeatures:
			if len(password) < self.minLength:
				return 0

		if 'mixedcase' in self.pvFeatures:
			lower = 0
			upper = 0
			for c in password:
				if c in string.lowercase:
					lower = 1
				if c in string.uppercase:
					upper = 1
			if not upper and lower:
				return 0
			
		if 'specialchar' in self.pvFeatures:
			special = 0
			for c in password:
				if c in string.punctuation:
					special = 1
					break
				elif c in string.digits:
					special = 1
					break
			if not special:
				return 0

		#
		# XXX Move this somewhere else
		#
			
		if 'notstupid' in self.pvFeatures:
			email=''
			# We try some permutations here...
			curUser=self.getUser(username)
			if curUser:
				email = curUser.getProperty('email')
			elif hasattr(self, 'REQUEST'):
				if self.REQUEST.has_key('user_email'): # new signup
					email=self.REQUEST['user_email']
				elif self.REQUEST.has_key('email'):
					email=self.REQUEST['email']

			if ((string.find(password, username)>=0) or
				( email and
				  (string.find(password,
							   string.split(email,'@')[0]) >=0))):
				return 0
		return 1

	# These next two look the same (and they are for now), but, the reason I
	# Don't use one single method, is I think that SkelObj might migrate to
	# using full paths, not relative paths.
	
	def findSkelRootObject(self):
		# Parent should be acl_users
		parent = getattr(self, 'aq_parent')

		# This should be the root...
		root = getattr(parent, 'aq_parent')
		searchPaths = string.split(self.copyFilesFrom, '/')
		for o in searchPaths:
			if not getattr(root, o):
				break
			root = getattr(root, o)

		self.homeSkelObj=root		
	
	def findHomeRootObject(self):
		# Parent should be acl_users
		parent = getattr(self, 'aq_parent')

		# This should be the root...
		root = getattr(parent, 'aq_parent')

		searchPaths = string.split(self.homeRoot, '/')
		for o in searchPaths:
			if o not in root.objectIds():
				root.manage_addFolder(id=o, title=o, createPublic=0, createUserF=0)
			root = getattr(root, o)

		self.homeRootObj=root
		
	def makeHomeDir(self, username):
		if not self.homeRootObj:
			return
		
		self.homeRootObj.manage_addFolder(id=username, title=username, createPublic=0, createUserF=0)
		home = getattr(self.homeRootObj, username)
		

		# Allow user to be in charge of their own destiny
		# XXXX WARNING THIS IS A NORMAL FOLDER *SO USERS CAN ADD ANYTHING*
		# YOU NEED TO CHANGE THE TYPE OF OBJECT ADDED FOR A USER UNLESS
		# THIS IS WHAT YOU WANT TO HAPPEN
		home.manage_addLocalRoles(userid=username, roles=['Manager'])

		if self.copyFilesFrom and self.homeSkelObj and self.homeSkelObj.objectIds():
			cp=self.homeSkelObj.manage_copyObjects(
				self.homeSkelObj.objectIds())
			home.manage_pasteObjects(cp)

		# Fix it so the user owns their stuff
		curUser=self.getUser(username).__of__(self.aq_parent)
		home.changeOwnership(curUser, recursive=1)
		
	def generatePassword(self):
		password = (choice(nouns) + choice(pastConjs) +
					choice(nouns) + choice(suffixes))
		return password
			
	def createUser(self, REQUEST):
		if self.passwordPolicy == 'user':
			if not self.validatePassword(REQUEST['password'], REQUEST['username']):
				return self.MessageDialog(self,
					title  ='Password problem', 
					message='Your password is invalid, please choose another',
					action ='%s/%s'%(self.baseURL, self.signupPage),
					REQUEST=REQUEST)

			if self.passwordPolicy=='hint':
				if not hasattr(REQUEST,'user_passwordhint'):
					return self.MessageDialog(self,
						title  ='Password requires hint', 
						message='You must choose a password hint',
						action ='%s/%s'%(self.baseURL, self.signupPage),
						REQUEST=REQUEST)

		elif self.passwordPolicy == 'system':
			REQUEST['password']=self.generatePassword()
			REQUEST['password_confirm']=REQUEST['password']

			# Email the password.
			self.newPasswordEmail(self, REQUEST)

		zLOG.LOG("exUserFolder.basicMemberSource", zLOG.BLATHER,
                         "Creating user",
                         "Passed all tests -- creating [%s]" % REQUEST['username'])
		REQUEST['roles']=self.defaultRoles
		self.manage_addUser(REQUEST) # Create the User...
		if self.createHomeDir:
			self.makeHomeDir(REQUEST['username'])

		return self.MessageDialog(self,
			title  ='You have signed up', 
			message='You have been signed up succesfully',
			action ='%s'%(self.baseURL),
			REQUEST=REQUEST)
		

		
basicMemberReg=PluginRegister('basicMemberSource',
							  'Basic Membership Source',
							  BasicMemberSource,
							  manage_addBasicMemberSourceForm,
							  manage_addBasicMemberSource,
							  manage_editBasicMemberSourceForm)
exUserFolder.membershipSources['basicMemberSource']=basicMemberReg

