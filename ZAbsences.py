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
from sco_utils import *
#import notes_users
from TrivialFormulator import TrivialFormulator, TF
from gen_tables import GenTable
import scolars
import sco_excel
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
    def __init__(self,date=None,fmt='ddmmyyyy',work_saturday=False):
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


def semestregroupe_decode(semestregroupe):
    """return formsemestre_id, groupetd, groupeanglais, groupetp
    from variable passed in URL"""
    formsemestre_id, groupetd, groupeanglais, groupetp = tuple(semestregroupe.split('!'))
    return formsemestre_id, groupetd, groupeanglais, groupetp

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
    def AddAbsence(self, etudid, jour, matin, estjust, REQUEST, description=None):
        "Ajoute une absence dans la bd"
        if self._isFarFutur(jour):
            raise ScoValueError('date absence trop loin dans le futur !')
        estjust = _toboolean(estjust)
        matin = _toboolean(matin)
        cnx = self.GetDBConnexion()
        cursor = cnx.cursor()
        cursor.execute('insert into absences (etudid,jour,estabs,estjust,matin,description) values (%(etudid)s, %(jour)s, TRUE, %(estjust)s, %(matin)s, %(description)s )', vars())
        logdb(REQUEST, cnx, 'AddAbsence', etudid=etudid,
              msg='JOUR=%(jour)s,MATIN=%(matin)s,ESTJUST=%(estjust)s,description=%(description)s'%vars())
        cnx.commit()
        # Invalid cache (nbabs sur bulletins)
        self.Notes._inval_cache()

    security.declareProtected(ScoAbsChange, 'AddJustif')
    def AddJustif(self, etudid, jour, matin, REQUEST, description=None):
        "Ajoute un justificatif dans la base"
        if self._isFarFutur(jour):
            raise ScoValueError('date justificatif trop loin dans le futur !')
        matin = _toboolean(matin)
        cnx = self.GetDBConnexion()
        cursor = cnx.cursor()
        cursor.execute('insert into absences (etudid,jour,estabs,estjust,matin, description) values (%(etudid)s,%(jour)s, FALSE, TRUE, %(matin)s, %(description)s )', vars() )
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
        """Supprime les absences aux dates indiquées
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
        if dates:
            date0 = dates[0]
        else:
            date0 = None
        if len(dates) > 1:
            date1 = dates[1]
        else:
            date1 = None
        logdb(REQUEST, cnx, 'AnnuleAbsencesDatesNoJust', etudid=etudid,
              msg='%s - %s' % (date0,date1) )
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


    def _ListeAbsDate(self, etudid, beg_date, end_date):
        # Liste des absences et justifs entre deux dates
        cnx = self.GetDBConnexion()
        cursor = cnx.cursor()
        cursor.execute("""SELECT jour, matin, estabs, estjust, description FROM ABSENCES A 
     WHERE A.ETUDID = %(etudid)s
     AND A.jour >= %(beg_date)s 
     AND A.jour <= %(end_date)s 
         """, vars() )
        Abs = cursor.dictfetchall()
        log('ListeAbsDate: abs=%s' % Abs)
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
        log('R=%s' % R)
        return R
    
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
        A = cursor.dictfetchall()
        for a in A:
            a['description'] = self._GetAbsDescription(a, cursor=cursor)
        return A

    security.declareProtected(ScoView, 'ListeAbsNonJust')
    def ListeAbsNonJust(self, etudid, datedebut):
        "Liste des absences NON justifiees"
        cnx = self.GetDBConnexion()
        cursor = cnx.cursor()
        cursor.execute("""SELECT ETUDID, JOUR, MATIN FROM ABSENCES A 
    WHERE A.ETUDID = %(etudid)s
    AND A.estabs 
    AND A.jour > %(datedebut)s
    EXCEPT SELECT ETUDID, JOUR, MATIN FROM ABSENCES B 
    WHERE B.estjust 
    AND B.ETUDID = %(etudid)s
        """, vars() )
        A = cursor.dictfetchall()
        for a in A:
            a['description'] = self._GetAbsDescription(a, cursor=cursor)
        return A

    def _GetAbsDescription(self, a, cursor=None):
        "Description associee a l'absence"
        if not cursor:
            cnx = self.GetDBConnexion()
            cursor = cnx.cursor()
        a = a.copy()
        a['jour'] = a['jour'].date
        if a['matin']: # devrait etre booleen... :-(
            a['matin'] = True
        else:
            a['matin'] = False
        cursor.execute("""select * from absences where etudid=%(etudid)s and jour=%(jour)s and matin=%(matin)s order by entry_date desc""", a)
        A = cursor.dictfetchall()
        for a in A:
            if a['description']:
                return a['description']
        return None

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
        A = cursor.dictfetchall()
        for a in A:
            a['description'] = self._GetAbsDescription(a, cursor=cursor)
        return A

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
        A = cursor.dictfetchall()
        for a in A:
            a['description'] = self._GetAbsDescription(a, cursor=cursor)
        return A

    security.declareProtected(ScoAbsChange, 'doSignaleAbsenceGrHebdo')
    def doSignaleAbsenceGrHebdo(self, abslist=[],
                                datedebut=None, datefin=None, etudids=[],
                                destination=None, REQUEST=None):
        """Enregistre absences hebdo. Efface les anciennes absences et
        signale les nouvelles.
        abslist : liste etudid:date:ampm des absences signalees
        etudids : liste des etudids concernes
        datedebut, datefin: dates (ISO) de la semaine        
        """
        if etudids:
            etudids = etudids.split(',')
        else:
            etudids = []
        H = [ self.sco_header(REQUEST,page_title='Absences') ]
        footer = self.sco_footer(REQUEST)
        if not etudids:
            return '\n'.join(H) + '<h3>Rien à ajouter !</h3>' + footer
        
        # 1- Efface les absences
        for etudid in etudids:
            self.AnnuleAbsencesPeriodNoJust(etudid, datedebut, datefin, REQUEST) 
        
        # 2- Ajoute les absences        
        self._add_abslist(abslist, REQUEST)

        H.append('<h3>Absences ajoutées</h3>')
        if not destination:
            destination = REQUEST.URL1
        H.append('<p><a class="stdlink" href="%s">continuer</a></p>'%destination)
        return '\n'.join(H) + footer

    security.declareProtected(ScoAbsChange, 'doSignaleAbsenceGrSemestre')
    def doSignaleAbsenceGrSemestre(self, abslist=[],
                                   dates=[], etudids=[],
                                   destination=None, REQUEST=None):
        """Enregistre absences aux dates indiquees (abslist et dates).
        dates est une liste de dates ISO (séparées par des ',').
        Efface les absences aux dates indiquées par dates, et ajoute
        celles de abslist.
        """
        etudids = etudids.split(',')
        dates = dates.split(',')
        H = [ self.sco_header(REQUEST,page_title='Absences') ]
        footer = self.sco_footer(REQUEST)
        if not etudids or not dates:
            return '\n'.join(H) + '<h3>Rien à ajouter !</h3>' + footer
        # 1- Efface les absences
        for etudid in etudids:
            self.AnnuleAbsencesDatesNoJust(etudid, dates, REQUEST) 
        
        # 2- Ajoute les absences
        self._add_abslist(abslist, REQUEST)

        H.append('<h3>Absences ajoutées</h3>')
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
            year = self.AnneeScolaire(REQUEST)
        sems = self.Notes.do_formsemestre_list()
        if not sems:
            js = ''
        else:
            js = 'onmouseover="highlightweek(this);" onmouseout="deselectweeks();" onclick="wclick(this);"'
        C = self.YearTable(int(year), dayattributes=js)
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
        formsemestre_id, groupetd, groupeanglais, groupetp = semestregroupe_decode(semestregroupe)
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
              <form action="doSignaleAbsenceGrHebdo" method="post" action="%s">              
              """ % (groupetd, groupeanglais, groupetp, sem['titre_num'], datelundi, REQUEST.URL0) ]
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
        """Saisie des absences sur une journée sur un semestre
        (ou intervalle de dates) entier"""
        formsemestre_id, groupetd, groupeanglais, groupetp = semestregroupe_decode(semestregroupe)
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
        #
        colnames = [ str(x) for x in dates ]
        dates = [ x.ISO() for x in dates ]
        dayname = self.day_names()[jourdebut.weekday]
        
        H = [ self.sco_header(page_title='Saisie des absences',
                              no_side_bar=1,REQUEST=REQUEST),
              """<table border="0" cellspacing="16"><tr><td>
              <h2>Saisie des absences pour le groupe %s %s %s de %s, 
              les %s</h2>
              <p>
              <a href="SignaleAbsenceGrSemestre?datedebut=%s&datefin=%s&semestregroupe=%s&destination=%s&nbweeks=%d">%s</a>
              <form action="doSignaleAbsenceGrSemestre" method="post">              
              """ % (groupetd, groupeanglais, groupetp, sem['titre_num'],
                     dayname,
                     datedebut, datefin, semestregroupe, destination, nwl, msg) ]
        #
        etuds = self.getEtudInfoGroupe(formsemestre_id,groupetd,groupeanglais,groupetp)
        H += self._gen_form_saisie_groupe(etuds, colnames, dates, destination, dayname)
        H.append(self.sco_footer(REQUEST))
        return '\n'.join(H)
    
    def _gen_form_saisie_groupe(self, etuds, colnames, dates, destination='', dayname=''):
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
        i=1
        for etud in etuds:
            i += 1
            etudid = etud['etudid']
            # UE capitalisee dans semestre courant ?
            cap = []
            if etud['cursem']:
                nt = self.Notes._getNotesCache().get_NotesTable(self.Notes, etud['cursem']['formsemestre_id'])
                for ue in nt.get_ues():
                    status = nt.get_etud_ue_status(etudid, ue['ue_id'])
                    if status['is_capitalized']:
                        cap.append(ue['acronyme'])
            if cap:
                capstr = ' <span class="capstr">(%s cap.)</span>' % ', '.join(cap)
            else:
                capstr = ''
            # XXX
            if etudid == '339691':
                log('\n****\netud=%s\n\n' % etud)
                #log('\n****\netud=%s\ncap=%s\nues=%s\n\n'%(etud, cap,nt.get_ues()))
            #
            bgcolor = ('bgcolor="#ffffff"', 'bgcolor="#ffffff"', 'bgcolor="#dfdfdf"')[i%3]
            matin_bgcolor = ('bgcolor="#e1f7ff"', 'bgcolor="#e1f7ff"', 'bgcolor="#c1efff"')[i%3]
            H.append('<tr %s><td><b><a class="discretelink" href="ficheEtud?etudid=%s" target="new">%s</a></b>%s</td>'
                     % (bgcolor, etudid, etud['nomprenom'], capstr))
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
        <p class="help">Les cases cochées correspondent à des absences.
        Les absences saisies ne sont pas justifiées (sauf si un justificatif a été entré
        par ailleurs).
        </p><p class="help">Si vous "décochez" une case,  l'absence correspondante sera supprimée.
        </p>
        """ % destination)
        return H
        
    security.declareProtected(ScoView, 'ListeAbsEtud')
    def ListeAbsEtud(self, etudid, with_evals=True, format='html',
                     absjust_only=0, REQUEST=None):
        "Liste des absences d'un étudiant sur l'année en cours"
        datedebut = '%s-08-31' % self.AnneeScolaire(REQUEST)
        #datefin = '%s-08-31' % (self.AnneeScolaire(REQUEST)+1)
        absjust = self.ListeAbsJust( etudid=etudid, datedebut=datedebut)
        absnonjust = self.ListeAbsNonJust(etudid=etudid, datedebut=datedebut)
        absjust_only = int(absjust_only) # si vrai, table absjust seule (export xls ou pdf)
        # examens ces jours là ?
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
        H.append( """<h2>Absences de %s (à partir du %s)</h2>"""
                  % (etud['nomprenom'], DateISOtoDMY(datedebut)))
        
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
                           % (mod['moduleimpl_id'], mod['module']['abbrev']))
                else:
                    ex.append(mod['module']['abbrev'])
            if ex:
                return ' ce jour: contrôles de: ' + ', '.join(ex)
            return ''

        # ajoute date formattee et exams
        for L in (absnonjust, absjust):
            for a in L:
                if with_evals:
                    a['exams'] = descr_exams(a)
                a['datedmy'] = a['jour'].strftime('%d/%m/%Y')
                a['matin_o'] = a['matin']
                a['matin'] = matin(a['matin'])
                a['description'] = a['description'] or ''
        # ajoute lien pour justifier
        if format == 'html':
            for a in absnonjust:
                a['justlink'] = '<em>justifier</em>'
                a['_justlink_target'] = 'doJustifAbsence?etudid=%s&datedebut=%s&datefin=%s&demijournee=%s'%(etudid, a['datedmy'], a['datedmy'], a['matin_o'])
        #
        titles={'datedmy' : 'Date', 'matin' : '', 'exams' : 'Examens', 'justlink' : '', 'description' : 'Raison' }
        columns_ids=['datedmy', 'matin']
        if with_evals:
            columns_ids.append('exams')
            
        columns_ids.append('description')

        if format == 'html':
            columns_ids.append('justlink')
        
        if len(absnonjust):
            H.append('<h3>%d absences non justifiées:</h3>' % len(absnonjust))
            tab = GenTable( titles=titles, columns_ids=columns_ids, rows = absnonjust,
                            html_class='gt_table table_leftalign',
                            base_url = '%s?etudid=%s&absjust_only=0' % (REQUEST.URL0, etudid),
                            filename='abs_'+make_filename(etud['nomprenom']),
                            caption='Absences non justifiées de %(nomprenom)s' % etud,
                            preferences=self.get_preferences())
            if format != 'html' and absjust_only == 0:
                return tab.make_page(self, format=format, REQUEST=REQUEST)
            H.append( tab.html() )
        else:
            H.append( """<h3>Pas d'absences non justifiées</h3>""")
            
        if len(absjust):
            H.append( """<h3>%d absences justifiées:</h3>""" % len(absjust),)
            tab = GenTable( titles=titles, columns_ids=columns_ids, rows = absjust,
                            html_class='gt_table table_leftalign',
                            base_url = '%s?etudid=%s&absjust_only=1' % (REQUEST.URL0, etudid),
                            filename='absjust_'+make_filename(etud['nomprenom']),
                            caption='Absences justifiées de %(nomprenom)s' % etud,
                            preferences=self.get_preferences())
            if format != 'html' and absjust_only:
                return tab.make_page(self, format=format, REQUEST=REQUEST)
            H.append( tab.html() )
        else:
            H.append( """<h3>Pas d'absences justifiées</h3>""")
        H.append("""<p style="top-margin: 1cm; font-size: small;">
        Si vous avez besoin d'autres formats pour les listes d'absences,
        envoyez un message sur la <a href="mailto:%s">liste</a>
        ou déclarez un ticket sur <a href="%s">le site web</a>.</p>""" % (SCO_DEVEL_LIST, SCO_WEBSITE) )
        return '\n'.join(H) + self.sco_footer(REQUEST)

    security.declareProtected(ScoView, 'EtatAbsencesGr') # ported from dtml
    def EtatAbsencesGr(self, semestregroupe, debut, fin, format='html', formsemestre_id=None, REQUEST=None): 
        """Liste les absences d'un groupe
        """
        # NB: formsemestre_id passed in semestregroupe (historical) but also
        # in formsemestre_id in order to display page header.
        formsemestre_id_sg, groupetd, groupeanglais, groupetp = semestregroupe_decode(semestregroupe)
        if not formsemestre_id:
            formsemestre_id = formsemestre_id_sg
        if formsemestre_id !=  formsemestre_id_sg:
            raise ValueError('inconsistent formsemestre_id !')
        datedebut = self.DateDDMMYYYY2ISO(debut)
        datefin = self.DateDDMMYYYY2ISO(fin)
        #
        sem = self.Notes.do_formsemestre_list({'formsemestre_id':formsemestre_id})[0]
        # Construit tableau (etudid, statut, nomprenom, nbJust, nbNonJust, NbTotal)
        etuds = self.getEtudInfoGroupe(formsemestre_id,groupetd,groupeanglais,groupetp)
        T = []
        for etud in etuds:
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
                        } )
            if s['ins']['etat'] == 'D':
                T[-1]['_css_row_class'] = 'etuddem'
                T[-1]['nomprenom'] += ' (dem)'
        columns_ids = ['nomprenom', 'nbabsjust', 'nbabsnonjust', 'nbabs']
        title = 'Etat des absences du groupe %s %s %s' % (groupetd, groupeanglais, groupetp)
        if format == 'xls' or format == 'xml':
            columns_ids = ['etudid'] + columns_ids
        tab =GenTable( columns_ids=columns_ids, rows=T,  
                       preferences=self.get_preferences(formsemestre_id),
                       titles={'etatincursem': 'Etat', 'nomprenom':'Nom', 'nbabsjust':'Justifiées',
                               'nbabsnonjust' : 'Non justifiées', 'nbabs' : 'Total' },
                       html_sortable=True,
                       html_class='gt_table table_leftalign',
                       html_header=self.sco_header(REQUEST, page_title=title,
                                                   javascripts=['calendarDateInput_js']),

                       html_title=self.Notes.html_sem_header(REQUEST, '%s' % title, sem, 
                                                                with_page_header=False) 
                       +  '<p>Période du %s au %s (nombre de <b>demi-journées</b>)<br/>' % (debut, fin),
                       
                       base_url = '%s?semestregroupe=%s&debut=%s&fin=%s' % (REQUEST.URL0, semestregroupe,debut, fin),
                       filename='etat_abs__'+make_filename('%s %s %s de %s'%(groupetd, groupeanglais, groupetp, sem['titreannee'])),
                       caption=title,
                       html_next_section="""</table>
<p class="help">
Cliquez sur un nom pour afficher le calendrier des absences<br/>
ou entrez une date pour visualiser les absents un jour donné&nbsp;:
</p>
<form action="EtatAbsencesDate" method="get" action="%s">
<input type="hidden" name="semestregroupe" value="%s">
<script>DateInput('date', true, 'DD/MM/YYYY')</script>
<input type="submit" name="" value="visualiser les absences">
</form>
                        """ % (REQUEST.URL0,semestregroupe))
        return tab.make_page(self, format=format, REQUEST=REQUEST)
    
    # ----- Gestion des "billets d'absence": signalement par les etudiants eux mêmes (à travers le portail)
    security.declareProtected(ScoAbsAddBillet, 'AddBilletAbsence')
    def AddBilletAbsence(self, begin, end, description, etudid=False, code_nip=None, code_ine=None, REQUEST=None, xml_reply=True ):
        """Memorise un "billet"
        begin et end sont au format ISO (eg "1999-01-08 04:05:06")
        """
        # check etudid
        etuds = self.getEtudInfo(etudid=etudid, code_nip=code_nip, REQUEST=REQUEST)        
        if not etuds:
            return self.log_unknown_etud(REQUEST=REQUEST)
        etud = etuds[0]
        # check dates
        begin_date = ParseDateTimeUTC(begin) # may raises ValueError
        end_date = ParseDateTimeUTC(end)
        if begin_date > end_date:
            raise ValueError('invalid dates')
        #
        cnx = self.GetDBConnexion()
        billet_id = billet_absence_create( cnx, { 'etudid' : etud['etudid'], 
                                                  'abs_begin' : begin, 'abs_end' : end,
                                                  'description' : description,
                                                  'etat' : 0 } )
        if xml_reply:
            if REQUEST:
                REQUEST.RESPONSE.setHeader('Content-type', XML_MIMETYPE)
            doc = jaxml.XML_document( encoding=SCO_ENCODING )
            doc.billet(id=billet_id)
            return repr(doc)
        else:
            return billet_id

    security.declareProtected(ScoAbsAddBillet, 'AddBilletAbsence')
    def AddBilletAbsenceForm(self, etudid, REQUEST=None):
        """Formulaire ajout billet (pour tests seulement, le vrai formulaire accessible aux etudiants
        étant sur le portail étudiant).
        """
        etud = self.getEtudInfo(etudid=etudid, filled=1, REQUEST=REQUEST)[0]
        H = [ self.sco_header(REQUEST,page_title="Billet d'absence de %s" % etud['nomprenom'], javascripts=['calendarDateInput_js']) ]
        tf = TrivialFormulator(
            REQUEST.URL0, REQUEST.form, 
            (('etudid',  { 'input_type' : 'hidden' }),
             ('begin', { 'input_type' : 'date' }),
             ('end', { 'input_type' : 'date' }),
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
            self.AddBilletAbsence(begin, end, tf[2]['description'], etudid=etudid, xml_reply=False)
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
                b['etat_str'] = 'à traiter'
                b['_etat_str_target'] = 'ProcessBilletAbsenceForm?billet_id=%s&estjust=0' % b['billet_id']
                if etud:
                    b['_etat_str_target'] += '&etudid=%s' % etud['etudid']
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
        return self.listeBilletsEtud(etudid, REQUEST=REQUEST, format='xml')

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

    def _ProcessBilletAbsence(self, billet, estjust, description, REQUEST):
        """Traite un billet: ajoute absence(s) et éventuellement justificatifs,
        et change l'état du billet à 1.
        NB: actuellement, les heures ne sont utilisées que pour déterminer si matin et/ou après midi.
        """
        cnx = self.GetDBConnexion()
        log('billet=%s' % billet)
        if billet['etat'] != 0:
            log('billet deja traité !')
            return -1
        n = 0 # nombre de demi-journées d'absence ajoutées
        # 1-- ajout des absences (et justifs)
        datedebut = billet['abs_begin'].strftime('%d/%m/%Y')
        datefin = billet['abs_end'].strftime('%d/%m/%Y')
        dates = self.DateRangeISO( datedebut, datefin )
        # commence apres midi ?
        if dates and billet['abs_begin'].hour > 11:
            self.AddAbsence(billet['etudid'], dates[0], 0, estjust, REQUEST, description=description)
            n += 1
            dates = dates[1:]
        # termine matin ?
        if dates and billet['abs_end'].hour < 12:
            self.AddAbsence(billet['etudid'], dates[-1], 1, estjust, REQUEST, description=description)
            n += 1
            dates = dates[:-1]
        
        for jour in dates:
            self.AddAbsence(billet['etudid'], jour, 0, estjust, REQUEST, description=description)
            self.AddAbsence(billet['etudid'], jour, 1, estjust, REQUEST, description=description)
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
                           'etudid' : etudid},
            submitlabel = 'Enregistrer ces absences')
        if tf[0] == 0:
            tab = self._tableBillets([billet], etud=etud)
            H.append(tab.html())
            F = '<p><a class="stdlink" href="listeBillets">Liste de tous les billets en attente</a></p>' + self.sco_footer(REQUEST)
            return '\n'.join(H) + '<br/>' +  tf[1] + F
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
        etud = self.getEtudInfo(REQUEST=REQUEST)[0]
        exp = re.compile('^(\d{4})\D?(0[1-9]|1[0-2])\D?([12]\d|0[1-9]|3[01])$')
        if not exp.match(beg_date):
            raise ScoValueError('invalid date: %s' % beg_date)
        if not exp.match(end_date):
            raise ScoValueError('invalid date: %s' % end_date)
        
        Abs = self._ListeAbsDate(etud['etudid'], beg_date, end_date)
        
        REQUEST.RESPONSE.setHeader('Content-type', XML_MIMETYPE)
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
        return repr(doc)

_billet_absenceEditor = EditableTable(
    'billet_absence',
    'billet_id',
    ('billet_id', 'etudid', 'abs_begin', 'abs_end', 'description', 'etat', 'entry_date'),
    sortkey='entry_date desc'
)

billet_absence_create = _billet_absenceEditor.create
billet_absence_delete = _billet_absenceEditor.delete
billet_absence_list = _billet_absenceEditor.list
billet_absence_edit = _billet_absenceEditor.edit

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
    log('XXX events=%s' % events)
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
                cc.append( '<td bgcolor="%s">' % color )
            else:
                cc.append( '<td>' )
            if href:
                cc.append( '<a href="%s">' % href )
            elif descr:
                cc.append( '<a title="%s">' % descr )
            
            if legend or d == 1:
                n = 8-len(legend) # pad to 8 cars
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
                    cc.append( '<td bgcolor="%s">'
                               % (color))
                else:
                    cc.append( '<td>'  )
                if href:
                    cc.append( '<a href="%s">' % href )
                elif descr:
                    cc.append( '<a title="%s">' % descr )
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


    

