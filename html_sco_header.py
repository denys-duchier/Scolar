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
               javascripts=[],     # additionals JS filenames to load
               scripts=[],         # script to put in page header
               bodyOnLoad='',      # JS
               init_jquery=False,  # load and init jQuery
               init_jquery_ui=False,# include all stuff for jquery-ui and initialize scripts
               init_google_maps=False,# Google maps
               titrebandeau='',    # titre dans bandeau superieur
               head_message='',    # message action (petit cadre jaune en haut)
               user_check=True     # verifie passwords temporaires
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
        'titrebandeau_mkup' : '<td>' + titrebandeau + '</td>',
        'authuser' : str(REQUEST.AUTHENTICATED_USER),
        }
    if bodyOnLoad:
        params['bodyOnLoad_mkup'] = """onload="%s" """ % bodyOnLoad
    else:
        params['bodyOnLoad_mkup'] = ''
    if no_side_bar:
        params['margin_left'] = "1em"
    else:
        params['margin_left'] = "140px"

    if init_jquery_ui:
        init_jquery = True

    H = [ """<?xml version="1.0" encoding="%(encoding)s"?>
<!DOCTYPE html PUBLIC "-//W3C//DTD XHTML 1.0 Transitional//EN" "http://www.w3.org/TR/xhtml1/DTD/xhtml1-transitional.dtd">
<html xmlns="http://www.w3.org/1999/xhtml">
<head>
<title>%(page_title)s</title>
<meta http-equiv="Content-Type" content="text/html; charset=%(encoding)s" />
<meta http-equiv="Content-Style-Type" content="text/css" />
<meta name="LANG" content="fr" />
<meta name="DESCRIPTION" content="ScoDoc" />

<link href="/ScoDoc/static/css/scodoc.css" rel="stylesheet" type="text/css" />
<link href="/ScoDoc/static/css/menu.css" rel="stylesheet" type="text/css" />""" % params ]
    # jQuery UI
    if init_jquery_ui:
        # can modify loaded theme here
        H.append('<link type="text/css" rel="stylesheet" href="/ScoDoc/static/libjs/jquery-ui/css/custom-theme/jquery-ui-1.7.2.custom.css" />\n')
    if init_google_maps:
        H.append('<script type="text/javascript" src="https://maps.google.com/maps/api/js?sensor=false"></script>')
    # Feuilles de style additionnelles:
    for cssstyle in cssstyles:
        H.append( """<link type="text/css" rel="stylesheet" href="/ScoDoc/static/css/%s" />\n"""
                  % cssstyle )
    
    H.append( """
<script language="javascript" type="text/javascript" src="/ScoDoc/static/libjs/menu.js"></script>
<script language="javascript" type="text/javascript" src="/ScoDoc/static/libjs/sorttable.js"></script>
<script language="javascript" type="text/javascript" src="/ScoDoc/static/libjs/bubble.js"></script>
<script type="text/javascript">
 window.onload=function(){enableTooltips("gtrcontent")};
</script>""" % params )

    # jQuery
    if init_jquery:
        H.append('<script language="javascript" type="text/javascript" src="/ScoDoc/static/jQuery/jquery.js"></script>')
    if init_jquery_ui:
        H.append('<script language="javascript" type="text/javascript" src="/ScoDoc/static/libjs/jquery-ui/js/jquery-ui-1.7.2.custom.min.js"></script>')
        H.append('<script language="javascript" type="text/javascript" src="/ScoDoc/static/libjs/jquery-ui/js/jquery-ui-i18n.js"></script>')
    if init_google_maps:
        H.append('<script type="text/javascript" src="/ScoDoc/static/libjs/jquery.ui.map.full.min.js"></script>')
    # JS additionels
    for js in javascripts:
        H.append( """<script language="javascript" type="text/javascript" src="/ScoDoc/static/%s"></script>\n"""
                  % js )

    H.append( """<style>
.gtrcontent {
   margin-left: %(margin_left)s;
   height: 100%%;
}
</style>
""" % params )
    # jQuery initialization
    if init_jquery_ui:
        H.append( """<script language="javascript" type="text/javascript">
           $(function() {
		$(".datepicker").datepicker({
                      showOn: 'button', 
                      buttonImage: '/ScoDoc/static/icons/calendar_img.png', 
                      buttonImageOnly: true,
                      dateFormat: 'dd/mm/yy',   
                      duration : 'fast',                   
                  });
                $('.datepicker').datepicker('option', $.extend({showMonthAfterYear: false},
				$.datepicker.regional['fr']));

	    });
        </script>""" )
    # Scripts de la page:
    if scripts:
        H.append( """<script language="javascript" type="text/javascript">""" )
        for script in scripts:
            H.append(script)
        H.append("""</script>""")

    H.append('</head>')
    
    # Body et bandeau haut:
    H.append("""<body %(bodyOnLoad_mkup)s>"""%params)
    H.append(CUSTOM_HTML_HEADER)
    #
    if not no_side_bar:
        H.append( context.sidebar(REQUEST) )
    H.append("""<div class="gtrcontent" id="gtrcontent">""")
    #
    # Barre menu semestre:
    H.append( formsemestre_page_title(context, REQUEST) )

    # Avertissement si mot de passe à changer
    if user_check:
        authuser = REQUEST.AUTHENTICATED_USER
        passwd_temp = context.Users.user_info(user_name=str(authuser))['passwd_temp']
        if passwd_temp:
            H.append('''<div class="passwd_warn">
    Attention !<br/>
    Vous avez reçu un mot de passe temporaire.<br/>
    Vous devez le changer: <a href="%s/Users/form_change_password?user_name=%s">cliquez ici</a>
    </div>''' % (context.ScoURL(), str(authuser)) )
    #
    if head_message:
        H.append('<div class="head_message">' + cgi.escape(head_message) + '</div>')
    #
    return ''.join(H)

    
def sco_footer(context, REQUEST=None):
    """Main HTMl pages footer
    """
    return """</div><!-- /gtrcontent -->""" + CUSTOM_HTML_FOOTER + """</body></html>"""



