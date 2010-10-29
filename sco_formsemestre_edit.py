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

"""Form choix modules / responsables et creation formsemestre
"""

from notesdb import *
from sco_utils import *
import sco_groups
from notes_log import log
from TrivialFormulator import TrivialFormulator, TF
import sco_portal_apogee, scolars, sco_parcours_dut
import sco_compute_moy

def _default_sem_title(F):
    """Default title for a semestre in formation F"""
    return F['titre']


def formsemestre_createwithmodules(context, REQUEST=None):
    """Page création d'un semestre"""
    H = [ context.sco_header(REQUEST, page_title='Création d\'un semestre',
                             init_jquery_ui=True,
                             javascripts=['libjs/AutoSuggest.js'],
                             cssstyles=['autosuggest_inquisitor.css'], 
                             bodyOnLoad="init_tf_form('')"
                             ),
          """<h2>Mise en place d'un semestre de formation</h2>""",
          do_formsemestre_createwithmodules(context, REQUEST=REQUEST),
          context.sco_footer(REQUEST)
          ]
    return '\n'.join(H)

def formsemestre_editwithmodules(context, REQUEST, formsemestre_id):
    """Page modification semestre"""
    # portage from dtml
    authuser = REQUEST.AUTHENTICATED_USER
    sem = context.get_formsemestre(formsemestre_id)
    F = context.formation_list( args={ 'formation_id' : sem['formation_id'] } )[0]
    H = [ context.html_sem_header(REQUEST, 'Modification du semestre', sem,
                                  init_jquery_ui=True,
                                  javascripts=['libjs/AutoSuggest.js'],
                                  cssstyles=['autosuggest_inquisitor.css'], 
                                  bodyOnLoad="init_tf_form('')"
                                  ) ]
    if sem['etat'] != '1':
        H.append("""<p>%s<b>Ce semestre est verrouillé.</b></p>""" %
                 context.icons.lock_img.tag(border='0',title='Semestre verrouillé'))
    else:
        H.append(do_formsemestre_createwithmodules(context, REQUEST=REQUEST, edit=1 ))
        if not REQUEST.get('tf-submitted',False):
            H.append("""<p class="help">Seuls les modules cochés font partie de ce semestre. Pour les retirer, les décocher et appuyer sur le bouton "modifier".
</p>
<p class="help">Attention : s'il y a déjà des évaluations dans un module, il ne peut pas être supprimé !</p>
<p class="help">Les modules ont toujours un responsable. Par défaut, c'est le directeur des études.</p>""")
    
    return '\n'.join(H) + context.sco_footer(REQUEST)


def can_edit_sem(context, REQUEST, formsemestre_id, sem=None):
    """Return sem if user can edit it, False otherwise
    """
    sem = sem or context.get_formsemestre(formsemestre_id)
    authuser = REQUEST.AUTHENTICATED_USER
    if not authuser.has_permission(ScoImplement,context):
        if not sem['resp_can_edit'] or str(authuser) != sem['responsable_id']:
            return False
    return sem

def do_formsemestre_createwithmodules(context, REQUEST=None, edit=False ):
    "Form choix modules / responsables et creation formsemestre"
    # Fonction accessible à tous, controle acces à la main:
    if edit:
        formsemestre_id = REQUEST.form['formsemestre_id']
        sem = context.get_formsemestre(formsemestre_id)
    authuser = REQUEST.AUTHENTICATED_USER
    if not authuser.has_permission(ScoImplement,context):
        if not edit:
            # il faut ScoImplement pour creer un semestre
            raise AccessDenied("vous n'avez pas le droit d'effectuer cette opération")
        else:
            if not sem['resp_can_edit'] or str(authuser) != sem['responsable_id']:
                raise AccessDenied("vous n'avez pas le droit d'effectuer cette opération")
    
    # Liste des enseignants avec forme pour affichage / saisie avec suggestion
    userlist = context.Users.get_userlist()
    login2display = {} # user_name : forme pour affichage = "NOM Prenom (login)"
    for u in userlist:
        login2display[u['user_name']] = u['nomplogin']
    allowed_user_names = login2display.values() + ['']
    #
    formation_id = REQUEST.form['formation_id']
    F = context.formation_list( args={ 'formation_id' : formation_id } )
    if not F:
        raise ScoValueError('Formation inexistante !')
    F = F[0]
    if not edit:
        initvalues = {
            'titre' : _default_sem_title(F)
            }
        semestre_id  = REQUEST.form['semestre_id']        
    else:
        # setup form init values
        initvalues = sem
        semestre_id = initvalues['semestre_id']
#        initvalues['inscrire_etuds'] = initvalues.get('inscrire_etuds','1')
#        if initvalues['inscrire_etuds'] == '1':
#            initvalues['inscrire_etudslist'] = ['X']
#        else:
#            initvalues['inscrire_etudslist'] = []
#        if REQUEST.form.get('tf-submitted',False) and not REQUEST.form.has_key('inscrire_etudslist'):
#            REQUEST.form['inscrire_etudslist'] = []
        # add associated modules to tf-checked
        ams = context.do_moduleimpl_list( { 'formsemestre_id' : formsemestre_id } )
        initvalues['tf-checked'] = [ x['module_id'] for x in ams ]
        for x in ams:
            initvalues[str(x['module_id'])] = login2display.get(x['responsable_id'], x['responsable_id'])
        
        initvalues['responsable_id'] = login2display.get(sem['responsable_id'], sem['responsable_id'])

    # Liste des ID de semestres
    cnx = context.GetDBConnexion()
    cursor = cnx.cursor()
    cursor.execute( "select semestre_id from notes_semestres" )
    semestre_id_list = [ str(x[0]) for x in cursor.fetchall() ]
    semestre_id_labels = []
    for sid in semestre_id_list:
        if sid == '-1':
            semestre_id_labels.append('pas de semestres')
        else:
            semestre_id_labels.append(sid)
    # Liste des modules  dans ce semestre de cette formation
    # on pourrait faire un simple context.module_list( )
    # mais si on veut l'ordre du PPN (groupe par UE et matieres) il faut:
    mods = [] # liste de dicts
    uelist = context.do_ue_list( { 'formation_id' : formation_id } )
    for ue in uelist:
        matlist = context.do_matiere_list( { 'ue_id' : ue['ue_id'] } )
        for mat in matlist:
            modsmat = context.do_module_list( { 'matiere_id' : mat['matiere_id'] } )
            # XXX debug checks
            for m in modsmat:
                log('checking module %s (ue_id %s)' % (m['module_id'], ue['ue_id']))
                if m['ue_id'] != ue['ue_id']:
                    log('XXX createwithmodules: m.ue_id=%s !' % m['ue_id'])
                if m['formation_id'] != formation_id:
                    log('XXX createwithmodules: formation_id=%s\n\tm=%s' % (formation_id,str(m)))
                if m['formation_id'] != ue['formation_id']:
                    log('XXX createwithmodules: formation_id=%s\n\tue=%s\tm=%s' % (formation_id,str(ue),str(m)))
            # /debug
            mods = mods + modsmat
    # Pour regroupement des modules par semestres:
    semestre_ids = {}
    for mod in mods:
        semestre_ids[mod['semestre_id']] = 1
    semestre_ids = semestre_ids.keys()
    semestre_ids.sort()
    #
    modform = [
        ('formsemestre_id', { 'input_type' : 'hidden' }),
        ('formation_id', { 'input_type' : 'hidden', 'default' : formation_id}),
        ('date_debut', { 'title' : 'Date de début', # j/m/a
                         'input_type' : 'date', 
                         'explanation' : 'j/m/a',
                         'size' : 9, 'allow_null' : False }),
        ('date_fin', { 'title' : 'Date de fin',  # j/m/a
                       'input_type' : 'date', 
                       'explanation' : 'j/m/a',
                       'size' : 9, 'allow_null' : False }),
        ('responsable_id', { 'input_type' : 'text_suggest',
                             'size' : 50,
                             'title' : 'Directeur des études',
                             'explanation' : 'taper le début du nom et choisir dans le menu',
                             'allowed_values' : allowed_user_names,
                             'allow_null' : False,
                             'text_suggest_options' : { 
                                             'script' : 'Users/get_userlist_xml?',
                                             'varname' : 'start',
                                             'json': False,
                                             'noresults' : 'Valeur invalide !',
                                             'timeout':60000 }
                             }), 
        ('titre', { 'size' : 40, 'title' : 'Nom de ce semestre',
                    'explanation' : """n'indiquez pas les dates, ni le semestre, ni la modalité dans le titre: ils seront automatiquement ajoutés <input type="button" value="remettre titre par défaut" onClick="document.tf.titre.value='%s';"/>""" % _default_sem_title(F)
                    }),
        ('modalite', { 'input_type' : 'menu',
                          'title' : 'Modalité',
                          'allowed_values' : ('', 'FI', 'FC', 'FAP'),
                          'labels' : ('Inconnue', 'Formation Initiale', 'Formation Continue', 'Apprentissage') }),
        ('semestre_id', { 'input_type' : 'menu',
                          'title' : 'Semestre dans la formation',
                          'allowed_values' : semestre_id_list,
                          'labels' : semestre_id_labels })
        ]
    etapes = sco_portal_apogee.get_etapes_apogee_dept(context)
    if etapes:
        # propose les etapes renvoyées par le portail
        modform.append(
        ('etape_apo', {
            'input_type' : 'menu',
            'title' : 'Etape Apogée',
            'allowed_values' : [''] + [ e[0] for e in etapes ],
            'labels' :  ['(aucune)'] + [ '%s (%s)' % (e[1], e[0]) for e in etapes ],
            'explanation' : 'nécessaire pour inscrire les étudiants et exporter les notes en fin de semestre'
            }))
        modform.append(
        ('etape_apo2', {
            'input_type' : 'menu',
            'title' : 'Etape Apogée (2)',
            'allowed_values' : [''] + [ e[0] for e in etapes ],
            'labels' :  ['(aucune)'] + [ '%s (%s)' % (e[1], e[0]) for e in etapes ],
            'explanation' : '(si deux étape pour ce même semestre)'
            }))
    else:
        # fallback: code etape libre
        modform.append(
        ('etape_apo', { 'size' : 12,
                        'title' : 'Code étape Apogée',
                        'explanation' : 'facultatif, nécessaire pour synchroniser les listes et exporter les décisions' })
        )
        modform.append(
        ('etape_apo2', { 'size' : 12,
                        'title' : 'Code étape Apogée (2)',
                        'explanation' : '(si deux étape pour ce même semestre)' })
        )
    if edit:
        formtit = """
        <p><a href="formsemestre_edit_uecoefs?formsemestre_id=%s">Modifier les coefficients des UE capitalisées</a></p>
        <h3>Sélectionner les modules, leurs responsables et les étudiants à inscrire:</h3>
        """ % formsemestre_id
    else:
        formtit = """<h3>Sélectionner les modules et leurs responsables</h3><p class="help">Si vous avez des parcours (options), ne sélectionnez que les modules du tronc commun.</p>"""

    modform += [
        ('gestion_compensation_lst',  { 'input_type' : 'checkbox',
                                        'title' : 'Jurys',
                                        'allowed_values' : ['X'],
                                        'explanation' : 'proposer compensations de semestres (parcours DUT)',
                                        'labels' : [''] }),

        ('gestion_semestrielle_lst',  { 'input_type' : 'checkbox',
                                        'title' : '',
                                        'allowed_values' : ['X'],
                                        'explanation' : 'formation semestrialisée (jurys avec semestres décalés)',
                                        'labels' : [''] }) ]
    if authuser.has_permission(ScoImplement,context):
        modform += [ 
        ('resp_can_edit',  { 'input_type' : 'boolcheckbox',
                             'title' : 'Autorisations',
                             'explanation' : 'Autoriser le directeur des études à modifier ce semestre' })]                             
    modform += [ 
        ('resp_can_change_ens',  { 
                    'input_type' : 'boolcheckbox',
                    'title' : '',
                    'explanation' : 'Autoriser le directeur des études à modifier les enseignants' }),

        ('bul_bgcolor', { 'size' : 8,
                          'title' : 'Couleur fond des bulletins',
                          'explanation' : 'version web seulement (ex: #ffeeee)' }),

        ('bul_publish_xml_lst', { 'input_type' : 'checkbox',
                                  'title' : 'Publication',
                                  'allowed_values' : ['X'],
                                  'explanation' : 'publier le bulletin sur le portail étudiants',
                                  'labels' : [''] }),

        ('sep', { 'input_type' : 'separator',                  
                  'title' : '',
                  'template' : '</table>%s<table>' % formtit
                  }) ]

    nbmod = 0
    if edit:
        templ_sep = '<tr><td>%(label)s</td><td><b>Responsable</b></td><td><b>Inscrire</b></td></tr>'
    else:
        templ_sep = '<tr><td>%(label)s</td><td><b>Responsable</b></td></tr>'
    for semestre_id in semestre_ids:
        modform.append(('sep',
                        { 'input_type' : 'separator',
                          'title' : '<b>Semestre %s</b>' % semestre_id,
                          'template' : templ_sep}))
        for mod in mods:
            if mod['semestre_id'] == semestre_id:
                nbmod += 1;
                if edit:
                    fcg = '<select name="%s!group_id">' % mod['module_id']
                    fcg += '<option value="%s">Tous</option>' % sco_groups.get_default_group(context,formsemestre_id)
                    fcg += '<option value="">Aucun</option>'
                    for p in sco_groups.get_partitions_list(context, formsemestre_id):
                        if p['partition_name'] != None:
                            for group in sco_groups.get_partition_groups(context, p):
                                fcg += '<option value="%s">%s %s</option>' % (group['group_id'], p['partition_name'], group['group_name'])
                    fcg += '</select>'
                    itemtemplate = """<tr><td class="tf-fieldlabel">%(label)s</td><td class="tf-field">%(elem)s</td><td>""" + fcg + '</td></tr>'
                else:
                    itemtemplate = """<tr><td class="tf-fieldlabel">%(label)s</td><td class="tf-field">%(elem)s</td></tr>"""
                modform.append( (str(mod['module_id']),
                                 { 'input_type' : 'text_suggest',
                                   'size' : 50,
                                   'withcheckbox' : True,
                                   'title' : '%s %s' % (mod['code'],mod['titre']),
                                   'allowed_values' : allowed_user_names,
                                   'template' : itemtemplate,
                                   'text_suggest_options' : { 
                                                   'script' : 'Users/get_userlist_xml?',
                                                   'varname' : 'start',
                                                   'json': False,
                                                   'noresults' : 'Valeur invalide !',
                                                   'timeout':60000 }
                                   }) )
    if nbmod == 0:
        modform.append(('sep',
                        { 'input_type' : 'separator',
                          'title' : 'aucun module dans cette formation !!!'}))
    if edit:
#         modform.append( ('inscrire_etudslist',
#                          { 'input_type' : 'checkbox',
#                            'allowed_values' : ['X'], 'labels' : [ '' ],
#                            'title' : '' ,
#                            'explanation' : 'inscrire tous les étudiants du semestre aux modules ajoutés'}) )
        submitlabel = 'Modifier ce semestre de formation'
    else:
        submitlabel = 'Créer ce semestre de formation'
    #
    
    initvalues['gestion_compensation'] = initvalues.get('gestion_compensation','0')
    if initvalues['gestion_compensation'] == '1':
        initvalues['gestion_compensation_lst'] = ['X']
    else:
        initvalues['gestion_compensation_lst'] = []
    if REQUEST.form.get('tf-submitted',False) and not REQUEST.form.has_key('gestion_compensation_lst'):
        REQUEST.form['gestion_compensation_lst'] = []

    initvalues['gestion_semestrielle'] = initvalues.get('gestion_semestrielle','0')
    if initvalues['gestion_semestrielle'] == '1':
        initvalues['gestion_semestrielle_lst'] = ['X']
    else:
        initvalues['gestion_semestrielle_lst'] = []        
    if REQUEST.form.get('tf-submitted',False) and not REQUEST.form.has_key('gestion_semestrielle_lst'):
        REQUEST.form['gestion_semestrielle_lst'] = []

    initvalues['bul_hide_xml'] = initvalues.get('bul_hide_xml','0')
    if initvalues['bul_hide_xml'] == '0':
        initvalues['bul_publish_xml_lst'] = ['X']
    else:
        initvalues['bul_publish_xml_lst'] = []
    if REQUEST.form.get('tf-submitted',False) and not REQUEST.form.has_key('bul_publish_xml_lst'):
        REQUEST.form['bul_publish_xml_lst'] = []

    #
    tf = TrivialFormulator( REQUEST.URL0, REQUEST.form, modform,
                            submitlabel = submitlabel,
                            cancelbutton = 'Annuler',
                            top_buttons=True,
                            initvalues = initvalues)
    msg = ''
    if tf[0] == 1:
        # check dates
        if DateDMYtoISO(tf[2]['date_debut']) > DateDMYtoISO(tf[2]['date_fin']):
            msg = '<ul class="tf-msg"><li class="tf-msg">Dates de début et fin incompatibles !</li></ul>'            
    
    if tf[0] == 0 or msg:
        return '<p>Formation <a class="discretelink" href="ue_list?formation_id=%(formation_id)s"><em>%(titre)s</em> (%(acronyme)s), version %(version)d, code %(formation_code)s</a></p>' % F + msg + tf[1]
    elif tf[0] == -1:
        return '<h4>annulation</h4>'
    else:
        if tf[2]['gestion_compensation_lst']:
            tf[2]['gestion_compensation'] = 1
        else:
            tf[2]['gestion_compensation'] = 0
        if tf[2]['gestion_semestrielle_lst']:
            tf[2]['gestion_semestrielle'] = 1
        else:
            tf[2]['gestion_semestrielle'] = 0
        if tf[2]['bul_publish_xml_lst']:
            tf[2]['bul_hide_xml'] = 0
        else:
            tf[2]['bul_hide_xml'] = 1

        # remap les identifiants de responsables:
        tf[2]['responsable_id'] = context.Users.get_user_name_from_nomplogin(tf[2]['responsable_id'])
        for module_id in tf[2]['tf-checked']:
            mod_resp_id = context.Users.get_user_name_from_nomplogin(tf[2][module_id])
            if mod_resp_id is None:
                # Si un module n'a pas de responsable (ou inconnu), l'affecte au directeur des etudes:
                mod_resp_id = tf[2]['responsable_id']
            tf[2][module_id] = mod_resp_id
        
        if not edit:
            # creation du semestre  
            formsemestre_id = context.do_formsemestre_create(tf[2], REQUEST)
            # creation des modules
            for module_id in tf[2]['tf-checked']:
                modargs = { 'module_id' : module_id,
                            'formsemestre_id' : formsemestre_id,
                            'responsable_id' :  tf[2][module_id]
                            }
                mid = context.do_moduleimpl_create(modargs)
            return REQUEST.RESPONSE.redirect('formsemestre_status?formsemestre_id=%s&head_message=Nouveau%%20semestre%%20créé' % formsemestre_id )
        else:
            # modification du semestre:
            # on doit creer les modules nouvellement selectionnés
            # modifier ceux a modifier, et DETRUIRE ceux qui ne sont plus selectionnés.
            # Note: la destruction echouera s'il y a des objets dependants
            #       (eg des evaluations définies)
            # nouveaux modules
            checkedmods = tf[2]['tf-checked']
            context.do_formsemestre_edit(tf[2])
            ams = context.do_moduleimpl_list(
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
                moduleimpl_id = context.do_moduleimpl_create(modargs)
                mod = context.do_module_list( { 'module_id' : module_id } )[0]
                msg += [ 'création de %s (%s)' % (mod['code'], mod['titre']) ] 
                # INSCRIPTIONS DES ETUDIANTS                
                log('inscription module: %s = "%s"' % ('%s!group_id'%module_id,tf[2]['%s!group_id'%module_id]))
                group_id = tf[2]['%s!group_id'%module_id]
                if group_id:
                    etudids = [ x['etudid'] for x in sco_groups.get_group_members(context, group_id) ]
                    log('inscription module:module_id=%s,moduleimpl_id=%s: %s' % (module_id,moduleimpl_id,etudids) )
                    context.do_moduleimpl_inscrit_etuds(moduleimpl_id,formsemestre_id, etudids,
                                                    REQUEST=REQUEST)
                    msg += [ 'inscription de %d étudiants au module %s' % (len(etudids),mod['code'])]
                else:
                    log('inscription module:module_id=%s,moduleimpl_id=%s: aucun etudiant inscrit' % (module_id,moduleimpl_id) )
            #
            ok, diag = formsemestre_delete_moduleimpls(context, formsemestre_id, mods_todelete)
            msg += diag
            for module_id in mods_toedit:
                moduleimpl_id = context.do_moduleimpl_list(
                    { 'formsemestre_id' : formsemestre_id,
                      'module_id' : module_id } )[0]['moduleimpl_id']
                modargs = {
                    'moduleimpl_id' : moduleimpl_id,
                    'module_id' : module_id,
                    'formsemestre_id' : formsemestre_id,
                    'responsable_id' :  tf[2][module_id] }
                context.do_moduleimpl_edit(modargs, formsemestre_id=formsemestre_id)
                mod = context.do_module_list( { 'module_id' : module_id } )[0]
            
            if msg:
                msg_html = '<div class="ue_warning"><span>Attention !<ul><li>' + '</li><li>'.join(msg) + '</li></ul></span></div>'
                if ok:
                    msg_html += '<p>Modification effectuée</p>'
                else:
                    msg_html += '<p>Modification effectuée (<b>mais modules cités non supprimés</b>)</p>'
                msg_html += '<a href="formsemestre_status?formsemestre_id=%s">retour au tableau de bord</a>' %  formsemestre_id
                return msg_html            
            else:
                return REQUEST.RESPONSE.redirect( 'formsemestre_status?formsemestre_id=%s&head_message=Semestre modifié' %  formsemestre_id)


def formsemestre_delete_moduleimpls(context, formsemestre_id, module_ids_to_del):
    """Delete moduleimpls
     module_ids_to_del: list of module_id (warning: not moduleimpl)
     Moduleimpls must have no associated evaluations.
     """
    ok = True
    msg = []
    for module_id in module_ids_to_del:
        # get id
        moduleimpl_id = context.do_moduleimpl_list(
            { 'formsemestre_id' : formsemestre_id,
              'module_id' : module_id } )[0]['moduleimpl_id']
        mod = context.do_module_list( { 'module_id' : module_id } )[0]
        # Evaluations dans ce module ?
        evals = context.do_evaluation_list( { 'moduleimpl_id' : moduleimpl_id} )
        if evals:
            msg += [ '<b>impossible de supprimer %s (%s) car il y a %d évaluations définies (<a href="moduleimpl_status?moduleimpl_id=%s" class="stdlink">supprimer les d\'abord</a>)</b>' % (mod['code'], mod['titre'], len(evals), moduleimpl_id) ]
            ok = False
        else:
            msg += [ 'suppression de %s (%s)'
                     % (mod['code'], mod['titre']) ]
            context.do_moduleimpl_delete(moduleimpl_id, formsemestre_id=formsemestre_id)

    return ok, msg


def formsemestre_clone(context, formsemestre_id, REQUEST=None):
    """
    Formulaire clonage d'un semestre
    """
    authuser = REQUEST.AUTHENTICATED_USER
    sem = context.get_formsemestre(formsemestre_id)
    # Liste des enseignants avec forme pour affichage / saisie avec suggestion
    userlist = context.Users.get_userlist()
    login2display = {} # user_name : forme pour affichage = "NOM Prenom (login)"
    for u in userlist:
        login2display[u['user_name']] = u['nomplogin']
    allowed_user_names = login2display.values() + ['']
    
    initvalues = {
        'formsemestre_id' : sem['formsemestre_id'],
        'responsable_id' : login2display.get(sem['responsable_id'], sem['responsable_id']) }
    
    H = [
        context.html_sem_header(REQUEST, 'Copie du semestre', sem,
                                init_jquery_ui=True,
                                javascripts=['libjs/AutoSuggest.js'],
                                cssstyles=['autosuggest_inquisitor.css'],
                                bodyOnLoad="init_tf_form('')"),
        """<p class="help">Cette opération duplique un semestre: on reprend les mêmes modules et responsables. Aucun étudiant n'est inscrit.</p>"""
    ]

    descr = [
        ('formsemestre_id', { 'input_type' : 'hidden' }), 
        ('date_debut', { 'title' : 'Date de début',  # j/m/a
                         'input_type' : 'date',
                         'explanation' : 'j/m/a',
                         'size' : 9, 'allow_null' : False }),
        ('date_fin', { 'title' : 'Date de fin',  # j/m/a
                       'input_type' : 'date',
                       'explanation' : 'j/m/a',
                       'size' : 9, 'allow_null' : False }),
        ('responsable_id',  { 'input_type' : 'text_suggest',
                              'size' : 50,
                              'title' : 'Directeur des études',
                              'explanation' : 'taper le début du nom et choisir dans le menu',
                              'allowed_values' : allowed_user_names,
                              'allow_null' : False,
                              'text_suggest_options' : { 
                    'script' : 'Users/get_userlist_xml?',
                    'varname' : 'start',
                    'json': False,
                    'noresults' : 'Valeur invalide !',
                    'timeout':60000 } }), 
        ('clone_evaluations', 
         { 'title' : "Copier aussi les évaluations",
           'input_type' : 'boolcheckbox',
           'explanation' : "copie toutes les évaluations, sans les dates (ni les notes!)"
           }),
        ]
    tf = TrivialFormulator( 
        REQUEST.URL0, REQUEST.form, descr,
        submitlabel = 'Dupliquer ce semestre',
        cancelbutton = 'Annuler',
        initvalues = initvalues)
    
    if tf[0] == 0:
        return ''.join(H) + tf[1] + context.sco_footer(REQUEST)
    elif tf[0] == -1: # cancel
        return REQUEST.RESPONSE.redirect('formsemestre_status?formsemestre_id=%s' % formsemestre_id )
    else:
        new_formsemestre_id = do_formsemestre_clone(
            context, formsemestre_id, 
            context.Users.get_user_name_from_nomplogin(tf[2]['responsable_id']),
            tf[2]['date_debut'], tf[2]['date_fin'],
            clone_evaluations=tf[2]['clone_evaluations'],
            REQUEST=REQUEST)
        return REQUEST.RESPONSE.redirect('formsemestre_status?formsemestre_id=%s&head_message=Nouveau%%20semestre%%20créé' % new_formsemestre_id )    


def do_formsemestre_clone(context, orig_formsemestre_id, 
                          responsable_id, 
                          date_debut, date_fin,  # 'dd/mm/yyyy'
                          clone_evaluations=False,
                          REQUEST=None):
    """Clone a semestre: make copy, same modules, same options, same resps.
    New dates, responsable_id    
    """
    log('cloning %s' % orig_formsemestre_id)
    orig_sem = context.get_formsemestre(orig_formsemestre_id)
    cnx = context.GetDBConnexion()
    # 1- create sem
    args = orig_sem.copy()
    del args['formsemestre_id']
    args['responsable_id'] = responsable_id
    args['date_debut'] = date_debut
    args['date_fin'] = date_fin
    args['etat'] = 1 # non verrouillé
    formsemestre_id = context.do_formsemestre_create(args, REQUEST)
    log('created formsemestre %s' % formsemestre_id)
    # 2- create moduleimpls
    mods_orig = context.do_moduleimpl_list( {'formsemestre_id':orig_formsemestre_id} )
    for mod_orig in mods_orig:
        args = mod_orig.copy()
        args['formsemestre_id'] = formsemestre_id
        mid = context.do_moduleimpl_create(args)        
        # copy notes_modules_enseignants
        ens = context.do_ens_list(args={'moduleimpl_id':mod_orig['moduleimpl_id']})
        for e in ens:
            args = e.copy()
            args['moduleimpl_id'] = mid
            context.do_ens_create(args)
        # optionally, copy evaluations
        if clone_evaluations:
            evals = context.do_evaluation_list( args={ 'moduleimpl_id' : mod_orig['moduleimpl_id']} )
            for e in evals:
                args = e.copy()
                del args['jour'] # erase date
                args['moduleimpl_id'] = mid
                evaluation_id = context.do_evaluation_create( REQUEST, args )
    
    # 3- copy uecoefs
    objs = formsemestre_uecoef_list(cnx, args={'formsemestre_id':orig_formsemestre_id})
    for obj in objs:
        args = obj.copy()
        args['formsemestre_id'] = formsemestre_id
        c = formsemestre_uecoef_create(cnx, args)
    
    # NB: don't copy notes_formsemestre_custommenu (usually specific)
    
    # 4- Copy new style preferences
    prefs = context.get_preferences(orig_formsemestre_id)

    if orig_formsemestre_id in prefs.base_prefs.prefs:
        for pname in prefs.base_prefs.prefs[orig_formsemestre_id]:
            if not prefs.is_global(pname):
                pvalue = prefs[pname]
                prefs.base_prefs.set(formsemestre_id, pname, pvalue)

    # 5- Copy formules utilisateur
    objs = sco_compute_moy.formsemestre_ue_computation_expr_list(cnx, args={'formsemestre_id':orig_formsemestre_id})
    for obj in objs:
        args = obj.copy()
        args['formsemestre_id'] = formsemestre_id
        c = sco_compute_moy.formsemestre_ue_computation_expr_create(cnx, args)
    
    return formsemestre_id

# ---------------------------------------------------------------------------------------

def formsemestre_associate_new_version(context, formsemestre_id, REQUEST=None, dialog_confirmed=False):
    """Formulaire changement formation d'un semestre"""
    if not dialog_confirmed:
        return context.confirmDialog(
            """<h2>Associer une nouvelle version de formation non verrouillée ?</h2>
                <p>Le programme pédagogique ("formation") va être dupliqué pour que vous puissiez le modifier sans affecter les autres semestres. Les autres paramètres (étudiants, notes...) du semestre seront inchangés.</p>
                <p>Veillez à ne pas abuser de cette possibilité, car créer trop de versions de formations va vous compliquer la gestion (à vous de garder trace des différences et à ne pas vous tromper par la suite...).
                </p>
                """,
                dest_url="", REQUEST=REQUEST,
                cancel_url="formsemestre_status?formsemestre_id=%s" % formsemestre_id,
                parameters={'formsemestre_id' : formsemestre_id})
    else:
        do_formsemestre_associate_new_version(context, formsemestre_id, REQUEST=REQUEST)
        return REQUEST.RESPONSE.redirect('formsemestre_status?formsemestre_id=%s&head_message=Formation%%20dupliquée' % formsemestre_id )


def do_formsemestre_associate_new_version(context, formsemestre_id, REQUEST=None):
    """Cree une nouvelle version de la formation du semestre, et y rattache ce semestre.
    Tous les moduleimpl sont ré-associés à la nouvelle formation, ainsi que les decisions de jury 
    si elles existent (codes d'UE validées).
    """
    log('formsemestre_change_formation %s' % formsemestre_id)
    sem = context.get_formsemestre(formsemestre_id)
    cnx = context.GetDBConnexion()
    # New formation:
    formation_id, modules_old2new, ues_old2new = context.formation_create_new_version(sem['formation_id'], redirect=False, REQUEST=REQUEST)
    # --- should be a transaction !
    sem['formation_id'] = formation_id
    context.do_formsemestre_edit(sem, html_quote=False)
    
    # re-associate moduleimpls to new modules:
    modimpls = context.do_moduleimpl_list( {'formsemestre_id':formsemestre_id} )
    for mod in modimpls:
        mod['module_id'] = modules_old2new[mod['module_id']]
        context.do_moduleimpl_edit(mod, formsemestre_id=formsemestre_id)
    # update decisions:
    events = scolars.scolar_events_list(cnx, args={'formsemestre_id' : formsemestre_id} )
    for e in events:
        if e['ue_id']:
            e['ue_id'] = ues_old2new[e['ue_id']]
        scolars.scolar_events_edit(cnx, e)
    validations = sco_parcours_dut.scolar_formsemestre_validation_list(
        cnx, args={'formsemestre_id': formsemestre_id} )
    for e in validations:
        if e['ue_id']:
            e['ue_id'] = ues_old2new[e['ue_id']]
        log('e=%s' % e )
        sco_parcours_dut.scolar_formsemestre_validation_edit(cnx, e)
    # transaction done.


def formsemestre_delete(context, formsemestre_id, REQUEST=None):
    """Delete a formsemestre (affiche avertissements)"""
    sem = context.get_formsemestre(formsemestre_id)
    F = context.formation_list( args={ 'formation_id' : sem['formation_id'] } )[0]
    H = [ context.html_sem_header(REQUEST, 'Suppression du semestre', sem),
          """<div class="ue_warning"><span>Attention !</span>
<p class="help">A n'utiliser qu'en cas d'erreur lors de la saisie d'une formation. Normalement,
<b>un semestre ne doit jamais être supprimé</b> (on perd la mémoire des notes et de tous les événements liés à ce semestre !).</p>

 <p class="help">Tous les modules de ce semestre seront supprimés. Ceci n'est possible que
 si :</p>
 <ol>
  <li>aucune décision de jury n'a été entrée dans ce semestre;</li>
  <li>et aucun étudiant de ce semestre ne le compense avec un autre semestre.</li>
  </ol></div>"""
          ]

    evals = context.do_evaluation_list_in_formsemestre(formsemestre_id)
    if evals:
        H.append("""<p class="warning">Attention: il y a %d évaluations dans ce semestre (sa suppression entrainera l'effacement définif des notes) !</p>""" % len(evals) ) 
        submit_label = 'Confirmer la suppression (du semestre et des %d évaluations !)' % len(evals)
    else:
        submit_label = 'Confirmer la suppression du semestre'
    tf = TrivialFormulator( REQUEST.URL0, REQUEST.form, 
                            ( ('formsemestre_id', { 'input_type' : 'hidden' }),
                              ),
                            initvalues = F,
                            submitlabel = submit_label,
                            cancelbutton = 'Annuler' )
    if tf[0] == 0:
        if formsemestre_has_decisions_or_compensations(context, formsemestre_id):
            H.append("""<p><b>Ce semestre ne peut pas être supprimé ! (il y a des décisions de jury ou des compensations par d'autres semestres)</b></p>"""  )
        else:
            H.append(tf[1])
        return '\n'.join(H) + context.sco_footer(REQUEST)
    elif tf[0] == -1: # cancel
        return REQUEST.RESPONSE.redirect( REQUEST.URL1 )
    else:
        return REQUEST.RESPONSE.redirect( 'formsemestre_delete2?formsemestre_id=' + formsemestre_id  )

def formsemestre_delete2(context, formsemestre_id, dialog_confirmed=False, REQUEST=None):
    """Delete a formsemestre (confirmation)"""
    sem = context.get_formsemestre(formsemestre_id)
    F = context.formation_list( args={ 'formation_id' : sem['formation_id'] } )[0]
    H = [ context.html_sem_header(REQUEST, 'Suppression du semestre', sem) ]
    # Confirmation dialog
    if not dialog_confirmed:
        return context.confirmDialog(
            """<h2>Vous voulez vraiment supprimer ce semestre ???</h2><p>(opération irréversible)</p>""",
            dest_url="", REQUEST=REQUEST,
            cancel_url="formsemestre_status?formsemestre_id=%s" % formsemestre_id,
            parameters={'formsemestre_id' : formsemestre_id})
    # Bon, s'il le faut...
    do_formsemestre_delete(context, formsemestre_id, REQUEST)
    return REQUEST.RESPONSE.redirect( REQUEST.URL2+'?head_message=Semestre%20supprimé' )

def formsemestre_has_decisions_or_compensations(context, formsemestre_id):
    """True if decision de jury dans ce semestre
    ou bien compensation de ce semestre par d'autre ssemestres.
    """
    r = SimpleDictFetch(
        context, 
        'SELECT v.* FROM scolar_formsemestre_validation v WHERE v.formsemestre_id = %(formsemestre_id)s OR v.compense_formsemestre_id = %(formsemestre_id)s',
        { 'formsemestre_id' : formsemestre_id } )
    return r

def do_formsemestre_delete(context, formsemestre_id, REQUEST):
    """delete formsemestre, and all its moduleimpls.
    No checks, no warnings: erase all !
    """
    cnx = context.GetDBConnexion()
    sem = context.get_formsemestre(formsemestre_id)

    # --- Destruction des modules de ce semestre
    mods = context.do_moduleimpl_list( {'formsemestre_id':formsemestre_id} )
    for mod in mods:
        # evaluations
        evals = context.do_evaluation_list( args={ 'moduleimpl_id' :  mod['moduleimpl_id']} )
        for e in evals:            
            SimpleQuery(context, "DELETE FROM notes_notes WHERE evaluation_id=%(evaluation_id)s", e)
            SimpleQuery(context, "DELETE FROM notes_notes_log WHERE evaluation_id=%(evaluation_id)s", e)
            SimpleQuery(context, "DELETE FROM notes_evaluation WHERE evaluation_id=%(evaluation_id)s", e)
        
        context.do_moduleimpl_delete(mod['moduleimpl_id'], formsemestre_id=formsemestre_id)
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
    # --- Supression des references a ce semestre dans les compensations:
    req = "UPDATE  scolar_formsemestre_validation SET compense_formsemestre_id=NULL WHERE compense_formsemestre_id=%(formsemestre_id)s"
    cursor.execute( req, { 'formsemestre_id' : formsemestre_id } )
    # --- Suppression des autorisations
    req = "DELETE FROM scolar_autorisation_inscription WHERE origin_formsemestre_id=%(formsemestre_id)s"
    cursor.execute( req, { 'formsemestre_id' : formsemestre_id } )
    # --- Suppression des item du menu custom
    req = "DELETE FROM notes_formsemestre_custommenu WHERE formsemestre_id=%(formsemestre_id)s"
    cursor.execute( req, { 'formsemestre_id' : formsemestre_id } )
    # --- Suppression des formules
    req = "DELETE FROM notes_formsemestre_ue_computation_expr WHERE formsemestre_id=%(formsemestre_id)s"
    cursor.execute( req, { 'formsemestre_id' : formsemestre_id } )
    # --- Suppression des preferences
    req = "DELETE FROM sco_prefs WHERE formsemestre_id=%(formsemestre_id)s"
    cursor.execute( req, { 'formsemestre_id' : formsemestre_id } )
    # --- Suppression des groupes et partitions
    req = "DELETE FROM group_membership  WHERE group_id IN (SELECT gm.group_id FROM group_membership gm, partition p, group_descr gd WHERE gm.group_id = gd.group_id AND gd.partition_id = p.partition_id AND p.formsemestre_id=%(formsemestre_id)s)"        
    cursor.execute( req, { 'formsemestre_id' : formsemestre_id } )
    req = "DELETE FROM group_descr WHERE group_id IN (SELECT gd.group_id FROM group_descr gd, partition p WHERE gd.partition_id = p.partition_id AND p.formsemestre_id=%(formsemestre_id)s)"
    cursor.execute( req, { 'formsemestre_id' : formsemestre_id } )
    req = "DELETE FROM partition WHERE formsemestre_id=%(formsemestre_id)s"
    cursor.execute( req, { 'formsemestre_id' : formsemestre_id } )
    # --- Destruction du semestre
    context._formsemestreEditor.delete(cnx, formsemestre_id)
    
    # news
    import sco_news
    sco_news.add(REQUEST, cnx, typ=sco_news.NEWS_SEM, object=formsemestre_id,
                 text='Suppression du semestre %(titre)s' % sem )


# ---------------------------------------------------------------------------------------
def formsemestre_edit_options(context, formsemestre_id, 
                              target_url=None,
                              REQUEST=None):
    """dialog to change formsemestre options
    (accessible par ScoImplement ou dir. etudes)
    """     
    log('formsemestre_edit_options')
    ok, err = context._check_access_diretud(formsemestre_id,REQUEST)
    if not ok:
        return err
    return context.get_preferences(formsemestre_id).edit(
        REQUEST=REQUEST,
        categories=[ 'bul' ] )

def formsemestre_change_lock(context, formsemestre_id,
                      REQUEST=None, dialog_confirmed=False):
    """change etat (verrouille si ouvert, déverrouille si fermé)
    nota: etat (1 ouvert, 0 fermé)
    """
    ok, err = context._check_access_diretud(formsemestre_id,REQUEST)
    if not ok:
        return err
    sem = context.get_formsemestre(formsemestre_id)
    etat = 1 - int(sem['etat'])

    if REQUEST and not dialog_confirmed:
        if etat:
            msg = 'déverrouillage'
        else:
            msg = 'verrouillage'
        return context.confirmDialog(
            '<h2>Confirmer le %s du semestre ?</h2>' % msg,
            helpmsg = """Les notes d'un semestre verrouillé ne peuvent plus être modifiées.
            Un semestre verrouillé peut cependant être déverrouillé facilement à tout moment
            (par son responsable ou un administrateur).
            <br/>
            Le programme d'une formation qui a un semestre verrouillé ne peut plus être modifié.
            """,
            dest_url="", REQUEST=REQUEST,
            cancel_url="formsemestre_status?formsemestre_id=%s"%formsemestre_id,
            parameters={'etat' : etat,
                        'formsemestre_id' : formsemestre_id})        
    
    if etat not in (0, 1):
        raise ScoValueError('formsemestre_lock: invalid value for etat (%s)'%etat)
    args = { 'formsemestre_id' : formsemestre_id,
             'etat' : etat }
    context.do_formsemestre_edit(args)
    if REQUEST:
        REQUEST.RESPONSE.redirect("formsemestre_status?formsemestre_id=%s"%formsemestre_id)


# ----------------------  Coefs des UE


_formsemestre_uecoef_editor = EditableTable(
    'notes_formsemestre_uecoef',
    'formsemestre_uecoef_id',
    ('formsemestre_uecoef_id', 'formsemestre_id', 'ue_id', 'coefficient')
    )

formsemestre_uecoef_create = _formsemestre_uecoef_editor.create
formsemestre_uecoef_edit   = _formsemestre_uecoef_editor.edit
formsemestre_uecoef_list   = _formsemestre_uecoef_editor.list
formsemestre_uecoef_delete = _formsemestre_uecoef_editor.delete

def formsemestre_edit_uecoefs(context, formsemestre_id, REQUEST=None):
    """Changement manuel des coefficients des UE capitalisées.
    """
    ok, err = context._check_access_diretud(formsemestre_id,REQUEST)
    if not ok:
        return err
    sem = context.get_formsemestre(formsemestre_id)
    F = context.formation_list( args={ 'formation_id' : sem['formation_id'] } )[0]
    
    footer = context.sco_footer(REQUEST)
    help = """<p class="help">
    Seuls les modules ont un coefficient. Cependant, il est nécessaire d'affecter un coefficient aux UE capitalisée pour pouvoir les prendre en compte dans la moyenne générale.
    </p>
    <p class="help">ScoDoc calcule normalement le coefficient d'une UE comme la somme des
    coefficients des modules qui la composent.
    </p>
    <p class="help">Dans certains cas, on n'a pas les mêmes modules dans le semestre antérieur
    (capitalisé) et dans le semestre courant, et le coefficient d'UE est alors variable.
    Il est alors possible de forcer la valeur du coefficient d'UE.
    </p>
    <p class="help">
    Indiquez "auto" (ou laisser vide) pour que ScoDoc calcule automatiquement le coefficient,
    ou bien entrez une valeur (nombre réel).
    </p>
    <p class="warning">Les coefficients indiqués ici ne s'appliquent que pour le traitement des UE capitalisées.
    </p>
    """
    H = [ context.html_sem_header(REQUEST,  'Coefficients des UE du semestre', sem),
          help
          ]
    #
    cnx = context.GetDBConnexion()
    nt = context._getNotesCache().get_NotesTable(context, formsemestre_id) #> get_ues
    ues = nt.get_ues()
    for ue in ues:
        ue['coef_auto'] = nt.ue_coefs[ue['ue_id']]
    initvalues = {
        'formsemestre_id' : formsemestre_id
        }
    form = [
        ('formsemestre_id', { 'input_type' : 'hidden' }),
        ]
    for ue in ues:
        coefs = formsemestre_uecoef_list(cnx, args={'formsemestre_id' : formsemestre_id, 'ue_id' : ue['ue_id']})
        if coefs:
            initvalues['ue_' + ue['ue_id']] = coefs[0]['coefficient']
        else:
            initvalues['ue_' + ue['ue_id']] = 'auto'
        form.append( ('ue_' + ue['ue_id'], { 'size': 10, 'title' : ue['acronyme'],
                                             'explanation' : 'coef. actuel = %s' % ue['coef_auto']
                                             } ) )

    
    tf = TrivialFormulator( REQUEST.URL0, REQUEST.form, form,
                            submitlabel = 'Changer les coefficients',
                            cancelbutton = 'Annuler',
                            initvalues = initvalues)
    if tf[0] == 0:
        return '\n'.join(H) + tf[1] + footer
    elif tf[0] == -1:
        return '<h4>annulation</h4>' # XXX
    else:
        # change values
        # 1- supprime les coef qui ne sont plus forcés
        # 2- modifie ou cree les coefs
        ue_deleted = []
        ue_modified=[]
        msg = []
        for ue in ues:
            val = tf[2]['ue_' + ue['ue_id']]
            coefs = formsemestre_uecoef_list(cnx, args={'formsemestre_id' : formsemestre_id, 'ue_id' : ue['ue_id']})
            if val == '' or val == 'auto':
                # supprime ce coef (il sera donc calculé automatiquement)
                if coefs:
                    ue_deleted.append(ue)
            else:
                try:
                    val = float(val)
                    if (not coefs) or (coefs[0]['coefficient'] != val):
                        ue['coef'] = val
                        ue_modified.append(ue)
                except:
                    ok = False
                    msg.append( "valeur invalide (%s) pour le coefficient de l'UE %s"
                                % (val, ue['acronyme']) )

        if not ok:
            return '\n'.join(H) + '<p><ul><li>%s</li></ul></p>'% '</li><li>'.join(msg) + tf[1] + footer

        # apply modifications
        for ue in ue_modified:
            coefs = formsemestre_uecoef_list(cnx, args={'formsemestre_id' : formsemestre_id, 'ue_id' : ue['ue_id']})
            # modifie ou cree le coef
            if coefs:
                formsemestre_uecoef_edit(cnx, args={'formsemestre_uecoef_id' : coefs[0]['formsemestre_uecoef_id'],
                                                    'coefficient' : ue['coef']})
            else:
                formsemestre_uecoef_create(cnx, args={'formsemestre_id' : formsemestre_id, 'ue_id' : ue['ue_id'],
                                                      'coefficient' : ue['coef']})
        for ue in ue_deleted:
            coefs = formsemestre_uecoef_list(cnx, args={'formsemestre_id' : formsemestre_id, 'ue_id' : ue['ue_id']})
            if coefs:
                formsemestre_uecoef_delete(cnx, coefs[0]['formsemestre_uecoef_id'])

        if ue_modified or ue_deleted:
            z = [ """<h3>Modification effectuées</h3>""" ]
            if ue_modified:
                z.append("""<h4>Coefs modifiés dans les UE:<h4><ul>""")
                for ue in ue_modified:
                    z.append('<li>%(acronyme)s : %(coef)s</li>' % ue )
                z.append('</ul>')
            if ue_deleted:
                z.append("""<h4>Coefs supprimés dans les UE:<h4><ul>""")
                for ue in ue_deleted:
                    z.append('<li>%(acronyme)s</li>' % ue )
                z.append('</ul>')
        else:
            z = [ """<h3>Aucune modification</h3>""" ]
        context._inval_cache(formsemestre_id=formsemestre_id) #> modif coef UE cap (modifs notes de _certains_ etudiants)
        
        header = context.html_sem_header(REQUEST,  'Coefficients des UE du semestre', sem)
        return header + '\n'.join(z) + """<p><a href="formsemestre_status?formsemestre_id=%s">Revenir au tableau de bord</a></p>""" % formsemestre_id + footer
        
    
