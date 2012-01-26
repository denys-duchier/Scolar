# -*- mode: python -*-
# -*- coding: iso8859-15 -*-

##############################################################################
#
# Gestion scolarite IUT
#
# Copyright (c) 2001 - 2011 Emmanuel Viennet.  All rights reserved.
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
import sco_bulletins_generator

"""Global/Semestre Preferences for ScoDoc (version dec 2008)

Preferences (param�tres) communs � tous les utilisateurs.
Peuvent �tre d�finis globalement (pour tous les semestres)
ou bien seulement pour un semestre pr�cis.

Chaque parametre est d�fini dans la base de donn�es SQL par:
 - name : nom du parametre
 - value: valeur du parametre, ou NULL si on doit utiliser une valeur par d�faut
 - formsemestre_id: semestre associ�, ou NULL si applicable � tous les semestres
                    pour lesquels une valeur sp�cifique n'est pas d�finie.

Au niveau du code interface, on d�fini pour chaque pr�f�rence:
 - name (cl�)
 - title : titre en fran�ais
 - initvalue : valeur initiale, charg�e depuis config/scodoc_config.py
 - explanation: explication en fran�ais
 - size: longueur du chap texte
 - input_type: textarea,separator,... type de widget TrivialFormulator a utiliser
 - rows, rols: geometrie des textareas
 - category: misc ou bul ou page_bulletins ou abs ou general ou portal 
             ou pdf ou pvpdf ou ...
 - only_global (default False): si vraie, ne peut pas etre associ�e a un seul semestre.

Les titres et sous-titres de chaque cat�gorie sont d�finis dans PREFS_CATEGORIES

On peut �diter les pr�f�rences d'une ou plusieurs cat�gories au niveau d'un 
semestre ou au niveau global. 
* niveau global: changer les valeurs, liste de cat�gories.
   
* niveau d'un semestre:
   pr�senter valeur courante: valeur ou "definie globalement" ou par defaut
    lien "changer valeur globale"
   
------------------------------------------------------------------------------
Doc technique:

* Base de donn�es:
Toutes les pr�f�rences sont stock�es dans la table sco_prefs, qui contient
des tuples (name, value, formsemestre_id).
Si formsemestre_id est NULL, la valeur concerne tous les semestres,
sinon, elle ne concerne que le semestre indiqu�. 

* Utilisation dans ScoDoc
  - lire une valeur: 
      context.get_preference(name, formsemestre_id)
      nb: les valeurs sont des chaines, sauf:
         . si le type est sp�cfi� (float ou int)
         . les boolcheckbox qui sont des entiers 0 ou 1
  - avoir un mapping (read only) de toutes les valeurs:
      context.get_preferences(context,formsemestre_id)
  - editer les preferences globales:
      sco_preferences.get_base_preferences(self).edit(REQUEST=REQUEST)
  - editer les preferences d'un semestre:
      sem_preferences(context,formsemestre_id).edit()

* Valeurs par d�faut:
On a deux valeurs par d�faut possibles: 
 - via le fichier scodoc_config.py, qui peut �tre modifi� localement.
 - si rien dans scodoc_config.py, la valeur d�finie par
   sco_preferences.py est utilis�e (ne pas modifier ce fichier).


* Impl�mentation: sco_preferences.py

PREF_CATEGORIES : d�finition des cat�gories de pr�f�rences (pour
dialogues �dition)
PREFS : pour chaque pref, donne infos pour �dition (titre, type...) et
valeur par d�faut.

class sco_base_preferences
Une instance unique par site (d�partement, rep�r� par URL).
- charge les preferences pour tous le semestres depuis la BD.
 .get(formsemestre_id, name)
 .is_global(formsemestre_id, name)
 .save(formsemestre_id=None, name=None)
 .set(formsemestre_id, name, value)
 .deleteformsemestre_id, name)
 .edit() (HTML dialog)

class sem_preferences(context,formsemestre_id)
Une instance par semestre, et une instance pour prefs globales.
L'attribut .base_prefs point sur sco_base_preferences.
 .__getitem__   [name]
 .is_global(name)
 .edit(categories=[])


get_base_preferences(context, formsemestre_id)
 Return base preferences for this context (instance sco_base_preferences)

"""

PREF_CATEGORIES = (
    # sur page "Param�tres"
    ('general', {}),
    ('abs'  , { 'title' : 'Suivi des absences', 'related' : ('bul',) }),
    ('portal',{ 'title' : 'Liaison avec portail (Apog�e, etc)' }),
    ('pdf'  , { 'title' : 'Mise en forme des documents PDF',
               'related' : ('pvpdf', 'bul_margins')}),
    ('pvpdf', { 'title' : 'Proc�s verbaux de jury (documents PDF)',
               'related' : ('pdf', 'bul_margins') }),
    ('misc' , { 'title' : 'Divers' }),
    # sur page "R�glages des bulletins de notes"
    ('bul'  , { 'title' : 'R�glages des bulletins de notes',
               'related' : ('abs', 'bul_margins', 'bul_mail') }),
    # sur page "Mise en page des bulletins"
    ('bul_margins'  , { 'title' : 'Marges additionnelles des bulletins, en millim�tres', 
                       'subtitle' : "Le bulletin de notes notes est toujours redimensionn� pour occuper l'espace disponible entre les marges.",
                       'related' : ('bul', 'bul_mail', 'pdf')}),
    ('bul_mail', { 'title' : 'Envoi des bulletins par e-mail',
                   'related' : ('bul', 'bul_margins', 'pdf') }),
)


PREFS = (
    ('DeptName',
      { 'initvalue' : 'Dept',
        'title' : 'Nom abr�g� du d�partement',
        'size' : 12,
        'category' : 'general',
        'only_global' : True
        }
     ),
    ( 'DeptFullName',
      { 'initvalue' : 'nom du d�partement',
        'title' : 'Nom complet du d�partement',
        'explanation' : 'inutilis� par d�faut',
        'size' : 40,
        'category' : 'general',
        'only_global' : True
        }
      ),
    ( 'UnivName',
      { 'initvalue' : '',
        'title' : 'Nom de l\'Universit�',
        'explanation' : 'apparait sur les bulletins et PV de jury',
        'size' : 40,
        'category' : 'general',
        'only_global' : True
        }
      ),
     ( 'InstituteName',
      { 'initvalue' : '',
        'title' : 'Nom de l\'Institut',
        'explanation' : 'exemple "IUT de Villetaneuse". Peut �tre utilis� sur les bulletins.',
        'size' : 40,
        'category' : 'general',
        'only_global' : True
        }
      ),
    ( 'DeptIntranetTitle',
      { 'initvalue' : 'Intranet',
        'title' : 'Nom lien intranet',
        'size' : 40,
        'explanation' : 'titre du lien "Intranet" en haut � gauche',
        'category' : 'general',
        'only_global' : True
        }
      ),
    ( 'DeptIntranetURL',
      { 'initvalue' : '',
        'title' : """URL de l'"intranet" du d�partement""",
        'size' : 40,
        'explanation' : 'lien "Intranet" en haut � gauche',
        'category' : 'general',
        'only_global' : True
        }
      ),
    ('emails_notifications',
    { 'initvalue' : '',
       'title' : 'e-mails � qui notifier les op�rations',
        'size' : 70,
        'explanation' : 'adresses s�par�es par des virgules; notifie les op�rations (saisies de notes, etc). (vous pouvez pr�f�rer utiliser le flux rss)',
        'category' : 'general',
        'only_global' : False # peut �tre sp�cifique � un semestre
        }
      ),
    ( 'email_chefdpt',
      { 'initvalue' : '',
        'title' : 'e-mail chef du d�partement',
        'size' : 40,
        'explanation' : 'utilis� pour envoi mail notification absences',
        'category' : 'abs',
        'only_global' : True
        }
      ),
    
    
    # ------------------ Absences
    
    ( 'work_saturday',
      { 'initvalue' : 0,
        'title' : "Consid�rer le samedi comme travaill�",
        'input_type' : 'boolcheckbox',
        'category' : 'abs',
        'only_global' : True # devrait etre par semestre, mais demanderait modif gestion absences
        }
      ),
    ( 'handle_billets_abs',
      { 'initvalue' : 0,
        'title' : "Gestion de \"billets\" d'absence",
        'explanation' : "fonctions pour traiter les \"billets\" d�clar�s par les �tudiants sur un portail externe",
        'input_type' : 'boolcheckbox',
        'category' : 'abs',
        'only_global' : True
        }
      ),
    ( 'abs_notify_chief', # renamed from "send_mail_absence_to_chef"
      { 'initvalue' : 0,
        'title' : 'Notifier les absences au chef',
        'explanation' : "Envoyer un mail au chef si un �tudiant a beaucoup d\'absences",
        'input_type' : 'boolcheckbox',
        'category' : 'abs',
        'only_global' : True
        }
      ),
    ( 'abs_notify_respsem', 
      { 'initvalue' : 0,
        'title' : 'Notifier les absences au dir. des �tudes',
        'explanation' : "Envoyer un mail au responsable du semestre si un �tudiant a beaucoup d\'absences",
        'input_type' : 'boolcheckbox',
        'category' : 'abs',
        }
      ),
    ( 'abs_notify_respeval', 
      { 'initvalue' : 0,
        'title' : 'Notifier les absences aux resp. de modules',
        'explanation' : "Envoyer un mail � chaque absence aux responsable des modules avec �valuation � cette date",
        'input_type' : 'boolcheckbox',
        'category' : 'abs',
        }
      ),
    ( 'abs_notify_etud', 
      { 'initvalue' : 0,
        'title' : 'Notifier les absences aux �tudiants concern�s',
        'explanation' : "Envoyer un mail � l'�tudiant s'il a \"beaucoup\" d'absences",
        'input_type' : 'boolcheckbox',
        'category' : 'abs',
        }
      ),
    ( 'abs_notify_email',
      { 'initvalue' : '',
        'title' : "Notifier �:",
        'explanation' : "e-mail � qui envoyer des notification d'absences (en sus des autres destinataires �ventuels, comme le chef etc.)",
        'size' : 40,
        'explanation' : 'utilis� pour envoi mail absences',
        'category' : 'abs',
        }
      ),
    ('abs_notify_max_freq',
     { 'initvalue' : 7,
       'title' : 'Fr�quence maximale de notification',
       'explanation' : 'en jours (pas plus de X envois de mail pour chaque �tudiant/destinataire)',
       'size' : 4,
       'type' : 'int',
       'convert_numbers' : True,
       'category' : 'abs'
        }
      ),
    ('abs_notify_abs_threshold',
     { 'initvalue' : 10,
       'title' : 'Seuil de premi�re notification',       
       'explanation' : "nb minimum d'absences (en 1/2 journ�es) avant notification",
       'size' : 4,
       'type' : 'int',
       'convert_numbers' : True,
       'category' : 'abs'
        }
      ),
    ('abs_notify_abs_increment',
     { 'initvalue' : 20, # les notification suivantes seront donc rares
       'title' : 'Seuil notifications suivantes',       
       'explanation' : "nb minimum d'absences (en 1/2 journ�es suppl�mentaires)",
       'size' : 4,
       'type' : 'int',
       'convert_numbers' : True,
       'category' : 'abs'
        }
      ),
    ('abs_notification_mail_tmpl',
     { 'initvalue' : """
--- Ceci est un message de notification automatique issu de ScoDoc ---

L'�tudiant %(nomprenom)s  
inscrit en %(inscription)s) 

a cumul� %(nbabsjust)s absences justifi�es 
et %(nbabsnonjust)s absences NON justifi�es.

Le compte a pu changer depuis cet envoi, voir la fiche sur %(url_ficheetud)s.


Votre d�vou� serveur ScoDoc.

PS: Au dela de %(abs_notify_abs_threshold)s, un email automatique est adress� toutes les %(abs_notify_abs_increment)s absences. Ces valeurs sont modifiables dans les pr�f�rences de ScoDoc.
""",
       'title' : """Message notification e-mail""",
       'explanation' : """Balises remplac�es, voir la documentation""",
       'input_type' : 'textarea',
       'rows' : 15,
       'cols' : 64,
       'category' : 'abs'
       }
     ),

    # portal
    ( 'portal_url',
      { 'initvalue' : '',
        'title' : 'URL du portail',
        'size' : 40,
        'category' : 'portal',
        'only_global' : True
        }
      ),
    ( 'portal_dept_name',
      { 'initvalue' : 'Dept',
        'title' : 'Code du d�partement sur le portail',
        'category' : 'portal',
        'only_global' : True
        }
      ),
    ( 'notify_etud_changes_to',
      { 'initvalue' : '',
        'title' : 'e-mail � qui notifier les changements d\'identit� des �tudiants',
        'explanation' : 'utile pour mettre � jour manuellement d\'autres bases de donn�es',
         'size' : 40,
        'category' : 'portal',
        'only_global' : True
        }
      ),
    ( 'always_require_ine',
      { 'initvalue' : 0,
        'title' : 'Impose la pr�sence du code INE',
        'explanation' : "lors de toute cr�ation d'�tudiant (manuelle ou non)",
        'input_type' : 'boolcheckbox',
        'category' : 'portal',
        'only_global' : True
        }
      ),
    # pdf
    ('SCOLAR_FONT',
     { 'initvalue' : 'Helvetica',
        'title' : 'Police de caract�re principale',
        'explanation' : 'pour les pdf',
         'size' : 25,
        'category' : 'pdf'
        }
      ),
    ('SCOLAR_FONT_SIZE',
     { 'initvalue' : 10,
       'title' : 'Taille des caract�res',
       'explanation' : 'pour les pdf',
       'size' : 4,
       'type' : 'int',
       'convert_numbers' : True,
        'category' : 'pdf'
        }
      ),
    ('SCOLAR_FONT_SIZE_FOOT',
     { 'initvalue' : 6,
       'title' : 'Taille des caract�res pied de page',
       'explanation' : 'pour les pdf',
       'size' : 4,
       'type' : 'int',
       'convert_numbers' : True,
       'category' : 'pdf'
        }
      ),
    ('pdf_footer_x',
     { 'initvalue' : 20,
       'title' : 'Position horizontale du pied de page pdf (en mm)',
       'size' : 8,
       'type' : 'float', 'category' : 'pdf' 
       }
     ),
    ('pdf_footer_y',
     { 'initvalue' : 6.35,
       'title' : 'Position verticale du pied de page pdf (en mm)',
       'size' : 8,
       'type' : 'float', 'category' : 'pdf' 
       }
     ),
    # pvpdf
    ( 'DirectorName',
      { 'initvalue' : '',
        'title' : 'Nom du directeur de l\'�tablissement',
        'size' : 32,
        'explanation' : 'pour les PV de jury',
        'category' : 'pvpdf'
        }
      ),
    ('DirectorTitle',
      { 'initvalue' : """directeur de l'IUT""",
        'title' : 'Titre du "directeur"',
        'explanation' : 'titre apparaissant � c�t� de la signature sur les PV de jury',
        'size' : 64,
        'category' : 'pvpdf'
        }
      ),
    ('ChiefDeptName',
     { 'initvalue' : '',
       'title' : 'Nom du chef de d�partement',
       'size' : 32,
       'explanation' : 'pour les bulletins pdf',
       'category' : 'pvpdf'
     }
    ),
    ('INSTITUTION_NAME',
     { 'initvalue' : "<b>Institut Universitaire de Technologie - Universit� Paris 13</b>",
       'title' : 'Nom institution sur pied de pages PV',
       'explanation' : '(pdf, balises &lt;b&gt; interpr�t�es)',
       'input_type' : 'textarea',
       'rows' : 4, 'cols' : 64,
       'category' : 'pvpdf'
        }
      ),
    ('INSTITUTION_ADDRESS',
     { 'initvalue' : "Web <b>www.iutv.univ-paris13.fr</b> - 99 avenue Jean-Baptiste Cl�ment - F 93430 Villetaneuse",
       'title' : 'Adresse institution sur pied de pages PV',
       'explanation' : '(pdf, balises &lt;b&gt; interpr�t�es)',
       'input_type' : 'textarea',
       'rows' : 4, 'cols' : 64,
       'category' : 'pvpdf'
        }
      ),
    ('INSTITUTION_CITY',
     { 'initvalue' : "Villetaneuse",
       'title' : "Ville de l'institution",
       'explanation' : 'pour les lettres individuelles',
       'size' : 64,
       'category' : 'pvpdf'
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
       'rows' : 10,
       'category' : 'pvpdf'
       }
     ),
    ('PV_LETTER_DIPLOMA_SIGNATURE',
     { 'initvalue' : """Le %(DirectorTitle)s, <br/>%(DirectorName)s""",
       'title' :  """Signature des lettres individuelles de dipl�me""",
       'explanation' : """%(DirectorName)s et %(DirectorTitle)s remplac�s""",
       'input_type' : 'textarea',
       'rows' : 4,
       'cols' : 64,
       'category' : 'pvpdf'
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
       'category' : 'pvpdf'
       },
     ),
    ('pv_sig_image_height',
     { 'initvalue' : 11, 
         'size' : 10, 'title' : 'Hauteur de l\'image de la signature', 'type' : 'float',
         'explanation' : 'Lorsqu\'on donne une image de signature, elle est redimensionn�e � cette taille (en millim�tres)',
         'category' : 'pvpdf'
         }),
    ('PV_LETTER_TEMPLATE',
     { 'initvalue' : """<para>%(DirectorName)s
</para>
<para>%(DirectorTitle)s
</para>

<para leftindent="%(pv_htab1)s">%(INSTITUTION_CITY)s, le %(date_jury)s
</para>

<para leftindent="%(pv_htab1)s" spaceBefore="10mm">
� <b>%(nomprenom)s</b>
</para>
<para leftindent="%(pv_htab1)s">%(domicile)s</para>
<para leftindent="%(pv_htab1)s">%(codepostaldomicile)s %(villedomicile)s</para>

<para spaceBefore="25mm" fontSize="14">
<b>Objet : jury de %(type_jury)s 
du d�partement %(DeptName)s</b>
</para>
<para spaceBefore="10mm" fontSize="14">
Le jury de %(type_jury_abbrv)s du d�partement %(DeptName)s
s'est r�uni le %(date_jury)s. Les d�cisions vous concernant sont :
</para>

<para leftindent="%(pv_htab2)s" spaceBefore="5mm" fontSize="14">%(prev_decision_sem_txt)s</para>
<para leftindent="%(pv_htab2)s" spaceBefore="5mm" fontSize="14">
    <b>D�cision %(decision_orig)s :</b> %(decision_sem_descr)s
</para>

<para leftindent="%(pv_htab2)s" spaceBefore="0mm" fontSize="14">
%(decision_ue_txt)s
</para>

<para leftindent="%(pv_htab2)s" spaceBefore="0mm" fontSize="14">
%(observation_txt)s
</para>

<para spaceBefore="10mm" fontSize="14">%(autorisations_txt)s</para>

<para spaceBefore="10mm" fontSize="14">%(diplome_txt)s</para>
""",
       'title' : """Lettre individuelle""",
       'explanation' : """Balises remplac�es et balisage XML, voir la documentation""",
       'input_type' : 'textarea',
       'rows' : 15,
       'cols' : 64,
       'category' : 'pvpdf'
       },
     ),
     ('PV_LETTER_WITH_HEADER',
     { 'initvalue' : 0,
     'title' : 'Imprimer le logo en t�te des lettres individuelles de d�cision',
     'input_type' : 'boolcheckbox',
     'labels' : ['non', 'oui'],
     'category' : 'pvpdf'
     }
    ),  
    ('PV_LETTER_WITH_FOOTER',
    { 'initvalue' : 0,
      'title' : 'Imprimer le pied de page sur les lettres individuelles de d�cision',
      'input_type' : 'boolcheckbox',
      'labels' : ['non', 'oui'],
      'category' : 'pvpdf'
      }
    ),  
    ('pv_htab1',
     { 'initvalue' : '8cm',
       'title' : 'marge colonne droite lettre',
       'explanation' : 'pour les courriers pdf',
       'size' : 10,
       'category' : 'pvpdf'
        }
      ),
    ('pv_htab2',
     { 'initvalue' : '5mm',
       'title' : 'marge colonne gauche lettre',
       'explanation' : 'pour les courriers pdf',
       'size' : 10,
       'category' : 'pvpdf'
        }
      ),
    ('PV_FONTNAME',
     { 'initvalue' : 'Times-Roman',
       'title' : 'Police de caract�re pour les PV',
       'explanation' : 'pour les pdf',
       'size' : 25,
       'category' : 'pvpdf'
        }
      ),
    
    # bul
   ( 'bul_title', 
      { 'initvalue' : 'Universit� Paris 13 - IUT de Villetaneuse - D�partement %(DeptName)s',
        'size' : 70, 
        'title' : 'Titre des bulletins', 
        'explanation' : '<tt>%(DeptName)s</tt> est remplac� par le nom du d�partement',
        'category' : 'bul' }
      ),
    ( 'bul_class_name',
      { 'initvalue' : sco_bulletins_generator.bulletin_default_class_name(),
        'input_type' : 'menu',
        'labels' : sco_bulletins_generator.bulletin_class_descriptions(),
        'allowed_values' : sco_bulletins_generator.bulletin_class_names(),
        'title' : 'Format des bulletins', 
        'explanation' : 'format de pr�sentation des bulletins de note (web et pdf)',
        'category' : 'bul' }
      ),
    ( 'bul_show_abs', # ex "gestion_absence"
      { 'initvalue' : 1,
        'title' : 'Indiquer les absences sous les bulletins',
        'input_type' : 'boolcheckbox',
        'category' : 'bul',
        'labels' : ['non', 'oui']
        }
      ),
    ( 'bul_show_abs_modules', 
      { 'initvalue' : 0,
        'title' : 'Indiquer les absences dans chaque module',
        'input_type' : 'boolcheckbox',
        'category' : 'bul',
        'labels' : ['non', 'oui']
        }
      ),
    ( 'bul_show_decision', 
      { 'initvalue' : 1,
        'title' : 'Faire figurer les d�cisions sur les bulletins',
        'input_type' : 'boolcheckbox',
        'category' : 'bul',
        'labels' : ['non', 'oui']
        }
      ),
    ( 'bul_show_codemodules', 
      { 'initvalue' : 0,
        'title' : 'Afficher codes des modules sur les bulletins',
        'input_type' : 'boolcheckbox',
        'category' : 'bul',
        'labels' : ['non', 'oui']
        }
      ),
    ( 'bul_show_matieres', 
      { 'initvalue' : 0,
        'title' : 'Afficher les mati�res sur les bulletins',
        'input_type' : 'boolcheckbox',
        'category' : 'bul',
        'labels' : ['non', 'oui']
        }
      ),
    ( 'bul_show_all_evals', 
      { 'initvalue' : 0,
        'title' : 'Afficher toutes les �valuations sur les bulletins',
        'explanation' : 'y compris incompl�tes ou futures',
        'input_type' : 'boolcheckbox',
        'category' : 'bul',
        'labels' : ['non', 'oui']
        }
      ),
    ( 'bul_show_rangs', 
      { 'initvalue' : 1,
        'title' : 'Afficher le classement sur les bulletins',
        'input_type' : 'boolcheckbox',
        'category' : 'bul',
        'labels' : ['non', 'oui']
        }
      ),
    ( 'bul_show_ue_rangs', 
      { 'initvalue' : 1,
        'title' : 'Afficher le classement dans chaque UE sur les bulletins',
        'input_type' : 'boolcheckbox',
        'category' : 'bul',
        'labels' : ['non', 'oui']
        }
      ),
    ( 'bul_show_mod_rangs', 
      { 'initvalue' : 1,
        'title' : 'Afficher le classement dans chaque module sur les bulletins',
        'input_type' : 'boolcheckbox',
        'category' : 'bul',
        'labels' : ['non', 'oui']
        }
      ),
    ( 'bul_show_minmax', 
      { 'initvalue' : 0,
        'title' : 'Afficher min/max moyennes sur les bulletins',
        'input_type' : 'boolcheckbox',
        'category' : 'bul',
        'labels' : ['non', 'oui']
        }
      ),
    ( 'bul_show_minmax_mod', 
      { 'initvalue' : 0,
        'title' : 'Afficher min/max moyennes des modules sur les bulletins',
        'input_type' : 'boolcheckbox',
        'category' : 'bul',
        'labels' : ['non', 'oui']
        }
      ),
      ( 'bul_show_ue_cap_details', 
      { 'initvalue' : 0,
        'title' : 'Afficher d�tail des notes des UE capitalis�es sur les bulletins',
        'input_type' : 'boolcheckbox',
        'category' : 'bul',
        'labels' : ['non', 'oui']
        }
      ),
    ( 'bul_show_temporary_forced', 
      { 'initvalue' : 0,
        'title' : 'Banni�re "provisoire" sur les bulletins',
        'input_type' : 'boolcheckbox',
        'category' : 'bul',
        'labels' : ['non', 'oui']
        }
      ),      
    ( 'bul_show_temporary', 
      { 'initvalue' : 1,
        'title' : 'Banni�re "provisoire" si pas de d�cision de jury',
        'input_type' : 'boolcheckbox',
        'category' : 'bul',
        'labels' : ['non', 'oui']
        }
      ),
    ( 'bul_temporary_txt',
      { 'initvalue' : 'Provisoire',
        'title' : 'Texte de la banni�re "provisoire',
        'explanation' : '',
        'size' : 40,
        'category' : 'bul',
        }
      ),
    ( 'bul_show_uevalid', 
      { 'initvalue' : 1,
        'title' : 'Faire figurer les UE valid�es sur les bulletins',
        'input_type' : 'boolcheckbox',
        'category' : 'bul',
        'labels' : ['non', 'oui']
        }
       ),
     ( 'bul_show_mention', 
      { 'initvalue' : 0,
        'title' : 'Faire figurer les mentions sur les bulletins et les PV',
        'input_type' : 'boolcheckbox',
        'category' : 'bul',
        'labels' : ['non', 'oui']
        }
      ),
     ( 'bul_show_date_inscr', 
      { 'initvalue' : 1,
        'title' : 'Faire figurer la date d\'inscription sur les bulletins',
        'input_type' : 'boolcheckbox',
        'category' : 'bul',
        'labels' : ['non', 'oui']
        }
      ),
    ( 'bul_show_sig_left', 
      { 'initvalue' : 0,
        'title' : 'Faire figurer la signature de gauche (nom du directeur) sur les bulletins',
        'input_type' : 'boolcheckbox',
        'category' : 'bul',
        'labels' : ['non', 'oui']
        }
      ),
    ( 'bul_show_sig_right', 
      { 'initvalue' : 0,
        'title' : 'Faire figurer la signature de droite (nom du chef de d�partement) sur les bulletins',
        'input_type' : 'boolcheckbox',
        'category' : 'bul',
        'labels' : ['non', 'oui']
        }
      ),

    # champs des bulletins PDF:
    ( 'bul_pdf_title',
      { 'initvalue' : """<para fontSize="14" align="center">
<b>%(UnivName)s</b>
</para>
<para fontSize="16" align="center" spaceBefore="2mm">
<b>%(InstituteName)s</b>
</para>
<para fontSize="16" align="center" spaceBefore="4mm">
<b>RELEV� DE NOTES</b>
</para>

<para fontSize="15" spaceBefore="3mm">
%(nomprenom)s <b>%(demission)s</b>
</para>

<para fontSize="14" spaceBefore="3mm">
Formation: %(titre_num)s</para>
<para fontSize="14" spaceBefore="2mm">
Ann�e scolaire: %(anneescolaire)s
</para>""",
        'title' : 'Bulletins PDF: paragraphe de titre',
        'explanation' : '(balises interpr�t�es, voir documentation)',
        'input_type' : 'textarea', 'rows' : 10, 'cols' : 64,
        'category' : 'bul' }
      ),
    ( 'bul_pdf_caption',
      { 'initvalue' : """<para spaceBefore="5mm" fontSize="14"><i>%(situation)s</i></para>""",
        'title' : 'Bulletins PDF: paragraphe sous table note',
        'explanation' : '(visible seulement si "Faire figurer les d�cision" est coch�)',
        'input_type' : 'textarea', 'rows' : 4, 'cols' : 64,
        'category' : 'bul' }
      ),
     ( 'bul_pdf_sig_left',
      { 'initvalue' : """<para>La direction des �tudes
<br/>
%(responsable)s
</para>
""",
        'title' : 'Bulletins PDF: signature gauche',
        'explanation' : '(balises interpr�t�es, voir documentation)',
        'input_type' : 'textarea', 'rows' : 4, 'cols' : 64,
        'category' : 'bul' }
      ),
    ( 'bul_pdf_sig_right',
      { 'initvalue' : """<para>Le chef de d�partement
<br/>
%(ChiefDeptName)s
</para>
""",
        'title' : 'Bulletins PDF: signature droite',
        'explanation' : '(balises interpr�t�es, voir documentation)',
        'input_type' : 'textarea', 'rows' : 4, 'cols' : 64,
        'category' : 'bul' }
      ),
    ('SCOLAR_FONT_BUL_FIELDS',
     { 'initvalue' : 'Times-Roman',
       'title' : 'Police titres bulletins',
       'explanation' : 'pour les pdf',
       'size' : 25,
       'category' : 'bul'
        }
      ),

    # XXX A COMPLETER, voir sco_formsemestre_edit.py XXX

    # bul_mail
    ( 'email_copy_bulletins',
      { 'initvalue' : '',
        'title' : 'e-mail copie bulletins',
        'size' : 40,
        'explanation' : 'adresse recevant une copie des bulletins envoy�s aux �tudiants',
        'category' : 'bul_mail'
        }
      ),
    ( 'email_from_addr',
      { 'initvalue' : 'noreply', 
        'title' : 'adresse mail origine',
        'size' : 40,
        'explanation' : 'adresse exp�diteur pour les envois par mails (bulletins)',
        'category' : 'bul_mail',
        'only_global' : True
        }
      ),
    ( 'bul_intro_mail',
      { 'initvalue' : """%(nomprenom)s,\n\nvous trouverez ci-joint votre relev� de notes au format PDF.\nIl s\'agit d\'un relev� indicatif. Seule la version papier sign�e par le responsable p�dagogique de l\'�tablissement prend valeur officielle.\n\nPour toute question sur ce document, contactez votre enseignant ou le directeur des �tudes (ne pas r�pondre � ce message).\n\nCordialement,\nla scolarit� du d�partement %(dept)s.\n\nPS: si vous recevez ce message par erreur, merci de contacter %(webmaster)s""",
        'input_type' : 'textarea',
        'title' : "Message d'accompagnement",
        'explanation' : '<tt>%(DeptName)s</tt> est remplac� par le nom du d�partement, <tt>%(nomprenom)s</tt> par les noms et pr�noms de l\'�tudiant, <tt>%(dept)s</tt> par le nom du d�partement, et <tt>%(webmaster)s</tt> par l\'adresse mail du Webmaster.',
        'rows' : 18,
        'cols' : 85,
        'category' : 'bul_mail' }
      ),

    ( 'bul_mail_contact_addr',
      { 'initvalue' : "l'administrateur",
        'title' : 'Adresse mail contact "webmaster"',
        'explanation' : 'apparait dans le mail accompagnant le bulletin, voir balise "webmaster" ci-dessus.',
        'category' : 'bul_mail',
        'size' : 32
        }
      ),
    ( 'bul_mail_allowed_for_all', 
      { 'initvalue' : 1,
        'title' : 'Autoriser tous les utilisateurs � exp�dier des bulletins par mail',
        'input_type' : 'boolcheckbox',
        'category' : 'bul_mail',
        'labels' : ['non', 'oui']
        }
      ),
    # bul_margins
    ( 'left_margin', 
      { 'initvalue' : 0, 
        'size' : 10, 'title' : 'Marge gauche', 'type' : 'float',
        'category' : 'bul_margins'
       }),
    ( 'top_margin', 
      { 'initvalue' : 0, 
        'size' : 10, 'title' : 'Marge haute', 'type' : 'float',
        'category' : 'bul_margins'
       }),
    ( 'right_margin', 
      { 'initvalue' : 0, 
        'size' : 10, 'title' : 'Marge droite', 'type' : 'float',
        'category' : 'bul_margins'
       }),
    ( 'bottom_margin', 
      { 'initvalue' : 0, 
        'size' : 10, 'title' : 'Marge basse', 'type' : 'float',
        'category' : 'bul_margins'
       }),
        

)

PREFS_NAMES = set( [ x[0] for x in PREFS ] )
PREFS_ONLY_GLOBAL = set( [ x[0] for x in PREFS if x[1].get('only_global',False) ] )

PREFS_DICT = dict(PREFS)

class sco_base_preferences:
    _editor = EditableTable(
        'sco_prefs',
        'pref_id',
        ('pref_id', 'name', 'value', 'formsemestre_id'),
        sortkey = 'name',
        convert_null_outputs_to_empty=False,
        allow_set_id = True,
        html_quote=False, # car markup pdf reportlab  (<b> etc)
        filter_nulls=False
        )
    
    def __init__(self, context):
        self.context = context
        self.load()
    
    def load(self):
        """Load all preferences from db
        """
        log('loading preferences')
        try:
            GSL.acquire()
            cnx = self.context.GetDBConnexion()
            preflist = self._editor.list(cnx)
            self.prefs = { None : {} } # { formsemestre_id (or None) : { name : value } }
            self.default = {} # { name : default_value }
            for p in preflist:
                if not p['formsemestre_id'] in self.prefs:
                    self.prefs[p['formsemestre_id']] = {}
                
                # Convert types:
                if p['name'] in PREFS_DICT and PREFS_DICT[p['name']].has_key('type'):
                    func = eval(PREFS_DICT[p['name']]['type'])
                    p['value'] = func(p['value'])
                if p['name'] in PREFS_DICT and PREFS_DICT[p['name']].get('input_type',None) == 'boolcheckbox':
                    if p['value']:
                        p['value'] = int(p['value']) # boolcheckboxes are always 0/1
                    else:
                        p['value'] = 0 # NULL (backward compat)
                self.prefs[p['formsemestre_id']][p['name']] = p['value']
            
            # log('prefs=%s' % self.prefs)
            
            # add defaults for missing prefs
            for pref in PREFS:
                name = pref[0]
                
                # Migration from previous ScoDoc installations (before june 2008)
                # search preferences in Zope properties and in configuration file
                if name and name[0] != '_' and not name in self.prefs[None]:
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

                    self.default[name] = value
                    self.prefs[None][name] = value
                    log('creating missing preference for %s=%s'%(name,value))
                    # add to db table
                    self._editor.create(cnx, { 'name' : name, 'value' : value })
        finally:
            GSL.release()
    
    def get(self, formsemestre_id, name):
        """Returns preference value.
        If no value defined for this semestre, returns global value.
        """
        if formsemestre_id in self.prefs and name in self.prefs[formsemestre_id]:
            return self.prefs[formsemestre_id][name]
        elif name in self.prefs[None]:
            return self.prefs[None][name]
        else:
            return self.default[name]

    def is_global(self, formsemestre_id, name):
        "True if name if not defined for semestre"
        if not (formsemestre_id in self.prefs) or not name in self.prefs[formsemestre_id]:
            return True
        else:
            return False

    def save(self, formsemestre_id=None, name=None):
        """Write one or all (if name is None) values to db"""
        try:
            GSL.acquire()
            modif = False
            cnx = self.context.GetDBConnexion()
            if name is None:
                names = self.prefs[formsemestre_id].keys()
            else:
                names = [name]
            for name in names:
                value = self.get(formsemestre_id, name)
                # existe deja ?
                pdb = self._editor.list(cnx, args={'formsemestre_id' : formsemestre_id, 
                                                   'name' : name})
                if not pdb:
                    # cree preference
                    log('create pref sem=%s %s=%s' % (formsemestre_id, name, value))
                    self._editor.create(cnx, { 'name' : name, 'value' : value,
                                               'formsemestre_id' : formsemestre_id})
                    modif = True
                    log('create pref sem=%s %s=%s' % (formsemestre_id, name, value))
                else:
                    # edit existing value
                    if pdb[0]['value'] != str(value) and (pdb[0]['value'] or str(value)):
                        self._editor.edit(cnx, 
                                          {'pref_id' : pdb[0]['pref_id'], 
                                           'formsemestre_id' : formsemestre_id, 
                                           'name' : name, 'value' : value
                                           })
                        modif = True
                        log('save pref sem=%s %s=%s' % (formsemestre_id, name, value))
            
            # les preferences peuvent affecter les PDF cach�s:
            if modif:
                self.context.Notes._inval_cache(pdfonly=True) #> modif preferences
        finally:
            GSL.release()
    
    def set(self, formsemestre_id, name, value):
        if not name or name[0] == '_' or name not in PREFS_NAMES:
            raise ValueError('invalid preference name: %s' % name)
        if formsemestre_id and name in PREFS_ONLY_GLOBAL:
            raise ValueError('pref %s is always defined globaly')
        if not formsemestre_id in self.prefs:
            self.prefs[formsemestre_id] = {}
        self.prefs[formsemestre_id][name] = value
        self.save(formsemestre_id, name) # immediately write back to db    

    def delete(self, formsemestre_id, name):
        if not formsemestre_id:
            raise ScoException()
        try:
            GSL.acquire()
            if formsemestre_id in self.prefs and name in self.prefs[formsemestre_id]:
                del self.prefs[formsemestre_id][name]
            cnx = self.context.GetDBConnexion()
            pdb = self._editor.list(cnx, args={'formsemestre_id' : formsemestre_id, 
                                               'name' : name})
            if pdb:
                log('deleting pref sem=%s %s'%(formsemestre_id, name))
                self._editor.delete(cnx, pdb[0]['pref_id'])
        finally:
            GSL.release()
    
    def edit(self, REQUEST):
        """HTML dialog: edit global preferences"""
        H = [ self.context.sco_header(REQUEST, page_title="Pr�f�rences"),          
              "<h2>Pr�f�rences globales pour %s</h2>" % self.context.ScoURL(),
              """<p class="help">Ces param�tres s'appliquent par d�faut � tous les semestres, sauf si ceux-ci d�finissent des valeurs sp�cifiques.</p>
              <p class="msg">Attention: cliquez sur "Enregistrer les modifications" en bas de page pour appliquer vos changements !</p>
              """]
        form = _build_form(self, global_edit=True)
        tf = TrivialFormulator(REQUEST.URL0, REQUEST.form, form,
                               initvalues = self.prefs[None],
                               submitlabel = 'Enregistrer les modifications' )
        if tf[0] == 0:
            return '\n'.join(H) + tf[1] + self.context.sco_footer(REQUEST)
        elif tf[0] == -1:
            return REQUEST.RESPONSE.redirect( REQUEST.URL1 ) # cancel
        else:
            for pref in PREFS:
                self.prefs[None][pref[0]] = tf[2][pref[0]]
            self.save()
            return REQUEST.RESPONSE.redirect( REQUEST.URL1 + '?head_message=Pr�f�rences modifi�es' ) 

_SCO_BASE_PREFERENCES = {} # { URL: sco_base_preferences instance }
def get_base_preferences(context):
    """Return global preferences for this context"""
    u = context.ScoURL()
    if not u in _SCO_BASE_PREFERENCES:
        _SCO_BASE_PREFERENCES[u] = sco_base_preferences(context)
    return _SCO_BASE_PREFERENCES[u]


class sem_preferences:
    def __init__(self, context, formsemestre_id=None):
        self.context = context
        self.formsemestre_id = formsemestre_id
        self.base_prefs = get_base_preferences(self.context)

    def __getitem__(self, name):
        return self.base_prefs.get(self.formsemestre_id, name)

    def get(self, name, defaultvalue=None):
        # utilis� seulement par TF
        try:
            return self[name] # ignore supplied default value
        except:
            return defaultvalue

    def is_global(self, name):
        "True if preference defined for all semestres"
        return self.base_prefs.is_global(self.formsemestre_id, name) 

    # The dialog
    def edit(self, categories=[], REQUEST=None):
        """Dialog to edit semestre preferences in given categories"""
        if not self.formsemestre_id:
            raise ScoValueError('sem_preferences.edit doit etre appele sur un semestre !') # a bug !
        sem = self.context.Notes.get_formsemestre(self.formsemestre_id)
        H = [ self.context.Notes.html_sem_header(REQUEST, 'Pr�f�rences du semestre', sem),
              """
<p class="help">Les param�tres d�finis ici ne s'appliqueront qu'� ce semestre.</p>
<p class="msg">Attention: cliquez sur "Enregistrer les modifications" en bas de page pour appliquer vos changements !</p>
<script type="text/javascript">
function sel_global(el, pref_name) {
     if (el.value == 'create') {
        document.getElementById('tf').create_local.value = pref_name;
        document.getElementById('tf').destination.value = 'again';
        document.tf.submit();
     } else if (el.value == 'changeglobal') {
        document.getElementById('tf').destination.value = 'global';
        document.tf.submit();
     }
}
function set_global_pref(el, pref_name) {
     document.getElementById('tf').suppress.value = pref_name;
     document.getElementById('tf').destination.value = 'again';
     f = document.getElementById('tf')[pref_name];
     if (f) {
       f.disabled = true;
     } else {
       f = document.getElementById('tf')[pref_name+':list'];
       if (f) {
         f.disabled = true;
       }
     }
     document.tf.submit();
}
</script>
"""
              ]
        # build the form:
        form = _build_form(self,categories=categories)
        form.append( ('suppress', { 'input_type' : 'hidden' } ) )
        form.append( ('create_local', { 'input_type' : 'hidden' } ) )
        form.append( ('destination', { 'input_type' : 'hidden' } ) )
        form.append( ('formsemestre_id', {'input_type' : 'hidden' }) )
        #log('REQUEST form=%s'%REQUEST.form)
        tf = TrivialFormulator(REQUEST.URL0, REQUEST.form, form, 
                               initvalues = self,
                               cssclass="sco_pref",
                               submitlabel = 'Enregistrer les modifications' )
        if tf[0] == 0:
            return '\n'.join(H) + tf[1] + self.context.sco_footer(REQUEST)
        elif tf[0] == -1:
            return REQUEST.RESPONSE.redirect( REQUEST.URL1 + '?head_message=Annul�' ) # cancel
        else:
            #log('tf[2]=%s' % tf[2])
            # Supprime pref locale du semestre (retour � la valeur globale)
            if tf[2]['suppress']:
                self.base_prefs.delete(self.formsemestre_id, tf[2]['suppress'])
            # Cree pref local (copie valeur globale)
            if tf[2]['create_local']:
                cur_value = self[tf[2]['create_local']]
                self.base_prefs.set(self.formsemestre_id, tf[2]['create_local'], cur_value)
            # Modifie valeurs:
            for (pref_name, descr) in PREFS:
                if pref_name in tf[2] and not descr.get('only_global',False) and pref_name != tf[2]['suppress']:
                    form_value = tf[2][pref_name]
                    cur_value = self[pref_name]
                    if cur_value is None:
                        cur_value = ''
                    else:
                        cur_value = str(cur_value)
                    if cur_value != str(form_value):
                        # log('cur_value=%s (type %s), form_value=%s (type %s)' % (cur_value,type(cur_value),form_value, type(form_value)))
                        self.base_prefs.set(self.formsemestre_id,  pref_name, form_value)
            
            # destination: 
            # global: change pref and redirect to global params
            # again: change prefs and redisplay this dialog
            # done: change prefs and redirect to semestre status
            destination = tf[2]['destination']
            if destination == 'done' or destination == '':
                return REQUEST.RESPONSE.redirect( REQUEST.URL1 + '/formsemestre_status?head_message=Pr�f�rences modifi�es&formsemestre_id=' + self.formsemestre_id ) 
            elif destination == 'again':
                return REQUEST.RESPONSE.redirect( REQUEST.URL0 + '?formsemestre_id=' + self.formsemestre_id )
            elif destination == 'global':
                return REQUEST.RESPONSE.redirect( self.context.ScoURL() + '/edit_preferences' )
            


# Build list of elements for TrivialFormulator...
def _build_form(self, categories=[], global_edit=False):
    form = []
    for cat, cat_descr in PREF_CATEGORIES:
        if categories and cat not in categories:
            continue # skip this category
        #
        cat_elems = []
        for pref_name, pref in PREFS:
            if pref['category'] == cat:
                if pref.get('only_global',False) and not global_edit:
                    continue # saute les prefs seulement globales
                descr = pref.copy()
                descr['comment'] = descr.get('explanation', None)
                if 'explanation' in descr:
                    del descr['explanation']
                if not global_edit:
                    descr['explanation'] = """ou <a href="" onClick="set_global_pref(this, '%s');">utiliser param�tre global</a>""" % pref_name
                #if descr.get('only_global',False):
                #    # pas modifiable, donne juste la valeur courante
                #    descr['readonly'] = True
                #    descr['explanation'] = '(valeur globale, non modifiable)'
                #elif
                if not global_edit and self.is_global(pref_name):
                    # valeur actuelle globale (ou vient d'etre supprimee localement):
                    # montre la valeur et menus pour la rendre locale
                    descr['readonly'] = True
                    menu_global = """<select class="tf-selglobal" onChange="sel_global(this, '%s');">
                        <option value=""><em>Valeur d�finie globalement</em></option>
                        <option value="create">Sp�cifier valeur pour ce semestre seulement</option>
                    </select>
                    """ % pref_name
#                         <option value="changeglobal">Changer param�tres globaux</option>
                    descr['explanation'] = menu_global

                cat_elems.append( (pref_name, descr) )
        if cat_elems:
            # category titles:
            title = cat_descr.get('title', None)
            if title:
                form.append( ('sep_%s'%cat, { 'input_type' : 'separator',
                                              'title' : '<h3>%s</h3>' % title }))
            subtitle = cat_descr.get('subtitle', None)
            if subtitle:
                form.append( ('sepsub_%s'%cat, { 'input_type' : 'separator',
                                                 'title' : '<p class="help">%s</p>' % subtitle }))
            form.extend(cat_elems)
    return form


#
def doc_preferences(context):
    """ Liste les preferences, pour la documentation"""
    L = []
    for cat, cat_descr in PREF_CATEGORIES:
        L.append( [ '' ] )
        L.append( [ '===='+cat_descr.get('title', '')+'====' ] )
        for pref_name, pref in PREFS:
            if pref['category'] == cat:
                L.append( [ pref_name, pref['title'], pref.get('explanation', '') ] )
    return '<br/>\n'.join( [ '|| ' + " || ".join(x)  + ' ||' for x in L ]) 


