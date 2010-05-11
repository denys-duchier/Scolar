# -*- mode: python -*-
# -*- coding: iso8859-15 -*-

##############################################################################
#
# Gestion scolarite IUT
#
# Copyright (c) 2001 - 2010 Emmanuel Viennet.  All rights reserved.
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

"""Système de notification par mail des excès d'absences
(see ticket #147)
"""


from notesdb import *
from sco_utils import *
from notes_log import log
import sco_groups
from scolars import format_nom, format_prenom, format_sexe, format_lycee
from ZAbsences import getAbsSemEtud

def abs_notify(context, etudid, date, nbabs, nbabsjust):
    """Given new counts of absences, check if notifications are requested and send them.
    """
    sem = retreive_current_formsemestre(context, etudid, date)
    if sem:
        formsemestre_id = sem['formsemestre_id']
    else:
        formsemestre_id = None
    # prefs fallback to global pref if sem is None:
    sem_prefs = context.get_preferences(formsemestre_id=formsemestre_id) 
    
    destinations = [] # list of email address to notify


    if abs_notify_above_threshold(context, etudid, nbabs, nbabsjust, formsemestre_id):
        if sem and sem_prefs['abs_notify_respsem']:
            u = context.Users.user_info(sem['responsable_id'])
            if u['email']:
                destinations.append(u['email'])
        

    # Notification (à chaque fois) des resp. de modules ayant des évaluations
    # à cette date
    # nb: on pourrait prevoir d'utiliser un autre format de message pour ce cas
    if sem and sem_prefs['abs_notify_respeval']:
        mods = sem_mod_with_evals_at_date(context, sem, date, etudid)
        for mod in mods:
            u = context.Users.user_info(mod['responsable_id'])
            if u['email']:
                destinations.append(u['email'])
    
    

def abs_notify_above_threshold(context, etudid, nbabs, nbabsjust, formsemestre_id):
    """True si il faut notifier les absences (indépendemment du destinataire)
    (nbabs > abs_notify_abs_threshold) 
    (nbabs - nbabs_last_notified) > abs_notify_abs_increment
    """
    abs_notify_abs_threshold = context.get_preference('abs_notify_abs_threshold', formsemestre_id)
    abs_notify_abs_increment = context.get_preference('abs_notify_abs_increment', formsemestre_id)
    nbabs_last_notified = etud_nbabs_last_notified(context, etudid)
    
    if nbabs_last_notified == 0:
        if nbabs > abs_notify_abs_threshold:
            return True # first notification
        else:
            return False
    else:
        if (nbabs - nbabs_last_notified) > abs_notify_abs_increment:
            return True
    return False


def etud_nbabs_last_notified(context, etudid):
    """nbabs lors de la dernière notification envoyée pour cet étudiant"""
    cnx = self.GetDBConnexion()
    cursor = cnx.cursor()
    cursor.execute("""select * from absences_notifications where etudid = %(etudid)s order by notification_date desc""")
    res = cursor.dictfetchone()
    if res:
        return res['nbabs']
    else:
        return 0

    abs_notify_max_freq = context.get_preference('abs_notify_max_freq', formsemestre_id)
    
