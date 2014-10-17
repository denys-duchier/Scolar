# -*- mode: python -*-
# -*- coding: utf-8 -*-

##############################################################################
#
# Gestion scolarite IUT
#
# Copyright (c) 2001 - 2014 Emmanuel Viennet.  All rights reserved.
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

""" Gestion des absences (v4)

C'est la partie la plus ancienne de ScoDoc, et elle est à revoir.

L'API de plus bas niveau est en gros:

 AnnuleAbsencesDatesNoJust(etudid, dates)
 CountAbs(etudid, debut, fin, matin=None, moduleimpl_id=None)
 CountAbsJust(etudid, debut, fin, matin=None, moduleimpl_id=None)
 ListeAbsJust(etudid, datedebut)  [pas de fin ?]
 ListeAbsNonJust(etudid, datedebut)  [pas de fin ?]
 ListeJustifsNoAbs(etudid, datedebut, datefin=None, only_no_abs=True)

 ListeAbsJour(date, am=True, pm=True, is_abs=None, is_just=None)
 ListeAbsNonJustJour(date, am=True, pm=True)


"""

import urllib

from sco_zope import *

# ---------------

from notesdb import *
from notes_log import log
from scolog import logdb
from sco_utils import *
#import notes_users
from TrivialFormulator import TrivialFormulator, TF
from gen_tables import GenTable
import scolars
import sco_groups
import sco_groups_view
import sco_excel
import sco_abs_notification, sco_abs_views
import sco_compute_moy
import string, re
import time, calendar 
from mx.DateTime import DateTime as mxDateTime
from mx.DateTime.ISO import ParseDateTimeUTC

def _toboolean(x):
    "convert a value to boolean (ensure backward compat with OLD intranet code)"
    if type(x) == type(''):
        x = x.lower()
    if x and x != 'false': # backward compat...
        return True
    else:
        return False


def MonthNbDays(month,year):
    "returns nb of days in month"
    if month > 7:
        month = month+1
    if month % 2:
        return 31
    elif month == 2:
        if calendar.isleap(year):
            return 29
        else:
            return 28
    else:
        return 30

class ddmmyyyy:
    """immutable dates"""
    def __init__(self, date=None, fmt='ddmmyyyy', work_saturday=False):
        self.work_saturday = work_saturday
        if date is None:
            return
        try:
            if fmt == 'ddmmyyyy':
                self.day, self.month, self.year = string.split(date, '/')
            elif fmt == 'iso':
                self.year, self.month, self.day = string.split(date, '-')
            else:
                raise ValueError('invalid format spec. (%s)' % fmt)
            self.year = string.atoi(self.year)
            self.month = string.atoi(self.month)
            self.day = string.atoi(self.day)
        except:
            raise ScoValueError('date invalide: %s' % date)
        # accept years YYYY or YY, uses 1970 as pivot
        if self.year < 1970:
            if self.year > 100:
                raise ScoValueError('Année invalide: %s' % self.year)
            if self.year < 70:
                self.year = self.year + 2000
            else:
                self.year = self.year + 1900
        if self.month < 1 or self.month > 12:
            raise ScoValueError('Mois invalide: %s' % self.month)
        
        if self.day < 1 or self.day > MonthNbDays(self.month,self.year):
            raise ScoValueError('Jour invalide: %s' % self.day)
        
        # weekday in 0-6, where 0 is monday
        self.weekday = calendar.weekday(self.year,self.month,self.day)
        
        self.time = time.mktime( (self.year,self.month,self.day,0,0,0,0,0,0) )
    
    def iswork(self):
        "returns true if workable day"
        if self.work_saturday:
            nbdays = 6
        else:
            nbdays = 5
        if self.weekday >= 0 and self.weekday < nbdays: # monday-friday or monday-saturday
            return 1
        else:
            return 0
    
    def __repr__(self):
        return "'%02d/%02d/%04d'" % (self.day,self.month, self.year)
    def __str__(self):
        return '%02d/%02d/%04d' % (self.day,self.month, self.year)
    def ISO(self):
        "iso8601 representation of the date"
        return '%04d-%02d-%02d' % (self.year, self.month, self.day)
    
    def next(self,days=1):
        "date for the next day (nota: may be a non workable day)"
        day = self.day + days        
        month = self.month
        year = self.year
        
        while day > MonthNbDays(month,year):
            day = day - MonthNbDays(month,year)
            month = month + 1
            if month > 12:
                month = 1
                year = year + 1
        return self.__class__( '%02d/%02d/%04d' % (day,month,year), work_saturday=self.work_saturday )
    
    def prev(self,days=1):
        "date for previous day"
        day = self.day - days 
        month = self.month
        year = self.year        
        while day <= 0:
            month = month - 1
            if month == 0:
                month = 12
                year = year - 1            
            day = day + MonthNbDays(month,year)
        
        return self.__class__( '%02d/%02d/%04d' % (day,month,year), work_saturday=self.work_saturday )
    
    def next_monday(self):
        "date of next monday"
        return self.next((7-self.weekday) % 7)

    def prev_monday(self):
        "date of last monday, but on sunday, pick next monday"
        if self.weekday == 6:
            return self.next_monday()
        else:
            return self.prev(self.weekday)
    
    def __cmp__ (self, other):
        """return a negative integer if self < other, 
        zero if self == other, a positive integer if self > other"""
        return int(self.time - other.time)
    
    def __hash__(self):
        "we are immutable !"
        return hash(self.time) ^ hash(str(self))

# d = ddmmyyyy( '21/12/99' )


def YearTable(context, year, events=[],
              firstmonth=9, lastmonth=7, halfday=0, dayattributes='',
              pad_width=8
              ):
    """Generate a calendar table
    events = list of tuples (date, text, color, href [,halfday])
             where date is a string in ISO format (yyyy-mm-dd)
             halfday is boolean (true: morning, false: afternoon)
    text  = text to put in calendar (must be short, 1-5 cars) (optional)
    if halfday, generate 2 cells per day (morning, afternoon)
    """
    T = [ '<table id="maincalendar" class="maincalendar" border="3" cellpadding="1" cellspacing="1" frame="box">' ]
    T.append( '<tr>' )
    month = firstmonth
    while 1:
        T.append( '<td valign="top">' )
        T.append( MonthTableHead( month ) )
        T.append( MonthTableBody( month, year, events, halfday, dayattributes, context.is_work_saturday(), pad_width=pad_width ) )
        T.append( MonthTableTail() )
        T.append( '</td>' )
        if month == lastmonth:
            break
        month = month + 1
        if month > 12:
            month = 1
            year = year + 1
    T.append('</table>')
    return string.join(T,'\n')


# ---------------

class ZAbsences(ObjectManager,
                PropertyManager,
                RoleManager,
                Item,
                Persistent,
                Implicit
                ):

    "ZAbsences object"

    meta_type = 'ZAbsences'
    security=ClassSecurityInfo()

    # This is the list of the methods associated to 'tabs' in the ZMI
    # Be aware that The first in the list is the one shown by default, so if
    # the 'View' tab is the first, you will never see your tabs by cliquing
    # on the object.
    manage_options = (
        ( {'label': 'Contents', 'action': 'manage_main'}, )
        + PropertyManager.manage_options # add the 'Properties' tab
        + (
            {'label': 'View',       'action': 'index_html'},
            )
        + Item.manage_options            # add the 'Undo' & 'Owner' tab 
        + RoleManager.manage_options     # add the 'Security' tab
        )

    # no permissions, only called from python
    def __init__(self, id, title):
        "initialise a new instance"
        self.id = id
        self.title = title
    
    # The form used to edit this object
    def manage_editZAbsences(self, title, RESPONSE=None):
        "Changes the instance values"
        self.title = title
        self._p_changed = 1
        RESPONSE.redirect('manage_editForm')

    # --------------------------------------------------------------------
    #
    #   ABSENCES (top level)
    #
    # --------------------------------------------------------------------
    # used to view content of the object
    security.declareProtected(ScoView, 'index_html')
    index_html = sco_abs_views.absences_index_html

    security.declareProtected(ScoView, 'EtatAbsences')
    EtatAbsences = sco_abs_views.EtatAbsences

    security.declareProtected(ScoView, 'CalAbs')
    CalAbs = sco_abs_views.CalAbs

    security.declareProtected(ScoAbsChange, 'SignaleAbsenceEtud')
    SignaleAbsenceEtud = sco_abs_views.SignaleAbsenceEtud
    security.declareProtected(ScoAbsChange, 'doSignaleAbsence')
    doSignaleAbsence = sco_abs_views.doSignaleAbsence

    security.declareProtected(ScoAbsChange, 'JustifAbsenceEtud')
    JustifAbsenceEtud = sco_abs_views.JustifAbsenceEtud
    security.declareProtected(ScoAbsChange, 'doJustifAbsence')
    doJustifAbsence = sco_abs_views.doJustifAbsence

    security.declareProtected(ScoAbsChange, 'AnnuleAbsenceEtud')
    AnnuleAbsenceEtud = sco_abs_views.AnnuleAbsenceEtud
    security.declareProtected(ScoAbsChange, 'doAnnuleAbsence')
    doAnnuleAbsence = sco_abs_views.doAnnuleAbsence
    security.declareProtected(ScoAbsChange, 'doAnnuleJustif')
    doAnnuleJustif = sco_abs_views.doAnnuleJustif

    security.declareProtected(ScoView, 'ListeAbsEtud')
    ListeAbsEtud = sco_abs_views.ListeAbsEtud

    # --------------------------------------------------------------------
    #
    #   SQL METHODS
    #
    # --------------------------------------------------------------------

    def _AddAbsence(self, etudid, jour, matin, estjust, REQUEST, description=None, moduleimpl_id=None):
        "Ajoute une absence dans la bd"
        # unpublished
        if self._isFarFutur(jour):
            raise ScoValueError('date absence trop loin dans le futur !')
        estjust = _toboolean(estjust)
        matin = _toboolean(matin)
        cnx = self.GetDBConnexion()
        cursor = cnx.cursor(cursor_factory=ScoDocCursor)
        cursor.execute('insert into absences (etudid,jour,estabs,estjust,matin,description, moduleimpl_id) values (%(etudid)s, %(jour)s, TRUE, %(estjust)s, %(matin)s, %(description)s, %(moduleimpl_id)s )', vars())
        logdb(REQUEST, cnx, 'AddAbsence', etudid=etudid,
              msg='JOUR=%(jour)s,MATIN=%(matin)s,ESTJUST=%(estjust)s,description=%(description)s,moduleimpl_id=%(moduleimpl_id)s'%vars())
        cnx.commit()
        invalidateAbsEtudDate(self, etudid, jour)
        sco_abs_notification.abs_notify(self, etudid, jour)
    
    def _AddJustif(self, etudid, jour, matin, REQUEST, description=None):
        "Ajoute un justificatif dans la base"
        # unpublished
        if self._isFarFutur(jour):
            raise ScoValueError('date justificatif trop loin dans le futur !')
        matin = _toboolean(matin)
        cnx = self.GetDBConnexion()
        cursor = cnx.cursor(cursor_factory=ScoDocCursor)
        cursor.execute('insert into absences (etudid,jour,estabs,estjust,matin, description) values (%(etudid)s,%(jour)s, FALSE, TRUE, %(matin)s, %(description)s )', vars() )
        logdb(REQUEST, cnx, 'AddJustif', etudid=etudid,
              msg='JOUR=%(jour)s,MATIN=%(matin)s'%vars())
        cnx.commit()
        invalidateAbsEtudDate(self, etudid, jour)
    
    def _AnnuleAbsence(self, etudid, jour, matin, moduleimpl_id=None, REQUEST=None):
        """Annule une absence ds base
        Si moduleimpl_id, n'annule que pour ce module
        """
        # unpublished
        matin = _toboolean(matin)
        cnx = self.GetDBConnexion()
        cursor = cnx.cursor(cursor_factory=ScoDocCursor)
        req = 'delete from absences where jour=%(jour)s and matin=%(matin)s and etudid=%(etudid)s and estabs'
        if moduleimpl_id:
            req += ' and moduleimpl_id=%(moduleimpl_id)s'
        cursor.execute(req, vars())
        logdb(REQUEST, cnx, 'AnnuleAbsence', etudid=etudid,
              msg='JOUR=%(jour)s,MATIN=%(matin)s,moduleimpl_id=%(moduleimpl_id)s'%vars())
        cnx.commit()
        invalidateAbsEtudDate(self, etudid, jour)
    
    def _AnnuleJustif(self, etudid, jour, matin, REQUEST=None):
        "Annule un justificatif"
        # unpublished
        matin = _toboolean(matin)
        cnx = self.GetDBConnexion()
        cursor = cnx.cursor(cursor_factory=ScoDocCursor)
        cursor.execute('delete from absences where jour=%(jour)s and matin=%(matin)s and etudid=%(etudid)s and ESTJUST AND NOT ESTABS', vars() )
        cursor.execute('update absences set estjust=false where jour=%(jour)s and matin=%(matin)s and etudid=%(etudid)s', vars() )
        logdb(REQUEST, cnx, 'AnnuleJustif', etudid=etudid,
              msg='JOUR=%(jour)s,MATIN=%(matin)s'%vars())
        cnx.commit()
        invalidateAbsEtudDate(self, etudid, jour)
    
    # Fonction inutile à supprimer (gestion moduleimpl_id incorrecte):
    # def _AnnuleAbsencesPeriodNoJust(self, etudid, datedebut, datefin,
    #                                 moduleimpl_id=None, REQUEST=None):
    #     """Supprime les absences entre ces dates (incluses).
    #     mais ne supprime pas les justificatifs.
    #     """
    #     # unpublished
    #     cnx = self.GetDBConnexion()
    #     cursor = cnx.cursor(cursor_factory=ScoDocCursor)
    #     # supr les absences non justifiees
    #     cursor.execute("delete from absences where etudid=%(etudid)s and (not estjust) and moduleimpl_id=(moduleimpl_id)s and jour BETWEEN %(datedebut)s AND %(datefin)s",
    #                    vars() )
    #     # s'assure que les justificatifs ne sont pas "absents"
    #     cursor.execute("update absences set estabs=FALSE where  etudid=%(etudid)s and jour and moduleimpl_id=(moduleimpl_id)s  BETWEEN %(datedebut)s AND %(datefin)s", vars())
    #     logdb(REQUEST, cnx, 'AnnuleAbsencesPeriodNoJust', etudid=etudid,
    #           msg='%(datedebut)s - %(datefin)s - (moduleimpl_id)s'%vars())
    #     cnx.commit()
    #     invalidateAbsEtudDate(self, etudid, datedebut)
    #     invalidateAbsEtudDate(self, etudid, datefin) # si un semestre commence apres datedebut et termine avant datefin, il ne sera pas invalide. Tant pis ;-)

    security.declareProtected(ScoAbsChange, 'AnnuleAbsencesDatesNoJust')
    def AnnuleAbsencesDatesNoJust(self, etudid, dates, moduleimpl_id=None, REQUEST=None):
        """Supprime les absences aux dates indiquées
        mais ne supprime pas les justificatifs.
        """
        #log('AnnuleAbsencesDatesNoJust: moduleimpl_id=%s' % moduleimpl_id)
        if not dates:
            return
        date0 = dates[0]
        if len(date0.split(':')) == 2:
            # am/pm is present
            for date in dates:
                jour, ampm = date.split(':')
                if ampm == 'am':
                    matin=1
                elif ampm=='pm':
                    matin=0
                else:
                    raise ValueError, 'invalid ampm !'
                self._AnnuleAbsence(etudid, jour, matin, moduleimpl_id, REQUEST)
            return
        cnx = self.GetDBConnexion()
        cursor = cnx.cursor(cursor_factory=ScoDocCursor)
        # supr les absences non justifiees
        for date in dates:
            cursor.execute(
                "delete from absences where etudid=%(etudid)s and (not estjust) and jour=%(date)s and moduleimpl_id=%(moduleimpl_id)s",
                vars() )
            invalidateAbsEtudDate(self, etudid, date)
        # s'assure que les justificatifs ne sont pas "absents"
        for date in dates:
            cursor.execute(
                "update absences set estabs=FALSE where  etudid=%(etudid)s and jour=%(date)s and moduleimpl_id=%(moduleimpl_id)s",
                vars())
        if dates:
            date0 = dates[0]
        else:
            date0 = None
        if len(dates) > 1:
            date1 = dates[1]
        else:
            date1 = None
        logdb(REQUEST, cnx, 'AnnuleAbsencesDatesNoJust', etudid=etudid,
              msg='%s - %s - %s' % (date0,date1,moduleimpl_id) )
        cnx.commit()

    security.declareProtected(ScoView, 'CountAbs')
    def CountAbs(self, etudid, debut, fin, matin=None, moduleimpl_id=None):
        "CountAbs"
        if matin != None:
            matin = _toboolean(matin)
            ismatin = ' AND A.MATIN = %(matin)s '
        else:
            ismatin = ''
        if moduleimpl_id:
            modul = ' AND A.MODULEIMPL_ID = %(moduleimpl_id)s '
        else:
            modul = ''
        cnx = self.GetDBConnexion()
        cursor = cnx.cursor(cursor_factory=ScoDocCursor)
        cursor.execute("""SELECT COUNT(*) AS NbAbs FROM (
    SELECT DISTINCT A.JOUR, A.MATIN
    FROM ABSENCES A
    WHERE A.ETUDID = %(etudid)s
      AND A.ESTABS""" + ismatin + modul + """
      AND A.JOUR BETWEEN %(debut)s AND %(fin)s
          ) AS tmp
          """, vars())
        res = cursor.fetchone()[0]
        return res

    security.declareProtected(ScoView, 'CountAbsJust')
    def CountAbsJust(self, etudid, debut, fin, matin=None, moduleimpl_id=None):
        if matin != None:
            matin = _toboolean(matin)
            ismatin = ' AND A.MATIN = %(matin)s '
        else:
            ismatin = ''
        if moduleimpl_id:
            modul = ' AND A.MODULEIMPL_ID = %(moduleimpl_id)s '
        else:
            modul = ''
        cnx = self.GetDBConnexion()
        cursor = cnx.cursor(cursor_factory=ScoDocCursor)
        cursor.execute("""SELECT COUNT(*) AS NbAbsJust FROM (
  SELECT DISTINCT A.JOUR, A.MATIN
  FROM ABSENCES A, ABSENCES B
  WHERE A.ETUDID = %(etudid)s
      AND A.ETUDID = B.ETUDID 
      AND A.JOUR = B.JOUR AND A.MATIN = B.MATIN
      AND A.JOUR BETWEEN %(debut)s AND %(fin)s
      AND A.ESTABS AND (A.ESTJUST OR B.ESTJUST)""" + ismatin + modul + """
) AS tmp
        """, vars() )
        res = cursor.fetchone()[0]
        return res


    def _ListeAbsDate(self, etudid, beg_date, end_date):
        # Liste des absences et justifs entre deux dates
        cnx = self.GetDBConnexion()
        cursor = cnx.cursor(cursor_factory=ScoDocCursor)
        cursor.execute("""SELECT jour, matin, estabs, estjust, description FROM ABSENCES A 
     WHERE A.ETUDID = %(etudid)s
     AND A.jour >= %(beg_date)s 
     AND A.jour <= %(end_date)s 
         """, vars() )
        Abs = cursor.dictfetchall()
        # log('ListeAbsDate: abs=%s' % Abs)
        # remove duplicates        
        A = {} # { (jour, matin) : abs }
        for a in Abs:
            jour, matin = a['jour'], a['matin']
            if (jour, matin) in A:
                # garde toujours la description
                a['description'] = a['description'] or A[(jour, matin)]['description']
                # et la justif:
                a['estjust'] = a['estjust'] or A[(jour, matin)]['estjust']
                a['estabs'] = a['estabs'] or A[(jour, matin)]['estabs']
                A[(jour, matin)] = a
            else:
                A[(jour, matin)] = a
            if A[(jour, matin)]['description'] is None:
                A[(jour, matin)]['description'] = ''
            # add hours: matin = 8:00 - 12:00, apresmidi = 12:00 - 18:00
            dat = '%04d-%02d-%02d' % (a['jour'].year,a['jour'].month,a['jour'].day)
            if a['matin']:
                A[(jour, matin)]['begin'] = dat + ' 08:00:00'
                A[(jour, matin)]['end'] = dat + ' 11:59:59'
            else:
                A[(jour, matin)]['begin'] = dat + ' 12:00:00'
                A[(jour, matin)]['end'] = dat + ' 17:59:59'
        # sort
        R = A.values()
        R.sort( key=lambda x: (x['begin']) )
        # log('R=%s' % R)
        return R
    
    security.declareProtected(ScoView, 'ListeAbsJust')
    def ListeAbsJust(self, etudid, datedebut):
        "Liste des absences justifiees (par ordre chronologique)"
        cnx = self.GetDBConnexion()
        cursor = cnx.cursor(cursor_factory=ScoDocCursor)
        cursor.execute("""SELECT DISTINCT A.ETUDID, A.JOUR, A.MATIN FROM ABSENCES A, ABSENCES B
 WHERE A.ETUDID = %(etudid)s
 AND A.ETUDID = B.ETUDID 
 AND A.JOUR = B.JOUR AND A.MATIN = B.MATIN AND A.JOUR >= %(datedebut)s
 AND A.ESTABS AND (A.ESTJUST OR B.ESTJUST)
 ORDER BY A.JOUR
        """, vars() )
        A = cursor.dictfetchall()
        for a in A:
            a['description'] = self._GetAbsDescription(a, cursor=cursor)
        return A

    security.declareProtected(ScoView, 'ListeAbsNonJust')
    def ListeAbsNonJust(self, etudid, datedebut):
        "Liste des absences NON justifiees (par ordre chronologique)"
        cnx = self.GetDBConnexion()
        cursor = cnx.cursor(cursor_factory=ScoDocCursor)
        cursor.execute("""SELECT ETUDID, JOUR, MATIN FROM ABSENCES A 
    WHERE A.ETUDID = %(etudid)s
    AND A.estabs 
    AND A.jour >= %(datedebut)s
    EXCEPT SELECT ETUDID, JOUR, MATIN FROM ABSENCES B 
    WHERE B.estjust 
    AND B.ETUDID = %(etudid)s
    ORDER BY JOUR
        """, vars() )
        A = cursor.dictfetchall()
        for a in A:
            a['description'] = self._GetAbsDescription(a, cursor=cursor)
        return A
    
    security.declareProtected(ScoView, 'ListeAbsJust')
    def ListeJustifs(self, etudid, datedebut, datefin=None, only_no_abs=False):
        """Liste des justificatifs (sans absence relevée) à partir d'une date,
        ou, si datefin spécifié, entre deux dates.
        Si only_no_abs: seulement les justificatifs correspondant aux jours sans absences relevées.
        """
        cnx = self.GetDBConnexion()
        cursor = cnx.cursor(cursor_factory=ScoDocCursor)
        req = """SELECT DISTINCT ETUDID, JOUR, MATIN FROM ABSENCES A
 WHERE A.ETUDID = %(etudid)s
 AND A.ESTJUST
 AND A.JOUR >= %(datedebut)s"""
        if datefin:
            req += """AND A.JOUR <= %(datefin)s"""
        if only_no_abs:
                req += """
 EXCEPT SELECT ETUDID, JOUR, MATIN FROM ABSENCES B 
 WHERE B.estabs
 AND B.ETUDID = %(etudid)s
        """
        cursor.execute(req, vars() )
        A = cursor.dictfetchall()
        for a in A:
            a['description'] = self._GetAbsDescription(a, cursor=cursor)
        
        return A
    
    def _GetAbsDescription(self, a, cursor=None):
        "Description associee a l'absence"
        if not cursor:
            cnx = self.GetDBConnexion()
            cursor = cnx.cursor(cursor_factory=ScoDocCursor)
        a = a.copy()
        # a['jour'] = a['jour'].date()
        if a['matin']: # devrait etre booleen... :-(
            a['matin'] = True
        else:
            a['matin'] = False
        cursor.execute("""select * from absences where etudid=%(etudid)s and jour=%(jour)s and matin=%(matin)s order by entry_date desc""", a)
        A = cursor.dictfetchall()
        desc = None
        module = ''
        for a in A:
            if a['description']:
                desc = a['description']
            if a['moduleimpl_id'] and a['moduleimpl_id'] != 'NULL':
                # Trouver le nom du module
                Mlist = self.Notes.do_moduleimpl_withmodule_list(args={'moduleimpl_id': a['moduleimpl_id']})
                if Mlist:
                    M = Mlist[0]
                    module += '%s ' % M['module']['code']

        if desc:
            return '(%s) %s' % (desc, module)
            return desc
        if module:
            return module
        return ''

    security.declareProtected(ScoView, 'ListeAbsJour')
    def ListeAbsJour(self, date, am=True, pm=True, is_abs=True, is_just=None):
        """Liste des absences et/ou justificatifs ce jour.
        is_abs: None (peu importe), True, False
        is_just: idem
        """
        cnx = self.GetDBConnexion()
        cursor = cnx.cursor(cursor_factory=ScoDocCursor)
        req = """SELECT DISTINCT etudid, jour, matin FROM ABSENCES A 
    WHERE A.jour = %(date)s
    """
        if is_abs != None:
            req += " AND A.estabs = %(is_abs)s"
        if is_just != None:
            req += " AND A.estjust = %(is_just)s"
        if not am:
            req += " AND NOT matin "
        if not pm:
            req += " AND matin"
        
        cursor.execute(req, { 'date' : date, 'is_just' : is_just, 'is_abs' : is_abs } )
        A = cursor.dictfetchall()
        for a in A:
            a['description'] = self._GetAbsDescription(a, cursor=cursor)
        return A

    security.declareProtected(ScoView, 'ListeAbsNonJustJour')
    def ListeAbsNonJustJour(self, date, am=True, pm=True):
        "Liste des absences non justifiees ce jour"
        cnx = self.GetDBConnexion()
        cursor = cnx.cursor(cursor_factory=ScoDocCursor)
        reqa = ''
        if not am:
            reqa += " AND NOT matin "
        if not pm:
            reqa += " AND matin "
        req = """SELECT  etudid, jour, matin FROM ABSENCES A 
    WHERE A.estabs 
    AND A.jour = %(date)s
    """ + reqa + """EXCEPT SELECT etudid, jour, matin FROM ABSENCES B 
    WHERE B.estjust AND B.jour = %(date)s""" + reqa        
        
        cursor.execute(req, { 'date' : date } )
        A = cursor.dictfetchall()
        for a in A:
            a['description'] = self._GetAbsDescription(a, cursor=cursor)
        return A
    
    security.declareProtected(ScoAbsChange, 'doSignaleAbsenceGrSemestre')
    def doSignaleAbsenceGrSemestre(self, moduleimpl_id=None, abslist=[],
                                   dates='', etudids='',
                                   destination=None, REQUEST=None):
        """Enregistre absences aux dates indiquees (abslist et dates).
        dates est une liste de dates ISO (séparées par des ',').
        Efface les absences aux dates indiquées par dates,
        ou bien ajoute celles de abslist.
        """
        if etudids:
            etudids = etudids.split(',')
        else:
            etudids = []
        if dates:
            dates = dates.split(',')
        else:
            dates = []
        
        # 1- Efface les absences
        if dates:
            for etudid in etudids:
                self.AnnuleAbsencesDatesNoJust(etudid, dates, moduleimpl_id, REQUEST) 
            return "Absences effacées"
        
        # 2- Ajoute les absences
        if abslist:
            self._add_abslist(abslist, REQUEST, moduleimpl_id)
            return "Absences ajoutées"
        
        return ''

    def _add_abslist(self, abslist, REQUEST, moduleimpl_id=None):
        for a in abslist:
            etudid, jour, ampm = a.split(':')
            if ampm == 'am':
                matin=1
            elif ampm=='pm':
                matin=0
            else:
                raise ValueError, 'invalid ampm !'
             # ajoute abs si pas deja absent
            if self.CountAbs( etudid, jour, jour, matin,moduleimpl_id) == 0:                
                self._AddAbsence( etudid, jour, matin, 0, REQUEST, '', moduleimpl_id)
        
    #
    security.declareProtected(ScoView, 'CalSelectWeek')
    def CalSelectWeek(self, year=None, REQUEST=None):
        "display calendar allowing week selection"
        if not year:
            year = self.AnneeScolaire(REQUEST)
        sems = self.Notes.do_formsemestre_list()
        if not sems:
            js = ''
        else:
            js = 'onmouseover="highlightweek(this);" onmouseout="deselectweeks();" onclick="wclick(this);"'
        C = YearTable(self, int(year), dayattributes=js)
        return C


    # --- Misc tools.... ------------------

    def _isFarFutur(self, jour):
        # check si jour est dans le futur "lointain"
        # pour autoriser les saisies dans le futur mais pas a plus de 6 mois
        y,m,d = [int(x) for x in jour.split('-')]
        j = datetime.date(y,m,d)
        # 6 mois ~ 182 jours:
        return j - datetime.date.today() > datetime.timedelta(182) 
            
        
    security.declareProtected(ScoView, 'is_work_saturday')
    def is_work_saturday(self):
        "Vrai si le samedi est travaillé"
        return int(self.get_preference('work_saturday'))
    
    def day_names(self):
        """Returns week day names.
        If work_saturday property is set, include saturday
        """
        if self.is_work_saturday():
            return ['Lundi', 'Mardi', 'Mercredi', 'Jeudi', 'Vendredi', 'Samedi']
        else:
            return ['Lundi', 'Mardi', 'Mercredi', 'Jeudi', 'Vendredi']
    
    security.declareProtected(ScoView, 'ListMondays')
    def ListMondays(self, year=None, REQUEST=None):
        """return list of mondays (ISO dates), from september to june
        """
        if not year:
            year = self.AnneeScolaire(REQUEST)
        d = ddmmyyyy( '1/9/%d' % year, work_saturday=self.is_work_saturday() )
        while d.weekday != 0:
            d = d.next()
        end = ddmmyyyy('1/7/%d' % (year+1), work_saturday=self.is_work_saturday())
        L = [ d ]
        while d < end:
            d = d.next(days=7)
            L.append(d)
        return map( lambda x: x.ISO(), L )

    security.declareProtected(ScoView, 'NextISODay')
    def NextISODay(self, date ):
        "return date after date"
        d = ddmmyyyy(date, fmt='iso', work_saturday=self.is_work_saturday())
        return d.next().ISO()

    security.declareProtected(ScoView, 'DateRangeISO')
    def DateRangeISO(self, date_beg, date_end, workable=1 ):
        """returns list of dates in [date_beg,date_end]
        workable = 1 => keeps only workable days"""
        if not date_beg:
            raise ScoValueError("pas de date spécifiée !")
        if not date_end:
            date_end = date_beg
        r = []
        cur = ddmmyyyy( date_beg, work_saturday=self.is_work_saturday() )
        end = ddmmyyyy( date_end, work_saturday=self.is_work_saturday() )
        while cur <= end:
            if (not workable) or cur.iswork():
                r.append(cur)
            cur = cur.next()
        
        return map( lambda x: x.ISO(), r )

    # ------------ HTML Interfaces
    security.declareProtected(ScoAbsChange, 'SignaleAbsenceGrHebdo')
    def SignaleAbsenceGrHebdo(self, datelundi, 
                              group_ids=[],
                              destination='',
                              moduleimpl_id=None, 
                              REQUEST=None):
        "Saisie hebdomadaire des absences"
        if not moduleimpl_id:
            moduleimp_id = None
        
        groups_infos = sco_groups_view.DisplayedGroupsInfos(self, group_ids, REQUEST=REQUEST)
        if not groups_infos.members:
            return self.sco_header(page_title='Saisie des absences',REQUEST=REQUEST) + '<h3>Aucun étudiant !</h3>' + self.sco_footer(REQUEST)
        
        base_url='SignaleAbsenceGrHebdo?datelundi=%s&amp;%s&amp;destination=%s' % (datelundi, groups_infos.groups_query_args, urllib.quote(destination))
        
        formsemestre_id = groups_infos.formsemestre_id
        etuds = [ self.getEtudInfo(etudid=m['etudid'],filled=True)[0] for m in groups_infos.members ]
        nt = self.Notes._getNotesCache().get_NotesTable(self.Notes, formsemestre_id)
        sem = self.Notes.do_formsemestre_list({'formsemestre_id':formsemestre_id})[0]
        
        # calcule dates jours de cette semaine
        datessem = [ DateDMYtoISO(datelundi) ]
        for jour in self.day_names()[1:]:
            datessem.append( self.NextISODay(datessem[-1]) )

        #                
        if groups_infos.tous_les_etuds_du_sem:
            gr_tit = 'en'
        else:
            if len(groups_infos.group_ids) > 1:
                p = 'des groupes'
            else:
                p = 'du groupe'
            gr_tit = p + '<span class="fontred">' + groups_infos.groups_titles + '</span>'
        
        H = [ self.sco_header(page_title='Saisie hebdomadaire des absences',
                              init_jquery_ui=True,
                              init_qtip=True,
                              javascripts=[
                                  'js/etud_info.js',
                                  'js/abs_ajax.js'
                                  ],
                              no_side_bar=1, REQUEST=REQUEST),
              """<table border="0" cellspacing="16"><tr><td>
              <h2>Saisie des absences %s %s, 
              <span class="fontred">semaine du lundi %s</span></h2>

              <p><a href="index_html">Annuler</a></p>

              <p>
              <form action="doSignaleAbsenceGrHebdo" method="post" action="%s">              
              """ % (gr_tit, sem['titre_num'], datelundi, REQUEST.URL0) ]
        #
        modimpls_list = []
        # Initialize with first student
        ues = nt.get_ues(etudid=etuds[0]['etudid'])
        for ue in ues:
            modimpls_list += nt.get_modimpls(ue_id=ue['ue_id'])

        # Add modules other students are subscribed to
        for etud in etuds[1:]:
            modimpls_etud = []
            ues = nt.get_ues(etudid=etud['etudid'])
            for ue in ues:
                modimpls_etud += nt.get_modimpls(ue_id=ue['ue_id'])
            modimpls_list += [m for m in modimpls_etud if m not in modimpls_list]

        menu_module = ''
        for modimpl in modimpls_list:
            if modimpl['moduleimpl_id'] == moduleimpl_id:
                sel = 'selected'
            else:
                sel = ''
            menu_module += """<option value="%(modimpl_id)s" %(sel)s>%(modname)s</option>\n""" % {
                'modimpl_id': modimpl['moduleimpl_id'],
                'modname': modimpl['module']['code'] + ' ' + (modimpl['module']['abbrev'] or modimpl['module']['titre']),
                'sel' : sel
                }
        if moduleimpl_id:
            sel = ''
        else:
            sel = 'selected' # aucun module specifie
        
        H.append("""
 Module concerné par ces absences (optionnel): <select id="moduleimpl_id" name="moduleimpl_id" onchange="document.location='%(url)s&amp;moduleimpl_id='+document.getElementById('moduleimpl_id').value">
    <option value="" %(sel)s>non spécifié</option>
    %(menu_module)s
    </select>
    </p>""" % {'menu_module': menu_module, 'url' : base_url, 'sel':sel })
        
        H += self._gen_form_saisie_groupe(etuds, self.day_names(), datessem, destination, None, moduleimpl_id)
        
        H.append(self.sco_footer(REQUEST))
        return '\n'.join(H)

    security.declareProtected(ScoAbsChange, 'SignaleAbsenceGrSemestre')
    def SignaleAbsenceGrSemestre(self, datedebut, datefin, 
                                 destination='',
                                 group_ids=[], # list of groups to display
                                 nbweeks=4, # ne montre que les nbweeks dernieres semaines
                                 moduleimpl_id=None,
                                 REQUEST=None):
        """Saisie des absences sur une journée sur un semestre (ou intervalle de dates) entier
        """
        #log('SignaleAbsenceGrSemestre: moduleimpl_id=%s destination=%s' % (moduleimpl_id, destination))
        groups_infos = sco_groups_view.DisplayedGroupsInfos(self, group_ids, REQUEST=REQUEST)
        if not groups_infos.members:
            return self.sco_header(page_title='Saisie des absences',REQUEST=REQUEST) + '<h3>Aucun étudiant !</h3>' + self.sco_footer(REQUEST)

        
        formsemestre_id = groups_infos.formsemestre_id
        etuds = [ self.getEtudInfo(etudid=m['etudid'],filled=True)[0] for m in groups_infos.members ]
                
        if not moduleimpl_id:
            moduleimp_id = None
        base_url_noweeks='SignaleAbsenceGrSemestre?datedebut=%s&amp;datefin=%s&amp;%s&amp;destination=%s' % (datedebut, datefin, groups_infos.groups_query_args, urllib.quote(destination))
        base_url = base_url_noweeks + '&amp;nbweeks=%s'%nbweeks # sans le moduleimpl_id

        if etuds: 
            nt = self.Notes._getNotesCache().get_NotesTable(self.Notes, formsemestre_id)
            sem = self.Notes.do_formsemestre_list({'formsemestre_id':formsemestre_id})[0]

        jourdebut = ddmmyyyy(datedebut, work_saturday=self.is_work_saturday())
        jourfin = ddmmyyyy(datefin, work_saturday=self.is_work_saturday())
        today = ddmmyyyy(time.strftime('%d/%m/%Y', time.localtime()), work_saturday=self.is_work_saturday())
        today.next()
        if jourfin > today: # ne propose jamais les semaines dans le futur
            jourfin = today
        if jourdebut > today:
            raise ScoValueError('date de début dans le futur (%s) !' % jourdebut)
        #
        if not jourdebut.iswork() or jourdebut > jourfin:
            raise ValueError('date debut invalide (%s, ouvrable=%d)' % (str(jourdebut), jourdebut.iswork()) )
        # calcule dates
        dates = [] # ddmmyyyy instances
        d = ddmmyyyy(datedebut, work_saturday=self.is_work_saturday())
        while d <= jourfin:
            dates.append(d)
            d = d.next(7) # avance d'une semaine
        #
        msg = 'Montrer seulement les 4 dernières semaines'
        nwl = 4
        if nbweeks:
            nbweeks = int(nbweeks)
            if nbweeks > 0:
                dates = dates[-nbweeks:]
                msg = 'Montrer toutes les semaines'
                nwl = 0
        url_link_semaines = base_url_noweeks + '&amp;nbweeks=%s'%nwl
        if moduleimpl_id:
            url_link_semaines += '&amp;moduleimpl_id=' + moduleimpl_id
        #
        colnames = [ str(x) for x in dates ]
        dates = [ x.ISO() for x in dates ]
        dayname = self.day_names()[jourdebut.weekday]

        if groups_infos.tous_les_etuds_du_sem:
            gr_tit = 'en'
        else:
            if len(groups_infos.group_ids) > 1:
                p = 'des groupes'
            else:
                p = 'du groupe'
            gr_tit = p + '<span class="fontred">' + groups_infos.groups_titles + '</span>'
            
        
        H = [ self.sco_header(page_title='Saisie des absences',
                              init_jquery_ui=True,
                              init_qtip = True,
                              javascripts=[
                                  'js/etud_info.js',
                                  'js/abs_ajax.js'
                                  ],
                              no_side_bar=1, REQUEST=REQUEST),
              """<table border="0" cellspacing="16"><tr><td>
              <h2>Saisie des absences %s %s, 
              les <span class="fontred">%s</span></h2>
              <p>
              <a href="%s">%s</a>
              <form action="doSignaleAbsenceGrSemestre" method="post">              
              """ % (gr_tit, sem['titre_num'], dayname, url_link_semaines, msg) ]
        #
        if etuds:
            modimpls_list = []
            # Initialize with first student
            ues = nt.get_ues(etudid=etuds[0]['etudid'])
            for ue in ues:
                modimpls_list += nt.get_modimpls(ue_id=ue['ue_id'])

            # Add modules other students are subscribed to
            for etud in etuds[1:]:
                modimpls_etud = []
                ues = nt.get_ues(etudid=etud['etudid'])
                for ue in ues:
                    modimpls_etud += nt.get_modimpls(ue_id=ue['ue_id'])
                modimpls_list += [m for m in modimpls_etud if m not in modimpls_list]

            menu_module = ''
            for modimpl in modimpls_list:
                if modimpl['moduleimpl_id'] == moduleimpl_id:
                    sel = 'selected'
                else:
                    sel = ''
                menu_module += """<option value="%(modimpl_id)s" %(sel)s>%(modname)s</option>\n""" % {
                    'modimpl_id': modimpl['moduleimpl_id'],
                    'modname': modimpl['module']['code'] + ' ' + (modimpl['module']['abbrev'] or modimpl['module']['titre']),
                    'sel' : sel
                    }
            if moduleimpl_id:
                sel = ''
            else:
                sel = 'selected' # aucun module specifie
            H.append("""<p>
    Module concerné par ces absences (optionnel): <select id="moduleimpl_id" name="moduleimpl_id" onchange="document.location='%(url)s&amp;moduleimpl_id='+document.getElementById('moduleimpl_id').value">
    <option value="" %(sel)s>non spécifié</option>
    %(menu_module)s
    </select>
</p>""" % {'menu_module': menu_module, 'url' : base_url, 'sel':sel })
        
        H += self._gen_form_saisie_groupe(etuds, colnames, dates, destination, dayname, moduleimpl_id)
        H.append(self.sco_footer(REQUEST))
        return '\n'.join(H)
    
    def _gen_form_saisie_groupe(self, etuds, colnames, dates, destination='', dayname='',moduleimpl_id=None):
        H = [ """
        <script type="text/javascript">
        function colorize(obj) {
             if (obj.checked) {
                 obj.parentNode.className = 'absent';
             } else {
                 obj.parentNode.className = 'present';
             }
        }
        function on_toggled(obj, etudid, dat) {
            colorize(obj);
            if (obj.checked) {
                ajaxFunction('add', etudid, dat);
            } else {
                ajaxFunction('remove', etudid, dat);
            }
        }
        </script>
        <div id="AjaxDiv"></div>
        <br/>
        <table rules="cols" frame="box" class="abs_form_table">
        <tr><td>&nbsp;</td>
        """]
        # Titres colonnes
        if dayname:
            for jour in colnames:
                H.append('<th colspan="2" width="100px" style="padding-left: 5px; padding-right: 5px;">' + dayname + '</th>')                
            H.append('</tr><tr><td>&nbsp;</td>')
        
        for jour in colnames:
            H.append('<th colspan="2" width="100px" style="padding-left: 5px; padding-right: 5px;">' + jour + '</th>')

        H.append('</tr><tr><td>&nbsp;</td>')
        H.append('<th>AM</th><th>PM</th>' * len(colnames) )
        H.append('</tr>')
        #
        if not etuds:
            H.append('<tr><td><span class="redboldtext">Aucun étudiant inscrit !</span></td></tr>')
        i=1        
        for etud in etuds:
            i += 1
            etudid = etud['etudid']
            # UE capitalisee dans semestre courant ?
            cap = []
            if etud['cursem']:
                nt = self.Notes._getNotesCache().get_NotesTable(self.Notes, etud['cursem']['formsemestre_id']) #> get_ues, get_etud_ue_status
                for ue in nt.get_ues():
                    status = nt.get_etud_ue_status(etudid, ue['ue_id'])
                    if status['is_capitalized']:
                        cap.append(ue['acronyme'])
            if cap:
                capstr = ' <span class="capstr">(%s cap.)</span>' % ', '.join(cap)
            else:
                capstr = ''
            
            tr_class = ('row_1', 'row_2', 'row_3')[i%3]
            td_matin_class = ('matin_1', 'matin_2', 'matin_3')[i%3]
            
            H.append('<tr class="%s"><td><b class="etudinfo" id="%s"><a class="discretelink" href="ficheEtud?etudid=%s" target="new">%s</a></b>%s</td>'
                     % (tr_class, etudid, etudid, etud['nomprenom'], capstr))
            for date in dates:
                # matin
                if self.CountAbs( etudid, date, date, True, moduleimpl_id=moduleimpl_id):
                    checked = 'checked'
                else:
                    checked = ''
                H.append('<td class="%s"><input type="checkbox" name="abslist:list" value="%s" %s onclick="on_toggled(this, \'%s\', \'%s\')"/></td>'
                         % (td_matin_class, etudid+':'+date+':'+'am', checked, etudid, date+':am'))
                # apres midi
                if self.CountAbs( etudid, date, date, False, moduleimpl_id=moduleimpl_id):
                    checked = 'checked'
                else:
                    checked = ''
                H.append('<td><input type="checkbox" name="abslist:list" value="%s" %s onclick="on_toggled(this, \'%s\', \'%s\')"/></td>'
                         % (etudid+':'+date+':'+'pm', checked, etudid, date+':pm'))
            H.append('</tr>')
        H.append('</table>')
        # place la liste des etudiants et les dates pour pouvoir effacer les absences
        H.append('<input type="hidden" name="etudids" value="%s"/>'
                 % ','.join( [ etud['etudid'] for etud in etuds ] ) )
        H.append('<input type="hidden" name="datedebut" value="%s"/>' % dates[0] )
        H.append('<input type="hidden" name="datefin" value="%s"/>' % dates[-1] )
        H.append('<input type="hidden" name="dates" value="%s"/>'
                 % ','.join(dates) )
        H.append('<input type="hidden" name="destination" value="%s"/>'
                 % urllib.quote(destination) )
        #
        # version pour formulaire avec AJAX (Yann LB)
        H.append("""
            <p><input type="button" value="Retour" onClick="window.location='%s'"/>
            </p>
            </form>
            </p>
            </td></tr></table>
            <p class="help">Les cases cochées correspondent à des absences.
            Les absences saisies ne sont pas justifiées (sauf si un justificatif a été entré
            par ailleurs).
            </p><p class="help">Si vous "décochez" une case,  l'absence correspondante sera supprimée.
            Attention, les modifications sont automatiquement entregistrées au fur et à mesure.
            </p>
        """ % destination)
        return H
        
    def _TablesAbsEtud(self, etudid, datedebut,
                       with_evals=True,
                       format='html',
                       absjust_only=0,
                       REQUEST=None):
        """Tables des absences justifiees et non justifiees d'un étudiant sur l'année en cours
        """
        absjust = self.ListeAbsJust( etudid=etudid, datedebut=datedebut)
        absnonjust = self.ListeAbsNonJust(etudid=etudid, datedebut=datedebut)
        # examens ces jours là ?
        if with_evals:
            cnx = self.GetDBConnexion()
            cursor = cnx.cursor(cursor_factory=ScoDocCursor)
            for a in absnonjust + absjust:
                cursor.execute(
                    """select eval.*
                from notes_evaluation eval, notes_moduleimpl_inscription mi, notes_moduleimpl m
                where eval.jour = %(jour)s and eval.moduleimpl_id = m.moduleimpl_id
                and mi.moduleimpl_id = m.moduleimpl_id and mi.etudid = %(etudid)s""",
                    { 'jour' : a['jour'].strftime('%Y-%m-%d'), 'etudid' : etudid } )
                a['evals'] = cursor.dictfetchall() 
                cursor.execute(
                    """SELECT mi.moduleimpl_id
                from  absences abs, notes_moduleimpl_inscription mi, notes_moduleimpl m
                where abs.matin = %(matin)s and abs.jour = %(jour)s and abs.etudid=%(etudid)s and abs.moduleimpl_id=mi.moduleimpl_id and mi.moduleimpl_id=m.moduleimpl_id 
                and mi.etudid = %(etudid)s""",
                { 'matin': bool(a['matin']),
                 'jour': a['jour'].strftime('%Y-%m-%d'),
                 'etudid' : etudid }
                    )
                a['absent'] = cursor.dictfetchall()
        
        def matin(x):
            if x:
                return 'matin'
            else:
                return 'après midi'

        def descr_exams(a):
            if not a.has_key('evals'):
                return ''
            ex = []
            for ev in a['evals']:
                mod = self.Notes.do_moduleimpl_withmodule_list(args={ 'moduleimpl_id' : ev['moduleimpl_id']})[0]
                if format == 'html':
                    ex.append( '<a href="Notes/moduleimpl_status?moduleimpl_id=%s">%s</a>'
                           % (mod['moduleimpl_id'], mod['module']['code']))
                else:
                    ex.append(mod['module']['code'])
            if ex:
                return  ', '.join(ex)
            return ''

        def descr_abs(a):
            ex = []
            for ev in a.get('absent', []):
                mod = self.Notes.do_moduleimpl_withmodule_list(args={ 'moduleimpl_id' : ev['moduleimpl_id']})[0]
                if format == 'html':
                    ex.append( '<a href="Notes/moduleimpl_status?moduleimpl_id=%s">%s</a>'
                           % (mod['moduleimpl_id'], mod['module']['code']))
                else:
                    ex.append(mod['module']['code'])
            if ex:
                return  ', '.join(ex)
            return ''

        # ajoute date formatée et évaluations
        for L in (absnonjust, absjust):
            for a in L:
                if with_evals:
                    a['exams'] = descr_exams(a)
                a['datedmy'] = a['jour'].strftime('%d/%m/%Y')
                a['matin_o'] = int(a['matin'])
                a['matin'] = matin(a['matin'])
                index=a['description'].find(')')
                if index != -1:
                    a['motif'] = a['description'][1:index]
                else: 
                    a['motif']=''
                a['description'] = descr_abs(a) or ''
        
        # ajoute lien pour justifier
        if format == 'html':
            for a in absnonjust:
                a['justlink'] = '<em>justifier</em>'
                a['_justlink_target'] = 'doJustifAbsence?etudid=%s&amp;datedebut=%s&amp;datefin=%s&amp;demijournee=%s'%(etudid, a['datedmy'], a['datedmy'], a['matin_o'])
        #
        titles={'datedmy' : 'Date', 'matin' : '', 'exams' : 'Examens ce jour', 'justlink' : '', 'description' : 'Modules', 'motif': 'Motif' }
        columns_ids=['datedmy', 'matin']
        if with_evals:
            columns_ids.append('exams')
            
        columns_ids.append('description')
        columns_ids.append('motif')
        if format == 'html':
            columns_ids.append('justlink')
        
        return titles, columns_ids, absnonjust, absjust

    security.declareProtected(ScoView, 'EtatAbsencesGr') # ported from dtml
    def EtatAbsencesGr(self, group_ids=[], # list of groups to display
                       debut='', fin='', 
                       format='html', REQUEST=None): 
        """Liste les absences de groupes
        """
        datedebut = DateDMYtoISO(debut)
        datefin = DateDMYtoISO(fin)
        # Informations sur les groupes à afficher:
        groups_infos = sco_groups_view.DisplayedGroupsInfos(self, group_ids, REQUEST=REQUEST)
        formsemestre_id = groups_infos.formsemestre_id
        sem = groups_infos.formsemestre
        
        # Construit tableau (etudid, statut, nomprenom, nbJust, nbNonJust, NbTotal)
        T = []
        for m in groups_infos.members:
            etud = self.getEtudInfo(etudid=m['etudid'],filled=True)[0]
            nbabs = self.CountAbs(etudid=etud['etudid'],debut=datedebut,fin=datefin)
            nbabsjust = self.CountAbsJust(etudid=etud['etudid'],debut=datedebut,fin=datefin)
            # retrouve sem dans etud['sems']
            s = None
            for s in etud['sems']:
                if s['formsemestre_id'] == formsemestre_id:
                    break
            if not s or s['formsemestre_id'] != formsemestre_id:
                raise ValueError("EtatAbsencesGr: can't retreive sem") # bug or malicious arg
            T.append( { 'etudid' : etud['etudid'],
                        'etatincursem' : s['ins']['etat'],
                        'nomprenom' : etud['nomprenom'],
                        'nbabsjust' : nbabsjust, 'nbabsnonjust' : nbabs-nbabsjust, 'nbabs' : nbabs,
                        '_nomprenom_target' : 'CalAbs?etudid=%s' % etud['etudid'],
                        '_nomprenom_td_attrs' : 'id="%s" class="etudinfo"' % etud['etudid'],
                        } )
            if s['ins']['etat'] == 'D':
                T[-1]['_css_row_class'] = 'etuddem'
                T[-1]['nomprenom'] += ' (dem)'
        columns_ids = ['nomprenom', 'nbabsjust', 'nbabsnonjust', 'nbabs']
        if groups_infos.tous_les_etuds_du_sem:
            gr_tit = ''
        else:
            if len(groups_infos.group_ids) > 1:
                p = 'des groupes'
            else:
                p = 'du groupe'
            if format == 'html':
                h = ' <span class="fontred">' + groups_infos.groups_titles + '</span>'
            else:
                h = groups_infos.groups_titles
            gr_tit = p + h
        
        title = 'Etat des absences %s' % gr_tit
        if format == 'xls' or format == 'xml':
            columns_ids = ['etudid'] + columns_ids
        tab =GenTable( columns_ids=columns_ids, rows=T,  
                       preferences=self.get_preferences(formsemestre_id),
                       titles={'etatincursem': 'Etat', 'nomprenom':'Nom', 'nbabsjust':'Justifiées',
                               'nbabsnonjust' : 'Non justifiées', 'nbabs' : 'Total' },
                       html_sortable=True,
                       html_class='gt_table table_leftalign',
                       html_header=self.sco_header(
                           REQUEST, 
                           page_title=title, 
                           init_jquery_ui=True,
                           init_qtip = True,
                           javascripts=['js/etud_info.js']
                           ),
                       html_title=self.Notes.html_sem_header(REQUEST, '%s' % title, sem, 
                                                                with_page_header=False) 
                       +  '<p>Période du %s au %s (nombre de <b>demi-journées</b>)<br/>' % (debut, fin),
                       
                       base_url = '%s&amp;formsemestre_id=%s&amp;debut=%s&amp;fin=%s' % (groups_infos.base_url, formsemestre_id, debut, fin),
                       filename='etat_abs_'+make_filename('%s de %s'%(groups_infos.groups_filename, sem['titreannee'])),
                       caption=title,
                       html_next_section="""</table>
<p class="help">
Cliquez sur un nom pour afficher le calendrier des absences<br/>
ou entrez une date pour visualiser les absents un jour donné&nbsp;:
</p>
<div style="margin-bottom: 10px;">
<form action="EtatAbsencesDate" method="get" action="%s">
<input type="hidden" name="formsemestre_id" value="%s">
%s
<input type="text" name="date" size="10" class="datepicker"/>
<input type="submit" name="" value="visualiser les absences">
</form></div>
                        """ % (REQUEST.URL0, formsemestre_id, groups_infos.get_form_elem()))
        return tab.make_page(self, format=format, REQUEST=REQUEST)
    
    security.declareProtected(ScoView, 'EtatAbsencesDate') # ported from dtml
    def EtatAbsencesDate(self, group_ids=[], # list of groups to display
                         date=None, REQUEST=None): 
        """Etat des absences pour un groupe à une date donnée
        """
        # Informations sur les groupes à afficher:
        groups_infos = sco_groups_view.DisplayedGroupsInfos(self, group_ids, REQUEST=REQUEST)
        formsemestre_id = groups_infos.formsemestre_id
        sem = self.Notes.do_formsemestre_list({'formsemestre_id':formsemestre_id})[0]
        H = [ self.sco_header(page_title='Etat des absences',REQUEST=REQUEST) ]
        if date:
            dateiso=DateDMYtoISO(date)
            nbetud=0
            t_nbabsjustam=0
            t_nbabsam=0
            t_nbabsjustpm=0
            t_nbabspm=0
            etuds = self.getEtudInfoGroupes(groups_infos.group_ids)
            H.append( '<h2>Etat des absences le %s</h2>' % date )
            H.append( """<table border="0" cellspacing="4" cellpadding="0">
             <tr><th>&nbsp;</th>
            <th style="width: 10em;">Matin</th><th style="width: 10em;">Après-midi</th></tr>
            """)
            for etud in groups_infos.members:
                nbabsam = self.CountAbs(etudid=etud['etudid'],debut=dateiso,fin=dateiso,matin=1)
                nbabspm = self.CountAbs(etudid=etud['etudid'],debut=dateiso,fin=dateiso,matin=0)
                if (nbabsam != 0) or (nbabspm != 0):
                    nbetud += 1
                    nbabsjustam=self.CountAbsJust(etudid=etud['etudid'],debut=dateiso,fin=dateiso,matin=1)
                    nbabsjustpm=self.CountAbsJust(etudid=etud['etudid'],debut=dateiso,fin=dateiso,matin=0)
                    H.append("""<tr bgcolor="#FFFFFF"><td>
                     <a href="CalAbs?etudid=%(etudid)s"><font color="#A00000">%(nomprenom)s</font></a></td><td align="center">"""
                     % etud ) # """
                    if nbabsam != 0:
                        if nbabsjustam:
                            H.append("Just.")
                            t_nbabsjustam += 1
                        else:
                            H.append("Abs.")
                            t_nbabsam += 1
                    else:
                        H.append("")
                    H.append('</td><td align="center">')
                    if nbabspm != 0:
                        if nbabsjustpm:
                            H.append("Just.")
                            t_nbabsjustam += 1
                        else:
                            H.append("Abs.")
                            t_nbabspm += 1
                    else:
                        H.append("")
                    H.append('</td></tr>')
            H.append("""<tr bgcolor="#FFFFFF"><td></td><td>%d abs, %d just.</td><td>%d abs, %d just.</td></tr>"""
                     % (t_nbabsam, t_nbabsjustam, t_nbabspm, t_nbabsjustpm))
            H.append('</table>')
            if nbetud == 0:
                H.append('<p>Aucune absence !</p>')
        else:
            H.append("""<h2>Erreur: vous n'avez pas choisi de date !</h2>
              <a class="stdlink" href="%s">Continuer</a>""" % REQUEST.HTTP_REFERER)
            
        return '\n'.join(H) + self.sco_footer(REQUEST)
    
    # ----- Gestion des "billets d'absence": signalement par les etudiants eux mêmes (à travers le portail)
    security.declareProtected(ScoAbsAddBillet, 'AddBilletAbsence')
    def AddBilletAbsence(self, begin, end, description, etudid=False, code_nip=None, code_ine=None, justified=True, REQUEST=None, xml_reply=True ):
        """Memorise un "billet"
        begin et end sont au format ISO (eg "1999-01-08 04:05:06")
        """
        t0 = time.time()
        # check etudid
        etuds = self.getEtudInfo(etudid=etudid, code_nip=code_nip, REQUEST=REQUEST,filled=True)        
        if not etuds:
            return self.log_unknown_etud(REQUEST=REQUEST)
        etud = etuds[0]
        # check dates
        begin_date = ParseDateTimeUTC(begin) # may raises ValueError
        end_date = ParseDateTimeUTC(end)
        if begin_date > end_date:
            raise ValueError('invalid dates')
        #
        justified = int(justified)
        #
        cnx = self.GetDBConnexion()
        billet_id = billet_absence_create( cnx, { 'etudid' : etud['etudid'], 
                                                  'abs_begin' : begin, 'abs_end' : end,
                                                  'description' : description,
                                                  'etat' : 0,
                                                  'justified' : justified
                                                  } )
        if xml_reply:
            # Renvoie le nouveau billet en XML
            if REQUEST:
                REQUEST.RESPONSE.setHeader('content-type', XML_MIMETYPE)
            
            billets = billet_absence_list(cnx,  {'billet_id': billet_id } )
            tab = self._tableBillets(billets, etud=etud)
            log('AddBilletAbsence: new billet_id=%s (%gs)' % (billet_id, time.time()-t0))
            return tab.make_page(self, REQUEST=REQUEST, format='xml')
        else:
            return billet_id

    security.declareProtected(ScoAbsAddBillet, 'AddBilletAbsenceForm')
    def AddBilletAbsenceForm(self, etudid, REQUEST=None):
        """Formulaire ajout billet (pour tests seulement, le vrai formulaire accessible aux etudiants
        étant sur le portail étudiant).
        """
        etud = self.getEtudInfo(etudid=etudid, filled=1, REQUEST=REQUEST)[0]
        H = [ self.sco_header(REQUEST,page_title="Billet d'absence de %s" % etud['nomprenom'], 
                              init_jquery_ui=True) ]
        tf = TrivialFormulator(
            REQUEST.URL0, REQUEST.form, 
            (('etudid',  { 'input_type' : 'hidden' }),
             ('begin', { 'input_type' : 'date' }),
             ('end', { 'input_type' : 'date' }),
             ('justified', { 'input_type' : 'boolcheckbox', 'default': 0, 'title' : 'Justifiée' }),
             ('description', { 'input_type' : 'textarea' } )))
        if  tf[0] == 0:
            return '\n'.join(H) + tf[1] + self.sco_footer(REQUEST)
        elif tf[0] == -1:
            return REQUEST.RESPONSE.redirect( REQUEST.URL1 )
        else:
            e = tf[2]['begin'].split('/')
            begin = e[2] + '-' + e[1] + '-' + e[0] + ' 00:00:00'
            e = tf[2]['end'].split('/')
            end = e[2] + '-' + e[1] + '-' + e[0] + ' 00:00:00'
            log( self.AddBilletAbsence(begin, end, tf[2]['description'], etudid=etudid, xml_reply=True, justified=tf[2]['justified']) )
            return REQUEST.RESPONSE.redirect( 'listeBilletsEtud?etudid=' + etudid )

    def _tableBillets(self, billets, etud=None, title='' ):
        for b in billets:
            if b['abs_begin'].hour < 12:
                m = ' matin'
            else:
                m = ' après midi'
            b['abs_begin_str'] = b['abs_begin'].strftime('%d/%m/%Y') + m
            if b['abs_end'].hour < 12:
                m = ' matin'
            else:
                m = ' après midi'
            b['abs_end_str'] = b['abs_end'].strftime('%d/%m/%Y') + m
            if b['etat'] == 0:
                if b['justified'] == 0:
                    b['etat_str'] = 'à traiter'
                else:
                    b['etat_str'] = 'à justifier'
                b['_etat_str_target'] = 'ProcessBilletAbsenceForm?billet_id=%s' % b['billet_id']
                if etud:
                    b['_etat_str_target'] += '&amp;etudid=%s' % etud['etudid']
                b['_billet_id_target'] = b['_etat_str_target']
            else:
                b['etat_str'] = 'ok'
            if not etud:
                # ajoute info etudiant
                e = self.getEtudInfo(etudid=b['etudid'], filled=1)
                if not e:
                    b['nomprenom'] = '???' # should not occur
                else:
                    b['nomprenom'] = e[0]['nomprenom']
                b['_nomprenom_target'] = 'ficheEtud?etudid=%s' % b['etudid']
        if etud and not title:
            title = "Billets d'absence déclarés par %(nomprenom)s" % etud
        else:
            title = title
        columns_ids = ['billet_id']
        if not etud:
            columns_ids += [ 'nomprenom' ]
        columns_ids += ['abs_begin_str', 'abs_end_str', 'description', 'etat_str']
        
        tab = GenTable( titles= { 'billet_id' : 'Numéro', 'abs_begin_str' : 'Début', 'abs_end_str' : 'Fin', 'description' : "Raison de l'absence", 'etat_str' : 'Etat'}, 
                        columns_ids=columns_ids,
                        page_title=title, html_title='<h2>%s</h2>' % title,
                        preferences=self.get_preferences(),
                        rows = billets, html_sortable=True )
        return tab

    security.declareProtected(ScoView, 'listeBilletsEtud')
    def listeBilletsEtud(self, etudid=False, REQUEST=None, format='html'):
        """Liste billets pour un etudiant
        """
        etuds = self.getEtudInfo(etudid=etudid, filled=1, REQUEST=REQUEST)
        if not etuds:
            return self.log_unknown_etud(format=format, REQUEST=REQUEST)
        
        etud = etuds[0]
        cnx = self.GetDBConnexion()
        billets = billet_absence_list(cnx,  {'etudid': etud['etudid'] } )
        tab = self._tableBillets(billets, etud=etud)
        return tab.make_page(self, REQUEST=REQUEST, format=format)

    security.declareProtected(ScoView, 'XMLgetBilletsEtud')
    def XMLgetBilletsEtud(self, etudid=False, REQUEST=None):
        """Liste billets pour un etudiant
        """
        t0 = time.time()
        r = self.listeBilletsEtud(etudid, REQUEST=REQUEST, format='xml')
        log('XMLgetBilletsEtud (%gs)' % (time.time()-t0))
        return r

    security.declareProtected(ScoView, 'listeBillets')
    def listeBillets(self, REQUEST=None):
        """Page liste des billets non traités et formulaire recherche d'un billet"""
        cnx = self.GetDBConnexion()
        billets = billet_absence_list(cnx,  {'etat': 0 } )
        tab = self._tableBillets(billets)
        T = tab.html()
        H = [ self.sco_header(REQUEST,page_title="Billet d'absence non traités"),
              "<h2>Billets d'absence en attente de traitement (%d)</h2>" % len(billets),
              ]

        tf = TrivialFormulator(
            REQUEST.URL0, REQUEST.form, 
            (('billet_id', { 'input_type' : 'text', 'title' : 'Numéro du billet' }),),
            submitbutton=False
            )
        if  tf[0] == 0:
            return '\n'.join(H) + tf[1] + T + self.sco_footer(REQUEST)
        else:
            return REQUEST.RESPONSE.redirect( 'ProcessBilletAbsenceForm?billet_id=' + tf[2]['billet_id'] )

    security.declareProtected(ScoAbsChange, 'deleteBilletAbsence')
    def deleteBilletAbsence(self, billet_id, REQUEST=None, dialog_confirmed=False):
        """Supprime un billet.
        """
        cnx = self.GetDBConnexion()
        billets = billet_absence_list(cnx,  {'billet_id': billet_id} )
        if not billets:
            return REQUEST.RESPONSE.redirect( 'listeBillets?head_message=Billet%%20%s%%20inexistant !' % billet_id)
        if not dialog_confirmed:
            tab = self._tableBillets(billets)
            return self.confirmDialog(
                """<h2>Supprimer ce billet ?</h2>""" + tab.html(),
                dest_url="", REQUEST=REQUEST,
                cancel_url="listeBillets",
                parameters={'billet_id':billet_id})
        
        billet_absence_delete(cnx, billet_id )
        
        return REQUEST.RESPONSE.redirect( 'listeBillets?head_message=Billet%20supprimé' )

    def _ProcessBilletAbsence(self, billet, estjust, description, REQUEST):
        """Traite un billet: ajoute absence(s) et éventuellement justificatifs,
        et change l'état du billet à 1.
        NB: actuellement, les heures ne sont utilisées que pour déterminer si matin et/ou après midi.
        """
        cnx = self.GetDBConnexion()
        if billet['etat'] != 0:
            log('billet=%s' % billet)
            log('billet deja traité !')
            return -1
        n = 0 # nombre de demi-journées d'absence ajoutées
        # 1-- ajout des absences (et justifs)
        datedebut = billet['abs_begin'].strftime('%d/%m/%Y')
        datefin = billet['abs_end'].strftime('%d/%m/%Y')
        dates = self.DateRangeISO( datedebut, datefin )
        # commence apres midi ?
        if dates and billet['abs_begin'].hour > 11:
            self._AddAbsence(billet['etudid'], dates[0], 0, estjust, REQUEST, description=description)
            n += 1
            dates = dates[1:]
        # termine matin ?
        if dates and billet['abs_end'].hour < 12:
            self._AddAbsence(billet['etudid'], dates[-1], 1, estjust, REQUEST, description=description)
            n += 1
            dates = dates[:-1]
        
        for jour in dates:
            self._AddAbsence(billet['etudid'], jour, 0, estjust, REQUEST, description=description)
            self._AddAbsence(billet['etudid'], jour, 1, estjust, REQUEST, description=description)
            n += 2
        
        # 2- change etat du billet
        billet_absence_edit(cnx, { 'billet_id' : billet['billet_id'], 'etat' : 1 } )
        
        return n
    
    security.declareProtected(ScoAbsChange, 'ProcessBilletAbsenceForm')
    def ProcessBilletAbsenceForm(self, billet_id, REQUEST=None):
        """Formulaire traitement d'un billet"""
        cnx = self.GetDBConnexion()
        billets = billet_absence_list(cnx,  {'billet_id': billet_id} )
        if not billets:
            return REQUEST.RESPONSE.redirect( 'listeBillets?head_message=Billet%%20%s%%20inexistant !' % billet_id)        
        billet = billets[0]
        etudid = billet['etudid']
        etud = self.getEtudInfo(etudid=etudid, filled=1, REQUEST=REQUEST)[0]
        
        H = [ self.sco_header(REQUEST,page_title="Traitement billet d'absence de %s" % etud['nomprenom']),
              '<h2>Traitement du billet %s : <a class="discretelink" href="ficheEtud?etudid=%s">%s</a></h2>' % (billet_id, etudid, etud['nomprenom'])
              ]
        
        tf = TrivialFormulator(
            REQUEST.URL0, REQUEST.form, 
            (('billet_id',  { 'input_type' : 'hidden' }),
             ('etudid',  { 'input_type' : 'hidden' }), # pour centrer l'UI sur l'étudiant
             ('estjust', { 'input_type' : 'boolcheckbox', 'title' : 'Absences justifiées' }),
             ('description',  { 'input_type' : 'text', 'size' : 42, 'title' : 'Raison' })),
            initvalues = { 'description' : billet['description'],
                           'estjust' : billet['justified'],
                           'etudid' : etudid},
            submitlabel = 'Enregistrer ces absences')
        if tf[0] == 0:
            tab = self._tableBillets([billet], etud=etud)
            H.append(tab.html())
            if billet['justified'] == 1:
                H.append("""<p>L'étudiant pense pouvoir justifier cette absence.<br/><em>Vérifiez le justificatif avant d'enregistrer.</em></p>""")
            F = """<p><a class="stdlink" href="deleteBilletAbsence?billet_id=%s">Supprimer ce billet</a> (utiliser en cas d'erreur, par ex. billet en double)</p>""" % billet_id
            F += '<p><a class="stdlink" href="listeBillets">Liste de tous les billets en attente</a></p>' 

            return '\n'.join(H) + '<br/>' +  tf[1] + F + self.sco_footer(REQUEST)
        elif tf[0] == -1:
            return REQUEST.RESPONSE.redirect( REQUEST.URL1 )
        else:
            n = self._ProcessBilletAbsence(billet, tf[2]['estjust'], tf[2]['description'], REQUEST)
            if tf[2]['estjust']:
                j = 'justifiées'
            else:
                j = 'non justifiées'
            H.append('<div class="head_message">')
            if n > 0:
                H.append('%d absences (1/2 journées) %s ajoutées' % (n,j))
            elif n == 0:
                H.append("Aucun jour d'absence dans les dates indiquées !")
            elif n < 0:
                H.append("Ce billet avait déjà été traité !")
            H.append('</div><p><a class="stdlink" href="listeBillets">Autre billets en attente</a></p><h4>Billets déclarés par %s</h4>' % (etud['nomprenom']))
            billets = billet_absence_list(cnx,  {'etudid': etud['etudid'] } )
            tab = self._tableBillets(billets, etud=etud)
            H.append(tab.html())
            return '\n'.join(H) + self.sco_footer(REQUEST)

    security.declareProtected(ScoView, 'XMLgetAbsEtud')
    def XMLgetAbsEtud(self, beg_date='', end_date='', REQUEST=None):
        """returns list of absences in date interval"""
        t0 = time.time()
        etud = self.getEtudInfo(REQUEST=REQUEST)[0]
        exp = re.compile('^(\d{4})\D?(0[1-9]|1[0-2])\D?([12]\d|0[1-9]|3[01])$')
        if not exp.match(beg_date):
            raise ScoValueError('invalid date: %s' % beg_date)
        if not exp.match(end_date):
            raise ScoValueError('invalid date: %s' % end_date)
        
        Abs = self._ListeAbsDate(etud['etudid'], beg_date, end_date)
        
        REQUEST.RESPONSE.setHeader('content-type', XML_MIMETYPE)
        doc = jaxml.XML_document( encoding=SCO_ENCODING )
        doc.absences( etudid=etud['etudid'], beg_date=beg_date, end_date=end_date )
        doc._push()
        for a in Abs:
            if a['estabs']: # ne donne pas les justifications si pas d'absence
                doc._push()
                doc.abs( begin=a['begin'], end=a['end'], 
                         description=a['description'], justified=a['estjust'] )
                doc._pop()
        doc._pop()
        log('XMLgetAbsEtud (%gs)' % (time.time()-t0))
        return repr(doc)

_billet_absenceEditor = EditableTable(
    'billet_absence',
    'billet_id',
    ('billet_id', 'etudid', 'abs_begin', 'abs_end', 'description', 'etat', 'entry_date', 'justified'),
    sortkey='entry_date desc'
)

billet_absence_create = _billet_absenceEditor.create
billet_absence_delete = _billet_absenceEditor.delete
billet_absence_list = _billet_absenceEditor.list
billet_absence_edit = _billet_absenceEditor.edit

# ------ HTML Calendar functions (see YearTable function)

# MONTH/DAY NAMES:

MONTHNAMES = (
    'Janvier', 'F&eacute;vrier', 'Mars', 'Avril', 'Mai', 'Juin',
    'Juillet', 'Aout', 'Septembre', 'Octobre', 'Novembre', 'D&eacute;cembre' )

MONTHNAMES_ABREV = (
    'Jan.', 'F&eacute;v.', 'Mars', 'Avr.', 'Mai&nbsp;', 'Juin',
    'Juil', 'Aout', 'Sept', 'Oct.', 'Nov.', 'D&eacute;c.' )

DAYNAMES   = ( 'Lundi', 'Mardi', 'Mercredi', 'Jeudi', 'Vendredi', 'Samedi', 'Dimanche' )

DAYNAMES_ABREV = ( 'L', 'M', 'M', 'J', 'V', 'S', 'D' )

# COLORS:

WHITE = "#FFFFFF"
GRAY1 = "#EEEEEE"
GREEN3 = "#99CC99"
WEEKDAYCOLOR = GRAY1
WEEKENDCOLOR = GREEN3


def MonthTableHead( month ):
    color = WHITE
    return """<table class="monthcalendar" border="0" cellpadding="0" cellspacing="0" frame="box">
     <tr bgcolor="%s"><td class="calcol" colspan="2" align="center">%s</td></tr>\n""" % (
         color,MONTHNAMES_ABREV[month-1])

def MonthTableTail():
    return '</table>\n'

def MonthTableBody( month, year, events=[], halfday=0, trattributes='', work_saturday=False,
                    pad_width=8):
    #log('XXX events=%s' % events)
    firstday, nbdays = calendar.monthrange(year,month)
    localtime = time.localtime()
    current_weeknum = time.strftime( '%U', localtime )
    current_year =  localtime[0]
    T = []
    # cherche date du lundi de la 1ere semaine de ce mois
    monday = ddmmyyyy( '1/%d/%d' % (month,year))
    while monday.weekday != 0:
        monday = monday.prev()

    if work_saturday:
        weekend = ('D',)
    else:
        weekend = ('S', 'D')
    
    if not halfday:
        for d in range(1,nbdays+1):
            weeknum = time.strftime( '%U', time.strptime('%d/%d/%d'%(d,month,year),
                                                         '%d/%m/%Y'))
            day = DAYNAMES_ABREV[ (firstday+d-1) % 7 ]
            if day in weekend:
                bgcolor = WEEKENDCOLOR
                weekclass = 'wkend'
                attrs = ''
            else:
                bgcolor = WEEKDAYCOLOR
                weekclass = 'wk' + str(monday).replace('/','_')
                attrs = trattributes
            color = None
            legend = ''
            href = ''
            descr = ''
            # event this day ?        
            # each event is a tuple (date, text, color, href)
            #  where date is a string in ISO format (yyyy-mm-dd)
            for ev in events:
                ev_year = int(ev[0][:4])
                ev_month = int(ev[0][5:7])
                ev_day = int(ev[0][8:10])
                if year == ev_year and month == ev_month and ev_day == d:
                    if ev[1]:
                        legend = ev[1]
                    if ev[2]:
                        color = ev[2]
                    if ev[3]:
                        href = ev[3]
                    if len(ev) > 4 and ev[4]:
                        descr = ev[4]
            #
            cc = []
            if color != None:
                cc.append( '<td bgcolor="%s" class="calcell">' % color )
            else:
                cc.append( '<td class="calcell">' )
            
            if href:
                href='href="%s"' % href
            if descr:
                descr = 'title="%s"' % descr
            if href or descr:
                    cc.append( '<a %s %s>' % (href, descr) )                    
            
            if legend or d == 1:
                if pad_width != None:
                    n = pad_width-len(legend) # pad to 8 cars
                    if n > 0:
                        legend = '&nbsp;'*(n/2) + legend + '&nbsp;'*((n+1)/2)
            else:
                legend = '&nbsp;' # empty cell
            cc.append(legend)
            if href or descr:
                cc.append('</a>')
            cc.append('</td>')
            cell = string.join(cc,'')
            if day == 'D':
                monday = monday.next(7)
            if weeknum == current_weeknum and current_year == year and weekclass != 'wkend':
                weekclass += " currentweek"
            T.append( '<tr bgcolor="%s" class="%s" %s><td class="calday">%d%s</td>%s</tr>'
                      % (bgcolor, weekclass, attrs, d, day, cell) )
    else:
        # Calendar with 2 cells / day
        for d in range(1,nbdays+1):
            weeknum = time.strftime( '%U', time.strptime('%d/%d/%d'%(d,month,year),
                                                         '%d/%m/%Y'))
            day = DAYNAMES_ABREV[ (firstday+d-1) % 7 ]
            if day in weekend:
                bgcolor = WEEKENDCOLOR
                weekclass = 'wkend'
                attrs = ''
            else:
                bgcolor = WEEKDAYCOLOR
                weekclass = 'wk' + str(monday).replace('/','_')
                attrs = trattributes
            if weeknum == current_weeknum and current_year == year and weekclass != 'wkend':
                weeknum += " currentweek"

            if day == 'D':
                monday = monday.next(7)
            T.append( '<tr bgcolor="%s" class="wk%s" %s><td class="calday">%d%s</td>' % (bgcolor, weekclass, attrs, d, day) )
            cc = []
            for morning in (1,0):
                color = None
                legend = ''
                href = ''
                descr = ''
                for ev in events:
                    ev_year = int(ev[0][:4])
                    ev_month = int(ev[0][5:7])
                    ev_day = int(ev[0][8:10])
                    if ev[4] != None:
                        ev_half = int(ev[4])
                    else:
                        ev_half = 0
                    if year == ev_year and month == ev_month \
                           and ev_day == d and morning == ev_half:
                        if ev[1]:
                            legend = ev[1]
                        if ev[2]:
                            color = ev[2]
                        if ev[3]:
                            href = ev[3]
                        if len(ev) > 5 and ev[5]:
                            descr = ev[5]                                                    
                #
                if color != None:
                    cc.append( '<td bgcolor="%s" class="calcell">'
                               % (color))
                else:
                    cc.append( '<td class="calcell">'  )
                if href:
                    href='href="%s"' % href
                if descr:
                    descr = 'title="%s"' % descr
                if href or descr:
                    cc.append( '<a %s %s>' % (href, descr) )                    
                if legend or d == 1:
                    n = 3-len(legend) # pad to 3 cars
                    if n > 0:
                        legend = '&nbsp;'*(n/2) + legend + '&nbsp;'*((n+1)/2)
                else:
                    legend = '&nbsp;&nbsp;&nbsp;' # empty cell
                cc.append(legend)
                if href or descr:
                    cc.append('</a>')
                cc.append('</td>\n')
            T.append(string.join(cc,'')+'</tr>')
    return string.join(T,'\n')


# --------------------------------------------------------------------
#
# Zope Product Administration
#
# --------------------------------------------------------------------
def manage_addZAbsences(self, id= 'id_ZAbsences', title='The Title for ZAbsences Object', REQUEST=None):
   "Add a ZAbsences instance to a folder."
   self._setObject(id, ZAbsences(id, title))
   if REQUEST is not None:
        return self.manage_main(self, REQUEST)
        #return self.manage_editForm(self, REQUEST)

# The form used to get the instance id from the user.
#manage_addZAbsencesForm = DTMLFile('dtml/manage_addZAbsencesForm', globals())

    



# --------------------------------------------------------------------
#
# Cache absences
#
# On cache simplement (à la demande) le nombre d'absences de chaque etudiant
# dans un semestre donné.
# Toute modification du semestre (invalidation) invalide le cache 
#  (simple mécanisme de "listener" sur le cache de semestres)
# Toute modification des absences d'un étudiant invalide les caches des semestres 
# concernés à cette date (en général un seul semestre)
#
# On ne cache pas la liste des absences car elle est rarement utilisée (calendrier, 
#  absences à une date donnée).
#
# --------------------------------------------------------------------
class CAbsSemEtud:
    """Comptes d'absences d'un etudiant dans un semestre"""
    def __init__(self, context, formsemestre_id, etudid):
        self.context = context
        self.formsemestre_id = formsemestre_id
        self.etudid = etudid
        self._loaded = False
        context.Notes._getNotesCache().add_listener(self.invalidate, formsemestre_id, (etudid, formsemestre_id))
        
    def CountAbs(self):
        if not self._loaded:
            self.load()
        return self._CountAbs
    def CountAbsJust(self):
        if not self._loaded:
            self.load()
        return self._CountAbsJust
    
    def load(self):
        "Load state from DB"
        #log('loading CAbsEtudSem(%s,%s)' % (self.etudid, self.formsemestre_id))
        sem = self.context.Notes.get_formsemestre(self.formsemestre_id)
        debut_sem = DateDMYtoISO(sem['date_debut'])
        fin_sem = DateDMYtoISO(sem['date_fin'])
        
        self._CountAbs = self.context.Absences.CountAbs(etudid=self.etudid, debut=debut_sem, fin=fin_sem)
        self._CountAbsJust = self.context.Absences.CountAbsJust(etudid=self.etudid, debut=debut_sem,fin=fin_sem)        
        self._loaded = True
    
    def invalidate(self, args=None):
        "Notify me that DB has been modified"
        # log('invalidate CAbsEtudSem(%s,%s)' % (self.etudid, self.formsemestre_id))
        self._loaded = False
        

# Accès au cache des absences
ABS_CACHE_INST = {} # { DeptId : { formsemestre_id : { etudid :  CAbsEtudSem } } }

def getAbsSemEtud(context, formsemestre_id, etudid):
    AbsSemEtuds = getAbsSemEtuds(context, formsemestre_id)
    if not etudid in AbsSemEtuds:
       AbsSemEtuds[etudid] = CAbsSemEtud(context, formsemestre_id, etudid)
    return AbsSemEtuds[etudid]

def getAbsSemEtuds(context, formsemestre_id):
    u = context.GetDBConnexionString() # identifie le dept de facon fiable
    if not u in ABS_CACHE_INST:
        ABS_CACHE_INST[u] = {}
    C = ABS_CACHE_INST[u]
    if formsemestre_id not in C:
        C[formsemestre_id] = {}
    return C[formsemestre_id]

def invalidateAbsEtudDate(context, etudid, date):
    """Doit etre appelé à chaque modification des absences pour cet étudiant et cette date.
    Invalide cache absence et PDF bulletins si nécessaire.
    date: date au format ISO
    """
    # Semestres a cette date:
    etud = context.getEtudInfo(etudid=etudid,filled=True)[0]
    sems = [ sem for sem in etud['sems'] if sem['date_debut_iso'] <= date and sem['date_fin_iso'] >= date ]
    
    # Invalide les PDF et les abscences:
    for sem in sems:
        # Inval cache bulletin et/ou note_table
        if sco_compute_moy.formsemestre_expressions_use_abscounts(context, sem['formsemestre_id']):
            pdfonly = False # seules certaines formules utilisent les absences
        else:
            pdfonly = True # efface toujours le PDF car il affiche en général les absences
        
        context.Notes._inval_cache(pdfonly=pdfonly, formsemestre_id=sem['formsemestre_id'])
        
        # Inval cache compteurs absences:
        AbsSemEtuds = getAbsSemEtuds(context, sem['formsemestre_id'])
        if etudid in AbsSemEtuds:
            AbsSemEtuds[etudid].invalidate()

