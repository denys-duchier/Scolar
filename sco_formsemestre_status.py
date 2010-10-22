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

# Rewritten from ancient DTML code
from mx.DateTime import DateTime as mxDateTime

from notesdb import *
from notes_log import log
from sco_utils import *
from sco_formsemestre_custommenu import formsemestre_custommenu_html
from gen_tables import GenTable
import sco_archives
import sco_groups
import sco_evaluations
import sco_formsemestre_edit
import sco_compute_moy

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
    "D�finition du menu 'Statistiques' "
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
          },
        { 'title' : 'Table "poursuite" (experimental)',
          'url' : 'formsemestre_poursuite_report?formsemestre_id=' + formsemestre_id,
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
        change_lock_msg = 'D�verrouiller'

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
        { 'title' : 'Pr�f�rences du semestre',
          'url' : 'formsemestre_edit_preferences?formsemestre_id=%(formsemestre_id)s' % sem,
          'enabled' : (authuser.has_permission(ScoImplement, context) or (sem['responsable_id'] == str(REQUEST.AUTHENTICATED_USER) and sem['resp_can_edit'])) and (sem['etat'] == '1'),
          'helpmsg' : 'Pr�f�rences du semestre'
          },
        { 'title' : 'R�glages bulletins',
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
        { 'title' : 'V�rifier absences aux �valuations',
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
        { 'title' : 'Associer � une nouvelle version du programme',
          'url' :  'formsemestre_associate_new_version?formsemestre_id=' + formsemestre_id,
          'enabled' : authuser.has_permission(ScoChangeFormation, context) and (sem['etat']== '1'),
          'helpmsg' : ''
          },
        { 'title' : 'Supprimer ce semestre',
          'url' : 'formsemestre_delete?formsemestre_id=' + formsemestre_id,
          'enabled' : authuser.has_permission(ScoImplement, context),
          'helpmsg' : ''
          },
        ]
    # debug :
    if uid == 'root' or uid[:7] == 'viennet':
        menuSemestre.append( { 'title' : 'Check integrity',
                               'url' : 'check_sem_integrity?formsemestre_id=' + formsemestre_id,
                               'enabled' : True })

    menuInscriptions = [
        { 'title' : 'Voir les inscriptions aux modules',
          'url' : 'moduleimpl_inscriptions_stats?formsemestre_id=' + formsemestre_id,
          } ]
    menuInscriptions += [        
        { 'title' : 'Passage des �tudiants depuis d\'autres semestres',
          'url' : 'formsemestre_inscr_passage?formsemestre_id=' + formsemestre_id,
          'enabled' : authuser.has_permission(ScoEtudInscrit, context) and (sem['etat']== '1')
          },
        { 'title' : 'Synchroniser avec �tape Apog�e',
          'url' : 'formsemestre_synchro_etuds?formsemestre_id=' + formsemestre_id,
          'enabled' : authuser.has_permission(ScoEtudInscrit, context) and context.get_preference('portal_url') and (sem['etat']== '1')
          },
        { 'title' : 'Inscrire un �tudiant',
          'url' : 'formsemestre_inscription_with_modules_etud?formsemestre_id=' + formsemestre_id,
          'enabled' : authuser.has_permission(ScoEtudInscrit, context) and (sem['etat']== '1')
          },
        { 'title' : 'Importer des �tudiants dans ce semestre (table Excel)',
          'url' : 'form_students_import_excel?formsemestre_id=' + formsemestre_id,
          'enabled' : authuser.has_permission(ScoEtudInscrit, context) and (sem['etat']== '1')
          },
        { 'title' : 'Importer donn�es admission',
          'url' : 'form_students_import_infos_admissions?formsemestre_id=' + formsemestre_id,
          'enabled' : authuser.has_permission(ScoEtudInscrit, context)
          },
        { 'title' : 'Resynchroniser donn�es identit�',
          'url' : 'formsemestre_import_etud_admission?formsemestre_id=' + formsemestre_id,
          'enabled' : authuser.has_permission(ScoEtudInscrit, context) and context.get_preference('portal_url'),
          },

        { 'title' : 'Exporter table des �tudiants',
          'url' : 'listegroupe?format=allxls&group_id='+ sco_groups.get_default_group(context, formsemestre_id),
          },
        { 'title' : 'V�rifier inscriptions multiples',
          'url' : 'formsemestre_inscrits_ailleurs?formsemestre_id=' + formsemestre_id,
          }
        ]

    menuGroupes = [
        { 'title' : 'Listes des �tudiants',
          'url' : 'formsemestre_lists?formsemestre_id=' + formsemestre_id,
          'enabled' : True,
          'helpmsg' : 'Acc�s aux listes des groupes d\'�tudiants'
          },
        { 'title' : 'Cr�er/modifier les partitions...',
          'url' : 'editPartitionForm?formsemestre_id=' + formsemestre_id,
          'enabled' : context.can_change_groups(REQUEST, formsemestre_id)
          },        
        ]
    # 1 item / partition:
    for partition in sco_groups.get_partitions_list(context, formsemestre_id, with_default=False):
        menuGroupes.append(
            { 'title' : 'Modifier les groupes de %s' % partition['partition_name'],
              'url' : 'affectGroups?partition_id=%s'% partition['partition_id'],
              'enabled' : context.can_change_groups(REQUEST, formsemestre_id)
              })


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
        { 'title' : 'Envoyer � chaque �tudiant son bulletin par e-mail',
          'url' : 'formsemestre_bulletins_mailetuds_choice?formsemestre_id='+ formsemestre_id,
          },
        { 'title' : 'Calendrier des �valuations',
          'url' : 'formsemestre_evaluations_cal?formsemestre_id='+ formsemestre_id,
          },
        { 'title' : 'Lister toutes les saisies de notes',
          'url' : 'formsemestre_list_saisies_notes?formsemestre_id='+ formsemestre_id,
          },
        ]
    menuJury = [
        { 'title' : 'Voir les d�cisions du jury',
          'url' : 'formsemestre_pvjury?formsemestre_id=' + formsemestre_id,
          },
        { 'title' : 'G�n�rer feuille pr�paration Jury',
          'url' : 'feuille_preparation_jury?formsemestre_id=' + formsemestre_id,
          },
        { 'title' : 'Saisie des d�cisions du jury',
          'url' : 'formsemestre_recapcomplet?modejury=1&hidemodules=1&formsemestre_id=' + formsemestre_id,
          'enabled' : context.can_validate_sem(REQUEST, formsemestre_id)
          },
        { 'title' : 'Editer les PV et archiver les r�sultats',
          'url' : 'formsemestre_archive?formsemestre_id=' + formsemestre_id,
          'enabled' : context.can_validate_sem(REQUEST, formsemestre_id)
          },
        { 'title' : 'Documents archiv�s',
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
        '<td>', makeMenu( 'Groupes', menuGroupes, base_url=base_url ), '</td>',
        '<td>',  makeMenu( 'Notes', menuNotes, base_url=base_url ), '</td>',
        '<td>', makeMenu( 'Jury', menuJury, base_url=base_url ), '</td>',
        '<td>', makeMenu( 'Statistiques', menuStats, base_url=base_url ), '</td>',
        '<td>', formsemestre_custommenu_html(context, formsemestre_id, base_url=base_url), '</td></tr></table></div>',
          ]
    return '\n'.join(H)


# Element HTML decrivant un semestre (barre de menu et infos)
def formsemestre_page_title(context, REQUEST):
    """Element HTML decrivant un semestre (barre de menu et infos)
    Cherche dans REQUEST si un semestre est d�fini (formsemestre_id ou moduleimpl ou evaluation ou group)
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
    elif REQUEST.form.has_key('group_id'):
        group = sco_groups.get_group(context, REQUEST.form['group_id'])        
        formsemestre_id = group['formsemestre_id']
    elif REQUEST.form.has_key('partition_id'):
        partition = sco_groups.get_partition(context, REQUEST.form['partition_id'])
        formsemestre_id = partition['formsemestre_id']
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
        sem['locklink'] = """<a href="%s/formsemestre_change_lock?formsemestre_id=%s">%s</a>""" % (sem['notes'], sem['formsemestre_id'], context.icons.lock_img.tag(border='0',title='Semestre verrouill�'))
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
        sem['etape_apo_str'] = 'Code �tape Apog�e: %s' % sem['etape_apo']
    else:
        sem['etape_apo_str'] = 'Pas de code �tape'
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
    sum_coef = 0
    sum_ects = 0
    for M in Mlist:
        ModInscrits = context.do_moduleimpl_inscription_list( args={ 'moduleimpl_id' : M['moduleimpl_id'] })
        l = { 'UE' : M['ue']['acronyme'],
              'Code' : M['module']['code'],
              'Module' : M['module']['abbrev'] or M['module']['titre'],
              'Inscrits' : len(ModInscrits),
              'Responsable' : context.Users.user_info(M['responsable_id'],REQUEST)['nomprenom'],
              'Coef.' : M['module']['coefficient'],
              'ECTS' : M['module']['ects'],
              }
        R.append(l)
        if M['module']['coefficient']:
            sum_coef += M['module']['coefficient']
        if M['module']['ects']:
            sum_ects += M['module']['ects']
    sums = { '_css_row_class' : 'moyenne sortbottom',
             'ECTS' : sum_ects,
             'Coef.' : sum_coef }
    R.append(sums)
    columns_ids = [ 'UE', 'Code', 'Module', 'Coef.', 'ECTS', 'Inscrits', 'Responsable' ]
    titles = columns_ids
    titles = {}
    # on veut { id : id }, peu elegant en python 2.3:
    map( lambda x,titles=titles: titles.__setitem__(x[0],x[1]), zip(columns_ids,columns_ids) )
    
    title = 'Semestre %s' % (sem['titremois'])
    
    return GenTable(
        columns_ids=columns_ids, rows=R, titles=titles,
        origin = 'G�n�r� par %s le ' % VERSION.SCONAME + timedate_human_repr() + '',
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
    """Listes des �tudiants"""
    sem = context.get_formsemestre(formsemestre_id)
    H = [ context.html_sem_header(REQUEST, '', sem),
          context.make_listes_sem(sem, REQUEST),
          context.sco_footer(REQUEST) ]
    return '\n'.join(H)


def html_expr_diagnostic(context, diagnostics):
    """Affiche messages d'erreur des formules utilisateurs"""
    H = []
    H.append('<div class="ue_warning">Erreur dans des formules utilisateurs:<ul>')
    last_id, last_msg = None, None
    for diag in diagnostics:
        if 'moduleimpl_id' in diag:
            mod = context.do_moduleimpl_withmodule_list( args={ 'moduleimpl_id' : diag['moduleimpl_id'] } )[0]
            H.append('<li>module <a href="moduleimpl_status?moduleimpl_id=%s">%s</a>: %s</li>' 
                     % (diag['moduleimpl_id'], mod['module']['abbrev'] or mod['module']['code'] or '?', diag['msg']))
        else:
            if diag['ue_id'] != last_id or diag['msg'] != last_msg:
                ue = context.do_ue_list( {'ue_id' : diag['ue_id']})[0]
                H.append('<li>UE "%s": %s</li>' % (ue['acronyme'] or ue['titre'] or '?', diag['msg']))
                last_id, last_msg = diag['ue_id'], diag['msg']

    H.append('</ul></div>')
    return ''.join(H)

def formsemestre_status_head(context, formsemestre_id=None, REQUEST=None, page_title=None):
    """En-t�te HTML des pages "semestre"
    """
    semlist = context.do_formsemestre_list( args={ 'formsemestre_id' : formsemestre_id } )
    if not semlist:
        raise ScoValueError( 'Semestre inexistant (il a peut �tre �t� supprim� ?)' )
    sem = semlist[0]
    F = context.do_formation_list( args={ 'formation_id' : sem['formation_id'] } )[0]

    page_title = page_title or 'Modules de '
    
    H = [ context.html_sem_header(REQUEST, page_title, sem, with_page_header=False, with_h2=False),
          """<table>
          <tr><td class="fichetitre2">Formation: </td><td>
         <a href="Notes/ue_list?formation_id=%(formation_id)s" class="discretelink" title="Formation %(acronyme)s, v%(version)s">%(titre)s</a>""" % F ]
    if sem['semestre_id'] >= 0:
        H.append(", semestre %(semestre_id)s" % sem )
    if sem['modalite']:
        H.append('&nbsp;en %(modalite)s' % sem )
    if sem['etape_apo']:
        H.append('&nbsp;&nbsp;&nbsp;(�tape <b><tt>%(etape_apo)s</tt></b>)' % sem )
    H.append('</td></tr>')
    
    evals = sco_evaluations.do_evaluation_etat_in_sem(context, formsemestre_id)   
    H.append('<tr><td class="fichetitre2">Evaluations: </td><td> %(nb_evals_completes)s ok, %(nb_evals_en_cours)s en cours, %(nb_evals_vides)s vides' % evals)
    if evals['last_modif']:
        H.append(' <em>(derni�re note saisie le %s)</em>' % evals['last_modif'].strftime('%d/%m/%Y � %Hh%M'))
    H.append('</td></tr>')
    if evals['attente']:
        H.append("""<tr><td class="fichetitre2"></td><td class="redboldtext">
Il y a des notes en attente ! Le classement des �tudiants n'a qu'une valeur indicative. 
</td></tr>""")
    H.append('</table>')
    if sem['bul_hide_xml'] != '0':
        H.append('<p><em>Bulletins non publi�s sur le portail</em></p>')
    
    return ''.join(H)


def formsemestre_status(context, formsemestre_id=None, REQUEST=None):
    """Tableau de bord semestre HTML"""
    # port� du DTML
    cnx = context.GetDBConnexion()
    status_head = formsemestre_status_head(context, formsemestre_id=formsemestre_id, REQUEST=REQUEST)
    sem = context.get_formsemestre(formsemestre_id)
    Mlist = context.do_moduleimpl_withmodule_list( args={ 'formsemestre_id' : formsemestre_id } )
    inscrits = context.do_formsemestre_inscription_list( args={ 'formsemestre_id' : formsemestre_id } )
    prev_ue_id = None

    can_edit = sco_formsemestre_edit.can_edit_sem(context, REQUEST, formsemestre_id, sem=sem)

    H = [ context.sco_header(REQUEST, page_title='Semestre %s' % sem['titreannee'] ),
          '<div class="formsemestre_status">',
          formsemestre_status_head(context, formsemestre_id=formsemestre_id, page_title='Tableau de bord'),
          """<p><b style="font-size: 130%">Tableau de bord: </b><span class="help">cliquez sur un module pour saisir des notes</span></p>""" ]
    nt = context._getNotesCache().get_NotesTable(context, formsemestre_id)
    if nt.expr_diagnostics:
        H.append(html_expr_diagnostic(context, nt.expr_diagnostics))
    H.append("""
<p>
<table class="formsemestre_status">
<tr>
<th class="formsemestre_status">Code</th>
<th class="formsemestre_status">Module</th>
<th class="formsemestre_status">Inscrits</th>
<th class="resp">Responsable</th>
<th class="evals">Evaluations</th></tr>"""
          )
    for M in Mlist:
        Mod = M['module']
        ModDescr = 'Module ' + M['module']['titre'] + ', coef. ' + str(M['module']['coefficient'])
        ModEns = context.Users.user_info(M['responsable_id'],REQUEST)['nomcomplet']
        if M['ens']:
            ModEns += ' (resp.), ' + ', '.join( [ context.Users.user_info(e['ens_id'],REQUEST)['nomcomplet'] for e in M['ens'] ] )
        ModInscrits = context.do_moduleimpl_inscription_list( args={ 'moduleimpl_id' : M['moduleimpl_id'] } )
        if prev_ue_id != M['ue']['ue_id']:
            prev_ue_id = M['ue']['ue_id']
            H.append("""<tr class="formsemestre_status_ue"><td colspan="4">
<span class="status_ue_acro">%(acronyme)s</span>
<span class="status_ue_title">%(titre)s</span>
</td><td>""" % M['ue'] )
            
            expr = sco_compute_moy.get_ue_expression(formsemestre_id, M['ue']['ue_id'], cnx, html_quote=True)

            if can_edit:
                H.append(' <a href="edit_ue_expr?formsemestre_id=%s&ue_id=%s">' % (formsemestre_id, M['ue']['ue_id']))
            H.append(icontag('formula', title="Mode calcul moyenne d'UE", style="vertical-align:middle"))
            if can_edit:
                H.append('</a>')
            if expr:
                H.append(''' <span class="formula" title="mode de calcul de la moyenne d'UE">%s</span>''' % expr)

            H.append('</td></tr>')

        if M['ue']['type'] != 0:
            fontorange = ' fontorange' # style css additionnel
        else:
            fontorange = ''
        etat = sco_evaluations.do_evaluation_etat_in_mod(context, M['moduleimpl_id'])
        if etat['nb_evals_completes'] > 0 and etat['nb_evals_en_cours'] == 0 and etat['nb_evals_vides'] == 0:
            H.append('<tr class="formsemestre_status_green%s">' % fontorange)
        else:
            H.append('<tr class="formsemestre_status%s">' % fontorange)

        H.append('<td class="formsemestre_status_code"><a href="moduleimpl_status?moduleimpl_id=%s" title="%s" class="stdlink">%s</a></td>' % 
                 (M['moduleimpl_id'],ModDescr,Mod['code']))
        H.append('<td><a href="moduleimpl_status?moduleimpl_id=%s" title="%s" class="formsemestre_status_link">%s</a></td>'
                 % (M['moduleimpl_id'], ModDescr, Mod['abbrev'] or Mod['titre']))
        H.append('<td class="formsemestre_status_inscrits">%s</td>' % len( ModInscrits ))
        H.append('<td class="resp"><a class="discretelink" href="moduleimpl_status?moduleimpl_id=%s" title="%s">%s</a></td>'
                 % (M['moduleimpl_id'], ModEns, context.Users.user_info(M['responsable_id'],REQUEST)['prenomnom']))
        
        H.append('<td class="evals">')
        nb_evals = etat['nb_evals_completes']+etat['nb_evals_en_cours']+etat['nb_evals_vides']
        if nb_evals != 0:
            H.append('<a href="moduleimpl_status?moduleimpl_id=%s" class="formsemestre_status_link">%s pr�vues, %s ok</a>' 
                     % (M['moduleimpl_id'], nb_evals, etat['nb_evals_completes']))
            if etat['nb_evals_en_cours'] > 0:
                H.append(', <span><a class="redlink" href="moduleimpl_status?moduleimpl_id=%s" title="Il manque des notes">%s en cours</a></span>' % (M['moduleimpl_id'], etat['nb_evals_en_cours']))
            if etat['attente']:
                H.append(' <span><a class="redlink" href="moduleimpl_status?moduleimpl_id=%s" title="Il y a des notes en attente">[en attente]</a></span>'
                         % M['moduleimpl_id'])
        H.append('</td></tr>')
    H.append('</table></p>')
    # --- LISTE DES ETUDIANTS 
    H += [ '<div id="groupes">',
           context.make_listes_sem(sem, REQUEST),
           '</div>' ]
    
    return ''.join(H) + context.sco_footer(REQUEST)

