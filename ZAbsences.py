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
    def __init__(self,date=None,fmt='ddmmyyyy',work_saturday=False):
        self.work_saturday = work_saturday
	if date is None:
	    return
        if fmt == 'ddmmyyyy':
            self.day, self.month, self.year = string.split(date, '/')
        elif fmt == 'iso':
            self.year, self.month, self.day = string.split(date, '-')
        else:
            raise ValueError; 'invalid format spec. (%s)' % fmt
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
	    raise ValueError, 'invalid month (%s)' % self.month
	
	if self.day < 1 or self.day > MonthNbDays(self.month,self.year):
	    raise ValueError, 'invalid day (%s)' % self.day

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

    security.declareProtected(ScoView, 'calabs_css')
    calabs_css = DTMLFile('JavaScripts/calabs_css', globals())
    security.declareProtected(ScoView, 'calabs_js')
    calabs_js = DTMLFile('JavaScripts/calabs_js', globals())
    
    # --------------------------------------------------------------------
    #
    #   SQL METHODS
    #
    # --------------------------------------------------------------------
    security.declareProtected(ScoAbsChange, 'AddAbsence')
    def AddAbsence(self, etudid, jour, matin, estjust, REQUEST):
        "Ajoute une absence dans la bd"
        if self._isFarFutur(jour):
            raise ScoValueError('date absence trop loin dans le futur !')
        estjust = _toboolean(estjust)
        matin = _toboolean(matin)
        cnx = self.GetDBConnexion()
        cursor = cnx.cursor()
        cursor.execute('insert into absences (etudid,jour,estabs,estjust,matin) values (%(etudid)s,%(jour)s, TRUE, %(estjust)s, %(matin)s )', vars() )
        logdb(REQUEST, cnx, 'AddAbsence', etudid=etudid,
              msg='JOUR=%(jour)s,MATIN=%(matin)s,ESTJUST=%(estjust)s'%vars())
        cnx.commit()
        # Invalid cache (nbabs sur bulletins)
        self.Notes._inval_cache()

    security.declareProtected(ScoAbsChange, 'AddJustif')
    def AddJustif(self, etudid, jour, matin, REQUEST):
        "Ajoute un justificatif dans la base"
        if self._isFarFutur(jour):
            raise ScoValueError('date justificatif trop loin dans le futur !')
        matin = _toboolean(matin)
        cnx = self.GetDBConnexion()
        cursor = cnx.cursor()
        cursor.execute('insert into absences (etudid,jour,estabs,estjust,matin) values (%(etudid)s,%(jour)s, FALSE, TRUE, %(matin)s )', vars() )
        logdb(REQUEST, cnx, 'AddJustif', etudid=etudid,
              msg='JOUR=%(jour)s,MATIN=%(matin)s'%vars())
        cnx.commit()
        # Invalid cache (nbabs sur bulletins)
        self.Notes._inval_cache()

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
        self.Notes._inval_cache()

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
        self.Notes._inval_cache()

    security.declareProtected(ScoAbsChange, 'AnnuleAbsencesPeriodNoJust' )
    def AnnuleAbsencesPeriodNoJust(self, etudid, datedebut, datefin, REQUEST=None):
        """Supprime les absences entre ces dates (incluses).
        mais ne supprime pas les justificatifs.
        """
        cnx = self.GetDBConnexion()
        cursor = cnx.cursor()
        # supr les absences non justifiees
        cursor.execute("delete from absences where etudid=%(etudid)s and (not estjust) and jour BETWEEN %(datedebut)s AND %(datefin)s",
                       vars() )
        # s'assure que les justificatifs ne sont pas "absents"
        cursor.execute("update absences set estabs=FALSE where  etudid=%(etudid)s and jour BETWEEN %(datedebut)s AND %(datefin)s", vars())
        logdb(REQUEST, cnx, 'AnnuleAbsencesPeriodNoJust', etudid=etudid,
              msg='%(datedebut)s - %(datefin)s'%vars())
        cnx.commit()

    security.declareProtected(ScoAbsChange, 'AnnuleAbsencesDatesNoJust')
    def AnnuleAbsencesDatesNoJust(self, etudid, dates, REQUEST=None):
        """Supprime les absences aux dates indiqu�es
        mais ne supprime pas les justificatifs.
        """
        if not dates:
            return
        cnx = self.GetDBConnexion()
        cursor = cnx.cursor()
        # supr les absences non justifiees
        for date in dates:
            cursor.execute(
                "delete from absences where etudid=%(etudid)s and (not estjust) and jour=%(date)s",
                vars() )
        # s'assure que les justificatifs ne sont pas "absents"
        for date in dates:
            cursor.execute(
                "update absences set estabs=FALSE where  etudid=%(etudid)s and jour=%(date)s",
                vars())
        logdb(REQUEST, cnx, 'AnnuleAbsencesDatesNoJust', etudid=etudid,
              msg='%s - %s' % (dates[0],dates[1]) )
        cnx.commit()

    security.declareProtected(ScoView, 'CountAbs')
    def CountAbs(self, etudid, debut, fin, matin=None):
        "CountAbs"
        if matin != None:
            matin = _toboolean(matin)
            ismatin = ' AND A.MATIN = %(matin)s '
        else:
            ismatin = ''
        cnx = self.GetDBConnexion()
        cursor = cnx.cursor()
        cursor.execute("""SELECT COUNT(*) AS NbAbs FROM (
    SELECT DISTINCT A.JOUR, A.MATIN
    FROM ABSENCES A
    WHERE A.ETUDID = %(etudid)s
      AND A.ESTABS""" + ismatin + """
      AND A.JOUR BETWEEN %(debut)s AND %(fin)s
          ) AS tmp
          """, vars())
        res = cursor.fetchone()[0]
        return res

    security.declareProtected(ScoView, 'CountAbsJust')
    def CountAbsJust(self, etudid, debut, fin, matin=None):
        if matin != None:
            matin = _toboolean(matin)
            ismatin = ' AND A.MATIN = %(matin)s '
        else:
            ismatin = ''
        cnx = self.GetDBConnexion()
        cursor = cnx.cursor()
        cursor.execute("""SELECT COUNT(*) AS NbAbsJust FROM (
  SELECT DISTINCT A.JOUR, A.MATIN
  FROM ABSENCES A, ABSENCES B
  WHERE A.ETUDID = %(etudid)s
      AND A.ETUDID = B.ETUDID 
      AND A.JOUR = B.JOUR AND A.MATIN = B.MATIN
      AND A.JOUR BETWEEN %(debut)s AND %(fin)s
      AND A.ESTABS AND (A.ESTJUST OR B.ESTJUST)""" + ismatin + """
) AS tmp
        """, vars() )
        res = cursor.fetchone()[0]
        return res
# XXX inutilis� (idem ListeAbsNonJust) ?
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

    security.declareProtected(ScoView, 'ListeAbsNonJust')
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

    security.declareProtected(ScoView, 'ListeAbsJour')
    def ListeAbsJour(self, date, am=True, pm=True):
        "Liste des absences ce jour"
        cnx = self.GetDBConnexion()
        cursor = cnx.cursor()
        req = """SELECT DISTINCT etudid, jour, matin FROM ABSENCES A 
    WHERE A.estabs 
    AND A.jour = %(date)s
    """
        if not am:
            req += "AND NOT matin "
        if not pm:
            req += "AND matin"
        
        cursor.execute(req, { 'date' : date } )
        return cursor.dictfetchall()

    security.declareProtected(ScoView, 'ListeAbsNonJustJour')
    def ListeAbsNonJustJour(self, date, am=True, pm=True):
        "Liste des absences non justifiees ce jour"
        cnx = self.GetDBConnexion()
        cursor = cnx.cursor()
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
        return cursor.dictfetchall()

    security.declareProtected(ScoAbsChange, 'doSignaleAbsenceGrHebdo')
    def doSignaleAbsenceGrHebdo(self, abslist=[],
                                datedebut=None, datefin=None, etudids=[],
                                destination=None, REQUEST=None):
        """Enregistre absences hebdo. Efface les anciennes absences et
        signale les nouvelles.
        abslist : liste etudid:date:ampm des absences signalees
        etudis : liste des etudids concernes
        datedebut, datefin: dates (ISO) de la semaine        
        """
        etudids = etudids.split(',')
        H = [ self.sco_header(REQUEST,page_title='Absences') ]
        footer = self.sco_footer(REQUEST)
        if not etudids:
            return '\n'.join(H) + '<h3>Rien � ajouter !</h3>' + footer
        
        # 1- Efface les absences
        for etudid in etudids:
            self.AnnuleAbsencesPeriodNoJust(etudid, datedebut, datefin, REQUEST) 
        
        # 2- Ajoute les absences        
        self._add_abslist(abslist, REQUEST)

        H.append('<h3>Absences ajout�es</h3>')
        if not destination:
            destination = REQUEST.URL1
        H.append('<p><a class="stdlink" href="%s">continuer</a></p>'%destination)
        return '\n'.join(H) + footer

    security.declareProtected(ScoAbsChange, 'doSignaleAbsenceGrSemestre')
    def doSignaleAbsenceGrSemestre(self, abslist=[],
                                   dates=[], etudids=[],
                                   destination=None, REQUEST=None):
        """Enregistre absences aux dates indiquees (abslist et dates).
        dates est une liste de dates ISO (s�par�es par des ',').
        Efface les absences aux dates indiqu�es par dates, et ajoute
        celles de abslist.
        """
        etudids = etudids.split(',')
        dates = dates.split(',')
        H = [ self.sco_header(REQUEST,page_title='Absences') ]
        footer = self.sco_footer(REQUEST)
        if not etudids or not dates:
            return '\n'.join(H) + '<h3>Rien � ajouter !</h3>' + footer
        # 1- Efface les absences
        for etudid in etudids:
            self.AnnuleAbsencesDatesNoJust(etudid, dates, REQUEST) 
        
        # 2- Ajoute les absences
        self._add_abslist(abslist, REQUEST)

        H.append('<h3>Absences ajout�es</h3>')
        if not destination:
            destination = REQUEST.URL1
        H.append('<p><a class="stdlink" href="%s">continuer</a></p>'
                 %destination)
        return '\n'.join(H) + footer

    def _add_abslist(self, abslist, REQUEST):
        for a in abslist:
            etudid, jour, ampm = a.split(':')
            if ampm == 'am':
                matin=1
            elif ampm=='pm':
                matin=0
            else:
                raise ValueError, 'invalid ampm !'
             # ajoute abs si pas deja absent
            if self.CountAbs( etudid, jour, jour, matin) == 0:                
                self.AddAbsence( etudid, jour, matin, 0, REQUEST )
        
    #
    security.declareProtected(ScoView, 'CalSelectWeek')
    def CalSelectWeek(self, year=None, REQUEST=None):
        "display calendar allowing week selection"
        if not year:
            year = self.AnneeScolaire()
        C = self.YearTable(int(year), dayattributes='onmouseover="highlightweek(this);" onmouseout="deselectweeks();" onclick="wclick(this);"')
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
        "Vrai si le samedi est travaill�"
        try:
            r = int(self.work_saturday) # preference: Zope property
        except:
            r = 0
        return r

    def day_names(self):
        """Returns week day names.
        If work_saturday property is set, include saturday
        """
        if self.is_work_saturday():
            return ['Lundi', 'Mardi', 'Mercredi', 'Jeudi', 'Vendredi', 'Samedi']
        else:
            return ['Lundi', 'Mardi', 'Mercredi', 'Jeudi', 'Vendredi']
    
    security.declareProtected(ScoView, 'ListMondays')
    def ListMondays(self, year=None):
        """return list of mondays (ISO dates), from september to june
        """
        if not year:
            year = self.AnneeScolaire()
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
            raise ScoValueError("pas de date sp�cifi�e !")
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

    def YearTable(self, year, events=[],
                  firstmonth=9, lastmonth=6, halfday=0, dayattributes='' ):
        """Generate a calendar table
        events = list of tuples (date, text, color, href [,halfday])
                 where date is a string in ISO format (yyyy-mm-dd)
                 halfday is boolean (true: morning, false: afternoon)
        text  = text to put in calendar (must be short, 1-5 cars) (optional)
        if halday, generate 2 cells per day (morning, afternoon)
        """
        T = [ '<table id="maincalendar" class="maincalendar" border="3" cellpadding="1" cellspacing="1" frame="box">' ]
        T.append( '<tr>' )
        month = firstmonth
        while 1:
            T.append( '<td valign="top">' )
            T.append( MonthTableHead( month ) )
            T.append( MonthTableBody( month, year, events, halfday, dayattributes, self.is_work_saturday() ) )
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

    # ------------ HTML Interfaces
    security.declareProtected(ScoAbsChange, 'SignaleAbsenceGrHebdo')
    def SignaleAbsenceGrHebdo(self, datelundi, semestregroupe,
                              destination, REQUEST=None):
        "Saisie hebdomadaire des absences"
        formsemestre_id = semestregroupe.split('!')[0]
        groupetd = semestregroupe.split('!')[1]
        groupeanglais = semestregroupe.split('!')[2]
        groupetp = semestregroupe.split('!')[3]
        sem = self.Notes.do_formsemestre_list({'formsemestre_id':formsemestre_id})[0]
        # calcule dates jours de cette semaine
        datessem = [ self.DateDDMMYYYY2ISO(datelundi) ]
        for jour in self.day_names()[1:]:
            datessem.append( self.NextISODay(datessem[-1]) )
        #                
        H = [ self.sco_header(page_title='Saisie hebdomadaire des absences',
                              no_side_bar=1,REQUEST=REQUEST),
              """<table border="0" cellspacing="16"><tr><td>
              <h2>Saisie des absences pour le groupe %s %s %s de %s, 
              semaine du lundi %s</h2>

              <p><a href="index_html">Annuler</a></p>

              <p>
              <form action="doSignaleAbsenceGrHebdo" method="post">              
              """ % (groupetd, groupeanglais, groupetp, sem['titre_num'], datelundi) ]
        #
        etuds = self.getEtudInfoGroupe(formsemestre_id,groupetd,groupeanglais,groupetp)

        H += self._gen_form_saisie_groupe(etuds, self.day_names(), datessem, destination)

        H.append(self.sco_footer(REQUEST))
        return '\n'.join(H)

    security.declareProtected(ScoAbsChange, 'SignaleAbsenceGrSemestre')
    def SignaleAbsenceGrSemestre(self, datedebut, datefin, semestregroupe,
                                 destination,
                                 nbweeks=4, # ne montre que les nbweeks dernieres semaines
                                 REQUEST=None):
        """Saisie des absences sur une journ�e sur un semestre
        (ou intervalle de dates) entier"""
        formsemestre_id = semestregroupe.split('!')[0]
        groupetd = semestregroupe.split('!')[1]
        groupeanglais = semestregroupe.split('!')[2]
        groupetp = semestregroupe.split('!')[3]
        sem = self.Notes.do_formsemestre_list({'formsemestre_id':formsemestre_id})[0]
        jourdebut = ddmmyyyy(datedebut, work_saturday=self.is_work_saturday())
        jourfin = ddmmyyyy(datefin, work_saturday=self.is_work_saturday())
        today = ddmmyyyy(time.strftime('%d/%m/%Y', time.localtime()), work_saturday=self.is_work_saturday())
        today.next()
        if jourfin > today: # ne propose pas les semaines dans le futur
            jourfin = today
        #
        if not jourdebut.iswork() or jourdebut > jourfin:
            raise ValueError('date debut invalide (ouvrable=%d)' % jourdebut.iswork() )
        # calcule dates
        dates = [] # ddmmyyyy instances
        d = ddmmyyyy(datedebut, work_saturday=self.is_work_saturday())
        while d <= jourfin:
            dates.append(d)
            d = d.next(7) # avance d'une semaine
        #
        msg = 'Montrer seulement les 4 derni�res semaines'
        nwl = 4
        if nbweeks:
            nbweeks = int(nbweeks)
            if nbweeks > 0:
                dates = dates[-nbweeks:]
                msg = 'Montrer toutes les semaines'
                nwl = 0
        #
        colnames = [ str(x) for x in dates ]
        dates = [ x.ISO() for x in dates ]
        
        H = [ self.sco_header(page_title='Saisie des absences',
                              no_side_bar=1,REQUEST=REQUEST),
              """<table border="0" cellspacing="16"><tr><td>
              <h2>Saisie des absences pour le groupe %s %s %s de %s, 
              les %s</h2>
              <p>
              <a href="SignaleAbsenceGrSemestre?datedebut=%s&datefin=%s&semestregroupe=%s&destination=%s&nbweeks=%d">%s</a>
              <form action="doSignaleAbsenceGrSemestre" method="post">              
              """ % (groupetd, groupeanglais, groupetp, sem['titre_num'],
                     self.day_names()[jourdebut.weekday],
                     datedebut, datefin, semestregroupe, destination, nwl, msg) ]
        #
        etuds = self.getEtudInfoGroupe(formsemestre_id,groupetd,groupeanglais,groupetp)
        H += self._gen_form_saisie_groupe(etuds, colnames, dates, destination)
        H.append(self.sco_footer(REQUEST))
        return '\n'.join(H)
    
    def _gen_form_saisie_groupe(self, etuds, colnames, dates, destination=''):
        H = [ """
        <script type="text/javascript">
        function colorize(obj) {
             if (obj.checked) {
                 obj.parentNode.className = 'absent';
             } else {
                 obj.parentNode.className = 'present';
             }
        }
        </script>
        <table rules="cols" frame="box">
        <tr><td>&nbsp;</td>
        """]
        # Titres colonnes
        for jour in colnames:
            H.append('<th colspan="2" width="100px" style="padding-left: 5px; padding-right: 5px;">' + jour + '</th>')
        H.append('</tr><tr><td>&nbsp;</td>')
        H.append('<th>AM</th><th>PM</th>' * len(colnames) )
        H.append('</tr>')
        #
        i=1
        for etud in etuds:
            i += 1
            etudid = etud['etudid']
            bgcolor = ('bgcolor="#ffffff"', 'bgcolor="#ffffff"', 'bgcolor="#dfdfdf"')[i%3]
            matin_bgcolor = ('bgcolor="#e1f7ff"', 'bgcolor="#e1f7ff"', 'bgcolor="#c1efff"')[i%3]
            H.append('<tr %s><td><b><a class="discretelink" href="ficheEtud?etudid=%s" target="new">%s</a></b></td>'
                     % (bgcolor, etudid, etud['nomprenom']))
            for date in dates:
                # matin
                if self.CountAbs( etudid, date, date, True):
                    checked = 'checked'
                else:
                    checked = ''
                H.append('<td %s><input type="checkbox" name="abslist:list" value="%s" %s onclick="colorize(this)"/></td>'
                         % (matin_bgcolor, etudid+':'+date+':'+'am', checked))
                # apres midi
                if self.CountAbs( etudid, date, date, False):
                    checked = 'checked'
                else:
                    checked = ''
                H.append('<td><input type="checkbox" name="abslist:list" value="%s" %s onclick="colorize(this)"/></td>'
                         % (etudid+':'+date+':'+'pm', checked))
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
                 % destination )
        #
        H.append("""
        <p><input type="submit" value="OK, enregistrer ces absences"/>
        <input type="button" value="Annuler"  onClick="window.location='%s'"/>
        </p>
        </form>        
        </p>
        </td></tr></table>
        <p class="help">Les cases coch�es correspondent � des absences.
        Les absences saisies ne sont pas justifi�es (sauf si un justificatif a �t� entr�
        par ailleurs).
        </p><p class="help">Si vous "d�cochez" une case,  l'absence correspondante sera supprim�e.
        </p>
        """ % destination)
        return H
        
    security.declareProtected(ScoView, 'ListeAbsEtud')
    def ListeAbsEtud(self, etudid, with_evals=True, REQUEST=None):
        "Liste des absences d'un �tudiant sur l'ann�e en cours"
        datedebut = '%s-08-31' % self.AnneeScolaire()
        #datefin = '%s-08-31' % (self.AnneeScolaire()+1)
        absjust = self.ListeAbsJust( etudid=etudid, datedebut=datedebut)
        absnonjust = self.ListeAbsNonJust(etudid=etudid, datedebut=datedebut)

        # examens ces jours l� ?
        if with_evals:
            cnx = self.GetDBConnexion()
            cursor = cnx.cursor()
            for a in absnonjust + absjust:
                cursor.execute("""select eval.*
                from notes_evaluation eval, notes_moduleimpl_inscription mi, notes_moduleimpl m
                where eval.jour = %(jour)s and eval.moduleimpl_id = m.moduleimpl_id
                and mi.moduleimpl_id = m.moduleimpl_id and mi.etudid = %(etudid)s""",
                               { 'jour' : a['jour'].strftime('%Y-%m-%d'), 'etudid' : etudid } )
                a['evals'] = cursor.dictfetchall() 
        # Mise en forme HTML:
        etud = self.getEtudInfo(etudid=etudid,filled=True)[0]
        H = [ self.sco_header(REQUEST,page_title='Absences de %s' % etud['nomprenom']) ]
        H.append( """<h2>Absences de %s (� partir du %s)</h2>
        <h3>%d absences non justifi�es</h3><ol>""" % (etud['nomprenom'], DateISOtoDMY(datedebut), len(absnonjust)))
        def matin(x):
            if x:
                return 'apr�s midi'
            else:
                return 'matin'
        def descr_exams(a):
            if not a.has_key('evals'):
                return ''
            ex = []
            for ev in a['evals']:
                mod = self.Notes.do_moduleimpl_withmodule_list(args={ 'moduleimpl_id' : ev['moduleimpl_id']})[0]
                ex.append( '<a href="Notes/moduleimpl_status?moduleimpl_id=%s">%s</a>'
                           % (mod['moduleimpl_id'], mod['module']['abbrev']))
            if ex:
                return ' ce jour: contr�les de: ' + ', '.join(ex)
            return ''
        
        for a in absnonjust:
            ex = descr_exams(a)
            H.append( '<li>%s (%s)%s</li>' % (a['jour'].strftime('%d/%m/%Y'), matin(a['matin']), ex) )
        H.append( """</ol><h3>%d absences justifi�es</h3><ol>""" % len(absjust),)
        for a in absjust:
            ex = descr_exams(a)
            H.append( '<li>%s (%s)%s</li>' % (a['jour'].strftime('%d/%m/%Y'), matin(a['matin']), ex) )
        H.append('</ol>')
        H.append("""<p style="top-margin: 1cm; font-size: small;">
        Si vous avez besoin d'autres formats pour les listes d'absences,
        envoyez un message sur la <a href="mailto:%s">liste</a>
        ou d�clarez un ticket sur <a href="%s">le site web</a>.</p>""" % (SCO_MAILING_LIST, SCO_WEBSITE) )
        return '\n'.join(H) + self.sco_footer(REQUEST)
    
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
    return """<table class="monthcalendar" border="0" cellpadding="0" cellspacing="0" frame="box">
     <tr bgcolor="%s"><td colspan="2" align="center">%s</td></tr>\n""" % (
	 color,MONTHNAMES_ABREV[month-1])

def MonthTableTail():
    return '</table>\n'

def MonthTableBody( month, year, events=[], halfday=0, trattributes='', work_saturday=False ):
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
            if day == 'D':
                monday = monday.next(7)
            if weeknum == current_weeknum and current_year == year and weekclass != 'wkend':
                weekclass += " currentweek"
            T.append( '<tr bgcolor="%s" class="%s" %s><td align="right">%d%s</td>%s</tr>'
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
            T.append( '<tr bgcolor="%s" class="wk%s" %s><td align="right">%d%s</td>' % (bgcolor, weekclass, attrs, d, day) )
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


    

