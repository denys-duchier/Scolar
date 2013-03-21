#
# Extensible User Folder
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
# $Id: PropertyEditor.py,v 1.3 2002/01/29 17:42:02 alex_zxc Exp $

from Globals import DTMLFile, MessageDialog, INSTANCE_HOME
from string import join,strip,split,lower,upper,find
from urllib import quote, unquote


def editStringProperty( name, value):
	""" """
	return('<input type="TEXT" name="%s:string" value="%s">\n'%(name, value))

def viewStringProperty( name, value):
	""" """
	return('<input type="HIDDEN" name="propValue:string" value="%s"><br>%s<br>\n'%(value, value))


def editIntegerProperty( name, value):
	""" """
	return('<input type="TEXT" name="%s:int" value="%d">\n'%(name, value or 0))

def viewIntegerProperty( name, value):
	""" """
	return('<input type="HIDDEN" name="propValue:int" value="%d"><br>%d<br>\n'%(value or 0 , value or 0))


def editLongProperty( name, value):
	""" """
	return('<input type="TEXT" name="%s:int" value="%d">\n'%(name, value or 0))	

def viewLongProperty( name, value):
	""" """
	return('<input type="HIDDEN" name="propValue:long" value="%d"><br>%d<br>\n'%(value or 0, value or 0))


def editFloatProperty( name, value):
	""" """
	return('<input type="TEXT" name="%s:float" value="%d">\n'%(name, value))

def viewFloatProperty( name, value):
	""" """
	return('<input type="HIDDEN" name="propValue:float" value="%f"><br>%f<br>\n'%(value, value))


def editListProperty( name, value):
	a=''
	if value:
		a = a + 'Select Items to keep<br>\n'
		a = a + '<select name="%s:list" multiple>\n'%(name)
		for i in value:
			a = a + (
				'<option value="%s" SELECTED>%s\n'%(i, i))
		a = a + '</select>\n<br>'
	a = a + 'Add an item\n<br>'
	a = a + '<input type="TEXT" name="%s:list">'%(name)
	return(a)

def viewListProperty( name, value):
	a=''
	if value:
		for i in value:
			a = a + (
				'<input type="HIDDEN" name="propValue:list" value="%s">\n'%(i))
			a = a + '%s\n<br>'%(i)
	return(a)


def editDictProperty( name, value):
	""" """
	a=''
	if value and value.keys():
		for i in value.keys():
			a = a + '%s : <input type="TEXT" name="%s.%s" value="%s">\n<br>'%(i, name, i, value[i])
	return a


def viewDictProperty( name, value):
	""" """
	a=''
	if value and value.keys():
		for i in value.keys():
			a = a + '%s : <input type="HIDDEN" name="propValue.%s" value="%s">\n<br>'%(i, name, i, value[i])
			a = a + '%s\n<br>'%(value[i])
	return a

EditMethods={'String':editStringProperty,
			 'Integer':editIntegerProperty,
			 'Long':editLongProperty,
			 'Float':editFloatProperty,
			 'List':editListProperty,
			 'Dict':editDictProperty}
			 

ViewMethods={'String':viewStringProperty,
			 'Integer':viewIntegerProperty,
			 'Long':viewLongProperty,
			 'Float':viewFloatProperty,
			 'List':viewListProperty,
			 'Dict':viewDictProperty}
			 



