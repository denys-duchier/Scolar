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

"""Tableau de bord module
"""

from notesdb import *
from sco_utils import *
from notes_log import log
from TrivialFormulator import TrivialFormulator, TF
from notes_table import *
import sco_groups
import sco_evaluations
import htmlutils
import sco_excel
from gen_tables import GenTable
from htmlutils import histogram_notes
import sco_formsemestre_status
from sco_formsemestre_status import makeMenu
import sco_compute_moy

from sets import Set

# ported from old DTML code in oct 2009

# menu evaluation dans moduleimpl
def moduleimpl_evaluation_menu(context, evaluation_id, nbnotes=0, REQUEST=None):
    "Menu avec actions sur une evaluation"
    authuser = REQUEST.AUTHENTICATED_USER
    E = context.do_evaluation_list({'evaluation_id' : evaluation_id})[0]
    modimpl = context.do_moduleimpl_list({'moduleimpl_id' : E['moduleimpl_id']})[0]

    group_id = sco_groups.get_default_group(context, modimpl['formsemestre_id'])

    if context.can_edit_notes(REQUEST.AUTHENTICATED_USER, E['moduleimpl_id'], allow_ens=False) and nbnotes != 0:
        sup_label = "Supprimer évaluation impossible (il y a des notes)"
    else:
        sup_label = "Supprimer évaluation"

    menuEval = [
        { 'title' : 'Saisir notes',
          'url' : 'notes_eval_selectetuds?evaluation_id=' + evaluation_id,
          'enabled' : context.can_edit_notes(REQUEST.AUTHENTICATED_USER, E['moduleimpl_id'])
          },
        { 'title' : 'Modifier évaluation',
          'url' : 'evaluation_edit?evaluation_id=' + evaluation_id,
          'enabled' : context.can_edit_notes(REQUEST.AUTHENTICATED_USER, E['moduleimpl_id'], allow_ens=False)
          },
        { 'title' : sup_label,
          'url' : 'evaluation_delete?evaluation_id=' + evaluation_id,
          'enabled' : nbnotes == 0 and context.can_edit_notes(REQUEST.AUTHENTICATED_USER, E['moduleimpl_id'], allow_ens=False)
          },
        { 'title' : 'Supprimer toutes les notes',
          'url' : 'evaluation_suppress_alln?evaluation_id=' + evaluation_id,
          'enabled' : context.can_edit_notes(REQUEST.AUTHENTICATED_USER, E['moduleimpl_id'], allow_ens=False)
          },
        { 'title' : 'Afficher les notes',
          'url' : 'evaluation_listenotes?evaluation_id=' + evaluation_id,
          'enabled' : nbnotes > 0
          },            
        { 'title' : 'Absences ce jour',
          'url' : 'Absences/EtatAbsencesDate?date=%s&group_id=%s'
          % (urllib.quote(E['jour'],safe=''), group_id),
          'enabled' : E['jour']
          },
        { 'title' : 'Vérifier notes vs absents',
          'url' : 'evaluation_check_absences_html?evaluation_id=%s' %(evaluation_id),
          'enabled' : nbnotes > 0 and E['jour']
          },
        ]

    return makeMenu( 'actions', menuEval )


def moduleimpl_status(context, moduleimpl_id=None, partition_id=None, REQUEST=None):
    """Tableau de bord module (liste des evaluations etc)"""
    authuser = REQUEST.AUTHENTICATED_USER
    M = context.do_moduleimpl_list( args={ 'moduleimpl_id' : moduleimpl_id } )[0]
    formsemestre_id = M['formsemestre_id']
    Mod = context.do_module_list( args={ 'module_id' : M['module_id'] } )[0]
    sem = context.do_formsemestre_list( args={ 'formsemestre_id' : formsemestre_id } )[0]
    F = context.formation_list( args={ 'formation_id' : sem['formation_id'] } )[0]
    ModInscrits = context.do_moduleimpl_inscription_list( args={ 'moduleimpl_id' : M['moduleimpl_id'] } )
    ModEvals = context.do_evaluation_list( args={ 'moduleimpl_id' : M['moduleimpl_id'] } )
    #
    caneditevals=context.can_edit_notes(authuser,moduleimpl_id,allow_ens=sem['ens_can_edit_eval'])
    caneditnotes=context.can_edit_notes(authuser,moduleimpl_id)
    arrow_up, arrow_down, arrow_none = sco_groups.getArrowIconsTags(context, REQUEST)
    #
    H = [ context.sco_header(REQUEST, page_title="Module %(titre)s" % Mod),
    """<h2 class="formsemestre">Module <tt>%(code)s</tt> %(titre)s</h2>""" % Mod,
    # XXX """caneditevals=%s caneditnotes=%s""" % (caneditevals,caneditnotes),
    """<div class="moduleimpl_tableaubord">

<table>
<tr>
<td class="fichetitre2">Responsable: </td><td class="redboldtext">""",
    context.Users.user_info(M['responsable_id'],REQUEST)['nomprenom'],
    """<span class="blacktt">(%(responsable_id)s)</span>""" % M,    
    ]
    try:
        context.can_change_module_resp(REQUEST, moduleimpl_id)
        H.append("""<a class="stdlink" href="edit_moduleimpl_resp?moduleimpl_id=%s">modifier</a>""" % moduleimpl_id)
    except:
        pass
    H.append("""</td><td>""")
    H.append(', '.join( [ context.Users.user_info(m['ens_id'],REQUEST)['nomprenom'] for m in M['ens'] ]))
    H.append("""</td><td>""")
    try:
        context.can_change_ens(REQUEST, moduleimpl_id)
        H.append("""<a class="stdlink" href="edit_enseignants_form?moduleimpl_id=%s">modifier les enseignants</a>""" % moduleimpl_id)
    except:
        pass
    H.append("""</td></tr>""")
    
    # 2ieme ligne: Semestre, Coef
    H.append("""<tr><td class="fichetitre2">""")
    if sem['semestre_id'] >= 0:
        H.append("""Semestre: </td><td>%s""" % sem['semestre_id'])
    else:
        H.append("""</td><td>""")
    if sem['etat'] != '1':
        H.append( icontag('lock32_img', title="verrouillé") )
    H.append("""</td><td class="fichetitre2">Coef dans le semestre: %(coefficient)s</td><td></td></tr>""" % Mod)
    # 3ieme ligne: Formation
    H.append("""<tr><td class="fichetitre2">Formation: </td><td>%(titre)s</td></tr>""" % F )
    # Ligne: Inscrits
    H.append("""<tr><td class="fichetitre2">Inscrits: </td><td> %d étudiants</td></tr>""" % len(ModInscrits) )
    # Ligne: règle de calcul
    has_expression = sco_compute_moy.moduleimpl_has_expression(context, M)
    if has_expression:
        H.append('<tr><td class="fichetitre2" colspan="2">Règle de calcul: <span class="formula" title="mode de calcul de la moyenne du module">moyenne=<tt>%s</tt></span>' % M['computation_expr'])
        if context.can_change_ens(REQUEST, moduleimpl_id, raise_exc=False):
            H.append('<span class="fl"><a class="stdlink"  href="edit_moduleimpl_expr?moduleimpl_id=%s">changer</a></span>'  % moduleimpl_id)
        H.append('</td></tr>')
    else:
        t0, t1 = '<em>règle de calcul standard</em>', ''
        H.append('<tr><td colspan="2"><em title="mode de calcul de la moyenne du module">règle de calcul standard</em>')
        if context.can_change_ens(REQUEST, moduleimpl_id, raise_exc=False):
            H.append(' (<a class="stdlink" href="edit_moduleimpl_expr?moduleimpl_id=%s">changer</a>)' % moduleimpl_id)
        H.append('</td></tr>')
    H.append('<tr><td colspan="2"><a class="stdlink" href="view_module_abs?moduleimpl_id=%s">Absences</a>' % moduleimpl_id)
    H.append('</table>')
    #
    if has_expression:
        nt = context._getNotesCache().get_NotesTable(context, formsemestre_id)
        if nt.expr_diagnostics:
            H.append( sco_formsemestre_status.html_expr_diagnostic(context, nt.expr_diagnostics) )
    #
    H.append("""<p><form name="f"><span style="font-size:120%%; font-weight: bold;">%d évaluations :</span>
<span style="padding-left: 30px;">
<input type="hidden" name="moduleimpl_id" value="%s"/>""" % (len(ModEvals), moduleimpl_id) )
    #
    # Liste les noms de partitions 
    partitions = sco_groups.get_partitions_list(context, sem['formsemestre_id'])
    H.append("""Afficher les groupes de&nbsp;<select name="partition_id" onchange="document.f.submit();">""")
    for partition in partitions:
        if partition['partition_id'] == partition_id:
            selected = 'selected'
        else:
            selected = ''
        name = partition['partition_name']
        if name is None:
            name = 'Tous'
        H.append("""<option value="%s" %s>%s</option>""" % (partition['partition_id'], selected, name))
    H.append("""</select>
&nbsp;&nbsp;&nbsp;&nbsp;
<a class="stdlink" href="evaluation_listenotes?moduleimpl_id=%(moduleimpl_id)s">Voir toutes les notes</a>
</span>
</form>
</p>
""" % M)
    
    # -------- Tableau des evaluations
    H.append("""<table class="moduleimpl_evaluations">""")
    eval_index = len(ModEvals) - 1
    for eval in ModEvals:
        etat = sco_evaluations.do_evaluation_etat(context, eval['evaluation_id'], partition_id=partition_id, select_first_partition=True)
        if eval['evaluation_type'] == EVALUATION_RATTRAPAGE:
            tr_class = 'mievr_rattr'
        else:
            tr_class = 'mievr'
        H.append("""<tr><td colspan="8">&nbsp;</td></tr>""")
        H.append("""<tr class="mievr"><td class="mievr_tit" colspan="8">""" )
        if eval['jour']:
            H.append("""Le %(jour)s%(descrheure)s""" % eval )
        else:
            H.append("""<a href="evaluation_edit?evaluation_id=%(evaluation_id)s" class="mievr_evalnodate">Evaluation sans date</a>""" % eval )
        H.append('&nbsp;&nbsp;&nbsp; <em>%(description)s</em>' % eval)
        if eval['evaluation_type'] == EVALUATION_RATTRAPAGE:
            H.append("""<span class="mievr_rattr">rattrapage</span>""")
        if etat['last_modif']:
            H.append("""<span class="mievr_lastmodif">(dernière modif le %s)</span>""" % etat['last_modif'].strftime('%d/%m/%Y à %Hh%M') )
        H.append('<span class="evalindex_cont">')
        if has_expression:
             H.append("""<span class="evalindex" title="Indice dans les vecteurs (formules)">%02d</span>""" % eval_index)
        # H.append("""<span class="evalindex" title="Numero">%s</span>""" % eval['numero']) debug
        # Fleches:
        H.append('<span class="eval_arrows_chld">')
        if eval_index != (len(ModEvals) - 1) and caneditevals:
            H.append('<a href="module_evaluation_move?evaluation_id=%s&after=0" class="aud">%s</a>' % (eval['evaluation_id'], arrow_up))
        else:
            H.append(arrow_none)
        if eval_index > 0 and caneditevals:
            H.append('<a href="module_evaluation_move?evaluation_id=%s&after=1" class="aud">%s</a>' % (eval['evaluation_id'], arrow_down))
        else:
            H.append(arrow_none)
        H.append('</span></span>')
                
        eval_index -= 1
        H.append("""</td></tr>""")
        H.append("""<tr class="%s"><th class="moduleimpl_evaluations" colspan="2">&nbsp;</th><th class="moduleimpl_evaluations">Durée</th><th class="moduleimpl_evaluations">Coef.</th><th class="moduleimpl_evaluations">Notes</th><th class="moduleimpl_evaluations">Abs</th><th class="moduleimpl_evaluations">N</th><th class="moduleimpl_evaluations">Moyenne """ % tr_class)
        
        if  etat['evalcomplete']:
             etat_txt = """(prise en compte)"""
             etat_descr = "notes utilisées dans les moyennes"
        elif eval['publish_incomplete'] != '0':
            etat_txt = """(prise en compte <b>immédiate</b>)"""
            etat_descr = "il manque des notes, mais la prise en compte immédiate a été demandée"
        elif etat['nb_notes'] != 0:
            etat_txt = '(<b>non</b> prise en compte)'
            etat_descr = "il manque des notes"
        else:
            etat_txt = ''
        if caneditevals and etat_txt:
            etat_txt = '<a href="evaluation_edit?evaluation_id=%s" title="%s">%s</a>' % (eval['evaluation_id'], etat_descr, etat_txt )
        H.append(etat_txt)
        H.append("""</th></tr>""")
        
        H.append("""<tr class="%s"><td class="mievr">""" % tr_class)
        if caneditevals:
            H.append("""<a class="smallbutton" href="evaluation_edit?evaluation_id=%s">%s</a>""" % (eval['evaluation_id'], icontag('edit_img', alt='modifier', title='Modifier informations')))
        if caneditnotes:
            H.append("""<a class="smallbutton" href="notes_eval_selectetuds?evaluation_id=%s">%s</a>""" % (eval['evaluation_id'], icontag('notes_img', alt='saisie notes', title='Saisie des notes')))
        if etat['nb_notes'] == 0:
            if caneditevals:
                H.append("""<a class="smallbutton" href="evaluation_delete?evaluation_id=%(evaluation_id)s">""" % eval)
            H.append( icontag('delete_img', alt='supprimer', title='Supprimer') )
            if caneditevals:
                H.append("""</a>""")
        elif etat['evalcomplete']:
             H.append("""<a class="smallbutton" href="evaluation_listenotes?evaluation_id=%s">%s</a>""" % (eval['evaluation_id'], icontag('status_green_img', title='ok')))
        else:
            if etat['evalattente']:
                H.append("""<a class="smallbutton" href="evaluation_listenotes?evaluation_id=%s">%s</a>""" % (eval['evaluation_id'], icontag("status_greenorange_img", file_format='gif',title='notes en attente')))
            else:
                H.append("""<a class="smallbutton" href="evaluation_listenotes?evaluation_id=%s">%s</a>""" % (eval['evaluation_id'], icontag('status_orange_img', title='il manque des notes')))
        #
        if eval['visibulletin']=='1':
            H.append(icontag('status_visible_img', title='visible dans bulletins intermédiaires'))
        else:
            H.append('&nbsp;')
        H.append( '</td><td class="mievr_menu">')
        if caneditnotes:
            H.append( moduleimpl_evaluation_menu(context, eval['evaluation_id'], nbnotes=etat['nb_notes'], REQUEST=REQUEST))
        H.append('</td>')
        #
        H.append("""
<td class="mievr_dur">%s</td><td class="rightcell mievr_coef">%s</td>"""
                 % (eval['duree'], '%g' % eval['coefficient']) )
        H.append("""<td class="rightcell mievr_nbnotes">%(nb_notes)s / %(nb_inscrits)s</td>
<td class="rightcell mievr_coef">%(nb_abs)s</td>
<td class="rightcell mievr_coef">%(nb_neutre)s</td>
<td class="rightcell">"""
                 % etat )
        if etat['moy']:
            H.append( '%s / %g' % (etat['moy'], eval['note_max']))
        else:
            H.append("""<a class="redlink" href="notes_eval_selectetuds?evaluation_id=%s">saisir notes</a>""" % (eval['evaluation_id']))
        H.append("""</td></tr>""")
        #
        if etat['nb_notes'] == 0:
            H.append("""<tr class="%s"><td colspan="8">&nbsp;""" % tr_class)
            # XXX
            H.append("""</td></tr>""")
        else: # il y a deja des notes saisies
            gr_moyennes = etat['gr_moyennes']
            for gr_moyenne in gr_moyennes:
                H.append("""<tr class="%s">""" % tr_class)
                H.append("""<td colspan="2">&nbsp;</td>""")                
                if gr_moyenne['group_name'] is None:
                    name = 'Tous' # tous
                else:
                    name = 'Groupe %s' % gr_moyenne['group_name']
                H.append("""<td colspan="5" class="mievr_grtit">%s &nbsp;</td><td>""" % name )
                if gr_moyenne['gr_nb_notes'] > 0:
                    H.append( '%(gr_moy)s' %  gr_moyenne )
                    H.append("""&nbsp; (<a href="evaluation_listenotes?tf-submitted=1&evaluation_id=%s&group_ids%%3Alist=%s">%s</a> notes"""
                             % (eval['evaluation_id'], gr_moyenne['group_id'], gr_moyenne['gr_nb_notes']))
                    if gr_moyenne['gr_nb_att'] > 0:
                        H.append(""", <span class="redboldtext">%s en attente</span>""" % gr_moyenne['gr_nb_att'])
                    H.append(""")""")
                    if gr_moyenne['group_id'] in etat['gr_incomplets']:
                        H.append("""[<font color="red">""")
                        if caneditnotes:
                            H.append("""<a class="redlink" href="notes_eval_selectetuds?evaluation_id=%s&group_ids:list=%s">incomplet</a></font>]""" % (eval['evaluation_id'], gr_moyenne['group_id']))
                        else:
                            H.append("""incomplet</font>]""")
                else:
                    H.append("""<span class="redboldtext">&nbsp; """)
                    if caneditnotes:
                        H.append("""<a class="redlink" href="notes_eval_selectetuds?evaluation_id=%s&group_ids:list=%s">""" % (eval['evaluation_id'], gr_moyenne['group_id']))
                    H.append('pas de notes')
                    if caneditnotes:
                        H.append("""</a>""")
                    H.append('</span>')
                H.append("""</td></tr>""")
    
    #
    if caneditevals or sem['etat'] != '1':
        H.append("""<tr><td colspan="7">""")
        if sem['etat'] != '1':
            H.append("""%s semestre verrouillé""" % icontag('lock32_img'))
        else:
            H.append("""<a class="stdlink" href="evaluation_create?moduleimpl_id=%s">Créer nouvelle évaluation</a>""" % M['moduleimpl_id'] )
            if authuser.has_permission(ScoEtudInscrit,context):
                H.append("""&nbsp;&nbsp;&nbsp;&nbsp;
<a class="stdlink" href="moduleimpl_inscriptions_edit?moduleimpl_id=%s">Gérer les inscriptions à ce module</a>""" % M['moduleimpl_id'] )
            H.append("""&nbsp;&nbsp;&nbsp;&nbsp;<a class="stdlink" href="module_evaluation_renumber?moduleimpl_id=%s&redirect=1">Trier par date</a>""" % M['moduleimpl_id'] )
    H.append("""</td></tr>
</table>

</div>

<!-- LEGENDE -->
<hr>
<h4>Légende</h4>
<ul>
<li>%s : modifie description de l'évaluation (date, heure, coefficient, ...)</li>
<li>%s : saisie des notes</li>
<li>%s : indique qu'il n'y a aucune note entrée (cliquer pour supprimer cette évaluation)</li>
<li>%s : indique qu'il manque quelques notes dans cette évaluation</li>
<li>%s : toutes les notes sont entrées (cliquer pour les afficher)</li>
<li>%s : indique que cette évaluation sera mentionnée dans les bulletins au format "intermédiaire"
</ul>

<p>Rappel : seules les notes des évaluations complètement saisies (affichées en vert) apparaissent dans les bulletins.
</p>
    """ % (icontag('edit_img'), 
           icontag('notes_img'),
           icontag('delete_img'),
           icontag('status_orange_img'),
           icontag('status_green_img'),
           icontag('status_visible_img')))
    H.append(context.sco_footer(REQUEST))
    return ''.join(H) 
