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

"""Site Scolarite pour d�partement IUT
"""

import time, string, glob

# Zope modules:
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
from sco_exceptions import *
from sco_utils import *
from ScolarRolesNames import *
from notesdb import *
from notes_log import log
from scolog import logdb
import scolars
from scolars import format_nom, format_prenom, format_sexe, format_lycee
from scolars import format_telephone, format_pays
from TrivialFormulator import TrivialFormulator, TF
import sco_excel
import imageresize

import ZNotes, ZAbsences, ZEntreprises, ZScoUsers
import ImportScolars
from VERSION import SCOVERSION, SCONEWS

import Products.ZPsycopgDA.DA

# XML generation package (apt-get install jaxml)
import jaxml

# ---------------

class ZScolar(ObjectManager,
              PropertyManager,
              RoleManager,
              Item,
              Persistent,
              Implicit
              ):

    "ZScolar object"

    meta_type = 'ZScolar'
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
    def __init__(self, id, title, db_cnx_string=None, mail_host='MailHost'):
	"initialise a new instance of ZScolar"
        self.id = id
	self.title = title
        self._db_cnx_string = db_cnx_string        
        self._cnx = None
        self.mail_host = mail_host
        # --- add editable DTML documents:
        self.defaultDocFile('sidebar_dept',
                            'barre gauche (partie haute)',
                            'sidebar_dept')
        
        # --- add DB connector
        id = 'DB'
        da = Products.ZPsycopgDA.DA.Connection(
            id, 'DB connector', db_cnx_string, False,
            check=1, tilevel=2, encoding='iso8859-15')
        self._setObject(id, da)
        # --- add Scousers instance
        id = 'Users'
        obj = ZScoUsers.ZScoUsers( id, 'Gestion utilisateurs zope')
	self._setObject(id, obj)        
        # --- add Notes instance
        id = 'Notes'
        obj = ZNotes.ZNotes( id, 'Gestion Notes')
	self._setObject(id, obj)
        # --- add Absences instance
        id = 'Absences'
        obj = ZAbsences.ZAbsences(id, 'Gestion absences')
        self._setObject(id, obj)
        # --- add Entreprises instance
        id = 'Entreprises'
        obj = ZEntreprises.ZEntreprises(id, 'Suivi entreprises')
        self._setObject(id, obj)

    # The for used to edit this object
    def manage_editZScolar(self, title, RESPONSE=None):
        "Changes the instance values"
        self.title = title
        self._p_changed = 1
        RESPONSE.redirect('manage_editForm')

    security.declareProtected('ScoView', 'essai')
    def essai(self, REQUEST=None):
        """essai: header / body / footer"""
        b = '<p>Hello, World !</p><br>'
        raise ScoValueError('essai exception !', dest_url='totoro', REQUEST=REQUEST)
        cnx = self.GetDBConnexion()
        b += str(dir(cnx))
        #cursor = cnx.cursor()
        #cursor.execute("select * from notes_formations")
        #b += str(cursor.fetchall())
        #b = self.Notes.gloups()
        raise NoteProcessError('test exception !')
        return self.sco_header(self,REQUEST)+ b + self.sco_footer(self,REQUEST)
        #return self.objectIds()
        #return sendCSVFile(REQUEST, "toto;titi", "toto.csv", "toto.csv")
        REQUEST.RESPONSE.setHeader('Content-type', 'text/comma-separated-values')
        return ('Content-type: text/comma-separated-values; name="listeTD.csv"\n'
                +'Content-disposition: filename="listeTD.csv"\n'
                +'Title: Groupe\n'
                +'\n' + 'NOM;PRENOM;ETAT\n')    
        
    # Ajout (dans l'instance) d'un dtml modifiable par Zope
    def defaultDocFile(self,id,title,file):
        f=open(file_path+'/dtml/'+file+'.dtml')     
        file=f.read()     
        f.close()     
        self.manage_addDTMLMethod(id,title,file)

    # Ajout des JavaScripts 
    security.declareProtected('ScoView', 'groupmgr_js')
    groupmgr_js = DTMLFile('JavaScripts/groupmgr_js', globals())

    security.declareProtected('ScoView', 'prototype_1_4_0_js')
    prototype_1_4_0_js = DTMLFile('JavaScripts/prototype_1_4_0_js', globals())

    security.declareProtected('ScoView', 'rico_js')
    rico_js = DTMLFile('JavaScripts/rico_js', globals())

    security.declareProtected('ScoView', 'sorttable_js')
    sorttable_js = DTMLFile('JavaScripts/sorttable_js', globals())

    security.declareProtected('ScoView', 'menu_js')
    menu_js = DTMLFile('JavaScripts/menu_js', globals())

    security.declareProtected('ScoView', 'menu_css')
    menu_css = DTMLFile('JavaScripts/menu_css', globals())

    
    security.declareProtected('ScoView', 'ScoURL')
    def ScoURL(self):
        "base URL for this sco instance"
        return self.absolute_url()

    security.declareProtected('ScoView', 'StyleURL')
    def StyleURL(self):
        "base URL for CSS style sheet"
        return self.gtrintranetstyle.absolute_url()


    security.declareProtected('ScoView', 'sco_header')
    sco_header = DTMLFile('dtml/sco_header', globals())
    security.declareProtected('ScoView', 'sco_footer')
    sco_footer = DTMLFile('dtml/sco_footer', globals())
    security.declareProtected('ScoView', 'menus_bandeau')
    menus_bandeau = DTMLFile('dtml/menus_bandeau', globals())

    # --------------------------------------------------------------------
    #
    #    GESTION DE LA BD
    #
    # --------------------------------------------------------------------
    security.declareProtected('Change DTML Documents', 'GetDBConnexion')
    def GetDBConnexion(self,new=False):
        # should not be published (but used from contained classes via acquisition)
        if not self._db_cnx_string:
            raise ScolarError('invalid sgbd connexion string')
        cnx = self.DB().db # a database adaptor called DB must exists        
        cnx.commit() # sync !
        return cnx
#         if new:
#             log('GetDBConnexion: requested new connexion')
#             return DB.connect( self._db_cnx_string )        
#         if self._cnx:
#             self._cnx.commit() # terminate transaction
#             return _cnx
#         log('GetDBConnexion: opening new db connexion')
#         self._cnx = DB.connect( self._db_cnx_string )
#         return self._cnx

#    def g(self):
#        "debug"
#        return '<html><body>voila:' + str(self.DB) + '<br>' + str(self.DB()) + '<br>' + str(dir(self.DB().db)) + '</body></html>'

    security.declareProtected(ScoView, "TrivialFormulator")
    def TrivialFormulator(self, form_url, values, formdescription=(), initvalues={},
                          method='POST', submitlabel='OK', formid='tf',
                          cancelbutton=None,
                          readonly=False ):
        "generator/validator of simple forms"
        return TrivialFormulator(
            form_url, values,
            formdescription=formdescription,
            initvalues=initvalues,
            method=method, submitlabel=submitlabel, formid=formid,
            cancelbutton=cancelbutton, readonly=readonly )
    # --------------------------------------------------------------------
    #
    #    SCOLARITE (top level)
    #
    # --------------------------------------------------------------------
    # used to view content of the object
    #security.declareProtected('ScoView', 'index_html')
    #index_html = DTMLFile('dtml/index_html', globals())
    security.declareProtected('ScoView', 'about')
    def about(self, REQUEST):
        "version info"
        H = [ """<h2>Syst�me de gestion scolarit�</h2>
        <p>&copy; Emmanuel Viennet 1997-2006</p>
        <p>Version %s (subversion %s)</p>
        """ % (SCOVERSION, get_svn_version(file_path)) ]
        H.append('<p>Logiciel �crit en <a href="http://www.python.org">Python</a> pour la plate-forme <a href="http://www.zope.org">Zope</a>.</p><p>Utilise <a href="http://reportlab.org/">ReportLab</a> pour g�n�rer les documents PDF, et <a href="http://sourceforge.net/projects/pyexcelerator">pyExcelerator</a> pour le traitement des documents Excel.</p>')
        H.append( "<h2>Derni�res �volutions</h2>" + SCONEWS )
        H.append( '<div class="about-logo">' + self.img.borgne_img.tag() + ' <em>Au pays des aveugles...</em></div>' )
        d = ''
        # debug
        #import locale
        #g='gon�alves'
        # 
        #d = "<p>locale=%s, g=%s -> %s</p>"% (locale.getlocale(), g, g.lower() )
        return self.sco_header(self,REQUEST)+ '\n'.join(H) + d + self.sco_footer(self,REQUEST)

    security.declareProtected(ScoView, 'AnneeScolaire')
    def AnneeScolaire(self):
        "annee de debut de l'annee scolaire courante"
        t = time.localtime()
        year, month = t[0], t[1]
        if month < 8: # le "pivot" est le 1er aout
            year = year - 1
        return year

    security.declareProtected(ScoView, 'DateISO2DDMMYYYY')
    def DateISO2DDMMYYYY(self,isodate):
        "Convert  date from ISO string to dd/mm/yyyy"
        # was a Python Script. Still used by some old dtml code.
        return DateISOtoDMY(isodate)
    
    security.declareProtected(ScoView, 'DateDDMMYYYY2ISO')
    def DateDDMMYYYY2ISO(self,dmy):
        "Check date and convert to ISO string"
        return DateDMYtoISO(dmy)
        
    security.declareProtected(ScoView, 'formChercheEtud')
    def formChercheEtud(self,REQUEST):
        "form recherche par nom"
        return """<form action="chercheEtud" method="GET">
        <b>Rechercher un &eacute;tudiant par nom&nbsp;: </b>
        <input type="text" name="expnom" width=12 value="">
        <input type="submit" value="Chercher">
        <br>(entrer une partie du nom ou une regexp)
        </form>"""
    
    security.declareProtected(ScoView, 'formChoixSemestreGroupe')
    def formChoixSemestreGroupe(self):
        "partie de formulaire pour le choix d'un semestre et d'un groupe"
        # XXX assez primitif, a ameliorer
        sems = self.Notes.do_formsemestre_list()
        H = ['<select name="semestregroupe">']
        for sem in sems:
            formsemestre_id = sem['formsemestre_id']
            gr_td,gr_tp,gr_anglais = self.Notes.do_formsemestre_inscription_listegroupes(formsemestre_id=formsemestre_id)
            for gr in gr_td:
                tmpl = '<option value="%s!%s!!">%s %s</option>'
                H.append( tmpl %(formsemestre_id,gr,sem['titre'],gr))
            for gr in gr_anglais:
                tmpl = '<option value="%s!!!%s">%s %s</option>'
                H.append( tmpl %(formsemestre_id,gr,sem['titre'],gr))
            for gr in gr_tp:
                tmpl = '<option value="%s!!%s!">%s %s</option>'
                H.append( tmpl %(formsemestre_id,gr,sem['titre'],gr))

        H.append('</select>')
        return '\n'.join(H)    

    # -----------------  BANDEAUX -------------------
    security.declareProtected('ScoView', 'sidebar')
    sidebar = DTMLFile('dtml/sidebar', globals())
    
    security.declareProtected('ScoView', 'showEtudLog')
    showEtudLog = DTMLFile('dtml/showEtudLog', globals())
    security.declareProtected('ScoView', 'listScoLog')
    def listScoLog(self,etudid):
        "liste des operations effectuees sur cet etudiant"
        cnx = self.GetDBConnexion()
        cursor = cnx.cursor()
        cursor.execute("select * from scolog where etudid=%(etudid)s ORDER BY DATE DESC",
                       {'etudid':etudid})
        return cursor.dictfetchall()
    #
    security.declareProtected('ScoView', 'getZopeUsers')
    def getZopeUsers(self):
        "liste des utilisateurs zope"
        return self.acl_users.getUserNames()

    # ----------  PAGE ACCUEIL (listes) --------------
    security.declareProtected('ScoView', 'index_html')
    def index_html(self,REQUEST=None):
        "page accueil sco"
        H = []
        # liste de toutes les sessions
        sems = self.Notes.do_formsemestre_list()
        now = time.strftime( '%Y-%m-%d' )
        # H.append('<p>listes du %s</p>' % now )
        cursems = []   # semestres "courants"
        othersems = [] # autres (anciens ou futurs)        
        for sem in sems:
            debut = DateDMYtoISO(sem['date_debut'])
            fin = DateDMYtoISO(sem['date_fin'])
            if debut <= now and now <= fin:
                cursems.append(sem)
            else:
                othersems.append(sem)
        # liste des fomsemestres "courants"
        H.append('<h2>Semestres en cours</h3>')
        for sem in cursems:
            H += self.make_listes_sem(sem, REQUEST)
        H.append('<h2>Semestres en pass�s ou futurs</h3>')
        for sem in othersems:
            H += self.make_listes_sem(sem, REQUEST)
        #
        authuser = REQUEST.AUTHENTICATED_USER
        if authuser.has_permission(ScoEtudInscrit,self):
            H.append('<hr><ul><li><a href="form_students_import_csv">importer de nouveaux �tudiants</a></li>')
            H.append('<li><a href="etudident_create_form">cr�er <em>un</em> nouvel �tudiant</a></li>')
            H.append('</ul>')
        #
        return self.sco_header(self,REQUEST)+'\n'.join(H)+self.sco_footer(self,REQUEST)

    # genere liste html pour acces aux groupes TD/TP/TA de ce semestre
    def make_listes_sem(self, sem, REQUEST):
        authuser = REQUEST.AUTHENTICATED_USER
        r = self.ScoURL() # root url
        H = []
        # -- prevoir si necessaire un moyen de chercher le vrai nom du
        #    responsable de formation.
        sem['responsable_name'] = sem['responsable_id'].lower().capitalize()
        #
        H.append('<h3>%(titre)s <span class="infostitresem">(%(date_debut)s - %(date_fin)s, %(responsable_name)s)</span></h3>' % sem )
        # cherche les groupes de ce semestre
        formsemestre_id = sem['formsemestre_id']
        gr_td,gr_tp,gr_anglais = self.Notes.do_formsemestre_inscription_listegroupes(formsemestre_id=formsemestre_id)
        #H.append( str(gr_td+gr_tp+gr_anglais) + '<p>')
        H.append('<ul>')            
        if gr_td:
            H.append('<li>Groupes de TD</li>')
            H.append('<ul>')
            for gr in gr_td:
                args = { 'formsemestre_id' : formsemestre_id, 'groupetd' : gr }
                ins = self.Notes.do_formsemestre_inscription_list( args=args )
                nb = len(ins) # nb etudiants
                H.append('<li><a href="%s/listegroupe?formsemestre_id=%s&groupetd=%s">groupe %s</a> (<a href="%s/listegroupe?formsemestre_id=%s&groupetd=%s&format=xls">format tableur</a>) <a href="%s/trombino?formsemestre_id=%s&groupetd=%s&etat=I">Trombinoscope</a> (%d �tudiants)</li>'%(r,formsemestre_id,gr,gr,r,formsemestre_id,gr,r,formsemestre_id,gr,nb))
            H.append('</ul>')
        if gr_anglais: 
            H.append('<li>Groupes d\'anglais</li>')
            H.append('<ul>')
            for gr in gr_anglais:
                args = { 'formsemestre_id' : formsemestre_id, 'groupeanglais' : gr }
                ins = self.Notes.do_formsemestre_inscription_list( args=args )
                nb = len(ins) # nb etudiants
                H.append('<li><a href="%s/listegroupe?formsemestre_id=%s&groupeanglais=%s">groupe %s</a> (<a href="%s/listegroupe?formsemestre_id=%s&groupeanglais=%s&format=xls">format tableur</a>) <a href="%s/trombino?formsemestre_id=%s&groupeanglais=%s&etat=I">Trombinoscope</a> (%d �tudiants)</li>'%(r,formsemestre_id,gr,gr,r,formsemestre_id,gr,r,formsemestre_id,gr,nb))
            H.append('</ul>')
        if gr_tp: 
            H.append('<li>Groupes de TP</li>')
            H.append('<ul>')
            for gr in gr_tp:
                args = { 'formsemestre_id' : formsemestre_id, 'groupetp' : gr }
                ins = self.Notes.do_formsemestre_inscription_list( args=args )
                nb = len(ins) # nb etudiants
                H.append('<li><a href="%s/listegroupe?formsemestre_id=%s&groupetp=%s">groupe %s</a> (<a href="%s/listegroupe?formsemestre_id=%s&groupetp=%s&format=xls">format tableur</a>) <a href="%s/trombino?formsemestre_id=%s&groupetp=%s&etat=I">Trombinoscope</a> (%d �tudiants)</li>'%(r,formsemestre_id,gr,gr,r,formsemestre_id,gr,r,formsemestre_id,gr,nb))
            H.append('</ul>')
        if len(gr_td) > 1:
            args = { 'formsemestre_id' : formsemestre_id }
            ins = self.Notes.do_formsemestre_inscription_list( args=args )
            nb = len(ins) # nb etudiants
            H.append('<li><a href="%s/listegroupe?formsemestre_id=%s">Tous les �tudiants de %s</a> (<a href="%s/listegroupe?formsemestre_id=%s&format=xls">format tableur</a>) <a href="%s/trombino?formsemestre_id=%s&etat=I">Trombinoscope</a> (%d �tudiants)</li>' % (r,formsemestre_id,sem['titre'],r,formsemestre_id,r,formsemestre_id,nb))
        # Si admin, lien changementde groupes
        if authuser.has_permission(ScoEtudChangeGroups,self):
            H.append('<li>Modifier les groupes de <a href="affectGroupes?formsemestre_id=%s&groupType=TD">TD</a>, <a href="affectGroupes?formsemestre_id=%s&groupType=TA">anglais</a>, <a href="affectGroupes?formsemestre_id=%s&groupType=TP">TP</a></li>' % (formsemestre_id,formsemestre_id,formsemestre_id))
        H.append('</ul>')
        return H

    security.declareProtected(ScoView, 'listegroupe')
    def listegroupe(self, 
                    formsemestre_id, REQUEST=None,
                    groupetd=None, groupetp=None, groupeanglais=None,
                    etat=None,
                    format='html' ):
        """liste etudiants inscrits dans ce semestre
        format: html, csv, xls, xml (XXX futur: pdf)
        """
        T, nomgroupe, ng, sem, nbdem = self._getlisteetud(formsemestre_id,
                                                   groupetd,groupetp,groupeanglais,etat )
        #
        if format == 'html':
            H = [ '<h2>Etudiants de %s %s</h2>' % (sem['titre'], ng) ]
            H.append('<table class="sortable" id="listegroupe">')
            H.append('<tr><th>Nom</th><th>Pr�nom</th><th>Groupe</th><th>Mail</th></tr>')
            for t in T:
                H.append( '<tr><td><a href="ficheEtud?etudid=%s">%s</a></td><td>%s</td><td>%s %s</td><td><a href="mailto:%s">%s</a></td></tr>' %
                          (t[2],t[0], t[1], t[5], t[4], t[3], t[3]) )
            H.append('</table>')
            if nbdem > 1:
                s = 's'
            else:
                s = ''
            H.append('<p>soit %d �tudiants inscrits et %d d�missionaire%s<br>' % (len(T)-nbdem,nbdem,s))
            amail=','.join([x[3] for x in T ])
            H.append('<a href="mailto:%s">envoyer un mail collectif au groupe %s</a></p>' % (amail,nomgroupe))
            return self.sco_header(self,REQUEST)+'\n'.join(H)+self.sco_footer(self,REQUEST)
        elif format == 'csv':
            Th = [ 'Nom', 'Pr�nom', 'Groupe', 'Etat', 'Mail' ]
            fs = [ (t[0], t[1], t[5], t[4], t[3]) for t in T ]
            CSV = CSV_LINESEP.join( [ CSV_FIELDSEP.join(x) for x in [Th]+fs ] )
            title = 'liste_%s' % nomgroupe
            filename = title + '.csv'
            return sendCSVFile(REQUEST,CSV, filename )
        elif format == 'xls':
            title = 'liste_%s' % nomgroupe
            xls = sco_excel.Excel_SimpleTable(
                titles= [ 'Nom', 'Pr�nom', 'Groupe', 'Etat', 'Mail' ],
                lines = [ (t[0], t[1], t[5], t[4], t[3]) for t in T ],
                SheetName = title )
            filename = title + '.xls'
            return sco_excel.sendExcelFile(REQUEST, xls, filename )
        elif format == 'xml':
            doc = jaxml.XML_document( encoding=SCO_ENCODING )
            if REQUEST:
                REQUEST.RESPONSE.setHeader('Content-type', XML_MIMETYPE)
            a = { 'formsemestre_id' : formsemestre_id }
            if groupetd:
                a['groupetd'] = groupetd
            if groupeanglais:
                a['groupeta'] = groupeanglais
            if groupetp:
                a['groupetp'] = groupetp
            if etat:
                a['etat'] = etat
            doc.groupe( **a )
            doc._push()
            for t in T:
                a = { 'etudid' : t[2],
                      'nom' : t[0], 'prenom' : t[1], 'groupe' : t[5],
                      'etat' : t[4], 'mail' : t[3] }
                doc._push()
                doc.etudiant(**a)
                doc._pop()
            doc._pop()
            return repr(doc)
        else:
            raise ValueError('unsupported format')

    security.declareProtected(ScoView,'trombino')
    def trombino(self,REQUEST,formsemestre_id,
                 groupetd=None, groupetp=None, groupeanglais=None, etat=None, nbcols=5):
        """Trombinoscope"""
        T, nomgroupe, ng, sem, nbdem = self._getlisteetud(formsemestre_id,
                                                          groupetd,groupetp,groupeanglais,etat )
        #
        nbcols = int(nbcols)
        H = [ '<h2>Etudiants de %s %s</h2>' % (sem['titre'], ng) ]
        H.append('<table width="100%">')
        i = 0
        for t in T:
            if i % nbcols == 0:
                H.append('<tr>')
            H.append('<td align="center">')
            foto = self.etudfoto(t[2],fototitle='fiche de '+ t[0],foto=t[6] )
            H.append('<a href="ficheEtud?etudid='+t[2]+'">'+foto+'</a>')
            H.append('<br>' + t[1] + '<br>' + t[0] )
            H.append('</td>')
            i += 1
            if i % nbcols == 0:
                H.append('</tr>')
        H.append('</table>')
        return self.sco_header(self,REQUEST)+'\n'.join(H)+self.sco_footer(self,REQUEST)

    def _getlisteetud(self, formsemestre_id,
                      groupetd=None, groupetp=None, groupeanglais=None, etat=None ):
        """utilise par listegroupe et trombino
        ( liste de tuples t,  nomgroupe, ng, sem, nbdem )
        """
        cnx = self.GetDBConnexion()
        sem = self.Notes.do_formsemestre_list( args={'formsemestre_id':formsemestre_id} )[0]
        args,nomgroupe=self._make_groupes_args(groupetd,groupetp,groupeanglais,
                                               etat)
        args['formsemestre_id'] = formsemestre_id
        ins = self.Notes.do_formsemestre_inscription_list( args=args )
        if nomgroupe:
            ng = 'groupe ' + nomgroupe
        else:
            ng = ''
        # --- recuperation infos sur les etudiants, tri
        T = []
        nbdem = 0 # nombre d'inscrits demissionnaires
        for i in ins:
            etud = scolars.etudident_list(cnx, {'etudid':i['etudid']})[0]
            t = [format_nom(etud['nom']), format_prenom(etud['prenom']), etud['etudid'],
                 scolars.getEmail(cnx,etud['etudid']), i['etat'],i['groupetd'],etud['foto']] 
            if t[4] == 'I':
                t[4] = '' # etudiant inscrit, ne l'indique pas dans la liste HTML
            elif t[4] == 'D':
                t[4] = '(dem.)'
                nbdem += 1
            T.append(t)
        T.sort() # sort by nom
        return T, nomgroupe, ng, sem, nbdem
    
    def _make_groupes_args(self,groupetd,groupetp,groupeanglais,etat):
        args = {}
        grs = []
        if groupetd:
            args['groupetd'] = groupetd
            grs.append(groupetd)
        if groupeanglais:
            args['groupeanglais'] = groupeanglais
            grs.append(groupeanglais)
        if groupetp:
            args['groupetp'] = groupetp
            grs.append(groupetp)
        nomgroupe = '/'.join(grs) # pour affichage dans le resultat
        if etat:
            args['etat'] = etat
        return args, nomgroupe
    
    security.declareProtected(ScoView,'getEtudInfoGroupe')
    def getEtudInfoGroupe(self, formsemestre_id,
                         groupetd=None, groupetp=None, groupeanglais=None,
                         etat=None ):
        """liste tri�e d'infos (dict) sur les etudiants du groupe indiqu�.
        Attention: peut etre lent, car plusieurs requetes SQL par etudiant !
        """
        cnx = self.GetDBConnexion()
        sem = self.Notes.do_formsemestre_list( args={'formsemestre_id':formsemestre_id} )[0]
        args,nomgroupe=self._make_groupes_args(groupetd,groupetp,groupeanglais,
                                               etat)
        args['formsemestre_id'] = formsemestre_id
        ins = self.Notes.do_formsemestre_inscription_list( args=args )
        etuds = []
        for i in ins:
            etud = self.getEtudInfo(i['etudid'],filled=True)[0]
            etuds.append(etud)
        # tri par nom
        etuds.sort( lambda x,y: cmp(x['nom'],y['nom']) )
        return etuds
        
    # -------------------------- INFOS SUR ETUDIANTS --------------------------
    security.declareProtected(ScoView, 'getEtudInfo')
    def getEtudInfo(self,etudid,filled=False):
        "infos sur un etudiant pour utilisation en Zope DTML"
        cnx = self.GetDBConnexion()
        etud = scolars.etudident_list(cnx,args={'etudid':etudid})
        if filled:
            self.fillEtudsInfo(etud)
        return etud

    #
    security.declareProtected(ScoView, 'nomprenom')
    def nomprenom(self, etud):
        "formatte sexe/nom/prenom pour affichages"
        return format_sexe(etud['sexe']) + ' ' + format_prenom(etud['prenom']) + ' ' + format_nom(etud['nom'])
    
    security.declareProtected(ScoView, "chercheEtud")
    chercheEtud = DTMLFile('dtml/chercheEtud', globals())
    security.declareProtected(ScoView, "chercheEtudsInfo")
    def chercheEtudsInfo(self, expnom, REQUEST):
        """recherche les etudiant correspondant a expnom
        et ramene liste de mappings utilisables en DTML.        
        """
        cnx = self.GetDBConnexion()
        expnom = expnom.upper() # les noms dans la BD sont en uppercase
        etuds = scolars.etudident_list(cnx, args={'nom':expnom}, test='~' )        
        self.fillEtudsInfo(etuds)
        return etuds

    security.declareProtected(ScoView, "fillEtudsInfo")
    def fillEtudsInfo(self,etuds):
        """etuds est une liste d'etudiants (mappings)
        Pour chaque etudiant, ajoute ou formatte les champs
        -> informations pour fiche etudiant ou listes diverses
        """
        cnx = self.GetDBConnexion()
        #open('/tmp/t','w').write( str(etuds) )
        for etud in etuds:
            etudid = etud['etudid']
            adrs = scolars.adresse_list(cnx, {'etudid':etudid})
            if not adrs:
                # certains "vieux" etudiants n'ont pas d'adresse
                adr = {}.fromkeys(scolars._adresseEditor.dbfields, '')
                adr['etudid'] = etudid
            else:
                adr = adrs[0]
                if len(adrs) > 1:
                    log('fillEtudsInfo: etudid=%d a %d adresses'%(etudid,len(adrs)))
            etud.update(adr)
            etud['nom'] = format_nom(etud['nom'])
            etud['prenom'] = format_nom(etud['prenom'])
            etud['sexe'] = format_sexe(etud['sexe'])
            etud['nomprenom'] = self.nomprenom(etud) # M. Pierre DUPONT
            if etud['sexe'] == 'M.':
                etud['ne'] = ''
            else:
                etud['ne'] = 'e'
            if etud['email']:
                etud['emaillink'] = '<a href="mailto:%s">%s</a>'%(etud['email'],etud['email'])
            else:
                etud['emaillink'] = '<em>(pas d\'adresse e-mail)</em>'
                    # Semestres dans lesquel il est inscrit
            ins = self.Notes.do_formsemestre_inscription_list({'etudid':etudid})
            etud['ins'] = ins
            now = time.strftime( '%Y-%m-%d' )
            sems = [] 
            cursem = None # semestre "courant" ou il est inscrit
            for i in ins:
                sem = self.Notes.do_formsemestre_list({'formsemestre_id':i['formsemestre_id']})[0]
                debut = DateDMYtoISO(sem['date_debut'])
                fin = DateDMYtoISO(sem['date_fin'])
                if debut <= now and now <= fin:
                    cursem = sem
                    curi = i
                sem['ins'] = i
                sems.append(sem)
            # tri les semestre par date de debut
            sems.sort( lambda x,y: cmp( y['date_debut'], x['date_debut'] ) )
            etud['sems'] = sems
            etud['cursem'] = cursem
            if cursem:
                etud['inscription'] = cursem['titre']
                etud['inscriptionstr'] = 'Inscrit en ' + cursem['titre']
                etud['inscription_formsemestre_id'] = cursem['formsemestre_id']
                etud['groupetd'] = curi['groupetd']
                etud['groupeanglais'] = curi['groupeanglais']
                etud['groupetp'] = curi['groupetp']
                etud['etatincursem'] = curi['etat']
            else:
                etud['inscription'] = 'pas inscrit'
                etud['inscriptionstr'] = etud['inscription']
                etud['inscription_formsemestre_id'] = None
                etud['groupetd'] = ''
                etud['groupeanglais'] = ''
                etud['groupetp'] = ''
                etud['etatincursem'] = '?'
            # situation et parcours
            etud['groupes'] = ' '.join( [etud['groupetd'],
                                         etud['groupeanglais'],etud['groupetp']] )
            etud['situation'], etud['parcours'] = self.descr_situation_etud(etudid,etud['ne'])
            # nettoyage champs souvents vides
            if etud['nomlycee']:
                etud['ilycee'] = 'Lyc�e ' + format_lycee(etud['nomlycee'])
                if etud['villelycee']:
                    etud['ilycee'] += ' (%s)' % etud['villelycee']
                etud['ilycee'] += '<br>'
            else:
                etud['ilycee'] = ''
            if etud['rapporteur'] or etud['commentaire']:
                etud['rap'] = 'Note du rapporteur'
                if etud['rapporteur']:
                    etud['rap'] += ' (%s)' % etud['rapporteur']
                etud['rap'] += ' :'
                if etud['commentaire']:
                    etud['rap'] += '<em>%s</em>' % etud['commentaire']
            else:
                etud['rap'] = "Pas d'informations sur les conditions d'admission."
            if etud['telephone']:
                etud['telephonestr'] = '<b>T�l.:</b> ' + format_telephone(etud['telephone'])
            else:
                etud['telephonestr'] = ''
            if etud['telephonemobile']:
                etud['telephonemobilestr'] = '<b>Mobile:</b> ' + format_telephone(etud['telephonemobile'])
            else:
                etud['telephonemobilestr'] = ''

    security.declareProtected(ScoView, 'XMLgetEtudInfos')
    def XMLgetEtudInfos(self, etudid, REQUEST):
        "Donne les informatons sur un etudiant"
        doc = jaxml.XML_document( encoding=SCO_ENCODING )
        REQUEST.RESPONSE.setHeader('Content-type', XML_MIMETYPE)
        cnx = self.GetDBConnexion()
        etud = scolars.etudident_list(cnx, {'etudid':etudid})[0]
        self.fillEtudsInfo([etud])
        doc.etudiant( etudid=etudid,
                      nom=etud['nom'],
                      prenom=etud['prenom'],
                      sexe=etud['sexe'],
                      nomprenom=etud['nomprenom'],
                      email=etud['email'])
        doc._push()
        sem = etud['cursem']
        if sem:
            doc._push()
            doc.insemestre( current='1',
                            formsemestre_id=sem['formsemestre_id'],
                            date_debut=DateDMYtoISO(sem['date_debut']),
                            date_fin=DateDMYtoISO(sem['date_fin']),
                            groupetd=sem['ins']['groupetd'],
                            groupeta=sem['ins']['groupeanglais'],
                            groupetp=sem['ins']['groupetp'],
                            etat=sem['ins']['etat']
                            )
            doc._pop()
        for sem in etud['sems']:
            if sem != etud['cursem']:
                doc._push()
                doc.insemestre( 
                    formsemestre_id=sem['formsemestre_id'],
                    date_debut=DateDMYtoISO(sem['date_debut']),
                    date_fin=DateDMYtoISO(sem['date_fin']),
                    groupetd=sem['ins']['groupetd'],
                    groupeta=sem['ins']['groupeanglais'],
                    groupetp=sem['ins']['groupetp'],
                    etat=sem['ins']['etat']
                    )
                doc._pop()
        doc._pop()
        return repr(doc)

    # -------------------------- FICHE ETUDIANT --------------------------
    security.declareProtected(ScoView, 'ficheEtud')
    def ficheEtud(self,etudid,REQUEST=None):
        "fiche d'informations sur un etudiant"
        authuser = REQUEST.AUTHENTICATED_USER
        cnx = self.GetDBConnexion()
        etud = scolars.etudident_list(cnx, {'etudid':etudid})[0]
        self.fillEtudsInfo([etud])
        #
        info = etud
        info['authuser'] = authuser
        info['etudfoto'] = self.etudfoto(etudid,foto=etud['foto'])
        if ((not info['domicile']) and (not info['codepostaldomicile'])
            and (not info['villedomicile'])):
            info['domicile'] ='<em>inconnue</em>'
        if info['paysdomicile']:
            pays = format_pays(info['paysdomicile'])
            if pays:
                info['paysdomicile'] = '(%s)' % pays
            else:
                info['paysdomicile'] = ''
        if info['telephone'] or info['telephonemobile']:
            info['telephones'] = '<br>%s &nbsp;&nbsp; %s' % (info['telephonestr'],
                                                             info['telephonemobilestr']) 
        else:
            info['telephones'] = ''
        # champs dependant des permissions
        if authuser.has_permission(ScoEtudChangeAdr,self):
            info['modifadresse'] = '<a href="formChangeCoordonnees?etudid=%s">modifier adresse</a>' % etudid
        else:
            info['modifadresse'] = ''
        # Liste des inscriptions
        ilist = []
        for sem in info['sems']:
            data = sem.copy()
            data.update(info)
            data.update(sem['ins'])
            i = sem['ins']
            ilist.append('<table><tr><td><a href="Notes/formsemestre_status?formsemestre_id=%(formsemestre_id)s">%(titre)s %(date_debut)s - %(date_fin)s</a> [%(etat)s] groupe %(groupetd)s </td><td><div class="barrenav"><ul class="nav"><li><a href="Notes/formsemestre_bulletinetud?formsemestre_id=%(formsemestre_id)s&etudid=%(etudid)s" class="menu bulletin">bulletin</a></li></ul></div></td>' % data )

            if authuser.has_permission(ScoEtudChangeGroups,self) or authuser.has_permission(ScoEtudInscrit,self):
                # menu pour action sur etudiant
                ilist.append("""<td><div class="barrenav"><ul class="nav"><li onmouseover="MenuDisplay(this)" onmouseout="MenuHide(this)"><a href="#"
	    class="menu direction_etud">Scolarit�</a><ul>""") # "

                if authuser.has_permission(ScoEtudChangeGroups,self):
                    ilist.append('<li><a href="formChangeGroupe?etudid=%s&formsemestre_id=%s">changer de groupe</a></li>' % (etudid,i['formsemestre_id']) )
                if authuser.has_permission(ScoEtudInscrit,self):
                    ilist.append("""
                    <li><a href="formDem?etudid=%(etudid)s&formsemestre_id=%(formsemestre_id)s">D&eacute;mission</a></li>
                    <li><a href="formDiplome?etudid=%(etudid)s&formsemestre_id=%(formsemestre_id)s">Validation du semestre</a></li>
                    <li><a href="Notes/formsemestre_inscription_with_modules_form?etudid=%(etudid)s">Inscrire ailleurs</a>
                    </ul></ul>
                    """ % { 'etudid' : etudid, 'formsemestre_id' : i['formsemestre_id'] } )                    
                    #                     <li><a href="formExclusion?etudid=%(etudid)s&formsemestre_id=%(formsemestre_id)s">Exclusion (non redoublement)</a></li>
                    #
                ilist.append('</div></td>')
            ilist.append('</tr></table>')
        if not ilist:
            ilist.append('<p><b>Etudiant%s non inscrit%s'%(info['ne'],info['ne']))
            if authuser.has_permission(ScoEtudInscrit,self):
                ilist.append('<a href="%s/Notes/formsemestre_inscription_with_modules_form?etudid=%s">inscrire</a></li>'%(self.ScoURL(),etudid))
            ilist.append('</b></b>')
                
        info['liste_inscriptions'] = '\n'.join(ilist)
        # Liste des annotations
        alist = []
        annos = scolars.etud_annotations_list(cnx, args={ 'etudid' : etudid })
        i = 0
        for a in annos:
            if i % 2: # XXX refaire avec du CSS
                a['bgcolor']="#EDEDED"
            else:
                a['bgcolor'] = "#DEDEDE"
            i += 1
            alist.append('<tr><td bgcolor="%(bgcolor)s">Le %(date)s par <b>%(author)s</b> (%(zope_authenticated_user)s) : <br>%(comment)s</td></tr>' % a )
        info['liste_annotations'] = '\n'.join(alist)
        #
        tmpl = """
<script language="javascript" type="text/javascript">
function bodyOnLoad() {
    //Rico.Corner.round('tota');
}
</script>

<div class="ficheEtud" id="ficheEtud"><table>
<tr><td>
<h2>%(nomprenom)s (%(inscription)s)</h2>

%(emaillink)s
</td><td class="photocell">
%(etudfoto)s
</td></tr></table>

<div class="fichesituation">
<div class="fichetablesitu">
<table>
<tr><td class="fichetitre2">Situation :</td><td>%(situation)s</td></tr>
<tr><td class="fichetitre2">Groupe :</td><td>%(groupes)s</td></tr>
<tr><td class="fichetitre2">Parcours :</td><td>%(parcours)s (n�%(ne)s en %(annee_naissance)s)</td></tr>
</table>
</div>

<!-- Adresse -->
<div class="ficheadresse" id="ficheadresse">
<table><tr>
<td class="fichetitre2">Adresse :</td><td> %(domicile)s %(codepostaldomicile)s %(villedomicile)s %(paysdomicile)s
%(modifadresse)s
%(telephones)s
</td></tr></table>
</div>

</div>

<!-- Inscriptions -->
<div class="ficheinscriptions" id="ficheinscriptions">
<p class="fichetitre">Inscriptions</p>
%(liste_inscriptions)s
</div>

<!-- Donnees admission -->
<div class="ficheadmission">
<p class="fichetitre">Informations admission</p>
<table>
<tr><th>Bac</th><th>An. Bac</th><th>Math</th><th>Physique</th><th>Anglais</th><th>Francais</th></tr>
<tr>
<td>%(bac)s (%(specialite)s)</td>
<td>%(annee_bac)s </td>
<td>%(math)s</td><td>%(physique)s</td><td>%(anglais)s</td><td>%(francais)s</td>
</tr>
</table>
<p>%(ilycee)s %(rap)s
</div>

<div class="ficheannotations">
<h4>Annotations</h4>
<table width="95%%">%(liste_annotations)s</table>

<form action="doAddAnnotation" method="GET" class="noprint">
<input type="hidden" name="etudid" value="%(etudid)s">
<b>Ajouter une annotation sur %(nomprenom)s: </b>
<table><tr>
<tr><td><textarea name="comment" rows="4" cols="50" value=""></textarea>
<br><font size=-1><i>Balises HTML autoris�es: b, a, i, br, p.</i></font>
</td></tr>
<tr><td>Auteur : <input type="text" name="author" width=12 value="%(authuser)s">&nbsp;
<input type="submit" value="Ajouter annotation"></td></tr>
</table>
</form>
</div>
</div>
        """
        header = self.sco_header(
                    self, REQUEST,
                    #javascripts=[ 'prototype_1_4_0_js', 'rico_js'],
                    #bodyOnLoad='javascript:bodyOnLoad()',
                    page_title='Fiche �tudiant %(prenom)s %(nom)s'%info )
        return header + tmpl % info + self.sco_footer(self,REQUEST)

    security.declareProtected(ScoView, 'descr_situation_etud')
    def descr_situation_etud(self, etudid, ne=''):
        """chaine decrivant la situation presente de l'etudiant
        et chaine decrivant son parcours"""
        cnx = self.GetDBConnexion()
        events = scolars.scolar_events_list(cnx, args={'etudid':etudid})
        if not events:
            return 'aucune information sur cet �tudiant !', ''
        # recherche la date de 1ere inscription
        date_entree = ''
        titressem = []
        for ev in events:
            if ev['event_type'] == 'INSCRIPTION':
                if not date_entree:
                    # garde la premiere date d'inscription
                    date_entree = '(entr�%s le %s)' % (ne,ev['event_date'])
                sem = self.Notes.do_formsemestre_list(
                     {'formsemestre_id' : ev['formsemestre_id']} )[0]
                titressem.append(sem['titre'])
        parcours = ', '.join(titressem)
        # dernier event
        lastev = events[-1]
        if lastev['event_type'] == 'CREATION':  
            etat = 'cr��%s le %s (<b>non inscrit%s</b>)' % (ne,ne,lastev['event_date'])
        elif lastev['event_type'] == 'INSCRIPTION':        
            sem = self.Notes.do_formsemestre_list(
                {'formsemestre_id' : lastev['formsemestre_id']} )[0]
            etat = 'inscrit%s en %s' % (ne,sem['titre'])
        elif lastev['event_type'] == 'DEMISSION':
            etat = '<span class="boldredmsg">d�mission le %s</span>' % lastev['event_date']
        elif lastev['event_type'] == 'VALID_SEM':
            sem = self.Notes.do_formsemestre_list(
                {'formsemestre_id' : lastev['formsemestre_id']} )[0]
            etat = 'valid�  %s (le %s)' % (sem['titre'],lastev['event_date'])
        elif lastev['event_type'] == 'VALID_UE':
            formsemestre_id = lastev['formsemestre_id']
            etat = self.Notes.etud_descr_situation_semestre(etudid, formsemestre_id, ne=ne)
        elif lastev['event_type'] == 'ECHEC_SEM':
            sem = self.Notes.do_formsemestre_list(
                {'formsemestre_id' : lastev['formsemestre_id']} )[0]
            etat = '�chec en %s le %s' % (sem['titre'],lastev['event_date'])
        elif lastev['event_type'] == 'AUT_RED':
            sem = self.Notes.do_formsemestre_list(
                {'formsemestre_id' : lastev['formsemestre_id']} )[0]
            etat = 'autoris�%s � redoubler le %s (le %s)' % (ne,sem['titre'],lastev['event_date'])
        elif lastev['event_type'] == 'EXCLUS':
            etat = 'exclu%s le %s' % (ne,lastev['event_date'])
        else:
            etat = 'code �venement inconnu (%s) !' % lastev['event_type']
        #
        return ('%s %s' % (etat, date_entree)), parcours

    security.declareProtected(ScoEtudAddAnnotations, 'doAddAnnotation')
    def doAddAnnotation(self, etudid, comment, author, REQUEST):
        "ajoute annotation sur etudiant"
        authuser = REQUEST.AUTHENTICATED_USER
        cnx = self.GetDBConnexion()
        scolars.etud_annotations_create(
            cnx,
            args={ 'etudid':etudid, 'author' : author,
                   'comment' : comment,
                   'zope_authenticated_user' : str(authuser),
                   'zope_remote_addr' : REQUEST.REMOTE_ADDR } )
        logdb(REQUEST,cnx,method='addAnnotation', etudid=etudid )
        REQUEST.RESPONSE.redirect('ficheEtud?etudid='+etudid)

    security.declareProtected(ScoEtudChangeAdr, 'formChangeCoordonnees')
    def formChangeCoordonnees(self,etudid,REQUEST):
        "edit coordonnes etudiant"
        cnx = self.GetDBConnexion()        
        etud = scolars.etudident_list(cnx, {'etudid':etudid})[0]
        adrs = scolars.adresse_list(cnx, {'etudid':etudid})
        if adrs:
            adr = adrs[0]
        else:
            adr = {} # no data for this student
        H = [ '<h2><font color="#FF0000">Changement des coordonn�es de </font> %(prenom)s %(nom)s</h2><p>' % etud ]
        header = self.sco_header(
            self,REQUEST,
            page_title='Changement adresse de %(prenom)s %(nom)s'%etud)
        
        tf = TrivialFormulator(
            REQUEST.URL0, REQUEST.form, 
            ( ('adresse_id', {'input_type' : 'hidden' }),
              ('etudid',  { 'input_type' : 'hidden' }),
              ('email',  { 'size' : 40, 'title' : 'e-mail' }),
              ('domicile'    ,  { 'size' : 65, 'explanation' : 'num�ro, rue', 'title' : 'Adresse' }),
              ('codepostaldomicile', { 'size' : 6, 'title' : 'Code postal' }),
              ('villedomicile', { 'size' : 20, 'title' : 'Ville' }),
              ('paysdomicile', { 'size' : 20, 'title' : 'Pays' }),    
              ('',     { 'input_type' : 'separator', 'default' : '&nbsp;' } ),
              ('telephone', { 'size' : 13, 'title' : 'T�l�phone'  }),    
              ('telephonemobile', { 'size' : 13, 'title' : 'Mobile' }),
              ),
            initvalues = adr,
            submitlabel = 'Valider le formulaire'
            )
        if  tf[0] == 0:
            return header + '\n'.join(H) + tf[1] + self.sco_footer(self,REQUEST)
        elif tf[0] == -1:
            return REQUEST.RESPONSE.redirect( REQUEST.URL1 )
        else:
            if adrs:
                scolars.adresse_edit( cnx, args=tf[2] )
            else:
                scolars.adresse_create( cnx, args=tf[2] )
            logdb(REQUEST,cnx,method='changeCoordonnees', etudid=etudid)
            REQUEST.RESPONSE.redirect('ficheEtud?etudid='+etudid)

    security.declareProtected(ScoEtudChangeGroups, 'formChangeGroupe')
    def formChangeGroupe(self, formsemestre_id, etudid, REQUEST):
        "changement groupe etudiant dans semestre"
        cnx = self.GetDBConnexion()    
        etud = scolars.etudident_list(cnx, {'etudid':etudid})[0]
        sem = self.Notes.do_formsemestre_list({'formsemestre_id':formsemestre_id})[0]
        ins = self.Notes.do_formsemestre_inscription_list(
            { 'etudid'  : etudid, 'formsemestre_id' : formsemestre_id })[0]
        #
        etud['semtitre'] = sem['titre']
        H = [ '<h2><font color="#FF0000">Changement de groupe de</font> %(prenom)s %(nom)s (semestre %(semtitre)s)</h2><p>' % etud ]
        header = self.sco_header(
            self,REQUEST,
            page_title='Changement de groupe de %(prenom)s %(nom)s'%etud)
        # Liste des groupes existant (== ou il y a des inscrits)
        gr_td,gr_tp,gr_anglais = self.Notes.do_formsemestre_inscription_listegroupes(formsemestre_id=formsemestre_id)
        #
        H.append("""<form action="doChangeGroupe" method="GET" name="cg">
<table>
<tr><th></th><th>TD</th><th>"Anglais"</th><th>TP</th></tr>
<tr><td><b>Groupes actuels&nbsp;:</b></td><td>%(groupetd)s</td><td>%(groupeanglais)s</td><td>%(groupetp)s</td></tr>
<tr><td><b>Nouveaux groupes&nbsp;:</b></td>
""" % ins)
        for (glist, gname) in (
            (gr_td,'groupetd'),
            (gr_anglais, 'groupeanglais'),
            (gr_tp, 'groupetp') ):
            H.append('<td><select name="%s" id="%s">' % (gname,gname) )
            for g in glist:
                if ins[gname] == g:
                    selected = 'selected'
                else:
                    selected = ''
                H.append('<option value="%s" %s>%s</option>' % (g,selected,g))
            H.append('</select></td>')
        H.append('</tr></table>')
        H.append("""<input type="hidden" name="etudid" value="%s">
<input type="hidden" name="formsemestre_id" value="%s">
<p>
(attention, v�rifier que les groupes de TD, TP et Anglais sont compatibles)
</p>
<script type="text/javascript">
function tweakmenu( gname ) {
   var gr = document.cg.newgroupname.value;
   if (!gr) {
      alert("nom de groupe vide !");
      return false;
   }
   var menutd = document.getElementById(gname);
   var newopt = document.createElement('option');
   newopt.value = gr;
   var textopt = document.createTextNode(gr);
   newopt.appendChild(textopt);
   menutd.appendChild(newopt);
   var msg = document.getElementById("groupemsg");
   msg.appendChild( document.createTextNode("groupe " + gr + " cr��; ") );
   document.cg.newgroupname.value = "";
}
</script>

<p>Cr�er un nouveau groupe:
<input type="text" id="newgroupname" size="8"/>
<input type="button" onClick="tweakmenu( 'groupetd' );" value="cr�er groupe TD"/>
<input type="button" onClick="tweakmenu( 'groupeanglais' );" value="cr�er groupe Anglais"/>
<input type="button" onClick="tweakmenu( 'groupetp' );" value="cr�er groupe TP"/>
</p>
<p id="groupemsg" style="font-style: italic;"></p>

<input type="submit" value="Changer de groupe">
<input type="button" value="Annuler" onClick="window.location='%s'">

</form>""" % (etudid, formsemestre_id, REQUEST.URL1) )
        
        return header + '\n'.join(H) + self.sco_footer(self,REQUEST)

    security.declareProtected(ScoEtudChangeGroups, 'doChangeGroupe')
    def doChangeGroupe(self, etudid, formsemestre_id, groupetd=None,
                       groupeanglais=None, groupetp=None, REQUEST=None,
                       redirect=1):
        "change le groupe"
        cnx = self.GetDBConnexion()
        ins = self.Notes.do_formsemestre_inscription_list(
            { 'etudid'  : etudid, 'formsemestre_id' : formsemestre_id })[0]
        ins['groupetd'] = groupetd
        if groupetp != None:
            ins['groupetp'] = groupetp
        if groupeanglais != None:
            ins['groupeanglais'] = groupeanglais
        self.Notes.do_formsemestre_inscription_edit( args=ins )
        logdb(REQUEST,cnx,method='changeGroupe', etudid=etudid,
              msg='groupetd=%s,groupeanglais=%s,groupetp=%s,formsemestre_id=%s' %
              (groupetd,groupeanglais,groupetp,formsemestre_id))
        if redirect:
            REQUEST.RESPONSE.redirect('ficheEtud?etudid='+etudid)

    # --- Affectation initiale des groupes
    security.declareProtected(ScoEtudChangeGroups, 'affectGroupes')
    affectGroupes = DTMLFile('dtml/groups/affectGroupes', globals()) 

    security.declareProtected(ScoView, 'XMLgetGroupesTD')
    def XMLgetGroupesTD(self, formsemestre_id, groupType, REQUEST):
        "Liste des etudiants dans chaque groupe de TD"
        if not groupType in ('TD', 'TP', 'TA'):
            raise ValueError( 'invalid group type: ' + groupType)
        cnx = self.GetDBConnexion()
        sem = self.Notes.do_formsemestre_list({'formsemestre_id':formsemestre_id})[0]
        REQUEST.RESPONSE.setHeader('Content-type', XML_MIMETYPE)
        doc = jaxml.XML_document( encoding=SCO_ENCODING )
        doc._text( '<ajax-response><response type="object" id="MyUpdater">' )
        doc._push()

        
        # --- Infos sur les groupes existants
        gr_td,gr_tp,gr_anglais = self.Notes.do_formsemestre_inscription_listegroupes(formsemestre_id=formsemestre_id)
        nt = self.Notes.CachedNotesTable.get_NotesTable(self.Notes,
                                                        formsemestre_id)
        inscrlist = nt.inscrlist # liste triee par nom
        open('/tmp/titi','w').write(str(inscrlist))
        # -- groupes TD (XXX experimental)
        if groupType == 'TD':
            gr, key = gr_td, 'groupetd'
        elif groupType == 'TP':
            gr, key = gr_tp, 'groupetp'
        else:
            gr, key = gr_anglais, 'groupeanglais'
        inscr_nogroups = [ e for e in inscrlist if not e[key] ]
        if inscr_nogroups:
            # ajoute None pour avoir ceux non affectes a un groupe
            gr.append(None)
        for g in gr: 
            doc._push()
            if g:
                gname = g
            else:
                gname = 'Aucun'
            doc.groupe( type=groupType, displayName=gname, groupName=g )
            for e in inscrlist:
                if (g and e[key] == g) or (not g and not e[key]):
                    ident = nt.identdict[e['etudid']]
                    doc._push()
                    doc.etud( etudid=e['etudid'],
                              sexe=format_sexe(ident['sexe']),
                              nom=format_nom(ident['nom']),
                              prenom=format_prenom(ident['prenom']))
                    doc._pop()    
            doc._pop()
        doc._pop()
        doc._text( '</response></ajax-response>' )
        return repr(doc)

    security.declareProtected(ScoEtudChangeGroups, 'setGroupes')
    def setGroupes(self, groupslists, formsemestre_id=None, groupType=None,
                   REQUEST=None):
        "affect groups (Ajax request)"
        #f = open('/tmp/toto','w')
        #f.write('formsemestre_id=%s\n' % formsemestre_id)
        #f.write('groupType=%s\n' % groupType )
        #f.write(groupslists)
        if not groupType in ('TD', 'TP', 'TA'):
            raise ValueError, 'invalid group type: ' + groupType
        if groupType == 'TD':
            grn = 'groupetd'
        elif groupType == 'TP':
            grn = 'groupetp'
        else:
            grn = 'groupeanglais'
        args = { 'REQUEST' : REQUEST, 'redirect' : False }
        for line in groupslists.split('\n'):
            fs = line.split(';')
            groupName = fs[0].strip();
            args[grn] = groupName
            for etudid in fs[1:-1]:
                self.doChangeGroupe( etudid, formsemestre_id, **args )
        
        REQUEST.RESPONSE.setHeader('Content-type', XML_MIMETYPE)
        return '<ajax-response><response type="object" id="ok"/></ajax-response>'
        
    # --- Trombi: gestion photos
    # Ancien systeme (www-gtr):
    #  fotos dans ZODB, folder Fotos, id=identite.foto
    security.declareProtected(ScoView, 'etudfoto')
    def etudfoto(self, etudid, foto=None, fototitle=''):
        "html foto (taille petite)"
        img = self.etudfoto_img(etudid, foto)
        return img.tag(border='0',title=fototitle)

    def etudfoto_img(self, etudid, foto=None):
        if foto is None:
            cnx = self.GetDBConnexion()
            etud = scolars.etudident_list(cnx, {'etudid': etudid })[0]
            foto = etud['foto']
        try:
            img = getattr(self.Fotos, foto)
        except:
            try:
                img = getattr(self.Fotos, foto + '.h90.jpg' )
            except:
                img = getattr(self.Fotos, 'unknown_img')        
        return img
    
    security.declareProtected(ScoEtudChangeAdr, 'formChangePhoto')
    formChangePhoto = DTMLFile('dtml/formChangePhoto', globals())
    security.declareProtected(ScoEtudChangeAdr, 'doChangePhoto')
    def doChangePhoto(self, etudid, photofile, REQUEST, suppress=False):
        """change la photo d'un etudiant
        Si suppress, supprime la photo existante.
        """
        if photofile:
            # mesure la taille du fichier uploaded
            filesize = len(photofile.read())
            photofile.seek(0)         
            if filesize < 10 or filesize > 800*1024:
                return 0, 'Fichier image de taille invalide !'
            # find a free id
            num = 0
            while hasattr( self.Fotos, 'img_n_%05d.h90.jpg' % num):
                num = num + 1
            nt = 'n_%05d' % num
            photo_id='img_' + nt + '.h90.jpg'

            small_img = imageresize.ImageScaleH(photofile,H=90)
            self.Fotos.manage_addProduct['OFSP'].manage_addImage(photo_id, small_img, etudid )
            # Update database
            cnx = self.GetDBConnexion() 
            scolars.identite_edit(cnx,args={'etudid':etudid,'foto':photo_id})
            logdb(REQUEST,cnx,method='changePhoto',msg=photo_id,etudid=etudid)
        elif suppress:
            scolars.identite_edit(cnx,args={'etudid':etudid,'foto':''})
            logdb(REQUEST,cnx,method='changePhoto',msg='supression', etudid=etudid)
        return 1, 'ok'
    #
    security.declareProtected(ScoEtudInscrit, "formDem")
    def formDem(self, etudid, formsemestre_id, REQUEST):
        "Formulaire Demission Etudiant"
        cnx = self.GetDBConnexion()    
        etud = scolars.etudident_list(cnx, {'etudid':etudid})[0]
        sem = self.Notes.do_formsemestre_list({'formsemestre_id':formsemestre_id})[0]
        etud['formsemestre_id']=formsemestre_id
        etud['semtitre'] = sem['titre']
        etud['nowdmy'] = time.strftime('%d/%m/%Y')
        #
        header = self.sco_header(
            self,REQUEST,
            page_title='D�mission de  %(prenom)s %(nom)s (du semestre %(semtitre)s)'%etud)
        H = [ '<h2><font color="#FF0000">D�mission de</font> %(prenom)s %(nom)s (semestre %(semtitre)s)</h2><p>' % etud ]
        H.append("""<form action="doDemEtudiant" method="GET">
<b>Date de la d&eacute;mission (J/M/AAAA):&nbsp;</b><input type="text" name="event_date" width=20 value="%(nowdmy)s">
<input type="hidden" name="etudid" value="%(etudid)s">
<input type="hidden" name="formsemestre_id" value="%(formsemestre_id)s">
<p>
<input type="submit" value="Confirmer la d&eacute;mission">

</form>""" % etud )
        return header + '\n'.join(H) + self.sco_footer(self,REQUEST)
    
    security.declareProtected(ScoEtudInscrit, "formDem")
    def doDemEtudiant(self,etudid,formsemestre_id,event_date=None,REQUEST=None):
        "demission d'un etudiant"
        # marque D dans l'inscription au semestre et ajoute
        # un "evenement" scolarite
        cnx = self.GetDBConnexion()
        ins = self.Notes.do_formsemestre_inscription_list(
            { 'etudid'  : etudid, 'formsemestre_id' : formsemestre_id })[0]
        if ins['etat'] != 'I':
            raise ScoException('etudiant non inscrit !')
        ins['etat'] = 'D'
        self.Notes.do_formsemestre_inscription_edit( args=ins )
        logdb(REQUEST,cnx,method='demEtudiant', etudid=etudid)
        scolars.scolar_events_create( cnx, args = {
            'etudid' : etudid,
            'event_date' : event_date,
            'formsemestre_id' : formsemestre_id,
            'event_type' : 'DEMISSION' } )
        if REQUEST:
            return REQUEST.RESPONSE.redirect('ficheEtud?etudid='+etudid)

    security.declareProtected(ScoEtudInscrit, "formDiplome")
    def formDiplome(self, etudid, formsemestre_id, REQUEST):
        "Formulaire Diplome Etudiant"
        # maintenant fait dans Notes
        return REQUEST.RESPONSE.redirect(
            'Notes/formsemestre_validation_form?formsemestre_id=%s&etudid=%s'
            % (formsemestre_id, etudid) )

    security.declareProtected(ScoEtudInscrit, "formExclusion")
    def formExclusion(self, etudid, formsemestre_id, REQUEST):
        "Formulaire Exclusion Etudiant"
        cnx = self.GetDBConnexion()    
        etud = scolars.etudident_list(cnx, {'etudid':etudid})[0]
        sem = self.Notes.do_formsemestre_list({'formsemestre_id':formsemestre_id})[0]
        etud['formsemestre_id'] = formsemestre_id
        etud['semtitre'] = sem['titre']
        etud['nowdmy'] = time.strftime('%d/%m/%Y')
        #
        header = self.sco_header(
            self,REQUEST,
            page_title='Exclusion de  %(prenom)s %(nom)s (du semestre %(semtitre)s)'%etud)
        H = [ '<h2><font color="#FF0000">Exclusion de</font> %(prenom)s %(nom)s (semestre %(semtitre)s)</h2><p>' % etud ]
        H.append("""Il s'agit normalement d'une non autorisation � redoubler<br>
Utiliser ce formulaire en fin de semestre, apr�s le jury.
""")
        H.append("""<form action="doExclusionEtudiant" method="GET">
<b>Date de l'exclusion (J/M/AAAA):&nbsp;</b><input type="text" name="event_date" width=20 value="%(nowdmy)s">
<input type="hidden" name="etudid" value="%(etudid)s">
<input type="hidden" name="formsemestre_id" value="%(formsemestre_id)s">
<p>
<input type="submit" value="Confirmer l\'exclusion">

</form>""" % etud )
        return header + '\n'.join(H) + self.sco_footer(self,REQUEST)

    security.declareProtected(ScoEtudInscrit, "doExclusionEtudiant")
    def doExclusionEtudiant(self,etudid,formsemestre_id,event_date=None,REQUEST=None):
        "exclusion de l'etudiant"
        cnx = self.GetDBConnexion()
        ins = self.Notes.do_formsemestre_inscription_list(
            { 'etudid'  : etudid, 'formsemestre_id' : formsemestre_id })[0]
        if ins['etat'] != 'I':
            raise ScoException('etudiant non inscrit !')
        logdb(REQUEST,cnx,method='exclusionEtudiant', etudid=etudid)
        scolars.scolar_events_create( cnx, args = {
            'etudid' : etudid,
            'event_date' : event_date,
            'formsemestre_id' : formsemestre_id,
            'event_type' : 'EXCLUS' } )
        if REQUEST:
            REQUEST.REQUEST.redirect('ficheEtud?etudid='+etudid)

#     security.declareProtected(ScoEtudInscrit, "formPassage")
#     def formPassage(self,REQUEST):
#         "Formulaire passage d'un semestre a l'autre"
#         raise NotImplementedError('fonctionnalit� non impl�ment�e !')
#         # -> choix du semestre, reincrition dans les bons groupes
        
#     security.declareProtected(ScoEtudInscrit, "formRedouble")
#     def formRedouble(self,REQUEST):
#         "Formulaire redoublement d'un semestre"
#         raise NotImplementedError('fonctionnalit� non impl�ment�e !')
#         # -> choix du semestre, reincrition dans les bons groupes

    security.declareProtected(ScoEtudInscrit,"etudident_create_form")
    def etudident_create_form(self, REQUEST):
        "formulaire creation individuelle etudiant"
        return self.etudident_create_or_edit_form(REQUEST, edit=False)
    
    security.declareProtected(ScoEtudInscrit,"etudident_edit_form")
    def etudident_edit_form(self, REQUEST):
        "formulaire edition individuelle etudiant"
        return self.etudident_create_or_edit_form(REQUEST, edit=True)
    
    security.declareProtected(ScoEtudInscrit,"etudident_create_or_edit_form")
    def etudident_create_or_edit_form(self, REQUEST, edit ):
        "Le formulaire HTML"
        H = self.sco_header(self,REQUEST)
        F = self.sco_footer(self,REQUEST)
        AUTHENTICATED_USER = REQUEST.AUTHENTICATED_USER
        etudid = REQUEST.form.get('etudid',None)
        cnx = self.GetDBConnexion()
        if not edit:
            # creation nouvel etudiant
            initvalues = {}
            submitlabel = 'Ajouter cet �tudiant'
        else:
            # edition donnees d'un etudiant existant
            # setup form init values
            if not etudid:
                raise ScoValueError('missing etudid parameter')
            initvalues = scolars.etudident_list(cnx, {'etudid' : etudid})
            assert len(initvalues) == 1
            initvalues = initvalues[0]
            submitlabel = 'Modifier les donn�es'
        tf = TrivialFormulator( REQUEST.URL0, REQUEST.form,
                                ( 
            ('etudid', { 'default' : etudid, 'input_type' : 'hidden' }),
            ('adm_id', { 'input_type' : 'hidden' }),

            ('nom',       { 'size' : 25, 'title' : 'Nom' }),
            ('prenom',    { 'size' : 25, 'title' : 'Pr�nom' }),
            ('sexe',      { 'input_type' : 'menu', 'labels' : ['MR','MME','MLLE'],
                            'allowed_values' : ['MR','MME','MLLE'], 'title' : 'Genre' }),
            ('annee_naissance', { 'size' : 5, 'title' : 'Ann�e de naissance', 'type' : 'int' }),
            ('nationalite', { 'size' : 25, 'title' : 'Nationalit�' }),

            ('annee', { 'size' : 5, 'title' : 'Ann�e admission IUT', 'type' : 'int' }),
            #
            ('sep', { 'input_type' : 'separator', 'title' : 'Scolarit� ant�rieure:' }),
            ('bac', { 'size' : 5, 'explanation' : 's�rie du bac (S, STI, STT, ...)' }),
            ('specialite', { 'size' : 25, 'title' : 'Sp�cialit�', 
                             'explanation' : 'sp�cialit� bac: SVT M, GENIE ELECTRONIQUE, ...' }),
            ('annee_bac', { 'size' : 5, 'title' : 'Ann�e bac', 'type' : 'int',
                            'explanation' : 'ann�e obtention du bac' }),
            ('math', { 'size' : 3, 'type' : 'float', 'title' : 'Note de math�matiques',
                       'explanation' : 'note sur 20 en terminale' }),
            ('physique', { 'size' : 3, 'type' : 'float', 'title' : 'Note de physique',
                       'explanation' : 'note sur 20 en terminale' }),
            ('anglais', { 'size' : 3, 'type' : 'float', 'title' : 'Note d\'anglais',
                       'explanation' : 'note sur 20 en terminale' }),
            ('francais', { 'size' : 3, 'type' : 'float', 'title' : 'Note de fran�ais',
                       'explanation' : 'note sur 20 obtenue au bac' }),
            ('rang', { 'size' : 1, 'type' : 'int', 'title' : 'Position IUT Villetaneuse',
                       'explanation' : 'rang de notre d�partement dans les voeux du candidat' }),
            ('qualite', { 'size' : 3, 'type' : 'float', 'title' : 'Qualit�',
                       'explanation' : 'Note de qualit� attribu�e au dossier' }),

            ('decision', { 'input_type' : 'menu',
                           'allowed_values' :
                           ['ADMIS','ATTENTE 1','ATTENTE 2', 'ATTENTE 3', 'REFUS', '?' ] }),
            ('score', { 'size' : 3, 'type' : 'float', 'title' : 'Score',
                       'explanation' : 'score calcul� lors de l\'admission' }),
            ('rapporteur', { 'size' : 50, 'title' : 'Enseignant rapporteur' }),
            ('commentaire', {'input_type' : 'textarea', 'rows' : 4, 'cols' : 50,
                             'title' : 'Note du rapporteur' }),
            ('nomlycee', { 'size' : 20, 'title' : 'Lyc�e d\'origine' }),
            ('villelycee', { 'size' : 15, 'title' : 'Commune du Lyc�e' })
            ),                            
                                submitlabel = submitlabel,
                                cancelbutton = 'Annuler',
                                initvalues = initvalues)
        if tf[0] == 0:
            return H + tf[1] + '<p>' + str(initvalues) + F
        elif tf[0] == -1:
            return H + '<h4>annulation</h4>' + F
        else:
            # form submission
            if not edit:
                # creation d'un etudiant
                etudid = scolars.etudident_create(cnx, tf[2])
                # event
                scolars.scolar_events_create( cnx, args = {
                    'etudid' : etudid,
                    'event_date' : time.strftime('%d/%m/%Y'),
                    'formsemestre_id' : None,
                    'event_type' : 'CREATION' } )
                # log
                logdb(REQUEST, cnx, method='etudident_edit_form',
                      etudid=etudid, msg='creation initiale')
            else:
                # modif d'un etudiant
                scolars.etudident_edit(cnx, tf[2])
            #
            return REQUEST.RESPONSE.redirect('ficheEtud?etudid='+etudid)
    
    # ---- inscriptions "en masse"
    security.declareProtected(ScoEtudInscrit, "students_import_csv")
    def students_import_excel(self, csvfile, REQUEST=None):
        "import students from Excel file"
        diag = ImportScolars.scolars_import_excel_file(
            csvfile, file_path, self.Notes, REQUEST )
        if REQUEST:
            H = [self.sco_header(self,REQUEST, page_title='Import etudiants')]
            H.append('<p>Import excel: %s</p>'% diag)
            H.append('<p>OK, import termin� !</p>')
            return '\n'.join(H) + self.sco_footer(self,REQUEST)
        # invalid all caches
        self.Notes.CachedNotesTable.inval_cache()
    
    security.declareProtected(ScoEtudInscrit, "form_students_import_csv")
    def form_students_import_csv(self, REQUEST):
        "formulaire import csv"
        H = [self.sco_header(self,REQUEST, page_title='Import etudiants')]        
        H.append('<h2>T�l�chargement d\'une nouvelle liste d\'etudiants</h2><p>')
        F = self.sco_footer(self,REQUEST)
        tf = TrivialFormulator(
            REQUEST.URL0, REQUEST.form, 
            (('csvfile', {'title' : 'Fichier Excel:', 'input_type' : 'file', 'size' : 40 }),
             ), submitlabel = 'T�l�charger')
        S = ["""<p>Le fichier Excel d�crivant les �tudiants doit comporter les colonnes suivantes.
<p>Les colonnes peuvent �tre plac�es dans n'importe quel ordre, mais
le <b>titre</b> exact (tel que ci-dessous) doit �tre sur la premi�re ligne.
</p>
<p>
Les champs avec un ast�risque (*) doivent �tre pr�sents (nulls non autoris�s).
</p>
<p>
Vous pouvez obtenir une feuille excel avec les colonnes � remplir <a href="import_generate_excel_sample">ici</a>
</p>
<p>
<table>
<tr><td><b>Attribut</b></td><td><b>Type</b></td><td><b>Description</b></td></tr>"""]
        for t in ImportScolars.sco_import_format(file_path):
            if int(t[3]):
                ast = ''
            else:
                ast = '*'
            S.append('<tr><td>%s</td><td>%s</td><td>%s</td><td>%s</td></tr>'
                     % (t[0],t[1],t[4], ast))
        if  tf[0] == 0:
            return '\n'.join(H) + tf[1] + '\n'.join(S) + F
        elif tf[0] == -1:
            return REQUEST.RESPONSE.redirect( REQUEST.URL1 )
        else:
            return self.students_import_excel(tf[2]['csvfile'], REQUEST=REQUEST)

    security.declareProtected(ScoEtudInscrit,"sco_import_generate_excel_sample")
    def import_generate_excel_sample(self, REQUEST):
        "une feuille excel pour importation etudiants"
        format = ImportScolars.sco_import_format(file_path)
        data = ImportScolars.sco_import_generate_excel_sample(format)
        return sco_excel.sendExcelFile(REQUEST,data,'ImportEtudiants.xls')
    
    # sendEmail is not used through the web
    security.declareProtected(ScoAdministrate, "sendEmail")
    def sendEmail(self,msg):
        # sends an email to the address using the mailhost, if there is one
        if not self.mail_host:
            return
        # a failed notification shouldn't cause a Zope error on a site.
        try:
            mhost=getattr(self,self.mail_host)
            mhost.send(msg.as_string())
            log('sendEmail')
        except:
            pass

                        
            
    # --------------------------------------------------------------------
# Uncomment these lines with the corresponding manage_option
# To everride the default 'Properties' tab
#    # Edit the Properties of the object
#    manage_editForm = DTMLFile('dtml/manage_editZScolarForm', globals())

#
# Product Administration
#

def manage_addZScolar(self, id= 'id_ZScolar',
                      title='The Title for ZScolar Object',
                      db_cnx_string='the db connexion string',
                      REQUEST=None):
   "Add a ZScolar instance to a folder."
   self._setObject(id, ZScolar(id, title, db_cnx_string=db_cnx_string))
   if REQUEST is not None:
        return self.manage_main(self, REQUEST)
        #return self.manage_editForm(self, REQUEST)

# The form used to get the instance id from the user.
manage_addZScolarForm = DTMLFile('dtml/manage_addZScolarForm', globals())


    
