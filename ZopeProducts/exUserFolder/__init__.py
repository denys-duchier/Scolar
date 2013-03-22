#
# Extensible User Folder
# 
# (C) Copyright 2000-2005 The Internet (Aust) Pty Ltd
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
# $Id: __init__.py,v 1.18 2004/11/10 14:15:33 akm Exp $

import exUserFolder

import CryptoSources
import AuthSources
import PropSources
import MembershipSources
import GroupSources

from GroupSource import GroupSource

from App.ImageFile import ImageFile
import OFS

#
# Install a dummy ZBabel setup if we don't have ZBabel installed.
#
import dummyZBabelTag

# Methods we need access to from any ObjectManager context
legacy_methods = (
	    ('manage_addexUserFolderForm', exUserFolder.manage_addexUserFolderForm),
	    ('manage_addexUserFolder',     exUserFolder.manage_addexUserFolder),
	    ('getAuthSources',             exUserFolder.getAuthSources),
	    #('getPropSources',             exUserFolder.getPropSources),
		('getCryptoSources',           exUserFolder.getCryptoSources),
	    ('getMembershipSources',       exUserFolder.getMembershipSources),
	    ('getGroupSources',            exUserFolder.getGroupSources),
	    ('doAuthSourceForm',           exUserFolder.doAuthSourceForm),
	    #('doPropSourceForm',           exUserFolder.doPropSourceForm),
	    ('doMembershipSourceForm',     exUserFolder.doMembershipSourceForm),
        #	    ('doGroupSourceForm',          exUserFolder.doGroupSourceForm),
	    ('getVariableType',            exUserFolder.getVariableType),
	    ('DialogHeader',               exUserFolder.exUserFolder.DialogHeader),
	    ('DialogFooter',               exUserFolder.exUserFolder.DialogFooter),
	    #('MailHostIDs',                exUserFolder.MailHostIDs),
	    )

# Image files to place in the misc_ object so they are accesible from misc_/exUserFolder
misc_={'exUserFolder.gif': ImageFile('exUserFolder.gif', globals()),
       'exUserFolderPlugin.gif': ImageFile('exUserFolderPlugin.gif', globals()),
       'exUser.gif': ImageFile('exUser.gif', globals()),
       }


def initialize(context):
    """
    Register base classes
    """
    context.registerClass(exUserFolder.exUserFolder,
			  meta_type="ex User Folder",
			  permission="Add exUser Folder",
			  constructors=(exUserFolder.manage_addexUserFolderForm,
					exUserFolder.manage_addexUserFolder,),
			  legacy=legacy_methods,
			  icon="exUserFolder.gif")

    context.registerClass(GroupSource.GroupSource,
			  meta_type="ex User Folder Group Source",
			  permission="Add exUser Folder",
			  constructors=(GroupSource.manage_addGroupSourceForm,
					GroupSource.manage_addGroupSource,),
			  icon="exUserFolderPlugin.gif")

