# -*- mode: python -*-
# -*- coding: utf-8 -*-

##############################################################################
#
# Gestion scolarite IUT
#
# Copyright (c) 2001 - 2015 Emmanuel Viennet.  All rights reserved.
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

"""Semestres: valisation semestre et UE dans parcours
"""
import urllib, time, datetime

from notesdb import *
from sco_utils import *
from notes_log import log
from scolog import logdb
from notes_table import *
import notes_table
from ZAbsences import getAbsSemEtud

import sco_formsemestre_status
import sco_parcours_dut, sco_codes_parcours
import sco_pvjury
import sco_photos

# ------------------------------------------------------------------------------------
def formsemestre_validation_etud_form(
    context, # ZNotes instance
    formsemestre_id=None, # required
    etudid=None, # one of etudid or etud_index is required
    etud_index=None,
    check=0, # opt: si true, propose juste une relecture du parcours
    desturl=None,
    sortcol=None,
    readonly=True,
    REQUEST=None):
    nt = context._getNotesCache().get_NotesTable(context, formsemestre_id) #> get_table_moyennes_triees, get_etud_decision_sem
    T = nt.get_table_moyennes_triees()
    if not etudid and not etud_index:
        raise ValueError('formsemestre_validation_etud_form: missing argument etudid')
    if etud_index:
        etud_index = int(etud_index)
        # cherche l'etudid correspondant
        if etud_index < 0 or etud_index >= len(T):
            raise ValueError('formsemestre_validation_etud_form: invalid etud_index value')
        etudid = T[etud_index][-1]        
    else:
        # cherche index pour liens navigation
        etud_index = len(T) - 1
        while etud_index >= 0 and T[etud_index][-1] != etudid:
            etud_index -= 1
        if etud_index < 0:
            raise ValueError("formsemestre_validation_etud_form: can't retreive etud_index !")
    # prev, next pour liens navigation
    etud_index_next = etud_index + 1
    if etud_index_next >= len(T):
        etud_index_next = None
    etud_index_prev = etud_index - 1
    if etud_index_prev < 0:
        etud_index_prev = None
    if readonly:
        check = True
    
    etud = context.getEtudInfo(etudid=etudid, filled=True)[0]
    Se = sco_parcours_dut.SituationEtudParcours(context, etud, formsemestre_id)
    if Se.sem['etat'] != '1':
        raise ScoValueError('validation: semestre verrouille')
    
    H = [ context.sco_header(REQUEST, page_title='Parcours %(nomprenom)s' % etud,
                             javascripts=[ 'js/recap_parcours.js']
                             ) ]

    Footer = ['<p>']
    # Navigation suivant/precedent
    if etud_index_prev != None:
        etud_p = context.getEtudInfo(etudid=T[etud_index_prev][-1], filled=True)[0]
        Footer.append('<span><a href="formsemestre_validation_etud_form?formsemestre_id=%s&amp;etud_index=%s">Etud. précédent (%s)</a></span>' % (formsemestre_id,etud_index_prev, etud_p['nomprenom']) )
    if etud_index_next != None:
        etud_n = context.getEtudInfo(etudid=T[etud_index_next][-1], filled=True)[0]
        Footer.append('<span style="padding-left: 50px;"><a href="formsemestre_validation_etud_form?formsemestre_id=%s&amp;etud_index=%s">Etud. suivant (%s)</a></span>' % (formsemestre_id,etud_index_next, etud_n['nomprenom']) )
    Footer.append('</p>')
    Footer.append(context.sco_footer(REQUEST))


    H.append('<table style="width: 100%"><tr><td>')
    if not check:
        H.append('<h2 class="formsemestre">%s: validation %s%s</h2>Parcours: %s' 
                 % (etud['nomprenom'], Se.parcours.SESSION_NAME_A, Se.parcours.SESSION_NAME, Se.get_parcours_descr()))
    else:
        H.append('<h2 class="formsemestre">Parcours de %s</h2>%s' % (etud['nomprenom'], Se.get_parcours_descr()) )
    
    H.append('</td><td style="text-align: right;"><a href="%s/ficheEtud?etudid=%s">%s</a></td></tr></table>'
             % (context.ScoURL(), etudid,    
                sco_photos.etud_photo_html(context, etud, title='fiche de %s'%etud['nom'], REQUEST=REQUEST)))

    etud_etat = nt.get_etud_etat(etudid)
    if etud_etat == 'D':
        H.append('<div class="ue_warning"><span>Etudiant démissionnaire</span></div>')
    if etud_etat == 'DEF':
        H.append('<div class="ue_warning"><span>Etudiant défaillant</span></div>')
    if etud_etat != 'I':
        H.append(tf_error_message("""Impossible de statuer sur cet étudiant: il est démissionnaire ou défaillant (voir <a href="%s/ficheEtud?etudid=%s">sa fiche</a>)""" % (context.ScoURL(), etudid)))
        return '\n'.join(H+Footer)
    
    H.append( formsemestre_recap_parcours_table(context, Se, etudid, with_links=(check and not readonly)) )
    if check:
        if not desturl:
            desturl = 'formsemestre_recapcomplet?modejury=1&amp;hidemodules=1&amp;formsemestre_id='+formsemestre_id
            if sortcol:
                desturl += '&amp;sortcol=' + sortcol # pour refaire tri sorttable du tableau de notes
            desturl += '#etudid%s' % etudid # va a la bonne ligne
        H.append('<ul><li><a href="%s">Continuer</a></li></ul>' % desturl)
        
        return '\n'.join(H+Footer)

    decision_jury = Se.nt.get_etud_decision_sem(etudid)

    # Bloque si note en attente
    if nt.etud_has_notes_attente(etudid):
        H.append(tf_error_message("""Impossible de statuer sur cet étudiant: il a des notes en attente dans des évaluations de ce semestre (voir <a href="formsemestre_status?formsemestre_id=%s">tableau de bord</a>)""" % formsemestre_id))
        return '\n'.join(H+Footer)
    
    # Infos si pas de semestre précédent
    if not Se.prev:
        if Se.sem['semestre_id'] == 1:
            H.append('<p>Premier semestre (pas de précédent)</p>')
        else:
            H.append('<p>Pas de semestre précédent !</p>')
    else:
        if not Se.prev_decision:
            H.append(tf_error_message("""Le jury n\'a pas statué sur le semestre précédent ! (<a href="formsemestre_validation_etud_form?formsemestre_id=%s&amp;etudid=%s">le faire maintenant</a>)""" % (Se.prev['formsemestre_id'], etudid)))
            if decision_jury:
                H.append('<a href="formsemestre_validation_suppress_etud?etudid=%s&amp;formsemestre_id=%s" class="stdlink">Supprimer décision existante</a>'% (etudid, formsemestre_id))
            H.append(context.sco_footer(REQUEST))
            return '\n'.join(H)

    # Infos sur decisions déjà saisies
    if decision_jury:
        if decision_jury['assidu']:
            ass = 'assidu'
        else:
            ass = 'non assidu'
        H.append('<p>Décision existante du %(event_date)s: %(code)s' % decision_jury )
        H.append(' (%s)' % ass )
        auts = sco_parcours_dut.formsemestre_get_autorisation_inscription(
            context, etudid, formsemestre_id)
        if auts:
            H.append( '. Autorisé%s à s\'inscrire en ' % etud['ne'] )
            alist = []
            for aut in auts:
                alist.append (str(aut['semestre_id']))
            H.append( ', '.join( ['S%s' % x for x in alist ]) + '.')
        H.append( '</p>' )

    # Cas particulier pour ATJ: corriger precedent avant de continuer
    if Se.prev_decision and Se.prev_decision['code'] == 'ATJ':
        H.append("""<div class="sfv_warning"><p>La décision du semestre précédent est en
        <b>attente</b> à cause d\'un <b>problème d\'assiduité<b>.</p>
        <p>Vous devez la corriger avant de continuer ce jury. Soit vous considérez que le
        problème d'assiduité n'est pas réglé et choisissez de ne pas valider le semestre
        précédent (échec), soit vous entrez une décision sans prendre en compte
        l'assiduité.</p>
        <form method="get" action="formsemestre_validation_etud_form">
        <input type="submit" value="Statuer sur le semestre précédent"/>
        <input type="hidden" name="formsemestre_id" value="%s"/>
        <input type="hidden" name="etudid" value="%s"/>
        <input type="hidden" name="desturl" value="formsemestre_validation_etud_form?etudid=%s&amp;formsemestre_id=%s"/>
        """ % (Se.prev['formsemestre_id'], etudid, etudid, formsemestre_id))
        if sortcol:
            H.append('<input type="hidden" name="sortcol" value="%s"/>' % sortcol)
        H.append('</form></div>')

        H.append(context.sco_footer(REQUEST))
        return '\n'.join(H)

    # Explication sur barres actuelles
    H.append('<p class="sfv_explication">L\'étudiant ')
    if Se.barre_moy_ok:
        H.append('a la moyenne générale, ')
    else:
        H.append('<b>n\'a pas</b> la moyenne générale, ')
    if Se.barres_ue_ok:
        H.append('les UEs sont au dessus des barres')
    else:
        H.append('<b>%d UE sous la barre</b>' % (Se.nb_ues_under))
    if (not Se.barre_moy_ok) and Se.can_compensate_with_prev:
        H.append(', et ce semestre peut se <b>compenser</b> avec le précédent')
    H.append('.</p>')
        
    # Décisions possibles
    rows_assidu = decisions_possible_rows(Se, True, subtitle='Etudiant assidu:', trclass='sfv_ass')
    rows_non_assidu = decisions_possible_rows(Se, False,
                                              subtitle='Si problème d\'assiduité:', trclass='sfv_pbass')
    # s'il y a des decisions recommandees issues des regles:
    if rows_assidu or rows_non_assidu: 
        H.append("""<form method="get" action="formsemestre_validation_etud" id="formvalid" class="sfv_decisions">
        <input type="hidden" name="etudid" value="%s"/>
        <input type="hidden" name="formsemestre_id" value="%s"/>""" %
                 (etudid, formsemestre_id) )
        if desturl:
            H.append('<input type="hidden" name="desturl" value="%s"/>' % desturl)
        if sortcol:
            H.append('<input type="hidden" name="sortcol" value="%s"/>' % sortcol)

        H.append('<h3 class="sfv">Décisions <em>recommandées</em> :</h3>')
        H.append('<table>')
        H.append(rows_assidu)        
        if rows_non_assidu:
            H.append('<tr><td>&nbsp;</td></tr>') # spacer
            H.append(rows_non_assidu)

        H.append('</table>')    
        H.append('<p><br/></p><input type="submit" value="Valider ce choix" disabled="1" id="subut"/>')
        H.append('</form>')

    H.append( form_decision_manuelle(context, Se, formsemestre_id, etudid) )

    H.append( """<div class="link_defaillance">Ou <a class="stdlink" href="formDef?etudid=%s&amp;formsemestre_id=%s">déclarer l'étudiant comme défaillant dans ce semestre</a></div>""" % (etudid, formsemestre_id) )

    H.append('<p style="font-size: 50%;">Formation ' )
    if Se.sem['gestion_semestrielle'] == '1':
        H.append('avec semestres décalés</p>' )
    else:
        H.append('sans semestres décalés</p>' )
    
    return ''.join(H+Footer)

def formsemestre_validation_etud(
    context, # ZNotes instance
    formsemestre_id=None, # required
    etudid=None, # required
    codechoice=None, # required
    desturl='', sortcol=None,
    REQUEST=None):
    """Enregistre validation"""
    etud = context.getEtudInfo(etudid=etudid, filled=True)[0]
    Se = sco_parcours_dut.SituationEtudParcours(context, etud, formsemestre_id)
    # retrouve la decision correspondant au code:
    choices = Se.get_possible_choices(assiduite=True)
    choices += Se.get_possible_choices(assiduite=False)
    found=False
    for choice in choices:
        if choice.codechoice == codechoice:
            found=True
            break
    if not found:
        raise ValueError('code choix invalide ! (%s)' % codechoice)
    #
    Se.valide_decision(choice, REQUEST) # enregistre
    _redirect_valid_choice(formsemestre_id, etudid, Se, choice, desturl, sortcol, REQUEST)

def formsemestre_validation_etud_manu(
    context, # ZNotes instance
    formsemestre_id=None, # required
    etudid=None, # required
    code_etat='', new_code_prev='', devenir='', # required (la decision manuelle)
    assidu=False,
    desturl='', sortcol=None,
    REQUEST=None,
    redirect=True):
    """Enregistre validation"""    
    if assidu:
        assidu = 1
    etud = context.getEtudInfo(etudid=etudid, filled=True)[0]
    Se = sco_parcours_dut.SituationEtudParcours(context, etud, formsemestre_id)
    if code_etat in Se.parcours.UNUSED_CODES:
        raise ScoValueError('code decision invalide dans ce parcours')
    # Si code ADC, extrait le semestre utilisé:
    if code_etat[:3] == 'ADC':
        formsemestre_id_utilise_pour_compenser = code_etat.split('_')[1]
        if not formsemestre_id_utilise_pour_compenser:
            formsemestre_id_utilise_pour_compenser = None # compense avec semestre hors ScoDoc
        code_etat = 'ADC'
    else:
        formsemestre_id_utilise_pour_compenser = None
    
    # Construit le choix correspondant:
    choice = sco_parcours_dut.DecisionSem(
        code_etat=code_etat, new_code_prev=new_code_prev, devenir=devenir,
        assiduite=assidu,
        formsemestre_id_utilise_pour_compenser = formsemestre_id_utilise_pour_compenser)
    #
    Se.valide_decision(choice, REQUEST) # enregistre    
    if redirect:
        _redirect_valid_choice(formsemestre_id, etudid, Se, choice, desturl, sortcol, REQUEST)


def _redirect_valid_choice(formsemestre_id, etudid, Se, choice, desturl, sortcol, REQUEST):
    adr = 'formsemestre_validation_etud_form?formsemestre_id=%s&amp;etudid=%s&amp;check=1' % (formsemestre_id, etudid)
    if sortcol:
        adr += '&amp;sortcol=' + sortcol
    if desturl:
        desturl += '&amp;desturl=' + desturl
    REQUEST.RESPONSE.redirect(adr)
    # Si le precedent a été modifié, demande relecture du parcours.
    # sinon  renvoie au listing general,
#     if choice.new_code_prev:
#         REQUEST.RESPONSE.redirect( 'formsemestre_validation_etud_form?formsemestre_id=%s&etudid=%s&amp;check=1&amp;desturl=%s' % (formsemestre_id, etudid, desturl) )
#     else:
#         if not desturl:
#             desturl = 'formsemestre_recapcomplet?modejury=1&amp;hidemodules=1&amp;formsemestre_id=' + formsemestre_id          
#         REQUEST.RESPONSE.redirect(desturl)


def _dispcode(c):
    if not c:
        return ''
    return c

def decisions_possible_rows(Se, assiduite, subtitle= '', trclass=''):
    "Liste HTML des decisions possibles"
    choices = Se.get_possible_choices(assiduite=assiduite)
    if not choices:
        return ''
    TitlePrev = ''
    if Se.prev:
        if Se.prev['semestre_id'] >= 0:
            TitlePrev = '%s%d' % (Se.parcours.SESSION_ABBRV, Se.prev['semestre_id'])
        else:
            TitlePrev = 'Prec.'

    if Se.sem['semestre_id'] >= 0:
        TitleCur = '%s%d' % (Se.parcours.SESSION_ABBRV, Se.sem['semestre_id'])
    else:
        TitleCur = Se.parcours.SESSION_NAME
    
    H = [ '<tr class="%s titles"><th class="sfv_subtitle">%s</em></th>' % (trclass, subtitle) ]
    if Se.prev:
        H.append('<th>Code %s</th>' % TitlePrev )
    H.append('<th>Code %s</th><th>Devenir</th></tr>' % TitleCur )
    for ch in choices:
        H.append("""<tr class="%s"><td title="règle %s"><input type="radio" name="codechoice" value="%s" onClick="document.getElementById('subut').disabled=false;">"""
                 % (trclass, ch.rule_id, ch.codechoice) )
        H.append('%s </input></td>' % ch.explication)
        if Se.prev:
            H.append('<td class="centercell">%s</td>' % _dispcode(ch.new_code_prev) )
        H.append( '<td class="centercell">%s</td><td>%s</td>'
                 % (_dispcode(ch.code_etat), Se.explique_devenir(ch.devenir)))
        H.append('</tr>')

    return '\n'.join(H)


def formsemestre_recap_parcours_table( context, Se, etudid, with_links=False,
                                       with_all_columns=True,
                                       a_url='',
                                       sem_info={},
                                       show_details=False):
    """Tableau HTML recap parcours
    Si with_links, ajoute liens pour modifier decisions (colonne de droite)   
    sem_info = { formsemestre_id : txt } permet d'ajouter des informations associées à chaque semestre
    with_all_columns: si faux, pas de colonne "assiduité".
    """
    H = []
    linktmpl  = '<span onclick="toggle_vis(this);" class="toggle_sem sem_%%s">%s</span>'
    minuslink = linktmpl % icontag('minus_img', border="0", alt="-")
    pluslink  = linktmpl % icontag('plus_img', border="0", alt="+")
    if show_details:
        sd = ' recap_show_details'
        plusminus = minuslink
    else:
        sd = ' recap_hide_details'
        plusminus = pluslink
    H.append( '<table class="recap_parcours%s"><tr>' % sd )
    H.append('<th><span onclick="toggle_all_sems(this);" title="Ouvrir/fermer tous les semestres">%s</span></th><th></th><th>Semestre</th>' %  icontag('plus18_img', width=18, height=18, border=0, title="", alt="+"))
    H.append('<th>Etat</th><th>Abs</th>')
    # titres des UE
    H.append( '<th></th>' * Se.nb_max_ue )
    #
    if with_links:
        H.append('<th></th>')
    H.append('<th></th></tr>')
    num_sem = 0
    
    for sem in Se.get_semestres():
        is_prev = Se.prev and (Se.prev['formsemestre_id'] == sem['formsemestre_id'])
        is_cur = (Se.formsemestre_id == sem['formsemestre_id'])        
        num_sem += 1
        
        dpv = sco_pvjury.dict_pvjury(context, sem['formsemestre_id'], etudids=[etudid])
        pv = dpv['decisions'][0]
        decision_sem = pv['decision_sem']
        decisions_ue = pv['decisions_ue']
        if with_all_columns and decision_sem and decision_sem['assidu'] == 0:
            ass = ' (non ass.)'
        else:
            ass = ''
        
        nt = context._getNotesCache().get_NotesTable(context, sem['formsemestre_id'] ) #> get_ues, get_etud_moy_gen, get_etud_ue_status
        if is_cur:
            type_sem = '*' # now unused
            class_sem = 'sem_courant'
        elif is_prev:
            type_sem = 'p'
            class_sem = 'sem_precedent'
        else:
            type_sem = ''
            class_sem = 'sem_autre'
        if sem['bul_bgcolor']:
            bgcolor = sem['bul_bgcolor']
        else:
            bgcolor = 'background-color: rgb(255,255,240)'
        # 1ere ligne: titre sem, decision, acronymes UE
        H.append('<tr class="%s rcp_l1 sem_%s">' % (class_sem,sem['formsemestre_id']))
        if is_cur:
            pm = ''
        elif is_prev:
            pm = minuslink % sem['formsemestre_id']
        else:
            pm = plusminus % sem['formsemestre_id']
        
        H.append('<td class="rcp_type_sem" style="background-color:%s;">%s%s</td>'
                 % (bgcolor, num_sem, pm) )
        H.append('<td class="datedebut">%(mois_debut)s</td>' % sem )
        H.append('<td><a class="formsemestre_status_link" href="%sformsemestre_bulletinetud?formsemestre_id=%s&amp;etudid=%s" title="Bulletin de notes">%s</a></td>' % (a_url,sem['formsemestre_id'], etudid,sem['titreannee']))
        if decision_sem:
            H.append('<td class="rcp_dec">%s</td>' % decision_sem['code'])
        else:
            H.append('<td colspan="%d"><em>en cours</em></td>')
        H.append('<td class="rcp_nonass">%s</td>' % ass) # abs
        # acronymes UEs
        ues = nt.get_ues(filter_sport=True) 
        for ue in ues:
            H.append('<td class="ue_acro"><span>%s</span></td>' % ue['acronyme'])
        if len(ues) < Se.nb_max_ue:
            H.append('<td colspan="%d"></td>' % (Se.nb_max_ue - len(ues)))
        # indique le semestre compensé par celui ci:
        if decision_sem and decision_sem['compense_formsemestre_id']:
            csem = context.do_formsemestre_list(
                {'formsemestre_id' : decision_sem['compense_formsemestre_id']})[0]
            H.append('<td><em>compense S%s</em></td>' % csem['semestre_id'] )
        else:
            H.append('<td></td>')
        if with_links:
            H.append('<td></td>')
        H.append('</tr>')
        # 2eme ligne: notes
        H.append('<tr class="%s rcp_l2 sem_%s">' % (class_sem, sem['formsemestre_id']))
        H.append('<td class="rcp_type_sem" style="background-color:%s;">&nbsp;</td>'
                 % (bgcolor) )
        if is_prev:
            default_sem_info = '<span class="fontred">[sem. précédent]</span>'
        else:
            default_sem_info = ''
        if sem['etat'] != '1': # locked
            lockicon = icontag('lock32_img', title="verrouillé", border='0')
            default_sem_info += lockicon
        H.append('<td class="datefin">%s</td><td class="sem_info">%s</td>'
                 % (sem['mois_fin'], 
                    sem_info.get(sem['formsemestre_id'], default_sem_info)))
        # Moy Gen (sous le code decision)
        H.append('<td class="rcp_moy">%s</td>' % notes_table.fmt_note( nt.get_etud_moy_gen(etudid)) )
        # Absences (nb d'abs non just. dans ce semestre)
        AbsEtudSem = getAbsSemEtud(context, sem['formsemestre_id'], etudid)
        nbabs = AbsEtudSem.CountAbs()
        nbabsjust = AbsEtudSem.CountAbsJust()
        H.append('<td class="rcp_abs">%d</td>' % (nbabs-nbabsjust) )
        
        # UEs
        for ue in ues:            
            if decisions_ue and decisions_ue.has_key(ue['ue_id']):
                code = decisions_ue[ue['ue_id']]['code']
            else:
                code = ''
            ue_status = nt.get_etud_ue_status(etudid, ue['ue_id'])
            moy_ue = ue_status['moy']
            explanation_ue = [] # list of strings 
            if code == 'ADM':
                class_ue = 'ue_adm'
            elif code == 'CMP':
                class_ue = 'ue_cmp'
            else:
                class_ue = 'ue'
            if ue_status['is_external']: # validation externe
                explanation_ue.append( 'UE externe.' )
                #log('x'*12+' EXTERNAL %s' % notes_table.fmt_note(moy_ue)) XXXXXXX
                #log('UE=%s' % pprint.pformat(ue))
                #log('explanation_ue=%s\n'%explanation_ue)
            if ue_status['is_capitalized']:
                class_ue += ' ue_capitalized'
                explanation_ue.append('Capitalisée le %s.' % (ue_status['event_date'] or '?'))
                #log('x'*12+' CAPITALIZED %s' % notes_table.fmt_note(moy_ue))
                #log('UE=%s' % pprint.pformat(ue))
                #log('UE_STATUS=%s'  % pprint.pformat(ue_status)) XXXXXX
                #log('')
                
            H.append('<td class="%s" title="%s">%s</td>' 
                     % (class_ue, ' '.join(explanation_ue), notes_table.fmt_note(moy_ue)) )
        if len(ues) < Se.nb_max_ue:
            H.append('<td colspan="%d"></td>' % (Se.nb_max_ue - len(ues)))
        
        H.append('<td></td>')
        if with_links:
            H.append('<td><a href="%sformsemestre_validation_etud_form?formsemestre_id=%s&amp;etudid=%s">modifier</a></td>' % (a_url,sem['formsemestre_id'],etudid))

        H.append('</tr>')
        # 3eme ligne: ECTS
        if context.get_preference('bul_show_ects', sem['formsemestre_id']) or nt.parcours.ECTS_ONLY:
            etud_moy_infos = nt.get_etud_moy_infos(etudid)
            H.append('<tr class="%s rcp_l2 sem_%s">' % (class_sem, sem['formsemestre_id']))
            H.append('<td class="rcp_type_sem" style="background-color:%s;">&nbsp;</td><td></td>'
                     % (bgcolor) )
            # total ECTS (affiché sous la moyenne générale)
            H.append('<td class="sem_ects_tit"><a title="crédit potentiels (dont nb de fondamentaux)">ECTS:</a></td><td class="sem_ects">%g <span class="ects_fond">%g</span></td>'
                     % (etud_moy_infos['ects_pot'],etud_moy_infos['ects_pot_fond']))
            H.append('<td class="rcp_abs"></td>'  ) 
            # ECTS validables dans chaque UE
            for ue in ues:
                ue_status = nt.get_etud_ue_status(etudid, ue['ue_id'])
                H.append('<td class="ue">%g <span class="ects_fond">%g</span></td>' % (ue_status['ects_pot'],ue_status['ects_pot_fond']))
            H.append('</tr>')

    H.append('</table>')
    return '\n'.join(H)


def form_decision_manuelle(context, Se, formsemestre_id, etudid, desturl='', sortcol=None):
    """Formulaire pour saisie décision manuelle
    """
    H = [ """
    <script type="text/javascript">
    function IsEmpty(aTextField) {
    if ((aTextField.value.length==0) || (aTextField.value==null)) {
        return true;
     } else { return false; }
    }	
    function check_sfv_form() {
    if (IsEmpty(document.forms.formvalidmanu.code_etat)) {
       alert('Choisir un code semestre !');
       return false;
    }
    return true;
    }
    </script>
    
    <form method="get" action="formsemestre_validation_etud_manu" name="formvalidmanu" id="formvalidmanu" class="sfv_decisions sfv_decisions_manuelles" onsubmit="return check_sfv_form()">
    <input type="hidden" name="etudid" value="%s"/>
    <input type="hidden" name="formsemestre_id" value="%s"/>
    """ % (etudid, formsemestre_id) ]
    if desturl:
        H.append('<input type="hidden" name="desturl" value="%s"/>' % desturl)
    if sortcol:
        H.append('<input type="hidden" name="sortcol" value="%s"/>' % sortcol)

    H.append('<h3 class="sfv">Décisions manuelles : <em>(vérifiez bien votre choix !)</em></h3><table>')

    # Choix code semestre:
    codes = sco_codes_parcours.CODES_EXPL.keys()
    codes.sort() # fortuitement, cet ordre convient bien !

    H.append('<tr><td>Code semestre: </td><td><select name="code_etat"><option value="" selected>Choisir...</option>')
    for cod in codes:
        if cod in Se.parcours.UNUSED_CODES:
            continue
        if cod != 'ADC':
            H.append('<option value="%s">%s (code %s)</option>' % (cod, sco_codes_parcours.CODES_EXPL[cod], cod) )
        elif Se.sem['gestion_compensation'] == '1':
            # traitement spécial pour ADC (compensation)
            # ne propose que les semestres avec lesquels on peut compenser
            # le code transmis est ADC_formsemestre_id
            # on propose aussi une compensation sans utiliser de semestre, pour les cas ou le semestre
            # précédent n'est pas géré dans ScoDoc (code ADC_)
            #log(str(Se.sems))
            for sem in Se.sems:
                if sem['can_compensate']:
                    H.append('<option value="%s_%s">Admis par compensation avec S%s (%s)</option>' %
                             (cod, sem['formsemestre_id'], sem['semestre_id'], sem['date_debut']) )
            if Se.could_be_compensated():
                H.append('<option value="ADC_">Admis par compensation (avec un semestre hors ScoDoc)</option>' )
    H.append('</select></td></tr>')

    # Choix code semestre precedent:
    if Se.prev:
        H.append('<tr><td>Code semestre précédent: </td><td><select name="new_code_prev"><option value="">Choisir une décision...</option>')
        for cod in codes:
            if cod == 'ADC': # ne propose pas ce choix
                continue
            if Se.prev_decision and cod == Se.prev_decision['code']:
                sel='selected'        
            else:
                sel=''
            H.append('<option value="%s" %s>%s (code %s)</option>' % (cod, sel, sco_codes_parcours.CODES_EXPL[cod], cod) )        
        H.append('</select></td></tr>')

    # Choix code devenir
    codes = sco_codes_parcours.DEVENIR_EXPL.keys()
    codes.sort() # fortuitement, cet ordre convient aussi bien !

    if Se.sem['semestre_id'] == -1:
        allowed_codes = sco_codes_parcours.DEVENIRS_MONO
    else:
        allowed_codes = set(sco_codes_parcours.DEVENIRS_STD)
        # semestres decales ?
        if Se.sem['gestion_semestrielle'] == '1':
            allowed_codes = allowed_codes.union(sco_codes_parcours.DEVENIRS_DEC)
        # n'autorise les codes NEXT2 que si semestres décalés et s'il ne manque qu'un semestre avant le n+2
        if Se.can_jump_to_next2():
            allowed_codes = allowed_codes.union(sco_codes_parcours.DEVENIRS_NEXT2)
    
    H.append('<tr><td>Devenir: </td><td><select name="devenir"><option value="" selected>Choisir...</option>')
    for cod in codes:
        if  cod in allowed_codes: # or Se.sem['gestion_semestrielle'] == '1'
            H.append('<option value="%s">%s</option>' % (cod, Se.explique_devenir(cod)))
    H.append('</select></td></tr>')

    H.append('<tr><td><input type="checkbox" name="assidu" checked="checked">assidu</input></td></tr>')
    
    H.append("""</table>
    <input type="submit" name="formvalidmanu_submit" value="Valider décision manuelle"/>
    <span style="padding-left: 5em;"><a href="formsemestre_validation_suppress_etud?etudid=%s&amp;formsemestre_id=%s" class="stdlink">Supprimer décision existante</a></span>
    </form>
    """ % (etudid, formsemestre_id))
    return '\n'.join(H)

# ----------- 
def  formsemestre_validation_auto(context, formsemestre_id, REQUEST):
    "Formulaire saisie automatisee des decisions d'un semestre"
    sem= context.get_formsemestre(formsemestre_id)
    H = [ context.html_sem_header(REQUEST, 'Saisie automatique des décisions du semestre', sem),
          """
    <ul>
    <li>Seuls les étudiants qui obtiennent le semestre seront affectés (code ADM, moyenne générale et
    toutes les barres, semestre précédent validé);</li>
    <li>le semestre précédent, s'il y en a un, doit avoir été validé;</li>
    <li>les décisions du semestre précédent ne seront pas modifiées;</li>
    <li>l'assiduité n'est <b>pas</b> prise en compte;</li>
    <li>les étudiants avec des notes en attente sont ignorés.</li>
    </ul>
    <p>Il est donc vivement conseillé de relire soigneusement les décisions à l'issue
    de cette procédure !</p>
    <form action="do_formsemestre_validation_auto">
    <input type="hidden" name="formsemestre_id" value="%s"/>
    <input type="submit" value="Calculer automatiquement ces décisions"/>
    <p><em>Le calcul prend quelques minutes, soyez patients !</em></p>
    </form>
    """  % formsemestre_id,
          context.sco_footer(REQUEST)
          ]
    return '\n'.join(H)

def do_formsemestre_validation_auto(context, formsemestre_id, REQUEST):
    "Saisie automatisee des decisions d'un semestre"
    sem= context.get_formsemestre(formsemestre_id)
    next_semestre_id = sem['semestre_id'] + 1
    nt = context._getNotesCache().get_NotesTable(context, formsemestre_id) #> get_etudids, get_etud_decision_sem, 
    etudids = nt.get_etudids()
    nb_valid = 0
    conflicts = [] # liste des etudiants avec decision differente déjà saisie
    for etudid in etudids:
        etud = context.getEtudInfo(etudid=etudid, filled=True)[0]
        Se = sco_parcours_dut.SituationEtudParcours(context, etud, formsemestre_id)
        ins = context.do_formsemestre_inscription_list({'etudid':etudid, 'formsemestre_id' : formsemestre_id})[0]
        
        # Conditions pour validation automatique:
        if ins['etat'] == 'I' and ( ((not Se.prev) or (Se.prev_decision and Se.prev_decision['code'] in ('ADM','ADC','ADJ')))
             and Se.barre_moy_ok and Se.barres_ue_ok and not nt.etud_has_notes_attente(etudid)):
            # check: s'il existe une decision ou autorisation et quelle sont differentes,
            # warning (et ne fait rien)
            decision_sem = nt.get_etud_decision_sem(etudid)
            ok = True
            if decision_sem and decision_sem['code'] != 'ADM':
                ok = False
                conflicts.append(etud)
            autorisations = sco_parcours_dut.formsemestre_get_autorisation_inscription(
                context, etudid, formsemestre_id)
            if len(autorisations) != 0: # accepte le cas ou il n'y a pas d'autorisation : BUG 23/6/7, A RETIRER ENSUITE
                if len(autorisations) != 1 or autorisations[0]['semestre_id'] != next_semestre_id:
                    if ok:
                        conflicts.append(etud)
                        ok = False
                
            # ok, valide !
            if ok:
                formsemestre_validation_etud_manu(context, formsemestre_id, etudid,
                                                  code_etat='ADM',
                                                  devenir = 'NEXT',
                                                  assidu = True,
                                                  REQUEST=REQUEST, redirect=False)
                nb_valid += 1
    log('do_formsemestre_validation_auto: %d validations, %d conflicts' % (nb_valid, len(conflicts)))
    H = [ context.sco_header(REQUEST, page_title='Saisie automatique') ]
    H.append("""<h2>Saisie automatique des décisions du semestre %s</h2>
    <p>Opération effectuée.</p>
    <p>%d étudiants validés (sur %s)</p>""" % (sem['titreannee'], nb_valid, len(etudids)))
    if conflicts:
        H.append("""<p><b>Attention:</b> %d étudiants non modifiés car décisions différentes
        déja saisies :<ul>""" % len(conflicts))
        for etud in conflicts:
            H.append('<li><a href="formsemestre_validation_etud_form?formsemestre_id=%s&amp;etudid=%s&amp;check=1">%s</li>'
                     % (formsemestre_id, etud['etudid'], etud['nomprenom']) )
        H.append('</ul>')
    H.append('<a href="formsemestre_recapcomplet?formsemestre_id=%s&amp;modejury=1&amp;hidemodules=1">continuer</a>'
             % formsemestre_id)
    H.append(context.sco_footer(REQUEST))
    return '\n'.join(H)
    

def formsemestre_fix_validation_ues(context, formsemestre_id, REQUEST=None):
    """
    Suite à un bug (fix svn 502, 26 juin 2008), les UE sans notes ont parfois été validées
    avec un code ADM (au lieu de AJ ou ADC, suivant le code semestre).

    Cette fonction vérifie les codes d'UE et les modifie si nécessaire.

    Si semestre validé: decision UE == CMP ou ADM
    Sinon: si moy UE > barre et assiduité au semestre: ADM, sinon AJ


    N'affecte que le semestre indiqué, pas les précédents.
    """
    from sco_codes_parcours import *
    sem= context.get_formsemestre(formsemestre_id)
    nt = context._getNotesCache().get_NotesTable(context, formsemestre_id) #> get_etudids, get_etud_decision_sem, get_ues, get_etud_decision_ues, get_etud_ue_status
    etudids = nt.get_etudids()
    modifs = [] # liste d'étudiants modifiés
    cnx = context.GetDBConnexion(autocommit=False)
    for etudid in etudids:
        etud = context.getEtudInfo(etudid=etudid, filled=True)[0]
        Se = sco_parcours_dut.SituationEtudParcours(context, etud, formsemestre_id)
        ins = context.do_formsemestre_inscription_list({'etudid':etudid, 'formsemestre_id' : formsemestre_id})[0]
        decision_sem = nt.get_etud_decision_sem(etudid)
        if not decision_sem:
            continue # pas encore de decision semestre
        valid_semestre = CODES_SEM_VALIDES.get(decision_sem['code'], False)
        ue_ids = [ x['ue_id'] for x in nt.get_ues(etudid=etudid, filter_sport=True) ]
        for ue_id in ue_ids:
            existing_code = nt.get_etud_decision_ues(etudid)[ue_id]['code']
            if existing_code == None:
                continue # pas encore de decision UE
            ue_status = nt.get_etud_ue_status(etudid, ue_id)
            moy_ue = ue_status['moy']
            if valid_semestre:
                if type(moy_ue) == FloatType and ue_status['moy'] >= nt.parcours.NOTES_BARRE_VALID_UE:
                    code_ue = ADM
                else:
                    code_ue = CMP
            else:
                if not decision_sem['assidu']:
                    code_ue = AJ
                elif type(moy_ue) == FloatType and ue_status['moy'] >= nt.parcours.NOTES_BARRE_VALID_UE:
                    code_ue = ADM
                else:
                    code_ue = AJ

            if code_ue != existing_code:
                msg = ('%s: %s: code %s changé en %s' %
                       (etud['nomprenom'],ue_id, existing_code, code_ue) )
                modifs.append(msg)
                log(msg)
                sco_parcours_dut.do_formsemestre_validate_ue(cnx, nt, formsemestre_id, etudid, ue_id, code_ue)
    cnx.commit()
    #
    H = [context.sco_header(REQUEST, page_title='Réparation des codes UE'),
         sco_formsemestre_status.formsemestre_status_head(context, REQUEST=REQUEST,
                                                          formsemestre_id=formsemestre_id )
         ]
    if modifs:
        H = H + [ '<h2>Modifications des codes UE</h2>', '<ul><li>',
                  '</li><li>'.join(modifs), '</li></ul>' ]
        context._inval_cache(formsemestre_id=formsemestre_id) #> modif decision UE
    else:
        H.append('<h2>Aucune modification: codes UE corrects ou inexistants</h2>')
    H.append(context.sco_footer(REQUEST))
    return '\n'.join(H)


def formsemestre_validation_suppress_etud(context, formsemestre_id, etudid):
    """Suppression des decisions de jury pour un etudiant.
    """
    log('formsemestre_validation_suppress_etud( %s, %s)' % (formsemestre_id, etudid))
    cnx = context.GetDBConnexion(autocommit=False)
    cursor = cnx.cursor(cursor_factory=ScoDocCursor)
    args = { 'formsemestre_id' : formsemestre_id, 'etudid' : etudid }
    try:
        # -- Validation du semestre et des UEs
        cursor.execute("""delete from scolar_formsemestre_validation
        where etudid = %(etudid)s and formsemestre_id=%(formsemestre_id)s""", args )
        # -- Autorisations d'inscription
        cursor.execute("""delete from scolar_autorisation_inscription
        where etudid = %(etudid)s and origin_formsemestre_id=%(formsemestre_id)s""", args )
        cnx.commit()
    except:
        cnx.rollback()
        raise
    
    sem = context.get_formsemestre(formsemestre_id)
    _invalidate_etud_formation_caches(context, etudid, sem['formation_id'])  #> suppr. decision jury (peut affecter de plusieurs semestres utilisant UE capitalisée)

def formsemestre_validate_previous_ue(context, formsemestre_id, etudid, REQUEST=None):
    """Form. saisie UE validée hors ScoDoc 
    (pour étudiants arrivant avec un UE antérieurement validée).
    """
    etud = context.getEtudInfo(etudid=etudid, filled=True)[0]
    sem = context.get_formsemestre(formsemestre_id)
    Fo = context.formation_list( args={ 'formation_id' : sem['formation_id'] } )[0]
    
    H = [ context.sco_header(REQUEST, page_title="Validation UE",
                             init_jquery_ui=True,
                             javascripts=[ 'js/validate_previous_ue.js'
                                           ]),
          '<table style="width: 100%"><tr><td>',
          '''<h2 class="formsemestre">%s: validation d'une UE antérieure</h2>''' % etud['nomprenom'],
          ('</td><td style="text-align: right;"><a href="%s/ficheEtud?etudid=%s">%s</a></td></tr></table>'
           % (context.ScoURL(), etudid,    
              sco_photos.etud_photo_html(context, etud, title='fiche de %s'%etud['nom'], REQUEST=REQUEST))),
          '''<p class="help">Utiliser cette page pour enregistrer une UE validée antérieurement, 
    <em>dans un semestre hors ScoDoc</em>. Les UE validées dans ScoDoc sont déjà
    automatiquement prises en compte. Cette page n'est utile que pour les étudiants ayant 
    suivi un début de cursus dans un autre établissement, ou dans un semestre géré sans 
    ScoDoc. Notez que l'UE est validée, avec enregistrement immédiat de la décision et 
    l'attribution des ECTS.</p>''',
          '<p>On ne peut prendre en compte ici que les UE du cursus <b>%(titre)s</b></p>' % Fo,
          ]
    
    # Toutes les UE de cette formation sont présentées (même celles des autres semestres)
    ues = context.do_ue_list({ 'formation_id' : Fo['formation_id'] })
    ue_names = ['Choisir...'] + [ '%(acronyme)s %(titre)s' % ue for ue in ues ]
    ue_ids = [''] + [ ue['ue_id'] for ue in ues ]
    tf = TrivialFormulator(REQUEST.URL0, REQUEST.form, (
            ('etudid', { 'input_type' : 'hidden' }),
            ('formsemestre_id', { 'input_type' : 'hidden' }),
            ('ue_id', { 'input_type' : 'menu',
                        'title' : 'Unité d\'Enseignement (UE)',
                        'allow_null' : False,
                        'allowed_values': ue_ids,
                        'labels' : ue_names }),
            ('semestre_id', { 'input_type' : 'menu',
                              'title' : 'Indice du semestre',
                              'explanation' : 'Facultatif: indice du semestre dans la formation',
                              'allow_null' : True,
                              'allowed_values': [''] + [ str(x) for x in range(11) ],
                              'labels' : ['-']+range(11) }),
            ('date', { 'input_type' : 'date', 'size' : 9, 'explanation' : 'j/m/a',
                       'default' : time.strftime('%d/%m/%Y')}),
            ('moy_ue', { 'type' : 'float', 
                         'allow_null' : False,
                         'min_value' : 0,
                         'max_value' : 20,
                         'title' : 'Moyenne (/20) obtenue dans cette UE:' }),
            ),
                           cancelbutton = 'Annuler',
                           submitlabel = "Enregistrer validation d'UE",
                           )
    if tf[0] == 0:
        X = """
           <div id="ue_list_etud_validations"><!-- filled by get_etud_ue_cap_html --></div>
           <div id="ue_list_code"><!-- filled by ue_sharing_code --></div>
        """
        warn, ue_multiples = check_formation_ues(context, Fo['formation_id'])
        return '\n'.join(H) + tf[1] + X + warn + context.sco_footer(REQUEST)
    elif tf[0] == -1:
        return REQUEST.RESPONSE.redirect( context.ScoURL()+'/Notes/formsemestre_status?formsemestre_id='+formsemestre_id )
    else:
        if tf[2]['semestre_id']:
            semestre_id = int(tf[2]['semestre_id'])
        else:
            semestre_id = None
        do_formsemestre_validate_previous_ue(context, formsemestre_id, etudid, 
                                             tf[2]['ue_id'], tf[2]['moy_ue'], tf[2]['date'],
                                             semestre_id=semestre_id,
                                             REQUEST=REQUEST)
        return REQUEST.RESPONSE.redirect( context.ScoURL()+"/Notes/formsemestre_bulletinetud?formsemestre_id=%s&amp;etudid=%s&amp;head_message=Validation%%20d'UE%%20enregistree" % (formsemestre_id, etudid))

def do_formsemestre_validate_previous_ue(context, formsemestre_id, etudid, ue_id, moy_ue, date,
                                         semestre_id=None,
                                         REQUEST=None):
    """Enregistre validation d'UE (obtenue hors ScoDoc)"""
    sem = context.get_formsemestre(formsemestre_id)
    cnx = context.GetDBConnexion(autocommit=False)
    nt = context._getNotesCache().get_NotesTable(context, formsemestre_id ) #> get_etud_ue_status

    sco_parcours_dut.do_formsemestre_validate_ue(
        cnx, nt, 
        formsemestre_id, # "importe" cette UE dans le semestre (new 3/2015)
        etudid, ue_id, 'ADM', moy_ue=moy_ue, date=date, semestre_id=semestre_id,
        is_external=1
        )

    logdb(REQUEST, cnx, method='formsemestre_validate_previous_ue',
          etudid=etudid, msg='Validation UE %s' % ue_id, commit=False)
    _invalidate_etud_formation_caches(context, etudid, sem['formation_id'])
    cnx.commit()

def _invalidate_etud_formation_caches(context, etudid, formation_id):
    "Invalide tous les semestres de cette formation où l'etudiant est inscrit..."
    r = SimpleDictFetch(context, """SELECT sem.* 
        FROM notes_formsemestre sem, notes_formsemestre_inscription i
        WHERE sem.formation_id = %(formation_id)s
        AND i.formsemestre_id = sem.formsemestre_id 
        AND i.etudid = %(etudid)s
        """, { 'etudid' : etudid, 'formation_id' : formation_id } )
    for fsid in [ s['formsemestre_id'] for s in r ]:
        context._inval_cache(formsemestre_id=fsid) #> modif decision UE (inval tous semestres avec cet etudiant, ok mais conservatif)


def get_etud_ue_cap_html(context, etudid, formsemestre_id, ue_id, REQUEST=None):
    """Ramene bout de HTML pour pouvoir supprimer une validation de cette UE
    """
    valids = SimpleDictFetch(context, """SELECT SFV.* FROM scolar_formsemestre_validation SFV
        WHERE ue_id=%(ue_id)s AND etudid=%(etudid)s""", { 'etudid' : etudid, 'ue_id' : ue_id })
    if not valids:
        return ''
    H = [ '<div class="existing_valids"><span>Validations existantes pour cette UE:</span><ul>' ]
    for valid in valids:
        valid['event_date'] = DateISOtoDMY(valid['event_date'])
        if valid['moy_ue'] != None:
            valid['m'] = ', moyenne %(moy_ue)g/20' % valid
        else:
            valid['m'] = ''
        if valid['formsemestre_id']:
            sem = context.get_formsemestre(valid['formsemestre_id'])
            valid['s'] = ', du semestre %s' % sem['titreannee']
        else:
            valid['s'] = " enregistrée d'un parcours antérieur (hors ScoDoc)"
        if valid['semestre_id']:
            valid['s'] += ' (<b>S%d</b>)' % valid['semestre_id']
        valid['ds'] = formsemestre_id
        H.append('<li>%(code)s%(m)s%(s)s, le %(event_date)s  <a class="stdlink" href="etud_ue_suppress_validation?etudid=%(etudid)s&amp;ue_id=%(ue_id)s&amp;formsemestre_id=%(ds)s" title="supprime cette validation">effacer</a></li>' % valid )
    H.append('</ul></div>')
    return '\n'.join(H)

def etud_ue_suppress_validation(context, etudid, formsemestre_id, ue_id, REQUEST=None):
    """Suppress a validation (ue_id, etudid) and redirect to formsemestre"""
    log('etud_ue_suppress_validation( %s, %s, %s)' % (etudid, formsemestre_id, ue_id))
    cnx = context.GetDBConnexion()
    cursor = cnx.cursor(cursor_factory=ScoDocCursor)
    cursor.execute("DELETE FROM scolar_formsemestre_validation WHERE etudid=%(etudid)s and ue_id=%(ue_id)s", 
                   { 'etudid' : etudid, 'ue_id' : ue_id } )
    
    sem = context.get_formsemestre(formsemestre_id)
    _invalidate_etud_formation_caches(context, etudid, sem['formation_id'])
    
    return REQUEST.RESPONSE.redirect( context.ScoURL()+"/Notes/formsemestre_validate_previous_ue?etudid=%s&amp;formsemestre_id=%s" % (etudid, formsemestre_id))

def check_formation_ues(context, formation_id):
    """Verifie que les UE d'une formation sont chacune utilisée dans un seul semestre_id
    Si ce n'est pas le cas, c'est probablement (mais pas forcément) une erreur de
    définition du programme: cette fonction retourne un bout de HTML
    à afficher pour prévenir l'utilisateur, ou '' si tout est ok.
    """
    ues = context.do_ue_list({ 'formation_id' : formation_id })
    ue_multiples = {} # { ue_id : [ liste des formsemestre ] }
    for ue in ues:
        # formsemestres utilisant cette ue ?
        sems = SimpleDictFetch(context, """SELECT DISTINCT sem.* 
             FROM notes_formsemestre sem, notes_modules mod, notes_moduleimpl mi
             WHERE sem.formation_id = %(formation_id)s
             AND mod.module_id = mi.module_id
             AND mi.formsemestre_id = sem.formsemestre_id
             AND mod.ue_id = %(ue_id)s""",
                            {'ue_id' : ue['ue_id'], 'formation_id' : formation_id })
        semestre_ids = set( [ x['semestre_id'] for x in sems ])
        if len(semestre_ids) > 1: # plusieurs semestres d'indices differents dans le cursus
            ue_multiples[ue['ue_id']] = sems
    
    if not ue_multiples:
        return '', {}
    # Genere message HTML:
    H = [ """<div class="ue_warning"><span>Attention:</span> les UE suivantes de cette formation 
        sont utilisées dans des
        semestres de rangs différents (eg S1 et S3). <br/>Cela peut engendrer des problèmes pour 
        la capitalisation des UE. Il serait préférable d'essayer de rectifier cette situation: 
        soit modifier le programme de la formation (définir des UE dans chaque semestre), 
        soit veiller à saisir le bon indice de semestre dans le menu lors de la validation d'une
        UE extérieure.
        <ul>
        """ ]
    for ue in ues:
        if ue['ue_id'] in ue_multiples:
            sems = [ context.get_formsemestre(x['formsemestre_id']) for x in ue_multiples[ue['ue_id']]]
            slist = ', '.join([ '%(titreannee)s (<em>semestre %(semestre_id)s</em>)' % s for s in sems ])
            H.append('<li><b>%s</b> : %s</li>' % (ue['acronyme'], slist))
    H.append( "</ul></div>" )

    return '\n'.join(H), ue_multiples
