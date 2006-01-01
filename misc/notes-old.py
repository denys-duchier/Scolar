# -*- mode: python -*-
# -*- coding: iso8859-15 -*-

import pdb,os,sys,time
import urllib

# adjust path for Zope:
if os.environ.has_key('INSTANCE_HOME'):
    sys.path.append(os.environ['INSTANCE_HOME']+'/Extensions')
    
from notesusers import *
from notesdb import *
from TrivialFormulator import TrivialFormulator, TF
import scolars
from notes_log import log

NOTES_PRECISION=1e-4 # evite eventuelles erreurs d'arrondis
NOTES_MIN = 0.       # valeur minimale admise pour une note
NOTES_MAX = 100.
NOTES_NEUTRALISE=-1000. # notes non prises en comptes dans moyennes

CSV_FIELDSEP = ';'
CSV_LINESEP  = '\n'
CSV_MIMETYPE = 'text/comma-separated-values';

# --- Exceptions
MSGPERMDENIED="l'utilisateur %s n'a pas le droit d'effectuer cette operation"

class NoteProcessError(Exception):
    "misc errors in process"
    pass

class NotImplementedError(NoteProcessError):
    pass

class NotesUserExists(NoteProcessError):
    pass

class InvalidEtudId(NoteProcessError):
    pass

# ---------------------------
class CacheTable:
    """gestion rudimentaire de cache pour les NotesTables"""
    def __init__(self):
        log('new CacheTable')
        self.cache = {} # { formsemestre_id : NoteTable instance }
    
    def get_NotesTable(self,uid,formsemestre_id):
        if self.cache.has_key(formsemestre_id):
            #log('cache hit %s' % formsemestre_id)
            return self.cache[formsemestre_id]
        else:
            nt = NotesTable(uid,formsemestre_id)
            self.cache[formsemestre_id] = nt
            log('caching formsemestre_id=%s' % formsemestre_id ) 
            return nt
    
    def inval_cache(self, formsemestre_id=None):
        "expire cache pour un semestre (ou tous si pas d'argument)"
        log('inval_cache, formsemestre_id=%s' % formsemestre_id)
        if formsemestre_id is None:
            self.cache = {}
        else:
            del self.cache[formsemestre_id]

CNT = CacheTable()

    
# ---------------------------


""" --- Gestion des formations
"""
_formationEditor = EditableTable(
    'notes_formations',
    'formation_id',
    'ViewInfosFormation', 
    'CreateFormation',
    ('formation_id', 'acronyme','titre'),
    callback_on_write=CNT.inval_cache
    )

notes_formation_create = _formationEditor.create
notes_formation_delete = _formationEditor.delete
notes_formation_list   = _formationEditor.list
notes_formation_edit   = _formationEditor.edit

""" --- Gestion des UE
"""
_ueEditor = EditableTable(
    'notes_ue',
    'ue_id',
    'ViewInfosFormation',
    'CreateFormation',
    ('ue_id', 'formation_id', 'acronyme', 'numero', 'titre'),
    sortkey='numero',
    output_formators = { 'numero' : int_null_is_zero },
    callback_on_write=CNT.inval_cache
    )

notes_ue_create   = _ueEditor.create
notes_ue_delete   = _ueEditor.delete
notes_ue_list     = _ueEditor.list
notes_ue_edit     = _ueEditor.edit

""" --- Gestion des matières
"""
_matiereEditor = EditableTable(
    'notes_matieres',
    'matiere_id',
    'ViewInfosFormation',
    'CreateFormation',
    ('matiere_id', 'ue_id', 'numero', 'titre'),
    sortkey='numero',
    output_formators = { 'numero' : int_null_is_zero },
    callback_on_write=CNT.inval_cache
    )

notes_matiere_create   = _matiereEditor.create
notes_matiere_delete   = _matiereEditor.delete
notes_matiere_list     = _matiereEditor.list
notes_matiere_edit     = _matiereEditor.edit


""" --- Gestion des Modules
"""

_moduleEditor = EditableTable(
    'notes_modules',
    'module_id',
    'ViewInfosFormation',
    'CreateFormation',
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
    callback_on_write=CNT.inval_cache
    )

notes_module_create = _moduleEditor.create
notes_module_delete = _moduleEditor.delete
notes_module_list   = _moduleEditor.list
notes_module_edit   = _moduleEditor.edit


""" --- Semestres de formation
"""
_formsemestreEditor = EditableTable(
    'notes_formsemestre',
    'formsemestre_id',
    'ViewInfosFormation',
    'CreateFormation',
    ('formsemestre_id', 'semestre_id', 'formation_id','titre',
     'date_debut', 'date_fin', 'responsable_id'),
    sortkey = 'date_debut',
    output_formators = { 'date_debut' : DateISOtoDMY,
                         'date_fin'   : DateISOtoDMY,
                         },
    input_formators  = { 'date_debut' : DateDMYtoISO,
                         'date_fin'   : DateDMYtoISO,
                         'responsable_id' : notes_user_create_ifdontexist },
    callback_on_write=CNT.inval_cache
    )

notes_formsemestre_create = _formsemestreEditor.create
notes_formsemestre_delete = _formsemestreEditor.delete
notes_formsemestre_list   = _formsemestreEditor.list
notes_formsemestre_edit   = _formsemestreEditor.edit

def notes_formsemestre_createwithmodules( REQUEST, userlist, edit=False ):
    AUTHENTICATED_USER = str(REQUEST.AUTHENTICATED_USER)
    # Check permission:  ImplementFormation
#    if not notes_user_has_permission(AUTHENTICATED_USER, 'ImplementFormation'):
#        raise AccessDenied
    formation_id = REQUEST.form['formation_id']
    if not edit:
        initvalues = {}
        semestre_id  = REQUEST.form['semestre_id']
    else:
        # setup form init values
        formsemestre_id = REQUEST.form['formsemestre_id']
        initvalues = notes_formsemestre_list( AUTHENTICATED_USER,
                                              {'formsemestre_id' : formsemestre_id})[0]
        semestre_id = initvalues['semestre_id']
        # add associated modules to tf-checked
        ams = notes_moduleimpl_list( AUTHENTICATED_USER,
                                     { 'formsemestre_id' : formsemestre_id } )
        initvalues['tf-checked'] = [ x['module_id'] for x in ams ]
        for x in ams:
            initvalues[str(x['module_id'])] = x['responsable_id']

    # Liste des modules  dans ce semestre de cette formation
    # on pourrait faire un simple notes_module_list( )
    # mais si on veut l'ordre du PPN (groupe par UE et matieres il faut:
    mods = [] # liste de dicts, as usual
    uelist = notes_ue_list( AUTHENTICATED_USER, { 'formation_id' : formation_id } )
    for ue in uelist:
        matlist = notes_matiere_list( AUTHENTICATED_USER, { 'ue_id' : ue['ue_id'] } )
        for mat in matlist:
            modsmat = notes_module_list(AUTHENTICATED_USER, { 'matiere_id' : mat['matiere_id'] })
            mods = mods + modsmat
    
#    mods = notes_module_list( AUTHENTICATED_USER,
#                              { 'formation_id' : formation_id, 'semestre_id' : semestre_id } )
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
        ('sep', { 'input_type' : 'separator',
                  'title' : '<h3>Sélectionner les modules et leur responsable:</h3>' }) ]
    for mod in mods:
        modform.append( (str(mod['module_id']),
                         { 'input_type' : 'menu',
                           'withcheckbox' : True,
                           'title' : '%s %s' % (mod['code'],mod['titre']),
                           'allowed_values' : userlist }) )
    if edit:
        submitlabel = 'Modifier ce semestre de formation'
    else:
        submitlabel = 'Créer ce semestre de formation'
    tf = TrivialFormulator( REQUEST.URL0, REQUEST.form, modform,
                            submitlabel = submitlabel,
                            cancelbutton = 'Annuler',
                            initvalues = initvalues)
    if tf[0] == 0:
        return tf[1] + '<p>' + str(initvalues)
    elif tf[0] == -1:
        return '<h4>annulation</h4>'
    else:
        if not edit:
            # creation du semestre
            formsemestre_id = notes_formsemestre_create(AUTHENTICATED_USER,tf[2])
            # creation des modules
            for module_id in tf[2]['tf-checked']:
                mod_resp_id = tf[2][module_id]
                modargs = { 'module_id' : module_id,
                            'formsemestre_id' : formsemestre_id,
                            'responsable_id' :  mod_resp_id }
                mid = notes_moduleimpl_create(AUTHENTICATED_USER,modargs)
            return 'ok<br>' + str(tf[2])
        else:
            # modification du semestre:
            # on doit creer les modules nouvellement selectionnés
            # modifier ceux a modifier, et DETRUIRE ceux qui ne sont plus selectionnés.
            # Note: la destruction echouera s'il y a des objets dependants
            #       (eg des etudiants inscrits ou des evaluations définies)
            notes_formsemestre_edit(AUTHENTICATED_USER,tf[2])
            # nouveaux modules
            checkedmods = tf[2]['tf-checked']
            ams = notes_moduleimpl_list( AUTHENTICATED_USER,
                                         { 'formsemestre_id' : formsemestre_id } )
            existingmods = [ x['module_id'] for x in ams ]
            mods_tocreate = [ x for x in checkedmods if not x in existingmods ]
            # modules a existants a modifier
            mods_toedit = [ x for x in checkedmods if x in existingmods ]
            # modules a detruire
            mods_todelete = [ x for x in existingmods if not x in checkedmods ]
            #
            for module_id in mods_tocreate:
                modargs = { 'module_id' : module_id,
                            'formsemestre_id' : formsemestre_id,
                            'responsable_id' :  tf[2][module_id] }
                notes_moduleimpl_create(AUTHENTICATED_USER,modargs)
            for module_id in mods_todelete:
                # get id
                moduleimpl_id = notes_moduleimpl_list(AUTHENTICATED_USER,
                                                      { 'formsemestre_id' : formsemestre_id,
                                                        'module_id' : module_id } )[0]['moduleimpl_id']
                notes_moduleimpl_delete(AUTHENTICATED_USER,moduleimpl_id)
            for module_id in mods_toedit:
                moduleimpl_id = notes_moduleimpl_list(AUTHENTICATED_USER,
                                                      { 'formsemestre_id' : formsemestre_id,
                                                        'module_id' : module_id } )[0]['moduleimpl_id']
                modargs = {
                    'moduleimpl_id' : moduleimpl_id,
                    'module_id' : module_id,
                    'formsemestre_id' : formsemestre_id,
                    'responsable_id' :  tf[2][module_id] }
                notes_moduleimpl_edit(AUTHENTICATED_USER,modargs)
            return 'edit ok<br>' + str(tf[2])


""" --- Gestion des "Implémentations de Modules"
     Un "moduleimpl" correspond a la mise en oeuvre d'un module
     dans une formation spécifique, à une date spécifique.
"""

class ModuleImplEditor(EditableTable):
    def create(self, uid, args ):
        "create moduleimpl, then add role"
        mid = EditableTable.create(self, uid, args)
        # give roles:
        self._give_role_to_resp(mid, args['responsable_id'])
        return mid
    def edit(self,uid, args):
        moduleimpl_id = args['moduleimpl_id']
        old_mod = notes_moduleimpl_list(uid,{'moduleimpl_id':moduleimpl_id})[0]
        old_resp_id = old_mod['responsable_id']
        # add new resp.
        self._give_role_to_resp( moduleimpl_id, args['responsable_id'])
        # change
        EditableTable.edit(self, uid, args )
        # remove old responsable
        notes_user_removeroles(old_resp_id,
                               [(RespModule, 'moduleimpl_id', moduleimpl_id)])
        
    def _give_role_to_resp(self, moduleimpl_id, responsable_id):
        notes_user_create_and_giveroles(
            responsable_id,
            [(RespModule, 'moduleimpl_id', moduleimpl_id)] )

_moduleimplEditor = ModuleImplEditor(
    'notes_moduleimpl',
    'moduleimpl_id',
    'ViewInfosFormation',
    'ModifModuleImpl',
    ('moduleimpl_id','module_id','formsemestre_id','responsable_id'),
    callback_on_write=CNT.inval_cache
    )

notes_moduleimpl_create = _moduleimplEditor.create
notes_moduleimpl_delete = _moduleimplEditor.delete
notes_moduleimpl_list   = _moduleimplEditor.list
notes_moduleimpl_edit   = _moduleimplEditor.edit

def notes_moduleimpl_withmodule_list(uid,args):
    """Liste les moduleimpls et ajoute dans chacun le module correspondant
    Tri la liste par numero de module
    """
    modimpls = notes_moduleimpl_list(uid,args)
    for mo in modimpls:
        mo['module'] = notes_module_list(uid, args={ 'module_id' : mo['module_id'] })[0]
    modimpls.sort( lambda x,y: cmp(x['module']['numero'],y['module']['numero']) )
    return modimpls
    
""" --- Gestion des inscriptions aux modules
"""
# pour l'instant fait en SQL, pas d'interface web

_formsemestre_inscriptionEditor = EditableTable(
    'notes_formsemestre_inscription',
    'formsemestre_inscription_id',
    GrantAccess, # read by all
    'InscritEtudiant',
    ('formsemestre_inscription_id', 'etudid', 'formsemestre_id',
     'groupetd', 'groupetp', 'groupeanglais'),
    sortkey = 'formsemestre_id',
    callback_on_write=CNT.inval_cache
    )

notes_formsemestre_inscription_create = _formsemestre_inscriptionEditor.create
notes_formsemestre_inscription_delete = _formsemestre_inscriptionEditor.delete
notes_formsemestre_inscription_list   = _formsemestre_inscriptionEditor.list
notes_formsemestre_inscription_edit   = _formsemestre_inscriptionEditor.edit

# Inscriptions aux modules
_moduleimpl_inscriptionEditor = EditableTable(
    'notes_moduleimpl_inscription',
    'moduleimpl_inscription_id',
    GrantAccess, # read by all
    'InscritEtudiant',
    ('moduleimpl_inscription_id', 'etud_id', 'moduleimpl_id'),
    callback_on_write=CNT.inval_cache
    )

notes_moduleimpl_inscription_create = _moduleimpl_inscriptionEditor.create
notes_moduleimpl_inscription_delete = _moduleimpl_inscriptionEditor.delete
notes_moduleimpl_inscription_list   = _moduleimpl_inscriptionEditor.list
notes_moduleimpl_inscription_edit   = _moduleimpl_inscriptionEditor.edit

def notes_moduleimpl_listeetuds(uid,moduleimpl_id):
    "retourne liste des etudids inscrits a ce module"
    # xxx access
    req = "select distinct Im.etudid from notes_moduleimpl_inscription Im, notes_formsemestre_inscription Isem, notes_moduleimpl M where Isem.etudid=Im.etudid and Im.moduleimpl_id=M.moduleimpl_id and M.moduleimpl_id = %(moduleimpl_id)s"
    cnx = GetDBConnexion()
    cursor = cnx.cursor()    
    cursor.execute( req, { 'moduleimpl_id' : moduleimpl_id } )
    res = cursor.fetchall()
    return [ x[0] for x in res ]


# Pour gestion des listes d'étudiants XXXX
#def notes_formsemestre_inscription_listegroupes( formsemestre_id, cnx=None ):
#     """donne la liste des groupes (td,tp,anglais) dans lesquels figurent des etudiants
#     inscrits a ce semestre
#     """    
#     req = 'select distinct %s from notes_formsemestre_inscription Isem, notes_formsemestre S where Isem.formsemestre_id=S.formsemestre_id and S.evaluation_id = %%(evaluation_id)s'
#     cnx = GetDBConnexion()
#     cursor = cnx.cursor()    
#     cursor.execute( req % 'groupetd', { 'evaluation_id' : evaluation_id } )
#     res = cursor.fetchall()
#     gr_td = [ x[0] for x in res ]
#     cursor.execute( req % 'groupetp', { 'evaluation_id' : evaluation_id } )
#     res = cursor.fetchall()
#     gr_tp = [ x[0] for x in res ]
#     cursor.execute( req % 'groupeanglais', { 'evaluation_id' : evaluation_id } )
#     res = cursor.fetchall()
#     gr_anglais = [ x[0] for x in res ]
#     return gr_td, gr_tp, gr_anglais


""" --- Evaluations
"""

class EvaluationEditor(EditableTable):
    def create(self, uid, args ):
        "check permission and add eval"
        # --- Access control (XXX fait a la main !!!)
        self._check_w_access(uid, args['moduleimpl_id'])
        # ---
        return EditableTable.create(self, uid, args)
    
    def edit(self,uid, args):
        "check permission and edit"
        # --- Access control (XXX fait a la main !!!)
        eid = args['evaluation_id']
        E = notes_evaluation_list(uid, {'evaluation_id' : eid})[0]
        self._check_w_access(uid, E['moduleimpl_id'])
        # ---
        EditableTable.edit(self, uid, args)
    
    def delete(self,uid, oid, commit=True ):
        "check permission and delete"
        # --- Access control (XXX fait a la main !!!)
        E = notes_evaluation_list(uid, {'evaluation_id' : oid})[0]
        self._check_w_access(uid, E['moduleimpl_id'])
        # ---
        EditableTable.delete(self, uid, oid, commit=commit)

    def _check_w_access(self, uid, moduleimpl_id):
        "raise exception if access not permitted"
        # diretud du semestre ou resp. module
        uid = str(uid)
        M = notes_moduleimpl_list(uid, args={ 'moduleimpl_id' : moduleimpl_id }  )[0]
        sem = notes_formsemestre_list(uid, args={ 'formsemestre_id' : M['formsemestre_id'] } )[0]
        if uid != 'admin' and uid != M['responsable_id'] and uid != sem['responsable_id']:
            raise AccessDenied('Modification évaluation impossible pour %s'%uid)
        

_evaluationEditor = EvaluationEditor(
    'notes_evaluation',
    'evaluation_id',
    'ViewNote', # read 
    'CreateEvaluation',
    ('evaluation_id', 'moduleimpl_id',
     'jour', 'heure_debut', 'heure_fin', 'description',
     'note_max', 'coefficient' ),
    sortkey = 'jour',
    output_formators = { 'jour' : DateISOtoDMY,
                         'heure_debut' : TimefromISO8601,
                         'heure_fin'   : TimefromISO8601
                         },
    input_formators  = { 'jour' : DateDMYtoISO,
                         'heure_debut' : TimetoISO8601,
                         'heure_fin'   : TimetoISO8601
                         },
    callback_on_write=CNT.inval_cache
    )

notes_evaluation_create = _evaluationEditor.create
notes_evaluation_delete = _evaluationEditor.delete
notes_evaluation_list   = _evaluationEditor.list
notes_evaluation_edit   = _evaluationEditor.edit

def notes_evaluation_create_form(REQUEST, edit=False, readonly=False ):
    "formulaire creation/edition des evaluations (pas des notes)"
    AUTHENTICATED_USER = str(REQUEST.AUTHENTICATED_USER )
    # XXX access ?
    evaluation_id = REQUEST.form.get('evaluation_id', None)
    if readonly:
        edit=True # montre les donnees existantes
    if not edit:
        # creation nouvel
        moduleimpl_id = REQUEST.form['moduleimpl_id']
        initvalues = { 'note_max' : 20 }
        submitlabel = 'Créer cette évaluation'
        action = 'Création d\'une '
    else:
        # edition donnees existantes
        # setup form init values
        if not evaluation_id:
            raise ValueError, 'missing evaluation_id parameter'
        initvalues = notes_evaluation_list( AUTHENTICATED_USER,
                                            {'evaluation_id' : evaluation_id})[0]    
        moduleimpl_id = initvalues['moduleimpl_id']
        submitlabel = 'Modifier les données'
        if readonly:
            action = ''
        else:
            action = 'Modification d\'une '
    #    
    M = notes_moduleimpl_list( AUTHENTICATED_USER, args={ 'moduleimpl_id' : moduleimpl_id } )[0]
    Mod = notes_module_list( AUTHENTICATED_USER, args={ 'module_id' : M['module_id'] } )[0]
    sem = notes_formsemestre_list( AUTHENTICATED_USER, args={ 'formsemestre_id' : M['formsemestre_id'] } )[0]
    #F = notes_formation_list( AUTHENTICATED_USER, args={ 'formation_id' : sem['formation_id'] } )[0]
    #ModEvals = notes_evaluation_list( AUTHENTICATED_USER, args={ 'moduleimpl_id' : M['moduleimpl_id'] } )
    #
    H = ['<h2>%sévaluation en <a href="moduleimpl_status?moduleimpl_id=%s">%s %s</a></h2>'
         % (action, moduleimpl_id, Mod['code'], Mod['titre']),
         'Semestre: %s' % sem['titre'] ]
    if readonly:
        E = initvalues
        # version affichage seule (générée ici pour etre plus jolie que le Formulator)
        H.append( '<br>évaluation réalisée le %s de %s à %s'
                  % (E['jour'],E['heure_debut'],E['heure_fin']) )
        H.append( '<br>coefficient dans le module: %s</p>' % E['coefficient'] )
        return '<div class="eval_description">' + '\n'.join(H) + '</div>'
    
    heures = [ '%02dh%02d' % (h,m) for h in range(8,19) for m in (0,30) ]

    tf = TrivialFormulator( REQUEST.URL0, REQUEST.form, (
        ('evaluation_id', { 'default' : evaluation_id, 'input_type' : 'hidden' }),
        ('moduleimpl_id', { 'default' : moduleimpl_id, 'input_type' : 'hidden' }),
        ('jour', { 'title' : 'Date (j/m/a)', 'size' : 12, 'explanation' : 'date de l\'examen, devoir ou contrôle' }),
        ('heure_debut'   , { 'title' : 'Heure de début', 'explanation' : 'heure du début de l\'épreuve',
                             'input_type' : 'menu', 'allowed_values' : heures, 'labels' : heures }),
        ('heure_fin'   , { 'title' : 'Heure de fin', 'explanation' : 'heure de fin de l\'épreuve',
                           'input_type' : 'menu', 'allowed_values' : heures, 'labels' : heures }),
        ('coefficient'    , { 'size' : 10, 'type' : 'float', 'explanation' : 'coef. dans le module (choisi librement par l\'enseignant)', 'allow_null':False }),
        ('note_max'    , { 'size' : 3, 'type' : 'float', 'title' : 'Notes de 0 à', 'explanation' : 'barème', 'allow_null':False, 'max_value' : NOTES_MAX }),
        
        ('description' , { 'size' : 36, 'type' : 'text'  }),    
        ),
                            cancelbutton = 'Annuler',
                            submitlabel = submitlabel,
                            initvalues = initvalues, readonly=readonly)
    
    dest_url = 'moduleimpl_status?moduleimpl_id=%s' % M['moduleimpl_id']
    if  tf[0] == 0:
        return '\n'.join(H) + '\n' + tf[1]
    elif tf[0] == -1:
        return REQUEST.RESPONSE.redirect( dest_url )
    else:
        # form submission
        if not edit:
            # creation d'une evaluation
            evaluation_id = notes_evaluation_create( AUTHENTICATED_USER, tf[2] )
            return REQUEST.RESPONSE.redirect( dest_url )
        else:
            notes_evaluation_edit( AUTHENTICATED_USER, tf[2] )
            return REQUEST.RESPONSE.redirect( dest_url )

def notes_evaluation_listegroupes( evaluation_id ):
    """donne la liste des groupes (td,tp,anglais) dans lesquels figurent des etudiants
    inscrits au module/semestre dans auquel appartient cette evaluation
    """    
    req = 'select distinct %s from notes_formsemestre_inscription Isem, notes_moduleimpl_inscription Im, notes_moduleimpl M, notes_evaluation E where Isem.etudid=Im.etudid and Im.moduleimpl_id=M.moduleimpl_id and E.moduleimpl_id=M.moduleimpl_id and E.evaluation_id = %%(evaluation_id)s'
    cnx = GetDBConnexion()
    cursor = cnx.cursor()    
    cursor.execute( req % 'groupetd', { 'evaluation_id' : evaluation_id } )
    res = cursor.fetchall()
    gr_td = [ x[0] for x in res ]
    cursor.execute( req % 'groupetp', { 'evaluation_id' : evaluation_id } )
    res = cursor.fetchall()
    gr_tp = [ x[0] for x in res ]
    cursor.execute( req % 'groupeanglais', { 'evaluation_id' : evaluation_id } )
    res = cursor.fetchall()
    gr_anglais = [ x[0] for x in res ]
    return gr_td, gr_tp, gr_anglais

def _simplesqlquote(s,maxlen=50):
    """simple SQL quoting to avoid most SQL injection attacks.
    Note: we use this function in the (rare) cases where we have to
    construct SQL code manually"""
    s = s[:maxlen] 
    s.replace("'", r"\'")
    s.replace(";", r"\;")
    for bad in ("select", "drop", ";", "--", "insert", "delete", "xp_"):
        s = s.replace(bad,'')
    return s

def notes_evaluation_listeetuds_groups(evaluation_id,gr_td=[],gr_tp=[],gr_anglais=[],
                                       getallstudents=False ):
    """Donne la liste des etudids inscrits a cette evaluation dans les groupes indiques
    Si getallstudents==True, donne tous les etudiants inscrits a cette evaluation.
    """
    # construit condition sur les groupes
    if not getallstudents:
        rg =  [ "Isem.groupetd = '%s'" % _simplesqlquote(x) for x in gr_td ]
        rg += [ "Isem.groupetp = '%s'" % _simplesqlquote(x) for x in gr_tp ]
        rg += [ "Isem.groupeanglais = '%s'" % _simplesqlquote(x) for x in gr_anglais ]
        if not rg:
            return [] # no groups, so no students
        r = ' and (' + ' or '.join(rg) + ' )'
    else:
        r = ''
    # requete complete
    req = 'select distinct Im.etudid from notes_moduleimpl_inscription Im, notes_formsemestre_inscription Isem, notes_moduleimpl M, notes_evaluation E where Isem.etudid=Im.etudid and Im.moduleimpl_id=M.moduleimpl_id and E.moduleimpl_id=M.moduleimpl_id and E.evaluation_id = %(evaluation_id)s' + r
    cnx = GetDBConnexion()
    cursor = cnx.cursor()    
    cursor.execute( req, { 'evaluation_id' : evaluation_id } )
    res = cursor.fetchall()
    return [ x[0] for x in res ]

def _displayNote(val):
    "convert note from DB to viewable string"
    if val is None:
        val = 'ABS'
    elif val == NOTES_NEUTRALISE:
        val = 'EXC' # excuse, note neutralise
    else:
        val = '%g' % val
    return val

def notes_evaluation_etat(uid, evaluation_id):
    """donne infos sur l'etat du evaluation
    ( nb_inscrits, nb_notes, nb_abs, nb_neutre, moyenne, mediane, date_last_modif )
    """
    uid = str(uid)
    nb_inscrits = len(notes_evaluation_listeetuds_groups(evaluation_id,getallstudents=True))
    NotesDB = note_notes_getall(uid, evaluation_id)
    notes = [ x['value'] for x in NotesDB.values() ]
    nb_notes = len(notes)
    nb_abs = len( [ x for x in notes if x is None ] )
    nb_neutre = len( [ x for x in notes if x == NOTES_NEUTRALISE ] )
    moy, median = notes_moyenne_median(notes)
    if moy is None:
        median, moy = '',''
    else:
        median = '%.3g' % median
        moy = '%.3g' % moy
    # cherche date derniere modif note
    if len(NotesDB):
        t = [ x['date'] for x in NotesDB.values() ]
        last_modif = max(t)
    else:
        last_modif = None
    return nb_inscrits, nb_notes, nb_abs, nb_neutre, moy, median, last_modif


def notes_evaluation_list_in_sem(uid, formsemestre_id):
    """Liste des evaluations pour un semestre (dans tous le smodules de ce semestre)
    Donne pour chaque eval son état:
    (evaluation_id,nb_inscrits, nb_notes, nb_abs, nb_neutre, moy, median, last_modif)
    """
    req = "select evaluation_id from notes_evaluation E, notes_moduleimpl MI where MI.formsemestre_id = %(formsemestre_id)s and MI.moduleimpl_id = E.moduleimpl_id"
    cnx = GetDBConnexion()
    cursor = cnx.cursor()    
    cursor.execute( req, { 'formsemestre_id' : formsemestre_id } )
    res = cursor.fetchall()
    evaluation_ids = [ x[0] for x in res ]
    #
    R = []
    for evaluation_id in evaluation_ids:
        R.append( (evaluation_id,) + notes_evaluation_etat(uid, evaluation_id) )        
    return R 

def _eval_etat(evals):
    """-> nb_eval_completes, nb_evals_en_cours, nb_evals_vides, date derniere modif"""
    
    nb_eval_completes, nb_evals_en_cours, nb_evals_vides = 0,0,0
    dates = []
    for e in evals:
        if e[1] == e[2]: # nb_inscrits == nb_notes
            nb_eval_completes += 1
        elif e[2] == 0: # nb_notes == 0
            nb_evals_vides += 1
        else:
            nb_evals_en_cours += 1
        dates.append(e[-1])
    dates.sort()
    if len(dates):
        last_modif = dates[-1] # date de derniere modif d'une note dans un module
    else:
        last_modif = ''
    return nb_eval_completes, nb_evals_en_cours, nb_evals_vides, last_modif

def notes_evaluation_etat_in_sem(uid, formsemestre_id):
    """-> nb_eval_completes, nb_evals_en_cours, nb_evals_vides, date derniere modif"""
    evals = notes_evaluation_list_in_sem(uid, formsemestre_id)
    return _eval_etat(evals)

def notes_evaluation_etat_in_mod(uid, moduleimpl_id):
    evals = notes_evaluation_list(uid, { 'moduleimpl_id' : moduleimpl_id } )
    evaluation_ids = [ x['evaluation_id'] for x in evals ]
    R = []
    for evaluation_id in evaluation_ids:
        R.append( (evaluation_id,) + notes_evaluation_etat(uid, evaluation_id) )
    return _eval_etat(R)

def notes_evaluation_listenotes( REQUEST ):
    """Affichage des notes d'une évaluation"""
    authuser = str(REQUEST.AUTHENTICATED_USER)
    evaluation_id = REQUEST.form.get('evaluation_id', None)
    # description de l'evaluation    
    H = [ notes_evaluation_create_form(REQUEST, readonly=1) ]
    # groupes
    gr_td, gr_tp, gr_anglais = notes_evaluation_listegroupes(evaluation_id)
    grnams  = ['tous'] + [('td'+x) for x in gr_td ] # noms des checkbox
    grnams += [('tp'+x) for x in gr_tp ]
    grnams += [('ta'+x) for x in gr_anglais ]
    grlabs  = ['tous'] + gr_td + gr_tp + gr_anglais # legendes des boutons
    descr = [
        ('evaluation_id', { 'default' : evaluation_id, 'input_type' : 'hidden' }),
        ('liste_format', {'input_type' : 'radio', 'default' : 'html', 'allow_null' : False, 
                         'allowed_values' : [ 'html', 'pdf', 'csv' ],
                         'labels' : ['page HTML', 'fichier PDF', 'fichier tableur' ],
                         'title' : 'Format' }),
        ('s' , {'input_type' : 'separator', 'title': 'Choix du ou des groupes d\'étudiants' }),
        ('groupes', { 'input_type' : 'checkbox', 'title':'',
                      'allowed_values' : grnams, 'labels' : grlabs }) ]
    tf = TrivialFormulator( REQUEST.URL0, REQUEST.form, descr,
                            cancelbutton = 'Annuler', method='GET',
                            submitlabel = 'OK' )
    if  tf[0] == 0:
        return '\n'.join(H) + '\n' + tf[1]
    elif tf[0] == -1:
        return REQUEST.RESPONSE.redirect( REQUEST.URL1 )
    else:
        liste_format = tf[2]['liste_format']
        # Build list of etudids (uniq, some groups may overlap)
        glist = tf[2]['groupes']
        gr_td = [ x[2:] for x in glist if x[:2] == 'td' ]
        gr_tp = [ x[2:] for x in glist if x[:2] == 'tp' ]
        gr_anglais = [ x[2:] for x in glist if x[:2] == 'ta' ]
        gr_title = ' '.join(gr_td+gr_tp+gr_anglais)
        if 'tous' in glist:
            getallstudents = True
            gr_title = 'tous'
        else:
            getallstudents = False
        NotesDB = note_notes_getall(authuser,evaluation_id)
        etudids= notes_evaluation_listeetuds_groups(evaluation_id,gr_td,gr_tp,gr_anglais,
                                                    getallstudents=getallstudents)
        E = notes_evaluation_list(authuser, {'evaluation_id' : evaluation_id})[0]
        M = notes_moduleimpl_list(authuser, args={ 'moduleimpl_id' : E['moduleimpl_id'] } )[0]
        Mod = notes_module_list(authuser, args={ 'module_id' : M['module_id'] } )[0]
        evalname = '%s-%s' % (Mod['code'],DateDMYtoISO(E['jour']))
        hh = '<h4>%s du %s, groupes %s (%d étudiants)</h4>' % (E['description'], E['jour'], gr_title,len(etudids))
        Th = ['', 'Nom', 'Prénom', 'Etat', 'Groupe', 'Note sur %d'% E['note_max'], 'Remarque']
        T = [] # list of lists, used to build HTML and CSV
        nb_notes = 0
        sum_notes = 0
        for etudid in etudids:
            # infos identite etudiant (xxx sous-optimal: 1/select par etudiant)
            ident = scolars.etudident_list( authuser, { 'etudid' : etudid })[0]
            # infos inscription
            inscr = notes_formsemestre_inscription_list(
                authuser, {'etudid':etudid, 'formsemestre_id' : M['formsemestre_id']})[0]
            if NotesDB.has_key(etudid):
                val = NotesDB[etudid]['value']
                if val != None and val != NOTES_NEUTRALISE: # calcul moyenne SANS LES ABSENTS
                    nb_notes = nb_notes + 1
                    sum_notes += val
                val = _displayNote(val)
                comment = NotesDB[etudid]['comment']
                if comment is None:
                    comment = ''
                explanation = '%s (%s) %s' % (NotesDB[etudid]['date'].strftime('%d/%m/%y %Hh%M'),
                                              NotesDB[etudid]['uid'],comment)
            else:
                explanation = ''
                val = '' 
            T.append( [ etudid, ident['nom'].upper(), ident['prenom'].lower().capitalize(),
                      inscr['etat'],
                      inscr['groupetd']+'/'+inscr['groupetp']+'/'+inscr['groupeanglais'],
                      val, explanation ] )
        T.sort() # sort by nom
        # display
        if liste_format == 'csv':
            CSV = CSV_LINESEP.join( [ CSV_FIELDSEP.join(x) for x in [Th]+T ] )
            filename = 'notes_%s.csv' % evalname
            return _sendFile(REQUEST,CSV, filename, title=evalname ) 
        elif liste_format == 'html':
            if T:
                Th = [ Th[1], Th[2], Th[5], Th[6] ]
                Th = [ '<th>' + '</th><th>'.join(Th) + '</th>' ]
                Tb = []
                demfmt = '<span class="etuddem">%s</span>'
                absfmt = '<span class="etudabs">%s</span>'
                cssclass = 'tablenote'
                for t in T:
                    fmt='%s'
                    if t[3] != 'I':
                        fmt = demfmt
                        comment =  t[3]+' '+t[6]
                    elif t[5][:3] == 'ABS':
                        fmt = absfmt
                    nom,prenom,note,comment = fmt%t[1], fmt%t[2], fmt%t[5], t[6]
                    Tb.append( '<tr class="%s"><td>%s</td><td>%s</td><td class="colnote">%s</td><td class="colcomment">%s</td></tr>' % (cssclass,nom,prenom,note,comment) )
                Tb = [ '\n'.join(Tb ) ]
                Tm = [ '<tr class="tablenote"><td></td><td>Moyenne</td><td class="colnotemoy">%.3g</td><td class="colcomment">sur %d notes (sans les absents)</td></tr>' % (sum_notes/nb_notes, nb_notes) ]
                Tab = [ '<table class="tablenote"><tr class="tablenotetitle">' ] + Th + ['</tr><tr><td>'] + Tb + Tm + [ '</td></tr></table>' ]
            else:
                Tab = 'aucun étudiant !'
            return tf[1] + '\n'.join(H) + hh + '\n'.join(Tab) 
        elif liste_format == 'pdf':
            return 'conversion PDF non implementée !'
        else:
            raise ValueError('invalid value for liste_format (%s)'%liste_format)

def notes_evaluation_selectetuds( REQUEST ):
    """Choisi les etudiants pour saisie notes"""
    evaluation_id = REQUEST.form.get('evaluation_id', None)
    # description de l'evaluation    
    H = [ notes_evaluation_create_form(REQUEST, readonly=1) ]
    # groupes
    gr_td, gr_tp, gr_anglais = notes_evaluation_listegroupes(evaluation_id)
    grnams  = ['tous'] + [('td'+x) for x in gr_td ] # noms des checkbox
    grnams += [('tp'+x) for x in gr_tp ]
    grnams += [('ta'+x) for x in gr_anglais ]
    grlabs  = ['tous'] + gr_td + gr_tp + gr_anglais # legendes des boutons
    descr = [
        ('evaluation_id', { 'default' : evaluation_id, 'input_type' : 'hidden' }),
        ('note_method', {'input_type' : 'radio', 'default' : 'form', 'allow_null' : False, 
                         'allowed_values' : [ 'csv', 'form' ],
                         'labels' : ['fichier tableur', 'formulaire web'],
                         'title' : 'Méthode de saisie des notes' }),
        ('s' , {'input_type' : 'separator', 'title': 'Choix du ou des groupes d\'étudiants' }),
        ('groupes', { 'input_type' : 'checkbox', 'title':'',
                      'allowed_values' : grnams, 'labels' : grlabs }) ]
    tf = TrivialFormulator( REQUEST.URL0, REQUEST.form, descr,
                            cancelbutton = 'Annuler',
                            submitlabel = 'OK' )
    if  tf[0] == 0:
        return '\n'.join(H) + '\n' + tf[1]
    elif tf[0] == -1:
        return REQUEST.RESPONSE.redirect( REQUEST.URL1 )
    else:
        # form submission
        #   get checked groups
        g = tf[2]['groupes']
        note_method =  tf[2]['note_method']
        if note_method in ('form', 'csv'):
            # return notes_evaluation_formnotes( REQUEST )
            gs = [('groupes%3Alist=' + urllib.quote_plus(x)) for x in g ]
            query = 'evaluation_id=%s&note_method=%s&' % (evaluation_id,note_method) + '&'.join(gs)
            REQUEST.RESPONSE.redirect( REQUEST.URL1 + '/notes_evaluation_formnotes?' + query )
        else:
            raise ValueError, "invalid note_method (%s)" % tf[2]['note_method'] 


def notes_evaluation_formnotes( REQUEST ):
    """Formulaire soumission notes pour une evaluation.
    parametres: evaluation_id, groupes (liste, avec prefixes tp, td, ta)
    """
    authuser = str(REQUEST.AUTHENTICATED_USER)
    evaluation_id = REQUEST.form['evaluation_id']
    E = notes_evaluation_list(authuser, {'evaluation_id' : evaluation_id})[0]
    # Check access
    # (admin, respformation, and responsable_id)
    # XXX A FAIRE (revoir roles, politique d'attribution etc)
    
    #
    note_method = REQUEST.form['note_method']
    okbefore = int(REQUEST.form.get('okbefore',0)) # etait ok a l'etape precedente
    reviewed = int(REQUEST.form.get('reviewed',0)) # a ete presenté comme "pret a soumettre"
    initvalues = {}
    CSV = [] # une liste de liste de chaines: lignes du fichier CSV
    CSV.append( ['Fichier de notes (à enregistrer au format CSV)'])
    # Construit liste des etudiants
    glist = REQUEST.form['groupes']
    gr_td = [ x[2:] for x in glist if x[:2] == 'td' ]
    gr_tp = [ x[2:] for x in glist if x[:2] == 'tp' ]
    gr_anglais = [ x[2:] for x in glist if x[:2] == 'ta' ]
    gr_title = ' '.join(gr_td+gr_tp+gr_anglais)
    if 'tous' in glist:
        getallstudents = True
        gr_title = 'tous'
    else:
        getallstudents = False
    etudids = notes_evaluation_listeetuds_groups(evaluation_id,gr_td,gr_tp,gr_anglais,
                                                 getallstudents=getallstudents)
    # Notes existantes
    NotesDB = note_notes_getall(authuser,evaluation_id)
    #
    M = notes_moduleimpl_list(authuser, args={ 'moduleimpl_id' : E['moduleimpl_id'] } )[0]
    Mod = notes_module_list(authuser, args={ 'module_id' : M['module_id'] } )[0]
    sem = notes_formsemestre_list(authuser, args={ 'formsemestre_id' : M['formsemestre_id'] } )[0]
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
        ('comment', { 'size' : 44, 'title' : 'Commentaire' }),
        ('s2' , {'input_type' : 'separator', 'title': '<br>'}),
        ]
    el = [] # list de (label, etudid, note_value, explanation )
    for etudid in etudids:
        # infos identite etudiant (xxx sous-optimal: 1/select par etudiant)
        ident = scolars.etudident_list( authuser, { 'etudid' : etudid })[0]
        # infos inscription
        inscr = notes_formsemestre_inscription_list(
            authuser, {'etudid':etudid, 'formsemestre_id' : M['formsemestre_id']})[0]
        label = '%s %s' % (ident['nom'].upper(), ident['prenom'].lower().capitalize())
        if inscr['etat'] != 'I':
            label = '<span class="etuddem">' + label + '</span>'
        if NotesDB.has_key(etudid):
            val = _displayNote(NotesDB[etudid]['value'])
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
        descr.append( ('note_'+etudid, { 'size' : 4, 'title' : label, 'explanation':explanation} ) )
        CSV.append( [ '%s' % etudid, ident['nom'].upper(), ident['prenom'].lower().capitalize(),
                      inscr['etat'],
                      inscr['groupetd']+'/'+inscr['groupetp']+'/'+inscr['groupeanglais'],
                      val, explanation ] )
    CSV = CSV_LINESEP.join( [ CSV_FIELDSEP.join(x) for x in CSV ] )
    if note_method == 'csv':
        filename = 'notes_%s.csv' % evalname
        return _sendFile(REQUEST,CSV, filename, title=evalname )
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
        L, invalids, withoutnotes, absents = notes_check_notes(notes, E)
        # demande confirmation
        H = ['<ul class="tf-msg">']
        if invalids:
            H.append( '<li class="tf-msg">%d notes invalides !</li>' % len(invalids) )
        if withoutnotes:
            H.append( '<li class="tf-msg-notice">%d étudiants sans notes !</li>' % len(withoutnotes) )
        if absents:
            H.append( '<li class="tf-msg-notice">%d étudiants absents !</li>' % len(absents) )
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
            nbchanged = notes_notes_add(authuser, evaluation_id, L, tf.result['comment'])
            return '<p>OK !<br>%s notes modifiées<br></p>' % nbchanged
        else:            
            return head + '\n'.join(H) + tf.getform()

def _sendFile(REQUEST,data,filename,title=None):
    """publication fichier.
    (on ne doit rien avoir émis avant, car ici sont générés les entetes)
    """
    if not title:
        title = filename
    head = """Content-type: %s; name="%s"
Content-disposition: filename="%s"
Title: %s

""" % (CSV_MIMETYPE,filename,filename,title)
    return head + str(data)

def notes_evaluation_upload_csv(REQUEST):
    """soumission d'un fichier CSV (evaluation_id, notefile)
    """
    authuser = str(REQUEST.AUTHENTICATED_USER)
    evaluation_id = REQUEST.form['evaluation_id']
    E = notes_evaluation_list(authuser, {'evaluation_id' : evaluation_id})[0]
    data = REQUEST.form['notefile'].read().replace('\r\n','\n').replace('\r','\n')
    lines = data.split('\n')
    # decode fichier
    # 1- skip lines until !evaluation_id
    n = len(lines)
    i = 0
    while i < n and lines[i].strip()[0] != '!':
        i = i + 1
    if i == n:
        raise NoteProcessError('Format de fichier invalide ! (pas de ligne evaludation_id)')
    eval_id = lines[i].split(CSV_FIELDSEP)[0].strip()[1:]
    if eval_id != evaluation_id:
        raise NoteProcessError("Fichier invalide: le code d\'évaluation de correspond pas ! ('%s' != '%s')"%(eval_id,evaluation_id))
    # 2- get notes -> list (etudid, value)
    notes = []
    for line in lines[i+1:]:
        fs = line.split(CSV_FIELDSEP)
        etudid = fs[0].strip()
        val = fs[5].strip()
        if etudid:
            notes.append((etudid,val))
    L, invalids, withoutnotes, absents = notes_check_notes(notes,E)
    if len(invalids):
        return '<p class="boldredmsg">Le fichier contient %d notes invalides</p>' % len(invalids)
    else:
        nb_changed = notes_notes_add( REQUEST.AUTHENTICATED_USER, evaluation_id, L )
    return '<p>%d notes changées (%d sans notes, %d absents)</p>'%(len(notes),len(withoutnotes),len(absents)) + '<p>' + str(notes)


def notes_check_notes( notes, evaluation ):
    """notes is a list of tuples (etudid, value)
    returns list of valid notes (etudid, float value)
    and 3 lists of etudid: invalids, withoutnotes, absents
    """
    note_max = evaluation['note_max']
    L = [] # liste (etudid, note) des notes ok (ou absent) 
    invalids = [] # etudid avec notes invalides
    withoutnotes = [] # etudid sans notes (champs vides)
    absents = [] # etudid absents
    for (etudid, note) in notes:
        note = str(note)        
        if note:
            note = note.strip().upper().replace(',','.')
            if note[:3] == 'ABS':
                note = None
                absents.append(etudid)
            elif note[:3] == 'NEU' or note[:3] == 'EXC':
                note = NOTES_NEUTRALISE
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
    return L, invalids, withoutnotes, absents

""" --- Notes
"""

def notes_can_edit_notes(uid, moduleimpl_id):
    "True if user 'uid' can enter or edit notes in this module"
    uid = str(uid)
    M = notes_moduleimpl_list(uid, args={ 'moduleimpl_id' : moduleimpl_id})[0]
    sem = notes_formsemestre_list(uid, args={ 'formsemestre_id' : M['formsemestre_id'] } )[0]
    if uid != 'admin' and uid != M['responsable_id'] and uid != sem['responsable_id']:
        return False
    else:
        return True

def notes_notes_add(uid, evaluation_id, notes, comment=None ):
    """Insert or update notes
    notes is a list of tuples (etudid,value)
    Nota:
    - va verifier si tous les etudiants sont inscrits
    au moduleimpl correspond a cet eval_id.
    - si la note existe deja avec valeur distincte, ajoute une entree au log (notes_notes_log)
    Return number of changed notes
    """
    uid = str(uid)
    # ------------  Access control (XXX fait a la main !!!)
    E = notes_evaluation_list(uid,
                              {'evaluation_id' : evaluation_id})[0]
    if not notes_can_edit_notes(uid, E['moduleimpl_id']):
        raise AccessDenied('Modification des notes impossible pour %s'%uid)
    # ------------
    # Verifie inscription et valeur note
    inscrits = {}.fromkeys(notes_evaluation_listeetuds_groups(evaluation_id,getallstudents=True))
    for (etudid,value) in notes:
        if not inscrits.has_key(etudid):
            raise NoteProcessError("etudiant %s non inscrit a l'evaluation %s" %(etudid,evaluation_id))
        if not ((value is None) or (type(value) == type(1.0))):
            raise NoteProcessError( "etudiant %s: valeur de note invalide (%s)" %(etudid,value))
    # Recherche notes existantes
    NotesDB = note_notes_getall(uid, evaluation_id)
    # Met a jour la base
    cnx = GetDBConnexion()
    cursor = cnx.cursor()
    nb_changed = 0
    try:
        for (etudid,value) in notes:
            if not NotesDB.has_key(etudid):
                # nouvelle note
                cursor.execute('insert into notes_notes (etudid,evaluation_id,value,comment,uid) values (%(etudid)s,%(evaluation_id)s,%(value)f,%(comment)s,%(uid)s)',
                               {'etudid':etudid, 'evaluation_id':evaluation_id, 'value':value,
                                'comment' : comment, 'uid' : uid} )
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
                    cursor.execute('update notes_notes set value=%(value)s, comment=%(comment)s, date=%(date)s, uid=%(uid)s where etudid=%(etudid)s and evaluation_id=%(evaluation_id)s',
                                   { 'etudid':etudid, 'evaluation_id':evaluation_id, 'value':value,
                                     'date': apply(DB.Timestamp, time.localtime()[:6]),
                                     'comment' : comment, 'uid' : uid} )
                    nb_changed = nb_changed + 1
    except:
        cnx.rollback() # abort
        raise # re-raise exception
    cnx.commit()
    CNT.inval_cache() # XXX should inval only one semestre
    return nb_changed

def note_notes_getall(uid, evaluation_id):
    """get tt les notes pour une evaluation: { etudid : { 'value' : value, 'date' : date ... }}
    """
    cnx = GetDBConnexion()
    cursor = cnx.cursor()
    cursor.execute("select * from notes_notes where evaluation_id=%(evaluation_id)s",
                   { 'evaluation_id' : evaluation_id } )
    res = cursor.dictfetchall()
    d = {}
    for x in res:
        d[x['etudid']] = x
    return d


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

""" --- Bulletins
"""
def notes_moduleimpl_moyennes(uid,moduleimpl_id):
    """Retourne dict { etudid : note_moyenne } pour tous les etuds inscrits
    à ce module, et la liste des evaluations "valides" (toutes notes entrées).
    La moyenne est calculée en utilisant les coefs des évaluations.
    Les notes NEUTRES (abs. excuses) ne sont pas prises en compte.
    Les notes ABS sont remplacées par des zéros.
    S'il manque des notes et que le coef n'est pas nul,
    la moyenne n'est pas calculée: NA
    Ne prend en compte que les evaluations où toutes les notes sont entrées
        (ie nb_inscrits == nb_notes)
    Le résultat est une note sur 20
    """
    uid = str(uid) # xxx access
    M = notes_moduleimpl_list(uid, args={ 'moduleimpl_id' : moduleimpl_id })[0]
    etudids = notes_moduleimpl_listeetuds(uid, moduleimpl_id)
    evals = notes_evaluation_list(uid,args={ 'moduleimpl_id' : moduleimpl_id })
    # recupere les notes de toutes les evaluations
    for e in evals:
        e['nb_inscrits'] = len(notes_evaluation_listeetuds_groups(e['evaluation_id'],
                                                                  getallstudents=True))
        NotesDB = note_notes_getall(uid, e['evaluation_id'])
        notes = [ x['value'] for x in NotesDB.values() ]
        e['nb_notes'] = len(notes)
        e['nb_abs'] = len( [ x for x in notes if x is None ] )
        e['nb_neutre'] = len( [ x for x in notes if x == NOTES_NEUTRALISE ] )
        e['notes'] = NotesDB
    # filtre les evals valides (toutes les notes entrées)
    valid_evals = [ e for e in evals if e['nb_inscrits'] == e['nb_notes'] ]
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

def notes_formsemestre_moyennes(uid,formsemestre_id):
    """retourne dict { moduleimpl_id : { etudid, note_moyenne_dans_ce_module } },
    la liste des moduleimpls, la liste des evaluations valides
    """
    uid = str(uid) # xxx access
    sem = notes_formsemestre_list(uid, args={ 'formsemestre_id' : formsemestre_id } )[0]
    inscr = notes_formsemestre_inscription_list(
        uid, args = { 'formsemestre_id' : formsemestre_id })
    etudids = [ x['etudid'] for x in inscr ]
    mods = notes_moduleimpl_list(uid, args={ 'formsemestre_id' : formsemestre_id})
    # recupere les moyennes des etudiants de tous les modules
    D = {}
    valid_evals = []
    for mod in mods:
        assert not D.has_key(mod['moduleimpl_id'])
        D[mod['moduleimpl_id']], valid_evals_mod = notes_moduleimpl_moyennes(
            uid, mod['moduleimpl_id'])
        valid_evals += valid_evals_mod
    #
    return D, mods, valid_evals

def fmt_note(val, note_max=None):
    "conversion note en str pour affichage dans tables HTML ou PDF"
    if val is None:
        return 'ABS'
    if val == NOTES_NEUTRALISE:
        return 'EXC' # excuse, note neutralise
    
    if type(val) == type(0.0) or type(val) == type(1):
        if note_max != None:
            val = val * 20. / note_max
        s = '%2.2f' % round(float(val),2) # 2 chiffres apres la virgule
        s = '0'*(5-len(s)) + s
        return s
    else:
        return val.replace('NA0', '-')  # notes sans le NA0

def notes_formsemestre_recapcomplet(REQUEST,formsemestre_id,format='html'):
    """Grand tableau récapitulatif avec toutes les notes de modules
    pour tous les étudiants, les moyennes par UE et générale,
    trié par moyenne générale décroissante.
    """
    uid = str(REQUEST.AUTHENTICATED_USER) # xxx access
    sem = notes_formsemestre_list(uid, args={ 'formsemestre_id' : formsemestre_id } )[0]
    nt = CNT.get_NotesTable(uid, formsemestre_id)    
    modimpls = nt.get_modimpls()
    ues = nt.get_ues()
    T = nt.get_table_moyennes_triees()
    # Construit une liste de listes de chaines: le champs du tableau resultat (HTML ou CSV)
    F = []
    h = [ 'Rg', 'Nom', 'Moy' ]
    cod2mod ={} # code : moduleimpl_id
    for ue in ues:
        h.append( ue['acronyme'] )
        for modimpl in modimpls:
            if modimpl['module']['ue_id'] == ue['ue_id']:
                code = modimpl['module']['code']
                h.append( code )
                cod2mod[code] = modimpl['moduleimpl_id'] # pour fabriquer le lien
    F.append(h)
    ue_index = [] # indices des moy UE dans l (pour appliquer style css)
    for t in T:
        etudid = t[-1]
        l = [ str(nt.get_etud_rang(etudid)),nt.get_nom(etudid), fmt_note(t[0]) ] # rang, nom, moy_gen
        i = 0
        for ue in ues:
            i += 1
            l.append( t[i] ) # moyenne dans l'ue
            ue_index.append(len(l)-1)
            j = 0
            for modimpl in modimpls:
                if modimpl['module']['ue_id'] == ue['ue_id']:
                    l.append( t[j+len(ues)+1] ) # moyenne etud dans module
                j += 1
        l.append(etudid) # derniere colonne = etudid
        F.append(l)
    # Dernière ligne: moyennes UE et modules
    l = [ '', 'Moyennes', '' ] # todo: calcul moyenne des moyennes
    i = 0
    for ue in ues:
        i += 1
        l.append( '' ) # todo: moyenne des moyennes dans l'ue
        ue_index.append(len(l)-1)
        for modimpl in modimpls:
            if modimpl['module']['ue_id'] == ue['ue_id']:
                l.append(fmt_note(nt.get_mod_moy(modimpl['moduleimpl_id'])[0])) # moyenne du module
    F.append(l)
    # Generation table au format demandé
    if format == 'html':
        # Table format HTML
        H = [ '<table class="notes_recapcomplet">' ]
        cells = '<tr class="recap_row_tit">'
        for i in range(len(F[0])):
            if i in ue_index:
                cls = 'recap_tit_ue'
            else:
                cls = 'recap_tit'
            if cod2mod.has_key(F[0][i]): # lien vers etat module
                cells += '<td class="%s"><a href="moduleimpl_status?moduleimpl_id=%s">%s</a></td>' % (cls,cod2mod[F[0][i]], F[0][i])
            else:
                cells += '<td class="%s">%s</td>' % (cls, F[0][i])
        ligne_titres = cells + '</tr>'
        H.append( ligne_titres ) # titres
        
        etudlink='<a href="formsemestre_bulletinetud?formsemestre_id=%s&etudid=%s">%s</a>'
        ir = 0
        nblines = len(F)-1
        for l in F[1:]:
            if ir == nblines-1:
                el = l[1] # derniere ligne
                cells = '<tr class="recap_row_moy">'
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
            cells += '<td class="recap_col_moy">%s</td>' % nsn[2]
            for i in range(3,len(nsn)):
                if i in ue_index:
                    cls = 'recap_col_ue'
                else:
                    cls = 'recap_col'
                cells += '<td class="%s">%s</td>' % (cls,nsn[i])
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
        return _sendFile(REQUEST,CSV, filename, title=semname ) 
    else:
        raise ValueError, 'unknown format %s' % format

def notes_formsemestre_bulletinetud(REQUEST,formsemestre_id,etudid,format='html'):
    uid = str(REQUEST.AUTHENTICATED_USER) # xxx access
    sem = notes_formsemestre_list(uid, args={ 'formsemestre_id' : formsemestre_id } )[0]
    nt = CNT.get_NotesTable(uid, formsemestre_id)  
    #nt.get_etud_eval_note(etudid, evaluation_id)
    ues = nt.get_ues()
    modimpls = nt.get_modimpls()
    nbetuds = len(nt.rangs)
    H = [ '<table class="notes_bulletin">' ]
    H.append( '<tr><td class="note_bold">Moyenne</td><td class="note_bold">%s</td><td class="note_bold">Rang %d/%d</td><td class="note_bold">Note</td><td class="note_bold">Coef</td>' %
              (fmt_note(nt.get_etud_moy(etudid)[0]), nt.get_etud_rang(etudid), nbetuds))
    for ue in ues:
        H.append('<tr class="notes_bulletin_row_ue">')
        H.append('<td class="note_bold">%s</td><td class="note_bold">%s</td><td colspan="2"></td><td>%s</td></tr>' %
                 (ue['acronyme'],
                  fmt_note(nt.get_etud_moy(etudid,ue_id=ue['ue_id'])[0]),
                  '' ) ) # xxx sum coef UE TODO
        for modimpl in modimpls:
            if modimpl['module']['ue_id'] == ue['ue_id']:
                H.append('<tr class="notes_bulletin_row_mod">')
                # module avec moy. dans ce module et coef du module
                nom_mod = modimpl['module']['abbrev']
                if not nom_mod:
                    nom_mod = ''
                link_mod = '<a class="bull_link" href="moduleimpl_status?moduleimpl_id=%s">' % modimpl['moduleimpl_id']
                H.append('<td>%s</a></td><td>%s</a></td><td>%s</td><td></td><td>%.2g</td></tr>' % (
                    link_mod + modimpl['module']['code'],
                    link_mod + nom_mod,
                    fmt_note(nt.get_etud_mod_moy(modimpl, etudid)),
                    modimpl['module']['coefficient'] ))
                # notes de chaque eval:
                evals = nt.get_evals_in_mod(modimpl['moduleimpl_id'])
                for e in evals:
                    H.append('<tr class="notes_bulletin_row_eval">')
                    nom_eval = e['description']
                    if not nom_eval:
                        nom_eval = 'le %s' % e['jour']
                    link_eval = '<a class="bull_link" href="notes_evaluation_listenotes?evaluation_id=%s&liste_format=html&groupes%%3Alist=tous&tf-submit=OK">%s</a>' % (e['evaluation_id'], nom_eval)
                    val = e['notes'][etudid]['value']
                    try:
                        val = fmt_note(val, note_max=e['note_max'] )
                    except:
                        val = _displayNote(val)
                    H.append('<td></td><td></td><td class="bull_nom_eval">%s</td><td>%s</td><td class="bull_coef_eval">%.2g</td></tr>' %
                             (link_eval, val, e['coefficient'] ) )
    H.append('</table>')
    # XXX TODO ajouter les absences, le nom et le rang
    return '\n'.join(H)    

class NotesTable:
    """Une NotesTable représente un tableau de notes pour un semestre de formation.
    Les colonnes sont des modules.
    Les lignes des étudiants.
    On peut calculer les moyennes par étudiant (pondérées par les coefs)
    ou les moyennes par module.
    """
    def __init__(self,uid,formsemestre_id):
        #open('/tmp/cache.log','a').write('NotesTables(%s)\n' % formsemestre_id) # XXX DEBUG
        uid = str(uid) # xxx access
        sem = notes_formsemestre_list(uid, args={ 'formsemestre_id' : formsemestre_id } )[0]
        # Infos sur les etudiants
        self.inscrlist = notes_formsemestre_inscription_list(
            uid, args = { 'formsemestre_id' : formsemestre_id })
        # infos identite etudiant
        # xxx sous-optimal: 1/select par etudiant -> 0.17" pour identdict sur GTR1 !
        self.identdict = {} # { etudid : ident }
        for x in self.inscrlist:
            i = scolars.etudident_list(uid, { 'etudid' : x['etudid'] } )[0]
            self.identdict[x['etudid']] = i
        # Notes dans les modules  { moduleimpl_id : { etudid: note_moyenne_dans_ce_module } }
        self.modmoys, self.modimpls, valid_evals = notes_formsemestre_moyennes(
            uid,formsemestre_id)
        self.valid_evals = {} # { evaluation_id : eval }
        for e in valid_evals:
            self.valid_evals[e['evaluation_id']] = e
        # Liste des modules et UE
        self.mods = []
        self.uedict = {} 
        for modimpl in self.modimpls:
            mod = notes_module_list(uid, args={'module_id' : modimpl['module_id']} )[0]
            self.mods.append(mod)
            modimpl['module'] = mod # add module dict to moduleimpl
            ue = notes_ue_list(uid, args={'ue_id' : mod['ue_id']})[0]
            modimpl['ue'] = ue # add ue dict to moduleimpl
            self.uedict[ue['ue_id']] = ue
            # calcul moyennes du module et stocke dans le module
            #nb_inscrits, nb_notes, nb_abs, nb_neutre, moy, median, last_modif=
        #
        # liste des moyennes de tous, en chaines de car., triées
        T = []
        self.ues = self.uedict.values()
        self.ues.sort( lambda x,y: cmp( x['numero'], y['numero'] ) )
        for etudid in self.get_etudids():
            moy_gen = self.get_etud_moy(etudid)[0]
            moy_ues = [ fmt_note(self.get_etud_moy(etudid, ue_id=ue['ue_id'])[0]) for ue in self.ues ]
            t = [fmt_note(moy_gen)] + moy_ues
            for ue in self.ues:
                for modimpl in self.modimpls:
                    if modimpl['module']['ue_id'] == ue['ue_id']:
                        val = self.get_etud_mod_moy(modimpl, etudid)
                        t.append(fmt_note(val))
            t.append(etudid)
            T.append(tuple(t))
        # tri par moyennes décroissantes
        T.sort()
        T.reverse()
        self.T = T
        # calcul rangs (/ moyenne generale)
        self.rangs = {} # { etudid : rangs }
        rang = 0
        for t in T:
            rang += 1
            self.rangs[t[-1]] = rang
        
    def get_etudids(self):
        return [ x['etudid'] for x in self.inscrlist ]
    def get_nom(self, etudid):
        "formatte nom dun etud"
        return self.identdict[etudid]['nom'].upper() + ' ' + self.identdict[etudid]['prenom'].upper()[0] + '.'
    def get_ues(self):
        "liste des ue, ordonnée par numero"
        return self.ues
    def get_modimpls(self, ue_id=None):
        "liste des modules pour une UE (ou toutes si ue_id==None)"
        if ue_id is None:
            r = self.modimpls
        else:
            r = [ m for m in self.modimpls if m['ue']['ue_id'] == ue_id ]
        # trie la liste par ue.numero puis mod.numero
        r.sort( lambda x,y: cmp( x['ue']['numero']*10000 + x['module']['numero'],
                                 y['ue']['numero']*10000 + y['module']['numero'] ) )
        return r
    def get_etud_eval_note(self,etudid, evaluation_id):
        "note d'un etudiant a une evaluation"
        return self.valid_evals[evaluation_id]['notes'][etudid]
    def get_evals_in_mod(self, moduleimpl_id):
        "liste des evaluations valides dans un module"
        return [ e for e in self.valid_evals.values() if e['moduleimpl_id'] == moduleimpl_id ]
    def get_mod_moy(self, moduleimpl_id):
        """moyenne generale pour un module
        Ne prend en compte que les evaluations où toutes les notes sont entrées
        (ie nb_inscrits == nb_notes)
        """
        nb_notes = 0
        sum_notes = 0.
        nb_missing = 0
        moys = self.modmoys[moduleimpl_id]
        for etudid in self.get_etudids():
            val = moys[etudid]
            try:
                sum_notes += val
                nb_notes = nb_notes + 1
            except:
                nb_missing = nb_missing + 1
        if nb_notes > 0:
            moy = sum_notes/nb_notes 
        else:
            moy = 'NA'
        return moy, nb_notes, nb_missing

    def get_etud_mod_moy(self, modimpl, etudid):
        """moyenne d'un etudiant dans un module"""
        return self.modmoys[modimpl['moduleimpl_id']][etudid]
    
    def get_etud_moy(self, etudid, ue_id=None):
        """moyenne gen. pour un etudiant dans une UE (ou toutes si ue_id==None)
        Ne prend en compte que les evaluations où toutes les notes sont entrées
        (ie nb_inscrits == nb_notes)
        Return: (moy, nb_notes, nb_missing)
        """
        modimpls = self.get_modimpls(ue_id)
        nb_notes = 0
        sum_notes = 0.
        sum_coefs = 0.
        nb_missing = 0
        for modimpl in modimpls:
            val = self.modmoys[modimpl['moduleimpl_id']][etudid]
            coef = modimpl['module']['coefficient']
            try:
                #print '%g in module %s coef %g' % (val, modimpl['moduleimpl_id'], coef)
                sum_notes += val * coef
                sum_coefs += coef
                nb_notes = nb_notes + 1
            except:
                nb_missing = nb_missing + 1
        if sum_coefs > 0:
            moy = sum_notes/ sum_coefs
        else:
            moy = 'NA'
        return moy, nb_notes, nb_missing

    def get_table_moyennes_triees(self):
        return self.T
    def get_etud_rang(self, etudid):
        return self.rangs[etudid]


"""
t = NotesTable( '', 'SEM1157' )
t.get_mod_moy( 'MIP1165' )
"""
