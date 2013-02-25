# -*- mode: python -*-
# -*- coding: iso8859-15 -*-

##############################################################################
#
# Gestion scolarite IUT
#
# Copyright (c) 2001 - 2012 Emmanuel Viennet.  All rights reserved.
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

"""Génération du bulletin en format JSON (beta, non completement testé)

"""

from notes_table import *
import sco_photos
import ZAbsences
import sco_bulletins

# -------- Bulletin en JSON


import mx
class ScoDocJSONEncoder(json.JSONEncoder):
    def default(self, o):
        # horrible hack pour encoder les dates
        if str(type(o)) == "<type 'mx.DateTime.DateTime'>":
            return o.strftime("%Y-%m-%dT%H:%M:%S") 
        else:
            log('not mx: %s' % type(o))
            return json.JSONEncoder.default(self, o)

def make_json_formsemestre_bulletinetud(
        context, formsemestre_id,  etudid, REQUEST=None,
        xml_with_decisions=False, version='long'):
    """Renvoie bulletin en chaine JSON"""
    
    d = formsemestre_bulletinetud_published_dict(
        context, formsemestre_id,  etudid, REQUEST=REQUEST,
        xml_with_decisions=xml_with_decisions, version=version)
    
    if REQUEST:
        REQUEST.RESPONSE.setHeader('content-type', JSON_MIMETYPE)
        
    return json.dumps(d, cls=ScoDocJSONEncoder, encoding=SCO_ENCODING)


# (fonction séparée: n'utilise pas formsemestre_bulletinetud_dict()
#   pour simplifier le code, mais attention a la maintenance !)
#
def formsemestre_bulletinetud_published_dict(
        context, formsemestre_id, etudid,
        force_publishing=False,
        xml_nodate=False,
        REQUEST=None,
        xml_with_decisions=False, # inclue les decisions même si non publiées
        version='long'
        ):
    """Dictionnaire representant les informations _publiees_ du bulletin de notes
    Utilisé pour JSON, devrait l'être aussi pour XML. (todo)
    """
    
    d = {}
    
    sem = context.get_formsemestre(formsemestre_id)
    if sem['bul_hide_xml'] == '0' or force_publishing:
        published=1
    else:
        published=0
    if xml_nodate:
        docdate = ''
    else:
        docdate = datetime.datetime.now().isoformat()
    
    d.update( etudid=etudid, formsemestre_id=formsemestre_id,
              date=docdate,
              publie=published,
              etape_apo=sem['etape_apo'] or '',
              etape_apo2=sem['etape_apo2'] or '',
              etape_apo3=sem['etape_apo3'] or '')
    
    # Infos sur l'etudiant
    etudinfo = context.getEtudInfo(etudid=etudid,filled=1)[0]
    
    d['etudiant'] = dict(
        etudid=etudid, code_nip=etudinfo['code_nip'], code_ine=etudinfo['code_ine'],
        nom=quote_xml_attr(etudinfo['nom']),
        prenom=quote_xml_attr(etudinfo['prenom']),
        sexe=quote_xml_attr(etudinfo['sexe']),
        photo_url=quote_xml_attr(sco_photos.etud_photo_url(context, etudinfo)),
        email=quote_xml_attr(etudinfo['email']))    
    
    # Disponible pour publication ?
    if not published:
        return doc # stop !
    
    # Groupes:
    partitions = sco_groups.get_partitions_list(context, formsemestre_id, with_default=False)
    partitions_etud_groups = {} # { partition_id : { etudid : group } }
    for partition in partitions:
        pid=partition['partition_id']
        partitions_etud_groups[pid] = sco_groups.get_etud_groups_in_partition(context, pid)
    
    nt = context._getNotesCache().get_NotesTable(context, formsemestre_id) #> toutes notes
    ues = nt.get_ues()
    modimpls = nt.get_modimpls()
    nbetuds = len(nt.rangs)
    mg = fmt_note(nt.get_etud_moy_gen(etudid))
    if nt.get_moduleimpls_attente() or context.get_preference('bul_show_rangs', formsemestre_id) == 0:
        # n'affiche pas le rang sur le bulletin s'il y a des
        # notes en attente dans ce semestre
        rang = ''
        rang_gr = {}
        ninscrits_gr = {}
    else:
        rang = str(nt.get_etud_rang(etudid))
        rang_gr, ninscrits_gr, gr_name = sco_bulletins.get_etud_rangs_groups(
            context, etudid, formsemestre_id, partitions, partitions_etud_groups, nt)
    
    d['note'] = dict( value=mg, min=fmt_note(nt.moy_min), max=fmt_note(nt.moy_max), moy=fmt_note(nt.moy_moy) )
    d['rang'] = dict( value=rang, ninscrits=nbetuds )
    d['rang_group'] = []
    if rang_gr:
        for partition in partitions:            
            d['rang_group'].append( dict(
                group_type=partition['partition_name'],
                group_name=gr_name[partition['partition_id']],
                value=rang_gr[partition['partition_id']],
                ninscrits=ninscrits_gr[partition['partition_id']] ))
    
    d['note_max'] = dict( value=20 ) # notes toujours sur 20
    d['bonus_sport_culture'] = dict( value=nt.bonus[etudid] )
    
    # Liste les UE / modules /evals
    d['ue'] = []
    d['ue_capitalisee'] = []
    for ue in ues:
        ue_status = nt.get_etud_ue_status(etudid, ue['ue_id'])
        u =  dict( id=ue['ue_id'],
                  numero=quote_xml_attr(ue['numero']),
                  acronyme=quote_xml_attr(ue['acronyme']),
                  titre=quote_xml_attr(ue['titre']),      
                  note = dict(value=fmt_note(ue_status['cur_moy_ue']), 
                              min=fmt_note(ue['min']), max=fmt_note(ue['max'])),                            
                  rang = str(nt.ue_rangs[ue['ue_id']][0][etudid]),
                  effectif = str(nt.ue_rangs[ue['ue_id']][1] - nt.nb_demissions)
                )
        d['ue'].append(u) 
        u['module'] = []
        # Liste les modules de l'UE 
        ue_modimpls = [ mod for mod in modimpls if mod['module']['ue_id'] == ue['ue_id'] ]
        for modimpl in ue_modimpls:
            mod_moy = fmt_note(nt.get_etud_mod_moy(modimpl['moduleimpl_id'], etudid))
            if mod_moy == 'NI': # ne mentionne pas les modules ou n'est pas inscrit
                continue
            mod = modimpl['module']
            #if mod['ects'] is None:
            #    ects = ''
            #else:
            #    ects = str(mod['ects'])
            modstat = nt.get_mod_stats(modimpl['moduleimpl_id'])

            m = dict(
                id=modimpl['moduleimpl_id'], code=mod['code'],
                coefficient=mod['coefficient'],
                numero=mod['numero'],
                titre=quote_xml_attr(mod['titre']),
                abbrev=quote_xml_attr(mod['abbrev']),
                # ects=ects, ects des modules maintenant inutilisés
                note = dict( value=mod_moy )
                )
            m['note'].update(modstat)
            for k in ('min', 'max', 'moy'): # formatte toutes les notes
                m['note'][k] = fmt_note(m['note'][k])
            
            u['module'].append(m)
            if context.get_preference('bul_show_mod_rangs', formsemestre_id):            
                m['rang'] = dict( value=nt.mod_rangs[modimpl['moduleimpl_id']][0][etudid] )
                m['effectif'] = dict( value=nt.mod_rangs[modimpl['moduleimpl_id']][1] )
            
            # --- notes de chaque eval:
            evals = nt.get_evals_in_mod(modimpl['moduleimpl_id'])
            m['evaluation'] = []
            if version != 'short':
                for e in evals:
                    if e['visibulletin'] == '1' or version == 'long':
                        val = e['notes'].get(etudid, {'value':'NP'})['value'] # NA si etud demissionnaire
                        val = fmt_note(val, note_max=e['note_max'] )
                        m['evaluation'].append( dict(
                            jour=DateDMYtoISO(e['jour'], null_is_empty=True),
                            heure_debut=TimetoISO8601(e['heure_debut'], null_is_empty=True),
                            heure_fin=TimetoISO8601(e['heure_fin'], null_is_empty=True),
                            coefficient=e['coefficient'],
                            evaluation_type=e['evaluation_type'],
                            description=quote_xml_attr(e['description']),
                            note = val
                            ))
                # Evaluations incomplètes ou futures:
                complete_eval_ids = Set( [ e['evaluation_id'] for e in evals ] )
                if context.get_preference('bul_show_all_evals', formsemestre_id):
                    all_evals = context.do_evaluation_list(args={ 'moduleimpl_id' : modimpl['moduleimpl_id'] })
                    all_evals.reverse() # plus ancienne d'abord
                    for e in all_evals:
                        if e['evaluation_id'] not in complete_eval_ids:
                            m['evaluation'].append( dict(
                                jour=DateDMYtoISO(e['jour'], null_is_empty=True),
                                heure_debut=TimetoISO8601(e['heure_debut'], null_is_empty=True),
                                heure_fin=TimetoISO8601(e['heure_fin'], null_is_empty=True),
                                coefficient=e['coefficient'],
                                description=quote_xml_attr(e['description']),
                                incomplete='1') )
        
        # UE capitalisee (listee seulement si meilleure que l'UE courante)
        if ue_status['is_capitalized']:
            d['ue_capitalisee'].append( dict(
                id=ue['ue_id'],
                numero=quote_xml_attr(ue['numero']),
                acronyme=quote_xml_attr(ue['acronyme']),
                titre=quote_xml_attr(ue['titre']),
                note = fmt_note(ue_status['moy']),
                coefficient_ue = fmt_note(ue_status['coef_ue']),
                date_capitalisation = DateDMYtoISO(ue_status['event_date'])
                ))

    # --- Absences
    if  context.get_preference('bul_show_abs', formsemestre_id):
        debut_sem = DateDMYtoISO(sem['date_debut'])
        fin_sem = DateDMYtoISO(sem['date_fin'])
        AbsEtudSem = ZAbsences.getAbsSemEtud(context, formsemestre_id, etudid)
        nbabs = AbsEtudSem.CountAbs()
        nbabsjust = AbsEtudSem.CountAbsJust()
        
        d['absences'] = dict(nbabs=nbabs, nbabsjust=nbabsjust)
    
    # --- Decision Jury
    if context.get_preference('bul_show_decision', formsemestre_id) or xml_with_decisions:
        infos, dpv = sco_bulletins.etud_descr_situation_semestre(
            context, etudid, formsemestre_id, format='xml',
            show_uevalid=context.get_preference('bul_show_uevalid',formsemestre_id))
        d['situation'] = quote_xml_attr(infos['situation']) 
        if dpv:
            decision = dpv['decisions'][0]
            etat = decision['etat']
            if decision['decision_sem']:
                code = decision['decision_sem']['code']
            else:
                code = ''
            
            d['decision'] = dict( code=code, etat=etat)
            d['decision_ue'] = []
            if decision['decisions_ue']: # and context.get_preference('bul_show_uevalid', formsemestre_id): always publish (car utile pour export Apogee)
                for ue_id in decision['decisions_ue'].keys():                
                    ue = context.do_ue_list({ 'ue_id' : ue_id})[0]
                    d['decision_ue'].append(dict(
                        ue_id=ue['ue_id'],
                        numero=quote_xml_attr(ue['numero']),
                        acronyme=quote_xml_attr(ue['acronyme']),
                        titre=quote_xml_attr(ue['titre']),
                        code=decision['decisions_ue'][ue_id]['code'],
                        ects=quote_xml_attr(ue['ects'] or '')
                        ))
            d['autorisation_inscription'] = []
            for aut in decision['autorisations']:
                d['autorisation_inscription'].append(dict( semestre_id=aut['semestre_id'] ))
        else:
            d['decision'] = dict( code='', etat='DEM' )
    
    # --- Appreciations
    cnx = context.GetDBConnexion() 
    apprecs = scolars.appreciations_list(
        cnx,
        args={'etudid':etudid, 'formsemestre_id' : formsemestre_id } )
    d['appreciation'] = []
    for app in apprecs:
        d['appreciation'].append( dict( comment=quote_xml_attr(app['comment']), date=DateDMYtoISO(app['date'])) )
    
    #
    return d
