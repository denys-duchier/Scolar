# -*- mode: python -*-
# -*- coding: iso8859-15 -*-

##############################################################################
#
# Gestion scolarite IUT
#
# Copyright (c) 2001 - 2009 Emmanuel Viennet.  All rights reserved.
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

"""ScoDoc preferences (replaces old Zope properties)
"""

from sco_utils import *
from notesdb import *
from TrivialFormulator import TrivialFormulator, TF

"""Global/Semestre Preferences for ScoDoc (version dec 2008)

Preferences (paramètres) communs à tous les utilisateurs.
Peuvent être définis globalement (pour tous les semestres)
ou bien seulement pour un semestre précis.

Chaque parametre est défini dans la base de données SQL par:
 - name : nom du parametre
 - value: valeur du parametre, ou NULL si on doit utiliser une valeur par défaut
 - formsemestre_id: semestre associé, ou NULL si applicable à tous les semestres
                    pour lesquels une valeur spécifique n'est pas définie.

Au niveau du code interface, on défini pour chaque préférence:
 - name (clé)
 - title : titre en français
 - initvalue : valeur initiale, chargée depuis config/scodoc_config.py
 - explanation: explication en français
 - size: longueur du chap texte
 - input_type: textarea,separator,... type de widget TrivialFormulator a utiliser
 - rows, rols: geometrie des textareas
 - category: misc ou bul ou page_bulletins ou abs ou general ou portal 
             ou pdf ou pvpdf ou ...
 - only_global (default False): si vraie, ne peut pas etre associée a un seul semestre.

Les titre et sous-titre de chaque catégorie sont définis dans PREFS_CATEGORIES

On peut éditer les préférences d'une ou plusieurs catégories au niveau d'un 
semestre ou au niveau global. 
* niveau global: changer les valeurs, liste de catégories.
   
* niveau d'un semestre:
   présenter valeur courante: valeur ou "definie globalement" ou par defaut
    lien "changer valeur globale"
   
------------------------------------------------------------------------------
Doc technique:

* Base de données:
Toutes les préférences sont stockées dans la table sco_prefs, qui contient
des tuples (name, value, formsemestre_id).
Si formsemestre_id est NULL, la valeur concerne tous les semestres,
sinon, elle ne concerne que le semestre indiqué. 

* Utilisation dans ScoDoc
  - lire une valeur: 
      context.get_preference(name, formsemestre_id)
      nb: les valeurs sont des chaines, sauf:
         . si le type est spécfié (float ou int)
         . les boolcheckbox qui sont des entiers 0 ou 1
  - avoir un mapping (read only) de toutes les valeurs:
      sem_preferences(context,formsemestre_id)
  - editer les preferences globales:
      sco_preferences.get_base_preferences(self).edit(REQUEST=REQUEST)
  - editer les preferences d'un semestre:
      sem_preferences(context,formsemestre_id).edit()

* Valeurs par défaut:
On a deux valeurs par défaut possibles: 
 - via le fichier scodoc_config.py, qui peut être modifié localement.
 - si rien dans scodoc_config.py, la valeur définie par
   sco_preferences.py est utilisée (ne pas modifier ce fichier).


* Implémentation: sco_preferences.py

PREF_CATEGORIES : définition des catégories de préférences (pour
dialogues édition)
PREFS : pour chaque pref, donne infos pour édition (titre, type...) et
valeur par défaut.

class sco_base_preferences
Une instance unique par site (département, repéré par URL).
- charge les preferences pour tous le semestres depuis la BD.
 .get(formsemestre_id, name)
 .is_global(formsemestre_id, name)
 .save(formsemestre_id=None, name=None)
 .set(formsemestre_id, name, value)
 .deleteformsemestre_id, name)
 .edit() (HTML dialog)

class sem_preferences(context,formsemestre_id)
Une instance par semestre, et une instance pour prefs globales.
L'attribut .base_prefs point sur sco_base_preferences.
 .__getitem__   [name]
 .is_global(name)
 .edit(categories=[])


get_base_preferences(context, formsemestre_id)
 Return base preferences for this context (instance sco_base_preferences)


TODO:
 - tests exhaustifs
"""

PREF_CATEGORIES = (
    # sur page "Paramètres"
    ('general', {}),
    ('abs'  , { 'title' : 'Suivi des absences', 'related' : ('bul',) }),
    ('portal',{ 'title' : 'Liaison avec portail (Apogée, etc)' }),
    ('pdf'  , { 'title' : 'Mise en forme des documents PDF',
               'related' : ('pvpdf', 'bul_margins')}),
    ('pvpdf', { 'title' : 'Procès verbaux de jury (documents PDF)',
               'related' : ('pdf', 'bul_margins') }),
    ('misc' , { 'title' : 'Divers' }),
    # sur page "Réglages des bulletins de notes"
    ('bul'  , { 'title' : 'Réglages des bulletins de notes',
               'related' : ('abs', 'bul_margins', 'bul_mail') }),
    # sur page "Mise en page des bulletins"
    ('bul_margins'  , { 'title' : 'Marges additionnelles, en millimètres', 
                       'subtitle' : "Le tableau des notes est toujours redimensionné pour occuper l'espace disponible entre les marges.",
                       'related' : ('bul', 'bul_mail', 'pdf')}),
    ('bul_mail', { 'title' : 'Envoi des bulletins par e-mail',
                   'related' : ('bul', 'bul_margins', 'pdf') }),
)


PREFS = (
    ('DeptName',
      { 'initvalue' : 'Dept',
        'title' : 'Nom abrégé du département',
        'size' : 12,
        'category' : 'general',
        'only_global' : True
        }
     ),
    ( 'DeptFullName',
      { 'initvalue' : 'nom du département',
        'title' : 'Nom complet du département',
        'explanation' : 'actuellement inutilisé',
        'size' : 40,
        'category' : 'general',
        'only_global' : True
        }
      ),
    ( 'DeptIntranetTitle',
      { 'initvalue' : 'Intranet',
        'title' : 'Nom lien intranet',
        'size' : 40,
        'explanation' : 'titre du lien "Intranet" en haut à gauche',
        'category' : 'general',
        'only_global' : True
        }
      ),
    ( 'DeptIntranetURL',
      { 'initvalue' : '',
        'title' : """URL de l'"intranet" du département""",
        'size' : 40,
        'explanation' : 'lien "Intranet" en haut à gauche',
        'category' : 'general',
        'only_global' : True
        }
      ),

    # abs
    ( 'work_saturday',
      { 'initvalue' : 0,
        'title' : "Considérer le samedi comme travaillé",
        'input_type' : 'boolcheckbox',
        'category' : 'abs',
        'only_global' : True
        }
      ),
    ( 'send_mail_absence_to_chef',
      { 'initvalue' : 0,
        'title' : "Envoyer un mail au chef si un étudiant a beaucoup d\'absences",
        'input_type' : 'boolcheckbox',
        'category' : 'abs',
        'only_global' : True
        }
      ),
    ( 'email_chefdpt',
      { 'initvalue' : '',
        'title' : 'e-mail chef du département',
        'size' : 40,
        'explanation' : 'utilisé pour envoi mail absences',
        'category' : 'abs',
        'only_global' : True
        }
      ),
    # portal
    ( 'portal_url',
      { 'initvalue' : '',
        'title' : 'URL du portail',
        'size' : 40,
        'category' : 'portal',
        'only_global' : True
        }
      ),
    ( 'portal_dept_name',
      { 'initvalue' : 'Dept',
        'title' : 'Code du département sur le portail',
        'category' : 'portal',
        'only_global' : True
        }
      ),
    ( 'notify_etud_changes_to',
      { 'initvalue' : '',
        'title' : 'e-mail à qui notifier les changements d\'identité des étudiants',
        'explanation' : 'utile pour mettre à jour manuellement d\'autres bases de données',
         'size' : 40,
        'category' : 'portal',
        'only_global' : True
        }
      ),
    # pdf
    ('SCOLAR_FONT',
     { 'initvalue' : 'Helvetica',
        'title' : 'Police de caractère principale',
        'explanation' : 'pour les pdf',
         'size' : 25,
        'category' : 'pdf'
        }
      ),
    ('SCOLAR_FONT_SIZE',
     { 'initvalue' : 10,
       'title' : 'Taille des caractères',
       'explanation' : 'pour les pdf',
       'size' : 4,
       'type' : 'int',
       'convert_numbers' : True,
        'category' : 'pdf'
        }
      ),
    ('SCOLAR_FONT_SIZE_FOOT',
     { 'initvalue' : 6,
       'title' : 'Taille des caractères pied de page',
       'explanation' : 'pour les pdf',
       'size' : 4,
       'type' : 'int',
       'convert_numbers' : True,
       'category' : 'pdf'
        }
      ),
    # pvpdf
    ( 'UnivName',
      { 'initvalue' : '',
        'title' : 'Nom de l\'Université',
        'explanation' : 'apparait sur les PV de jury',
        'size' : 40,
        'category' : 'pvpdf',
        'only_global' : True
        }
      ),
    ( 'DirectorName',
      { 'initvalue' : '',
        'title' : 'Nom du directeur de l\'établissement',
        'size' : 32,
        'explanation' : 'pour les PV de jury',
        'category' : 'pvpdf'
        }
      ),
    ('DirectorTitle',
      { 'initvalue' : """directeur de l'IUT""",
        'title' : 'Titre du "directeur"',
        'explanation' : 'titre apparaissant à côté de la signature sur les PV de jury',
        'size' : 64,
        'category' : 'pvpdf'
        }
      ),
    ('INSTITUTION_NAME',
     { 'initvalue' : "<b>Institut Universitaire de Technologie - Université Paris 13</b>",
       'title' : 'Nom institution sur pied de pages PV',
       'explanation' : '(pdf, balises &lt;b&gt; interprétées)',
       'input_type' : 'textarea',
       'rows' : 4, 'cols' : 64,
       'category' : 'pvpdf'
        }
      ),
    ('INSTITUTION_ADDRESS',
     { 'initvalue' : "Web <b>www.iutv.univ-paris13.fr</b> - 99 avenue Jean-Baptiste Clément - F 93430 Villetaneuse",
       'title' : 'Adresse institution sur pied de pages PV',
       'explanation' : '(pdf, balises &lt;b&gt; interprétées)',
       'input_type' : 'textarea',
       'rows' : 4, 'cols' : 64,
       'category' : 'pvpdf'
        }
      ),
    ('INSTITUTION_CITY',
     { 'initvalue' : "Villetaneuse",
       'title' : "Ville de l'institution",
       'explanation' : 'pour les lettres individuelles',
       'size' : 64,
       'category' : 'pvpdf'
        }
      ),
    ('PV_INTRO',
     { 'initvalue' : """<bullet>-</bullet>  
Vu l'arrêté du 3 août 2005 relatif au diplôme universitaire de technologie et notamment son article 4 et 6;
</para>
<para><bullet>-</bullet>  
vu l'arrêté n° %(Decnum)s du Président de l'%(UnivName)s;
</para>
<para><bullet>-</bullet> 
vu la délibération de la commission %(Type)s en date du %(Date)s présidée par le Chef du département;
""",
       'title' : """Paragraphe d'introduction sur le PV""",
       'explanation' : """Balises remplacées: %(Univname)s = nom de l'université, %(DecNum)s = numéro de l'arrêté, %(Date)s = date de la commission, %(Type)s = type de commission (passage ou délivrance) """,
       'input_type' : 'textarea',
       'cols' : 80,
       'rows' : 10,
       'category' : 'pvpdf'
       }
     ),
    ('PV_LETTER_DIPLOMA_SIGNATURE',
     { 'initvalue' : """Le %(DirectorTitle)s, <br/>%(DirectorName)s""",
       'title' :  """Signature des lettres individuelles de diplôme""",
       'explanation' : """%(DirectorName)s et %(DirectorTitle)s remplacés""",
       'input_type' : 'textarea',
       'rows' : 4,
       'cols' : 64,
       'category' : 'pvpdf'
       },
     ),
    ('PV_LETTER_PASSAGE_SIGNATURE',
     { 'initvalue' : """Pour le Directeur de l'IUT<br/>
et par délégation<br/>
Le Chef du département""",
       'title' : """Signature des lettres individuelles de passage d'un semestre à l'autre""",
       'explanation' : """%(DirectorName)s et %(DirectorTitle)s remplacés""",
       'input_type' : 'textarea',
       'rows' : 4,
       'cols' : 64,
       'category' : 'pvpdf'
       },
     ),
    ('PV_FONTNAME',
     { 'initvalue' : 'Times-Roman',
       'title' : 'Police de caractère pour les PV',
       'explanation' : 'pour les pdf',
       'size' : 25,
       'category' : 'pvpdf'
        }
      ),
    # bul
    ( 'bul_show_abs', # ex "gestion_absence"
      { 'initvalue' : 1,
        'title' : 'Indiquer les absences sur les bulletins',
        'input_type' : 'boolcheckbox',
        'category' : 'bul',
        'labels' : ['non', 'oui']
        }
      ),
    ( 'bul_show_decision', 
      { 'initvalue' : 1,
        'title' : 'Faire figurer les décisions sur les bulletins',
        'input_type' : 'boolcheckbox',
        'category' : 'bul',
        'labels' : ['non', 'oui']
        }
      ),
    ( 'bul_show_codemodules', 
      { 'initvalue' : 0,
        'title' : 'Afficher codes des modules sur les bulletins',
        'input_type' : 'boolcheckbox',
        'category' : 'bul',
        'labels' : ['non', 'oui']
        }
      ),
    ( 'bul_show_rangs', 
      { 'initvalue' : 1,
        'title' : 'Afficher le classement sur les bulletins',
        'input_type' : 'boolcheckbox',
        'category' : 'bul',
        'labels' : ['non', 'oui']
        }
      ),
    ( 'bul_show_ue_rangs', 
      { 'initvalue' : 1,
        'title' : 'Afficher le classement dans chaque UE sur les bulletins',
        'input_type' : 'boolcheckbox',
        'category' : 'bul',
        'labels' : ['non', 'oui']
        }
      ),
    ( 'bul_show_mod_rangs', 
      { 'initvalue' : 1,
        'title' : 'Afficher le classement dans chaque module sur les bulletins',
        'input_type' : 'boolcheckbox',
        'category' : 'bul',
        'labels' : ['non', 'oui']
        }
      ),
    ( 'bul_show_uevalid', 
      { 'initvalue' : 1,
        'title' : 'Faire figurer les UE validées sur les bulletins',
        'input_type' : 'boolcheckbox',
        'category' : 'bul',
        'labels' : ['non', 'oui']
        }
      ),
    
    # XXX A COMPLETER, voir sco_formsemestre_edit.py XXX

    # bul_mail
    ( 'email_copy_bulletins',
      { 'initvalue' : '',
        'title' : 'e-mail copie bulletins',
        'size' : 40,
        'explanation' : 'adresse recevant une copie des bulletins envoyés aux étudiants',
        'category' : 'bul_mail'
        }
      ),
    ( 'email_from_addr',
      { 'initvalue' : 'noreply', 
        'title' : 'adresse mail origine',
        'size' : 40,
        'explanation' : 'adresse expéditeur pour les envois par mails (bulletins)',
        'category' : 'bul_mail',
        'only_global' : True
        }
      ),
    ( 'bul_intro_mail',
      { 'initvalue' : """%(nomprenom)s,\n\nvous trouverez ci-joint votre relevé de notes au format PDF.\nIl s\'agit d\'un relevé indicatif. Seule la version papier signée par le responsable pédagogique de l\'établissement prend valeur officielle.\n\nPour toute question sur ce document, contactez votre enseignant ou le directeur des études (ne pas répondre à ce message).\n\nCordialement,\nla scolarité du département %(dept)s.\n\nPS: si vous recevez ce message par erreur, merci de contacter %(webmaster)s""",
        'input_type' : 'textarea',
        'title' : "Message d'accompagnement",
        'explanation' : '<tt>%(DeptName)s</tt> est remplacé par le nom du département, <tt>%(nomprenom)s</tt> par les noms et prénoms de l\'étudiant, <tt>%(dept)s</tt> par le nom du département, et <tt>%(webmaster)s</tt> par l\'adresse mail du Webmaster.',
        'rows' : 18,
        'cols' : 85,
        'category' : 'bul_mail' }
      ),

    ( 'bul_mail_contact_addr',
      { 'initvalue' : "l'administrateur",
        'title' : 'Adresse mail contact "webmaster"',
        'explanation' : 'apparait dans le mail accompagnant le bulletin, voir balise "webmaster" ci-dessus.',
        'category' : 'bul_mail',
        'size' : 32
        }
      ),
    ( 'bul_title', 
      { 'initvalue' : 'Université Paris 13 - IUT de Villetaneuse - Département %(DeptName)s',
        'size' : 70, 
        'title' : 'Titre des bulletins', 
        'explanation' : '<tt>%(DeptName)s</tt> est remplacé par le nom du département',
        'category' : 'bul' }
      ),
    # bul_margins
    ( 'left_margin', 
      { 'initvalue' : 0, 
        'size' : 10, 'title' : 'Marge gauche', 'type' : 'float',
        'category' : 'bul_margins'
       }),
    ( 'top_margin', 
      { 'initvalue' : 0, 
        'size' : 10, 'title' : 'Marge haute', 'type' : 'float',
        'category' : 'bul_margins'
       }),
    ( 'right_margin', 
      { 'initvalue' : 0, 
        'size' : 10, 'title' : 'Marge droite', 'type' : 'float',
        'category' : 'bul_margins'
       }),
    ( 'bottom_margin', 
      { 'initvalue' : 0, 
        'size' : 10, 'title' : 'Marge basse', 'type' : 'float',
        'category' : 'bul_margins'
       }),
        

)

PREFS_NAMES = set( [ x[0] for x in PREFS ] )
PREFS_ONLY_GLOBAL = set( [ x[0] for x in PREFS if x[1].get('only_global',False) ] )

PREFS_DICT = dict(PREFS)

class sco_base_preferences:
    _editor = EditableTable(
        'sco_prefs',
        'pref_id',
        ('pref_id', 'name', 'value', 'formsemestre_id'),
        sortkey = 'name',
        convert_null_outputs_to_empty=False,
        allow_set_id = True,
        html_quote=False # car markup pdf reportlab  (<b> etc)
        )
    
    def __init__(self, context):
        self.context = context
        self.load()
    
    def load(self):
        """Load all preferences from db
        """
        log('loading preferences')
        try:
            GSL.acquire()
            cnx = self.context.GetDBConnexion()
            preflist = self._editor.list(cnx)
            self.prefs = { None : {} } # { formsemestre_id (or None) : { name : value } }
            self.default = {} # { name : default_value }
            for p in preflist:
                if not p['formsemestre_id'] in self.prefs:
                    self.prefs[p['formsemestre_id']] = {}
                
                # Convert types:
                if p['name'] in PREFS_DICT and PREFS_DICT[p['name']].has_key('type'):
                    func = eval(PREFS_DICT[p['name']]['type'])
                    p['value'] = func(p['value'])
                if p['name'] in PREFS_DICT and PREFS_DICT[p['name']].get('input_type',None) == 'boolcheckbox':
                    if p['value']:
                        p['value'] = int(p['value']) # boolcheckboxes are always 0/1
                    else:
                        p['value'] = 0 # NULL (backward compat)
                self.prefs[p['formsemestre_id']][p['name']] = p['value']
            
            # log('prefs=%s' % self.prefs)
            
            # add defaults for missing prefs
            for pref in PREFS:
                name = pref[0]
                
                # Migration from previous ScoDoc installations (before june 2008)
                # search preferences in Zope properties and in configuration file
                if name and name[0] != '_' and not name in self.prefs[None]:
                    try:
                        value = getattr(self.context,name)
                        log('sco_preferences: found default value in Zope for %s=%s'%(name,value))
                    except:
                        # search in CONFIG
                        if hasattr(CONFIG,name):
                            value = getattr(CONFIG,name)
                            log('sco_preferences: found default value in config for %s=%s'%(name,value))
                        else:
                            # uses hardcoded default
                            value = pref[1]['initvalue']

                    self.default[name] = value
                    self.prefs[None][name] = value
                    log('creating missing preference for %s=%s'%(name,value))
                    # add to db table
                    self._editor.create(cnx, { 'name' : name, 'value' : value })
        finally:
            GSL.release()
    
    def get(self, formsemestre_id, name):
        """Returns preference value.
        If no value defined for this semestre, returns global value.
        """
        if formsemestre_id in self.prefs and name in self.prefs[formsemestre_id]:
            return self.prefs[formsemestre_id][name]
        elif name in self.prefs[None]:
            return self.prefs[None][name]
        else:
            return self.default[name]

    def is_global(self, formsemestre_id, name):
        "True if name if not defined for semestre"
        if not (formsemestre_id in self.prefs) or not name in self.prefs[formsemestre_id]:
            return True
        else:
            return False

    def save(self, formsemestre_id=None, name=None):
        """Write one or all (if name is None) values to db"""
        try:
            GSL.acquire()
            cnx = self.context.GetDBConnexion()
            if name is None:
                names = self.prefs[formsemestre_id].keys()
            else:
                names = [name]
            for name in names:
                value = self.get(formsemestre_id, name)
                log('save pref sem=%s %s=%s' % (formsemestre_id, name, value))
                # existe deja ?
                pdb = self._editor.list(cnx, args={'formsemestre_id' : formsemestre_id, 
                                                   'name' : name})
                if not pdb:
                    # cree preference
                    log('create pref sem=%s %s=%s' % (formsemestre_id, name, value))
                    self._editor.create(cnx, { 'name' : name, 'value' : value,
                                               'formsemestre_id' : formsemestre_id})
                else:
                    # edit existing value
                    self._editor.edit(cnx, 
                                      {'pref_id' : pdb[0]['pref_id'], 
                                       'formsemestre_id' : formsemestre_id, 
                                       'name' : name, 'value' : value
                                       })
            
            # les preferences peuvent affecter les PDF cachés:
            self.context.Notes._inval_cache(pdfonly=True)
        finally:
            GSL.release()
    
    def set(self, formsemestre_id, name, value):
        if not name or name[0] == '_' or name not in PREFS_NAMES:
            raise ValueError('invalid preference name: %s' % name)
        if formsemestre_id and name in PREFS_ONLY_GLOBAL:
            raise ValueError('pref %s is always defined globaly')
        if not formsemestre_id in self.prefs:
            self.prefs[formsemestre_id] = {}
        self.prefs[formsemestre_id][name] = value
        self.save(formsemestre_id, name) # immediately write back to db    

    def delete(self, formsemestre_id, name):
        if not formsemestre_id:
            raise ScoException()
        try:
            GSL.acquire()
            if formsemestre_id in self.prefs and name in self.prefs[formsemestre_id]:
                del self.prefs[formsemestre_id][name]
            cnx = self.context.GetDBConnexion()
            pdb = self._editor.list(cnx, args={'formsemestre_id' : formsemestre_id, 
                                               'name' : name})
            if pdb:
                log('deleting pref sem=%s %s'%(formsemestre_id, name))
                self._editor.delete(cnx, pdb[0]['pref_id'])
        finally:
            GSL.release()
    
    def edit(self, REQUEST):
        """HTML dialog: edit global preferences"""
        H = [ self.context.sco_header(REQUEST, page_title="Préférences"),          
              "<h2>Préférences globales pour %s</h2>" % self.context.ScoURL(),
              """<p class="help">Ces paramètres s'appliquent par défaut à tous les semestres, sauf si ceux-ci définissent des valeurs spécifiques.</p>
              <p class="msg">Attention: cliquez sur "Enregistrer les modifications" en bas de page pour appliquer vos changements !</p>
              """]
        form = _build_form(self, global_edit=True)
        tf = TrivialFormulator(REQUEST.URL0, REQUEST.form, form,
                               initvalues = self.prefs[None],
                               submitlabel = 'Enregistrer les modifications' )
        if tf[0] == 0:
            return '\n'.join(H) + tf[1] + self.context.sco_footer(REQUEST)
        elif tf[0] == -1:
            return REQUEST.RESPONSE.redirect( REQUEST.URL1 ) # cancel
        else:
            for pref in PREFS:
                self.prefs[None][pref[0]] = tf[2][pref[0]]
            self.save()
            return REQUEST.RESPONSE.redirect( REQUEST.URL1 + '?head_message=Préférences modifiées' ) 

_SCO_BASE_PREFERENCES = {} # { URL: sco_base_preferences instance }
def get_base_preferences(context):
    """Return global preferences for this context"""
    u = context.ScoURL()
    if not u in _SCO_BASE_PREFERENCES:
        _SCO_BASE_PREFERENCES[u] = sco_base_preferences(context)
    return _SCO_BASE_PREFERENCES[u]


class sem_preferences:
    def __init__(self, context, formsemestre_id=None):
        self.context = context
        self.formsemestre_id = formsemestre_id
        self.base_prefs = get_base_preferences(self.context)

    def __getitem__(self, name):
        return self.base_prefs.get(self.formsemestre_id, name)

    def get(self, name, defaultvalue=None):
        # utilisé seulement par TF
        try:
            return self[name] # ignore supplied default value
        except:
            return defaultvalue

    def is_global(self, name):
        "True if preference defined for all semestres"
        return self.base_prefs.is_global(self.formsemestre_id, name) 

    # The dialog
    def edit(self, categories=[], REQUEST=None):
        """Dialog to edit semestre preferences in given categories"""
        if not self.formsemestre_id:
            raise ScoValueError('sem_preferences.edit doit etre appele sur un semestre !') # a bug !
        sem = self.context.Notes.get_formsemestre(self.formsemestre_id)
        H = [ self.context.Notes.html_sem_header(REQUEST, 'Préférences du semestre', sem),
              """
<p class="help">Les paramètres définis ici ne s'appliqueront qu'à ce semestre.</p>
<p class="msg">Attention: cliquez sur "Enregistrer les modifications" en bas de page pour appliquer vos changements !</p>
<script type="text/javascript">
function sel_global(el, pref_name) {
     if (el.value == 'create') {
        document.getElementById('tf').create_local.value = pref_name;
        document.getElementById('tf').destination.value = 'again';
        document.tf.submit();
     } else if (el.value == 'changeglobal') {
        document.getElementById('tf').destination.value = 'global';
        document.tf.submit();
     }
}
function set_global_pref(el, pref_name) {
     document.getElementById('tf').suppress.value = pref_name;
     document.getElementById('tf').destination.value = 'again';
     f = document.getElementById('tf')[pref_name];
     if (f) {
       f.disabled = true;
     } else {
       f = document.getElementById('tf')[pref_name+':list'];
       if (f) {
         f.disabled = true;
       }
     }
     document.tf.submit();
}
</script>
"""
              ]
        # build the form:
        form = _build_form(self,categories=categories)
        form.append( ('suppress', { 'input_type' : 'hidden' } ) )
        form.append( ('create_local', { 'input_type' : 'hidden' } ) )
        form.append( ('destination', { 'input_type' : 'hidden' } ) )
        form.append( ('formsemestre_id', {'input_type' : 'hidden' }) )
        log('REQUEST form=%s'%REQUEST.form)
        tf = TrivialFormulator(REQUEST.URL0, REQUEST.form, form, 
                               initvalues = self,
                               cssclass="sco_pref",
                               submitlabel = 'Enregistrer les modifications' )
        if tf[0] == 0:
            return '\n'.join(H) + tf[1] + self.context.sco_footer(REQUEST)
        elif tf[0] == -1:
            return REQUEST.RESPONSE.redirect( REQUEST.URL1 + '?head_message=Annulé' ) # cancel
        else:
            log('tf[2]=%s' % tf[2])
            # Supprime pref locale du semestre (retour à la valeur globale)
            if tf[2]['suppress']:
                self.base_prefs.delete(self.formsemestre_id, tf[2]['suppress'])
            # Cree pref local (copie valeur globale)
            if tf[2]['create_local']:
                cur_value = self[tf[2]['create_local']]
                self.base_prefs.set(self.formsemestre_id, tf[2]['create_local'], cur_value)
            # Modifie valeurs:
            for (pref_name, descr) in PREFS:
                if pref_name in tf[2] and not descr.get('only_global',False) and pref_name != tf[2]['suppress']:
                    form_value = tf[2][pref_name]
                    cur_value = self[pref_name]
                    if cur_value is None:
                        cur_value = ''
                    else:
                        cur_value = str(cur_value)
                    if cur_value != str(form_value):
                        # log('cur_value=%s (type %s), form_value=%s (type %s)' % (cur_value,type(cur_value),form_value, type(form_value)))
                        self.base_prefs.set(self.formsemestre_id,  pref_name, form_value)
            
            # destination: 
            # global: change pref and redirect to global params
            # again: change prefs and redisplay this dialog
            # done: change prefs and redirect to semestre status
            destination = tf[2]['destination']
            if destination == 'done' or destination == '':
                return REQUEST.RESPONSE.redirect( REQUEST.URL1 + '/formsemestre_status?head_message=Préférences modifiées&formsemestre_id=' + self.formsemestre_id ) 
            elif destination == 'again':
                return REQUEST.RESPONSE.redirect( REQUEST.URL0 + '?formsemestre_id=' + self.formsemestre_id )
            elif destination == 'global':
                return REQUEST.RESPONSE.redirect( self.context.ScoURL() + '/edit_preferences' )
            


# Build list of elements for TrivialFormulator...
def _build_form(self, categories=[], global_edit=False):
    form = []
    for cat, cat_descr in PREF_CATEGORIES:
        if categories and cat not in categories:
            continue # skip this category
        #
        cat_elems = []
        for pref_name, pref in PREFS:
            if pref['category'] == cat:
                if pref.get('only_global',False) and not global_edit:
                    continue # saute les prefs seulement globales
                descr = pref.copy()
                descr['comment'] = descr.get('explanation', None)
                if 'explanation' in descr:
                    del descr['explanation']
                if not global_edit:
                    descr['explanation'] = """ou <a href="" onClick="set_global_pref(this, '%s');">utiliser paramètre global</a>""" % pref_name
                #if descr.get('only_global',False):
                #    # pas modifiable, donne juste la valeur courante
                #    descr['readonly'] = True
                #    descr['explanation'] = '(valeur globale, non modifiable)'
                #elif
                if not global_edit and self.is_global(pref_name):
                    # valeur actuelle globale (ou vient d'etre supprimee localement):
                    # montre la valeur et menus pour la rendre locale
                    descr['readonly'] = True
                    menu_global = """<select class="tf-selglobal" onChange="sel_global(this, '%s');">
                        <option value=""><em>Valeur définie globalement</em></option>
                        <option value="create">Spécifier valeur pour ce semestre seulement</option>
                    </select>
                    """ % pref_name
#                         <option value="changeglobal">Changer paramètres globaux</option>
                    descr['explanation'] = menu_global

                cat_elems.append( (pref_name, descr) )
        if cat_elems:
            # category titles:
            title = cat_descr.get('title', None)
            if title:
                form.append( ('sep_%s'%cat, { 'input_type' : 'separator',
                                              'title' : '<h3>%s</h3>' % title }))
            subtitle = cat_descr.get('subtitle', None)
            if subtitle:
                form.append( ('sepsub_%s'%cat, { 'input_type' : 'separator',
                                                 'title' : '<p class="help">%s</p>' % subtitle }))
            form.extend(cat_elems)
    return form

# essais:
def edit_preferences2(context, REQUEST):
    """essai jQuery
    """
    H = [ context.sco_header(
            page_title='Préférences', 
            REQUEST=REQUEST,
            javascripts=[ 'jquery_1_2_6_min_js' ],
            scripts=[ """
$(function() {
   // $('#vide').html('hello !');
   
});
          """ 
                      ]),
          """
<form>
<input type="text" id="essai" name="essai" size="16" value="blurps"/>
</form>
          """
          ]
    
    return '\n'.join(H) + context.sco_footer(REQUEST)
