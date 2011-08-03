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

"""Generation du bulletin note au format standard

Nouvelle version juillet 2011: changement de la présentation de la table.




Note sur le PDF:
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
import sco_bulletins_generator
import sco_bulletins_pdf
import gen_tables

# Important: Le nom de la classe ne doit pas changer (bien le choisir), car il sera stocké en base de données (dans les préférences)
class BulletinGeneratorStandard(sco_bulletins_generator.BulletinGenerator):
    description = 'standard ScoDoc (version 2011, beta)'  # la description doit être courte: elle apparait dans le menu de paramètrage ScoDoc
    supported_formats = [ 'html', 'pdf' ]

    def bul_title_pdf(self):
        """Génère la partie "titre" du bulletin de notes.
        Renvoie une liste d'objets platypus
        """
        objects = sco_bulletins_pdf.process_field(self.context, self.preferences['bul_pdf_title'], self.infos, self.FieldStyle)
        objects.append(Spacer(1, 5*mm)) # impose un espace vertical entre le titre et la table qui suit
        return objects
    
    def bul_table(self, format='html'):
        """Génère la table centrale du bulletin de notes
        Renvoie:
        - en HTML: une chaine
        - en PDF: une liste d'objets PLATYPUS (eg instance de Table).
        """
        formsemestre_id = self.infos['formsemestre_id']
        colkeys, P, pdf_style, colWidths = self.build_bulletin_table()
        
        T = gen_tables.GenTable(
            rows = P,
            columns_ids = colkeys,
            pdf_table_style = pdf_style,
            pdf_col_widths = [ colWidths[k] for k in colkeys ],
            preferences = self.context.get_preferences(formsemestre_id),
            html_class = 'notes_bulletin',
            html_with_td_classes = True
            )
        
        return T.gen(format=format)
    
    def bul_part_below(self, format='html'):
        """Génère les informations placées sous la table de notes
        (absences, appréciations, décisions de jury...)
        Renvoie:
        - en HTML: une chaine
        - en PDF: une liste d'objets platypus
        """
        H = [] # html
        Op = [] # objets platypus
        # ----- ABSENCES
        if self.preferences['bul_show_abs']:
            nbabs = self.infos['nbabs']
            Op.append( Spacer(1, 2*mm) )
            if nbabs:
                H.append("""<p class="bul_abs">
                <a href="../Absences/CalAbs?etudid=%(etudid)s" class="bull_link">
                <b>Absences :</b> %(nbabs)s demi-journées, dont %(nbabsjust)s justifiées
                (pendant ce semestre).
                </a></p>
                """ % self.infos )
                Op.append( Paragraph(
                    SU("%(nbabs)s absences (1/2 journées), dont %(nbabsjust)s justifiées." % self.infos), self.CellStyle ) )
            else:
                H.append("""<p class="bul_abs">Pas d'absences signalées.</p>""")
                Op.append( Paragraph(SU("Pas d'absences signalées."), self.CellStyle) )
        
        # ---- APPRECIATIONS
        # le dir. des etud peut ajouter des appreciations,
        # mais aussi le chef (perm. ScoEtudInscrit)
        can_edit_app = ((str(self.authuser) == self.infos['responsable_id'])
                        or (self.authuser.has_permission(ScoEtudInscrit,self.context)))
        H.append('<div class="bull_appreciations">')
        for app in self.infos['appreciations_list']:
            if can_edit_app:
                mlink = '<a class="stdlink" href="appreciation_add_form?id=%s">modifier</a> <a class="stdlink" href="appreciation_add_form?id=%s&suppress=1">supprimer</a>'%(app['id'],app['id'])
            else:
                mlink = ''
            H.append('<p><span class="bull_appreciations_date">%s</span>%s<span class="bull_appreciations_link">%s</span></p>'
                     % (app['date'], app['comment'], mlink ) )
        if can_edit_app:
            H.append('<p><a class="stdlink" href="appreciation_add_form?etudid=%(etudid)s&formsemestre_id=%(formsemestre_id)s">Ajouter une appréciation</a></p>' % self.infos)
        H.append('</div>')
        # Appreciations sur PDF:
        if self.infos.get('appreciations_list', False):
            Op.append( Spacer(1, 3*mm) )
            Op.append( Paragraph(SU('Appréciation : ' + '\n'.join(self.infos['appreciations_txt'])), self.CellStyle) )

        # ----- DECISION JURY
        if self.preferences['bul_show_decision']:
            Op += sco_bulletins_pdf.process_field(
                self.context, self.preferences['bul_pdf_caption'], self.infos, self.FieldStyle,
                format='pdf')
            field = sco_bulletins_pdf.process_field(
                self.context, self.preferences['bul_pdf_caption'], self.infos, self.FieldStyle,
                format='html')
            H.append('<div class="bul_decision">' + field + '</div>' )
        
        # -----  
        if format == 'pdf':
            return Op
        elif format == 'html':
            return '\n'.join(H)

    def bul_signatures_pdf(self):
        """Génère les signatures placées en bas du bulletin PDF
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

    PDF_LINEWIDTH = 0.5
    PDF_LINECOLOR = Color(0,0,0)
    PDF_MODSEPCOLOR = Color(170/255.,170/255.,170/255.) # lignes séparant les modules
    PDF_UE_CUR_BG = Color(210/255.,210/255.,210/255.) # fond UE courantes non prises en compte
    PDF_LIGHT_GRAY = Color(0.75,0.75,0.75)

    PDF_COLOR_CACHE = {} # (r,g,b) : pdf Color instance
    def ue_color(self, ue_type=UE_STANDARD):
        rgb_color = UE_COLORS.get(ue_type, UE_DEFAULT_COLOR)
        color = self.PDF_COLOR_CACHE.get(rgb_color, None)
        if not color:
            color = Color( *rgb_color )
            self.PDF_COLOR_CACHE[rgb_color] = color
        return color

    def ue_color_rgb(self, ue_type=UE_STANDARD):
        rgb_color = UE_COLORS.get(ue_type, UE_DEFAULT_COLOR)
        return "rgb(%d,%d,%d);" % (rgb_color[0]*255,rgb_color[1]*255,rgb_color[2]*255)


    def build_bulletin_table(self):
        """Génère la table centrale du bulletin de notes
        Renvoie: colkeys, P, pdf_style, colWidths
        - colkeys: nom des colonnes de la table (clés)
        - table (liste de dicts de chaines de caracteres)
        - style (commandes table Platypus)
        - largeurs de colonnes pour PDF
        """
        I = self.infos
        context = self.context
        P = [] # elems pour générer table avec gen_table (liste de dicts)
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
                      'coef' : 1.5*cm, 'abs' : 2.0*cm }
        # HTML specific
        linktmpl  = '<span onclick="toggle_vis_ue(this);" class="toggle_ue">%s</span>&nbsp;'
        minuslink = linktmpl % context.icons.minus_img.tag(border="0", alt="-")
        pluslink  = linktmpl % context.icons.plus_img.tag(border="0", alt="+")

        # 1er ligne titres
        t = { 'min': 'Promotion', 'max' : '', 'rang' : 'Rang',
              'note' : 'Note/20', 'coef' : 'Coef.',
              'abs' : 'Abs.',
              '_min_colspan' : 2,
              '_css_row_class' : 'note_bold',
              '_pdf_row_markup' : ['b'],
              '_pdf_style' : [],
              }
        if with_col_minmax:
            t['_pdf_style'].append(('SPAN', (colidx['min'],0), (colidx['min']+1,0)))
        P.append(t)
        # 2eme ligne titres si nécessaire
        if  with_col_minmax or with_col_abs:
            t = { 'min': 'mini', 'max' : 'maxi', 'abs' : '(J. / N.J.)',
                  '_css_row_class' : 'note_bold', '_pdf_row_markup' : ['b'], '_pdf_style' : [] }
            P.append(t)
        P[-1]['_pdf_style'].append(('LINEBELOW', (0,0), (-1,0), self.PDF_LINEWIDTH, self.PDF_LINECOLOR))

        # Moyenne générale
        nbabs = I['nbabs']
        nbabsjust = I['nbabsjust']
        t = { 'titre' : 'Moyenne générale:',
              'rang' : I['rang_nt'],
              'note' : I['moy_gen'],
              'min' : I['moy_min'],
              'max' : I['moy_max'],
              'abs' : '%s / %s' % (nbabs, nbabsjust),
              '_css_row_class' : 'notes_bulletin_row_gen',
              '_pdf_row_markup' : ['font size="12"', 'b'], # bold, size 12
              '_pdf_style' : [ ('SPAN', (colidx['titre'],0), (colidx['module'],0)),
                               ('LINEABOVE', (0,1), (-1,1), 1, self.PDF_LINECOLOR)
                                ]
              }
        P.append(t)

        # Chaque UE
        for ue in I['ues']:
            ue_type = None 
            coef_ue  = ue['coef_ue_txt']        
            ue_descr = ue['ue_descr_txt']
            rowstyle = ''
            plusminus = minuslink # 
            if ue['ue_status']['is_capitalized']:
                # UE capitalisée meilleure que UE courante:
                if prefs['bul_show_ue_cap_details']:
                    hidden = False
                    cssstyle = ''
                    plusminus = minuslink
                else:
                    hidden = True
                    cssstyle = 'sco_hide'
                    plusminus = pluslink

                t = { 'titre' : ue['acronyme'],
                      '_titre_html' : plusminus + ue['acronyme'],
                      'module' : ue_descr,
                      'note' : ue['moy_ue_txt'],
                      'coef' : coef_ue,
                      '_css_row_class' : 'notes_bulletin_row_ue',
                      '_tr_attrs' : 'style="background-color: %s"' % self.ue_color_rgb(),
                      '_pdf_row_markup' : ['b'],
                      '_pdf_style' : [ ('BACKGROUND', (0,0), (-1,0), self.ue_color() ),
                                       ('LINEABOVE', (0,0), (-1,0), 1, self.PDF_LINECOLOR) ]
                      }
                P.append(t)
                # Notes de l'UE capitalisée obtenues antérieurement:            
                self._list_modules(ue['modules_capitalized'], ue_type=ue_type, P=P, prefs=prefs,
                                   rowstyle=' bul_row_ue_cap %s' % cssstyle, hidden=hidden
                                   )
                ue_type = 'cur'
                ue_descr = ''
                rowstyle=' bul_row_ue_cur' # style css pour indiquer UE non prise en compte

            t = { 'titre' : ue['acronyme'],
                  '_titre_html' : minuslink + ue['acronyme'],
                  'rang' : ue_descr,
                  'note' : ue['cur_moy_ue_txt'],
                  'coef' : coef_ue,
                  '_css_row_class' : 'notes_bulletin_row_ue',
                  '_tr_attrs' : 'style="background-color: %s"' % self.ue_color_rgb(ue_type=ue['type']),
                  '_pdf_row_markup' : ['b'],
                  '_pdf_style' : [ ('BACKGROUND', (0,0), (-1,0), self.ue_color(ue_type=ue['type']) ),
                                   ('LINEABOVE', (0,0), (-1,0), 1, self.PDF_LINECOLOR)               
                                   ]
                  }
            if ue_type == 'cur':
                t['module'] = '(en cours, non prise en compte)'
                t['_css_row_class'] += ' notes_bulletin_row_ue_cur'
            if prefs['bul_show_minmax']:
                t['min'] = fmt_note(ue['min'])
                t['max'] = fmt_note(ue['max'])
            # Cas particulier des UE sport (bonus)
            if ue['type'] == UE_SPORT and not ue_descr:
                t['module'] = '%s: <i>%s</i>' % (ue['titre'], ue['cur_moy_ue_txt'])
                del t['note']
                del t['coef']
                t['_pdf_style'].append(('SPAN', (colidx['module'],0), (-1,0)))
                t['_module_colspan'] = 3
            P.append(t)
            self._list_modules(ue['modules'], ue_type=ue_type, P=P, prefs=prefs, rowstyle=rowstyle)

        # Global pdf style comands:
        pdf_style = [
            ('VALIGN', (0,0), (-1,-1), 'TOP'),
            ('BOX', (0,0), (-1,-1), 0.4, blue), # ajoute cadre extérieur bleu:
            ]
        #
        return colkeys, P, pdf_style, colWidths
    
    
    def _list_modules(self, ue_modules, ue_type=None, P=None, prefs=None,
                      rowstyle='', hidden=False):
        """Liste dans la table les descriptions des modules et, si version != short, des évaluations.
        """
        if ue_type == 'cur':  # UE courante non prise en compte (car capitalisee)
            pdf_style_bg = [('BACKGROUND', (0,0), (-1,0), self.PDF_UE_CUR_BG)]
        else:
            pdf_style_bg = []
        pdf_style = pdf_style_bg + [
            ('LINEABOVE', (0,0), (-1,0), 1, self.PDF_MODSEPCOLOR),
            ('SPAN', (0,0), (1,0))
            ]
        if ue_type == 'cur':  # UE courante non prise en compte (car capitalisee)
            pdf_style.append(('BACKGROUND', (0,0), (-1,0), self.PDF_UE_CUR_BG))

        for mod in ue_modules:
            if mod['mod_moy_txt'] == 'NI':
                continue # saute les modules où on n'est pas inscrit
            t = { 'titre' : mod['code_txt'] + ' ' + mod['name'],
                  '_titre_colspan' : 2,
                  'rang' : mod['mod_rang_txt'], # vide si pas option rang
                  'note' : mod['mod_moy_txt'],
                  'coef' : mod['mod_coef_txt'],
                  'abs' : mod.get('mod_abs_txt', ''), # absent si pas option show abs module
                  '_css_row_class' : 'notes_bulletin_row_mod%s' % rowstyle,
                  '_titre_target' : 'moduleimpl_status?moduleimpl_id=%s' % mod['moduleimpl_id'],
                  '_titre_help' : mod['mod_descr_txt'],
                  '_hidden' : hidden,
                  '_pdf_style' : pdf_style
                  }
            if prefs['bul_show_minmax_mod']:
                t['min'] = fmt_note(mod['stats']['min'])
                t['max'] = fmt_note(mod['stats']['max'])

            P.append(t)

            if self.version != 'short':           
                # --- notes de chaque eval:
                nbeval = 0
                for e in mod['evaluations']:
                    if e['visibulletin'] == '1' or self.version == 'long':
                        if nbeval == 0:
                            eval_style = ' b_eval_first'
                        else:
                            eval_style = ''
                        t = { 'module' : '<bullet indent="2mm">&bull;</bullet>&nbsp;' + e['name'],
                              'note' : '<i>'+e['note_txt']+'</i>',
                              'coef' : '<i>'+e['coef_txt']+'</i>',
                              '_hidden' : hidden,
                              '_module_target' : e['target_html'],
                              # '_module_help' : ,
                              '_css_row_class' : 'notes_bulletin_row_eval' + eval_style + rowstyle,
                              '_pdf_style' : pdf_style_bg[:] }
                        P.append(t)
                        nbeval += 1
                if nbeval: # boite autour des evaluations (en pdf)
                    P[-1]['_pdf_style'].append(('BOX', (1,1-nbeval), (-1, 0), 0.2, self.PDF_LIGHT_GRAY))



sco_bulletins_generator.register_bulletin_class(BulletinGeneratorStandard)




