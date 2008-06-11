# -*- mode: python -*-
# -*- coding: iso8859-15 -*-

##############################################################################
#
# Gestion scolarite IUT
#
# Copyright (c) 2001 - 2008 Emmanuel Viennet.  All rights reserved.
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

"""ScoDoc preferences (replaces old Zope properties)
"""

from sco_utils import *
from notesdb import *
from TrivialFormulator import TrivialFormulator, TF


PREFS = (
    ('DeptName',
      { 'initvalue' : 'Dept',
        'title' : 'Nom abbr�g� du d�partement',
        'size' : 12,
        }
     ),
    ( 'DeptFullName',
      { 'initvalue' : 'nom du d�partement',
        'title' : 'Nom complet du d�partement',
        'explanation' : 'actuellement inutilis�',
        'size' : 40
        }
      ),
    ( 'UnivName',
      { 'initvalue' : '',
        'title' : 'Nom de l\'Universit�',
        'size' : 40
        }
      ),
    ( 'DirectorName',
      { 'initvalue' : '',
        'title' : 'Nom du directeur de l\'�tablissement',
        'size' : 32,
        }
      ),
   ( 'DeptIntranetURL',
      { 'initvalue' : '',
        'title' : 'URL du web (intranet ou site) du d�partement',
         'size' : 40
        }
      ),
    ( 'email_chefdpt',
      { 'initvalue' : '',
        'title' : 'e-mail chef du d�partement',
        'size' : 40
        }
      ),
    ('_sep_abs',
     { 'input_type' : 'separator',
       'title' : 'Suivi des absences'
       }
     ),
    ( 'work_saturday',
      { 'initvalue' : 0,
        'title' : "Consid�rer le samedi comme travaill�",
        'input_type' : 'boolcheckbox',
        }
      ),
    ( 'send_mail_absence_to_chef',
      { 'initvalue' : 0,
        'title' : "Envoyer un mail au chef si un �tudiant a beaucoup d\'absences",
        'input_type' : 'boolcheckbox',
        }
      ),
    ( 'portal_url',
      { 'initvalue' : '',
        'title' : 'URL du portail (Apog�e)',
        'size' : 40
        }
      ),
    ( 'portal_dept_name',
      { 'initvalue' : 'Dept',
        'title' : 'code du d�partement sur le portail (Apog�e)',
        }
      ),
    ( 'notify_etud_changes_to',
      { 'initvalue' : '',
        'title' : 'e-mail a qui notifier les changements d\'identit� des �tudiants',
        'explanation' : 'utile pour mettre � jour manuellement d\'autres bases de donn�es',
         'size' : 40
        }
      ),
    ( 'DeptCreatedUsersRoles',
      { 'initvalue' : 'EnsDept,SecrDept',
        'title' : 'R�les que l\'on peut attribuer aux utilisateurs de ce d�partement',
        'explanation' : 'liste de noms de r�les, s�par�s par des virgules',
         'size' : 40
        }
      ),
)


class sco_preferences:
    _editor = EditableTable(
        'sco_prefs',
        'name',
        ('name', 'value'),
        sortkey='name',
        allow_set_id = True
        )
    
    def __init__(self, context):
        self.context = context
        self.load()

    def __getitem__(self, name):
        return self.prefs[name]

    def __setitem___(self, name, value):
        if name and name[0] == '_':
            raise ValueError('invalid preference name: %s' % name)
        self.prefs[name] = value
        self.save(name) # immediately write back to db

    def load(self):
        """Load all preferences from db
        """
        log('loading preferences')
        cnx = self.context.GetDBConnexion()
        preflist = self._editor.list(cnx)
        self.prefs = {}
        for p in preflist:
            self.prefs[p['name']] = p['value']
        # add defaults for missing prefs
        for pref in PREFS:
            name = pref[0]
            if name and name[0] != '_' and not name in self.prefs:
                # migration from Zope: search value in Zope property
                try:
                    value = getattr(self.context,name)
                    log('sco_preferences: found default value for %s=%s'%(name,value))
                except:
                    # uses hardcoded default
                    value = pref[1]['initvalue']
                self.prefs[name] = value
                log('creating missing preference for %s=%s'%(name,pref[1]['initvalue']))
                # add to db table
                self._editor.create(cnx, { 'name' : name, 'value' : self.prefs[name] })

    def save(self, name=None):
        """Write one or all values to db"""
        cnx = self.context.GetDBConnexion()
        if name is None:
            names = self.prefs.keys()
        else:
            names = [name]
        for name in names:
            log('save pref %s=%s' % (name, self[name]))
            self._editor.edit(cnx, { 'name' : name, 'value' : self[name] })       
    
    def edit(self, REQUEST):
        """HTML dialog"""
        H = [ self.context.sco_header(REQUEST, page_title="Pr�f�rences"),          
              "<h2>Pr�f�rences pour %s</h2>" % self.context.ScoURL() ]
        tf = TrivialFormulator(REQUEST.URL0, REQUEST.form, PREFS,
                               initvalues = self.prefs,
                               submitlabel = 'Modifier les valeurs' )
        if tf[0] == 0:
            return '\n'.join(H) + tf[1] + self.context.sco_footer(REQUEST)
        elif tf[0] == -1:
            return REQUEST.RESPONSE.redirect( REQUEST.URL1 ) # cancel
        else:
            for pref in PREFS:
                self.prefs[pref[0]] = tf[2][pref[0]]
            self.save()
            return REQUEST.RESPONSE.redirect( REQUEST.URL1 + '?head_message=Pr�f�rences modifi�es' ) 
