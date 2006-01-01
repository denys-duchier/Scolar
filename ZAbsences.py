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

""" Gestion des absences (v4)
"""
import urllib

from OFS.SimpleItem import Item # Basic zope object
from OFS.PropertyManager import PropertyManager # provide the 'Properties' tab with the
                                # 'manage_propertiesForm' method
from OFS.ObjectManager import ObjectManager
from AccessControl.Role import RoleManager # provide the 'Ownership' tab with
                                # the 'manage_owner' method
from AccessControl import ClassSecurityInfo
import Globals
from Globals import DTMLFile # can use DTML files
from Globals import Persistent
from Acquisition import Implicit

# where we exist on the file system
file_path = Globals.package_home(globals())

# ---------------

from notesdb import *
from notes_log import log
from scolog import logdb
from sco_exceptions import *
from sco_utils import *
#import notes_users
from ScolarRolesNames import *
from TrivialFormulator import TrivialFormulator, TF
import scolars
import string, re
import time, calendar 

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
    def __init__(self,date=None,fmt='ddmmyyyy'):
	if date is None:
	    return
        if fmt == 'ddmmyyyy':
            self.day, self.month, self.year = string.split(date, '/')
        elif fmt == 'iso':
            self.year, self.month, self.day = string.split(date, '-')
        else:
            raise ValueError; 'invalid format spec.'
	self.year = string.atoi(self.year)
	self.month = string.atoi(self.month)
	self.day = string.atoi(self.day)
	# accept years YYYY or YY, uses 1970 as pivot
	if self.year < 1970:
	    if self.year > 100:
		raise ValueError, 'invalid year'
	    if self.year < 70:
		self.year = self.year + 2000
	    else:
		self.year = self.year + 1900
	if self.month < 1 or self.month > 12:
	    raise ValueError, 'invalid month'
	
	if self.day < 1 or self.day > MonthNbDays(self.month,self.year):
	    raise ValueError, 'invalid day'
    
	self.weekday = calendar.weekday(self.year,self.month,self.day)
	self.time = time.mktime( (self.year,self.month,self.day,0,0,0,0,0,0) )
    
    def iswork(self):
	"returns true if workable day"
	if self.weekday >= 0 and self.weekday < 5: # monday-friday
	    return 1
	else:
	    return 0
    
    def __repr__(self):
	return "'%02d/%02d/%04d'" % (self.day,self.month, self.year)
    def __str__(self):
	return '%02d/%02d/%04d' % (self.day,self.month, self.year)
    def ISO(self):
	"iso8601 representation of the date"
	return '%d-%d-%d' % (self.year, self.month, self.day)
    
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
	return self.__class__( '%02d/%02d/%04d' % (day,month,year) )
    
    def __cmp__ (self, other):
	"""return a negative integer if self < other, 
	zero if self == other, a positive integer if self > other"""
	return int(self.time - other.time)
    
    def __hash__(self):
	"we are immutable !"
	return hash(self.time) ^ hash(str(self))

# d = ddmmyyyy( '21/12/99' )




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
# this line is kept as an example with the files :
#     dtml/manage_editZScolarForm.dtml
#     html/ZScolar-edit.stx
#	{'label': 'Properties', 'action': 'manage_editForm',},
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

    # Ajout (dans l'instance) d'un dtml modifiable par Zope
    def defaultDocFile(self,id,title,file):
        f=open(file_path+'/dtml-editable/'+file+'.dtml')     
        file=f.read()     
        f.close()     
        self.manage_addDTMLMethod(id,title,file)

    # --------------------------------------------------------------------
    #
    #   ABSENCES (top level)
    #
    # --------------------------------------------------------------------
    # used to view content of the object
    security.declareProtected(ScoView, 'index_html')
    index_html = DTMLFile('dtml/absences/index_html', globals())

    security.declareProtected(ScoView, 'EtatAbsences')
    EtatAbsences = DTMLFile('dtml/absences/EtatAbsences', globals())
    security.declareProtected(ScoView, 'EtatAbsencesGr')
    EtatAbsencesGr = DTMLFile('dtml/absences/EtatAbsencesGr', globals())
    security.declareProtected(ScoView, 'EtatAbsencesDate')
    EtatAbsencesDate = DTMLFile('dtml/absences/EtatAbsencesDate', globals())
    security.declareProtected(ScoView, 'CalAbs')
    CalAbs = DTMLFile('dtml/absences/CalAbs', globals())

    security.declareProtected(ScoAbsChange, 'SignaleAbsenceEtud')
    SignaleAbsenceEtud=DTMLFile('dtml/absences/SignaleAbsenceEtud', globals())
    security.declareProtected(ScoAbsChange, 'doSignaleAbsence')
    doSignaleAbsence=DTMLFile('dtml/absences/doSignaleAbsence', globals())
    security.declareProtected(ScoAbsChange, 'SignaleAbsenceGrHebdo')
    SignaleAbsenceGrHebdo = DTMLFile('dtml/absences/SignaleAbsenceGrHebdo', globals())

    security.declareProtected(ScoAbsChange, 'JustifAbsenceEtud')
    JustifAbsenceEtud=DTMLFile('dtml/absences/JustifAbsenceEtud', globals())
    security.declareProtected(ScoAbsChange, 'doJustifAbsence')
    doJustifAbsence=DTMLFile('dtml/absences/doJustifAbsence', globals())

    security.declareProtected(ScoAbsChange, 'AnnuleAbsenceEtud')
    AnnuleAbsenceEtud=DTMLFile('dtml/absences/AnnuleAbsenceEtud', globals())
    security.declareProtected(ScoAbsChange, 'doAnnuleAbsence')
    doAnnuleAbsence=DTMLFile('dtml/absences/doAnnuleAbsence', globals())
    security.declareProtected(ScoAbsChange, 'doAnnuleJustif')
    doAnnuleJustif=DTMLFile('dtml/absences/doAnnuleJustif', globals())

    # --------------------------------------------------------------------
    #
    #   SQL METHODS
    #
    # --------------------------------------------------------------------
    security.declareProtected(ScoAbsChange, 'AddAbsence')
    def AddAbsence(self, etudid, jour, matin, estjust, REQUEST):
        "Ajoute une absence dans la bd"
        estjust = _toboolean(estjust)
        matin = _toboolean(matin)
        cnx = self.GetDBConnexion()
        cursor = cnx.cursor()
        cursor.execute('insert into absences (etudid,jour,estabs,estjust,matin) values (%(etudid)s,%(jour)s, TRUE, %(estjust)s, %(matin)s )', vars() )
        logdb(REQUEST, cnx, 'AddAbsence', etudid=etudid,
              msg='JOUR=%(jour)s,MATIN=%(matin)s,ESTJUST=%(estjust)s'%vars())
        cnx.commit()
        # Invalid cache (nbabs sur bulletins)
        self.Notes.CachedNotesTable.inval_cache()

    security.declareProtected(ScoAbsChange, 'AddJustif')
    def AddJustif(self, etudid, jour, matin, REQUEST):
        "Ajoute un justificatif dans la base"
        matin = _toboolean(matin)
        cnx = self.GetDBConnexion()
        cursor = cnx.cursor()
        cursor.execute('insert into absences (etudid,jour,estabs,estjust,matin) values (%(etudid)s,%(jour)s, FALSE, TRUE, %(matin)s )', vars() )
        logdb(REQUEST, cnx, 'AddJustif', etudid=etudid,
              msg='JOUR=%(jour)s,MATIN=%(matin)s'%vars())
        cnx.commit()
        # Invalid cache (nbabs sur bulletins)
        self.Notes.CachedNotesTable.inval_cache()

    security.declareProtected(ScoAbsChange, 'AnnuleAbsence')
    def AnnuleAbsence(self, etudid, jour, matin, REQUEST):
        "Annule une absence ds base"
        matin = _toboolean(matin)
        cnx = self.GetDBConnexion()
        cursor = cnx.cursor()
        cursor.execute('delete from absences where jour=%(jour)s and matin=%(matin)s and etudid=%(etudid)s and estabs', vars())
        logdb(REQUEST, cnx, 'AnnuleAbsence', etudid=etudid,
              msg='JOUR=%(jour)s,MATIN=%(matin)s'%vars())
        cnx.commit()
        # Invalid cache (nbabs sur bulletins)
        self.Notes.CachedNotesTable.inval_cache()

    security.declareProtected(ScoAbsChange, 'AnnuleJustif')
    def AnnuleJustif(self,etudid, jour, matin, REQUEST):
        "Annule un justificatif"
        matin = _toboolean(matin)
        cnx = self.GetDBConnexion()
        cursor = cnx.cursor()
        cursor.execute('delete from absences where jour=%(jour)s and matin=%(matin)s and etudid=%(etudid)s and ESTJUST AND NOT ESTABS', vars() )
        logdb(REQUEST, cnx, 'AnnuleJustif', etudid=etudid,
              msg='JOUR=%(jour)s,MATIN=%(matin)s'%vars())
        cnx.commit()
        # Invalid cache (nbabs sur bulletins)
        self.Notes.CachedNotesTable.inval_cache()

    security.declareProtected(ScoView, 'CountAbs')
    def CountAbs(self, etudid, debut, fin):
        cnx = self.GetDBConnexion()
        cursor = cnx.cursor()
        cursor.execute("""SELECT COUNT(*) AS NbAbs FROM (
    SELECT DISTINCT A.JOUR, A.MATIN
    FROM ABSENCES A
    WHERE A.ETUDID = %(etudid)s
      AND A.ESTABS
      AND A.JOUR BETWEEN %(debut)s AND %(fin)s
          ) AS tmp
          """, vars())
        res = cursor.fetchone()[0]
        return res

    security.declareProtected(ScoView, 'CountAbsJust')
    def CountAbsJust(self, etudid, debut, fin):
        cnx = self.GetDBConnexion()
        cursor = cnx.cursor()
        cursor.execute("""SELECT COUNT(*) AS NbAbsJust FROM (
  SELECT DISTINCT A.JOUR, A.MATIN
  FROM ABSENCES A, ABSENCES B
  WHERE A.ETUDID = %(etudid)s
      AND A.ETUDID = B.ETUDID 
      AND A.JOUR = B.JOUR AND A.MATIN = B.MATIN
      AND A.JOUR BETWEEN %(debut)s AND %(fin)s
      AND A.ESTABS AND (A.ESTJUST OR B.ESTJUST)
) AS tmp
        """, vars() )
        res = cursor.fetchone()[0]
        return res
# XXX inutilisé (idem ListeAbsNonJust) ?
#     security.declareProtected(ScoView, 'ListeAbsDate')
#     def ListeAbsDate(self, etudid, datedebut):
#         "Liste des absences NON justifiees"
#         cnx = self.GetDBConnexion()
#         cursor = cnx.cursor()
#         cursor.execute("""SELECT JOUR, MATIN FROM ABSENCES A 
#     WHERE A.ETUDID = %(etudid)s
#     AND A.estabs 
#     AND A.jour > %(datebut)s
#     EXCEPT SELECT JOUR FROM ABSENCES B 
#     WHERE B.estjust 
#     AND B.ETUDID = %(etudid)s
#         """, vars() )
#         return cursor.dictfetchall()
    
    security.declareProtected(ScoView, 'ListeAbsJust')
    def ListeAbsJust(self, etudid, datedebut):
        "Liste des absences justifiees"
        cnx = self.GetDBConnexion()
        cursor = cnx.cursor()
        cursor.execute("""SELECT DISTINCT A.ETUDID, A.JOUR, A.MATIN FROM ABSENCES A, ABSENCES B
 WHERE A.ETUDID = %(etudid)s
 AND A.ETUDID = B.ETUDID 
 AND A.JOUR = B.JOUR AND A.MATIN = B.MATIN AND A.JOUR > %(datedebut)s
 AND A.ESTABS AND (A.ESTJUST OR B.ESTJUST)
        """, vars() )
        return cursor.dictfetchall()

    security.declareProtected(ScoView, '')
    def ListeAbsNonJust(self, etudid, datedebut):
        "Liste des absences NON justifiees"
        cnx = self.GetDBConnexion()
        cursor = cnx.cursor()
        cursor.execute("""SELECT JOUR, MATIN FROM ABSENCES A 
    WHERE A.ETUDID = %(etudid)s
    AND A.estabs 
    AND A.jour > %(datedebut)s
    EXCEPT SELECT JOUR, MATIN FROM ABSENCES B 
    WHERE B.estjust 
    AND B.ETUDID = %(etudid)s
        """, vars() )
        return cursor.dictfetchall()



    # --- Misc tools.... ------------------
    security.declareProtected(ScoView, 'ListMondays')
    def ListMondays(self, year=None):
        """return list of mondays (ISO dates), from september to june
        """
        if not year:
            year = int(time.strftime('%Y'))
        d = ddmmyyyy( '1/9/%d' % year )
        while d.weekday != 0:
            d = d.next()
        end = ddmmyyyy('1/7/%d' % (year+1))
        L = [ d ]
        while d < end:
            d = d.next(days=7)
            L.append(d)
        return map( lambda x: x.ISO(), L )

    security.declareProtected(ScoView, 'NextISODay')
    def NextISODay(self, date ):
        "return date after date"
        d = ddmmyyyy(date, fmt='iso')
        return d.next().ISO()

    security.declareProtected(ScoView, 'DateRangeISO')
    def DateRangeISO(self, date_beg, date_end, workable=1 ):
        """returns list of dates in [date_beg,date_end]
        workable = 1 => keeps only workable days"""
        if not date_end:
            date_end = date_beg
        r = []
        cur = ddmmyyyy( date_beg )
        end = ddmmyyyy( date_end )
        while cur <= end:
            if (not workable) or cur.iswork():
                r.append(cur)
            cur = cur.next()
        return map( lambda x: x.ISO(), r )

    security.declareProtected(ScoView, 'DateDDMMYYYY2ISO')
    def DateDDMMYYYY2ISO(self,  dmy ):
        "convert dmy to ISO date format"
        day, month, year = string.split(dmy, '/')
        year = string.atoi(year)
        month = string.atoi(month)
        day = string.atoi(day)
        # accept years YYYY or YYY, uses 1970 as pivot
        if year < 1970:
            if year > 100:
                raise ValueError, 'invalid year'
            if year < 70:
                year = year + 2000
            else:
                year = year + 1900
        if month < 1 or month > 12:
            raise ValueError, 'invalid month'
        # compute nb of day in month:
        mo = month
        if mo > 7:
            mo = mo+1
        if mo % 2:
            MonthNbDays = 31
        elif mo == 2:
            if year % 4 == 0 and (year % 100 <> 0 or year % 400 == 0):
                MonthNbDays = 29 # leap
            else:
                MonthNbDays = 28
        else:
            MonthNbDays = 30    
        if day < 1 or day > MonthNbDays:
            raise ValueError, 'invalid day'    
        return '%d-%d-%d' % (year, month, day)

    def YearTable(self, year, events=[], firstmonth=9, lastmonth=6, halfday=0 ):
        """Generate a calendar table
        events = list of tuples (date, text, color, href [,halfday])
                 where date is a string in ISO format (yyyy-mm-dd)
                 halfday is boolean (true: morning, false: afternoon)
        text  = text to put in calendar (must be short, 1-5 cars) (optional)
        if halday, generate 2 cells per day (morning, afternoon)
        """
        T = [ '<table class="maincalendar" border="3" cellpadding="1" cellspacing="1" frame="box">' ]
        T.append( '<tr>' )
        month = firstmonth
        while 1:
            T.append( '<td valign="top">' )
            T.append( MonthTableHead( month ) )
            T.append( MonthTableBody( month, year, events, halfday ) )
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

# ------ HTML Calendar functions (see YearTable method)

# MONTH/DAY NAMES:

MONTHNAMES = ( 'Janvier', 'F&eacute;vrier', 'Mars', 'Avril', 'Mai',
	       'Juin', 'Juillet', 'Aout', 'Septembre', 'Octobre', 
	       'Novembre', 'D&eacute;cembre' )

MONTHNAMES_ABREV = ( 'Jan.', 'F&eacute;v.', 'Mars', 'Avr.', 'Mai&nbsp;',
	       'Juin', 'Juil', 'Aout', 'Sept', 'Oct.', 
	       'Nov.', 'D&eacute;c.' )


DAYNAMES   = ( 'Lundi', 'Mardi', 'Mercredi', 'Jeudi', 'Vendredi', 
	       'Samedi', 'Dimanche' )

DAYNAMES_ABREV = ( 'L', 'M', 'M', 'J', 'V', 'S', 'D' )

# COLORS:

WHITE = "#FFFFFF"
GRAY1 = "#EEEEEE"
GREEN3 = "#99CC99"
WEEKDAYCOLOR = GRAY1
WEEKENDCOLOR = GREEN3


def MonthTableHead( month ):
    color = WHITE
    return """<table class="maincalendar" border="0" cellpadding="0" cellspacing="0" frame="box">
     <tr bgcolor="%s"><td colspan="2" align="center">%s</td></tr>\n""" % (
	 color,MONTHNAMES_ABREV[month-1])

def MonthTableTail():
    return '</table>\n'

def MonthTableBody( month, year, events=[], halfday=0 ):
    firstday, nbdays = calendar.monthrange(year,month)
    T = []
    if not halfday:
        for d in range(1,nbdays+1):
            day = DAYNAMES_ABREV[ (firstday+d-1) % 7 ]	
            if day in ('S','D'):
                bgcolor = WEEKENDCOLOR
            else:
                bgcolor = WEEKDAYCOLOR
            color = None
            legend = ''
            href = ''
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
            #
            cc = []
            if color != None:
                cc.append( '<td bgcolor="%s">' % color )
            else:
                cc.append( '<td>' )
            if href:
                cc.append( '<a href="%s">' % href )
            if legend or d == 1:
                n = 8-len(legend) # pad to 8 cars
                if n > 0:
                    legend = '&nbsp;'*(n/2) + legend + '&nbsp;'*((n+1)/2)
            else:
                legend = '&nbsp;' # empty cell
            cc.append(legend)
            if href:
                cc.append('</a>')
            cc.append('</td>')
            cell = string.join(cc,'')
            T.append( '<tr bgcolor="%s"><td align="right">%d%s</td>%s</tr>'
                      % (bgcolor, d, day, cell) )
    else:
        # Calendar with 2 cells / day
        for d in range(1,nbdays+1):
            day = DAYNAMES_ABREV[ (firstday+d-1) % 7 ]	
            if day in ('S','D'):
                bgcolor = WEEKENDCOLOR
            else:
                bgcolor = WEEKDAYCOLOR
            T.append( '<tr bgcolor="%s"><td align="right">%d%s</td>' % (bgcolor, d, day) )
            cc = []
            for morning in (1,0):
                color = None
                legend = ''
                href = ''
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
                #
                if color != None:
                    cc.append( '<td bgcolor="%s">'
                               % (color))
                else:
                    cc.append( '<td>'  )
                if href:
                    cc.append( '<a href="%s">' % href )
                if legend or d == 1:
                    n = 3-len(legend) # pad to 3 cars
                    if n > 0:
                        legend = '&nbsp;'*(n/2) + legend + '&nbsp;'*((n+1)/2)
                else:
                    legend = '&nbsp;&nbsp;&nbsp;' # empty cell
                cc.append(legend)
                if href:
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


    

