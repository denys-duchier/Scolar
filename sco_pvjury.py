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

"""PV Jury IUTV 2006: on d�taillait 8 cas:
Jury de semestre n
    On a 8 types de d�cisions:
    Passages:
    1. passage de ceux qui ont valid�s Sn-1
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
    "r�sum� textuel des d�cisions d'UE"
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
    "r�sum� textuel de la d�cision de semestre"
    if etat == 'D':
        decision = 'D�mission'
    else:
        if decision_sem:
            cod = decision_sem['code']
            decision = sco_codes_parcours.CODES_EXPL.get(cod,'') #+ ' (%s)' % cod
        else:
            decision = ''
    return decision

def descr_decision_sem_abbrev(znotes, etat, decision_sem):
    "r�sum� textuel tres court (code) de la d�cision de semestre"
    if etat == 'D':
        decision = 'D�mission'
    else:
        if decision_sem:
            decision = decision_sem['code']
        else:
            decision = ''
    return decision

def descr_autorisations(znotes, autorisations):
    "r�sum� texturl des autorisations d'inscription (-> 'S1, S3' )"
    alist = []
    for aut in autorisations:
        alist.append( 'S' + str(aut['semestre_id']) )
    return ', '.join(alist)


def dict_pvjury( znotes, formsemestre_id, etudids=None, with_prev=False ):
    """Donn�es pour �dition jury
    etudids == None => tous les inscrits, sinon donne la liste des ids
    Si with_prev: ajoute infos sur code jury semestre precedent
    R�sultat:
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
                        'prev_code' : code (calcul� slt si with_prev)
                    ]
                  }
    }    
    """
    nt = znotes._getNotesCache().get_NotesTable(znotes, formsemestre_id)
    if etudids is None:
        etudids = nt.get_etudids()
    if not etudids:
        return {}
    cnx = znotes.GetDBConnexion()
    sem = znotes.get_formsemestre(formsemestre_id)
    max_date = '0000-01-01'
    has_prev = False # vrai si au moins un etudiant a un code prev    
    # construit un Se pour savoir si le semestre est terminal:
    etud = znotes.getEtudInfo(etudid=etudids[0], filled=True)[0]
    Se = sco_parcours_dut.SituationEtudParcours(znotes, etud, formsemestre_id) 
    L = []
    for etudid in etudids:
        d = {}
        d['identite'] = nt.identdict[etudid]
        d['etat'] = nt.get_etud_etat(etudid) # I|D  (inscription ou d�mission)
        d['decision_sem'] = nt.get_etud_decision_sem(etudid)
        d['decisions_ue'] = nt.get_etud_decision_ues(etudid)
        # Versions "en fran�ais":
        d['decisions_ue_descr'] = descr_decisions_ues(znotes, d['decisions_ue'], d['decision_sem'])
        d['decision_sem_descr'] = descr_decision_sem(znotes, d['etat'], d['decision_sem'])

        d['autorisations'] = sco_parcours_dut.formsemestre_get_autorisation_inscription(
            znotes, etudid, formsemestre_id)
        d['autorisations_descr'] = descr_autorisations(znotes, d['autorisations'])
        # Observations sur les compensations:
        obs = ''
        compensators = sco_parcours_dut.scolar_formsemestre_validation_list(
            cnx, 
            args={'compense_formsemestre_id': formsemestre_id,
                  'etudid' : etudid })
        for compensator in compensators:
            # nb: il ne devrait y en avoir qu'un !
            csem = znotes.get_formsemestre(compensator['formsemestre_id'])
            obs += 'Compens� par %s' % csem['titreannee']
        
        if d['decision_sem'] and d['decision_sem']['compense_formsemestre_id']:
            compensed = znotes.get_formsemestre(d['decision_sem']['compense_formsemestre_id'])
            obs += ' Compense %s' % compensed['titreannee']
        
        d['observation'] = obs
        
        # Cherche la date de decision (sem ou UE) la plus r�cente:
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
            etud = znotes.getEtudInfo(etudid=etudid, filled=True)[0]
            Se = sco_parcours_dut.SituationEtudParcours(znotes, etud, formsemestre_id)
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
             'formation' : znotes.do_formation_list(args={'formation_id':sem['formation_id']})[0],
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
              'decision' : 'D�cision' + id_cur,
              'ue_cap' : 'UE' + id_cur + ' capitalis�es',
              'devenir' : 'Devenir', 'observations' : 'Observations'
              }
    columns_ids = ['nomprenom', 'decision', 'ue_cap', 'devenir', 'observations']
    if dpv['has_prev']:
        id_prev = sem['semestre_id'] - 1 # numero du semestre precedent
        titles['prev_decision'] = 'D�cision S%s' % id_prev
        columns_ids[1:1] = ['prev_decision']
    lines = []
    for e in dpv['decisions']:
        l = { 'etudid' : e['identite']['etudid'],
              'nomprenom' : znotes.nomprenom(e['identite']),
              '_nomprenom_target' : '%s/ficheEtud?etudid=%s' % (znotes.ScoURL(),e['identite']['etudid']),
              'decision' : descr_decision_sem_abbrev(znotes, e['etat'], e['decision_sem']),
              'ue_cap' : e['decisions_ue_descr'],
              'devenir' : e['autorisations_descr'],
              'observations' : unquote(e['observation']) }        
        if dpv['has_prev']:
            l['prev_decision'] = descr_decision_sem_abbrev(znotes, None, e['prev_decision_sem'])
        lines.append(l)
    return lines, titles, columns_ids

    
def formsemestre_pvjury(context, formsemestre_id, format='html', REQUEST=None):
    """Page r�capitulant les d�cisions de jury
    dpv: result of dict_pvjury
    """
    header = context.sco_header(REQUEST)
    footer = context.sco_footer(REQUEST)
    dpv = dict_pvjury(context, formsemestre_id, with_prev=True)
    if not dpv:
        if format == 'html':
            return header + '<h2>Aucune information disponible !</h2>' + footer
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
                   origin = 'G�n�r� par %s le ' % VERSION.SCONAME + timedate_human_repr() + '',
                   caption = 'D�cisions jury pour ' + sem['titreannee'],
                   html_class='gt_table table_leftalign',
                   html_sortable=True,
                   preferences=context.get_preferences()
                   )
    if format != 'html':
        return tab.make_page(context, format=format, with_html_headers=False, REQUEST=REQUEST)
    tab.base_url = '%s?formsemestre_id=%s' % (REQUEST.URL0, formsemestre_id)
    H = [ context.html_sem_header(
            REQUEST, 'D�cisions du jury pour le semestre', sem),
          """<p>(derni�re modif le %s)</p>""" % dpv['date'] ]
    
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
    # L�gende des codes
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
                       preferences=context.get_preferences()
                       ).html() )
    H.append('<p></p>') # force space at bottom
    return '\n'.join(H) + footer

# ---------------------------------------------------------------------------

def formsemestre_pvjury_pdf(context, formsemestre_id, etudid=None, REQUEST=None):
    """Generation PV jury en PDF: saisie des param�tres
    Si etudid, PV pour un seul etudiant. Sinon, tout les inscrits au semestre.
    """
    sem = context.get_formsemestre(formsemestre_id)
    if etudid:
        etud = context.getEtudInfo(etudid=etudid,filled=1)[0]
        etuddescr = '<a class="discretelink" href="ficheEtud?etudid=%s">%s</a> en' % (etudid,etud['nomprenom'])
    else:
        etuddescr = ''

    H = [ context.html_sem_header(REQUEST,'Edition du PV de jury de %s'%etuddescr, sem),
          """<p class="help">Utiliser cette page pour �diter des versions provisoires des PV.
          <span class="fontred">Il est recommand� d'archiver les versions d�finitives: <a href="formsemestre_archive?formsemestre_id=%s">voir cette page</a></span>
          </p>""" % formsemestre_id
          ]
    F = [ """<p><em>Voir aussi si besoin les r�glages sur la page "Param�trage" (accessible � l'administrateur du d�partement).</em>
        </p>""",
        context.sco_footer(REQUEST) ]
    descr = descrform_pvjury(sem)
    if etudid:
        descr.append( ('etudid', {'input_type' : 'hidden' }) )
    tf = TrivialFormulator( REQUEST.URL0, REQUEST.form, descr,
                            cancelbutton = 'Annuler', method='GET',
                            submitlabel = 'G�n�rer document', 
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
    """D�finition de formulaire pour PV jury PDF
    """
    return [
        ('dateCommission', {'input_type' : 'text', 'size' : 50, 'title' : 'Date de la commission', 'explanation' : '(format libre)'}),
        ('dateJury', {'input_type' : 'text', 'size' : 50, 'title' : 'Date du Jury', 'explanation' : '(si le jury a eu lieu)' }),
        ('numeroArrete', {'input_type' : 'text', 'size' : 50, 'title' : 'Num�ro de l\'arr�t� du pr�sident',
        'explanation' : 'le pr�sident de l\'Universit� prend chaque ann�e un arr�t� formant les jurys'}),
        ('showTitle', { 'input_type' : 'checkbox', 'title':'Indiquer le titre du semestre sur le PV', 'explanation' : '(le titre est "%s")' % sem['titre'], 'labels' : [''], 'allowed_values' : ('1',)}),
        ('formsemestre_id', {'input_type' : 'hidden' }) ]


def formsemestre_lettres_individuelles(context, formsemestre_id, REQUEST=None):
    "Lettres avis jury en PDF"
    sem = context.get_formsemestre(formsemestre_id)
    H = [context.html_sem_header(REQUEST,'Edition des lettres individuelles', sem),
         """<p class="help">Utiliser cette page pour �diter des versions provisoires des PV.
          <span class="fontred">Il est recommand� d'archiver les versions d�finitives: <a href="formsemestre_archive?formsemestre_id=%s">voir cette page</a></span></p>
         """ % formsemestre_id
         ]
    F = context.sco_footer(REQUEST)
    descr = descrform_lettres_individuelles()
    tf = TrivialFormulator( REQUEST.URL0, REQUEST.form, descr,
                            cancelbutton = 'Annuler', method='POST',
                            submitlabel = 'G�n�rer document', 
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
        ('signature',  {'input_type' : 'file', 'size' : 30, 'explanation' : 'optionnel: image scann�e de la signature'}),
        ('formsemestre_id', {'input_type' : 'hidden' })]

