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

Format table "UCAC"

(ceci est un essai)

"""
from sco_pdf import *
import sco_preferences
import traceback
from notes_log import log
import sco_bulletins_pdf
import sco_bulletins_pdf_default

class PDFBulletinGeneratorUCAC(sco_bulletins_pdf_default.PDFBulletinGeneratorDefault):
    description = 'bulletins style "UCAC" (beta)'  # la description doit être courte: elle apparait dans le menu de paramètrage ScoDoc
    
    def gen_table(self):
        """Génère la tabe centrale du bulletin de notes
        Renvoie une liste d'objets PLATYPUS (eg instance de Table).
        """
        P, pdfTableStyle, colWidths = bulletin_pdf_table_ucac(self.context, self.infos, version=self.version)
        return [ self.buildTableObject(P, pdfTableStyle, colWidths) ]
    
sco_bulletins_pdf.register_pdf_bulletin_class(PDFBulletinGeneratorUCAC)


class BulTableStyleUCAC:
    """Construction du style de tables reportlab platypus pour les bulletins "classiques"
    """
    LINEWIDTH = 1.25
    LINECOLOR = Color(0.,0,0)
    TITLEBGCOLOR = Color(170/255.,187/255.,204/255.) # couleur fond lignes titres UE
    
    def __init__(self):
        self.pdfTableStyle = [ ('FONTNAME', (0,0), (-1,0), 'Helvetica-Bold'),
                               ('VALIGN',  (0,0), (-1,-1), 'MIDDLE'),
                               ('ALIGN',  (0,0), (-1,-1), 'CENTER'),
                               ('INNERGRID', (0,0), (-1,-1), self.LINEWIDTH, self.LINECOLOR), # grille interne
                               ('BOX', (0,0), (-1,-1), self.LINEWIDTH, self.LINECOLOR), # bordure extérieure
                               ('BACKGROUND', (0,0), (-1,0),self.TITLEBGCOLOR ), # couleur fond ligne titre
                               ('FONTNAME', (0,0), (-1,0), 'Helvetica-Bold'), # titres en gras
                               ]
        self.tabline = 0

    def get_style(self):
        "get resulting style (a list of platypus table commands)"
        return self.pdfTableStyle
    
    def newline(self, ue_type=None):
        self.tabline += 1
        if ue_type == 'cur': # UE courante non prise en compte (car capitalisee)
            self.pdfTableStyle.append(('BACKGROUND', (0,self.tabline), (-1,self.tabline),
                                       Color(210/255.,210/255.,210/255.) ))

    def ueline(self, nb_modules=1, ue_descr=None): # met la ligne courante du tableau pdf en style 'UE'
        i = self.tabline
        if ue_descr:
            self.pdfTableStyle.append(('SPAN', (2,i), (6,i)))
            self.newline()
        if nb_modules > 1:
            self.pdfTableStyle.append(('SPAN', (0,i), (0,i+nb_modules-1)))
            self.pdfTableStyle.append(('SPAN', (1,i), (1,i+nb_modules-1)))
            self.pdfTableStyle.append(('SPAN', (4,i), (4,i+nb_modules-1)))
            self.pdfTableStyle.append(('SPAN', (5,i), (5,i+nb_modules-1)))
            self.pdfTableStyle.append(('SPAN', (6,i), (6,i+nb_modules-1)))
        self.newline()
    
    def modline(self, ue_type=None): # met la ligne courante du tableau pdf en style 'Module'
        self.newline(ue_type=ue_type)
        i = self.tabline

def bulletin_pdf_table_ucac(context, I, version=None):
    """Génère la table centrale du bulletin de notes

    La version n'est ici pas utilisée (on ne montre jamais les notes des évaluations).
    
    """    
    S = BulTableStyleUCAC()
    P = [] # elems pour gen. pdf
    formsemestre_id = I['formsemestre_id']
    sem = context.get_formsemestre(formsemestre_id)
    bul_show_abs_modules = context.get_preference('bul_show_abs_modules', formsemestre_id)    

    if context.get_preference('bul_show_minmax', formsemestre_id):
        minmax = ' <font size="8">[%s, %s]</font>' % (I['moy_min'], I['moy_max'])
    else:
        minmax = ''

    t = [ "Code UE", "Unités d'enseignement", "Modules", "Notes /20", "Moyenne UE/20", "Coef.", "Total"]
    if bul_show_abs_modules:
        t.append( 'Abs (J. / N.J.)')
    P.append(t)
    S.newline()

    def list_modules(ue_modules, ue_type=None):
        "ajoute les lignes decrivant les modules d'une UE"
        for mod in ue_modules:
            if mod['mod_moy_txt'] == 'NI':
                continue # saute les modules où on n'est pas inscrit
            S.modline(ue_type=ue_type)
            if context.get_preference('bul_show_minmax_mod', formsemestre_id):
                rang_minmax = '%s <font size="8">[%s, %s]</font>' % (mod['mod_rang_txt'], fmt_note(mod['stats']['min']), fmt_note(mod['stats']['max']))
            else:
                rang_minmax = mod['mod_rang_txt'] # vide si pas option rang
            t = ['', '', mod['name'], mod['mod_moy_txt'], '', '', '']
            if bul_show_abs_modules:
                t.append(mod['mod_abs_txt'])
            P.append(t)

    def list_ue( ue, ue_descr ):
        if context.get_preference('bul_show_minmax', formsemestre_id):
            moy_txt = '%s <font size="8">[%s, %s]</font>' % (ue['cur_moy_ue_txt'], ue['min'], ue['max'])
        else:
            moy_txt = ue['cur_moy_ue_txt']
        if ue['modules']:
            firstmod = ue['modules'][0]
        else:
            firstmod = DictDefault(defaultvalue='')
        #log("ue['ue_status']['cur_moy_ue'] = %s" % ue['ue_status']['cur_moy_ue'] )
        #log("ue['ue_status']['coef_ue'] = %s" % ue['ue_status']['coef_ue'] )
        try:
            total_pt_ue = fmt_note(ue['ue_status']['cur_moy_ue'] * ue['ue_status']['coef_ue'])
            # log('total_pt_ue = %s' % total_pt_ue)
        except:
            #log("ue['ue_status']['cur_moy_ue'] = %s" % ue['ue_status']['cur_moy_ue'] )
            #log("ue['ue_status']['coef_ue'] = %s" % ue['ue_status']['coef_ue'] )
            total_pt_ue = ''
        
        t = [ ue['acronyme'], '%s (%s)' % (ue['titre'], ue_descr or ''),
              firstmod['name'], firstmod['mod_moy_txt'],
              moy_txt, # moyenne de l'UE
              coef_ue, # Attention: on affiche le coefficient de l'UE, et non le total des crédits
              total_pt_ue, # points (et non crédits)
              ]
        if bul_show_abs_modules:
            t.append('')
        P.append(t)
    
    for ue in I['ues']:
        #log('** ue %s' % ue['titre'])
        ue_descr = ue['ue_descr_txt']
        coef_ue  = ue['coef_ue_txt']
        ue_type = None
        # --- UE capitalisée:
        if ue['ue_status']['is_capitalized']:            
            P.append(t)
            list_ue( ue, ue_descr )
            coef_ue = ''
            ue_descr = '(en cours, non prise en compte)'
            if context.get_preference('bul_show_ue_cap_details', formsemestre_id):
                S.ueline(nb_modules=len(ue['modules_capitalized']), ue_descr=ue_descr)
                list_modules(ue['modules_capitalized'], ue_descr=ue_descr)
            else:
                S.ueline(nb_modules=1)
            ue_type = 'cur'
        
        if context.get_preference('bul_show_minmax', formsemestre_id):
            moy_txt = '%s <font size="8">[%s, %s]</font>' % (ue['cur_moy_ue_txt'], ue['min'], ue['max'])
        else:
            moy_txt = ue['cur_moy_ue_txt']
        # --- UE ordinaire
        list_ue( ue, ue_descr )
        S.ueline(nb_modules=len(ue['modules']))
        #log('ueline(%s)' % len(ue['modules']))
        if len(ue['modules']) > 1: # liste les autres modules
            list_modules(ue['modules'][1:], ue_type=ue_type)

    # Largeur colonnes:
    colWidths = [20*mm, 40*mm, 42*mm, 22*mm, 22*mm, 22*mm, 22*mm ]
    #    if len(P[0]) > 5:
    #    colWidths.append( 1.5*cm ) # absences/modules
    #log('tabline=%s' % S.tabline)
    #log('len(P) = %s' % len(P) )
    #log( 'lens P=%s' % [ len(x) for x in P ] )
    #log('style=\n%s' % pprint.pformat( S.get_style() ))
    #log('P=\n%s' % pprint.pformat(P))
    return P, S.get_style(), colWidths


