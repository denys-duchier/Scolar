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
from notes_table import *
import notes_table

import sco_parcours_dut, sco_codes_parcours

    
# ------------------------------------------------------------------------------------
def formsemestre_validation_etud_form(
    znotes, # ZNotes instance
    formsemestre_id=None, # required
    etudid=None, # required
    check=0, # opt: si true, propose juste une relecture du parcours
    desturl=None,
    REQUEST=None):
    authuser = REQUEST.AUTHENTICATED_USER
    if not authuser.has_permission('ScoEtudInscrit', znotes):
        # simple read only version
        nomodif = True
        check = True
    else:
        nomodif = False
    etud = znotes.getEtudInfo(etudid=etudid, filled=True)[0]
    Se = sco_parcours_dut.SituationEtudParcours(znotes, etud, formsemestre_id)
    if Se.sem['etat'] != '1':
        pass # ? autoriser ou pas ? warning ?
        # raise ScoValueError('validation: semestre verrouille')
    
    H = [ znotes.sco_header(znotes,REQUEST, page_title='Parcours %(nomprenom)s' % etud) ]

    H.append('<table style="width: 100%"><tr><td>')
    if not check:
        H.append("<h2>%s: validation du semestre %s</h2>"
                 % (etud['nomprenom'], Se.sem['titre_num']))
    else:
        H.append("<h2>Parcours de %s</h2>" % (etud['nomprenom']) )
    
    H.append('</td><td style="text-align: right;"><a href="%s/ficheEtud?etudid=%s">%s</a></td></tr></table>'
             % (znotes.ScoURL(), etudid,
                znotes.etudfoto(etudid, foto=etud['foto'],
                                fototitle='fiche de %s'%etud['nom'])))
    H.append( formsemestre_recap_parcours_table(znotes, Se, etudid, check and not nomodif) )
    if check:
        if not desturl:
            desturl = 'formsemestre_recapcomplet?modejury=1&hidemodules=1&formsemestre_id=' + formsemestre_id     
        H.append('<p><a href="%s">Continuer</a>' % desturl)
        H.append(znotes.sco_footer(znotes, REQUEST))
        return '\n'.join(H)

    # Infos si pas de semestre pr�c�dent
    if not Se.prev:
        if Se.sem['semestre_id'] == 1:
            H.append('<p>Premier semestre (pas de pr�c�dent)</p>')
        else:
            H.append('<p>Pas de semestre pr�c�dent !</p>')
    else:
        if not Se.prev_decision:
            H.append('<ul class="tf-msg"><li class="tf-msg">Le jury n\'a pas statu� sur le semestre pr�c�dent ! (<a href="formsemestre_validation_etud_form?formsemestre_id=%s&etudid=%s">le faire maintenant</a>)</li></ul>' % (Se.prev['formsemestre_id'], etudid))
            H.append(znotes.sco_footer(znotes, REQUEST))
            return '\n'.join(H)

    # Infos sur decisions d�j� saisies
    decision_jury = Se.nt.get_etud_decision_sem(etudid)
    if decision_jury:
        if decision_jury['assidu']:
            ass = 'assidu'
        else:
            ass = 'non assidu'
        H.append('<p>D�cision existante du %(event_date)s: %(code)s' % decision_jury )
        H.append(' (%s)' % ass )
        auts = sco_parcours_dut.formsemestre_get_autorisation_inscription(
            znotes, etudid, formsemestre_id)
        if auts:
            H.append( '. Autoris� � s\'inscrire en ' )
            alist = []
            for aut in auts:
                alist.append (str(aut['semestre_id']))
            H.append( ', '.join( ['S%s' % x for x in alist ]) + '.')
        H.append( '</p>' )

    # Cas particulier pour ATJ: corriger precedent avant de continuer
    if Se.prev_decision and Se.prev_decision['code'] == 'ATJ':
        H.append("""<div class="sfv_warning"><p>La d�cision du semestre pr�c�dent est en
        <b>attente</b> � cause d\'un <b>probl�me d\'assiduit�<b>.</p>
        <p>Vous devez la corriger avant de continuer ce jury. Soit vous consid�rez que le
        probl�me d'assiuit� n'est pas r�gl� et choisissez de ne pas valider le semestre
        pr�c�dent (�chec), soit vous entrez une d�cision sans prendre en compte
        l'assiduit�.</p>
        <form method="get" action="formsemestre_validation_etud_form">
        <input type="submit" value="Statuer sur le semestre pr�c�dent"/>
        <input type="hidden" name="formsemestre_id" value="%s"/>
        <input type="hidden" name="etudid" value="%s"/>
        <input type="hidden" name="desturl" value="formsemestre_validation_etud_form?etudid=%s&formsemestre_id=%s"/>        
        </form>
        </div>
        """ % (Se.prev['formsemestre_id'], etudid, etudid, formsemestre_id))
        H.append(znotes.sco_footer(znotes, REQUEST))
        return '\n'.join(H)

    # Explication sur barres actuelles
    H.append('<p class="sfv_explication">L\'�tudiant ')
    if Se.barre_moy_ok:
        H.append('a la moyenne g�n�rale, ')
    else:
        H.append('<b>n\'a pas</b> la moyenne g�n�rale, ')
    if Se.barres_ue_ok:
        H.append('les UEs sont au dessus des barres')
    else:
        H.append('<b>%d UE sous la barre</b> (%g/20)' % (Se.nb_ues_under, NOTES_BARRE_UE))
    if (not Se.barre_moy_ok) and Se.can_compensate_with_prev:
        H.append(', et ce semestre peut se <b>compenser</b> avec le pr�c�dent')
    H.append('.</p>')
        
    # D�cisions possibles
    H.append("""<form method="get" action="formsemestre_validation_etud" id="formvalid" class="sfv_decisions">
    <input type="hidden" name="etudid" value="%s"/>
    <input type="hidden" name="formsemestre_id" value="%s"/>""" %
             (etudid, formsemestre_id) )
    if desturl:
        H.append('<input type="hidden" name="desturl" value="%s"/>' % desturl)
    H.append('<h3 class="sfv">D�cisions <em>recommand�es</em> :</h3>')
    H.append('<table>')
    H.append(decisions_possible_rows(Se, True, subtitle='Etudiant assidu:', trclass='sfv_ass'))
    
    rows_pb_assiduite = decisions_possible_rows(Se, False,
                                                subtitle='Si probl�me d\'assiduit�:',
                                                trclass='sfv_pbass')
    if rows_pb_assiduite:
        H.append('<tr><td>&nbsp;</td></tr>') # spacer
        H.append(rows_pb_assiduite)

    H.append('</table>')    
    H.append('<p><br/></p><input type="submit" value="Valider ce choix" disabled="1" id="subut"/>')
    H.append('</form>')

    H.append( form_decision_manuelle(znotes, Se, formsemestre_id, etudid) )

    H.append('<p style="font-size: 50%;">Formation ' )
    if Se.sem['gestion_semestrielle'] == '1':
        H.append('avec semestres d�cal�s</p>' )
    else:
        H.append('sans semestres d�cal�s</p>' )
    
    H.append(znotes.sco_footer(znotes, REQUEST))
    return '\n'.join(H)

def formsemestre_validation_etud(
    znotes, # ZNotes instance
    formsemestre_id=None, # required
    etudid=None, # required
    codechoice=None, # required
    desturl='',
    REQUEST=None):
    """Enregistre validation"""
    etud = znotes.getEtudInfo(etudid=etudid, filled=True)[0]
    Se = sco_parcours_dut.SituationEtudParcours(znotes, etud, formsemestre_id)
    # retrouve la decision correspondant au code:
    choices = Se.get_possible_choices(assiduite=True)
    choices += Se.get_possible_choices(assiduite=False)
    found=False
    for choice in choices:
        if choice.codechoice == codechoice:
            found=True
            break
    if not found:
        raise ScoValueError('code choix invalide ! (%s)' % codechoice)
    #
    Se.valide_decision(choice, REQUEST) # enregistre
    _do_valid_choice(formsemestre_id, etudid, Se, choice, desturl, REQUEST)

def formsemestre_validation_etud_manu(
    znotes, # ZNotes instance
    formsemestre_id=None, # required
    etudid=None, # required
    code_etat='', new_code_prev='', devenir='', # required (la decision manuelle)
    desturl='',
    REQUEST=None):
    """Enregistre validation"""
    etud = znotes.getEtudInfo(etudid=etudid, filled=True)[0]
    Se = sco_parcours_dut.SituationEtudParcours(znotes, etud, formsemestre_id)
    # Si code ADC, extrait le semestre utilis�:
    if code_etat[:3] == 'ADC':
        formsemestre_id_utilise_pour_compenser = code_etat.split('_')[1]
        code_etat = 'ADC'
    else:
        formsemestre_id_utilise_pour_compenser = None
    
    # Construit le choix correspondant:
    choice = sco_parcours_dut.DecisionSem(
        code_etat=code_etat, new_code_prev=new_code_prev, devenir=devenir,
        formsemestre_id_utilise_pour_compenser = formsemestre_id_utilise_pour_compenser)
    #
    Se.valide_decision(choice, REQUEST) # enregistre
    _do_valid_choice(formsemestre_id, etudid, Se, choice, desturl, REQUEST)


def _do_valid_choice(formsemestre_id, etudid, Se, choice, desturl, REQUEST):
    REQUEST.RESPONSE.redirect( 'formsemestre_validation_etud_form?formsemestre_id=%s&etudid=%s&check=1&desturl=%s' % (formsemestre_id, etudid, desturl) )
    # Si le precedent a �t� modifi�, demande relecture du parcours.
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
        TitlePrev = 'S%d' % Se.prev['semestre_id']
    TitleCur = 'S%d' % Se.sem['semestre_id']

    H = [ '<tr class="%s titles"><th class="sfv_subtitle">%s</em></th>' % (trclass, subtitle) ]
    if Se.prev:
        H.append('<th>Code %s</th>' % TitlePrev )
    H.append('<th>Code %s</th><th>Devenir</th></tr>' % TitleCur )
    for ch in choices:
        H.append("""<tr class="%s"><td><input type="radio" name="codechoice" value="%s" onClick="document.getElementById('subut').disabled=false;">"""
                 % (trclass, ch.codechoice) )
        H.append('%s </input></td>' % ch.explication)
        if Se.prev:
            H.append('<td class="centercell">%s</td>' % _dispcode(ch.new_code_prev) )
        H.append( '<td class="centercell">%s</td><td>%s</td>'
                 % (_dispcode(ch.code_etat), Se.explique_devenir(ch.devenir)))
        H.append('</tr>')

    return '\n'.join(H)


def formsemestre_recap_parcours_table( znotes, Se, etudid, with_links=False ):
    """Tableau HTML recap parcours
    Si with_links, ajoute liens pour modifier decisions    
    """
    H = []
    H.append('<table class="recap_parcours"><tr><th></th><th>Dates</th><th>Semestre</th><th>Assidu</th><th>Etat</th><th>Abs</th><th>Moy.</th>')
    # titres des UE
    H.append( '<th></th>' * Se.nb_max_ue )
    #
    if with_links:
        H.append('<th></th>')
    H.append('<th></th></tr>')
    for sem in Se.get_semestres():
        is_prev = Se.prev and (Se.prev['formsemestre_id'] == sem['formsemestre_id'])
        is_cur = (Se.formsemestre_id == sem['formsemestre_id'])        
        etat, decision_sem, decisions_ue = znotes._formsemestre_get_decision(
            etudid, sem['formsemestre_id'] )
        nt = znotes._getNotesCache().get_NotesTable(znotes, sem['formsemestre_id'] )
        if is_cur:
            type_sem = '*'
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
        H.append('<tr class="%s rcp_l1"><td class="rcp_type_sem" style="background-color:%s;">%s</td>'
                 % (class_sem, bgcolor, type_sem) )
        H.append('<td>%(mois_debut)s</td>' % sem )
        H.append('<td><a class="formsemestre_status_link" href="formsemestre_bulletinetud?formsemestre_id=%s&etudid=%s">%s</a></td>' % (sem['formsemestre_id'], etudid,sem['titre_num']))
        H.append('<td></td>'*4) # assidu, etat, abs, moy
        # acronymes UEs
        ues = nt.get_ues(filter_sport=True) 
        for ue in ues:
            H.append('<td>%s</td>' % ue['acronyme'])
        if len(ues) < Se.nb_max_ue:
            H.append('<td colspan="%d"></td>' % (Se.nb_max_ue - len(ues)))
        if with_links:
            H.append('<td></td>')
        H.append('<td></td></tr>')
        # 2eme ligne: etat et notes
        H.append('<tr class="%s rcp_l2"><td class="rcp_type_sem" style="background-color:%s;">&nbsp;</td>'
                 % (class_sem, bgcolor) )
        H.append('<td>%(mois_fin)s</td><td></td>'%sem)
        if decision_sem:
            ass = {0:'non',1:'oui', None:'-', '':'-'}[decision_sem['assidu']]
            H.append('<td>%s</td><td>%s</td>'
                     % (ass, decision_sem['code']) )
        else:
            H.append('<td colspan="2"><em>pas de d�cision</em></td>')
        # Absences (nb d'abs non just. dans ce semestre)
        debut_sem = znotes.DateDDMMYYYY2ISO(sem['date_debut'])
        fin_sem = znotes.DateDDMMYYYY2ISO(sem['date_fin'])
        nbabs = znotes.Absences.CountAbs(etudid=etudid, debut=debut_sem, fin=fin_sem)
        nbabsjust = znotes.Absences.CountAbsJust(etudid=etudid,
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
        # indique le semestre compens� par celui ci:
        if decision_sem and decision_sem['compense_formsemestre_id']:
            csem = znotes.do_formsemestre_list(
                {'formsemestre_id' : decision_sem['compense_formsemestre_id']})[0]
            H.append('<td><em>compense S%s</em></td>' % csem['semestre_id'] )
        else:
            H.append('<td></td>')
        if with_links:
            H.append('<td><a href="formsemestre_validation_etud_form?formsemestre_id=%s&etudid=%s">modifier</a></td>' % (sem['formsemestre_id'],etudid))

        H.append('</tr>')
    H.append('</table>')
    return '\n'.join(H)


def form_decision_manuelle(znotes, Se, formsemestre_id, etudid, desturl=''):
    """Formulaire pour saisie d�cision manuelle
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
    H.append('<h3 class="sfv">D�cisions manuelles : <em>(v�rifiez bien votre choix !)</em></h3><table>')

    # Choix code semestre:
    codes = sco_codes_parcours.CODES_EXPL.keys()
    codes.sort() # fortuitement, cet ordre convient bien !

    H.append('<tr><td>Code semestre: </td><td><select name="code_etat"><option value="" selected>Choisir...</option>')
    for cod in codes:
        if cod != 'ADC':
            H.append('<option value="%s">%s (code %s)</option>' % (cod, sco_codes_parcours.CODES_EXPL[cod], cod) )
        else:
            # traitement sp�cial pour ADC (compensation)
            # ne propose que les semestres avec lesquels on peut compenser
            # le code transmis est ADC_formsemestre_id
            log(str(Se.sems))
            for sem in Se.sems:
                if sem['can_compensate']:
                    H.append('<option value="%s_%s">Admis par compensation avec S%s (%s)</option>' %
                             (cod, sem['formsemestre_id'], sem['semestre_id'], sem['date_debut']) )
    H.append('</select></td></tr>')

    # Choix code semestre precedent:
    if Se.prev:
        H.append('<tr><td>Code semestre pr�c�dent: </td><td><select name="new_code_prev"><option value="">Choisir une d�cision...</option>')
        for cod in codes:
            if cod == 'ADC': # ne propose pas ce choix
                continue
            if Se.prev_decision and cod == Se.prev_decision['code']:
                sel='selected'        
            else:
                sel=''
            H.append('<option value="%s" %s>%s</option>' % (cod, sel, sco_codes_parcours.CODES_EXPL[cod]) )        
        H.append('</select></td></tr>')

    # Choix code devenir
    codes = sco_codes_parcours.DEVENIR_EXPL.keys()
    codes.sort() # fortuitement, cet ordre convient aussi bien !

    H.append('<tr><td>Devenir: </td><td><select name="devenir"><option value="" selected>Choisir...</option>')
    for cod in codes:
        if Se.sem['gestion_semestrielle'] == '1' or sco_codes_parcours.DEVENIRS_STD.has_key(cod):
            H.append('<option value="%s">%s</option>' % (cod, Se.explique_devenir(cod)))
    H.append('</select></td></tr>')
    
    H.append("""</table>
    <input type="submit" value="Valider d�cision manuelle"/>
    </form>
    """)
    return '\n'.join(H)
