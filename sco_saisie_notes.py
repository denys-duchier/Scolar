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

"""Saisie des notes
"""
import datetime

from notesdb import *
from sco_utils import *
from notes_log import log
from TrivialFormulator import TrivialFormulator, TF
from notes_table import *
import sco_groups
import htmlutils
import sco_excel
import scolars
import sco_news
from sco_news import NEWS_INSCR, NEWS_NOTE, NEWS_FORM, NEWS_SEM, NEWS_MISC

def do_evaluation_selectetuds(context, REQUEST ):
    """
    Choisi les etudiants pour saisie notes
    """
    evaluation_id = REQUEST.form['evaluation_id']
    E = context.do_evaluation_list( {'evaluation_id' : evaluation_id})
    if not E:
        raise ScoValueError("invalid evaluation_id")
    E = E[0]
    M = context.do_moduleimpl_list( args={ 'moduleimpl_id' : E['moduleimpl_id'] } )[0]
    formsemestre_id = M['formsemestre_id']
    # groupes
    groups = sco_groups.do_evaluation_listegroupes(context,evaluation_id, include_default=True)
    grlabs = [ g['group_name'] or 'tous' for g in groups ]  # legendes des boutons
    grnams  = [ g['group_id'] for g in groups ] # noms des checkbox
    no_groups = (len(groups) == 1) and groups[0]['group_name'] is None
    
    # description de l'evaluation    
    H = [ context.evaluation_create_form(evaluation_id=evaluation_id,
                                      REQUEST=REQUEST, readonly=1),
          '<h3>Saisie des notes</h3>'
          ]
    #
    descr = [
        ('evaluation_id', { 'default' : evaluation_id, 'input_type' : 'hidden' }),
        ('note_method', {'input_type' : 'radio', 'default' : 'form', 'allow_null' : False, 
                         'allowed_values' : [ 'xls', 'form' ],
                         'labels' : ['fichier tableur', 'formulaire web'],
                         'title' : 'Méthode de saisie des notes :' }) ]
    if no_groups:
        submitbuttonattributes = []
        descr += [ 
            ('group_ids', { 'default' : [g['group_id'] for g in groups],  'input_type' : 'hidden', 'type':'list' }) ]
    else:
        descr += [ 
            ('group_ids', { 'input_type' : 'checkbox',
                          'title':'Choix du ou des groupes d\'étudiants :',
                          'allowed_values' : grnams, 'labels' : grlabs,
                          'attributes' : ['onchange="gr_change(this);"']
                          }) ]
        if not(REQUEST.form.has_key('groupes') and REQUEST.form['groupes']):
            submitbuttonattributes = [ 'disabled="1"' ]
        else:
            submitbuttonattributes = [] # groupe(s) preselectionnés
        H.append(
          # JS pour desactiver le bouton OK si aucun groupe selectionné
          """<script type="text/javascript">
          function gr_change(e) {
          var boxes = document.getElementsByName("group_ids:list");
          var nbchecked = 0;
          for (var i=0; i < boxes.length; i++) {
              if (boxes[i].checked)
                 nbchecked++;
          }
          if (nbchecked > 0) {
              document.getElementsByName('gr_submit')[0].disabled=false;
          } else {
              document.getElementsByName('gr_submit')[0].disabled=true;
          }
          }
          </script>
          """
          )

    tf = TrivialFormulator( REQUEST.URL0, REQUEST.form, descr,
                            cancelbutton = 'Annuler',
                            submitbuttonattributes=submitbuttonattributes,
                            submitlabel = 'OK', formid='gr' )
    if  tf[0] == 0:
        H.append( """<div class="saisienote_etape1">
        <span class="titredivsaisienote">Etape 1 : choix du groupe et de la méthode</span>
        """)
        return '\n'.join(H) + '\n' + tf[1] + "\n</div>"
    elif tf[0] == -1:
        return REQUEST.RESPONSE.redirect( '%s/Notes/moduleimpl_status?moduleimpl_id=%s'
                                          % (context.ScoURL(),E['moduleimpl_id']) )
    else:
        # form submission
        #   get checked groups
        group_ids = tf[2]['group_ids']
        note_method =  tf[2]['note_method']
        if note_method in ('form', 'xls'):
            # return notes_evaluation_formnotes( REQUEST )
            gs = [('group_ids%3Alist=' + urllib.quote_plus(x)) for x in group_ids ]
            query = 'evaluation_id=%s&note_method=%s&' % (evaluation_id,note_method) + '&'.join(gs)
            REQUEST.RESPONSE.redirect( REQUEST.URL1 + '/notes_evaluation_formnotes?' + query )
        else:
            raise ValueError, "invalid note_method (%s)" % tf[2]['note_method'] 

def evaluation_formnotes(context, REQUEST ):
    """Formulaire soumission notes pour une evaluation.
    """
    isFile = REQUEST.form.get('note_method','html') in ('csv','xls')
    H = []
    if not isFile:
        H += [ context.sco_header(REQUEST),
               "<h2>Saisie des notes</h2>" ]
    
    H += [do_evaluation_formnotes(context, REQUEST)]
    if not isFile:
        H += [ context.sco_footer(REQUEST) ]
    
    return ''.join(H)

def do_evaluation_formnotes(context, REQUEST ):
    """Formulaire soumission notes pour une evaluation.
    parametres: evaluation_id, group_ids (liste des id de groupes)
    """
    authuser = REQUEST.AUTHENTICATED_USER
    authusername = str(authuser)
    try:
        evaluation_id = REQUEST.form['evaluation_id']
    except:        
        raise ScoValueError("Formulaire incomplet ! Vous avez sans doute attendu trop longtemps, veuillez vous reconnecter. Si le problème persiste, contacter l'administrateur. Merci.")
    E = context.do_evaluation_list( {'evaluation_id' : evaluation_id})[0]
    # Check access
    # (admin, respformation, and responsable_id)
    if not context.can_edit_notes( authuser, E['moduleimpl_id'] ):
        return '<h2>Modification des notes impossible pour %s</h2>' % authusername\
               + """<p>(vérifiez que le semestre n'est pas verrouillé et que vous
               avez l'autorisation d'effectuer cette opération)</p>
               <p><a href="moduleimpl_status?moduleimpl_id=%s">Continuer</a></p>
               """ % E['moduleimpl_id']
           #
    cnx = context.GetDBConnexion()
    note_method = REQUEST.form['note_method']
    okbefore = int(REQUEST.form.get('okbefore',0)) # etait ok a l'etape precedente
    changed = int(REQUEST.form.get('changed',0)) # a ete modifie depuis verif 
    #reviewed = int(REQUEST.form.get('reviewed',0)) # a ete presenté comme "pret a soumettre"
    initvalues = {}
    CSV = [] # une liste de liste de chaines: lignes du fichier CSV
    CSV.append( ['Fichier de notes (à enregistrer au format CSV XXX)'])
    # Construit liste des etudiants        
    group_ids = REQUEST.form.get('group_ids', [] )
    groups = sco_groups.listgroups(context, group_ids)
    gr_title_filename = sco_groups.listgroups_filename(groups) 
    gr_title = sco_groups.listgroups_abbrev(groups)

    if None in [ g['group_name'] for g in groups ]: # tous les etudiants
        getallstudents = True
        gr_title = 'tous'
        gr_title_filename = 'tous'
    else:
        getallstudents = False
    etudids = sco_groups.do_evaluation_listeetuds_groups(
        context, evaluation_id, groups, getallstudents=getallstudents, include_dems=True)
    if not etudids:
        return '<p>Aucun groupe sélectionné !</p>'
    # Notes existantes
    NotesDB = context._notes_getall(evaluation_id)
    #
    M = context.do_moduleimpl_list( args={ 'moduleimpl_id' : E['moduleimpl_id'] } )[0]
    Mod = context.do_module_list( args={ 'module_id' : M['module_id'] } )[0]
    sem = context.get_formsemestre(M['formsemestre_id'])
    evalname = '%s-%s' % (Mod['code'],DateDMYtoISO(E['jour']))
    if E['description']:
        evaltitre = '%s du %s' % (E['description'],E['jour'])
    else:
        evaltitre = 'évaluation du %s' % E['jour']
    description = '%s: %s en %s (%s) resp. %s' % (sem['titreannee'], evaltitre, Mod['abbrev'], Mod['code'], M['responsable_id'].capitalize())

    head = """
    <h4>Codes spéciaux:</h4>
    <ul>
    <li>ABS: absent (compte comme un zéro)</li>
    <li>EXC: excusé (note neutralisée)</li>
    <li>SUPR: pour supprimer une note existante</li>
    <li>ATT: note en attente (permet de publier une évaluation avec des notes manquantes)</li>
    </ul>
    <h3>%s</h3>
    """ % description
        
    CSV.append ( [ description ] )
    head += '<p>Etudiants des groupes %s (%d étudiants)</p>'%(gr_title,len(etudids))

    head += '<em>%s</em> du %s (coef. %g, <span class="boldredmsg">notes sur %g</span>)' % (E['description'],E['jour'],E['coefficient'],E['note_max'])
    CSV.append ( [ '', 'date', 'coef.' ] )
    CSV.append ( [ '', '%s' % E['jour'], '%g' % E['coefficient'] ] )
    CSV.append( ['!%s' % evaluation_id ] )
    CSV.append( [ '', 'Nom', 'Prénom', 'Etat', 'Groupe',
                  'Note sur %d'% E['note_max'], 'Remarque' ] )    

    # JS code to monitor changes
    head += """<script type="text/javascript">
    function form_change() {
    var cpar = document.getElementById('changepar');
    // cpar.innerHTML += '*';
    document.getElementById('tf').changed.value="1";
    document.getElementById('tf').tf_submit.value = "Vérifier ces notes";
    return true;
    }        
    </script>
    <p id="changepar"></p>
    """
    
    descr = [
        ('evaluation_id', { 'default' : evaluation_id, 'input_type' : 'hidden' }),
        ('group_ids', { 'default' : group_ids,  'input_type' : 'hidden', 'type':'list' }),
        ('note_method', { 'default' : note_method, 'input_type' : 'hidden'}),
        ('comment', { 'size' : 44, 'title' : 'Commentaire',
                      'return_focus_next' : True, }),
        ('changed', {'default':"0", 'input_type' : 'hidden'}), # changed in JS
        ('s2' , {'input_type' : 'separator', 'title': '<br/>'}),
        ]
    el = [] # list de (label, etudid, note_value, explanation )
    for etudid in etudids:
        # infos identite etudiant (xxx sous-optimal: 1/select par etudiant)
        ident = scolars.etudident_list(cnx, { 'etudid' : etudid })[0] # XXX utiliser ZScolar (parent)
        # infos inscription
        inscr = context.do_formsemestre_inscription_list(
            {'etudid':etudid, 'formsemestre_id' : M['formsemestre_id']})[0]
        nom = ident['nom'].upper()
        label = '%s %s' % (nom, ident['prenom'].lower().capitalize())
        if NotesDB.has_key(etudid):
            val = context._displayNote(NotesDB[etudid]['value'])
            comment = NotesDB[etudid]['comment']
            if comment is None:
                comment = ''
            explanation = '%s (%s) %s' % (NotesDB[etudid]['date'].strftime('%d/%m/%y %Hh%M'),
                                          NotesDB[etudid]['uid'], comment )
        else:
            explanation = ''
            val = ''            
        el.append( (nom, label, etudid, val, explanation, ident, inscr) )
    el.sort() # sort by name
    for (nom, label,etudid, val, explanation, ident, inscr) in el:

        if inscr['etat'] == 'D':
            label = '<span class="etuddem">' + label + '</span>'
            if not val:
                val = 'DEM'
                explanation = 'Démission'
        initvalues['note_'+etudid] = val                
        descr.append( ('note_'+etudid, { 'size' : 4, 'title' : label,
                                         'explanation':explanation,
                                         'return_focus_next' : True,
                                         'attributes' : ['onchange="form_change();"'],
                                         } ) )
        groups = sco_groups.get_etud_groups(context, ident['etudid'], sem)
        grc = sco_groups.listgroups_abbrev(groups)
        CSV.append( [ '%s' % etudid, ident['nom'].upper(), ident['prenom'].lower().capitalize(),
                      inscr['etat'],
                      grc, val, explanation ] )
    if note_method == 'csv':
        CSV = CSV_LINESEP.join( [ CSV_FIELDSEP.join(x) for x in CSV ] )
        filename = 'notes_%s_%s.csv' % (evalname,gr_title_filename)
        return sendCSVFile(REQUEST,CSV, filename )
    elif note_method == 'xls':
        filename = 'notes_%s_%s.xls' % (evalname, gr_title_filename)
        xls = sco_excel.Excel_feuille_saisie( E, description, lines=CSV[6:] )
        return sco_excel.sendExcelFile(REQUEST, xls, filename )

    if REQUEST.form.has_key('changed'): # reset
        del REQUEST.form['changed']
    tf =  TF( REQUEST.URL0, REQUEST.form, descr, initvalues=initvalues,
              cancelbutton='Annuler', submitlabel='Vérifier ces notes' )
    junk = tf.getform()  # check and init
    if tf.canceled():
        return REQUEST.RESPONSE.redirect( '%s/Notes/notes_eval_selectetuds?evaluation_id=%s'
                                          % (context.ScoURL(), evaluation_id) )
    elif (not tf.submitted()) or not tf.result:
        # affiche premier formulaire
        tf.formdescription.append(
            ('okbefore', { 'input_type':'hidden', 'default' : 0 } ) )
        form = tf.getform()            
        return head + form # + '<p>' + CSV # + '<p>' + str(descr)
    else:
        # form submission
        # build list of (etudid, note) and check it
        notes = [ (etudid, tf.result['note_'+etudid]) for etudid in etudids ]
        L, invalids, withoutnotes, absents, tosuppress = _check_notes(notes, E)
        oknow = int(not len(invalids))
        existing_decisions = []
        if oknow:
            nbchanged, nbsuppress, existing_decisions = _notes_add(context, authuser, evaluation_id, L, do_it=False )
            msg_chg = ' (%d modifiées, %d supprimées)' % (nbchanged, nbsuppress)
        else:
            msg_chg = ''
        # Affiche infos et messages d'erreur
        H = ['<ul class="tf-msg">']
        if invalids:
            H.append( '<li class="tf-msg">%d notes invalides !</li>' % len(invalids) )
        if len(L):
             H.append( '<li class="tf-msg-notice">%d notes valides%s</li>' % (len(L), msg_chg) )
        if withoutnotes:
            H.append( '<li class="tf-msg-notice">%d étudiants sans notes !</li>' % len(withoutnotes) )
        if absents:
            H.append( '<li class="tf-msg-notice">%d étudiants absents !</li>' % len(absents) )
        if tosuppress:
            H.append( '<li class="tf-msg-notice">%d notes à supprimer !</li>' % len(tosuppress) )
        if existing_decisions:
            H.append( """<li class="tf-msg">Attention: il y a déjà des <b>décisions de jury</b> enregistrées pour %d étudiants. Après changement des notes, vérifiez la situation !</li>""" % len(existing_decisions))
        H.append( '</ul>' )
        H.append("""<p class="redboldtext">Les notes ne sont pas enregistrées; n'oubliez pas d'appuyer sur le bouton en bas du formulaire.</p>""")
        
        tf.formdescription.append(
            ('okbefore', { 'input_type':'hidden', 'default' : oknow } ) )
        tf.values['okbefore'] = oknow        
        #tf.formdescription.append(
        # ('reviewed', { 'input_type':'hidden', 'default' : oknow } ) )        
        if oknow and okbefore and not changed:
            # ---------------  ok, on rentre ces notes
            nbchanged, nbsuppress, existing_decisions = _notes_add(context, authuser, evaluation_id, L, tf.result['comment'])
            if nbchanged > 0 or nbsuppress > 0:
                Mod['moduleimpl_id'] = M['moduleimpl_id']
                Mod['url'] = "Notes/moduleimpl_status?moduleimpl_id=%(moduleimpl_id)s" % Mod
                sco_news.add(REQUEST, cnx, typ=NEWS_NOTE, object=M['moduleimpl_id'],
                             text='Chargement notes dans <a href="%(url)s">%(titre)s</a>' % Mod,
                             url=Mod['url'])
            # affiche etat evaluation
            etat = context.do_evaluation_etat(evaluation_id)[0]             
            msg = '%d notes / %d inscrits' % (
                etat['nb_notes'], etat['nb_inscrits'])
            if etat['nb_att']:
                msg += ' (%d notes en attente)' % etat['nb_att']
            if etat['evalcomplete'] or etat['evalattente']:
                msg += """</p><p class="greenboldtext">Cette évaluation est prise en compte sur les bulletins et dans les calculs de moyennes"""
                if etat['nb_att']:
                    msg += ' (mais il y a des notes en attente !).'
                else:
                    msg += '.'
            else:
                msg += """</p><p class="fontred">Cette évaluation n'est pas encore prise en compte sur les bulletins et dans les calculs de moyennes car il manque des notes."""
            if existing_decisions:
                existing_msg = """<p class="warning">Important: il y avait déjà des décisions de jury enregistrées, qui sont potentiellement à revoir suite à cette modification de notes.</p>"""
            #
            return """<h3>%s</h3>
            <p>%s notes modifiées (%d supprimées)<br/></p>
            <p>%s</p>
            %s
            <p>
            <a class="stdlink" href="moduleimpl_status?moduleimpl_id=%s">Aller au tableau de bord module</a>
            &nbsp;&nbsp;
            <a class="stdlink" href="notes_eval_selectetuds?evaluation_id=%s">Charger d'autres notes dans cette évaluation</a>
            </p>
            """ % (description,nbchanged,nbsuppress,msg,existing_msg,E['moduleimpl_id'],evaluation_id)
        else:
            if oknow:
                tf.submitlabel = 'Entrer ces notes'
            else:        
                tf.submitlabel = 'Vérifier ces notes'
            return head + '\n'.join(H) + tf.getform()


# ---------------------------------------------------------------------------------

def _XXX_do_evaluation_upload_csv(context, REQUEST): # XXX UNUSED
    """soumission d'un fichier CSV (evaluation_id, notefile)  [XXX UNUSED]
    """
    authuser = REQUEST.AUTHENTICATED_USER
    evaluation_id = REQUEST.form['evaluation_id']
    comment = REQUEST.form['comment']
    E = context.do_evaluation_list( {'evaluation_id' : evaluation_id})[0]
    # Check access
    # (admin, respformation, and responsable_id)
    if not context.can_edit_notes( authuser, E['moduleimpl_id'] ):
        # XXX imaginer un redirect + msg erreur
        raise AccessDenied('Modification des notes impossible pour %s'%authuser)
    #
    data = REQUEST.form['notefile'].read()
    #log('data='+str(data))
    data = data.replace('\r\n','\n').replace('\r','\n')
    lines = data.split('\n')
    # decode fichier
    # 1- skip lines until !evaluation_id
    n = len(lines)
    i = 0
    #log('lines='+str(lines))
    while i < n:
        if not lines[i]:
            raise NoteProcessError('Format de fichier invalide ! (1)')
        if lines[i].strip()[0] == '!':
            break
        i = i + 1
    if i == n:
        raise NoteProcessError('Format de fichier invalide ! (pas de ligne evaluation_id)')
    eval_id = lines[i].split(CSV_FIELDSEP)[0].strip()[1:]
    if eval_id != evaluation_id:
        raise NoteProcessError("Fichier invalide: le code d\'évaluation de correspond pas ! ('%s' != '%s')"%(eval_id,evaluation_id))
    # 2- get notes -> list (etudid, value)
    notes = []
    ni = i+1
    try:
        for line in lines[i+1:]:
            line = line.strip()
            if line:
                fs = line.split(CSV_FIELDSEP)
                etudid = fs[0].strip()
                val = fs[5].strip()
                if etudid:
                    notes.append((etudid,val))
            ni += 1
    except:
        raise NoteProcessError('Format de fichier invalide ! (erreur ligne %d)<br/>"%s"' % (ni, lines[ni]))
    L, invalids, withoutnotes, absents, tosuppress = _check_notes(notes,E)
    if len(invalids):
        return '<p class="boldredmsg">Le fichier contient %d notes invalides</p>' % len(invalids)
    else:
        nb_changed, nb_suppress, existing_decisions = _notes_add(context, authuser, evaluation_id, L, comment )
        return '<p>%d notes changées (%d sans notes, %d absents, %d note supprimées)</p>'%(nb_changed,len(withoutnotes),len(absents),nb_suppress) + '<p>' + str(notes)


def do_evaluation_upload_xls(context, REQUEST):
    """
    Soumission d'un fichier XLS (evaluation_id, notefile)
    """
    authuser = REQUEST.AUTHENTICATED_USER
    evaluation_id = REQUEST.form['evaluation_id']
    comment = REQUEST.form['comment']
    E = context.do_evaluation_list( {'evaluation_id' : evaluation_id})[0]
    # Check access
    # (admin, respformation, and responsable_id)
    if not context.can_edit_notes( authuser, E['moduleimpl_id'] ):
        # XXX imaginer un redirect + msg erreur
        raise AccessDenied('Modification des notes impossible pour %s'%authuser)
    #
    data = REQUEST.form['notefile'].read()
    diag, lines = sco_excel.Excel_to_list( data )
    try:
        if not lines:
            raise FormatError()
        # -- search eval code
        n = len(lines)
        i = 0
        ok = True
        while i < n:
            if not lines[i]:
                diag.append('Erreur: format invalide (ligne vide ?)')
                raise FormatError()
            f0 = lines[i][0].strip()
            if f0 and f0[0] == '!':
                break
            i = i + 1
        if i == n:
            diag.append('Erreur: format invalide ! (pas de ligne evaluation_id)')
            raise FormatError()

        eval_id = lines[i][0].strip()[1:]
        if eval_id != evaluation_id:
            diag.append("Erreur: fichier invalide: le code d\'évaluation de correspond pas ! ('%s' != '%s')"%(eval_id,evaluation_id))
            raise FormatError()
        # --- get notes -> list (etudid, value)
        # ignore toutes les lignes ne commençant pas par !
        notes = []
        ni = i+1
        try:
            for line in lines[i+1:]:
                if line:
                    cell0 = line[0].strip()
                    if cell0 and cell0[0] == '!':
                        etudid = cell0[1:]
                        if len(line) > 4:
                            val = line[4].strip()
                        else:
                            val = '' # ligne courte: cellule vide
                        if etudid:
                            notes.append((etudid,val))
                ni += 1
        except:
            diag.append('Erreur: feuille invalide ! (erreur ligne %d)<br/>"%s"' % (ni, str(lines[ni])))
            raise FormatError()
        # -- check values
        L, invalids, withoutnotes, absents, tosuppress = _check_notes(notes,E)
        if len(invalids):
            diag.append('Erreur: la feuille contient %d notes invalides</p>' % len(invalids))
            if len(invalids) < 25:
                etudsnames = [ context.getEtudInfo(etudid=etudid,filled=True)[0]['nomprenom'] 
                               for etudid in invalids ]
                diag.append('Notes invalides pour: ' + ', '.join(etudsnames) )
            raise FormatError()
        else:
            nb_changed, nb_suppress, existing_decisions = _notes_add(context, authuser, evaluation_id, L, comment )
            # news
            cnx = context.GetDBConnexion()
            E = context.do_evaluation_list( {'evaluation_id' : evaluation_id})[0]
            M = context.do_moduleimpl_list( args={ 'moduleimpl_id':E['moduleimpl_id'] } )[0]
            mod = context.do_module_list( args={ 'module_id':M['module_id'] } )[0]
            mod['moduleimpl_id'] = M['moduleimpl_id']
            mod['url']="Notes/moduleimpl_status?moduleimpl_id=%(moduleimpl_id)s"%mod
            sco_news.add(REQUEST, cnx, typ=NEWS_NOTE, object=M['moduleimpl_id'],
                         text='Chargement notes dans <a href="%(url)s">%(titre)s</a>' % mod,
                         url = mod['url'])

            msg = '<p>%d notes changées (%d sans notes, %d absents, %d note supprimées)</p>'%(nb_changed,len(withoutnotes),len(absents),nb_suppress)
            if existing_decisions:
                msg += '''<p class="warning">Important: il y avait déjà des décisions de jury enregistrées, qui sont potentiellement à revoir suite à cette modification !</p>'''
            # msg += '<p>' + str(notes) # debug
            return 1, msg

    except FormatError:
        if diag:
            msg = '<ul class="tf-msg"><li class="tf_msg">' + '</li><li class="tf_msg">'.join(diag) + '</li></ul>'
        else:
            msg = '<ul class="tf-msg"><li class="tf_msg">Une erreur est survenue</li></ul>'
        return 0, msg + '<p>(pas de notes modifiées)</p>'


def do_evaluation_set_missing(context, evaluation_id, value, REQUEST=None, dialog_confirmed=False):
    """Initialisation des notes manquantes
    """
    authuser = REQUEST.AUTHENTICATED_USER
    evaluation_id = REQUEST.form['evaluation_id']
    E = context.do_evaluation_list( {'evaluation_id' : evaluation_id})[0]
    # Check access
    # (admin, respformation, and responsable_id)
    if not context.can_edit_notes( authuser, E['moduleimpl_id'] ):
        # XXX imaginer un redirect + msg erreur
        raise AccessDenied('Modification des notes impossible pour %s'%authuser)
    #
    NotesDB = context._notes_getall(evaluation_id)        
    etudids = context.do_evaluation_listeetuds_groups(evaluation_id,
                                                   getallstudents=True,
                                                   include_dems=False)
    notes = []
    for etudid in etudids: # pour tous les inscrits
        if not NotesDB.has_key(etudid): # pas de note
            notes.append( (etudid, value) )
    # Check value
    L, invalids, withoutnotes, absents, tosuppress = _check_notes(notes,E)
    diag = ''
    if len(invalids):
        diag = 'Valeur %s invalide' % value
    if diag:
        return context.sco_header(REQUEST)\
               + '<h2>%s</h2><p><a href="notes_eval_selectetuds?evaluation_id=%s">Recommencer</a>'\
               % (diag, evaluation_id) \
               + context.sco_footer(REQUEST)
    # Confirm action
    if not dialog_confirmed:
        return context.confirmDialog(
            """<h2>Mettre toutes les notes manquantes de l'évaluation
            à la valeur %s ? (<em>%d étudiants concernés</em>)</h2>
            <p>(seuls les étudiants pour lesquels aucune note (ni valeur, ni ABS, ni EXC)
            n'a été rentrée seront affectés)</p>
            """ % (value, len(L)),
            dest_url="", REQUEST=REQUEST,
            cancel_url="notes_eval_selectetuds?evaluation_id=%s" % evaluation_id,
            parameters={'evaluation_id' : evaluation_id, 'value' : value})
    # ok
    comment = 'Initialisation notes manquantes'
    nb_changed, nb_suppress, existing_decisions = _notes_add(context, authuser, evaluation_id, L, comment )
    # news
    cnx = context.GetDBConnexion()
    M = context.do_moduleimpl_list( args={ 'moduleimpl_id':E['moduleimpl_id'] } )[0]
    mod = context.do_module_list( args={ 'module_id':M['module_id'] } )[0]
    mod['moduleimpl_id'] = M['moduleimpl_id']
    mod['url']="Notes/moduleimpl_status?moduleimpl_id=%(moduleimpl_id)s"%mod
    sco_news.add(REQUEST, cnx, typ=NEWS_NOTE, object=M['moduleimpl_id'],
                 text='Initialisation notes dans <a href="%(url)s">%(titre)s</a>' % mod,
                 url = mod['url'])
    return context.sco_header(REQUEST)\
               + """<h2>%d notes changées</h2>
               <p><a href="moduleimpl_status?moduleimpl_id=%s">
               Revenir au tableau de bord du module</a>
               </p>
               """ % (nb_changed, M['moduleimpl_id']) \
               + context.sco_footer(REQUEST)


def evaluation_suppress_alln(context, evaluation_id, REQUEST, dialog_confirmed=False):
    "suppress all notes in this eval"
    authuser = REQUEST.AUTHENTICATED_USER
    E = context.do_evaluation_list( {'evaluation_id' : evaluation_id})[0]
    if not context.can_edit_notes( authuser, E['moduleimpl_id'], allow_ens=False ):
        # NB: les chargés de TD n'ont pas le droit.
        # XXX imaginer un redirect + msg erreur
        raise AccessDenied('Modification des notes impossible pour %s'%authuser)

    # recupere les etuds ayant une note
    NotesDB = context._notes_getall(evaluation_id)
    notes = [ (etudid, NOTES_SUPPRESS) for etudid in NotesDB.keys() ]

    if not dialog_confirmed:
        nb_changed, nb_suppress, existing_decisions = _notes_add(
            context, authuser, evaluation_id, notes, do_it=False)
        msg = '<p>Confirmer la suppression des %d notes ?</p>' % nb_suppress
        if existing_decisions:
            msg += '''<p class="warning">Important: il y a déjà des décisions de jury enregistrées, qui seront potentiellement à revoir suite à cette modification !</p>'''
        return context.confirmDialog(
            msg, dest_url="", REQUEST=REQUEST, OK='Supprimer les notes',
            cancel_url="moduleimpl_status?moduleimpl_id=%s"%E['moduleimpl_id'],
            parameters={'evaluation_id':evaluation_id})
    
    # modif
    nb_changed, nb_suppress, existing_decisions = _notes_add(
        context, authuser, evaluation_id, notes, comment='suppress all' )
    assert nb_changed == nb_suppress       
    H = [ '<p>%s notes supprimées</p>' % nb_suppress ]
    if existing_decisions:
        H.append( '''<p class="warning">Important: il y avait déjà des décisions de jury enregistrées, qui sont potentiellement à revoir suite à cette modification !</p>''')
    H += [ '<p><a class="stdlink" href="moduleimpl_status?moduleimpl_id=%s">continuer</a>'
           % E['moduleimpl_id'] ]
    # news
    M = context.do_moduleimpl_list( args={ 'moduleimpl_id':E['moduleimpl_id'] } )[0]
    mod = context.do_module_list( args={ 'module_id':M['module_id'] } )[0]
    mod['moduleimpl_id'] = M['moduleimpl_id']
    cnx = context.GetDBConnexion()
    mod['url'] = "Notes/moduleimpl_status?moduleimpl_id=%(moduleimpl_id)s"%mod
    sco_news.add(REQUEST, cnx, typ=NEWS_NOTE, object=M['moduleimpl_id'],
                 text='Suppression des notes d\'une évaluation dans <a href="%(url)s">%(titre)s</a>' % mod,
                 url= mod['url'])

    return context.sco_header(REQUEST) + '\n'.join(H) + context.sco_footer(REQUEST)


def _check_notes( notes, evaluation ):
    """notes is a list of tuples (etudid, value)
    returns list of valid notes (etudid, float value)
    and 4 lists of etudid: invalids, withoutnotes, absents, tosuppress, existingjury
    """
    note_max = evaluation['note_max']
    L = [] # liste (etudid, note) des notes ok (ou absent) 
    invalids = [] # etudid avec notes invalides
    withoutnotes = [] # etudid sans notes (champs vides)
    absents = [] # etudid absents
    tosuppress = [] # etudids avec ancienne note à supprimer
    existingjury = [] # etudids avec decision de jury (sem et/ou UE) a revoir eventuellement
    for (etudid, note) in notes:
        note = str(note)        
        if note:
            invalid = False
            note = note.strip().upper().replace(',','.')
            if note[:3] == 'ABS':
                note = None
                absents.append(etudid)
            elif note[:3] == 'NEU' or note[:3] == 'EXC':
                note = NOTES_NEUTRALISE
            elif  note[:3] == 'ATT':
                note = NOTES_ATTENTE
            elif note[:3] == 'SUP':
                note = NOTES_SUPPRESS
                tosuppress.append(etudid)
            elif note[:3] == 'DEM':
                continue # skip !
            else:
                try:
                    note = float(note)
                    if (note < NOTES_MIN) or (note > note_max):
                        raise ValueError
                except:
                    invalids.append(etudid)
                    invalid = True
            if not invalid:
                L.append((etudid,note))
        else:
            withoutnotes.append(etudid)
    
    return L, invalids, withoutnotes, absents, tosuppress


def _notes_add(context, uid, evaluation_id, notes, comment=None, do_it=True ):
    """
    Insert or update notes
    notes is a list of tuples (etudid,value)
    If do_it is False, simulate the process and returns the number of values that
    WOULD be changed or suppressed.
    Nota:
    - va verifier si tous les etudiants sont inscrits
    au moduleimpl correspond a cet eval_id.
    - si la note existe deja avec valeur distincte, ajoute une entree au log (notes_notes_log)
    Return number of changed notes
    """
    uid = str(uid)
    now = apply(DB.Timestamp, time.localtime()[:6]) #datetime.datetime.now().isoformat()
    # Verifie inscription et valeur note
    inscrits = {}.fromkeys(sco_groups.do_evaluation_listeetuds_groups(
            context, evaluation_id, getallstudents=True, include_dems=True))
    for (etudid,value) in notes:
        if not inscrits.has_key(etudid):
            raise NoteProcessError("etudiant %s non inscrit a l'evaluation %s" %(etudid,evaluation_id))
        if not ((value is None) or (type(value) == type(1.0))):
            raise NoteProcessError( "etudiant %s: valeur de note invalide (%s)" %(etudid,value))
    # Recherche notes existantes
    NotesDB = context._notes_getall(evaluation_id)
    # Met a jour la base
    cnx = context.GetDBConnexion()
    cursor = cnx.cursor()
    nb_changed = 0
    nb_suppress = 0
    E = context.do_evaluation_list( {'evaluation_id' : evaluation_id})[0]
    M = context.do_moduleimpl_list(args={ 'moduleimpl_id' : E['moduleimpl_id']})[0]
    existing_decisions = [] # etudids pour lesquels il y a une decision de jury et que la note change
    try:
        for (etudid,value) in notes:
            changed = False
            if not NotesDB.has_key(etudid):
                # nouvelle note
                if value != NOTES_SUPPRESS:
                    if do_it:
                        aa = {'etudid':etudid, 'evaluation_id':evaluation_id,
                              'value': value, 'comment' : comment, 'uid' : uid, 
                              'date' : now}
                        quote_dict(aa)
                        cursor.execute('insert into notes_notes (etudid,evaluation_id,value,comment,date,uid) values (%(etudid)s,%(evaluation_id)s,%(value)f,%(comment)s,%(date)s,%(uid)s)', aa )
                    changed = True
            else:
                # il y a deja une note
                oldval = NotesDB[etudid]['value']
                if type(value) != type(oldval):
                    changed = True
                elif type(value) == type(1.0) and (abs(value-oldval) > NOTES_PRECISION):
                    changed = True
                elif value != oldval:
                    changed = True
                if changed:
                    # recopie l'ancienne note dans notes_notes_log, puis update
                    if do_it:
                        cursor.execute('insert into notes_notes_log (etudid,evaluation_id,value,comment,date,uid) select etudid,evaluation_id,value,comment,date,uid from notes_notes where etudid=%(etudid)s and evaluation_id=%(evaluation_id)s',
                                       { 'etudid':etudid, 'evaluation_id':evaluation_id } )
                        aa = { 'etudid':etudid, 'evaluation_id':evaluation_id,
                               'value':value,
                               'date': now,
                               'comment' : comment, 'uid' : uid}
                        quote_dict(aa)
                    if value != NOTES_SUPPRESS:
                        if do_it:
                            cursor.execute('update notes_notes set value=%(value)s, comment=%(comment)s, date=%(date)s, uid=%(uid)s where etudid=%(etudid)s and evaluation_id=%(evaluation_id)s', aa )
                    else: # suppression ancienne note
                        if do_it:
                            log('_notes_add, suppress, evaluation_id=%s, etudid=%s, oldval=%s'
                            % (evaluation_id,etudid,oldval) )
                            cursor.execute('delete from notes_notes where etudid=%(etudid)s and evaluation_id=%(evaluation_id)s', aa )
                            # garde trace de la suppression dans l'historique:
                            aa['value'] = NOTES_SUPPRESS
                            cursor.execute('insert into notes_notes_log (etudid,evaluation_id,value,comment,date,uid) values (%(etudid)s, %(evaluation_id)s, %(value)s, %(comment)s, %(date)s, %(uid)s)', aa)
                        nb_suppress += 1
            if changed:
                nb_changed += 1
                if has_existing_decision(context, M, E, etudid):
                    existing_decisions.append(etudid)
    except:
        log('*** exception in _notes_add')
        if do_it:
            # inval cache
            context._inval_cache(formsemestre_id=M['formsemestre_id'])
            cnx.rollback() # abort
        raise # re-raise exception
    if do_it:
        cnx.commit()
        context._inval_cache(formsemestre_id=M['formsemestre_id']) 
    return nb_changed, nb_suppress, existing_decisions


def notes_eval_selectetuds(context, evaluation_id, REQUEST=None):
    """Dialogue saisie notes: choix methode et groupes
    """
    H = [ context.sco_header(REQUEST, page_title='Saisie des notes')]
    
    formid = 'notesfile'
    if not REQUEST.form.get('%s-submitted'%formid,False):
        # not submitted, choix groupe
        r = do_evaluation_selectetuds(context, REQUEST)
        if r:
            H.append(r)            

    theeval = context.do_evaluation_list( {'evaluation_id' : evaluation_id})[0]
    H.append('''<div class="saisienote_etape2">
    <span class="titredivsaisienote">Etape 2 : chargement d'un fichier de notes</span>''' #'
             )

    nf = TrivialFormulator( REQUEST.URL0, REQUEST.form, ( 
        ('evaluation_id', { 'default' : evaluation_id, 'input_type' : 'hidden' }),
        ('notefile',  { 'input_type' : 'file', 'title' : 'Fichier de note (.xls)', 'size' : 44 }),
        ('comment', { 'size' : 44, 'title' : 'Commentaire',
                      'explanation':'(note: la colonne remarque du fichier excel est ignorée)' }),
        ),
                            formid=formid,
                            submitlabel = 'Télécharger')
    if nf[0] == 0:
        H.append('''<p>Le fichier doit être un fichier tableur obtenu via
        le formulaire ci-dessus, puis complété et enregistré au format Excel.
        </p>''')
        H.append(nf[1])
    elif nf[0] == -1:
        H.append('<p>Annulation</p>')
    elif nf[0] == 1:
        updiag = do_evaluation_upload_xls(context, REQUEST)
        if updiag[0]:
            H.append(updiag[1])
            H.append('''<p>Notes chargées.&nbsp;&nbsp;&nbsp;
            <a class="stdlink" href="moduleimpl_status?moduleimpl_id=%(moduleimpl_id)s">
            Revenir au tableau de bord du module</a>
            &nbsp;&nbsp;&nbsp;
            <a class="stdlink" href="notes_eval_selectetuds?evaluation_id=%(evaluation_id)s">Charger d'autres notes dans cette évaluation</a>
            </p>''' % theeval)
        else:
            H.append('''<p class="redboldtext">Notes non chargées !</p>'''            
                     + updiag[1] )
            H.append('''
            <p><a class="stdlink" href="notes_eval_selectetuds?evaluation_id=%(evaluation_id)s">
            Reprendre</a>
            </p>''' % theeval)
    #
    H.append('''</div><h3>Autres opérations</h3><ul>''')
    if context.can_edit_notes(REQUEST.AUTHENTICATED_USER,theeval['moduleimpl_id'],allow_ens=False):
        H.append('''
        <li>
        <form action="do_evaluation_set_missing" method="GET">
        Mettre toutes les notes manquantes à <input type="text" size="5" name="value"/>
        <input type="submit" value="OK"/> 
        <input type="hidden" name="evaluation_id" value="%s"/> 
        <em>ABS indique "absent" (zéro), EXC "excusé" (neutralisées), ATT "attente"</em>
        </form>
        </li>        
        <li><a class="stdlink" href="evaluation_suppress_alln?evaluation_id=%s">Effacer toutes les notes de cette évaluation</a> (ceci permet ensuite de supprimer l'évaluation si besoin)
        </li>''' % (evaluation_id, evaluation_id)) #'
    H.append('''<li><a class="stdlink" href="moduleimpl_status?moduleimpl_id=%(moduleimpl_id)s">Revenir au module</a>
    </li>
    </ul>''' % theeval )
    
    H.append("""<h3>Explications</h3>
<ol>
<li>Cadre bleu (étape 1): 
<ol><li>choisir la méthode de saisie (formulaire web ou feuille Excel);
    <li>choisir le ou les groupes;</li>
</ol>
</li>
<li>Cadre vert (étape 2): à n'utiliser que si l'on est passé par une feuille Excel. Indiquer le fichier Excel <em>téléchargé à l'étape 1</em> et dans lequel on a saisi des notes. Remarques:
<ul>
<li>le fichier Excel ne doit pas forcément être complet: on peut ne saisir que quelques notes et répéter l'opération (en téléchargeant un nouveau fichier) plus tard;</li>
<li>seules les valeurs des notes modifiées sont prises en compte;</li>
<li>seules les notes sont extraites du fichier Excel;</li>
<li>on peut optionnellement ajouter un commentaire (type "copies corrigées par Dupont", ou "Modif. suite à contestation") dans la case "Commentaire".
</li>
<li>le fichier Excel <em>doit impérativement être celui chargé à l'étape 1 pour cette évaluation</em>. Il n'est pas possible d'utiliser une liste d'appel ou autre document Excel téléchargé d'une autre page.</li>
</ul>
</li>
</ol>
""")
    H.append( context.sco_footer(REQUEST) )
    return '\n'.join(H)

def has_existing_decision(context, M, E, etudid):
    """Verifie s'il y a une validation pour cette etudiant dans ce semestre ou UE
    Si oui, return True
    """
    formsemestre_id = M['formsemestre_id']
    nt = context._getNotesCache().get_NotesTable(context, formsemestre_id)
    if nt.get_etud_decision_sem(etudid):
        return True
    dec_ues = nt.get_etud_decision_ues(etudid)
    if dec_ues:
        mod = context.do_module_list({ 'module_id' : M['module_id']})[0]
        ue_id = mod['ue_id']
        if ue_id in dec_ues:
            return True # decision pour l'UE a laquelle appartient cette evaluation
    
    return False # pas de decision de jury affectee par cette note
