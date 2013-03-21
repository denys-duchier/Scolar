# -*- mode: python -*-
# -*- coding: iso8859-15 -*-

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

"""ScoDoc : annulation des saisies de notes


note = {evaluation_id, etudid, value, date, uid, comment}

Pour une évaluation:
 - notes actuelles: table notes_notes
 - historique: table notes_notes_log 

saisie de notes == saisir ou supprimer une ou plusieurs notes (mêmes date et uid)
/!\ tolérance sur les dates (200ms ?)
Chaque saisie affecte ou remplace une ou plusieurs notes.

Opérations:
 - lister les saisies de notes
 - annuler une saisie complète
 - lister les modifs d'une seule note
 - annuler une modif d'une note
"""

import datetime

from sco_utils import *
from notesdb import *
from notes_log import log
from gen_tables import GenTable
from intervals import intervalmap


# deux notes (de même uid) sont considérées comme de la même opération si
# elles sont séparées de moins de 2*tolerance:
OPERATION_DATE_TOLERANCE = datetime.timedelta(seconds=0.1)


class NotesOperation(dict):
    """Represents an operation on an evaluation
    Keys: evaluation_id, date, uid, notes
    """
    def get_comment(self):
        if self['notes']:
            return self['notes'][0]['comment']
        else:
            return ''
    
    def comp_values(self):
        "compute keys: comment, nb_notes"
        self['comment'] = self.get_comment()
        self['nb_notes'] = len(self['notes'])
        self['datestr'] = self['date'].strftime('%a %d/%m/%y %Hh%M')
        
    def undo(self, context):
        "undo operation"
        pass
        # replace notes by last found in notes_log
        # and suppress log entry
        # select * from notes_notes_log where evaluation_id= and etudid= and date < 
        #
        # verrouille tables notes, notes_log
        # pour chaque note qui n'est pas plus recente que l'operation:
        #   recupere valeurs precedentes dans log
        #   affecte valeurs notes
        #   suppr log
        # deverrouille tablesj
        #for note in self['notes']:
        #    # il y a-t-il une modif plus recente ?
        #    if self['current_notes_by_etud']['date'] <= self['date'] + OPERATION_DATE_TOLERANCE:
        #
        # + invalider cache   context.get_evaluations_cache().inval_cache(key=evaluation_id)

def list_operations(context, evaluation_id):
    """returns list of NotesOperation for this evaluation"""
    notes = context._notes_getall(evaluation_id, filter_suppressed=False).values()
    notes_log = context._notes_getall(evaluation_id, filter_suppressed=False, table='notes_notes_log').values()
    dt = OPERATION_DATE_TOLERANCE
    NotesDates = {} # { uid : intervalmap }

    for note in notes + notes_log:
        if not NotesDates.has_key(note['uid']):
            NotesDates[note['uid']] = intervalmap()
        nd = NotesDates[note['uid']]
        if nd[note['date']] is None:
            nd[note['date']-dt:note['date']+dt] = [ note ]
        else:
            nd[note['date']].append(note)

    current_notes_by_etud={} # { etudid : note }
    for note in notes:
        current_notes_by_etud[note['etudid']] = note
    
    Ops = []
    for uid in NotesDates.keys():
        for (t0, t1), notes in NotesDates[uid].items():
            Op = NotesOperation(evaluation_id=evaluation_id, date=t0, 
                                uid=uid, notes=NotesDates[uid][t0], 
                                current_notes_by_etud=current_notes_by_etud)
            Op.comp_values()
            Ops.append(Op)
    
    return Ops

def evaluation_list_operations(context, REQUEST, evaluation_id):
    """Page listing operations on evaluation"""
    E = context.do_evaluation_list( {'evaluation_id' : evaluation_id})[0]
    M = context.do_moduleimpl_list( args={ 'moduleimpl_id' : E['moduleimpl_id'] } )[0]

    Ops = list_operations(context, evaluation_id)

    columns_ids=('datestr', 'uid', 'nb_notes', 'comment')
    titles = { 'datestr' : 'Date', 'uid' : 'Enseignant', 'nb_notes' : 'Nb de notes',
               'comment' : 'Commentaire' }
    tab = GenTable( titles=titles, columns_ids=columns_ids, rows=Ops, 
                    html_sortable=False, 
                    html_title="<h2>Opérations sur l'évaluation %s du %s</h2>" % (E['description'], E['jour']),
                    preferences=context.get_preferences(M['formsemestre_id'])
                    )
    return tab.make_page(context, REQUEST=REQUEST)
                    

def formsemestre_list_saisies_notes(context, formsemestre_id, format='html', REQUEST=None):
    """Table listant toutes les operations de saisies de notes, dans toutes les evaluations du semestre."""
    sem = context.Notes.get_formsemestre(formsemestre_id)
    r = SimpleDictFetch(
        context, 
        """select i.nom, n.*, mod.titre, e.description from notes_notes n, notes_evaluation e, notes_moduleimpl m, notes_modules mod, identite i where m.moduleimpl_id = e.moduleimpl_id and m.module_id = mod.module_id and e.evaluation_id=n.evaluation_id and i.etudid=n.etudid and m.formsemestre_id=%(formsemestre_id)s order by date desc""",
        { 'formsemestre_id' : formsemestre_id,
          } )
    columns_ids=('date', 'nom', 'value', 'uid', 'titre', 'description', 'comment')
    titles = { 'nom' : 'Etudiant', 'date':'Date', 'value' : 'Note', 'comment' : 'Remarque', 'uid' : 'Enseignant', 
               'titre' : 'Module', 'description' : 'Evaluation' }
    tab = GenTable( titles=titles, columns_ids=columns_ids, rows=r,
                    html_title="<h2>Saisies de notes dans %s</h2>" % sem['titreannee'],
                    html_class='gt_table table_leftalign table_coldate',
                    html_sortable=True,
                    caption='Saisies de notes dans %s' % sem['titreannee'],
                    preferences=context.get_preferences(formsemestre_id),
                    base_url = '%s?formsemestre_id=%s' % (REQUEST.URL0, formsemestre_id),
                    origin = 'Généré par %s le ' % VERSION.SCONAME + timedate_human_repr() + ''
                    )
    return tab.make_page(context, format=format, REQUEST=REQUEST)
