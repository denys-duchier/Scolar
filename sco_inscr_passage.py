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

"""Form. pour inscription rapide des etudiants d'un semestre dans un autre
   Utilise les autorisations d'inscription délivrées en jury.
"""

from notesdb import *
from sco_utils import *
from notes_log import log


def list_authorized_etuds(formsemestre_id, delai=274):
    """Liste des etudiants autorisés à s'inscrire.
    delai = nb de jours max entre la date de l'autorisation et celel de debut du semestre cible.
    """
    XXX
    pass

def list_inscrits(formsemestre_id):
    """Etudiants déjà inscrits à ce semestre
    { etudid : i }
    """
    ins = self.Notes.do_formsemestre_inscription_list(
        args={  'formsemestre_id' : formsemestre_id, 'etat' : 'I' } )
    for i in ins:
        etudid = i['etudid']
        inscr[etudid] = context.getEtudInfo(etudid=etudid,filled=1)[0]
    return inscr


def do_inscrit(formsemestre_id, etuds):
    """Inscrit ces etudiants dans ce semestre
    Vérifie qu'ils ont l'autorisation
    Ignore ceux qui sont déjà inscrits
    """
    XXX

    

def formsemestre_inscr_passage(context, formsemestre_id, REQUEST=None):
    """Form. pour inscription des etudiants d'un semestre dans un autre.
    Permet de selectionner parmi les etudiants autorisés à s'inscrire
    Les etudiants sont places dans le groupe "A"
    """
    cnx = self.GetDBConnexion()
    sem = self.get_formsemestre(formsemestre_id)
    header = self.sco_header(REQUEST, page_title='Passage des étudiants')
    footer = self.sco_footer(REQUEST)

    


    nt = self._getNotesCache().get_NotesTable(self, formsemestre_id)
    T = nt.get_table_moyennes_triees()


    #
    passe = {} # etudid qui passent
    already_inscr = {} # etudid deja inscrits (pour eviter double sinscriptions)
    next_semestre_id = None
    info = ''
    if REQUEST.form.get('tf-submitted',False):
        # --- soumission
        # - formulaire passage
        for etudid in [t[-1] for t in T]:
            v = REQUEST.form.get('pas_%s'%etudid,None)
            if v != None:
                passe[etudid] = int(v)
        # - etudiants dans le semestre selectionne
        next_semestre_id = REQUEST.form.get('next_semestre_id',None)
        ins = self.Notes.do_formsemestre_inscription_list(
            args={  'formsemestre_id' : next_semestre_id, 'etat' : 'I' } )
        next_sem = self.get_formsemestre(next_formsemestre_id)

        info = ('<p>Information: <b>%d</b> étudiants déjà inscrits dans le semestre %s</p>'
                % (len(ins), next_sem['titre_num']))
        for i in ins:
            already_inscr[i['etudid']] = True

    if REQUEST.form.get('inscrire',False):
        # --- Inscription de tous les etudiants selectionnes non deja inscrits
        # - recupere les groupes TD/TP d'origine
        ins =  self.Notes.do_formsemestre_inscription_list(
            args={  'formsemestre_id' : formsemestre_id } )
        gr = {}
        for i in ins:
            gr[i['etudid']] = { 'groupetd' : i['groupetd'],
                                'groupeanglais' : i['groupeanglais'],
                                'groupetp' : i['groupetp'] }
        # - inscription de chaque etudiant
        inscrits = []
        for t in T:
            etudid = t[-1]                
            if passe.has_key(etudid) and passe[etudid] \
                   and not already_inscr.has_key(etudid):
                inscrits.append(etudid)
                args={ 'formsemestre_id' : next_semestre_id,
                       'etudid' : etudid,
                       'etat' : 'I' }
                args.update(gr[etudid])
                self.do_formsemestre_inscription_with_modules(
                    args = args, 
                    REQUEST = REQUEST,
                    method = 'formsemestre_inscr_passage' )
        H = '<p>%d étudiants inscrits : <ul><li>' % len(inscrits)            
        if len(inscrits) > 0:
            H += '</li><li>'.join(
                [ self.nomprenom(nt.identdict[eid]) for eid in inscrits ]
                ) + '</li></ul></p>'
        return header + H + footer
    #
    # --- HTML head
    H = [ """<h2>Passage suite au semestre %s</h2>
    <p>Inscription des étudiants du semestre dans un autre.</p>
    <p>Seuls les étudiants inscrits (non démissionnaires) sont mentionnés.</p>
    <p>Rappel: d'autres étudiants peuvent être inscrits individuellement par ailleurs
    (et ceci à tout moment).</p>
    <p>Le choix par défaut est de proposer le passage à tous les étudiants ayant validé
    le semestre. Vous devez sélectionner manuellement les autres qui vous voulez faire
    passer sans qu'ils aient validé le semestre.</p>
    <p>Les étudiants seront ensuite inscrits à <em>tous les modules</em> constituant le
    semestre choisi (attention si vous avez des parcours optionnels, vous devrez les désinscrire
    des modules non désirés ensuite).<p>
    <p>Les étudiants seront inscrit dans les mêmes <b>groupes de TD</b> et TP
    que ceux du semestres qu'ils terminent. Pensez à modifier les groupes par
    la suite si nécessaire.
    </p>
    <p><b>Vérifiez soigneusement le <font color="red">semestre de destination</font> !</b></p>
    """ % (sem['titre_num'],) ]
    H.append("""<form method="POST">
    <input type="hidden" name="tf-submitted" value="1"/>
    <input type="hidden" name="formsemestre_id" value="%s"/>
    """ % (formsemestre_id,) )
    # menu avec liste des semestres "ouverts" débutant a moins
    # de 123 jours (4 mois) de la date de fin du semestre d'origine.
    sems = self.do_formsemestre_list()
    othersems = []
    d,m,y = [ int(x) for x in sem['date_fin'].split('/') ]
    date_fin_origine = datetime.date(y,m,d)
    delais = datetime.timedelta(123) # 123 jours ~ 4 mois
    for s in sems:
        if s['etat'] != '1':
            continue # saute semestres pas ouverts
        if s['formsemestre_id'] == formsemestre_id:
            continue # saute le semestre d'où on vient
        if s['date_debut']:
            d,m,y = [ int(x) for x in s['date_debut'].split('/') ]
            datedebut = datetime.date(y,m,d)
            if abs(date_fin_origine - datedebut) > delais:
                continue # semestre trop ancien
        s['titremenu'] = s['titre'] + '&nbsp;&nbsp;(%s - %s)' % (s['date_debut'],s['date_fin'])
        othersems.append(s)
    if not othersems:
        raise ScoValueError('Aucun autre semestre de formation défini !')
    menulist = []
    for o in othersems:
        if o['formsemestre_id'] == next_semestre_id:
            s = 'selected'
        else:
            s = ''
        menulist.append(
            '<option value="%s" %s>%s</option>' % (o['formsemestre_id'],s,o['titremenu']) )

    H.append( '<p><b>Semestre destination:</b> <select name="next_semestre_id">'
              + '\n '.join(menulist) + '</select></p>' )
    H.append(info)
    # --- Liste des etudiants
    H.append("""<p>Cocher les étudiants à faire passer (à inscrire) :</p>
    <table class="notes_recapcomplet">
    <tr class="recap_row_tit"><td class="recap_tit">Nom</td>
                              <td>Décision jury</td><td>Passage ?</td><td></td>
    </tr>
    """)
    ir = 0
    for t in T:
        etudid = t[-1]
        if ir % 2 == 0:
            cls = 'recap_row_even'
        else:
            cls = 'recap_row_odd'
        ir += 1
        valid, decision, acros, comp_sem = self._formsemestre_get_decision_str(cnx, etudid, formsemestre_id)
        comment = ''
        if acros:
            acros = '(%s)' % acros # liste des UE validees
        if passe.has_key(etudid): # form (prioritaire)
            valid = passe[etudid]
        if already_inscr.has_key(etudid):
            valid = False # deja inscrit dans semestre destination
            comment = 'déjà inscrit dans ' + next_sem['titre_num']
        if valid: 
            checked, unchecked = 'checked', ''
            cellfmt = 'greenboldtext'
        else:
            checked, unchecked = '', 'checked'
            cellfmt = 'redboldtext'
        H.append('<tr class="%s"><td class="%s">%s</td><td class="%s">%s %s</td>'
                 % (cls, cellfmt, self.nomprenom(nt.identdict[etudid]),
                    cellfmt, decision, acros) )
        # checkbox pour decision passage
        H.append("""<td>
        <input type="radio" name="pas_%s" value="1" %s/>O&nbsp;
        <input type="radio" name="pas_%s" value="0" %s/>N
        </td><td>%s</td></tr>
        """ % (etudid, checked, etudid, unchecked, comment) )

    #
    H.append("""</table>
    <p>
    <input type="submit" name="check" value="Vérifier ces informations" />
    &nbsp;
    <input type="submit" name="inscrire" value="Inscrire les étudiants choisis !" />
    </p></form>""")
    return header + '\n'.join(H) + footer


