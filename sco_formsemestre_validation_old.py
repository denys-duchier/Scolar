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

"""
Sx est valid� si moyenne g�n� >=10 et UE>=8
UE valid�e si >=10 (n'a de sens que si le semestre n'est pas valid�)

         Si Sx est valid�
         |  alors si Sx-1 est valid�
         |        |  alors passage en Sx+1
         |        |  sinon /* compensation  AUTOMATIQUE pour obtenir Sx-1 */
         |        |        si (Sx + Sx+1) est valid�
         |        |        |  /* on met ensemble les notes des 2
         |        |        |     semestres pour obtenir de nouvelles
         |        |        |     moyennes et UEs > 8 */
         |        |        |  alors passage en Sx+1 avec Sx et Sx-1
         |        |        |  sinon refaire les UE manquantes de Sx-1
         |        |        |        /* redoublement de Sx-1 */
         |        |        finsi
         |        finsi
         |  sinon si Sx-1 est valid�
         |        |  alors passage en Sx+1
         |        |  sinon refaire les UE non valid�es
         |        |        des semestres Sx et Sx+1 /* redoublement */
         |        finsi
         finsi


Arret� du 13 ao�t 2005

* Art 19.

Les unit�s d'enseignement sont d�finitivement acquises et
capitalisables d�s lors que l'�tudiant y a obtenu la
moyenne. L'acquisition de l'unit� d'enseignement emporte
l'acquisition des cr�dits europ�ens correspondants.

Toute unit� d'enseignement capitalis�e est prise en compte dans le
dispositif de compensation, au m�me titre et dans les m�mes conditions
que les autres unit�s d'enseignement.

Dans le cas de redoublement d'un semestre, si un �tudiant ayant acquis
une unit� d'enseignement souhaite, notamment pour am�liorer les
conditions de r�ussite de sa formation, suivre les enseignements de
cette unit� d'enseignement et se repr�senter au contr�le des
connaissances correspondant, la compensation prend en compte le
r�sultat le plus favorable pour l'�tudiant.
[XXX non impl�ment�: il faudrait chercher si plusieurs semestres "adjacents"
 et prendre en compte le "meilleur" r�sultat:
 => calcul d'une moyenne g�n�rale avec de UE obtenues dans des
 ann�es (ou semestres) diff�rentes.
 ]

* Art. 20.
La validation d'un semestre est acquise de droit lorsque l'�tudiant a
obtenu � la fois :
a) Une moyenne g�n�rale �gale ou sup�rieure � 10 sur 20 et une moyenne
�gale ou sup�rieure � 8 sur 20 dans chacune des UE;

b) La validation des semestres pr�c�dents, lorsqu'ils existent.

Lorsque les conditions pos�es ci-dessus ne sont pas remplies, la
validation est assur�e, sauf opposition de l'�tudiant, par une
compensation organis�e entre deux semestres cons�cutifs sur la base
d'une moyenne g�n�rale �gale ou sup�rieure � 10 sur 20 et d'une
moyenne �gale ou sup�rieure � 8 sur 20 dans chacune des UE
constitutives de ces semestres. Le semestre servant � compenser ne
peut �tre utilis� qu'une fois au cours du cursus.

En outre, le directeur de l'IUT peut prononcer la validation d'un
semestre sur proposition du jury.  La validation de tout semestre
donne lieu � l'obtention de l'ensemble des UE qui le composent et des
cr�dits europ�ens correspondants. [=> si un semestre est valid�, les UE le sont]


* Art. 21.
La poursuite d'�tudes dans un nouveau semestre est de droit pour tout
�tudiant � qui ne manque au maximum que la validation d'un seul
semestre de son cursus.
[ XXX a prendre en compte dans le formulaire de passage ]

* Art. 22.
Le redoublement est de droit dans les cas o� :

 - l'�tudiant a obtenu la moyenne g�n�rale et lorsque celle-ci ne
 suffit pas pour remplir la condition pos�e au a de l'article 20
 ci-dessus ; [ donc au moins une UE < 8 ]

 - l'�tudiant a rempli la condition pos�e au a de l'article 20
 ci-dessus dans un des deux semestres utilis�s dans le processus de
 compensation. [ un semestre acquis normalement ]

En outre, l'�tudiant peut �tre autoris� � redoubler par d�cision du
directeur de l'IUT, sur proposition du jury de passage ou du jury de
d�livrance pour l'obtention du dipl�me universitaire de technologie.


Durant la totalit� du cursus conduisant au dipl�me universitaire de
technologie, l'�tudiant ne peut �tre autoris� � redoubler plus de deux
semestres. En cas de force majeure d�ment justifi�e et appr�ci�e par
le directeur de l'IUT, un redoublement suppl�mentaire peut �tre
autoris�.


* Art. 24. ~ Le DUT (...) est d�livr� par le pr�sident de l'universit�
(...)
La d�livrance du dipl�me universitaire de technologie donne lieu � l'obtention
de l'ensemble des unit�s d~enseignement qui le composent et les cr�dits
correspondants.


* Art. 25.

Les unit�s d'enseignement dans lesquelles la moyenne de 10 a �t�
obtenue sont capitalisables en vue de la reprise d'�tudes en
formation continue.

Les �tudiants qui sortent de l'IUT sans avoir obtenu le dipl�me
universitaire de technologie re�oivent une attestation d'�tudes
comportant la liste des unit�s d'enseignement capitalisables qu'ils
ont acquises, ainsi que les cr�dits europ�ens correspondants, d�livr�e
par le directeur de l'IUT.


------ ADIUT:
Un accord sur certains termes semble acquis et afin de respecter
la terminologie Apog�e, nous utiliserons, lorsque le semestre est
valid�, les 3 possibilit�s suivantes :
 - Admis (validation de droit)
 - Admis par compensation (validation par compensation entre semestres)
 - Admis jury (validation par le jury)

Lorsque le semestre n'est pas valid�, l'�tudiant est en attente d'une
d�cision qui sera prise au semestre suivant.


Codes � utiliser:
- Jury S1:
 . ADM  (auto) moyenne gen., barres UE, assiduit�: sem. valid�
 . ATT  (auto) pas moy., barres UE ok, assiduit�: d�cision en attente de S2
 . ATB  (auto) pb barre UE (qq soit moy gen), assiduit�: d�cision en attente de S2
 . ATJ  (manu) pb assiduit�. d�cision en attente de S2
 . ATJ* (manu) manque note. attente jury "d�cal�"

- Codes �tat UEs: (toujours calcul� automatiquement)
 . ADM  moy UE >= 10 (qq soit resultat semestre)
 . CMP  moy UE < 10 et semestre valid� (ADC, ADJ, ADM)
 . AJ   moy UE < 10 et semestre non valid� (ATT, ATB, ATJ, AJ, NAR)


- Codes �tat semestres:
 . AJ   redoublement
 . NAR  r�orientation (non admis � redoubler)
 . ADC  admis par compensation (eg moy(S1, S2) > 10)
 . ADJ  admis par Jury

"""

def formsemestre_validation_form(
    self, # ZNotes instance
    formsemestre_id, etudid=None,
    REQUEST=None):
    """formulaire valisation semestre et UE
    Si etudid, traite un seul �tudiant !
    """

    cnx = self.GetDBConnexion()
    sem = self.do_formsemestre_list(args={ 'formsemestre_id' : formsemestre_id } )[0]
    if sem['etat'] != '1':
        header = self.sco_header(self,REQUEST,
                                 page_title="Semestre verrouill�")
        footer = self.sco_footer(self, REQUEST)
        return header + '<p>Semestre verrouill�</p>' + footer

    nt = self._getNotesCache().get_NotesTable(self, formsemestre_id)
    ues = nt.get_ues()
    T = nt.get_table_moyennes_triees()
    # Traite toute la promo ou un seul �tudiant ?
    if REQUEST.form.has_key('etudid'):
        etudid = REQUEST.form['etudid']
    if etudid:
        # restreint T a cet �tudiant (validation individuelle)
        for t in T:
            if t[-1] == etudid:
                ok = 1
                break
        if not ok:
            raise ScoValueError('etudid invalide (%s)' % etudid)
        T = [t]
        valid_individuelle = True            
        # XXX OK, la suite est inachevee (modif titre, prise en compte de l'etat
        # XXX courant de l'etudiant (sem et ue d�j� valid�es) pour initialiser le form.            
    else:
        valid_individuelle = False

    # ------- Validations au dessus des barres
    # sem_must_valid = { etudid : True|False }
    # ue_must_valid = { ue_id : { etudid : True|False } }
    sem_must_valid, ue_must_valid = _compute_barres( ues, nt, T )

    # ------- Traitement des donn�es formulaire
    date_jury = REQUEST.form.get('date_jury', time.strftime('%d/%m/%Y') )
    msg = ''
    # --------------   Soumission du formulaire
    if REQUEST.form.get('tf-submitted',False):
        # recupere infos du form
        semvalid, semcomp, form_sem_decision, uevalid, uevalid_byetud = \
                  _get_validation_form_state( REQUEST, ues, T, sem_must_valid, ue_must_valid )
        # verification coh�rence d�cision semestre/UE
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
            msg += '<li class="tf-msg">D�cisions incoh�rentes pour les �tudiants suivants ! (si le semestre est valid�, toutes les UE doivent l\'�tre)<ul><li>' + '</li><li>'.join( inconsistent_etuds ) + '</li></ul></li>'
        msg += '<li class="tf-msg">%d �tudiants valident le semestre</li>' % nbvalid
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
            msg += '<input type="submit" name="go" value="OK, valider ces d�cisions"/>'
        msg += '</ul>'
    else:
        # premier passage: initialise le form avec decisions ant�rieures s'il y en a
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
            if sem_d == 2: # semestre valid�
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
                                 % (sem['titre_num'],nomprenom))
        H = [ """<h2>Validation (Jury) du semestre %s pour %s</h2>
        <p>Utiliser ce formulaire apr�s la <b>d�cision d�finitive du jury</b>.</p>
        <p>Attention: les d�cisions prises ici remplacent et annulent les pr�c�dentes s'il y en avait !</p>
        """ % (sem['titre_num'],nomprenom)]
    else:
        header = self.sco_header(self,REQUEST,
                                 page_title="Validation du semestre "+sem['titre_num'])
        H = [ """<h2>Validation (Jury) du semestre %s</h2>


        <h3>Attention: gestion des compensation inter-semestre en cours de d�veloppement</h3>
        <p style="color:red"><em>Il est pr�f�rable d'attendre quelques jours avant
        de valider ce formulaire</em></p>


        <p>Utiliser ce formulaire apr�s la d�cision d�finitive du jury.</p>
        <p>Les �tudiants au dessus des "barres" vont valider automatiquement le semestre ou certaines UE.
        </p><p>Pour valider des �tudiants sous les barres, cocher les cases correspondantes.</p>
        <p>Un semestre peut �tre valid� automatiquement, ou sur d�cision du jury (choisir "Admis"), ou, si le parcours le permet, par compensation avec l'un des semestre propos� dans le menu (<b>vous devez v�rifier les notes</b>, car le calcul des moyennes n'est pas pris en compte: on propose ici tous les semestres possibles)</p>
        <p>Attention: les d�cisions prises ici remplacent et annulent les pr�c�dentes s'il y en avait !</p>
        <p>Attention: le formulaire va affecter TOUS LES ETUDIANTS !</p>
        """ % sem['titre_num'] ]

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
            H.append('<td class="fvs_tit">%s</td><td class="fvs_tit_chk">valid�e</td>' % ue['acronyme'])
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
            H.append('<td class="fvs_chk">valid�</td>')
        elif nt.get_etud_etat(etudid) == 'D':
            H.append('<td class="fvs_chk">d�mission</td>')
        else:
            # semestres pour compensation
            sems_pour_comp = _lists_semestre_utilisables(self, formsemestre_id, etudid)
            H.append('<td><select name="sem_decision_%s" style="width: 250px">'% etudid)
            decision = form_sem_decision.get(etudid,None)
            if decision == 'N':
                selected = 'selected'
            else:
                selected = ''
            H.append('<option value="N" %s>Non</option>' % selected)
            if decision == 'O':
                selected = 'selected'
            else:
                selected = ''
            H.append('<option value="O" %s>Admis</option>' % selected)

            for sem in sems_pour_comp:
                if sem['formsemestre_id'] == decision:
                    selected = 'selected'
                else:
                    selected = ''
                H.append("""<option value="%s" %s>Compens� avec %s (%s - %s) [moy=%s, moy comp.=%s]</option>"""
                         % (sem['formsemestre_id'], selected,
                            sem['titre_num'], sem['date_debut'], sem['date_fin'],
                            fmt_note(sem['moy_gen']), fmt_note(sem['moy_comp']) ))
            H.append("""</select>""")
            # check: s'il y a eu compensation, doit etre dans la liste des possibles
            # sinon, bug ou modification des notes ou de l'archi de formation
            if decision and decision != 'O' and decision != 'N' \
                   and decision not in [ x['formsemestre_id']
                                         for x in sems_pour_comp ]:
                H.append('(compensation impossible d�j� saisie !)')
            H.append("""</td>""")

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
    H.append("""<input type="submit" name="submit" value="V�rifier" /></form>

    <p style="color:red"><em>En d�veloppement: il est pr�f�rable d'attendre quelques jours avant
        de valider ce formulaire</em></p>

    """)
    return header + '\n'.join(H) + footer


#
def _lists_semestre_utilisables(self, formsemestre_id, etudid):
    """Liste des semestres utilisables pour compenser une decision
    sur formsemestre_id.
    On prend tous les semestres de la m�me formation 
    dans lesquels etudid a �t� inscrit
    et qui sont "adjacents" (semestre precedent ou suivant)
    et tels que moyenne des moyennes generales > 10 (=NOTES_BARRE_GEN)
    et toutes les UE > 8 (=NOTES_BARRE_UE)
    Ajoute les champs moy_gen et moy_comp (moyenne des 2 semestres)
    a chaque semestre selectionne
    """
    cursem = self.do_formsemestre_list(
        args={ 'formsemestre_id' : formsemestre_id })[0]
    if cursem['gestion_compensation'] != '1':
        return [] # pas de compensation possible
    cur_formation_id = cursem['formation_id']
    insems = self.do_formsemestre_inscription_list( args={ 'etudid' : etudid } )
    # Cherche les semestres avec lesquels on pourrait compenser
    nt = self._getNotesCache().get_NotesTable(self, formsemestre_id) 
    moy_gen = nt.moy_gen[etudid]
    if type(moy_gen) != type(1.0):
        return [] # pas de moyenne calculee, on ne peut pas compenser
    # Pour pr�tendre � compenser, il faut que toutes les UE soient > 8           
    if not nt.etud_has_all_ue_over_threshold(etudid):
        return [] # aucune compensation possible car une UE sous la barre
    #
    cnx = self.GetDBConnexion()
    sems = []
    for ins in insems:
        sem = self.do_formsemestre_list(
            args={ 'formsemestre_id' : ins['formsemestre_id'] })[0]
        # semestres "adjacents" ?
        adjacent = False
        if sem['semestre_id'] != None and cursem['semestre_id'] != None:
            d = sem['semestre_id'] - cursem['semestre_id']
            if abs(d) == 1:
                adjacent = True
        
        if sem['formsemestre_id'] != formsemestre_id \
               and sem['formation_id'] == cur_formation_id \
               and adjacent:
            # semestre adjacents de la meme formation
            # a-t-il ete valid� ?
            sem_d, ue_ids, comp_semid = self._formsemestre_get_decision(
                cnx, etudid, sem['formsemestre_id'] )
            nto = self._getNotesCache().get_NotesTable(self, sem['formsemestre_id'])
            # Sem valide avec toutes ses UE > 8 ?
            if sem_d == 2 and nto.etud_has_all_ue_over_threshold(etudid):
                # A-t-il deja �t� utilis� ?
                events = scolars.scolar_events_list(
                    cnx, args={'etudid':etudid,
                               'formsemestre_id': sem['formsemestre_id'],
                               'event_type' : 'UTIL_COMPENSATION' })                
                if not events or events[0]['comp_formsemestre_id'] == formsemestre_id:
                    # Pas deja utilis� (ou utilis� pour ce semestre)
                    # Calcule moyenne des moyennes g�n�rales
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
    # D�termine pour chaque etudiant s'il DOIT valider le semestre
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
        # et s'il est d�missionnaire, il n'a rien
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
        # recupere chaque UE valid�e
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
    # effectue la validation des semestres et UE indiqu�s
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
    self._inval_cache(formsemestre_id=formsemestre_id)
    #
    return REQUEST.RESPONSE.redirect(
        'formsemestre_validation_list?formsemestre_id=%s'%formsemestre_id)

# ---
def get_etud_moys_semestre(self, etudid, formsemestre_id):
    """Notes moyennes du semestre:
    { 'moy' : moyenne generale
      'moy_ues' : { ue_id : (moy, coef) }
      'comment' : explication si des UEs faites a des formsemestre differents
                  (capitalisation ou calcul de la meilleure UE si rep�t�e)
      }

    Cherche dans le semestre, et tous les semestres identiques
    (m�me semestre_id dans la formation) pour g�rer capitalisations et redoublements.
    """
    
    nt = self._getNotesCache().get_NotesTable(self, formsemestre_id)
    cursem = self.do_formsemestre_list({'formsemestre_id':formsemestre_id})[0]
    # cherche les semestres identiques o� l'etudiant est inscrit
    ins = self.do_formsemestre_inscription_list({'etudid':etudid})
    sems = [] # semestres "identiques"
    for i in ins:
        sem = self.do_formsemestre_list({'formsemestre_id':i['formsemestre_id']})[0]
        if sem['formation_id'] == cursem['formation_id'] \
           and sem['semestre_id'] == cursem['semestre_id']:
            sems.append(sem)
    # cherche la liste des UEs
    # (au cas improbable ou l'on aurait pas les m�mes UE dans les differents
    #  semestres identiques, merge les listes d'ue...)
    # Dans chaque UE, place sa moyenne (moycoef) et son semestre (sem).
    ues = nt.get_ues(etudid=etudid)
    uedict = {}
    for ue in ues:
        ue['moycoef'] = nt.get_etud_moycoef_ue(etudid, ue['ue_id'])
        ue['sem'] = cursem
        uedict[ue['ue_id']] = ue

    comment = [] # explications
    for sem in sems:
        nt1 = self._getNotesCache().get_NotesTable(self, sem['formsemestre_id'])
        ues1 = nt1.get_ues(etudid=etudid)
        for ue in ues1:
            ue['moycoef'] = nt1.get_etud_moycoef_ue(etudid, ue['ue_id'])
            ue['sem'] = sem
            if not uedict.has_key(ue['ue_id']):
                uedict[ue['ue_id']] = ue
            else:
                # remplace UE existante 
                # Si UE "acquise" (au sens de l'article 19, donc moy > 10)
                # et (pas cette UE dans sem. courant OU note meilleure)
                moy, coef = ue['moycoef']
                if coef > 0 and moy > NOTES_BARRE_VALID_UE:
                    cur_ue = uedict[ue['ue_id']]
                    cur_moy, cur_coef = cur_ue['moycoef']
                    if (cur_coef == 0) or moy > cur_moy:
                        uedict[ue['ue_id']] = ue
                        comment.append('UE %s reprise de %s' %
                                       ue['acronyme'], sem['date_debut'] )
    # Recalcul moyenne g�n�rale avec UE reprises
    summoy = 0.
    sumcoef = 0.
    for ue in uedict.values():
        moy, coef = ue['moycoef']
        if coef > 0:
            summoy += moy
            sumcoef += coef
    if sumcoef > 0:
        moy = summoy / sumcoef
    else:
        moy = 'NA'        
    #
    moy_ues = {}
    for ue in uedict.values():
        moy_ues[ue['ue_id']] = ue['moycoef']
    return { 'moy' : moy,
             'moy_ues' : moy_ues,
             'comment' : comment }

def get_etud_situation_semestre(self, etudid, formsemestre_id):
    """Toutes les infos decrivant la situation de l'etudiant
    au moment du jury.
    """
    nt = self._getNotesCache().get_NotesTable(self, formsemestre_id)
    moys = get_etud_moys_semestre(self, etudid, formsemestre_id)

    # XXX pour savoir si on peut valider: il faut regarder le sem. precedent (article 20)

    info = { 'nom_abbrv' : nt.get_nom_short(etudid),
             # rang semestre courant sans tenir compte des capitalisations d'UE
             'rang' : nt.get_etud_rang(etudid),
             'moys' : moys
             }
    
