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

# Important: Le nom de la classe ne doit pas changer (bien le choisir), car il sera stocké en base de données (dans les préférences)
class PDFBulletinGeneratorDefault(sco_bulletins_pdf.PDFBulletinGenerator):
    description = 'standard ScoDoc'  # la description doit être courte: elle apparait dans le menu de paramètrage ScoDoc

    def gen_part_title(self):
        """Génère la partie "titre" du bulletin de notes.
        Renvoie une liste d'objets platypus
        """
        objects = sco_bulletins_pdf.process_field(self.context, self.preferences['bul_pdf_title'], self.infos, self.FieldStyle)
        objects.append(Spacer(1, 5*mm)) # impose un espace vertical entre le titre et la table qui suit
        return objects
    
    def gen_table(self):
        """Génère la tabe centrale du bulletin de notes
        Renvoie une liste d'objets PLATYPUS (eg instance de Table).
        """
        P, pdfTableStyle, colWidths = bulletin_pdf_table_classic(self.context, self.infos, version=self.version)
        return [ self.buildTableObject(P, pdfTableStyle, colWidths) ]
    
    def gen_part_below(self):
        """Génère les informations placées sous la table de notes
        (absences, appréciations, décisions de jury...)
        Renvoie une liste d'objets platypus
        """
        objects = []
        
        # ----- ABSENCES
        if self.preferences['bul_show_abs']:
            nbabs = self.infos['nbabs']
            nbabsjust = self.infos['nbabsjust']
            objects.append( Spacer(1, 2*mm) )
            if nbabs:
                objects.append( Paragraph(
                    SU("%d absences (1/2 journées), dont %d justifiées." % (nbabs, nbabsjust)), self.CellStyle ) )
            else:
                objects.append( Paragraph(SU("Pas d'absences signalées."), self.CellStyle) )
        
        # ----- APPRECIATIONS
        if self.infos.get('appreciations_list', False):
            objects.append( Spacer(1, 3*mm) )
            objects.append( Paragraph(SU('Appréciation : ' + '\n'.join(self.infos['appreciations_txt'])), self.CellStyle) )
        
        # ----- DECISION JURY
        if self.preferences['bul_show_decision']:
            objects += sco_bulletins_pdf.process_field(
                self.context, self.preferences['bul_pdf_caption'], self.infos, self.FieldStyle)

        return objects
        
    def gen_signatures(self):
        """Génère les signatures placées en bas du bulletin
        Renvoie une liste d'objets platypus
        """
        show_left = self.preferences['bul_show_sig_left']
        show_right = self.preferences['bul_show_sig_right']
        if show_left or show_right:
            if show_left:
                L = [[sco_bulletins_pdf.process_field(self.context, self.preferences['bul_pdf_sig_left'], self.infos, self.FieldStyle)]]
            else:
                L = [['']]
            if show_right:
                L[0].append(sco_bulletins_pdf.process_field(self.context, self.preferences['bul_pdf_sig_right'], self.infos, self.FieldStyle))
            else:
                L[0].append('')
            t = Table(L)
            t._argW[0] = 10*cm # fixe largeur colonne gauche
            
            return [ Spacer(1, 1.5*cm), # espace vertical avant signatures
                     t ]
        else:
            return []

sco_bulletins_pdf.register_pdf_bulletin_class(PDFBulletinGeneratorDefault)


class BulTableStyle:
    """Construction du style de tables reportlab platypus pour les bulletins "classiques"
    """
    LINEWIDTH = 0.5
    LINECOLOR = Color(0,0,0)
    UEBGCOLOR = Color(170/255.,187/255.,204/255.) # couleur fond lignes titres UE
    MODSEPCOLOR=Color(170/255.,170/255.,170/255.) # lignes séparant les modules
    def __init__(self):
        self.pdfTableStyle = [ ('FONTNAME', (0,0), (-1,0), 'Helvetica-Bold'),
                               ('LINEBELOW', (0,0), (-1,0), self.LINEWIDTH, self.LINECOLOR),
                               ]
        self.tabline = 0

    def get_style(self):
        "get resulting style (a list of platypus table commands)"
        # ajoute cadre extérieur bleu:
        self.pdfTableStyle.append( ('BOX', (0,0), (-1,-1), 0.4, blue) )
        
        return self.pdfTableStyle
    
    def newline(self, ue_type=None):
        self.tabline += 1
        if ue_type == 'cur': # UE courante non prise en compte (car capitalisee)
            self.pdfTableStyle.append(('BACKGROUND', (0,self.tabline), (-1,self.tabline),
                                       Color(210/255.,210/255.,210/255.) ))

    def ueline(self): # met la ligne courante du tableau pdf en style 'UE'
        self.newline()
        i = self.tabline
        self.pdfTableStyle.append(('FONTNAME', (0,i), (-1,i), 'Helvetica-Bold'))
        self.pdfTableStyle.append(('BACKGROUND', (0,i), (-1,i),self.UEBGCOLOR ))
    
    def modline(self, ue_type=None): # met la ligne courante du tableau pdf en style 'Module'
        self.newline(ue_type=ue_type)
        i = self.tabline
        self.pdfTableStyle.append(('LINEABOVE', (0,i), (-1,i), 1, self.MODSEPCOLOR))

def bulletin_pdf_table_classic(context, I, version='long'):
    """Génère la tabe centrale du bulletin de notes
    Renvoie un triplet:
    - table (liste de listes de chaines de caracteres)
    - style (commandes table Platypus)
    - largeurs de colonnes
    """    
    S = BulTableStyle()
    P = [] # elems pour gen. pdf
    formsemestre_id = I['formsemestre_id']
    sem = context.get_formsemestre(formsemestre_id)
    bul_show_abs_modules = context.get_preference('bul_show_abs_modules', formsemestre_id)    

    if context.get_preference('bul_show_minmax', formsemestre_id):
        minmax = ' <font size="8">[%s, %s]</font>' % (I['moy_min'], I['moy_max'])
    else:
        minmax = ''

    t = ['Moyenne', '%s%s%s' % (I['moy_gen'], I['etud_etat_html'], minmax),
         I['rang_txt'], 
         'Note/20', 
         'Coef']
    if bul_show_abs_modules:
        t.append( 'Abs (J. / N.J.)')
    P.append(t)

    def list_modules(ue_modules, ue_type=None):
        "ajoute les lignes decrivant les modules d'une UE, avec eventuellement les évaluations de chacun"
        for mod in ue_modules:
            if mod['mod_moy_txt'] == 'NI':
                continue # saute les modules où on n'est pas inscrit
            S.modline(ue_type=ue_type)
            if context.get_preference('bul_show_minmax_mod', formsemestre_id):
                rang_minmax = '%s <font size="8">[%s, %s]</font>' % (mod['mod_rang_txt'], fmt_note(mod['stats']['min']), fmt_note(mod['stats']['max']))
            else:
                rang_minmax = mod['mod_rang_txt'] # vide si pas option rang
            t = [mod['code'], mod['name'], rang_minmax, mod['mod_moy_txt'], mod['mod_coef_txt']]
            if bul_show_abs_modules:
                t.append(mod['mod_abs_txt'])
            P.append(t)
            if version != 'short':
                # --- notes de chaque eval:
                for e in mod['evaluations']:
                    if e['visibulletin'] == '1' or version == 'long':
                        S.newline(ue_type=ue_type)
                        t = ['','', e['name'], e['note_txt'], e['coef_txt']]
                        if bul_show_abs_modules:
                            t.append('')
                        P.append(t)
       
    for ue in I['ues']:
        ue_descr = ue['ue_descr_txt']
        coef_ue  = ue['coef_ue_txt']
        ue_type = None
        if ue['ue_status']['is_capitalized']:
            t = [ue['acronyme'], ue['moy_ue_txt'], ue_descr, '', coef_ue]
            if bul_show_abs_modules:
                t.append('')
            P.append(t)
            coef_ue = ''
            ue_descr = '(en cours, non prise en compte)'
            S.ueline()
            if context.get_preference('bul_show_ue_cap_details', formsemestre_id):
                list_modules(ue['modules_capitalized'])
            ue_type = 'cur'
        
        if context.get_preference('bul_show_minmax', formsemestre_id):
            moy_txt = '%s <font size="8">[%s, %s]</font>' % (ue['cur_moy_ue_txt'], ue['min'], ue['max'])
        else:
            moy_txt = ue['cur_moy_ue_txt']
        t = [ue['acronyme'], moy_txt, ue_descr, '', coef_ue]
        if bul_show_abs_modules:
            t.append('')
        P.append(t)
        S.ueline()
        list_modules(ue['modules'], ue_type=ue_type)

    # Largeur colonnes:
    colWidths = [None, 5*cm, 6*cm, 2*cm, 1.2*cm]
    if len(P[0]) > 5:
        colWidths.append( 1.5*cm ) # absences/modules
        
    return P, S.get_style(), colWidths


