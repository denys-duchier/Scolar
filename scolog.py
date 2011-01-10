# -*- mode: python -*-
# -*- coding: iso8859-15 -*-

##############################################################################
#
# Gestion scolarite IUT
#
# Copyright (c) 2001 - 2011 Emmanuel Viennet.  All rights reserved.
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA  02111-1307  USA
#
#   Emmanuel Viennet      emmanuel.viennet@viennet.net
#
##############################################################################


import pdb,os,sys,psycopg
from sco_exceptions import *
from notesdb import quote_dict
from notes_log import retreive_request
DB = psycopg

def logdb(REQUEST=None, cnx=None, method=None, etudid=None, msg=None, commit=True ):
    if not cnx:
        raise ValueError('logdb: cnx is None')
    if not REQUEST:
        REQUEST = retreive_request(skip=1)
    if REQUEST:
        args = { 'authenticated_user' : str(REQUEST.AUTHENTICATED_USER),
                 'remote_addr' : REQUEST.REMOTE_ADDR,
                 'remote_host' : REQUEST.REMOTE_HOST }
    else:
        args = { 'authenticated_user' : None,
                 'remote_addr' : None,
                 'remote_host' : None }
    args.update( { 'method' : method, 'etudid' : etudid, 'msg' : msg })
    quote_dict(args)
    cursor = cnx.cursor()
    cursor.execute('insert into scolog (authenticated_user,remote_addr,remote_host,method,etudid,msg) values (%(authenticated_user)s,%(remote_addr)s,%(remote_host)s,%(method)s,%(etudid)s,%(msg)s)', args )
    if commit:
        cnx.commit()

def loglist(cnx, method=None, authenticated_user=None):
    """List of events logged for these method and user
    """
    cursor = cnx.cursor()
    cursor.execute('select * from scolog where method=%(method)s and authenticated_user=%(authenticated_user)s', { 'method' : method, 'authenticated_user' : authenticated_user})
    return cursor.dictfetchall()
