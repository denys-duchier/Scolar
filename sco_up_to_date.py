# -*- mode: python -*-
# -*- coding: iso8859-15 -*-

##############################################################################
#
# Gestion scolarite IUT
#
# Copyright (c) 2001 - 2013 Emmanuel Viennet.  All rights reserved.
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


""" Verification version logiciel vs version "stable" sur serveur
    N'effectue pas la mise à jour automatiquement, mais permet un affichage d'avertissement.
"""

from sco_utils import *

# Appel renvoyant la subversion "stable"
# La notion de "stable" est juste là pour éviter d'afficher trop frequemment
# des avertissements de mise à jour: on veut pouvoir inciter à mettre à jour lors de
# correctifs majeurs.

GET_VER_URL = 'http://notes.iutv.univ-paris13.fr/scodoc-installmgr/last_stable_version'

def get_last_stable_version():
    """request last stable version number from server
    (returns string as given by server, empty if failure)
    (do not wait server answer more than 3 seconds)
    """
    global _LAST_UP_TO_DATE_REQUEST
    ans = query_portal(GET_VER_URL, msg='ScoDoc version server', timeout=3) # sco_utils
    if ans:
        ans = ans.strip()
    _LAST_UP_TO_DATE_REQUEST = datetime.datetime.now()
    log('get_last_stable_version: updated at %s, answer="%s"' % (_LAST_UP_TO_DATE_REQUEST, ans))
    return ans

_LAST_UP_TO_DATE_REQUEST = None # datetime of last request to server
_UP_TO_DATE = True # cached result (limit requests to 1 per day)
_UP_TO_DATE_MSG = ''

def is_up_to_date(context):
    """True if up_to_date
    Returns status, message
    """
    global _LAST_UP_TO_DATE_REQUEST, _UP_TO_DATE, _UP_TO_DATE_MSG
    if (_LAST_UP_TO_DATE_REQUEST
        and (datetime.datetime.now() - _LAST_UP_TO_DATE_REQUEST) < datetime.timedelta(1)):
        # requete deja effectuee aujourd'hui:
        return _UP_TO_DATE, _UP_TO_DATE_MSG
    
    last_stable_ver = get_last_stable_version()
    cur_ver = get_svn_version(context.file_path) # in sco_utils
    # Convert versions to integers:
    try:
        # cur_ver can be "1234" or "1234M' or '1234:1245M'...
        fs = cur_ver.split(':',1)
        if len(fs) > 1:
            cur_ver2 = fs[-1]
        else:
            cur_ver2 = cur_ver
        m = re.match( r'([0-9]*)', cur_ver2 )
        if not m:
            raise ValueError('invalid svn version') # should never occur, regexp always (maybe empty) match
        cur_ver_num = int(m.group(1))
    except:
        log('Warning: no numeric subversion !')
        return _UP_TO_DATE, _UP_TO_DATE_MSG # silently ignore misconfiguration ?
    try:
        last_stable_ver_num = int(last_stable_ver)
    except:
        log('Warning: last_stable_version returned by server is invalid !')
        return  _UP_TO_DATE, _UP_TO_DATE_MSG # should ignore this error (maybe server is unreachable)
    #
    if cur_ver_num < last_stable_ver_num:
        _UP_TO_DATE = False
        _UP_TO_DATE_MSG = 'Version %s disponible (version %s installée)' % (last_stable_ver, cur_ver_num)
        log('Warning: ScoDoc installation is not up-to-date, should upgrade\n%s' % _UP_TO_DATE_MSG)
    else:
        _UP_TO_DATE = True
        _UP_TO_DATE_MSG = ''
        log('ScoDoc is up-to-date (cur_ver: %s)' % cur_ver)
    
    return _UP_TO_DATE, _UP_TO_DATE_MSG

def html_up_to_date_box(context):
    """
    """
    status, msg = is_up_to_date(context)
    if status:
        return ''
    return """<div class="update_warning">
    <span>Attention: cette installation de ScoDoc n'est pas à jour.</span>
    <div class="update_warning_sub">Contactez votre administrateur. %s</div>
    </div>""" % msg


