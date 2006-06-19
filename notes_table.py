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

import scolars
from notes_log import log

NOTES_PRECISION=1e-4 # evite eventuelles erreurs d'arrondis
NOTES_MIN = 0.       # valeur minimale admise pour une note
NOTES_MAX = 100.
NOTES_NEUTRALISE=-1000. # notes non prises en comptes dans moyennes
NOTES_SUPPRESS=-1001.   # note a supprimer

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
    """Une NotesTable repr�sente un tableau de notes pour un semestre de formation.
    Les colonnes sont des modules.
    Les lignes des �tudiants.
    On peut calculer les moyennes par �tudiant (pond�r�es par les coefs)
    ou les moyennes par module.

    Attributs publics (en lecture):
    - inscrlist: �tudiants inscrits � ce semestre, par ordre alphab�tique
    - identdict: { etudid : ident }
    - 
    """
    def __init__(self, znote, formsemestre_id):
        #open('/tmp/cache.log','a').write('NotesTables(%s)\n' % formsemestre_id) # XXX DEBUG
        if not formsemestre_id:
            raise ScoValueError('invalid formsemestre_id' )
        cnx = znote.GetDBConnexion()
        sem = znote.do_formsemestre_list(args={ 'formsemestre_id' : formsemestre_id})[0]
        # Infos sur les etudiants
        self.inscrlist = znote.do_formsemestre_inscription_list(
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
        # Notes dans les modules  { moduleimpl_id : { etudid: note_moyenne_dans_ce_module } }
        self._modmoys, self._modimpls, valid_evals = znote.do_formsemestre_moyennes(
            formsemestre_id)
        self._valid_evals = {} # { evaluation_id : eval }
        for e in valid_evals:
            self._valid_evals[e['evaluation_id']] = e
        # Liste des modules et UE
        uedict = {}
        for modimpl in self._modimpls:
            mod = znote.do_module_list(args={'module_id' : modimpl['module_id']} )[0]
            modimpl['module'] = mod # add module dict to moduleimpl
            ue = znote.do_ue_list(args={'ue_id' : mod['ue_id']})[0]
            modimpl['ue'] = ue # add ue dict to moduleimpl            
            uedict[ue['ue_id']] = ue
            mat = znote.do_matiere_list(args={'matiere_id': mod['matiere_id']})[0]
            modimpl['mat'] = mat # add matiere dict to moduleimpl 
            # calcul moyennes du module et stocke dans le module
            #nb_inscrits, nb_notes, nb_abs, nb_neutre, moy, median, last_modif=
        #
        # liste des moyennes de tous, en chaines de car., tri�es
        self._ues = uedict.values()
        self._ues.sort( lambda x,y: cmp( x['numero'], y['numero'] ) )
        T = []
        for etudid in self.get_etudids():
            moy_gen = self.get_etud_moy(etudid)[0]
            moy_ues = [ fmt_note(self.get_etud_moy(etudid, ue_id=ue['ue_id'])[0]) for ue in self._ues ]
            t = [fmt_note(moy_gen)] + moy_ues
            for ue in self._ues:
                for modimpl in self._modimpls:
                    if modimpl['module']['ue_id'] == ue['ue_id']:
                        val = self.get_etud_mod_moy(modimpl, etudid)
                        t.append(fmt_note(val))
            t.append(etudid)
            T.append(tuple(t))
        # tri par moyennes d�croissantes
        T.sort()
        T.reverse()
        self.T = T
        # calcul rangs (/ moyenne generale)
        self.rangs = {} # { etudid : rangs } (rang est une chaine)
        nb_ex = 0 # nb d'ex-aequo cons�cutifs en cours
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
        
    def get_etudids(self):
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
        return self.inscrdict[etudid]['etat']
    def get_etud_etat_html(self, etudid):
        etat = self.inscrdict[etudid]['etat']
        if etat == 'I':
            return ''
        elif etat == 'D':
            return ' <font color="red">(DEMISSIONNAIRE)</font> '
        else:
            return ' <font color="red">(%s)</font> ' % etat
    def get_ues(self, filter_sport=False, etudid=None):
        """liste des ue, ordonn�e par numero.
        Si filter_sport, retire les UE "sport" si etudiant pas inscrit.
        """
        if not filter_sport:
            return self._ues
        ues = []
        for ue in self._ues:
            # verifie que l'etud. est inscrit a au moins un module de l'UE
            # (en fait verifie qu'il a une note)
            modimpls = self.get_modimpls( ue['ue_id'] )
            has_note = False
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
        Ne prend en compte que les evaluations o� toutes les notes sont entr�es
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

    def get_etud_mod_moy(self, modimpl, etudid):
        """moyenne d'un etudiant dans un module (ou NI si non inscrit)"""        
        return self._modmoys[modimpl['moduleimpl_id']].get(etudid, 'NI')
    
    def get_etud_moy(self, etudid, ue_id=None):
        """moyenne gen. pour un etudiant dans une UE (ou toutes si ue_id==None)
        Ne prend en compte que les evaluations o� toutes les notes sont entr�es
        Return: (moy, nb_notes, nb_missing)
        """
        modimpls = self.get_modimpls(ue_id)
        nb_notes = 0
        sum_notes = 0.
        sum_coefs = 0.
        nb_missing = 0
        sum_notes_sport = 0.
        sum_coef_sport = 0.
        for modimpl in modimpls:
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
        if sum_coefs > 0:
            moy = sum_notes/ sum_coefs
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
        return moy, nb_notes, nb_missing

    def get_table_moyennes_triees(self):
        return self.T
    def get_etud_rang(self, etudid):
        return self.rangs[etudid]



class CacheNotesTable:
    """gestion rudimentaire de cache pour les NotesTables"""
    def __init__(self):
        log('new CacheTable')
        # Cache des NotesTables
        self.cache = {} # { formsemestre_id : NoteTable instance }
        # Cache des classeur PDF (bulletins)
        self.pdfcache = {} # { formsemestre_id : (filename, pdfdoc) }
    
    def get_NotesTable(self, znote, formsemestre_id):
        if self.cache.has_key(formsemestre_id):
            log('cache hit %s' % formsemestre_id)
            return self.cache[formsemestre_id]
        else:
            nt = NotesTable( znote, formsemestre_id)
            self.cache[formsemestre_id] = nt
            log('caching formsemestre_id=%s' % formsemestre_id ) 
            return nt
    
    def inval_cache(self, formsemestre_id=None, pdfonly=False):
        "expire cache pour un semestre (ou tous si pas d'argument)"
        log('inval_cache, formsemestre_id=%s pdfonly=%s' % (formsemestre_id,pdfonly))
        if not hasattr(self,'pdfcache'):
            self.pdfcache = {} # fix for old zope instances...
        if formsemestre_id is None:
            if not pdfonly:
                self.cache = {}
            self.pdfcache = {}
        else:
            if not pdfonly:
                if self.cache.has_key(formsemestre_id):
                    del self.cache[formsemestre_id]
            if self.pdfcache.has_key(formsemestre_id):
                del self.pdfcache[formsemestre_id]

    def store_bulletins_pdf(self, formsemestre_id, version, (filename,pdfdoc) ):
        "cache pdf data"
        log('caching PDF formsemestre_id=%s version=%s'
            % (formsemestre_id, version) )
        self.pdfcache[(formsemestre_id,version)] = (filename,pdfdoc)

    def get_bulletins_pdf(self, formsemestre_id, version):
        "returns cached PDF, or None if not in the cache"
        if not hasattr(self,'pdfcache'):
            self.pdfcache = {} # fix for old zope instances...
        return self.pdfcache.get((formsemestre_id,version), None)
