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

def makeMenu( title, items, cssclass='custommenu' ):
    """HTML snippet to render a simple drop down menu.
    items is a list of dicts:
    { 'title' :
      'url' :
      'enabled' : # True by default
      'helpmsg' :
    }
    """
    H = [ """<div class="barrenav"><ul class="nav">
    <li onmouseover="MenuDisplay(this)" onmouseout="MenuHide(this)"><a href="#" class="menu %s">%s</a><ul>""" % (cssclass, title)
          ]
    for item in items:
        if item.get('enabled', True):
            H.append('<li><a href="%(url)s">%(title)s</a></li>' % item)
        else:
            H.append('<li><span class="disabled_menu_item">%(title)s</span></li>' % item)
    H.append('</ul></li></ul></div>')
    return ''.join(H)


def defMenuStats(context,formsemestre_id):
    "Définition du menu 'Statistiques' "
    return [
        { #'title' : 'Tableau de répartition des bacs',
          #'url' : 'stat_bac_fmt?formsemestre_id=' + formsemestre_id,
        'title' : 'Statistiques...',
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
            
    menuSemestre = [
        # Si on voulait autoriser le dir des etud a modifier le semestre,
        # il faudrait ajouter (sem['responsable_id'] == str(REQUEST.AUTHENTICATED_USER))
        # et aussi modifer les permissions sur formsemestre_editwithmodules
        { 'title' : 'Modifier le semestre',
          'url' : 'formsemestre_editwithmodules?formation_id=%(formation_id)s&formsemestre_id=%(formsemestre_id)s' % sem,
          'enabled' : authuser.has_permission(ScoImplement, context) and (sem['etat'] == '1'),
          'helpmsg' : 'Modifie le contenu du semestre (modules)'
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
          }
        ]
    if uid == 'root' or uid[:7] == 'viennet':
        menuSemestre.append( { 'title' : 'Check integrity',
                               'url' : 'check_sem_integrity?formsemestre_id=' + formsemestre_id,
                               'enabled' : True })

    menuInscriptions = [
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
        { 'title' : 'Exporter table des étudiants',
          'url' : 'listegroupe?format=allxls&formsemestre_id='+ formsemestre_id,
          },
        { 'title' : 'Vérifier inscriptions multiples',
          'url' : 'formsemestre_inscrits_ailleurs?formsemestre_id=' + formsemestre_id,
          }
        ]

    menuBulletins = [
        { 'title' : 'Tableau des moyennes (et liens bulletins)',
          'url' : 'formsemestre_recapcomplet?formsemestre_id=' + formsemestre_id,
          },
        { 'title' : 'Classeur PDF des bulletins (versions courtes)',
          'url' : 'formsemestre_bulletins_pdf?version=short&formsemestre_id='+ formsemestre_id,
          'helpmsg' : 'PDF regroupant tous les bulletins'
          },
        { 'title' : 'Classeur PDF des bulletins (versions intermédiaires)',
          'url' : 'formsemestre_bulletins_pdf?version=selectedevals&formsemestre_id='+ formsemestre_id,
          'helpmsg' : 'PDF regroupant tous les bulletins'
          },
        { 'title' : 'Classeur PDF des bulletins (versions completes)',
          'url' : 'formsemestre_bulletins_pdf?version=long&formsemestre_id='+ formsemestre_id,
          'helpmsg' : 'PDF regroupant tous les bulletins'
          },
        { 'title' : 'Envoyer à chaque étudiant son bulletin par e-mail (versions courtes)',
          'url' : 'formsemestre_bulletins_mailetuds?version=short&formsemestre_id='+ formsemestre_id,
          },
        { 'title' : 'Envoyer à chaque étudiant son bulletin par e-mail (versions intermédiaires)',
          'url' : 'formsemestre_bulletins_mailetuds?version=selectedevals&formsemestre_id='+ formsemestre_id,
          },
        { 'title' : 'Envoyer à chaque étudiant son bulletin par e-mail (versions complètes)',
          'url' : 'formsemestre_bulletins_mailetuds?version=long&formsemestre_id='+ formsemestre_id,
          },

        ]
    menuJury = [
        { 'title' : 'Voir les décisions du jury (et éditer les PV)',
          'url' : 'formsemestre_pvjury?formsemestre_id=' + formsemestre_id,
          },
        { 'title' : 'Générer feuille préparation Jury',
          'url' : 'feuille_preparation_jury?formsemestre_id=' + formsemestre_id,
          },
        { 'title' : 'Saisie des décisions du jury',
          'url' : 'formsemestre_recapcomplet?modejury=1&hidemodules=1&formsemestre_id=' + formsemestre_id,
          'enabled' : context.can_validate_sem(REQUEST, formsemestre_id)
          }
        ]
    
    menuStats = defMenuStats(context,formsemestre_id)

    H = [
        '<div class="formsemestre_menubar">',
        makeMenu( 'Semestre', menuSemestre ),
        makeMenu( 'Inscriptions', menuInscriptions),
        makeMenu( 'Bulletins', menuBulletins),
        makeMenu( 'Jury', menuJury),
        makeMenu( 'Statistiques', menuStats),
        formsemestre_custommenu_html(context, formsemestre_id),
        '</div>'
          ]
    return '\n'.join(H)



# Description du semestre sous forme de table exportable
def formsemestre_description_table(context, formsemestre_id, REQUEST):
    """Description du semestre sous forme de table exportable
    Liste des modules et de leurs coefficients
    """
    sem = context.do_formsemestre_list( args={ 'formsemestre_id' : formsemestre_id } )[0]
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
    
    title = 'Semestre %s' % (sem['titreannee'])
    
    return GenTable(
        columns_ids=columns_ids, rows=R, titles=titles,
        origin = 'Généré par %s le ' % VERSION.SCONAME + timedate_human_repr() + '',
        caption = title,
        html_caption = title,
        html_class='gt_table table_leftalign',
        base_url = '%s?formsemestre_id=%s' % (REQUEST.URL0, formsemestre_id),
        page_title = title,
        html_title = """<h2>Semestre <a href="formsemestre_status?formsemestre_id=%s">%s</a></h2>""" % (formsemestre_id, sem['titreannee']),
        pdf_title = title,
        preferences=context.get_preferences()
        )

def formsemestre_description(context, formsemestre_id, format='html', REQUEST=None):
    """Description du semestre sous forme de table exportable
    Liste des modules et de leurs coefficients
    """
    tab = formsemestre_description_table(context, formsemestre_id, REQUEST)
    return tab.make_page(context, format=format, REQUEST=REQUEST)                          
