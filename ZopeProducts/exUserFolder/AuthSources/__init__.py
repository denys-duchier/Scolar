#
# Extensible User Folder
#
# (C) Copyright 2000-2004 The Internet (Aust) Pty Ltd
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
# $Id: __init__.py,v 1.1 2004/11/10 14:15:34 akm Exp $

#import etcAuthSource
#import httpsAuthSource
#import mysqlAuthSource
import pgAuthSource
#import pgAuthSourceAlt
#import radiusAuthSource
#import smbAuthSource
#import usAuthSource
#import zodbAuthSource
#import zodbBTreeAuthSource

#
# These have special requirements for external libraries
# that my not be present.
#

# try:
# 	import nisAuthSource
# except:
# 	pass

# try:
# 	import LDAPAuthSource
# except:
# 	pass
