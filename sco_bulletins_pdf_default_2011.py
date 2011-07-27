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
#   Emmanuel Viennet      emmanuel.viennet@gmail.com
#
##############################################################################

"""Generation bulletins de notes en PDF (avec reportlab)

Nouvelle version juillet 2011: changement de la présentation de la table.
Devrait normalement devenir le format par defaut après tests.

XXX dev en cours - Ne pas utiliser ni modifier XXX


Les templates utilisent les XML markup tags de ReportLab
 (voir ReportLab user guide, page 70 et suivantes), dans lesquels les balises
de la forme %(XXX)s sont remplacées par la valeur de XXX, pour XXX dans:

- preferences du semestre (ou globales) (voir sco_preferences.py)
- champs de formsemestre: titre, date_debut, date_fin, responsable, anneesem
- champs de l'etudiant s(etud, décoré par getEtudInfo)
- demission ("DEMISSION" ou vide)
- situation ("Inscrit le XXX")

Balises img: actuellement interdites.

"""
from sco_pdf import *
import sco_preferences
import traceback, re
from notes_log import log
import sco_bulletins_pdf
import sco_bulletins_pdf_default

# Important: Le nom de la classe ne doit pas changer (bien le choisir), car il sera stocké en base de données (dans les préférences)
class PDFBulletinGeneratorDefault2011(sco_bulletins_pdf_default.PDFBulletinGeneratorDefault):
    description = 'standard ScoDoc (version 2011, beta)'  # la description doit être courte: elle apparait dans le menu de paramètrage ScoDoc  
    def gen_table(self):
        """Génère la table centrale du bulletin de notes
        Renvoie une liste d'objets PLATYPUS (eg instance de Table).
        """
        colkeys, P, pdfTableStyle, colWidths = bulletin_pdf_table_classic_2011(self.context, self.infos, version=self.version)
        return [ self.buildTableFromDicts( colkeys, P, pdfTableStyle, colWidths) ]
    

sco_bulletins_pdf.register_pdf_bulletin_class(PDFBulletinGeneratorDefault2011)


class BulTableStyle:
    """Construction du style de tables reportlab platypus pour les bulletins "classiques"
    """
    LINEWIDTH = 0.5
    LINECOLOR = Color(0,0,0)
    UEBGCOLOR = Color(150/255.,200/255.,180/255.) # couleur fond lignes titres UE
    MODSEPCOLOR=Color(170/255.,170/255.,170/255.) # lignes séparant les modules
    def __init__(self):
        self.tabline = 0
        self.pdfTableStyle = []
    
    def get_style(self):
        "get resulting style (a list of platypus table commands)"
        # ajoute cadre extérieur bleu:
        self.pdfTableStyle.append( ('BOX', (0,0), (-1,-1), 0.4, blue) )
        
        return self.pdfTableStyle
    
    def newline(self, ue_type=None):
        if ue_type == 'cur': # UE courante non prise en compte (car capitalisee)
            self.pdfTableStyle.append(('BACKGROUND', (0,self.tabline), (-1,self.tabline),
                                       Color(210/255.,210/255.,210/255.) ))
        self.tabline += 1
    
    def ueline(self): # met la ligne courante du tableau pdf en style 'UE'
        i = self.tabline
        self.pdfTableStyle.append(('BACKGROUND', (0,i), (-1,i),self.UEBGCOLOR ))
        self.pdfTableStyle.append(('LINEABOVE', (0,i), (-1,i), 1, Color(0.,0.,0.)))
        self.newline()
    
    def modline(self, ue_type=None): # met la ligne courante du tableau pdf en style 'Module'
        i = self.tabline
        self.pdfTableStyle.append(('LINEABOVE', (0,i), (-1,i), 1, self.MODSEPCOLOR))
        self.pdfTableStyle.append(('SPAN', (0,i), (1,i)))
        self.newline(ue_type=ue_type)

    def evalline(self, ue_type=None): # ligne decrivant evaluation
        self.newline(ue_type=ue_type)
    
    def sessionline(self):
        self.newline()
        i = self.tabline
        self.pdfTableStyle.append(('LINEABOVE', (0,i), (-1,i), 1, Color(0.,0.,0.)))

def bulletin_pdf_table_classic_2011(context, I, version='long'):
    """Génère la table centrale du bulletin de notes
    Renvoie un triplet:
    - table (liste de listes de chaines de caracteres)
    - style (commandes table Platypus)
    - largeurs de colonnes
    """
    S = BulTableStyle()
    P = [] # elems pour gen. pdf (liste de dicts)
    formsemestre_id = I['formsemestre_id']
    sem = context.get_formsemestre(formsemestre_id)
    prefs = context.get_preferences(formsemestre_id)

    # Colonnes à afficher:
    with_col_abs = prefs['bul_show_abs_modules']
    with_col_minmax = prefs['bul_show_minmax'] or prefs['bul_show_minmax_mod']
    with_col_rang = prefs['bul_show_rangs']
    
    colkeys = ['titre', 'module' ] # noms des colonnes à afficher
    if with_col_rang:
        colkeys += ['rang']
    if with_col_minmax:
        colkeys += ['min', 'max']
    colkeys += ['note', 'coef']
    if with_col_abs:
        colkeys += ['abs']
    colidx = {}  # { nom_colonne : indice à partir de 0 } (pour styles platypus)
    i = 0
    for k in colkeys:
        colidx[k] = i
        i += 1

    colWidths = { 'titre' : None, 'module' : None, # 6*cm,
                  'min' : 1.5*cm, 'max' : 1.5*cm, 'rang' : 2.2*cm,
                  'note' : 2*cm,
                  'coef' : 1.5*cm, 'abs' : 1.5*cm }
    
    # 1er ligne titres
    t = { 'min': 'Promotion', 'max' : '', 'rang' : 'Rang',
          'note' : 'Note/20', 'coef' : 'Coef.',
          'abs' : 'Abs.' }
    P.append(bold_paras(t))
    if with_col_minmax:
        S.pdfTableStyle.append(('SPAN', (colidx['min'],S.tabline), (colidx['min']+1,S.tabline)))
    S.newline()
    # 2eme ligne titres si nécessaire
    if  with_col_minmax or with_col_abs:
        t = { 'min': 'mini', 'max' : 'maxi', 'abs' : '(J. / N.J.)' }
        P.append(bold_paras(t))
        S.newline()
    S.pdfTableStyle.append(('LINEABOVE', (0,S.tabline), (-1,S.tabline), S.LINEWIDTH, S.LINECOLOR))

    # Moyenne générale
    nbabs = I['nbabs']
    nbabsjust = I['nbabsjust']
    t = { 'titre' : 'Moyenne générale:',
          'rang' : I['rang_nt'],
          'note' : I['moy_gen'],
          'abs' : '%s / %s' % (nbabs, nbabsjust) }
    S.pdfTableStyle.append(('SPAN', (colidx['titre'],S.tabline), (colidx['module'],S.tabline)))
    P.append(bold_paras(t))
    S.sessionline()

    # Chaque UE
    for ue in I['ues']:
        ue_type = None 
        coef_ue  = ue['coef_ue_txt']        
        ue_descr = ue['ue_descr_txt']
        if ue['ue_status']['is_capitalized']:
            t = { 'titre' : ue['acronyme'],
                  'module' : ue_descr,
                  'note' : ue['moy_ue_txt'],
                  'coef' : coef_ue,
                  }
            P.append(bold_paras(t))
            S.ueline()
            if prefs['bul_show_ue_cap_details']:
                _list_modules(ue['modules_capitalized'], ue_type=ue_type, version=version, S=S, P=P, context=context, prefs=prefs)
            ue_descr = '(en cours, non prise en compte)'
            ue_type = 'cur'
        
        t = { 'titre' : ue['acronyme'],
              'module' : ue_descr,
              'note' : ue['cur_moy_ue_txt'],
              'coef' : coef_ue }
        if prefs['bul_show_minmax']:
            t['min'] = fmt_note(ue['min'])
            t['max'] = fmt_note(ue['max'])
        P.append(bold_paras(t))
        S.ueline()
        _list_modules(ue['modules'], ue_type=ue_type, version=version, S=S, P=P, context=context, prefs=prefs)
    
    #
    return colkeys, P, S.get_style(), colWidths


def _list_modules(ue_modules, ue_type=None, version='', S=None, P=None, context=None, prefs=None):
    """Liste dans la table les descriptions des modules et, si version != short, des évaluations.
    """
    for mod in ue_modules:
        if mod['mod_moy_txt'] == 'NI':
            continue # saute les modules où on n'est pas inscrit
        t = { 'titre' : mod['code'] + ' ' + mod['name'],
              'rang' : mod['mod_rang_txt'], # vide si pas option rang
              'note' : mod['mod_moy_txt'],
              'coef' : mod['mod_coef_txt'],
              'abs' : mod.get('mod_abs_txt', ''), # absent si pas option show abs module
              }
        if prefs['bul_show_minmax_mod']:
            t['min'] = fmt_note(mod['stats']['min'])
            t['max'] = fmt_note(mod['stats']['max'])
        
        P.append(t)
        S.modline(ue_type=ue_type)
        if version != 'short':
            # --- notes de chaque eval:
            nbeval = 0
            for e in mod['evaluations']:
                if e['visibulletin'] == '1' or version == 'long':
                    t = { 'module' : '<bullet indent="2.5mm">&bull;</bullet>' + e['name'],
                          'note' : '<i>'+e['note_txt']+'</i>',
                          'coef' : '<i>'+e['coef_txt']+'</i>' }
                    P.append(t)
                    S.evalline(ue_type=ue_type)
                    nbeval += 1
            if nbeval:
                S.pdfTableStyle.append(('BOX', (1,S.tabline-nbeval),
                                        (-1, S.tabline-1), 0.2, Color(0.75,0.75,0.75)))



