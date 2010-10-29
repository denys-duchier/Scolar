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

"""Edition des PV de jury
"""

import sco_parcours_dut
import sco_codes_parcours
import sco_excel
from notesdb import *
from sco_utils import *
from gen_tables import GenTable
import sco_pvpdf
from sco_pdf import PDFLOCK

"""PV Jury IUTV 2006: on détaillait 8 cas:
Jury de semestre n
    On a 8 types de décisions:
    Passages:
    1. passage de ceux qui ont validés Sn-1
    2. passage avec compensation Sn-1, Sn
    3. passage sans validation de Sn avec validation d'UE
    4. passage sans validation de Sn sans validation d'UE

    Redoublements:
    5. redoublement de Sn-1 et Sn sans validation d'UE pour Sn
    6. redoublement de Sn-1 et Sn avec validation d'UE pour Sn

    Reports
    7. report sans validation d'UE

    8. non validation de Sn-1 et Sn et non redoublement
"""

def descr_decisions_ues(znotes, decisions_ue, decision_sem):
    "résumé textuel des décisions d'UE"
    if not decisions_ue:
        return ''
    uelist = []
    for ue_id in decisions_ue.keys():
        if decisions_ue[ue_id]['code'] == 'ADM' \
           or (CONFIG.CAPITALIZE_ALL_UES and sco_codes_parcours.code_semestre_validant(decision_sem['code'])):
            ue = znotes.do_ue_list( args={ 'ue_id' : ue_id } )[0]
            uelist.append(ue)
    uelist.sort( lambda x,y: cmp(x['numero'],y['numero']) )
    ue_acros = ', '.join( [ ue['acronyme'] for ue in uelist ] )
    return ue_acros

def descr_decision_sem(znotes, etat, decision_sem):
    "résumé textuel de la décision de semestre"
    if etat == 'D':
        decision = 'Démission'
    else:
        if decision_sem:
            cod = decision_sem['code']
            decision = sco_codes_parcours.CODES_EXPL.get(cod,'') #+ ' (%s)' % cod
        else:
            decision = ''
    return decision

def descr_decision_sem_abbrev(znotes, etat, decision_sem):
    "résumé textuel tres court (code) de la décision de semestre"
    if etat == 'D':
        decision = 'Démission'
    else:
        if decision_sem:
            decision = decision_sem['code']
        else:
            decision = ''
    return decision

def descr_autorisations(znotes, autorisations):
    "résumé texturl des autorisations d'inscription (-> 'S1, S3' )"
    alist = []
    for aut in autorisations:
        alist.append( 'S' + str(aut['semestre_id']) )
    return ', '.join(alist)


def dict_pvjury( znotes, formsemestre_id, etudids=None, with_prev=False ):
    """Données pour édition jury
    etudids == None => tous les inscrits, sinon donne la liste des ids
    Si with_prev: ajoute infos sur code jury semestre precedent
    Résultat:
    {
    'date' : date de la decision la plus recente,
    'formsemestre' : sem,
    'formation' : { 'acronyme' :, 'titre': ... }
    'decisions' : { [ { 'identite' : {'nom' :, 'prenom':,  ...,},
                        'etat' : I ou D
                        'decision' : {'code':, 'code_prev': },
                        'ues' : {  ue_id : { 'code' : ADM|CMP|AJ, 'event_date' :,
                                             'acronyme', 'numero': } },
                        'autorisations' : [ { 'semestre_id' : { ... } }
                        'prev_code' : code (calculé slt si with_prev)
                    ]
                  }
    }    
    """
    nt = znotes._getNotesCache().get_NotesTable(znotes, formsemestre_id) #> get_etudids, get_etud_etat, get_etud_decision_sem, get_etud_decision_ues
    if etudids is None:
        etudids = nt.get_etudids()
    if not etudids:
        return {}
    cnx = znotes.GetDBConnexion()
    sem = znotes.get_formsemestre(formsemestre_id)
    max_date = '0000-01-01'
    has_prev = False # vrai si au moins un etudiant a un code prev    
    
    L = []
    for etudid in etudids:
        etud = znotes.getEtudInfo(etudid=etudid, filled=True)[0]
        Se = sco_parcours_dut.SituationEtudParcours(znotes, etud, formsemestre_id)
        d = {}
        d['identite'] = nt.identdict[etudid]
        d['etat'] = nt.get_etud_etat(etudid) # I|D  (inscription ou démission)
        d['decision_sem'] = nt.get_etud_decision_sem(etudid)
        d['decisions_ue'] = nt.get_etud_decision_ues(etudid)
        # Versions "en français":
        d['decisions_ue_descr'] = descr_decisions_ues(znotes, d['decisions_ue'], d['decision_sem'])
        d['decision_sem_descr'] = descr_decision_sem(znotes, d['etat'], d['decision_sem'])

        d['autorisations'] = sco_parcours_dut.formsemestre_get_autorisation_inscription(
            znotes, etudid, formsemestre_id)
        d['autorisations_descr'] = descr_autorisations(znotes, d['autorisations'])
        d['parcours'] = Se.get_parcours_descr()
        
        # Observations sur les compensations:
        obs = ''
        compensators = sco_parcours_dut.scolar_formsemestre_validation_list(
            cnx, 
            args={'compense_formsemestre_id': formsemestre_id,
                  'etudid' : etudid })
        for compensator in compensators:
            # nb: il ne devrait y en avoir qu'un !
            csem = znotes.get_formsemestre(compensator['formsemestre_id'])
            obs += 'Compensé par %s' % csem['titreannee']
        
        if d['decision_sem'] and d['decision_sem']['compense_formsemestre_id']:
            compensed = znotes.get_formsemestre(d['decision_sem']['compense_formsemestre_id'])
            obs += ' Compense %s' % compensed['titreannee']
        
        d['observation'] = obs
        
        # Cherche la date de decision (sem ou UE) la plus récente:
        if d['decision_sem']:
            date = DateDMYtoISO(d['decision_sem']['event_date'])
            if date > max_date: # decision plus recente
                max_date = date
        if d['decisions_ue']:
            for dec_ue in d['decisions_ue'].values():
                if dec_ue:
                    date = DateDMYtoISO(dec_ue['event_date'])
                    if date > max_date: # decision plus recente
                        max_date = date
        # Code semestre precedent
        if with_prev: # optionnel car un peu long...
            info = znotes.getEtudInfo(etudid=etudid, filled=True)
            if not info:
                continue # should not occur
            etud = info[0]
            if Se.prev and Se.prev_decision:
                d['prev_decision_sem'] = Se.prev_decision
                d['prev_code'] = Se.prev_decision['code']
                d['prev_code_descr'] = descr_decision_sem(znotes, 'I', Se.prev_decision)
                d['prev'] = Se.prev
                has_prev = True
            else:
                d['prev_decision_sem'] = None
                d['prev_code'] = ''
                d['prev_code_descr'] = ''
            d['Se'] = Se
        
        L.append(d)
    return { 'date' : DateISOtoDMY(max_date),
             'formsemestre' : sem, 
             'has_prev' : has_prev,
             'semestre_non_terminal' : Se.semestre_non_terminal,
             'formation' : znotes.formation_list(args={'formation_id':sem['formation_id']})[0],
             'decisions' : L }


def pvjury_table(znotes, dpv):
    """idem mais rend list de dicts
    """
    sem = dpv['formsemestre']
    if sem['semestre_id'] >= 0:
        id_cur = ' S%s' % sem['semestre_id']
    else:
        id_cur = ''
    titles = {'etudid' : 'etudid', 'nomprenom' : 'Nom',
              'parcours' : 'Parcours',
              'decision' : 'Décision' + id_cur,
              'ue_cap' : 'UE' + id_cur + ' capitalisées',
              'devenir' : 'Devenir', 'observations' : 'Observations'
              }
    columns_ids = ['nomprenom', 'parcours', 'decision', 'ue_cap', 'devenir', 'observations']
    if dpv['has_prev']:
        id_prev = sem['semestre_id'] - 1 # numero du semestre precedent
        titles['prev_decision'] = 'Décision S%s' % id_prev
        columns_ids[2:2] = ['prev_decision']
    lines = []
    for e in dpv['decisions']:
        l = { 'etudid' : e['identite']['etudid'],
              'nomprenom' : znotes.nomprenom(e['identite']),
              '_nomprenom_target' : '%s/ficheEtud?etudid=%s' % (znotes.ScoURL(),e['identite']['etudid']),
              '_nomprenom_td_attrs' : 'id="%s" class="etudinfo"' % e['identite']['etudid'],
              'parcours' : e['parcours'],
              'decision' : descr_decision_sem_abbrev(znotes, e['etat'], e['decision_sem']),
              'ue_cap' : e['decisions_ue_descr'],
              'devenir' : e['autorisations_descr'],
              'observations' : unquote(e['observation']) }        
        if dpv['has_prev']:
            l['prev_decision'] = descr_decision_sem_abbrev(znotes, None, e['prev_decision_sem'])
        lines.append(l)
    return lines, titles, columns_ids

    
def formsemestre_pvjury(context, formsemestre_id, format='html', publish=True, REQUEST=None):
    """Page récapitulant les décisions de jury
    dpv: result of dict_pvjury
    """
    footer = context.sco_footer(REQUEST)
    
    dpv = dict_pvjury(context, formsemestre_id, with_prev=True)
    if not dpv:
        if format == 'html':
            return context.sco_header(REQUEST) + '<h2>Aucune information disponible !</h2>' + footer
        else:
            return None
    sem = dpv['formsemestre']
    formsemestre_id = sem['formsemestre_id']

    rows, titles, columns_ids = pvjury_table(context, dpv)
    if format != 'html' and format != 'pdf':
        columns_ids=['etudid'] + columns_ids
    
    tab = GenTable(rows=rows, titles=titles,
                   columns_ids=columns_ids,
                   filename=make_filename('decisions ' + sem['titreannee']),
                   origin = 'Généré par %s le ' % VERSION.SCONAME + timedate_human_repr() + '',
                   caption = 'Décisions jury pour ' + sem['titreannee'],
                   html_class='gt_table table_leftalign',
                   html_sortable=True,
                   preferences=context.get_preferences(formsemestre_id),
                   )
    if format != 'html':
        return tab.make_page(context, format=format, with_html_headers=False, REQUEST=REQUEST, publish=publish)
    tab.base_url = '%s?formsemestre_id=%s' % (REQUEST.URL0, formsemestre_id)
    H = [ context.html_sem_header(
            REQUEST, 'Décisions du jury pour le semestre', sem,
            javascripts=['jQuery/jquery.js', 
                         'libjs/qtip/jquery.qtip.js',
                         'js/etud_info.js'
                         ],                
            ),
          """<p>(dernière modif le %s)</p>""" % dpv['date'] ]
    
    H.append('<ul><li><a class="stdlink" href="formsemestre_lettres_individuelles?formsemestre_id=%s">Courriers individuels (classeur pdf)</a></li>' % formsemestre_id)
    H.append('<li><a class="stdlink" href="formsemestre_pvjury_pdf?formsemestre_id=%s">PV officiel (pdf)</a></li></ul>' % formsemestre_id)

    H.append( tab.html() )

    # Count number of cases for each decision
    counts = DictDefault()
    for row in rows:
        counts[row['decision']] += 1
        # add codes for previous (for explanation, without count)
        if row.has_key('prev_decision') and row['prev_decision']:
            counts[row['prev_decision']] += 0
    # Légende des codes
    codes = counts.keys() # sco_codes_parcours.CODES_EXPL.keys()
    codes.sort()
    H.append('<h3>Explication des codes</h3>')
    lines = []
    for code in codes:
        lines.append( { 'code' : code, 'count' : counts[code], 'expl' : sco_codes_parcours.CODES_EXPL.get(code, '') } )
    
    H.append( GenTable(rows=lines, titles={ 'code' : 'Code', 'count' : 'Nombre', 'expl' : '' },
                       columns_ids= ('code', 'count', 'expl'),
                       html_class='gt_table table_leftalign',
                       html_sortable=True,
                       preferences=context.get_preferences(formsemestre_id)
                       ).html() )
    H.append('<p></p>') # force space at bottom
    return '\n'.join(H) + footer

# ---------------------------------------------------------------------------

def formsemestre_pvjury_pdf(context, formsemestre_id, etudid=None, REQUEST=None):
    """Generation PV jury en PDF: saisie des paramètres
    Si etudid, PV pour un seul etudiant. Sinon, tout les inscrits au semestre.
    """
    sem = context.get_formsemestre(formsemestre_id)
    if etudid:
        etud = context.getEtudInfo(etudid=etudid,filled=1)[0]
        etuddescr = '<a class="discretelink" href="ficheEtud?etudid=%s">%s</a> en' % (etudid,etud['nomprenom'])
    else:
        etuddescr = ''

    H = [ context.html_sem_header(REQUEST,'Edition du PV de jury de %s'%etuddescr, sem),
          """<p class="help">Utiliser cette page pour éditer des versions provisoires des PV.
          <span class="fontred">Il est recommandé d'archiver les versions définitives: <a href="formsemestre_archive?formsemestre_id=%s">voir cette page</a></span>
          </p>""" % formsemestre_id
          ]
    F = [ """<p><em>Voir aussi si besoin les réglages sur la page "Paramétrage" (accessible à l'administrateur du département).</em>
        </p>""",
        context.sco_footer(REQUEST) ]
    descr = descrform_pvjury(sem)
    if etudid:
        descr.append( ('etudid', {'input_type' : 'hidden' }) )
    tf = TrivialFormulator( REQUEST.URL0, REQUEST.form, descr,
                            cancelbutton = 'Annuler', method='GET',
                            submitlabel = 'Générer document', 
                            name='tf' )
    if  tf[0] == 0:
        return '\n'.join(H) + '\n' + tf[1] + '\n'.join(F)
    elif tf[0] == -1:
        return REQUEST.RESPONSE.redirect( "formsemestre_pvjury?formsemestre_id=%s" %(formsemestre_id))
    else:
        # submit
        if etudid:
            etudids = [etudid]
        else:
            etudids = None
        dpv = dict_pvjury(context, formsemestre_id, etudids=etudids, with_prev=True)
        if tf[2]['showTitle']:
            tf[2]['showTitle'] = True
        else:
            tf[2]['showTitle'] = False
        try:
            PDFLOCK.acquire()
            pdfdoc = sco_pvpdf.pvjury_pdf(context, dpv, REQUEST,
                                          numeroArrete=tf[2]['numeroArrete'],
                                          dateCommission=tf[2]['dateCommission'],
                                          dateJury=tf[2]['dateJury'],
                                          showTitle=tf[2]['showTitle'])
        finally:
            PDFLOCK.release()                
        sem = context.get_formsemestre(formsemestre_id)
        dt = time.strftime( '%Y-%m-%d' )
        filename = 'PV-%s-%s.pdf' % (sem['titre_num'], dt)
        return sendPDFFile(REQUEST, pdfdoc, filename)

def descrform_pvjury(sem):
    """Définition de formulaire pour PV jury PDF
    """
    return [
        ('dateCommission', {'input_type' : 'text', 'size' : 50, 'title' : 'Date de la commission', 'explanation' : '(format libre)'}),
        ('dateJury', {'input_type' : 'text', 'size' : 50, 'title' : 'Date du Jury', 'explanation' : '(si le jury a eu lieu)' }),
        ('numeroArrete', {'input_type' : 'text', 'size' : 50, 'title' : 'Numéro de l\'arrêté du président',
        'explanation' : 'le président de l\'Université prend chaque année un arrêté formant les jurys'}),
        ('showTitle', { 'input_type' : 'checkbox', 'title':'Indiquer le titre du semestre sur le PV', 'explanation' : '(le titre est "%s")' % sem['titre'], 'labels' : [''], 'allowed_values' : ('1',)}),
        ('formsemestre_id', {'input_type' : 'hidden' }) ]


def formsemestre_lettres_individuelles(context, formsemestre_id, REQUEST=None):
    "Lettres avis jury en PDF"
    sem = context.get_formsemestre(formsemestre_id)
    H = [context.html_sem_header(REQUEST,'Edition des lettres individuelles', sem),
         """<p class="help">Utiliser cette page pour éditer des versions provisoires des PV.
          <span class="fontred">Il est recommandé d'archiver les versions définitives: <a href="formsemestre_archive?formsemestre_id=%s">voir cette page</a></span></p>
         """ % formsemestre_id
         ]
    F = context.sco_footer(REQUEST)
    descr = descrform_lettres_individuelles()
    tf = TrivialFormulator( REQUEST.URL0, REQUEST.form, descr,
                            cancelbutton = 'Annuler', method='POST',
                            submitlabel = 'Générer document', 
                            name='tf' )
    if  tf[0] == 0:
        return '\n'.join(H) + '\n' + tf[1] + F
    elif tf[0] == -1:
        return REQUEST.RESPONSE.redirect( "formsemestre_pvjury?formsemestre_id=%s" %(formsemestre_id))
    else:
        # submit
        sf = tf[2]['signature']
        #pdb.set_trace()
        signature = sf.read() # image of signature
        try:
            PDFLOCK.acquire()
            pdfdoc = sco_pvpdf.pdf_lettres_individuelles(context, formsemestre_id,
                                                         dateJury=tf[2]['dateJury'],
                                                         signature=signature)
        finally:
            PDFLOCK.release()
        sem = context.get_formsemestre(formsemestre_id)
        dt = time.strftime( '%Y-%m-%d' )
        filename = 'lettres-%s-%s.pdf' % (sem['titre_num'], dt)
        return sendPDFFile(REQUEST, pdfdoc, filename)

def descrform_lettres_individuelles():
    return  [
        ('dateJury', {'input_type' : 'text', 'size' : 50, 'title' : 'Date du Jury', 'explanation' : '(si le jury a eu lieu)' }),
        ('signature',  {'input_type' : 'file', 'size' : 30, 'explanation' : 'optionnel: image scannée de la signature'}),
        ('formsemestre_id', {'input_type' : 'hidden' })]

