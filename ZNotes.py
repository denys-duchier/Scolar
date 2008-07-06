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

"""Interface Zope <-> Notes
"""

from email.MIMEMultipart import MIMEMultipart
from email.MIMEText import MIMEText
from email.MIMEBase import MIMEBase
from email.Header import Header
from email import Encoders

# XML generation package (apt-get install jaxml)
import jaxml

from sets import Set

# Zope stuff
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
from notes_log import log, sendAlarm
import scolog
from scolog import logdb
from sco_utils import *
import htmlutils
import sco_excel
#import notes_users
from TrivialFormulator import TrivialFormulator, TF
from gen_tables import GenTable
import sco_cache
import scolars
import sco_news
from sco_news import NEWS_INSCR, NEWS_NOTE, NEWS_FORM, NEWS_SEM, NEWS_MISC
from sco_pagebulletin import formsemestre_pagebulletin_get
import sco_formsemestre_edit, sco_formsemestre_status
import sco_edit_ue, sco_edit_formation, sco_edit_matiere, sco_edit_module
from sco_formsemestre_status import makeMenu
import sco_formsemestre_inscriptions, sco_formsemestre_custommenu
import sco_moduleimpl_inscriptions
import sco_bulletins, sco_recapcomplet, sco_liste_notes, sco_saisie_notes
import sco_formations, sco_pagebulletin, sco_report
import sco_formsemestre_validation, sco_parcours_dut, sco_codes_parcours
import sco_pvjury, sco_pvpdf, sco_prepajury
import sco_inscr_passage, sco_synchro_etuds
import pdfbulletins
from sco_pdf import PDFLOCK
from notes_table import *
import VERSION

#
# Cache global: chaque instance, repérée par son URL, a un cache
# qui est recréé à la demande
#
CACHE_formsemestre_inscription = {}

# ---------------

class ZNotes(ObjectManager,
             PropertyManager,
             RoleManager,
             Item,
             Persistent,
             Implicit
             ):

    "ZNotes object"

    meta_type = 'ZNotes'
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
	"initialise a new instance of ZNotes"
        self.id = id
	self.title = title
    
    # The form used to edit this object
    def manage_editZNotes(self, title, RESPONSE=None):
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
    
    def _getNotesCache(self):
        "returns CacheNotesTable instance for us"
        u = self.ScoURL()
        if not NOTES_CACHE_INST.has_key(u):
            NOTES_CACHE_INST[u] = CacheNotesTable()
        return NOTES_CACHE_INST[u]

    def _inval_cache(self, formsemestre_id=None, pdfonly=False):
        "expire cache pour un semestre (ou tous si pas d'argument)"
        self._getNotesCache().inval_cache(self, formsemestre_id=formsemestre_id, pdfonly=pdfonly)
        # Affecte aussi cache inscriptions
        self.get_formsemestre_inscription_cache().inval_cache(key=formsemestre_id)
    
    security.declareProtected(ScoView, 'clearcache')
    def clearcache(self, REQUEST=None):
        "Efface les caches de notes (utile pendant developpement slt)"
        log('*** clearcache request')
        # Debugging code: compare results before and after cache reconstruction
        # (_should_ be identicals !)
        # Compare XML representation
        cache = self._getNotesCache()
        formsemestre_ids = cache.get_cached_formsemestre_ids()
        docs_before = []        
        for formsemestre_id in formsemestre_ids:
            docs_before.append(
                self.do_formsemestre_recapcomplet(REQUEST,formsemestre_id, format='xml', xml_nodate=True))
        #
        cache.inval_cache(self)
        # Rebuild cache (useful only to debug)
        docs_after = []
        for formsemestre_id in formsemestre_ids:
            docs_after.append(
                self.do_formsemestre_recapcomplet(REQUEST,formsemestre_id, format='xml', xml_nodate=True))
        if docs_before != docs_after:
            log('clearcache: inconsistency !')
            txt = 'before=' + repr(docs_before) + '\n\nafter=' + repr(docs_after) + '\n'
            log(txt)
            sendAlarm(self, 'clearcache: inconsistency !', txt)
        
    # --------------------------------------------------------------------
    #
    #    NOTES (top level)
    #
    # --------------------------------------------------------------------
    # XXX essai
    security.declareProtected(ScoView, 'gloups')
    def gloups(self, REQUEST): 
        "essai gloups"
        return ''
        #return pdfbulletins.essaipdf(REQUEST)
        #return sendPDFFile(REQUEST, pdfbulletins.pdftrombino(0,0), 'toto.pdf' )

    # DTML METHODS
    security.declareProtected(ScoView, 'formsemestre_status_head')
    formsemestre_status_head = DTMLFile('dtml/notes/formsemestre_status_head', globals())
    security.declareProtected(ScoView, 'formsemestre_status')
    formsemestre_status = DTMLFile('dtml/notes/formsemestre_status', globals())
    security.declareProtected(ScoView, 'formsemestre_description')
    formsemestre_description = sco_formsemestre_status.formsemestre_description

    security.declareProtected(ScoView, 'formsemestre_status_menubar')
    formsemestre_status_menubar = sco_formsemestre_status.formsemestre_status_menubar

    security.declareProtected(ScoEnsView, 'evaluation_delete')
    evaluation_delete = DTMLFile('dtml/notes/evaluation_delete', globals())

    security.declareProtected(ScoChangeFormation, 'formation_create')
    formation_create = sco_edit_formation.formation_create
    security.declareProtected(ScoChangeFormation, 'formation_delete')
    formation_delete = sco_edit_formation.formation_delete
    security.declareProtected(ScoChangeFormation, 'formation_edit')
    formation_edit = sco_edit_formation.formation_edit

    security.declareProtected(ScoView, 'formsemestre_bulletinetud')
    formsemestre_bulletinetud = sco_bulletins.formsemestre_bulletinetud
    
    security.declareProtected(ScoImplement, 'formsemestre_createwithmodules')
    formsemestre_createwithmodules = DTMLFile('dtml/notes/formsemestre_createwithmodules', globals(), title='Création d\'un semestre (ou session) de formation avec ses modules')
    security.declareProtected(ScoImplement, 'formsemestre_editwithmodules')
    formsemestre_editwithmodules = DTMLFile('dtml/notes/formsemestre_editwithmodules', globals(), title='Modification d\'un semestre (ou session) de formation avec ses modules' )
    security.declareProtected(ScoImplement, 'formsemestre_delete')
    formsemestre_delete = DTMLFile('dtml/notes/formsemestre_delete', globals(), title='Suppression d\'un semestre (ou session) de formation avec ses modules' )
    security.declareProtected(ScoView, 'formsemestre_recapcomplet')
    formsemestre_recapcomplet = DTMLFile('dtml/notes/formsemestre_recapcomplet', globals(), title='Tableau de toutes les moyennes du semestre')

    security.declareProtected(ScoChangeFormation, 'ue_create')
    ue_create = sco_edit_ue.ue_create
    security.declareProtected(ScoChangeFormation, 'ue_delete')
    ue_delete = sco_edit_ue.ue_delete
    security.declareProtected(ScoChangeFormation, 'ue_edit')
    ue_edit = sco_edit_ue.ue_edit
    security.declareProtected(ScoView, 'ue_list')
    ue_list = sco_edit_ue.ue_list
    
    security.declareProtected(ScoChangeFormation, 'matiere_create')
    matiere_create = sco_edit_matiere.matiere_create
    security.declareProtected(ScoChangeFormation, 'matiere_delete')
    matiere_delete = sco_edit_matiere.matiere_delete
    security.declareProtected(ScoChangeFormation, 'matiere_edit')
    matiere_edit = sco_edit_matiere.matiere_edit
    
    security.declareProtected(ScoChangeFormation, 'module_create')
    module_create = sco_edit_module.module_create
    security.declareProtected(ScoChangeFormation, 'module_delete')
    module_delete = sco_edit_module.module_delete
    security.declareProtected(ScoChangeFormation, 'module_edit')
    module_edit = sco_edit_module.module_edit
    security.declareProtected(ScoView, 'module_list')
    module_list = sco_edit_module.module_list
    
    security.declareProtected(ScoView,'moduleimpl_status')
    moduleimpl_status = DTMLFile('dtml/notes/moduleimpl_status', globals(), title='Tableau de bord module')

    security.declareProtected(ScoView,'moduleimpl_listenotes')
    moduleimpl_listenotes = sco_liste_notes.moduleimpl_listenotes

    security.declareProtected(ScoEnsView, 'notes_eval_selectetuds')
    notes_eval_selectetuds = sco_saisie_notes.notes_eval_selectetuds
    security.declareProtected(ScoEnsView, 'notes_evaluation_formnotes')
    notes_evaluation_formnotes = DTMLFile('dtml/notes/notes_evaluation_formnotes', globals(), title='Saisie des notes')

    # used to view content of the object
    security.declareProtected(ScoView, 'index_html')
    def index_html(self, REQUEST=None):
        "Page accueil formations"
        lockicon = self.icons.lock32_img.tag(title="formation verrouillé", border='0')
        editable = REQUEST.AUTHENTICATED_USER.has_permission(ScoChangeFormation,self)

        H = [ self.sco_header(REQUEST, page_title="Programmes formations"),
              """<h2>Programmes des formations</h2>
              <ul class="notes_formation_list">""" ]

        for F in self.do_formation_list():
            H.append('<li class="notes_formation_list">%(acronyme)s: %(titre)s (version %(version)s)' % F )
            locked = self.formation_has_locked_sems(F['formation_id'])
            if locked:
                H.append(lockicon)
            elif editable:
                H.append("""<a class="stdlink" href="formation_edit?formation_id=%(formation_id)s">modifier</a>
 	     <a class="stdlink" href="formation_delete?formation_id=%(formation_id)s">supprimer</a>""" % F )
            H.append("""<a class="stdlink" href="ue_list?formation_id=%(formation_id)s">programme détaillé et semestres</a>""" % F )
            H.append('</li>')
        H.append('</ul>')
        if editable:
            H.append("""<p><a class="stdlink" href="formation_create">Créer une formation</a></p>
 	 <p><a class="stdlink" href="formation_import_xml_form">Importer une formation (xml)</a></p>""")

        H.append(self.sco_footer(REQUEST))
        return '\n'.join(H)

    # --------------------------------------------------------------------
    #
    #    Notes Methods
    #
    # --------------------------------------------------------------------

    # --- Formations
    _formationEditor = EditableTable(
        'notes_formations',
        'formation_id',
        ('formation_id', 'acronyme','titre', 'titre_officiel', 'version', 'formation_code'),
        sortkey='acronyme'
        )

    security.declareProtected(ScoChangeFormation, 'do_formation_create')
    def do_formation_create(self, args, REQUEST):
        "create a formation"
        cnx = self.GetDBConnexion()
        # check unique acronyme/titre/version
        a = args.copy()
        if a.has_key('formation_id'):
            del a['formation_id']
        F = self.do_formation_list(args=a)
        if len(F) > 0:
            raise ScoValueError("Formation non unique (%s) !" % str(a))
        # Si pas de formation_code, l'enleve (default SQL)
        if args.has_key('formation_code') and not args['formation_code']:
            del args['formation_code']
        #
        r = self._formationEditor.create(cnx, args)
        self._inval_cache()
        sco_news.add(REQUEST, cnx, typ=NEWS_FORM,
                     text='Création de la formation %(titre)s (%(acronyme)s)' % args )
        return r
    
    security.declareProtected(ScoChangeFormation, 'do_formation_delete')
    def do_formation_delete(self, oid, REQUEST):
        "delete a formation (and all its UE, matieres, modules)"
        F = self.do_formation_list(args={'formation_id':oid})[0]
        if self.formation_has_locked_sems(oid):
            raise ScoLockedFormError()
        cnx = self.GetDBConnexion()
        # delete all UE in this formation
        ues = self.do_ue_list({ 'formation_id' : oid })
        for ue in ues:
            self.do_ue_delete(ue['ue_id'], REQUEST)
        
        self._formationEditor.delete(cnx, oid)
        self._inval_cache()
        # news
        sco_news.add(REQUEST, cnx, typ=NEWS_FORM, object=oid,
                     text='Suppression de la formation %(acronyme)s' % F )

    security.declareProtected(ScoView, 'do_formation_list')
    def do_formation_list(self, **kw ):
        "list formations"
        cnx = self.GetDBConnexion()        
        return self._formationEditor.list( cnx, **kw )

    security.declareProtected(ScoChangeFormation, 'do_formation_edit')
    def do_formation_edit(self, *args, **kw ):
        "edit a formation"
        log('do_formation_edit( args=%s kw=%s )'%(args,kw))
        #if self.formation_has_locked_sems(args[0]['formation_id']):
        #    raise ScoLockedFormError()
        # nb: on autorise finalement la modif de la formation meme si elle est verrouillee
        # car cela ne change que du cosmetique, (sauf eventuellement le code formation ?)
        cnx = self.GetDBConnexion()
        self._formationEditor.edit( cnx, *args, **kw )
        self._inval_cache()

    security.declareProtected(ScoView, 'formation_export_xml')
    def formation_export_xml(self, formation_id, REQUEST):
        "export XML de la formation"
        REQUEST.RESPONSE.setHeader('Content-type', XML_MIMETYPE)        
        return sco_formations.formation_export_xml(self, formation_id)

    security.declareProtected(ScoChangeFormation, 'formation_import_xml')
    def formation_import_xml(self, file, REQUEST):
        "import d'une formation en XML"
        log('formation_import_xml')
        doc = file.read()
        return sco_formations.formation_import_xml(self,REQUEST, doc)

    security.declareProtected(ScoChangeFormation, 'formation_import_xml_form')
    def formation_import_xml_form(self,REQUEST):
        "form import d'une formation en XML"
        H = [ self.sco_header(page_title='Import d\'une formation',
                              REQUEST=REQUEST),
              """<h2>Import d'une formation</h2>
        <p>Création d'une formation (avec UE, matières, modules)
        à partir un fichier XML (réservé aux utilisateurs avertis)</p>
        """]
        footer = self.sco_footer(REQUEST)
        tf = TrivialFormulator(REQUEST.URL0, REQUEST.form,
                               ( ('xmlfile',
                                  { 'input_type' : 'file',
                                    'title' : 'Fichier XML', 'size' : 30 }),    
                                 ),
                               submitlabel='Importer',
                               cancelbutton = 'Annuler')
        if tf[0] == 0:
            return '\n'.join(H) + tf[1] + footer
        elif tf[0] == -1:
            return REQUEST.RESPONSE.redirect( REQUEST.URL1 )
        else:
            formation_id = self.formation_import_xml(tf[2]['xmlfile'],REQUEST)
            
            return '\n'.join(H) + """<p>Import effectué !</p>
            <p><a class="stdlink" href="ue_list?formation_id=%s">Voir la formation</a></p>""" % formation_id + footer

    security.declareProtected(ScoChangeFormation, 'formation_create_new_version')
    def formation_create_new_version(self,formation_id,REQUEST):
        "duplicate formation, with new version number"
        xml = sco_formations.formation_export_xml(self, formation_id)
        new_id = sco_formations.formation_import_xml(self,REQUEST, xml)
        # news
        cnx = self.GetDBConnexion()
        F = self.do_formation_list(args={ 'formation_id' :new_id})[0]
        sco_news.add(REQUEST, cnx, typ=NEWS_FORM, object=new_id,
                     text='Nouvelle version de la formation %(acronyme)s'%F)
        return REQUEST.RESPONSE.redirect("ue_list?formation_id=" + new_id + '&msg=Nouvelle version !')
        
    # --- UE
    _ueEditor = EditableTable(
        'notes_ue',
        'ue_id',
        ('ue_id', 'formation_id', 'acronyme', 'numero', 'titre',
         'type', 'ue_code' ),
        sortkey='numero',
        input_formators = { 'type' : int_null_is_zero },
        output_formators = { 'numero' : int_null_is_zero },
        )

    security.declareProtected(ScoChangeFormation, 'do_ue_create')
    def do_ue_create(self, args, REQUEST):
        "create an ue"
        if self.formation_has_locked_sems(args['formation_id']):
            raise ScoLockedFormError()
        cnx = self.GetDBConnexion()
        # check duplicates
        ues = self.do_ue_list({'formation_id' : args['formation_id'],
                               'acronyme' : args['acronyme'] })
        if ues:
            raise ScoValueError('UE "%s" déjà existante !' % args['acronyme'])
        # create
        r = self._ueEditor.create(cnx, args)
        self._inval_cache()
        # news
        F = self.do_formation_list(args={ 'formation_id' :args['formation_id']})[0]
        sco_news.add(REQUEST, cnx, typ=NEWS_FORM, object=args['formation_id'],
                     text='Modification de la formation %(acronyme)s' % F )
        return r

    security.declareProtected(ScoChangeFormation, 'do_ue_delete')
    def do_ue_delete(self, oid, REQUEST):
        "delete UE and attached matieres"
        # check
        ue = self.do_ue_list({ 'ue_id' : oid })[0]
        if self.formation_has_locked_sems(ue['formation_id']):
            raise ScoLockedFormError()        
        # delete all matiere in this UE
        mats = self.do_matiere_list({ 'ue_id' : oid })
        for mat in mats:
            self.do_matiere_delete(mat['matiere_id'], REQUEST)
        cnx = self.GetDBConnexion()
        self._ueEditor.delete(cnx, oid)
        self._inval_cache()
        # news
        F = self.do_formation_list(args={ 'formation_id' :ue['formation_id']})[0]
        sco_news.add(REQUEST, cnx, typ=NEWS_FORM, object=ue['formation_id'],
                     text='Modification de la formation %(acronyme)s' % F )

    security.declareProtected(ScoView, 'do_ue_list')
    def do_ue_list(self, *args, **kw ):
        "list UEs"
        cnx = self.GetDBConnexion()
        return self._ueEditor.list(cnx, *args, **kw)

    security.declareProtected(ScoChangeFormation, 'do_ue_edit')
    def do_ue_edit(self, *args, **kw ):
        "edit an UE"
        # check
        ue_id = args[0]['ue_id']
        ue = self.do_ue_list({ 'ue_id' : ue_id })[0]
        if self.formation_has_locked_sems(ue['formation_id']):
            raise ScoLockedFormError()        
        # check: acronyme unique dans cette formation
        if args[0].has_key('acronyme'):
            new_acro = args[0]['acronyme']
            ues = self.do_ue_list({'formation_id' : ue['formation_id'], 'acronyme' : new_acro })
            if ues and ues[0]['ue_id'] != ue_id:
                raise ScoValueError('UE "%s" déjà existante !' % args[0]['acronyme'])
        
        cnx = self.GetDBConnexion()
        self._ueEditor.edit( cnx, *args, **kw )
        self._inval_cache()

    # --- Matieres
    _matiereEditor = EditableTable(
        'notes_matieres',
        'matiere_id',
        ('matiere_id', 'ue_id', 'numero', 'titre'),
        sortkey='numero',
        output_formators = { 'numero' : int_null_is_zero },
        )

    security.declareProtected(ScoChangeFormation, 'do_matiere_create')
    def do_matiere_create(self, args, REQUEST):
        "create a matiere"
        cnx = self.GetDBConnexion()
        # check
        ue = self.do_ue_list({ 'ue_id' : args['ue_id'] })[0]
        if self.formation_has_locked_sems(ue['formation_id']):
            raise ScoLockedFormError()
        # create matiere
        r = self._matiereEditor.create(cnx, args)
        self._inval_cache()
        # news
        F = self.do_formation_list(args={ 'formation_id' :ue['formation_id']})[0]
        sco_news.add(REQUEST, cnx, typ=NEWS_FORM, object=ue['formation_id'],
                     text='Modification de la formation %(acronyme)s' % F )
        return r

    security.declareProtected(ScoChangeFormation, 'do_matiere_delete')
    def do_matiere_delete(self, oid, REQUEST):
        "delete matiere and attached modules"
        cnx = self.GetDBConnexion()
        # check
        mat = self.do_matiere_list({ 'matiere_id' : oid })[0]
        ue = self.do_ue_list({ 'ue_id' : mat['ue_id'] })[0]
        locked = self.formation_has_locked_sems(ue['formation_id'])
        if locked:
            log('do_matiere_delete: mat=%s' % mat)
            log('do_matiere_delete: ue=%s' % ue)
            log('do_matiere_delete: locked sems: %s' % locked)
            raise ScoLockedFormError()  
        # delete all modules in this matiere
        mods = self.do_module_list({ 'matiere_id' : oid })
        for mod in mods:
            self.do_module_delete(mod['module_id'],REQUEST)
        self._matiereEditor.delete(cnx, oid)
        self._inval_cache()
        # news
        F = self.do_formation_list(args={ 'formation_id' :ue['formation_id']})[0]
        sco_news.add(REQUEST, cnx, typ=NEWS_FORM, object=ue['formation_id'],
                     text='Modification de la formation %(acronyme)s' % F )

    security.declareProtected(ScoView, 'do_matiere_list')
    def do_matiere_list(self, *args, **kw ):
        "list matieres"
        cnx = self.GetDBConnexion()
        return self._matiereEditor.list(cnx, *args, **kw)

    security.declareProtected(ScoChangeFormation, 'do_matiere_edit')
    def do_matiere_edit(self, *args, **kw ):
        "edit a matiere"
        cnx = self.GetDBConnexion()
        # check
        mat = self.do_matiere_list({ 'matiere_id' :args[0]['matiere_id']})[0]
        ue = self.do_ue_list({ 'ue_id' : mat['ue_id'] })[0]
        if self.formation_has_locked_sems(ue['formation_id']):
            raise ScoLockedFormError() 
        # edit
        self._matiereEditor.edit( cnx, *args, **kw )
        self._inval_cache()

    security.declareProtected(ScoView, 'do_matiere_formation_id')
    def do_matiere_formation_id(self, matiere_id):
        "get formation_id from matiere"
        cnx = self.GetDBConnexion()
        cursor = cnx.cursor()
        cursor.execute('select UE.formation_id from notes_matieres M, notes_ue UE where M.matiere_id = %(matiere_id)s and M.ue_id = UE.ue_id',
                       { 'matiere_id' : matiere_id } )
        res = cursor.fetchall()
        return res[0][0]

    # --- Modules
    _moduleEditor = EditableTable(
        'notes_modules',
        'module_id',
        ('module_id','titre','code', 'abbrev',
         'heures_cours','heures_td','heures_tp',
         'coefficient',
         'ue_id', 'matiere_id', 'formation_id',
         'semestre_id', 'numero' ),
        sortkey='numero',
        output_formators = { 'heures_cours' : float_null_is_zero,
                             'heures_td' : float_null_is_zero,
                             'heures_tp' :  float_null_is_zero,
                             'numero' : int_null_is_zero
                             },
        )

    security.declareProtected(ScoChangeFormation, 'do_module_create')
    def do_module_create(self, args, REQUEST):
        "create a module"
        # check
        if self.formation_has_locked_sems(args['formation_id']):
            raise ScoLockedFormError()
        # create
        cnx = self.GetDBConnexion()
        r = self._moduleEditor.create(cnx, args)
        self._inval_cache()
        # news
        F = self.do_formation_list(args={ 'formation_id' :args['formation_id']})[0]
        sco_news.add(REQUEST, cnx, typ=NEWS_FORM, object=args['formation_id'],
                     text='Modification de la formation %(acronyme)s' % F )
        return r

    security.declareProtected(ScoChangeFormation, 'do_module_delete')
    def do_module_delete(self, oid, REQUEST):
        "delete module"
        mod = self.do_module_list({ 'module_id' : oid})[0]
        if self.formation_has_locked_sems(mod['formation_id']):
            raise ScoLockedFormError()

        # S'il y a des moduleimpls, on ne peut pas detruire le module !
        mods = self.do_moduleimpl_list({'module_id' : oid })
        if mods:
            err_page = self.confirmDialog(
                message="""<h3>Destruction du module impossible car il est utilisé dans des semestres existants !</h3>""",
                helpmsg="""Il faut d'abord supprimer le semestre. Mais il est peut être préférable de laisser ce programme intact et d'en créer une nouvelle version pour la modifier.""",
                dest_url='ue_list',
                parameters = { 'formation_id' : mod['formation_id'] },
                REQUEST=REQUEST )
            raise ScoGenError(err_page)
        # delete
        cnx = self.GetDBConnexion()
        self._moduleEditor.delete(cnx, oid)
        self._inval_cache()
        # news
        F = self.do_formation_list(args={ 'formation_id' :mod['formation_id']})[0]
        sco_news.add(REQUEST, cnx, typ=NEWS_FORM, object=mod['formation_id'],
                     text='Modification de la formation %(acronyme)s' % F )

    security.declareProtected(ScoView, 'do_module_list')
    def do_module_list(self, *args, **kw ):
        "list modules"
        cnx = self.GetDBConnexion()
        return self._moduleEditor.list(cnx, *args, **kw)

    security.declareProtected(ScoChangeFormation, 'do_module_edit')
    def do_module_edit(self, *args, **kw ):
        "edit a module"
        # check
        mod = self.do_module_list({'module_id' : args[0]['module_id']})[0]
        if self.formation_has_locked_sems(mod['formation_id']):
            raise ScoLockedFormError()
        # edit
        cnx = self.GetDBConnexion()
        self._moduleEditor.edit(cnx, *args, **kw )
        self._inval_cache()

    #
    security.declareProtected(ScoView, 'formation_has_locked_sems')
    def formation_has_locked_sems(self, formation_id):
        "True if there is a locked formsemestre in this formation"
        sems = self.do_formsemestre_list(
            args={ 'formation_id' : formation_id,
                   'etat' : '0'} )
        return sems

    security.declareProtected(ScoView, 'formation_count_sems')
    def formation_count_sems(self, formation_id):
        "Number of formsemestre in this formation (locked or not)"
        sems = self.do_formsemestre_list(
            args={ 'formation_id' : formation_id } )
        return len(sems)

    security.declareProtected(ScoView, 'module_count_moduleimpls')
    def module_count_moduleimpls(self, module_id):
        "Number of moduleimpls using this module"
        mods = self.do_moduleimpl_list({'module_id' : module_id })
        return len(mods)
    
    # --- Semestres de formation
    _formsemestreEditor = EditableTable(
        'notes_formsemestre',
        'formsemestre_id',
        ('formsemestre_id', 'semestre_id', 'formation_id','titre',
         'date_debut', 'date_fin', 'responsable_id',
         'gestion_absence', 'bul_show_decision', 'bul_show_uevalid',
         'bul_show_codemodules', 
         'bul_show_ue_rangs', 'bul_show_mod_rangs',
         'gestion_compensation', 'gestion_semestrielle',
         'etat', 'bul_hide_xml', 'bul_bgcolor',
         'nomgroupetd', 'nomgroupetp', 'nomgroupeta',
         'etape_apo', 'modalite'
         ),
        sortkey = 'date_debut',
        output_formators = { 'date_debut' : DateISOtoDMY,
                             'date_fin'   : DateISOtoDMY,
                             'gestion_absence' : str,
                             'bul_show_decision' : str,
                             'bul_show_uevalid' : str,
                             'bul_show_codemodules' : str,
                             'bul_show_ue_rangs' : str,
                             'bul_show_mod_rangs' : str,
                             'gestion_compensation' : str,
                             'gestion_semestrielle' : str,
                             'etat' : str,
                             'bul_hide_xml' : str },

        input_formators  = { 'date_debut' : DateDMYtoISO,
                             'date_fin'   : DateDMYtoISO,
                             'gestion_absence' : int,
                             'bul_show_decision' : int,
                             'bul_show_uevalid' : int,
                             'bul_show_codemodules' : int,
                             'bul_show_ue_rangs' : int,
                             'bul_show_mod_rangs' : int,
                             'gestion_compensation' : int,
                             'gestion_semestrielle' : int,
                             'etat' : int,
                             'bul_hide_xml' : int },

        fields_creators = { 'bul_show_ue_rangs' : [
                'alter table notes_formsemestre add column bul_show_ue_rangs int',
                'alter table notes_formsemestre alter column bul_show_ue_rangs set default 1' ],
                            'bul_show_mod_rangs' : [
                'alter table notes_formsemestre add column bul_show_mod_rangs int',
                'alter table notes_formsemestre alter column bul_show_mod_rangs set default 1' ],
                            }
        )
    
    security.declareProtected(ScoImplement, 'do_formsemestre_create')
    def do_formsemestre_create(self, args, REQUEST):
        "create a formsemestre"
        cnx = self.GetDBConnexion()
        r = self._formsemestreEditor.create(cnx, args)
        self._inval_cache()
        # news
        if not args.has_key('titre'):
            args['titre'] = 'sans titre'
        args['formsemestre_id'] = r
        args['url'] = 'Notes/formsemestre_status?formsemestre_id=%(formsemestre_id)s'%args
        sco_news.add(REQUEST, cnx, typ=NEWS_SEM,
                     text='Création du semestre <a href="%(url)s">%(titre)s</a>' % args,
                     url=args['url'])
        return r

    security.declareProtected(ScoImplement, 'do_formsemestre_delete')
    def do_formsemestre_delete(self, formsemestre_id, REQUEST):
        "delete formsemestre, and all its moduleimpls"
        cnx = self.GetDBConnexion()
        sem = self.get_formsemestre(formsemestre_id)
        # --- Destruction des modules de ce semestre
        mods = self.do_moduleimpl_list( {'formsemestre_id':formsemestre_id} )
        for mod in mods:
            self.do_moduleimpl_delete(mod['moduleimpl_id'])
        # --- Desinscription des etudiants
        cursor = cnx.cursor()
        req = "DELETE FROM notes_formsemestre_inscription WHERE formsemestre_id=%(formsemestre_id)s"
        cursor.execute( req, { 'formsemestre_id' : formsemestre_id } )
        # --- Suppression des evenements
        req = "DELETE FROM scolar_events WHERE formsemestre_id=%(formsemestre_id)s"
        cursor.execute( req, { 'formsemestre_id' : formsemestre_id } )
        # --- Suppression des appreciations
        req = "DELETE FROM notes_appreciations WHERE formsemestre_id=%(formsemestre_id)s"
        cursor.execute( req, { 'formsemestre_id' : formsemestre_id } )
        # --- Supression des validations (!!!)
        req = "DELETE FROM scolar_formsemestre_validation WHERE formsemestre_id=%(formsemestre_id)s"
        cursor.execute( req, { 'formsemestre_id' : formsemestre_id } )
        # --- Suppression des autorisations
        req = "DELETE FROM scolar_autorisation_inscription WHERE origin_formsemestre_id=%(formsemestre_id)s"
        cursor.execute( req, { 'formsemestre_id' : formsemestre_id } )
        # --- Suppression des item du menu custom
        req = "DELETE FROM notes_formsemestre_custommenu WHERE formsemestre_id=%(formsemestre_id)s"
        cursor.execute( req, { 'formsemestre_id' : formsemestre_id } )
        # --- Destruction du semestre
        self._formsemestreEditor.delete(cnx, formsemestre_id)
        self._inval_cache()
        # news
        sco_news.add(REQUEST, cnx, typ=NEWS_SEM, object=formsemestre_id,
                     text='Suppression du semestre %(titre)s' % sem )

    security.declareProtected(ScoView, 'do_formsemestre_list')
    def do_formsemestre_list(self, *a, **kw ):
        "list formsemestres"
        #log('do_formsemestre_list: a=%s kw=%s' % (str(a),str(kw)))
        cnx = self.GetDBConnexion()
        #log( 'x %s' % str(self._formsemestreEditor.list(cnx)))
        try:
            sems = self._formsemestreEditor.list(cnx,*a,**kw)
        except:
            # debug (isodate bug !)
            log('*** do_formsemestre_list: exception')
            log('*** do_formsemestre_list: a=%s kw=%s' % (a,kw) )
            raise
        #log( 'sems=%s' % str(sems) )
        # ajoute titre + annee et dateord (pour tris)
        for sem in sems:
            # Ajoute nom avec numero semestre:
            sem['titre_num'] = sem['titre']
            if sem['semestre_id'] != -1:
                sem['titre_num'] += ' Semestre %s' % sem['semestre_id']

            sem['dateord'] = DateDMYtoISO(sem['date_debut'])
            try:
                mois_debut, annee_debut = sem['date_debut'].split('/')[1:]
            except:
                mois_debut, annee_debut = '', ''
            try:
                mois_fin, annee_fin = sem['date_fin'].split('/')[1:]
            except:
                mois_fin, annee_fin = '', ''
            sem['annee_debut'] = annee_debut
            sem['annee_fin'] = annee_fin
            sem['mois_debut_ord'] = int(mois_debut)
            sem['mois_fin_ord'] = int(mois_fin)
            
            sem['annee'] = annee_debut # 2007 ou 2007-2008
            
            sem['titreannee'] = '%s %s  %s' % (sem['titre_num'], sem.get('modalite',''), annee_debut)
            if annee_fin != annee_debut:
                sem['titreannee'] += '-' + annee_fin
                sem['annee'] += '-' + annee_fin
            # et les dates sous la forme "oct 2007 - fev 2008"
            months = scolars.abbrvmonthsnames
            if mois_debut:
                mois_debut = months[int(mois_debut)-1]
            if mois_fin:
                mois_fin = months[int(mois_fin)-1]
            sem['mois_debut'] = mois_debut + ' ' + annee_debut
            sem['mois_fin'] = mois_fin + ' ' + annee_fin
        
        # tri par date
        sems.sort(lambda x,y: cmp(y['dateord'],x['dateord']))

        return sems

    security.declareProtected(ScoView, 'get_formsemestre')
    def get_formsemestre(self, formsemestre_id):
        "list ONE formsemestre"
        return self.do_formsemestre_list(args={ 'formsemestre_id' : formsemestre_id } )[0]

    security.declareProtected(ScoView, 'XMLgetFormsemestres')
    def XMLgetFormsemestres(self, etape_apo=None, formsemestre_id=None, REQUEST=None):
        "List all formsemestres matching etape, XML format"
        args = {}
        if etape_apo:
            args['etape_apo'] = etape_apo
        if formsemestre_id:
            args['formsemestre_id'] = formsemestre_id
        if REQUEST:
            REQUEST.RESPONSE.setHeader('Content-type', XML_MIMETYPE)
        doc = jaxml.XML_document( encoding=SCO_ENCODING )
        doc.formsemestrelist()
        for sem in self.do_formsemestre_list( args=args ):
            doc._push()
            doc.formsemestre(sem)
            doc._pop()
        return repr(doc)

    security.declareProtected(ScoImplement, 'do_formsemestre_edit')
    def do_formsemestre_edit(self, *a, **kw ):
        "edit a formsemestre"
        cnx = self.GetDBConnexion()
        self._formsemestreEditor.edit(cnx, *a, **kw )
        self._inval_cache()

    security.declareProtected(ScoImplement, 'do_formsemestre_createwithmodules')
    do_formsemestre_createwithmodules = sco_formsemestre_edit.do_formsemestre_createwithmodules

    security.declareProtected(ScoView,'formsemestre_edit_uecoefs')
    formsemestre_edit_uecoefs = sco_formsemestre_edit.formsemestre_edit_uecoefs

    security.declareProtected(ScoView,'formsemestre_edit_options')
    formsemestre_edit_options = sco_formsemestre_edit.formsemestre_edit_options

    security.declareProtected(ScoView,'formsemestre_change_lock')
    formsemestre_change_lock = sco_formsemestre_edit.formsemestre_change_lock

    def _check_access_diretud(self, formsemestre_id, REQUEST):
        """Check if access granted: responsable_id or ScoImplement
        Return True|False, HTML_error_page
        """
        authuser = REQUEST.AUTHENTICATED_USER
        sem = self.get_formsemestre(formsemestre_id)
        header = self.sco_header(page_title='Accès interdit',
                                 REQUEST=REQUEST)
        footer = self.sco_footer(REQUEST)
        if ((sem['responsable_id'] != str(authuser))
            and not authuser.has_permission(ScoImplement,self)):
            return False, '\n'.join( [
                header,
                '<h2>Opération non autorisée pour %s</h2>' % authuser,
                '<p>Responsable de ce semestre : <b>%s</b></p>'
                % sem['responsable_id'],
                footer ])
        else:
            return True, ''
        

    security.declareProtected(ScoView,'formsemestre_pagebulletin_dialog')
    def formsemestre_pagebulletin_dialog(self, REQUEST, formsemestre_id):
        "Dialogue mise en page bulletin"
        # Ad-Hoc access control (dir. etud)
        ok, err = self._check_access_diretud(formsemestre_id,REQUEST)
        if not ok:
            return err
        return sco_pagebulletin.formsemestre_pagebulletin_dialog(
            self, REQUEST, formsemestre_id )

    security.declareProtected(ScoView,'formsemestre_custommenu_edit')
    def formsemestre_custommenu_edit(self, REQUEST, formsemestre_id):
        "Dialogue modif menu"
        # accessible à tous !
        return sco_formsemestre_custommenu.formsemestre_custommenu_edit(
            self, formsemestre_id, REQUEST=REQUEST)

    security.declareProtected(ScoView,'formsemestre_custommenu_html')
    formsemestre_custommenu_html = sco_formsemestre_custommenu.formsemestre_custommenu_html
    
    # --- Gestion des "Implémentations de Modules"
    # Un "moduleimpl" correspond a la mise en oeuvre d'un module
    # dans une formation spécifique, à une date spécifique.
    _moduleimplEditor = EditableTable(
        'notes_moduleimpl',
        'moduleimpl_id',
        ('moduleimpl_id','module_id','formsemestre_id','responsable_id'),
        )

    _modules_enseignantsEditor = EditableTable(
        'notes_modules_enseignants',
        'modules_enseignants_id',
        ('modules_enseignants_id','moduleimpl_id','ens_id'),
        )
    
    security.declareProtected(ScoImplement, 'do_moduleimpl_create')
    def do_moduleimpl_create(self, args):
        "create a moduleimpl"
        cnx = self.GetDBConnexion()
        r = self._moduleimplEditor.create(cnx, args)
        self._inval_cache()
        return r

    security.declareProtected(ScoImplement, 'do_moduleimpl_delete')
    def do_moduleimpl_delete(self, oid):
        "delete moduleimpl (desinscrit tous ls etudiants)"
        cnx = self.GetDBConnexion()
        # --- desinscription des etudiants
        cursor = cnx.cursor()
        req = "DELETE FROM notes_moduleimpl_inscription WHERE moduleimpl_id=%(moduleimpl_id)s"
        cursor.execute( req, { 'moduleimpl_id' : oid } )
        # --- suppression des enseignants
        cursor.execute( "DELETE FROM notes_modules_enseignants WHERE moduleimpl_id=%(moduleimpl_id)s", { 'moduleimpl_id' : oid } )
        # --- destruction du moduleimpl
        self._moduleimplEditor.delete(cnx, oid)
        self._inval_cache()

    security.declareProtected(ScoView, 'do_moduleimpl_list')
    def do_moduleimpl_list(self, *args, **kw ):
        "list moduleimpls"
        cnx = self.GetDBConnexion()
        modimpls = self._moduleimplEditor.list(cnx, *args, **kw)
        # Ajoute la liste des enseignants
        for mo in modimpls:
            mo['ens'] = self.do_ens_list(
                args={'moduleimpl_id':mo['moduleimpl_id']})
        return modimpls

    security.declareProtected(ScoImplement, 'do_moduleimpl_edit')
    def do_moduleimpl_edit(self, *args, **kw ):
        "edit a moduleimpl"
        cnx = self.GetDBConnexion()
        self._moduleimplEditor.edit(cnx, *args, **kw )
        self._inval_cache()

    security.declareProtected(ScoView, 'do_moduleimpl_withmodule_list')
    def do_moduleimpl_withmodule_list(self,args):
        """Liste les moduleimpls et ajoute dans chacun le module correspondant
        Tri la liste par numero de module
        """
        modimpls = self.do_moduleimpl_list(args)
        for mo in modimpls:
            mo['module'] = self.do_module_list(
                args={'module_id':mo['module_id']})[0]
            mo['ue'] = self.do_ue_list( args={'ue_id' : mo['module']['ue_id']} )[0]
            mo['matiere'] = self.do_matiere_list( args={'matiere_id':mo['module']['matiere_id']} )[0]
        
        # tri par semestre/UE/numero_matiere/numero_module
        
        extr = lambda x: (x['ue']['numero'], x['ue']['ue_id'],
                          x['matiere']['numero'], x['matiere']['matiere_id'],
                          x['module']['numero'])
        
        modimpls.sort(lambda x,y: cmp(extr(x), extr(y)))
        #log('after sort args=%s' % args)
        #log( ',\n'.join( [ str(extr(m)) for m in modimpls ] ))        
        #log('after sort: Mlist=\n' + ',\n'.join( [ str(m) for m in  modimpls ] ) + '\n')
        return modimpls

    security.declareProtected(ScoView,'do_ens_list')
    def do_ens_list(self, *args, **kw ):
        "liste les enseignants d'un moduleimpl (pas le responsable)"
        cnx = self.GetDBConnexion()
        ens = self._modules_enseignantsEditor.list(cnx, *args, **kw)
        return ens

    security.declareProtected(ScoImplement, 'do_ens_edit')
    def do_ens_edit(self, *args, **kw ):
        "edit ens"
        cnx = self.GetDBConnexion()
        self._modules_enseignantsEditor.edit(cnx, *args, **kw )

    security.declareProtected(ScoImplement, 'do_ens_create')
    def do_ens_create(self, args):
        "create ens"
        cnx = self.GetDBConnexion()
        r = self._modules_enseignantsEditor.create(cnx, args)
        return r

    security.declareProtected(ScoImplement, 'do_ens_delete')
    def do_ens_delete(self, oid):
        "delete ens"
        cnx = self.GetDBConnexion()
        r = self._modules_enseignantsEditor.delete(cnx, oid)
        return r

    # --- dialogue modif enseignants/moduleimpl
    security.declareProtected(ScoView, 'edit_enseignants_form')
    def edit_enseignants_form(self, REQUEST, moduleimpl_id):
        "modif liste enseignants/moduleimpl"
        M, sem = self.can_change_ens(REQUEST, moduleimpl_id)
        # --
        header = self.sco_header(REQUEST,
                                 page_title='Enseignants du module %s' % M['module']['titre'])
        footer = self.sco_footer(REQUEST)
        H = [ '<h2>Semestre %s, du %s au %s</h2>'
              % (sem['titre_num'], sem['date_debut'], sem['date_fin']),
              '<h3>Enseignants du <a href="moduleimpl_status?moduleimpl_id=%s">module %s</a></h3>' % (moduleimpl_id, M['module']['titre']),
              '<ul><li>%s (responsable)</li>' % M['responsable_id']
              ]
        for ens in M['ens']:
            H.append('<li>%s (<a class="stdlink" href="edit_enseignants_form_delete?moduleimpl_id=%s&ens_id=%s">supprimer</a>)</li>' %
                     (self.Users.user_info(ens['ens_id'],REQUEST)['nomprenom'], moduleimpl_id, ens['ens_id']))
        H.append('</ul>')
        F = """<p class="help">Les enseignants d'un module ont le droit de
        saisir et modifier toutes les notes des évaluations de ce module.
        </p>
        <p class="help">Pour changer le responsable du module, passez par la
        page "<a class="stdlink" href="formsemestre_editwithmodules?formation_id=%s&formsemestre_id=%s">Modification du semestre</a>", accessible uniquement au responsable de la formation (chef de département)
        </p>
        """ % (sem['formation_id'],M['formsemestre_id'])
        userlist = self.getZopeUsers()
        iii = []
        for user in userlist: # XXX may be slow on large user base ?
            info = self.Users.user_info(user,REQUEST)
            iii.append( (info['nom'].upper(), info['nomprenom'], user) )
        iii.sort()
        nomprenoms = [ x[1] for x in iii ]
        userlist =  [ x[2] for x in iii ]
        modform = [
            ('moduleimpl_id', { 'input_type' : 'hidden' }),
            ('ens_id',
             { 'input_type' : 'menu',
               'title' : 'Ajouter un enseignant',
               'allowed_values' : [''] + userlist,
               'labels' : ['Choisir un enseignant...'] + nomprenoms })
            ]
        tf = TrivialFormulator( REQUEST.URL0, REQUEST.form, modform,
                                submitlabel = 'Ajouter enseignant',
                                cancelbutton = 'Annuler')
        if tf[0] == 0:
            return header + '\n'.join(H) + tf[1] + F + footer
        elif tf[0] == -1:
            return REQUEST.RESPONSE.redirect('moduleimpl_status?moduleimpl_id='+moduleimpl_id)
        else:
            ens_id = tf[2]['ens_id']
            # verifie qu'il existe
            if not ens_id in userlist:
                H.append('<p class="help">Pour ajouter un enseignant, choisissez un nom dans le menu</p>')
            else:
                # et qu'il n'est pas deja:
                if ens_id in [ x['ens_id'] for x in M['ens'] ]:
                    H.append('<p class="help">Enseignant %s déjà dans la liste !</p>' % ens_id)
                else:                    
                    self.do_ens_create( { 'moduleimpl_id' : moduleimpl_id,
                                          'ens_id' : ens_id } )
                    return REQUEST.RESPONSE.redirect('edit_enseignants_form?moduleimpl_id=%s'%moduleimpl_id)
            return header + '\n'.join(H) + tf[1] + F + footer

    security.declareProtected(ScoView, 'formsemestre_enseignants_list')
    def formsemestre_enseignants_list(self, REQUEST, formsemestre_id, format='html'):
        """Liste les enseignants intervenants dans le semestre (resp. modules et chargés de TD)
        et indique les absences saisies par chacun.
        """
        sem = self.get_formsemestre(formsemestre_id)
        # resp. de modules:
        mods = self.do_moduleimpl_withmodule_list( args={'formsemestre_id' : formsemestre_id} )
        sem_ens = {}
        for mod in mods:
            if not mod['responsable_id'] in sem_ens:
                sem_ens[mod['responsable_id']] = { 'mods' : [mod] }
            else:
                sem_ens[mod['responsable_id']]['mods'].append(mod)
        # charges de TD:
        for mod in mods:
            for ensd in mod['ens']:
                if not ensd['ens_id'] in sem_ens:
                    sem_ens[ensd['ens_id']] = { 'mods' : [mod] }
                else:
                    sem_ens[ensd['ens_id']]['mods'].append(mod)
        # compte les absences ajoutées par chacun dans tout le semestre
        cnx = self.GetDBConnexion()
        cursor = cnx.cursor()
        for ens in sem_ens:
            cursor.execute("select * from scolog L, notes_formsemestre_inscription I where method='AddAbsence' and authenticated_user=%(authenticated_user)s and L.etudid = I.etudid and  I.formsemestre_id=%(formsemestre_id)s and date > %(date_debut)s and date < %(date_fin)s", { 'authenticated_user' : ens, 'formsemestre_id' : formsemestre_id, 'date_debut' : DateDMYtoISO(sem['date_debut']), 'date_fin' : DateDMYtoISO(sem['date_fin']) })
            
            events = cursor.dictfetchall()
            sem_ens[ens]['nbabsadded'] = len(events)
        
        # description textuelle des modules
        for ens in sem_ens:
            sem_ens[ens]['descr_mods'] = ', '.join([ x['module']['code'] for x in sem_ens[ens]['mods'] ])
        
        # ajoute infos sur enseignant:
        for ens in sem_ens:
            sem_ens[ens]['ensinfo'] = self.Users.user_info(ens,REQUEST)
            sem_ens[ens]['nomprenom'] = sem_ens[ens]['ensinfo']['nomprenom']

        sem_ens_list = sem_ens.values()
        sem_ens_list.sort(lambda x,y:  cmp(x['nomprenom'],y['nomprenom']))

        # --- Generate page with table
        title = 'Enseignants de ' + sem['titreannee']
        T = GenTable( columns_ids=['nomprenom', 'descr_mods', 'nbabsadded'],
                      titles={'nomprenom' : 'Enseignant', 'descr_mods': 'Modules',
                              'nbabsadded' : 'Saisies Abs.' },
                      rows=sem_ens_list, html_sortable=True,
                      filename = make_filename('Enseignants-' + sem['titreannee']),
                      html_title = '<h2>Enseignants de <a href="formsemestre_status?formsemestre_id=%s">%s</a></h2>' % (formsemestre_id,sem['titreannee']),
                      base_url= '%s?formsemestre_id=%s' % (REQUEST.URL0, formsemestre_id),
                      caption="Tous les enseignants (responsables ou associés aux modules de ce semestre) apparaissent. Le nombre de saisies d'absences est le nombre d'opérations d'ajout effectuées sur ce semestre, sans tenir compte des annulations ou double saisies.",
                      preferences=self.get_preferences()
                      )
        return T.make_page(self, page_title=title, title=title, REQUEST=REQUEST, format=format)

    # menu evaluation dans moduleimpl
    security.declareProtected(ScoView, 'moduleimpl_evaluation_menu')
    def moduleimpl_evaluation_menu(self, evaluation_id, nbnotes=0, REQUEST=None):
        "Menu avec actions sur une evaluation"
        E = self.do_evaluation_list({'evaluation_id' : evaluation_id})[0]
        modimpl = self.do_moduleimpl_list({'moduleimpl_id' : E['moduleimpl_id']})[0]
        
        menuEval = [
            { 'title' : 'Saisir notes',
              'url' : 'notes_eval_selectetuds?evaluation_id=' + evaluation_id,
              'enabled' : self.can_edit_notes(REQUEST.AUTHENTICATED_USER, E['moduleimpl_id'])
              },
            { 'title' : 'Modifier évaluation',
              'url' : 'evaluation_edit?evaluation_id=' + evaluation_id,
              'enabled' : self.can_edit_notes(REQUEST.AUTHENTICATED_USER, E['moduleimpl_id'], allow_ens=False)
              },
            { 'title' : 'Afficher les notes',
              'url' : 'evaluation_listenotes?evaluation_id=' + evaluation_id,
              'enabled' : nbnotes > 0
              },
            { 'title' : 'Supprimer évaluation',
              'url' : 'evaluation_delete?evaluation_id=' + evaluation_id,
              'enabled' : nbnotes == 0 and self.can_edit_notes(REQUEST.AUTHENTICATED_USER, E['moduleimpl_id'], allow_ens=False)
              },
            { 'title' : 'Absences ce jour',
              'url' : 'Absences/EtatAbsencesDate?semestregroupe=%s%%21%%21%%21&date=%s'
              % (modimpl['formsemestre_id'], urllib.quote(E['jour'],safe='')),
              'enabled' : E['jour']
              },
            { 'title' : 'Vérifier notes vs absents',
              'url' : 'evaluation_check_absences_html?evaluation_id=' + evaluation_id,
              'enabled' : nbnotes > 0
              },
            ]
            
        return makeMenu( 'actions', menuEval )

    security.declareProtected(ScoView, 'edit_enseignants_form_delete')
    def edit_enseignants_form_delete(self, REQUEST, moduleimpl_id, ens_id):
        "remove ens"
        M, sem = self.can_change_ens(REQUEST, moduleimpl_id)
        # search ens_id
        ok = False
        for ens in M['ens']:
            if ens['ens_id'] == ens_id:
                ok = True
                break
        if not ok:
            raise ScoValueError('invalid ens_id (%s)' % ens_id)
        self.do_ens_delete(ens['modules_enseignants_id'])
        return REQUEST.RESPONSE.redirect('edit_enseignants_form?moduleimpl_id=%s'%moduleimpl_id)

    security.declareProtected(ScoView,'can_change_ens')
    def can_change_ens(self, REQUEST, moduleimpl_id):
        "check if current user can modify ens list (raise exception if not)"
        M = self.do_moduleimpl_withmodule_list(args={ 'moduleimpl_id' : moduleimpl_id})[0]
        # -- check lock
        sem = self.get_formsemestre(M['formsemestre_id'])
        if sem['etat'] != '1':
            raise ScoValueError('Modification impossible: semestre verrouille')
        # -- check access
        authuser = REQUEST.AUTHENTICATED_USER
        uid = str(authuser)
        # admin, resp. module ou resp. semestre
        if (uid != M['responsable_id']
            and not authuser.has_permission(ScoImplement, self)
            and uid != sem['responsable_id']):
            raise AccessDenied('Modification impossible pour %s' % uid)
        return M, sem
    
    # --- Gestion des inscriptions aux modules
    _formsemestre_inscriptionEditor = EditableTable(
        'notes_formsemestre_inscription',
        'formsemestre_inscription_id',
        ('formsemestre_inscription_id', 'etudid', 'formsemestre_id',
         'groupetd', 'groupetp', 'groupeanglais', 'etat'),
        sortkey = 'formsemestre_id'
        )
    
    security.declareProtected(ScoEtudInscrit,'do_formsemestre_inscription_create')
    def do_formsemestre_inscription_create(self, args, REQUEST, method=None ):
        "create a formsemestre_inscription (and sco event)"
        cnx = self.GetDBConnexion()
        log('do_formsemestre_inscription_create: args=%s' % str(args))
        # check lock
        sems = self.do_formsemestre_list(
            {'formsemestre_id':args['formsemestre_id']})
        if len(sems) != 1:
            raise ScoValueError('code de semestre invalide: %s'%args['formsemestre_id'])
        sem = sems[0]
        if sem['etat'] != '1':
            raise ScoValueError('inscription: semestre verrouille')
        #
        r = self._formsemestre_inscriptionEditor.create(cnx, args)
        # Evenement
        scolars.scolar_events_create( cnx, args = {
            'etudid' : args['etudid'],
            'event_date' : time.strftime('%d/%m/%Y'),
            'formsemestre_id' : args['formsemestre_id'],
            'event_type' : 'INSCRIPTION' } )
        # Log etudiant
        logdb(REQUEST, cnx, method=method,
              etudid=args['etudid'], msg='inscription initiale',
              commit=False )
        #
        self._inval_cache()
        return r

    security.declareProtected(ScoImplement, 'do_formsemestre_inscription_delete')
    def do_formsemestre_inscription_delete(self, oid):
        "delete formsemestre_inscription"
        cnx = self.GetDBConnexion()
        self._formsemestre_inscriptionEditor.delete(cnx, oid)
        self._inval_cache()

    security.declareProtected(ScoView, 'do_formsemestre_inscription_list')
    def do_formsemestre_inscription_list(self, *args, **kw ):
        "list formsemestre_inscriptions"
        cnx = self.GetDBConnexion()        
        return self._formsemestre_inscriptionEditor.list(cnx, *args, **kw)

    security.declareProtected(ScoView, 'do_formsemestre_inscription_listinscrits')
    def do_formsemestre_inscription_listinscrits(self, formsemestre_id):
        """Liste les inscrits (état I) à ce semestre et cache le résultat"""
        cache = self.get_formsemestre_inscription_cache()
        r = cache.get(formsemestre_id)
        if r != None:
            return r
        # retreive list
        r = self.do_formsemestre_inscription_list(args={ 'formsemestre_id' : formsemestre_id, 'etat' : 'I' } )
        cache.set(formsemestre_id,r)
        return r
    
    security.declareProtected(ScoImplement, 'do_formsemestre_inscription_edit')
    def do_formsemestre_inscription_edit(self, **kw ):
        "edit a formsemestre_inscription"
        cnx = self.GetDBConnexion()
        self._formsemestre_inscriptionEditor.edit(cnx, **kw )
        self._inval_cache()

    security.declareProtected(ScoView,'do_formsemestre_inscription_listegroupes')
    def do_formsemestre_inscription_listegroupes(self, formsemestre_id):
        "donne la liste des groupes dans ce semestre (td, tp, anglais)"
        cnx = self.GetDBConnexion()
        ins = self._formsemestre_inscriptionEditor.list(
            cnx, args={'formsemestre_id':formsemestre_id} )
        gr_td = {}.fromkeys( [ x['groupetd'] for x in ins if x['groupetd'] ] ).keys()
        gr_tp = {}.fromkeys( [ x['groupetp'] for x in ins if x['groupetp'] ] ).keys()
        gr_anglais = {}.fromkeys( [ x['groupeanglais'] for x in ins if x['groupeanglais'] ] ).keys()
        gr_td.sort()
        gr_tp.sort()
        gr_anglais.sort()
        return gr_td, gr_tp, gr_anglais

    # Cache inscriptions semestres
    def get_formsemestre_inscription_cache(self):
        url = self.ScoURL()
        if CACHE_formsemestre_inscription.has_key(url):
            return CACHE_formsemestre_inscription[url]
        else:
            log('get_formsemestre_inscription_cache: new simpleCache')
            CACHE_formsemestre_inscription[url] = sco_cache.simpleCache()
            return CACHE_formsemestre_inscription[url]


    security.declareProtected(ScoImplement, 'formsemestre_desinscription')
    def formsemestre_desinscription(self, etudid, formsemestre_id, REQUEST=None, dialog_confirmed=False):
        """desinscrit l'etudiant de ce semestre (et donc de tous les modules).
        A n'utiliser qu'en cas d'erreur de saisie"""
        sem = self.get_formsemestre(formsemestre_id)
        # -- check lock
        if sem['etat'] != '1':
            raise ScoValueError('desinscription impossible: semestre verrouille')
        
        if not dialog_confirmed:
            etud = self.getEtudInfo(etudid=etudid,filled=1)[0]
            return self.confirmDialog(
                """<h2>Confirmer la demande de desinscription ?</h2>
                <p>%s sera désinscrit de tous les modules du semestre %s (%s - %s).</p>
                <p>Cette opération ne doit être utilisée que pour corriger une <b>erreur</b> !
                Un étudiant réellement inscrit doit le rester, le faire éventuellement <b>démissionner<b>.
                </p>
                """ % (etud['nomprenom'],sem['titre_num'],sem['date_debut'],sem['date_fin']),
                dest_url="", REQUEST=REQUEST,
                cancel_url="formsemestre_status?formsemestre_id=%s" % formsemestre_id,
                parameters={'etudid':etudid, 'formsemestre_id' : formsemestre_id})

        self.do_formsemestre_desinscription(etudid, formsemestre_id)
        
        return self.sco_header(REQUEST) + '<p>Etudiant désinscrit !</p><p><a class="stdlink" href="%s/ficheEtud?etudid=%s">retour à la fiche</a>'%(self.ScoURL(),etudid) + self.sco_footer(REQUEST)


    def do_formsemestre_desinscription(self, etudid, formsemestre_id):
        "Deinscription d'un étudiant"
        sem = self.get_formsemestre(formsemestre_id)
        # -- check lock
        if sem['etat'] != '1':
            raise ScoValueError('desinscription impossible: semestre verrouille')
        # -- desinscription de tous les modules
        cnx = self.GetDBConnexion()
        cursor = cnx.cursor()
        cursor.execute( "select moduleimpl_inscription_id from notes_moduleimpl_inscription Im, notes_moduleimpl M  where Im.etudid=%(etudid)s and Im.moduleimpl_id = M.moduleimpl_id and M.formsemestre_id = %(formsemestre_id)s",
                        { 'etudid' : etudid, 'formsemestre_id' : formsemestre_id } )
        res = cursor.fetchall()
        moduleimpl_inscription_ids = [ x[0] for x in res ]
        for moduleimpl_inscription_id in moduleimpl_inscription_ids:
            self.do_moduleimpl_inscription_delete(moduleimpl_inscription_id)
        # -- desincription du semestre
        insem = self.do_formsemestre_inscription_list(
            args={ 'formsemestre_id' : formsemestre_id, 'etudid' : etudid } )[0]
        self.do_formsemestre_inscription_delete( insem['formsemestre_inscription_id'] )

    
    # --- Inscriptions aux modules
    _moduleimpl_inscriptionEditor = EditableTable(
        'notes_moduleimpl_inscription',
        'moduleimpl_inscription_id',
        ('moduleimpl_inscription_id', 'etudid', 'moduleimpl_id'),
        )

    security.declareProtected(ScoEtudInscrit,'do_moduleimpl_inscription_create')
    def do_moduleimpl_inscription_create(self, args, REQUEST=None):
        "create a moduleimpl_inscription"
        cnx = self.GetDBConnexion()
        log('do_moduleimpl_inscription_create: '+ str(args))
        r = self._moduleimpl_inscriptionEditor.create(cnx, args)
        self._inval_cache()
        if REQUEST:
            logdb(REQUEST, cnx, method='moduleimpl_inscription',
                  etudid=args['etudid'],
                  msg='inscription module %s' % args['moduleimpl_id'],
                  commit=False )
        return r

    security.declareProtected(ScoImplement, 'do_moduleimpl_inscription_delete')
    def do_moduleimpl_inscription_delete(self, oid):
        "delete moduleimpl_inscription"
        cnx = self.GetDBConnexion()
        self._moduleimpl_inscriptionEditor.delete(cnx, oid)
        self._inval_cache()

    security.declareProtected(ScoView, 'do_moduleimpl_inscription_list')
    def do_moduleimpl_inscription_list(self, **kw ):
        "list moduleimpl_inscriptions"
        cnx = self.GetDBConnexion()
        return self._moduleimpl_inscriptionEditor.list(cnx, **kw)

    security.declareProtected(ScoEtudInscrit, 'do_moduleimpl_inscription_edit')
    def do_moduleimpl_inscription_edit(self, *args, **kw ):
        "edit a moduleimpl_inscription"
        cnx = self.GetDBConnexion()
        self._moduleimpl_inscriptionEditor.edit(cnx, *args, **kw )
        self._inval_cache()

    security.declareProtected(ScoView, 'do_moduleimpl_listeetuds')
    def do_moduleimpl_listeetuds(self, moduleimpl_id):
        "retourne liste des etudids inscrits a ce module"
        req = "select distinct Im.etudid from notes_moduleimpl_inscription Im, notes_formsemestre_inscription Isem, notes_moduleimpl M where Isem.etudid=Im.etudid and Im.moduleimpl_id=M.moduleimpl_id and M.moduleimpl_id = %(moduleimpl_id)s"
        cnx = self.GetDBConnexion()
        cursor = cnx.cursor()    
        cursor.execute( req, { 'moduleimpl_id' : moduleimpl_id } )
        res = cursor.fetchall()
        return [ x[0] for x in res ]

    security.declareProtected(ScoEtudInscrit,'do_moduleimpl_inscrit_tout_semestre')
    def do_moduleimpl_inscrit_tout_semestre(self,
                                            moduleimpl_id,formsemestre_id):
        "inscrit tous les etudiants inscrit au semestre a ce module"
        cnx = self.GetDBConnexion()
        cursor = cnx.cursor()
        req = """INSERT INTO notes_moduleimpl_inscription
                             (moduleimpl_id, etudid)
                    SELECT %(moduleimpl_id)s, I.etudid
                    FROM  notes_formsemestre_inscription I
                    WHERE I.formsemestre_id=%(formsemestre_id)s"""
        args = { 'moduleimpl_id':moduleimpl_id,
                 'formsemestre_id':formsemestre_id }
        cursor.execute( req, args )

    security.declareProtected(ScoEtudInscrit,'do_moduleimpl_inscrit_etuds')
    def do_moduleimpl_inscrit_etuds(self,
                                    moduleimpl_id, formsemestre_id, etudids,
                                    reset=False,
                                    REQUEST=None):
        """Inscrit les etudiants (liste d'etudids) a ce module.
        Si reset, desinscrit tous les autres.
        """
        # Verifie qu'ils sont tous bien inscrits au semestre
        for etudid in etudids:
            insem = self.do_formsemestre_inscription_list( args={ 'formsemestre_id' : formsemestre_id, 'etudid' : etudid } )
            if not insem:
                raise ScoValueError("%s n'est pas inscrit au semestre !" % etudid)

        # Desinscriptions
        if reset:
            cnx = self.GetDBConnexion()
            cursor = cnx.cursor()
            cursor.execute( "delete from notes_moduleimpl_inscription where moduleimpl_id = %(moduleimpl_id)s", { 'moduleimpl_id' : moduleimpl_id })
        # Inscriptions au module:
        inmod_set = Set( [ x['etudid'] for x in self.do_moduleimpl_inscription_list( args={ 'moduleimpl_id' : moduleimpl_id } ) ])
        for etudid in etudids:
            # deja inscrit ?
            if not etudid in inmod_set:
                self.do_moduleimpl_inscription_create( { 'moduleimpl_id' :moduleimpl_id, 'etudid' :etudid }, REQUEST=REQUEST )
        
    # --- Inscriptions
    security.declareProtected(ScoEtudInscrit,'do_formsemestre_inscription_with_modules')
    do_formsemestre_inscription_with_modules = sco_formsemestre_inscriptions.do_formsemestre_inscription_with_modules

    security.declareProtected(ScoEtudInscrit,'formsemestre_inscription_with_modules_form')
    formsemestre_inscription_with_modules_form = sco_formsemestre_inscriptions.formsemestre_inscription_with_modules_form

    security.declareProtected(ScoEtudInscrit,'formsemestre_inscription_with_modules_etud')
    formsemestre_inscription_with_modules_etud = sco_formsemestre_inscriptions.formsemestre_inscription_with_modules_etud
    
    security.declareProtected(ScoEtudInscrit,'formsemestre_inscription_with_modules')
    formsemestre_inscription_with_modules = sco_formsemestre_inscriptions.formsemestre_inscription_with_modules

    security.declareProtected(ScoEtudInscrit,'formsemestre_inscription_option')
    formsemestre_inscription_option = sco_formsemestre_inscriptions.formsemestre_inscription_option

    security.declareProtected(ScoEtudInscrit,'do_moduleimpl_incription_options')
    do_moduleimpl_incription_options = sco_formsemestre_inscriptions.do_moduleimpl_incription_options

    security.declareProtected(ScoView, 'formsemestre_inscrits_ailleurs')
    formsemestre_inscrits_ailleurs = sco_formsemestre_inscriptions.formsemestre_inscrits_ailleurs

    security.declareProtected(ScoEtudInscrit,'moduleimpl_inscriptions_edit')
    moduleimpl_inscriptions_edit = sco_moduleimpl_inscriptions.moduleimpl_inscriptions_edit

    security.declareProtected(ScoView,'moduleimpl_inscriptions_stats')
    moduleimpl_inscriptions_stats = sco_moduleimpl_inscriptions.moduleimpl_inscriptions_stats

    # --- Evaluations
    _evaluationEditor = EditableTable(
        'notes_evaluation',
        'evaluation_id',
        ('evaluation_id', 'moduleimpl_id',
         'jour', 'heure_debut', 'heure_fin', 'description',
         'note_max', 'coefficient', 'visibulletin' ),
        sortkey = 'jour desc',
        output_formators = { 'jour' : DateISOtoDMY,
                             'heure_debut' : TimefromISO8601,
                             'heure_fin'   : TimefromISO8601,
                             'visibulletin': str
                             },
        input_formators  = { 'jour' : DateDMYtoISO,
                             'heure_debut' : TimetoISO8601,
                             'heure_fin'   : TimetoISO8601,
                             'visibulletin': int
                             }
        )

    def _evaluation_check_write_access(self, REQUEST, moduleimpl_id=None):
        """Vérifie que l'on a le droit de modifier, créer ou détruire une
        évaluation dans ce module.
        Sinon, lance une exception.
        (nb: n'implique pas le droit de saisir ou modifier des notes)
        """
        # acces pour resp. moduleimpl et resp. form semestre (dir etud)
        if moduleimpl_id is None:
            raise ValueError('no moduleimpl specified') # bug
        authuser = REQUEST.AUTHENTICATED_USER
        uid = str(authuser)
        M = self.do_moduleimpl_list( args={ 'moduleimpl_id':moduleimpl_id } )[0]
        sem = self.get_formsemestre(M['formsemestre_id'])
        
        if (not authuser.has_permission(ScoEditAllEvals,self)) and uid != M['responsable_id'] and uid != sem['responsable_id']:
            raise AccessDenied('Modification évaluation impossible pour %s'%(uid,))
    
    security.declareProtected(ScoEnsView,'do_evaluation_create')
    def do_evaluation_create(self, REQUEST, args):
        "create a evaluation"
        moduleimpl_id = args['moduleimpl_id']
        self._evaluation_check_write_access(REQUEST, moduleimpl_id=moduleimpl_id)
        self._check_evaluation_args(args)
        #
        cnx = self.GetDBConnexion()
        r = self._evaluationEditor.create(cnx, args)
        # inval cache pour ce semestre
        M = self.do_moduleimpl_list( args={ 'moduleimpl_id':moduleimpl_id } )[0]
        
        self._inval_cache(formsemestre_id=M['formsemestre_id'])
        # news
        mod = self.do_module_list( args={ 'module_id':M['module_id'] } )[0]
        mod['moduleimpl_id'] = M['moduleimpl_id']
        mod['url'] = "Notes/moduleimpl_status?moduleimpl_id=%(moduleimpl_id)s"%mod
        sco_news.add(REQUEST, cnx, typ=NEWS_NOTE, object=moduleimpl_id,
                     text='Création d\'une évaluation dans <a href="%(url)s">%(titre)s</a>' % mod,
                     url=mod['url'])

        return r

    def _check_evaluation_args(self, args):
        "raise exception if invalid args"
        moduleimpl_id = args['moduleimpl_id']
        # check date
        jour = args.get('jour', None)
        if jour:
            M = self.do_moduleimpl_list( args={ 'moduleimpl_id' : moduleimpl_id } )[0]
            sem = self.get_formsemestre(M['formsemestre_id'])
            d,m,y = [ int(x) for x in sem['date_debut'].split('/') ]
            date_debut = datetime.date(y,m,d)
            d,m,y = [ int(x) for x in sem['date_fin'].split('/') ]
            date_fin = datetime.date(y,m,d)
            # passe par DateDMYtoISO pour avoir date pivot
            y,m,d = [ int(x) for x in DateDMYtoISO(jour).split('-') ]
            jour = datetime.date(y,m,d)
            if (jour > date_fin) or (jour < date_debut):
                raise ScoValueError("La date de l'évaluation n'est pas dans le semestre !")
        heure_debut = args.get('heure_debut', None)
        heure_fin = args.get('heure_fin', None)
        d = TimeDuration(heure_debut, heure_fin)
        if d and ((d < 0) or (d > 60*12)):
            raise ScoValueError("Heures de l'évaluation incohérentes !")            


    security.declareProtected(ScoEnsView, 'do_evaluation_delete')
    def do_evaluation_delete(self, REQUEST, evaluation_id):
        "delete evaluation"
        the_evals = self.do_evaluation_list( 
                {'evaluation_id' : evaluation_id})
        if not the_evals:
            raise ValueError, "evaluation inexistante !"
        
        moduleimpl_id = the_evals[0]['moduleimpl_id']
        self._evaluation_check_write_access( REQUEST, moduleimpl_id=moduleimpl_id)
        cnx = self.GetDBConnexion()
        self._evaluationEditor.delete(cnx, evaluation_id)
        # inval cache pour ce semestre
        M = self.do_moduleimpl_list( args={ 'moduleimpl_id':moduleimpl_id } )[0]
        self._inval_cache(formsemestre_id=M['formsemestre_id'])
        # news
        mod = self.do_module_list( args={ 'module_id':M['module_id'] } )[0]
        mod['moduleimpl_id'] = M['moduleimpl_id']
        mod['url'] = "Notes/moduleimpl_status?moduleimpl_id=%(moduleimpl_id)s"%mod
        sco_news.add(REQUEST, cnx, typ=NEWS_NOTE, object=moduleimpl_id,
                     text='Suppression d\'une évaluation dans <a href="%(url)s">%(titre)s</a>' % mod,
                     url=mod['url'])

    security.declareProtected(ScoView, 'do_evaluation_list')
    def do_evaluation_list(self, args ):
        "list evaluations"
        cnx = self.GetDBConnexion()
        evals = self._evaluationEditor.list(cnx, args)
        # calcule duree (chaine de car.) de chaque evaluation
        for e in evals:
            heure_debut, heure_fin = e['heure_debut'], e['heure_fin']
            d = TimeDuration(heure_debut, heure_fin)
            if d is not None:
                m = d%60                
                e['duree'] = '%dh' % (d/60)
                if m != 0:
                    e['duree'] += '%02d' % m
            else:
                e['duree'] = ''
            if heure_debut and (not heure_fin or heure_fin == heure_debut):
                e['descrheure'] = ' à ' + heure_debut
            elif heure_debut and heure_fin:
                e['descrheure'] = ' de %s à %s' % (heure_debut, heure_fin)
            else:
                e['descrheure'] = ''
        return evals

    security.declareProtected(ScoView, 'do_evaluation_list_in_formsemestre')
    def do_evaluation_list_in_formsemestre(self, formsemestre_id ):
        "list evaluations in this formsemestre"
        cnx = self.GetDBConnexion()
        mods = self.do_moduleimpl_list( args={'formsemestre_id' : formsemestre_id} )
        evals = []
        for mod in mods:
            evals += self.do_evaluation_list(
                args={'moduleimpl_id':mod['moduleimpl_id']})
        return evals
                          
    security.declareProtected(ScoEnsView, 'do_evaluation_edit')
    def do_evaluation_edit(self, REQUEST, args ):
        "edit a evaluation"
        evaluation_id = args['evaluation_id']
        the_evals = self.do_evaluation_list( 
                {'evaluation_id' : evaluation_id})
        if not the_evals:
            raise ValueError, "evaluation inexistante !"
        moduleimpl_id = the_evals[0]['moduleimpl_id']
        args['moduleimpl_id'] = moduleimpl_id
        self._check_evaluation_args(args)
        self._evaluation_check_write_access(REQUEST, moduleimpl_id=moduleimpl_id)
        cnx = self.GetDBConnexion()
        self._evaluationEditor.edit(cnx, args )
        # inval cache pour ce semestre
        M = self.do_moduleimpl_list( args={ 'moduleimpl_id':moduleimpl_id } )[0]
        self._inval_cache(formsemestre_id=M['formsemestre_id'])

    security.declareProtected(ScoEnsView, 'evaluation_edit')
    def evaluation_edit(self, evaluation_id, REQUEST ):
        "form edit evaluation"
        return self.evaluation_create_form(evaluation_id=evaluation_id,
                                           REQUEST=REQUEST,
                                           edit=True)
    security.declareProtected(ScoEnsView, 'evaluation_create')
    def evaluation_create(self, moduleimpl_id, REQUEST ):
        "form create evaluation"
        return self.evaluation_create_form(moduleimpl_id=moduleimpl_id,
                                           REQUEST=REQUEST,
                                           edit=False)
    
    security.declareProtected(ScoEnsView, 'evaluation_create_form')
    def evaluation_create_form(self, moduleimpl_id=None,
                               evaluation_id=None,
                               REQUEST=None,
                               edit=False, readonly=False ):
        "formulaire creation/edition des evaluations (pas des notes)"
        if evaluation_id != None:
            the_eval = self.do_evaluation_list( 
                {'evaluation_id' : evaluation_id})[0]    
            moduleimpl_id = the_eval['moduleimpl_id']
        #
        M = self.do_moduleimpl_list( args={ 'moduleimpl_id' : moduleimpl_id } )[0]
        formsemestre_id = M['formsemestre_id']
        if not readonly:
            try:
                self._evaluation_check_write_access( REQUEST,
                                                     moduleimpl_id=moduleimpl_id )
            except AccessDenied, detail:
                return self.sco_header(REQUEST)\
                       + '<h2>Opération non autorisée</h2><p>' + str(detail) + '</p>'\
                       + '<p><a href="%s">Revenir</a></p>' % (str(REQUEST.HTTP_REFERER), ) \
                       + self.sco_footer(REQUEST)
        if readonly:
            edit=True # montre les donnees existantes
        if not edit:
            # creation nouvel
            if moduleimpl_id is None:
                raise ValueError, 'missing moduleimpl_id parameter'
            initvalues = { 'note_max' : 20,
                           'jour' : time.strftime('%d/%m/%Y', time.localtime()) }
            submitlabel = 'Créer cette évaluation'
            action = 'Création d\'une é'
            
        else:
            # edition donnees existantes
            # setup form init values
            if evaluation_id is None:
                raise ValueError, 'missing evaluation_id parameter'
            initvalues = the_eval
            moduleimpl_id = initvalues['moduleimpl_id']
            submitlabel = 'Modifier les données'
            if readonly:
                action = 'E'
            else:
                action = 'Modification d\'une é'
        #    
        Mod = self.do_module_list( args={ 'module_id' : M['module_id'] } )[0]
        sem = self.get_formsemestre(M['formsemestre_id'])        
        #
        help = """<div class="help"><p class="help">
        Le coefficient d'une évaluation n'est utilisé que pour pondérer les évaluations au sein d'un module.
        Il est fixé librement par l'enseignant pour refléter l'importance de ses différentes notes
        (examens, projets, travaux pratiques...). Ce coefficient est utilisé pour calculer la note
        moyenne de chaque étudiant dans ce module.
        </p><p class="help">
        Ne pas confondre ce coefficient avec le coefficient du module, qui est lui fixé par le programme
        pédagogique (par exemple le PPN pour les DUT) et pondère les moyennes de chaque module pour obtenir
        les moyennes d'UE et la moyenne générale.
        </p><p class="help">
        L'option <em>Visible sur bulletins</em> indique que la note sera reportée sur les bulletins
        en version dite "intermédiaire" (dans cette version, on peut ne faire apparaitre que certaines
        notes, en sus des moyennes de modules. Attention, cette option n'empêche pas la publication sur
        les bulletins en version "longue" (la note est donc visible par les étudiants sur le portail).
        </p>
        """
        H = ['<h3>%svaluation en <a href="moduleimpl_status?moduleimpl_id=%s">%s %s</a></h3>'
             % (action, moduleimpl_id, Mod['code'], Mod['titre']),
             '<p>Semestre: <a href="%s/Notes/formsemestre_status?formsemestre_id=%s">%s</a>' % (self.ScoURL(),formsemestre_id, sem['titre_num']),
             'du %(date_debut)s au %(date_fin)s' % sem ]
        if readonly:
            E = initvalues
            # version affichage seule (générée ici pour etre plus jolie que le Formulator)
            jour = E['jour']
            if not jour:
                jour = '???'
            H.append( '<br/>Evaluation réalisée le <b>%s</b> de %s à %s'
                      % (jour,E['heure_debut'],E['heure_fin']) )
            if E['jour']:
                H.append('<span class="noprint"><a href="%s/Absences/EtatAbsencesDate?semestregroupe=%s%%21%%21%%21&date=%s">(absences ce jour)</a></span>' % (self.ScoURL(),formsemestre_id,urllib.quote(E['jour'],safe='')  ))
            H.append( '<br/>Coefficient dans le module: <b>%s</b>' % E['coefficient'] )
            if self.can_edit_notes(REQUEST.AUTHENTICATED_USER, moduleimpl_id, allow_ens=False):
                H.append('<a href="evaluation_edit?evaluation_id=%s">(modifier l\'évaluation)</a>' % evaluation_id)
            H.append('</p>')
            return '<div class="eval_description">' + '\n'.join(H) + '</div>'

        heures = [ '%02dh%02d' % (h,m) for h in range(8,19) for m in (0,30) ]
        #
        initvalues['visibulletin'] = initvalues.get('visibulletin', '1')
        if initvalues['visibulletin'] == '1':            
            initvalues['visibulletinlist'] = ['X']
        else:
            initvalues['visibulletinlist'] = []
        if REQUEST.form.get('tf-submitted',False) and not REQUEST.form.has_key('visibulletinlist'):
            REQUEST.form['visibulletinlist'] = []
        #
        tf = TrivialFormulator( REQUEST.URL0, REQUEST.form, (
            ('evaluation_id', { 'default' : evaluation_id, 'input_type' : 'hidden' }),
            ('formsemestre_id', { 'default' : formsemestre_id, 'input_type' : 'hidden' }),
            ('moduleimpl_id', { 'default' : moduleimpl_id, 'input_type' : 'hidden' }),
            #('jour', { 'title' : 'Date (j/m/a)', 'size' : 12, 'explanation' : 'date de l\'examen, devoir ou contrôle' }),
            ('jour', { 'input_type' : 'date', 'title' : 'Date (j/m/a)', 'size' : 12, 'explanation' : 'date de l\'examen, devoir ou contrôle' }),
            ('heure_debut'   , { 'title' : 'Heure de début', 'explanation' : 'heure du début de l\'épreuve',
                                 'input_type' : 'menu', 'allowed_values' : heures, 'labels' : heures }),
            ('heure_fin'   , { 'title' : 'Heure de fin', 'explanation' : 'heure de fin de l\'épreuve',
                               'input_type' : 'menu', 'allowed_values' : heures, 'labels' : heures }),
            ('coefficient'    , { 'size' : 10, 'type' : 'float', 'explanation' : 'coef. dans le module (choisi librement par l\'enseignant)', 'allow_null':False }),
            ('note_max'    , { 'size' : 3, 'type' : 'float', 'title' : 'Notes de 0 à', 'explanation' : 'barème', 'allow_null':False, 'max_value' : NOTES_MAX }),

            ('description' , { 'size' : 36, 'type' : 'text'  }),    
            ('visibulletinlist', { 'input_type' : 'checkbox',
                                   'allowed_values' : ['X'], 'labels' : [ '' ],
                                   'title' : 'Visible sur bulletins' ,
                                   'explanation' : '(pour les bulletins en version intermédiaire)'}),
            ),
                                cancelbutton = 'Annuler',
                                submitlabel = submitlabel,
                                initvalues = initvalues, readonly=readonly)

        dest_url = 'moduleimpl_status?moduleimpl_id=%s' % M['moduleimpl_id']
        if  tf[0] == 0:
            return self.sco_header(REQUEST, javascripts=['calendarDateInput_js']) + '\n'.join(H) + '\n' + tf[1] + help + self.sco_footer(REQUEST)
        elif tf[0] == -1:
            return REQUEST.RESPONSE.redirect( dest_url )
        else:
            # form submission
            if tf[2]['visibulletinlist']:
                tf[2]['visibulletin'] = 1
            else:
                tf[2]['visibulletin'] = 0
            if not edit:
                # creation d'une evaluation
                evaluation_id = self.do_evaluation_create( REQUEST, tf[2] )
                return REQUEST.RESPONSE.redirect( dest_url )
            else:
                self.do_evaluation_edit( REQUEST, tf[2] )
                return REQUEST.RESPONSE.redirect( dest_url )

    security.declareProtected(ScoView, 'do_evaluation_listegroupes')
    def do_evaluation_listegroupes(self, evaluation_id ):
        """donne la liste des groupes (td,tp,anglais) dans lesquels figurent
        des etudiants inscrits au module/semestre dans auquel appartient
        cette evaluation
        """    
        req = 'select distinct %s from notes_formsemestre_inscription Isem, notes_moduleimpl_inscription Im, notes_moduleimpl M, notes_evaluation E where Isem.etudid=Im.etudid and Im.moduleimpl_id=M.moduleimpl_id and E.moduleimpl_id=M.moduleimpl_id and M.formsemestre_id =  Isem.formsemestre_id and E.evaluation_id = %%(evaluation_id)s'
        cnx = self.GetDBConnexion()
        cursor = cnx.cursor()    
        cursor.execute( req % 'groupetd', { 'evaluation_id' : evaluation_id } )
        res = cursor.fetchall()
        gr_td = [ x[0] for x in res if x[0] ]
        cursor.execute( req % 'groupetp', { 'evaluation_id' : evaluation_id } )
        res = cursor.fetchall()
        gr_tp = [ x[0] for x in res if x[0] ]
        cursor.execute( req % 'groupeanglais', { 'evaluation_id' : evaluation_id } )
        res = cursor.fetchall()
        gr_anglais = [ x[0] for x in res if x[0] ]
        return gr_td, gr_tp, gr_anglais

    security.declareProtected(ScoView, 'do_evaluation_listeetuds_groups')
    def do_evaluation_listeetuds_groups(self, evaluation_id,
                                        gr_td=[],gr_tp=[],gr_anglais=[],
                                        getallstudents=False,
                                        include_dems=False):
        """Donne la liste des etudids inscrits a cette evaluation dans les
        groupes indiqués.
        Si getallstudents==True, donne tous les etudiants inscrits a cette
        evaluation.
        Si include_dems, compte aussi les etudiants démissionnaires
        (sinon, par défaut, seulement les 'I')
        """
        # construit condition sur les groupes
        if not getallstudents:
            rg =  [ "Isem.groupetd = '%s'" % simplesqlquote(x) for x in gr_td ]
            rg += [ "Isem.groupetp = '%s'" % simplesqlquote(x) for x in gr_tp ]
            rg += [ "Isem.groupeanglais = '%s'" % simplesqlquote(x) for x in gr_anglais ]
            if not rg:
                return [] # no groups, so no students
            r = ' and (' + ' or '.join(rg) + ' )'
        else:
            r = ''        
        # requete complete
        req = "select distinct Im.etudid from notes_moduleimpl_inscription Im, notes_formsemestre_inscription Isem, notes_moduleimpl M, notes_evaluation E where Isem.etudid=Im.etudid and Im.moduleimpl_id=M.moduleimpl_id and Isem.formsemestre_id=M.formsemestre_id and E.moduleimpl_id=M.moduleimpl_id and E.evaluation_id = %(evaluation_id)s"
        if not include_dems:
            req += " and Isem.etat='I'"
        req += r
        cnx = self.GetDBConnexion()
        cursor = cnx.cursor()
        cursor.execute( req, { 'evaluation_id' : evaluation_id } )
        res = cursor.fetchall()
        return [ x[0] for x in res ]

    def _displayNote(self, val):
        "convert note from DB to viewable string"
        # Utilisé seulement pour I/O vers formulaires (sans perte de precision)
        # Utiliser fmt_note pour les affichages
        if val is None:
            val = 'ABS'
        elif val == NOTES_NEUTRALISE:
            val = 'EXC' # excuse, note neutralise
        elif val == NOTES_ATTENTE:
            val = 'ATT' # attente, note neutralise
        else:
            val = '%g' % val
        return val

    security.declareProtected(ScoView, 'do_evaluation_etat')
    def do_evaluation_etat(self, evaluation_id, group_type='groupetd'):
        """donne infos sur l'etat du evaluation
        { nb_inscrits, nb_notes, nb_abs, nb_neutre, nb_att, moyenne, mediane,
        date_last_modif, gr_complets, gr_incomplets, evalcomplete }
        evalcomplete est vrai si l'eval est complete (tous les inscrits
        à ce module ont des notes)
        evalattente est vrai s'il ne manque que des notes en attente
        """
        nb_inscrits = len(self.do_evaluation_listeetuds_groups(evaluation_id,getallstudents=True))
        NotesDB = self._notes_getall(evaluation_id) # { etudid : value }
        notes = [ x['value'] for x in NotesDB.values() ]
        nb_notes = len(notes)
        nb_abs = len( [ x for x in notes if x is None ] )
        nb_neutre = len( [ x for x in notes if x == NOTES_NEUTRALISE ] )
        nb_att = len( [ x for x in notes if x == NOTES_ATTENTE ] )
        moy, median = notes_moyenne_median(notes)
        if moy is None:
            median, moy = '',''
        else:
            median = fmt_note(median) # '%.3g' % median
            moy = fmt_note(moy) # '%.3g' % moy
        # cherche date derniere modif note
        if len(NotesDB):
            t = [ x['date'] for x in NotesDB.values() ]
            last_modif = max(t)
        else:
            last_modif = None
        # ---- Liste des groupes complets et incomplets
        E = self.do_evaluation_list( args={ 'evaluation_id' : evaluation_id } )[0]
        M = self.do_moduleimpl_list( args={ 'moduleimpl_id' : E['moduleimpl_id']})[0]
        formsemestre_id = M['formsemestre_id']
        # il faut considerer les inscription au semestre
        # (pour avoir l'etat et le groupe) et aussi les inscriptions
        # au module (pour gerer les modules optionnels correctement)
        insem = self.do_formsemestre_inscription_listinscrits(formsemestre_id)
        insmod = self.do_moduleimpl_inscription_list(
            args={ 'moduleimpl_id' : E['moduleimpl_id'] } )
        insmoddict = {}.fromkeys( [ x['etudid'] for x in insmod ] )
        # retire de insem ceux qui ne sont pas inscrits au module
        ins = [ i for i in insem if insmoddict.has_key(i['etudid']) ]
        
        # On considere une note "manquante" lorsqu'elle n'existe pas
        # ou qu'elle est en attente (ATT)
        GrNbMissing = DictDefault() # groupe : nb notes manquantes
        GrNotes = DictDefault(defaultvalue=[]) # groupetd: liste notes valides
        TotalNbMissing = 0
        TotalNbAtt = 0
        for i in ins:
            group = i[group_type]
            isMissing = False
            if NotesDB.has_key(i['etudid']):
                val = NotesDB[i['etudid']]['value']
                if val == NOTES_ATTENTE:
                    isMissing = True
                    TotalNbAtt += 1
                GrNotes[group].append( val )
            else:
                junk = GrNotes[group] # create group
                isMissing = True
            if isMissing:
                TotalNbMissing += 1
                GrNbMissing[group] += 1
        
        gr_incomplets = [ x for x in GrNbMissing.keys() ]
        gr_incomplets.sort()
        if TotalNbMissing > 0:
            complete = False
        else:
            complete = True            
        if TotalNbMissing > 0 and TotalNbMissing == TotalNbAtt:
            evalattente = True
        else:
            evalattente = False
        # calcul moyenne dans chaque groupe de TD
        gr_moyennes = [] # group : {moy,median, nb_notes}
        for gr in GrNotes.keys():
            notes = GrNotes[gr]
            gr_moy, gr_median = notes_moyenne_median(notes)
            gr_moyennes.append(
                {'gr':gr, 'gr_moy' : fmt_note(gr_moy),
                 'gr_median':fmt_note(gr_median),
                 'gr_nb_notes': len(notes),
                 'gr_nb_att' : len([ x for x in notes if x == NOTES_ATTENTE ])
                 } )
        # retourne mapping
        return [ {
            'evaluation_id' : evaluation_id,
            'nb_inscrits':nb_inscrits, 'nb_notes':nb_notes,
            'nb_abs':nb_abs, 'nb_neutre':nb_neutre, 'nb_att' : nb_att,
            'moy':moy, 'median':median,
            'last_modif':last_modif,
            'gr_incomplets':gr_incomplets,
            'gr_moyennes' : gr_moyennes,
            'evalcomplete' : complete,
            'evalattente' : evalattente } ]
    
    security.declareProtected(ScoView, 'do_evaluation_list_in_sem')
    def do_evaluation_list_in_sem(self, formsemestre_id):
        """Liste des evaluations pour un semestre (dans tous le smodules de ce
        semestre).
        Donne pour chaque eval son état:
        (evaluation_id,nb_inscrits, nb_notes, nb_abs, nb_neutre, moy, median, last_modif)
        """
        req = "select evaluation_id from notes_evaluation E, notes_moduleimpl MI where MI.formsemestre_id = %(formsemestre_id)s and MI.moduleimpl_id = E.moduleimpl_id"
        cnx = self.GetDBConnexion()
        cursor = cnx.cursor()    
        cursor.execute( req, { 'formsemestre_id' : formsemestre_id } )
        res = cursor.fetchall()
        evaluation_ids = [ x[0] for x in res ]
        #
        R = []
        for evaluation_id in evaluation_ids:
            R.append( self.do_evaluation_etat(evaluation_id)[0] )
        return R 

    def _eval_etat(self,evals):
        """evals: list of mappings (etats)
        -> nb_eval_completes, nb_evals_en_cours,
        nb_evals_vides, date derniere modif

        Une eval est "complete" ssi tous les etudiants *inscrits* ont une note.
        
        """
        
        nb_evals_completes, nb_evals_en_cours, nb_evals_vides = 0,0,0
        dates = []
        for e in evals:
            if e['evalcomplete']:
                nb_evals_completes += 1
            elif e['nb_notes'] == 0: # nb_notes == 0
                nb_evals_vides += 1
            else:
                nb_evals_en_cours += 1
            dates.append(e['last_modif'])
        dates.sort()
        if len(dates):
            last_modif = dates[-1] # date de derniere modif d'une note dans un module
        else:
            last_modif = ''
        
        return [ { 'nb_evals_completes':nb_evals_completes,
                   'nb_evals_en_cours':nb_evals_en_cours,
                   'nb_evals_vides':nb_evals_vides,
                   'last_modif':last_modif } ]

    security.declareProtected(ScoView, 'do_evaluation_etat_in_sem')
    def do_evaluation_etat_in_sem(self, formsemestre_id):
        """-> nb_eval_completes, nb_evals_en_cours, nb_evals_vides,
        date derniere modif, attente"""
        evals = self.do_evaluation_list_in_sem(formsemestre_id)
        etat = self._eval_etat(evals)
        # Ajoute information sur notes en attente
        nt = self._getNotesCache().get_NotesTable(self, formsemestre_id)
        etat[0]['attente'] = len(nt.get_moduleimpls_attente()) > 0
        return etat
    

    security.declareProtected(ScoView, 'do_evaluation_etat_in_mod')
    def do_evaluation_etat_in_mod(self, moduleimpl_id):
        evals = self.do_evaluation_list( { 'moduleimpl_id' : moduleimpl_id } )
        evaluation_ids = [ x['evaluation_id'] for x in evals ]
        R = []
        for evaluation_id in evaluation_ids:
            R.append( self.do_evaluation_etat(evaluation_id)[0] )
        etat = self._eval_etat(R)
        # Ajoute information sur notes en attente
        M = self.do_moduleimpl_list( args={ 'moduleimpl_id' : moduleimpl_id})[0]
        formsemestre_id = M['formsemestre_id']
        nt = self._getNotesCache().get_NotesTable(self, formsemestre_id)
        
        etat[0]['attente'] = moduleimpl_id in [
            m['moduleimpl_id'] for m in nt.get_moduleimpls_attente() ]
        return etat


    security.declareProtected(ScoView, 'evaluation_listenotes')
    def evaluation_listenotes(self, REQUEST ):
        """Affichage des notes d'une évaluation"""
        if REQUEST.form.get('liste_format','html')=='html':
            H = self.sco_header(REQUEST, cssstyles=['verticalhisto_css']) 
            F = self.sco_footer(REQUEST)
        else:
            H, F = '', ''
        B = self.do_evaluation_listenotes(REQUEST)
        return H + B + F

    security.declareProtected(ScoView, 'do_evaluation_listenotes')
    do_evaluation_listenotes = sco_liste_notes.do_evaluation_listenotes

    security.declareProtected(ScoView, 'evaluation_check_absences_html')
    evaluation_check_absences_html = sco_liste_notes.evaluation_check_absences_html

    security.declareProtected(ScoView, 'formsemestre_check_absences_html')
    formsemestre_check_absences_html = sco_liste_notes.formsemestre_check_absences_html

    # --- Saisie des notes
    security.declareProtected(ScoEnsView, 'do_evaluation_selectetuds')
    do_evaluation_selectetuds = sco_saisie_notes.do_evaluation_selectetuds
    
    security.declareProtected(ScoEnsView, 'do_evaluation_formnotes')
    do_evaluation_formnotes = sco_saisie_notes.do_evaluation_formnotes

    # now unused:
    #security.declareProtected(ScoEnsView, 'do_evaluation_upload_csv')
    #do_evaluation_upload_csv = sco_saisie_notes.do_evaluation_upload_csv


    security.declareProtected(ScoEnsView, 'do_evaluation_upload_xls')
    do_evaluation_upload_xls = sco_saisie_notes.do_evaluation_upload_xls

    security.declareProtected(ScoEnsView, 'do_evaluation_set_missing')
    do_evaluation_set_missing = sco_saisie_notes.do_evaluation_set_missing

    security.declareProtected(ScoView, 'evaluation_suppress_alln')
    evaluation_suppress_alln = sco_saisie_notes.evaluation_suppress_alln

    # not accessible through the web
    _notes_add = sco_saisie_notes._notes_add
            
    security.declareProtected(ScoView, 'can_edit_notes')
    def can_edit_notes(self, authuser, moduleimpl_id, allow_ens=True ):
        """True if authuser can enter or edit notes in this module.
        If allow_ens, grant access to all ens in this module
        """
        uid = str(authuser)
        M = self.do_moduleimpl_list(args={ 'moduleimpl_id' : moduleimpl_id})[0]
        sem = self.get_formsemestre(M['formsemestre_id'])
        if sem['etat'] != '1':
            return False # semestre verrouillé
        if ((not authuser.has_permission(ScoEditAllNotes,self))
            and uid != M['responsable_id']
            and uid != sem['responsable_id']):
            # enseignant (chargé de TD) ?
            if allow_ens:
                for ens in M['ens']:
                    if ens['ens_id'] == uid:
                        return True
            return False
        else:
            return True        

    security.declareProtected(ScoEditAllNotes, 'dummy_ScoEditAllNotes')
    def dummy_ScoEditAllNotes(self):
        "dummy method, necessary to declare permission ScoEditAllNotes"
        return True

    security.declareProtected(ScoEditAllEvals, 'dummy_ScoEditAllEvals')
    def dummy_ScoEditAllEvals(self):
        "dummy method, necessary to declare permission ScoEditAllEvals"
        return True

    security.declareProtected(ScoSuperAdmin, 'dummy_ScoSuperAdmin')
    def dummy_ScoSuperAdmin(self):
        "dummy method, necessary to declare permission ScoSuperAdmin"
        return True

    security.declareProtected(ScoEtudChangeGroups, 'dummy_ScoEtudChangeGroups')
    def dummy_ScoEtudChangeGroups(self):
        "dummy method, necessary to declare permission ScoEtudChangeGroups"
        return True

    def _notes_getall(self, evaluation_id):
        """get tt les notes pour une evaluation: { etudid : { 'value' : value, 'date' : date ... }}
        """
        cnx = self.GetDBConnexion()
        cursor = cnx.cursor()
        cursor.execute("select * from notes_notes where evaluation_id=%(evaluation_id)s",
                       { 'evaluation_id' : evaluation_id } )
        res = cursor.dictfetchall()
        d = {}
        for x in res:
            d[x['etudid']] = x
        return d

    # --- Bulletins
    security.declareProtected(ScoView, 'do_moduleimpl_moyennes')
    def do_moduleimpl_moyennes(self,moduleimpl_id):
        """Retourne dict { etudid : note_moyenne } pour tous les etuds inscrits
        à ce module, la liste des evaluations "valides" (toutes notes entrées
        ou en attente), et att (vrai s'il y a des notes en attente dans ce module).
        La moyenne est calculée en utilisant les coefs des évaluations.
        Les notes NEUTRES (abs. excuses) ne sont pas prises en compte.
        Les notes ABS sont remplacées par des zéros.
        S'il manque des notes et que le coef n'est pas nul,
        la moyenne n'est pas calculée: NA
        Ne prend en compte que les evaluations où toutes les notes sont entrées
        Le résultat est une note sur 20
        """
        M = self.do_moduleimpl_list(args={ 'moduleimpl_id' : moduleimpl_id })[0]
        etudids = self.do_moduleimpl_listeetuds(moduleimpl_id) # tous, y compris demissions
        # Inscrits au semestre (pour traiter les demissions):
        inssem_set = Set( [x['etudid'] for x in
                           self.do_formsemestre_inscription_listinscrits(M['formsemestre_id'])])
        evals = self.do_evaluation_list(args={ 'moduleimpl_id' : moduleimpl_id })
        attente = False
        # recupere les notes de toutes les evaluations
        for e in evals:
            e['nb_inscrits'] = len(
                self.do_evaluation_listeetuds_groups(e['evaluation_id'],
                                                     getallstudents=True))
            NotesDB = self._notes_getall(e['evaluation_id']) # toutes, y compris demissions
            # restreint aux étudiants encore inscrits à ce module            
            notes = [ NotesDB[etudid]['value'] for etudid in NotesDB if etudid in inssem_set ]
            e['nb_notes'] = len(notes)
            e['nb_abs'] = len( [ x for x in notes if x is None ] )
            e['nb_neutre'] = len( [ x for x in notes if x == NOTES_NEUTRALISE ] )
            e['nb_att'] = len( [ x for x in notes if x == NOTES_ATTENTE ] )
            e['notes'] = NotesDB
            e['etat'] = self.do_evaluation_etat(e['evaluation_id'])[0]
            if e['nb_att']:
                attente = True
        # filtre les evals valides (toutes les notes entrées)        
        valid_evals = [ e for e in evals
                        if (e['etat']['evalcomplete'] or e['etat']['evalattente']) ]
        # 
        R = {}
        for etudid in etudids:
            nb_notes = 0
            sum_notes = 0.
            sum_coefs = 0.
            nb_missing = 0
            for e in valid_evals:
                if e['notes'].has_key(etudid):
                    note = e['notes'][etudid]['value']
                    if note == None: # ABSENT
                        note = 0            
                    if note != NOTES_NEUTRALISE and note != NOTES_ATTENTE:
                        nb_notes += 1
                        sum_notes += (note * 20. / e['note_max']) * e['coefficient']
                        sum_coefs += e['coefficient']
                else:
                    # il manque une note !
                    if e['coefficient'] > 0:
                        nb_missing += 1
            if nb_missing == 0 and sum_coefs > 0:
                if sum_coefs > 0:
                    R[etudid] = sum_notes / sum_coefs
                else:
                    R[etudid] = 'na'
            else:
                R[etudid] = 'NA%d' % nb_missing
        return R, valid_evals, attente

    security.declareProtected(ScoView, 'do_formsemestre_moyennes')
    def do_formsemestre_moyennes(self, formsemestre_id):
        """retourne dict { moduleimpl_id : { etudid, note_moyenne_dans_ce_module } },
        la liste des moduleimpls, la liste des evaluations valides,
        liste des moduleimpls  avec notes en attente.
        """
        sem = self.get_formsemestre(formsemestre_id)
        inscr = self.do_formsemestre_inscription_list(
            args = { 'formsemestre_id' : formsemestre_id })
        etudids = [ x['etudid'] for x in inscr ]
        mods = self.do_moduleimpl_list( args={ 'formsemestre_id' : formsemestre_id})
        # recupere les moyennes des etudiants de tous les modules
        D = {}
        valid_evals = []
        mods_att = []
        for mod in mods:
            assert not D.has_key(mod['moduleimpl_id'])
            D[mod['moduleimpl_id']], valid_evals_mod, attente =\
                                     self.do_moduleimpl_moyennes(mod['moduleimpl_id'])
            valid_evals += valid_evals_mod
            if attente:
                mods_att.append(mod)
        #
        return D, mods, valid_evals, mods_att

    security.declareProtected(ScoView, 'do_formsemestre_recapcomplet')
    def do_formsemestre_recapcomplet(
        self,REQUEST,formsemestre_id,format='html',
        xml_nodate=False, modejury=False, hidemodules=False, sortcol=None,
        xml_with_decisions=False):
        """Grand tableau récapitulatif avec toutes les notes de modules
        pour tous les étudiants, les moyennes par UE et générale,
        trié par moyenne générale décroissante.
        """
        return sco_recapcomplet.do_formsemestre_recapcomplet(
            self, REQUEST, formsemestre_id, format=format, xml_nodate=xml_nodate,
            modejury=modejury, hidemodules=hidemodules, sortcol=sortcol,
            xml_with_decisions=xml_with_decisions)
    
    security.declareProtected(ScoView, 'do_formsemestre_bulletinetud')
    def do_formsemestre_bulletinetud(self, formsemestre_id, etudid,
                                     version='long', # short, long, selectedevals
                                     format='html',
                                     REQUEST=None,
                                     nohtml=False,
                                     xml_with_decisions=False # force decisions dans XML
                                     ):
        if format != 'mailpdf':
            if format == 'xml':
                bul = repr(sco_bulletins.make_xml_formsemestre_bulletinetud(
                    self, formsemestre_id,  etudid, REQUEST=REQUEST,
                    xml_with_decisions=xml_with_decisions))
            else:
                bul, etud, filename = sco_bulletins.make_formsemestre_bulletinetud(
                    self, formsemestre_id, etudid,
                    version=version,format=format,
                    REQUEST=REQUEST)
            if format == 'pdf':
                return sendPDFFile(REQUEST, bul, filename)        
            else:
                return bul
        else:
            # format mailpdf: envoie le pdf par mail a l'etud, et affiche le html
            if nohtml:
                htm = '' # speed up if html version not needed
            else:
                htm, junk, junk = sco_bulletins.make_formsemestre_bulletinetud(self,
                    formsemestre_id, etudid, version=version,format='html',
                    REQUEST=REQUEST)
            pdf, etud, filename = sco_bulletins.make_formsemestre_bulletinetud(self,
                formsemestre_id, etudid, version=version,format='pdf',
                REQUEST=REQUEST)
            if not etud['email']:
                return ('<div class="boldredmsg">%s n\'a pas d\'adresse e-mail !</div>'
                        % etud['nomprenom']) + htm
            #
            webmaster = getattr(self,'webmaster_email',"l'administrateur.")
            dept = unescape_html(self.get_preference('DeptName'))
            #pdb.set_trace()
            fmt = formsemestre_pagebulletin_get(self, formsemestre_id)
            log(fmt)
            hea = fmt['intro_mail'] % { 'nomprenom' : etud['nomprenom'], 'dept':dept, 'webmaster':webmaster }
            
            msg = MIMEMultipart()
            subj = Header( 'Relevé de note de %s' % etud['nomprenom'],  SCO_ENCODING )
            recipients = [ etud['email'] ] 
            msg['Subject'] = subj
            msg['From'] = getattr(self,'mail_bulletin_from_addr', 'noreply' )
            msg['To'] = ' ,'.join(recipients)
            msg['Bcc'] = 'viennet@iutv.univ-paris13.fr' # XXX
            # Guarantees the message ends in a newline
            msg.epilogue = ''
            # Text
            txt = MIMEText( hea, 'plain', SCO_ENCODING )
            msg.attach(txt)
            # Attach pdf
            att = MIMEBase('application', 'pdf')
            att.add_header('Content-Disposition', 'attachment', filename=filename)
            att.set_payload( pdf )
            Encoders.encode_base64(att)
            msg.attach(att)
            log('mail bulletin a %s' % msg['To'] )
            self.sendEmail(msg)
            return ('<div class="boldredmsg">Message mail envoyé à %s</div>'
                    % (etud['emaillink'])) + htm


    security.declareProtected(ScoView, 'formsemestre_bulletins_pdf')
    def formsemestre_bulletins_pdf(self, formsemestre_id, REQUEST,
                                   version='selectedevals'):
        "Publie les bulletins dans un classeur PDF"
        cached = self._getNotesCache().get_bulletins_pdf(formsemestre_id,version)
        if cached:
            return sendPDFFile(REQUEST,cached[1],cached[0])
        fragments = []
        sem = self.get_formsemestre(formsemestre_id)
        # Make each bulletin
        nt = self._getNotesCache().get_NotesTable(self, formsemestre_id)
        bookmarks = {}
        i = 1
        for etudid in nt.get_etudids():
            fragments += self.do_formsemestre_bulletinetud(
                formsemestre_id, etudid, format='pdfpart',
                version=version, 
                REQUEST=REQUEST )
            bookmarks[i] = nt.get_sexnom(etudid)
            i = i + 1
        #
        infos = { 'DeptName' : self.get_preference('DeptName') }
        if REQUEST:
            server_name = REQUEST.BASE0
        else:
            server_name = ''
        try:
            PDFLOCK.acquire()
            pdfdoc = pdfbulletins.pdfassemblebulletins(
                formsemestre_id,
                fragments, sem, infos, bookmarks,
                server_name=server_name,
                context=self )
        finally:
            PDFLOCK.release()
        #
        dt = time.strftime( '%Y-%m-%d' )
        filename = 'bul-%s-%s.pdf' % (sem['titre_num'], dt)
        filename = unescape_html(filename).replace(' ','_').replace('&','')
        # fill cache
        self._getNotesCache().store_bulletins_pdf(formsemestre_id,version,
                                                  (filename,pdfdoc))
        return sendPDFFile(REQUEST, pdfdoc, filename)

    security.declareProtected(ScoView, 'formsemestre_bulletins_mailetuds')
    def formsemestre_bulletins_mailetuds(self, formsemestre_id, REQUEST,
                                         version='long',
                                         dialog_confirmed=False ):
        "envoi a chaque etudiant (inscrit et ayant un mail) son bulletin"
        sem = self.get_formsemestre(formsemestre_id)
        nt = self._getNotesCache().get_NotesTable(self, formsemestre_id)
        etudids = nt.get_etudids()
        # Confirmation dialog
        if not dialog_confirmed:
            return self.confirmDialog(
                "<h2>Envoyer les %d bulletins par e-mail aux étudiants ?" % len(etudids),
                dest_url="", REQUEST=REQUEST,
                cancel_url="formsemestre_status?formsemestre_id=%s" % formsemestre_id,
                parameters={'version':version, 'formsemestre_id' : formsemestre_id})
                                      
        # Make each bulletin
        for etudid in etudids:
            self.do_formsemestre_bulletinetud(
                formsemestre_id, etudid,
                version=version, 
                format = 'mailpdf', nohtml=True, REQUEST=REQUEST )
        #
        return self.sco_header(REQUEST) + '<p>%d bulletins envoyés par mail !</p><p><a class="stdlink" href="formsemestre_status?formsemestre_id=%s">continuer</a></p>' % (len(nt.get_etudids()),formsemestre_id) + self.sco_footer(REQUEST)

    security.declareProtected(ScoEnsView, 'appreciation_add_form')
    def appreciation_add_form(self, etudid=None, formsemestre_id=None,
                              id=None, # si id, edit
                              suppress=False, # si true, supress id
                              REQUEST=None ):
        "form ajout ou edition d'une appreciation"
        cnx = self.GetDBConnexion()
        authuser = REQUEST.AUTHENTICATED_USER
        if id: # edit mode
            apps = scolars.appreciations_list( cnx, args={'id':id} )
            if not apps:
                raise ScoValueError("id d'appreciation invalide !") 
            app = apps[0]
            formsemestre_id = app['formsemestre_id']
            etudid = app['etudid']
        if REQUEST.form.has_key('edit'):
            edit = int(REQUEST.form['edit'])
        elif id:
            edit = 1
        else:
            edit = 0
        sem = self.get_formsemestre(formsemestre_id)
        # check custom access permission
        can_edit_app = ((str(authuser) == sem['responsable_id'])
                        or (authuser.has_permission(ScoEtudInscrit,self)))
        if not can_edit_app:
            raise AccessDenied("vous n'avez pas le droit d'ajouter une appreciation")
        #
        bull_url = 'formsemestre_bulletinetud?formsemestre_id=%s&etudid=%s' % (formsemestre_id,etudid)
        if suppress:
            scolars.appreciations_delete( cnx, id )
            logdb(REQUEST, cnx, method='appreciation_suppress',
                  etudid=etudid, msg='')
            return REQUEST.RESPONSE.redirect( bull_url )
        #
        etud = self.getEtudInfo(etudid=etudid,filled=1)[0]
        if id:
            a='Edition'
        else:
            a='Ajout'
        H = [self.sco_header(REQUEST) + '<h2>%s d\'une appréciation sur %s</h2>' % (a,etud['nomprenom']) ]
        F = self.sco_footer(REQUEST)
        descr = [
            ('edit', {'input_type' : 'hidden', 'default' : edit }),
            ('etudid', {'input_type' : 'hidden' }),
            ('formsemestre_id', {'input_type' : 'hidden' }),
            ('id', {'input_type' : 'hidden'}),
            ('comment', {'title' :'','input_type' : 'textarea', 'rows' : 4, 'cols' : 60})
            ]
        if id:
            initvalues = { 'etudid' : etudid,
                           'formsemestre_id':formsemestre_id,
                           'comment' : app['comment'] }
        else:
            initvalues = {}
        tf = TrivialFormulator( REQUEST.URL0, REQUEST.form, descr,
                                initvalues=initvalues,
                                cancelbutton = 'Annuler',
                                submitlabel = 'Ajouter appréciation' )
        if  tf[0] == 0:
            return '\n'.join(H) + '\n' + tf[1] + F
        elif tf[0] == -1:
            return REQUEST.RESPONSE.redirect( bull_url )
        else:
            args={ 'etudid' : etudid,
                   'formsemestre_id':formsemestre_id,
                   'author' : str(authuser),
                   'comment' : tf[2]['comment'],
                   'zope_authenticated_user' : str(authuser),
                   'zope_remote_addr' : REQUEST.REMOTE_ADDR}
            if edit:
                args['id'] = id
                scolars.appreciations_edit( cnx, args )
            else: # nouvelle
                scolars.appreciations_create( cnx, args, has_uniq_values=False)
            # log
            logdb(REQUEST, cnx, method='appreciation_add',
                  etudid=etudid, msg=tf[2]['comment'])
            # ennuyeux mais necessaire (pour le PDF seulement)
            self._inval_cache(pdfonly=True)
            return REQUEST.RESPONSE.redirect( bull_url )

    security.declareProtected(ScoView,'can_change_groups')
    def can_change_groups(self, REQUEST, formsemestre_id):
        "Vrai si utilisateur peut changer les groupes dans ce semestre"
        sem = self.get_formsemestre(formsemestre_id)
        if sem['etat'] != '1':
            return False # semestre verrouillé
        authuser = REQUEST.AUTHENTICATED_USER
        if authuser.has_permission(ScoEtudChangeGroups, self):
            return True # admin, chef dept
        uid = str(authuser)
        if uid == sem['responsable_id']:
            return True
        return False
    
    # --- FORMULAIRE POUR VALIDATION DES UE ET SEMESTRES
    security.declareProtected(ScoView,'can_validate_sem')
    def can_validate_sem(self, REQUEST, formsemestre_id):
        "Vrai si utilisateur peut saisir decision de jury dans ce semestre"
        sem = self.get_formsemestre(formsemestre_id)
        if sem['etat'] != '1':
            return False # semestre verrouillé

        authuser = REQUEST.AUTHENTICATED_USER
        if authuser.has_permission(ScoEtudInscrit, self):
            return True # admin, chef dept

        uid = str(authuser)
        if uid == sem['responsable_id']:
            return True
        return False
    
    security.declareProtected(ScoView, 'formsemestre_validation_etud_form')
    def formsemestre_validation_etud_form(self, formsemestre_id, etudid=None, etud_index=None,
                                          check=0,
                                          desturl='', sortcol=None, REQUEST=None):
        "Formulaire choix jury pour un étudiant"
        readonly = not self.can_validate_sem(REQUEST, formsemestre_id)
        return sco_formsemestre_validation.formsemestre_validation_etud_form(
            self, formsemestre_id, etudid=etudid, etud_index=etud_index,
            check=check, readonly=readonly,
            desturl=desturl, sortcol=sortcol, 
            REQUEST=REQUEST )
    
    security.declareProtected(ScoView, 'formsemestre_validation_etud')
    def formsemestre_validation_etud(self, formsemestre_id, etudid=None,
                                     codechoice=None,
                                     desturl='', sortcol=None, REQUEST=None):
        "Enregistre choix jury pour un étudiant"
        if not self.can_validate_sem(REQUEST, formsemestre_id):
            return self.confirmDialog(
                message='<p>Opération non autorisée pour %s</h2>' % REQUEST.AUTHENTICATED_USER,
                dest_url=self.ScoURL(), REQUEST=REQUEST)
        
        return sco_formsemestre_validation.formsemestre_validation_etud(
            self, formsemestre_id, etudid=etudid, codechoice=codechoice,
            desturl=desturl, sortcol=sortcol, REQUEST=REQUEST )

    security.declareProtected(ScoView, 'formsemestre_validation_etud_manu')
    def formsemestre_validation_etud_manu(self, formsemestre_id, etudid=None,
                                          code_etat='', new_code_prev='', devenir='',
                                          assidu=False,
                                          desturl='', sortcol=None, REQUEST=None):
        "Enregistre choix jury pour un étudiant"
        if not self.can_validate_sem(REQUEST, formsemestre_id):
            return self.confirmDialog(
                message='<p>Opération non autorisée pour %s</h2>' % REQUEST.AUTHENTICATED_USER,
                dest_url=self.ScoURL(), REQUEST=REQUEST)
        
        return sco_formsemestre_validation.formsemestre_validation_etud_manu(
            self, formsemestre_id, etudid=etudid,
            code_etat=code_etat, new_code_prev=new_code_prev, devenir=devenir,
            assidu=assidu, desturl=desturl, sortcol=sortcol, REQUEST=REQUEST )

    security.declareProtected(ScoView, 'formsemestre_validation_auto')
    def formsemestre_validation_auto(self, formsemestre_id, REQUEST):
        "Formulaire saisie automatisee des decisions d'un semestre"
        if not self.can_validate_sem(REQUEST, formsemestre_id):
            return self.confirmDialog(
                message='<p>Opération non autorisée pour %s</h2>' % REQUEST.AUTHENTICATED_USER,
                dest_url=self.ScoURL(), REQUEST=REQUEST)
        
        return sco_formsemestre_validation.formsemestre_validation_auto(self, formsemestre_id, REQUEST)
    
    security.declareProtected(ScoView, 'formsemestre_validation_auto')
    def do_formsemestre_validation_auto(self, formsemestre_id, REQUEST):
        "Formulaire saisie automatisee des decisions d'un semestre"
        if not self.can_validate_sem(REQUEST, formsemestre_id):
            return self.confirmDialog(
                message='<p>Opération non autorisée pour %s</h2>' % REQUEST.AUTHENTICATED_USER,
                dest_url=self.ScoURL(), REQUEST=REQUEST)
        
        return sco_formsemestre_validation.do_formsemestre_validation_auto(self, formsemestre_id, REQUEST)
    
    security.declareProtected(ScoView, 'formsemestre_fix_validation_ues')
    def formsemestre_fix_validation_ues(self, formsemestre_id, REQUEST=None):
        "Verif/reparation codes UE"
        if not self.can_validate_sem(REQUEST, formsemestre_id):
            return self.confirmDialog(
                message='<p>Opération non autorisée pour %s</h2>' % REQUEST.AUTHENTICATED_USER,
                dest_url=self.ScoURL(), REQUEST=REQUEST)
        
        return sco_formsemestre_validation.formsemestre_fix_validation_ues(self,formsemestre_id, REQUEST)
    
    security.declareProtected(ScoView, 'formsemestre_pvjury')
    formsemestre_pvjury = sco_pvjury.formsemestre_pvjury
    
    security.declareProtected(ScoView, 'formsemestre_lettres_individuelles')
    def formsemestre_lettres_individuelles(self, formsemestre_id, REQUEST=None):
        "Lettres avis jury en PDF"
        sem = self.get_formsemestre(formsemestre_id)
        H = [self.sco_header(REQUEST) + '<h2>Edition des lettres individuelles de %s</h2>' % sem['titreannee'] ]
        F = self.sco_footer(REQUEST)
        descr = [
            ('dateJury', {'input_type' : 'text', 'size' : 50, 'title' : 'Date du Jury', 'explanation' : '(si le jury a eu lieu)' }),
            ('signature',  {'input_type' : 'file', 'size' : 30, 'explanation' : 'optionnel: image scannée de la signature'}),
            ('formsemestre_id', {'input_type' : 'hidden' })]
        tf = TrivialFormulator( REQUEST.URL0, REQUEST.form, descr,
                                cancelbutton = 'Annuler', method='POST',
                                submitlabel = 'Générer document', 
                                name='tf' )
        if  tf[0] == 0:
            return '\n'.join(H) + '\n' + tf[1] + F
        elif tf[0] == -1:
            return REQUEST.RESPONSE.redirect( "formsemestre_pvjury?formsemestre_id=%s" %(formsemestre_id))
        else:
            # submit
            sf = tf[2]['signature']
            #pdb.set_trace()
            signature = sf.read() # image of signature
            try:
                PDFLOCK.acquire()
                pdfdoc = sco_pvpdf.pdf_lettres_individuelles(self, formsemestre_id,
                                                             dateJury=tf[2]['dateJury'],
                                                             signature=signature)
            finally:
                PDFLOCK.release()
            sem = self.get_formsemestre(formsemestre_id)
            dt = time.strftime( '%Y-%m-%d' )
            filename = 'lettres-%s-%s.pdf' % (sem['titre_num'], dt)
            return sendPDFFile(REQUEST, pdfdoc, filename)
        
    security.declareProtected(ScoView, 'formsemestre_pvjury_pdf')
    def formsemestre_pvjury_pdf(self, formsemestre_id, etudid=None, REQUEST=None):
        """Generation PV jury en PDF: saisie des paramètres
        Si etudid, PV pour un seul etudiant. Sinon, tout les inscrits au semestre.
        """
        sem = self.get_formsemestre(formsemestre_id)
        if etudid:
            etud = self.getEtudInfo(etudid=etudid,filled=1)[0]
            etuddescr = '<a class="discretelink" href="ficheEtud?etudid=%s">%s</a> en' % (etudid,etud['nomprenom'])
        else:
            etuddescr = ''

        H = [self.sco_header(REQUEST) + '<h2>Edition du PV de jury de %s %s</h2>'
             % (etuddescr, sem['titreannee']) ]
        F = self.sco_footer(REQUEST)
        descr = [
            ('dateCommission', {'input_type' : 'text', 'size' : 50, 'title' : 'Date de la commission', 'explanation' : '(format libre)'}),
            ('dateJury', {'input_type' : 'text', 'size' : 50, 'title' : 'Date du Jury', 'explanation' : '(si le jury a eu lieu)' }),
            ('numeroArrete', {'input_type' : 'text', 'size' : 50, 'title' : 'Numéro de l\'arrêté du président',
            'explanation' : 'le président de l\'Université prend chaque anné un arrêté formant les jurys'}),
            ('showTitle', { 'input_type' : 'checkbox', 'title':'Indiquer le titre du semestre', 'explanation' : '(le titre est "%s")' % sem['titre'], 'labels' : [''], 'allowed_values' : ('1',)}),
            ('formsemestre_id', {'input_type' : 'hidden' }) ]
        if etudid:
            descr.append( ('etudid', {'input_type' : 'hidden' }) )
        tf = TrivialFormulator( REQUEST.URL0, REQUEST.form, descr,
                                cancelbutton = 'Annuler', method='GET',
                                submitlabel = 'Générer document', 
                                name='tf' )
        if  tf[0] == 0:
            return '\n'.join(H) + '\n' + tf[1] + F
        elif tf[0] == -1:
            return REQUEST.RESPONSE.redirect( "formsemestre_pvjury?formsemestre_id=%s" %(formsemestre_id))
        else:
            # submit
            if etudid:
                etudids = [etudid]
            else:
                etudids = None
            dpv = sco_pvjury.dict_pvjury(self, formsemestre_id, etudids=etudids, with_prev=True)
            if tf[2]['showTitle']:
                tf[2]['showTitle'] = True
            else:
                tf[2]['showTitle'] = False
            try:
                PDFLOCK.acquire()
                pdfdoc = sco_pvpdf.pvjury_pdf(self, dpv, REQUEST,
                                              numeroArrete=tf[2]['numeroArrete'],
                                              dateCommission=tf[2]['dateCommission'],
                                              dateJury=tf[2]['dateJury'],
                                              showTitle=tf[2]['showTitle'])
            finally:
                PDFLOCK.release()                
            sem = self.get_formsemestre(formsemestre_id)
            dt = time.strftime( '%Y-%m-%d' )
            filename = 'PV-%s-%s.pdf' % (sem['titre_num'], dt)
            return sendPDFFile(REQUEST, pdfdoc, filename)
        
#     def _formsemestre_get_decision_str(self, cnx, etudid, formsemestre_id ):
#         """Chaine HTML decrivant la decision du jury pour cet etudiant.
#         Resultat: decision semestre, UE capitalisees
#         """
#         etat, decision_sem, decisions_ue = self._formsemestre_get_decision(etudid, formsemestre_id )
#         if etat == 'D':
#             decision = 'démission'
#         else:
#             if decision_sem:
#                 cod = decision_sem['code']
#                 decision = sco_codes_parcours.CODES_EXPL.get(cod,'') + ' (%s)' % cod
#             else:
#                 decision = ''

#         if decisions_ue:
#             uelist = []
#             for ue_id in decisions_ue.keys():
#                 if decisions_ue[ue_id]['code'] == 'ADM':
#                     ue = self.do_ue_list( args={ 'ue_id' : ue_id } )[0]
#                     uelist.append(ue)
#             uelist.sort( lambda x,y: cmp(x['numero'],y['numero']) )
#             ue_acros = ', '.join( [ ue['acronyme'] for ue in uelist ] )
#         else:
#             ue_acros = ''
#         return decision, ue_acros
    
#     def _formsemestre_get_decision(self, etudid, formsemestre_id ):
#         """Semestre et liste des UE validées
#         Resultat:
#           etat = I|D  (inscription ou démission)
#           decision_sem = {}
#           decisions_ue = {} 
#         }
#         """
#         nt = self._getNotesCache().get_NotesTable(self, formsemestre_id)
#         etat = nt.get_etud_etat(etudid)
#         decision_sem = nt.get_etud_decision_sem(etudid)
#         decisions_ue = nt.get_etud_decision_ues(etudid)
#         return etat, decision_sem, decisions_ue                                                       

    # ------------- Feuille excel pour preparation des jurys
    security.declareProtected(ScoView,'feuille_preparation_jury')
    def feuille_preparation_jury(self, formsemestre_id, REQUEST):
        "Feuille excel pour preparation des jurys"
        return sco_prepajury.feuille_preparation_jury(self, formsemestre_id, REQUEST)        
        
    # ------------- INSCRIPTIONS: PASSAGE D'UN SEMESTRE A UN AUTRE
    security.declareProtected(ScoEtudInscrit,'formsemestre_inscr_passage')
    formsemestre_inscr_passage = sco_inscr_passage.formsemestre_inscr_passage

    security.declareProtected(ScoEtudInscrit,'formsemestre_synchro_etuds')
    formsemestre_synchro_etuds = sco_synchro_etuds.synchronize_etuds

    # ------------- RAPPORTS STATISTIQUES
    security.declareProtected(ScoView, "formsemestre_report_counts")
    formsemestre_report_counts = sco_report.formsemestre_report_counts

    security.declareProtected(ScoView, "formsemestre_suivi_cohorte")
    formsemestre_suivi_cohorte = sco_report.formsemestre_suivi_cohorte

    security.declareProtected(ScoView, "formsemestre_suivi_parcours")
    formsemestre_suivi_parcours = sco_report.formsemestre_suivi_parcours

    security.declareProtected(ScoView, "formsemestre_graph_parcours")
    formsemestre_graph_parcours = sco_report.formsemestre_graph_parcours

    # --------------------------------------------------------------------
    # DEBUG
    security.declareProtected(ScoView,'check_sem_integrity')
    def check_sem_integrity(self, formsemestre_id, REQUEST):
        "debug"
        sem = self.get_formsemestre(formsemestre_id)
        modimpls = self.do_moduleimpl_list( {'formsemestre_id':formsemestre_id} )
        bad = []
        for modimpl in modimpls:
            mod = self.do_module_list( {'module_id': modimpl['module_id'] } )[0]
            ue = self.do_ue_list( {'ue_id' : mod['ue_id']})[0]
            if ue['formation_id'] != mod['formation_id']:
                modimpl['mod'] = mod
                modimpl['ue'] = ue                
                bad.append(modimpl)                
        return self.sco_header(REQUEST=REQUEST)+'<br/>'.join([str(x) for x in bad])+self.sco_footer(REQUEST)

    security.declareProtected(ScoView,'check_form_integrity')
    def check_form_integrity(self, formation_id, fix=False, REQUEST=None):
        "debug"
        log("check_form_integrity: formation_id=%s  fix=%s" % (formation_id, fix))
        F = self.do_formation_list( args={ 'formation_id' : formation_id } )[0]
        ues = self.do_ue_list( args={ 'formation_id' : formation_id } )
        bad = []
        for ue in ues:
            mats = self.do_matiere_list( args={ 'ue_id' : ue['ue_id'] })
            for mat in mats:
                mods = self.do_module_list( {'matiere_id': mat['matiere_id'] } )
                for mod in mods:
                    if mod['ue_id'] != ue['ue_id']:
                        if fix:
                            # fix mod.ue_id
                            log("fix: mod.ue_id = %s (was %s)" % (ue['ue_id'], mod['ue_id']))
                            mod['ue_id'] = ue['ue_id']
                            self.do_module_edit(mod)                    
                        bad.append(mod)
                    if mod['formation_id'] != formation_id:
                        bad.append(mod)
        if bad:
            txth = '<br/>'.join([str(x) for x in bad])
            txt = '\n'.join([str(x) for x in bad])
            log('check_form_integrity: formation_id=%s\ninconsistencies:' % formation_id)
            log(txt)
            # Notify by e-mail
            sendAlarm( self, 'Notes: formation incoherente !', txt)
        else:
            txth = 'OK'
            log('ok')
        return self.sco_header(REQUEST=REQUEST)+txth+self.sco_footer(REQUEST)

    security.declareProtected(ScoView,'check_formsemestre_integrity')
    def check_formsemestre_integrity(self, formsemestre_id, REQUEST=None):
        "debug"
        log("check_formsemestre_integrity: formsemestre_id=%s" % (formsemestre_id))
        # verifie que tous les moduleimpl d'un formsemestre
        # se réfèrent à un module dont l'UE appartient a la même formation
        # Ancien bug: les ue_id étaient mal copiés lors des création de versions
        # de formations
        diag = []
        sem = self.do_formsemestre_list(args={ 'formsemestre_id' : formsemestre_id })[0]
        Mlist = self.do_moduleimpl_withmodule_list( args={ 'formsemestre_id' : formsemestre_id })
        for mod in Mlist:
            if mod['module']['ue_id'] != mod['matiere']['ue_id']:
                diag.append('moduleimpl %s: module.ue_id=%s != matiere.ue_id=%s'
                            % (mod['moduleimpl_id'], mod['module']['ue_id'], mod['matiere']['ue_id']) )
            if mod['ue']['formation_id'] != mod['module']['formation_id']:
                diag.append('moduleimpl %s: ue.formation_id=%s != mod.formation_id=%s'
                            % (mod['moduleimpl_id'],mod['ue']['formation_id'],mod['module']['formation_id']))
        if diag:
            sendAlarm( self, 'Notes: formation incoherente dans semestre %s !'
                       % formsemestre_id, '\n'.join(diag) )
            log('check_formsemestre_integrity: formsemestre_id=%s' % formsemestre_id)
            log('inconsistencies:\n'+'\n'.join(diag))
        else:
            diag = ['OK']
            log('ok')
        return self.sco_header(REQUEST=REQUEST)+'<br/>'.join(diag)+self.sco_footer(REQUEST)

    security.declareProtected(ScoView,'check_integrity_all')
    def check_integrity_all(self, REQUEST=None):
        "debug: verifie tous les semestres et tt les formations"
        # formations
        for F in self.do_formation_list():
            self.check_form_integrity(F['formation_id'], REQUEST=REQUEST)
        # semestres
        for sem in self.do_formsemestre_list():
            self.check_formsemestre_integrity(sem['formsemestre_id'], REQUEST=REQUEST)
        return self.sco_header(REQUEST=REQUEST)+'<p>empty page: see logs and mails</p>'+self.sco_footer(REQUEST)
    
    # --------------------------------------------------------------------
# Uncomment these lines with the corresponding manage_option
# To everride the default 'Properties' tab
#    # Edit the Properties of the object
#    manage_editForm = DTMLFile('dtml/manage_editZScolarForm', globals())


# --------------------------------------------------------------------
#
#    MISC AUXILIARY FUNCTIONS
#
# --------------------------------------------------------------------
def notes_moyenne_median(notes):
    "calcule moyenne et mediane d'une liste de valeurs (floats)"
    notes = [ x for x in notes if (x != None) and (x != NOTES_NEUTRALISE) and (x != NOTES_ATTENTE) ]
    n = len(notes)
    if not n:
        return None, None
    moy = sum(notes) / n
    median = ListMedian(notes)
    return moy, median

def ListMedian( L ):
    """Median of a list L"""
    n = len(L)
    if not n:
	raise ValueError, 'empty list'
    L.sort()
    if n % 2:
	return L[n/2]
    else:
	return (L[n/2] + L[n/2-1])/2 

# --------------------------------------------------------------------
#
# Zope Product Administration
#
# --------------------------------------------------------------------
def manage_addZNotes(self, id= 'id_ZNotes', title='The Title for ZNotes Object', REQUEST=None):
   "Add a ZNotes instance to a folder."
   self._setObject(id, ZNotes(id, title))
   if REQUEST is not None:
        return self.manage_main(self, REQUEST)
        #return self.manage_editForm(self, REQUEST)

# The form used to get the instance id from the user.
manage_addZNotesForm = DTMLFile('dtml/manage_addZNotesForm', globals())


    

