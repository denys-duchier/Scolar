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
        'explanation' : 'pour les PV de jury',
        }
      ),
    ('DirectorTitle',
      { 'initvalue' : """directeur de l'IUT""",
        'title' : 'titre du "directeur" (celui qui signe les PV)',
        'size' : 64,
        }
      ),
    ( 'DeptIntranetTitle',
      { 'initvalue' : 'Intranet',
        'title' : 'Nom lien intranet',
        'size' : 40,
        'explanation' : 'Titre du lien "Intranet" en haut � gauche',
        }
      ),
    ( 'DeptIntranetURL',
      { 'initvalue' : '',
        'title' : """URL de l'"intranet" du d�partement""",
        'size' : 40,
        'explanation' : 'lien "Intranet" en haut � gauche',
        }
      ),
 
    ('_sep_abs',
     { 'input_type' : 'separator',
       'title' : '<b>Suivi des absences</b>'
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
    ( 'email_chefdpt',
      { 'initvalue' : '',
        'title' : 'e-mail chef du d�partement',
        'size' : 40,
        'explanation' : 'utilis� pour envoi mail absences'
        }
      ),
    ('_sep_portal',
     { 'input_type' : 'separator',
       'title' : '<b>Liaison avec portail (Apog�e, etc)</b>'
       }
     ),
    ( 'portal_url',
      { 'initvalue' : '',
        'title' : 'URL du portail',
        'size' : 40
        }
      ),
    ( 'portal_dept_name',
      { 'initvalue' : 'Dept',
        'title' : 'code du d�partement sur le portail',
        }
      ),
    ( 'notify_etud_changes_to',
      { 'initvalue' : '',
        'title' : 'e-mail � qui notifier les changements d\'identit� des �tudiants',
        'explanation' : 'utile pour mettre � jour manuellement d\'autres bases de donn�es',
         'size' : 40
        }
      ),
    ('_sep_users',
     { 'input_type' : 'separator',
       'title' : '<b>Gestion des utilisateurs</b>'
       }
     ),
    ('_sep_pdf',
     { 'input_type' : 'separator',
       'title' : '<b>Mise en forme des documents PDF</b>'
       }
     ),
    ('SCOLAR_FONT',
     { 'initvalue' : 'Helvetica',
        'title' : 'Police de caract�re principale',
        'explanation' : 'pour les pdf',
         'size' : 25
        }
      ),
    ('SCOLAR_FONT_SIZE',
     { 'initvalue' : 10,
       'title' : 'Taille des caract�res',
       'explanation' : 'pour les pdf',
       'size' : 4,
       'type' : 'int',
       'convert_numbers' : True
        }
      ),
    ('SCOLAR_FONT_SIZE_FOOT',
     { 'initvalue' : 6,
       'title' : 'Taille des caract�res pied de page',
       'explanation' : 'pour les pdf',
       'size' : 4,
       'type' : 'int',
       'convert_numbers' : True
        }
      ),
    ('_sep_pv',
     { 'input_type' : 'separator',
       'title' : '<b>Proc�s verbaux de jury (documents PDF)</b>'
       }
     ),
    ('INSTITUTION_NAME',
     { 'initvalue' : "<b>Institut Universitaire de Technologie - Universit� Paris 13</b>",
       'title' : 'Nom institution sur pied de pages PV',
       'explanation' : '(pdf, balises &lt;b&gt; interpr�t�es)',
       'input_type' : 'textarea',
       'rows' : 4, 'cols' : 64
        }
      ),
    ('INSTITUTION_ADDRESS',
     { 'initvalue' : "Web <b>www.iutv.univ-paris13.fr</b> - 99 avenue Jean-Baptiste Cl�ment - F 93430 Villetaneuse",
       'title' : 'Adresse institution sur pied de pages PV',
       'explanation' : '(pdf, balises &lt;b&gt; interpr�t�es)',
       'input_type' : 'textarea',
       'rows' : 4, 'cols' : 64
        }
      ),
    ('INSTITUTION_CITY',
     { 'initvalue' : "Villetaneuse",
       'title' : "Ville de l'institution",
       'explanation' : 'pour les lettres individuelles',
       'size' : 64,
        }
      ),
    ('PV_INTRO',
     { 'initvalue' : """<bullet>-</bullet>  
Vu l'arr�t� du 3 ao�t 2005 relatif au dipl�me universitaire de technologie et notamment son article 4 et 6;
</para>
<para><bullet>-</bullet>  
vu l'arr�t� n� %(Decnum)s du Pr�sident de l'%(UnivName)s;
</para>
<para><bullet>-</bullet> 
vu la d�lib�ration de la commission %(Type)s en date du %(Date)s pr�sid�e par le Chef du d�partement;
""",
       'title' : """Paragraphe d'introduction sur le PV""",
       'explanation' : """Balises remplac�es: %(Univname)s = nom de l'universit�, %(DecNum)s = num�ro de l'arr�t�, %(Date)s = date de la commission, %(Type)s = type de commission (passage ou d�livrance) """,
       'input_type' : 'textarea',
       'cols' : 80,
       'rows' : 10
       }
     ),
    ('PV_LETTER_DIPLOMA_SIGNATURE',
     { 'initvalue' : """Le %(DirectorTitle)s, <br/>%(DirectorName)s""",
       'title' :  """Signature des lettres individuelles de dipl�me""",
       'explanation' : """%(DirectorName)s et %(DirectorTitle)s remplac�s""",
       'input_type' : 'textarea',
       'rows' : 4,
       'cols' : 64,
       },
     ),
    ('PV_LETTER_PASSAGE_SIGNATURE',
     { 'initvalue' : """Pour le Directeur de l'IUT<br/>
et par d�l�gation<br/>
Le Chef du d�partement""",
       'title' : """Signature des lettres individuelles de passage d'un semestre � l'autre""",
       'explanation' : """%(DirectorName)s et %(DirectorTitle)s remplac�s""",
       'input_type' : 'textarea',
       'rows' : 4,
       'cols' : 64,
       },
     ),
    ('PV_FONTNAME',
     { 'initvalue' : 'Times-Roman',
        'title' : 'Police de caract�re pour les PV',
        'explanation' : 'pour les pdf',
         'size' : 25
        }
      ),
)


class sco_preferences:
    _editor = EditableTable(
        'sco_prefs',
        'name',
        ('name', 'value'),
        sortkey='name',
        allow_set_id = True,
        html_quote=False # car markup pdf reportlab  (<b> etc)
        )
    
    def __init__(self, context):
        self.context = context
        self.load()

    def __getitem__(self, name):
        return self.prefs[name]

    def __setitem___(self, name, value):
        self.set(name,value)
        
    def set(self,name,value):
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
        # add defaults for missing prefs, and convert types
        for pref in PREFS:
            name = pref[0]
            # convert integer types
            if pref[1].has_key('type') and pref[1]['type'] == 'int' and name in self.prefs:
                 self.prefs[name] = int(self.prefs[name])
            # add defaults:
            if name and name[0] != '_' and not name in self.prefs:
                # Migration from previous ScoDoc installations (before june 2008)
                # search preferences in Zope properties and in configuration file
                try:
                    value = getattr(self.context,name)
                    log('sco_preferences: found default value in Zope for %s=%s'%(name,value))
                except:
                    # search in CONFIG
                    if hasattr(CONFIG,name):
                        value = getattr(CONFIG,name)
                        log('sco_preferences: found default value in config for %s=%s'%(name,value))
                    else:
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

        # les preferences peuvent affecter les PDF cach�s:
        self.context.Notes._inval_cache(pdfonly=True)

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
