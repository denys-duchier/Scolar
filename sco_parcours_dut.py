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

"""Semestres: gestion parcours DUT (Arreté du 13 août 2005)
"""
import urllib, time, datetime

from notesdb import *
from sco_utils import *
from notes_log import log
from scolog import logdb
from notes_table import *

from sco_codes_parcours import *
from dutrules import DUTRules # regles generees a partir du CSV


class DecisionSem:
    "Decision prenable pour un semestre"
    def __init__(self, code_etat=None,
                 code_etat_ues={}, # { ue_id : code }
                 new_code_prev='',
                 explication='', # aide pour le jury
                 formsemestre_id_utilise_pour_compenser=None, # None si code != ADC
                 devenir=None, # code devenir
                 assiduite=1,
                 rule_id=None # id regle correspondante
                 ):
        self.code_etat = code_etat
        self.code_etat_ues = code_etat_ues
        self.new_code_prev = new_code_prev
        self.explication = explication
        self.formsemestre_id_utilise_pour_compenser = formsemestre_id_utilise_pour_compenser
        self.devenir = devenir
        self.assiduite = assiduite
        self.rule_id = rule_id
        # code unique utilise pour la gestion du formulaire
        self.codechoice = str(hash( (code_etat,new_code_prev,formsemestre_id_utilise_pour_compenser,devenir,assiduite)))
        # xxx debug
        #log('%s: %s %s %s %s %s' % (self.codechoice,code_etat,new_code_prev,formsemestre_id_utilise_pour_compenser,devenir,assiduite) ) 

class SituationEtudParcours:
    "Semestre dans un parcours"
    def __init__(self, znotes, etud, formsemestre_id):
        """
        etud: dict filled by fillEtudsInfo()
        """
        self.znotes = znotes
        self.etud = etud
        self.etudid = etud['etudid']
        self.formsemestre_id = formsemestre_id
        self.sem= znotes.do_formsemestre_list(
            args={ 'formsemestre_id' : formsemestre_id } )[0]
        self.formation = znotes.do_formation_list(args={ 'formation_id' : self.sem['formation_id'] })[0]
        self.nt = self.znotes._getNotesCache().get_NotesTable(znotes, formsemestre_id ) #> get_etud_decision_sem, etud_count_ues_under_threshold, get_etud_moy_gen, get_ues, get_etud_ue_status, etud_has_all_ue_over_threshold
        
        # Ce semestre est-il le dernier de la formation ? (e.g. semestre 4 du DUT)
        # pour le DUT, le dernier est toujours S4.
        # Si on voulait gérer d'autres formations, il faudrait un flag sur les formsemestre
        # indiquant s'ils sont "terminal" ou non. XXX TODO
        # Ici: terminal si semestre 4 ou bien semestre_id==-1
        #        (licences et autres formations en 1 seule session))
        self.semestre_non_terminal = (self.sem['semestre_id'] != DUT_NB_SEM) # True | False
        if self.sem['semestre_id'] == NO_SEMESTRE_ID:
            self.semestre_non_terminal = False
        # Liste des semestres du parcours de cet étudiant:
        self._comp_semestres()
        # Determine le semestre "precedent"
        self.prev_formsemestre_id = self._search_prev()
        # Verifie barres
        self._comp_barres()
        # Verifie compensation
        if self.prev and self.sem['gestion_compensation'] == '1':
            self.can_compensate_with_prev = self.prev['can_compensate']
        else:
            self.can_compensate_with_prev = False
    
    def get_possible_choices(self, assiduite=True):
        """Donne la liste des décisions possibles en jury
        (liste d'instances de DecisionSem)
        assiduite = True si pas de probleme d'assiduité
        """
        choices = []
        if self.prev_decision:
            prev_code_etat = self.prev_decision['code']
        else:
            prev_code_etat = None
        
        state = (prev_code_etat, assiduite,
                 self.barre_moy_ok, self.barres_ue_ok,
                 self.can_compensate_with_prev, self.semestre_non_terminal)
        # log('get_possible_choices: state=%s' % str(state) )
        for rule in DUTRules:
            # saute regles REDOSEM si pas de semestres decales:
            if self.sem['gestion_semestrielle'] != '1' and rule.conclusion[3] == 'REDOSEM':
                continue
            if rule.match(state):
                if rule.conclusion[0] == ADC:
                    # dans les regles on ne peut compenser qu'avec le PRECEDENT:
                    fiduc = self.prev_formsemestre_id
                    assert fiduc
                else:
                    fiduc = None
                # Detection d'incoherences (regles BUG)
                if rule.conclusion[5] == BUG:
                    log('get_possible_choices: inconsistency: state=%s' % str(state) )
                # 
                valid_semestre = code_semestre_validant(rule.conclusion[0])
                choices.append( DecisionSem(
                    code_etat = rule.conclusion[0],
                    new_code_prev = rule.conclusion[2],
                    devenir = rule.conclusion[3],
                    formsemestre_id_utilise_pour_compenser=fiduc,
                    explication = rule.conclusion[5],
                    assiduite=assiduite, rule_id=rule.rule_id))
        return choices

    def explique_devenir(self, devenir):
        "Phrase d'explication pour le code devenir"
        if not devenir:
            return ''
        s = self.sem['semestre_id'] # numero semestre courant
        if s < 0: # formation sans semestres (eg licence)
            next = 1
        else:
            next = self._get_next_semestre_id()
        if self.semestre_non_terminal and not self.all_other_validated(): 
            passage = 'Passe en S%s' % next
        else:
            passage = 'Formation terminée'
        if devenir == NEXT:
            return passage
        elif devenir == REO:
            return 'Réorienté'
        elif devenir == REDOANNEE:
            return 'Redouble année (recommence S%s)' % (s - 1)
        elif devenir == REDOSEM:
            return 'Redouble semestre (recommence en S%s)' % (s)
        elif devenir == 'RA_OR_NEXT':
            return passage + ', ou redouble année (en S%s)' % (s-1)
        elif devenir == 'RA_OR_RS':
            return 'Redouble semestre S%s, ou redouble année (en S%s)' % (s, s-1)
        elif devenir == 'RS_OR_NEXT':
            return passage + ', ou semestre S%s' % (s)
        else:
            log('explique_devenir: code devenir inconnu: %s' % devenir)
            return 'Code devenir inconnu !'

    def all_other_validated(self):
        "True si tous les autres semestres de cette formation sont validés"
        return self._sems_validated( exclude_current=True )
        
    def parcours_validated(self):
        "True si parcours validé (diplôme obtenu, donc)."
        return self._sems_validated()
    
    def _sems_validated(self, exclude_current=False):
        "True si semestres du parcours validés"
        if self.sem['semestre_id'] == NO_SEMESTRE_ID:
            # mono-semestre: juste celui ci
            decision = self.nt.get_etud_decision_sem(self.etudid)
            return decision and code_semestre_validant(decision['code'])
        else:
            to_validate = Set(range(1,DUT_NB_SEM+1)) # ensemble des indices à valider
            if exclude_current:
                to_validate.remove(self.sem['semestre_id'])
            for sem in self.get_semestres():
                if sem['formation_code'] == self.formation['formation_code']:
                    nt = self.znotes._getNotesCache().get_NotesTable(self.znotes, sem['formsemestre_id']) #> get_etud_decision_sem
                    decision = nt.get_etud_decision_sem(self.etudid)
                    if decision and code_semestre_validant(decision['code']):
                        # validé
                        to_validate.discard(sem['semestre_id'])

            return not to_validate

    def _comp_semestres(self):
        # etud['sems'] est trie par date decroissante (voir fillEtudsInfo)
        sems = self.etud['sems'][:] # copy
        sems.reverse()
        # Nb max d'UE et acronymes
        ue_acros = {} # acronyme ue : 1
        nb_max_ue = 0
        for sem in sems:
            nt = self.znotes._getNotesCache().get_NotesTable(self.znotes, sem['formsemestre_id'] ) #> get_ues 
            ues = nt.get_ues(filter_sport=True)
            for ue in ues:
                ue_acros[ue['acronyme']] = 1
            nb_ue = len(ues)
            if nb_ue > nb_max_ue:
                nb_max_ue = nb_ue
            # add formation_code to each sem:
            sem['formation_code'] = self.znotes.do_formation_list(
                args={ 'formation_id' : sem['formation_id'] })[0]['formation_code']
            # si sem peut servir à compenser le semestre courant, positionne
            #  can_compensate
            sem['can_compensate'] = check_compensation(self.etudid, self.sem, self.nt, sem, nt)
        
        self.ue_acros = ue_acros.keys()
        self.ue_acros.sort()
        self.nb_max_ue = nb_max_ue
        self.sems = sems
    
    def get_semestres(self):
        """Liste des semestres dans lesquels a été inscrit
        l'étudiant (quelle que soit la formation), le plus ancien en tête"""
        return self.sems
    
    def _comp_barres(self):
        "calcule barres_ue_ok et barre_moy_ok:  barre moy. gen. et barres UE"
        from notes_table import NOTES_BARRE_GEN
        self.nb_ues_under = self.nt.etud_count_ues_under_threshold(self.etudid)
        self.barres_ue_ok = (self.nb_ues_under == 0)
        self.moy_gen = self.nt.get_etud_moy_gen(self.etudid)
        self.barre_moy_ok = type(self.moy_gen) == FloatType and self.moy_gen >= NOTES_BARRE_GEN
        # conserve etat UEs
        ue_ids = [ x['ue_id'] for x in self.nt.get_ues(etudid=self.etudid, filter_sport=True) ]
        self.ues_status = {} # ue_id : status
        for ue_id in ue_ids:
            self.ues_status[ue_id] = self.nt.get_etud_ue_status(self.etudid, ue_id)

    def could_be_compensated(self):
        "true si ce semestre pourrait etre compensé par un autre (barres UE > 8)"
        return (self.nb_ues_under == 0)
        
    def _search_prev(self):
        """Recherche semestre 'precedent'.
        return prev_formsemestre_id
        """
        self.prev = None
        self.prev_decision = None
        if len(self.sems) < 2:
            return None
        # Cherche sem courant dans la liste triee par date_debut
        cur = None
        icur = -1
        for cur in self.sems:
            icur += 1
            if cur['formsemestre_id'] == self.formsemestre_id:
                break
        if not cur or cur['formsemestre_id'] != self.formsemestre_id:
            log('*** SituationEtudParcours: search_prev: cur not found (formsemestre_id=%s, etudid=%s)'
                % (formsemestre_id,etudid) )            
            return None # pas de semestre courant !!!
        # Cherche semestre antérieur de même formation (code) et semestre_id precedent
        # 
        #i = icur - 1 # part du courant, remonte vers le passé
        i = len(self.sems) - 1 # par du dernier, remonte vers le passé
        prev = None
        while i >= 0:
            if self.sems[i]['formation_code'] == self.formation['formation_code'] \
               and self.sems[i]['semestre_id'] == cur['semestre_id'] - 1:
                prev = self.sems[i]
                break
            i -= 1
        if not prev:
            return None # pas de precedent trouvé
        self.prev = prev
        # Verifications basiques:
        # ?
        # Code etat du semestre precedent:
        nt = self.znotes._getNotesCache().get_NotesTable(self.znotes, prev['formsemestre_id'] ) #> get_etud_decision_sem, get_etud_moy_gen, etud_has_all_ue_over_threshold
        self.prev_decision = nt.get_etud_decision_sem(self.etudid)
        self.prev_moy_gen = nt.get_etud_moy_gen(self.etudid)
        self.prev_barres_ue_ok = nt.etud_has_all_ue_over_threshold(self.etudid)
        return self.prev['formsemestre_id']
    
    def get_next_semestre_ids(self, devenir):
        "Liste des numeros de semestres autorises avec ce devenir"
        s = self.sem['semestre_id']
        if devenir == NEXT:
            ids = [self._get_next_semestre_id()]
        elif devenir == REDOANNEE:
            ids = [s-1]
        elif devenir == REDOSEM:
            ids = [s]
        elif devenir == RA_OR_NEXT:
            ids = [s-1,self._get_next_semestre_id()]
        elif devenir == RA_OR_RS:
            ids = [s-1, s]
        elif devenir == RS_OR_NEXT:
            ids = [s, self._get_next_semestre_id()]
        else:
            ids = [] # reoriente ou autre: pas de next !
        # clip [1--4]
        r=[]
        for idx in ids:
            if idx > 0 and idx <= DUT_NB_SEM:
                r.append(idx)
        return r

    def _get_next_semestre_id(self):
        """Indice du semestre suivant non validé.
        S'il n'y en a pas, ramène DUT_NB_SEM+1
        """
        s = self.sem['semestre_id']
        if s >= DUT_NB_SEM:
            return DUT_NB_SEM+1
        validated = True
        while validated and (s < DUT_NB_SEM):
            s = s + 1
            # semestre s validé ?
            validated = False
            for sem in self.sems:
                if sem['formation_code'] == self.formation['formation_code'] \
                   and sem['semestre_id'] == s:
                    nt = self.znotes._getNotesCache().get_NotesTable(self.znotes, sem['formsemestre_id']) #> get_etud_decision_sem
                    decision = nt.get_etud_decision_sem(self.etudid)
                    if decision and code_semestre_validant(decision['code']):
                        validated = True
        return s
        
    def valide_decision(self, decision, REQUEST):
        """Enregistre la decision (instance de DecisionSem)
        Enregistre codes semestre et UE, et autorisations inscription.
        """
        cnx = self.znotes.GetDBConnexion()
        # -- check
        if decision.code_etat == 'ADC':
            fsid = decision.formsemestre_id_utilise_pour_compenser
            if fsid:
                ok = False
                for sem in self.sems:
                    if sem['formsemestre_id'] == fsid and sem['can_compensate']:
                        ok = True
                        break
                if not ok:
                    raise ScoValueError('valide_decision: compensation impossible')
        # -- supprime decision precedente et enregistre decision
        to_invalidate = []
        if self.nt.get_etud_decision_sem(self.etudid):
            to_invalidate = formsemestre_update_validation_sem(
                cnx, self.formsemestre_id, self.etudid,
                decision.code_etat, decision.assiduite,
                decision.formsemestre_id_utilise_pour_compenser)
        else:
            formsemestre_validate_sem(
                cnx, self.formsemestre_id, self.etudid,
                decision.code_etat, decision.assiduite,
                decision.formsemestre_id_utilise_pour_compenser)
        logdb(REQUEST, cnx, method='validate_sem', etudid=self.etudid,
              msg='formsemestre_id=%s code=%s'%(self.formsemestre_id, decision.code_etat))
        # -- decisions UEs
        formsemestre_validate_ues(self.znotes, self.formsemestre_id, self.etudid,
                                  decision.code_etat, decision.assiduite, REQUEST=REQUEST)
        # -- modification du code du semestre precedent
        if self.prev and decision.new_code_prev:
            if decision.new_code_prev == ADC:
                # ne compense le prec. qu'avec le sem. courant
                fsid = self.formsemestre_id
            else:
                fsid = None
            to_invalidate += formsemestre_update_validation_sem(
                cnx, self.prev['formsemestre_id'],
                self.etudid, decision.new_code_prev, assidu=1,
                formsemestre_id_utilise_pour_compenser=fsid)
            logdb(REQUEST, cnx, method='validate_sem', etudid=self.etudid,
                  msg='formsemestre_id=%s code=%s'%(self.prev['formsemestre_id'],
                                                    decision.new_code_prev))
            # modifs des codes d'UE (pourraient passer de ADM a CMP, meme sans modif des notes)
            formsemestre_validate_ues(self.znotes, self.prev['formsemestre_id'], self.etudid,
                                      decision.new_code_prev,
                                      decision.assiduite, # XXX attention: en toute rigueur il faudrait utiliser une indication de l'assiduite au sem. precedent, que nous n'avons pas...
                                      REQUEST=REQUEST)
            
            self.znotes._inval_cache(formsemestre_id=self.prev['formsemestre_id']) #> modif decisions jury (sem, UE)

        # -- supprime autorisations venant de ce formsemestre        
        cursor = cnx.cursor()
        try:
            cursor.execute("""delete from scolar_autorisation_inscription
            where etudid = %(etudid)s and origin_formsemestre_id=%(origin_formsemestre_id)s
            """, { 'etudid' : self.etudid, 'origin_formsemestre_id' : self.formsemestre_id })
                        
            # -- enregistre autorisations inscription
            next_semestre_ids = self.get_next_semestre_ids(decision.devenir)
            for next_semestre_id in next_semestre_ids:
                _scolar_autorisation_inscription_editor.create(
                    cnx,
                    {
                    'etudid' : self.etudid,
                    'formation_code' : self.formation['formation_code'],
                    'semestre_id' : next_semestre_id,
                    'origin_formsemestre_id' : self.formsemestre_id } )
            cnx.commit()
        except:
            cnx.rollback()
            raise
        self.znotes._inval_cache(formsemestre_id=self.formsemestre_id) #> modif decisions jury et autorisations inscription
        if decision.formsemestre_id_utilise_pour_compenser:
            # inval aussi le semestre utilisé pour compenser:
            self.znotes._inval_cache(formsemestre_id=decision.formsemestre_id_utilise_pour_compenser) #> modif decision jury
        for formsemestre_id in to_invalidate:
            self.znotes._inval_cache(formsemestre_id=formsemestre_id) #> modif decision jury


def check_compensation( etudid, sem, nt, semc, ntc ):
    """Verifie si le semestre sem peut se compenser en utilisant semc
    - semc non utilisé par un autre semestre
    - decision du jury prise  ADM ou ADJ ou ATT ou ADC
    - barres UE (moy ue > 8) dans sem et semc
    - moyenne des moy_gen > 10
    Return boolean
    """
    from notes_table import NOTES_BARRE_GEN
    #pdb.set_trace()
    # -- deja utilise ?
    decc = ntc.get_etud_decision_sem(etudid)
    if decc \
           and decc['compense_formsemestre_id'] \
           and decc['compense_formsemestre_id'] != sem['formsemestre_id']:
        return False
    # -- semestres consecutifs ?
    if abs(sem['semestre_id'] - semc['semestre_id']) != 1:
        return False
    # -- decision jury:
    if decc and not decc['code'] in ('ADM', 'ADJ', 'ATT', 'ADC'):
        return False
    # -- barres UE et moyenne des moyennes:
    moy_gen = nt.get_etud_moy_gen(etudid)
    moy_genc= ntc.get_etud_moy_gen(etudid)
    try:
        moy_moy = (moy_gen + moy_genc) / 2
    except: # un des semestres sans aucune note !
        return False
    
    if (nt.etud_has_all_ue_over_threshold(etudid)
        and ntc.etud_has_all_ue_over_threshold(etudid)
        and moy_moy >= NOTES_BARRE_GEN):
        return True
    else:
        return False


# -------------------------------------------------------------------------------------------

def int_or_null(s):
    if s == '':
        return None
    else:
        return int(s)

_scolar_formsemestre_validation_editor = EditableTable(
    'scolar_formsemestre_validation',
    'formsemestre_validation_id',
    ('formsemestre_validation_id', 'etudid', 'formsemestre_id', 'ue_id', 'code', 'assidu', 'event_date',
     'compense_formsemestre_id', 'moy_ue', 'semestre_id' ),
    output_formators = { 'event_date' : DateISOtoDMY,
                         'assidu' : str },
    input_formators  = { 'event_date' : DateDMYtoISO,
                         'assidu' : int_or_null }
)

scolar_formsemestre_validation_create = _scolar_formsemestre_validation_editor.create
scolar_formsemestre_validation_list = _scolar_formsemestre_validation_editor.list
scolar_formsemestre_validation_delete = _scolar_formsemestre_validation_editor.delete
scolar_formsemestre_validation_edit = _scolar_formsemestre_validation_editor.edit

def formsemestre_validate_sem(cnx, formsemestre_id, etudid, code, assidu=True,
                              formsemestre_id_utilise_pour_compenser=None):
    "Ajoute ou change validation semestre"
    args = { 'formsemestre_id' : formsemestre_id, 'etudid' : etudid }
    # delete existing
    cursor = cnx.cursor()
    try:
        cursor.execute("""delete from scolar_formsemestre_validation
        where etudid = %(etudid)s and formsemestre_id=%(formsemestre_id)s and ue_id is null""", args )    
        # insert
        args['code'] = code
        args['assidu'] = assidu
        log('formsemestre_validate_sem: %s' % args )
        scolar_formsemestre_validation_create(cnx, args)
        # marque sem. utilise pour compenser:
        if formsemestre_id_utilise_pour_compenser:
            assert code == 'ADC'            
            args2 = { 'formsemestre_id' : formsemestre_id_utilise_pour_compenser,
                      'compense_formsemestre_id' : formsemestre_id,
                      'etudid' : etudid }
            cursor.execute("""update scolar_formsemestre_validation
            set compense_formsemestre_id=%(compense_formsemestre_id)s
            where etudid = %(etudid)s and formsemestre_id=%(formsemestre_id)s
            and ue_id is null""", args2 )
    except:
        cnx.rollback()
        raise

def formsemestre_update_validation_sem(cnx, formsemestre_id, etudid, code, assidu=1,
                                       formsemestre_id_utilise_pour_compenser=None):
    "Update validation semestre"
    args = { 'formsemestre_id' : formsemestre_id, 'etudid' : etudid, 'code' : code,
             'assidu': int(assidu)}
    log('formsemestre_update_validation_sem: %s' % args )
    cursor = cnx.cursor()
    to_invalidate = []

    # enleve compensations si necessaire
    # recupere les semestres auparavant utilisés pour invalider les caches
    # correspondants:
    cursor.execute("""select formsemestre_id from scolar_formsemestre_validation
    where compense_formsemestre_id=%(formsemestre_id)s and etudid = %(etudid)s""",
                   args )
    to_invalidate = [ x[0] for x in cursor.fetchall() ]
    # suppress:
    cursor.execute("""update scolar_formsemestre_validation set compense_formsemestre_id=NULL
    where compense_formsemestre_id=%(formsemestre_id)s and etudid = %(etudid)s""",
                   args )
    if formsemestre_id_utilise_pour_compenser:
        assert code == 'ADC'
        # marque sem. utilise pour compenser:
        args2 = { 'formsemestre_id' : formsemestre_id_utilise_pour_compenser,
                  'compense_formsemestre_id' : formsemestre_id,
                  'etudid' : etudid }
        cursor.execute("""update scolar_formsemestre_validation
        set compense_formsemestre_id=%(compense_formsemestre_id)s
        where etudid = %(etudid)s and formsemestre_id=%(formsemestre_id)s
        and ue_id is null""", args2 ) 
    
    cursor.execute("""update scolar_formsemestre_validation
    set code = %(code)s, event_date=DEFAULT, assidu=%(assidu)s
    where etudid = %(etudid)s and formsemestre_id=%(formsemestre_id)s
    and ue_id is null""", args )
    return to_invalidate


def formsemestre_validate_ues(znotes, formsemestre_id, etudid, code_etat_sem, assiduite, REQUEST=None):
    """Enregistre codes UE, selon état semestre.
    Les codes UE sont toujours calculés ici, et non passés en paramètres
    car ils ne dépendent que de la note d'UE et de la validation ou non du semestre.
    Les UE des semestres NON ASSIDUS ne sont jamais validées (code AJ).
    """
    from notes_table import NOTES_BARRE_VALID_UE
    valid_semestre = CODES_SEM_VALIDES.get(code_etat_sem, False)
    cnx = znotes.GetDBConnexion()
    nt = znotes._getNotesCache().get_NotesTable(znotes, formsemestre_id ) #> get_ues, get_etud_ue_status
    ue_ids = [ x['ue_id'] for x in nt.get_ues(etudid=etudid, filter_sport=True) ]
    for ue_id in ue_ids:
        ue_status = nt.get_etud_ue_status(etudid, ue_id)
        if not assiduite:
            code_ue = AJ
        else:
            # log('%s: %s: ue_status=%s' % (formsemestre_id,ue_id,ue_status))
            if type(ue_status['moy_ue']) == FloatType and ue_status['moy_ue'] >= NOTES_BARRE_VALID_UE:
                code_ue = ADM
            elif valid_semestre:
                code_ue = CMP
            else:
                code_ue = AJ
        # log('code_ue=%s' % code_ue)
        do_formsemestre_validate_ue(cnx, nt, formsemestre_id, etudid, ue_id, code_ue)
        if REQUEST:
            logdb(REQUEST, cnx, method='validate_ue', etudid=etudid,
                  msg='ue_id=%s code=%s'%(ue_id, code_ue))

            
def do_formsemestre_validate_ue(cnx, nt, formsemestre_id, etudid, ue_id, code, moy_ue=None, date=None, semestre_id=None):
    "Ajoute ou change validation UE"
    args = { 'formsemestre_id' : formsemestre_id, 
             'etudid' : etudid, 
             'ue_id' : ue_id, 
             'semestre_id' : semestre_id }
    if date:
        args['event_date'] = date
        
    # delete existing
    cursor = cnx.cursor()
    try:
        cond =  "etudid = %(etudid)s and ue_id=%(ue_id)s"
        if formsemestre_id:
            cond += " and formsemestre_id=%(formsemestre_id)s"
        if semestre_id:
            cond += " and semestre_id=%(semestre_id)s"
        cursor.execute("delete from scolar_formsemestre_validation where " + cond, args )
        # insert
        args['code'] = code
        if code == 'ADM':
            if moy_ue is None:
                # stocke la moyenne d'UE capitalisée:
                moy_ue = nt.get_etud_ue_status(etudid, ue_id)['moy_ue']            
            args['moy_ue'] = moy_ue
        log('formsemestre_validate_ue: %s' % args)
        scolar_formsemestre_validation_create(cnx, args)
    except:
        cnx.rollback()
        raise

_scolar_autorisation_inscription_editor = EditableTable(
    'scolar_autorisation_inscription',
    'autorisation_inscription_id',
    ('etudid', 'formation_code', 'semestre_id', 'date', 'origin_formsemestre_id'),
    output_formators = { 'date' : DateISOtoDMY },
    input_formators  = { 'date' : DateDMYtoISO }
)
scolar_autorisation_inscription_list =_scolar_autorisation_inscription_editor.list

def formsemestre_get_autorisation_inscription(znotes, etudid, origin_formsemestre_id):
    """Liste des autorisations d'inscription pour cet étudiant
    émanant du semestre indiqué.
    """
    cnx = znotes.GetDBConnexion()
    #sem = self.do_formsemestre_list(args={ 'formsemestre_id' : formsemestre_id } )[0]
    #F = self.do_formation_list( args={ 'formation_id' : sem['formation_id'] } )[0]
    return scolar_autorisation_inscription_list(
        cnx,
        {'origin_formsemestre_id' : origin_formsemestre_id, 'etudid' : etudid } )

def formsemestre_get_etud_capitalisation(znotes, sem, etudid):
    """Liste des UE capitalisées (ADM) correspondant au semestre sem.
    Recherche dans les semestres de la même formation (code) avec le même
    semestre_id et une date de début antérieure à celle du semestre mentionné.
    Resultat: [ { 'formsemestre_id' :
                  'ue_id' :
                  'ue_code' : 
                  'moy_ue' :
                  'event_date' :                  
                  } ]
    """
    cnx = znotes.GetDBConnexion()
    cursor = cnx.cursor()
    cursor.execute("""select SFV.*, ue.ue_code from notes_ue ue, notes_formations nf, notes_formations nf2,
    scolar_formsemestre_validation SFV, notes_formsemestre sem

    where ue.formation_id = nf.formation_id    
    and nf.formation_code = nf2.formation_code 
    and nf2.formation_id=%(formation_id)s

    and SFV.ue_id = ue.ue_id
    and SFV.code = 'ADM'
    and SFV.etudid = %(etudid)s
    
    and (  (sem.formsemestre_id = SFV.formsemestre_id
           and sem.date_debut < %(date_debut)s
           and sem.semestre_id = %(semestre_id)s )
         or (
             (SFV.formsemestre_id is NULL) 
             AND (SFV.semestre_id is NULL OR SFV.semestre_id=%(semestre_id)s)
           ) )
    """, { 'etudid' : etudid,
           'formation_id' : sem['formation_id'],
           'semestre_id' : sem['semestre_id'],
           'date_debut' : DateDMYtoISO(sem['date_debut'])
           })
    
    return cursor.dictfetchall()

def list_formsemestre_utilisateurs_uecap( znotes, formsemestre_id ):
    """Liste des formsemestres pouvant utiliser une UE capitalisee de ce semestre
    (et qui doivent donc etre sortis du cache si l'on modifie ce
    semestre): meme code formation, meme semestre_id, date posterieure"""
    cnx = znotes.GetDBConnexion()
    sem = znotes.do_formsemestre_list({'formsemestre_id' : formsemestre_id})[0]
    F = znotes.do_formation_list( args={ 'formation_id' : sem['formation_id'] } )[0]
    cursor = cnx.cursor()
    cursor.execute("""select sem.formsemestre_id
    from notes_formsemestre sem, notes_formations F
    where sem.formation_id = F.formation_id
    and F.formation_code = %(formation_code)s
    and sem.semestre_id = %(semestre_id)s
    and sem.date_debut >= %(date_debut)s
    and sem.formsemestre_id != %(formsemestre_id)s;
    """, { 'formation_code' : F['formation_code'],
           'semestre_id' : sem['semestre_id'],
           'formsemestre_id' : formsemestre_id,
           'date_debut' : DateDMYtoISO(sem['date_debut']) })
    return [ x[0] for x in cursor.fetchall() ]
