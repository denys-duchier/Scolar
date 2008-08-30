# -*- mode: python -*-
# -*- coding: iso8859-15 -*-

##############################################################################
#
# Gestion scolarite IUT
#
# Copyright (c) 2001 - 2006 Emmanuel Viennet.  All rights reserved.
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

from sco_utils import *
from sco_formsemestre_status import formsemestre_page_title

"""
Main HTML page header for ScoDoc
"""

def sco_header(context, REQUEST=None, 
               # optional args
               container=None,     # objet qui a lancé la demande
               page_title='',      # page title
               no_side_bar=False,  # hide sidebar
               cssstyles=[],       # additionals CSS sheets
               javascripts=[],     # additionals JS
               bodyOnLoad='',      # JS
               titrebandeau='',    # titre dans bandeau superieur
               head_message='',    # message action (petit cadre jaune en haut)
               ):    
    "Main HTML page header for ScoDoc"

    # If running for first time, initialize roles and permissions
    try:
        ri = context.roles_initialized
    except:
        ri = None # old instances does not have this attribute
    if ri == '0':
        context._setup_initial_roles_and_permissions()

    # context est une instance de ZScolar. container est une instance qui "acquiert" ZScolar
    if container:
        context = container # je pense que cela suffit pour ce qu'on veut.

    # Add a HTTP header (can be used by Apache to log requests)
    if REQUEST.AUTHENTICATED_USER:
        REQUEST.RESPONSE.setHeader('X-ScoDoc-User', str(REQUEST.AUTHENTICATED_USER))

    # Get more parameters from REQUEST
    if not head_message and REQUEST.form.has_key('head_message'):
        head_message = REQUEST.form['head_message']
    
    params = {
        'page_title' : page_title or context.title_or_id(),
        'no_side_bar': no_side_bar,
        'ScoURL' : context.ScoURL(),
        'encoding' : SCO_ENCODING,
        # 'maincss_url' : context.gtrintranetstyle.absolute_url(), (si style Zope)
        'maincss_url' : context.ScoURL() + '/' + 'scodoc_css',
        'titrebandeau_mkup' : '<td>' + titrebandeau + '</td>',
        'authuser' : str(REQUEST.AUTHENTICATED_USER),
        }
    if no_side_bar:
        params['maincss_args'] = '?no_side_bar=1'
    else:
        params['maincss_args'] = ''
    if bodyOnLoad:
        params['bodyOnLoad_mkup'] = """onload="%s" """ % bodyOnLoad
    else:
        params['bodyOnLoad_mkup'] = ''
    if no_side_bar:
        params['margin_left'] = "1em"
    else:
        params['margin_left'] = "140px"
    H = [ """<?xml version="1.0" encoding="%(encoding)s"?>
<!DOCTYPE html PUBLIC "-//W3C//DTD XHTML 1.0 Transitional//EN" "http://www.w3.org/TR/xhtml1/DTD/xhtml1-transitional.dtd">
<html xmlns="http://www.w3.org/1999/xhtml">
<head>
<title>%(page_title)s</title>
<meta http-equiv="Content-Type" content="text/html; charset=%(encoding)s" />
<meta http-equiv="Content-Style-Type" content="text/css" />
<meta name="LANG" content="fr" />
<meta name="DESCRIPTION" content="ScoDoc" />

<link href="%(maincss_url)s%(maincss_args)s" rel="stylesheet" type="text/css" />
<link href="%(ScoURL)s/menu_css" rel="stylesheet" type="text/css" />
<script language="javascript" type="text/javascript" src="%(ScoURL)s/menu_js"></script>
<script language="javascript" type="text/javascript" src="%(ScoURL)s/sorttable_js"></script>
<script language="javascript" type="text/javascript" src="%(ScoURL)s/bubble_js"></script>
<script type="text/javascript">
window.onload=function(){enableTooltips("gtrcontent")};
</script>
<style>
.gtrcontent {
   margin-left: %(margin_left)s;
   height: 100%%;
}
</style>
""" % params
          ]
    # Feuilles de style additionnelles:
    for cssstyle in cssstyles:
        H.append( """<link type="text/css" rel="stylesheet" href="%s/%s" />"""
                  % (params['ScoURL'], cssstyle) )
    # JS additionels
    for js in javascripts:
        H.append( """<script language="javascript" type="text/javascript" src="%s/%s"></script>"""
                  % (params['ScoURL'], js) )
    H.append('</head>')
    # Body et bandeau haut:
    H.append("""<body %(bodyOnLoad_mkup)s>"""%params)
#<span class="bandeaugtr">
#<span id="authuser"><a id="authuserlink" href="%(ScoURL)s/Users/userinfo">%(authuser)s</a>
#&nbsp;&nbsp;&nbsp;<a id="deconnectlink" href="%(ScoURL)s/acl_users/logout">déconnexion</a></span></span>
#""" % params )
    #
    if not no_side_bar:
        H.append( context.sidebar(REQUEST) )
    H.append("""<div class="gtrcontent" id="gtrcontent">""")
    #
    # Barre menu semestre:
    H.append( formsemestre_page_title(context, REQUEST) )
    #
    if head_message:
        H.append('<div class="head_message">' + cgi.escape(head_message) + '</div>')
    #
    return ''.join(H)

    
def sco_footer(context, REQUEST=None):
    """Main HTMl pages footer
    """
    return """</div> <!-- gtr-content -->
</body></html>"""



