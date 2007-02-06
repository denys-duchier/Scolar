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

"""Semestres: formulaire valisation semestre et UE
"""
import urllib, time, datetime

from notesdb import *
from sco_utils import *
from notes_log import log
from notes_table import *

def formsemestre_validation_form(
    self, # ZNotes instance
    formsemestre_id, etudid=None,
    REQUEST=None):
    """formulaire valisation semestre et UE
    Si etudid, traite un seul étudiant !
    """

    cnx = self.GetDBConnexion()
    sem = self.do_formsemestre_list(args={ 'formsemestre_id' : formsemestre_id } )[0]
    if sem['etat'] != '1':
        header = self.sco_header(self,REQUEST,
                                 page_title="Semestre verrouillé")
        footer = self.sco_footer(self, REQUEST)
        return header + '<p>Semestre verrouillé</p>' + footer

    nt = self._getNotesCache().get_NotesTable(self, formsemestre_id)
    ues = nt.get_ues()
    T = nt.get_table_moyennes_triees()
    # Traite toute la promo ou un seul étudiant ?
    if REQUEST.form.has_key('etudid'):
        etudid = REQUEST.form['etudid']
    if etudid:
        # restreint T a cet étudiant (validation individuelle)
        for t in T:
            if t[-1] == etudid:
                ok = 1
                break
        if not ok:
            raise ScoValueError('etudid invalide (%s)' % etudid)
        T = [t]
        valid_individuelle = True            
        # XXX OK, la suite est inachevee (modif titre, prise en compte de l'etat
        # XXX courant de l'etudiant (sem et ue déjà validées) pour initialiser le form.            
    else:
        valid_individuelle = False

    # ------- Validations au dessus des barres
    # sem_must_valid = { etudid : True|False }
    # ue_must_valid = { ue_id : { etudid : True|False } }
    sem_must_valid, ue_must_valid = _compute_barres( ues, nt, T )

    # ------- Traitement des données formulaire
    date_jury = REQUEST.form.get('date_jury', time.strftime('%d/%m/%Y') )
    msg = ''
    # --------------   Soumission du formulaire
    if REQUEST.form.get('tf-submitted',False):
        # recupere infos du form
        semvalid, semcomp, form_sem_decision, uevalid, uevalid_byetud = \
                  _get_validation_form_state( REQUEST, ues, T, sem_must_valid, ue_must_valid )
        # verification cohérence décision semestre/UE
        inconsistent_etuds = []
        for etudid in semvalid.keys():
            if semvalid[etudid]:
                # le semestre valide, donc les UE doivent valider
                for ue_id in uevalid.keys():
                    if not uevalid[ue_id][etudid]:
                        inconsistent_etuds.append(nt.get_nom_short(etudid))            
        #
        nbvalid = len([ x for x in semvalid.values() if x ])            
        msg = """<ul class="tf-msg">"""
        if inconsistent_etuds:
            msg += '<li class="tf-msg">Décisions incohérentes pour les étudiants suivants ! (si le semestre est validé, toutes les UE doivent l\'être)<ul><li>' + '</li><li>'.join( inconsistent_etuds ) + '</li></ul></li>'
        msg += '<li class="tf-msg">%d étudiants valident le semestre</li>' % nbvalid
        date_ok = False
        try:
            junk = DateDMYtoISO(date_jury)
            if junk:
                date_ok = True
        except:
            pass
        if not date_ok:
            msg += '<li class="tf-msg">la date est incorrecte !</li>'
        if len(inconsistent_etuds)==0 and date_ok:
            msg += '<input type="submit" name="go" value="OK, valider ces décisions"/>'
        msg += '</ul>'
    else:
        # premier passage: initialise le form avec decisions antérieures s'il y en a
        semvalid = {} # etudid: 0 ou 1
        semcomp = {} # etudid : id semestre utilise pour compenser, or None
        form_sem_decision = {} # etudid : 'O', 'N' ou formsemestre_id util. pour compenser
        uevalid = {} # ue_id : { etudid : True|False }
        uevalid_byetud = {} # etudid : [ ue_id, ... ]
        for ue in ues:
            uevalid[ue['ue_id']] = {}
        #
        for t in T:
            etudid = t[-1]
            sem_d, ue_ids, semcomp[etudid] = self._formsemestre_get_decision(
                cnx, etudid, formsemestre_id )
            if sem_d == 2: # semestre validé
                semvalid[etudid] = 1
                if not semcomp[etudid]:
                    form_sem_decision[etudid] = 'O'
                else:
                    form_sem_decision[etudid] = semcomp[etudid]
                for ue_id in uevalid.keys(): # valide tt les UE
                    uevalid[ue_id][etudid] = 1
            else:
                semvalid[etudid] = 0
                form_sem_decision[etudid] = 'N'
                for ue_id in ue_ids:
                    if uevalid.has_key(ue_id):
                        # test car la formation peut avoir ete modifie
                        # apres saisie des decisions !
                        uevalid[ue_id][etudid] = 1
        #open('/tmp/toto','a').write('\n'+str(uevalid)+'\n')
    #
    if REQUEST.form.get('go',False) and len(inconsistent_etuds)==0:
        # OK, validation
        return _do_formsemestre_validation( self,
            formsemestre_id, semvalid, semcomp,
            uevalid_byetud, date_jury,
            REQUEST=REQUEST)

    # --- HTML head
    footer = self.sco_footer(self, REQUEST)
    if valid_individuelle:
        nomprenom = self.nomprenom(nt.identdict[etudid])
        header = self.sco_header(self,REQUEST,
                                 page_title='Validation du semestre %s pour %s'
                                 % (sem['titre'],nomprenom))
        H = [ """<h2>Validation (Jury) du semestre %s pour %s</h2>
        <p>Utiliser ce formulaire après la <b>décision définitive du jury</b>.</p>
        <p>Attention: les décisions prises ici remplacent et annulent les précédentes s'il y en avait !</p>
        """ % (sem['titre'],nomprenom)]
    else:
        header = self.sco_header(self,REQUEST,
                                 page_title="Validation du semestre "+sem['titre'])
        H = [ """<h2>Validation (Jury) du semestre %s</h2>


        <h3>Attention: gestion des compensation inter-semestre en cours de développement</h3>
        <p style="color:red"><em>Il est préférable d'attendre quelques jours avant
        de valider ce formulaire</em></p>


        <p>Utiliser ce formulaire après la décision définitive du jury.</p>
        <p>Les étudiants au dessus des "barres" vont valider automatiquement le semestre ou certaines UE.
        </p><p>Pour valider des étudiants sous les barres, cocher les cases correspondantes.</p>
        <p>Un semestre peut être validé automatiquement, ou sur décision du jury (choisir "Admis"), ou, si le parcours le permet, par compensation avec l'un des semestre proposé dans le menu (<b>vous devez vérifier les notes</b>, car le calcul des moyennes n'est pas pris en compte: on propose ici tous les semestres possibles)</p>
        <p>Attention: les décisions prises ici remplacent et annulent les précédentes s'il y en avait !</p>
        <p>Attention: le formulaire va affecter TOUS LES ETUDIANTS !</p>
        """ % sem['titre'] ]

    H.append( """
    <form class="formvalidsemestre" method="POST">
    <input type="hidden" name="tf-submitted" value="1"/>
    <input type="hidden" name="formsemestre_id" value="%s"/>
    %s
    <p>Date du jury (j/m/a): <input type="text" name="date_jury" size="12" value="%s" /></p>
    <table class="notes_recapcomplet">
    <tr class="recap_row_tit"><td class="recap_tit">Rg</td><td class="recap_tit">Nom</td><td class="fvs_tit">Moy</td>
    <td class="fvs_tit_chk">Semestre</td>
    """ % (formsemestre_id,msg,date_jury) )        

    for ue in ues:
        if ue['type'] != UE_SPORT:
            H.append('<td class="fvs_tit">%s</td><td class="fvs_tit_chk">validée</td>' % ue['acronyme'])
    H.append('</tr>')
    # --- Generate form
    ir = 0
    for t in T:
        etudid = t[-1]
        if ir % 2 == 0:
            cls = 'recap_row_even'
        else:
            cls = 'recap_row_odd'
        ir += 1
        if sem_must_valid[etudid]:
            moycls = 'fvs_val'
        else:
            moycls = 'fvs_val_inf'
        if semvalid.has_key(etudid): # dans le formulaire
            if semvalid[etudid]:
                sem_checked, sem_unchecked = "checked", ""
                sem_is_valid = True
            else:
                sem_checked, sem_unchecked = "", "checked"
                sem_is_valid = False
        elif sem_must_valid[etudid]:
            sem_checked, sem_unchecked = "checked", ""
            sem_is_valid = True
        else:
            sem_checked, sem_unchecked = "", "checked"
            sem_is_valid = False

        H.append('<tr class="%s"><td>%s</td><td><a href="ficheEtud?etudid=%s">%s</a></td><td class="%s">%s</td>'
                 % (cls, nt.get_etud_rang(etudid),
                    etudid, nt.get_nom_short(etudid),
                    moycls, fmt_note(t[0]) ))
        # ne propose que si sous la barre
        if sem_must_valid[etudid]:
            H.append('<td class="fvs_chk">validé</td>')
        elif nt.get_etud_etat(etudid) == 'D':
            H.append('<td class="fvs_chk">démission</td>')
        else:
            # semestres pour compensation
            sems_pour_comp = _lists_semestre_utilisables(self, formsemestre_id, etudid)
            H.append('<td><select name="sem_decision_%s" style="width: 250px">'% etudid)
            if form_sem_decision.get(etudid,None) == 'N':
                selected = 'selected'
            else:
                selected = ''
            H.append('<option value="N" %s>Non</option>' % selected)
            if form_sem_decision.get(etudid,None) == 'O':
                selected = 'selected'
            else:
                selected = ''
            H.append('<option value="O" %s>Admis</option>' % selected)

            for sem in sems_pour_comp:
                if sem['formsemestre_id'] == form_sem_decision.get(etudid,None):
                    selected = 'selected'
                else:
                    selected = ''
                H.append("""<option value="%s" %s>Compensé avec %s (%s - %s) [moy=%s, moy comp.=%s] %s</option>"""
                         % (sem['formsemestre_id'], selected,
                            sem['titre'], sem['date_debut'], sem['date_fin'],
                            fmt_note(sem['moy_gen']), fmt_note(sem['moy_comp']), selected ))
            H.append("""</select></td>""")
        # UEs
        iue = 0
        for ue in ues:
            iue += 1
            if ue['type'] == UE_SPORT:
                continue
            if uevalid[ue['ue_id']].has_key(etudid): # dans le formulaire
                if uevalid[ue['ue_id']][etudid]:
                    sem_checked, sem_unchecked = "checked", ""
                else:
                    sem_checked, sem_unchecked = "", "checked"
            elif ue_must_valid[ue['ue_id']][etudid]:
                sem_checked, sem_unchecked = "checked", ""
            else:
                sem_checked, sem_unchecked = "", "checked"
            # ne propose les UE que si le semestre est sous la barre
            if ue_must_valid[ue['ue_id']][etudid]:
                H.append('<td class="fvs_val">%s</td><td class="fvs_chk">valid.</td>'
                         % (t[iue],))
            elif nt.get_etud_etat(etudid) == 'D':
                H.append('<td class="fvs_val"></td><td class="fvs_chk"></td>')
            else:
                H.append("""<td class="fvs_val_inf">%s</td><td class="fvs_chk">
                <input type="radio" name="ue_%s_%s" value="1" class="radio_green" %s/>O&nbsp;
                <input type="radio" name="ue_%s_%s" value="0" class="radio_red" %s/>N
                </td>            
                """ % (t[iue],ue['ue_id'],etudid,sem_checked,
                       ue['ue_id'],etudid,sem_unchecked))
        #
        H.append('</tr>')
    # ligne titres en bas
    H.append('<tr class="recap_row_tit"><td></td><td></td><td class="fvs_tit">Moy</td><td class="fvs_tit_chk">Semestre</td>')
    for ue in ues:
        if ue['type'] != UE_SPORT:
            H.append('<td class="fvs_tit">%s</td><td class="fvs_tit_chk"></td>' % ue['acronyme'])
    H.append('</tr></table>')
    if valid_individuelle:
        H.append('<input type="hidden" name="etudid" value="%s" />' % etudid)

    #
    H.append("""<input type="submit" name="submit" value="Vérifier" /></form>

    <p style="color:red"><em>En développement: il est préférable d'attendre quelques jours avant
        de valider ce formulaire</em></p>

    """)
    return header + '\n'.join(H) + footer


#
def _lists_semestre_utilisables(self, formsemestre_id, etudid):
    """Liste des semestres utilisables pour compenser une decision
    sur formsemestre_id.
    On prend tous les semestres de la même formation 
    dans lesquels etudid a été inscrit.
    
    Ajoute les champs moy_gen et moy_comp (moyenne des 2 semestres)
    a chaque semestre selectionne
    """
    cursem = self.do_formsemestre_list(
        args={ 'formsemestre_id' : formsemestre_id })[0]
    if cursem['gestion_compensation'] != '1':
        return [] # pas de compensation possible
    cur_formation_id = cursem['formation_id']
    insems = self.do_formsemestre_inscription_list( args={ 'etudid' : etudid } )
    # Cherche les semestre avec lesquels on pourrait compenser
    nt = self._getNotesCache().get_NotesTable(self, formsemestre_id) 
    moy_gen = nt.moy_gen[etudid]
    if type(moy_gen) != type(1.0):
        return [] # pas de moyenne calculee, on ne peut pas compenser
    cnx = self.GetDBConnexion()
    sems = []
    for ins in insems:
        sem = self.do_formsemestre_list(
            args={ 'formsemestre_id' : ins['formsemestre_id'] })[0]
        if sem['formsemestre_id'] != formsemestre_id \
               and sem['formation_id'] == cur_formation_id:
            # semestre de la meme formation
            # a-t-il ete validé ?
            sem_d, ue_ids, comp_semid = self._formsemestre_get_decision(
                cnx, etudid, sem['formsemestre_id'] )
            if sem_d == 2:
                # Sem valide
                # A-t-il deja été utilisé ?
                events = scolars.scolar_events_list(
                    cnx, args={'etudid':etudid,
                               'formsemestre_id': sem['formsemestre_id'],
                               'event_type' : 'UTIL_COMPENSATION' })                
                if not events or events[0]['comp_formsemestre_id'] == formsemestre_id:
                    # Pas deja utilisé (ou utilisé pour ce semestre)
                    # Calcule moyenne des moyennes générales
                    nto = self._getNotesCache().get_NotesTable(self, sem['formsemestre_id'] ) 
                    other_moy = nto.moy_gen[etudid]
                    if type(moy_gen) == type(1.0):
                        moy_comp = (moy_gen+other_moy) / 2
                        log('moy_comp=%s' % moy_comp)
                        if moy_comp >= NOTES_BARRE_GEN:
                            sem['moy_gen'] = other_moy
                            sem['moy_comp'] = moy_comp
                            sems.append(sem)
    return sems


#
def _compute_barres( ues, nt, T ):
    # Détermine pour chaque etudiant s'il DOIT valider le semestre
    # car > barre et la liste des UE qu'il DOIT valider car > barre,
    # Elimine les demissionnaires
    
    sem_must_valid = {} # etudid : True|False
    ue_must_valid = {}  # ue_id : { etudid : True|False }
    for ue in ues:
        ue_must_valid[ue['ue_id']] = {}
    for t in T:
        etudid = t[-1]            
        # premiere passe sur les UE pour verif barres (sauf sport):
        barres_ue_ok = True
        iue = 0
        for ue in ues:
            iue += 1
            if ue['type'] == UE_SPORT:
                continue # pas de barre sur notes de sport
            try:
                if (float(t[iue]) < NOTES_BARRE_UE):
                    barres_ue_ok = False
            except:
                barres_ue_ok = False # une UE sans note
        # valide semestre
        try:
            if (float(t[0]) >= NOTES_BARRE_GEN) and barres_ue_ok:
                sem_must_valid[etudid] = True
            else:
                sem_must_valid[etudid] = False
        except:
            sem_must_valid[etudid] = False # manque notes
        # valide les UE
        iue = 0
        for ue in ues:
            iue += 1
            if ue['type'] == UE_SPORT:
                ue_must_valid[ue['ue_id']][etudid] = False
                continue
            try:
                if (float(t[iue]) < NOTES_BARRE_VALID_UE) and not sem_must_valid[etudid]:
                    ue_must_valid[ue['ue_id']][etudid] = False
                else:
                    ue_must_valid[ue['ue_id']][etudid] = True                    
            except:
                ue_must_valid[ue['ue_id']][etudid] = False
        # et s'il est démissionnaire, il n'a rien
        if nt.get_etud_etat(etudid) == 'D':
            sem_must_valid[etudid] = False
            for ue in ues:
                ue_must_valid[ue['ue_id']][etudid] = False
    
    return sem_must_valid, ue_must_valid

#
def _get_validation_form_state( REQUEST, ues, T, sem_must_valid, ue_must_valid ):
    # recupere les etudiants du form
    semvalid = {} # etudid: 0 ou 1
    semcomp = {} # etudid : id semestre utilise pour compenser, or None
    form_sem_decision = {} # etudid : 'O', 'N' ou formsemestre_id util. pour compenser
    uevalid = {} # ue_id : { etudid : True|False }
    uevalid_byetud = {} # etudid : [ ue_id, ... ]
    for ue in ues:
        uevalid[ue['ue_id']] = {}
    #
    for etudid in [t[-1] for t in T]:
        semcomp[etudid] = None
        if sem_must_valid[etudid]:
            semvalid[etudid] = 1 # happily ignore form
            form_sem_decision[etudid] = None
        else:
            v = REQUEST.form.get('sem_decision_%s'%etudid,None)
            form_sem_decision[etudid] = v
            if v != None and v != 'N':
                semvalid[etudid] = 1
                if v != 'O':
                    semcomp[etudid] = v # semestre utilise pour compenser
            else:
                semvalid[etudid] = 0
        # recupere chaque UE validée
        for ue in ues:
            if ue['type'] == UE_SPORT:
                uevalid[ue['ue_id']][etudid] = 1
                continue
            if ue_must_valid[ue['ue_id']][etudid]:
                uevalid[ue['ue_id']][etudid] = 1 # happily ignore form
            else:
                v = REQUEST.form.get('ue_%s_%s'%(ue['ue_id'],etudid),None)
                if v != None:
                    uevalid[ue['ue_id']][etudid] = int(v)
                else:
                    uevalid[ue['ue_id']][etudid] = 0
    # reconstruit la liste des ue valides pour chaque etud
    uevalid_byetud = {}
    for ue_id in uevalid.keys():
        for etudid in uevalid[ue_id].keys():
            if not uevalid_byetud.has_key(etudid):
                uevalid_byetud[etudid] = []
            if uevalid[ue_id][etudid]:
                uevalid_byetud[etudid].append(ue_id)                    
    #
    return semvalid, semcomp, form_sem_decision, uevalid, uevalid_byetud


#
def _do_formsemestre_validation(
    self, # ZNotes instance
    formsemestre_id,
    semvalid,
    semcomp, # etudid : semestre utilise pour compenser
    uevalid_byetud,
    date_jury=None, REQUEST=None):
    # effectue la validation des semestres et UE indiqués
    cnx = self.GetDBConnexion()
    # semestres
    for etudid in semvalid.keys():
        scolars.scolar_validate_sem(
            cnx, etudid,
            formsemestre_id, valid=semvalid[etudid],
            formsemestre_used_to_compensate=semcomp.get( etudid, None ),
            event_date=date_jury,
            REQUEST=REQUEST)
    # UE
    for etudid in uevalid_byetud.keys():
        scolars.scolar_validate_ues(self, cnx, etudid, formsemestre_id, 
                                    uevalid_byetud[etudid], event_date=date_jury,
                                    suppress_previously_validated=True,
                                    REQUEST=REQUEST)
    # Inval cache bulletins
    self._getNotesCache().inval_cache(formsemestre_id=formsemestre_id)
    #
    return REQUEST.RESPONSE.redirect(
        'formsemestre_validation_list?formsemestre_id=%s'%formsemestre_id)
