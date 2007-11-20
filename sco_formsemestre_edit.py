# -*- mode: python -*-
# -*- coding: iso8859-15 -*-

##############################################################################
#
# Gestion scolarite IUT
#
# Copyright (c) 2001 - 2007 Emmanuel Viennet.  All rights reserved.
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
from notes_log import log
from TrivialFormulator import TrivialFormulator, TF
import sco_portal_apogee

def do_formsemestre_createwithmodules(context, REQUEST, userlist, edit=False ):
    "Form choix modules / responsables et creation formsemestre"
    formation_id = REQUEST.form['formation_id']
    F = context.do_formation_list( args={ 'formation_id' : formation_id } )[0]
    if not edit:
        initvalues = {
            'nomgroupetd' : 'TD',
            'nomgroupetp' : 'TP',
            'nomgroupeta' : 'langues'
            }
        semestre_id  = REQUEST.form['semestre_id']
    else:
        # setup form init values
        formsemestre_id = REQUEST.form['formsemestre_id']
        initvalues = context.get_formsemestre(formsemestre_id)
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
            initvalues[str(x['module_id'])] = x['responsable_id']        
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
        ('date_debut', { 'title' : 'Date de début (j/m/a)',
                         'size' : 9, 'allow_null' : False }),
        ('date_fin', { 'title' : 'Date de fin (j/m/a)',
                         'size' : 9, 'allow_null' : False }),
        ('responsable_id', { 'input_type' : 'menu',
                             'title' : 'Directeur des études',
                             'allowed_values' : userlist }),        
        ('titre', { 'size' : 20, 'title' : 'Nom de ce semestre' }),
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
            'allowed_values' : [ e[0] for e in etapes ],
            'labels' :  [ '%s (%s)' % (e[1], e[0]) for e in etapes ],
            }))
    else:
        # fallback: code etape libre
        modform.append(
        ('etape_apo', { 'size' : 12,
                        'title' : 'Code étape Apogée',
                        'explanation' : 'facultatif, nécessaire pour synchroniser les listes et exporter les décisions' })
        )
    if edit:
        formtit = "<h3>Sélectionner les modules, leurs responsables et les étudiants à inscrire:</h3>"
    else:
        formtit = """<h3>Sélectionner les modules et leurs responsables</h3><p class="help">Si vous avez des parcours (options), ne sélectionnez que les modules du tronc commun.</p>"""

    modform += [
        ('gestion_absence_lst', { 'input_type' : 'checkbox',
                                  'title' : 'Suivi des absences',
                                  'allowed_values' : ['X'],
                                  'explanation' : 'indiquer les absences sur les bulletins',
                                  'labels' : [''] }),
        ('bul_show_decision_lst', { 'input_type' : 'checkbox',
                                  'title' : 'Décisions',
                                  'allowed_values' : ['X'],
                                  'explanation' : 'faire figurer les décisions sur les bulletins',
                                   'labels' : [''] }),
        ('bul_show_codemodules_lst',  { 'input_type' : 'checkbox',
                                  'title' : '',
                                  'allowed_values' : ['X'],
                                  'explanation' : 'afficher codes des modules sur les bulletins',
                                   'labels' : [''] }),

        ('gestion_compensation_lst',  { 'input_type' : 'checkbox',
                                        'title' : '',
                                        'allowed_values' : ['X'],
                                        'explanation' : 'proposer compensations de semestres (parcours DUT)',
                                        'labels' : [''] }),

        ('gestion_semestrielle_lst',  { 'input_type' : 'checkbox',
                                        'title' : '',
                                        'allowed_values' : ['X'],
                                        'explanation' : 'formation semestrialisée (jurys avec semestres décalés)',
                                        'labels' : [''] }),
        ('nomgroupetd', { 'size' : 20,
                          'title' : 'Nom des groupes primaires',
                          'explanation' : 'TD' }),
        ('nomgroupetp', { 'size' : 20,
                          'title' : 'Nom des groupes secondaires',
                          'explanation' : 'TP' }),
        ('nomgroupeta', { 'size' : 20,
                          'title' : 'Nom des groupes tertiaires',
                          'explanation' : 'langues' }),

        ('bul_bgcolor', { 'size' : 8,
                          'title' : 'Couleur fond des bulletins',
                          'explanation' : 'version web seulement (ex: #ffeeee)' }),

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
                    fcg = '<select name="%s!groupe"><option value="%s!*!*!*">Tous</option><option value="%s!-!-!-">Aucun</option>' % (mod['module_id'],mod['module_id'],mod['module_id'])  + context.formChoixGroupe(formsemestre_id) + '</select>'
                    itemtemplate = """<tr><td class="tf-fieldlabel">%(label)s</td><td class="tf-field">%(elem)s</td><td>""" + fcg + '</td></tr>'
                else:
                    itemtemplate = """<tr><td class="tf-fieldlabel">%(label)s</td><td class="tf-field">%(elem)s</td></tr>"""
                modform.append( (str(mod['module_id']),
                                 { 'input_type' : 'menu',
                                   'withcheckbox' : True,
                                   'title' : '%s %s' % (mod['code'],mod['titre']),
                                   'allowed_values' : userlist,
                                   'template' : itemtemplate }) )
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
    initvalues['gestion_absence'] = initvalues.get('gestion_absence','1')
    if initvalues['gestion_absence'] == '1':
        initvalues['gestion_absence_lst'] = ['X']
    else:
        initvalues['gestion_absence_lst'] = []
    if REQUEST.form.get('tf-submitted',False) and not REQUEST.form.has_key('gestion_absence_lst'):
        REQUEST.form['gestion_absence_lst'] = []

    initvalues['bul_show_decision'] = initvalues.get('bul_show_decision','1')
    if initvalues['bul_show_decision'] == '1':
        initvalues['bul_show_decision_lst'] = ['X']
    else:
        initvalues['bul_show_decision_lst'] = []
    if REQUEST.form.get('tf-submitted',False) and not REQUEST.form.has_key('bul_show_decision_lst'):
        REQUEST.form['bul_show_decision_lst'] = []

    initvalues['bul_show_codemodules'] = initvalues.get('bul_show_codemodules','1')
    if initvalues['bul_show_codemodules'] == '1':
        initvalues['bul_show_codemodules_lst'] = ['X']
    else:
        initvalues['bul_show_codemodules_lst'] = []
    if REQUEST.form.get('tf-submitted',False) and not REQUEST.form.has_key('bul_show_codemodules_lst'):
        REQUEST.form['bul_show_codemodules_lst'] = []

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

    #
    tf = TrivialFormulator( REQUEST.URL0, REQUEST.form, modform,
                            submitlabel = submitlabel,
                            cancelbutton = 'Annuler',
                            initvalues = initvalues)
    if tf[0] == 0:
        return '<p>Formation %(titre)s (%(acronyme)s), version %(version)d, code %(formation_code)s</p>' % F + tf[1] # + '<p>' + str(initvalues)
    elif tf[0] == -1:
        return '<h4>annulation</h4>'
    else:
        if tf[2]['gestion_absence_lst']:
            tf[2]['gestion_absence'] = 1
        else:
            tf[2]['gestion_absence'] = 0
        if tf[2]['bul_show_decision_lst']:
            tf[2]['bul_show_decision'] = 1
        else:
            tf[2]['bul_show_decision'] = 0
        if tf[2]['bul_show_codemodules_lst']:
            tf[2]['bul_show_codemodules'] = 1
        else:
            tf[2]['bul_show_codemodules'] = 0
        if tf[2]['gestion_compensation_lst']:
            tf[2]['gestion_compensation'] = 1
        else:
            tf[2]['gestion_compensation'] = 0
        if tf[2]['gestion_semestrielle_lst']:
            tf[2]['gestion_semestrielle'] = 1
        else:
            tf[2]['gestion_semestrielle'] = 0
        if not edit:
            # creation du semestre                
            formsemestre_id = context.do_formsemestre_create(tf[2], REQUEST)
            # creation des modules
            for module_id in tf[2]['tf-checked']:
                mod_resp_id = tf[2][module_id]
                modargs = { 'module_id' : module_id,
                            'formsemestre_id' : formsemestre_id,
                            'responsable_id' :  mod_resp_id,
                            }
                mid = context.do_moduleimpl_create(modargs)
            return '<p>ok, session créée<p/><p><a class="stdlink" href="%s">Continuer</a>'%REQUEST.URL2
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
                log('inscription module: %s = "%s"' % ('%s!groupe'%module_id,tf[2]['%s!groupe'%module_id]))
                groupetd,groupetp,groupeta = tf[2]['%s!groupe'%module_id].split('!')[1:]
                args = { 'formsemestre_id' : formsemestre_id,
                         'etat' : 'I' }
                if groupetd and groupetd != '*':
                    args['groupetd'] = groupetd
                if groupeta and groupeta != '*':
                    args['groupeanglais'] = groupeta
                if groupetp and groupetp != '*':
                    args['groupetp'] = groupetp
                ins = context.Notes.do_formsemestre_inscription_list( args=args )
                etudids = [ x['etudid'] for x in ins ]
                log('inscription module:module_id=%s,moduleimpl_id=%s: %s' % (module_id,moduleimpl_id,etudids) )
                context.do_moduleimpl_inscrit_etuds(moduleimpl_id,formsemestre_id, etudids,
                                                    REQUEST=REQUEST)
                msg += [ 'inscription de %d étudiants au module %s' % (len(etudids),mod['code'])]
#                if tf[2]['inscrire_etudslist']:
#                    # il faut inscrire les etudiants du semestre
#                    # dans le nouveau module
#                    context.do_moduleimpl_inscrit_tout_semestre(
#                        moduleimpl_id,formsemestre_id)
#                    msg += ['étudiants inscrits à %s (module %s)</p>'
#                            % (moduleimpl_id, mod['code']) ]
            #
            for module_id in mods_todelete:
                # get id
                moduleimpl_id = context.do_moduleimpl_list(
                    { 'formsemestre_id' : formsemestre_id,
                      'module_id' : module_id } )[0]['moduleimpl_id']
                mod = context.do_module_list( { 'module_id' : module_id } )[0]
                # Evaluations dans ce module ?
                evals = context.do_evaluation_list(
                    { 'moduleimpl_id' : moduleimpl_id} )
                if evals:
                    msg += [ '<b>impossible de supprimer %s (%s) car il y a %d évaluations définies (supprimer les d\'abord)</b>' % (mod['code'], mod['titre'], len(evals)) ]
                else:
                    msg += [ 'suppression de %s (%s)'
                             % (mod['code'], mod['titre']) ]
                    context.do_moduleimpl_delete(moduleimpl_id)
            for module_id in mods_toedit:
                moduleimpl_id = context.do_moduleimpl_list(
                    { 'formsemestre_id' : formsemestre_id,
                      'module_id' : module_id } )[0]['moduleimpl_id']
                modargs = {
                    'moduleimpl_id' : moduleimpl_id,
                    'module_id' : module_id,
                    'formsemestre_id' : formsemestre_id,
                    'responsable_id' :  tf[2][module_id] }
                context.do_moduleimpl_edit(modargs)
                mod = context.do_module_list( { 'module_id' : module_id } )[0]
                #msg += [ 'modification de %s (%s)' % (mod['code'], mod['titre']) ]
            if msg:
                msg = '<ul><li>' + '</li><li>'.join(msg) + '</li></ul>'
            else:
                msg = ''
            return '<p>Modification effectuée</p>'  + msg # + str(tf[2])



# ---------------------------------------------------------------------------------------


def formsemestre_edit_options(context, formsemestre_id, REQUEST=None):
    """dialog to change formsemestre options
    (accessible par ScoImplement ou dir. etudes)
    """        
    ok, err = context._check_access_diretud(formsemestre_id,REQUEST)
    if not ok:
        return err
    sem = context.get_formsemestre(formsemestre_id)
    F = context.do_formation_list( args={ 'formation_id' : sem['formation_id'] } )[0]
    header = context.sco_header(page_title='Modification d\'un semestre',
                             REQUEST=REQUEST)
    footer = context.sco_footer(REQUEST)
    H = [ header,
          context.formsemestre_status_head(context, REQUEST=REQUEST,
                                        formsemestre_id=formsemestre_id )
          ]
    H.append("""<h2>Modification du semestre
         <a href="formsemestre_status?formsemestre_id=%s">%s</a>
         (formation %s)</h2>
         """ % (formsemestre_id, sem['titre_num'], F['acronyme']) )        
    modform = [
        ('formsemestre_id', { 'input_type' : 'hidden' }),
        ('gestion_absence_lst', { 'input_type' : 'checkbox',
                                  'title' : 'Suivi des absences',
                                  'allowed_values' : ['X'],
                                  'explanation' : 'indiquer les absences sur les bulletins',
                                   'labels' : [''] }),
        ('bul_show_decision_lst', { 'input_type' : 'checkbox',
                                  'title' : 'Décisions',
                                  'allowed_values' : ['X'],
                                  'explanation' : 'faire figurer les décisions sur les bulletins',
                                   'labels' : [''] }),
        ('bul_show_codemodules_lst',  { 'input_type' : 'checkbox',
                                  'title' : '',
                                  'allowed_values' : ['X'],
                                  'explanation' : 'afficher codes des modules sur les bulletins',
                                   'labels' : [''] }),
        ('bul_show_uevalid_lst', { 'input_type' : 'checkbox',
                               'title' : '',
                               'allowed_values' : ['X'],
                               'explanation' : 'faire figurer les UE validées sur les bulletins',
                               'labels' : [''] }),
        ('etat_lst', { 'input_type' : 'checkbox',
                       'title' : '',
                       'allowed_values' : ['X'],
                       'explanation' : 'semestre "ouvert" (non verrouillé)',
                       'labels' : [''] }),
        ('bul_publish_xml_lst', { 'input_type' : 'checkbox',
                                  'title' : 'Accès portail étudiants',
                                  'allowed_values' : ['X'],
                                  'explanation' : 'publier le bulletin sur le portail',
                                  'labels' : [''] }),
        ]
    initvalues = sem
    initvalues['gestion_absence'] = initvalues.get('gestion_absence','1')
    if initvalues['gestion_absence'] == '1':
        initvalues['gestion_absence_lst'] = ['X']
    else:
        initvalues['gestion_absence_lst'] = []
    if REQUEST.form.get('tf-submitted',False) and not REQUEST.form.has_key('gestion_absence_lst'):
        REQUEST.form['gestion_absence_lst'] = []

    initvalues['bul_show_decision'] = initvalues.get('bul_show_decision','1')
    if initvalues['bul_show_decision'] == '1':
        initvalues['bul_show_decision_lst'] = ['X']
    else:
        initvalues['bul_show_decision_lst'] = []
    if REQUEST.form.get('tf-submitted',False) and not REQUEST.form.has_key('bul_show_decision_lst'):
        REQUEST.form['bul_show_decision_lst'] = []

    initvalues['bul_show_uevalid'] = initvalues.get('bul_show_uevalid','1')
    if initvalues['bul_show_uevalid'] == '1':
        initvalues['bul_show_uevalid_lst'] = ['X']
    else:
        initvalues['bul_show_uevalid_lst'] = []
    if REQUEST.form.get('tf-submitted',False) and not REQUEST.form.has_key('bul_show_uevalid_lst'):
        REQUEST.form['bul_show_uevalid_lst'] = []

    initvalues['bul_show_codemodules'] = initvalues.get('bul_show_codemodules','1')
    if initvalues['bul_show_codemodules'] == '1':
        initvalues['bul_show_codemodules_lst'] = ['X']
    else:
        initvalues['bul_show_codemodules_lst'] = []
    if REQUEST.form.get('tf-submitted',False) and not REQUEST.form.has_key('bul_show_codemodules_lst'):
        REQUEST.form['bul_show_codemodules_lst'] = []

    initvalues['etat'] = initvalues.get('etat','1')
    if initvalues['etat'] == '1':
        initvalues['etat_lst'] = ['X']
    else:
        initvalues['etat_lst'] = []
    if REQUEST.form.get('tf-submitted',False) and not REQUEST.form.has_key('etat_lst'):
        REQUEST.form['etat_lst'] = []

    initvalues['bul_hide_xml'] = initvalues.get('bul_hide_xml','1')
    if initvalues['bul_hide_xml'] == '0':
        initvalues['bul_publish_xml_lst'] = ['X']
    else:
        initvalues['bul_publish_xml_lst'] = []
    if REQUEST.form.get('tf-submitted',False) and not REQUEST.form.has_key('bul_publish_xml_lst'):
        REQUEST.form['bul_publish_xml_lst'] = []


    tf = TrivialFormulator( REQUEST.URL0, REQUEST.form, modform,
                            submitlabel = 'Modifier',
                            cancelbutton = 'Annuler',
                            initvalues = initvalues)
    if tf[0] == 0:
        return '\n'.join(H) + tf[1] + '<p><a class="stdlink" href="formsemestre_pagebulletin_dialog?formsemestre_id=%s">Réglage de la mise en page et envoi mail des bulletins</a>' % formsemestre_id + footer
    elif tf[0] == -1:
        return header + '<h4>annulation</h4>' + footer
    else:
        if tf[2]['gestion_absence_lst']:
            tf[2]['gestion_absence'] = 1
        else:
            tf[2]['gestion_absence'] = 0

        if tf[2]['bul_show_decision_lst']:
            tf[2]['bul_show_decision'] = 1
        else:
            tf[2]['bul_show_decision'] = 0

        if tf[2]['bul_show_uevalid_lst']:
            tf[2]['bul_show_uevalid'] = 1
        else:
            tf[2]['bul_show_uevalid'] = 0

        if tf[2]['bul_show_codemodules_lst']:
            tf[2]['bul_show_codemodules'] = 1
        else:
            tf[2]['bul_show_codemodules'] = 0

        if tf[2]['etat_lst']:
            tf[2]['etat'] = 1
        else:
            tf[2]['etat'] = 0                

        if tf[2]['bul_publish_xml_lst']:
            tf[2]['bul_hide_xml'] = 0
        else:
            tf[2]['bul_hide_xml'] = 1 

        # modification du semestre:
        context.do_formsemestre_edit(tf[2])
        return header + ('<h3>Modifications effectuées<h3><p><a class="stdlink" href="formsemestre_status?formsemestre_id=%s">retour au tableau de bord du semestre</a>' % formsemestre_id)  + footer



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
                '<p>Confirmer le %s du semestre ?</p>' % msg,
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
    

