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

# Affiche tous les semestres:
for sem in sems:
    print sem['formsemestre_id'], sem['titre_num']

# Recupere la table de notes:
nt = context.Notes._getNotesCache().get_NotesTable(context.Notes, formsemestre_id)


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


class DummyResponse:
    """Emulation vide de Reponse http Zope"""
    def __init__(self):
        self.header = {}
        self.redirected = ''
    def setHeader(self, name, value):
        self.header[name] = value
    def redirect(self, url):
        self.redirected = url
    
class DummyRequest:
    """Emulation vide de Request Zope"""
    def __init__(self):
        self.RESPONSE = DummyResponse()
        self.AUTHENTICATED_USER = 'admin'
        self.form = {}
        self.URL = 'http://scodoc/'
        self.URL1 = self.URL
        self.URL0 = self.URL
        self.BASE0 = 'localhost'
        self.REMOTE_ADDR = '127.0.0.1'
        self.HTTP_REFERER = ''
        self.REQUEST_METHOD = 'get'
        self.QUERY_STRING = ''
        
        
REQUEST = DummyRequest()
