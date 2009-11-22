# -*- mode: python -*-
# -*- coding: iso8859-15 -*-

##############################################################################
#
# Gestion scolarite IUT
#
# Copyright (c) 2001 - 2010 Emmanuel Viennet.  All rights reserved.
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

"""Liste des notes d'une évaluation
"""

from notesdb import *
from sco_utils import *
from notes_log import log
from TrivialFormulator import TrivialFormulator, TF
from notes_table import *
import sco_groups
import htmlutils
import sco_excel
from gen_tables import GenTable
from htmlutils import histogram_notes

from sets import Set

def do_evaluation_listenotes(context, REQUEST):
    """
    Affichage des notes d'une évaluation

    args: evaluation_id 
    """        
    cnx = context.GetDBConnexion()
    mode = None
    if REQUEST.form.has_key('evaluation_id'):
        evaluation_id = REQUEST.form['evaluation_id']
        mode = 'eval'
        evals = context.do_evaluation_list( {'evaluation_id' : evaluation_id})
    if REQUEST.form.has_key('moduleimpl_id'):
        moduleimpl_id = REQUEST.form['moduleimpl_id']
        mode = 'module'
        evals = context.do_evaluation_list( {'moduleimpl_id' : moduleimpl_id})
    if not mode:
        raise ValueError('missing argument: evaluation or module')
    if not evals:
        return '<p>Aucune évaluation !</p>'

    format = REQUEST.form.get('format', 'html')
    E = evals[0]
    M = context.do_moduleimpl_list( args={ 'moduleimpl_id' : E['moduleimpl_id'] } )[0]
    formsemestre_id = M['formsemestre_id']
    
    # description de l'evaluation    
    if mode == 'eval':
        H = [ context.evaluation_create_form(evaluation_id=evaluation_id, REQUEST=REQUEST, readonly=1) ]
    else:
        H = []
    # groupes
    groups = sco_groups.do_evaluation_listegroupes(context, E['evaluation_id'])
    grlabs = [ g['group_name'] or 'tous' for g in groups ]  # legendes des boutons
    grnams  = [ g['group_id'] for g in groups ] # noms des checkbox
    if len(evals) > 1:
        descr = [
            ('moduleimpl_id',
             { 'default' : E['moduleimpl_id'], 'input_type' : 'hidden' }) ]
    else:
        descr = [
            ('evaluation_id',
             { 'default' : E['evaluation_id'], 'input_type' : 'hidden' }) ]
    descr += [
        ('s' ,
         {'input_type' : 'separator',
          'title': '<b>Choix du ou des groupes d\'étudiants:</b>' }),
        ('group_ids',
         { 'input_type' : 'checkbox', 'title':'',
           'allowed_values' : grnams, 'labels' : grlabs,
           'attributes' : ('onclick="document.tf.submit();"',) }),
        ('anonymous_listing',
         { 'input_type' : 'checkbox', 'title':'',
           'allowed_values' : ('yes',), 'labels' : ('listing "anonyme"',),
           'attributes' : ('onclick="document.tf.submit();"',),
           'template' : '<tr><td class="tf-fieldlabel">%(label)s</td><td class="tf-field">%(elem)s &nbsp;&nbsp;'
           }),
        ('note_sur_20',
         { 'input_type' : 'checkbox', 'title':'',
           'allowed_values' : ('yes',), 'labels' : ('notes sur 20',),
           'attributes' : ('onclick="document.tf.submit();"',),
           'template' : '%(elem)s</td></tr>'
           }),            
        ]
    tf = TrivialFormulator( REQUEST.URL0, REQUEST.form, descr,
                            cancelbutton=None, submitbutton=None, bottom_buttons=False,
                            method='GET',
                            cssclass='noprint',
                            name='tf',
                            is_submitted = True # toujours "soumis" (démarre avec liste complète)
                            )
    if  tf[0] == 0:
        return '\n'.join(H) + '\n' + tf[1]
    elif tf[0] == -1:
        return REQUEST.RESPONSE.redirect( '%s/Notes/moduleimpl_status?moduleimpl_id=%s'
                                          % (context.ScoURL(),E['moduleimpl_id']) )
    else:
        anonymous_listing = tf[2]['anonymous_listing']
        note_sur_20 = tf[2]['note_sur_20']
        return _make_table_notes(context, REQUEST, tf[1], evals, 
                                 format=format, note_sur_20=note_sur_20,
                                 anonymous_listing=anonymous_listing, group_ids=tf[2]['group_ids'])

def _make_table_notes(context, REQUEST, html_form, evals, 
                      format='', 
                      note_sur_20=False, anonymous_listing=False,
                      group_ids=[] ):
    """Generate table for evaluations marks"""
    if not evals:
        return '<p>Aucune évaluation !</p>'
    E = evals[0]
    moduleimpl_id = E['moduleimpl_id']
    M = context.do_moduleimpl_list( args={ 'moduleimpl_id' : moduleimpl_id  } )[0]
    Mod = context.do_module_list( args={ 'module_id' : M['module_id'] } )[0]
    sem = context.get_formsemestre(M['formsemestre_id'])
    # (debug) check that all evals are in same module:
    for e in evals:
        if e['moduleimpl_id'] != moduleimpl_id:
            raise ValueError('invalid evaluations list')
    
    if format == 'xls':
        keep_numeric = True # pas de conversion des notes en strings
    else:
        keep_numeric = False
    # Si pas de groupe, affiche tout
    if not group_ids:
        group_ids = [sco_groups.get_default_group(context, M['formsemestre_id'])]
    groups = sco_groups.listgroups(context, group_ids)
    
    gr_title = sco_groups.listgroups_abbrev(groups)
    gr_title_filename = sco_groups.listgroups_filename(groups)    
    
    etudids = sco_groups.do_evaluation_listeetuds_groups(
        context, E['evaluation_id'], groups, include_dems=True)
    
    if anonymous_listing:
        columns_ids = ['code', 'group' ] # cols in table
    else:
        if format == 'xls' or format == 'xml':
            columns_ids = ['nom', 'prenom', 'group' ]
        else:
            columns_ids = ['nomprenom', 'group' ]        
    
    titles={ 'code' : 'Code', 'group' : 'Groupe', 
             'nom' : 'Nom', 'prenom' : 'Prénom', 'nomprenom' : 'Nom',
             'expl_key' : 'Rem.' }

    rows = []

    class keymgr(dict): # comment : key (pour regrouper les comments a la fin)
        def __init__(self):
            self.lastkey = 'a'
        def nextkey(self):
            r = self.lastkey
            self.lastkey = chr(ord(self.lastkey)+1)
            return r

    K = keymgr() 
    for etudid in etudids:
        css_row_class = None
        # infos identite etudiant
        etud = context.getEtudInfo(etudid=etudid,filled=1)[0]
        # infos inscription
        inscr = context.do_formsemestre_inscription_list(
            {'etudid':etudid, 'formsemestre_id' : M['formsemestre_id']})[0]
        
        if inscr['etat'] == 'I': # si inscrit, indique groupe
            groups = sco_groups.get_etud_groups(context, etudid, sem)
            grc = sco_groups.listgroups_abbrev(groups)
        else:
            if inscr['etat'] == 'D':
                grc = 'DEM' # attention: ce code est re-ecrit plus bas, ne pas le changer (?)
                css_row_class = 'etuddem'
            else:
                grc = inscr['etat']
                
        rows.append( { 'code' : etud['code_nip'] or etudid,
                       '_code_td_attrs' : 'style="padding-left: 1em; padding-right: 2em;"',
                       'etudid' : etudid,
                       'nom' : etud['nom'].upper(),
                       '_nomprenom_target' : 'formsemestre_bulletinetud?formsemestre_id=%s&etudid=%s' % (M['formsemestre_id'], etudid),
                       'prenom' : etud['prenom'].lower().capitalize(),
                       'nomprenom' : etud['nomprenom'],
                       'group' : grc,
                       
                       '_css_row_class' : css_row_class or '',
                       } )

    #    lignes en tête:
    coefs = { 'nom' : '', 'prenom':'', 'nomprenom' : '', 'group' : '', 'code':'',
              '_css_row_class' : 'sorttop fontitalic' }
    note_max = { 'nom' : '', 'prenom':'', 'nomprenom' : '', 'group' : '', 'code':'',
                 '_css_row_class' : 'sorttop fontitalic' }
    moys = { '_css_row_class' : 'moyenne sortbottom',
             #'_nomprenom_td_attrs' : 'colspan="2" ',
             'nomprenom' : 'Moyenne (sans les absents) :',
             'comment' : '' }
    # Ajoute les notes de chaque évaluation:
    for e in evals:
        e['eval_state'] = context.do_evaluation_etat(e['evaluation_id'])[0]
        notes = _add_eval_columns(context, e, rows, titles, coefs, note_max, moys, K, 
                          note_sur_20, keep_numeric)
        columns_ids.append(e['evaluation_id'])
    #
    if anonymous_listing:
        rows.sort( key=lambda x: x['code'] )
    else:
        rows.sort( key=lambda x: (x['nom'], x['prenom'])) # sort by nom, prenom

    # Si module, ajoute moyenne du module:
    if len(evals) > 1:
        notes =  _add_moymod_column(context, sem['formsemestre_id'], e, rows, titles, coefs,
                                    note_max, moys, 
                                    note_sur_20, keep_numeric)
        columns_ids.append('moymod')
    
    # ajoute lignes en tête et moyennes    
    if len(evals) > 0: 
        rows = [coefs, note_max] + rows
    rows.append(moys)
    # ajout liens HTMl vers affichage une evaluation:
    if format == 'html' and len(evals) > 1:
        rlinks = {}
        for e in evals:
            rlinks[e['evaluation_id']] = 'afficher'
            rlinks['_'+e['evaluation_id']+'_help'] = 'afficher seulement les notes de cette évaluation'
            rlinks['_'+e['evaluation_id']+'_target'] = 'evaluation_listenotes?evaluation_id=' + e['evaluation_id']
            rlinks['_'+e['evaluation_id']+'_td_attrs'] = ' class="tdlink" '
        rows.append(rlinks)

    if len(evals) == 1: # colonne "Rem." seulement si une eval
        if format == 'html': # pas d'indication d'origine en pdf (pour affichage)
            columns_ids.append( 'expl_key' ) 
        elif (format == 'xls' or format == 'xml'):
            columns_ids.append( 'comment' ) 
    
    # titres divers:
    gl = ''.join([ '&group_ids%3Alist=' + g for g in group_ids ])
    if note_sur_20:
        gl = '&note_sur_20%3Alist=yes' + gl
    if anonymous_listing:
        gl = '&anonymous_listing%3Alist=yes' + gl

    if len(evals) == 1:
        evalname = '%s-%s' % (Mod['code'],DateDMYtoISO(E['jour']))
        hh = '%s, %s (%d étudiants)' % (E['description'], gr_title,len(etudids))
        filename = make_filename('notes_%s_%s' % (evalname,gr_title_filename))
        caption = hh
        pdf_title = '%(description)s (%(jour)s)' % e
        html_title= ''
        base_url = 'evaluation_listenotes?evaluation_id=%s'%E['evaluation_id'] + gl
    else:
        filename = make_filename('notes_%s_%s' % (Mod['code'],gr_title_filename))
        title = 'Notes du module %(code)s %(titre)s' % Mod
        title += ' semestre %(titremois)s' % sem
        if gr_title and gr_title != 'tous':
            title += ' %s' % gr_title
        caption = title
        if format == 'pdf':
            caption = '' # same as pdf_title
        pdf_title = title
        html_title="""<h2 class="formsemestre">Notes du module <a href="moduleimpl_status?moduleimpl_id=%s">%s %s</a></h2>"""% (moduleimpl_id, Mod['code'], Mod['titre'])
        base_url = 'evaluation_listenotes?moduleimpl_id=%s'%moduleimpl_id + gl
    # display
    tab = GenTable( titles=titles, columns_ids=columns_ids,
                    rows=rows, 
                    html_sortable=True,
                    base_url = base_url,
                    filename=filename,
                    origin = 'Généré par %s le ' % VERSION.SCONAME + timedate_human_repr() + '',
                    caption = caption,
                    page_title = 'Notes de ' + sem['titremois'],
                    html_title=html_title,
                    pdf_title = pdf_title,
                    html_class='gt_table table_leftalign notes_evaluation',
                    preferences=context.get_preferences(M['formsemestre_id']),
                    #generate_cells=False # la derniere ligne (moyennes) est incomplete
                    )
    
    t = tab.make_page(context, format=format, with_html_headers=False, REQUEST=REQUEST)
    if format != 'html':
        return t

    if len(evals) > 1:
        all_complete = True
        for e in evals:
            if not e['eval_state']['evalcomplete']:
                all_complete = False
        if all_complete:
            eval_info = '<span class="eval_info eval_complete">Evaluations prises en compte dans les moyennes</span>'
        else:
            eval_info = '<span class="eval_info help">Les évaluations en vert et orange sont prises en compte dans les moyennes. Celles en rouge n\'ont pas toutes leurs notes.</span>'
        return   html_form + eval_info + t + '<p></p>'
    else:
        # Une seule evaluation: ajoute histogramme
        histo = histogram_notes(notes)
        # 2 colonnes: histo, comments
        C = ['<table><tr><td><div><h4>Répartition des notes:</h4>' + histo + '</div></td>\n',
             '<td style="padding-left: 50px; vertical-align: top;"><p>' ]
        commentkeys = K.items() # [ (comment, key), ... ]
        commentkeys.sort( lambda x,y: cmp(x[1], y[1]) )
        for (comment,key) in commentkeys:
            C.append('<span class="colcomment">(%s)</span> <em>%s</em><br/>' % (key, comment))
        if commentkeys:
            C.append('<span><a class=stdlink" href="evaluation_list_operations?evaluation_id=%s">Gérer les opérations</a></span><br/>' % E['evaluation_id'])
        eval_info = 'xxx'
        if E['eval_state']['evalcomplete']:
            eval_info = '<span class="eval_info eval_complete">Evaluation prise en compte dans les moyennes</span>'
        elif E['eval_state']['evalattente']:
            eval_info = '<span class="eval_info eval_attente">Il y a des notes en attente (les autres sont prises en compte)</span>'
        else:
            eval_info = '<span class="eval_info eval_incomplete">Notes incomplètes, évaluation non prise en compte dans les moyennes</span>'
            
        return context.evaluation_create_form(evaluation_id=E['evaluation_id'], REQUEST=REQUEST, readonly=1) + eval_info + html_form + t + '\n'.join(C)


    
def _add_eval_columns(context, e, rows, titles, coefs, note_max, moys, K, 
                      note_sur_20, keep_numeric):
    """Add eval e"""
    nb_notes = 0
    sum_notes = 0
    notes = [] # liste des notes numeriques, pour calcul histogramme uniquement
    evaluation_id = e['evaluation_id']
    NotesDB = context._notes_getall(evaluation_id)
    for row in rows:
        etudid = row['etudid']
        if NotesDB.has_key(etudid):
            val = NotesDB[etudid]['value']
            # calcul moyenne SANS LES ABSENTS
            if val != None and val != NOTES_NEUTRALISE and val != NOTES_ATTENTE: 
                valsur20 = val * 20. / e['note_max'] # remet sur 20
                notes.append(valsur20) # toujours sur 20 pour l'histogramme
                if note_sur_20:                            
                    val = valsur20 # affichage notes / 20 demandé
                nb_notes = nb_notes + 1
                sum_notes += val
            val_fmt = fmt_note(val, keep_numeric=keep_numeric)
            comment = NotesDB[etudid]['comment']
            if comment is None:
                comment = ''
            explanation = '%s (%s) %s' % (NotesDB[etudid]['date'].strftime('%d/%m/%y %Hh%M'),
                                          NotesDB[etudid]['uid'],comment)
        else:
            explanation = ''
            val_fmt = ''
            val = None
        
        if val is None:
            row['_'+evaluation_id+'_td_attrs'] = 'class="etudabs" '
            if not row.get('_css_row_class', ''):
                row['_css_row_class'] = 'etudabs'
        # regroupe les commentaires
        if explanation:
            if K.has_key(explanation):
                expl_key = '(%s)' % K[explanation]
            else:
                K[explanation] = K.nextkey()
                expl_key = '(%s)' % K[explanation]
        else:
            expl_key = ''
        
        row.update( {evaluation_id : val_fmt,
                     '_'+evaluation_id+'_help' : explanation,
                     # si plusieurs evals seront ecrasés et non affichés:
                     'comment' : explanation,
                     'expl_key' : expl_key,
                     '_expl_key_help' : explanation} )
        
        coefs[evaluation_id] = 'coef. %s' % e['coefficient']
        if note_sur_20:
            nmx = 20.
        else:
            nmx = e['note_max']
        if keep_numeric:
            note_max[evaluation_id] = nmx
        else:
            note_max[evaluation_id] = '/ %s' % nmx

        if nb_notes > 0:
            moys[evaluation_id] = '%.3g' % (sum_notes/nb_notes)
            moys['_'+evaluation_id+'_help'] = ('moyenne sur %d notes (%s le %s)' 
                                               % (nb_notes, e['description'], e['jour']))
        else:
            moys[evaluation_id] = ''
        
        titles[evaluation_id] = '%(description)s (%(jour)s)' % e
        
        if e['eval_state']['evalcomplete']:
            titles['_'+evaluation_id+'_td_attrs'] = 'class="eval_complete"'
        elif e['eval_state']['evalattente']:
            titles['_'+evaluation_id+'_td_attrs'] = 'class="eval_attente"'
        else:
            titles['_'+evaluation_id+'_td_attrs'] = 'class="eval_incomplete"'

    return notes # pour histogramme

def _add_moymod_column(context, formsemestre_id, e, rows, titles, coefs, note_max, moys, 
                       note_sur_20, keep_numeric):
    col_id = 'moymod'
    nt = context._getNotesCache().get_NotesTable(context, formsemestre_id)
    nb_notes = 0
    sum_notes = 0
    notes = [] # liste des notes numeriques, pour calcul histogramme uniquement
    for row in rows:
        etudid = row['etudid']
        val = nt.get_etud_mod_moy(e['moduleimpl_id'], etudid) # note sur 20, ou 'NA','NI'
        row[col_id] = fmt_note(val, keep_numeric=keep_numeric)
        row['_'+col_id+'_td_attrs'] = ' class="moyenne" '
        if type(val) != StringType:
            notes.append(val)
            nb_notes = nb_notes + 1
            sum_notes += val
    coefs[col_id] = ''
    if keep_numeric:
        note_max[col_id] = 20.
    else:
        note_max[col_id] = '/ 20'
    titles[col_id] = 'Moyenne module'
    if nb_notes > 0:
        moys[col_id] = '%.3g' % (sum_notes/nb_notes)
        moys['_'+col_id+'_help'] = 'moyenne des moyennes' 
    else:
        moys[col_id] = ''



# ---------------------------------------------------------------------------------


# matin et/ou après-midi ?
def _eval_demijournee(E):
    "1 si matin, 0 si apres midi, 2 si toute la journee"
    am, pm = False, False
    if E['heure_debut'] < '13:00':
        am = True
    if E['heure_fin'] > '13:00':
        pm = True
    if am and pm:
        demijournee = 2
    elif am:
        demijournee = 1
    else:
        demijournee = 0
        pm = True
    return am, pm, demijournee

def evaluation_check_absences(context, evaluation_id):
    """Vérifie les absences au moment de cette évaluation.
    Cas incohérents que l'on peut rencontrer pour chaque étudiant:
      note et absent  
      ABS et pas noté absent
      EXC et pas noté absent
      EXC et pas justifie
    Ramene 3 listes d'etudid
    """
    E = context.do_evaluation_list({'evaluation_id' : evaluation_id})[0]
    M = context.do_moduleimpl_list({'moduleimpl_id' : E['moduleimpl_id']})[0]
    formsemestre_id = M['formsemestre_id']
    etudids = sco_groups.do_evaluation_listeetuds_groups(context, evaluation_id, getallstudents=True)
    
    am, pm, demijournee = _eval_demijournee(E)
    
    # Liste les absences à ce moment:
    A = context.Absences.ListeAbsJour(DateDMYtoISO(E['jour']), am=am, pm=pm)
    As = Set( [ x['etudid'] for x in A ] ) # ensemble des etudiants absents
    NJ = context.Absences.ListeAbsNonJustJour(DateDMYtoISO(E['jour']), am=am, pm=pm)

    NJs = Set( [ x['etudid'] for x in NJ ] )# ensemble des etudiants absents non justifies
    # Les notes:
    NotesDB = context._notes_getall(evaluation_id)
    ValButAbs = [] # une note mais noté absent
    AbsNonSignalee = [] # note ABS mais pas noté absent
    ExcNonSignalee = [] # note EXC mais pas noté absent
    ExcNonJust = [] #  note EXC mais absent non justifie
    for etudid in etudids:
        if NotesDB.has_key(etudid):
            val = NotesDB[etudid]['value']
            if (val != None and val != NOTES_NEUTRALISE and val != NOTES_ATTENTE) and etudid in As:
                # note valide et absent
                ValButAbs.append(etudid)
            if val is None and not etudid in As:
                # absent mais pas signale comme tel
                AbsNonSignalee.append(etudid)
            if val == NOTES_NEUTRALISE and not etudid in As:
                # nbeutralise mais pas signale absent
                ExcNonSignalee.append(etudid)
            if val == NOTES_NEUTRALISE and etudid in NJs:
                # EXC mais pas justifie
                ExcNonJust.append(etudid)

    return ValButAbs, AbsNonSignalee, ExcNonSignalee, ExcNonJust


def evaluation_check_absences_html(context, evaluation_id, with_header=True, show_ok=True, REQUEST=None):
    """Affiche etat verification absences d'une evaluation"""

    E = context.do_evaluation_list({'evaluation_id' : evaluation_id})[0]
    am, pm, demijournee = _eval_demijournee(E)
    
    ValButAbs, AbsNonSignalee, ExcNonSignalee, ExcNonJust = evaluation_check_absences(context, evaluation_id)

    if with_header:
        H = [ context.html_sem_header(REQUEST, "Vérification absences à l'évaluation"),
              context.evaluation_create_form(evaluation_id=evaluation_id, REQUEST=REQUEST, readonly=1),
              """<p class="help">Vérification de la cohérence entre les notes saisies et les absences signalées.</p>"""]
    else:
        # pas de header, mais un titre
        H = [ """<h2 class="eval_check_absences">%s du %s """
              % (E['description'], E['jour'])
              ]
        if not ValButAbs and not AbsNonSignalee and not ExcNonSignalee and not ExcNonJust:
            H.append(': <span class="eval_check_absences_ok">ok</span>')
        H.append('</h2>')

    def etudlist(etudids, linkabs=False):
        H.append('<ul>')
        if not etudids and show_ok:
            H.append('<li>aucun</li>')        
        for etudid in etudids:
            etud = context.getEtudInfo(etudid=etudid,filled=True)[0]
            H.append('<li><a class="discretelink" href="ficheEtud?etudid=%(etudid)s">%(nomprenom)s</a>' % etud )
            if linkabs:
                H.append('<a class="stdlink" href="Absences/doSignaleAbsence?etudid=%s&datedebut=%s&datefin=%s&demijournee=%s">signaler cette absence</a>'
                         % (etud['etudid'],urllib.quote(E['jour']), urllib.quote(E['jour']), demijournee) )
            H.append('</li>')
        H.append('</ul>')

    if ValButAbs or show_ok:
        H.append("<h3>Etudiants ayant une note alors qu'ils sont signalés absents:</h3>")
        etudlist(ValButAbs)

    if AbsNonSignalee or show_ok:
        H.append("""<h3>Etudiants avec note "ABS" alors qu'ils ne sont <em>pas</em> signalés absents:</h3>""")
        etudlist(AbsNonSignalee, linkabs=True)

    if ExcNonSignalee or show_ok:
        H.append("""<h3>Etudiants avec note "EXC" alors qu'ils ne sont <em>pas</em> signalés absents:</h3>""")
        etudlist(ExcNonSignalee)

    if ExcNonJust or show_ok:
        H.append("""<h3>Etudiants avec note "EXC" alors qu'ils sont absents <em>non justifés</em>:</h3>""")
        etudlist(ExcNonJust)

    if with_header:
        H.append(context.sco_footer(REQUEST))
    return '\n'.join(H)

def formsemestre_check_absences_html(context, formsemestre_id, REQUEST=None):
    """Affiche etat verification absences pour toutes les evaluations du semestre !
    """
    sem = context.get_formsemestre(formsemestre_id)
    H = [ context.html_sem_header(REQUEST, 'Vérification absences aux évaluations de ce semestre', sem),
          """<p class="help">Vérification de la cohérence entre les notes saisies et les absences signalées.
          Sont listés tous les modules avec des évaluations.<br/>Aucune action n'est effectuée:
          il vous appartient de corriger les erreurs détectées si vous le jugez nécessaire.
          </p>"""]
    # Modules, dans l'ordre
    Mlist = context.do_moduleimpl_withmodule_list( args={ 'formsemestre_id' : formsemestre_id } )
    for M in Mlist:
        evals = context.do_evaluation_list( { 'moduleimpl_id' : M['moduleimpl_id'] } )        
        if evals:
            H.append( '<div class="module_check_absences"><h2><a href="moduleimpl_status?moduleimpl_id=%s">%s: %s</a></h2>'
                      % (M['moduleimpl_id'],M['module']['code'],M['module']['abbrev']) )
        for E in evals:
            H.append( evaluation_check_absences_html(context, E['evaluation_id'],
                                                     with_header=False, show_ok=False, REQUEST=REQUEST) )
        if evals:
            H.append('</div>')
    H.append(context.sco_footer(REQUEST))
    return '\n'.join(H)
