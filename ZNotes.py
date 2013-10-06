# -*- mode: python -*-
# -*- coding: iso8859-15 -*-

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

"""Interface Zope <-> Notes
"""

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
from gen_tables import GenTable
import sco_cache
import scolars
import sco_news
from sco_news import NEWS_INSCR, NEWS_NOTE, NEWS_FORM, NEWS_SEM, NEWS_MISC

import sco_formsemestre_edit, sco_formsemestre_status
import sco_edit_ue, sco_edit_formation, sco_edit_matiere, sco_edit_module
from sco_formsemestre_status import makeMenu
import sco_formsemestre_inscriptions
import sco_formsemestre_custommenu
import sco_moduleimpl_status
import sco_moduleimpl_inscriptions
import sco_evaluations
import sco_groups
import sco_bulletins, sco_bulletins_pdf, sco_recapcomplet
import sco_liste_notes, sco_saisie_notes, sco_undo_notes
import sco_formations
import sco_report
import sco_lycee
import sco_poursuite_dut
import sco_debouche
import sco_cost_formation
import sco_formsemestre_validation, sco_parcours_dut, sco_codes_parcours
import sco_pvjury, sco_pvpdf, sco_prepajury
import sco_inscr_passage, sco_synchro_etuds
import sco_archives
from sco_pdf import PDFLOCK
from notes_table import *
import VERSION

#
# Cache global: chaque instance, repérée par sa connexion db, a un cache
# qui est recréé à la demande
#
CACHE_formsemestre_inscription = {}
CACHE_evaluations = {}

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
    
    def _getNotesCache(self):
        "returns CacheNotesTable instance for us"
        u = self.GetDBConnexionString() # identifie le dept de facon fiable
        if not NOTES_CACHE_INST.has_key(u):
            log('getNotesCache: creating cache for %s' % u )
            NOTES_CACHE_INST[u] = CacheNotesTable()
        return NOTES_CACHE_INST[u]

    def _inval_cache(self, formsemestre_id=None, 
                     pdfonly=False,
                     formsemestre_id_list=None,
                     ): #>
        "expire cache pour un semestre (ou tous si pas d'argument)"
        if formsemestre_id_list:
            for formsemestre_id in formsemestre_id_list:
                self._getNotesCache().inval_cache(self, formsemestre_id=formsemestre_id, pdfonly=pdfonly)
                # Affecte aussi cache inscriptions
                self.get_formsemestre_inscription_cache().inval_cache(key=formsemestre_id) #>
        else:
            self._getNotesCache().inval_cache(self, formsemestre_id=formsemestre_id, pdfonly=pdfonly) #>
            # Affecte aussi cache inscriptions
            self.get_formsemestre_inscription_cache().inval_cache(key=formsemestre_id) #>
    
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
                sco_recapcomplet.do_formsemestre_recapcomplet(self, REQUEST,formsemestre_id, format='xml', xml_nodate=True))
        #
        cache.inval_cache(self) #>
        # Rebuild cache (useful only to debug)
        docs_after = []
        for formsemestre_id in formsemestre_ids:
            docs_after.append(
                sco_recapcomplet.do_formsemestre_recapcomplet(self, REQUEST,formsemestre_id, format='xml', xml_nodate=True))
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

    # Python methods:
    security.declareProtected(ScoView, 'formsemestre_status')
    formsemestre_status = sco_formsemestre_status.formsemestre_status

    security.declareProtected(ScoImplement, 'formsemestre_createwithmodules')
    formsemestre_createwithmodules = sco_formsemestre_edit.formsemestre_createwithmodules

    security.declareProtected(ScoView, 'formsemestre_editwithmodules')
    formsemestre_editwithmodules = sco_formsemestre_edit.formsemestre_editwithmodules

    security.declareProtected(ScoView, 'formsemestre_clone')
    formsemestre_clone = sco_formsemestre_edit.formsemestre_clone
    
    security.declareProtected(ScoChangeFormation, 'formsemestre_associate_new_version')
    formsemestre_associate_new_version = sco_formsemestre_edit.formsemestre_associate_new_version

    security.declareProtected(ScoImplement, 'formsemestre_delete')
    formsemestre_delete = sco_formsemestre_edit.formsemestre_delete
    security.declareProtected(ScoImplement, 'formsemestre_delete2')
    formsemestre_delete2 = sco_formsemestre_edit.formsemestre_delete2
    
    security.declareProtected(ScoView, 'formsemestre_recapcomplet')
    formsemestre_recapcomplet = sco_recapcomplet.formsemestre_recapcomplet
    
    security.declareProtected(ScoView,'moduleimpl_status')
    moduleimpl_status = sco_moduleimpl_status.moduleimpl_status

    security.declareProtected(ScoView, 'formsemestre_description')
    formsemestre_description = sco_formsemestre_status.formsemestre_description

    security.declareProtected(ScoView, 'formsemestre_lists')
    formsemestre_lists = sco_formsemestre_status.formsemestre_lists

    security.declareProtected(ScoView, 'formsemestre_status_menubar')
    formsemestre_status_menubar = sco_formsemestre_status.formsemestre_status_menubar
    security.declareProtected(ScoChangeFormation, 'formation_create')
    formation_create = sco_edit_formation.formation_create
    security.declareProtected(ScoChangeFormation, 'formation_delete')
    formation_delete = sco_edit_formation.formation_delete
    security.declareProtected(ScoChangeFormation, 'formation_edit')
    formation_edit = sco_edit_formation.formation_edit

    security.declareProtected(ScoView, 'formsemestre_bulletinetud')
    formsemestre_bulletinetud = sco_bulletins.formsemestre_bulletinetud

    security.declareProtected(ScoView, 'formsemestre_evaluations_cal')
    formsemestre_evaluations_cal = sco_evaluations.formsemestre_evaluations_cal
    security.declareProtected(ScoView, 'module_evaluation_renumber')
    module_evaluation_renumber = sco_evaluations.module_evaluation_renumber
    security.declareProtected(ScoView, 'module_evaluation_move')
    module_evaluation_move = sco_evaluations.module_evaluation_move
    
    security.declareProtected(ScoView, 'formsemestre_list_saisies_notes')
    formsemestre_list_saisies_notes = sco_undo_notes.formsemestre_list_saisies_notes

    security.declareProtected(ScoChangeFormation, 'ue_create')
    ue_create = sco_edit_ue.ue_create
    security.declareProtected(ScoChangeFormation, 'ue_delete')
    ue_delete = sco_edit_ue.ue_delete
    security.declareProtected(ScoChangeFormation, 'ue_edit')
    ue_edit = sco_edit_ue.ue_edit
    security.declareProtected(ScoView, 'ue_list')
    ue_list = sco_edit_ue.ue_list
    security.declareProtected(ScoView, 'ue_sharing_code')
    ue_sharing_code = sco_edit_ue.ue_sharing_code
    security.declareProtected(ScoView, 'formation_table_recap')
    formation_table_recap = sco_edit_ue.formation_table_recap
    
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
    
    # 
    security.declareProtected(ScoView, 'index_html')
    def index_html(self, REQUEST=None):
        "Page accueil formations"
        sco_groups.checkLastIcon(self, REQUEST)
        lockicon = self.icons.lock32_img.tag(title="Comporte des semestres verrouillés", border='0')
        suppricon= self.icons.delete_small_img.tag(border='0', alt='supprimer', title='Supprimer')
        editicon = self.icons.edit_img.tag(border='0', alt='modifier', title='Modifier titres et code')

        editable = REQUEST.AUTHENTICATED_USER.has_permission(ScoChangeFormation,self)

        H = [ self.sco_header(REQUEST, page_title="Programmes formations"),
              """<h2>Programmes des formations</h2>
              <ul class="notes_formation_list">""" ]

        for F in self.formation_list():
            H.append('<li class="notes_formation_list">')
            H.append('<a class="stdlink" href="formation_delete?formation_id=%s">%s</a>' % (F['formation_id'], suppricon))
            if editable:
                H.append('<a class="stdlink" href="formation_edit?formation_id=%s">%s</a>' % (F['formation_id'], editicon))
            H.append('%(acronyme)s: <em>%(titre)s</em> (version %(version)s)' % F )
            locked = self.formation_has_locked_sems(F['formation_id'])
            if locked:
                H.append(lockicon)
            
            H.append("""<a class="stdlink" href="ue_list?formation_id=%(formation_id)s">éditer le programme</a>""" % F )
            H.append(""" <a class="stdlink" href="ue_list?formation_id=%(formation_id)s#sems">créer semestre</a>""" % F )
            H.append('</li>')
        H.append('</ul>')
        if editable:
            H.append("""<p><a class="stdlink" href="formation_create">Créer une formation</a></p>
 	 <p><a class="stdlink" href="formation_import_xml_form">Importer une formation (xml)</a></p>
         <p class="help">Une "formation" définie un programme pédagogique structuré en UE, matières et modules. Chaque semestre (session) fait référence à une formation. La modification d'une formation affecte tous les semestres qui s'y réfèrent.</p>
            """)

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
        ('formation_id', 'acronyme','titre', 'titre_officiel', 'version', 'formation_code', 'type_parcours'),
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
        F = self.formation_list(args=a)
        if len(F) > 0:
            log('do_formation_create: error: %d formations matching args=%s'
                % (len(F), a))
            raise ScoValueError("Formation non unique (%s) !" % str(a))
        # Si pas de formation_code, l'enleve (default SQL)
        if args.has_key('formation_code') and not args['formation_code']:
            del args['formation_code']
        #
        r = self._formationEditor.create(cnx, args)
        
        sco_news.add(self, REQUEST, typ=NEWS_FORM,
                     text='Création de la formation %(titre)s (%(acronyme)s)' % args )
        return r
    
    security.declareProtected(ScoChangeFormation, 'do_formation_delete')
    def do_formation_delete(self, oid, REQUEST):
        """delete a formation (and all its UE, matieres, modules)
        XXX delete all ues, will break if there are validations ! USE WITH CARE !
        """
        F = self.formation_list(args={'formation_id':oid})[0]
        if self.formation_has_locked_sems(oid):
            raise ScoLockedFormError()
        cnx = self.GetDBConnexion()
        # delete all UE in this formation
        ues = self.do_ue_list({ 'formation_id' : oid })
        for ue in ues:
            self._do_ue_delete(ue['ue_id'], REQUEST=REQUEST, force=True)
        
        self._formationEditor.delete(cnx, oid)
        
        # news
        sco_news.add(self, REQUEST, typ=NEWS_FORM, object=oid,
                     text='Suppression de la formation %(acronyme)s' % F )

    security.declareProtected(ScoView, 'formation_list')
    def formation_list(self, format=None, REQUEST=None, formation_id=None, args={} ):
        """List formation(s) with given id, or matching args
        (when args is given, formation_id is ignored).
        """
        #logCallStack()
        if not args:
            if formation_id is None:
                args = {}
            else:
                args = { 'formation_id' : formation_id }
        cnx = self.GetDBConnexion()        
        r = self._formationEditor.list( cnx, args=args )
        #log('%d formations found' % len(r))
        return sendResult(REQUEST, r, name='formation', format=format)

    security.declareProtected(ScoView, 'formation_export')
    def formation_export(self, formation_id, export_ids=False, format=None, REQUEST=None):
        "Export de la formation au format indiqué (xml ou json)"
        return sco_formations.formation_export(self, formation_id, export_ids=export_ids,
                                               format=format, REQUEST=REQUEST)
    
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
            formation_id, junk, junk = self.formation_import_xml(tf[2]['xmlfile'],REQUEST)
            
            return '\n'.join(H) + """<p>Import effectué !</p>
            <p><a class="stdlink" href="ue_list?formation_id=%s">Voir la formation</a></p>""" % formation_id + footer

    security.declareProtected(ScoChangeFormation, 'formation_create_new_version')
    def formation_create_new_version(self,formation_id,redirect=True,REQUEST=None):
        "duplicate formation, with new version number"
        xml = sco_formations.formation_export(self, formation_id, export_ids=True, format='xml')
        new_id, modules_old2new, ues_old2new = sco_formations.formation_import_xml(self,REQUEST, xml)
        # news
        F = self.formation_list(args={ 'formation_id' :new_id})[0]
        sco_news.add(self, REQUEST, typ=NEWS_FORM, object=new_id,
                     text='Nouvelle version de la formation %(acronyme)s'%F)
        if redirect:
            return REQUEST.RESPONSE.redirect("ue_list?formation_id=" + new_id + '&msg=Nouvelle version !')
        else:
            return new_id, modules_old2new, ues_old2new
        
    # --- UE
    _ueEditor = EditableTable(
        'notes_ue',
        'ue_id',
        ('ue_id', 'formation_id', 'acronyme', 'numero', 'titre',
         'type', 'ue_code', 'ects' ),
        sortkey='numero',
        input_formators = { 'type' : int_null_is_zero },
        output_formators = { 'numero' : int_null_is_zero,
                             'ects' : float_null_is_null },
        )

    security.declareProtected(ScoChangeFormation, 'do_ue_create')
    def do_ue_create(self, args, REQUEST):
        "create an ue"
        cnx = self.GetDBConnexion()
        # check duplicates
        ues = self.do_ue_list({'formation_id' : args['formation_id'],
                               'acronyme' : args['acronyme'] })
        if ues:
            raise ScoValueError('Acronyme d\'UE "%s" déjà utilisé !' % args['acronyme'])
        # create
        r = self._ueEditor.create(cnx, args)
        
        # news
        F = self.formation_list(args={ 'formation_id' :args['formation_id']})[0]
        sco_news.add(self, REQUEST, typ=NEWS_FORM, object=args['formation_id'],
                     text='Modification de la formation %(acronyme)s' % F )
        return r

    def _do_ue_delete(self, ue_id, delete_validations=False, REQUEST=None, force=False):
        "delete UE and attached matieres (but not modules (it should ?))"
        cnx = self.GetDBConnexion()
        log('do_ue_delete: ue_id=%s, delete_validations=%s' % (ue_id, delete_validations))
        # check
        ue = self.do_ue_list({ 'ue_id' : ue_id })
        if not ue:
            raise ScoValueError('UE inexistante !')
        ue = ue[0]
        if self.ue_is_locked(ue['ue_id']):
            raise ScoLockedFormError()      
        # Il y a-t-il des etudiants ayant validé cette UE ?
        # si oui, propose de supprimer les validations
        validations = sco_parcours_dut.scolar_formsemestre_validation_list ( cnx, args={'ue_id' : ue_id} )
        if validations and not delete_validations and not force:
            return self.confirmDialog(
                '<p>%d étudiants ont validé l\'UE %s (%s)</p><p>Si vous supprimez cette UE, ces validations vont être supprimées !</p>' % (len(validations), ue['acronyme'], ue['titre']),
                dest_url="", REQUEST=REQUEST,
                target_variable='delete_validations',
                cancel_url="ue_list?formation_id=%s"%ue['formation_id'],
                parameters={'ue_id' : ue_id, 'dialog_confirmed' : 1} )
        if delete_validations:
            log('deleting all validations of UE %s' % ue_id )
            SimpleQuery(self, "DELETE FROM scolar_formsemestre_validation WHERE ue_id=%(ue_id)s",
                        { 'ue_id' : ue_id } )
        
        # delete all matiere in this UE
        mats = self.do_matiere_list({ 'ue_id' : ue_id })
        for mat in mats:
            self.do_matiere_delete(mat['matiere_id'], REQUEST)
        # delete uecoef and events
        SimpleQuery(self, "DELETE FROM notes_formsemestre_uecoef WHERE ue_id=%(ue_id)s",{'ue_id':ue_id})
        SimpleQuery(self, "DELETE FROM scolar_events WHERE ue_id=%(ue_id)s", { 'ue_id' : ue_id } )
        cnx = self.GetDBConnexion()
        self._ueEditor.delete(cnx, ue_id)
        self._inval_cache() #> UE delete + supr. validations associées etudiants (cas compliqué, mais rarement utilisé: acceptable de tout invalider ?)
        # news
        F = self.formation_list(args={ 'formation_id' :ue['formation_id']})[0]
        sco_news.add(self, REQUEST, typ=NEWS_FORM, object=ue['formation_id'],
                     text='Modification de la formation %(acronyme)s' % F )
        #
        if not force:
            return REQUEST.RESPONSE.redirect( REQUEST.URL1 + '/ue_list?formation_id=' + str(ue['formation_id']))
        else:
            return None

    security.declareProtected(ScoView, 'do_ue_list')
    def do_ue_list(self, *args, **kw ):
        "list UEs"
        cnx = self.GetDBConnexion()
        return self._ueEditor.list(cnx, *args, **kw)

 

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
        # create matiere
        r = self._matiereEditor.create(cnx, args)
        
        # news
        F = self.formation_list(args={ 'formation_id' :ue['formation_id']})[0]
        sco_news.add(self, REQUEST, typ=NEWS_FORM, object=ue['formation_id'],
                     text='Modification de la formation %(acronyme)s' % F )
        return r

    security.declareProtected(ScoChangeFormation, 'do_matiere_delete')
    def do_matiere_delete(self, oid, REQUEST):
        "delete matiere and attached modules"
        cnx = self.GetDBConnexion()
        # check
        mat = self.do_matiere_list({ 'matiere_id' : oid })[0]
        ue = self.do_ue_list({ 'ue_id' : mat['ue_id'] })[0]
        locked = self.matiere_is_locked(mat['matiere_id'])
        if locked:
            log('do_matiere_delete: mat=%s' % mat)
            log('do_matiere_delete: ue=%s' % ue)
            log('do_matiere_delete: locked sems: %s' % locked)
            raise ScoLockedFormError()  
        log('do_matiere_delete: matiere_id=%s' % oid)
        # delete all modules in this matiere
        mods = self.do_module_list({ 'matiere_id' : oid })
        for mod in mods:
            self.do_module_delete(mod['module_id'],REQUEST)
        self._matiereEditor.delete(cnx, oid)
        
        # news
        F = self.formation_list(args={ 'formation_id' :ue['formation_id']})[0]
        sco_news.add(self, REQUEST, typ=NEWS_FORM, object=ue['formation_id'],
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
        if self.matiere_is_locked(mat['matiere_id']):
            raise ScoLockedFormError() 
        # edit
        self._matiereEditor.edit( cnx, *args, **kw )
        self._inval_cache() #> modif matiere

    security.declareProtected(ScoView, 'do_matiere_formation_id')
    def do_matiere_formation_id(self, matiere_id):
        "get formation_id from matiere"
        cnx = self.GetDBConnexion()
        cursor = cnx.cursor(cursor_factory=ScoDocCursor)
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
         'semestre_id', 'numero', 'ects' ),
        sortkey='numero',
        output_formators = { 'heures_cours' : float_null_is_zero,
                             'heures_td' : float_null_is_zero,
                             'heures_tp' :  float_null_is_zero,
                             'numero' : int_null_is_zero,
                             'ects' : float_null_is_null
                             },
        )

    security.declareProtected(ScoChangeFormation, 'do_module_create')
    def do_module_create(self, args, REQUEST):
        "create a module"
        # create
        cnx = self.GetDBConnexion()
        r = self._moduleEditor.create(cnx, args)
        
        # news
        F = self.formation_list(args={ 'formation_id' :args['formation_id']})[0]
        sco_news.add(self, REQUEST, typ=NEWS_FORM, object=args['formation_id'],
                     text='Modification de la formation %(acronyme)s' % F )
        return r

    security.declareProtected(ScoChangeFormation, 'do_module_delete')
    def do_module_delete(self, oid, REQUEST):
        "delete module"
        mod = self.do_module_list({ 'module_id' : oid})[0]
        if self.module_is_locked(mod['module_id']):
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
        
        # news
        F = self.formation_list(args={ 'formation_id' :mod['formation_id']})[0]
        sco_news.add(self, REQUEST, typ=NEWS_FORM, object=mod['formation_id'],
                     text='Modification de la formation %(acronyme)s' % F )

    security.declareProtected(ScoView, 'do_module_list')
    def do_module_list(self, *args, **kw ):
        "list modules"
        cnx = self.GetDBConnexion()
        return self._moduleEditor.list(cnx, *args, **kw)

    security.declareProtected(ScoChangeFormation, 'do_module_edit')
    def do_module_edit(self, val):
        "edit a module"
        # check
        mod = self.do_module_list({'module_id' : val['module_id']})[0]
        if self.module_is_locked(mod['module_id']):
            # formation verrouillée: empeche de modifier certains champs:
            protected_fields = ('coefficient', 'ue_id', 'matiere_id', 'semestre_id')
            for f in protected_fields:
                if f in val:
                    del val[f]
        # edit
        cnx = self.GetDBConnexion()
        self._moduleEditor.edit(cnx, val)
        
        sems = self.do_formsemestre_list(args={ 'formation_id' : mod['formation_id'] })
        if sems:
            self._inval_cache(formsemestre_id_list=[s['formsemestre_id'] for s in sems]) #> modif module
    
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

    security.declareProtected(ScoView, 'module_is_locked')
    def module_is_locked(self, module_id):
        """True if UE should not be modified
        (used in a locked formsemestre)
        """
        r = SimpleDictFetch(
            self, 
            """SELECT mi.* from notes_modules mod, notes_formsemestre sem, notes_moduleimpl mi
            WHERE mi.module_id = mod.module_id AND mi.formsemestre_id = sem.formsemestre_id
            AND mi.module_id = %(module_id)s AND sem.etat = 0
            """, { 'module_id' : module_id } )
        return len(r) > 0
    
    security.declareProtected(ScoView, 'matiere_is_locked')
    def matiere_is_locked(self, matiere_id):
        """True if matiere should not be modified
        (contains modules used in a locked formsemestre)
        """
        r = SimpleDictFetch(
            self, 
            """SELECT ma.* from notes_matieres ma, notes_modules mod, notes_formsemestre sem, notes_moduleimpl mi
            WHERE ma.matiere_id = mod.matiere_id AND mi.module_id = mod.module_id AND mi.formsemestre_id = sem.formsemestre_id
            AND ma.matiere_id = %(matiere_id)s AND sem.etat = 0
            """, { 'matiere_id' : matiere_id } )
        return len(r) > 0
    
    security.declareProtected(ScoView, 'ue_is_locked')
    def ue_is_locked(self, ue_id):
        """True if module should not be modified
        (contains modules used in a locked formsemestre)
        """
        r = SimpleDictFetch(
            self, 
            """SELECT ue.* FROM notes_ue ue, notes_modules mod, notes_formsemestre sem, notes_moduleimpl mi
               WHERE ue.ue_id = mod.ue_id
               AND mi.module_id = mod.module_id AND mi.formsemestre_id = sem.formsemestre_id
               AND ue.ue_id = %(ue_id)s AND sem.etat = 0
            """, { 'ue_id' : ue_id } )
        return len(r) > 0

    security.declareProtected(ScoChangeFormation, 'module_move')
    def module_move(self, module_id, after=0, REQUEST=None, redirect=1):
        """Move before/after previous one (decrement/increment numero)"""
        module = self.do_module_list({'module_id' : module_id})[0]
        redirect = int(redirect)
        after = int(after) # 0: deplace avant, 1 deplace apres
        if after not in (0,1):
            raise ValueError('invalid value for "after"')
        formation_id = module['formation_id']
        others = self.do_module_list({'matiere_id' : module['matiere_id']})
        # log('others=%s' % others)
        if len(others) > 1:
            idx = [ p['module_id'] for p in others ].index(module_id)
            # log('module_move: after=%s idx=%s' % (after, idx))
            neigh = None # object to swap with
            if after == 0 and idx > 0:
                neigh = others[idx-1]            
            elif after == 1 and idx < len(others)-1:
                neigh = others[idx+1]
            if neigh: # 
                # swap numero between partition and its neighbor
                # log('moving module %s' % module_id)
                cnx = self.GetDBConnexion()
                module['numero'], neigh['numero'] = neigh['numero'], module['numero']
                if module['numero'] == neigh['numero']:
                    neigh['numero'] -= 2*after - 1
                self._moduleEditor.edit(cnx, module)
                self._moduleEditor.edit(cnx, neigh)
        
        # redirect to partition edit page:
        if redirect:
            return REQUEST.RESPONSE.redirect('ue_list?formation_id='+formation_id)
    
    # --- Semestres de formation
    _formsemestreEditor = EditableTable(
        'notes_formsemestre',
        'formsemestre_id',
        ('formsemestre_id', 'semestre_id', 'formation_id','titre',
         'date_debut', 'date_fin', 'responsable_id',
         'gestion_compensation', 'gestion_semestrielle',
         'etat', 'bul_hide_xml', 'bul_bgcolor',
         'etape_apo', 'etape_apo2', 'etape_apo3', 'etape_apo4',
         'modalite', 'resp_can_edit', 'resp_can_change_ens',
         'ens_can_edit_eval'
         ),
        sortkey = 'date_debut',
        output_formators = { 'date_debut' : DateISOtoDMY,
                             'date_fin'   : DateISOtoDMY,
                             'gestion_compensation' : str,
                             'gestion_semestrielle' : str,
                             'etat' : str,
                             'bul_hide_xml' : str,
                             },

        input_formators  = { 'date_debut' : DateDMYtoISO,
                             'date_fin'   : DateDMYtoISO,
                             'gestion_compensation' : int,
                             'gestion_semestrielle' : int,
                             'etat' : int,
                             'bul_hide_xml' : int,
                             },        
        )
    
    security.declareProtected(ScoImplement, 'do_formsemestre_create')
    def do_formsemestre_create(self, args, REQUEST):
        "create a formsemestre"
        cnx = self.GetDBConnexion()
        formsemestre_id = self._formsemestreEditor.create(cnx, args)
        # create default partition
        partition_id = sco_groups.partition_create(self, formsemestre_id, default=True, redirect=0, REQUEST=REQUEST)
        group_id = sco_groups.createGroup(self, partition_id, default=True, REQUEST=REQUEST)
        
        # news
        if not args.has_key('titre'):
            args['titre'] = 'sans titre'
        args['formsemestre_id'] = formsemestre_id
        args['url'] = 'Notes/formsemestre_status?formsemestre_id=%(formsemestre_id)s'%args
        sco_news.add(self, REQUEST, typ=NEWS_SEM,
                     text='Création du semestre <a href="%(url)s">%(titre)s</a>' % args,
                     url=args['url'])
        return formsemestre_id

    security.declareProtected(ScoView, 'do_formsemestre_list')
    def do_formsemestre_list(self, *a, **kw ):
        "list formsemestres"
        # XPUB should not be published !
        # log('do_formsemestre_list: a=%s kw=%s' % (str(a),str(kw)))
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
            F = self.formation_list(args={ 'formation_id' :sem['formation_id']})[0]
            parcours = sco_codes_parcours.get_parcours_from_code(F['type_parcours'])
            # Ajoute nom avec numero semestre:
            sem['titre_num'] = sem['titre']
            if sem['semestre_id'] != -1:
                sem['titre_num'] += ', %s %s' % (parcours.SESSION_NAME, sem['semestre_id'])

            sem['dateord'] = DateDMYtoISO(sem['date_debut'])
            sem['date_debut_iso'] = DateDMYtoISO(sem['date_debut'])
            sem['date_fin_iso'] = DateDMYtoISO(sem['date_fin'])
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
            
            sem['annee'] = annee_debut
            # 2007 ou 2007-2008:
            sem['anneescolaire'] = annee_scolaire_repr(int(annee_debut), sem['mois_debut_ord']) 
            
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
            sem['titremois'] =  '%s %s  (%s - %s)' % (sem['titre_num'], sem.get('modalite',''), 
                                                    sem['mois_debut'], sem['mois_fin'])
        # tri par date
        sems.sort(lambda x,y: cmp(y['dateord'],x['dateord']))

        return sems

    def formsemestre_list(self, format=None, REQUEST=None,
                          formsemestre_id=None,
                          formation_id=None,                          
                          etape_apo=None,
                          etape_apo2=None,
                          etape_apo3=None,
                          etape_apo4=None
                          ):
        """List formsemestres in given format.
        kw can specify some conditions: examples:
           formsemestre_list( format='json', formation_id='F777', REQUEST=REQUEST)
        """
        # XAPI: new json api
        args = {}
        L = locals()
        for argname in ('formsemestre_id', 'formation_id', 'etape_apo', 'etape_apo2', 'etape_apo3', 'etape_apo4'):
            if L[argname] is not None:
                args[argname] = L[argname]
        sems = self.do_formsemestre_list(args=args)
        # log('formsemestre_list: format="%s", %s semestres found' % (format,len(sems)))
        return sendResult(REQUEST, sems, name='formsemestre', format=format)
    
    security.declareProtected(ScoView, 'get_formsemestre')
    def get_formsemestre(self, formsemestre_id):
        "list ONE formsemestre"
        # XPUB should not be published !
        try:
            return self.do_formsemestre_list(args={ 'formsemestre_id' : formsemestre_id } )[0]
        except:
            log('get_formsemestre: invalid formsemestre_id (%s)' % formsemestre_id)
            raise

    security.declareProtected(ScoView, 'XMLgetFormsemestres')
    def XMLgetFormsemestres(self, etape_apo=None, formsemestre_id=None, REQUEST=None):
        """List all formsemestres matching etape, XML format
        DEPRECATED: use formsemestre_list()
        """
        args = {}
        if etape_apo:
            args['etape_apo'] = etape_apo
        if formsemestre_id:
            args['formsemestre_id'] = formsemestre_id
        if REQUEST:
            REQUEST.RESPONSE.setHeader('content-type', XML_MIMETYPE)
        doc = jaxml.XML_document( encoding=SCO_ENCODING )
        doc.formsemestrelist()
        for sem in self.do_formsemestre_list( args=args ):
            doc._push()
            doc.formsemestre(sem)
            doc._pop()
        return repr(doc)

    security.declareProtected(ScoImplement, 'do_formsemestre_edit')
    def do_formsemestre_edit(self, sem, cnx=None, **kw ):
        "edit a formsemestre"
        if not cnx:
            cnx = self.GetDBConnexion()
        self._formsemestreEditor.edit(cnx, sem, **kw )
        self._inval_cache(formsemestre_id=sem['formsemestre_id']) #> modif formsemestre
    
    security.declareProtected(ScoView,'formsemestre_edit_uecoefs')
    formsemestre_edit_uecoefs = sco_formsemestre_edit.formsemestre_edit_uecoefs

    security.declareProtected(ScoView,'formsemestre_edit_options')
    formsemestre_edit_options = sco_formsemestre_edit.formsemestre_edit_options

    security.declareProtected(ScoView,'formsemestre_change_lock')
    formsemestre_change_lock = sco_formsemestre_edit.formsemestre_change_lock

    def _check_access_diretud(self, formsemestre_id, REQUEST, required_permission=ScoImplement):
        """Check if access granted: responsable_id or ScoImplement
        Return True|False, HTML_error_page
        """
        authuser = REQUEST.AUTHENTICATED_USER
        sem = self.get_formsemestre(formsemestre_id)
        header = self.sco_header(page_title='Accès interdit',
                                 REQUEST=REQUEST)
        footer = self.sco_footer(REQUEST)
        if ((sem['responsable_id'] != str(authuser))
            and not authuser.has_permission(required_permission,self)):
            return False, '\n'.join( [
                header,
                '<h2>Opération non autorisée pour %s</h2>' % authuser,
                '<p>Responsable de ce semestre : <b>%s</b></p>'
                % sem['responsable_id'],
                footer ])
        else:
            return True, ''
    
    security.declareProtected(ScoView,'formsemestre_custommenu_edit')
    def formsemestre_custommenu_edit(self, REQUEST, formsemestre_id):
        "Dialogue modif menu"
        # accessible à tous !
        return sco_formsemestre_custommenu.formsemestre_custommenu_edit(
            self, formsemestre_id, REQUEST=REQUEST)

    security.declareProtected(ScoView,'formsemestre_custommenu_html')
    formsemestre_custommenu_html = sco_formsemestre_custommenu.formsemestre_custommenu_html

    security.declareProtected(ScoView,'html_sem_header')
    def html_sem_header(self, REQUEST, title, sem=None, with_page_header=True, with_h2=True,
                        page_title=None, **args):
        "Titre d'une page semestre avec lien vers tableau de bord"
        # sem now unused and thus optional...
        if with_page_header:
            h = self.sco_header(REQUEST, page_title="%s" % (page_title or title), **args)
        else:
            h = ''
        if with_h2:            
            return  h + """<h2 class="formsemestre">%s</h2>""" % (title)
        else:
            return h
    
    # --- Gestion des "Implémentations de Modules"
    # Un "moduleimpl" correspond a la mise en oeuvre d'un module
    # dans une formation spécifique, à une date spécifique.
    _moduleimplEditor = EditableTable(
        'notes_moduleimpl',
        'moduleimpl_id',
        ('moduleimpl_id','module_id','formsemestre_id','responsable_id', 'computation_expr'),
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
        self._inval_cache(formsemestre_id=args['formsemestre_id']) #> creation moduleimpl 
        return r

    security.declareProtected(ScoImplement, 'do_moduleimpl_delete')
    def do_moduleimpl_delete(self, oid, formsemestre_id=None):
        "delete moduleimpl (desinscrit tous les etudiants)"
        cnx = self.GetDBConnexion()
        # --- desinscription des etudiants
        cursor = cnx.cursor(cursor_factory=ScoDocCursor)
        req = "DELETE FROM notes_moduleimpl_inscription WHERE moduleimpl_id=%(moduleimpl_id)s"
        cursor.execute( req, { 'moduleimpl_id' : oid } )
        # --- suppression des enseignants
        cursor.execute( "DELETE FROM notes_modules_enseignants WHERE moduleimpl_id=%(moduleimpl_id)s", { 'moduleimpl_id' : oid } )
        # --- suppression des references dans les absences
        cursor.execute( "UPDATE absences SET moduleimpl_id=NULL WHERE moduleimpl_id=%(moduleimpl_id)s", { 'moduleimpl_id' : oid } )
        # --- destruction du moduleimpl
        self._moduleimplEditor.delete(cnx, oid)
        self._inval_cache(formsemestre_id=formsemestre_id) #> moduleimpl_delete

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
    def do_moduleimpl_edit(self, args, formsemestre_id=None, cnx=None):
        "edit a moduleimpl"
        if not cnx:
            cnx = self.GetDBConnexion()
        self._moduleimplEditor.edit(cnx, args)
        
        self._inval_cache(formsemestre_id=formsemestre_id) #> modif moduleimpl 
        
    security.declareProtected(ScoView, 'do_moduleimpl_withmodule_list')
    def do_moduleimpl_withmodule_list(self,args):
        """Liste les moduleimpls et ajoute dans chacun le module correspondant
        Tri la liste par semestre/UE/numero_matiere/numero_module
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
        header = self.html_sem_header(
            REQUEST, 
            'Enseignants du <a href="moduleimpl_status?moduleimpl_id=%s">module %s</a>' 
            % (moduleimpl_id, M['module']['titre']), 
            page_title='Enseignants du module %s' % M['module']['titre'],
            javascripts=['libjs/AutoSuggest.js'],
            cssstyles=['autosuggest_inquisitor.css'], 
            bodyOnLoad="init_tf_form('')"
            )
        footer = self.sco_footer(REQUEST)

        # Liste des enseignants avec forme pour affichage / saisie avec suggestion
        userlist = self.Users.get_userlist()
        login2display = {} # user_name : forme pour affichage = "NOM Prenom (login)"
        for u in userlist:
            login2display[u['user_name']] = u['nomplogin']
            allowed_user_names = login2display.values()

        H = [ 
              '<ul><li><b>%s</b> (responsable)</li>' % login2display.get(M['responsable_id'],M['responsable_id'])
              ]
        for ens in M['ens']:
            H.append('<li>%s (<a class="stdlink" href="edit_enseignants_form_delete?moduleimpl_id=%s&ens_id=%s">supprimer</a>)</li>' %
                     (login2display.get(ens['ens_id'],ens['ens_id']),
                      moduleimpl_id, ens['ens_id']))
        H.append('</ul>')
        F = """<p class="help">Les enseignants d'un module ont le droit de
        saisir et modifier toutes les notes des évaluations de ce module.
        </p>
        <p class="help">Pour changer le responsable du module, passez par la
        page "<a class="stdlink" href="formsemestre_editwithmodules?formation_id=%s&formsemestre_id=%s">Modification du semestre</a>", accessible uniquement au responsable de la formation (chef de département)
        </p>
        """ % (sem['formation_id'],M['formsemestre_id'])
        
        modform = [
            ('moduleimpl_id', { 'input_type' : 'hidden' }),
            ('ens_id',
             { 'input_type' : 'text_suggest', 
               'size' : 50,
               'title' : 'Ajouter un enseignant',
               'allowed_values' : allowed_user_names,
               'allow_null' : False,
               'text_suggest_options' : { 
                               'script' : 'Users/get_userlist_xml?',
                               'varname' : 'start',
                               'json': False,
                               'noresults' : 'Valeur invalide !',
                               'timeout':60000 }
               })
            ]
        tf = TrivialFormulator( REQUEST.URL0, REQUEST.form, modform,
                                submitlabel = 'Ajouter enseignant',
                                cancelbutton = 'Annuler')
        if tf[0] == 0:
            return header + '\n'.join(H) + tf[1] + F + footer
        elif tf[0] == -1:
            return REQUEST.RESPONSE.redirect('moduleimpl_status?moduleimpl_id='+moduleimpl_id)
        else:
            ens_id = self.Users.get_user_name_from_nomplogin(tf[2]['ens_id'])
            if not ens_id:
                H.append('<p class="help">Pour ajouter un enseignant, choisissez un nom dans le menu</p>')
            else:
                # et qu'il n'est pas deja:
                if ens_id in [ x['ens_id'] for x in M['ens'] ] or  ens_id == M['responsable_id']:
                    H.append('<p class="help">Enseignant %s déjà dans la liste !</p>' % ens_id)
                else:                    
                    self.do_ens_create( { 'moduleimpl_id' : moduleimpl_id,
                                          'ens_id' : ens_id } )
                    return REQUEST.RESPONSE.redirect('edit_enseignants_form?moduleimpl_id=%s'%moduleimpl_id)
            return header + '\n'.join(H) + tf[1] + F + footer

    security.declareProtected(ScoView, 'edit_moduleimpl_resp')
    def edit_moduleimpl_resp(self, REQUEST, moduleimpl_id):
        """Changement d'un enseignant responsable de module
        Accessible par Admin et dir des etud si flag resp_can_change_ens
        """
        M, sem = self.can_change_module_resp(REQUEST, moduleimpl_id)
        H = [ 
            self.html_sem_header(
                    REQUEST, 
                    'Modification du responsable du <a href="moduleimpl_status?moduleimpl_id=%s">module %s</a>' 
                    % (moduleimpl_id, M['module']['titre']), 
                    sem,
                    javascripts=['libjs/AutoSuggest.js'],
                    cssstyles=['autosuggest_inquisitor.css'], 
                    bodyOnLoad="init_tf_form('')"
                    )
            ]
        help = """<p class="help">Taper le début du nom de l'enseignant.</p>"""
        # Liste des enseignants avec forme pour affichage / saisie avec suggestion
        userlist = self.Users.get_userlist()
        login2display = {} # user_name : forme pour affichage = "NOM Prenom (login)"
        for u in userlist:
            login2display[u['user_name']] = u['nomplogin']
            allowed_user_names = login2display.values()

        initvalues = M
        initvalues['responsable_id'] = login2display.get(M['responsable_id'], M['responsable_id'])
        form = [
            ('moduleimpl_id', { 'input_type' : 'hidden' }),
            ('responsable_id', { 
                        'input_type' : 'text_suggest', 
                        'size' : 50,
                        'title' : 'Responsable du module',
                        'allowed_values' : allowed_user_names,
                        'allow_null' : False,
                        'text_suggest_options' : { 
                                        'script' : 'Users/get_userlist_xml?',
                                        'varname' : 'start',
                                        'json': False,
                                        'noresults' : 'Valeur invalide !',
                                        'timeout':60000 }
               }) ]
        tf = TrivialFormulator( REQUEST.URL0, REQUEST.form, form,
                                submitlabel = 'Changer responsable',
                                cancelbutton = 'Annuler',
                                initvalues=initvalues)
        if tf[0] == 0:
            return '\n'.join(H) + tf[1] + help + self.sco_footer(REQUEST)
        elif tf[0] == -1:
            return REQUEST.RESPONSE.redirect('moduleimpl_status?moduleimpl_id='+moduleimpl_id)
        else:
            responsable_id = self.Users.get_user_name_from_nomplogin(tf[2]['responsable_id'])
            if not responsable_id: # presque impossible: tf verifie les valeurs (mais qui peuvent changer entre temps)
                return REQUEST.RESPONSE.redirect('moduleimpl_status?moduleimpl_id='+moduleimpl_id)
            self.do_moduleimpl_edit( { 'moduleimpl_id' : moduleimpl_id,
                                       'responsable_id' : responsable_id },
                                     formsemestre_id=sem['formsemestre_id']
                                     )
            return REQUEST.RESPONSE.redirect('moduleimpl_status?moduleimpl_id='+moduleimpl_id+'&head_message=responsable%20modifié')

    _expr_help = """<p class="help">Expérimental: formule de calcul de la moyenne %(target)s</p>
        <p class="help">Dans la formule, les variables suivantes sont définies:</p>
        <ul class="help">
        <li><tt>moy</tt> la moyenne, calculée selon la règle standard (moyenne pondérée)</li>
        <li><tt>moy_is_valid</tt> vrai si la moyenne est valide (numérique)</li>
        <li><tt>moy_val</tt> la valeur de la moyenne (nombre, valant 0 si invalide)</li>
        <li><tt>notes</tt> vecteur des notes (/20) aux %(objs)s</li>
        <li><tt>coefs</tt> vecteur des coefficients des %(objs)s, les coefs des %(objs)s sans notes (ATT, EXC) étant mis à zéro</li>
        <li><tt>cmask</tt> vecteur de 0/1, 0 si le coef correspondant a été annulé</li>
        <li>Nombre d'absences: <tt>nb_abs</tt>, <tt>nb_abs_just</tt>, <tt>nb_abs_nojust</tt> (en demi-journées)</li>
        </ul>
        <p class="help">Les éléments des vecteurs sont ordonnés dans l'ordre des %(objs)s%(ordre)s.</p>
        <p class="help">Les fonctions suivantes sont utilisables: <tt>abs, cmp, dot, len, map, max, min, pow, reduce, round, sum, ifelse</tt></p>
        <p class="help">La notation <tt>V(1,2,3)</tt> représente un vecteur <tt>(1,2,3)</tt></p>
        <p class="help">Vous pouvez désactiver la formule (et revenir au mode de calcul "classique") 
        en supprimant le texte ou en faisant précéder la première ligne par <tt>#</tt></p>
    """

    security.declareProtected(ScoView, 'edit_moduleimpl_expr')
    def edit_moduleimpl_expr(self, REQUEST, moduleimpl_id):
        """Edition formule calcul moyenne module
        Accessible par Admin, dir des etud et responsable module
        """
        M, sem = self.can_change_ens(REQUEST, moduleimpl_id)
        H = [ 
            self.html_sem_header(
                REQUEST, 
                'Modification règle de calcul du <a href="moduleimpl_status?moduleimpl_id=%s">module %s</a>' 
                % (moduleimpl_id, M['module']['titre']), 
                sem
                ),
            self._expr_help % {'target':'du module', 'objs' : 'évaluations', 'ordre' : ' (le premier élément est la plus ancienne évaluation)'}
            ]
        initvalues = M
        form = [
            ('moduleimpl_id', { 'input_type' : 'hidden' }),
            ('computation_expr', { 'title' : 'Formule de calcul',
                                   'input_type' : 'textarea', 'rows' : 4, 'cols' : 60,
                                   'explanation' : 'formule de calcul (expérimental)' }),
            ]
        tf = TrivialFormulator( REQUEST.URL0, REQUEST.form, form,
                                submitlabel = 'Modifier formule de calcul',
                                cancelbutton = 'Annuler',
                                initvalues=initvalues)
        if tf[0] == 0:
            return '\n'.join(H) + tf[1] + self.sco_footer(REQUEST)
        elif tf[0] == -1:
            return REQUEST.RESPONSE.redirect('moduleimpl_status?moduleimpl_id='+moduleimpl_id)
        else:            
            self.do_moduleimpl_edit( { 'moduleimpl_id' : moduleimpl_id,
                                       'computation_expr' : tf[2]['computation_expr'] },
                                     formsemestre_id=sem['formsemestre_id'])
            self._inval_cache(formsemestre_id=sem['formsemestre_id']) #> modif regle calcul
            return REQUEST.RESPONSE.redirect('moduleimpl_status?moduleimpl_id='+moduleimpl_id+'&head_message=règle%20de%20calcul%20modifiée')
    
    
    security.declareProtected(ScoView, 'view_module_abs')
    def view_module_abs(self, REQUEST, moduleimpl_id, format='html'):
        """Visulalisation des absences a un module
        """
        M = self.do_moduleimpl_withmodule_list(args={ 'moduleimpl_id' : moduleimpl_id})[0]
        sem = self.get_formsemestre(M['formsemestre_id'])
        debut_sem = DateDMYtoISO(sem['date_debut'])
        fin_sem = DateDMYtoISO(sem['date_fin'])
        list_insc = self.do_moduleimpl_listeetuds(moduleimpl_id)
        
        T = []
        for etudid in list_insc:
            nb_abs = self.Absences.CountAbs(etudid=etudid, debut=debut_sem, fin=fin_sem, moduleimpl_id=moduleimpl_id)
            if nb_abs:
                nb_abs_just = self.Absences.CountAbsJust(etudid=etudid, debut=debut_sem, fin=fin_sem, moduleimpl_id=moduleimpl_id)
                etud = self.getEtudInfo(etudid=etudid, filled=True)[0]
                T.append({
                    'nomprenom' : etud['nomprenom'],
                    'just' : nb_abs_just,
                    'nojust' : nb_abs-nb_abs_just,
                    'total' : nb_abs,
                    '_nomprenom_target' : 'ficheEtud?etudid=%s' % etudid
                    })
        
        H = [ 
            self.html_sem_header(
                REQUEST, 
                'Absences du <a href="moduleimpl_status?moduleimpl_id=%s">module %s</a>' 
                % (moduleimpl_id, M['module']['titre']),
                page_title = 'Absences du module %s' % (M['module']['titre']),
                sem=sem
                ),
            ]
        if not T:
            return '\n'.join(H) + '<p>Aucune absence signalée</p>' + self.sco_footer(REQUEST)
        
        tab = GenTable( titles={ 'nomprenom' : 'Nom',
                                 'just' : 'Just.',
                                 'nojust' : 'Non Just.',
                                 'total' : 'Total' },
                        columns_ids=('nomprenom', 'just', 'nojust', 'total'),
                        rows = T,
                        html_class='gt_table table_leftalign',
                        base_url = '%s?moduleimpl_id=%s' % (REQUEST.URL0, moduleimpl_id),
                        filename='absmodule_'+make_filename(M['module']['titre']),
                        caption='Absences dans le module %s' % M['module']['titre'],
                        preferences=self.get_preferences())

        if format != 'html':
            return tab.make_page(self, format=format, REQUEST=REQUEST)
        
        return '\n'.join(H) + tab.html() + self.sco_footer(REQUEST)

    security.declareProtected(ScoView, 'edit_ue_expr')
    def edit_ue_expr(self, REQUEST, formsemestre_id, ue_id):
        """Edition formule calcul moyenne UE"""
        # Check access
        sem = sco_formsemestre_edit.can_edit_sem(self, REQUEST, formsemestre_id)
        if not sem:
            raise AccessDenied("vous n'avez pas le droit d'effectuer cette opération")
        cnx = self.GetDBConnexion()
        # 
        ue = self.do_ue_list( {'ue_id' : ue_id})[0]
        H = [ 
            self.html_sem_header(
                REQUEST, 
                "Modification règle de calcul de l'UE %s (%s)" % (ue['acronyme'], ue['titre']), 
                sem
                ),
            self._expr_help % {'target':"de l'UE", 'objs' : 'modules', 'ordre' : ''}
            ]
        el = sco_compute_moy.formsemestre_ue_computation_expr_list(cnx, {'formsemestre_id':formsemestre_id, 'ue_id':ue_id})
        if el:
            initvalues = el[0]
        else:
            initvalues = {}
        form = [
            ('ue_id', { 'input_type' : 'hidden' }),
            ('formsemestre_id', { 'input_type' : 'hidden' }),
            ('computation_expr', { 'title' : 'Formule de calcul',
                                   'input_type' : 'textarea', 'rows' : 4, 'cols' : 60,
                                   'explanation' : 'formule de calcul (expérimental)' }),
            ]
        tf = TrivialFormulator( REQUEST.URL0, REQUEST.form, form,
                                submitlabel = 'Modifier formule de calcul',
                                cancelbutton = 'Annuler',
                                initvalues=initvalues)
        if tf[0] == 0:
            return '\n'.join(H) + tf[1] + self.sco_footer(REQUEST)
        elif tf[0] == -1:
            return REQUEST.RESPONSE.redirect('formsemestre_status?formsemestre_id='+formsemestre_id)
        else:
            if el:
                el[0]['computation_expr'] = tf[2]['computation_expr']
                sco_compute_moy.formsemestre_ue_computation_expr_edit(cnx, el[0])
            else:
                sco_compute_moy.formsemestre_ue_computation_expr_create(cnx, tf[2])
            
            self._inval_cache(formsemestre_id=formsemestre_id) #> modif regle calcul
            return REQUEST.RESPONSE.redirect('formsemestre_status?formsemestre_id='+formsemestre_id+'&head_message=règle%20de%20calcul%20modifiée')

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
        cursor = cnx.cursor(cursor_factory=ScoDocCursor)
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
        title = 'Enseignants de ' + sem['titremois']
        T = GenTable( columns_ids=['nomprenom', 'descr_mods', 'nbabsadded'],
                      titles={'nomprenom' : 'Enseignant', 'descr_mods': 'Modules',
                              'nbabsadded' : 'Saisies Abs.' },
                      rows=sem_ens_list, html_sortable=True,
                      filename = make_filename('Enseignants-' + sem['titreannee']),
                      html_title=self.html_sem_header(REQUEST, 'Enseignants du semestre',
                                                      sem, with_page_header=False), 
                      base_url= '%s?formsemestre_id=%s' % (REQUEST.URL0, formsemestre_id),
                      caption="Tous les enseignants (responsables ou associés aux modules de ce semestre) apparaissent. Le nombre de saisies d'absences est le nombre d'opérations d'ajout effectuées sur ce semestre, sans tenir compte des annulations ou double saisies.",
                      preferences=self.get_preferences(formsemestre_id)
                      )
        return T.make_page(self, page_title=title, title=title, REQUEST=REQUEST, format=format)
    
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
    def can_change_ens(self, REQUEST, moduleimpl_id, raise_exc=True):
        "check if current user can modify ens list (raise exception if not)"
        M = self.do_moduleimpl_withmodule_list(args={ 'moduleimpl_id' : moduleimpl_id})[0]
        # -- check lock
        sem = self.get_formsemestre(M['formsemestre_id'])
        if sem['etat'] != '1':
            if raise_exc:
                raise ScoValueError('Modification impossible: semestre verrouille')
            else:
                return False
        # -- check access
        authuser = REQUEST.AUTHENTICATED_USER
        uid = str(authuser)
        # admin, resp. module ou resp. semestre
        if (uid != M['responsable_id']
            and not authuser.has_permission(ScoImplement, self)
            and uid != sem['responsable_id']):
            if raise_exc:
                raise AccessDenied('Modification impossible pour %s' % uid)
            else:
                return False
        return M, sem

    security.declareProtected(ScoView,'can_change_module_resp')
    def can_change_module_resp(self, REQUEST, moduleimpl_id):
        """Check if current user can modify module resp. (raise exception if not).
        = Admin, et dir des etud. (si option l'y autorise)
        """
        M = self.do_moduleimpl_withmodule_list(args={ 'moduleimpl_id' : moduleimpl_id})[0]
        # -- check lock
        sem = self.get_formsemestre(M['formsemestre_id'])
        if sem['etat'] != '1':
            raise ScoValueError('Modification impossible: semestre verrouille')
        # -- check access
        authuser = REQUEST.AUTHENTICATED_USER
        uid = str(authuser)
        # admin ou resp. semestre avec flag resp_can_change_resp
        if (not authuser.has_permission(ScoImplement, self)
            and ((uid != sem['responsable_id'])
                 or (not sem['resp_can_change_ens']))):
                raise AccessDenied('Modification impossible pour %s' % uid)
        return M, sem
        
    # --- Gestion des inscriptions aux modules
    _formsemestre_inscriptionEditor = EditableTable(
        'notes_formsemestre_inscription',
        'formsemestre_inscription_id',
        ('formsemestre_inscription_id', 'etudid', 'formsemestre_id',
         'etat'),
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
              etudid=args['etudid'], msg='inscription en semestre %s' % args['formsemestre_id'],
              commit=False )
        #
        self._inval_cache(formsemestre_id=args['formsemestre_id']) #> inscription au semestre
        return r

    security.declareProtected(ScoImplement, 'do_formsemestre_inscription_delete')
    def do_formsemestre_inscription_delete(self, oid, formsemestre_id=None):
        "delete formsemestre_inscription"
        cnx = self.GetDBConnexion()
        self._formsemestre_inscriptionEditor.delete(cnx, oid)
        
        self._inval_cache(formsemestre_id=formsemestre_id) #> desinscription du semestre

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
    def do_formsemestre_inscription_edit(self, args=None, formsemestre_id=None):
        "edit a formsemestre_inscription"
        cnx = self.GetDBConnexion()
        self._formsemestre_inscriptionEditor.edit(cnx, args)
        self._inval_cache(formsemestre_id=formsemestre_id) #> modif inscription semestre (demission ?)
    
    # Cache inscriptions semestres
    def get_formsemestre_inscription_cache(self):
        u = self.GetDBConnexionString()
        if CACHE_formsemestre_inscription.has_key(u):
            return CACHE_formsemestre_inscription[u]
        else:
            log('get_formsemestre_inscription_cache: new simpleCache')
            CACHE_formsemestre_inscription[u] = sco_cache.simpleCache()
            return CACHE_formsemestre_inscription[u]


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

        self.do_formsemestre_desinscription(etudid, formsemestre_id, REQUEST=REQUEST)
        
        return self.sco_header(REQUEST) + '<p>Etudiant désinscrit !</p><p><a class="stdlink" href="%s/ficheEtud?etudid=%s">retour à la fiche</a>'%(self.ScoURL(),etudid) + self.sco_footer(REQUEST)


    def do_formsemestre_desinscription(self, etudid, formsemestre_id, REQUEST=None):
        "Deinscription d'un étudiant"
        sem = self.get_formsemestre(formsemestre_id)
        # -- check lock
        if sem['etat'] != '1':
            raise ScoValueError('desinscription impossible: semestre verrouille')
        insem = self.do_formsemestre_inscription_list(
            args={ 'formsemestre_id' : formsemestre_id, 'etudid' : etudid } )
        if not insem:
            raise ScoValueError("%s n'est pas inscrit au semestre !" % etudid)
        insem = insem[0]
        # -- desinscription de tous les modules
        cnx = self.GetDBConnexion()
        cursor = cnx.cursor(cursor_factory=ScoDocCursor)
        cursor.execute( "select moduleimpl_inscription_id from notes_moduleimpl_inscription Im, notes_moduleimpl M  where Im.etudid=%(etudid)s and Im.moduleimpl_id = M.moduleimpl_id and M.formsemestre_id = %(formsemestre_id)s",
                        { 'etudid' : etudid, 'formsemestre_id' : formsemestre_id } )
        res = cursor.fetchall()
        moduleimpl_inscription_ids = [ x[0] for x in res ]
        for moduleimpl_inscription_id in moduleimpl_inscription_ids:
            self.do_moduleimpl_inscription_delete(moduleimpl_inscription_id, formsemestre_id=formsemestre_id)
        # -- desincription du semestre        
        self.do_formsemestre_inscription_delete( insem['formsemestre_inscription_id'], 
                                                 formsemestre_id=formsemestre_id )
        if REQUEST:
            logdb(REQUEST, cnx, method='formsemestre_desinscription',
                  etudid=etudid,
                  msg='desinscription semestre %s' % formsemestre_id,
                  commit=False )
    
    # --- Inscriptions aux modules
    _moduleimpl_inscriptionEditor = EditableTable(
        'notes_moduleimpl_inscription',
        'moduleimpl_inscription_id',
        ('moduleimpl_inscription_id', 'etudid', 'moduleimpl_id'),
        )

    security.declareProtected(ScoEtudInscrit,'do_moduleimpl_inscription_create')
    def do_moduleimpl_inscription_create(self, args, REQUEST=None, formsemestre_id=None):
        "create a moduleimpl_inscription"
        cnx = self.GetDBConnexion()
        log('do_moduleimpl_inscription_create: '+ str(args))
        r = self._moduleimpl_inscriptionEditor.create(cnx, args)
        self._inval_cache(formsemestre_id=formsemestre_id) #> moduleimpl_inscription 
        if REQUEST:
            logdb(REQUEST, cnx, method='moduleimpl_inscription',
                  etudid=args['etudid'],
                  msg='inscription module %s' % args['moduleimpl_id'],
                  commit=False )
        return r

    security.declareProtected(ScoImplement, 'do_moduleimpl_inscription_delete')
    def do_moduleimpl_inscription_delete(self, oid, formsemestre_id=None):
        "delete moduleimpl_inscription"
        cnx = self.GetDBConnexion()
        self._moduleimpl_inscriptionEditor.delete(cnx, oid)
        self._inval_cache(formsemestre_id=formsemestre_id) #> moduleimpl_inscription

    security.declareProtected(ScoView, 'do_moduleimpl_inscription_list')
    def do_moduleimpl_inscription_list(self, **kw ):
        "list moduleimpl_inscriptions"
        cnx = self.GetDBConnexion()
        return self._moduleimpl_inscriptionEditor.list(cnx, **kw)

    security.declareProtected(ScoView, 'do_moduleimpl_listeetuds')
    def do_moduleimpl_listeetuds(self, moduleimpl_id):
        "retourne liste des etudids inscrits a ce module"
        req = "select distinct Im.etudid from notes_moduleimpl_inscription Im, notes_formsemestre_inscription Isem, notes_moduleimpl M where Isem.etudid=Im.etudid and Im.moduleimpl_id=M.moduleimpl_id and M.moduleimpl_id = %(moduleimpl_id)s"
        cnx = self.GetDBConnexion()
        cursor = cnx.cursor(cursor_factory=ScoDocCursor)    
        cursor.execute( req, { 'moduleimpl_id' : moduleimpl_id } )
        res = cursor.fetchall()
        return [ x[0] for x in res ]

    security.declareProtected(ScoEtudInscrit,'do_moduleimpl_inscrit_tout_semestre')
    def do_moduleimpl_inscrit_tout_semestre(self,
                                            moduleimpl_id,formsemestre_id):
        "inscrit tous les etudiants inscrit au semestre a ce module"
        cnx = self.GetDBConnexion()
        cursor = cnx.cursor(cursor_factory=ScoDocCursor)
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
            cursor = cnx.cursor(cursor_factory=ScoDocCursor)
            cursor.execute( "delete from notes_moduleimpl_inscription where moduleimpl_id = %(moduleimpl_id)s", { 'moduleimpl_id' : moduleimpl_id })
        # Inscriptions au module:
        inmod_set = Set( [ x['etudid'] for x in self.do_moduleimpl_inscription_list( args={ 'moduleimpl_id' : moduleimpl_id } ) ])
        for etudid in etudids:
            # deja inscrit ?
            if not etudid in inmod_set:
                self.do_moduleimpl_inscription_create( { 'moduleimpl_id' :moduleimpl_id, 'etudid' :etudid }, REQUEST=REQUEST, formsemestre_id=formsemestre_id)
        
        self._inval_cache(formsemestre_id=formsemestre_id) #> moduleimpl_inscrit_etuds

    security.declareProtected(ScoEtudInscrit,'etud_desinscrit_ue')
    def etud_desinscrit_ue(self, etudid, formsemestre_id, ue_id, REQUEST=None):
        """Desinscrit l'etudiant de tous les modules de cette UE dans ce semestre.
        """
        sco_moduleimpl_inscriptions.do_etud_desinscrit_ue(self, etudid, formsemestre_id, ue_id, REQUEST=REQUEST)
        return REQUEST.RESPONSE.redirect( self.ScoURL()+'/Notes/moduleimpl_inscriptions_stats?formsemestre_id='+formsemestre_id)

    security.declareProtected(ScoEtudInscrit,'etud_inscrit_ue')
    def etud_inscrit_ue(self, etudid, formsemestre_id, ue_id, REQUEST=None):
        """Inscrit l'etudiant de tous les modules de cette UE dans ce semestre.
        """
        sco_moduleimpl_inscriptions.do_etud_inscrit_ue(self, etudid, formsemestre_id, ue_id, REQUEST=REQUEST)
        return REQUEST.RESPONSE.redirect( self.ScoURL()+'/Notes/moduleimpl_inscriptions_stats?formsemestre_id='+formsemestre_id)
    

    # --- Inscriptions
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
         'note_max', 'coefficient', 'visibulletin', 'publish_incomplete',
         'evaluation_type', 'numero' ),
         sortkey = 'numero desc, jour desc, heure_debut desc', # plus recente d'abord
         output_formators = { 'jour' : DateISOtoDMY,
                             'heure_debut' : TimefromISO8601,
                             'heure_fin'   : TimefromISO8601,
                             'visibulletin': str,
                             'publish_incomplete' : str,
                             # numero: int or None
                             },
        input_formators  = { 'jour' : DateDMYtoISO,
                             'heure_debut' : TimetoISO8601,
                             'heure_fin'   : TimetoISO8601,
                             'visibulletin': int,
                             'publish_incomplete' : int,
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
            if sem['ens_can_edit_eval']:
                for ens in M['ens']:
                    if ens['ens_id'] == uid:
                        return # ok
            raise AccessDenied('Modification évaluation impossible pour %s'%(uid,))
    
    security.declareProtected(ScoEnsView,'do_evaluation_create')
    def do_evaluation_create(self, REQUEST, args):
        """Create an evaluation
        """
        moduleimpl_id = args['moduleimpl_id']
        self._evaluation_check_write_access(REQUEST, moduleimpl_id=moduleimpl_id)
        self._check_evaluation_args(args)
        # Check numeros
        sco_evaluations.module_evaluation_renumber(
            self, moduleimpl_id, REQUEST=REQUEST, only_if_unumbered=True)
        if not 'numero' in args or args['numero'] is None:
            n = None
            # determine le numero avec la date
            # Liste des eval existantes triees par date, la plus ancienne en tete
            ModEvals = self.do_evaluation_list(
                args={ 'moduleimpl_id' : moduleimpl_id },
                sortkey='jour asc, heure_debut asc' )
            log('ModEvals=[%s]' % ','.join( [x['evaluation_id'] for x in ModEvals ]) )
            if args['jour']:
                next_eval = None
                t = (DateDMYtoISO(args['jour']),
                     TimetoISO8601( args['heure_debut']))
                log( 'args: t=%s' % str(t))
                for e in ModEvals:
                    if (DateDMYtoISO(e['jour']), TimetoISO8601(e['heure_debut'])) > t:
                        next_eval = e
                        break                
                if next_eval:
                    log('inserting !')
                    n = sco_evaluations.module_evaluation_insert_before(self, ModEvals, next_eval, REQUEST)
                else:
                    n = None # a placer en fin
            if n is None: # pas de date ou en fin:
                if ModEvals:
                    n = ModEvals[-1]['numero'] + 1
                else:
                    n = 0 # the only one
            log('creating with numero n=%d' % n)
            args['numero'] = n
                    
        #
        cnx = self.GetDBConnexion()
        r = self._evaluationEditor.create(cnx, args)
        
        # news
        M = self.do_moduleimpl_list( args={ 'moduleimpl_id':moduleimpl_id } )[0]
        mod = self.do_module_list( args={ 'module_id':M['module_id'] } )[0]
        mod['moduleimpl_id'] = M['moduleimpl_id']
        mod['url'] = "Notes/moduleimpl_status?moduleimpl_id=%(moduleimpl_id)s"%mod
        sco_news.add(self, REQUEST, typ=NEWS_NOTE, object=moduleimpl_id,
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
                raise ScoValueError("La date de l'évaluation (%s/%s/%s) n'est pas dans le semestre !" % (d,m,y))
        heure_debut = args.get('heure_debut', None)
        heure_fin = args.get('heure_fin', None)
        d = TimeDuration(heure_debut, heure_fin)
        if d and ((d < 0) or (d > 60*12)):
            raise ScoValueError("Heures de l'évaluation incohérentes !")            

    security.declareProtected(ScoEnsView, 'evaluation_delete')
    def evaluation_delete(self, REQUEST, evaluation_id):
        """Form delete evaluation"""
        El = self.do_evaluation_list( args={ 'evaluation_id' : evaluation_id } )
        if not El:
            raise ValueError('Evalution inexistante ! (%s)' % evaluation_id )
        E = El[0]
        M = self.do_moduleimpl_list( args={ 'moduleimpl_id' : E['moduleimpl_id'] } )[0]
        Mod = self.do_module_list( args={ 'module_id' : M['module_id'] } )[0]
        tit = "Suppression de l'évaluation %(description)s (%(jour)s)" % E
        etat = sco_evaluations.do_evaluation_etat(self, evaluation_id)
        H = [ self.html_sem_header( REQUEST, tit, with_h2=False ),
              """<h2 class="formsemestre">Module <tt>%(code)s</tt> %(titre)s</h2>""" % Mod,
              """<h3>%s</h3>""" % tit,
              """<p class="help">Opération <span class="redboldtext">irréversible</span>. Si vous supprimez l'évaluation, vous ne pourrez pas retrouver les notes associées.</p>"""
              ]
        warning = False
        if etat['nb_notes_total']:
            warning = True
            nb_desinscrits = etat['nb_notes_total'] - etat['nb_notes']
            H.append("""<div class="ue_warning"><span>Il y a %s notes""" % etat['nb_notes_total'])
            if nb_desinscrits:
                H.append(""" (dont %s d'étudiants qui ne sont plus inscrits)""" % nb_desinscrits)
            H.append(""" dans l'évaluation</span>""")
            if etat['nb_notes'] == 0:
                H.append("""<p>Vous pouvez quand même supprimer l'évaluation, les notes des étudiants désincrits seront effacées.</p>""")
        
        if etat['nb_notes']:
            H.append("""<p>Suppression impossible (effacer les notes d'abord)</p><p><a class="stdlink" href="moduleimpl_status?moduleimpl_id=%s">retour au tableau de bord du module</a></p></div>""" % E['moduleimpl_id'])
            return '\n'.join(H) + self.sco_footer(REQUEST)
        if warning:
            H.append("""</div>""" )

        tf = TrivialFormulator( REQUEST.URL0, REQUEST.form,
                                ( ('evaluation_id', { 'input_type' : 'hidden' }),
                                  ),
                                initvalues = E,
                                submitlabel = 'Confirmer la suppression',
                                cancelbutton = 'Annuler')
        if tf[0] == 0:
            return '\n'.join(H) + tf[1] + self.sco_footer(REQUEST)
        elif tf[0] == -1:
            return REQUEST.RESPONSE.redirect( self.ScoURL()+'/Notes/moduleimpl_status?moduleimpl_id='+E['moduleimpl_id'] )
        else:
            sco_evaluations.do_evaluation_delete(self, REQUEST, E['evaluation_id'])
            return '\n'.join(H) + """<p>OK, évaluation supprimée.</p>
            <p><a class="stdlink" href="%s">Continuer</a></p>""" % (self.ScoURL()+'/Notes/moduleimpl_status?moduleimpl_id='+E['moduleimpl_id']) + self.sco_footer(REQUEST)
        

    security.declareProtected(ScoView, 'do_evaluation_list')
    def do_evaluation_list(self, args, sortkey=None ):
        "List evaluations, sorted by numero (or most recent date first)."
        cnx = self.GetDBConnexion()
        evals = self._evaluationEditor.list(cnx, args, sortkey=sortkey)
        # calcule duree (chaine de car.) de chaque evaluation et ajoute jouriso
        for e in evals:
            e['jouriso'] = DateDMYtoISO(e['jour'])
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
        self._inval_cache(formsemestre_id=M['formsemestre_id']) #> evaluation_edit (coef, ...)

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
            link=''
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
                link=' &nbsp;<span class="evallink"><a class="stdlink" href="evaluation_listenotes?moduleimpl_id=%s">voir toutes les notes du module</a></span>'%M['moduleimpl_id']
            else:
                action = 'Modification d\'une é'
                link =''
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
        pédagogique (le PPN pour les DUT) et pondère les moyennes de chaque module pour obtenir
        les moyennes d'UE et la moyenne générale.
        </p><p class="help">
        L'option <em>Visible sur bulletins</em> indique que la note sera reportée sur les bulletins
        en version dite "intermédiaire" (dans cette version, on peut ne faire apparaitre que certaines
        notes, en sus des moyennes de modules. Attention, cette option n'empêche pas la publication sur
        les bulletins en version "longue" (la note est donc visible par les étudiants sur le portail).
        </p><p class="help">
        La modalité "rattrapage" permet de définir une évaluation dont les notes remplaceront les moyennes du modules
        si elles sont meilleures que celles calculées. Dans ce cas, le coefficient est ignoré, et toutes les notes n'ont
        pas besoin d'être rentrées.
        </p>
        """
        mod_descr = '<a href="moduleimpl_status?moduleimpl_id=%s">%s %s</a>%s' % (moduleimpl_id, Mod['code'], Mod['titre'], link)
        if not readonly:
            H = ['<h3>%svaluation en %s</h3>' % (action, mod_descr) ]
        else:
            E = initvalues
            H = [ '<h3>Evaluation "%s"</h3><p><b>Module : %s</b></p>' % (E['description'], mod_descr) ]
            # version affichage seule (générée ici pour etre plus jolie que le Formulator)
            jour = E['jour']
            if not jour:
                jour = '<em>pas de date</em>'
            H.append( '<p>Réalisée le <b>%s</b> de %s à %s '
                      % (jour,E['heure_debut'],E['heure_fin']) )
            if E['jour']:
                group_id = sco_groups.get_default_group(self, formsemestre_id)
                H.append('<span class="noprint"><a href="%s/Absences/EtatAbsencesDate?group_id=%s&date=%s">(absences ce jour)</a></span>' % (self.ScoURL(),group_id,urllib.quote(E['jour'],safe='') ))
            H.append( '</p><p>Coefficient dans le module: <b>%s</b> ' % E['coefficient'] )
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
            ('jour', { 'input_type' : 'date', 'title' : 'Date', 'size' : 12, 'explanation' : 'date de l\'examen, devoir ou contrôle' }),
            ('heure_debut'   , { 'title' : 'Heure de début', 'explanation' : 'heure du début de l\'épreuve',
                                 'input_type' : 'menu', 'allowed_values' : heures, 'labels' : heures }),
            ('heure_fin'   , { 'title' : 'Heure de fin', 'explanation' : 'heure de fin de l\'épreuve',
                               'input_type' : 'menu', 'allowed_values' : heures, 'labels' : heures }),
            ('coefficient'    , { 'size' : 10, 'type' : 'float', 'explanation' : 'coef. dans le module (choisi librement par l\'enseignant)', 'allow_null':False }),
        ('note_max'    , { 'size' : 3, 'type' : 'float', 'title' : 'Notes de 0 à', 'explanation' : 'barème', 'allow_null':False, 'max_value' : NOTES_MAX, 'min_value' : 1 }),

            ('description' , { 'size' : 36, 'type' : 'text', 'explanation' : 'type d\'évaluation, apparait sur le bulletins longs. Exemples: "contrôle court", "examen de TP", "examen final".' }),    
            ('visibulletinlist', { 'input_type' : 'checkbox',
                                   'allowed_values' : ['X'], 'labels' : [ '' ],
                                   'title' : 'Visible sur bulletins' ,
                                   'explanation' : '(pour les bulletins en version intermédiaire)'}),
            ('publish_incomplete', { 'input_type' : 'boolcheckbox',
                                     'title' : 'Prise en compte immédiate' ,
                                     'explanation' : 'notes utilisées même si incomplètes'}),
            ('evaluation_type', { 'input_type' : 'menu',
                                  'title' : 'Modalité',
                                  'allowed_values' : (EVALUATION_NORMALE, EVALUATION_RATTRAPAGE),
                                  'type' : 'int',
                                  'labels' : ('Normale', 'Rattrapage') }),
            ), 
                                cancelbutton = 'Annuler',
                                submitlabel = submitlabel,
                                initvalues = initvalues, readonly=readonly)

        dest_url = 'moduleimpl_status?moduleimpl_id=%s' % M['moduleimpl_id']
        if  tf[0] == 0:
            return self.sco_header(REQUEST, init_jquery_ui=True) + '\n'.join(H) + '\n' + tf[1] + help + self.sco_footer(REQUEST)
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
        
    security.declareProtected(ScoView, 'evaluation_listenotes')
    def evaluation_listenotes(self, REQUEST=None ):
        """Affichage des notes d'une évaluation"""
        if REQUEST.form.get('format','html')=='html':
            H = self.sco_header(REQUEST, cssstyles=['verticalhisto.css']) 
            F = self.sco_footer(REQUEST)
        else:
            H, F = '', ''
        B = self.do_evaluation_listenotes(REQUEST)
        return H + B + F

    security.declareProtected(ScoView, 'do_evaluation_listenotes')
    do_evaluation_listenotes = sco_liste_notes.do_evaluation_listenotes

    security.declareProtected(ScoView, 'evaluation_list_operations')
    evaluation_list_operations = sco_undo_notes.evaluation_list_operations

    security.declareProtected(ScoView, 'evaluation_check_absences_html')
    evaluation_check_absences_html = sco_liste_notes.evaluation_check_absences_html

    security.declareProtected(ScoView, 'formsemestre_check_absences_html')
    formsemestre_check_absences_html = sco_liste_notes.formsemestre_check_absences_html

    # --- Saisie des notes    
    security.declareProtected(ScoEnsView, 'notes_eval_selectetuds')
    notes_eval_selectetuds = sco_saisie_notes.notes_eval_selectetuds
    
    security.declareProtected(ScoEnsView, 'notes_evaluation_formnotes')
    notes_evaluation_formnotes = sco_saisie_notes.evaluation_formnotes
    
    # now unused:
    #security.declareProtected(ScoEnsView, 'do_evaluation_upload_csv')
    #do_evaluation_upload_csv = sco_saisie_notes.do_evaluation_upload_csv
    
    security.declareProtected(ScoEnsView, 'do_evaluation_set_missing')
    do_evaluation_set_missing = sco_saisie_notes.do_evaluation_set_missing

    security.declareProtected(ScoView, 'evaluation_suppress_alln')
    evaluation_suppress_alln = sco_saisie_notes.evaluation_suppress_alln

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

    security.declareProtected(ScoEtudSupprAnnotations, 'dummy_ScoEtudSupprAnnotations')
    def dummy_ScoEtudSupprAnnotations(self):
        "dummy method, necessary to declare permission ScoEtudSupprAnnotations"
        return True

    # cache notes evaluations
    def get_evaluations_cache(self):
        u = self.GetDBConnexionString()
        if CACHE_evaluations.has_key(u):
            return CACHE_evaluations[u]
        else:
            log('get_evaluations_cache: new simpleCache')
            CACHE_evaluations[u] = sco_cache.simpleCache()
            return CACHE_evaluations[u]

    def _notes_getall(self, evaluation_id, table='notes_notes', filter_suppressed=True):
        """get tt les notes pour une evaluation: { etudid : { 'value' : value, 'date' : date ... }}
        Attention: inclue aussi les notes des étudiants qui ne sont plus inscrits au module.
        """
        #log('_notes_getall( e=%s fs=%s )' % (evaluation_id, filter_suppressed))
        do_cache = filter_suppressed and table=='notes_notes' # pas de cache pour (rares) appels via undo_notes
        if do_cache:
            cache = self.get_evaluations_cache()
            r = cache.get(evaluation_id)
            if r != None:
                return r
        cnx = self.GetDBConnexion()
        cursor = cnx.cursor(cursor_factory=ScoDocCursor)
        cursor.execute("select * from " + table + " where evaluation_id=%(evaluation_id)s",
                       { 'evaluation_id' : evaluation_id } )
        res = cursor.dictfetchall()
        d = {}
        if filter_suppressed:
            for x in res:
                if x['value'] != NOTES_SUPPRESS:
                    d[x['etudid']] = x
        else:
            for x in res:
                d[x['etudid']] = x
        if do_cache:
            cache.set(evaluation_id,d)
        return d

    # --- Bulletins        
    security.declareProtected(ScoView, 'formsemestre_bulletins_pdf')
    def formsemestre_bulletins_pdf(self, formsemestre_id, REQUEST,
                                   version='selectedevals'):
        "Publie les bulletins dans un classeur PDF"
        pdfdoc, filename = self._get_formsemestre_bulletins_pdf(
            formsemestre_id, REQUEST, version=version)
        return sendPDFFile(REQUEST, pdfdoc, filename)

    security.declareProtected(ScoView, 'formsemestre_bulletins_pdf_choice')
    formsemestre_bulletins_pdf_choice = sco_bulletins.formsemestre_bulletins_pdf_choice

    security.declareProtected(ScoView, 'formsemestre_bulletins_mailetuds_choice')
    formsemestre_bulletins_mailetuds_choice = sco_bulletins.formsemestre_bulletins_mailetuds_choice

    def _get_formsemestre_bulletins_pdf(self, formsemestre_id, REQUEST,
                                   version='selectedevals'):
        cached = self._getNotesCache().get_bulletins_pdf(formsemestre_id,version)
        if cached:
            return cached[1], cached[0]
        fragments = []
        sem = self.get_formsemestre(formsemestre_id)
        # Make each bulletin
        nt = self._getNotesCache().get_NotesTable(self, formsemestre_id) #> get_etudids, get_sexnom
        bookmarks = {}
        filigrannes = {}
        i = 1
        for etudid in nt.get_etudids():
            frag, filigranne = sco_bulletins.do_formsemestre_bulletinetud(
                self, formsemestre_id, etudid, format='pdfpart',
                version=version, 
                REQUEST=REQUEST )
            fragments += frag
            filigrannes[i] = filigranne
            bookmarks[i] = nt.get_sexnom(etudid)
            i = i + 1
        #
        infos = { 'DeptName' : self.get_preference('DeptName',formsemestre_id) }
        if REQUEST:
            server_name = REQUEST.BASE0
        else:
            server_name = ''
        try:
            PDFLOCK.acquire()
            pdfdoc = sco_bulletins_pdf.pdfassemblebulletins(
                formsemestre_id,
                fragments, sem, infos, bookmarks,
                filigranne=filigrannes,
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
        return pdfdoc, filename

    security.declareProtected(ScoView, 'formsemestre_bulletins_mailetuds')
    def formsemestre_bulletins_mailetuds(self, formsemestre_id, REQUEST,
                                         version='long',
                                         dialog_confirmed=False ):
        "envoi a chaque etudiant (inscrit et ayant un mail) son bulletin"
        sem = self.get_formsemestre(formsemestre_id)
        nt = self._getNotesCache().get_NotesTable(self, formsemestre_id) #> get_etudids
        etudids = nt.get_etudids()
        #
        ok, err = self._check_access_diretud(formsemestre_id,REQUEST,required_permission=ScoEtudChangeAdr)
        if not ok:
            return err
        # Confirmation dialog
        if not dialog_confirmed:
            return self.confirmDialog(
                "<h2>Envoyer les %d bulletins par e-mail aux étudiants ?" % len(etudids),
                dest_url="", REQUEST=REQUEST,
                cancel_url="formsemestre_status?formsemestre_id=%s" % formsemestre_id,
                parameters={'version':version, 'formsemestre_id' : formsemestre_id})
                                      
        # Make each bulletin
        for etudid in etudids:
            sco_bulletins.do_formsemestre_bulletinetud(
                self, formsemestre_id, etudid,
                version=version, 
                format = 'pdfmail', nohtml=True, REQUEST=REQUEST )
        #
        return self.sco_header(REQUEST) + '<p>%d bulletins envoyés par mail !</p><p><a class="stdlink" href="formsemestre_status?formsemestre_id=%s">continuer</a></p>' % (len(etudids),formsemestre_id) + self.sco_footer(REQUEST)

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
            self._inval_cache(pdfonly=True, formsemestre_id=formsemestre_id) #> appreciation_add
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
        if authuser.has_permission(ScoImplement, self):
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

    security.declareProtected(ScoView, 'formsemestre_validate_previous_ue')
    def formsemestre_validate_previous_ue(self, formsemestre_id, etudid=None, REQUEST=None):
        "Form. saisie UE validée hors ScoDoc "
        if not self.can_validate_sem(REQUEST, formsemestre_id):
            return self.confirmDialog(
                message='<p>Opération non autorisée pour %s</h2>' % REQUEST.AUTHENTICATED_USER,
                dest_url=self.ScoURL(), REQUEST=REQUEST)
        return sco_formsemestre_validation.formsemestre_validate_previous_ue(self, formsemestre_id, etudid, REQUEST=REQUEST)
    
    security.declareProtected(ScoView, 'get_etud_ue_cap_html')
    get_etud_ue_cap_html = sco_formsemestre_validation.get_etud_ue_cap_html

    security.declareProtected(ScoView, 'etud_ue_suppress_validation')
    def etud_ue_suppress_validation(self,  etudid, formsemestre_id, ue_id, REQUEST=None):
        """Suppress a validation (ue_id, etudid) and redirect to formsemestre"""
        if not self.can_validate_sem(REQUEST, formsemestre_id):
            return self.confirmDialog(
                message='<p>Opération non autorisée pour %s</h2>' % REQUEST.AUTHENTICATED_USER,
                dest_url=self.ScoURL(), REQUEST=REQUEST)
        return sco_formsemestre_validation.etud_ue_suppress_validation(self, etudid, formsemestre_id, ue_id, REQUEST=REQUEST)
    
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
    security.declareProtected(ScoView, 'formsemestre_validation_suppress_etud')
    def formsemestre_validation_suppress_etud(self, formsemestre_id, etudid, REQUEST=None, dialog_confirmed=False):
        """Suppression des decisions de jury pour un etudiant.
        """
        if not self.can_validate_sem(REQUEST, formsemestre_id):
            return self.confirmDialog(
                message='<p>Opération non autorisée pour %s</h2>' % REQUEST.AUTHENTICATED_USER,
                dest_url=self.ScoURL(), REQUEST=REQUEST)
        if not dialog_confirmed:
            sem = self.get_formsemestre(formsemestre_id)
            etud = self.getEtudInfo(etudid=etudid,filled=1)[0]
            nt = self._getNotesCache().get_NotesTable(self, formsemestre_id) #> get_etud_decision_sem
            decision_jury = nt.get_etud_decision_sem(etudid)
            if decision_jury:
                existing = '<p>Décision existante: %(code)s du %(event_date)s</p>' % decision_jury
            else:
                existing = ''
            return self.confirmDialog(
                """<h2>Confirmer la suppression des décisions du semestre %s (%s - %s) pour %s ?</h2>%s
                <p>Cette opération est irréversible.
                </p>
                """ % (sem['titre_num'],sem['date_debut'],sem['date_fin'], etud['nomprenom'],existing),
                OK = "Supprimer", 
                dest_url="", REQUEST=REQUEST,
                cancel_url="formsemestre_validation_etud_form?formsemestre_id=%s&etudid=%s" % (formsemestre_id, etudid),
                parameters={'etudid':etudid, 'formsemestre_id' : formsemestre_id})
        
        sco_formsemestre_validation.formsemestre_validation_suppress_etud(self, formsemestre_id, etudid)
        return REQUEST.RESPONSE.redirect( self.ScoURL()+'/Notes/formsemestre_validation_etud_form?formsemestre_id=%s&etudid=%s&head_message=Décision%%20supprimée' % (formsemestre_id,etudid))
    
    # ------------- PV de JURY et archives
    security.declareProtected(ScoView, 'formsemestre_pvjury')
    formsemestre_pvjury = sco_pvjury.formsemestre_pvjury
    
    security.declareProtected(ScoView, 'formsemestre_lettres_individuelles')
    formsemestre_lettres_individuelles = sco_pvjury.formsemestre_lettres_individuelles        
    security.declareProtected(ScoView, 'formsemestre_pvjury_pdf')
    formsemestre_pvjury_pdf = sco_pvjury.formsemestre_pvjury_pdf
        
    security.declareProtected(ScoView,'feuille_preparation_jury')
    feuille_preparation_jury = sco_prepajury.feuille_preparation_jury

    security.declareProtected(ScoImplement, 'formsemestre_archive')
    formsemestre_archive = sco_archives.formsemestre_archive

    security.declareProtected(ScoImplement, 'formsemestre_delete_archive')
    formsemestre_delete_archive = sco_archives.formsemestre_delete_archive
    
    security.declareProtected(ScoView, 'formsemestre_list_archives')
    formsemestre_list_archives = sco_archives.formsemestre_list_archives
    
    security.declareProtected(ScoView, 'formsemestre_get_archived_file')
    formsemestre_get_archived_file = sco_archives.formsemestre_get_archived_file
        
    # ------------- INSCRIPTIONS: PASSAGE D'UN SEMESTRE A UN AUTRE
    security.declareProtected(ScoEtudInscrit,'formsemestre_inscr_passage')
    formsemestre_inscr_passage = sco_inscr_passage.formsemestre_inscr_passage

    security.declareProtected(ScoEtudInscrit,'formsemestre_synchro_etuds')
    formsemestre_synchro_etuds = sco_synchro_etuds.formsemestre_synchro_etuds

    # ------------- RAPPORTS STATISTIQUES
    security.declareProtected(ScoView, "formsemestre_report_counts")
    formsemestre_report_counts = sco_report.formsemestre_report_counts

    security.declareProtected(ScoView, "formsemestre_suivi_cohorte")
    formsemestre_suivi_cohorte = sco_report.formsemestre_suivi_cohorte

    security.declareProtected(ScoView, "formsemestre_suivi_parcours")
    formsemestre_suivi_parcours = sco_report.formsemestre_suivi_parcours

    security.declareProtected(ScoView, "formsemestre_etuds_lycees")
    formsemestre_etuds_lycees = sco_lycee.formsemestre_etuds_lycees

    security.declareProtected(ScoView, "scodoc_table_etuds_lycees")
    scodoc_table_etuds_lycees = sco_lycee.scodoc_table_etuds_lycees

    security.declareProtected(ScoView, "formsemestre_graph_parcours")
    formsemestre_graph_parcours = sco_report.formsemestre_graph_parcours

    security.declareProtected(ScoView, "formsemestre_poursuite_report")
    formsemestre_poursuite_report = sco_poursuite_dut.formsemestre_poursuite_report

    security.declareProtected(ScoView, "report_debouche_date")
    report_debouche_date = sco_debouche.report_debouche_date
    
    security.declareProtected(ScoView, "formsemestre_estim_cost")
    formsemestre_estim_cost = sco_cost_formation.formsemestre_estim_cost
    
    # --------------------------------------------------------------------
    # DEBUG
    security.declareProtected(ScoView,'check_sem_integrity')
    def check_sem_integrity(self, formsemestre_id, REQUEST):
        """Debug.
        Check that ue and module formations are consistents
        """
        sem = self.get_formsemestre(formsemestre_id)

        modimpls = self.do_moduleimpl_list( {'formsemestre_id':formsemestre_id} )
        bad_ue = []
        bad_sem = []
        for modimpl in modimpls:
            mod = self.do_module_list( {'module_id': modimpl['module_id'] } )[0]
            ue = self.do_ue_list( {'ue_id' : mod['ue_id']})[0]
            if ue['formation_id'] != mod['formation_id']:
                modimpl['mod'] = mod
                modimpl['ue'] = ue                
                bad_ue.append(modimpl)  
            if sem['formation_id'] !=  mod['formation_id']:
                bad_sem.append(modimpl)
                modimpl['mod'] = mod
                
        return self.sco_header(REQUEST=REQUEST)+ '<p>formation_id=%s' % sem['formation_id'] + '<h2>Inconsistent UE/MOD:</h2>'+'<br/>'.join([str(x) for x in bad_ue])+ '<h2>Inconsistent SEM/MOD:</h2>'+'<br/>'.join([str(x) for x in bad_sem])+self.sco_footer(REQUEST)

    security.declareProtected(ScoView,'check_form_integrity')
    def check_form_integrity(self, formation_id, fix=False, REQUEST=None):
        "debug"
        log("check_form_integrity: formation_id=%s  fix=%s" % (formation_id, fix))
        F = self.formation_list( args={ 'formation_id' : formation_id } )[0]
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
        for F in self.formation_list():
            self.check_form_integrity(F['formation_id'], REQUEST=REQUEST)
        # semestres
        for sem in self.do_formsemestre_list():
            self.check_formsemestre_integrity(sem['formsemestre_id'], REQUEST=REQUEST)
        return self.sco_header(REQUEST=REQUEST)+'<p>empty page: see logs and mails</p>'+self.sco_footer(REQUEST)
    
    # --------------------------------------------------------------------

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


    

