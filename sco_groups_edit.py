# -*- mode: python -*-
# -*- coding: utf-8 -*-

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

"""Formulaires gestion des groupes
"""

import re

from sco_utils import *
from notesdb import *
from notes_log import log
import sco_groups

def affectGroups(context, partition_id, REQUEST=None):
    """Formulaire affectation des etudiants aux groupes de la partition.
    Permet aussi la creation et la suppression de groupes.
    """
    # Ported form DTML and adapted to new group management (nov 2009)
    partition = sco_groups.get_partition(context, partition_id)
    formsemestre_id = partition['formsemestre_id']
    if not context.Notes.can_change_groups(REQUEST,formsemestre_id):
        raise AccessDenied("vous n'avez pas la permission d'effectuer cette opération")
    
    sem = context.Notes.get_formsemestre(formsemestre_id)
    
    H = [ context.sco_header(
        REQUEST, page_title='Affectation aux groupes',
        javascripts=['js/groupmgr.js'],
        cssstyles=['groups.css']
        ),
        """<h2 class="formsemestre">Affectation aux groupes de %s</h2><form id="sp">""" % partition['partition_name']]    
    
    H += [
        """</select></form>""",
        """<p>Faites glisser les étudiants d'un groupe à l'autre. Les modifications ne sont enregistrées que lorsque vous cliquez sur le bouton "<em>Enregistrer ces groupes</em>". Vous pouvez créer de nouveaux groupes. Pour <em>supprimer</em> un groupe, utiliser le lien "suppr." en haut à droite de sa boite. Vous pouvez aussi <a class="stdlink" href="groups_auto_repartition?partition_id=%(partition_id)s">répartir automatiquement les groupes</a>.
</p>""" % partition,
        """<div id="gmsg" class="head_message"></div>""",
        """<div id="ginfo"></div>""",
        """<div id="savedinfo"></div>""",
        """<form name="formGroup" id="formGroup" onSubmit="return false;">""",
        """<input type="hidden" name="partition_id" value="%s"/>""" % partition_id,
        """<input name="groupName" size="6"/>
<input type="button" onClick="createGroup();" value="Créer groupe"/>
&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;
<input type="button" onClick="submitGroups( target='gmsg' );" value="Enregistrer ces groupes" />
&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;
<input type="button" onClick="document.location = 'formsemestre_status?formsemestre_id=%s'" value="Annuler" />&nbsp;&nbsp;&nbsp;&nbsp;
Editer groupes de
<select name="other_partition_id" onchange="GotoAnother();">""" % formsemestre_id ]
    for p in sco_groups.get_partitions_list(context, formsemestre_id, with_default=False):
        H.append('<option value="%s"' % p['partition_id'])
        if p['partition_id'] == partition_id:
            H.append(' selected')
        H.append('>%s</option>' % p['partition_name'])
    H += [ """</select>
</form>

<div id="groups">
</div>

<div style="clear: left; margin-top: 15px;">
<p class="help"></p>
</div>

</div>
""" ,
           context.sco_footer(REQUEST)
           ]
    return '\n'.join(H)
