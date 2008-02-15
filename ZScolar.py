# -*- mode: python -*-
# -*- coding: iso8859-15 -*-

##############################################################################
#
# Gestion scolarite IUT
# 
# Copyright (c) 2001 - 2008 Emmanuel Viennet.  All rights reserved.
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

import time, string, glob, re
import urllib, urllib2, xml
try: from cStringIO import StringIO
except: from StringIO import StringIO
from zipfile import ZipFile

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
from Globals import INSTANCE_HOME
from Acquisition import Implicit


# ---------------
from notes_log import log
log.set_log_directory( INSTANCE_HOME + '/log' )
log("restarting...")


# where we exist on the file system
file_path = Globals.package_home(globals())

# Hackery to use packages in pour product
import sys
log( 'ZScolar home=%s' % file_path )
#sys.path.append( file_path )

from sco_utils import *
from ScolarRolesNames import *
from notesdb import *
from scolog import logdb

import scolars
import sco_formations
from scolars import format_nom, format_prenom, format_sexe, format_lycee
from scolars import format_telephone, format_pays, make_etud_args

import sco_news
from sco_news import NEWS_INSCR, NEWS_NOTE, NEWS_FORM, NEWS_SEM, NEWS_MISC

import html_sco_header, html_sidebar

from TrivialFormulator import TrivialFormulator, TF
from gen_tables import GenTable
import sco_excel
import imageresize

import ZNotes, ZAbsences, ZEntreprises, ZScoUsers
import ImportScolars
import sco_portal_apogee
import sco_groupes, sco_trombino
from sco_formsemestre_status import makeMenu
from VERSION import SCOVERSION, SCONEWS

try:
    import Products.ZPsycopgDA.DA as ZopeDA
except:
    import ZPsycopgDA.DA as ZopeDA # interp.py

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
    file_path = Globals.package_home(globals())
    
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
        da = ZopeDA.Connection(
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

    security.declareProtected(ScoView, 'essai')
    def essai(self, REQUEST=None):
        """essai: header / body / footer"""
        b = '<p>Hello, World !</p><br/>'
        #raise ScoValueError('essai exception !', dest_url='totoro', REQUEST=REQUEST)
        cnx = self.GetDBConnexion()
        b += str(dir(cnx))
        #cursor = cnx.cursor()
        #cursor.execute("select * from notes_formations")
        #b += str(cursor.fetchall())
        #b = self.Notes.gloups()
        #raise NoteProcessError('test exception !')        

        # essai: liste des permissions
        from AccessControl import getSecurityManager
        from AccessControl.Permission import Permission        
        
        permissions = self.ac_inherited_permissions(1)
        scoperms = [ p for p in permissions if p[0][:3] == 'Sco' ]
        #H.append( str(self.aq_parent.aq_parent.permission_settings()) )
        #H.append('<p>perms: %s</p>'%str(scoperms))
        #H.append('<p>valid_roles: %s</p>'%str(self.valid_roles()))
        #H.append('<p>ac_inherited_permissions=%s</p>'%str(self.ac_inherited_permissions(1)))
        def collect_roles( context, rd ):
            for p in scoperms:
                name, value = p[:2]
                P = Permission(name,value,context)
                roles = list(P.getRoles())
                if rd.has_key(name):
                    rd[name] += roles
                else:
                    rd[name] = roles
            if hasattr(context, 'aq_parent'):
                collect_roles(context.aq_parent, rd)
            
        b = ''
        rd = {}
        collect_roles(self, rd)
        b = '<p>' + str(rd) + '</p>'

        authuser = REQUEST.AUTHENTICATED_USER
        for p in scoperms:
            permname, value = p[:2]
            b += '<p>' + permname + ' : '
            if authuser.has_permission(permname,self):
                b += 'yes'
            else:
                b += 'no'
            b += '</p>'
        b += '<p>xxx</p><hr><p>' + str(self.aq_parent.aq_parent)

        return self.sco_header(REQUEST)+ str(b) + self.sco_footer(REQUEST)
        
    # Ajout (dans l'instance) d'un dtml modifiable par Zope
    def defaultDocFile(self,id,title,file):
        f=open(file_path+'/dtml/'+file+'.dtml')     
        file=f.read()     
        f.close()     
        self.manage_addDTMLMethod(id,title,file)

    # Ajout des JavaScripts 
    security.declareProtected(ScoView, 'groupmgr_js')
    groupmgr_js = DTMLFile('JavaScripts/groupmgr_js', globals())

    security.declareProtected(ScoView, 'prototype_1_4_0_js')
    prototype_1_4_0_js = DTMLFile('JavaScripts/prototype_1_4_0_js', globals())

    security.declareProtected(ScoView, 'rico_js')
    rico_js = DTMLFile('JavaScripts/rico_js', globals())

    security.declareProtected(ScoView, 'sorttable_js')
    sorttable_js = DTMLFile('JavaScripts/sorttable_js', globals())

    security.declareProtected(ScoView, 'menu_js')
    menu_js = DTMLFile('JavaScripts/menu_js', globals())

    security.declareProtected(ScoView, 'bubble_js')
    bubble_js = DTMLFile('JavaScripts/bubble_js', globals())

    security.declareProtected(ScoView, 'calendarDateInput_js')
    calendarDateInput_js = DTMLFile('JavaScripts/calendarDateInput_js',
                                    globals())

    # Styles CSS
    security.declareProtected(ScoView, 'scodoc_css')
    scodoc_css = DTMLFile('JavaScripts/scodoc_css', globals())

    security.declareProtected(ScoView, 'menu_css')
    menu_css = DTMLFile('JavaScripts/menu_css', globals())

    security.declareProtected(ScoView, 'verticalhisto_css')
    verticalhisto_css = DTMLFile('JavaScripts/verticalhisto_css', globals())
    
    security.declareProtected(ScoView, 'ScoURL')
    def ScoURL(self):
        "base URL for this sco instance"
        return self.absolute_url()

    security.declareProtected(ScoView, 'StyleURL')
    def StyleURL(self):
        "base URL for CSS style sheet"
        return self.gtrintranetstyle.absolute_url()


    security.declareProtected(ScoView, 'sco_header')
    #sco_header = DTMLFile('dtml/sco_header', globals())
    sco_header = html_sco_header.sco_header

    security.declareProtected(ScoView, 'sco_footer')
    sco_footer = DTMLFile('dtml/sco_footer', globals())
    security.declareProtected(ScoView, 'menus_bandeau')
    menus_bandeau = DTMLFile('dtml/menus_bandeau', globals())

    security.declareProtected(ScoView, 'http_expiration_date')
    def http_expiration_date(self):
        "http expiration date for cachable elements (css, ...)"
        d = datetime.timedelta(minutes=10)
        return (datetime.datetime.utcnow() + d).strftime("%a, %d %b %Y %H:%M:%S GMT")
    
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
    
    security.declareProtected(ScoView, 'about')
    def about(self, REQUEST):
        "version info"
        H = [ """<h2>Syst�me de gestion scolarit�</h2>
        <p>&copy; Emmanuel Viennet 1997-2007</p>
        <p>Version %s (subversion %s)</p>
        """ % (SCOVERSION, get_svn_version(file_path)) ]
        H.append('<p>Logiciel �crit en <a href="http://www.python.org">Python</a> pour la plate-forme <a href="http://www.zope.org">Zope</a>.</p><p>Utilise <a href="http://reportlab.org/">ReportLab</a> pour g�n�rer les documents PDF, et <a href="http://sourceforge.net/projects/pyexcelerator">pyExcelerator</a> pour le traitement des documents Excel.</p>')
        H.append( "<h2>Derni�res �volutions</h2>" + SCONEWS )
        H.append( '<div class="about-logo">' + self.scodoc_img.borgne_img.tag() + ' <em>Au pays des aveugles...</em></div>' )
        d = ''
        # debug
        #import locale
        #g='gon�alves'
        # 
        #d = "<p>locale=%s, g=%s -> %s</p>"% (locale.getlocale(), g, g.lower() )
        return self.sco_header(REQUEST)+ '\n'.join(H) + d + self.sco_footer(REQUEST)

    
    security.declareProtected(ScoView, 'raiseScoValueError')
    def raiseScoValueError(self,msg):
        """raise ScoValueError exception
        (used from legacy dtml code, where class-based exception
        cannot be raised...)
        """
        raise ScoValueError(msg)

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
    def formChercheEtud(self, REQUEST=None, dest_url=None, parameters=None, parameters_keys=None):
        "form recherche par nom"
        H = [ """<form action="chercheEtud" method="POST">
        <b>Rechercher un &eacute;tudiant par nom&nbsp;: </b>
        <input type="text" name="expnom" width=12 value="">
        <input type="submit" value="Chercher">
        <br/>(entrer une partie du nom)
        """ ]
        if dest_url:
            H.append('<input type="hidden" name="dest_url" value="%s"/>' % dest_url)
        if parameters:
            for param in parameters.keys():
                H.append('<input type="hidden" name="%s" value="%s"/>'
                         % (param, parameters[param]))
            H.append('<input type="hidden" name="parameters_keys" value="%s"/>'%(','.join(parameters.keys())))
        elif parameters_keys:
            for key in parameters_keys.split(','):
                v = REQUEST.form.get(key,False)
                if v:
                    H.append('<input type="hidden" name="%s" value="%s"/>'%(key,v))
            H.append('<input type="hidden" name="parameters_keys" value="%s"/>'%parameters_keys)
        H.append('</form>')
        return '\n'.join(H)
    
    security.declareProtected(ScoView, 'formChoixSemestreGroupe')
    def formChoixSemestreGroupe(self, all=False):
        """partie de formulaire pour le choix d'un semestre et d'un groupe.
        Si all, donne tous les semestres (meme ceux verrouill�s).
        """
        # XXX assez primitif, a ameliorer
        if all:
            sems = self.Notes.do_formsemestre_list()
        else:
            sems = self.Notes.do_formsemestre_list( args={'etat':'1'} )
        H = ['<select name="semestregroupe">']
        nbgroups = 0
        for sem in sems:
            formsemestre_id = sem['formsemestre_id']
            H.append( self.formChoixGroupe(formsemestre_id, prefix=formsemestre_id) )
        H.append('</select>')
        return '\n'.join(H)    

    security.declareProtected(ScoView, 'formChoixGroupe')
    def formChoixGroupe(self, formsemestre_id, prefix=''):
        """Partie de formulaire pour le choix d'un groupe.
        Le groupe sera cod� comme prefix!x!y!z
        groupe TD:   td!!, groupe TA !!ta, groupe tp !tp!        
        """
        # XXX assez primitif, a ameliorer
        sem = self.Notes.get_formsemestre(formsemestre_id)

        H = []
        nbgroups = 0
        gr_td,gr_tp,gr_anglais = self.Notes.do_formsemestre_inscription_listegroupes(formsemestre_id=formsemestre_id)
        for gr in gr_td:
            tmpl = '<option value="%s!%s!!">%s: %s %s</option>'
            H.append( tmpl %(prefix,gr,sem['titreannee'],sem['nomgroupetd'],gr))
            nbgroups += 1
        for gr in gr_anglais:
            tmpl = '<option value="%s!!!%s">%s: %s %s</option>'
            H.append( tmpl %(prefix,gr,sem['titreannee'],sem['nomgroupeta'], gr))
            nbgroups += 1
        for gr in gr_tp:
            tmpl = '<option value="%s!!%s!">%s: %s %s</option>'
            H.append( tmpl %(prefix,gr,sem['titreannee'],sem['nomgroupetp'], gr))
            nbgroups += 1
        if nbgroups == 0:
            return '' # aucun groupe, pas de choix
        return '\n'.join(H) 

    # -----------------  BANDEAUX -------------------
    security.declareProtected(ScoView, 'sidebar')
    #sidebar = DTMLFile('dtml/sidebar', globals())
    sidebar = html_sidebar.sidebar
    
    security.declareProtected(ScoView, 'showEtudLog')
    def showEtudLog(self, etudid, format='html', REQUEST=None):
        """Display log of operations on this student"""
        etud = self.getEtudInfo(filled=1, REQUEST=REQUEST)[0]

        ops = self.listScoLog(etudid)
        
        tab = GenTable( titles={ 'date' : 'Date', 'authenticated_user' : 'Utilisateur',
                                 'remote_addr' : 'IP', 'method' : 'Op�ration',
                                 'msg' : 'Message'},
                        columns_ids=('date', 'authenticated_user', 'remote_addr', 'method', 'msg'),
                        rows=ops,
                        html_sortable=True,
                        html_class='gt_table table_leftalign',
                        base_url = '%s?etudid=%s' % (REQUEST.URL0, etudid),
                        page_title='Op�rations sur %(nomprenom)s' % etud,
                        html_title="<h2>Op�rations effectu�es sur l'�tudiant %(nomprenom)s</h2>" % etud,
                        filename='log_'+make_filename(etud['nomprenom']),
                        html_next_section='<ul><li><a href="ficheEtud?etudid=%(etudid)s">fiche de %(nomprenom)s</a></li></ul>' % etud)
        
        return tab.make_page(self, format=format, REQUEST=REQUEST)
                                 
    def listScoLog(self,etudid):
        "liste des operations effectuees sur cet etudiant"
        cnx = self.GetDBConnexion()
        cursor = cnx.cursor()
        cursor.execute("select * from scolog where etudid=%(etudid)s ORDER BY DATE DESC",
                       {'etudid':etudid})
        return cursor.dictfetchall()
    #
    security.declareProtected(ScoView, 'getZopeUsers')
    def getZopeUsers(self):
        "liste des utilisateurs zope"
        l = self.acl_users.getUserNames()
        l.sort()
        return l

    # ----------  PAGE ACCUEIL (listes) --------------
    security.declareProtected(ScoView, 'index_html')
    def index_html(self,REQUEST=None, showcodes=0, showlocked=0):
        "page accueil sco"
        showlocked=int(showlocked)
        H = []
        # news
        rssicon = self.scodoc_img.rssicon_img.tag(title='Flux RSS', border='0') 
        H.append( sco_news.scolar_news_summary_html(self, rssicon=rssicon) )

        # liste de toutes les sessions
        sems = self.Notes.do_formsemestre_list()
        now = time.strftime( '%Y-%m-%d' )

        cursems = []   # semestres "courants"
        othersems = [] # autres (anciens ou futurs)
        # icon image:
        groupicon = self.scodoc_img.groupicon_img.tag(title="Inscrits",
                                               border='0') 
        emptygroupicon = self.scodoc_img.emptygroupicon_img.tag(title="Pas d'inscrits",
                                                         border='0')
        lockicon = self.scodoc_img.lock32_img.tag(title="verrouill�", border='0')
        # selection sur l'etat du semestre
        for sem in sems:
            if sem['etat'] == '1':
                sem['lockimg'] = ''
                cursems.append(sem)
            else:
                sem['lockimg'] = lockicon
                othersems.append(sem)
            # Responsable de formation:
            user_info = self.Users.user_info(sem['responsable_id'], REQUEST)
            sem['responsable_name'] = user_info['nomprenom']
            if showcodes=='1':
                sem['tmpcode'] = '<td><tt>%s</tt></td>' % sem['formsemestre_id']
            else:
                sem['tmpcode'] = ''
            # Nombre d'inscrits:
            args = { 'formsemestre_id' : sem['formsemestre_id'] }
            ins = self.Notes.do_formsemestre_inscription_list( args=args )
            nb = len(ins) # nb etudiants
            if nb > 0:
                sem['groupicon'] = groupicon
            else:
                sem['groupicon'] = emptygroupicon
        
        # liste des fomsemestres "courants"
        if cursems:
            H.append('<h2 class="listesems">Semestres en cours</h2>')
            H.append(self._sem_table(cursems))
        
        else:
            # aucun semestre courant: affiche aide
            H.append("""<h2 class="listesems">Aucun semestre courant !</h2>
            <p>Pour ajouter un semestre, aller dans <a href="Notes">Programmes</a>,
            choisissez une formation, puis suivez le lien "<em>UE, modules, semestres</em>".
            </p><p>
            L�, en bas de page, suivez le lien
            "<em>Mettre en place un nouveau semestre de formation...</em>"
            </p>""")
        
        if othersems and showlocked:
            H.append("""<hr/>
            <h2>Semestres termin�s (non modifiables)</h2>
            """)            
            H.append(self._sem_table(othersems))
            H.append('</table>')
        if not showlocked:
            H.append('<hr/><p><a href="%s?showlocked=1">Montrer les semestres verrouill�s</a></p>' % REQUEST.URL0)
        #
        authuser = REQUEST.AUTHENTICATED_USER
        if authuser.has_permission(ScoEtudInscrit,self):
            H.append("""<hr>
            <h3>Gestion des �tudiants</h3>
            <ul>
            <li><a class="stdlink" href="etudident_create_form">cr�er <em>un</em> nouvel �tudiant</a></li>
            <li><a class="stdlink" href="form_students_import_excel">importer de nouveaux �tudiants</a> (ne pas utiliser sauf cas particulier, utilisez plut�t le lien dans
            le tableau de bord semestre si vous souhaitez inscrire les
            �tudiants import�s � un semestre)</li>
            </ul>
            """)
        #
        return self.sco_header(REQUEST)+'\n'.join(H)+self.sco_footer(REQUEST)

    def _sem_table(self, sems):
        tmpl = """<tr>%(tmpcode)s
        <td class="semicon">%(lockimg)s <a href="Notes/formsemestre_status?formsemestre_id=%(formsemestre_id)s#groupes">%(groupicon)s</a></td>        
        <td class="datesem">%(mois_debut)s - %(mois_fin)s</td>
        <td><a class="stdlink" href="Notes/formsemestre_status?formsemestre_id=%(formsemestre_id)s">%(titre_num)s</a>
        <span class="respsem">(%(responsable_name)s)</span>
        </td>
        </tr>
        """
        # " (this quote fix a font lock bug)
        H = ['<table class="listesems">']
        # diff�rentes modalit�s ?
        modalites = list(Set([s['modalite'] for s in sems]))
        # tri selon un ordre fix�:
        modalites.sort( lambda x,y: cmp(MODALITY_ORDER[x],MODALITY_ORDER[y]))
        sems_by_mod = DictDefault(defaultvalue=[])
        for modalite in modalites:
            for sem in sems:
                if sem['semestre_id'] < 0:
                    sem['sortkey'] = (-100*sem['semestre_id'],sem['dateord'])
                else:
                    sem['sortkey'] = (sem['semestre_id'],sem['dateord'])
                if sem['modalite'] == modalite:
                    sems_by_mod[modalite].append(sem)
        
        for modalite in modalites:
            if len(modalites) > 1:
                H.append('<tr><th colspan="3">%s</th></tr>' % MODALITY_NAMES[modalite])
            # tri dans chaque modalit� par indice de semestre et date debut
            sems_by_mod[modalite].sort(
                lambda x,y: cmp(x['sortkey'],y['sortkey']))
            for sem in sems_by_mod[modalite]:
                H.append( tmpl % sem )
        H.append('</table>')
        return '\n'.join(H)
    
    security.declareProtected(ScoView, 'index_html')
    def rssnews(self,REQUEST=None):
        "rss feed"
        REQUEST.RESPONSE.setHeader('Content-type', XML_MIMETYPE)
        return sco_news.scolar_news_summary_rss(self, 'Nouvelles de ' + self.DeptName,
                                                 self.ScoURL() )
        
    # genere liste html pour acces aux groupes TD/TP/TA de ce semestre
    def make_listes_sem(self, sem, REQUEST=None, with_absences=True):
        authuser = REQUEST.AUTHENTICATED_USER
        r = self.ScoURL() # root url
        H = []
        # pas de menu absences si pas autorise:
        if with_absences and not authuser.has_permission(ScoAbsChange,self):
            with_absences = False

        #
        H.append('<h3>Listes de %(titre)s <span class="infostitresem">(%(mois_debut)s - %(mois_fin)s)</span></h3>' % sem )
        # cherche les groupes de ce semestre
        formsemestre_id = sem['formsemestre_id']
        gr_td,gr_tp,gr_anglais = self.Notes.do_formsemestre_inscription_listegroupes(formsemestre_id=formsemestre_id)
        # calcule dates 1er jour semaine pour absences
        if with_absences:
            first_monday = ZAbsences.ddmmyyyy(sem['date_debut']).prev_monday()
            FA = [] # formulaire avec menu saisi absences
            FA.append('<td><form action="Absences/SignaleAbsenceGrSemestre" method="GET">')
            FA.append('<input type="hidden" name="datefin" value="%(date_fin)s"/>'
                             % sem )
            FA.append('<input type="hidden" name="semestregroupe" value="%s!%%s"/>'
                     % (formsemestre_id,) )
            FA.append('<input type="hidden" name="destination" value="%s?%s"/>'
                     % (REQUEST.URL, REQUEST.QUERY_STRING))
            FA.append('<input type="submit" value="Saisir absences du" />')
            FA.append('<select name="datedebut" class="noprint">')
            date = first_monday
            for jour in self.Absences.day_names():
                FA.append('<option value="%s">%s</option>' % (date, jour) )
                date = date.next()
            FA.append('</select>')
            FA.append('<a href="Absences/EtatAbsencesGr?semestregroupe=%(formsemestre_id)s!%%s&debut=%(date_debut)s&fin=%(date_fin)s">�tat</a>' % sem )
            FA.append('</form></td>')
            FormAbs = '\n'.join(FA)
        else:
            FormAbs = ''
        #
        H.append('<div id="grouplists">')
        # Genere liste pour chaque categorie de groupes
        for (groupes, nomgroupe, semnomgroupe, grmask) in (
            (gr_td, 'groupetd', 'nomgroupetd', '%s!!'),
            (gr_anglais, 'groupeanglais', 'nomgroupeta', '!!%s'),
            (gr_tp, 'groupetp', 'nomgroupetp', '!%s!')
            ):
            if groupes:
                H.append('<h4>Groupes de %s</h4>' % sem[semnomgroupe])
                H.append('<table>')
                for gr in groupes:
                    args = { 'formsemestre_id' : formsemestre_id, nomgroupe : gr }
                    ins = self.Notes.do_formsemestre_inscription_list( args=args )
                    nb = len(ins) # nb etudiants
                    H.append('<tr class="listegroupelink">')
                    H.append("""<td>
                    <a href="%s/listegroupe?formsemestre_id=%s&%s=%s">groupe %s</a>
                    </td><td>
                    (<a href="%s/listegroupe?formsemestre_id=%s&%s=%s&format=xls">format tableur</a>)
                    <a href="%s/trombino?formsemestre_id=%s&%s=%s&etat=I">Photos</a>
                    </td><td>(%d �tudiants)</td>
                    """ % (r, formsemestre_id, nomgroupe, gr, gr,
                           r, formsemestre_id, nomgroupe, gr,
                           r, formsemestre_id, nomgroupe, gr,
                           nb))
                    if with_absences:
                        H.append( FormAbs % ((grmask % gr),(grmask % gr)) )
                    H.append('</tr>')
                H.append('</table>')
        
        if len(gr_td) > 1:
            args = { 'formsemestre_id' : formsemestre_id }
            ins = self.Notes.do_formsemestre_inscription_list( args=args )
            nb = len(ins) # nb etudiants
            H.append("""<br/><p class="listegroupelink">
            <a href="%s/listegroupe?formsemestre_id=%s">Tous les �tudiants de %s</a>
            (<a href="%s/listegroupe?formsemestre_id=%s&format=xls">format tableur</a>)
            <a href="%s/trombino?formsemestre_id=%s&etat=I">Photos</a>
            <br/> (%d �tudiants)
            """ % (r,formsemestre_id,sem['titre_num'],r,formsemestre_id,r,formsemestre_id,nb))
            H.append("""
            (<a href="Absences/EtatAbsencesGr?semestregroupe=%(formsemestre_id)s!!!&debut=%(date_debut)s&fin=%(date_fin)s">�tat des absences</a>)
            </p>
            """ % sem )
        H.append('</div>')

        return H

    def _make_query_groups(self,groupetd,groupetp,groupeanglais,etat):
        "query string"
        qs = []
        if groupetd:
            qs.append('groupetd=%s' % groupetd)
        if groupetp:
            qs.append('groupetp=%s' % groupetp)
        if groupeanglais:
            qs.append('groupeanglais=%s' % groupeanglais)
        if etat:
            qs.append('etat=%s' % etat)
        return '&'.join(qs)

    security.declareProtected(ScoView, 'listegroupe')
    def listegroupe(self, 
                    formsemestre_id, REQUEST=None,
                    groupetd='', groupetp='', groupeanglais='',
                    with_codes=0,
                    all_groups=0,
                    etat=None,
                    format='html' ):
        """liste etudiants inscrits dans ce semestre
        format: html, csv, xls, xml, allxls (XXX futur: pdf)
        Si with_codes, ajoute 3 colonnes avec les codes etudid, NIP, INE
        Si all_groupes, donne les 3 groupes (3 colonnes)
        """
        authuser = REQUEST.AUTHENTICATED_USER
        T, nomgroupe, ng, sem, nbdem = self._getlisteetud(formsemestre_id,
                                                   groupetd,groupetp,groupeanglais,etat )
        if not nomgroupe:
            nomgroupe = 'tous'

        with_codes = int(with_codes)
        all_groups = int(all_groups)
        base_url = '%s?formsemestre_id=%s&groupetd=%s&groupetp=%s&groupeanglais=%s&with_codes=%s&all_groups=%s' % (REQUEST.URL0,formsemestre_id,groupetd,groupetp,groupeanglais,with_codes,all_groups)
        
        #
        columns_ids=['nom', 'prenom', 'groupetd']
        if all_groups:
            columns_ids += ['groupeta','groupetp']
        if format != 'html':
            columns_ids.append('etat')
        columns_ids.append('email')
        if with_codes:
            columns_ids += ['etudid', 'code_nip', 'code_ine']
        # ajoute liens
        for t in T:
            t['_email_target'] = 'mailto:' + t['email']
            t['_nom_target'] = 'ficheEtud?etudid=' + t['etudid']
            t['_prenom_target'] = 'ficheEtud?etudid=' + t['etudid']
        if nbdem > 1:
            s = 's'
        else:
            s = ''
        
        tab = GenTable( rows=T, columns_ids=columns_ids, 
                        titles={ 'nom' : 'Nom', 'prenom' : 'Pr�nom',
                                 'groupetd' : sem['nomgroupetd'],
                                 'groupeta' : sem['nomgroupeta'],
                                 'groupetp' : sem['nomgroupetp'],
                                 'email' : 'Mail',
                                 'etat':'Etat',
                                 'etudid':'etudid',
                                 'code_nip':'code_nip', 'code_ine':'code_ine'
                                 },
                        caption='soit %d �tudiants inscrits et %d d�missionaire%s.' % (len(T)-nbdem,nbdem,s),
                        base_url=base_url,
                        pdf_link=False, # pas d'export pdf
                        html_sortable=True,
                        html_class='gt_table table_leftalign table_listegroupe')
        #
        if format == 'html':
            H = [ '<h2>Etudiants de <a href="Notes/formsemestre_status?formsemestre_id=%s">%s</a> %s</h2>' % (formsemestre_id, sem['titreannee'], ng) ]
            
            H.append(tab.html())
            
            amail=','.join([x['email'] for x in T ])
            H.append('<ul>')
            H.append("""<li><a class="stdlink" href="%s&format=xls">Feuille d'�margement</a></li>"""
                     % base_url)
            H.append("""<li><a class="stdlink" href="trombino?formsemestre_id=%s&groupetd=%s&groupetp=%s&groupeanglais=%s&etat=I">Photos</a></li>"""
                     % (formsemestre_id,groupetd,groupetp,groupeanglais))
            H.append('<li><a class="stdlink" href="mailto:%s">Envoyer un mail collectif au groupe %s</a></li>' % (amail,nomgroupe))
            # Lien pour verif codes INE/NIP
            if authuser.has_permission(ScoEtudInscrit,self):
                H.append('<li><a class="stdlink" href="check_group_apogee?formsemestre_id=%s&%s">V�rifier codes Apog�e</a></li>'
                         % (formsemestre_id,
                            self._make_query_groups(groupetd,groupetp,groupeanglais,etat)))
            
            H.append('</ul>')
            
            return self.sco_header(REQUEST)+'\n'.join(H)+self.sco_footer(REQUEST)
        
        elif format=='pdf':
            return tab.make_page(self, format=format, REQUEST=REQUEST)
        
        elif format == 'csv':
            Th = [ x[k] for k in columns_ids ]
            fs = [ (t['nom'], t['prenom'], t['groupetd'], t['etat'], t['email']) for t in T ]
            CSV = CSV_LINESEP.join( [ CSV_FIELDSEP.join(x) for x in [Th]+fs ] )
            title = 'liste_%s' % nomgroupe
            filename = title + '.csv'
            return sendCSVFile(REQUEST,CSV, filename )
        
        elif format == 'xls':
            title = 'liste_%s' % nomgroupe
#             xls = sco_excel.Excel_SimpleTable(
#                 titles= [ 'Nom', 'Pr�nom', 'Groupe', 'Etat', 'Mail' ],
#                 lines = lines,
#                 SheetName = title )
            xls = sco_excel.Excel_feuille_listeappel(self, sem, nomgroupe, T,
                                                     all_groups=all_groups,
                                                     with_codes=with_codes,
                                                     server_name=REQUEST.BASE0)
            filename = title + '.xls'
            return sco_excel.sendExcelFile(REQUEST, xls, filename )
        elif format == 'allxls':
            # feuille Excel avec toutes les infos etudiants
            Ld = [ self.getEtudInfo(etudid=i['etudid'],filled=True)[0] for i in T ]
            if not Ld:
                return ''            
            cols = Ld[0].keys()
            def dicttakestr(d, keys):
                r = []
                for k in keys:
                    r.append(str(d[k]))
                return r
            keys = ('etudid', 'code_nip', 'etatincursem',
                    'sexe', 'nom','prenom',
                    'inscriptionstr', 'groupetd', 'groupeanglais', 'groupetp',
                    'email', 'domicile', 'villedomicile', 'codepostaldomicile', 'paysdomicile',
                    'telephone', 'telephonemobile', 'fax',
                    'annee_naissance',
                    'bac', 'specialite', 'annee_bac',
                    'nomlycee', 'villelycee',
                    )
            L = [ dicttakestr(d, keys) for d in Ld ]
            title = 'etudiants_%s' % nomgroupe
            xls = sco_excel.Excel_SimpleTable(
                titles=keys,
                lines = L,
                SheetName = title )
            filename = title + '.xls'
            return sco_excel.sendExcelFile(REQUEST, xls, filename)
        
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
            a = dict_quote_xml_attr(a)
            doc.groupe( **a )
            doc._push()
            for t in T:
                a = { 'etudid' : t['etudid'],
                      'nom' : t['nom'], 'prenom' : t['prenom'],
                      'groupe' : t['groupetd'], # backward compat
                      'groupetd' : t['groupetd'],
                      'groupeta' : t['groupeta'],
                      'groupetp' : t['groupetp'],
                      'etat' : t['etat'], 
                      'mail' : 'email' }
                doc._push()
                a = dict_quote_xml_attr(a)
                doc.etudiant(**a)
                doc._pop()
            doc._pop()
            return repr(doc)
        else:
            raise ValueError('unsupported format')

    security.declareProtected(ScoView,'trombino')
    trombino = sco_trombino.trombino

    security.declareProtected(ScoView,'trombino_copy_photos')
    trombino_copy_photos = sco_trombino.trombino_copy_photos

    def _getlisteetud(self, formsemestre_id,
                      groupetd=None, groupetp=None, groupeanglais=None, etat=None ):
        """utilise par listegroupe et trombino
        ( liste de dicts t,  nomgroupe, ng, sem, nbdem )
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
            t = { 'nom' :format_nom(etud['nom']),
                  'prenom' : format_prenom(etud['prenom']),
                  'sexe' : etud['sexe'],
                  'etud' : etud['etudid'],
                  'email' : scolars.getEmail(cnx,etud['etudid']),
                  'etat' : i['etat'],
                  'groupetd' : i['groupetd'],
                  'groupeta' : i['groupeanglais'],
                  'groupetp' : i['groupetp'],
                  'foto' : etud['foto'],
                  'etudid' : etud['etudid'],
                  'code_ine' : etud['code_ine'],
                  'code_nip' : etud['code_nip']
                  }
            if t['etat'] == 'I':
                t['etath'] = '' # etudiant inscrit, ne l'indique pas dans la liste HTML
            elif t['etat'] == 'D':
                t['etath'] = '(dem.)'
                nbdem += 1
            T.append(t)
        def cmpnom(x,y):
            return cmp( x['nom'], y['nom'] )
        T.sort(cmpnom) # sort by nom
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
        sem = self.Notes.do_formsemestre_list(
            args={'formsemestre_id':formsemestre_id} )[0]
        args,nomgroupe=self._make_groupes_args(groupetd,groupetp,groupeanglais,
                                               etat)
        args['formsemestre_id'] = formsemestre_id
        ins = self.Notes.do_formsemestre_inscription_list( args=args )
        etuds = []
        for i in ins:
            etud = self.getEtudInfo(etudid=i['etudid'],filled=True)[0]
            etuds.append(etud)
        # tri par nom
        etuds.sort( lambda x,y: cmp(x['nom'],y['nom']) )
        return etuds
        
    # -------------------------- INFOS SUR ETUDIANTS --------------------------
    security.declareProtected(ScoView, 'getEtudInfo')
    def getEtudInfo(self,etudid=False,filled=False,REQUEST=None):
        """infos sur un etudiant pour utilisation en Zope DTML
        On peut specifier etudid
        ou bien cherche dans REQUEST.form: etudid, code_nip, code_ine
        (dans cet ordre).
        """
        if etudid is None:
            return []
        cnx = self.GetDBConnexion()
        args = make_etud_args(etudid=etudid,REQUEST=REQUEST)
        etud = scolars.etudident_list(cnx,args=args)
        if filled:
            self.fillEtudsInfo(etud)
        return etud

    security.declareProtected(ScoView, 'log_unknown_etud')
    def log_unknown_etud(self, REQUEST=None):
        """Log request: cas ou getEtudInfo n'a pas ramene de resultat"""
        etudid = REQUEST.form.get('etudid', '?')
        code_nip = REQUEST.form.get('code_nip', '?')
        code_ine = REQUEST.form.get('code_ine', '?')
        log("unknown student: etudid=%s code_nip=%s code_ine=%s"
            % (etudid, code_nip, code_ine))
        REQUEST.RESPONSE.setStatus(404, reason='etudiant inconnu')
        raise ScoValueError('etudiant inconnu')
    
    #
    security.declareProtected(ScoView, 'nomprenom')
    def nomprenom(self, etud):
        "formatte sexe/nom/prenom pour affichages"
        return ' '.join([ format_sexe(etud['sexe']), format_prenom(etud['prenom']), format_nom(etud['nom'])])
    
    security.declareProtected(ScoView, "chercheEtud")
    #chercheEtud = DTMLFile('dtml/chercheEtud', globals())
    def chercheEtud(self, expnom=None,
                    dest_url='ficheEtud',
                    parameters={},
                    parameters_keys='',
                    add_headers = True, # complete page
                    title=None,
                    REQUEST=None ):
        """Page recherche d'un etudiant
        expnom est un regexp sur le nom
        dest_url est la page sur laquelle on sera redirig� apr�s choix
        parameters sp�cifie des arguments additionnels a passer � l'URL (en plus de etudid)
        """
        q = []
        if parameters:
            for param in parameters.keys():
                q.append( '%s=%s' % (param, parameters[param]))
        elif parameters_keys:
            for key in parameters_keys.split(','):
                v = REQUEST.form.get(key,False)
                if v:
                    q.append( '%s=%s' % (key,v) )
        query_string = '&'.join(q)
        
        H = []
        if title:
            H.append('<h2>%s</h2>'%title)
        if expnom:
            etuds = self.chercheEtudsInfo(expnom=expnom,REQUEST=REQUEST)
            if len(etuds) == 1:
                # va directement a la destination
                return REQUEST.RESPONSE.redirect( dest_url + '?etudid=%s&' % etuds[0]['etudid'] + query_string )

            if len(etuds) > 0:
                # Choix dans la liste des r�sultats:
                H.append('<h2>%d r�sultats pour "%s": choisissez un �tudiant:</h2>' % (len(etuds),expnom))
                H.append('<table cellspacing="0" cellpadding ="3" border="0" bgcolor="#ccffff">')
                i = 0
                for etud in etuds:
                    if i % 2 == 0:
                        bgcolor = '#ffffcc'
                    else:
                        bgcolor = '#ccffff'
                    i += 1
                    H.append('<tr bgcolor="%s"><td>%s</td><td><a class="discretelink" href="%s"><b>%s</b> %s</a></td><td>%s %s</tr>'
                             % (bgcolor, format_sexe(etud['sexe']),
                                dest_url + '?etudid=%s&' % etud['etudid'] + query_string,
                                format_nom(etud['nom']), format_prenom(etud['prenom']),
                                etud['inscription'], etud['groupetd']) )
                H.append('</table>')
            else:
                H.append('<h2 style="color: red;">Aucun r�sultat pour "%s".</h2>' % expnom )

        H.append(self.formChercheEtud(dest_url=dest_url,
                                      parameters=parameters, parameters_keys=parameters_keys, REQUEST=REQUEST))
        
        if add_headers:
            return self.sco_header(REQUEST, page_title='Choix d\'un �tudiant', no_side_bar=True) + '\n'.join(H) + self.sco_footer(REQUEST)
        else:
            return '\n'.join(H)
    
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
                etud['emaillink'] = '<a class="stdlink" href="mailto:%s">%s</a>'%(etud['email'],etud['email'])
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
            # trie les semestres par date de debut, le plus recent d'abord
            # (important, ne pas changer (suivi cohortes))
            sems.sort( lambda x,y: cmp(y['dateord'], x['dateord']) )
            etud['sems'] = sems
            etud['cursem'] = cursem
            if cursem:
                etud['inscription'] = cursem['titreannee']
                etud['inscriptionstr'] = 'Inscrit en ' + cursem['titreannee']
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
            etud['situation'] = self.descr_situation_etud(etudid,etud['ne'])
            # nettoyage champs souvents vides
            if etud['nomlycee']:
                etud['ilycee'] = 'Lyc�e ' + format_lycee(etud['nomlycee'])
                if etud['villelycee']:
                    etud['ilycee'] += ' (%s)' % etud['villelycee']
                etud['ilycee'] += '<br/>'
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
    def XMLgetEtudInfos(self, etudid=None, REQUEST=None):
        "Donne les informations sur un etudiant"
        args = make_etud_args(etudid=etudid,REQUEST=REQUEST)
        doc = jaxml.XML_document( encoding=SCO_ENCODING )
        REQUEST.RESPONSE.setHeader('Content-type', XML_MIMETYPE)
        cnx = self.GetDBConnexion()
        etuds = scolars.etudident_list(cnx, args)
        if not etuds:
            # etudiant non trouv�: message d'erreur en XML
            doc.etudiant( etudid=etudid, nom='?', prenom='?', sexe='?',
                          email='?', error='code inconnu')
            return repr(doc)
        
        etud = etuds[0]
        self.fillEtudsInfo([etud])

        doc.etudiant( etudid=etudid, code_nip=etud['code_nip'], code_ine=etud['code_ine'],
                      nom=quote_xml_attr(etud['nom']),
                      prenom=quote_xml_attr(etud['prenom']),
                      sexe=quote_xml_attr(etud['sexe']),
                      nomprenom=quote_xml_attr(etud['nomprenom']),
                      email=quote_xml_attr(etud['email']),
                      photo_url=quote_xml_attr(self.etudfoto_url(etudid)))
        doc._push()
        sem = etud['cursem']
        if sem:
            doc._push()
            doc.insemestre( current='1',
                            formsemestre_id=sem['formsemestre_id'],
                            date_debut=DateDMYtoISO(sem['date_debut']),
                            date_fin=DateDMYtoISO(sem['date_fin']),
                            groupetd=quote_xml_attr(sem['ins']['groupetd']),
                            groupeta=quote_xml_attr(sem['ins']['groupeanglais']),
                            groupetp=quote_xml_attr(sem['ins']['groupetp']),
                            etat=quote_xml_attr(sem['ins']['etat'])
                            )
            doc._pop()
        for sem in etud['sems']:
            if sem != etud['cursem']:
                doc._push()
                doc.insemestre( 
                    formsemestre_id=sem['formsemestre_id'],
                    date_debut=DateDMYtoISO(sem['date_debut']),
                    date_fin=DateDMYtoISO(sem['date_fin']),
                    groupetd=quote_xml_attr(sem['ins']['groupetd']),
                    groupeta=quote_xml_attr(sem['ins']['groupeanglais']),
                    groupetp=quote_xml_attr(sem['ins']['groupetp']),
                    etat=quote_xml_attr(sem['ins']['etat'])
                    )
                doc._pop()
        doc._pop()
        return repr(doc)

    # -------------------------- FICHE ETUDIANT --------------------------
    security.declareProtected(ScoView, 'ficheEtud')
    def ficheEtud(self,etudid=None,REQUEST=None):
        "fiche d'informations sur un etudiant"
        authuser = REQUEST.AUTHENTICATED_USER
        cnx = self.GetDBConnexion()
        args = make_etud_args(etudid=etudid,REQUEST=REQUEST)
        etud = scolars.etudident_list(cnx, args)[0]
        etudid = etud['etudid']
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
            info['telephones'] = '<br/>%s &nbsp;&nbsp; %s' % (info['telephonestr'],
                                                             info['telephonemobilestr']) 
        else:
            info['telephones'] = ''
        # champs dependant des permissions
        if authuser.has_permission(ScoEtudChangeAdr,self):
            info['modifadresse'] = '<a class="stdlink" href="formChangeCoordonnees?etudid=%s">modifier adresse</a>' % etudid
        else:
            info['modifadresse'] = ''
        # Liste des inscriptions
        ilist = []
        for sem in info['sems']:
            data = sem.copy()
            data.update(info)
            data.update(sem['ins'])
            locked = (sem['etat'] != '1')
            i = sem['ins']
            if data['etat'] == 'D':
                data['grlink'] = '(d�mission)'
            else:                
                data['grlink'] = '<a class="discretelink" href="listegroupe?formsemestre_id=%(formsemestre_id)s&groupetd=%(groupetd)s">groupe %(groupetd)s</a>' % data
            ilist.append("""<table><tr>
            <td>%(mois_debut)s - %(mois_fin)s <a href="Notes/formsemestre_status?formsemestre_id=%(formsemestre_id)s">%(titre_num)s</a> %(grlink)s
            </td><td><div class="barrenav">
            <ul class="nav"><li><a href="Notes/formsemestre_bulletinetud?formsemestre_id=%(formsemestre_id)s&etudid=%(etudid)s" class="menu bulletin">bulletin</a></li></ul>
            </div></td>"""
                         % data )

            if authuser.has_permission(ScoEtudChangeGroups,self) or authuser.has_permission(ScoEtudInscrit,self):
                # menu pour action sur etudiant
                ilist.append("""<td><div class="barrenav"><ul class="nav"><li onmouseover="MenuDisplay(this)" onmouseout="MenuHide(this)"><a href="#"
                    class="menu direction_etud">Scolarit�</a><ul>""") # "

                if authuser.has_permission(ScoEtudChangeGroups,self) and not locked:
                    ilist.append('<li><a href="formChangeGroupe?etudid=%s&formsemestre_id=%s">changer de groupe</a></li>' % (etudid,i['formsemestre_id']) )
                if authuser.has_permission(ScoEtudInscrit,self) and not locked:
                    args = { 'etudid' : etudid,
                             'formsemestre_id' : i['formsemestre_id'] }
                    if data['etat'] != 'D':
                        ilist.append("""
                        <li><a href="formDem?etudid=%(etudid)s&formsemestre_id=%(formsemestre_id)s">D&eacute;mission</a></li>""" % args )
                    else: # demissionnaire
                        ilist.append("""
                        <li><a href="doCancelDem?etudid=%(etudid)s&formsemestre_id=%(formsemestre_id)s">Annuler la d&eacute;mission</a></li>""" % args )
                    ilist.append("""
                    <li><a href="Notes/formsemestre_validation_etud_form?etudid=%(etudid)s&formsemestre_id=%(formsemestre_id)s">Validation du semestre</a></li>
                    <li><a href="Notes/formsemestre_inscription_option?formsemestre_id=%(formsemestre_id)s&etudid=%(etudid)s">Inscrire � un module optionnel (ou au sport)</a></li>
                    <li><a href="Notes/formsemestre_desinscription?formsemestre_id=%(formsemestre_id)s&etudid=%(etudid)s">d�inscrire (en cas d'erreur)</a></li>
                    """ % args )
                if authuser.has_permission(ScoEtudInscrit,self):
                    ilist.append('<li><a href="Notes/formsemestre_inscription_with_modules_form?etudid=%(etudid)s">Inscrire � un autre semestre</a></li>'%{ 'etudid' : etudid})
                ilist.append('</ul></ul>')
                
                ilist.append('</div></td>')
            ilist.append('</tr></table>')
        if not ilist:
            ilist.append('<p><b>Etudiant%s non inscrit%s'%(info['ne'],info['ne']))
            if authuser.has_permission(ScoEtudInscrit,self):
                ilist.append('<a href="%s/Notes/formsemestre_inscription_with_modules_form?etudid=%s">inscrire</a></li>'%(self.ScoURL(),etudid))
            ilist.append('</b></b>')
                
        info['liste_inscriptions'] = '\n'.join(ilist)
        if info['sems']:
            info['last_formsemestre_id'] = info['sems'][0]['formsemestre_id']
        else:
            info['last_formsemestre_id'] = ''
        info['ScoURL'] = self.ScoURL()
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
            alist.append('<tr><td bgcolor="%(bgcolor)s">Le %(date)s par <b>%(author)s</b> (%(zope_authenticated_user)s) : <br/>%(comment)s</td></tr>' % a )
        info['liste_annotations'] = '\n'.join(alist)
        # fiche admission
        has_adm_notes = info['math'] or info['physique'] or info['anglais'] or info['francais']
        has_bac_info = info['bac'] or info['specialite'] or info['annee_bac']
        if has_bac_info or has_adm_notes:
            if has_adm_notes:
                adm_tmpl = """<!-- Donnees admission -->
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
"""
            else:
                adm_tmpl = """<!-- Donnees admission (pas de notes) -->
<div class="ficheadmission">
<p class="fichetitre">Informations admission</p>
<p>Bac %(bac)s (%(specialite)s) obtenu en %(annee_bac)s </p>
<p>%(ilycee)s %(rap)s
</div>
"""
        else:
            adm_tmpl = '' # pas de boite "info admission"
        info['adm_data'] = adm_tmpl % info
        #
        if info['liste_annotations']:
            info['tit_anno'] = '<h4>Annotations</h4>'
        else:
            info['tit_anno'] = '<div style="margin-top: 1em; padding-top: 5px;"></div>'
        # Inscriptions
        if info['sems']:
            rcl = """(<a href="%(ScoURL)s/Notes/formsemestre_validation_etud_form?check=1&etudid=%(etudid)s&formsemestre_id=%(last_formsemestre_id)s&desturl=ficheEtud?etudid=%(etudid)s">r�capitulatif parcours</a>)""" % info
        else:
            rcl = ''
        info['inscriptions_mkup'] = """<div class="ficheinscriptions" id="ficheinscriptions">
<p class="fichetitre">Inscriptions %s</p>
</div>""" % info['liste_inscriptions']
        
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

<span>%(emaillink)s</span> 
</td><td class="photocell">
%(etudfoto)s
</td></tr></table>

<div class="fichesituation">
<div class="fichetablesitu">
<table>
<tr><td class="fichetitre2">Situation :</td><td>%(situation)s</td></tr>
<tr><td class="fichetitre2">Groupe :</td><td>%(groupes)s</td></tr>
<tr><td class="fichetitre2">N�%(ne)s en :</td><td>%(annee_naissance)s</td></tr>
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

%(inscriptions_mkup)s

%(adm_data)s

<div class="ficheannotations">
%(tit_anno)s
<table width="95%%">%(liste_annotations)s</table>

<form action="doAddAnnotation" method="GET" class="noprint">
<input type="hidden" name="etudid" value="%(etudid)s">
<b>Ajouter une annotation sur %(nomprenom)s: </b>
<table><tr>
<tr><td><textarea name="comment" rows="4" cols="50" value=""></textarea>
<br/><font size=-1><i>Balises HTML autoris�es: b, a, i, br, p. Ces annotations sont lisibles par tous les enseignants et le secr�tariat.</i></font>
</td></tr>
<tr><td>Auteur : <input type="text" name="author" width=12 value="%(authuser)s">&nbsp;
<input type="submit" value="Ajouter annotation"></td></tr>
</table>
</form>
</div>

<div class="code_nip">code NIP: %(code_nip)s</div>

</div>
        """                           
        header = self.sco_header(
                    REQUEST,
                    #javascripts=[ 'prototype_1_4_0_js', 'rico_js'],
                    #bodyOnLoad='javascript:bodyOnLoad()',
                    page_title='Fiche �tudiant %(prenom)s %(nom)s'%info )
        return header + tmpl % info + self.sco_footer(REQUEST)

    security.declareProtected(ScoView, 'descr_situation_etud')
    def descr_situation_etud(self, etudid, ne=''):
        """chaine decrivant la situation presente de l'etudiant
        et chaine decrivant son parcours"""
        cnx = self.GetDBConnexion()
        cursor = cnx.cursor()
        cursor.execute("select I.formsemestre_id, I.etat from notes_formsemestre_inscription I,  notes_formsemestre S where etudid=%(etudid)s and S.formsemestre_id = I.formsemestre_id and date_debut < now() and date_fin > now() order by S.date_debut desc;",                       
                       {'etudid' : etudid} )
        r = cursor.dictfetchone()
        if not r:
            situation = 'non inscrit'        
        else:
            sem = self.Notes.do_formsemestre_list(
                {'formsemestre_id' : r['formsemestre_id']} )[0]
            if r['etat'] == 'I':
                situation = 'inscrit%s en %s' % (ne,sem['titreannee'])
                # Cherche la date d'inscription dans scolar_events:
                events = scolars.scolar_events_list(
                    cnx,
                    args={'etudid':etudid, 'formsemestre_id' : sem['formsemestre_id'],
                          'event_type' : 'INSCRIPTION' })                
                if not events:
                    log('*** situation inconsistante pour %s (inscrit mais pas d\'event)'%etudid)
                    date_ins = '???' # ???
                else:
                    date_ins = events[0]['event_date']
                situation += ' le ' + str(date_ins)
            else:
                situation = 'd�mission de %s' % sem['titreannee']
                # Cherche la date de demission dans scolar_events:
                events = scolars.scolar_events_list(
                    cnx,
                    args={'etudid':etudid, 'formsemestre_id' : sem['formsemestre_id'],
                          'event_type' : 'DEMISSION' })                
                if not events:
                    log('*** situation inconsistante pour %s (demission mais pas d\'event)'%etudid)
                    date_dem = '???' # ???
                else:
                    date_dem = events[0]['event_date']
                situation += ' le ' + str(date_dem)
        return situation

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
            REQUEST, page_title='Changement adresse de %(prenom)s %(nom)s' % etud )
        
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
            return header + '\n'.join(H) + tf[1] + self.sco_footer(REQUEST)
        elif tf[0] == -1:
            return REQUEST.RESPONSE.redirect( REQUEST.URL1 )
        else:
            if adrs:
                scolars.adresse_edit( cnx, args=tf[2], context=self )
            else:
                scolars.adresse_create( cnx, args=tf[2] )
            logdb(REQUEST,cnx,method='changeCoordonnees', etudid=etudid)
            REQUEST.RESPONSE.redirect('ficheEtud?etudid='+etudid)

    security.declareProtected(ScoView, 'formChangeGroupe')
    def formChangeGroupe(self, formsemestre_id, etudid, REQUEST):
        "changement groupe etudiant dans semestre"
        if not self.Notes.can_change_groups(REQUEST, formsemestre_id):
            raise ScoValueError("Vous n'avez pas le droit d'effectuer cette op�ration !")
        cnx = self.GetDBConnexion()
        etud = scolars.etudident_list(cnx, {'etudid':etudid})[0]
        sem = self.Notes.do_formsemestre_list({'formsemestre_id':formsemestre_id})[0]
        ins = self.Notes.do_formsemestre_inscription_list(
            { 'etudid'  : etudid, 'formsemestre_id' : formsemestre_id })[0]
        #
        # -- check lock
        sem = self.Notes.do_formsemestre_list({'formsemestre_id':formsemestre_id})[0]
        if sem['etat'] != '1':
            raise ScoValueError('Modification impossible: semestre verrouille')
        #
        etud['semtitre'] = sem['titreannee']
        H = [ '<h2><font color="#FF0000">Changement de groupe de</font> %(prenom)s %(nom)s (semestre %(semtitre)s)</h2><p>' % etud ]
        header = self.sco_header(
            REQUEST, page_title='Changement de groupe de %(prenom)s %(nom)s'%etud)
        # Liste des groupes existant (== ou il y a des inscrits)
        gr_td,gr_tp,gr_anglais = self.Notes.do_formsemestre_inscription_listegroupes(formsemestre_id=formsemestre_id)
        #
        H.append("""<form action="doChangeGroupe" method="GET" name="cg">
<table>
<tr><th></th><th>%s</th><th>%s</th><th>%s</th></tr>"""
                 % (sem['nomgroupetd'],sem['nomgroupeta'],sem['nomgroupetp']) )
        H.append("""
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
            H.append('<option value="">Aucun</option>')
            H.append('</select></td>')
        H.append('</tr></table>')
        H.append("""<input type="hidden" name="etudid" value="%s">
<input type="hidden" name="formsemestre_id" value="%s">
<p>
(attention, v�rifier que les groupes sont compatibles, selon votre organisation)
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
<input type="button" onClick="tweakmenu( 'groupetd' );" value="cr�er groupe de %s"/>
<input type="button" onClick="tweakmenu( 'groupeanglais' );" value="cr�er groupe de %s"/>
<input type="button" onClick="tweakmenu( 'groupetp' );" value="cr�er groupe de %s"/>
</p>
<p id="groupemsg" style="font-style: italic;"></p>

<input type="submit" value="Changer de groupe">
<input type="button" value="Annuler" onClick="window.location='%s'">

</form>""" % (etudid, formsemestre_id,
              sem['nomgroupetd'], sem['nomgroupeta'], sem['nomgroupetp'], 
              REQUEST.URL1) )
        
        return header + '\n'.join(H) + self.sco_footer(REQUEST)

    security.declareProtected(ScoView, 'doChangeGroupe')
    def doChangeGroupe(self, etudid, formsemestre_id, groupetd=None,
                       groupeanglais=None, groupetp=None, REQUEST=None,
                       redirect=1):
        """Change le groupe. Si la valeur du groupe est '' (vide) ou 'None',
        le met � NULL (aucun groupe).
        """
        if not self.Notes.can_change_groups(REQUEST, formsemestre_id):
            raise ScoValueError("Vous n'avez pas le droit d'effectuer cette op�ration !")
        cnx = self.GetDBConnexion()
        log('doChangeGroupe(etudid=%s,formsemestre_id=%s) len=%d'%(etudid,formsemestre_id, len(formsemestre_id)))
        
        sem = self.Notes.do_formsemestre_list({'formsemestre_id':formsemestre_id})
        #log( 'sem=' + str(sem))

        sem = sem[0]
        if sem['etat'] != '1':
            raise ScoValueError('Modification impossible: semestre verrouille')
        #
        ins = self.Notes.do_formsemestre_inscription_list(
            { 'etudid'  : etudid, 'formsemestre_id' : formsemestre_id })[0]
        if groupetd != None:
            if groupetd == '' or groupetd == 'None':
                groupetd = None
            ins['groupetd'] = groupetd
        if groupetp != None:
            if groupetp == '' or groupetp == 'None':
                groupetp = None
            ins['groupetp'] = groupetp
        if groupeanglais != None:
            if groupeanglais == '' or groupeanglais == 'None':
                groupeanglais = None
            ins['groupeanglais'] = groupeanglais
        #self.Notes.do_formsemestre_inscription_edit( args=ins )
        # on ne peut pas utiliser do_formsemestre_inscription_edit car le groupe peut
        # etre null et les nulls sont filtr�s par dictfilter dans notesdb
        cursor = cnx.cursor()
        cursor.execute("update notes_formsemestre_inscription set groupetd=%(groupetd)s, groupetp=%(groupetp)s, groupeanglais=%(groupeanglais)s where formsemestre_id=%(formsemestre_id)s and etudid=%(etudid)s", ins)
        logdb(REQUEST,cnx,method='changeGroupe', etudid=etudid,
              msg='groupetd=%s,groupeanglais=%s,groupetp=%s,formsemestre_id=%s' %
              (groupetd,groupeanglais,groupetp,formsemestre_id))
        cnx.commit()
        self.Notes._inval_cache(formsemestre_id=formsemestre_id)
        if redirect:
            REQUEST.RESPONSE.redirect('ficheEtud?etudid='+etudid)

    # --- Affectation initiale des groupes
    security.declareProtected(ScoView, 'affectGroupes')
    affectGroupes = DTMLFile('dtml/groups/affectGroupes', globals()) 

    security.declareProtected(ScoView, 'XMLgetGroupesTD')
    XMLgetGroupesTD = sco_groupes.XMLgetGroupesTD

    security.declareProtected(ScoView, 'setGroupes')
    setGroupes = sco_groupes.setGroupes

    security.declareProtected(ScoView, 'suppressGroup')
    suppressGroup = sco_groupes.suppressGroup

    security.declareProtected(ScoView, 'groupes_auto_repartition')
    groupes_auto_repartition = sco_groupes.groupes_auto_repartition
    
    # --- Trombi: gestion photos
    # Ancien systeme (www-gtr):
    #  fotos dans ZODB, folder Fotos, id=identite.foto
    security.declareProtected(ScoView, 'etudfoto')
    def etudfoto(self, etudid, foto=None, fototitle=''):
        "html foto (taille petite)"        
        url = self.etudfoto_url(etudid, foto=foto)
        return '<img src="%s" alt="" title="" height="90" border="0" />' % url
    # XXX la taille devrait etre param�trable (difficile si lien portail)

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

    security.declareProtected(ScoView, 'etudfoto_islocal')
    def etudfoto_islocal(self, etudid):
        "True if ScoDoc has a copy of the photo"
        cnx = self.GetDBConnexion()
        etud = scolars.etudident_list(cnx, {'etudid': etudid })[0]
        foto = etud['foto']
        if not foto:
            return False # no photo data
        try:
            getattr(self.Fotos, foto)
            return True
        except:
            try:
                getattr(self.Fotos, foto + '.h90.jpg' )
                return True
            except:
                pass
        return False

    def etudfoto_url(self, etudid, foto=None):
        """URL de la photo (petit format):
        soit sur ScoDoc, soit sur le portail, 
        soit image 'inconnu'
        """
        etud = None
        if foto is None:    
            cnx = self.GetDBConnexion()
            etud = scolars.etudident_list(cnx, {'etudid': etudid })[0]
            foto = etud['foto']
        if foto:
            try:
                img = getattr(self.Fotos, foto)
                return img.absolute_url()
            except:
                try:
                    img = getattr(self.Fotos, foto + '.h90.jpg' )
                    return img.absolute_url()
                except:
                    pass
        # Portail ?
        if not etud:
            cnx = self.GetDBConnexion()
            etud = scolars.etudident_list(cnx, {'etudid': etudid })[0]
        portal_url = sco_portal_apogee.get_portal_url(self)
        if portal_url and etud['code_nip']:
            return portal_url + '/getPhoto.php?nip=' + etud['code_nip']
        
        # fallback: Photo "inconnu"
        img = getattr(self.Fotos, 'unknown_img')
        return img.absolute_url()
        
    security.declareProtected(ScoEtudChangeAdr, 'formChangePhoto')
    formChangePhoto = DTMLFile('dtml/formChangePhoto', globals())
    security.declareProtected(ScoEtudChangeAdr, 'doChangePhoto')
    def doChangePhoto(self, etudid, photofile, REQUEST, suppress=False, filesize=None):
        """change la photo d'un etudiant
        Si suppress, supprime la photo existante.
        """
        cnx = self.GetDBConnexion() 
        if photofile:
            if not filesize:
                # mesure la taille du fichier uploaded
                filesize = len(photofile.read())
                photofile.seek(0)         
            if filesize < 10 or filesize > 800*1024:
                return 0, 'Fichier image de taille invalide ! (%d)' % filesize
            # find a free id
            num = 0
            while hasattr( self.Fotos, 'img_n_%05d.h90.jpg' % num):
                num = num + 1
            nt = 'n_%05d' % num
            photo_id='img_' + nt + '.h90.jpg'

            small_img = imageresize.ImageScaleH(photofile,H=90)
            self.Fotos.manage_addProduct['OFSP'].manage_addImage(photo_id, small_img, etudid )
            # Update database
            scolars.identite_edit(cnx,args={'etudid':etudid,'foto':photo_id})
            logdb(REQUEST,cnx,method='changePhoto',msg=photo_id,etudid=etudid)
        elif suppress:
            scolars.identite_edit(cnx,args={'etudid':etudid,'foto':'unknown_img'})
            logdb(REQUEST,cnx,method='changePhoto',msg='supression', etudid=etudid)
        return 1, 'ok'
    #
    security.declareProtected(ScoEtudInscrit, "formDem")
    def formDem(self, etudid, formsemestre_id, REQUEST):
        "Formulaire Demission Etudiant"
        cnx = self.GetDBConnexion()    
        etud = scolars.etudident_list(cnx, {'etudid':etudid})[0]
        sem = self.Notes.do_formsemestre_list({'formsemestre_id':formsemestre_id})[0]
        if sem['etat'] != '1':
            raise ScoValueError('Modification impossible: semestre verrouille')

        etud['formsemestre_id']=formsemestre_id
        etud['semtitre'] = sem['titreannee']
        etud['nowdmy'] = time.strftime('%d/%m/%Y')
        #
        header = self.sco_header(
            REQUEST,
            page_title='D�mission de  %(prenom)s %(nom)s (du semestre %(semtitre)s)'%etud)
        H = [ '<h2><font color="#FF0000">D�mission de</font> %(prenom)s %(nom)s (semestre %(semtitre)s)</h2><p>' % etud ]
        H.append("""<form action="doDemEtudiant" method="GET">
<b>Date de la d&eacute;mission (J/M/AAAA):&nbsp;</b><input type="text" name="event_date" width=20 value="%(nowdmy)s">
<input type="hidden" name="etudid" value="%(etudid)s">
<input type="hidden" name="formsemestre_id" value="%(formsemestre_id)s">
<p>
<input type="submit" value="Confirmer la d&eacute;mission">

</form>""" % etud )
        return header + '\n'.join(H) + self.sco_footer(REQUEST)
    
    security.declareProtected(ScoEtudInscrit, "doDemEtudiant")
    def doDemEtudiant(self,etudid,formsemestre_id,event_date=None,REQUEST=None):
        "demission d'un etudiant"
        # marque D dans l'inscription au semestre et ajoute
        # un "evenement" scolarite
        cnx = self.GetDBConnexion()
        # check lock
        sem = self.Notes.do_formsemestre_list({'formsemestre_id':formsemestre_id})[0]
        if sem['etat'] != '1':
            raise ScoValueError('Modification impossible: semestre verrouille')
        #
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

    security.declareProtected(ScoEtudInscrit, "doCancelDem")
    def doCancelDem(self,etudid,formsemestre_id,dialog_confirmed=False, args=None,
                    REQUEST=None):
        "annule une demission"
        # check lock
        sem = self.Notes.do_formsemestre_list({'formsemestre_id':formsemestre_id})[0]
        if sem['etat'] != '1':
            raise ScoValueError('Modification impossible: semestre verrouille')
        # verif
        info = self.getEtudInfo(etudid, filled=True)[0]
        ok = False
        for i in info['ins']:
            if i['formsemestre_id'] == formsemestre_id:
                if i['etat'] != 'D':
                    raise ScoValueError('etudiant non demissionnaire !')
                ok = True
                break
        if not ok:
            raise ScoValueError('etudiant non inscrit ???')
        if not dialog_confirmed:
            return self.confirmDialog(
                '<p>Confirmer l\'annulation de la d�mission ?</p>',
                dest_url="", REQUEST=REQUEST,
                cancel_url="ficheEtud?etudid=%s"%etudid,
                parameters={'etudid' : etudid,
                            'formsemestre_id' : formsemestre_id})
        # 
        ins = self.Notes.do_formsemestre_inscription_list(
            { 'etudid'  : etudid, 'formsemestre_id' : formsemestre_id })[0]
        if ins['etat'] != 'D':
            raise ScoException('etudiant non dem. !!!') # obviously a bug
        ins['etat'] = 'I'
        cnx = self.GetDBConnexion()
        self.Notes.do_formsemestre_inscription_edit( args=ins )
        logdb(REQUEST,cnx,method='cancelDem', etudid=etudid)
        cursor = cnx.cursor()
        cursor.execute( "delete from scolar_events where etudid=%(etudid)s and formsemestre_id=%(formsemestre_id)s and event_type='DEMISSION'",
                        { 'etudid':etudid, 'formsemestre_id':formsemestre_id})
        cnx.commit()
        return REQUEST.RESPONSE.redirect("ficheEtud?etudid=%s"%etudid)
    
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
        H = [self.sco_header(REQUEST)]
        F = self.sco_footer(REQUEST)
        AUTHENTICATED_USER = REQUEST.AUTHENTICATED_USER
        etudid = REQUEST.form.get('etudid',None)
        cnx = self.GetDBConnexion()
        descr = []
        if not edit:
            # creation nouvel etudiant
            initvalues = {}
            submitlabel = 'Ajouter cet �tudiant'
            H.append("""<h2>Cr�ation d'un �tudiant</h2>
            <p>En g�n�ral, il est <b>recommand�</b> d'importer les �tudiants depuis Apog�e.
            N'utilisez ce formulaire que <b>pour les cas particuliers</b> ou si votre �tablissement
            n'utilise pas d'autre logiciel de gestion des inscriptions.</p>
            <p><em>L'�tudiant cr�� ne sera pas inscrit.
            Pensez � l'inscrire dans un semestre !</em></p>
            """)
        else:
            # edition donnees d'un etudiant existant
            # setup form init values
            if not etudid:
                raise ValueError('missing etudid parameter')
            descr.append( ('etudid', { 'default' : etudid, 'input_type' : 'hidden' }) )
            H.append('<h2>Modification d\'un �tudiant (<a href="ficheEtud?etudid=%s">fiche</a>)</h2>' % etudid)
            initvalues = scolars.etudident_list(cnx, {'etudid' : etudid})
            assert len(initvalues) == 1
            initvalues = initvalues[0]
            submitlabel = 'Modifier les donn�es'

        # recuperation infos Apogee
        nom = REQUEST.form.get('nom',None)
        if nom is None:
            nom = initvalues.get('nom',None)
        if nom is None:
            infos = []
        else:
            prenom = REQUEST.form.get('prenom','')
            if REQUEST.form.get('tf-submitted', False) and not prenom:
                prenom = initvalues.get('prenom','')
            infos = sco_portal_apogee.get_infos_apogee(self, nom, prenom)
        if infos:
            formatted_infos = [ """
            <script type="text/javascript">
            /* <![CDATA[ */
            function copy_nip(nip) {
            document.tf.code_nip.value = nip;
            }
            /* ]]> */
            </script>
            <ol>""" ]
            nanswers = len(infos)
            nmax = 10 # nb max de reponse montrees
            infos = infos[:nmax]
            for i in infos:
                formatted_infos.append( '<li><ul>' )
                for k in i.keys():
                    if k != 'nip':
                        item = '<li>%s : %s</li>' % (k, i[k])
                    else:
                        item = '<li><form>%s : %s <input type="button" value="copier ce code" onmousedown="copy_nip(%s);"/></form></li>' % (k, i[k], i[k])
                    formatted_infos.append( item )
                    
                formatted_infos.append( '</ul></li>' )                
            formatted_infos.append( '</ol>' )
            m = "%d �tudiants trouv�s" % nanswers
            if len(infos) != nanswers:
                m += " (%d montr�s)" % len(infos)
            A = """<div class="infoapogee">
            <h5>Informations Apog�e</h5>
            <p>%s</p>
            %s
            </div>""" % (m, '\n'.join(formatted_infos))
        else:
            A = """<div class="infoapogee"><p>Pas d'informations d'Apog�e</p></div>"""
        
        descr += [
            ('adm_id', { 'input_type' : 'hidden' }),

            ('nom',       { 'size' : 25, 'title' : 'Nom', 'allow_null':False }),
            ('prenom',    { 'size' : 25, 'title' : 'Pr�nom' }),
            ('sexe',      { 'input_type' : 'menu', 'labels' : ['MR','MME','MLLE'],
                            'allowed_values' : ['MR','MME','MLLE'], 'title' : 'Genre' }),
            ('annee_naissance', { 'size' : 5, 'title' : 'Ann�e de naissance', 'type' : 'int' }),
            ('nationalite', { 'size' : 25, 'title' : 'Nationalit�' }),

            ('annee', { 'size' : 5, 'title' : 'Ann�e admission IUT',
                        'type' : 'int', 'allow_null' : False,
                        'explanation' : 'ann�e 1ere inscription (obligatoire)'}),
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
            ('villelycee', { 'size' : 15, 'title' : 'Commune du Lyc�e' }),
            ('sep', { 'input_type' : 'separator', 'title' : 'Codes Apog�e: (optionnels)' }),
            ('code_nip', { 'size' : 25, 'title' : 'Num�ro NIP', 'allow_null':True,
                           'explanation' : 'num�ro identit� �tudiant (Apog�e)'}),
            ('code_ine', { 'size' : 25, 'title' : 'Num�ro INE (optionnel)', 'allow_null':True,
                           'explanation' : 'num�ro INE'}),
            ]

        tf = TrivialFormulator( REQUEST.URL0, REQUEST.form, descr,
                                submitlabel = submitlabel,
                                cancelbutton = 'Re-interroger Apogee',
                                initvalues = initvalues)
        if tf[0] == 0:
            return '\n'.join(H) + tf[1] + '<p>' + A + F
        elif tf[0] == -1:
            return '\n'.join(H) + tf[1] + '<p>' + A + F
            #return '\n'.join(H) + '<h4>annulation</h4>' + F
        else:
            # form submission
            if not edit:
                # creation d'un etudiant
                etudid = scolars.etudident_create(cnx, tf[2], context=self, REQUEST=REQUEST)
                # event
                scolars.scolar_events_create( cnx, args = {
                    'etudid' : etudid,
                    'event_date' : time.strftime('%d/%m/%Y'),
                    'formsemestre_id' : None,
                    'event_type' : 'CREATION' } )
                # log
                logdb(REQUEST, cnx, method='etudident_edit_form',
                      etudid=etudid, msg='creation initiale')
                etud = scolars.etudident_list(cnx, {'etudid':etudid})[0]
                self.fillEtudsInfo([etud])
                etud['url']='ficheEtud?etudid=%(etudid)s' % etud
                sco_news.add(REQUEST, cnx, typ=NEWS_INSCR, # pas d'object pour ne montrer qu'un etudiant
                             text='Nouvel �tudiant <a href="%(url)s">%(nomprenom)s</a>' % etud,
                             url=etud['url'])  
            else:
                # modif d'un etudiant
                scolars.etudident_edit(cnx, tf[2], context=self, REQUEST=REQUEST)
            # inval all caches
            self.Notes._inval_cache()
            #
            return REQUEST.RESPONSE.redirect('ficheEtud?etudid='+etudid)

    
    security.declareProtected(ScoEtudInscrit,"etudident_delete")
    def etudident_delete(self, etudid, dialog_confirmed=False, REQUEST=None):
        "Delete a student"
        cnx = self.GetDBConnexion()
        etud = scolars.etudident_list(cnx, {'etudid':etudid})[0]
        self.fillEtudsInfo([etud])
        if not dialog_confirmed:
            return self.confirmDialog(
                """<p>Confirmer la supression de l'�tudiant <b>%(nomprenom)s</b> ?
                </p>
                <p>Cette op�ration <b>irreversible</b> efface toute trace de l'�tudiant: inscriptions, notes, absences...</p>
                <p><a href="ficheEtud?etudid=%(etudid)s">V�rifier la fiche de %(nomprenom)s</a>
                </p>""" % etud,
                dest_url="", REQUEST=REQUEST,
                cancel_url="ficheEtud?etudid=%s"%etudid,
                OK = "Supprimer d�finitivement cet �tudiant",
                parameters={'etudid' : etudid})
        log('etudident_delete: etudid=%(etudid)s nomprenom=%(nomprenom)s' % etud)
        # delete in all tables !
        tables = [ 'notes_appreciations', 'scolar_autorisation_inscription',
                   'scolar_formsemestre_validation',
                   'scolar_events',
                   'notes_notes_log',
                   'notes_notes',
                   'notes_moduleimpl_inscription',
                   'notes_formsemestre_inscription',
                   'entreprise_contact',
                   'etud_annotations',
                   'scolog',
                   'admissions',
                   'adresse',
                   'identite' ]
        cursor = cnx.cursor()
        for table in tables:
            cursor.execute( "delete from %s where etudid=%%(etudid)s" % table,
                            etud )            
        cnx.commit()
        return REQUEST.RESPONSE.redirect(REQUEST.URL1)
    
    # ---- inscriptions "en masse"
    security.declareProtected(ScoEtudInscrit, "students_import_excel")
    def students_import_excel(self, csvfile, REQUEST=None,
                              formsemestre_id=None):
        "import students from Excel file"
        diag = ImportScolars.scolars_import_excel_file(
            csvfile, file_path, self.Notes, REQUEST,
            formsemestre_id=formsemestre_id )
        if REQUEST:
            H = [self.sco_header(REQUEST, page_title='Import etudiants')]
            H.append('<p>Import excel: %s</p>'% diag)
            H.append('<p>OK, import termin� !</p>')
            H.append('<p><a class="stdlink" href="%s">Continuer</a></p>' % REQUEST.URL1)
            return '\n'.join(H) + self.sco_footer(REQUEST)
        # invalid all caches
        self.Notes._inval_cache()    
    
    security.declareProtected(ScoEtudInscrit, "check_group_apogee")
    def check_group_apogee(self, formsemestre_id, REQUEST=None,
                           groupetd=None,groupetp=None,groupeanglais=None, etat=None,
                           fix=False,
                           fixmail = False):
        """Verification des codes Apogee et mail de tout un groupe.
        Si fix == True, change les codes avec Apog�e.
        """
        T, nomgroupe, ng, sem, nbdem = self._getlisteetud(formsemestre_id,
                                                          groupetd,groupetp,groupeanglais,etat )
        if not nomgroupe:
            nomgroupe = 'tous'
        cnx = self.GetDBConnexion()
        H = [ '<h2>Etudiants de <a href="Notes/formsemestre_status?formsemestre_id=%s">%s</a> %s</h2>' % (formsemestre_id, sem['titreannee'], ng) ]
        H.append('<table class="sortable" id="listegroupe">')
        H.append('<tr><th>Nom</th><th>Pr�nom</th><th>Mail</th><th>NIP (ScoDoc)</th><th>Apog�e</th></tr>')
        nerrs = 0 # nombre d'anomalies d�tect�es
        nfix = 0 # nb codes changes
        nmailmissing = 0 # nb etuds sans mail
        for t in T:
            nom, prenom, etudid, email, code_nip = t['nom'], t['prenom'], t['etudid'], t['email'], t['code_nip']
            infos = sco_portal_apogee.get_infos_apogee(self, nom, prenom)
            if not infos:
                info_apogee = '<b>Pas d\'information</b> (<a href="etudident_edit_form?etudid=%s">Modifier identit�</a>)' % etudid
                nerrs += 1
            else:
                if len(infos) == 1:
                    nip_apogee = infos[0]['nip']
                    if code_nip != nip_apogee:
                        if fix:
                            # Update database
                            scolars.identite_edit(
                                cnx,
                                args={'etudid':etudid,'code_nip':nip_apogee},
                                context=self)
                            info_apogee = '<span style="color:green">copi� %s</span>' % nip_apogee
                            nfix += 1
                        else:
                            info_apogee = '<span style="color:red">%s</span>' % nip_apogee
                            nerrs += 1
                    else:
                        info_apogee = 'ok'
                else:
                    info_apogee = '<b>%d correspondances</b> (<a href="etudident_edit_form?etudid=%s">Choisir</a>)' % (len(infos), etudid)
                    nerrs += 1
            # check mail
            if email:
                mailstat = 'ok'
            else:
                if fixmail and len(infos) == 1:
                    mail_apogee = infos[0]['mail']
                    adrs = scolars.adresse_list(cnx, {'etudid' : etudid})
                    if adrs:
                        adr = adrs[0] # modif adr existante
                        args={'adresse_id':adr['adresse_id'],'email':mail_apogee}
                        scolars.adresse_edit(cnx, args=args)
                    else:
                        # creation adresse
                        args={'etudid': etudid,'email':mail_apogee}
                        scolars.adresse_create(cnx, args=args)
                    mailstat = '<span style="color:green">copi�</span>'
                else:
                    mailstat = 'inconnu'
                    nmailmissing += 1
            H.append( '<tr><td><a href="ficheEtud?etudid=%s">%s</a></td><td>%s</td><td>%s</td><td>%s</td><td>%s</td></tr>' %
                          (etudid, nom, prenom, mailstat, code_nip, info_apogee) )
        H.append('</table>')
        H.append('<ul>')
        if nfix:
            H.append('<li><b>%d</b> codes modifi�s</li>' % nfix )
        H.append('<li>Codes NIP: <b>%d</b> anomalies d�tect�es</li>' % nerrs )
        H.append('<li>Adresse mail: <b>%d</b> �tudiants sans adresse</li>' % nmailmissing )
        H.append('</ul>')
        H.append("""
        <form method="get" action="">
        <input type="hidden" name="formsemestre_id" value="%s"/>
        <input type="hidden" name="groupetd" value="%s"/>
        <input type="hidden" name="groupetp" value="%s"/>
        <input type="hidden" name="groupeanglais" value="%s"/>
        <input type="hidden" name="etat" value="%s"/>
        <input type="hidden" name="fix" value="1"/>
        <input type="submit" value="Mettre � jour les codes NIP depuis Apog�e"/>
        </form>
        <p><a href="Notes/formsemestre_status?formsemestre_id=%s"> Retour au semestre</a>
        """ % (formsemestre_id,strnone(groupetd),strnone(groupetp),
               strnone(groupeanglais),strnone(etat),formsemestre_id ))
        H.append("""
        <form method="get" action="">
        <input type="hidden" name="formsemestre_id" value="%s"/>
        <input type="hidden" name="groupetd" value="%s"/>
        <input type="hidden" name="groupetp" value="%s"/>
        <input type="hidden" name="groupeanglais" value="%s"/>
        <input type="hidden" name="etat" value="%s"/>
        <input type="hidden" name="fixmail" value="1"/>
        <input type="submit" value="Renseigner les e-mail manquants (adresse institutionnelle)"/>
        </form>
        <p><a href="Notes/formsemestre_status?formsemestre_id=%s"> Retour au semestre</a>
        """ % (formsemestre_id,strnone(groupetd),strnone(groupetp),
               strnone(groupeanglais),strnone(etat),formsemestre_id ))

        return self.sco_header(REQUEST)+'\n'.join(H)+self.sco_footer(REQUEST)
        
    security.declareProtected(ScoEtudInscrit, "form_students_import_excel")
    def form_students_import_excel(self, REQUEST, formsemestre_id=None):
        "formulaire import xls"
        if formsemestre_id:
            sem = self.Notes.get_formsemestre(formsemestre_id)
        else:
            sem = None
        H = [self.sco_header(REQUEST, page_title='Import etudiants'),
             """<h2>T�l�chargement d\'une nouvelle liste d\'etudiants</h2>
             <div style="color: red">
             <p>A utiliser pour importer de <b>nouveaux</b> �tudiants (typiquement au
             <b>premier semestre</b>).</p>
             <p>Si les �tudiants � inscrire sont d�j� dans un autre
             semestre, utiliser le lien "<em>Inscriptions (passage des �tudiants)
             depuis d'autres semestres</em> � partir du semestre destination.
             </p>
             <p>Si vous avez un portail Apog�e, il est en g�n�ral pr�f�rable d'importer les
             �tudiants depuis Apog�e, via le lien "<em>Synchroniser avec �tape Apog�e</em>".
             </p>
             </div>
             <p>
             L'op�ration se d�roule en deux �tapes. Dans un premier temps,
             vous t�l�chargez une feuille Excel type. Vous devez remplir
             cette feuille, une ligne d�crivant chaque �tudiant. Ensuite,
             vous indiquez le nom de votre fichier dans la case "Fichier Excel"
             ci-dessous, et cliquez sur "T�l�charger" pour envoyer au serveur
             votre liste.
             </p>
             """] # '
        if sem:
            H.append("""<p style="color: red">Les �tudiants import�s seront inscrits dans
            le semestre <b>%s</b></p>""" % sem['titreannee'])
        else:
            H.append("""
             <p>Pour inscrire directement les �tudiants dans un semestre de
             formation, il suffit d'indiquer le code de ce semestre
             (qui doit avoir �t� cr�� au pr�alable). <a class="stdlink" href="%s?showcodes=1">Cliquez ici pour afficher les codes</a>
             </p>
             """  % (self.ScoURL()))

        H.append("""<ol><li>""")
        if formsemestre_id:
            H.append("""
            <a class="stdlink" href="import_generate_excel_sample?with_codesemestre=0">
            """)
        else:
            H.append("""<a class="stdlink" href="import_generate_excel_sample">""")
        H.append("""Obtenir la feuille excel � remplir</a></li>
        <li>""")
        
        F = self.sco_footer(REQUEST)
        tf = TrivialFormulator(
            REQUEST.URL0, REQUEST.form, 
            (('csvfile', {'title' : 'Fichier Excel:', 'input_type' : 'file',
                          'size' : 40 }),
             ('formsemestre_id', {'input_type' : 'hidden' }), 
             ), submitlabel = 'T�l�charger')
        S = ["""<hr/><p>Le fichier Excel d�crivant les �tudiants doit comporter les colonnes suivantes.
<p>Les colonnes peuvent �tre plac�es dans n'importe quel ordre, mais
le <b>titre</b> exact (tel que ci-dessous) doit �tre sur la premi�re ligne.
</p>
<p>
Les champs avec un ast�risque (*) doivent �tre pr�sents (nulls non autoris�s).
</p>


<p>
<table>
<tr><td><b>Attribut</b></td><td><b>Type</b></td><td><b>Description</b></td></tr>"""]
        for t in ImportScolars.sco_import_format(
                    file_path,
                    with_codesemestre=(formsemestre_id == None)):
            if int(t[3]):
                ast = ''
            else:
                ast = '*'
            S.append('<tr><td>%s</td><td>%s</td><td>%s</td><td>%s</td></tr>'
                     % (t[0],t[1],t[4], ast))
        if  tf[0] == 0:            
            return '\n'.join(H) + tf[1] + '</li></ol>' + '\n'.join(S) + F
        elif tf[0] == -1:
            return REQUEST.RESPONSE.redirect( REQUEST.URL1 )
        else:
            return self.students_import_excel(tf[2]['csvfile'],
                                              REQUEST=REQUEST,
                                              formsemestre_id=formsemestre_id)

    security.declareProtected(ScoEtudInscrit,"sco_import_generate_excel_sample")
    def import_generate_excel_sample(self, REQUEST, with_codesemestre='1'):
        "une feuille excel pour importation etudiants"
        if with_codesemestre:
            with_codesemestre = int(with_codesemestre)
        else:
            with_codesemestre = 0
        format = ImportScolars.sco_import_format(file_path)
        data = ImportScolars.sco_import_generate_excel_sample(format, with_codesemestre)
        return sco_excel.sendExcelFile(REQUEST,data,'ImportEtudiants.xls')

    # --- Donn�es admission
    security.declareProtected(ScoEtudInscrit, "form_students_import_infos_admissions")
    def form_students_import_infos_admissions(self, REQUEST, formsemestre_id=None):
        "formulaire import xls"
        sem = self.Notes.get_formsemestre(formsemestre_id)

        H = [self.sco_header(REQUEST, page_title='Import donn�es admissions'),
             """<h2>T�l�chargement des informations sur l'admission des d\'etudiants</h2>
             <div style="color: red">
             <p>A utiliser pour renseigner les informations sur l'origine des �tudiants (lyc�es, bac, etc). Ces informations sont facultatives mais souvent utiles pour mieux connaitre les �tudiants et aussi pour effectuer des statistiques (r�sultats suivant le type de bac...). Les donn�es sont affich�es sur les fiches individuelles des �tudiants.</p>
             </div>
             <p>
             L'op�ration se d�roule en trois �tapes. <ol><li>Dans un premier temps,
             vous t�l�chargez une feuille Excel type.</li>
             <li> Vous devez remplir
             cette feuille, une ligne d�crivant chaque �tudiant.
             Ne modifiez pas les titres des colonnes !
             </li>
             <li>Ensuite,
             vous indiquez le nom de votre fichier dans la case "Fichier Excel"
             ci-dessous, et cliquez sur "T�l�charger" pour envoyer au serveur
             votre liste. <em>Seules les donn�es admission seront modifi�es (et pas l'identit� de l'�tudiant).</em>
             </li></ol></p>
             """] # '

        H.append("""<ul><li>
        <a class="stdlink" href="import_generate_admission_sample?formsemestre_id=%s">
        """ % formsemestre_id)
        H.append("""Obtenir la feuille excel � remplir</a></li></ul>""")
        
        F = self.sco_footer(REQUEST)
        tf = TrivialFormulator(
            REQUEST.URL0, REQUEST.form, 
            (('csvfile', {'title' : 'Fichier Excel:', 'input_type' : 'file',
                          'size' : 40 }),
             ('formsemestre_id', {'input_type' : 'hidden' }), 
             ), submitlabel = 'T�l�charger')
        
        if  tf[0] == 0:            
            return '\n'.join(H) + tf[1] + F
        elif tf[0] == -1:
            return REQUEST.RESPONSE.redirect( REQUEST.URL1 )
        else:
            return self.students_import_admission(
                tf[2]['csvfile'],
                REQUEST=REQUEST, formsemestre_id=formsemestre_id)

    security.declareProtected(ScoEtudInscrit,"sco_import_generate_admission_sample")
    def import_generate_admission_sample(self, REQUEST, formsemestre_id):
        "une feuille excel pour importation donn�es admissions"
        format = ImportScolars.sco_import_format(file_path)
        data = ImportScolars.sco_import_generate_excel_sample(
            format, only_tables=['identite', 'admissions'],
            exclude_cols = ['nationalite', 'foto', 'code_ine' ],
            formsemestre_id=formsemestre_id,context=self.Notes)
        return sco_excel.sendExcelFile(REQUEST,data,'AdmissionEtudiants.xls')

    security.declareProtected(ScoEtudInscrit, "students_import_excel")
    def students_import_admission(self, csvfile, REQUEST=None,
                                  formsemestre_id=None):
        "import donnees admission from Excel file"
        diag = ImportScolars.scolars_import_admission(
            csvfile, file_path, self.Notes, REQUEST,
            formsemestre_id=formsemestre_id )
        if REQUEST:
            H = [self.sco_header(REQUEST, page_title='Import donn�es admissions')]
            H.append('<p>Import termin� !</p>')
            H.append('<p><a class="stdlink" href="%s">Continuer</a></p>'
                     % 'formsemestre_status?formsemestre_id=%s' % formsemestre_id)
            if diag:
                H.append('<p>diagnostic: <tt>%s</tt></p>' % diag)
            return '\n'.join(H) + self.sco_footer(REQUEST)
        

    # --- Statistiques
    security.declareProtected(ScoView, "stat_bac")
    def stat_bac(self,formsemestre_id):
        "Renvoie statistisques sur nb d'etudiants par bac"
        cnx = self.GetDBConnexion()
        sem = self.Notes.do_formsemestre_list( args={'formsemestre_id':formsemestre_id} )[0]
        ins = self.Notes.do_formsemestre_inscription_list(
            args={ 'formsemestre_id' : formsemestre_id } )
        Bacs = {} # type bac : nb etud 
        for i in ins:
            etud = scolars.etudident_list(cnx, {'etudid':i['etudid']})[0]
            typebac = '%(bac)s %(specialite)s' % etud
            Bacs[typebac] = Bacs.get(typebac, 0) + 1
        return Bacs
    
    security.declareProtected(ScoView, "stat_bac_fmt")
    def stat_bac_fmt(self,formsemestre_id, format='html', REQUEST=None):
        "Statistiques sur nb d'etudiants par bac"
        Bacs = self.stat_bac(formsemestre_id)
        sem = self.Notes.do_formsemestre_list(
            {'formsemestre_id' : formsemestre_id} )[0]
        header = self.sco_header(REQUEST,
                                 page_title='Statistiques bacs ' + sem['titreannee'])
        H = [ """
        <h2>Origine des �tudiants de <a href="formsemestre_status?formsemestre_id=%(formsemestre_id)s">%(titre)s</a> (%(date_debut)s - %(date_fin)s)</h2>
        """ % sem,
              '<table><tr><th>Nombre d\'inscrits</th><th>Bac</th></tr>']
        bacs = Bacs.keys()
        bacs.sort()
        for bac in bacs:
            H.append('<tr><td>%s</td><td>%s</td></tr>' % (Bacs[bac],bac) )
        H.append('</table>')
        return header + '\n'.join(H) + self.sco_footer(REQUEST)
    
    # sendEmail is not used through the web
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

    def confirmDialog(self, message='<p>Confirmer ?</p>',
                      OK='OK', Cancel='Annuler',
                      dest_url= "", cancel_url="",
                      parameters={},
                      add_headers = True, # complete page
                      REQUEST=None,
                      helpmsg=None):
        # dialog de confirmation simple"
        parameters['dialog_confirmed'] = 1
        H = [ message,
              """<form action="%s" method="post">
              <input type="submit" value="%s"/>""" % (dest_url, OK) ]
        if cancel_url:
            H.append(
                """<input type ="button" value="%s"
                onClick="document.location='%s';"/>""" % (Cancel,cancel_url))
        for param in parameters.keys():
            H.append('<input type="hidden" name="%s" value="%s"/>'
                     % (param, parameters[param]))
        H.append('</form>')
        if helpmsg:
            H.append('<p class="help">' + helpmsg + '</p>') 
        if add_headers and REQUEST:
            return self.sco_header(REQUEST) + '\n'.join(H) + self.sco_footer(REQUEST)
        else:
            return '\n'.join(H)

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


    
