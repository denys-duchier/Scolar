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

"""Liste des notes d'une �valuation
"""

from notesdb import *
from sco_utils import *
from notes_log import log
from TrivialFormulator import TrivialFormulator, TF
from notes_table import *
import htmlutils

def do_evaluation_listenotes(self, REQUEST):
    """
    Affichage des notes d'une �valuation
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
    grnams  = ['tous'] + [('td'+x) for x in gr_td ] # noms des checkbox
    grnams += [('tp'+x) for x in gr_tp ]
    grnams += [('ta'+x) for x in gr_anglais ]
    grlabs  = ['tous'] + gr_td + gr_tp + gr_anglais # legendes des boutons
    descr = [
        ('evaluation_id',
         { 'default' : evaluation_id, 'input_type' : 'hidden' }),
        ('liste_format',
         {'input_type' : 'radio', 'default' : 'html', 'allow_null' : False, 
          'allowed_values' : [ 'html', 'pdf', 'xls' ],
          'labels' : ['page HTML', 'fichier PDF', 'fichier tableur' ],
          'title' : 'Format' }),
        ('s' ,
         {'input_type' : 'separator',
          'title': 'Choix du ou des groupes d\'�tudiants' }),
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
                            cancelbutton = 'Annuler', method='GET',
                            submitlabel = 'OK', cssclass='noprint',
                            name='tf' )
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
        if 'tous' in glist:
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
        hh = '<h4>%s du %s, %s (%d �tudiants)</h4>' % (E['description'], E['jour'], gr_title,len(etudids))
        if note_sur_20:
            nmx = 20
        else:
            nmx = E['note_max']
        Th = ['', 'Nom', 'Pr�nom', 'Groupe', 'Note sur %d'%nmx,
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
                        val = valsur20 # affichage notes / 20 demand�
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
                    # ce mode bizarre a �t� demand� par GTR1 en 2005
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
                C = ['<table><tr><td><div><h4>R�partition des notes:</h4>' + histo + '</div></td>\n',
                     '<td style="padding-left: 50px; vertical-align: top;"><p>' ]
                commentkeys = comments.items() # [ (comment, key), ... ]
                commentkeys.sort( lambda x,y: cmp(x[1], y[1]) )
                for (comment,key) in commentkeys:
                    C.append('<span class="colcomment">(%s)</span> <em>%s</em><br/>' % (key, comment))

                Tab = [ '<table class="%s"><tr class="tablenotetitle">'%tclass ] + Th + ['</tr><tr><td>'] + Tb + Tm + [ '</td></tr></table>' ] + C
            else:
                Tab = [ '<span class="boldredmsg">aucun groupe s�lectionn� !</span>' ]
            return tf[1] + '\n'.join(H) + hh + '\n'.join(Tab) 
        elif liste_format == 'pdf':
            return 'conversion PDF non implement�e !'
        else:
            raise ScoValueError('invalid value for liste_format (%s)'%liste_format)