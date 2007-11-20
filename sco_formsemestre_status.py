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
from sco_utils import SCO_ENCODING
from ScolarRolesNames import *
from sco_formsemestre_custommenu import formsemestre_custommenu_html

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
    H.append('</ul></ul></div>')
    return ''.join(H)


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
        { 'title' : 'Options du semestre',
          'url' :  'formsemestre_edit_options?formsemestre_id=' + formsemestre_id,
          'enabled' : (uid == sem['responsable_id']) or authuser.has_permission(ScoImplement, context),
          'helpmsg' : 'Change les options'
          },
        { 'title' : change_lock_msg,
          'url' :  'formsemestre_change_lock?formsemestre_id=' + formsemestre_id,
          'enabled' : (uid == sem['responsable_id']) or authuser.has_permission(ScoImplement, context),
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
          'enabled' :  authuser.has_permission(ScoEtudChangeGroups, context)
          },
        { 'title' : 'Modifier les groupes de ' + sem['nomgroupeta'],
          'url' : 'affectGroupes?formsemestre_id=%s&groupType=TA&groupTypeName=%s'% (formsemestre_id,sem['nomgroupeta']),
          'enabled' :  authuser.has_permission(ScoEtudChangeGroups, context)
          },
        { 'title' : 'Modifier les groupes de ' + sem['nomgroupetp'],
          'url' : 'affectGroupes?formsemestre_id=%s&groupType=TP&groupTypeName=%s'% (formsemestre_id,sem['nomgroupetp']),
          'enabled' :  authuser.has_permission(ScoEtudChangeGroups, context)
          },        
        { 'title' : 'Passage des étudiants depuis d\'autres semestres',
          'url' : 'formsemestre_inscr_passage?formsemestre_id=' + formsemestre_id,
          'enabled' : authuser.has_permission(ScoEtudInscrit, context)
          },
        { 'title' : 'Synchroniser avec étape Apogée',
          'url' : 'formsemestre_synchro_etuds?formsemestre_id=' + formsemestre_id,
          'enabled' : authuser.has_permission(ScoEtudInscrit, context)
          },
        { 'title' : 'Importer des étudiants dans ce semestre (table Excel)',
          'url' : 'form_students_import_excel?formsemestre_id=' + formsemestre_id,
          'enabled' : authuser.has_permission(ScoEtudInscrit, context)
          },
        { 'title' : 'Créer un nouvel étudiant',
          'url' : 'etudident_create_form?formsemestre_id=' + formsemestre_id,
          'enabled' : authuser.has_permission(ScoEtudInscrit, context)
          },
        { 'title' : 'Importer données admission',
          'url' : 'form_students_import_infos_admissions?formsemestre_id=' + formsemestre_id,
          'enabled' : authuser.has_permission(ScoEtudInscrit, context)
          },
        { 'title' : 'Exporter table des étudiants',
          'url' : 'listegroupe?format=allxls&formsemestre_id='+ formsemestre_id,
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
    menuStats = [
        { 'title' : 'Tableau de répartition des bacs',
          'url' : 'stat_bac_fmt?formsemestre_id=' + formsemestre_id,
          },
        { 'title' : 'Suivi de cohortes (à implémenter)',
          'url' : '',
          'enabled' : False, # XXX
          }
        ]

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
