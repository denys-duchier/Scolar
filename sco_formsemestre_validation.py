# -*- mode: python -*-
# -*- coding: iso8859-15 -*-

##############################################################################
#
# Gestion scolarite IUT
#
# Copyright (c) 2001 - 2006 Emmanuel Viennet.  All rights reserved.
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
    nt = context._getNotesCache().get_NotesTable(context, formsemestre_id)
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
                             javascripts=['jQuery/jquery.js', 'js/recap_parcours.js']
                             ) ]

    H.append('<table style="width: 100%"><tr><td>')
    if not check:
        H.append('<h2 class="formsemestre">%s: validation du semestre</h2>' % (etud['nomprenom']))
    else:
        H.append('<h2 class="formsemestre">Parcours de %s</h2>' % (etud['nomprenom']) )
    
    H.append('</td><td style="text-align: right;"><a href="%s/ficheEtud?etudid=%s">%s</a></td></tr></table>'
             % (context.ScoURL(), etudid,    
                sco_photos.etud_photo_html(context, etud, title='fiche de %s'%etud['nom'], REQUEST=REQUEST)))
    
    H.append( formsemestre_recap_parcours_table(context, Se, etudid, check and not readonly) )
    if check:
        if not desturl:
            desturl = 'formsemestre_recapcomplet?modejury=1&hidemodules=1&formsemestre_id='+formsemestre_id
            if sortcol:
                desturl += '&sortcol=' + sortcol # pour refaire tri sorttable du tableau de notes
            desturl += '#etudid%s' % etudid # va a la bonne ligne
        H.append('<ul><li><a href="%s">Continuer</a></li>' % desturl)
        if etud_index_prev != None:
            etud = context.getEtudInfo(etudid=T[etud_index_prev][-1], filled=True)[0]
            H.append("""<li><a href="formsemestre_validation_etud_form?formsemestre_id=%s&etud_index=%s">Traiter l'étudiant précédent (%s)</a></li>""" % (formsemestre_id,etud_index_prev, etud['nomprenom']) )
        if etud_index_next != None:
            etud = context.getEtudInfo(etudid=T[etud_index_next][-1], filled=True)[0]
            H.append("""<li><a href="formsemestre_validation_etud_form?formsemestre_id=%s&etud_index=%s">Traiter l'étudiant suivant (%s)</a></li>""" % (formsemestre_id,etud_index_next, etud['nomprenom']) )
        H.append('</ul>')
        H.append(context.sco_footer(REQUEST))
        return '\n'.join(H)

    decision_jury = Se.nt.get_etud_decision_sem(etudid)
    
    # Infos si pas de semestre précédent
    if not Se.prev:
        if Se.sem['semestre_id'] == 1:
            H.append('<p>Premier semestre (pas de précédent)</p>')
        else:
            H.append('<p>Pas de semestre précédent !</p>')
    else:
        if not Se.prev_decision:
            H.append(tf_error_message("""Le jury n\'a pas statué sur le semestre précédent ! (<a href="formsemestre_validation_etud_form?formsemestre_id=%s&etudid=%s">le faire maintenant</a>)""" % (Se.prev['formsemestre_id'], etudid)))
            if decision_jury:
                H.append('<a href="formsemestre_validation_suppress_etud?etudid=%s&formsemestre_id=%s" class="stdlink">Supprimer décision existante</a>'% (etudid, formsemestre_id))
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
        <input type="hidden" name="desturl" value="formsemestre_validation_etud_form?etudid=%s&formsemestre_id=%s"/>
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
        H.append('<b>%d UE sous la barre</b> (%g/20)' % (Se.nb_ues_under, NOTES_BARRE_UE))
    if (not Se.barre_moy_ok) and Se.can_compensate_with_prev:
        H.append(', et ce semestre peut se <b>compenser</b> avec le précédent')
    H.append('.</p>')
        
    # Décisions possibles
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
    H.append(decisions_possible_rows(Se, True, subtitle='Etudiant assidu:', trclass='sfv_ass'))
    
    rows_pb_assiduite = decisions_possible_rows(Se, False,
                                                subtitle='Si problème d\'assiduité:',
                                                trclass='sfv_pbass')
    if rows_pb_assiduite:
        H.append('<tr><td>&nbsp;</td></tr>') # spacer
        H.append(rows_pb_assiduite)

    H.append('</table>')    
    H.append('<p><br/></p><input type="submit" value="Valider ce choix" disabled="1" id="subut"/>')
    H.append('</form>')

    H.append( form_decision_manuelle(context, Se, formsemestre_id, etudid) )

    H.append('<p style="font-size: 50%;">Formation ' )
    if Se.sem['gestion_semestrielle'] == '1':
        H.append('avec semestres décalés</p>' )
    else:
        H.append('sans semestres décalés</p>' )

    # navigation suivant/precedent
    H.append('<p>')
    if etud_index_prev != None:
        etud = context.getEtudInfo(etudid=T[etud_index_prev][-1], filled=True)[0]
        H.append('<span><a href="formsemestre_validation_etud_form?formsemestre_id=%s&etud_index=%s">Etud. précédent (%s)</a></span>' % (formsemestre_id,etud_index_prev, etud['nomprenom']) )
    if etud_index_next != None:
        etud = context.getEtudInfo(etudid=T[etud_index_next][-1], filled=True)[0]
        H.append('<span style="padding-left: 50px;"><a href="formsemestre_validation_etud_form?formsemestre_id=%s&etud_index=%s">Etud. suivant (%s)</a></span>' % (formsemestre_id,etud_index_next, etud['nomprenom']) )
    H.append('</p>')
    H.append(context.sco_footer(REQUEST))
    return '\n'.join(H)

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
    adr = 'formsemestre_validation_etud_form?formsemestre_id=%s&etudid=%s&check=1' % (formsemestre_id, etudid)
    if sortcol:
        adr += '&sortcol=' + sortcol
    if desturl:
        desturl += '&desturl=' + desturl
    REQUEST.RESPONSE.redirect(adr)
    # Si le precedent a été modifié, demande relecture du parcours.
    # sinon  renvoie au listing general,
#     if choice.new_code_prev:
#         REQUEST.RESPONSE.redirect( 'formsemestre_validation_etud_form?formsemestre_id=%s&etudid=%s&check=1&desturl=%s' % (formsemestre_id, etudid, desturl) )
#     else:
#         if not desturl:
#             desturl = 'formsemestre_recapcomplet?modejury=1&hidemodules=1&formsemestre_id=' + formsemestre_id          
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
            TitlePrev = 'S%d' % Se.prev['semestre_id']
        else:
            TitlePrev = 'Prec.'

    if Se.sem['semestre_id'] >= 0:
        TitleCur = 'S%d' % Se.sem['semestre_id']
    else:
        TitleCur = 'Sem'
    
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
    linktmpl  = '<span onclick="toggle_vis(this);" class="toggle_sem">%s</span>'
    minuslink = linktmpl % context.icons.minus_img.tag(border="0", alt="-")
    pluslink  = linktmpl % context.icons.plus_img.tag(border="0", alt="+")
    if show_details:
        sd = ' recap_show_details'
        plusminus = minuslink
    else:
        sd = ' recap_hide_details'
        plusminus = pluslink
    H.append( '<table class="recap_parcours%s"><tr>' % sd )
    H.append('<th><span onclick="toggle_all_sems(this);" title="Ouvrir/fermer tous les semestres">+</span></th><th></th><th>Semestre</th>')
    if with_all_columns:
        H.append('<th>Assidu</th>')
    H.append('<th>Etat</th><th>Abs</th><th>Moy.</th>')
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

        nt = context._getNotesCache().get_NotesTable(context, sem['formsemestre_id'] )
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
        # 1ere ligne: titre sem, acronymes UE
        H.append('<tr class="%s rcp_l1">' % class_sem)
        if is_cur:
            pm = ''
        elif is_prev:
            pm = minuslink
        else:
            pm = plusminus
        H.append('<td class="rcp_type_sem" style="background-color:%s;">%s%s</td>'
                 % (bgcolor, num_sem, pm) )
        H.append('<td class="datedebut">%(mois_debut)s</td>' % sem )
        H.append('<td><a class="formsemestre_status_link" href="%sformsemestre_bulletinetud?formsemestre_id=%s&etudid=%s" title="Bulletin de notes">%s</a></td>' % (a_url,sem['formsemestre_id'], etudid,sem['titreannee']))
        if with_all_columns:
            nc = 4
        else:
            nc = 3
        H.append('<td></td>'*nc) # [assidu,] etat, abs, moy
        # acronymes UEs
        ues = nt.get_ues(filter_sport=True) 
        for ue in ues:
            H.append('<td class="ue_acro"><span>%s</span></td>' % ue['acronyme'])
        if len(ues) < Se.nb_max_ue:
            H.append('<td colspan="%d"></td>' % (Se.nb_max_ue - len(ues)))
        if with_links:
            H.append('<td></td>')
        H.append('<td></td></tr>')
        # 2eme ligne: etat et notes
        H.append('<tr class="%s rcp_l2">' % class_sem)
        H.append('<td class="rcp_type_sem" style="background-color:%s;">&nbsp;</td>'
                 % (bgcolor) )
        if is_prev:
            default_sem_info = '<span class="fontred">[sem. précédent]</span>'
        else:
            default_sem_info = ''
        if sem['etat'] != '1': # locked
            lockicon = context.icons.lock32_img.tag(title="verrouillé", border='0')
            default_sem_info += lockicon
        H.append('<td class="datefin">%s</td><td>%s</td>'
                 % (sem['mois_fin'], 
                    sem_info.get(sem['formsemestre_id'], default_sem_info)))
        if decision_sem:
            if with_all_columns:
                ass = {0:'non',1:'oui', None:'-', '':'-'}[decision_sem['assidu']]
                H.append('<td>%s</td>' % ass)
            H.append('<td>%s</td>' % decision_sem['code'])
        else:
            if with_all_columns:
                nc = 2
            else:
                nc = 1
            H.append('<td colspan="%d"><em>pas de décision</em></td>'%nc)
        # Absences (nb d'abs non just. dans ce semestre)
        debut_sem = DateDMYtoISO(sem['date_debut'])
        fin_sem = DateDMYtoISO(sem['date_fin'])
        nbabs = context.Absences.CountAbs(etudid=etudid, debut=debut_sem, fin=fin_sem)
        nbabsjust = context.Absences.CountAbsJust(etudid=etudid,
                                                 debut=debut_sem,fin=fin_sem)
        H.append('<td class="rcp_abs">%d</td>' % (nbabs-nbabsjust) )
        # Moy Gen
        H.append('<td class="rcp_moy">%s</td>' % notes_table.fmt_note( nt.get_etud_moy_gen(etudid)) )
        # UEs
        for ue in ues:            
            if decisions_ue and decisions_ue.has_key(ue['ue_id']):
                code = decisions_ue[ue['ue_id']]['code']
            else:
                code = ''
            ue_status = nt.get_etud_ue_status(etudid, ue['ue_id'])
            moy_ue = ue_status['moy_ue']
            if code == 'ADM':
                class_ue = 'ue_adm'
            elif code == 'CMP':
                class_ue = 'ue_cmp'
            else:
                class_ue = 'ue'
            H.append('<td class="%s">%s</td>' % (class_ue, notes_table.fmt_note(moy_ue)) )
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
            H.append('<td><a href="%sformsemestre_validation_etud_form?formsemestre_id=%s&etudid=%s">modifier</a></td>' % (a_url,sem['formsemestre_id'],etudid))

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
        allowed_codes = sco_codes_parcours.DEVENIRS_STD

    H.append('<tr><td>Devenir: </td><td><select name="devenir"><option value="" selected>Choisir...</option>')
    for cod in codes:
        if Se.sem['gestion_semestrielle'] == '1' or allowed_codes.has_key(cod):
            H.append('<option value="%s">%s</option>' % (cod, Se.explique_devenir(cod)))
    H.append('</select></td></tr>')

    H.append('<tr><td><input type="checkbox" name="assidu" checked="checked">assidu</input></td></tr>')
    
    H.append("""</table>
    <input type="submit" value="Valider décision manuelle"/>
    <span style="padding-left: 5em;"><a href="formsemestre_validation_suppress_etud?etudid=%s&formsemestre_id=%s" class="stdlink">Supprimer décision existante</a></span>
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
    nt = context._getNotesCache().get_NotesTable(context, formsemestre_id)
    etudids = nt.get_etudids()
    nb_valid = 0
    conflicts = [] # liste des etudiants avec decision differente déjà saisie
    for etudid in etudids:
        etud = context.getEtudInfo(etudid=etudid, filled=True)[0]
        Se = sco_parcours_dut.SituationEtudParcours(context, etud, formsemestre_id)
        ins = context.do_formsemestre_inscription_list({'etudid':etudid, 'formsemestre_id' : formsemestre_id})[0]
        
        # Conditions pour validation automatique:
        if ins['etat'] == 'I' and ( ((not Se.prev) or (Se.prev_decision and Se.prev_decision['code'] in ('ADM','ADC','ADJ')))
             and Se.barre_moy_ok and Se.barres_ue_ok ):
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
            H.append('<li><a href="formsemestre_validation_etud_form?formsemestre_id=%s&etudid=%s&check=1">%s</li>'
                     % (formsemestre_id, etud['etudid'], etud['nomprenom']) )
        H.append('</ul>')
    H.append('<a href="formsemestre_recapcomplet?formsemestre_id=%s&modejury=1&hidemodules=1">continuer</a>'
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
    nt = context._getNotesCache().get_NotesTable(context, formsemestre_id)
    etudids = nt.get_etudids()
    modifs = [] # liste d'étudiants modifiés
    cnx = context.GetDBConnexion()
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
            moy_ue = ue_status['moy_ue']
            if valid_semestre:
                if type(moy_ue) == FloatType and ue_status['moy_ue'] >= NOTES_BARRE_VALID_UE:
                    code_ue = ADM
                else:
                    code_ue = CMP
            else:
                if not decision_sem['assidu']:
                    code_ue = AJ
                elif type(moy_ue) == FloatType and ue_status['moy_ue'] >= NOTES_BARRE_VALID_UE:
                    code_ue = ADM
                else:
                    code_ue = AJ

            if code_ue != existing_code:
                msg = ('%s: %s: code %s changé en %s' %
                       (etud['nomprenom'],ue_id, existing_code, code_ue) )
                modifs.append(msg)
                log(msg)
                sco_parcours_dut.do_formsemestre_validate_ue(cnx, nt, formsemestre_id, etudid, ue_id, code_ue)
    #
    H = [context.sco_header(REQUEST, page_title='Réparation des codes UE'),
         context.formsemestre_status_head(context, REQUEST=REQUEST,
                                          formsemestre_id=formsemestre_id )
         ]
    if modifs:
        H = H + [ '<h2>Modifications des codes UE</h2>', '<ul><li>',
                  '</li><li>'.join(modifs), '</li></ul>' ]
        context._inval_cache(formsemestre_id=formsemestre_id)
    else:
        H.append('<h2>Aucune modification: codes UE corrects ou inexistants</h2>')
    H.append(context.sco_footer(REQUEST))
    return '\n'.join(H)


def formsemestre_validation_suppress_etud(context, formsemestre_id, etudid):
    """Suppression des decisions de jury pour un etudiant.
    """
    cnx = context.GetDBConnexion()
    cursor = cnx.cursor()
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
    context._inval_cache(formsemestre_id=formsemestre_id)

def formsemestre_validate_previous_ue(context, formsemestre_id, etudid, REQUEST=None):
    """Form. saisie UE validée hors ScoDoc 
    (pour étudiants arrivant avec un UE antérieurement validée).
    """
    etud = context.getEtudInfo(etudid=etudid, filled=True)[0]
    sem = context.get_formsemestre(formsemestre_id)
    Fo = context.do_formation_list( args={ 'formation_id' : sem['formation_id'] } )[0]
    
    H = [ context.sco_header(REQUEST, page_title="Validation UE",
                             javascripts=[ 'jQuery/jquery.js', 
                                           'js/validate_previous_ue.js',
                                           'libjs/calendarDateInput.js']),
          '<table style="width: 100%"><tr><td>',
          '''<h2 class="formsemestre">%s: validation d'une UE antérieure</h2>''' % etud['nomprenom'],
          ('</td><td style="text-align: right;"><a href="%s/ficheEtud?etudid=%s">%s</a></td></tr></table>'
           % (context.ScoURL(), etudid,    
              sco_photos.etud_photo_html(context, etud, title='fiche de %s'%etud['nom'], REQUEST=REQUEST))),
          '''<p class="help">Utiliser cette page pour enregistrer une UE validée antérieurement, 
    <em>dans un semestres hors ScoDoc</em>. Les UE validées dans ScoDoc sont déjà
    automatiquement prises en compte. Cette page n'est utile que pour les étudiants ayant 
    suivi un début de cursus dans un autre établissement, ou dans un semestre géré sans 
    ScoDoc.</p>''',
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
            ('date', { 'input_type' : 'date', 'size' : 9,
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
           <div id="ue_list_etud_validations"></div>
           <div id="ue_list_code"></div>
        """
        warn, ue_multiples = check_formation_ues(context, Fo['formation_id'])
        return '\n'.join(H) + tf[1] + X + warn + context.sco_footer(REQUEST)
    elif tf[0] == -1:
        return REQUEST.RESPONSE.redirect( context.ScoURL()+'/Notes/formsemestre_status?formsemestre_id='+formsemestre_id )
    else:
        do_formsemestre_validate_previous_ue(context, formsemestre_id, etudid, 
                                             tf[2]['ue_id'], tf[2]['moy_ue'], tf[2]['date'],
                                             REQUEST=REQUEST)
        return REQUEST.RESPONSE.redirect( context.ScoURL()+"/Notes/formsemestre_bulletinetud?formsemestre_id=%s&etudid=%s&head_message=Validation%%20d'UE%%20enregistree" % (formsemestre_id, etudid))
    
def do_formsemestre_validate_previous_ue(context, formsemestre_id, etudid, ue_id, moy_ue, date,
                                         REQUEST=None):
    """Enregistre validation d'UE"""
    sem = context.get_formsemestre(formsemestre_id)
    cnx = context.GetDBConnexion()
    nt = context._getNotesCache().get_NotesTable(context, formsemestre_id )

    sco_parcours_dut.do_formsemestre_validate_ue(
        cnx, nt, None, etudid, ue_id, 'ADM', moy_ue=moy_ue, date=date)

    logdb(REQUEST, cnx, method='formsemestre_validate_previous_ue',
          etudid=etudid, msg='Validation UE %s' % ue_id)
    # Invalide tous les semestres de cette formation où l'etudiant est inscrit...
    r = SimpleDictFetch(context, """SELECT sem.* 
        FROM notes_formsemestre sem, notes_formsemestre_inscription i
        WHERE sem.formation_id = %(formation_id)s
        AND i.formsemestre_id = sem.formsemestre_id 
        AND i.etudid = %(etudid)s
        """, { 'etudid' : etudid, 'formation_id' : sem['formation_id'] } )
    for fsid in [ s['formsemestre_id'] for s in r ]:
        context._inval_cache(formsemestre_id=fsid)

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
        valid['ds'] = formsemestre_id
        H.append('<li>%(code)s%(m)s%(s)s, le %(event_date)s  <a class="stdlink" href="etud_ue_suppress_validation?etudid=%(etudid)s&ue_id=%(ue_id)s&formsemestre_id=%(ds)s" title="supprime cette validation">effacer</a></li>' % valid )
    H.append('</ul></div>')
    return '\n'.join(H)

def etud_ue_suppress_validation(context, etudid, formsemestre_id, ue_id, REQUEST=None):
    """Suppress a validation (ue_id, etudid) and redirect to formsemestre"""
    cnx = context.GetDBConnexion()
    cursor = cnx.cursor()
    cursor.execute("DELETE FROM scolar_formsemestre_validation WHERE etudid=%(etudid)s and ue_id=%(ue_id)s", 
                   { 'etudid' : etudid, 'ue_id' : ue_id } )
    return REQUEST.RESPONSE.redirect( context.ScoURL()+"/Notes/formsemestre_validate_previous_ue?etudid=%s&formsemestre_id=%s" % (etudid, formsemestre_id))

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
        la capitalisation des UE. Il serait préférable d'essayer de rectifier cette situation.
        <ul>
        """ ]
    for ue in ues:
        if ue['ue_id'] in ue_multiples:
            sems = [ context.get_formsemestre(x['formsemestre_id']) for x in ue_multiples[ue['ue_id']]]
            slist = ', '.join([ '%(titreannee)s (<em>semestre %(semestre_id)s</em>)' % s for s in sems ])
            H.append('<li><b>%s</b> : %s</li>' % (ue['acronyme'], slist))
    H.append( "</ul></div>" )

    return '\n'.join(H), ue_multiples
