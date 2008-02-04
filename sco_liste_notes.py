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

"""Liste des notes d'une évaluation
"""

from notesdb import *
from sco_utils import *
from notes_log import log
from TrivialFormulator import TrivialFormulator, TF
from notes_table import *
import htmlutils
import sco_excel
from gen_tables import GenTable

from sets import Set

def do_evaluation_listenotes(self, REQUEST):
    """
    Affichage des notes d'une évaluation


    args: evaluation_id 
    """        
    cnx = self.GetDBConnexion()
    evaluation_id = REQUEST.form['evaluation_id']
    E = self.do_evaluation_list( {'evaluation_id' : evaluation_id})[0]
    M = self.do_moduleimpl_list( args={ 'moduleimpl_id' : E['moduleimpl_id'] } )[0]
    formsemestre_id = M['formsemestre_id']
    # description de l'evaluation    
    H = [ self.evaluation_create_form(evaluation_id=evaluation_id, REQUEST=REQUEST, readonly=1) ]
    # groupes
    gr_td, gr_tp, gr_anglais = self.do_evaluation_listegroupes(evaluation_id)
    grnams  = [('td'+x) for x in gr_td ] # noms des checkbox
    grnams += [('tp'+x) for x in gr_tp ]
    grnams += [('ta'+x) for x in gr_anglais ]
    grlabs  = gr_td + gr_tp + gr_anglais # legendes des boutons
    descr = [
        ('evaluation_id',
         { 'default' : evaluation_id, 'input_type' : 'hidden' }),
        ('liste_format',
         {'input_type' : 'radio', 'default' : 'html', 'allow_null' : False, 
          'allowed_values' : [ 'html', 'pdf', 'xls' ],
          'labels' : ['page HTML', 'fichier PDF', 'fichier tableur' ],
          'attributes' : ('onclick="document.tf.submit();"',),
          'title' : 'Format' }),
        ('s' ,
         {'input_type' : 'separator',
          'title': 'Choix du ou des groupes d\'étudiants' }),
        ('groupes',
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
                            cancelbutton=None, submitbutton=None,
                            method='GET',
                            cssclass='noprint',
                            name='tf',
                            is_submitted = True # toujours "soumis" (démarre avec liste complète)
                            )
    if  tf[0] == 0:
        return '\n'.join(H) + '\n' + tf[1]
    elif tf[0] == -1:
        return REQUEST.RESPONSE.redirect( '%s/Notes/moduleimpl_status?moduleimpl_id=%s'
                                          % (self.ScoURL(),E['moduleimpl_id']) )
    else:
        liste_format = tf[2]['liste_format']
        anonymous_listing = tf[2]['anonymous_listing']
        note_sur_20 = tf[2]['note_sur_20']
        if liste_format == 'xls':
            keep_numeric = True # pas de conversion des notes en strings
        else:
            keep_numeric = False
        # Build list of etudids (uniq, some groups may overlap)
        glist = tf[2]['groupes']
        gr_td = [ x[2:] for x in glist if x[:2] == 'td' ]
        gr_tp = [ x[2:] for x in glist if x[:2] == 'tp' ]
        gr_anglais = [ x[2:] for x in glist if x[:2] == 'ta' ]
        g = gr_td+gr_tp+gr_anglais
        gr_title_filename = 'gr' + '+'.join(gr_td+gr_tp+gr_anglais)
        if len(g) > 1:
            gr_title = 'groupes ' + ', '.join(g)                
        elif len(g) == 1:            
            gr_title = 'groupe ' + g[0]
        else:
            gr_title = ''
        if not glist:# aucun groupe selectionne: affiche tous les etudiants
            getallstudents = True
            gr_title = 'tous'
            gr_title_filename = 'tous'
        else:
            getallstudents = False
        NotesDB = self._notes_getall(evaluation_id)
        etudids = self.do_evaluation_listeetuds_groups(evaluation_id,
                                                       gr_td,gr_tp,gr_anglais,
                                                       getallstudents=getallstudents)
        E = self.do_evaluation_list( {'evaluation_id' : evaluation_id})[0]
        M = self.do_moduleimpl_list( args={ 'moduleimpl_id' : E['moduleimpl_id'] } )[0]
        Mod = self.do_module_list( args={ 'module_id' : M['module_id'] } )[0]
        evalname = '%s-%s' % (Mod['code'],DateDMYtoISO(E['jour']))
        hh = '<h4>%s du %s, %s (%d étudiants)</h4>' % (E['description'], E['jour'], gr_title,len(etudids))
        if note_sur_20:
            nmx = 20
        else:
            nmx = E['note_max']
        Th = ['', 'Nom', 'Prénom', 'Groupe', 'Note sur %d'%nmx,
              'Rem.']
        T = [] # list of lists, used to build HTML and CSV
        nb_notes = 0
        sum_notes = 0
        notes = [] # liste des notes numeriques, pour calcul histogramme uniquement
        for etudid in etudids:
            # infos identite etudiant (xxx sous-optimal: 1/select par etudiant)
            ident = scolars.etudident_list(cnx, { 'etudid' : etudid })[0]
            # infos inscription
            inscr = self.do_formsemestre_inscription_list(
                {'etudid':etudid, 'formsemestre_id' : M['formsemestre_id']})[0]
            if NotesDB.has_key(etudid):
                val = NotesDB[etudid]['value']
                # calcul moyenne SANS LES ABSENTS
                if val != None and val != NOTES_NEUTRALISE and val != NOTES_ATTENTE: 
                    valsur20 = val * 20. / E['note_max'] # remet sur 20
                    notes.append(valsur20) # toujours sur 20 pour l'histogramme
                    if note_sur_20:                            
                        val = valsur20 # affichage notes / 20 demandé
                    nb_notes = nb_notes + 1
                    sum_notes += val
                val = fmt_note(val, keep_numeric=keep_numeric)
                comment = NotesDB[etudid]['comment']
                if comment is None:
                    comment = ''
                explanation = '%s (%s) %s' % (NotesDB[etudid]['date'].strftime('%d/%m/%y %Hh%M'),
                                              NotesDB[etudid]['uid'],comment)
            else:
                explanation = ''
                val = ''
            if inscr['etat'] == 'I': # si inscrit, indique groupe
                grc=inscr['groupetd']
                if inscr['groupetp']:
                    grc += '/' + inscr['groupetp']
                if inscr['groupeanglais']:
                    grc += '/' + inscr['groupeanglais']
            else:
                if inscr['etat'] == 'D':
                    grc = 'DEM' # attention: ce code est re-ecrit plus bas, ne pas le changer
                else:
                    grc = inscr['etat']
            T.append( [ etudid, ident['nom'].upper(),
                        ident['prenom'].lower().capitalize(),
                        grc, val, explanation ] )
        T.sort( lambda x,y: cmp(x[1:3],y[1:3]) ) # sort by nom, prenom
        # display
        if liste_format == 'csv':
            CSV = CSV_LINESEP.join( [ CSV_FIELDSEP.join(x) for x in [Th]+T ] )
            filename = 'notes_%s_%s.csv' % (evalname,gr_title_filename)
            return sendCSVFile(REQUEST,CSV, filename ) 
        elif liste_format == 'xls':
            title = 'notes_%s_%s' % (evalname, gr_title_filename)
            xls = sco_excel.Excel_SimpleTable(
                titles= Th,
                lines = T,
                SheetName = title )
            filename = title + '.xls'
            return sco_excel.sendExcelFile(REQUEST, xls, filename )
        elif liste_format == 'html':
            if T:
                if anonymous_listing:
                    # ce mode bizarre a été demandé par GTR1 en 2005
                    Th = [ '', Th[4] ]
                    # tri par note decroissante (anonymisation !)
                    def mcmp(x,y):                            
                        try:
                            return cmp(float(y[4]), float(x[4]))
                        except:
                            return cmp(y[4], x[4])
                    T.sort( mcmp )
                else:
                    Th = [ Th[1], Th[2], Th[4], Th[5] ]
                Th = [ '<th>' + '</th><th>'.join(Th) + '</th>' ]
                Tb = []
                demfmt = '<span class="etuddem">%s</span>'
                absfmt = '<span class="etudabs">%s</span>'
                cssclass = 'tablenote'
                idx = 0
                lastkey = 'a'
                comments = {} # comment : key (pour regrouper les comments a la fin)
                for t in T:
                    idx += 1
                    fmt='%s'
                    if t[3] == 'DEM':
                        fmt = demfmt
                        comment =  t[3]+' '+t[5]
                    elif t[4][:3] == 'ABS':
                        fmt = absfmt
                    nomlink = '<a href="formsemestre_bulletinetud?formsemestre_id=%s&etudid=%s">%s</a>' % (M['formsemestre_id'],t[0],t[1])
                    nom,prenom,note,comment = fmt%nomlink, fmt%t[2],fmt%t[4],t[5]
                    if anonymous_listing:
                        Tb.append( '<tr class="%s"><td>%s</td><td class="colnote">%s</td></tr>' % (cssclass, t[0], note) )
                    else:
                        if comment:
                            if comments.has_key(comment):
                                key = comments[comment]
                            else:
                                comments[comment] = lastkey
                                key = lastkey
                                lastkey = chr(ord(lastkey)+1)
                        else:
                            key = ''
                        Tb.append( '<tr class="%s"><td>%s</td><td>%s</td><td class="colnote">%s</td><td class="colcomment">%s</td></tr>' % (cssclass,nom,prenom,note,key) )
                Tb = [ '\n'.join(Tb ) ]

                if nb_notes > 0:
                    moy = '%.3g' % (sum_notes/nb_notes)
                else:
                    moy = 'ND'
                if anonymous_listing:
                    Tm = [ '<tr class="tablenote"><td colspan="2" class="colnotemoy">Moyenne %s</td></tr>' % moy ]
                else:
                    Tm = [ '<tr class="tablenote"><td colspan="2" style="text-align: right;"><b>Moyenne</b> sur %d notes (sans les absents) :</td><td class="colnotemoy">%s</td></tr>' % (nb_notes, moy) ]
                if anonymous_listing:
                    tclass='tablenote_anonyme'
                else:
                    tclass='tablenote'
                from htmlutils import histogram_notes
                histo = histogram_notes(notes)
                # 2 colonnes: histo, comments
                C = ['<table><tr><td><div><h4>Répartition des notes:</h4>' + histo + '</div></td>\n',
                     '<td style="padding-left: 50px; vertical-align: top;"><p>' ]
                commentkeys = comments.items() # [ (comment, key), ... ]
                commentkeys.sort( lambda x,y: cmp(x[1], y[1]) )
                for (comment,key) in commentkeys:
                    C.append('<span class="colcomment">(%s)</span> <em>%s</em><br/>' % (key, comment))

                Tab = [ '<table class="%s"><tr class="tablenotetitle">'%tclass ] + Th + ['</tr><tr><td>'] + Tb + Tm + [ '</td></tr></table>' ] + C
            else:
                Tab = [ '<span class="boldredmsg">aucun groupe sélectionné !</span>' ]
            # XXX return tf[1] + '\n'.join(H) + hh + '\n'.join(Tab) 
            return self.evaluation_create_form(evaluation_id=evaluation_id, REQUEST=REQUEST, readonly=1) + tf[1] + hh + '\n'.join(Tab)
        elif liste_format == 'pdf':
            return 'conversion PDF non implementée !'
        else:
            raise ScoValueError('invalid value for liste_format (%s)'%liste_format)


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
    etudids = context.do_evaluation_listeetuds_groups(evaluation_id, getallstudents=True)
    
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
        H = [ context.sco_header(REQUEST, page_title='Vérification absences évaluation'),
              '<h2>Vérification absences à une évaluation</h2>',
              context.evaluation_create_form(evaluation_id=evaluation_id, REQUEST=REQUEST, readonly=1),
              """<p>Vérification de la cohérence entre les notes saisies et les absences signalées.</p>"""]
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
    H = [ context.sco_header(REQUEST, page_title='Vérification absences évaluations'),
          '<h2>Vérification absences aux évaluations du semestre %s</h2>' % sem['titreannee'],
          """<p>Vérification de la cohérence entre les notes saisies et les absences signalées.
          Sont listés tous les modules avec des évaluations. Aucune action n'est effectuée:
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

# ------------------------------------------------------------------------------


def moduleimpl_listenotes(context, moduleimpl_id, format='html', REQUEST=None):
    """Tableau avec toutes les notes saisies dans un module.
    """
    M = context.do_moduleimpl_withmodule_list( args={ 'moduleimpl_id' : moduleimpl_id } )[0]
    formsemestre_id = M['formsemestre_id']
    sem = context.do_formsemestre_list( args={ 'formsemestre_id' : formsemestre_id } )[0]
    
    # [ { etudid: etudid, nom : nom, prenom : prenom, evaluation1_id : note, evaluation2_id : note, ... } ]
    R = []
    # Get liste de tous les etudiants inscrits a ce module
    etudids = context.do_moduleimpl_listeetuds(moduleimpl_id)
    for etudid in etudids:
        R.append( context.getEtudInfo(etudid=etudid, filled=True)[0] )
    
    # Rempli les notes de chaque eval:
    evals = context.do_evaluation_list( {'moduleimpl_id' : moduleimpl_id})
    for e in evals:
        NotesDB = context._notes_getall(e['evaluation_id'])
        for r in R:
            n = NotesDB.get(r['etudid'],None)
            if n:
                val = fmt_note( n['value'], keep_numeric=False) # keep numeric ?
            else:
                val = 'NA'
            r[e['evaluation_id']] = val
    #
    titles = {}
    if format == 'xls' or format == 'xml':
        columns_ids = [ 'etudid' ]
        titles['etudid'] = 'etudid'
    else:
        columns_ids = []
    columns_ids += [ 'nom', 'prenom' ]
    titles['nom'] = 'Nom'
    titles['prenom'] = 'Prénom'
    for e in evals:
        columns_ids.append( e['evaluation_id'] )
        titles[e['evaluation_id']] = '%(description)s (%(jour)s)' % e

    title = 'Toutes les notes du module %(code)s %(titre)s' % M['module']
    title += ' (semestre %(titreannee)s)' % sem
    tab = GenTable(
        columns_ids=columns_ids, rows=R, titles=titles,
        origin = 'Généré par %s le ' % VERSION.SCONAME + timedate_human_repr() + '',
        caption = title,
        html_caption = title,
        html_sortable=True,
        base_url = '%s?moduleimpl_id=%s' % (REQUEST.URL0, moduleimpl_id),
        page_title = title,
        html_title = """<h2>Notes du module <a href="moduleimpl_status?moduleimpl_id=%s">%s %s</a>, semestre <a href="formsemestre_status?formsemestre_id=%s">%s</a></h2>
        <p class="help">Attention: toutes ces notes ne sont pas forcément déjà prise en compte dans le moyennes
        (seules les évaluations complètes le sont).
        </p>
        """ % (moduleimpl_id, M['module']['code'], M['module']['titre'], formsemestre_id, sem['titreannee']),
        pdf_title = title
        )
    return tab.make_page(context, format=format, REQUEST=REQUEST)      


    
