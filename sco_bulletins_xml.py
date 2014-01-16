# -*- mode: python -*-
# -*- coding: utf-8 -*-

##############################################################################
#
# Gestion scolarite IUT
#
# Copyright (c) 2001 - 2013 Emmanuel Viennet.  All rights reserved.
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

"""Génération du bulletin en format XML


Note: la structure de ce XML est issue de (mauvais) choix historiques
et ne peut pas être modifiée car d'autres logiciels l'utilisent (portail publication bulletins etudiants).

Je recommande d'utiliser la version JSON.
Malheureusement, le code de génération JSON et XML sont séparés, ce qui est absurde et complique la maintenance (si on ajoute des informations au xbuletins).

Je propose de considérer le XMl comme "deprecated" et de ne plus le modifier, sauf nécessité.
"""

from notes_table import *
import sco_photos
import ZAbsences
import sco_bulletins

# -------- Bulletin en XML
# (fonction séparée: n'utilise pas formsemestre_bulletinetud_dict()
#   pour simplifier le code, mais attention a la maintenance !)
#
def make_xml_formsemestre_bulletinetud(
    context, formsemestre_id, etudid,
    doc=None, # XML document
    force_publishing=False,
    xml_nodate=False,
    REQUEST=None,
    xml_with_decisions=False, # inclue les decisions même si non publiées
    version='long'
    ):
    "bulletin au format XML"
    log('xml_bulletin( formsemestre_id=%s, etudid=%s )' % (formsemestre_id, etudid))
    if REQUEST:
        REQUEST.RESPONSE.setHeader('content-type', XML_MIMETYPE)
    if not doc:            
        doc = jaxml.XML_document( encoding=SCO_ENCODING )
    
    sem = context.get_formsemestre(formsemestre_id)
    if sem['bul_hide_xml'] == '0' or force_publishing:
        published=1
    else:
        published=0
    if xml_nodate:
        docdate = ''
    else:
        docdate = datetime.datetime.now().isoformat()
    
    doc.bulletinetud( etudid=etudid, formsemestre_id=formsemestre_id,
                      date=docdate,
                      publie=published,
                      etape_apo=sem['etape_apo'] or '',
                      etape_apo2=sem['etape_apo2'] or '',
                      etape_apo3=sem['etape_apo3'] or '',
                      etape_apo4=sem['etape_apo4'] or ''
        )

    # Infos sur l'etudiant
    etudinfo = context.getEtudInfo(etudid=etudid,filled=1)[0]
    doc._push()
    doc.etudiant(
        etudid=etudid, code_nip=etudinfo['code_nip'], code_ine=etudinfo['code_ine'],
        nom=quote_xml_attr(etudinfo['nom']),
        prenom=quote_xml_attr(etudinfo['prenom']),
        sexe=quote_xml_attr(etudinfo['sexe']),
        photo_url=quote_xml_attr(sco_photos.etud_photo_url(context, etudinfo)),
        email=quote_xml_attr(etudinfo['email']))    
    doc._pop()

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
    
    doc._push()
    doc.note( value=mg, min=fmt_note(nt.moy_min), max=fmt_note(nt.moy_max), moy=fmt_note(nt.moy_moy) )
    doc._pop()
    doc._push()
    doc.rang( value=rang, ninscrits=nbetuds )
    doc._pop()
    if rang_gr:
        for partition in partitions:
            doc._push()
            doc.rang_group( group_type=partition['partition_name'],
                            group_name=gr_name[partition['partition_id']],
                            value=rang_gr[partition['partition_id']], 
                            ninscrits=ninscrits_gr[partition['partition_id']] )
            doc._pop()
    doc._push()
    doc.note_max( value=20 ) # notes toujours sur 20
    doc._pop()
    doc._push()
    doc.bonus_sport_culture( value=nt.bonus[etudid] )
    doc._pop()
    # Liste les UE / modules /evals
    for ue in ues:
        ue_status = nt.get_etud_ue_status(etudid, ue['ue_id'])
        doc._push()
        doc.ue( id=ue['ue_id'],
                numero=quote_xml_attr(ue['numero']),
                acronyme=quote_xml_attr(ue['acronyme']),
                titre=quote_xml_attr(ue['titre']) )            
        doc._push()
        doc.note( value=fmt_note(ue_status['cur_moy_ue']), 
                  min=fmt_note(ue['min']), max=fmt_note(ue['max']) )
        doc._pop()
        doc._push()
        doc.rang( value=str(nt.ue_rangs[ue['ue_id']][0][etudid]) )
        doc._pop()
        doc._push()
        doc.effectif( value=str(nt.ue_rangs[ue['ue_id']][1] - nt.nb_demissions) )
        doc._pop()
        # Liste les modules de l'UE 
        ue_modimpls = [ mod for mod in modimpls if mod['module']['ue_id'] == ue['ue_id'] ]
        for modimpl in ue_modimpls:
            mod_moy = fmt_note(nt.get_etud_mod_moy(modimpl['moduleimpl_id'], etudid))
            if mod_moy == 'NI': # ne mentionne pas les modules ou n'est pas inscrit
                continue
            mod = modimpl['module']
            doc._push()
            #if mod['ects'] is None:
            #    ects = ''
            #else:
            #    ects = str(mod['ects'])
            doc.module( id=modimpl['moduleimpl_id'], code=mod['code'],
                        coefficient=mod['coefficient'],
                        numero=mod['numero'],
                        titre=quote_xml_attr(mod['titre']),
                        abbrev=quote_xml_attr(mod['abbrev']),
                        # ects=ects ects des modules maintenant inutilisés
                        )
            doc._push()
            modstat = nt.get_mod_stats(modimpl['moduleimpl_id'])
            doc.note( value=mod_moy, 
                      min=fmt_note(modstat['min']), max=fmt_note(modstat['max'])
                      )
            doc._pop()
            if context.get_preference('bul_show_mod_rangs', formsemestre_id):
                doc._push()
                doc.rang( value=nt.mod_rangs[modimpl['moduleimpl_id']][0][etudid] )
                doc._pop()
                doc._push()
                doc.effectif( value=nt.mod_rangs[modimpl['moduleimpl_id']][1] )
                doc._pop()
            # --- notes de chaque eval:
            evals = nt.get_evals_in_mod(modimpl['moduleimpl_id'])
            if version != 'short':
                for e in evals:
                    if e['visibulletin'] == '1' or version == 'long':
                        doc._push()
                        doc.evaluation(jour=DateDMYtoISO(e['jour'], null_is_empty=True),
                               heure_debut=TimetoISO8601(e['heure_debut'], null_is_empty=True),
                               heure_fin=TimetoISO8601(e['heure_fin'], null_is_empty=True),
                               coefficient=e['coefficient'],
                               evaluation_type=e['evaluation_type'],
                               description=quote_xml_attr(e['description']),
                               note_max_origin=e['note_max'] # notes envoyées sur 20, ceci juste pour garder trace
                            )
                        val = e['notes'].get(etudid, {'value':'NP'})['value'] # NA si etud demissionnaire
                        val = fmt_note(val, note_max=e['note_max'] )
                        doc.note( value=val )
                        doc._pop()
                # Evaluations incomplètes ou futures:
                complete_eval_ids = Set( [ e['evaluation_id'] for e in evals ] )
                if context.get_preference('bul_show_all_evals', formsemestre_id):
                    all_evals = context.do_evaluation_list(args={ 'moduleimpl_id' : modimpl['moduleimpl_id'] })
                    all_evals.reverse() # plus ancienne d'abord
                    for e in all_evals:
                        if e['evaluation_id'] not in complete_eval_ids:
                            doc._push()
                            doc.evaluation(jour=DateDMYtoISO(e['jour'], null_is_empty=True),
                                           heure_debut=TimetoISO8601(e['heure_debut'], null_is_empty=True),
                                           heure_fin=TimetoISO8601(e['heure_fin'], null_is_empty=True),
                                           coefficient=e['coefficient'],
                                           description=quote_xml_attr(e['description']),
                                           incomplete='1',
                                           note_max_origin=e['note_max'] # notes envoyées sur 20, ceci juste pour garder trace          
                                )
                            doc._pop()
            doc._pop()
        doc._pop()
        # UE capitalisee (listee seulement si meilleure que l'UE courante)
        if ue_status['is_capitalized']:
            doc._push()
            doc.ue_capitalisee( id=ue['ue_id'],
                                numero=quote_xml_attr(ue['numero']),
                                acronyme=quote_xml_attr(ue['acronyme']),
                                titre=quote_xml_attr(ue['titre']) )
            doc._push()
            doc.note( value=fmt_note(ue_status['moy']) )
            doc._pop()
            doc._push()
            doc.coefficient_ue( value=fmt_note(ue_status['coef_ue']) )
            doc._pop()
            doc._push()
            doc.date_capitalisation(
                value=DateDMYtoISO(ue_status['event_date']) )
            doc._pop()
            doc._pop()
    # --- Absences
    if  context.get_preference('bul_show_abs', formsemestre_id):
        debut_sem = DateDMYtoISO(sem['date_debut'])
        fin_sem = DateDMYtoISO(sem['date_fin'])
        AbsEtudSem = ZAbsences.getAbsSemEtud(context, formsemestre_id, etudid)
        nbabs = AbsEtudSem.CountAbs()
        nbabsjust = AbsEtudSem.CountAbsJust()
        doc._push()
        doc.absences(nbabs=nbabs, nbabsjust=nbabsjust )
        doc._pop()
    # --- Decision Jury
    if context.get_preference('bul_show_decision', formsemestre_id) or xml_with_decisions:
        infos, dpv = sco_bulletins.etud_descr_situation_semestre(
            context, etudid, formsemestre_id, format='xml',
            show_uevalid=context.get_preference('bul_show_uevalid',formsemestre_id))
        doc.situation( quote_xml_attr(infos['situation']) )
        if dpv:
            decision = dpv['decisions'][0]
            etat = decision['etat']
            if decision['decision_sem']:
                code = decision['decision_sem']['code']
            else:
                code = ''
            doc._push()
            doc.decision( code=code, etat=etat)
            doc._pop()
            if decision['decisions_ue']: # and context.get_preference('bul_show_uevalid', formsemestre_id): always publish (car utile pour export Apogee)
                for ue_id in decision['decisions_ue'].keys():                
                    ue = context.do_ue_list({ 'ue_id' : ue_id})[0]
                    doc._push()
                    doc.decision_ue( ue_id=ue['ue_id'],
                                     numero=quote_xml_attr(ue['numero']),
                                     acronyme=quote_xml_attr(ue['acronyme']),
                                     titre=quote_xml_attr(ue['titre']),
                                     code=decision['decisions_ue'][ue_id]['code']
                                     )
                    doc._pop()
            
            for aut in decision['autorisations']:
                doc._push()
                doc.autorisation_inscription( semestre_id=aut['semestre_id'] )
                doc._pop()
        else:
            doc._push()
            doc.decision( code='', etat='DEM' )
            doc._pop()
    # --- Appreciations
    cnx = context.GetDBConnexion() 
    apprecs = scolars.appreciations_list(
        cnx,
        args={'etudid':etudid, 'formsemestre_id' : formsemestre_id } )
    for app in apprecs:
        doc.appreciation( quote_xml_attr(app['comment']), date=DateDMYtoISO(app['date']))
    return doc
