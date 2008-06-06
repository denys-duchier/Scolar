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

from notesdb import *
from sco_utils import *
from notes_log import log
from TrivialFormulator import TrivialFormulator, TF
from notes_table import *
import htmlutils
import sco_excel
import scolars
import sco_news
from sco_news import NEWS_INSCR, NEWS_NOTE, NEWS_FORM, NEWS_SEM, NEWS_MISC

def do_evaluation_selectetuds(self, REQUEST ):
    """
    Choisi les etudiants pour saisie notes
    """
    evaluation_id = REQUEST.form['evaluation_id']
    E = self.do_evaluation_list( {'evaluation_id' : evaluation_id})[0]
    M = self.do_moduleimpl_list( args={ 'moduleimpl_id' : E['moduleimpl_id'] } )[0]
    formsemestre_id = M['formsemestre_id']
    # groupes
    gr_td, gr_tp, gr_anglais = self.do_evaluation_listegroupes(evaluation_id)
    grnams  = ['tous'] + [('td'+x) for x in gr_td ] # noms des checkbox
    grnams += [('tp'+x) for x in gr_tp ]
    grnams += [('ta'+x) for x in gr_anglais ]
    grlabs  = ['tous'] + gr_td + gr_tp + gr_anglais # legendes des boutons
    if len(gr_td) <= 1 and len(gr_tp) <= 1 and len(gr_anglais) <= 1:
        no_group = True
    else:
        no_group = False
    # description de l'evaluation    
    H = [ self.evaluation_create_form(evaluation_id=evaluation_id,
                                      REQUEST=REQUEST, readonly=1),
          '<h3>Saisie des notes</h3>'
          ]
    #
    descr = [
        ('evaluation_id', { 'default' : evaluation_id, 'input_type' : 'hidden' }),
        ('note_method', {'input_type' : 'radio', 'default' : 'form', 'allow_null' : False, 
                         'allowed_values' : [ 'xls', 'form' ],
                         'labels' : ['fichier tableur', 'formulaire web'],
                         'title' : 'M�thode de saisie des notes :' }) ]
    if no_group:
        submitbuttonattributes = []
    else:
        descr += [ 
            ('groupes', { 'input_type' : 'checkbox',
                          'title':'Choix du ou des groupes d\'�tudiants :',
                          'allowed_values' : grnams, 'labels' : grlabs,
                          'attributes' : ['onchange="gr_change(this);"']
                          }) ]
        if not(REQUEST.form.has_key('groupes') and REQUEST.form['groupes']):
            submitbuttonattributes = [ 'disabled="1"' ]
        else:
            submitbuttonattributes = [] # groupe(s) preselectionn�s
        H.append(
          # JS pour desactiver le bouton OK si aucun groupe selectionn�
          """<script type="text/javascript">
          function gr_change(e) {
          var boxes = document.getElementsByName("groupes:list");
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
        <span class="titredivsaisienote">Etape 1 : choix du groupe et de la m�thode</span>
        """)
        return '\n'.join(H) + '\n' + tf[1] + "\n</div>"
    elif tf[0] == -1:
        return REQUEST.RESPONSE.redirect( '%s/Notes/moduleimpl_status?moduleimpl_id=%s'
                                          % (self.ScoURL(),E['moduleimpl_id']) )
    else:
        # form submission
        #   get checked groups
        if no_group:
            g = ['tous']
        else:
            g = tf[2]['groupes']
        note_method =  tf[2]['note_method']
        if note_method in ('form', 'xls'):
            # return notes_evaluation_formnotes( REQUEST )
            gs = [('groupes%3Alist=' + urllib.quote_plus(x)) for x in g ]
            query = 'evaluation_id=%s&note_method=%s&' % (evaluation_id,note_method) + '&'.join(gs)
            REQUEST.RESPONSE.redirect( REQUEST.URL1 + '/notes_evaluation_formnotes?' + query )
        else:
            raise ValueError, "invalid note_method (%s)" % tf[2]['note_method'] 


def do_evaluation_formnotes(self, REQUEST ):
    """Formulaire soumission notes pour une evaluation.
    parametres: evaluation_id, groupes (liste, avec prefixes tp, td, ta)
    """
    authuser = REQUEST.AUTHENTICATED_USER
    authusername = str(authuser)
    try:
        evaluation_id = REQUEST.form['evaluation_id']
    except:        
        raise ScoValueError("Formulaire incomplet ! Vous avez sans doute attendu trop longtemps, veuillez vous reconnecter. Si le probl�me persiste, contacter l'administrateur. Merci.")
    E = self.do_evaluation_list( {'evaluation_id' : evaluation_id})[0]
    # Check access
    # (admin, respformation, and responsable_id)
    if not self.can_edit_notes( authuser, E['moduleimpl_id'] ):
        return self.sco_header(REQUEST)\
               + '<h2>Modification des notes impossible pour %s</h2>' % authusername\
               + """<p>(v�rifiez que le semestre n'est pas verrouill� et que vous
               avez l'autorisation d'effectuer cette op�ration)</p>
               <p><a href="moduleimpl_status?moduleimpl_id=%s">Continuer</a></p>
               """ % E['moduleimpl_id']  + self.sco_footer(REQUEST)                
           #
    cnx = self.GetDBConnexion()
    note_method = REQUEST.form['note_method']
    okbefore = int(REQUEST.form.get('okbefore',0)) # etait ok a l'etape precedente
    changed = int(REQUEST.form.get('changed',0)) # a ete modifie depuis verif 
    #reviewed = int(REQUEST.form.get('reviewed',0)) # a ete present� comme "pret a soumettre"
    initvalues = {}
    CSV = [] # une liste de liste de chaines: lignes du fichier CSV
    CSV.append( ['Fichier de notes (� enregistrer au format CSV XXX)'])
    # Construit liste des etudiants        
    glist = REQUEST.form.get('groupes', [] )
    gr_td = [ x[2:] for x in glist if x[:2] == 'td' ]
    gr_tp = [ x[2:] for x in glist if x[:2] == 'tp' ]
    gr_anglais = [ x[2:] for x in glist if x[:2] == 'ta' ]
    gr_title = ' '.join(gr_td+gr_tp+gr_anglais)
    gr_title_filename = 'gr' + '+'.join(gr_td+gr_tp+gr_anglais)
    if 'tous' in glist:
        getallstudents = True
        gr_title = 'tous'
        gr_title_filename = 'tous'
    else:
        getallstudents = False
    etudids = self.do_evaluation_listeetuds_groups(evaluation_id,
                                                   gr_td,gr_tp,gr_anglais,
                                                   getallstudents=getallstudents,
                                                   include_dems=True)
    if not etudids:
        return '<p>Aucun groupe s�lectionn� !</p>'
    # Notes existantes
    NotesDB = self._notes_getall(evaluation_id)
    #
    M = self.do_moduleimpl_list( args={ 'moduleimpl_id' : E['moduleimpl_id'] } )[0]
    Mod = self.do_module_list( args={ 'module_id' : M['module_id'] } )[0]
    sem = self.get_formsemestre(M['formsemestre_id'])
    evalname = '%s-%s' % (Mod['code'],DateDMYtoISO(E['jour']))
    if E['description']:
        evaltitre = '%s du %s' % (E['description'],E['jour'])
    else:
        evaltitre = '�valuation du %s' % E['jour']
    description = '%s: %s en %s (%s) resp. %s' % (sem['titreannee'], evaltitre, Mod['abbrev'], Mod['code'], M['responsable_id'].capitalize())

    head = """
    <h4>Codes sp�ciaux:</h4>
    <ul>
    <li>ABS: absent (compte comme un z�ro)</li>
    <li>EXC: excus� (note neutralis�e)</li>
    <li>SUPR: pour supprimer une note existante</li>
    <li>ATT: note en attente (permet de publier une �valuation avec des notes manquantes)</li>
    </ul>
    <h3>%s</h3>
    """ % description
        
    CSV.append ( [ description ] )
    head += '<p>Etudiants des groupes %s (%d �tudiants)</p>'%(gr_title,len(etudids))

    head += '<em>%s</em> du %s (coef. %g, <span class="boldredmsg">notes sur %g</span>)' % (E['description'],E['jour'],E['coefficient'],E['note_max'])
    CSV.append ( [ '', 'date', 'coef.' ] )
    CSV.append ( [ '', '%s' % E['jour'], '%g' % E['coefficient'] ] )
    CSV.append( ['!%s' % evaluation_id ] )
    CSV.append( [ '', 'Nom', 'Pr�nom', 'Etat', 'Groupe',
                  'Note sur %d'% E['note_max'], 'Remarque' ] )    

    # JS code to monitor changes
    head += """<script type="text/javascript">
    function form_change() {
    var cpar = document.getElementById('changepar');
    // cpar.innerHTML += '*';
    document.getElementById('tf').changed.value="1";
    document.getElementById('tf').tf_submit.value = "V�rifier ces notes";
    return true;
    }        
    </script>
    <p id="changepar"></p>
    """
    
    descr = [
        ('evaluation_id', { 'default' : evaluation_id, 'input_type' : 'hidden' }),
        ('groupes', { 'default' : glist,  'input_type' : 'hidden', 'type':'list' }),
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
        inscr = self.do_formsemestre_inscription_list(
            {'etudid':etudid, 'formsemestre_id' : M['formsemestre_id']})[0]
        label = '%s %s' % (ident['nom'].upper(), ident['prenom'].lower().capitalize())
        if NotesDB.has_key(etudid):
            val = self._displayNote(NotesDB[etudid]['value'])
            comment = NotesDB[etudid]['comment']
            if comment is None:
                comment = ''
            explanation = '%s (%s) %s' % (NotesDB[etudid]['date'].strftime('%d/%m/%y %Hh%M'),
                                          NotesDB[etudid]['uid'], comment )
        else:
            explanation = ''
            val = ''            
        el.append( (label, etudid, val, explanation, ident, inscr) )
    el.sort() # sort by name
    for (label,etudid, val, explanation, ident, inscr) in el:

        if inscr['etat'] == 'D':
            label = '<span class="etuddem">' + label + '</span>'
            if not val:
                val = 'DEM'
                explanation = 'D�mission'
        initvalues['note_'+etudid] = val                
        descr.append( ('note_'+etudid, { 'size' : 4, 'title' : label,
                                         'explanation':explanation,
                                         'return_focus_next' : True,
                                         'attributes' : ['onchange="form_change();"'],
                                         } ) )
        grnam = inscr['groupetd']
        if inscr['groupetp'] or inscr['groupeanglais']:
            grnam += '/' + inscr['groupetp']
            if inscr['groupeanglais']:
                grnam += '/' + inscr['groupeanglais']
        CSV.append( [ '%s' % etudid, ident['nom'].upper(), ident['prenom'].lower().capitalize(),
                      inscr['etat'],
                      grnam, val, explanation ] )
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
              cancelbutton='Annuler', submitlabel='V�rifier ces notes' )
    junk = tf.getform()  # check and init
    if tf.canceled():
        return REQUEST.RESPONSE.redirect( '%s/Notes/notes_eval_selectetuds?evaluation_id=%s'
                                          % (self.ScoURL(), evaluation_id) )
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
        if oknow:
            nbchanged, nbsuppress = self._notes_add(authuser, evaluation_id, L, do_it=False )
            msg_chg = ' (%d modifi�es, %d supprim�es)' % (nbchanged, nbsuppress)
        else:
            msg_chg = ''
        # Affiche infos et messages d'erreur
        H = ['<ul class="tf-msg">']
        if invalids:
            H.append( '<li class="tf-msg">%d notes invalides !</li>' % len(invalids) )
        if len(L):
             H.append( '<li class="tf-msg-notice">%d notes valides%s</li>' % (len(L), msg_chg) )
        if withoutnotes:
            H.append( '<li class="tf-msg-notice">%d �tudiants sans notes !</li>' % len(withoutnotes) )
        if absents:
            H.append( '<li class="tf-msg-notice">%d �tudiants absents !</li>' % len(absents) )
        if tosuppress:
            H.append( '<li class="tf-msg-notice">%d notes � supprimer !</li>' % len(tosuppress) )
        H.append("""<p class="redboldtext">Les notes ne sont pas enregistr�es; n'oubliez pas d'appuyer sur le bouton en bas du formulaire.</p>""")

        H.append( '</ul>' )


        tf.formdescription.append(
            ('okbefore', { 'input_type':'hidden', 'default' : oknow } ) )
        tf.values['okbefore'] = oknow        
        #tf.formdescription.append(
        # ('reviewed', { 'input_type':'hidden', 'default' : oknow } ) )        
        if oknow and okbefore and not changed:
            # ---------------  ok, on rentre ces notes
            nbchanged, nbsuppress = self._notes_add(authuser, evaluation_id, L, tf.result['comment'])
            if nbchanged > 0 or nbsuppress > 0:
                Mod['moduleimpl_id'] = M['moduleimpl_id']
                Mod['url'] = "Notes/moduleimpl_status?moduleimpl_id=%(moduleimpl_id)s" % Mod
                sco_news.add(REQUEST, cnx, typ=NEWS_NOTE, object=M['moduleimpl_id'],
                             text='Chargement notes dans <a href="%(url)s">%(titre)s</a>' % Mod,
                             url=Mod['url'])
            # affiche etat evaluation
            etat = self.do_evaluation_etat(evaluation_id)[0]             
            msg = '%d notes / %d inscrits' % (
                etat['nb_notes'], etat['nb_inscrits'])
            if etat['nb_att']:
                msg += ' (%d notes en attente)' % etat['nb_att']
            if etat['evalcomplete'] or etat['evalattente']:
                msg += """</p><p class="greenboldtext">Cette �valuation est prise en compte sur les bulletins et dans les calculs de moyennes"""
                if etat['nb_att']:
                    msg += ' (mais il y a des notes en attente !).'
                else:
                    msg += '.'
            else:
                msg += """</p><p class="fontred">Cette �valuation n'est pas encore prise en compte sur les bulletins et dans les calculs de moyennes car il manque des notes."""
            #
            return """<h3>%s</h3>
            <p>%s notes modifi�es (%d supprim�es)<br/></p>
            <p>%s</p>
            <p>
            <a class="stdlink" href="moduleimpl_status?moduleimpl_id=%s">Aller au tableau de bord module</a>
            &nbsp;&nbsp;
            <a class="stdlink" href="notes_eval_selectetuds?evaluation_id=%s">Charger d'autres notes dans cette �valuation</a>
            </p>
            """ % (description,nbchanged,nbsuppress,msg,E['moduleimpl_id'],evaluation_id)
        else:
            if oknow:
                tf.submitlabel = 'Entrer ces notes'
            else:        
                tf.submitlabel = 'V�rifier ces notes'
            return head + '\n'.join(H) + tf.getform()


# ---------------------------------------------------------------------------------

def _XXX_do_evaluation_upload_csv(self, REQUEST): # XXX UNUSED
    """soumission d'un fichier CSV (evaluation_id, notefile)  [XXX UNUSED]
    """
    authuser = REQUEST.AUTHENTICATED_USER
    evaluation_id = REQUEST.form['evaluation_id']
    comment = REQUEST.form['comment']
    E = self.do_evaluation_list( {'evaluation_id' : evaluation_id})[0]
    # Check access
    # (admin, respformation, and responsable_id)
    if not self.can_edit_notes( authuser, E['moduleimpl_id'] ):
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
        raise NoteProcessError("Fichier invalide: le code d\'�valuation de correspond pas ! ('%s' != '%s')"%(eval_id,evaluation_id))
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
        nb_changed, nb_suppress = self._notes_add(authuser, evaluation_id, L, comment )
        return '<p>%d notes chang�es (%d sans notes, %d absents, %d note supprim�es)</p>'%(nb_changed,len(withoutnotes),len(absents),nb_suppress) + '<p>' + str(notes)


def do_evaluation_upload_xls(self, REQUEST):
    """
    Soumission d'un fichier XLS (evaluation_id, notefile)
    """
    authuser = REQUEST.AUTHENTICATED_USER
    evaluation_id = REQUEST.form['evaluation_id']
    comment = REQUEST.form['comment']
    E = self.do_evaluation_list( {'evaluation_id' : evaluation_id})[0]
    # Check access
    # (admin, respformation, and responsable_id)
    if not self.can_edit_notes( authuser, E['moduleimpl_id'] ):
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
            diag.append("Erreur: fichier invalide: le code d\'�valuation de correspond pas ! ('%s' != '%s')"%(eval_id,evaluation_id))
            raise FormatError()
        # --- get notes -> list (etudid, value)
        # ignore toutes les lignes ne commen�ant pas par !
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
                diag.append('Notes invalides pour les id: ' + str(invalids) )
            raise FormatError()
        else:
            nb_changed, nb_suppress = self._notes_add(authuser, evaluation_id, L, comment )
            # news
            cnx = self.GetDBConnexion()
            E = self.do_evaluation_list( {'evaluation_id' : evaluation_id})[0]
            M = self.do_moduleimpl_list( args={ 'moduleimpl_id':E['moduleimpl_id'] } )[0]
            mod = self.do_module_list( args={ 'module_id':M['module_id'] } )[0]
            mod['moduleimpl_id'] = M['moduleimpl_id']
            mod['url']="Notes/moduleimpl_status?moduleimpl_id=%(moduleimpl_id)s"%mod
            sco_news.add(REQUEST, cnx, typ=NEWS_NOTE, object=M['moduleimpl_id'],
                         text='Chargement notes dans <a href="%(url)s">%(titre)s</a>' % mod,
                         url = mod['url'])

            return 1, '<p>%d notes chang�es (%d sans notes, %d absents, %d note supprim�es)</p>'%(nb_changed,len(withoutnotes),len(absents),nb_suppress) + '<p>' + str(notes)

    except FormatError:
        if diag:
            msg = '<ul class="tf-msg"><li class="tf_msg">' + '</li><li class="tf_msg">'.join(diag) + '</li></ul>'
        else:
            msg = '<ul class="tf-msg"><li class="tf_msg">Une erreur est survenue</li></ul>'
        return 0, msg + '<p>(pas de notes modifi�es)</p>'


def do_evaluation_set_missing(self, evaluation_id, value, REQUEST=None, dialog_confirmed=False):
    """Initialisation des notes manquantes
    """
    authuser = REQUEST.AUTHENTICATED_USER
    evaluation_id = REQUEST.form['evaluation_id']
    E = self.do_evaluation_list( {'evaluation_id' : evaluation_id})[0]
    # Check access
    # (admin, respformation, and responsable_id)
    if not self.can_edit_notes( authuser, E['moduleimpl_id'] ):
        # XXX imaginer un redirect + msg erreur
        raise AccessDenied('Modification des notes impossible pour %s'%authuser)
    #
    NotesDB = self._notes_getall(evaluation_id)        
    etudids = self.do_evaluation_listeetuds_groups(evaluation_id,
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
        return self.sco_header(REQUEST)\
               + '<h2>%s</h2><p><a href="notes_eval_selectetuds?evaluation_id=%s">Recommencer</a>'\
               % (diag, evaluation_id) \
               + self.sco_footer(REQUEST)
    # Confirm action
    if not dialog_confirmed:
        return self.confirmDialog(
            """<h2>Mettre toutes les notes manquantes de l'�valuation
            � la valeur %s ? (<em>%d �tudiants concern�s</em>)</h2>
            <p>(seuls les �tudiants pour lesquels aucune note (ni valeur, ni ABS, ni EXC)
            n'a �t� rentr�e seront affect�s)</p>
            """ % (value, len(L)),
            dest_url="", REQUEST=REQUEST,
            cancel_url="notes_eval_selectetuds?evaluation_id=%s" % evaluation_id,
            parameters={'evaluation_id' : evaluation_id, 'value' : value})
    # ok
    comment = 'Initialisation notes manquantes'
    nb_changed, nb_suppress = self._notes_add(authuser, evaluation_id, L, comment )
    # news
    cnx = self.GetDBConnexion()
    M = self.do_moduleimpl_list( args={ 'moduleimpl_id':E['moduleimpl_id'] } )[0]
    mod = self.do_module_list( args={ 'module_id':M['module_id'] } )[0]
    mod['moduleimpl_id'] = M['moduleimpl_id']
    mod['url']="Notes/moduleimpl_status?moduleimpl_id=%(moduleimpl_id)s"%mod
    sco_news.add(REQUEST, cnx, typ=NEWS_NOTE, object=M['moduleimpl_id'],
                 text='Initialisation notes dans <a href="%(url)s">%(titre)s</a>' % mod,
                 url = mod['url'])
    return self.sco_header(REQUEST)\
               + """<h2>%d notes chang�es</h2>
               <p><a href="moduleimpl_status?moduleimpl_id=%s">
               Revenir au tableau de bord du module</a>
               </p>
               """ % (nb_changed, M['moduleimpl_id']) \
               + self.sco_footer(REQUEST)


def evaluation_suppress_alln(self, evaluation_id, REQUEST, dialog_confirmed=False):
    "suppress all notes in this eval"
    authuser = REQUEST.AUTHENTICATED_USER
    E = self.do_evaluation_list( {'evaluation_id' : evaluation_id})[0]
    if not self.can_edit_notes( authuser, E['moduleimpl_id'], allow_ens=False ):
        # NB: les charg�s de TD n'ont pas le droit.
        # XXX imaginer un redirect + msg erreur
        raise AccessDenied('Modification des notes impossible pour %s'%authuser)
    if not dialog_confirmed:
        return self.confirmDialog(
            '<p>Confirmer la suppression des notes ?</p>',
            dest_url="", REQUEST=REQUEST,
            cancel_url="moduleimpl_status?moduleimpl_id=%s"%E['moduleimpl_id'],
            parameters={'evaluation_id':evaluation_id})
    # recupere les etuds ayant une note
    NotesDB = self._notes_getall(evaluation_id)
    notes = [ (etudid, NOTES_SUPPRESS) for etudid in NotesDB.keys() ]
    # modif
    nb_changed, nb_suppress = self._notes_add(
        authuser, evaluation_id, notes, comment='suppress all' )
    assert nb_changed == nb_suppress       
    H = [ '<p>%s notes supprim�es</p>' % nb_suppress,
          '<p><a class="stdlink" href="moduleimpl_status?moduleimpl_id=%s">continuer</a>'
          % E['moduleimpl_id']
          ]
    # news
    M = self.do_moduleimpl_list( args={ 'moduleimpl_id':E['moduleimpl_id'] } )[0]
    mod = self.do_module_list( args={ 'module_id':M['module_id'] } )[0]
    mod['moduleimpl_id'] = M['moduleimpl_id']
    cnx = self.GetDBConnexion()
    mod['url'] = "Notes/moduleimpl_status?moduleimpl_id=%(moduleimpl_id)s"%mod
    sco_news.add(REQUEST, cnx, typ=NEWS_NOTE, object=M['moduleimpl_id'],
                 text='Suppression des notes d\'une �valuation dans <a href="%(url)s">%(titre)s</a>' % mod,
                 url= mod['url'])

    return self.sco_header(REQUEST) + '\n'.join(H) + self.sco_footer(REQUEST)


def _check_notes( notes, evaluation ):
    """notes is a list of tuples (etudid, value)
    returns list of valid notes (etudid, float value)
    and 4 lists of etudid: invalids, withoutnotes, absents, tosuppress
    """
    note_max = evaluation['note_max']
    L = [] # liste (etudid, note) des notes ok (ou absent) 
    invalids = [] # etudid avec notes invalides
    withoutnotes = [] # etudid sans notes (champs vides)
    absents = [] # etudid absents
    tosuppress = [] # etudids avaec ancienne note � supprimer
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


def _notes_add(self, uid, evaluation_id, notes, comment=None, do_it=True ):
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
    # Verifie inscription et valeur note
    inscrits = {}.fromkeys(self.do_evaluation_listeetuds_groups(
        evaluation_id,getallstudents=True, include_dems=True))
    for (etudid,value) in notes:
        if not inscrits.has_key(etudid):
            raise NoteProcessError("etudiant %s non inscrit a l'evaluation %s" %(etudid,evaluation_id))
        if not ((value is None) or (type(value) == type(1.0))):
            raise NoteProcessError( "etudiant %s: valeur de note invalide (%s)" %(etudid,value))
    # Recherche notes existantes
    NotesDB = self._notes_getall(evaluation_id)
    # Met a jour la base
    cnx = self.GetDBConnexion()
    cursor = cnx.cursor()
    nb_changed = 0
    nb_suppress = 0
    E = self.do_evaluation_list( {'evaluation_id' : evaluation_id})[0]
    M = self.do_moduleimpl_list(args={ 'moduleimpl_id' : E['moduleimpl_id']})[0]

    try:
        for (etudid,value) in notes:
            if not NotesDB.has_key(etudid):
                # nouvelle note
                if value != NOTES_SUPPRESS:
                    if do_it:
                        aa = {'etudid':etudid, 'evaluation_id':evaluation_id,
                              'value':value, 'comment' : comment, 'uid' : uid}
                        quote_dict(aa)
                        cursor.execute('insert into notes_notes (etudid,evaluation_id,value,comment,uid) values (%(etudid)s,%(evaluation_id)s,%(value)f,%(comment)s,%(uid)s)', aa )
                    nb_changed = nb_changed + 1
            else:
                # il y a deja une note
                oldval = NotesDB[etudid]['value']
                changed = False
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
                               'date': apply(DB.Timestamp, time.localtime()[:6]),
                               'comment' : comment, 'uid' : uid}
                        quote_dict(aa)
                    if value != NOTES_SUPPRESS:
                        if do_it:
                            cursor.execute('update notes_notes set value=%(value)s, comment=%(comment)s, date=%(date)s, uid=%(uid)s where etudid=%(etudid)s and evaluation_id=%(evaluation_id)s', aa )
                    else: # supression ancienne note
                        if do_it:
                            log('_notes_add, suppress, evaluation_id=%s, etudid=%s, oldval=%s'
                            % (evaluation_id,etudid,oldval) )
                            cursor.execute('delete from notes_notes where etudid=%(etudid)s and evaluation_id=%(evaluation_id)s', aa )
                        nb_suppress += 1
                    nb_changed += 1                    
    except:
        log('*** exception in _notes_add')
        if do_it:
            # inval cache
            self._inval_cache(formsemestre_id=M['formsemestre_id'])
            cnx.rollback() # abort
        raise # re-raise exception
    if do_it:
        cnx.commit()
        self._inval_cache(formsemestre_id=M['formsemestre_id']) 
    return nb_changed, nb_suppress


def notes_eval_selectetuds(context, evaluation_id, REQUEST=None):
    """Dialogue saisie notes: choix methode et groupes
    """
    H = [ context.sco_header(REQUEST, page_title='Saisie des notes')]
    
    formid = 'notesfile'
    if not REQUEST.form.get('%s-submitted'%formid,False):
        # not submitted, choix groupe
        r = context.do_evaluation_selectetuds(REQUEST)
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
                      'explanation':'(note: la colonne remarque du fichier excel est ignor�e)' }),
        ),
                            formid=formid,
                            submitlabel = 'T�l�charger')
    if nf[0] == 0:
        H.append('''<p>Le fichier doit �tre un fichier tableur obtenu via
        le formulaire ci-dessus, puis compl�t� et enregistr� au format Excel.
        </p>''')
        H.append(nf[1])
    elif nf[0] == -1:
        H.append('<p>Annulation</p>')
    elif nf[0] == 1:
        updiag = context.do_evaluation_upload_xls(REQUEST)
        if updiag[0]:
            H.append('''<p>Notes charg�es.&nbsp;&nbsp;&nbsp;
            <a class="stdlink" href="moduleimpl_status?moduleimpl_id=%(moduleimpl_id)s">
            Revenir au tableau de bord du module</a>
            &nbsp;&nbsp;&nbsp;
            <a class="stdlink" href="notes_eval_selectetuds?evaluation_id=%(evaluation_id)s">Charger d'autres notes dans cette �valuation</a>
            </p>''' % theeval)
        else:
            H.append('''<p class="redboldtext">Notes non charg�es !</p>'''            
                     + updiag[1] )
            H.append('''
            <p><a class="stdlink" href="notes_eval_selectetuds?evaluation_id=%(evaluation_id)s">
            Reprendre</a>
            </p>''' % theeval)
    #
    H.append('''</div><h3>Autres op�rations</h3><ul>''')
    if context.can_edit_notes(REQUEST.AUTHENTICATED_USER,theeval['moduleimpl_id'],allow_ens=False):
        H.append('''
        <li>
        <form action="do_evaluation_set_missing" method="GET">
        Mettre toutes les notes manquantes � <input type="text" size="5" name="value"/>
        <input type="submit" value="OK"/> 
        <input type="hidden" name="evaluation_id" value="%s"/> 
        <em>ABS indique "absent" (z�ro), EXC "excus�" (neutralis�es), ATT "attente"</em>
        </form>
        </li>        
        <li><a class="stdlink" href="evaluation_suppress_alln?evaluation_id=%s">Effacer toutes les notes de cette �valuation</a> (ceci permet ensuite de supprimer l'�valuation si besoin)
        </li>''' % (evaluation_id, evaluation_id)) #'
    H.append('''<li><a class="stdlink" href="moduleimpl_status?moduleimpl_id=%(moduleimpl_id)s">Revenir au module</a>
    </li>
    </ul>''' % theeval )
    
    H.append("""<h3>Explications</h3>
<ol>
<li>Cadre bleu (�tape 1): 
<ol><li>choisir la m�thode de saisie (formulaire web ou feuille Excel);
    <li>choisir le ou les groupes;</li>
</ol>
</li>
<li>Cadre vert (�tape 2): � n'utiliser que si l'on est pass� par une feuille Excel. Indiquer le fichier Excel <em>t�l�charg� � l'�tape 1</em> et dans lequel on a saisi des notes. Remarques:
<ul>
<li>le fichier Excel ne doit pas forc�ment �tre complet: on peut ne saisir que quelques notes et r�p�ter l'op�ration (en t�l�chargeant un nouveau fichier) plus tard;</li>
<li>seules les valeurs des notes modifi�es sont prises en compte;</li>
<li>seules les notes sont extraites du fichier Excel;</li>
<li>on peut optionnellement ajouter un commentaire (type "copies corrig�es par Dupont", ou "Modif. suite � contestation") dans la case "Commentaire".
</li>
<li>le fichier Excel <em>doit imp�rativement �tre celui charg� � l'�tape 1 pour cette �valuation</em>. Il n'est pas possible d'utiliser une liste d'appel ou autre document Excel t�l�charg� d'une autre page.</li>
</ul>
</li>
</ol>
""")
    H.append( context.sco_footer(REQUEST) )
    return '\n'.join(H)

