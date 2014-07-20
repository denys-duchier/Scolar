# -*- mode: python -*-
# -*- coding: utf-8 -*-

##############################################################################
#
# Gestion scolarite IUT
#
# Copyright (c) 2001 - 2014 Emmanuel Viennet.  All rights reserved.
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
import inspect

import scolars
import sco_groups
from notes_log import log, logCallStack
from sco_utils import *
from notesdb import *
import sco_codes_parcours
from sco_parcours_dut import formsemestre_get_etud_capitalisation
from sco_parcours_dut import list_formsemestre_utilisateurs_uecap
import sco_parcours_dut 
from sco_formsemestre_edit import formsemestre_uecoef_list
import sco_compute_moy
from sco_formulas import NoteVector

# Support for old user-written "bonus" functions with 2 args:
BONUS_TWO_ARGS = len(inspect.getargspec(CONFIG.compute_bonus)[0]) == 2 


def comp_ranks(T):
    """Calcul rangs à partir d'une liste ordonnée de tuples [ (valeur, ..., etudid) ] 
    (valeur est une note numérique), en tenant compte des ex-aequos
    Le resultat est: { etudid : rang } où rang est une chaine decrivant le rang
    """
    rangs = {} # { etudid : rang } (rang est une chaine)
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
        rangs[T[i][-1]] = srang # str(i+1)
    return rangs

class NotesTable:
    """Une NotesTable représente un tableau de notes pour un semestre de formation.
    Les colonnes sont des modules.
    Les lignes des étudiants.
    On peut calculer les moyennes par étudiant (pondérées par les coefs)
    ou les moyennes par module.

    Attributs publics (en lecture):
    - inscrlist: étudiants inscrits à ce semestre, par ordre alphabétique (avec demissions)
    - identdict: { etudid : ident }
    - sem : le formsemestre
    get_table_moyennes_triees: [ (moy_gen, moy_ue1, moy_ue2, ... moy_ues, moy_mod1, ..., moy_modn, etudid) ] 
    (où toutes les valeurs sont formatées (fmt_note), incluant les UE de sport

    - bonus[etudid] : valeur du bonus "sport".

    Attributs privés:
    - _modmoys : { moduleimpl_id : { etudid: note_moyenne_dans_ce_module } }
    - _ues : liste des UE de ce semestre (hors capitalisees)
    - _matmoys : { matiere_id : { etudid: note moyenne dans cette matiere } }
    
    """
    def __init__(self, context, formsemestre_id):
        log('NotesTable( formsemestre_id=%s )' % formsemestre_id)
        #open('/tmp/cache.log','a').write('NotesTables(%s)\n' % formsemestre_id) # XXX DEBUG        
        if not formsemestre_id:
            logCallStack()
            raise ScoValueError('invalid formsemestre_id (%s)' % formsemestre_id)
        self.context = context
        self.formsemestre_id = formsemestre_id
        cnx = context.GetDBConnexion()
        self.sem = context.get_formsemestre(formsemestre_id)
        self.moduleimpl_stats = {} # { moduleimpl_id : {stats} }
        # Infos sur les etudiants
        self.inscrlist = context.do_formsemestre_inscription_list(
            args = { 'formsemestre_id' : formsemestre_id })
        # infos identite etudiant
        # xxx sous-optimal: 1/select par etudiant -> 0.17" pour identdict sur GTR1 !
        self.identdict = {} # { etudid : ident }
        self.inscrdict = {} # { etudid : inscription }
        for x in self.inscrlist:
            i = scolars.etudident_list( cnx, { 'etudid' : x['etudid'] } )[0]
            self.identdict[x['etudid']] = i
            self.inscrdict[x['etudid']] = x
            x['nomp'] = (i['nom_usuel'] or i['nom']) + i['prenom'] # pour tri
        
        # Tri les etudids par NOM
        self.inscrlist.sort( lambda x,y: cmp(x['nomp'],y['nomp']) )
        
        # { etudid : rang dans l'ordre alphabetique }
        rangalpha = {}
        for i in range(len(self.inscrlist)):
            rangalpha[self.inscrlist[i]['etudid']] = i

        self.bonus = DictDefault(defaultvalue=0)
        # Notes dans les modules  { moduleimpl_id : { etudid: note_moyenne_dans_ce_module } }
        self._modmoys, self._modimpls, self._valid_evals_per_mod, valid_evals, mods_att, self.expr_diagnostics =\
            sco_compute_moy.do_formsemestre_moyennes(context, formsemestre_id)
        self._mods_att = mods_att # liste des modules avec des notes en attente
        self._matmoys = {} # moyennes par matieres
        self._valid_evals = {} # { evaluation_id : eval }
        for e in valid_evals:
            self._valid_evals[e['evaluation_id']] = e        # Liste des modules et UE
        uedict = {}
        self.uedict = uedict
        for modimpl in self._modimpls:
            mod = context.do_module_list(args={'module_id' : modimpl['module_id']} )[0]
            modimpl['module'] = mod # add module dict to moduleimpl
            if not mod['ue_id'] in uedict:
                ue = context.do_ue_list(args={'ue_id' : mod['ue_id']})[0]
                uedict[ue['ue_id']] = ue
            else:
                ue = uedict[mod['ue_id']]
            modimpl['ue'] = ue # add ue dict to moduleimpl            
            self._matmoys[mod['matiere_id']] = {}
            mat = context.do_matiere_list(args={'matiere_id': mod['matiere_id']})[0]
            modimpl['mat'] = mat # add matiere dict to moduleimpl 
            # calcul moyennes du module et stocke dans le module
            #nb_inscrits, nb_notes, nb_abs, nb_neutre, moy, median, last_modif=

        self.formation = context.formation_list( args={ 'formation_id' : self.sem['formation_id'] } )[0]
        self.parcours = sco_codes_parcours.get_parcours_from_code(self.formation['type_parcours'])
        
        # Decisions jury et UE capitalisées
        self.comp_decisions_jury()
        self.comp_ue_capitalisees()

        # Liste des moyennes de tous, en chaines de car., triées
        self._ues = uedict.values()
        self._ues.sort( lambda x,y: cmp( x['numero'], y['numero'] ) )
        T = []
        self.comp_ue_coefs(cnx)
        self.moy_gen = {} # etudid : moy gen (avec UE capitalisées)
        self.moy_ue = {} # ue_id : { etudid : moy ue } (valeur numerique)
        valid_moy = [] # liste des valeurs valides de moyenne generale (pour min/max)
        for ue in self._ues:
            self.moy_ue[ue['ue_id']] = {}
        self._etud_moy_ues = {} # { etudid : { ue_id : {'moy', 'sum_coefs', ... } }

        for etudid in self.get_etudids():
            etud_moy_gen = self.comp_etud_moy_gen(etudid, cnx)
            ue_status = etud_moy_gen['moy_ues']
            self._etud_moy_ues[etudid] = ue_status
            
            moy_gen = etud_moy_gen['moy']
            self.moy_gen[etudid] = moy_gen
            if etud_moy_gen['sum_coefs'] > 0:
                valid_moy.append(moy_gen)
            
            moy_ues = []
            for ue in self._ues:
                moy_ue = ue_status[ue['ue_id']]['moy']
                moy_ues.append(fmt_note(moy_ue))
                self.moy_ue[ue['ue_id']][etudid] = moy_ue
            
            t = [fmt_note(moy_gen)] + moy_ues
            #
            is_cap = {} # ue_id : is_capitalized
            for ue in self._ues:
                is_cap[ue['ue_id']] = ue_status[ue['ue_id']]['is_capitalized']                
            
            for modimpl in self.get_modimpls():
                val = self.get_etud_mod_moy(modimpl['moduleimpl_id'], etudid)
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
                    return cmp(type(vy),type(vx))
                    # fallback *** should not occur ***
                    #txt = '\nkey missing in cmprows !!!\nx=%s\ny=%s\n' % (str(x),str(y)) 
                    #txt += '\nrangalpha=%s' % str(rangalpha) + '\n\nT=%s' % str(T)
                    #context.send_debug_alert(txt, REQUEST=None)
                    #return cmp(x,y) 
        T.sort(cmprows)
        self.T = T
        
        if len(valid_moy):
            self.moy_min = min(valid_moy)
            self.moy_max = max(valid_moy)
        else:
            self.moy_min = self.moy_max = 'NA'
        
        # calcul rangs (/ moyenne generale)
        self.rangs = comp_ranks(T)
        self.rangs_groupes = {} # { group_id : { etudid : rang } }  (lazy, see get_etud_rang_group)
        self.group_etuds = {} # { group_id : set of etudids } (lazy, see get_etud_rang_group)

        # calcul rangs dans chaque UE
        ue_rangs = {} # ue_rangs[ue_id] = ({ etudid : rang }, nb_inscrits) (rang est une chaine)
        for ue in self._ues:
            ue_id = ue['ue_id']
            val_ids = [ (self.moy_ue[ue_id][etudid], etudid) for etudid in self.moy_ue[ue_id] ]
            val_ids.sort(cmprows)
            ue_rangs[ue_id] = (comp_ranks(val_ids), len(self.moy_ue[ue_id]))
        self.ue_rangs = ue_rangs
        # ---- calcul rangs dans les modules
        self.mod_rangs = {}
        for modimpl in self._modimpls:
            vals = self._modmoys[modimpl['moduleimpl_id']]
            val_ids = [ (vals[etudid], etudid) for etudid in vals.keys() ]
            val_ids.sort(cmprows)
            self.mod_rangs[modimpl['moduleimpl_id']] = (comp_ranks(val_ids), len(vals))
        #
        self.compute_moy_moy()
        #
        log('NotesTable( formsemestre_id=%s ) done.' % formsemestre_id)
    
    def get_etudids(self, sorted=False):
        if sorted:
            # Tri par moy. generale décroissante
            return [ x[-1] for x in self.T ]
        else:
            # Tri par ordre alphabetique de NOM
            return [ x['etudid'] for x in self.inscrlist ]
    
    def get_sexnom(self,etudid):
        "M. DUPONT"
        etud =  self.identdict[etudid]
        return etud['sexe'] + ' ' + strupper(etud['nom_usuel'] or etud['nom'])
    
    def get_nom_short(self, etudid):
        "formatte nom d'un etud (pour table recap)"
        etud =  self.identdict[etudid]
        # Attention aux caracteres multibytes pour decouper les 2 premiers:
        return strupper(etud['nom_usuel'] or etud['nom']) + ' ' + etud['prenom'].decode(SCO_ENCODING).capitalize()[:2].encode(SCO_ENCODING) + '.'
    
    def get_nom_long(self, etudid):
        "formatte nom d'un etud:  M. Pierre DUPONT"
        etud =  self.identdict[etudid]
        return ' '.join([ scolars.format_sexe(etud['sexe']), scolars.format_prenom(etud['prenom']), scolars.format_nom(etud['nom_usuel'] or etud['nom'])])

    def get_displayed_etud_code(self, etudid):
        'code à afficher sur les listings "anonymes"'
        return self.identdict[etudid]['code_nip'] or self.identdict[etudid]['etudid'] 
    
    def get_etud_etat(self, etudid):
        "Etat de l'etudiant: 'I', 'D', 'DEF' ou '' (si pas connu dans ce semestre)"
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
        elif etat == 'DEF':
            return ' <font color="red">(DEFAILLANT)</font> '
        else:
            return ' <font color="red">(%s)</font> ' % etat
        
    def get_ues(self, filter_sport=False, filter_empty=False, etudid=None):
        """liste des ue, ordonnée par numero.
        Si filter_empty, retire les UE où l'etudiant n'a pas de notes.
        Si filter_sport, retire les UE de type SPORT
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
                    moy = self.get_etud_mod_moy(modi['moduleimpl_id'], etudid)
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
        "liste des modules pour une UE (ou toutes si ue_id==None), triés par matières."
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
    def get_mod_stats(self, moduleimpl_id):
        """moyenne generale, min, max pour un module
        Ne prend en compte que les evaluations où toutes les notes sont entrées
        Cache le resultat.
        """
        if moduleimpl_id in self.moduleimpl_stats:
            return self.moduleimpl_stats[moduleimpl_id]
        nb_notes = 0
        sum_notes = 0.
        nb_missing = 0
        moys = self._modmoys[moduleimpl_id]
        vals = []
        for etudid in self.get_etudids():
            # saute les demissionnaires et les défaillants:
            if self.inscrdict[etudid]['etat'] != 'I':
                continue
            val = moys.get(etudid, None) # None si non inscrit
            try:
                vals.append(float(val))
            except:
                nb_missing = nb_missing + 1
        sum_notes = sum(vals)
        nb_notes = len(vals)
        if nb_notes > 0:
            moy = sum_notes/nb_notes
            max_note, min_note = max(vals), min(vals) 
        else:
            moy, min_note, max_note = 'NA', '-', '-'
        s = { 'moy' : moy, 'max' : max_note, 'min' : min_note,
              'nb_notes' : nb_notes, 'nb_missing' : nb_missing,
              'nb_valid_evals' : len(self._valid_evals_per_mod[moduleimpl_id])
              }
        self.moduleimpl_stats[moduleimpl_id] = s
        return s
    
    def compute_moy_moy(self):
        """precalcule les moyennes d'UE et generale (moyennes sur tous
        les etudiants), et les stocke dans self.moy_moy, self.ue['moy']

        Les moyennes d'UE ne tiennent pas compte des capitalisations.
        """
        ues = self.get_ues()
        sum_moy = 0
        nb_moy = 0
        for ue in ues:
            ue['_notes'] = [] # liste tmp des valeurs de notes valides dans l'ue
        nb_dem = 0 #
        T = self.get_table_moyennes_triees()
        for t in T:
            etudid = t[-1]
            # saute les demissionnaires et les défaillants:
            if self.inscrdict[etudid]['etat'] != 'I':
                if self.inscrdict[etudid]['etat'] == 'D':
                    nb_dem += 1
                continue
            try:
                sum_moy += float(t[0])
                nb_moy += 1
            except:
                pass
            i = 0
            for ue in ues:
                i += 1
                try:
                    ue['_notes'].append(float(t[i]))
                except:
                    pass
        self.nb_demissions = nb_dem
        if nb_moy > 0:
            self.moy_moy = sum_moy / nb_moy
        else:
            self.moy_moy = '-'
        i = 0
        for ue in ues:
            i += 1
            ue['nb_moy'] = len(ue['_notes'])
            if ue['nb_moy'] > 0:
                ue['moy'] = sum(ue['_notes']) / ue['nb_moy']
                ue['max'] = max(ue['_notes'])
                ue['min'] = min(ue['_notes'])
            else:
                ue['moy'], ue['max'], ue['min'] = '', '', ''
            del ue['_notes']
    
    def get_etud_mod_moy(self, moduleimpl_id, etudid):
        """moyenne d'un etudiant dans un module (ou NI si non inscrit)"""        
        return self._modmoys[moduleimpl_id].get(etudid, 'NI')

    def get_etud_mat_moy(self, matiere_id, etudid):
        """moyenne d'un étudiant dans une matière (ou NA si pas de notes)"""
        matmoy = self._matmoys.get(matiere_id, None)
        if not matmoy:
            return 'NM' # non inscrit
            #log('*** oups: get_etud_mat_moy(%s, %s)' % (matiere_id, etudid))
            #raise ValueError('matiere invalide !') # should not occur
        return matmoy.get(etudid, 'NA')
        
    def comp_etud_moy_ue(self, etudid, ue_id=None, cnx=None):
        """Calcule moyenne gen. pour un etudiant dans une UE 
        Ne prend en compte que les evaluations où toutes les notes sont entrées
        Return a dict(moy, nb_notes, nb_missing, sum_coefs)
        Si pas de notes, moy == 'NA' et sum_coefs==0                
        """
        assert ue_id
        modimpls = self.get_modimpls(ue_id)
        nb_notes = 0    # dans cette UE
        sum_notes = 0.
        sum_coefs = 0.
        nb_missing = 0  # nb de modules sans note dans cette UE
        
        notes_bonus_gen = [] # liste des notes de sport et culture
        coefs_bonus_gen = []

        notes = NoteVector()
        coefs = NoteVector()
        coefs_mask = NoteVector() # 0/1, 0 si coef a ete annulé

        matiere_id_last = None
        matiere_sum_notes = matiere_sum_coefs = 0.

        for modimpl in modimpls:
            mod_ue_id = modimpl['ue']['ue_id']
            # module ne faisant pas partie d'une UE capitalisee
            val = self._modmoys[modimpl['moduleimpl_id']].get(etudid, 'NI')
            # si 'NI' probablement etudiant non inscrit a ce module
            coef = modimpl['module']['coefficient']
            if modimpl['ue']['type'] != UE_SPORT:
                notes.append(val, name=modimpl['module']['code'])
                try:
                    sum_notes += val * coef
                    sum_coefs += coef
                    nb_notes = nb_notes + 1
                    coefs.append(coef)
                    coefs_mask.append(1)                    
                    matiere_id = modimpl['module']['matiere_id']
                    if matiere_id_last and matiere_id != matiere_id_last and matiere_sum_coefs:
                        self._matmoys[matiere_id_last][etudid] = matiere_sum_notes / matiere_sum_coefs
                        matiere_sum_notes = matiere_sum_coefs = 0.
                    matiere_sum_notes += val * coef
                    matiere_sum_coefs += coef
                    matiere_id_last = matiere_id                    
                except:
                    nb_missing = nb_missing + 1
                    coefs.append(0)
                    coefs_mask.append(0)
            
            else: # UE_SPORT:
                # la note du module de sport agit directement sur la moyenne gen.
                try:
                    notes_bonus_gen.append(float(val))
                    coefs_bonus_gen.append(coef)
                except:
                    # log('comp_etud_moy_ue: exception: val=%s coef=%s' % (val,coef))
                    pass
        
        if matiere_id_last and matiere_sum_coefs:
            self._matmoys[matiere_id_last][etudid] = matiere_sum_notes / matiere_sum_coefs
        # Calcul moyenne:
        if sum_coefs > 0:
            moy = sum_notes / sum_coefs
            moy_valid = True
        else:
            moy = 'NA'
            moy_valid = False

        # (experimental) recalcule la moyenne en utilisant une formule utilisateur
        expr_diag = {}
        formula = sco_compute_moy.get_ue_expression(self.formsemestre_id, ue_id, cnx)
        if formula:            
            moy = sco_compute_moy.compute_user_formula(
                self.context, self.formsemestre_id, etudid, 
                moy, moy_valid,
                notes, coefs, coefs_mask, formula,
                diag_info=expr_diag)
            if expr_diag:
                expr_diag['ue_id'] = ue_id
                self.expr_diagnostics.append(expr_diag)
        
        return dict(moy=moy, nb_notes=nb_notes, nb_missing=nb_missing, sum_coefs=sum_coefs,
                    notes_bonus_gen=notes_bonus_gen, coefs_bonus_gen=coefs_bonus_gen,
                    expr_diag=expr_diag)

    def comp_etud_moy_gen(self, etudid, cnx):
        """Calcule moyenne gen. pour un etudiant
        Return a dict:
         moy  : moyenne générale
         nb_notes, nb_missing, sum_coefs
         moy_ues : { ue_id : ue_status }
        où ue_status = {
             'moy' : , 'coef_ue' : , # avec capitalisation eventuelle
             'cur_moy_ue' : , 'cur_coef_ue' # dans ce sem., sans capitalisation
             'is_capitalized' : True|False,
             'ects' : nb de crédits ECTS acquis dans cette UE,
             'formsemestre_id' : (si capitalisee),
             'event_date' : (si capitalisee)
             }
        Si pas de notes, moy == 'NA' et sum_coefs==0

        Prend toujours en compte les UE capitalisées.
        """
        # log('comp_etud_moy_gen(etudid=%s)' % etudid)
        moy_ues = {}
        notes_bonus_gen = [] # liste des notes de sport et culture (s'appliquant à la MG)
        coefs_bonus_gen = []
        nb_notes = 0   # nb de notes d'UE (non capitalisees)
        sum_notes = 0. # somme des notes d'UE
        sum_coefs = 0. # somme des coefs d'UE (eux même somme des coefs de modules avec notes)
        nb_missing = 0 # nombre d'UE sans notes
        
        for ue in self.get_ues():
            ue_id = ue['ue_id']
            # - Dans tous les cas, on calcule la moyenne d'UE courante:
            mu = self.comp_etud_moy_ue(etudid, ue_id=ue['ue_id'], cnx=cnx)
            mu['ue'] = ue # infos supplementaires pouvant servir au calcul du bonus sport
            moy_ues[ue['ue_id']] = mu
            
            # - Faut-il prendre une UE capitalisée ?
            max_moy_ue = mu['moy']
            coef_ue = mu['sum_coefs']
            mu['is_capitalized']  = False # l'UE prise en compte est une UE capitalisée
            mu['was_capitalized'] = False # il y a precedemment une UE capitalisée (pas forcement meilleure)
            event_date = None
            for ue_cap in self.ue_capitalisees[etudid]:
                if ue_cap['ue_code'] == ue['ue_code']:
                    moy_ue_cap = ue_cap['moy']
                    mu['was_capitalized'] = True
                    event_date = event_date or ue_cap['event_date']
                    if (coef_ue <= 0) or (moy_ue_cap > max_moy_ue):
                        # meilleure UE capitalisée
                        event_date = ue_cap['event_date']
                        max_moy_ue = moy_ue_cap
                        mu['is_capitalized'] = True
                        capitalized_ue_id = ue_cap['ue_id']
                        formsemestre_id = ue_cap['formsemestre_id']
                        coef_ue = self.ue_coefs[ue_id]
                        
            mu['cur_moy_ue'] = mu['moy'] # la moyenne dans le sem. courant
            mu['cur_coef_ue']= mu['sum_coefs']
            mu['moy'] = max_moy_ue   # la moyenne d'UE a prendre en compte
            
            mu['coef_ue'] = coef_ue # coef reel ou coef de l'ue si capitalisee
            if mu['is_capitalized']:
                mu['formsemestre_id'] = formsemestre_id
                mu['capitalized_ue_id'] = capitalized_ue_id
            if mu['was_capitalized']:
                mu['event_date'] = event_date
            
            # - Calcul moyenne:
            if mu['is_capitalized']:
                try:
                    sum_notes += mu['moy'] * mu['coef_ue']
                    sum_coefs += mu['coef_ue']
                except: # pas de note dans cette UE
                    pass
            else:
                if mu['coefs_bonus_gen']:
                    notes_bonus_gen.extend(mu['notes_bonus_gen'])
                    coefs_bonus_gen.extend(mu['coefs_bonus_gen'])
                #
                try:
                    sum_notes += mu['moy'] * mu['sum_coefs']
                    sum_coefs += mu['sum_coefs']
                    nb_notes = nb_notes + 1
                except TypeError:
                    nb_missing = nb_missing + 1
        # Le resultat:
        infos = dict( nb_notes=nb_notes, nb_missing=nb_missing, 
                      sum_coefs=sum_coefs, moy_ues=moy_ues,
                      sem = self.sem )
        # ---- Calcul moyenne (avec bonus sport&culture)
        if sum_coefs <= 0:
            infos['moy'] = 'NA'
        else:
            infos['moy'] = sum_notes / sum_coefs
            if notes_bonus_gen:
                # regle de calcul maison (configurable, voir bonus_sport.py)
                if sum(coefs_bonus_gen) <= 0 and len(coefs_bonus_gen) != 1:
                    log('comp_etud_moy_gen: invalid or null coefficient (%s) for notes_bonus_gen=%s (etudid=%s, formsemestre_id=%s)'
                        % (coefs_bonus_gen, notes_bonus_gen, etudid, self.formsemestre_id))
                    bonus = 0
                else:
                    if len(coefs_bonus_gen) == 1:
                        coefs_bonus_gen = [1.0] # irrelevant, may be zero
                    
                    if BONUS_TWO_ARGS:
                        # backward compat: compute_bonus took only 2 args
                        bonus = CONFIG.compute_bonus(notes_bonus_gen, coefs_bonus_gen)
                    else:
                        bonus = CONFIG.compute_bonus(notes_bonus_gen, coefs_bonus_gen, infos=infos)
                self.bonus[etudid] = bonus
                infos['moy'] += bonus
                infos['moy'] = min(infos['moy'], 20.) # clip bogus bonus

        return infos
    
    def get_etud_moy_gen(self, etudid):
        """Moyenne generale de cet etudiant dans ce semestre.
        Prend en compte les UE capitalisées.
        """
        return self.moy_gen[etudid]

    def etud_count_ues_under_threshold(self, etudid):
        """Nombre d'UE < barre
        Prend en compte les éventuelles UE capitalisées.
        (les UE sans notes ne sont pas comptées comme sous la barre)
        """
        n = 0
        for ue in self._ues:
            ue_status = self.get_etud_ue_status(etudid, ue['ue_id'])
            if ue_status['coef_ue'] > 0 and type(ue_status['moy']) == FloatType and ue_status['moy'] < self.parcours.get_barre_ue(ue['type']):
                n += 1
        return n

    def etud_has_all_ue_over_threshold(self, etudid):
        """True si moyenne d'UE toutes > à 8 (sauf celles sans notes)
        Prend en compte les éventuelles UE capitalisées.
        """
        return self.etud_count_ues_under_threshold(etudid) == 0
        
    def get_table_moyennes_triees(self):
        return self.T
    def get_etud_rang(self, etudid):
        return self.rangs[etudid]
    def get_etud_rang_group(self, etudid, group_id):
        """Returns rank of etud in this group and number of etuds in group.
        If etud not in group, returns None.
        """
        if not group_id in self.rangs_groupes:
            # lazy: fill rangs_groupes on demand
            # { groupe : { etudid : rang } }
            if not group_id in self.group_etuds:
                # lazy fill: list of etud in group_id
                etuds = sco_groups.get_group_members(self.context, group_id)
                self.group_etuds[group_id] = set( [ x['etudid'] for x in etuds ] )
            # 1- build T restricted to group
            Tr = []
            for t in self.get_table_moyennes_triees():
                t_etudid = t[-1]
                if t_etudid in self.group_etuds[group_id]:
                    Tr.append(t)
            #
            self.rangs_groupes[group_id] = comp_ranks(Tr)
        
        return self.rangs_groupes[group_id].get(etudid, None), len(self.rangs_groupes[group_id])
    
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
        Si l'étudiant est défaillant, met un code DEF sur toutes les UE
        """
        cnx = self.context.GetDBConnexion()
        cursor = cnx.cursor(cursor_factory=ScoDocCursor)
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
            # Calcul des ECTS associes a cette UE:
            ects = 0.
            if sco_codes_parcours.code_ue_validant(code) and self.context.get_preference('ects_mode', self.formsemestre_id) == 'UE':
                ue = self.uedict.get(ue_id, None)
                if ue is None: # not in cache
                    ue = self.context.do_ue_list(args={'ue_id' : ue_id})[0]
                    self.uedict[ue_id] = ue # cache
                ects = ue['ects'] or 0. # 0 if None
            
            decisions_jury_ues[etudid][ue_id] = {
                'code' : code,
                'ects' : ects, # 0. si non UE validée ou si mode de calcul different (?)
                'event_date' : DateISOtoDMY(event_date) }
        
        self.decisions_jury_ues = decisions_jury_ues
    
    def get_etud_decision_sem(self, etudid):
        """Decision du jury prise pour cet etudiant, ou None s'il n'y en pas eu.
        { 'code' : None|'ATT'|..., 'assidu' : 0|1, 'event_date' : , compense_formsemestre_id }
        Si état défaillant, force le code a DEF
        """
        if self.get_etud_etat(etudid) == 'DEF':
            return { 'code' : 'DEF', 'assidu' : 0,
                     'event_date' : '', 'compense_formsemestre_id' : None }
        else:
            return self.decisions_jury.get(etudid, None)

    def get_etud_decision_ues(self, etudid):
        """Decisions du jury pour les UE de cet etudiant, ou None s'il n'y en pas eu.
        { ue_id : { 'code' : ADM|CMP|AJ, 'event_date' : }
        Ne renvoie aucune decision d'UE pour les défaillants
        """
        if self.get_etud_etat(etudid) == 'DEF':
            return {}
        else:
            return self.decisions_jury_ues.get(etudid, None)

    # Capitalisation des UEs
    def comp_ue_capitalisees(self):
        """Cherche pour chaque etudiant ses UE capitalisées dans ce semestre.
        Calcule l'attribut:
        ue_capitalisees = { etudid :
                             [{ 'moy':, 'event_date' : ,'formsemestre_id' : }, ...] }
        """
        self.ue_capitalisees = DictDefault(defaultvalue=[])
        cnx = None
        for etudid in self.get_etudids():
            capital = formsemestre_get_etud_capitalisation(self.context, self.sem, etudid)
            for ue_cap in capital:
                # Si la moyenne d'UE n'avait pas été stockée (anciennes versions de ScoDoc)
                # il faut la calculer ici et l'enregistrer
                if ue_cap['moy_ue'] is None:
                    log('comp_ue_capitalisees: recomputing UE moy (etudid=%s, ue_id=%s formsemestre_id=%s)' % (etudid, ue_cap['ue_id'], ue_cap['formsemestre_id']))
                    nt_cap = self.context._getNotesCache().get_NotesTable(self.context, ue_cap['formsemestre_id'] ) #> UE capitalisees par un etud
                    moy_ue_cap = nt_cap.get_etud_ue_status(etudid, ue_cap['ue_id'])['moy']
                    ue_cap['moy_ue'] = moy_ue_cap
                    if type(moy_ue_cap) == FloatType and moy_ue_cap >= self.parcours.NOTES_BARRE_VALID_UE:
                        if not cnx:
                            cnx = self.context.GetDBConnexion(autocommit=False)
                        sco_parcours_dut.do_formsemestre_validate_ue(cnx, nt_cap, ue_cap['formsemestre_id'], etudid,  ue_cap['ue_id'], ue_cap['code'])
                    else:
                        log('*** valid inconsistency: moy_ue_cap=%s (etudid=%s, ue_id=%s formsemestre_id=%s)' % (moy_ue_cap, etudid, ue_cap['ue_id'], ue_cap['formsemestre_id']))
                ue_cap['moy'] = ue_cap['moy_ue'] # backward compat (needs refactoring)
                self.ue_capitalisees[etudid].append(ue_cap)
        if cnx:
            cnx.commit()
    
    def comp_ue_coefs(self, cnx):
        """Les coefficients sont attribués aux modules, pas aux UE.
        Cependant, pour insérer une UE capitalisée dans un autre semestre,
        il faut lui attribuer un coefficient.
        Le coef. d'une UE est ici calculé comme la somme des coefs des
        modules qui la composent dans le programme,
        sauf si un coefficient a été explicitement déclaré dans
        la table notes_formsemestre_uecoef.
        
        Calcule l'attribut: ue_coefs = { ue_id : coef }
        """
        self.ue_coefs = {}
        for ue_id in [ ue['ue_id'] for ue in self.get_ues()]:
            coefs = formsemestre_uecoef_list(cnx, args={'formsemestre_id' : self.formsemestre_id, 'ue_id' : ue_id })
            if not coefs:
                # calcul automatique du coef en sommant les modules du ce semestre:
                self.ue_coefs[ue_id] = sum(
                    [ mod['module']['coefficient']
                      for mod in self._modimpls
                      if mod['module']['ue_id'] == ue_id ] )
            else:
                # utilisation du coef manuel
                self.ue_coefs[ue_id] = coefs[0]['coefficient']
    
    def get_etud_ue_status(self, etudid, ue_id):
        "Etat de cette UE (note, coef, capitalisation, ...)"
        return self._etud_moy_ues[etudid][ue_id]

    def etud_has_notes_attente(self, etudid):
        """Vrai si cet etudiant a au moins une note en attente dans ce semestre.
        (ne compte que les notes en attente dans des évaluation avec coef. non nul).
        """
        cnx = self.context.GetDBConnexion()
        cursor = cnx.cursor(cursor_factory=ScoDocCursor)
        cursor.execute("select n.* from notes_notes n, notes_evaluation e, notes_moduleimpl m, notes_moduleimpl_inscription i where n.etudid = %(etudid)s and n.value = %(code_attente)s and n.evaluation_id=e.evaluation_id and e.moduleimpl_id=m.moduleimpl_id and m.formsemestre_id=%(formsemestre_id)s and e.coefficient != 0 and m.moduleimpl_id=i.moduleimpl_id and i.etudid=%(etudid)s",
                       {'formsemestre_id' : self.formsemestre_id, 'etudid' : etudid, 'code_attente' : NOTES_ATTENTE} )
        return len(cursor.fetchall()) > 0

import thread
class CacheNotesTable:
    """gestion rudimentaire de cache pour les NotesTables"""

    def __init__(self):
        log('new CacheTable (id=%s)' % id(self))
        #
        self.lock = thread.allocate_lock()
        self.owner_thread = None # thread owning this cache
        self.nref = 0
        # Cache des NotesTables
        self.cache = {} # { formsemestre_id : NoteTable instance }
        # Cache des classeur PDF (bulletins)
        self.pdfcache = {} # { formsemestre_id : (filename, pdfdoc) }
        # Listeners:
        self.listeners = DictDefault(defaultvalue={}) # {formsemestre_id : {listener_id : callback }}

    def acquire(self):
        "If this thread does not own the cache, acquire the lock"
        if thread.get_ident() != self.owner_thread:
            # log('acquire: ident=%s' % thread.get_ident()) # XXX debug
            self.lock.acquire()
            self.owner_thread = thread.get_ident()
            # log('%s got lock' % thread.get_ident()) # XXX debug
        self.nref += 1
        # log('nref=%d' % self.nref)
    
    def release(self):
        "Release the lock"
        if thread.get_ident() != self.owner_thread: # debug
            log('WARNING: release: ident=%s != owner=%s' % (thread.get_ident(), self.owner_thread))
            raise NoteProcessError('problem with notes cache')
        # log('release: ident=%s (nref=%d)' % (thread.get_ident(), self.nref)) 
        self.nref -= 1
        if self.nref == 0:
            self.lock.release()
            self.owner_thread = None
    
    def get_NotesTable(self, context, formsemestre_id): #>
        try:
            self.acquire()
            if self.cache.has_key(formsemestre_id):
                #log('cache hit %s (id=%s, thread=%s)'
                #    % (formsemestre_id, id(self), thread.get_ident()))
                return self.cache[formsemestre_id]
            else:
                t0 = time.time()
                nt = NotesTable( context, formsemestre_id)
                dt = time.time() - t0
                self.cache[formsemestre_id] = nt
                log('caching formsemestre_id=%s (id=%s) (%gs)' % (formsemestre_id,id(self),dt) ) 
                return nt
        finally:
            self.release()
            
    def get_cached_formsemestre_ids(self):
        "List of currently cached formsemestre_id"
        return self.cache.keys() 
    
    def inval_cache(self, context, formsemestre_id=None, pdfonly=False): #>
        "expire cache pour un semestre (ou tous si pas d'argument)"
        log('inval_cache, formsemestre_id=%s pdfonly=%s (id=%s)' % #>
            (formsemestre_id,pdfonly,id(self)))
        try:
            self.acquire()
            if not hasattr(self,'pdfcache'):
                self.pdfcache = {} # fix for old zope instances...
            if formsemestre_id is None:
                # clear all caches
                log('----- inval_cache: clearing all caches -----')
                # logCallStack() # >>> DEBUG <<<
                if not pdfonly:
                    self.cache = {}
                self.pdfcache = {}
                self._call_all_listeners()
                context.get_evaluations_cache().inval_cache()
            else:
                # formsemestre_id modifié:
                # on doit virer formsemestre_id et tous les semestres
                # susceptibles d'utiliser des UE capitalisées de ce semestre.
                to_trash = [formsemestre_id] + list_formsemestre_utilisateurs_uecap(context, formsemestre_id)
                if not pdfonly:
                    for formsemestre_id in to_trash:
                        if self.cache.has_key(formsemestre_id):
                            log('delete %s from cache (id=%s)' % (formsemestre_id, id(self)))
                            del self.cache[formsemestre_id]
                            self._call_listeners(formsemestre_id)
                    context.get_evaluations_cache().inval_cache()
                
                for formsemestre_id in to_trash:
                    for (cached_formsemestre_id, cached_version) in self.pdfcache.keys():
                        if cached_formsemestre_id == formsemestre_id:
                            log('delete pdfcache[(%s,%s)]' % (formsemestre_id,cached_version))
                            del self.pdfcache[(formsemestre_id,cached_version)]
        finally:
            self.release()

    def store_bulletins_pdf(self, formsemestre_id, version, (filename,pdfdoc) ):
        "cache pdf data"
        log('caching PDF formsemestre_id=%s version=%s (id=%s)'
            % (formsemestre_id, version, id(self)) )
        try:
            self.acquire()
            self.pdfcache[(formsemestre_id,version)] = (filename,pdfdoc)
        finally:
             self.release()

    def get_bulletins_pdf(self, formsemestre_id, version):
        "returns cached PDF, or None if not in the cache"
        try:
            self.acquire()
            if not hasattr(self,'pdfcache'):
                self.pdfcache = {} # fix for old zope instances...
            r = self.pdfcache.get((formsemestre_id,version), None)
            if r:
                log('get_bulletins_pdf(%s): cache hit %s (id=%s, thread=%s)'
                    % (version, formsemestre_id, id(self), thread.get_ident()))
            return r
        finally:
             self.release()

    def add_listener(self, callback, formsemestre_id, listener_id):
        """Add a "listener": a function called each time a formsemestre is modified"""
        self.listeners[formsemestre_id][listener_id] = callback
    
    def remove_listener(self, formsemestre_id, listener_id):
        """Remove a listener.
        May raise exception if does not exists.
        """
        del self.listeners[formsemestre_id][listener_id]

    def _call_listeners(self, formsemestre_id):
        for listener_id, callback in self.listeners[formsemestre_id].items():
            callback(listener_id)
    
    def _call_all_listeners(self):
        for formsemestre_id in self.listeners:
            self._call_listeners(formsemestre_id)

#
# Cache global: chaque instance, repérée par sa connexion a la DB, a un cache
# qui est recréé à la demande (voir ZNotes._getNotesCache() )
#
NOTES_CACHE_INST = {} # { db_cnx_string : CacheNotesTable instance }

