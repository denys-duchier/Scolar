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

"""Calculs sur les notes et cache des resultats
"""
from types import StringType
import pdb

import scolars
from notes_log import log
from sco_utils import *
from sco_exceptions import *
from notesdb import *
from sco_parcours_dut import formsemestre_get_etud_capitalisation
from sco_parcours_dut import list_formsemestre_utilisateurs_uecap


NOTES_PRECISION=1e-4 # evite eventuelles erreurs d'arrondis
NOTES_MIN = 0.       # valeur minimale admise pour une note
NOTES_MAX = 100.
NOTES_NEUTRALISE=-1000. # notes non prises en comptes dans moyennes
NOTES_SUPPRESS=-1001.   # note a supprimer
NOTES_ATTENTE=-1002.    # note "en attente" (se calcule comme une note neutralisee)

NOTES_BARRE_GEN = 10. # barre sur moyenne generale
NOTES_BARRE_UE = 8.   # barre sur UE
NOTES_BARRE_VALID_UE = 10. # seuil pour valider UE

UE_STANDARD = 0
UE_SPORT = 1

UE_TYPE_NAME = { UE_STANDARD : 'standard', UE_SPORT : 'sport' }

def fmt_note(val, note_max=None, keep_numeric=False):
    """conversion note en str pour affichage dans tables HTML ou PDF.
    Si keep_numeric, laisse les valeur numeriques telles quelles (pour export Excel)
    """
    if val is None:
        return 'ABS'
    if val == NOTES_NEUTRALISE:
        return 'EXC' # excuse, note neutralise
    if val == NOTES_ATTENTE:
        return 'ATT' # attente, note neutralisee
    if type(val) == type(0.0) or type(val) == type(1):
        if note_max != None:
            val = val * 20. / note_max
        if keep_numeric:
            return val
        else:
            s = '%2.2f' % round(float(val),2) # 2 chiffres apres la virgule
            s = '0'*(5-len(s)) + s
            return s
    else:
        return val.replace('NA0', '-')  # notes sans le NA0

class NotesTable:
    """Une NotesTable représente un tableau de notes pour un semestre de formation.
    Les colonnes sont des modules.
    Les lignes des étudiants.
    On peut calculer les moyennes par étudiant (pondérées par les coefs)
    ou les moyennes par module.

    Attributs publics (en lecture):
    - inscrlist: étudiants inscrits à ce semestre, par ordre alphabétique
    - identdict: { etudid : ident }
    - sem : le formsemestre
    get_table_moyennes_triees: [ (moy_gen, moy_ue1, moy_ue2, ... moy_ues, moy_mod1, ..., moy_modn, etudid) ] 
    (où toutes les valeurs sont formatéees (fmt_note), incluant les UE de sport

    Attributs privés:
    - _modmoys : { moduleimpl_id : { etudid: note_moyenne_dans_ce_module } }
    - _ues : liste des UE de ce semestre
    
    """
    def __init__(self, znotes, formsemestre_id):
        #open('/tmp/cache.log','a').write('NotesTables(%s)\n' % formsemestre_id) # XXX DEBUG
        if not formsemestre_id:
            raise ScoValueError('invalid formsemestre_id (%s)' % formsemestre_id)
        self.znotes = znotes
        self.formsemestre_id = formsemestre_id
        cnx = znotes.GetDBConnexion()
        self.sem = znotes.get_formsemestre(formsemestre_id)
        # Infos sur les etudiants
        self.inscrlist = znotes.do_formsemestre_inscription_list(
            args = { 'formsemestre_id' : formsemestre_id })
        # infos identite etudiant
        # xxx sous-optimal: 1/select par etudiant -> 0.17" pour identdict sur GTR1 !
        self.identdict = {} # { etudid : ident }
        self.inscrdict = {} # { etudid : inscription }
        for x in self.inscrlist:
            i = scolars.etudident_list( cnx, { 'etudid' : x['etudid'] } )[0]
            self.identdict[x['etudid']] = i
            self.inscrdict[x['etudid']] = x
            x['nom'] = i['nom'] # pour tri
        # Tri les etudids par NOM
        self.inscrlist.sort( lambda x,y: cmp(x['nom'],y['nom']) )
        # { etudid : rang dans l'ordre alphabetique }
        rangalpha = {}
        for i in range(len(self.inscrlist)):
            rangalpha[self.inscrlist[i]['etudid']] = i
        # Notes dans les modules  { moduleimpl_id : { etudid: note_moyenne_dans_ce_module } }
        self._modmoys, self._modimpls, valid_evals, mods_att =\
                       znotes.do_formsemestre_moyennes(formsemestre_id)
        self._mods_att = mods_att # liste des modules avec des notes en attente
        self._valid_evals = {} # { evaluation_id : eval }
        for e in valid_evals:
            self._valid_evals[e['evaluation_id']] = e
        # Liste des modules et UE
        uedict = {}
        for modimpl in self._modimpls:
            mod = znotes.do_module_list(args={'module_id' : modimpl['module_id']} )[0]
            modimpl['module'] = mod # add module dict to moduleimpl
            ue = znotes.do_ue_list(args={'ue_id' : mod['ue_id']})[0]
            modimpl['ue'] = ue # add ue dict to moduleimpl            
            uedict[ue['ue_id']] = ue
            mat = znotes.do_matiere_list(args={'matiere_id': mod['matiere_id']})[0]
            modimpl['mat'] = mat # add matiere dict to moduleimpl 
            # calcul moyennes du module et stocke dans le module
            #nb_inscrits, nb_notes, nb_abs, nb_neutre, moy, median, last_modif=

        # Decisions jury et UE capitalisées
        self.comp_decisions_jury()
        self.comp_ue_capitalisees()

        # Liste des moyennes de tous, en chaines de car., triées
        self._ues = uedict.values()
        self._ues.sort( lambda x,y: cmp( x['numero'], y['numero'] ) )
        T = []
        self.comp_ue_coefs()
        self.moy_gen = {} # etudid : moy gen (avec UE capitalisées)
        self.moy_ue = {} # ue_id : { etudid : moy ue }
        self._etud_moycoef_ue = {} # { etudid : { ue_id : (moy, coef) } }
        self.etud_ues_status = {} # { etudid : { ue_id : {...status...} } }
        for etudid in self.get_etudids():
            self._etud_moycoef_ue[etudid] = self.comp_etud_moy_ues(etudid)
            self.etud_ues_status[etudid] = self.comp_etud_ues_status(etudid)
            moy_gen = self.comp_etud_moy(etudid, with_capitalized_ue=True)[0]
            self.moy_gen[etudid] = moy_gen
            moy_ues = []
            for ue in self._ues:
                ue_status = self.etud_ues_status[etudid]
                if ue_status[ue['ue_id']]['is_capitalized']:
                    moy_ue = ue_status[ue['ue_id']]['moy_ue']
                    moy_ues.append(fmt_note(moy_ue))
                else:
                    moy_ue = self._etud_moycoef_ue[etudid][ue['ue_id']][0]
                    moy_ues.append(fmt_note(moy_ue))
                if not self.moy_ue.has_key(ue['ue_id']):
                    self.moy_ue[ue['ue_id']] = {}
                self.moy_ue[ue['ue_id']][etudid] = moy_ue
            t = [fmt_note(moy_gen)] + moy_ues
            #
            is_cap = {} # ue_id : is_capitalized
            ue_status = self.etud_ues_status[etudid]
            for ue in self._ues:
                is_cap[ue['ue_id']] = ue_status[ue['ue_id']]['is_capitalized']                
            for modimpl in self._modimpls:
                val = self.get_etud_mod_moy(modimpl, etudid)
                if is_cap[modimpl['module']['ue_id']]:
                    t.append('-c-')
                else:
                    t.append(fmt_note(val))
            #
            t.append(etudid)
            T.append(tuple(t))
        # tri par moyennes décroissantes,
        # en laissant les demissionnaires a la fin, par ordre alphabetique
        def cmprows(x,y):
            try:
                return cmp(float(y[0]), float(x[0])) # moy. gen.
            except:
                vx, vy = x[0], y[0]
                try:
                    vx = float(vx)
                except:
                    pass
                try:
                    vy = float(vy)
                except:
                    pass
                if (type(vx) == type(vy)): # and type(vx) == StringType:
                    # rang alphabetique par nom
                    return rangalpha[x[-1]] - rangalpha[y[-1]]
                else:
                    return cmp(type(vx),type(vy))
        T.sort(cmprows)
        self.T = T
        
        # calcul rangs (/ moyenne generale)
        self.rangs = {} # { etudid : rangs } (rang est une chaine)
        nb_ex = 0 # nb d'ex-aequo consécutifs en cours
        for i in range(len(T)):
            # test ex-aequo
            if i < len(T)-1:
                next = T[i+1][0]
            else:
                next = None
            moy = T[i][0]
            if nb_ex:
                srang = '%d ex' % (i+1-nb_ex)
                if moy == next:
                    nb_ex += 1
                else:
                    nb_ex = 0
            else:
                if moy == next:
                    srang = '%d ex' % (i+1-nb_ex)
                    nb_ex = 1
                else:
                    srang = '%d' % (i+1)                        
            self.rangs[T[i][-1]] = srang # str(i+1)
        #
        self.compute_moy_moy()
        
    def get_etudids(self, sorted=False):
        if sorted:
            # Tri par moy. generale décroissante
            return [ x[-1] for x in self.T ]
        else:
            # Tri par ordre alphabetique de NOM
            return [ x['etudid'] for x in self.inscrlist ]

    def get_sexnom(self,etudid):
        return self.identdict[etudid]['sexe'] + ' ' + self.identdict[etudid]['nom'].upper()
    def get_nom_short(self, etudid):
        "formatte nom d'un etud (pour table recap)"
        return self.identdict[etudid]['nom'].upper() + ' ' + self.identdict[etudid]['prenom'].upper()[0] + '.'

    def get_groupetd(self,etudid):
        "groupe de TD de l'etudiant dans ce semestre"
        return self.inscrdict[etudid]['groupetd']

    def get_etud_etat(self, etudid):
        "Etat de l'etudiant: 'I', 'D' ou '' (si pas connu dans ce semestre)"
        if self.inscrdict.has_key(etudid):
            return self.inscrdict[etudid]['etat']
        else:
            return ''
    
    def get_etud_etat_html(self, etudid):
        etat = self.inscrdict[etudid]['etat']
        if etat == 'I':
            return ''
        elif etat == 'D':
            return ' <font color="red">(DEMISSIONNAIRE)</font> '
        else:
            return ' <font color="red">(%s)</font> ' % etat
        
    def get_ues(self, filter_sport=False, filter_empty=False, etudid=None):
        """liste des ue, ordonnée par numero.
        Si filter_empty, retire les UE où l'etudiant n'a pas de notes.
        Si filter_sport, retire les UE de tupe SPORT
        """
        if not filter_sport and not filter_empty:
            return self._ues
        
        if filter_sport:
            ues_src = [ ue for ue in self._ues if ue['type'] != UE_SPORT ]
        else:
            ues_src = self._ues
        if not filter_empty:
            return ues_src
        ues = []
        for ue in ues_src:
            if self.get_etud_ue_status(etudid,ue['ue_id'])['is_capitalized']:
                # garde toujours les UE capitalisees
                has_note = True
            else:
                has_note = False                
                # verifie que l'etud. est inscrit a au moins un module de l'UE
                # (en fait verifie qu'il a une note)
                modimpls = self.get_modimpls( ue['ue_id'] )

                for modi in modimpls:
                    moy = self.get_etud_mod_moy(modi, etudid)
                    try:
                        float(moy)
                        has_note = True
                        break
                    except:
                        pass
            if has_note:
                ues.append(ue)
        return ues
    
    def get_modimpls(self, ue_id=None):
        "liste des modules pour une UE (ou toutes si ue_id==None)"
        if ue_id is None:
            r = self._modimpls
        else:
            r = [ m for m in self._modimpls if m['ue']['ue_id'] == ue_id ]
        # trie la liste par ue.numero puis mat.numero puis mod.numero
        r.sort( lambda x,y:
                cmp( x['ue']['numero']*1000000 + x['mat']['numero']*1000 + x['module']['numero'],
                     y['ue']['numero']*1000000 + y['mat']['numero']*1000 + y['module']['numero'] ) )
        return r

    def get_etud_eval_note(self,etudid, evaluation_id):
        "note d'un etudiant a une evaluation"
        return self._valid_evals[evaluation_id]['notes'][etudid]

    def get_evals_in_mod(self, moduleimpl_id):
        "liste des evaluations valides dans un module"
        return [ e for e in self._valid_evals.values() if e['moduleimpl_id'] == moduleimpl_id ]
    def get_mod_moy(self, moduleimpl_id):
        """moyenne generale pour un module
        Ne prend en compte que les evaluations où toutes les notes sont entrées
        """
        nb_notes = 0
        sum_notes = 0.
        nb_missing = 0
        moys = self._modmoys[moduleimpl_id]
        for etudid in self.get_etudids():
            val = moys.get(etudid, None) # None si non inscrit
            try:
                sum_notes += val
                nb_notes = nb_notes + 1
            except:
                nb_missing = nb_missing + 1
        if nb_notes > 0:
            moy = sum_notes/nb_notes 
        else:
            moy = 'NA'
        return moy, nb_notes, nb_missing

    def compute_moy_moy(self):
        """precalcule les moyennes d'UE et generale (moyennes sur tous
        les etudiants), et les stocke dans self.moy_moy, self.ue['moy']

        Les moyennes d'UE ne tiennent pas compte des capitalisations.
        """
        ues = self.get_ues()
        sum_moy = 0
        nb_moy = 0
        for ue in ues:
            ue['sum_moy'] = 0
            ue['nb_moy'] = 0
        T = self.get_table_moyennes_triees()
        for t in T:
            etudid = t[-1]
            try:
                sum_moy += float(t[0])
                nb_moy += 1
            except:
                pass
            i = 0
            for ue in ues:
                i += 1
                try:
                    ue['sum_moy'] += float(t[i])
                    ue['nb_moy']  += 1
                except:
                    pass
        if nb_moy > 0:
            self.moy_moy = sum_moy / nb_moy
        else:
            self.moy_moy = '-'
        i = 0
        for ue in ues:
            i += 1
            if ue['nb_moy'] > 0:
                ue['moy'] = ue['sum_moy'] / ue['nb_moy']
            else:
                ue['moy'] = ''
        

    def get_etud_mod_moy(self, modimpl, etudid):
        """moyenne d'un etudiant dans un module (ou NI si non inscrit)"""        
        return self._modmoys[modimpl['moduleimpl_id']].get(etudid, 'NI')
    
    def comp_etud_moy(self, etudid, ue_id=None, with_capitalized_ue = False):
        """Calcule moyenne gen. pour un etudiant dans une UE (ou toutes si ue_id==None)
        Ne prend en compte que les evaluations où toutes les notes sont entrées
        Return: (moy, nb_notes, nb_missing, sum_coef)
        Si pas de notes, moy == 'NA' et sum_coefs==0

        Ne tient pas compte des UE capitalisées, sauf si with_capitalized_ue True.
        """
        modimpls = self.get_modimpls(ue_id)
        nb_notes = 0
        sum_notes = 0.
        sum_coefs = 0.
        nb_missing = 0
        sum_notes_sport = 0.
        sum_coef_sport = 0.
        if with_capitalized_ue:
            ues_status = self.etud_ues_status[etudid] # { ue_id : ... }
        for modimpl in modimpls:
            mod_ue_id = modimpl['ue']['ue_id']
            if (not with_capitalized_ue) or not ues_status[mod_ue_id]['is_capitalized']:
                # module ne faisant pas partie d'une UE capitalisee
                val = self._modmoys[modimpl['moduleimpl_id']].get(etudid, 'NI')
                # si 'NI' probablement etudiant non inscrit a ce module
                if modimpl['ue']['type'] == UE_STANDARD:
                    coef = modimpl['module']['coefficient']
                    try:
                        sum_notes += val * coef
                        sum_coefs += coef
                        nb_notes = nb_notes + 1
                    except:
                        nb_missing = nb_missing + 1
                elif modimpl['ue']['type'] == UE_SPORT:
                    # la note du module de sport agit directement sur la moyenne gen.
                    try:
                        sum_notes_sport += val * coef
                        sum_coef_sport += coef
                    except:
                        pass
                else:
                    raise ScoValueError("type d'UE inconnu (%s)"%modimpl['ue']['type'])
        # Ajoute les UE capitalisées:
        if with_capitalized_ue:
            for ueid in ues_status.keys():
                ue_status = ues_status[ueid]
                if ue_status['is_capitalized']:
                    try:
                        sum_notes += ue_status['moy_ue'] * self.ue_coefs[ueid]
                        sum_coefs += self.ue_coefs[ueid]
                    except: # pas de note dans cette UE
                        pass
        # Calcul moyenne:
        if sum_coefs > 0:
            moy = sum_notes / sum_coefs
            # la note de sport n'est prise en compte que sur la moy. gen.
            if not ue_id:
                if sum_coef_sport > 0:
                    note_sport = sum_notes_sport / sum_coef_sport
                    # regle de calcul maison:
                    if note_sport > 10.:
                        bonus = (note_sport - 10.) / 20.
                        moy += bonus
        else:
            moy = 'NA'
        return moy, nb_notes, nb_missing, sum_coefs

    def comp_etud_moy_ues(self, etudid):
        """Calcule les moyennes d'UE
        Returns: { ue_id : (moy, coef) }
        Le coef est la somme des coefs modules où on a une note dans cette UE.

        Ne tient pas compte ici des UE capitalisées.

        Nota: le coef d'une UE peut ainsi varier, si l'étudiant est
        absent excusé dans certains modules.
        """
        d = {}
        for ue in self._ues:
            ue_id = ue['ue_id']
            moy_ue, junk, junk, sum_coefs = self.comp_etud_moy(etudid, ue_id=ue_id)
            d[ue_id] = (moy_ue, sum_coefs)
        return d
    
    def get_etud_moy_gen(self, etudid):
        """Moyenne generale de cet etudiant dans ce semestre.
        Prend en compte les UE capitalisées.
        """
        return self.moy_gen[etudid]

    def etud_count_ues_under_threshold(self, etudid, threshold=NOTES_BARRE_UE):
        """Nombre d'UE < barre
        Prend en compte les éventuelles UE capitalisées.
        """
        n = 0
        for ue in self._ues:
            ue_status = self.get_etud_ue_status(etudid, ue['ue_id'])
            if ue_status['coef_ue'] > 0 and ue_status['moy_ue'] < NOTES_BARRE_UE:
                n += 1
        return n

    def etud_has_all_ue_over_threshold(self, etudid, threshold=NOTES_BARRE_UE):
        """True si moyenne d'UE toutes > à 8
        Prend en compte les éventuelles UE capitalisées.
        """
        return self.etud_count_ues_under_threshold(etudid, threshold=threshold) == 0
        
    def get_table_moyennes_triees(self):
        return self.T
    def get_etud_rang(self, etudid):
        return self.rangs[etudid]

    def get_table_moyennes_dict(self):
        """{ etudid : (liste des moyennes) } comme get_table_moyennes_triees
        """
        D = {}
        for t in self.T:
            D[t[-1]] = t
        return D

    def get_moduleimpls_attente(self):
        "Liste des moduleimpls avec des notes en attente"
        return self._mods_att
    
    # Decisions existantes du jury
    def comp_decisions_jury(self):
        """Cherche les decisions du jury pour le semestre (pas les UE).
        Calcule l'attribut:
        decisions_jury = { etudid : { 'code' : None|'ATT'|..., 'assidu' : 0|1 }}
        decision_jury_ues={ etudid : { ue_id : { 'code' : Note|ADM|CMP, 'event_date' }}}
        Si la decision n'a pas été prise, la clé etudid n'est pas présente.
        """
        cnx = self.znotes.GetDBConnexion()
        cursor = cnx.cursor()
        cursor.execute("select etudid, code, assidu, compense_formsemestre_id, event_date from scolar_formsemestre_validation where formsemestre_id=%(formsemestre_id)s and ue_id is NULL;",
                       {'formsemestre_id' : self.formsemestre_id} )
        decisions_jury = {}
        for (etudid, code, assidu, compense_formsemestre_id, event_date) in cursor.fetchall():
            decisions_jury[etudid] = {'code' : code, 'assidu' : assidu,
                                      'compense_formsemestre_id' : compense_formsemestre_id,
                                      'event_date' : DateISOtoDMY(event_date) }
        self.decisions_jury = decisions_jury
        # UEs:
        cursor.execute("select etudid, ue_id, code, event_date from scolar_formsemestre_validation where formsemestre_id=%(formsemestre_id)s and ue_id is not NULL;",
                       {'formsemestre_id' : self.formsemestre_id} )
        decisions_jury_ues = {}
        for (etudid, ue_id, code, event_date) in cursor.fetchall():
            if not decisions_jury_ues.has_key(etudid):
                decisions_jury_ues[etudid] = {}
            decisions_jury_ues[etudid][ue_id] = {'code' : code, 
                                                 'event_date' : DateISOtoDMY(event_date)}
        self.decisions_jury_ues = decisions_jury_ues
    
    def get_etud_decision_sem(self, etudid):
        """Decision du jury prise pour cet etudiant, ou None s'il n'y en pas eu.
        { 'code' : None|'ATT'|..., 'assidu' : 0|1, 'event_date' : }
        """        
        return self.decisions_jury.get(etudid, None)

    def get_etud_decision_ues(self, etudid):
        """Decisions du jury pour les UE de cet etudiant, ou None s'il n'y en pas eu.
        { ue_id : { 'code' : ADM|CMP|AJ, 'event_date' : }
        """
        return self.decisions_jury_ues.get(etudid, None)

    # Capitalisation des UEs
    def comp_ue_capitalisees(self):
        """Cherche pour chaque etudiants ses UE capitalisées dans ce semestre.
        Calcule l'attribut:
        ue_capitalisees = { etudid :
                             [{ 'moy_ue':, 'event_date' : ,'formsemestre_id' : }, ...] }
        """
        self.ue_capitalisees = DictDefault(defaultvalue=[])
        for etudid in self.get_etudids():
            capital = formsemestre_get_etud_capitalisation(self.znotes, self.sem, etudid)
            for ue_capital in capital:
                self.ue_capitalisees[etudid].append(ue_capital)
    
    def comp_ue_coefs(self):
        """Les coefficients sont attribués aux modules, pas aux UE.
        Cependant, pour insérer une UE capitalisée dans un autre semestre,
        il faut lui attribuer un coefficient.
        Le coef. d'une UE est ici calculé comme la somme des coefs des
        modules qui la composent dans le programme.
        Calcule l'attribut: ue_coefs = { ue_id : coef }
        """
        self.ue_coefs = {}
        for ue_id in [ ue['ue_id'] for ue in self.get_ues()]:
            self.ue_coefs[ue_id] = sum(
                [ mod['module']['coefficient']
                  for mod in self._modimpls
                  if mod['module']['ue_id'] == ue_id ] )

    def comp_etud_ues_status(self, etudid):
        """Calcule des moyennes d'UE "capitalisees".
        Prend en compte dans chaque UE la moyenne la plus favorable.
        Returns:
        { ue_id : {
             'moy_ue' : , 'coef_ue' : , # avec capitalisation eventuelle
             'cur_moy_ue' : , 'cur_coef_ue' # dans ce sem., sans capitalisation
             'is_capitalized' : True|False,
             'formsemestre_id' : (si capitalisee),
             'event_date' : (si capitalisee)
             }
        }
        """
        d = {}
        for ue in self.get_ues():
            ue_id=ue['ue_id']
            cur_moy_ue, cur_coef_ue = self._etud_moycoef_ue[etudid][ue_id]
            is_capitalized = False
            formsemestre_id = None
            event_date = None
            # compare aux UE capitalisées
            max_moy_ue = cur_moy_ue
            coef_ue = cur_coef_ue
            for ue_cap in self.ue_capitalisees[etudid]:
                if ue_cap['ue_code'] == ue['ue_code']:
                    # Retrouve la moyenne de l'UE capitalisee
                    # ce qui demande de construire le semestre correspondant
                    # qui est la plupart du temps dans le cache
                    nt_cap = self.znotes._getNotesCache().get_NotesTable(self.znotes, ue_cap['formsemestre_id'] )
                    moy_ue_cap = nt_cap.get_etud_ue_status(etudid, ue_cap['ue_id'])['moy_ue']
                    if (coef_ue <= 0) or (moy_ue_cap > max_moy_ue):
                        max_moy_ue = moy_ue_cap
                        is_capitalized = True
                        formsemestre_id = ue_cap['formsemestre_id']
                        event_date = ue_cap['event_date']
                        coef_ue = self.ue_coefs[ue_id]
            d[ue_id] = {
                'moy_ue' : max_moy_ue,
                'coef_ue' : coef_ue, # coef reel ou coef de l'ue si capitalisee
                'cur_moy_ue' : cur_moy_ue,
                'cur_coef_ue' : cur_coef_ue,
                'is_capitalized' : is_capitalized }
            if is_capitalized:
                d[ue_id]['formsemestre_id'] = formsemestre_id
                d[ue_id]['event_date'] = event_date
        #if etudid=='10500853': # YYY
        #    pdb.set_trace()
        return d

    def get_etud_ue_status(self, etudid, ue_id):
        "Etat de cette UE (note, coef, capitalisation, ...)"
        return self.etud_ues_status[etudid][ue_id]


class CacheNotesTable:
    """gestion rudimentaire de cache pour les NotesTables"""
    def __init__(self):
        log('new CacheTable (id=%s)' % id(self))
        # Cache des NotesTables
        self.cache = {} # { formsemestre_id : NoteTable instance }
        # Cache des classeur PDF (bulletins)
        self.pdfcache = {} # { formsemestre_id : (filename, pdfdoc) }
    
    def get_NotesTable(self, znotes, formsemestre_id):
        if self.cache.has_key(formsemestre_id):
            log('cache hit %s (id=%s)' % (formsemestre_id, id(self)))
            return self.cache[formsemestre_id]
        else:
            nt = NotesTable( znotes, formsemestre_id)
            self.cache[formsemestre_id] = nt
            log('caching formsemestre_id=%s (id=%s)' % (formsemestre_id,id(self)) ) 
            return nt

    def get_cached_formsemestre_ids(self):
        "List of currently cached formsemestre_id"
        return self.cache.keys() 
    
    def inval_cache(self, znotes, formsemestre_id=None, pdfonly=False):
        "expire cache pour un semestre (ou tous si pas d'argument)"
        log('inval_cache, formsemestre_id=%s pdfonly=%s (id=%s)' %
            (formsemestre_id,pdfonly,id(self)))
        if not hasattr(self,'pdfcache'):
            self.pdfcache = {} # fix for old zope instances...
        if formsemestre_id is None:
            # clear all caches
            if not pdfonly:
                self.cache = {}
            self.pdfcache = {}
        else:
            # formsemestre_id modifié:
            # on doit virer formsemestre_id et tous les semestres
            # susceptibles d'utiliser des UE capitalisées de ce semestre.
            to_trash = [formsemestre_id] + list_formsemestre_utilisateurs_uecap(znotes, formsemestre_id)
            log('to_trash: ' + str(to_trash) )
            if not pdfonly:
                for formsemestre_id in to_trash:
                    if self.cache.has_key(formsemestre_id):
                        del self.cache[formsemestre_id]
            for formsemestre_id in to_trash:
                if self.pdfcache.has_key(formsemestre_id):
                    del self.pdfcache[formsemestre_id]

    def store_bulletins_pdf(self, formsemestre_id, version, (filename,pdfdoc) ):
        "cache pdf data"
        log('caching PDF formsemestre_id=%s version=%s (id=%s)'
            % (formsemestre_id, version, id(self)) )
        self.pdfcache[(formsemestre_id,version)] = (filename,pdfdoc)

    def get_bulletins_pdf(self, formsemestre_id, version):
        "returns cached PDF, or None if not in the cache"
        if not hasattr(self,'pdfcache'):
            self.pdfcache = {} # fix for old zope instances...
        return self.pdfcache.get((formsemestre_id,version), None)

#
# Cache global: chaque instance, repérée par son URL, a un cache
# qui est recréé à la demande (voir ZNotes._getNotesCache() )
#
GLOBAL_NOTES_CACHE = {} # { URL : CacheNotesTable instance }
