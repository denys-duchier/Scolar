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

"""Génération des bulletins de notes
"""

from notes_table import *
import htmlutils, time
import pdfbulletins
import sco_pvjury
from sco_pdf import PDFLOCK

def make_formsemestre_bulletinetud(
    znotes, formsemestre_id, etudid,
    version='long', # short, long, selectedevals
    format='html',
    REQUEST=None):        
    #
    if REQUEST:
        server_name = REQUEST.BASE0
    else:
        server_name = ''
    authuser = REQUEST.AUTHENTICATED_USER
    if not version in ('short','long','selectedevals'):
        raise ValueError('invalid version code !')
    sem = znotes.do_formsemestre_list(args={ 'formsemestre_id' : formsemestre_id } )[0]
    nt = znotes._getNotesCache().get_NotesTable(znotes, formsemestre_id)
    ues = nt.get_ues( filter_empty=True, etudid=etudid )
    modimpls = nt.get_modimpls()
    nbetuds = len(nt.rangs)
    # Genere le HTML H, une table P pour le PDF
    if sem['bul_bgcolor']:
        bgcolor = sem['bul_bgcolor']
    else:
        bgcolor = 'background-color: rgb(255,255,240)'
        
    H = [ '<table class="notes_bulletin" style="background-color: %s;">' % bgcolor  ]
    P = [] # elems pour gen. pdf
    LINEWIDTH = 0.5
    from reportlab.lib.colors import Color
    PdfStyle = [ ('FONTNAME', (0,0), (-1,0), 'Helvetica-Bold'),
                 ('LINEBELOW', (0,0), (-1,0), LINEWIDTH, Color(0,0,0)) ]
    def ueline(i): # met la ligne i du tableau pdf en style 'UE'
        PdfStyle.append(('FONTNAME', (0,i), (-1,i), 'Helvetica-Bold'))
        PdfStyle.append(('BACKGROUND', (0,i), (-1,i),
                         Color(170/255.,187/255.,204/255.) ))
    # ligne de titres
    moy = nt.get_etud_moy_gen(etudid)
    mg = fmt_note(moy)
    etatstr = nt.get_etud_etat_html(etudid)
    if type(moy) != StringType and nt.moy_moy != StringType:
        bargraph = '&nbsp;' + htmlutils.horizontal_bargraph(moy*5, nt.moy_moy*5)
    else:
        bargraph = ''

    if nt.get_moduleimpls_attente():
        # n'affiche pas le rang sur le bulletin s'il y a des
        # notes en attente dans ce semestre
        rang = '(notes en attente)'
    else:
        rang = 'Rang %s / %d' % (nt.get_etud_rang(etudid), nbetuds)

    t = ('Moyenne', mg + etatstr + bargraph,
         rang, 
         'Note/20', 'Coef')
    P.append(t)        
    H.append( '<tr><td class="note_bold">' +
              '</td><td class="note_bold">'.join(t) + '</td></tr>' )
    # Contenu table: UE apres UE
    tabline = 0 # line index in table
    for ue in ues:
        # Ligne UE
        ue_status = nt.get_etud_ue_status(etudid, ue['ue_id'])
        moy_ue = fmt_note(ue_status['cur_moy_ue'])
        if ue['type'] == UE_SPORT:
            moy_ue = '(note spéciale, bonus de %s points)' % nt.bonus[etudid]
        # UE capitalisee ?
        if ue_status['is_capitalized']:
            sem_origin = znotes.do_formsemestre_list(args={ 'formsemestre_id' : ue_status['formsemestre_id'] } )[0]
            t = ( ue['acronyme'], fmt_note(ue_status['moy_ue']),
                  '<a href="formsemestre_bulletinetud?formsemestre_id=%s&etudid=%s" title="%s" class="bull_link">Capitalisée le %s</a>'
                  % (sem_origin['formsemestre_id'], etudid,
                     sem_origin['titreannee'],
                     DateISOtoDMY(ue_status['event_date'])),
                  '', '%.2g' % ue_status['coef_ue'] )
            P.append(t)
            tabline += 1
            ueline(tabline)
            H.append('<tr class="notes_bulletin_row_ue">')
            H.append('<td class="note_bold">%s</td><td class="note_bold">%s</td><td>%s</td><td>%s</td><td>%s</td></tr>' % t )
            ue_comment = '(en cours, non prise en compte)'
        else:
            if sem['bul_show_ue_rangs'] != '0':
                ue_comment = '%s/%s' % (nt.ue_rangs[ue['ue_id']][0][etudid], nt.ue_rangs[ue['ue_id']][1])
            else:
                ue_comment = ''
        if (not ue_status['is_capitalized']) or ue_status['cur_moy_ue'] != 'NA':
            t = ( ue['acronyme'], moy_ue, ue_comment, '', '%.2g' % ue_status['cur_coef_ue'] )
            P.append(t)
            tabline += 1
            ueline(tabline)
            H.append('<tr class="notes_bulletin_row_ue">')
            H.append('<td class="note_bold">%s</td><td class="note_bold">%s</td><td>%s</td><td>%s</td><td>%s</td></tr>' % t )
            # Liste les modules de l'UE 
            ue_modimpls = [ mod for mod in modimpls if mod['module']['ue_id'] == ue['ue_id'] ]
            for modimpl in ue_modimpls:
                mod_moy = fmt_note(nt.get_etud_mod_moy(modimpl, etudid))
                if mod_moy != 'NI': # ne montre pas les modules 'non inscrit'
                    tabline += 1
                    H.append('<tr class="notes_bulletin_row_mod">')
                    # --- module avec moy. dans ce module et coef du module
                    nom_mod = modimpl['module']['abbrev']
                    if not nom_mod:
                        nom_mod = ''                        
                    t = [ modimpl['module']['code'], nom_mod, '', mod_moy,
                          '%.2g' % modimpl['module']['coefficient'] ]
                    
                    if sem['bul_show_mod_rangs'] != '0' and mod_moy != '-':
                        t[2] = '%s/%s' % (nt.mod_rangs[modimpl['moduleimpl_id']][0][etudid],
                                          nt.mod_rangs[modimpl['moduleimpl_id']][1])
                    
                    if sem['bul_show_codemodules'] != '1':
                        t[0] = '' # pas affichage du code module
                    
                    P.append(tuple(t))
                    link_mod = '<a class="bull_link" href="moduleimpl_status?moduleimpl_id=%s">' % modimpl['moduleimpl_id']
                    t[0] = link_mod + t[0] # add html link
                    t[1] = link_mod + t[1]
                    H.append('<td>%s</a></td><td>%s</a></td><td>%s</td><td>%s</td><td>%s</td></tr>' % tuple(t) )
                    if version != 'short':
                        # --- notes de chaque eval:
                        evals = nt.get_evals_in_mod(modimpl['moduleimpl_id'])
                        for e in evals:
                            if e['visibulletin'] == '1' or version == 'long':
                                tabline += 1
                                H.append('<tr class="notes_bulletin_row_eval">')
                                nom_eval = e['description']
                                if not nom_eval:
                                    nom_eval = 'le %s' % e['jour']
                                link_eval = '<a class="bull_link" href="evaluation_listenotes?evaluation_id=%s&liste_format=html&groupes%%3Alist=tous&tf-submitted=1">%s</a>' % (e['evaluation_id'], nom_eval)
                                val = e['notes'].get(etudid, {'value':'NP'})['value'] # NA si etud demissionnaire
                                val = fmt_note(val, note_max=e['note_max'] )
                                t = [ '', '', nom_eval, val, '%.2g' % e['coefficient'] ]
                                P.append(tuple(t))
                                t[2] = link_eval
                                H.append('<td>%s</td><td>%s</td><td class="bull_nom_eval">%s</td><td>%s</td><td class="bull_coef_eval">%s</td></tr>' % tuple(t))
    H.append('</table>')
    # --- Absences
    if sem['gestion_absence'] == '1':
        debut_sem = znotes.DateDDMMYYYY2ISO(sem['date_debut'])
        fin_sem = znotes.DateDDMMYYYY2ISO(sem['date_fin'])
        nbabs = znotes.Absences.CountAbs(etudid=etudid, debut=debut_sem, fin=fin_sem)
        nbabsjust = znotes.Absences.CountAbsJust(etudid=etudid,
                                           debut=debut_sem,fin=fin_sem)
        H.append("""<p>
    <a href="../Absences/CalAbs?etudid=%(etudid)s" class="bull_link">
    <b>Absences :</b> %(nbabs)s demi-journées, dont %(nbabsjust)s justifiées
    (pendant ce semestre).
    </a></p>
        """ % {'etudid':etudid, 'nbabs' : nbabs, 'nbabsjust' : nbabsjust } )
    # --- Decision Jury
    if sem['bul_show_decision'] == '1':
        situation, dpv = _etud_descr_situation_semestre(
            znotes, etudid, formsemestre_id,
            format=format,
            show_uevalid=(sem['bul_show_uevalid']=='1'))
    else:
        situation = ''
    if situation:
        H.append( """<p class="bull_situation">%s</p>""" % situation )
    # --- Appreciations
    # le dir. des etud peut ajouter des appreciation,
    # mais aussi le chef (perm. ScoEtudInscrit)
    can_edit_app = ((authuser == sem['responsable_id'])
                    or (authuser.has_permission(ScoEtudInscrit,znotes)))
    cnx = znotes.GetDBConnexion()   
    apprecs = scolars.appreciations_list(
        cnx,
        args={'etudid':etudid, 'formsemestre_id' : formsemestre_id } )
    H.append('<div class="bull_appreciations">')
    if apprecs:
        H.append('<p><b>Appréciations</b></p>')
    for app in apprecs:
        if can_edit_app:
            mlink = '<a class="stdlink" href="appreciation_add_form?id=%s">modifier</a> <a class="stdlink" href="appreciation_add_form?id=%s&suppress=1">supprimer</a>'%(app['id'],app['id'])
        else:
            mlink = ''
        H.append('<p><span class="bull_appreciations_date">%s</span>%s<span class="bull_appreciations_link">%s</span></p>'
                     % (app['date'], app['comment'], mlink ) )
    if can_edit_app:
        H.append('<p><a class="stdlink" href="appreciation_add_form?etudid=%s&formsemestre_id=%s">Ajouter une appréciation</a></p>' % (etudid, formsemestre_id))
    H.append('</div>')
    # ---------------
    if format == 'html':
        return '\n'.join(H), None, None
    elif format == 'pdf' or format == 'pdfpart':
        etud = znotes.getEtudInfo(etudid=etudid,filled=1)[0]
        if sem['gestion_absence'] == '1':
            etud['nbabs'] = nbabs
            etud['nbabsjust'] = nbabsjust
        infos = { 'DeptName' : znotes.DeptName }
        stand_alone = (format != 'pdfpart')
        if nt.get_etud_etat(etudid) == 'D':
            filigranne = 'DEMISSION'
        else:
            filigranne = ''
        try:
            PDFLOCK.acquire()
            pdfbul = pdfbulletins.pdfbulletin_etud(
                etud, sem, P, PdfStyle,
                infos, stand_alone=stand_alone, filigranne=filigranne,
                appreciations=[ x['date'] + ': ' + x['comment'] for x in apprecs ],
                situation=situation,
                server_name=server_name, context=znotes )
        finally:
            PDFLOCK.release()
        dt = time.strftime( '%Y-%m-%d' )
        filename = 'bul-%s-%s-%s.pdf' % (sem['titre_num'], dt, etud['nom'])
        filename = unescape_html(filename).replace(' ','_').replace('&','')
        return pdfbul, etud, filename
    else:
        raise ValueError('invalid parameter: format')


# -------- Bulletin en XML
# (fonction séparée pour simplifier le code,
#  mais attention a la maintenance !)
def make_xml_formsemestre_bulletinetud( znotes, formsemestre_id, etudid,
                                        doc=None, # XML document
                                        force_publishing=False,
                                        xml_nodate=False,
                                        REQUEST=None):
    "bulletin au format XML"
    if REQUEST:
        REQUEST.RESPONSE.setHeader('Content-type', XML_MIMETYPE)
    if not doc:            
        doc = jaxml.XML_document( encoding=SCO_ENCODING )

    sem = znotes.do_formsemestre_list(args={ 'formsemestre_id' : formsemestre_id } )[0]
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
                      etape_apo=sem['etape_apo'] or '')

    # Infos sur l'etudiant
    etudinfo = znotes.getEtudInfo(etudid=etudid,filled=1)[0]
    doc._push()
    doc.etudiant(
        etudid=etudid, code_nip=etudinfo['code_nip'], code_ine=etudinfo['code_ine'],
        nom=quote_xml_attr(etudinfo['nom']),
        prenom=quote_xml_attr(etudinfo['prenom']),
        sexe=quote_xml_attr(etudinfo['sexe']),
        photo_url=quote_xml_attr(znotes.etudfoto_url(etudid)),
        email=quote_xml_attr(etudinfo['email']))    
    doc._pop()

    # Disponible pour publication ?
    if not published:
        return doc # stop !

    nt = znotes._getNotesCache().get_NotesTable(znotes, formsemestre_id)
    ues = nt.get_ues()
    modimpls = nt.get_modimpls()
    nbetuds = len(nt.rangs)
    mg = fmt_note(nt.get_etud_moy_gen(etudid))
    if nt.get_moduleimpls_attente():
        # n'affiche pas le renag sur le bulletin s'il y a des
        # notes en attente dans ce semestre
        rang = '?'
    else:
        rang = str(nt.get_etud_rang(etudid))
    doc._push()
    doc.note( value=mg )
    doc._pop()
    doc._push()
    doc.rang( value=rang, ninscrits=nbetuds )
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
        doc.note( value=fmt_note(ue_status['cur_moy_ue']) )
        doc._pop()
        doc._push()
        doc.rang( value=str(nt.ue_rangs[ue['ue_id']][0][etudid]) )
        doc._pop()
        doc._push()
        doc.effectif( value=str(nt.ue_rangs[ue['ue_id']][1]) )
        doc._pop()
        # Liste les modules de l'UE 
        ue_modimpls = [ mod for mod in modimpls if mod['module']['ue_id'] == ue['ue_id'] ]
        for modimpl in ue_modimpls:
            mod_moy = fmt_note(nt.get_etud_mod_moy(modimpl, etudid))
            if mod_moy == 'NI': # ne mentionne pas les modules ou n'est pas inscrit
                continue
            mod = modimpl['module']
            doc._push()
            doc.module( id=modimpl['moduleimpl_id'], code=mod['code'],
                        coefficient=mod['coefficient'],
                        numero=mod['numero'],
                        titre=quote_xml_attr(mod['titre']),
                        abbrev=quote_xml_attr(mod['abbrev']) )
            doc._push()
            doc.note( value=mod_moy )
            doc._pop()
            if sem['bul_show_mod_rangs'] != '0':
                doc._push()
                doc.rang( value=nt.mod_rangs[modimpl['moduleimpl_id']][0][etudid] )
                doc._pop()
                doc._push()
                doc.effectif( value=nt.mod_rangs[modimpl['moduleimpl_id']][1] )
                doc._pop()
            # --- notes de chaque eval:
            evals = nt.get_evals_in_mod(modimpl['moduleimpl_id'])
            for e in evals:
                doc._push()
                doc.evaluation(jour=DateDMYtoISO(e['jour']),
                               heure_debut=TimetoISO8601(e['heure_debut']),
                               heure_fin=TimetoISO8601(e['heure_fin']),
                               coefficient=e['coefficient'],
                               description=quote_xml_attr(e['description']))
                val = e['notes'].get(etudid, {'value':'NP'})['value'] # NA si etud demissionnaire
                val = fmt_note(val, note_max=e['note_max'] )
                doc.note( value=val )
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
            doc.note( value=fmt_note(ue_status['moy_ue']) )
            doc._pop()
            doc._push()
            doc.coefficient_ue( value=fmt_note(ue_status['coef_ue']) )
            doc._pop()
            doc._push()
            doc.date_capitalisation(
                value=znotes.DateDDMMYYYY2ISO(ue_status['event_date']) )
            doc._pop()
            doc._pop()
    # --- Absences
    if sem['gestion_absence'] == '1':
        debut_sem = znotes.DateDDMMYYYY2ISO(sem['date_debut'])
        fin_sem = znotes.DateDDMMYYYY2ISO(sem['date_fin'])
        nbabs = znotes.Absences.CountAbs(etudid=etudid, debut=debut_sem, fin=fin_sem)
        nbabsjust = znotes.Absences.CountAbsJust(etudid=etudid,
                                           debut=debut_sem,fin=fin_sem)
        doc._push()
        doc.absences(nbabs=nbabs, nbabsjust=nbabsjust )
        doc._pop()
    # --- Decision Jury
    if sem['bul_show_decision'] == '1':
        situation, dpv = _etud_descr_situation_semestre(
            znotes, etudid, formsemestre_id, format='xml',
            show_uevalid=(sem['bul_show_uevalid']=='1'))
        doc.situation( quote_xml_attr(situation) )
        if dpv:
            decision = dpv['decisions'][0]
            etat = decision['etat']
            if decision['decision_sem']:
                code = decision['decision_sem']['code']
            else:
                code = ''
            doc.decision( code=code, etat=etat)
            for aut in decision['autorisations']:
                doc.autorisation_inscription( semestre_id=aut['semestre_id'] )
        else:
            doc.decision( code='', etat='DEM' )
    # --- Appreciations
    cnx = znotes.GetDBConnexion() 
    apprecs = scolars.appreciations_list(
        cnx,
        args={'etudid':etudid, 'formsemestre_id' : formsemestre_id } )
    for app in apprecs:
        doc.appreciation( quote_xml_attr(app['comment']), date=znotes.DateDDMMYYYY2ISO(app['date']))
    return doc


def _etud_descr_situation_semestre(znotes, etudid, formsemestre_id, ne='',
                                  format='html',
                                  show_uevalid=True
                                  ):
    """chaine de caractères decrivant la situation de l'étudiant
    dans ce semestre.
    Si format == 'html', peut inclure du balisage html"""
    cnx = znotes.GetDBConnexion()
    # --- Situation et décisions jury

    # demission/inscription ?
    events = scolars.scolar_events_list(
        cnx, args={'etudid':etudid, 'formsemestre_id':formsemestre_id} )
    date_inscr = None
    date_dem = None
    date_echec = None
    for event in events:
        event_type = event['event_type']
        if event_type == 'INSCRIPTION':
            if date_inscr:
                # plusieurs inscriptions ???
                #date_inscr += ', ' +   event['event_date'] + ' (!)'
                # il y a eu une erreur qui a laissé un event 'inscription'
                # on l'efface:
                log('etud_descr_situation_semestre: removing duplicate INSCRIPTION event !')
                scolars.scolar_events_delete( cnx, event['event_id'] )
            else:
                date_inscr = event['event_date']
        elif event_type == 'DEMISSION':
            assert date_dem == None, 'plusieurs démissions !'
            date_dem = event['event_date']
    if not date_inscr:
        inscr = 'Pas inscrit' + ne
    else:
        inscr = 'Inscrit%s le %s.' % (ne, date_inscr)
    if date_dem:
        return inscr + '. Démission le %s.' % date_dem, None

    dpv = sco_pvjury.dict_pvjury(znotes, formsemestre_id, etudids=[etudid])
    pv = dpv['decisions'][0]
    dec = ''
    if pv['decision_sem_descr']:
        dec = 'Décision jury: ' + pv['decision_sem_descr'] + '. '
    if pv['decisions_ue_descr']:
        dec += ' UE acquises: ' + pv['decisions_ue_descr']
    return inscr + ' ' + dec, dpv


# ------ page bulletin (traduite du DTML)

from sco_formsemestre_status import makeMenu

def formsemestre_bulletinetud(context, etudid=None, formsemestre_id=None, format='html', version='long', REQUEST=None):
    "page bulletin de notes"
    try:
        etud = context.getEtudInfo(filled=1, REQUEST=REQUEST)[0]
        etudid = etud['etudid']
    except:
        context.log_unknown_etud(REQUEST)
    sem = context.do_formsemestre_list( args={ 'formsemestre_id' : formsemestre_id } )[0]
    R = []
    if format == 'html' or format == 'mailpdf':
        R.append( _formsemestre_bulletinetud_header_html(context, etud, etudid, sem,
                                                   formsemestre_id, format, version, REQUEST) )
    R.append(context.do_formsemestre_bulletinetud(formsemestre_id, etudid,
                                                  format=format, version=version, REQUEST=REQUEST))
    if format == 'html' or format == 'mailpdf':
        R.append("""<p>Situation actuelle: """)
        if etud['inscription_formsemestre_id']:
            R.append("""<a href="formsemestre_status?formsemestre_id=%s">"""
                     % etud['inscription_formsemestre_id'])
        R.append(etud['inscriptionstr'] + ' ' + etud['groupetd'])
        if etud['inscription_formsemestre_id']:
            R.append("""</a>""")
        R.append("""</p>""")

    return ''.join(R)

def _formsemestre_bulletinetud_header_html(context, etud, etudid, sem,
                                           formsemestre_id=None, format=None, version=None, REQUEST=None):
    authuser = REQUEST.AUTHENTICATED_USER
    uid = str(authuser)
    H = [ context.sco_header(page_title='Bulletin de %(nomprenom)s' % etud, REQUEST=REQUEST),
          """<table class="bull_head"><tr><td>
          <h2><a class="discretelink" href="ficheEtud?etudid=%(etudid)s">%(nomprenom)s</a></h2>
          """ % etud,
          """
          <form name="f" method="GET">
          Bulletin <span class="bull_liensemestre"><a href="formsemestre_status?formsemestre_id=%(formsemestre_id)s">
          %(titreannee)s</a></span> 
          <br/>""" % sem,
          """<table><tr>""",
          """<td>établi le %s (notes sur 20)</td>""" % time.strftime('%d/%m/%Y à %Hh%M'),
          """<td><span class="rightjust">
             <input type="hidden" name="formsemestre_id" value="%s"></input>""" % formsemestre_id,
          """<input type="hidden" name="etudid" value="%s"></input>""" % etudid,
          """<input type="hidden" name="format" value="%s"></input>""" % format,
          """<select name="version" onChange="document.f.submit()" class="noprint">""",
          ]
    for (v,e) in ( ('short', 'Version courte'),
                   ('selectedevals', 'Version intermédiaire'),
                   ('long', 'Version complète')):
        if v == version:
            selected = ' selected'
        else:
            selected = ''
        H.append('<option value="%s"%s>%s</option>' % (v, selected, e))
    H.append("""</select></td>""")
    # Menu
    url = REQUEST.URL0
    qurl = urllib.quote_plus( url + '?' + REQUEST.QUERY_STRING )
    
    menuBul = [
        { 'title' : 'Réglages bulletins',
          'url' : 'formsemestre_edit_options?formsemestre_id=%s&target_url=%s' % (formsemestre_id, qurl),
          'enabled' : (uid == sem['responsable_id']) or authuser.has_permission(ScoImplement, context),
          },
        { 'title' : 'Version papier (pdf)',
          'url' : url + '?formsemestre_id=%s&etudid=%s&format=pdf&version=%s' % (formsemestre_id,etudid,version),
          },
        { 'title' : "Envoi par mail à l'étudiant",
          'url' : url + '?formsemestre_id=%s&etudid=%s&format=mailpdf&version=%s' % (formsemestre_id,etudid,version),
          'enabled' : etud['email'] # possible slt si on a un mail...
          },
        { 'title' : 'Version XML',
          'url' : url + '?formsemestre_id=%s&etudid=%s&format=xml&version=%s' % (formsemestre_id,etudid,version),
          },
        { 'title' : 'Ajouter une appréciation',
          'url' : 'appreciation_add_form?etudid=%s&formsemestre_id=%s' % (etudid, formsemestre_id),
          'enabled' : ((authuser == sem['responsable_id'])
                       or (authuser.has_permission(ScoEtudInscrit,context)))
          },
        { 'title' : 'Editer PV jury',
          'url' : 'formsemestre_pvjury_pdf?formsemestre_id=%s&etudid=%s' % (formsemestre_id,etudid),
          'enabled' : True
          }
        ]
    
    H.append("""<td class="bulletin_menubar"><div class="bulletin_menubar">""")
    H.append( makeMenu( 'Autres opérations', menuBul) )
    H.append("""</div></td></tr></table>""")
    #
    H.append("""</form></span></td><td class="bull_photo">
    <a href="%s/ficheEtud?etudid=%s">%s</a>
    """ % (context.ScoURL(),etudid, context.etudfoto(foto=etud['foto'],etudid=etudid,fototitle='fiche de '+etud['nom'])))
    H.append("""</td></tr>
    </table>
    """)
    
    return ''.join(H)
