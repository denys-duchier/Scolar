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

"""Interface Zope <-> Notes
"""
import urllib, time, datetime

from email.MIMEMultipart import MIMEMultipart
from email.MIMEText import MIMEText
from email.MIMEBase import MIMEBase
from email.Header import Header
from email import Encoders

# XML generation package (apt-get install jaxml)
import jaxml

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
from notes_log import log
from scolog import logdb
from sco_exceptions import *
from sco_utils import *
import sco_excel
#import notes_users
from ScolarRolesNames import *
from TrivialFormulator import TrivialFormulator, TF
import scolars
import pdfbulletins
from notes_table import *


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
        # Create a cache
        self.CachedNotesTable = CacheNotesTable()
        
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

    security.declareProtected('ScoView', 'clearcache')
    def clearcache(self):
        "efface les caches de notes (utile pendant developpement slt)"
        log('*** clearcache request')
        self.CachedNotesTable.inval_cache()

    # --------------------------------------------------------------------
    #
    #    NOTES (top level)
    #
    # --------------------------------------------------------------------
    # used to view content of the object
    security.declareProtected('ScoView', 'index_html')
    index_html = DTMLFile('dtml/notes/index_html', globals())

    # XXX essai
    security.declareProtected('ScoView', 'essai')
    def gloups(self, REQUEST): 
        "essai gloups"
        #return 'gloups gloups' + self.essai()
        return pdfbulletins.essaipdf(REQUEST)

    # DTML METHODS
    security.declareProtected(ScoView, 'formsemestre_status_head')
    formsemestre_status_head = DTMLFile('dtml/notes/formsemestre_status_head', globals())
    security.declareProtected(ScoView, 'formsemestre_status')
    formsemestre_status = DTMLFile('dtml/notes/formsemestre_status', globals())

    security.declareProtected(ScoEnsView, 'evaluation_delete')
    evaluation_delete = DTMLFile('dtml/notes/evaluation_delete', globals())

    security.declareProtected(ScoAdministrate, 'formation_create')
    formation_create = DTMLFile('dtml/notes/formation_create', globals())
    security.declareProtected(ScoAdministrate, 'formation_delete')
    formation_delete = DTMLFile('dtml/notes/formation_delete', globals())
    security.declareProtected(ScoAdministrate, 'formation_edit')
    formation_edit = DTMLFile('dtml/notes/formation_edit', globals())
    security.declareProtected(ScoView, 'formation_list')
    formation_list = DTMLFile('dtml/notes/formation_list', globals())

    security.declareProtected(ScoView, 'formsemestre_bulletinetud')
    formsemestre_bulletinetud = DTMLFile('dtml/notes/formsemestre_bulletinetud', globals())
    security.declareProtected(ScoImplement, 'formsemestre_createwithmodules')
    formsemestre_createwithmodules = DTMLFile('dtml/notes/formsemestre_createwithmodules', globals(), title='Création d\'un semestre (ou session) de formation avec ses modules')
    security.declareProtected(ScoImplement, 'formsemestre_editwithmodules')
    formsemestre_editwithmodules = DTMLFile('dtml/notes/formsemestre_editwithmodules', globals(), title='Modification d\'un semestre (ou session) de formation avec ses modules' )
    security.declareProtected(ScoImplement, 'formsemestre_delete')
    formsemestre_delete = DTMLFile('dtml/notes/formsemestre_delete', globals(), title='Suppression d\'un semestre (ou session) de formation avec ses modules' )
    security.declareProtected(ScoView, 'formsemestre_recapcomplet')
    formsemestre_recapcomplet = DTMLFile('dtml/notes/formsemestre_recapcomplet', globals(), title='Tableau de toutes les moyennes du semestre')

    security.declareProtected(ScoAdministrate, 'ue_create')
    ue_create = DTMLFile('dtml/notes/ue_create', globals(), title='Création d\'une UE')
    security.declareProtected(ScoAdministrate, 'ue_delete')
    ue_delete = DTMLFile('dtml/notes/ue_delete', globals(), title='Suppression d\'une UE')
    security.declareProtected(ScoAdministrate, 'ue_edit')
    ue_edit = DTMLFile('dtml/notes/ue_edit', globals(), title='Modification d\'une UE')
    security.declareProtected(ScoView, 'ue_list')
    ue_list = DTMLFile('dtml/notes/ue_list', globals(), title='Liste des matières (dans une formation)')

    security.declareProtected(ScoAdministrate, 'matiere_create')
    matiere_create = DTMLFile('dtml/notes/matiere_create', globals(), title='Création d\'une matière')
    security.declareProtected(ScoAdministrate, 'matiere_delete')
    matiere_delete = DTMLFile('dtml/notes/matiere_delete', globals(), title='Suppression d\'une matière')
    security.declareProtected(ScoAdministrate, 'matiere_edit')
    matiere_edit = DTMLFile('dtml/notes/matiere_edit', globals(), title='Modification d\'une matière')
    security.declareProtected(ScoView, 'matiere_list')
    matiere_list = DTMLFile('dtml/notes/matiere_list', globals(), title='Liste des matières (dans une UE)')

    security.declareProtected(ScoAdministrate, 'module_create')
    module_create = DTMLFile('dtml/notes/module_create', globals(), title='Création d\'une module')
    security.declareProtected(ScoAdministrate, 'module_delete')
    module_delete = DTMLFile('dtml/notes/module_delete', globals(), title='Suppression d\'une module')
    security.declareProtected(ScoAdministrate, 'module_edit')
    module_edit = DTMLFile('dtml/notes/module_edit', globals(), title='Modification d\'un module')
    security.declareProtected(ScoView, 'module_list')
    module_list = DTMLFile('dtml/notes/module_list', globals(), title='Liste des modules (dans une formation)')
    
    security.declareProtected(ScoView,'moduleimpl_status')
    moduleimpl_status = DTMLFile('dtml/notes/moduleimpl_status', globals(), title='Tableau de bord module')

    security.declareProtected(ScoEnsView, 'notes_eval_selectetuds')
    notes_eval_selectetuds = DTMLFile('dtml/notes/notes_eval_selectetuds', globals(), title='Choix groupe avant saisie notes')
    security.declareProtected(ScoEnsView, 'notes_evaluation_formnotes')
    notes_evaluation_formnotes = DTMLFile('dtml/notes/notes_evaluation_formnotes', globals(), title='Saisie des notes')

    # --------------------------------------------------------------------
    #
    #    Notes Methods
    #
    # --------------------------------------------------------------------

    # --- Formations
    _formationEditor = EditableTable(
        'notes_formations',
        'formation_id',
        ('formation_id', 'acronyme','titre'),
        )

    security.declareProtected(ScoAdministrate, 'do_formation_create')
    def do_formation_create(self, args):
        "create a formation"
        cnx = self.GetDBConnexion()
        r = self._formationEditor.create(cnx, args)
        self.CachedNotesTable.inval_cache()
        return r 
    
    security.declareProtected(ScoAdministrate, 'do_formation_delete')
    def do_formation_delete(self, oid):
        "delete a formation (and all its UE, matiers, modules)"
        cnx = self.GetDBConnexion()
        # delete all UE in this formation
        ues = self.do_ue_list({ 'formation_id' : oid })
        for ue in ues:
            self.do_ue_delete(ue['ue_id'])
        
        self._formationEditor.delete(cnx, oid)
        self.CachedNotesTable.inval_cache()

    security.declareProtected(ScoView, 'do_formation_list')
    def do_formation_list(self, **kw ):
        "list formations"
        cnx = self.GetDBConnexion()        
        return self._formationEditor.list( cnx, **kw )

    security.declareProtected(ScoAdministrate, 'do_formation_edit')
    def do_formation_edit(self, *args, **kw ):
        "edit a formation"
        cnx = self.GetDBConnexion()
        self._formationEditor.edit( cnx, *args, **kw )
        self.CachedNotesTable.inval_cache()

    # --- UE
    _ueEditor = EditableTable(
        'notes_ue',
        'ue_id',
        ('ue_id', 'formation_id', 'acronyme', 'numero', 'titre', 'type'),
        sortkey='numero',
        input_formators = { 'type' : int_null_is_zero },
        output_formators = { 'numero' : int_null_is_zero },
        )

    security.declareProtected(ScoAdministrate, 'do_ue_create')
    def do_ue_create(self, args):
        "create an ue"
        cnx = self.GetDBConnexion()
        r = self._ueEditor.create(cnx, args)
        self.CachedNotesTable.inval_cache()
        return r

    security.declareProtected(ScoAdministrate, 'do_ue_delete')
    def do_ue_delete(self, oid):
        "delete UE and attached matieres"
        cnx = self.GetDBConnexion()
        # delete all matiere in this UE
        mats = self.do_matiere_list({ 'ue_id' : oid })
        for mat in mats:
            self.do_matiere_delete(mat['matiere_id'])
        
        self._ueEditor.delete(cnx, oid)
        self.CachedNotesTable.inval_cache()

    security.declareProtected(ScoView, 'do_ue_list')
    def do_ue_list(self, *args, **kw ):
        "list UEs"
        cnx = self.GetDBConnexion()
        return self._ueEditor.list(cnx, *args, **kw)

    security.declareProtected(ScoAdministrate, 'do_ue_edit')
    def do_ue_edit(self, *args, **kw ):
        "edit an UE"
        cnx = self.GetDBConnexion()
        self._ueEditor.edit( cnx, *args, **kw )
        self.CachedNotesTable.inval_cache()

    # --- Matieres
    _matiereEditor = EditableTable(
        'notes_matieres',
        'matiere_id',
        ('matiere_id', 'ue_id', 'numero', 'titre'),
        sortkey='numero',
        output_formators = { 'numero' : int_null_is_zero },
        )

    security.declareProtected(ScoAdministrate, 'do_matiere_create')
    def do_matiere_create(self, args):
        "create a matiere"
        cnx = self.GetDBConnexion()
        r = self._matiereEditor.create(cnx, args)
        self.CachedNotesTable.inval_cache()
        return r

    security.declareProtected(ScoAdministrate, 'do_matiere_delete')
    def do_matiere_delete(self, oid):
        "delete matiere and attached modules"
        cnx = self.GetDBConnexion()
        # delete all modules in this matiere
        mods = self.do_module_list({ 'matiere_id' : oid })
        for mod in mods:
            self.do_module_delete(mod['module_id'])
        self._matiereEditor.delete(cnx, oid)
        self.CachedNotesTable.inval_cache()

    security.declareProtected(ScoView, 'do_matiere_list')
    def do_matiere_list(self, *args, **kw ):
        "list matieres"
        cnx = self.GetDBConnexion()
        return self._matiereEditor.list(cnx, *args, **kw)

    security.declareProtected(ScoAdministrate, 'do_matiere_edit')
    def do_matiere_edit(self, *args, **kw ):
        "edit a matiere"
        cnx = self.GetDBConnexion()
        self._matiereEditor.edit( cnx, *args, **kw )
        self.CachedNotesTable.inval_cache()

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

    security.declareProtected(ScoAdministrate, 'do_module_create')
    def do_module_create(self, args):
        "create a module"
        cnx = self.GetDBConnexion()
        r = self._moduleEditor.create(cnx, args)
        self.CachedNotesTable.inval_cache()
        return r

    security.declareProtected(ScoAdministrate, 'do_module_delete')
    def do_module_delete(self, oid):
        "delete module"
        cnx = self.GetDBConnexion()
        self._moduleEditor.delete(cnx, oid)
        self.CachedNotesTable.inval_cache()

    security.declareProtected(ScoView, 'do_module_list')
    def do_module_list(self, *args, **kw ):
        "list modules"
        cnx = self.GetDBConnexion()
        return self._moduleEditor.list(cnx, *args, **kw)

    security.declareProtected(ScoAdministrate, 'do_module_edit')
    def do_module_edit(self, *args, **kw ):
        "edit a module"
        cnx = self.GetDBConnexion()
        self._moduleEditor.edit(cnx, *args, **kw )
        self.CachedNotesTable.inval_cache()
    
    # --- Semestres de formation
    _formsemestreEditor = EditableTable(
        'notes_formsemestre',
        'formsemestre_id',
        ('formsemestre_id', 'semestre_id', 'formation_id','titre',
         'date_debut', 'date_fin', 'responsable_id', 'gestion_absence'),
        sortkey = 'date_debut',
        output_formators = { 'date_debut' : DateISOtoDMY,
                             'date_fin'   : DateISOtoDMY,
                             'gestion_absence' : str },
        input_formators  = { 'date_debut' : DateDMYtoISO,
                             'date_fin'   : DateDMYtoISO,
                             'gestion_absence' : int }
        )
    
    security.declareProtected(ScoImplement, 'do_formsemestre_create')
    def do_formsemestre_create(self, args):
        "create a formsemestre"
        cnx = self.GetDBConnexion()
        r = self._formsemestreEditor.create(cnx, args)
        self.CachedNotesTable.inval_cache()
        return r

    security.declareProtected(ScoImplement, 'do_formsemestre_delete')
    def do_formsemestre_delete(self, formsemestre_id):
        "delete formsemestre, and all its moduleimpls"
        cnx = self.GetDBConnexion()
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
        # --- Destruction du semestre
        self._formsemestreEditor.delete(cnx, formsemestre_id)
        self.CachedNotesTable.inval_cache()

    security.declareProtected(ScoView, 'do_formsemestre_list')
    def do_formsemestre_list(self, *a, **kw ):
        "list formsemestres"
        #log('do_formsemestre_list: kw=%s' % (str(kw)))
        cnx = self.GetDBConnexion()
        #log( 'x %s' % str(self._formsemestreEditor.list(cnx)))
        try:
            return self._formsemestreEditor.list(cnx,*a,**kw)
        except:
            # debug (isodate bug !)
            log('*** do_formsemestre_list: exception')
            log('*** do_formsemestre_list: a=%s kw=%s' % (a,kw) )
            raise
    
    security.declareProtected(ScoImplement, 'do_formsemestre_edit')
    def do_formsemestre_edit(self, *a, **kw ):
        "edit a formsemestre"
        cnx = self.GetDBConnexion()
        self._formsemestreEditor.edit(cnx, *a, **kw )
        self.CachedNotesTable.inval_cache()

    security.declareProtected(ScoImplement, 'do_formsemestre_createwithmodules')
    def do_formsemestre_createwithmodules(self,REQUEST, userlist, edit=False ):
        "Form choix modules / responsables et creation formsemestre"
        formation_id = REQUEST.form['formation_id']
        if not edit:
            initvalues = {}
            semestre_id  = REQUEST.form['semestre_id']
        else:
            # setup form init values
            formsemestre_id = REQUEST.form['formsemestre_id']
            initvalues = self.do_formsemestre_list(
                {'formsemestre_id' : formsemestre_id})[0]
            semestre_id = initvalues['semestre_id']
            initvalues['inscrire_etuds'] = initvalues.get('inscrire_etuds','1')
            if initvalues['inscrire_etuds'] == '1':
                initvalues['inscrire_etudslist'] = ['X']
            else:
                initvalues['inscrire_etudslist'] = []
            if REQUEST.form.get('tf-submitted',False) and not REQUEST.form.has_key('inscrire_etudslist'):
                REQUEST.form['inscrire_etudslist'] = []                
            # add associated modules to tf-checked
            ams = self.do_moduleimpl_list( { 'formsemestre_id' : formsemestre_id } )
            initvalues['tf-checked'] = [ x['module_id'] for x in ams ]
            for x in ams:
                initvalues[str(x['module_id'])] = x['responsable_id']        
        # Liste des modules  dans ce semestre de cette formation
        # on pourrait faire un simple self.module_list( )
        # mais si on veut l'ordre du PPN (groupe par UE et matieres) il faut:
        mods = [] # liste de dicts
        uelist = self.do_ue_list( { 'formation_id' : formation_id } )
        for ue in uelist:
            matlist = self.do_matiere_list( { 'ue_id' : ue['ue_id'] } )
            for mat in matlist:
                modsmat = self.do_module_list( { 'matiere_id' : mat['matiere_id'] })
                mods = mods + modsmat
        #
        modform = [
            ('formsemestre_id', { 'input_type' : 'hidden' }),
            ('formation_id', { 'input_type' : 'hidden', 'default' : formation_id}),
            ('semestre_id',  { 'input_type' : 'hidden', 'default' : semestre_id}),
            ('date_debut', { 'title' : 'Date de début (j/m/a)',
                             'size' : 9, 'allow_null' : False }),
            ('date_fin', { 'title' : 'Date de fin (j/m/a)',
                             'size' : 9, 'allow_null' : False }),
            ('responsable_id', { 'input_type' : 'menu',
                                 'title' : 'Directeur des études',
                                 'allowed_values' : userlist }),        
            ('titre', { 'size' : 20, 'title' : 'Nom de ce semestre' }),
            ('gestion_absence_lst', { 'input_type' : 'checkbox',
                                      'title' : 'Suivi des absences',
                                      'allowed_values' : ['X'],
                                      'explanation' : 'indiquer les absences sur les bulletins',
                                       'labels' : [''] }),
            ('sep', { 'input_type' : 'separator',
                      'title' : '<h3>Sélectionner les modules et leur responsable:</h3>' }) ]
        for mod in mods:
            modform.append( (str(mod['module_id']),
                             { 'input_type' : 'menu',
                               'withcheckbox' : True,
                               'title' : '%s %s' % (mod['code'],mod['titre']),
                               'allowed_values' : userlist }) )
        if edit:
            modform.append( ('inscrire_etudslist',
                             { 'input_type' : 'checkbox',
                               'allowed_values' : ['X'], 'labels' : [ '' ],
                               'title' : '' ,
                               'explanation' : 'inscrire tous les étudiants du semestre aux modules ajoutés'}) )
            submitlabel = 'Modifier ce semestre de formation'
        else:
            submitlabel = 'Créer ce semestre de formation'
        #
        initvalues['gestion_absence'] = initvalues.get('gestion_absence','1')
        if initvalues['gestion_absence'] == '1':
            initvalues['gestion_absence_lst'] = ['X']
        else:
            initvalues['gestion_absence_lst'] = []
        if REQUEST.form.get('tf-submitted',False) and not REQUEST.form.has_key('gestion_absence_lst'):
            REQUEST.form['gestion_absence_lst'] = []
        #
        tf = TrivialFormulator( REQUEST.URL0, REQUEST.form, modform,
                                submitlabel = submitlabel,
                                cancelbutton = 'Annuler',
                                initvalues = initvalues)
        if tf[0] == 0:
            return tf[1] # + '<p>' + str(initvalues)
        elif tf[0] == -1:
            return '<h4>annulation</h4>'
        else:
            if tf[2]['gestion_absence_lst']:
                tf[2]['gestion_absence'] = 1
            else:
                tf[2]['gestion_absence'] = 0
            if not edit:
                # creation du semestre                
                formsemestre_id = self.do_formsemestre_create(tf[2])
                # creation des modules
                for module_id in tf[2]['tf-checked']:
                    mod_resp_id = tf[2][module_id]
                    modargs = { 'module_id' : module_id,
                                'formsemestre_id' : formsemestre_id,
                                'responsable_id' :  mod_resp_id }
                    mid = self.do_moduleimpl_create(modargs)
                return '<p>ok</>' # + str(tf[2])
            else:
                # modification du semestre:
                # on doit creer les modules nouvellement selectionnés
                # modifier ceux a modifier, et DETRUIRE ceux qui ne sont plus selectionnés.
                # Note: la destruction echouera s'il y a des objets dependants
                #       (eg des evaluations définies)
                # nouveaux modules
                checkedmods = tf[2]['tf-checked']
                self.do_formsemestre_edit(tf[2])
                ams = self.do_moduleimpl_list(
                    { 'formsemestre_id' : formsemestre_id } )
                existingmods = [ x['module_id'] for x in ams ]
                mods_tocreate = [ x for x in checkedmods if not x in existingmods ]
                # modules a existants a modifier
                mods_toedit = [ x for x in checkedmods if x in existingmods ]
                # modules a detruire
                mods_todelete = [ x for x in existingmods if not x in checkedmods ]
                #
                msg = []
                for module_id in mods_tocreate:
                    modargs = { 'module_id' : module_id,
                                'formsemestre_id' : formsemestre_id,
                                'responsable_id' :  tf[2][module_id] }
                    moduleimpl_id = self.do_moduleimpl_create(modargs)
                    mod = self.do_module_list( { 'module_id' : module_id } )[0]
                    msg += [ 'création de %s (%s)' % (mod['code'], mod['titre']) ] 
                    if tf[2]['inscrire_etudslist']:
                        # il faut inscrire les etudiants du semestre
                        # dans le nouveau module
                        self.do_moduleimpl_inscrit_tout_semestre(
                            moduleimpl_id,formsemestre_id)
                        msg += ['étudiants inscrits à %s (module %s)</p>'
                                % (moduleimpl_id, mod['code']) ]
                #
                for module_id in mods_todelete:
                    # get id
                    moduleimpl_id = self.do_moduleimpl_list(
                        { 'formsemestre_id' : formsemestre_id,
                          'module_id' : module_id } )[0]['moduleimpl_id']
                    mod = self.do_module_list( { 'module_id' : module_id } )[0]
                    # Evaluations dans ce module ?
                    evals = self.do_evaluation_list(
                        { 'moduleimpl_id' : moduleimpl_id} )
                    if evals:
                        msg += [ '<b>impossible de supprimer %s (%s) car il y a %d évaluations définies (supprimer les d\'abord)</b>' % (mod['code'], mod['titre'], len(evals)) ]
                    else:
                        msg += [ 'suppression de %s (%s)'
                                 % (mod['code'], mod['titre']) ]
                        self.do_moduleimpl_delete(moduleimpl_id)
                for module_id in mods_toedit:
                    moduleimpl_id = self.do_moduleimpl_list(
                        { 'formsemestre_id' : formsemestre_id,
                          'module_id' : module_id } )[0]['moduleimpl_id']
                    modargs = {
                        'moduleimpl_id' : moduleimpl_id,
                        'module_id' : module_id,
                        'formsemestre_id' : formsemestre_id,
                        'responsable_id' :  tf[2][module_id] }
                    self.do_moduleimpl_edit(modargs)
                    mod = self.do_module_list( { 'module_id' : module_id } )[0]
                    #msg += [ 'modification de %s (%s)' % (mod['code'], mod['titre']) ]
                    
                msg = '<ul><li>' + '</li><li>'.join(msg) + '</li></ul>'
                return '<p>Modification effectuée</p>'  + msg # + str(tf[2])

    # --- Gestion des "Implémentations de Modules"
    # Un "moduleimpl" correspond a la mise en oeuvre d'un module
    # dans une formation spécifique, à une date spécifique.
    _moduleimplEditor = EditableTable(
        'notes_moduleimpl',
        'moduleimpl_id',
        ('moduleimpl_id','module_id','formsemestre_id','responsable_id'),
        )
    
    security.declareProtected(ScoImplement, 'do_moduleimpl_create')
    def do_moduleimpl_create(self, args):
        "create a moduleimpl"
        cnx = self.GetDBConnexion()
        r = self._moduleimplEditor.create(cnx, args)
        self.CachedNotesTable.inval_cache()
        return r

    security.declareProtected(ScoImplement, 'do_moduleimpl_delete')
    def do_moduleimpl_delete(self, oid):
        "delete moduleimpl (desinscrit tous ls etudiants)"
        cnx = self.GetDBConnexion()
        # --- desinscription des etudiants
        cursor = cnx.cursor()
        req = "DELETE FROM notes_moduleimpl_inscription WHERE moduleimpl_id=%(moduleimpl_id)s"
        cursor.execute( req, { 'moduleimpl_id' : oid } )
        # --- destruction du moduleimpl
        self._moduleimplEditor.delete(cnx, oid)
        self.CachedNotesTable.inval_cache()

    security.declareProtected(ScoView, 'do_moduleimpl_list')
    def do_moduleimpl_list(self, *args, **kw ):
        "list moduleimpls"
        cnx = self.GetDBConnexion()
        return self._moduleimplEditor.list(cnx, *args, **kw)

    security.declareProtected(ScoImplement, 'do_moduleimpl_edit')
    def do_moduleimpl_edit(self, *args, **kw ):
        "edit a moduleimpl"
        cnx = self.GetDBConnexion()
        self._moduleimplEditor.edit(cnx, *args, **kw )
        self.CachedNotesTable.inval_cache()

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
        modimpls.sort(lambda x,y:
                      cmp(x['ue']['numero']*1000 + x['module']['numero'],
                          y['ue']['numero']*1000 + y['module']['numero']))
        return modimpls

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
        self.CachedNotesTable.inval_cache()
        return r

    security.declareProtected(ScoImplement, 'do_formsemestre_inscription_delete')
    def do_formsemestre_inscription_delete(self, oid):
        "delete formsemestre_inscription"
        cnx = self.GetDBConnexion()
        self._formsemestre_inscriptionEditor.delete(cnx, oid)
        self.CachedNotesTable.inval_cache()

    security.declareProtected(ScoView, 'do_formsemestre_inscription_list')
    def do_formsemestre_inscription_list(self, *args, **kw ):
        "list formsemestre_inscriptions"
        cnx = self.GetDBConnexion()
        return self._formsemestre_inscriptionEditor.list(cnx, *args, **kw)

    security.declareProtected(ScoImplement, 'do_formsemestre_inscription_edit')
    def do_formsemestre_inscription_edit(self, **kw ):
        "edit a formsemestre_inscription"
        cnx = self.GetDBConnexion()
        self._formsemestre_inscriptionEditor.edit(cnx, **kw )
        self.CachedNotesTable.inval_cache()

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

    security.declareProtected(ScoImplement, 'do_formsemestre_desinscription')
    def do_formsemestre_desinscription(self, etudid, formsemestre_id, REQUEST=None, dialog_confirmed=False):
        """desinscrit l'etudiant de ce semestre (et donc de tous les modules).
        A n'utiliser qu'en cas d'erreur de saisie"""
        if not dialog_confirmed:
            etud = self.getEtudInfo(etudid=etudid,filled=1)[0]
            sem = self.do_formsemestre_list({'formsemestre_id':formsemestre_id})[0]
            return self.confirmDialog(
                """<p>Confirmer la demande de desinscription ?</p>
                <p>%s sera désinscrit de tous les modules du semestre %s (%s - %s).</p>
                <p>Cette opération ne doit être utilisée que pour corriger une <b>erreur</b> !
                Un étudiant réellement inscrit doit le rester, le faire éventuellement <b>démissionner<b>.
                </p>
                """ % (etud['nomprenom'],sem['titre'],sem['date_debut'],sem['date_fin']),
                dest_url="", REQUEST=REQUEST,
                cancel_url="formsemestre_status?formsemestre_id=%s" % formsemestre_id,
                parameters={'etudid':etudid, 'formsemestre_id' : formsemestre_id})
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
        return self.sco_header(self,REQUEST) + '<p>Etudiant désinscrit !</p><p><a href="ficheEtud?etudid=%s">retour à la fiche</a>'%etudid + self.sco_footer(self,REQUEST)
        
    # --- Inscriptions aux modules
    _moduleimpl_inscriptionEditor = EditableTable(
        'notes_moduleimpl_inscription',
        'moduleimpl_inscription_id',
        ('moduleimpl_inscription_id', 'etudid', 'moduleimpl_id'),
        )

    security.declareProtected(ScoEtudInscrit,'do_moduleimpl_inscription_create')
    def do_moduleimpl_inscription_create(self, args):
        "create a moduleimpl_inscription"
        cnx = self.GetDBConnexion()
        #log('do_moduleimpl_inscription_create: '+ str(args))
        r = self._moduleimpl_inscriptionEditor.create(cnx, args)
        self.CachedNotesTable.inval_cache()
        return r

    security.declareProtected(ScoImplement, 'do_moduleimpl_inscription_delete')
    def do_moduleimpl_inscription_delete(self, oid):
        "delete moduleimpl_inscription"
        cnx = self.GetDBConnexion()
        self._moduleimpl_inscriptionEditor.delete(cnx, oid)
        self.CachedNotesTable.inval_cache()

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
        self.CachedNotesTable.inval_cache()

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
        

    security.declareProtected(ScoEtudInscrit,'do_formsemestre_inscription_with_modules')
    def do_formsemestre_inscription_with_modules(self, args=None,
                                                 REQUEST=None, method='inscription_with_modules' ):
        "inscrit cet etudiant a ce semestre et TOUS ses modules normaux (donc sauf le sport)"
        cnx = self.GetDBConnexion()
        cursor = cnx.cursor()
        etudid = args['etudid']
        formsemestre_id = args['formsemestre_id']
        # inscription au semestre
        self.do_formsemestre_inscription_create( args, REQUEST, method=method )
        # inscription a tous les modules de ce semestre
        modimpls = self.do_moduleimpl_withmodule_list(
            {'formsemestre_id':formsemestre_id} )
        for mod in modimpls:
            if mod['ue']['type'] == UE_STANDARD:
                self.do_moduleimpl_inscription_create(
                    {'moduleimpl_id' : moduleimpl_id,
                     'etudid' : etudid} )

    security.declareProtected(ScoEtudInscrit,'formsemestre_inscription_with_modules_form')
    def formsemestre_inscription_with_modules_form(self,etudid,REQUEST):
        "formulaire inscription de l'etud dans l'une des sessions existantes"
        etud = self.getEtudInfo(etudid=etudid,filled=1)[0]        
        H = [ self.sco_header(self,REQUEST)
              + "<h2>Inscription de %s</h2>" % etud['nomprenom']
              + "<p>L'étudiant sera inscrit à <em>tous</em> les modules de la session choisie.</p>" 
              ]
        F = self.sco_footer(self,REQUEST)
        sems = self.do_formsemestre_list()
        if sems:
            H.append('<ul>')
            for sem in sems:
                H.append('<li><a href="formsemestre_inscription_with_modules?etudid=%s&formsemestre_id=%s">%s</a>' %
                         (etudid,sem['formsemestre_id'],sem['titre']))
            H.append('</ul>')
        else:
            H.append('<p>aucune session de formation !</p>')
        H.append('<a href="%s/ficheEtud?etudid=%s">retour à la fiche de %s</a>'
                 % (self.ScoURL(), etudid, etud['nomprenom']) )
        return '\n'.join(H) + F

    
    security.declareProtected(ScoEtudInscrit,'formsemestre_inscription_with_modules')
    def formsemestre_inscription_with_modules(
        self,etudid,formsemestre_id,
        groupetd=None, groupeanglais=None, groupetp=None,
        REQUEST=None):
        """inscription de l'etud dans ce semestre.
        Formulaire avec choix groupe
        """
        sem = self.do_formsemestre_list( {'formsemestre_id':formsemestre_id} )[0]
        etud = self.getEtudInfo(etudid=etudid,filled=1)[0]
        H = [ self.sco_header(self,REQUEST)
              + "<h2>Inscription de %s dans %s</h2>" %
              (etud['nomprenom'],sem['titre']) ]
        F = self.sco_footer(self,REQUEST)
        if groupetd:
            # OK, inscription
            self.do_formsemestre_inscription_with_modules(
                args={'formsemestre_id' : formsemestre_id,
                      'etudid' : etudid,
                      'etat' : 'I',
                      'groupetd' : groupetd, 'groupeanglais' : groupeanglais,
                      'groupetp' : groupetp
                      },
                REQUEST = REQUEST, method='formsemestre_inscription_with_modules')
            return REQUEST.RESPONSE.redirect(self.ScoURL()+'/ficheEtud?etudid='+etudid)
        else:
            # formulaire choix groupe
            # Liste des groupes existant (== ou il y a des inscrits)
            gr_td,gr_tp,gr_anglais = self.do_formsemestre_inscription_listegroupes(formsemestre_id=formsemestre_id)
            if not gr_td:
                gr_td = ['A']
            if not gr_anglais:
                gr_anglais = ['']
            if not gr_tp:
                gr_tp = ['']
            H.append("""<form method="GET" name="groupesel">
            <input type="hidden" name="etudid" value="%s">
            <input type="hidden" name="formsemestre_id" value="%s">
            <table>
            <tr><td>Groupe de TD</td><td>
            <select name="groupetdmenu" onChange="document.groupesel.groupetd.value=this.options[this.selectedIndex].value;">""" %(etudid,formsemestre_id))
            for g in gr_td:
                H.append('<option value="%s">%s</option>'%(g,g))
            H.append("""</select>
            </td><td><input type="text" name="groupetd" size="12" value="%s">
            </input></td></tr>
            """ % gr_td[0])
            # anglais
            H.append("""<tr><td>Groupe d'"anglais"</td><td>
            <select name="groupeanglaismenu" onChange="document.groupesel.groupeanglais.value=this.options[this.selectedIndex].value;">""" )
            for g in gr_anglais:
                H.append('<option value="%s">%s</option>'%(g,g))
            H.append("""</select>
            </td><td><input type="text" name="groupeanglais" size="12" value="%s">
            </input></td></tr>
            """% gr_anglais[0])
            # tp
            H.append("""<tr><td>Groupe de TP</td><td>
            <select name="groupetpmenu" onChange="document.groupesel.groupetp.value=this.options[this.selectedIndex].value;">""" )
            for g in gr_tp:
                H.append('<option value="%s">%s</option>'%(g,g))
            H.append("""</select>
            </td><td><input type="text" name="groupetp" size="12" value="%s">
            </input></td></tr>
            """ % gr_tp[0])
            #
            H.append("""</table>
            <input type="submit" value="Inscrire"/>
            <p>Note: vous pouvez choisir l'un des groupes existants (figurant dans les menus) ou bien décider de créer un nouveau groupe (saisir son identifiant dans les champs textes).</p>
            <p>Note 2: le groupe de TD doit être non vide. Les autres groupes sont facultatifs.</p>
            </form>            
            """)
            return '\n'.join(H) + F

    security.declareProtected(ScoEtudInscrit,'formsemestre_inscription_optionXXX')
    def formsemestre_inscription_optionXXX(self, etudid, formsemestre_id,
                                        REQUEST=None):
        "Dialogue pour inscription a un module optionnel"
        sem = self.do_formsemestre_list( {'formsemestre_id':formsemestre_id} )[0]
        etud = self.getEtudInfo(etudid=etudid,filled=1)[0]
        H = [ self.sco_header(self,REQUEST)
              + "<h2>Inscription de %s à un module optionnel de %s</h2>" %
              (etud['nomprenom'],sem['titre']) ]
        # Cherche les moduleimlps ou il n'est pas deja inscrit
        mods = self.do_moduleimpl_withmodule_list(
            {'formsemestre_id':formsemestre_id} )
        inscr= self.do_moduleimpl_inscription_list( args={'etudid':etudid} )
        todel = {}
        for ins in inscr:
            for i in range(len(mods)):
                if mods[i]['moduleimpl_id'] == ins['moduleimpl_id']:
                    todel[i] = 1
        todel = todel.keys()
        todel.sort()
        todel.reverse()
        for i in todel:
            del mods[i]
        #
        if mods:
            H.append("""<p>Choisir un module:</p>
            <form>
            <input type="hidden" name="etudid" value="%s" />
            <input type="hidden" name="formsemestre_id" value="%s" />        
            <select name="moduleimpl_id">
            """ % (etudid, formsemestre_id))
            for mod in mods:
                H.append('<option value="%s" >%s</option>'
                         % (mod['moduleimpl_id'], mod['module']['titre']) )
            # XXXX manque bouton valider et renvoi vers une fonction faisant l'inscription
            H.append("</select></form>")
        else:
            H.append('<p>Cet étudiant est déjà inscrit à tous les modules du semestre !</p><p><a href="ficheEtud?etudid=%(etudid)s">Retour à la fiche de %(nomprenom)s</a></p>' % etud )
        return '\n'.join(H) + self.sco_footer(self,REQUEST)


    security.declareProtected(ScoEtudInscrit,'formsemestre_inscription_option')
    def formsemestre_inscription_option(self, etudid, formsemestre_id,
                                        REQUEST=None):
        "Dialogue pour (des)inscription a des modules optionnels"
        sem = self.do_formsemestre_list( {'formsemestre_id':formsemestre_id} )[0]
        etud = self.getEtudInfo(etudid=etudid,filled=1)[0]
        F = self.sco_footer(self,REQUEST)
        H = [ self.sco_header(self,REQUEST)
              + "<h2>Inscription de %s aux modules de %s (%s - %s)</h2>" %
              (etud['nomprenom'],sem['titre'],
               sem['date_debut'],sem['date_fin']) ]
        H.append("""<p>Voici la liste des modules du semestre choisi.</p><p>
        Les modules cochés sont ceux dans lesquels l'étudiant est inscrit. Vous pouvez l'inscrire ou le désincrire d'un ou plusieurs modules.</p>
        <p>Attention: cette méthode ne devrait être utilisée que pour les modules <b>optionnels</b> ou les activités culturelles et sportives.</p>
        """)
        # Cherche les moduleimlps et lesinscriptions
        mods = self.do_moduleimpl_withmodule_list(
            {'formsemestre_id':formsemestre_id} )
        inscr= self.do_moduleimpl_inscription_list( args={'etudid':etudid} )
        # Formulaire
        modimpls_ids = []
        modimpl_names= []
        initvalues = { 'moduleimpls' : [] }
        for mod in mods:
            modimpls_ids.append(mod['moduleimpl_id'])
            if mod['ue']['type'] == UE_STANDARD:
                ue_type = ''
            else:
                ue_type = '<b>%s</b>' % UE_TYPE_NAME[mod['ue']['type']]
            modimpl_names.append('%s %s &nbsp;&nbsp;(%s %s)' % (
                mod['module']['code'], mod['module']['titre'],
                mod['ue']['acronyme'], ue_type))
            # inscrit ?
            for ins in inscr:
                if ins['moduleimpl_id'] == mod['moduleimpl_id']:
                    initvalues['moduleimpls'].append(mod['moduleimpl_id'])
                    break
        descr = [
            ('formsemestre_id', { 'input_type' : 'hidden' }),
            ('etudid', { 'input_type' : 'hidden' }),
            ('moduleimpls',
             { 'input_type' : 'checkbox', 'title':'',
               'allowed_values' : modimpls_ids, 'labels' : modimpl_names,
               'vertical' : True
               }),
        ]
        tf = TrivialFormulator( REQUEST.URL0, REQUEST.form, descr,
                                initvalues,
                                cancelbutton = 'Annuler', method='GET',
                                submitlabel = 'Modifier les inscriptions', cssclass='inscroption',
                                name='tf' )
        if  tf[0] == 0:
            return '\n'.join(H) + '\n' + tf[1] + F
        elif tf[0] == -1:
            return REQUEST.RESPONSE.redirect( "ficheEtud?etudid=" + etudid )
        else:
            # Inscriptions aux modules choisis
            moduleimpls = REQUEST.form['moduleimpls']
            # il faut desinscrire des modules qui ne figurent pas
            # et inscrire aux autres, sauf si deja inscrit
            a_desinscrire = {}.fromkeys( [ x['moduleimpl_id'] for x in mods ] )
            insdict = {}
            for ins in inscr:
                insdict[ins['moduleimpl_id']] = ins
            for moduleimpl_id in moduleimpls:                    
                if a_desinscrire.has_key(moduleimpl_id):
                    del a_desinscrire[moduleimpl_id]
            # supprime ceux auxquel pas inscrit
            for moduleimpl_id in a_desinscrire.keys():
                if not insdict.has_key(moduleimpl_id):
                    del a_desinscrire[moduleimpl_id]
            a_inscrire = {}.fromkeys( moduleimpls )
            for ins in inscr:
                if a_inscrire.has_key(ins['moduleimpl_id']):
                    del a_inscrire[ins['moduleimpl_id']]
            # dict des modules:
            modsdict = {}
            for mod in mods:
                modsdict[mod['moduleimpl_id']] = mod
            #
            if (not a_inscrire) and (not a_desinscrire):
                H.append("""<h3>Aucune modification à effectuer</h3>
                <p><a href="ficheEtud?etudid=%s">retour à la fiche étudiant</a></p>""" % etudid)
                return '\n'.join(H) + F
            
            H.append("<h3>Confirmer les modifications</h3>")
            if a_desinscrire:
                H.append("<p>%s va être <b>désinscrit</b> des modules:"
                         %etud['nomprenom'])
                H.append( ', '.join([
                    '%s (%s)' %
                    (modsdict[x]['module']['titre'],
                     modsdict[x]['module']['code'])
                    for x in a_desinscrire ]) + '</p>' )
            if a_inscrire:
                H.append("<p>%s va être <b>inscrit</b> aux modules:"
                         %etud['nomprenom'])
                H.append( ', '.join([
                    '%s (%s)' %
                    (modsdict[x]['module']['titre'],
                     modsdict[x]['module']['code'])
                    for x in a_inscrire ]) + '</p>' )
            modulesimpls_ainscrire=','.join(a_inscrire)
            modulesimpls_adesinscrire=','.join(a_desinscrire)
            H.append("""<form action="do_moduleimpl_incription_options">
            <input type="hidden" name="etudid" value="%s"/>
            <input type="hidden" name="modulesimpls_ainscrire" value="%s"/>
            <input type="hidden" name="modulesimpls_adesinscrire" value="%s"/>
            <input type ="submit" value="Confirmer"/>
            <input type ="button" value="Annuler" onClick="document.location='ficheEtud?etudid=%s';"/>
            </form>
            """ % (etudid,modulesimpls_ainscrire,modulesimpls_adesinscrire,etudid))
            return '\n'.join(H) + F

    security.declareProtected(ScoEtudInscrit,'do_moduleimpl_incription_options')
    def do_moduleimpl_incription_options(
        self,etudid,
        modulesimpls_ainscrire,modulesimpls_adesinscrire,
        REQUEST=None):
        "effectue l'inscriptin et la description aux modules optionnels"
        if modulesimpls_ainscrire:
            a_inscrire = modulesimpls_ainscrire.split(',')
        else:
            a_inscrire = []
        if modulesimpls_adesinscrire:
            a_desinscrire = modulesimpls_adesinscrire.split(',')
        else:
            a_desinscrire = []
        # inscriptions
        for moduleimpl_id in a_inscrire:
            # verifie que ce module existe bien
            mod = self.do_moduleimpl_list({'moduleimpl_id':moduleimpl_id})
            if len(mod) != 1:
                raise ScoValueError('inscription: invalid moduleimpl_id: %s' % moduleimpl_id)
            self.do_moduleimpl_inscription_create(
                {'moduleimpl_id':moduleimpl_id, 'etudid' : etudid })
        # desinscriptions
        for moduleimpl_id in a_desinscrire:
            # verifie que ce module existe bien
            mod = self.do_moduleimpl_list({'moduleimpl_id':moduleimpl_id})
            if len(mod) != 1:
                raise ScoValueError('desinscription: invalid moduleimpl_id: %s' % moduleimpl_id)
            inscr = self.do_moduleimpl_inscription_list( args=
                {'moduleimpl_id':moduleimpl_id, 'etudid' : etudid })
            if not inscr:
                raise ScoValueError('pas inscrit a ce module ! (etudid=%s, moduleimpl_id=%)'%(etudid,moduleimpl_id))
            oid = inscr[0]['moduleimpl_inscription_id']
            self.do_moduleimpl_inscription_delete(oid)

        if REQUEST:
            H = [ self.sco_header(self,REQUEST),
                  """<h3>Modifications effectuées</h3>
                  <p><a href="ficheEtud?etudid=%s">
                  Retour à la fiche étudiant</a></p>
                  """ % etudid,
                  self.sco_footer(self, REQUEST)]
            return '\n'.join(H)

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
        # acces pour resp. moduleimpl et resp. form semestre (dir etud)
        if moduleimpl_id is None:
            raise ValueError('no moduleimpl specified') # bug
        uid=str(REQUEST.AUTHENTICATED_USER)
        M = self.do_moduleimpl_list( args={ 'moduleimpl_id':moduleimpl_id } )[0]
        sem = self.do_formsemestre_list(
            args={ 'formsemestre_id' : M['formsemestre_id'] } )[0]
        if uid != 'admin' and uid != M['responsable_id'] and uid != sem['responsable_id']:
            raise AccessDenied('Modification évaluation impossible pour %s (%s) (%s)'%(uid,str(M),str(sem)))
    
    security.declareProtected(ScoEnsView,'do_evaluation_create')
    def do_evaluation_create(self, REQUEST, args):
        "create a evaluation"
        moduleimpl_id = args['moduleimpl_id']
        self._evaluation_check_write_access(REQUEST, moduleimpl_id=moduleimpl_id)
        # check date
        jour = args.get('jour', None)
        if jour:
            M = self.do_moduleimpl_list( args={ 'moduleimpl_id' : moduleimpl_id } )[0]
            sem = self.do_formsemestre_list(args={ 'formsemestre_id':M['formsemestre_id']})[0]
            d,m,y = [ int(x) for x in sem['date_debut'].split('/') ]
            date_debut = datetime.date(y,m,d)
            d,m,y = [ int(x) for x in sem['date_fin'].split('/') ]
            date_fin = datetime.date(y,m,d)
            d,m,y = [ int(x) for x in jour.split('/') ]
            jour = datetime.date(y,m,d)
            if (jour > date_fin) or (jour < date_debut):
                raise ScoValueError("La date de l'évaluation n'est pas dans le semestre !")
        #
        cnx = self.GetDBConnexion()
        r = self._evaluationEditor.create(cnx, args)
        # inval cache pour ce semestre
        M = self.do_moduleimpl_list( args={ 'moduleimpl_id':moduleimpl_id } )[0]
        
        self.CachedNotesTable.inval_cache(formsemestre_id=M['formsemestre_id'])
        return r

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
        self.CachedNotesTable.inval_cache(formsemestre_id=M['formsemestre_id'])

    security.declareProtected(ScoView, 'do_evaluation_list')
    def do_evaluation_list(self, args ):
        "list evaluations"
        cnx = self.GetDBConnexion()
        evals = self._evaluationEditor.list(cnx, args)
        # calcule duree (chaine de car.) de chaque evaluation
        for e in evals:
            heure_debut, heure_fin = e['heure_debut'], e['heure_fin']
            if heure_debut and heure_fin:
                h0, m0 = [ int(x) for x in heure_debut.split('h') ]
                h1, m1 = [ int(x) for x in heure_fin.split('h') ]
                d = (h1-h0)*60 + (m1-m0)
                m = d%60                
                e['duree'] = '%dh' % (d/60)
                if m != 0:
                    e['duree'] += '%02d' % m
            else:
                e['duree'] = ''
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
        self._evaluation_check_write_access(REQUEST, moduleimpl_id=moduleimpl_id)
        cnx = self.GetDBConnexion()
        self._evaluationEditor.edit(cnx, args )
        # inval cache pour ce semestre
        M = self.do_moduleimpl_list( args={ 'moduleimpl_id':moduleimpl_id } )[0]
        self.CachedNotesTable.inval_cache(formsemestre_id=M['formsemestre_id'])

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
            self._evaluation_check_write_access( REQUEST,
                                                 moduleimpl_id=moduleimpl_id )
        if readonly:
            edit=True # montre les donnees existantes
        if not edit:
            # creation nouvel
            if moduleimpl_id is None:
                raise ValueError, 'missing moduleimpl_id parameter'
            initvalues = { 'note_max' : 20 }
            submitlabel = 'Créer cette évaluation'
            action = 'Création d\'une '
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
        sem = self.do_formsemestre_list( args={ 'formsemestre_id' : M['formsemestre_id'] } )[0]
        #F=self.do_formation_list(args={ 'formation_id' : sem['formation_id'] } )[0]
        #ModEvals =self.do_evaluation_list(args={ 'moduleimpl_id' : M['moduleimpl_id'] } )
        #
        H = ['<h3>%svaluation en <a href="moduleimpl_status?moduleimpl_id=%s">%s %s</a></h3>'
             % (action, moduleimpl_id, Mod['code'], Mod['titre']),
             '<p>Semestre: <a href="%s/Notes/formsemestre_status?formsemestre_id=%s">%s</a>' % (self.ScoURL(),formsemestre_id, sem['titre']),
             'du %(date_debut)s au %(date_fin)s' % sem ]
        if readonly:
            E = initvalues
            # version affichage seule (générée ici pour etre plus jolie que le Formulator)
            jour = E['jour']
            if not jour:
                jour = '???'
            H.append( '<br>Evaluation réalisée le <b>%s</b> de %s à %s'
                      % (jour,E['heure_debut'],E['heure_fin']) )
            if E['jour']:
                H.append('<span class="noprint"><a href="%s/Absences/EtatAbsencesDate?semestregroupe=%s%%21%%21%%21&date=%s">(absences ce jour)</a></span>' % (self.ScoURL(),formsemestre_id,urllib.quote(E['jour'],safe='')  ))
            H.append( '<br>Coefficient dans le module: <b>%s</b></p>' % E['coefficient'] )
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
            ('jour', { 'title' : 'Date (j/m/a)', 'size' : 12, 'explanation' : 'date de l\'examen, devoir ou contrôle' }),
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
            return self.sco_header(self,REQUEST) + '\n'.join(H) + '\n' + tf[1] + self.sco_footer(self,REQUEST)
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
        gr_td = [ x[0] for x in res if x[0] != None ]
        cursor.execute( req % 'groupetp', { 'evaluation_id' : evaluation_id } )
        res = cursor.fetchall()
        gr_tp = [ x[0] for x in res if x[0] != None ]
        cursor.execute( req % 'groupeanglais', { 'evaluation_id' : evaluation_id } )
        res = cursor.fetchall()
        gr_anglais = [ x[0] for x in res if x[0] != None ]
        return gr_td, gr_tp, gr_anglais

    security.declareProtected(ScoView, 'do_evaluation_listeetuds_groups')
    def do_evaluation_listeetuds_groups(self, evaluation_id,
                                        gr_td=[],gr_tp=[],gr_anglais=[],
                                        getallstudents=False ):
        """Donne la liste des etudids inscrits a cette evaluation dans les
        groupes indiqués.
        Si getallstudents==True, donne tous les etudiants inscrits a cette
        evaluation.
        Ne compte pas les etudinats démissionnaires (seulement les 'I')
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
        req = "select distinct Im.etudid from notes_moduleimpl_inscription Im, notes_formsemestre_inscription Isem, notes_moduleimpl M, notes_evaluation E where Isem.etudid=Im.etudid and Im.moduleimpl_id=M.moduleimpl_id and E.moduleimpl_id=M.moduleimpl_id and E.evaluation_id = %(evaluation_id)s and Isem.etat='I'" + r
        cnx = self.GetDBConnexion()
        cursor = cnx.cursor()    
        cursor.execute( req, { 'evaluation_id' : evaluation_id } )
        res = cursor.fetchall()
        return [ x[0] for x in res ]

    def _displayNote(self, val):
        "convert note from DB to viewable string"
        # utilisé seulement pour I/O vers formulaires (sans perte de precision)
        # Utliser fmt_note pour les affichages
        if val is None:
            val = 'ABS'
        elif val == NOTES_NEUTRALISE:
            val = 'EXC' # excuse, note neutralise
        else:
            val = '%g' % val
        return val

    security.declareProtected(ScoView, 'do_evaluation_etat')
    def do_evaluation_etat(self,evaluation_id):
        """donne infos sur l'etat du evaluation
        { nb_inscrits, nb_notes, nb_abs, nb_neutre, moyenne, mediane,
        date_last_modif, gr_complets, gr_incomplets, evalcomplete }
        evalcomplete est vrai si l'eval est complete (tous les inscrits
        à ce module ont des notes)
        """
        nb_inscrits = len(self.do_evaluation_listeetuds_groups(evaluation_id,getallstudents=True))
        NotesDB = self._notes_getall(evaluation_id) # { etudid : value }
        notes = [ x['value'] for x in NotesDB.values() ]
        nb_notes = len(notes)
        nb_abs = len( [ x for x in notes if x is None ] )
        nb_neutre = len( [ x for x in notes if x == NOTES_NEUTRALISE ] )
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
        insem = self.do_formsemestre_inscription_list(
            args={ 'formsemestre_id' : formsemestre_id, 'etat' : 'I' } )
        insmod = self.do_moduleimpl_inscription_list(
            args={ 'moduleimpl_id' : E['moduleimpl_id'] } )
        insmoddict = {}.fromkeys( [ x['etudid'] for x in insmod ] )
        # retire de insem ceux qui ne sont pas inscrits au module
        ins = [ i for i in insem if insmoddict.has_key(i['etudid']) ]
        GrNbMissing = {} # groupetd : nb notes manquantes
        GrNotes = {} # groupetd : liste de notes valides
        for i in ins:
            groupetd = i['groupetd']
            if NotesDB.has_key(i['etudid']):
                val = NotesDB[i['etudid']]['value']
                if GrNotes.has_key(groupetd):
                    GrNotes[groupetd].append( val )
                else:
                    GrNotes[groupetd] = [ val ]
            else:
                if not GrNotes.has_key(groupetd):
                    GrNotes[groupetd] = []
                if GrNbMissing.has_key(groupetd):
                    GrNbMissing[groupetd] += 1
                else:
                    GrNbMissing[groupetd] = 1
        gr_incomplets = [ x for x in GrNbMissing.keys() ]
        gr_incomplets.sort()
        if gr_incomplets:
            complete = 0
        else:
            complete = 1
        # calcul moyenne dans chaque groupe de TD
        gr_moyennes = [] # groupetd : {moy,median, nb_notes}
        for gr in GrNotes.keys():
            notes = GrNotes[gr]
            gr_moy, gr_median = notes_moyenne_median(notes)
            gr_moyennes.append(
                {'gr':gr, 'gr_moy' : fmt_note(gr_moy),
                 'gr_median':fmt_note(gr_median),
                 'gr_nb_notes': len(notes)} )
        # retourne mapping
        return [ {
            'evaluation_id' : evaluation_id,
            'nb_inscrits':nb_inscrits, 'nb_notes':nb_notes,
            'nb_abs':nb_abs, 'nb_neutre':nb_neutre,
            'moy':moy, 'median':median,
            'last_modif':last_modif,
            'gr_incomplets':gr_incomplets,
            'gr_moyennes' : gr_moyennes,
            'evalcomplete' : complete } ]
        #return (nb_inscrits, nb_notes, nb_abs, nb_neutre, moy, median, last_modif,
        #gr_complets, gr_incomplets)
    
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
        #return nb_eval_completes, nb_evals_en_cours, nb_evals_vides, last_modif
        return [ { 'nb_evals_completes':nb_evals_completes,
                   'nb_evals_en_cours':nb_evals_en_cours,
                   'nb_evals_vides':nb_evals_vides,
                   'last_modif':last_modif } ]

    security.declareProtected(ScoView, 'do_evaluation_etat_in_sem')
    def do_evaluation_etat_in_sem(self, formsemestre_id):
        """-> nb_eval_completes, nb_evals_en_cours, nb_evals_vides,
        date derniere modif"""
        evals = self.do_evaluation_list_in_sem(formsemestre_id)
        return self._eval_etat(evals)

    security.declareProtected(ScoView, 'do_evaluation_etat_in_mod')
    def do_evaluation_etat_in_mod(self, moduleimpl_id):
        evals = self.do_evaluation_list( { 'moduleimpl_id' : moduleimpl_id } )
        evaluation_ids = [ x['evaluation_id'] for x in evals ]
        R = []
        for evaluation_id in evaluation_ids:
            R.append( self.do_evaluation_etat(evaluation_id)[0] )
        return self._eval_etat(R)


    security.declareProtected(ScoView, 'evaluation_liste_notes')
    def evaluation_listenotes(self, REQUEST ):
        """Affichage des notes d'une évaluation"""
        if REQUEST.form.get('liste_format','html')=='html':
            H = self.sco_header(self,REQUEST) + "<h2>Affichage des notes d'une évaluation</h2><p>"
            F = '</p>' + self.sco_footer(self,REQUEST)
        else:
            H, F = '', ''
        B = self.do_evaluation_listenotes(REQUEST)
        return H + B + F

    security.declareProtected(ScoView, 'do_evaluation_liste_notes')
    def do_evaluation_listenotes(self, REQUEST ):
        """Affichage des notes d'une évaluation"""        
        cnx = self.GetDBConnexion()
        evaluation_id = REQUEST.form['evaluation_id']
        E = self.do_evaluation_list( {'evaluation_id' : evaluation_id})[0]
        M = self.do_moduleimpl_list( args={ 'moduleimpl_id' : E['moduleimpl_id'] } )[0]
        formsemestre_id = M['formsemestre_id']
        # description de l'evaluation    
        H = [ self.evaluation_create_form(evaluation_id=evaluation_id, REQUEST=REQUEST, readonly=1) ]
        # groupes
        gr_td, gr_tp, gr_anglais = self.do_evaluation_listegroupes(evaluation_id)
        grnams  = ['tous'] + [('td'+x) for x in gr_td ] # noms des checkbox
        grnams += [('tp'+x) for x in gr_tp ]
        grnams += [('ta'+x) for x in gr_anglais ]
        grlabs  = ['tous'] + gr_td + gr_tp + gr_anglais # legendes des boutons
        descr = [
            ('evaluation_id',
             { 'default' : evaluation_id, 'input_type' : 'hidden' }),
            ('liste_format',
             {'input_type' : 'radio', 'default' : 'html', 'allow_null' : False, 
              'allowed_values' : [ 'html', 'pdf', 'xls' ],
              'labels' : ['page HTML', 'fichier PDF', 'fichier tableur' ],
              'title' : 'Format' }),
            ('s' ,
             {'input_type' : 'separator',
              'title': 'Choix du ou des groupes d\'étudiants' }),
            ('groupes',
             { 'input_type' : 'checkbox', 'title':'',
               'allowed_values' : grnams, 'labels' : grlabs,
               'attributes' : ('onClick="document.tf.submit();"',) }),
            ('anonymous_listing',
             { 'input_type' : 'checkbox', 'title':'',
               'allowed_values' : ('yes',), 'labels' : ('listing "anonyme"',),
               'attributes' : ('onClick="document.tf.submit();"',),
               'template' : '<tr><td class="tf-fieldlabel">%(label)s</td><td class="tf-field">%(elem)s &nbsp;&nbsp;'
               }),
            ('note_sur_20',
             { 'input_type' : 'checkbox', 'title':'',
               'allowed_values' : ('yes',), 'labels' : ('notes sur 20',),
               'attributes' : ('onClick="document.tf.submit();"',),
               'template' : '%(elem)s</td></tr>'
               }),            
            ]
        tf = TrivialFormulator( REQUEST.URL0, REQUEST.form, descr,
                                cancelbutton = 'Annuler', method='GET',
                                submitlabel = 'OK', cssclass='noprint',
                                name='tf' )
        if  tf[0] == 0:
            return '\n'.join(H) + '\n' + tf[1]
        elif tf[0] == -1:
            return REQUEST.RESPONSE.redirect( REQUEST.URL1 )
        else:
            liste_format = tf[2]['liste_format']
            anonymous_listing = tf[2]['anonymous_listing']
            note_sur_20 = tf[2]['note_sur_20']
            if liste_format == 'xls':
                keep_numeric = True # pas de converison des notes en strings
            else:
                keep_numeric = False
            # Build list of etudids (uniq, some groups may overlap)
            glist = tf[2]['groupes']
            gr_td = [ x[2:] for x in glist if x[:2] == 'td' ]
            gr_tp = [ x[2:] for x in glist if x[:2] == 'tp' ]
            gr_anglais = [ x[2:] for x in glist if x[:2] == 'ta' ]
            g = gr_td+gr_tp+gr_anglais
            gr_title_filename = 'gr' + '+'.join(gr_td+gr_tp+gr_anglais)
            if len(g) > 1:
                gr_title = 'groupes ' + ', '.join(g)                
            elif len(g) == 1:            
                gr_title = 'groupe ' + g[0]
            else:
                gr_title = ''
            if 'tous' in glist:
                getallstudents = True
                gr_title = 'tous'
                gr_title_filename = 'tous'
            else:
                getallstudents = False
            NotesDB = self._notes_getall(evaluation_id)
            etudids = self.do_evaluation_listeetuds_groups(evaluation_id,
                                                           gr_td,gr_tp,gr_anglais,
                                                           getallstudents=getallstudents)
            E = self.do_evaluation_list( {'evaluation_id' : evaluation_id})[0]
            M = self.do_moduleimpl_list( args={ 'moduleimpl_id' : E['moduleimpl_id'] } )[0]
            Mod = self.do_module_list( args={ 'module_id' : M['module_id'] } )[0]
            evalname = '%s-%s' % (Mod['code'],DateDMYtoISO(E['jour']))
            hh = '<h4>%s du %s, %s (%d étudiants)</h4>' % (E['description'], E['jour'], gr_title,len(etudids))
            if note_sur_20:
                nmx = 20
            else:
                nmx = E['note_max']
            Th = ['', 'Nom', 'Prénom', 'Groupe', 'Note sur %d'%nmx,
                  'Remarque']
            T = [] # list of lists, used to build HTML and CSV
            nb_notes = 0
            sum_notes = 0
            for etudid in etudids:
                # infos identite etudiant (xxx sous-optimal: 1/select par etudiant)
                ident = scolars.etudident_list(cnx, { 'etudid' : etudid })[0]
                # infos inscription
                inscr = self.do_formsemestre_inscription_list(
                    {'etudid':etudid, 'formsemestre_id' : M['formsemestre_id']})[0]
                if NotesDB.has_key(etudid):
                    val = NotesDB[etudid]['value']
                    if val != None and val != NOTES_NEUTRALISE: # calcul moyenne SANS LES ABSENTS
                        if note_sur_20:
                            # remet sur 20
                            val = val * 20. / E['note_max']
                        nb_notes = nb_notes + 1
                        sum_notes += val
                    val = fmt_note(val, keep_numeric=keep_numeric)
                    comment = NotesDB[etudid]['comment']
                    if comment is None:
                        comment = ''
                    explanation = '%s (%s) %s' % (NotesDB[etudid]['date'].strftime('%d/%m/%y %Hh%M'),
                                                  NotesDB[etudid]['uid'],comment)
                else:
                    explanation = ''
                    val = ''
                if inscr['etat'] == 'I': # si inscrit, indique groupe
                    grc=inscr['groupetd']
                    if inscr['groupetp']:
                        grc += '/' + inscr['groupetp']
                    if inscr['groupeanglais']:
                        grc += '/' + inscr['groupeanglais']
                else:
                    if inscr['etat'] == 'D':
                        grc = 'DEM' # attention: ce code est re-ecrit plus bas, ne pas le changer
                    else:
                        grc = inscr['etat']
                T.append( [ etudid, ident['nom'].upper(),
                            ident['prenom'].lower().capitalize(),
                            grc, val, explanation ] )
            T.sort( lambda x,y: cmp(x[1:3],y[1:3]) ) # sort by nom, prenom
            # display
            if liste_format == 'csv':
                CSV = CSV_LINESEP.join( [ CSV_FIELDSEP.join(x) for x in [Th]+T ] )
                filename = 'notes_%s_%s.csv' % (evalname,gr_title_filename)
                return sendCSVFile(REQUEST,CSV, filename ) 
            elif liste_format == 'xls':
                title = 'notes_%s_%s' % (evalname, gr_title_filename)
                xls = sco_excel.Excel_SimpleTable(
                    titles= Th,
                    lines = T,
                    SheetName = title )
                filename = title + '.xls'
                return sco_excel.sendExcelFile(REQUEST, xls, filename )
            elif liste_format == 'html':
                if T:
                    if anonymous_listing:
                        # ce mode bizarre a été demandé par GTR1 en 2005
                        Th = [ '', Th[4] ]
                        # tri par note decroissante (anonymisation !)
                        def mcmp(x,y):                            
                            try:
                                return cmp(float(y[4]), float(x[4]))
                            except:
                                return cmp(y[4], x[4])
                        T.sort( mcmp )
                    else:
                        Th = [ Th[1], Th[2], Th[4], Th[5] ]
                    Th = [ '<th>' + '</th><th>'.join(Th) + '</th>' ]
                    Tb = []
                    demfmt = '<span class="etuddem">%s</span>'
                    absfmt = '<span class="etudabs">%s</span>'
                    cssclass = 'tablenote'
                    idx = 0
                    for t in T:
                        idx += 1
                        fmt='%s'
                        if t[3] == 'DEM':
                            fmt = demfmt
                            comment =  t[3]+' '+t[5]
                        elif t[4][:3] == 'ABS':
                            fmt = absfmt
                        nomlink = '<a href="formsemestre_bulletinetud?formsemestre_id=%s&etudid=%s">%s</a>' % (M['formsemestre_id'],t[0],t[1])
                        nom,prenom,note,comment = fmt%nomlink, fmt%t[2],fmt%t[4],t[5]
                        if anonymous_listing:
                            Tb.append( '<tr class="%s"><td>%s</td><td class="colnote">%s</td></tr>' % (cssclass, t[0], note) )
                        else:
                            Tb.append( '<tr class="%s"><td>%s</td><td>%s</td><td class="colnote">%s</td><td class="colcomment">%s</td></tr>' % (cssclass,nom,prenom,note,comment) )
                    Tb = [ '\n'.join(Tb ) ]
                    if nb_notes > 0:
                        moy = '%.3g' % (sum_notes/nb_notes)
                    else:
                        moy = 'ND'
                    if anonymous_listing:
                        Tm = [ '<tr class="tablenote"><td colspan="2" class="colnotemoy">Moyenne %s</td></tr>' % moy ]
                    else:
                        Tm = [ '<tr class="tablenote"><td></td><td>Moyenne</td><td class="colnotemoy">%s</td><td class="colcomment">sur %d notes (sans les absents)</td></tr>' % (moy, nb_notes) ]
                    if anonymous_listing:
                        tclass='tablenote_anonyme'
                    else:
                        tclass='tablenote'
                    Tab = [ '<table class="%s"><tr class="tablenotetitle">'%tclass ] + Th + ['</tr><tr><td>'] + Tb + Tm + [ '</td></tr></table>' ]
                else:
                    Tab = [ '<span class="boldredmsg">aucun groupe sélectionné !</span>' ]
                return tf[1] + '\n'.join(H) + hh + '\n'.join(Tab) 
            elif liste_format == 'pdf':
                return 'conversion PDF non implementée !'
            else:
                raise ScoValueError('invalid value for liste_format (%s)'%liste_format)

    security.declareProtected(ScoEnsView, 'do_evaluation_selectetuds')
    def do_evaluation_selectetuds(self, REQUEST ):
        """Choisi les etudiants pour saisie notes"""
        evaluation_id = REQUEST.form['evaluation_id']
        E = self.do_evaluation_list( {'evaluation_id' : evaluation_id})[0]
        M = self.do_moduleimpl_list( args={ 'moduleimpl_id' : E['moduleimpl_id'] } )[0]
        formsemestre_id = M['formsemestre_id']
        # description de l'evaluation    
        H = [ self.evaluation_create_form(evaluation_id=evaluation_id,
                                          REQUEST=REQUEST, readonly=1) ]
        # groupes
        gr_td, gr_tp, gr_anglais = self.do_evaluation_listegroupes(evaluation_id)
        grnams  = ['tous'] + [('td'+x) for x in gr_td ] # noms des checkbox
        grnams += [('tp'+x) for x in gr_tp ]
        grnams += [('ta'+x) for x in gr_anglais ]
        grlabs  = ['tous'] + gr_td + gr_tp + gr_anglais # legendes des boutons
        if len(gr_td) <= 1 and len(gr_tp) <= 1 and len(gr_anglais) <= 1:
            no_group = True
        else:
            no_group = False
        descr = [
            ('evaluation_id', { 'default' : evaluation_id, 'input_type' : 'hidden' }),
            ('note_method', {'input_type' : 'radio', 'default' : 'form', 'allow_null' : False, 
                             'allowed_values' : [ 'xls', 'form' ],
                             'labels' : ['fichier tableur', 'formulaire web'],
                             'title' : 'Méthode de saisie des notes' }) ]
        if not no_group:
            descr += [ 
                ('s' , {'input_type' : 'separator', 'title': 'Choix du ou des groupes d\'étudiants' }),
                ('groupes', { 'input_type' : 'checkbox', 'title':'',
                              'allowed_values' : grnams, 'labels' : grlabs }) ]
        tf = TrivialFormulator( REQUEST.URL0, REQUEST.form, descr,
                                cancelbutton = 'Annuler',
                                submitlabel = 'OK' )
        if  tf[0] == 0:
            H.append( """<div class="saisienote_etape1">
            <span class="titredivsaisienote">Etape 1 : choix du groupe et de la méthode</span>
            """)
            return '\n'.join(H) + '\n' + tf[1] + "\n</div>"
        elif tf[0] == -1:
            return REQUEST.RESPONSE.redirect( REQUEST.URL1 )
        else:
            # form submission
            #   get checked groups
            if no_group:
                g = ['tous']
            else:
                g = tf[2]['groupes']
            note_method =  tf[2]['note_method']
            if note_method in ('form', 'xls'):
                # return notes_evaluation_formnotes( REQUEST )
                gs = [('groupes%3Alist=' + urllib.quote_plus(x)) for x in g ]
                query = 'evaluation_id=%s&note_method=%s&' % (evaluation_id,note_method) + '&'.join(gs)
                REQUEST.RESPONSE.redirect( REQUEST.URL1 + '/notes_evaluation_formnotes?' + query )
            else:
                raise ValueError, "invalid note_method (%s)" % tf[2]['note_method'] 
        
    security.declareProtected(ScoEnsView, 'do_evaluation_formnotes')
    def do_evaluation_formnotes(self, REQUEST ):
        """Formulaire soumission notes pour une evaluation.
        parametres: evaluation_id, groupes (liste, avec prefixes tp, td, ta)
        """
        authuser = str(REQUEST.AUTHENTICATED_USER)
        evaluation_id = REQUEST.form['evaluation_id']
        E = self.do_evaluation_list( {'evaluation_id' : evaluation_id})[0]
        # Check access
        # (admin, respformation, and responsable_id)
        if not self.can_edit_notes( authuser, E['moduleimpl_id'] ):
            # XXX imaginer un redirect + msg erreur
            raise AccessDenied('Modification des notes impossible pour %s'%authuser)
        #
        cnx = self.GetDBConnexion()
        note_method = REQUEST.form['note_method']
        okbefore = int(REQUEST.form.get('okbefore',0)) # etait ok a l'etape precedente
        reviewed = int(REQUEST.form.get('reviewed',0)) # a ete presenté comme "pret a soumettre"
        initvalues = {}
        CSV = [] # une liste de liste de chaines: lignes du fichier CSV
        CSV.append( ['Fichier de notes (à enregistrer au format CSV XXX)'])
        # Construit liste des etudiants        
        glist = REQUEST.form.get('groupes', [] )
        gr_td = [ x[2:] for x in glist if x[:2] == 'td' ]
        gr_tp = [ x[2:] for x in glist if x[:2] == 'tp' ]
        gr_anglais = [ x[2:] for x in glist if x[:2] == 'ta' ]
        gr_title = ' '.join(gr_td+gr_tp+gr_anglais)
        gr_title_filename = 'gr' + '+'.join(gr_td+gr_tp+gr_anglais)
        if 'tous' in glist:
            getallstudents = True
            gr_title = 'tous'
            gr_title_filename = 'tous'
        else:
            getallstudents = False
        etudids = self.do_evaluation_listeetuds_groups(evaluation_id,
                                                       gr_td,gr_tp,gr_anglais,
                                                       getallstudents=getallstudents)
        if not etudids:
            return '<p>Aucun groupe sélectionné !</p>'
        # Notes existantes
        NotesDB = self._notes_getall(evaluation_id)
        #
        M = self.do_moduleimpl_list( args={ 'moduleimpl_id' : E['moduleimpl_id'] } )[0]
        Mod = self.do_module_list( args={ 'module_id' : M['module_id'] } )[0]
        sem = self.do_formsemestre_list( args={ 'formsemestre_id' : M['formsemestre_id'] } )[0]
        evalname = '%s-%s' % (Mod['code'],DateDMYtoISO(E['jour']))
        if E['description']:
            evaltitre = '%s du %s' % (E['description'],E['jour'])
        else:
            evaltitre = 'évaluation du %s' % E['jour']
        description = '%s: %s en %s (%s) resp. %s' % (sem['titre'], evaltitre, Mod['abbrev'], Mod['code'], M['responsable_id'].capitalize())
        head = '<h3>%s</h3>' % description
        CSV.append ( [ description ] )
        head += '<p>Etudiants des groupes %s (%d étudiants)</p>'%(gr_title,len(etudids))

        head += '<em>%s</em> du %s (coef. %g, <span class="boldredmsg">notes sur %g</span>)' % (E['description'],E['jour'],E['coefficient'],E['note_max'])
        CSV.append ( [ '', 'date', 'coef.' ] )
        CSV.append ( [ '', '%s' % E['jour'], '%g' % E['coefficient'] ] )
        CSV.append( ['!%s' % evaluation_id ] )
        CSV.append( [ '', 'Nom', 'Prénom', 'Etat', 'Groupe',
                      'Note sur %d'% E['note_max'], 'Remarque' ] )    
        descr = [
            ('evaluation_id', { 'default' : evaluation_id, 'input_type' : 'hidden' }),
            ('groupes', { 'default' : glist,  'input_type' : 'hidden', 'type':'list' }),
            ('note_method', { 'default' : note_method, 'input_type' : 'hidden'}),
            ('comment', { 'size' : 44, 'title' : 'Commentaire',
                          'return_focus_next' : True, }),
            ('s2' , {'input_type' : 'separator', 'title': '<br>'}),
            ]
        el = [] # list de (label, etudid, note_value, explanation )
        for etudid in etudids:
            # infos identite etudiant (xxx sous-optimal: 1/select par etudiant)
            ident = scolars.etudident_list(cnx, { 'etudid' : etudid })[0] # XXX utiliser ZScolar (parent)
            # infos inscription
            inscr = self.do_formsemestre_inscription_list(
                {'etudid':etudid, 'formsemestre_id' : M['formsemestre_id']})[0]
            label = '%s %s' % (ident['nom'].upper(), ident['prenom'].lower().capitalize())
            if NotesDB.has_key(etudid):
                val = self._displayNote(NotesDB[etudid]['value'])
                comment = NotesDB[etudid]['comment']
                if comment is None:
                    comment = ''
                explanation = '%s (%s) %s' % (NotesDB[etudid]['date'].strftime('%d/%m/%y %Hh%M'),
                                              NotesDB[etudid]['uid'], comment )
            else:
                explanation = ''
                val = ''            
            el.append( (label, etudid, val, explanation, ident, inscr) )
        el.sort() # sort by name
        for (label,etudid, val, explanation, ident, inscr) in el:
            initvalues['note_'+etudid] = val
            if inscr['etat'] != 'I':
                label = '<span class="etuddem">' + label + '</span>'
            descr.append( ('note_'+etudid, { 'size' : 4, 'title' : label,
                                             'explanation':explanation,
                                             'return_focus_next' : True,
                                             } ) )
            CSV.append( [ '%s' % etudid, ident['nom'].upper(), ident['prenom'].lower().capitalize(),
                          inscr['etat'],
                          inscr['groupetd']+'/'+inscr['groupetp']+'/'+inscr['groupeanglais'],
                          val, explanation ] )
        if note_method == 'csv':
            CSV = CSV_LINESEP.join( [ CSV_FIELDSEP.join(x) for x in CSV ] )
            filename = 'notes_%s_%s.csv' % (evalname,gr_title_filename)
            return sendCSVFile(REQUEST,CSV, filename )
        elif note_method == 'xls':
            filename = 'notes_%s_%s.xls' % (evalname, gr_title_filename)
            xls = sco_excel.Excel_feuille_saisie( E, description, lines=CSV[6:] )
            return sco_excel.sendExcelFile(REQUEST, xls, filename )
        if okbefore:
            submitlabel = 'Entrer ces notes'
        else:        
            submitlabel = 'Vérifier ces notes'
        tf =  TF( REQUEST.URL0, REQUEST.form, descr, initvalues=initvalues,
                  cancelbutton='Annuler', submitlabel=submitlabel )
        form = tf.getform()
        if tf.canceled():
            return REQUEST.RESPONSE.redirect( REQUEST.URL1 )
        elif (not tf.submitted()) or not tf.result:
            # affiche premier formulaire
            return head + form # + '<p>' + CSV # + '<p>' + str(descr)
        else:
            # form submission
            # build list of (etudid, note) and check it
            notes = [ (etudid, tf.result['note_'+etudid]) for etudid in etudids ]
            L, invalids, withoutnotes, absents, tosuppress = self._check_notes(notes, E)
            # demande confirmation
            H = ['<ul class="tf-msg">']
            if invalids:
                H.append( '<li class="tf-msg">%d notes invalides !</li>' % len(invalids) )
            if len(L):
                 H.append( '<li class="tf-msg-notice">%d notes valides</li>' % len(L) )
            if withoutnotes:
                H.append( '<li class="tf-msg-notice">%d étudiants sans notes !</li>' % len(withoutnotes) )
            if absents:
                H.append( '<li class="tf-msg-notice">%d étudiants absents !</li>' % len(absents) )
            if tosuppress:
                H.append( '<li class="tf-msg-notice">%d notes à supprimer !</li>' % len(tosuppress) )
            H.append( '</ul>' )

            oknow = int(not len(invalids))
            tf.formdescription.append(
                ('okbefore', { 'input_type':'hidden', 'default' : oknow } ) )
            tf.values['okbefore'] = oknow        
            tf.formdescription.append(
                ('reviewed', { 'input_type':'hidden', 'default' : okbefore } ) )        
            tf.values['reviewed'] = okbefore
            if oknow and reviewed:
                # ok, on rentre ces notes
                nbchanged, nbsuppress = self._notes_add(authuser, evaluation_id, L, tf.result['comment'])
                return '<p>OK !<br>%s notes modifiées (%d supprimées)<br></p><p><a href="moduleimpl_status?moduleimpl_id=%s">Continuer</a></p>' % (nbchanged,nbsuppress,E['moduleimpl_id'])
            else:            
                return head + '\n'.join(H) + tf.getform()

    security.declareProtected(ScoEnsView, 'do_evaluation_upload_csv')
    def do_evaluation_upload_csv(self, REQUEST):
        """soumission d'un fichier CSV (evaluation_id, notefile)
        """
        authuser = str(REQUEST.AUTHENTICATED_USER)
        evaluation_id = REQUEST.form['evaluation_id']
        comment = REQUEST.form['comment']
        E = self.do_evaluation_list( {'evaluation_id' : evaluation_id})[0]
        # Check access
        # (admin, respformation, and responsable_id)
        if not self.can_edit_notes( authuser, E['moduleimpl_id'] ):
            # XXX imaginer un redirect + msg erreur
            raise AccessDenied('Modification des notes impossible pour %s'%authuser)
        #
        data = REQUEST.form['notefile'].read()
        #log('data='+str(data))
        data = data.replace('\r\n','\n').replace('\r','\n')
        lines = data.split('\n')
        # decode fichier
        # 1- skip lines until !evaluation_id
        n = len(lines)
        i = 0
        #log('lines='+str(lines))
        while i < n:
            if not lines[i]:
                raise NoteProcessError('Format de fichier invalide ! (1)')
            if lines[i].strip()[0] == '!':
                break
            i = i + 1
        if i == n:
            raise NoteProcessError('Format de fichier invalide ! (pas de ligne evaluation_id)')
        eval_id = lines[i].split(CSV_FIELDSEP)[0].strip()[1:]
        if eval_id != evaluation_id:
            raise NoteProcessError("Fichier invalide: le code d\'évaluation de correspond pas ! ('%s' != '%s')"%(eval_id,evaluation_id))
        # 2- get notes -> list (etudid, value)
        notes = []
        ni = i+1
        try:
            for line in lines[i+1:]:
                line = line.strip()
                if line:
                    fs = line.split(CSV_FIELDSEP)
                    etudid = fs[0].strip()
                    val = fs[5].strip()
                    if etudid:
                        notes.append((etudid,val))
                ni += 1
        except:
            raise NoteProcessError('Format de fichier invalide ! (erreur ligne %d)<br>"%s"' % (ni, lines[ni]))
        L, invalids, withoutnotes, absents, tosuppress = self._check_notes(notes,E)
        if len(invalids):
            return '<p class="boldredmsg">Le fichier contient %d notes invalides</p>' % len(invalids)
        else:
            nb_changed, nb_suppress = self._notes_add(authuser, evaluation_id, L, comment )
            return '<p>%d notes changées (%d sans notes, %d absents, %d note supprimées)</p>'%(nb_changed,len(withoutnotes),len(absents),nb_suppress) + '<p>' + str(notes)


    security.declareProtected(ScoEnsView, 'do_evaluation_upload_xls')
    def do_evaluation_upload_xls(self, REQUEST):
        """soumission d'un fichier XLS (evaluation_id, notefile)
        """
        authuser = str(REQUEST.AUTHENTICATED_USER)
        evaluation_id = REQUEST.form['evaluation_id']
        comment = REQUEST.form['comment']
        E = self.do_evaluation_list( {'evaluation_id' : evaluation_id})[0]
        # Check access
        # (admin, respformation, and responsable_id)
        if not self.can_edit_notes( authuser, E['moduleimpl_id'] ):
            # XXX imaginer un redirect + msg erreur
            raise AccessDenied('Modification des notes impossible pour %s'%authuser)
        #
        data = REQUEST.form['notefile'].read()
        diag, lines = sco_excel.Excel_to_list( data )
        try:
            if not lines:
                raise FormatError()
            # -- search eval code
            n = len(lines)
            i = 0
            ok = True
            while i < n:
                if not lines[i]:
                    diag.append('Erreur: format invalide (ligne vide ?)')
                    raise FormatError()
                if lines[i][0].strip()[0] == '!':
                    break
                i = i + 1
            if i == n:
                diag.append('Erreur: format invalide ! (pas de ligne evaluation_id)')
                raise FormatError()
            
            eval_id = lines[i][0].strip()[1:]
            if eval_id != evaluation_id:
                diag.append("Erreur: fichier invalide: le code d\'évaluation de correspond pas ! ('%s' != '%s')"%(eval_id,evaluation_id))
                raise FormatError()
            # --- get notes -> list (etudid, value)
            # ignore toutes les lignes ne commençant pas par !
            notes = []
            ni = i+1
            try:
                for line in lines[i+1:]:
                    if line:
                        cell0 = line[0].strip()
                        if cell0 and cell0[0] == '!':
                            etudid = cell0[1:]
                            if len(line) > 4:
                                val = line[4].strip()
                            else:
                                val = '' # ligne courte: cellule vide
                            if etudid:
                                notes.append((etudid,val))
                    ni += 1
            except:
                diag.append('Erreur: feuille invalide ! (erreur ligne %d)<br>"%s"' % (ni, str(lines[ni])))
                raise FormatError()
            # -- check values
            L, invalids, withoutnotes, absents, tosuppress = self._check_notes(notes,E)
            if len(invalids):
                diag.append('Erreur: la feuille contient %d notes invalides</p>' % len(invalids))
                if len(invalids) < 25:
                    diag.append('Notes invalides pour les id: ' + str(invalids) )
                raise FormatError()
            else:
                nb_changed, nb_suppress = self._notes_add(authuser, evaluation_id, L, comment )
                return '<p>%d notes changées (%d sans notes, %d absents, %d note supprimées)</p>'%(nb_changed,len(withoutnotes),len(absents),nb_suppress) + '<p>' + str(notes)

        except FormatError:
            if diag:
                msg = '<ul class="tf-msg"><li class="tf_msg">' + '</li><li class="tf_msg">'.join(diag) + '</li></ul>'
            else:
                msg = '<ul class="tf-msg"><li class="tf_msg">Une erreur est survenue</li></ul>'
            return msg + '<p>(pas de notes modifiées)</p>'
            
    def _check_notes(self, notes, evaluation ):
        """notes is a list of tuples (etudid, value)
        returns list of valid notes (etudid, float value)
        and 4 lists of etudid: invalids, withoutnotes, absents, tosuppress
        """
        note_max = evaluation['note_max']
        L = [] # liste (etudid, note) des notes ok (ou absent) 
        invalids = [] # etudid avec notes invalides
        withoutnotes = [] # etudid sans notes (champs vides)
        absents = [] # etudid absents
        tosuppress = [] # etudids avaec ancienne note à supprimer
        for (etudid, note) in notes:
            note = str(note)        
            if note:
                note = note.strip().upper().replace(',','.')
                if note[:3] == 'ABS':
                    note = None
                    absents.append(etudid)
                elif note[:3] == 'NEU' or note[:3] == 'EXC':
                    note = NOTES_NEUTRALISE
                elif note[:3] == 'SUP':
                    note = NOTES_SUPPRESS
                    tosuppress.append(etudid)
                else:
                    try:
                        note = float(note)
                        if (note < NOTES_MIN) or (note > note_max):
                            raise ValueError
                    except:
                        invalids.append(etudid)
                L.append((etudid,note))
            else:
                withoutnotes.append(etudid)
        return L, invalids, withoutnotes, absents, tosuppress

    security.declareProtected(ScoView, 'can_edit_notes')
    def can_edit_notes(self, uid, moduleimpl_id ):
        "True if user 'uid' can enter or edit notes in this module"
        uid = str(uid)
        M = self.do_moduleimpl_list(args={ 'moduleimpl_id' : moduleimpl_id})[0]
        sem = self.do_formsemestre_list(args={ 'formsemestre_id' : M['formsemestre_id'] } )[0]
        if uid != 'admin' and uid != M['responsable_id'] and uid != sem['responsable_id']:
            return False
        else:
            return True        

    security.declareProtected(ScoView, 'evaluation_suppress_alln')
    def evaluation_suppress_alln(self, evaluation_id, REQUEST, dialog_confirmed=False):
        "suppress all notes in this eval"
        authuser = str(REQUEST.AUTHENTICATED_USER)
        E = self.do_evaluation_list( {'evaluation_id' : evaluation_id})[0]
        if not self.can_edit_notes( authuser, E['moduleimpl_id'] ):
            # XXX imaginer un redirect + msg erreur
            raise AccessDenied('Modification des notes impossible pour %s'%authuser)
        if not dialog_confirmed:
            return self.confirmDialog('<p>Confirmer la suppression des notes ?</p>',
                                      dest_url="", REQUEST=REQUEST,
                                      cancel_url="moduleimpl_status?moduleimpl_id=%s"%E['moduleimpl_id'],
                                      parameters={'evaluation_id':evaluation_id})
        # recupere les etuds ayant une note
        NotesDB = self._notes_getall(evaluation_id)
        notes = [ (etudid, NOTES_SUPPRESS) for etudid in NotesDB.keys() ]
        # modif
        nb_changed, nb_suppress = self._notes_add(
            authuser, evaluation_id, notes, comment='suppress all' )
        assert nb_changed == nb_suppress       
        H = [ '<p>%s notes supprimées</p>' % nb_suppress,
              '<p><a href="moduleimpl_status?moduleimpl_id=%s">continuer</a>'
              % E['moduleimpl_id']
              ]
        return self.sco_header(self,REQUEST) + '\n'.join(H) + self.sco_footer(self,REQUEST)
    
    # not accessible through the web
    def _notes_add(self, uid, evaluation_id, notes, comment=None ):
        """Insert or update notes
        notes is a list of tuples (etudid,value)
        Nota:
        - va verifier si tous les etudiants sont inscrits
        au moduleimpl correspond a cet eval_id.
        - si la note existe deja avec valeur distincte, ajoute une entree au log (notes_notes_log)
        Return number of changed notes
        """
        # Verifie inscription et valeur note
        inscrits = {}.fromkeys(self.do_evaluation_listeetuds_groups(evaluation_id,getallstudents=True))
        for (etudid,value) in notes:
            if not inscrits.has_key(etudid):
                raise NoteProcessError("etudiant %s non inscrit a l'evaluation %s" %(etudid,evaluation_id))
            if not ((value is None) or (type(value) == type(1.0))):
                raise NoteProcessError( "etudiant %s: valeur de note invalide (%s)" %(etudid,value))
        # Recherche notes existantes
        NotesDB = self._notes_getall(evaluation_id)
        # Met a jour la base
        cnx = self.GetDBConnexion()
        cursor = cnx.cursor()
        nb_changed = 0
        nb_suppress = 0
        try:
            for (etudid,value) in notes:
                if not NotesDB.has_key(etudid):
                    # nouvelle note
                    if value != NOTES_SUPPRESS:
                        aa = {'etudid':etudid, 'evaluation_id':evaluation_id,
                              'value':value, 'comment' : comment, 'uid' : uid}
                        quote_dict(aa)
                        cursor.execute('insert into notes_notes (etudid,evaluation_id,value,comment,uid) values (%(etudid)s,%(evaluation_id)s,%(value)f,%(comment)s,%(uid)s)', aa )
                        nb_changed = nb_changed + 1
                else:
                    # il y a deja une note
                    oldval = NotesDB[etudid]['value']
                    changed = False
                    if type(value) != type(oldval):
                        changed = True
                    elif type(value) == type(1.0) and (abs(value-oldval) > NOTES_PRECISION):
                        changed = True
                    elif value != oldval:
                        changed = True
                    if changed:
                        # recopie l'ancienne note dans notes_notes_log, puis update
                        cursor.execute('insert into notes_notes_log (etudid,evaluation_id,value,comment,date,uid) select etudid,evaluation_id,value,comment,date,uid from notes_notes where etudid=%(etudid)s and evaluation_id=%(evaluation_id)s',
                                       { 'etudid':etudid, 'evaluation_id':evaluation_id } )
                        aa = { 'etudid':etudid, 'evaluation_id':evaluation_id,
                               'value':value,
                               'date': apply(DB.Timestamp, time.localtime()[:6]),
                               'comment' : comment, 'uid' : uid}
                        quote_dict(aa)
                        if value != NOTES_SUPPRESS:
                            cursor.execute('update notes_notes set value=%(value)s, comment=%(comment)s, date=%(date)s, uid=%(uid)s where etudid=%(etudid)s and evaluation_id=%(evaluation_id)s', aa )
                        else: # supression ancienne note
                            log('_notes_add, suppress, evaluation_id=%s, etudid=%s, oldval=%s'
                                % (evaluation_id,etudid,oldval) )
                            cursor.execute('delete from notes_notes where etudid=%(etudid)s and evaluation_id=%(evaluation_id)s', aa )
                            nb_suppress += 1
                        nb_changed += 1                    
        except:
            log('*** exception in _notes_add')
            # inval cache
            self.CachedNotesTable.inval_cache(formsemestre_id=M['formsemestre_id'])
            cnx.rollback() # abort
            raise # re-raise exception
        cnx.commit()
        E = self.do_evaluation_list( {'evaluation_id' : evaluation_id})[0]
        M = self.do_moduleimpl_list(args={ 'moduleimpl_id' : E['moduleimpl_id']})[0]
        self.CachedNotesTable.inval_cache(formsemestre_id=M['formsemestre_id']) 
        return nb_changed, nb_suppress

    
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
        à ce module, et la liste des evaluations "valides" (toutes notes entrées).
        La moyenne est calculée en utilisant les coefs des évaluations.
        Les notes NEUTRES (abs. excuses) ne sont pas prises en compte.
        Les notes ABS sont remplacées par des zéros.
        S'il manque des notes et que le coef n'est pas nul,
        la moyenne n'est pas calculée: NA
        Ne prend en compte que les evaluations où toutes les notes sont entrées
        Le résultat est une note sur 20
        """
        M = self.do_moduleimpl_list(args={ 'moduleimpl_id' : moduleimpl_id })[0]
        etudids = self.do_moduleimpl_listeetuds(moduleimpl_id)
        evals = self.do_evaluation_list(args={ 'moduleimpl_id' : moduleimpl_id })
        # recupere les notes de toutes les evaluations
        for e in evals:
            e['nb_inscrits'] = len(
                self.do_evaluation_listeetuds_groups(e['evaluation_id'],
                                                     getallstudents=True))
            NotesDB = self._notes_getall(e['evaluation_id'])
            notes = [ x['value'] for x in NotesDB.values() ]
            e['nb_notes'] = len(notes)
            e['nb_abs'] = len( [ x for x in notes if x is None ] )
            e['nb_neutre'] = len( [ x for x in notes if x == NOTES_NEUTRALISE ] )
            e['notes'] = NotesDB
            e['etat'] = self.do_evaluation_etat(e['evaluation_id'])[0]
        # filtre les evals valides (toutes les notes entrées)        
        valid_evals = [ e for e in evals if e['etat']['evalcomplete'] ]
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
                    if note != NOTES_NEUTRALISE:
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
        return R, valid_evals

    security.declareProtected(ScoView, 'do_formsemestre_moyennes')
    def do_formsemestre_moyennes(self, formsemestre_id):
        """retourne dict { moduleimpl_id : { etudid, note_moyenne_dans_ce_module } },
        la liste des moduleimpls, la liste des evaluations valides
        """
        sem = self.do_formsemestre_list(args={ 'formsemestre_id' : formsemestre_id } )[0]
        inscr = self.do_formsemestre_inscription_list(
            args = { 'formsemestre_id' : formsemestre_id })
        etudids = [ x['etudid'] for x in inscr ]
        mods = self.do_moduleimpl_list( args={ 'formsemestre_id' : formsemestre_id})
        # recupere les moyennes des etudiants de tous les modules
        D = {}
        valid_evals = []
        for mod in mods:
            assert not D.has_key(mod['moduleimpl_id'])
            D[mod['moduleimpl_id']], valid_evals_mod = self.do_moduleimpl_moyennes(mod['moduleimpl_id'])
            valid_evals += valid_evals_mod
        #
        return D, mods, valid_evals

    security.declareProtected(ScoView, 'notes_formsemestre_recapcomplet')
    def do_formsemestre_recapcomplet(self,REQUEST,formsemestre_id,format='html'):
        """Grand tableau récapitulatif avec toutes les notes de modules
        pour tous les étudiants, les moyennes par UE et générale,
        trié par moyenne générale décroissante.
        """
        sem = self.do_formsemestre_list(args={ 'formsemestre_id' : formsemestre_id } )[0]
        nt = self.CachedNotesTable.get_NotesTable(self, formsemestre_id)    
        modimpls = nt.get_modimpls()
        ues = nt.get_ues()
        T = nt.get_table_moyennes_triees()
        if format == 'xls':
            keep_numeric = True # pas de conversion des notes en strings
        else:
            keep_numeric = False
        if format=='xml':
            # XML export: liste tous les bulletins XML
            REQUEST.RESPONSE.setHeader('Content-type', XML_MIMETYPE)
            doc = jaxml.XML_document( encoding=SCO_ENCODING )
            doc.recapsemestre( formsemestre_id=formsemestre_id,
                               date=datetime.datetime.now().isoformat() )
            evals=self.do_evaluation_etat_in_sem(formsemestre_id)[0]
            doc._push()
            doc.evals_info( nb_evals_completes=evals['nb_evals_completes'],
                            nb_evals_en_cours=evals['nb_evals_en_cours'],
                            nb_evals_vides=evals['nb_evals_vides'],
                            date_derniere_note=evals['last_modif'])
            doc._pop()
            for t in T:
                etudid = t[-1]
                doc._push()
                self.make_xml_formsemestre_bulletinetud(
                    formsemestre_id, etudid, doc=doc )
                doc._pop()
            return repr(doc)
        
        # Construit une liste de listes de chaines: le champs du tableau resultat (HTML ou CSV)
        F = []
        h = [ 'Rg', 'Nom', 'Gr', 'Moy' ]
        cod2mod ={} # code : moduleimpl_id
        for ue in ues:
            if ue['type'] == UE_STANDARD:            
                h.append( ue['acronyme'] )
            elif ue['type'] == UE_SPORT:
                h.append('') # n'affiche pas la moyenne d'UE dans ce cas
            else:
                raise ScoValueError('type UE invalide !')
            for modimpl in modimpls:
                if modimpl['module']['ue_id'] == ue['ue_id']:
                    code = modimpl['module']['code']
                    h.append( code )
                    cod2mod[code] = modimpl['moduleimpl_id'] # pour fabriquer le lien
        F.append(h)
        ue_index = [] # indices des moy UE dans l (pour appliquer style css)
        def fmtnum(val): # conversion en nombre pour cellules excel
            if keep_numeric:
                try:
                    return float(val)
                except:
                    return val
            else:
                return val
        # calcul des moyennes des moyennes (generale et par UE)
        sum_moy = 0
        nb_moy = 0
        for ue in ues:
            ue['sum_moy'] = 0
            ue['nb_moy'] = 0
        for t in T:
            etudid = t[-1]
            l = [ nt.get_etud_rang(etudid),nt.get_nom_short(etudid),
                  nt.get_groupetd(etudid),
                  fmtnum(fmt_note(t[0],keep_numeric=keep_numeric))] # rang, nom,  groupe, moy_gen
            try:
                sum_moy += float(t[0])
                nb_moy += 1
            except:
                pass
            i = 0
            for ue in ues:
                i += 1
                try:
                    ue['sum_moy'] += float(t[i])
                    ue['nb_moy']  += 1
                except:
                    pass
                if ue['type'] == UE_STANDARD:
                    l.append( fmtnum(t[i]) ) # moyenne dans l'ue
                elif ue['type'] == UE_SPORT:
                    l.append('') # n'affiche pas la moyenne d'UE dans ce cas
                ue_index.append(len(l)-1)
                j = 0
                for modimpl in modimpls:
                    if modimpl['module']['ue_id'] == ue['ue_id']:
                        l.append( fmtnum(t[j+len(ues)+1]) ) # moyenne etud dans module
                    j += 1
            l.append(etudid) # derniere colonne = etudid
            F.append(l)
        # Dernière ligne: moyennes UE et modules
        if nb_moy > 0:
            moy_moy = sum_moy / nb_moy
        else:
            moy_moy = '-'
        l = [ '', 'Moyennes', '', fmt_note(moy_moy) ] 
        i = 0
        for ue in ues:
            i += 1
            if ue['nb_moy'] > 0:
                moy_ue = ue['sum_moy'] / ue['nb_moy']
            else:
                moy_ue = ''
            if ue['type'] == UE_STANDARD:
                l.append( fmt_note(moy_ue) ) 
            elif ue['type'] == UE_SPORT:
                l.append('') # n'affiche pas la moyenne d'UE dans ce cas
            ue_index.append(len(l)-1)
            for modimpl in modimpls:
                if modimpl['module']['ue_id'] == ue['ue_id']:
                    l.append(fmt_note(nt.get_mod_moy(modimpl['moduleimpl_id'])[0],
                                      keep_numeric=keep_numeric)) # moyenne du module
        F.append(l + [''] ) # ajoute cellule etudid inutilisee ici
        # Generation table au format demandé
        if format == 'html':
            # Table format HTML
            H = [ '<table class="notes_recapcomplet sortable" id="recapcomplet">' ]
            cells = '<tr class="recap_row_tit sortbottom">'
            for i in range(len(F[0])):
                if i in ue_index:
                    cls = 'recap_tit_ue'
                else:
                    cls = 'recap_tit'
                if i == 0: # Rang: force tri numerique pour sortable
                    cls = cls + ' sortnumeric'
                if cod2mod.has_key(F[0][i]): # lien vers etat module
                    cells += '<td class="%s"><a href="moduleimpl_status?moduleimpl_id=%s">%s</a></td>' % (cls,cod2mod[F[0][i]], F[0][i])
                else:
                    cells += '<td class="%s">%s</td>' % (cls, F[0][i])
            ligne_titres = cells + '</tr>'
            H.append( ligne_titres ) # titres

            etudlink='<a href="formsemestre_bulletinetud?formsemestre_id=%s&etudid=%s&version=selectedevals">%s</a>'
            ir = 0
            nblines = len(F)-1
            for l in F[1:]:
                if ir == nblines-1:
                    el = l[1] # derniere ligne
                    cells = '<tr class="recap_row_moy sortbottom">'
                else:
                    el = etudlink % (formsemestre_id,l[-1],l[1])
                    if ir % 2 == 0:
                        cells = '<tr class="recap_row_even">'
                    else:
                        cells = '<tr class="recap_row_odd">'
                ir += 1
                nsn = [ x.replace('NA0', '-') for x in l[:-1] ] # notes sans le NA0
                cells += '<td class="recap_col">%s</td>' % nsn[0] # rang
                cells += '<td class="recap_col">%s</td>' % el # nom etud (lien)
                cells += '<td class="recap_col">%s</td>' % nsn[2] # groupetd
                # grise si moyenne generale < barre
                cssclass = 'recap_col_moy'
                try:
                    if float(nsn[3]) < NOTES_BARRE_GEN:
                        cssclass = 'recap_col_moy_inf'
                except:
                    pass
                cells += '<td class="%s">%s</td>' % (cssclass,nsn[3])
                for i in range(4,len(nsn)):
                    if i in ue_index:
                        cssclass = 'recap_col_ue'
                        # grise si moy UE < barre
                        try:
                            if float(nsn[i]) < NOTES_BARRE_UE:
                                cssclass = 'recap_col_ue_inf'
                            elif float(nsn[i]) >= NOTES_BARRE_VALID_UE:
                                cssclass = 'recap_col_ue_val'
                        except:
                            pass
                    else:
                        cssclass = 'recap_col'
                    cells += '<td class="%s">%s</td>' % (cssclass,nsn[i])
                H.append( cells + '</tr>' )
                #H.append( '<tr><td class="recap_col">%s</td><td class="recap_col">%s</td><td class="recap_col">' % (l[0],el) +  '</td><td class="recap_col">'.join(nsn) + '</td></tr>')
            H.append( ligne_titres )
            H.append('</table>')
            return '\n'.join(H)
        elif format == 'csv':
            CSV = CSV_LINESEP.join( [ CSV_FIELDSEP.join(x[:-1]) for x in F ] )
            semname = sem['titre'].replace( ' ', '_' )
            date = time.strftime( '%d-%m-%Y')
            filename = 'notes_modules-%s-%s.csv' % (semname,date)
            return sendCSVFile(REQUEST,CSV, filename )
        elif format == 'xls':
            semname = sem['titre'].replace( ' ', '_' )
            date = time.strftime( '%d-%m-%Y')
            filename = 'notes_modules-%s-%s.xls' % (semname,date)
            xls = sco_excel.Excel_SimpleTable(
                titles= F[0],
                lines = [ x[:-1] for x in F[1:] ], # sup. dern. col (etudid)
                SheetName = 'notes %s %s' % (semname,date) )
            return sco_excel.sendExcelFile(REQUEST, xls, filename )
        else:
            raise ValueError, 'unknown format %s' % format

    
    security.declareProtected(ScoView, 'do_formsemestre_bulletinetud')
    def do_formsemestre_bulletinetud(self, formsemestre_id, etudid,
                                     version='long', # short, long, selectedevals
                                     format='html', REQUEST=None, nohtml=False):
        if format != 'mailpdf':
            if format == 'xml':
                bul = repr(self.make_xml_formsemestre_bulletinetud(
                    formsemestre_id,  etudid, REQUEST=REQUEST ))
            else:
                bul, etud, filename = self.make_formsemestre_bulletinetud(
                    formsemestre_id, etudid,
                    version=version,format=format, REQUEST=REQUEST)
            if format == 'pdf':
                return sendPDFFile(REQUEST, bul, filename)        
            else:
                return bul
        else:
            # format mailpdf: envoie le pdf par mail a l'etud, et affiche le html
            if nohtml:
                htm = '' # speed up if html version not needed
            else:
                htm, junk, junk = self.make_formsemestre_bulletinetud(
                    formsemestre_id, etudid, version=version,format='html',
                    REQUEST=REQUEST)
            pdf, etud, filename = self.make_formsemestre_bulletinetud(
                formsemestre_id, etudid, version=version,format='pdf',
                REQUEST=REQUEST)
            if not etud['email']:
                return ('<div class="boldredmsg">%s n\'a pas d\'adresse e-mail !</div>'
                        % etud['nomprenom']) + htm
            #
            webmaster = getattr(self,'webmaster_email',"l'administrateur.")
            dept = unescape_html(getattr(self,'DeptName', ''))
            hea = """%(nomprenom)s,

vous trouverez ci-joint votre relevé de notes au format PDF.

Il s'agit d'un relevé provisoire n'ayant aucune valeur officielle
et susceptible de modifications.
Pour toute question sur ce document, contactez votre enseignant
ou le directeur des études (ne pas répondre à ce message).

Cordialement,
la scolarité du département %(dept)s.

PS: si vous recevez ce message par erreur, merci de contacter %(webmaster)s

""" % { 'nomprenom' : etud['nomprenom'], 'dept':dept, 'webmaster':webmaster }
            msg = MIMEMultipart()
            subj = Header( 'Relevé de note de %s' % etud['nomprenom'],  SCO_ENCODING )
            recipients = [ etud['email'] ] 
            msg['Subject'] = subj
            msg['From'] = getattr(self,'mail_bulletin_from_addr', 'noreply' )
            msg['To'] = ' ,'.join(recipients)
            msg['Bcc'] = 'viennet@iutv.univ-paris13.fr'
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

    security.declareProtected(ScoView, 'make_formsemestre_bulletinetud')
    def make_formsemestre_bulletinetud(
        self, formsemestre_id, etudid,
        version='long', # short, long, selectedevals
        format='html', REQUEST=None):        
        #
        authuser = REQUEST.AUTHENTICATED_USER
        if not version in ('short','long','selectedevals'):
            raise ValueError('invalid version code !')
        sem = self.do_formsemestre_list(args={ 'formsemestre_id' : formsemestre_id } )[0]
        nt = self.CachedNotesTable.get_NotesTable(self, formsemestre_id)
        ues = nt.get_ues( filter_sport=True, etudid=etudid )
        modimpls = nt.get_modimpls()
        nbetuds = len(nt.rangs)
        # Genere le HTML H, une table P pour le PDF
        H = [ '<table class="notes_bulletin">' ]
        P = []
        LINEWIDTH = 0.5
        from reportlab.lib.colors import Color
        PdfStyle = [ ('FONTNAME', (0,0), (-1,0), 'Helvetica-Bold'),
                     ('LINEBELOW', (0,0), (-1,0), LINEWIDTH, Color(0,0,0)) ]
        def ueline(i): # met la ligne i du tableau pdf en style 'UE'
            PdfStyle.append(('FONTNAME', (0,i), (-1,i), 'Helvetica-Bold'))
            PdfStyle.append(('BACKGROUND', (0,i), (-1,i),
                             Color(170/255.,187/255.,204/255.) ))
        # ligne de titres
        mg = fmt_note(nt.get_etud_moy(etudid)[0])
        etatstr = nt.get_etud_etat_html(etudid)
        t = ('Moyenne', mg + etatstr,
             'Rang %s / %d' % (nt.get_etud_rang(etudid), nbetuds),
             'Note/20', 'Coef')
        P.append(t)        
        H.append( '<tr><td class="note_bold">' +
                  '</td><td class="note_bold">'.join(t) + '</td></tr>' )
        # Contenu table: UE apres UE
        tabline = 0 # line index in table
        for ue in ues:
            tabline += 1
            # Ligne UE
            moy_ue = fmt_note(nt.get_etud_moy(etudid,ue_id=ue['ue_id'])[0])
            if ue['type'] == UE_SPORT:
                moy_ue = '(note spéciale)'
            t = ( ue['acronyme'], moy_ue, '', '', '' ) # xxx sum coef UE TODO
            P.append(t)
            ueline(tabline)
            H.append('<tr class="notes_bulletin_row_ue">')
            H.append('<td class="note_bold">%s</td><td class="note_bold">%s</td><td>%s</td><td>%s</td><td>%s</td></tr>' % t )
            # Liste les modules de l'UE 
            ue_modimpls = [ mod for mod in modimpls if mod['module']['ue_id'] == ue['ue_id'] ]
            for modimpl in ue_modimpls:
                    tabline += 1
                    H.append('<tr class="notes_bulletin_row_mod">')
                    # --- module avec moy. dans ce module et coef du module
                    nom_mod = modimpl['module']['abbrev']
                    if not nom_mod:
                        nom_mod = ''                        
                    t = [ modimpl['module']['code'], nom_mod,
                          fmt_note(nt.get_etud_mod_moy(modimpl, etudid)), '',
                          '%.2g' % modimpl['module']['coefficient'] ]
                    if version == 'short':
                        t[3], t[2] = t[2], t[3] # deplace colonne note
                    P.append(tuple(t))
                    link_mod = '<a class="bull_link" href="moduleimpl_status?moduleimpl_id=%s">' % modimpl['moduleimpl_id']
                    t[0] = link_mod + t[0] # add html link
                    t[1] = link_mod + t[1]
                    H.append('<td>%s</a></td><td>%s</a></td><td>%s</td><td>%s</td><td>%s</td></tr>' % tuple(t) )
                    if version != 'short':
                        # --- notes de chaque eval:
                        evals = nt.get_evals_in_mod(modimpl['moduleimpl_id'])
                        for e in evals:
                            if e['visibulletin'] == '1' or version == 'long':
                                tabline += 1
                                H.append('<tr class="notes_bulletin_row_eval">')
                                nom_eval = e['description']
                                if not nom_eval:
                                    nom_eval = 'le %s' % e['jour']
                                link_eval = '<a class="bull_link" href="evaluation_listenotes?evaluation_id=%s&liste_format=html&groupes%%3Alist=tous&tf-submit=OK">%s</a>' % (e['evaluation_id'], nom_eval)
                                val = e['notes'].get(etudid, {'value':'NP'})['value'] # NA si etud demissionnaire
                                val = fmt_note(val, note_max=e['note_max'] )
                                t = [ '', '', nom_eval, val, '%.2g' % e['coefficient'] ]
                                P.append(tuple(t))
                                t[2] = link_eval
                                H.append('<td>%s</td><td>%s</td><td class="bull_nom_eval">%s</td><td>%s</td><td class="bull_coef_eval">%s</td></tr>' % tuple(t))
        H.append('</table>')
        # --- Absences
        if sem['gestion_absence'] == '1':
            debut_sem = self.DateDDMMYYYY2ISO(sem['date_debut'])
            fin_sem = self.DateDDMMYYYY2ISO(sem['date_fin'])
            nbabs = self.Absences.CountAbs(etudid=etudid, debut=debut_sem, fin=fin_sem)
            nbabsjust = self.Absences.CountAbsJust(etudid=etudid,
                                               debut=debut_sem,fin=fin_sem)
            H.append("""<p>
        <a href="../Absences/CalAbs?etudid=%(etudid)s" class="bull_link">
        <b>Absences :</b> %(nbabs)s demi-journées, dont %(nbabsjust)s justifiées
        (pendant ce semestre).
        </a></p>
            """ % {'etudid':etudid, 'nbabs' : nbabs, 'nbabsjust' : nbabsjust } )
        # --- Decision Jury
        situation = self.etud_descr_situation_semestre( etudid, formsemestre_id )
        H.append( """<p class="bull_situation">%s</p>""" % situation )
        # --- Appreciations
        # le dir. des etud peut ajouter des appreciation,
        # mais aussi le chef (perm. ScoEtudInscrit)
        can_edit_app = ((authuser == sem['responsable_id'])
                        or (authuser.has_permission(ScoEtudInscrit,self)))
        cnx = self.GetDBConnexion()   
        apprecs = scolars.appreciations_list(
            cnx,
            args={'etudid':etudid, 'formsemestre_id' : formsemestre_id } )
        H.append('<div class="bull_appreciations">')
        if apprecs:
            H.append('<p><b>Appréciations</b></p>')
        for app in apprecs:
            if can_edit_app:
                mlink = '<a href="appreciation_add_form?id=%s">modifier</a> <a href="appreciation_add_form?id=%s&suppress=1">supprimer</a>'%(app['id'],app['id'])
            else:
                mlink = ''
            H.append('<p><span class="bull_appreciations_date">%s</span>%s<span class="bull_appreciations_link">%s</span></p>'
                         % (app['date'], app['comment'], mlink ) )
        if can_edit_app:
            H.append('<p><a href="appreciation_add_form?etudid=%s&formsemestre_id=%s">Ajouter une appréciation</a></p>' % (etudid, formsemestre_id))
        H.append('</div>')
        # ---------------
        if format == 'html':
            return '\n'.join(H), None, None
        elif format == 'pdf' or format == 'pdfpart':
            etud = self.getEtudInfo(etudid=etudid,filled=1)[0]
            if sem['gestion_absence'] == '1':
                etud['nbabs'] = nbabs
                etud['nbabsjust'] = nbabsjust
            infos = { 'DeptName' : self.DeptName }
            stand_alone = (format != 'pdfpart')
            if nt.get_etud_etat(etudid) == 'D':
                filigranne = 'DEMISSION'
            else:
                filigranne = ''
            pdfbul = pdfbulletins.pdfbulletin_etud(
                etud, sem, P, PdfStyle,
                infos, stand_alone=stand_alone, filigranne=filigranne,
                appreciations=[ x['comment'] for x in apprecs ],
                situation=situation )
            dt = time.strftime( '%Y-%m-%d' )
            filename = 'bul-%s-%s-%s.pdf' % (sem['titre'], dt, etud['nom'])
            filename = unescape_html(filename).replace(' ','_').replace('&','')
            return pdfbul, etud, filename
        else:
            raise ValueError('invalid parameter: format')

    security.declareProtected(ScoView, 'formsemestre_bulletins_pdf')
    def formsemestre_bulletins_pdf(self, formsemestre_id, REQUEST,
                                   version='selectedevals'):
        "Publie les bulletins dans un classeur PDF"
        cached = self.CachedNotesTable.get_bulletins_pdf(formsemestre_id,version)
        if cached:
            return sendPDFFile(REQUEST,cached[1],cached[0])
        fragments = []
        sem = self.do_formsemestre_list(args={ 'formsemestre_id' : formsemestre_id } )[0]
        # Make each bulletin
        nt = self.CachedNotesTable.get_NotesTable(self, formsemestre_id)
        bookmarks = {}
        i = 1
        for etudid in nt.get_etudids():
            fragments += self.do_formsemestre_bulletinetud(
                formsemestre_id, etudid, format='pdfpart',
                version=version, REQUEST=REQUEST )
            bookmarks[i] = nt.get_sexnom(etudid)
            i = i + 1
        #
        infos = { 'DeptName' : self.DeptName }
        pdfdoc = pdfbulletins.pdfassemblebulletins(fragments, sem, infos, bookmarks)
        #
        dt = time.strftime( '%Y-%m-%d' )
        filename = 'bul-%s-%s.pdf' % (sem['titre'], dt)
        filename = unescape_html(filename).replace(' ','_').replace('&','')
        # fill cache
        self.CachedNotesTable.store_bulletins_pdf(formsemestre_id,version,
                                                  (filename,pdfdoc))
        return sendPDFFile(REQUEST, pdfdoc, filename)

    security.declareProtected(ScoView, 'formsemestre_bulletins_mailetuds')
    def formsemestre_bulletins_mailetuds(self, formsemestre_id, REQUEST,
                                         version='long'):
        "envoi a chaque etudiant (inscrit et ayant un mail) son bulletin"
        sem = self.do_formsemestre_list(args={ 'formsemestre_id' : formsemestre_id } )[0]
        # Make each bulletin
        nt = self.CachedNotesTable.get_NotesTable(self, formsemestre_id)
        for etudid in nt.get_etudids():
            self.do_formsemestre_bulletinetud(
                formsemestre_id, etudid,
                version=version,
                format = 'mailpdf', nohtml=True, REQUEST=REQUEST )
        #
        return self.sco_header(self,REQUEST) + '<p>%d bulletins envoyés par mail !</p><p><a href="formsemestre_status?formsemestre_id=%s">continuer</a></p>' % (len(nt.get_etudids()),formsemestre_id) + self.sco_footer(self,REQUEST)

    security.declareProtected(ScoEnsView, 'appreciation_add_form')
    def appreciation_add_form(self, etudid=None, formsemestre_id=None,
                              id=None, # si id, edit
                              suppress=False, # si true, supress id
                              REQUEST=None ):
        "form ajout ou edition d'une appreciation"
        cnx = self.GetDBConnexion()
        authuser = REQUEST.AUTHENTICATED_USER
        if id: # edit mode
            app = scolars.appreciations_list( cnx, args={'id':id} )[0]
            formsemestre_id = app['formsemestre_id']
            etudid = app['etudid']
        if REQUEST.form.has_key('edit'):
            edit = int(REQUEST.form['edit'])
        elif id:
            edit = 1
        else:
            edit = 0
        sem = self.do_formsemestre_list(args={ 'formsemestre_id' : formsemestre_id } )[0]
        # check custom access permission
        can_edit_app = ((authuser == sem['responsable_id'])
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
        H = [self.sco_header(self,REQUEST) + '<h2>%s d\'une appréciation sur %s</h2>' % (a,etud['nomprenom']) ]
        F = self.sco_footer(self,REQUEST)
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
            self.CachedNotesTable.inval_cache(pdfonly=True)
            return REQUEST.RESPONSE.redirect( bull_url )
    # -------- Bulletin en XML
    # (fonction séparée pour simplifier le code,
    #  mais attention a la maintenance !)
    security.declareProtected(ScoView, 'make_xml_formsemestre_bulletinetud')
    def make_xml_formsemestre_bulletinetud( self, formsemestre_id, etudid,
                                            doc=None, # XML document
                                            REQUEST=None):
        "bulletin au format XML"
        if REQUEST:
            REQUEST.RESPONSE.setHeader('Content-type', XML_MIMETYPE)
        if not doc:            
            doc = jaxml.XML_document( encoding=SCO_ENCODING )
        doc.bulletinetud( etudid=etudid, formsemestre_id=formsemestre_id,
                          date=datetime.datetime.now().isoformat() )
        # infos sur l'etudiant
        etudinfo = self.getEtudInfo(etudid=etudid,filled=1)[0]
        doc._push()
        doc.etudiant( nom=etudinfo['nom'],
                      prenom=etudinfo['prenom'],
                      sexe=etudinfo['sexe'],
                      photo_url=self.etudfoto_img(etudid).absolute_url()
                      )
        doc._pop()
        # Note générale
        sem = self.do_formsemestre_list(args={ 'formsemestre_id' : formsemestre_id } )[0]
        nt = self.CachedNotesTable.get_NotesTable(self, formsemestre_id)
        ues = nt.get_ues()
        modimpls = nt.get_modimpls()
        nbetuds = len(nt.rangs)
        mg = fmt_note(nt.get_etud_moy(etudid)[0])
        doc._push()
        doc.note( value=mg )
        doc._pop()
        doc._push()
        doc.rang( value=nt.get_etud_rang(etudid), ninscrits=nbetuds )
        doc._pop()
        doc._push()
        doc.note_max( value=20 ) # notes toujours sur 20
        doc._pop()
        # Liste les UE / modules /evals
        for ue in ues:
            doc._push()
            doc.ue( id=ue['ue_id'], numero=ue['numero'],
                    acronyme=ue['acronyme'], titre=ue['titre'] )            
            doc._push()
            doc.note( value=fmt_note(nt.get_etud_moy(etudid,ue_id=ue['ue_id'])[0]) )
            doc._pop()
            # Liste les modules de l'UE 
            ue_modimpls = [ mod for mod in modimpls if mod['module']['ue_id'] == ue['ue_id'] ]
            for modimpl in ue_modimpls:
                mod = modimpl['module']
                doc._push()
                doc.module( id=modimpl['moduleimpl_id'], code=mod['code'],
                            coefficient=mod['coefficient'],
                            numero=mod['numero'],
                            titre=mod['titre'],
                            abbrev=mod['abbrev'] )                
                doc._push()
                doc.note( value=fmt_note(nt.get_etud_mod_moy(modimpl, etudid)) )
                doc._pop()
                # --- notes de chaque eval:
                evals = nt.get_evals_in_mod(modimpl['moduleimpl_id'])
                for e in evals:
                    doc._push()
                    doc.evaluation(jour=DateDMYtoISO(e['jour']),
                                   heure_debut=TimetoISO8601(e['heure_debut']),
                                   heure_fin=TimetoISO8601(e['heure_fin']),
                                   coefficient=e['coefficient'],
                                   description=e['description'])
                    val = e['notes'].get(etudid, {'value':'NP'})['value'] # NA si etud demissionnaire
                    val = fmt_note(val, note_max=e['note_max'] )
                    doc.note( value=val )
                    doc._pop()
                doc._pop()
            doc._pop()
        # --- Absences
        if sem['gestion_absence'] == '1':
            debut_sem = self.DateDDMMYYYY2ISO(sem['date_debut'])
            fin_sem = self.DateDDMMYYYY2ISO(sem['date_fin'])
            nbabs = self.Absences.CountAbs(etudid=etudid, debut=debut_sem, fin=fin_sem)
            nbabsjust = self.Absences.CountAbsJust(etudid=etudid,
                                               debut=debut_sem,fin=fin_sem)
            doc._push()
            doc.absences(nbabs=nbabs, nbabsjust=nbabsjust )
            doc._pop()
        # --- Decision Jury
        situation = self.etud_descr_situation_semestre( etudid, formsemestre_id )
        doc.situation( situation )
        # --- Appreciations
        cnx = self.GetDBConnexion() 
        apprecs = scolars.appreciations_list(
            cnx,
            args={'etudid':etudid, 'formsemestre_id' : formsemestre_id } )
        for app in apprecs:
            doc.appreciation( app['comment'], date=self.DateDDMMYYYY2ISO(app['date']))
        return doc

    # -------- Events
    security.declareProtected(ScoEnsView, 'appreciation_add_form')
    def etud_descr_situation_semestre(self, etudid, formsemestre_id, ne='' ):
        """chaine de caractères decrivant la situation de l'étudiant
        dans ce semestre"""
        cnx = self.GetDBConnexion()
        # semestre et UE validés ?
        evt_valid_sem, evt_echec_sem, ue_events = scolars.scolar_get_validated(
            cnx, etudid, formsemestre_id )
        # demission/inscription ?
        events = scolars.scolar_events_list(
            cnx, args={'etudid':etudid, 'formsemestre_id':formsemestre_id} )
        date_inscr = None
        date_dem = None
        date_echec = None
        for event in events:
            event_type = event['event_type']
            if event_type == 'INSCRIPTION':
                if date_inscr:
                    date_inscr += ', ' +   event['event_date'] + ' (!)'
                else:
                    date_inscr = event['event_date']
            elif event_type == 'DEMISSION':
                assert date_dem == None, 'plusieurs démissions !'
                date_dem = event['event_date']
            elif event_type == 'ECHEC_SEM':
                date_echec = event['event_date']
        if not date_inscr:
            inscr = 'Pas inscrit' + ne
        else:
            inscr = 'Inscrit%s le %s' % (ne, date_inscr)
        if date_dem:
            return inscr + '. Démission le %s.' % date_dem
        if evt_valid_sem:
            return inscr + ', obtenu le %s.' % evt_valid_sem['event_date']
        if date_echec:
            inscr += ', échec le %s.' % date_echec
            # indique UE validées
            if ue_events:
                uelist = []
                for ue_id in [ evt['ue_id'] for evt in ue_events ]:
                    ue = self.do_ue_list( args={ 'ue_id' : ue_id } )[0]
                    uelist.append(ue)
                uelist.sort( lambda x,y: cmp(x['numero'],y['numero']) )
                acros = ', '.join( [ ue['acronyme'] for ue in uelist ] )
                inscr += ' UE validées: ' + acros + '. '
            return inscr
        else:
            # ni echec ni valid: en cours ?
            return inscr + ' (en cours).'
    

    # --- FORMULAIRE POUR VALIDATION DES UE ET SEMESTRES
    security.declareProtected(ScoEtudInscrit, 'formsemestre_validation_form')
    def formsemestre_validation_form(self, formsemestre_id, etudid=None,
                                     REQUEST=None):
        """formulaire valisation semestre et UE
        Si etudid, traite un seul étudiant !
        """
        cnx = self.GetDBConnexion()
        sem = self.do_formsemestre_list(args={ 'formsemestre_id' : formsemestre_id } )[0]
        nt = self.CachedNotesTable.get_NotesTable(self, formsemestre_id)
        ues = nt.get_ues()
        T = nt.get_table_moyennes_triees()
        # Traite toute la promo ou un seul étudiant ?
        if REQUEST.form.has_key('etudid'):
            etudid = REQUEST.form['etudid']
        if etudid:
            # restreint T a cet étudiant (validation individuelle)
            for t in T:
                if t[-1] == etudid:
                    ok = 1
                    break
            if not ok:
                raise ScoValueError('etudid invalide (%s)' % etudid)
            T = [t]
            valid_individuelle = True            
            # XXX OK, la suite est inachevee (modif titre, prise en compte de l'etat
            # XXX courant de l'etudiant (sem et ue déjà validées) pour initialiser le form.            
        else:
            valid_individuelle = False
        
        # ------- Validations au dessus des barres
        sem_must_valid = {} # etudid : True|False
        ue_must_valid = {}  # ue_id : { etudid : True|False }
        for ue in ues:
            ue_must_valid[ue['ue_id']] = {}
        for t in T:
            etudid = t[-1]            
            # premiere passe sur les UE pour verif barres:
            barres_ue_ok = True
            iue = 0
            for ue in ues:
                iue += 1
                try:
                    if (float(t[iue]) < NOTES_BARRE_UE):
                        barres_ue_ok = False
                except:
                    barres_ue_ok = False # une UE sans note
            # valide semestre
            try:
                if (float(t[0]) >= NOTES_BARRE_GEN) and barres_ue_ok:
                    sem_must_valid[etudid] = True
                else:
                    sem_must_valid[etudid] = False
            except:
                sem_must_valid[etudid] = False # manque notes
            # valide les UE
            iue = 0
            for ue in ues:
                iue += 1
                try:
                    if (float(t[iue]) < NOTES_BARRE_VALID_UE) and not sem_must_valid[etudid]:
                        ue_must_valid[ue['ue_id']][etudid] = False
                    else:
                        ue_must_valid[ue['ue_id']][etudid] = True                    
                except:
                    ue_must_valid[ue['ue_id']][etudid] = False
            # et s'il est démissionnaire, il n'a rien
            if nt.get_etud_etat(etudid) == 'D':
                sem_must_valid[etudid] = False
                for ue in ues:
                    ue_must_valid[ue['ue_id']][etudid] = False
        
        # ------- Traitement des données formulaire
        date_jury = REQUEST.form.get('date_jury','')
        msg = ''
        semvalid = {}
        uevalid = {} # ue_id : { etudid : True|False }
        uevalid_byetud = {} # etudid : [ ue_id, ... ]
        for ue in ues:
            uevalid[ue['ue_id']] = {}
        if REQUEST.form.get('tf-submitted',False): # Soumission
            # recupere les etudiants du form
            for etudid in [t[-1] for t in T]:
                if sem_must_valid[etudid]:
                    semvalid[etudid] = 1 # happily ignore form
                else:
                    v = REQUEST.form.get('sem_%s'%etudid,None)
                    if v != None:
                        semvalid[etudid] = int(v)
                    else:
                        semvalid[etudid] = 0
                # recupere chaque UE validée
                for ue in ues:
                    if ue_must_valid[ue['ue_id']][etudid]:
                        uevalid[ue['ue_id']][etudid] = 1 # happily ignore form
                    else:
                        v = REQUEST.form.get('ue_%s_%s'%(ue['ue_id'],etudid),None)
                        if v != None:
                            uevalid[ue['ue_id']][etudid] = int(v)
                        else:
                            uevalid[ue['ue_id']][etudid] = 0
            # reconstruit la liste des ue valides pour chaque etud
            uevalid_byetud = {}
            for ue_id in uevalid.keys():
                for etudid in uevalid[ue_id].keys():
                    if not uevalid_byetud.has_key(etudid):
                        uevalid_byetud[etudid] = []
                    if uevalid[ue_id][etudid]:
                        uevalid_byetud[etudid].append(ue_id)                    
            # verification cohérence décision semestre/UE
            inconsistent_etuds = []
            for etudid in semvalid.keys():
                if semvalid[etudid]:
                    # le semestre valide, donc les UE doivent valider
                    for ue_id in uevalid.keys():
                        if not uevalid[ue_id][etudid]:
                            inconsistent_etuds.append(nt.get_nom_short(etudid))            
            #
            nbvalid = len([ x for x in semvalid.values() if x ])            
            msg = """<ul class="tf-msg">"""
            if inconsistent_etuds:
                msg += '<li class="tf-msg">Décisions incohérentes pour les étudiants suivants ! (si le semestre est validé, toutes les UE doivent l\'être)<ul><li>' + '</li><li>'.join( inconsistent_etuds ) + '</li></ul></li>'
            msg += '<li class="tf-msg">%d étudiants valident le semestre</li>' % nbvalid
            date_ok = False
            try:
                junk = DateDMYtoISO(date_jury)
                if junk:
                    date_ok = True
            except:
                pass
            if not date_ok:
                msg += '<li class="tf-msg">la date est incorrecte !</li>'
            if len(inconsistent_etuds)==0 and date_ok:
                msg += '<input type="submit" name="go" value="OK, valider ces décisions"/>'
            msg += '</ul>'
        else:
            # premier passage: initialise le form avec decisions antérieures s'il y en a
            for t in T:
                etudid = t[-1]
                sem_d, ue_ids = self._formsemestre_get_decision(
                    cnx, etudid, formsemestre_id )
                if sem_d == 2: # semestre validé
                    semvalid[etudid] = 1
                    for ue_id in uevalid.keys():
                        uevalid[ue_id][etudid] = 1
                else:
                    for ue_id in ue_ids:
                        if uevalid.has_key(ue_id):
                            # test car la formation peut avoir ete modifie
                            # apres saisie des decisions !
                            uevalid[ue_id][etudid] = 1
            #open('/tmp/toto','a').write('\n'+str(uevalid)+'\n')
        #
        if REQUEST.form.get('go',False) and len(inconsistent_etuds)==0:
            # OK, validation
            return self._do_formsemestre_validation(formsemestre_id, semvalid,
                                                    uevalid_byetud, REQUEST=REQUEST)
        
        # --- HTML head
        footer = self.sco_footer(self, REQUEST)
        if valid_individuelle:
            nomprenom = self.nomprenom(nt.identdict[etudid])
            header = self.sco_header(self,REQUEST,
                                     page_title='Validation du semestre %s pour %s'
                                     % (sem['titre'],nomprenom))
            H = [ """<h2>Validation (Jury) du semestre %s pour %s</h2>
            <p>Utiliser ce formulaire après la décision définitive du jury.</p>
            <p>Attention: les décisions prises ici remplacent et annulent les précédentes s'il y en avait !</p>
            """ % (sem['titre'],nomprenom)]
        else:
            header = self.sco_header(self,REQUEST,
                                     page_title="Validation du semestre "+sem['titre'])
            H = [ """<h2>Validation (Jury) du semestre %s</h2>
            <p>Utiliser ce formulaire après la décision définitive du jury.</p>
            <p>Les étudiants au dessus des "barres" vont valider automatiquement le semestre ou certaines UE.
            </p><p>Pour valider des étudiants sous les barres, cocher les cases correspondantes.</p>
            <p>Attention: les décisions prises ici remplacent et annulent les précédentes s'il y en avait !</p>
            <p>Attention: le formulaire va affecter TOUS LES ETUDIANTS !</p>
            """ % sem['titre'] ]
        
        H.append( """
        <form class="formvalidsemestre" method="POST">
        <input type="hidden" name="tf-submitted" value="1"/>
        <input type="hidden" name="formsemestre_id" value="%s"/>
        %s
        <p>Date du jury (j/m/a): <input type="text" name="date_jury" size="12" value="%s" /></p>
        <table class="notes_recapcomplet">
        <tr class="recap_row_tit"><td class="recap_tit">Rg</td><td class="recap_tit">Nom</td><td class="fvs_tit">Moy</td>
        <td class="fvs_tit_chk">Semestre</td>
        """ % (formsemestre_id,msg,date_jury) )        

        for ue in ues:
            H.append('<td class="fvs_tit">%s</td><td class="fvs_tit_chk">validée</td>' % ue['acronyme'])
        H.append('</tr>')
        # --- Generate form
        ir = 0
        for t in T:
            etudid = t[-1]
            if ir % 2 == 0:
                cls = 'recap_row_even'
            else:
                cls = 'recap_row_odd'
            ir += 1
            if sem_must_valid[etudid]:
                moycls = 'fvs_val'
            else:
                moycls = 'fvs_val_inf'
            if semvalid.has_key(etudid): # dans le formulaire
                if semvalid[etudid]:
                    sem_checked, sem_unchecked = "checked", ""
                    sem_is_valid = True
                else:
                    sem_checked, sem_unchecked = "", "checked"
                    sem_is_valid = False
            elif sem_must_valid[etudid]:
                sem_checked, sem_unchecked = "checked", ""
                sem_is_valid = True
            else:
                sem_checked, sem_unchecked = "", "checked"
                sem_is_valid = False
                
            H.append('<tr class="%s"><td>%s</td><td>%s</td><td class="%s">%s</td>'
                     % (cls, nt.get_etud_rang(etudid), nt.get_nom_short(etudid),
                        moycls, fmt_note(t[0]) ))
            # ne propose que si sous la barre
            if sem_must_valid[etudid]:
                H.append('<td class="fvs_chk">validé</td>')
            elif nt.get_etud_etat(etudid) == 'D':
                H.append('<td class="fvs_chk">démission</td>')
            else:
                H.append("""<td class="fvs_chk">
                <input type="radio" name="sem_%s" value="1" %s/>O&nbsp;
                <input type="radio" name="sem_%s" value="0" %s/>N
                </td>            
                """ % (etudid,sem_checked,etudid,sem_unchecked))
            # UEs
            iue = 0
            for ue in ues:
                iue += 1
                if uevalid[ue['ue_id']].has_key(etudid): # dans le formulaire
                    if uevalid[ue['ue_id']][etudid]:
                        sem_checked, sem_unchecked = "checked", ""
                    else:
                        sem_checked, sem_unchecked = "", "checked"
                elif ue_must_valid[ue['ue_id']][etudid]:
                    sem_checked, sem_unchecked = "checked", ""
                else:
                    sem_checked, sem_unchecked = "", "checked"
                # ne propose les UE que si le semestre est sous la barre
                if ue_must_valid[ue['ue_id']][etudid]:
                    H.append('<td class="fvs_val">%s</td><td class="fvs_chk">valid.</td>'
                             % (t[iue],))
                elif nt.get_etud_etat(etudid) == 'D':
                    H.append('<td class="fvs_val"></td><td class="fvs_chk"></td>')
                else:
                    H.append("""<td class="fvs_val_inf">%s</td><td class="fvs_chk">
                    <input type="radio" name="ue_%s_%s" value="1" class="radio_green" %s/>O&nbsp;
                    <input type="radio" name="ue_%s_%s" value="0" class="radio_red" %s/>N
                    </td>            
                    """ % (t[iue],ue['ue_id'],etudid,sem_checked,ue['ue_id'],etudid,sem_unchecked))
            #
            H.append('</tr>')
        # ligne titres en bas
        H.append('<tr class="recap_row_tit"><td></td><td></td><td class="fvs_tit">Moy</td><td class="fvs_tit_chk">Semestre</td>')
        for ue in ues:
            H.append('<td class="fvs_tit">%s</td><td class="fvs_tit_chk"></td>' % ue['acronyme'])
        H.append('</tr></table>')
        if valid_individuelle:
            H.append('<input type="hidden" name="etudid" value="%s" />' % etudid)
        
        #
        H.append("""<input type="submit" name="submit" value="Vérifier" /></form>""")
        return header + '\n'.join(H) + footer

    security.declareProtected(ScoEtudInscrit, '_do_formsemestre_validation')
    def _do_formsemestre_validation(self, formsemestre_id, semvalid, uevalid_byetud,
                                    date_jury=None, REQUEST=None):
        # effectue la validation des semestres et UE indiques
        cnx = self.GetDBConnexion()
        # semestres
        for etudid in semvalid.keys():
            scolars.scolar_validate_sem( cnx, etudid,
                                         formsemestre_id, valid=semvalid[etudid],
                                         event_date=date_jury,
                                         REQUEST=REQUEST)
        # UE
        for etudid in uevalid_byetud.keys():
            scolars.scolar_validate_ues(cnx, etudid, formsemestre_id, 
                                        uevalid_byetud[etudid], event_date=date_jury,
                                        suppress_previously_validated=True,
                                        REQUEST=REQUEST)
        # Inval cache bulletins
        self.CachedNotesTable.inval_cache(formsemestre_id=formsemestre_id)
        #
        return REQUEST.RESPONSE.redirect(
            'formsemestre_validation_list?formsemestre_id=%s'%formsemestre_id)
    
    security.declareProtected(ScoEnsView, 'formsemestre_validation_list')
    def formsemestre_validation_list(self,formsemestre_id, REQUEST):
        "Liste les UE et semestres validés"
        cnx = self.GetDBConnexion()
        nt = self.CachedNotesTable.get_NotesTable(self, formsemestre_id)
        sem = self.do_formsemestre_list(args={ 'formsemestre_id' : formsemestre_id } )[0]
        header = self.sco_header(self,REQUEST)
        footer = self.sco_footer(self, REQUEST)
        H = [ """<h2>Etudiants validant le semestre %s</h2>
        <table><tr><td>Nom</td><td>Décision</td><td>UE validées</td></tr>"""
              % sem['titre'] ]        
        #
        for e in nt.inscrlist: # ici par ordre alphabetique
            etudid = e['etudid']
            valid, decision, acros = self._formsemestre_get_decision_str(cnx, etudid, formsemestre_id)
            #
            H.append( '<tr><td>%s</td><td>%s</td><td>%s</td></tr>'
                      % (self.nomprenom(nt.identdict[etudid]), decision, acros) )
        H.append('</table>')
        return header + '\n'.join(H) + footer

    def _formsemestre_get_decision_str(self, cnx, etudid, formsemestre_id ):
        """Chaine HTML decrivant la decision du jury pour cet etudiant.
        Resultat: True/False, decision, description des UE validees    
        """
        sem_d, ue_ids = self._formsemestre_get_decision(cnx, etudid, formsemestre_id )
        decision = [ '<em>en cours</em>', 'démission', 'validé', 'refusé' ][sem_d]
        if sem_d == 2:
            valid = True
        else:
            valid = False
        uelist = []
        acros = ''
        for ue_id in ue_ids:
            # XXX a optimiser: chercher les UE en dehors de la boucle !
            ue = self.do_ue_list( args={ 'ue_id' : ue_id } )[0]
            uelist.append(ue)
        uelist.sort( lambda x,y: cmp(x['numero'],y['numero']) )
        acros = ', '.join( [ ue['acronyme'] for ue in uelist ] )
        return valid, decision, acros
    
    def _formsemestre_get_decision(self, cnx, etudid, formsemestre_id ):
        """Semestre et liste des UE validées
        Resultat: semestre, [ ue_id ]
        ou semestre = 0 si en cours, 1 si démission, 2 si validé, 3 si refusé
        """
        nt = self.CachedNotesTable.get_NotesTable(self, formsemestre_id)
        evt_valid_sem, evt_echec_sem, ue_events = scolars.scolar_get_validated(
            cnx, etudid, formsemestre_id)
        if nt.get_etud_etat(etudid) == 'D':
            sem_d = 1
        elif evt_valid_sem:
            sem_d = 2
        elif evt_echec_sem:
            sem_d = 3
        else:
            sem_d = 0
        if not evt_valid_sem and ue_events:
            ue_ids = [ evt['ue_id'] for evt in ue_events ]
        else:
            ue_ids = []
        return sem_d, ue_ids

    # ------------- Feuille excel pour preparation des jurys
    security.declareProtected(ScoView,'do_feuille_preparation_jury')
    def do_feuille_preparation_jury(self, formsemestre_id1, formsemestre_id2, REQUEST):
        "Feuille excel pour preparation des jurys"
        nt1 = self.CachedNotesTable.get_NotesTable(self, formsemestre_id1)
        nt2 = self.CachedNotesTable.get_NotesTable(self, formsemestre_id2)
        # construit { etudid : [ ident, { formsemestre_id : (moyennes) } ] }
        # (fusionne les liste d'etudiants qui peuvent differer d'un semestre a l'autre)
        R = {}
        Tdict = nt1.get_table_moyennes_dict()
        for etudid in Tdict.keys():
            R[etudid] = [ nt1.identdict[etudid], { formsemestre_id1 : Tdict[etudid] } ]
        Tdict = nt2.get_table_moyennes_dict()
        for etudid in Tdict.keys():
            if R.has_key(etudid):
                R[etudid][1][formsemestre_id2] = Tdict[etudid]
            else:
                R[etudid] = [ nt2.identdict[etudid], { formsemestre_id2 : Tdict[etudid] } ]
        ues_sems = { formsemestre_id1 : nt1.get_ues(), formsemestre_id2 : nt2.get_ues() }
        # Contruit table pour export excel
        # Nom, Prenom, Naissance, Cursus (?), moy sem. 1, moy sem 2
        head = ['Nom', 'Prénom', 'Date Naissance', 'Cursus']
        for nt in (nt1,nt2):
            for ue in nt.get_ues():
                head.append(ue['acronyme'])
            head += ['Moy', 'Décision Comm.', 'Compensation' ]
        titres_sems = ['','','','']
        for nt in (nt1,nt2):
            titres_sems += [ '%s du %s au %s'%(unquote(nt.sem['titre']), # export xls, pas html
                                               nt.sem['date_debut'], nt.sem['date_fin']) ]
            titres_sems += ['']*(len(ues_sems[nt.sem['formsemestre_id']])+2)
        L = [ titres_sems ]
        # forme la liste des etudids tries par noms
        etudids = [ (R[k][0]['nom'], k) for k in R.keys() ] # (nom, etudid)
        etudids.sort()
        etudids = [ x[1] for x in etudids ]
        for etudid in etudids:
            ident = R[etudid][0]
            l = [ ident['nom'], ident['prenom'], ident['annee_naissance'], '' ]
            for formsemestre_id in (formsemestre_id1, formsemestre_id2):
                t = R[etudid][1].get(formsemestre_id,None)
                if not t:
                    l += ['']*(len(ues_sems[formsemestre_id])+3)
                else:
                    iue = 0
                    for ues in ues_sems[formsemestre_id]:
                        iue += 1
                        l.append(t[iue])
                    l.append(t[0])
                    l += ['',''] # decision com, compensation
            L.append(l)
        # 
        xls = sco_excel.Excel_SimpleTable( titles=head, lines=L, SheetName='Notes' )
        return sco_excel.sendExcelFile(REQUEST, xls, 'RecapMoyennesJury.xls' )

    security.declareProtected(ScoView,'feuille_preparation_jury')
    def feuille_preparation_jury(self,formsemestre_id, REQUEST):
        "choix semestre precedent pour feuille jury"
        sem = self.do_formsemestre_list(args={ 'formsemestre_id' : formsemestre_id } )[0]
        H = [ self.sco_header(self,REQUEST) ]
        H.append( """<p>
        Cette fonction va générer une feuille Excel avec les moyennes de deux semestres,
        pour présentation en jury de fin d'année.</p>
        <p>Le semestre courant est: %s (%s - %s)</p>
        <p>Choissisez le semestre "précédent".</p>
        <form method="GET" action="do_feuille_preparation_jury">
        <input type="hidden" name="formsemestre_id2" value="%s"/>
        """ % (sem['titre'], sem['date_debut'], sem['date_fin'], formsemestre_id) )
        sems = self.do_formsemestre_list()
        othersems = []
        d,m,y = [ int(x) for x in sem['date_fin'].split('/') ]
        date_fin_origine = datetime.date(y,m,d)
        for s in sems:
            if s['formsemestre_id'] == formsemestre_id:
                continue # saute le semestre d'où on vient
            if s['date_debut']:
                d,m,y = [ int(x) for x in s['date_debut'].split('/') ]
                datedebut = datetime.date(y,m,d)
                if datedebut > date_fin_origine:
                    continue # ne mentionne pas les semestres situes apres
            s['titremenu'] = s['titre'] + '&nbsp;&nbsp;(%s - %s)' % (s['date_debut'],s['date_fin'])
            othersems.append(s)  
        menulist = []
        for o in othersems:
            s = ''
            menulist.append(
                '<option value="%s" %s>%s</option>' % (o['formsemestre_id'],s,o['titremenu']) )
        
        H.append( '<p><b>Semestre destination:</b> <select name="formsemestre_id1">'
                  + '\n '.join(menulist) + '</select></p>' )
        H.append("""<input type="submit" value="Générer feuille"/></form>""")
        H.append(self.sco_footer(self, REQUEST))
        return '\n'.join(H)

        
        
    # ------------- INSCRIPTIONS: PASSAGE D'UN SEMESTRE A UN AUTRE
    security.declareProtected(ScoEtudInscrit,'formsemestre_inscr_passage')
    def formsemestre_inscr_passage(self, formsemestre_id, REQUEST=None):
        """Form. pour inscription rapide des etudiants d'un semestre dans un autre
        Permet de (de)selectionner parmi les etudiants inscrits (non demissionnaires).        
        Les etudiants sont places dans le groupe "A"
        """
        cnx = self.GetDBConnexion()
        sem = self.do_formsemestre_list(args={ 'formsemestre_id' : formsemestre_id } )[0]
        nt = self.CachedNotesTable.get_NotesTable(self, formsemestre_id)
        T = nt.get_table_moyennes_triees()
        header = self.sco_header(self,REQUEST)
        footer = self.sco_footer(self, REQUEST)
        #
        passe = {} # etudid qui passent
        already_inscr = {} # etudid deja inscrits (pour eviter double sinscriptions)
        next_semestre_id = None
        info = ''
        if REQUEST.form.get('tf-submitted',False):
            # --- soumission
            # - formulaire passage
            for etudid in [t[-1] for t in T]:
                v = REQUEST.form.get('pas_%s'%etudid,None)
                if v != None:
                    passe[etudid] = int(v)
            # - etudiants dans le semestre selectionne
            next_semestre_id = REQUEST.form.get('next_semestre_id',None)
            ins = self.Notes.do_formsemestre_inscription_list(
                args={  'formsemestre_id' : next_semestre_id, 'etat' : 'I' } )
            next_sem = self.do_formsemestre_list(args={'formsemestre_id':next_semestre_id})[0]
            info = ('<p>Information: <b>%d</b> étudiants déjà inscrits dans le semestre %s</p>'
                    % (len(ins), next_sem['titre']))
            for i in ins:
                already_inscr[i['etudid']] = True
                
        if REQUEST.form.get('inscrire',False):
            # --- Inscription de tous les etudiants selectionnes non deja inscrits
            # - recupere les groupes TD/TP d'origine
            ins =  self.Notes.do_formsemestre_inscription_list(
                args={  'formsemestre_id' : formsemestre_id } )
            gr = {}
            for i in ins:
                gr[i['etudid']] = { 'groupetd' : i['groupetd'],
                                    'groupeanglais' : i['groupeanglais'],
                                    'groupetp' : i['groupetp'] }
            # - inscription de chaque etudiant
            inscrits = []
            for t in T:
                etudid = t[-1]                
                if passe.has_key(etudid) and passe[etudid] \
                       and not already_inscr.has_key(etudid):
                    inscrits.append(etudid)
                    args={ 'formsemestre_id' : next_semestre_id,
                           'etudid' : etudid,
                           'etat' : 'I' }
                    args.update(gr[etudid])
                    self.do_formsemestre_inscription_with_modules(
                        args = args, 
                        REQUEST = REQUEST,
                        method = 'formsemestre_inscr_passage' )
            H = '<p>%d étudiants inscrits : <ul><li>' % len(inscrits)            
            if len(inscrits) > 0:
                H += '</li><li>'.join(
                    [ self.nomprenom(nt.identdict[eid]) for eid in inscrits ]
                    ) + '</li></ul></p>'
            return header + H + footer
        #
        # --- HTML head
        H = [ """<h2>Passage suite au semestre %s</h2>
        <p>Inscription des étudiants du semestre dans un autre.</p>
        <p>Seuls les étudiants inscrits (non démissionnaires) sont mentionnés.</p>
        <p>Rappel: d'autres étudiants peuvent être inscrits individuellement par ailleurs
        (et ceci à tout moment).</p>
        <p>Le choix par défaut est de proposer le passage à tous les étudiants ayant validé
        le semestre. Vous devez sélectionner manuellement les autres qui vous voulez faire
        passer sans qu'ils aient validé le semestre.</p>
        <p>Les étudiants seront ensuite inscrits à <em>tous les modules</em> constituant le
        semestre choisi (attention si vous avez des parcours optionnels, vous devrez les désinscrire
        des modules non désirés ensuite).<p>
        <p>Les étudiants seront inscrit dans les mêmes <b>groupes de TD</b> et TP
        que ceux du semestres qu'ils terminent. Pensez à modifier les groupes par
        la suite si nécessaire.
        </p>
        <p><b>Vérifiez soigneusement le <font color="red">semestre de destination</font> !</b></p>
        """ % (sem['titre'],) ]
        H.append("""<form method="POST">
        <input type="hidden" name="tf-submitted" value="1"/>
        <input type="hidden" name="formsemestre_id" value="%s"/>
        """ % (formsemestre_id,) )
        # menu avec liste des semestres débutant a moins de 123 jours (4 mois)
        # de la date de fin du semestre d'origine.
        sems = self.do_formsemestre_list()
        othersems = []
        d,m,y = [ int(x) for x in sem['date_fin'].split('/') ]
        date_fin_origine = datetime.date(y,m,d)
        delais = datetime.timedelta(123) # 123 jours ~ 4 mois
        for s in sems:
            if s['formsemestre_id'] == formsemestre_id:
                continue # saute le semestre d'où on vient
            if s['date_debut']:
                d,m,y = [ int(x) for x in s['date_debut'].split('/') ]
                datedebut = datetime.date(y,m,d)
                if abs(date_fin_origine - datedebut) > delais:
                    continue # semestre trop ancien
            s['titremenu'] = s['titre'] + '&nbsp;&nbsp;(%s - %s)' % (s['date_debut'],s['date_fin'])
            othersems.append(s)
        if not othersems:
            raise ScoValueError('Aucun autre semestre de formation défini !')
        menulist = []
        for o in othersems:
            if o['formsemestre_id'] == next_semestre_id:
                s = 'selected'
            else:
                s = ''
            menulist.append(
                '<option value="%s" %s>%s</option>' % (o['formsemestre_id'],s,o['titremenu']) )
        
        H.append( '<p><b>Semestre destination:</b> <select name="next_semestre_id">'
                  + '\n '.join(menulist) + '</select></p>' )
        H.append(info)
        # --- Liste des etudiants
        H.append("""<p>Cocher les étudiants à faire passer (à inscrire) :</p>
        <table class="notes_recapcomplet">
        <tr class="recap_row_tit"><td class="recap_tit">Nom</td>
                                  <td>Décision jury</td><td>Passage ?</td><td></td>
        </tr>
        """)
        ir = 0
        for t in T:
            etudid = t[-1]
            if ir % 2 == 0:
                cls = 'recap_row_even'
            else:
                cls = 'recap_row_odd'
            ir += 1
            valid, decision, acros = self._formsemestre_get_decision_str(cnx, etudid, formsemestre_id)
            comment = ''
            if acros:
                acros = '(%s)' % acros # liste des UE validees
            if passe.has_key(etudid): # form (prioritaire)
                valid = passe[etudid]
            if already_inscr.has_key(etudid):
                valid = False # deja inscrit dans semestre destination
                comment = 'déjà inscrit dans ' + next_sem['titre']
            if valid: 
                checked, unchecked = 'checked', ''
                cellfmt = 'greenboldtext'
            else:
                checked, unchecked = '', 'checked'
                cellfmt = 'redboldtext'
            H.append('<tr class="%s"><td class="%s">%s</td><td class="%s">%s %s</td>'
                     % (cls, cellfmt, self.nomprenom(nt.identdict[etudid]),
                        cellfmt, decision, acros) )
            # checkbox pour decision passage
            H.append("""<td>
            <input type="radio" name="pas_%s" value="1" %s/>O&nbsp;
            <input type="radio" name="pas_%s" value="0" %s/>N
            </td><td>%s</td></tr>
            """ % (etudid, checked, etudid, unchecked, comment) )
            
        #
        H.append("""</table>
        <p>
        <input type="submit" name="check" value="Vérifier ces informations" />
        &nbsp;
        <input type="submit" name="inscrire" value="Inscrire les étudiants choisis !" />
        </p></form>""")
        return header + '\n'.join(H) + footer

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
    notes = [ x for x in notes if (x != None) and (x != NOTES_NEUTRALISE) ]
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


    

