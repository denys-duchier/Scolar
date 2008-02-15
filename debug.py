
import time, os, sys, pdb

from sco_utils import *
from ScolarRolesNames import *
from notesdb import *
from notes_log import log
from scolog import logdb
import scolars
from scolars import format_nom, format_prenom, format_sexe, format_lycee
from TrivialFormulator import TrivialFormulator, TF

import ZNotes

DB_CNX_STRING = 'xxxxxxx'
cnx=DB.connect( DB_CNX_STRING )
