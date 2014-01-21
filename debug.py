# -*- mode: python -*-
# -*- coding: utf-8 -*-

"""Configuration pour debugguer en mode console

Lancer ScoDoc ainsi: (comme root)

 /opt/scodoc/instance/bin/zopectl debug 

Puis

from debug import *
context = go(app)
 
Exemple:
sems = context.Notes.formsemestre_list()
formsemestre_id = sems[0]['formsemestre_id']

# Affiche tous le semestres:
for sem in sems:
    print sem['formsemestre_id'], sem['titre_num']

"""
from notesdb import *
from notes_log import log
from sco_utils import *

from gen_tables import GenTable
import sco_archives
import sco_groups
import sco_evaluations
import sco_formsemestre_edit
import sco_compute_moy
import sco_codes_parcours
import sco_bulletins
import sco_excel
import sco_formsemestre_status
import sco_bulletins_xml

# Prend le premier departement comme context

def go(app, n=0):
    context = app.ScoDoc.objectValues('Folder')[0].Scolarite
    return context



