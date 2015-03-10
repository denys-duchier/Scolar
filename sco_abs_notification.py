# -*- mode: python -*-
# -*- coding: utf-8 -*-

##############################################################################
#
# Gestion scolarite IUT
#
# Copyright (c) 2001 - 2015 Emmanuel Viennet.  All rights reserved.
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


Il suffit d'appeler abs_notify() après chaque ajout d'absence.
"""

from email.MIMEMultipart import MIMEMultipart
from email.MIMEText import MIMEText
from email.Header import Header
from email import Encoders

from notesdb import *
from sco_utils import *
from notes_log import log
from scolog import logdb
import sco_bulletins

def abs_notify(context, etudid, date):
    """Check if notifications are requested and send them
    Considère le nombre d'absence dans le semestre courant 
    (s'il n'y a pas de semestre courant, ne fait rien,
    car l'etudiant n'est pas inscrit au moment de l'absence!).
    """
    sem = retreive_current_formsemestre(context, etudid, date)
    if not sem:
        return # non inscrit a la date, pas de notification
    
    debut_sem = DateDMYtoISO(sem['date_debut'])
    fin_sem = DateDMYtoISO(sem['date_fin'])
    nbabs = context.CountAbs(etudid, debut=debut_sem, fin=fin_sem)
    nbabsjust = context.CountAbsJust(etudid, debut=debut_sem, fin=fin_sem)
    
    do_abs_notify(context, sem, etudid, date, nbabs, nbabsjust)

def do_abs_notify(context, sem, etudid, date, nbabs, nbabsjust):
    """Given new counts of absences, check if notifications are requested and send them.
    """
    # prefs fallback to global pref if sem is None:
    if sem:
        formsemestre_id = sem['formsemestre_id']
    else:
        formsemestre_id = None
    prefs = context.get_preferences(formsemestre_id=sem['formsemestre_id']) 
    
    destinations = abs_notify_get_destinations(context, sem, prefs, etudid, date, nbabs, nbabsjust)
    msg = abs_notification_message(context, sem, prefs, etudid, nbabs, nbabsjust)

    abs_notify_max_freq = context.get_preference('abs_notify_max_freq')
    destinations_filtered = []
    for email_addr in destinations:
        nbdays_since_last_notif = user_nbdays_since_last_notif(context, email_addr, etudid)
        if (nbdays_since_last_notif is None) or (nbdays_since_last_notif >= abs_notify_max_freq):
            destinations_filtered.append(email_addr)
    if destinations_filtered:
        abs_notify_send(context, destinations_filtered, etudid, msg, nbabs, nbabsjust, formsemestre_id)

def abs_notify_send(context, destinations, etudid, msg, nbabs, nbabsjust, formsemestre_id):
    """Actually send the notification by email, and register it in database"""
    cnx = context.GetDBConnexion()
    log('abs_notify: sending notification to %s' % destinations)
    cursor=cnx.cursor(cursor_factory=ScoDocCursor)
    for email in destinations:
        del msg['To']
        msg['To'] = email
        context.sendEmail(msg)
        SimpleQuery(context, """insert into absences_notifications (etudid, email, nbabs, nbabsjust, formsemestre_id) values (%(etudid)s, %(email)s, %(nbabs)s, %(nbabsjust)s, %(formsemestre_id)s)""", vars(), cursor=cursor)
    
    logdb(cnx=cnx, method='abs_notify', etudid=etudid, msg='sent to %s (nbabs=%d)' % (destinations, nbabs))


def abs_notify_get_destinations(context, sem, prefs, etudid, date, nbabs, nbabsjust):
    """Returns set of destination emails to be notified
    """
    formsemestre_id = sem['formsemestre_id']
    
    destinations = [] # list of email address to notify
    
    if abs_notify_is_above_threshold(context, etudid, nbabs, nbabsjust, formsemestre_id):
        if sem and prefs['abs_notify_respsem']:
            u = context.Users.user_info(sem['responsable_id'])
            if u['email']:
                destinations.append(u['email'])
        if prefs['abs_notify_chief'] and prefs['email_chefdpt']:
            destinations.append(prefs['email_chefdpt'])
        if prefs['abs_notify_email']:
            destinations.append(prefs['abs_notify_email'])
        if prefs['abs_notify_etud']:
            etud = context.getEtudInfo(etudid=etudid, filled=1)[0]
            if etud['email']:
                destinations.append(etud['email'])        
    
    # Notification (à chaque fois) des resp. de modules ayant des évaluations
    # à cette date
    # nb: on pourrait prevoir d'utiliser un autre format de message pour ce cas
    if sem and prefs['abs_notify_respeval']:
        mods = mod_with_evals_at_date(context, date, etudid)
        for mod in mods:
            u = context.Users.user_info(mod['responsable_id'])
            if u['email']:
                destinations.append(u['email'])
    
    # uniq
    destinations = set(destinations)
    
    return destinations

def abs_notify_is_above_threshold(context, etudid, nbabs, nbabsjust, formsemestre_id):
    """True si il faut notifier les absences (indépendemment du destinataire)
    (nbabs > abs_notify_abs_threshold) 
    (nbabs - nbabs_last_notified) > abs_notify_abs_increment
    """
    abs_notify_abs_threshold = context.get_preference('abs_notify_abs_threshold', formsemestre_id)
    abs_notify_abs_increment = context.get_preference('abs_notify_abs_increment', formsemestre_id)
    nbabs_last_notified = etud_nbabs_last_notified(context, etudid, formsemestre_id)
    
    if nbabs_last_notified == 0:
        if nbabs > abs_notify_abs_threshold:
            return True # first notification
        else:
            return False
    else:
        if (nbabs - nbabs_last_notified) >= abs_notify_abs_increment:
            return True
    return False


def etud_nbabs_last_notified(context, etudid, formsemestre_id=None):
    """nbabs lors de la dernière notification envoyée pour cet étudiant dans ce semestre
    ou sans semestre (ce dernier cas est nécessaire pour la transition au nouveau code)"""
    cnx = context.GetDBConnexion()
    cursor = cnx.cursor(cursor_factory=ScoDocCursor)
    cursor.execute("""select * from absences_notifications where etudid = %(etudid)s and (formsemestre_id = %(formsemestre_id)s or formsemestre_id is NULL) order by notification_date desc""",
                   vars() )
    res = cursor.dictfetchone()
    if res:
        return res['nbabs']
    else:
        return 0

def user_nbdays_since_last_notif(context, email_addr, etudid):
    """nb days since last notification to this email, or None if no previous notification"""
    cnx = context.GetDBConnexion()
    cursor = cnx.cursor(cursor_factory=ScoDocCursor)
    cursor.execute("""select * from absences_notifications where email = %(email_addr)s and etudid=%(etudid)s order by notification_date desc""", {'email_addr' : email_addr, 'etudid' : etudid} )
    res = cursor.dictfetchone()
    if res:
        mxd = res['notification_date'] # mx.DateTime instance
        lastdate = datetime.datetime(mxd.year, mxd.month, mxd.day)
        now = datetime.datetime.now()
        return (now - lastdate).days
    else:
        return None
    
def abs_notification_message(context, sem, prefs, etudid, nbabs, nbabsjust):
    """Mime notification message based on template"""
    etud = context.getEtudInfo(etudid=etudid,filled=True)[0]

    # Variables accessibles dans les balises du template: %(nom_variable)s :
    values = sco_bulletins.make_context_dict(context, sem, etud)
    
    values['nbabs'] = nbabs
    values['nbabsjust'] = nbabsjust
    values['nbabsnonjust'] = nbabs - nbabsjust
    values['url_ficheetud'] = context.ScoURL() + '/ficheEtud?etudid=' + etudid
    
    txt = prefs['abs_notification_mail_tmpl'] % values
    subject = """Trop d'absences pour %(nomprenom)s""" % etud
    #
    msg = MIMEMultipart()
    subj = Header( '[ScoDoc] ' + subject,  SCO_ENCODING )
    msg['Subject'] = subj
    msg['From'] = prefs['email_from_addr']
    txt = MIMEText( txt, 'plain', SCO_ENCODING )
    msg.attach(txt)
    return msg

def retreive_current_formsemestre(context, etudid, cur_date):
    """Get formsemestre dans lequel etudid est (ou était) inscrit a la date indiquée
    date est une chaine au format ISO (yyyy-mm-dd)
    """
    req = """SELECT i.formsemestre_id FROM notes_formsemestre_inscription i, notes_formsemestre sem
    WHERE sem.formsemestre_id = i.formsemestre_id AND i.etudid=%(etudid)s
    AND (%(cur_date)s >= sem.date_debut) AND (%(cur_date)s <= sem.date_fin)"""

    r = SimpleDictFetch(context, req, { 'etudid' : etudid, 'cur_date' : cur_date })
    if not r:
        return None
    # s'il y a plusieurs semestres, prend le premier (rarissime et non significatif):
    sem = context.Notes.get_formsemestre(r[0]['formsemestre_id'])
    return sem

def mod_with_evals_at_date(context, date_abs, etudid):
    """Liste des moduleimpls avec des evaluations a la date indiquée
    """
    req = """SELECT m.* FROM notes_moduleimpl m, notes_evaluation e, notes_moduleimpl_inscription i
    WHERE m.moduleimpl_id = e.moduleimpl_id AND e.moduleimpl_id = i.moduleimpl_id
    AND i.etudid = %(etudid)s AND e.jour = %(date_abs)s"""
    r = SimpleDictFetch(context, req, { 'etudid' : etudid, 'date_abs' : date_abs })
    return r

