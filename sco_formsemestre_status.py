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

"""Tableau de bord semestre
"""

# XXX migration code en cours: etait en DTML

from notesdb import *
from notes_log import log
from sco_utils import *
from sco_formsemestre_custommenu import formsemestre_custommenu_html
from gen_tables import GenTable
import sco_archives

def makeMenu( title, items, cssclass='custommenu', elem='span', base_url='' ):
    """HTML snippet to render a simple drop down menu.
    items is a list of dicts:
    { 'title' :
      'url' :
      'enabled' : # True by default
      'helpmsg' :
    }
    """
    H = [ """<%s class="barrenav"><ul class="nav">
    <li onmouseover="MenuDisplay(this)" onmouseout="MenuHide(this)"><a href="#" class="menu %s">%s</a><ul>""" % (elem, cssclass, title)
          ]
    for item in items:
        if item.get('enabled', True):
            if base_url:
                item['urlq'] = urllib.quote(item['url'])
            else:
                item['urlq'] = item['url']
            H.append('<li><a href="' + base_url + '%(urlq)s">%(title)s</a></li>' % item)
        else:
            H.append('<li><span class="disabled_menu_item">%(title)s</span></li>' % item)
    H.append('</ul></li></ul></%s>' % elem)
    return ''.join(H)


def defMenuStats(context,formsemestre_id):
    "Définition du menu 'Statistiques' "
    return [
        { 'title' : 'Statistiques...',
          'url' : 'formsemestre_report_counts?formsemestre_id=' + formsemestre_id,
          },
        { 'title' : 'Suivi de cohortes',
          'url' : 'formsemestre_suivi_cohorte?formsemestre_id=' + formsemestre_id,
          'enabled' : True,
          },
        { 'title' : 'Graphe des parcours',
          'url' : 'formsemestre_graph_parcours?formsemestre_id=' + formsemestre_id,
          'enabled' : WITH_PYDOT,
          },
        { 'title' : 'Codes des parcours',
          'url' : 'formsemestre_suivi_parcours?formsemestre_id=' + formsemestre_id,
          'enabled' : True,
          }
        ]


def formsemestre_status_menubar(context, sem, REQUEST):
    """HTML to render menubar"""
    authuser = REQUEST.AUTHENTICATED_USER
    uid = str(authuser)
    formsemestre_id = sem['formsemestre_id']
    if int(sem['etat']):
        change_lock_msg = 'Verrouiller'
    else:
        change_lock_msg = 'Déverrouiller'

    F = context.do_formation_list( args={ 'formation_id' : sem['formation_id'] } )[0]

    menuSemestre = [
        { 'title' : 'Tableau de bord',
          'url' : 'formsemestre_status?formsemestre_id=%(formsemestre_id)s' % sem,
          'enabled' : True,
          'helpmsg' : 'Tableau de bord du semestre'
          },
        { 'title' : 'Voir la formation %(acronyme)s' % F,
          'url' : 'ue_list?formation_id=%(formation_id)s' % sem,
          'enabled' : True,
          'helpmsg' : 'Tableau de bord du semestre'
          },
        { 'title' : 'Modifier le semestre',
          'url' : 'formsemestre_editwithmodules?formation_id=%(formation_id)s&formsemestre_id=%(formsemestre_id)s' % sem,
          'enabled' : (authuser.has_permission(ScoImplement, context) or (sem['responsable_id'] == str(REQUEST.AUTHENTICATED_USER) and sem['resp_can_edit'])) and (sem['etat'] == '1'),
          'helpmsg' : 'Modifie le contenu du semestre (modules)'
          },
        { 'title' : 'Préférences du semestre',
          'url' : 'formsemestre_edit_preferences?formsemestre_id=%(formsemestre_id)s' % sem,
          'enabled' : (authuser.has_permission(ScoImplement, context) or (sem['responsable_id'] == str(REQUEST.AUTHENTICATED_USER) and sem['resp_can_edit'])) and (sem['etat'] == '1'),
          'helpmsg' : 'Préférences du semestre'
          },
        { 'title' : 'Réglages bulletins',
          'url' :  'formsemestre_edit_options?formsemestre_id=' + formsemestre_id,
          'enabled' : (uid == sem['responsable_id']) or authuser.has_permission(ScoImplement, context),
          'helpmsg' : 'Change les options'
          },
        { 'title' : change_lock_msg,
          'url' :  'formsemestre_change_lock?formsemestre_id=' + formsemestre_id,
          'enabled' : (uid == sem['responsable_id']) or authuser.has_permission(ScoImplement, context),
          'helpmsg' : ''
          },
        { 'title' : 'Description du semestre',
          'url' :  'formsemestre_description?formsemestre_id=' + formsemestre_id,
          'enabled' : True,
          'helpmsg' : ''
          },
        { 'title' : 'Vérifier absences aux évaluations',
          'url' :  'formsemestre_check_absences_html?formsemestre_id=' + formsemestre_id,
          'enabled' : True,
          'helpmsg' : ''
          },
        { 'title' : 'Lister tous les enseignants',
          'url' :  'formsemestre_enseignants_list?formsemestre_id=' + formsemestre_id,
          'enabled' : True,
          'helpmsg' : ''
          },
        { 'title' : 'Cloner ce semestre',
          'url' :  'formsemestre_clone?formsemestre_id=' + formsemestre_id,
          'enabled' : authuser.has_permission(ScoImplement, context),
          'helpmsg' : ''
          },
        { 'title' : 'Associer à une nouvelle version du programme',
          'url' :  'formsemestre_associate_new_version?formsemestre_id=' + formsemestre_id,
          'enabled' : authuser.has_permission(ScoChangeFormation, context) and (sem['etat']== '1'),
          'helpmsg' : ''
          },
        ]
    # debug :
    if uid == 'root' or uid[:7] == 'viennet':
        menuSemestre.append( { 'title' : 'Check integrity',
                               'url' : 'check_sem_integrity?formsemestre_id=' + formsemestre_id,
                               'enabled' : True })

    menuInscriptions = [
        { 'title' : 'Listes des étudiants',
          'url' : 'formsemestre_lists?formsemestre_id=' + formsemestre_id,
          'enabled' : True,
          'helpmsg' : 'Accès aux listes des groues d\'étudiants'
          },
        { 'title' : 'Voir les inscriptions aux modules',
          'url' : 'moduleimpl_inscriptions_stats?formsemestre_id=' + formsemestre_id,
          },
        { 'title' : 'Modifier les groupes de ' + sem['nomgroupetd'],
          'url' : 'affectGroupes?formsemestre_id=%s&groupType=TD&groupTypeName=%s'% (formsemestre_id,sem['nomgroupetd']),
          'enabled' : context.can_change_groups(REQUEST, formsemestre_id)
          },
        { 'title' : 'Modifier les groupes de ' + sem['nomgroupeta'],
          'url' : 'affectGroupes?formsemestre_id=%s&groupType=TA&groupTypeName=%s'% (formsemestre_id,sem['nomgroupeta']),
          'enabled' : context.can_change_groups(REQUEST, formsemestre_id)
          },
        { 'title' : 'Modifier les groupes de ' + sem['nomgroupetp'],
          'url' : 'affectGroupes?formsemestre_id=%s&groupType=TP&groupTypeName=%s'% (formsemestre_id,sem['nomgroupetp']),
          'enabled' : context.can_change_groups(REQUEST, formsemestre_id)
          },        
        { 'title' : 'Passage des étudiants depuis d\'autres semestres',
          'url' : 'formsemestre_inscr_passage?formsemestre_id=' + formsemestre_id,
          'enabled' : authuser.has_permission(ScoEtudInscrit, context)
          },
        { 'title' : 'Synchroniser avec étape Apogée',
          'url' : 'formsemestre_synchro_etuds?formsemestre_id=' + formsemestre_id,
          'enabled' : authuser.has_permission(ScoEtudInscrit, context)
          },
        { 'title' : 'Inscrire un étudiant',
          'url' : 'formsemestre_inscription_with_modules_etud?formsemestre_id=' + formsemestre_id,
          'enabled' : authuser.has_permission(ScoEtudInscrit, context)
          },
        { 'title' : 'Importer des étudiants dans ce semestre (table Excel)',
          'url' : 'form_students_import_excel?formsemestre_id=' + formsemestre_id,
          'enabled' : authuser.has_permission(ScoEtudInscrit, context)
          },
        { 'title' : 'Importer données admission',
          'url' : 'form_students_import_infos_admissions?formsemestre_id=' + formsemestre_id,
          'enabled' : authuser.has_permission(ScoEtudInscrit, context)
          },
        { 'title' : 'Resynchroniser données admission', # TEMPORAIRE POUR MIGRER IUTV
          'url' : 'formsemestre_import_etud_admission?formsemestre_id=' + formsemestre_id,
          'enabled' : authuser.has_permission(ScoEtudInscrit, context) and (str(authuser) == 'viennetadm' or str(authuser) == 'admin'),
          },

        { 'title' : 'Exporter table des étudiants',
          'url' : 'listegroupe?format=allxls&formsemestre_id='+ formsemestre_id,
          },
        { 'title' : 'Vérifier inscriptions multiples',
          'url' : 'formsemestre_inscrits_ailleurs?formsemestre_id=' + formsemestre_id,
          }
        ]

    menuNotes = [
        { 'title' : 'Tableau des moyennes (et liens bulletins)',
          'url' : 'formsemestre_recapcomplet?formsemestre_id=' + formsemestre_id,
          },
        { 'title' : 'Saisie des notes',
          'url' : 'formsemestre_status?formsemestre_id=%(formsemestre_id)s' % sem,
          'enabled' : True,
          'helpmsg' : 'Tableau de bord du semestre'
          },
        { 'title' : 'Classeur PDF des bulletins',
          'url' : 'formsemestre_bulletins_pdf_choice?formsemestre_id='+ formsemestre_id,
          'helpmsg' : 'PDF regroupant tous les bulletins'
          },
        { 'title' : 'Envoyer à chaque étudiant son bulletin par e-mail',
          'url' : 'formsemestre_bulletins_mailetuds_choice?formsemestre_id='+ formsemestre_id,
          },
        ]
    menuJury = [
        { 'title' : 'Voir les décisions du jury',
          'url' : 'formsemestre_pvjury?formsemestre_id=' + formsemestre_id,
          },
        { 'title' : 'Générer feuille préparation Jury',
          'url' : 'feuille_preparation_jury?formsemestre_id=' + formsemestre_id,
          },
        { 'title' : 'Saisie des décisions du jury',
          'url' : 'formsemestre_recapcomplet?modejury=1&hidemodules=1&formsemestre_id=' + formsemestre_id,
          'enabled' : context.can_validate_sem(REQUEST, formsemestre_id)
          },
        { 'title' : 'Editer les PV et archiver les résultats',
          'url' : 'formsemestre_archive?formsemestre_id=' + formsemestre_id,
          'enabled' : context.can_validate_sem(REQUEST, formsemestre_id)
          },
        { 'title' : 'Documents archivés',
          'url' : 'formsemestre_list_archives?formsemestre_id=' + formsemestre_id,
          'enabled' : sco_archives.Archive.list_formsemestre_archives(context,formsemestre_id)
          },
        ]
    
    menuStats = defMenuStats(context,formsemestre_id)
    base_url=context.absolute_url() + '/' # context must be Notes
    H = [
        '<div class="formsemestre_menubar"><table><tr>', 
        '<td>', makeMenu( 'Semestre', menuSemestre, base_url=base_url ), '</td>',
        '<td>', makeMenu( 'Inscriptions', menuInscriptions, base_url=base_url ), '</td>',
        '<td>',  makeMenu( 'Notes', menuNotes, base_url=base_url ), '</td>',
        '<td>', makeMenu( 'Jury', menuJury, base_url=base_url ), '</td>',
        '<td>', makeMenu( 'Statistiques', menuStats, base_url=base_url ), '</td>',
        '<td>', formsemestre_custommenu_html(context, formsemestre_id, base_url=base_url), '</td></tr></table></div>',
          ]
    return '\n'.join(H)


# Element HTML decrivant un semestre (barre de menu et infos)
def formsemestre_page_title(context, REQUEST):
    """Element HTML decrivant un semestre (barre de menu et infos)
    Cherche dans REQUEST si un semestre esi défini (formsemestre_id ou moduleimpl ou evaluation)
    """
    try:
        notes = context.Notes
    except:
        notes = context
    # Search formsemestre
    if REQUEST.form.has_key('formsemestre_id'):
        formsemestre_id = REQUEST.form['formsemestre_id']
    elif REQUEST.form.has_key('moduleimpl_id'):
        modimpl = notes.do_moduleimpl_list({'moduleimpl_id' : REQUEST.form['moduleimpl_id']})
        if not modimpl:
            return '' # suppressed ?
        modimpl = modimpl[0]
        formsemestre_id = modimpl['formsemestre_id']
    elif REQUEST.form.has_key('evaluation_id'):
        E = notes.do_evaluation_list({'evaluation_id' : REQUEST.form['evaluation_id']})
        if not E:
            return '' # evaluation suppressed ?
        E = E[0]
        modimpl = notes.do_moduleimpl_list({'moduleimpl_id' : E['moduleimpl_id']})[0]
        formsemestre_id = modimpl['formsemestre_id']
    elif REQUEST.form.has_key('semestregroupe'):
        formsemestre_id = REQUEST.form['semestregroupe'].split('!')[0]
    else:
        return '' # no current formsemestre
    #
    if not formsemestre_id:
        return ''
    try:
        sem = context.Notes.get_formsemestre(formsemestre_id).copy()    
    except:
        log("can't find formsemestre_id %s" % formsemestre_id)
        return ''
    sem['notes'] = notes.absolute_url()
    if sem['etat'] != '1':
        sem['locklink'] = """<a href="%s/formsemestre_change_lock?formsemestre_id=%s">%s</a>""" % (sem['notes'], sem['formsemestre_id'], context.icons.lock_img.tag(border='0',title='Semestre verrouillé'))
    else:
        sem['locklink'] = ''
    if sem['semestre_id'] != -1:
        sem['num_sem'] = ', semestre %s' % sem['semestre_id']
    else:
        sem['num_sem'] = '' # formation sans semestres
    if sem['modalite']:
        sem['modalitestr'] = ' en %s' % sem['modalite']
    else:
        sem['modalitestr'] = ''
    if sem['etape_apo']:
        sem['etape_apo_str'] = 'Code étape Apogée: %s' % sem['etape_apo']
    else:
        sem['etape_apo_str'] = 'Pas de code étape'
    inscrits = notes.do_formsemestre_inscription_list( args={ 'formsemestre_id' : formsemestre_id } )
    sem['nbinscrits'] = len(inscrits)
    u = context.Users.user_info(sem['responsable_id'],REQUEST)
    sem['resp'] = u['prenomnom']
    sem['nomcomplet'] = u['nomcomplet']
    H = [ 
        """<div class="formsemestre_page_title">""", 
        
        """<div class="infos">
<span class="semtitle"><a class="stdlink" href="%(notes)s/formsemestre_status?formsemestre_id=%(formsemestre_id)s">%(titre)s</a><a title="%(etape_apo_str)s">%(num_sem)s</a>%(modalitestr)s</span><span class="dates"><a title="du %(date_debut)s au %(date_fin)s ">%(mois_debut)s - %(mois_fin)s</a></span><span class="resp"><a title="%(nomcomplet)s">%(resp)s</a></span><span class="nbinscrits"><a class="discretelink" href="%(notes)s/formsemestre_lists?formsemestre_id=%(formsemestre_id)s">%(nbinscrits)d inscrits</a></span><span class="lock">%(locklink)s</span></div>""" % sem,

        formsemestre_status_menubar(notes, sem, REQUEST),

        """</div>"""
          ]
    return '\n'.join(H)

# Description du semestre sous forme de table exportable
def formsemestre_description_table(context, formsemestre_id, REQUEST):
    """Description du semestre sous forme de table exportable
    Liste des modules et de leurs coefficients
    """
    sem = context.get_formsemestre(formsemestre_id)
    F = context.do_formation_list( args={ 'formation_id' : sem['formation_id'] } )[0]
    inscrits = context.do_formsemestre_inscription_list( args={ 'formsemestre_id' : formsemestre_id } )
    Mlist = context.do_moduleimpl_withmodule_list( args={ 'formsemestre_id' : formsemestre_id } )
    
    R = []
    for M in Mlist:
        ModInscrits = context.do_moduleimpl_inscription_list( args={ 'moduleimpl_id' : M['moduleimpl_id'] })
        l = { 'UE' : M['ue']['acronyme'],
              'Code' : M['module']['code'],
              'Module' : M['module']['abbrev'] or M['module']['titre'],
              'Inscrits' : len(ModInscrits),
              'Responsable' : context.Users.user_info(M['responsable_id'],REQUEST)['nomprenom'],
              'Coef.' : M['module']['coefficient']
              }
        R.append(l)
    
    columns_ids = [ 'UE', 'Code', 'Module', 'Coef.', 'Inscrits', 'Responsable' ]
    titles = columns_ids
    titles = {}
    # on veut { id : id }, peu elegant en python 2.3:
    map( lambda x,titles=titles: titles.__setitem__(x[0],x[1]), zip(columns_ids,columns_ids) )
    
    title = 'Semestre %s' % (sem['titremois'])
    
    return GenTable(
        columns_ids=columns_ids, rows=R, titles=titles,
        origin = 'Généré par %s le ' % VERSION.SCONAME + timedate_human_repr() + '',
        caption = title,
        html_caption = title,
        html_class='gt_table table_leftalign',
        base_url = '%s?formsemestre_id=%s' % (REQUEST.URL0, formsemestre_id),
        page_title = title,
        html_title = context.html_sem_header(REQUEST, 'Description du semestre', sem, with_page_header=False), 
        pdf_title = title,
        preferences=context.get_preferences(formsemestre_id)
        )

def formsemestre_description(context, formsemestre_id, format='html', REQUEST=None):
    """Description du semestre sous forme de table exportable
    Liste des modules et de leurs coefficients
    """
    tab = formsemestre_description_table(context, formsemestre_id, REQUEST)
    return tab.make_page(context, format=format, REQUEST=REQUEST)                          

def formsemestre_lists(context, formsemestre_id, REQUEST=None):
    """Listes des étudiants"""
    sem = context.get_formsemestre(formsemestre_id)
    H = [ context.html_sem_header(REQUEST, '', sem),
          context.make_listes_sem(sem, REQUEST),
          context.sco_footer(REQUEST) ]
    return '\n'.join(H)
