# -*- mode: python -*-
# -*- coding: iso8859-15 -*-

##############################################################################
#
# Gestion scolarite IUT
#
# Copyright (c) 2001 - 2006 Emmanuel Viennet.  All rights reserved.
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


""" Excel file handling
"""

from pyExcelerator import *

from notes_log import log
from scolog import logdb
from sco_exceptions import *
from sco_utils import SCO_ENCODING, XLS_MIMETYPE, unescape_html, suppress_accents
import notesdb

import time
from types import StringType, IntType, FloatType, LongType

COLOR_CODES = { 'black' : 0,
                'red' : 0x0A,
                'mauve' : 0x19,
                'marron' : 0x3c,
                'blue' : 0x4,
                'orange' : 0x34
                }


def sendExcelFile(REQUEST,data,filename):
    """publication fichier.
    (on ne doit rien avoir émis avant, car ici sont générés les entetes)
    """
    filename = unescape_html(suppress_accents(filename)).replace('&','').replace(' ','_')
    REQUEST.RESPONSE.setHeader('Content-type', XLS_MIMETYPE)
    REQUEST.RESPONSE.setHeader('Content-Disposition', 'attachment; filename=%s' % filename)
    return data


# Sous-classes pour ajouter methode savetostr()
# (generation de fichiers en memoire)
# XXX ne marche pas car accès a methodes privees (__xxx)
# -> on utilise version modifiee par nous meme de pyExcelerator
#
# class XlsDocWithSave(CompoundDoc.XlsDoc):
#     def savetostr(self, stream):
#         #added by Emmanuel: save method, but returns a string
#         # 1. Align stream on 0x1000 boundary (and therefore on sector boundary)
#         padding = '\x00' * (0x1000 - (len(stream) % 0x1000))
#         self.book_stream_len = len(stream) + len(padding)
        
#         self.__build_directory()
#         self.__build_sat()
#         self.__build_header()
        
#         return self.header+self.packed_MSAT_1st+stream+padding+self.packed_MSAT_2nd+self.packed_SAT+self.dir_stream

# class WorkbookWithSave(Workbook):
#     def savetostr(self):
#         doc = XlsDocWithSave()
#         return doc.savetostr(self.get_biff_data())

# ------ Export simple type 'CSV': 1ere ligne en gras, le reste tel quel
def Excel_SimpleTable( titles=[], lines=[[]],                       
                       SheetName='feuille',
                       titlesStyles=[]
                       ):
    
    UnicodeUtils.DEFAULT_ENCODING = SCO_ENCODING
    wb = Workbook()
    ws0 = wb.add_sheet(SheetName)
    if not titlesStyles:
        style = Excel_MakeStyle( bold=True )
        titlesStyles = [style]*len(titles)
    # ligne de titres
    col = 0
    for it in titles:
        ws0.write(0, col, it, titlesStyles[col])
        col += 1
    # suite
    style = Excel_MakeStyle()
    li = 1
    for l in lines:
        col = 0
        for it in l:
            # safety net: allow only str, int and float
            if type(it) == LongType:
                it = int(it) # assume all ScoDoc longs fits in int !
            elif type(it) not in (StringType, IntType, FloatType):
                it = str(it)
            ws0.write(li, col, it, style)
            col += 1
        li += 1
    #
    return wb.savetostr()

def Excel_MakeStyle( bold=False, color='black' ):
    style = XFStyle()
    font = Font()
    font.bold = bold
    font.name = 'Arial'                    
    colour_index = COLOR_CODES.get(color, None)    
    if colour_index:
        font.colour_index = colour_index
    style.font = font
    return style

def Excel_feuille_saisie( E, description, lines ):
    """Genere feuille excel pour saisie des notes.
    E: evaluation (dict)
    lines: liste de tuples
               (etudid, nom, prenom, etat, groupe, val, explanation)
    """
    UnicodeUtils.DEFAULT_ENCODING = SCO_ENCODING
    SheetName = 'Saisie notes'
    wb = Workbook()
    ws0 = wb.add_sheet(SheetName)
    # ajuste largeurs colonnes (unite inconnue, empirique)
    ws0.col(0).width = 3000 # codes
    ws0.col(1).width = 6000 # noms
    ws0.col(3).width = 1800 # groupes
    ws0.col(5).width = 13000 # remarques
    # styles
    style_titres = XFStyle()
    font0 = Font()
    font0.bold = True
    font0.name = 'Arial'
    font0.bold = True
    font0.height = 14*0x14
    style_titres.font = font0

    style_expl = XFStyle()
    font_expl = Font()
    font_expl.name = 'Arial'
    font_expl.italic = True
    font0.height = 12*0x14
    font_expl.colour_index = 0x0A # rouge, voir exemple format.py
    style_expl.font = font_expl

    topborders = Borders()
    topborders.top = 1
    topleftborders = Borders()
    topleftborders.top = 1
    topleftborders.left = 1
    rightborder = Borders()
    rightborder.right = 1
    
    style_ro = XFStyle() # cells read-only
    font_ro = Font()
    font_ro.name = 'Arial'
    font_ro.colour_index = 0x19 # mauve, voir exemple format.py
    style_ro.font = font_ro
    style_ro.borders = rightborder

    style_dem = XFStyle() # cells read-only
    font_dem = Font()
    font_dem.name = 'Arial'
    font_dem.colour_index = 0x3c # marron
    style_dem.font = font_dem
    style_dem.borders = topleftborders
    
    style = XFStyle()
    font1 = Font()
    font1.name = 'Arial'
    font1.height = 12*0x14
    style.font = font1

    style_nom = XFStyle() # style pour nom, prenom, groupe
    style_nom.font = font1
    style_nom.borders = topborders
    
    style_notes = XFStyle()
    font2 = Font()
    font2.name = 'Arial'
    font2.bold = True
    style_notes.font = font2
    style_notes.num_format_str = 'general'
    style_notes.pattern = Pattern() # fond jaune
    style_notes.pattern.pattern = Pattern.SOLID_PATTERN    
    style_notes.pattern.pattern_fore_colour = 0x2b # jaune clair
    style_notes.borders = topborders
    
    # ligne de titres
    li = 0
    ws0.write(li,0, "Feuille saisie note (à enregistrer au format excel)",
              style_titres)
    li += 1
    ws0.write(li,0, "Saisir les notes dans la colonne E (cases jaunes)", style_expl)
    li += 1
    ws0.write(li,0, "Ne pas modifier les cases en mauve !",style_expl)
    li += 1
    # description evaluation    
    ws0.write(li,0, unescape_html(description), style_titres)
    li += 1
    ws0.write(li,0, 'Evaluation du %s (coef. %g)' % (E['jour'],E['coefficient']),
              style )
    li += 1
    # code et titres colonnes
    ws0.write(li,0, '!%s' % E['evaluation_id'], style_ro )
    ws0.write(li,1, 'Nom', style_titres )
    ws0.write(li,2, 'Prénom', style_titres )
    ws0.write(li,3, 'Groupe', style_titres )
    ws0.write(li,4, 'Note sur %g'%E['note_max'], style_titres )
    ws0.write(li,5, 'Remarque', style_titres )
    # etudiants
    for line in lines:
        li += 1
        st = style_nom
        ws0.write(li,0, '!'+line[0], style_ro ) # code
        if line[3] != 'I':
            st = style_dem
            if line[3] == 'D': # demissionnaire
                s = 'DEM'
            else:
                s = line[3] # etat autre
        else:
            s = line[4] # groupes TD/TP/...
        ws0.write(li,1, line[1], st )
        ws0.write(li,2, line[2], st )
        ws0.write(li,3, s, st )
        try:
            val = float(line[5])
        except:
            val = line[5]
        ws0.write(li,4, val, style_notes ) # note
        ws0.write(li,5, line[6], st ) # comment
    # explication en bas
    li+=2
    ws0.write(li, 1, "Code notes", style_titres )
    ws0.write(li+1, 1, "ABS", style_expl )
    ws0.write(li+1, 2, "absent (0)", style_expl )
    ws0.write(li+2, 1, "EXC", style_expl )
    ws0.write(li+2, 2, "pas prise en compte", style_expl )
    ws0.write(li+3, 1, "ATT", style_expl )
    ws0.write(li+3, 2, "en attente", style_expl )
    ws0.write(li+4, 1, "SUPR", style_expl )
    ws0.write(li+4, 2, "pour supprimer note déjà entrée", style_expl )
    ws0.write(li+5, 1, "", style_expl )
    ws0.write(li+5, 2, "cellule vide -> note non modifiée", style_expl )
    return wb.savetostr()


def Excel_to_list( data ): # we may need 'encoding' argument ?
    try:
        P = parse_xls('', SCO_ENCODING, doc=data )
    except:
        log('Excel_to_list: failure to import document')
        open('/tmp/last_scodoc_import_failure.xls', 'w').write(data)
        raise ScoValueError("Fichier illisible: assurez-vous qu'il s'agit bien d'un document Excel !")
    
    diag = [] # liste de chaines pour former message d'erreur
    # n'utilise que la première feuille
    if len(P) < 1:
        diag.append('Aucune feuille trouvée dans le classeur !')
        return diag, None
    if len(P) > 1:
        diag.append('Attention: n\'utilise que la première feuille du classeur !')
    # fill matrix 
    sheet_name, values = P[0]
    sheet_name = sheet_name.encode(SCO_ENCODING, 'backslashreplace')
    # diag.append(str(values))
    indexes = values.keys()
    # search numbers of rows and cols
    rows = [ x[0] for x in values.keys() ]
    cols = [ x[1] for x in values.keys() ]
    nbcols = max(cols) + 1
    nbrows = max(rows) + 1
    M = []
    for i in range(nbrows):
        M.append( [''] * nbcols )
    
    for row_idx, col_idx in indexes:
        v = values[(row_idx, col_idx)]
        if isinstance(v, unicode):
            v = v.encode(SCO_ENCODING, 'backslashreplace')
        else:
            v = str(v)
        M[row_idx][col_idx] = v
    diag.append('Feuille "%s", %d lignes' %
                (sheet_name,len(M)))
    #diag.append(str(M))
    #
    return diag, M

#
def Excel_feuille_listeappel(context, sem, groupname, lines,
                             groups_excel=[], # types de groupes a montrer
                             with_codes=False, # indique codes etuds
                             server_name=None ):
    "generation feuille appel"
    SheetName = 'Liste ' + groupname
    wb = Workbook()
    ws0 = wb.add_sheet(SheetName)
    
    font1 = Font()
    font1.name = 'Arial'
    font1.height = 10*0x14

    font1i = Font()
    font1i.name = 'Arial'
    font1i.height = 10*0x14
    font1i.italic = True
    
    style1i = XFStyle()
    style1i.font = font1i
    
    style1b = XFStyle()
    style1b.font = font1
    borders = Borders()
    borders.left = 1
    borders.top = 1
    borders.bottom = 1
    style1b.borders = borders
    
    style2 = XFStyle()
    font2 = Font()
    font2.name = 'Arial'
    font2.height = 14*0x14
    style2.font = font2
    
    style2b = XFStyle()
    style2b.font = font1i
    borders = Borders()
    borders.left = 1
    borders.top = 1
    borders.bottom = 1
    borders.right = 1
    style2b.borders = borders

    style2tb = XFStyle()
    borders = Borders()
    borders.top = 1
    borders.bottom = 1
    style2tb.borders = borders
    style2tb.font = Font()
    style2tb.font.height = 16*0x14 # -> ligne hautes

    style2t3 = XFStyle()
    borders = Borders()
    borders.top = 1
    borders.bottom = 1
    borders.left = 1
    style2t3.borders = borders

    style3 = XFStyle()
    font3 = Font()
    font3.name = 'Arial'
    font3.bold = True
    font3.height = 14*0x14
    style3.font = font3
    
    # ligne 1
    li = 0
    ws0.write(li,1, "%s %s (%s - %s)"
              % (context.get_preference('DeptName'), notesdb.unquote(sem['titre_num']),
                 sem['date_debut'],sem['date_fin']), style2)
    # ligne 2
    li += 1
    ws0.write(li,1, "Discipline :", style2)
    # ligne 3
    li += 1
    ws0.write(li,1, "Enseignant :", style2)
    ws0.write(li,5, "Groupe %s" % groupname, style3)
    # Avertissement pour ne pas confondre avec listes notes
    ws0.write(li+1,2, "Ne pas utiliser cette feuille pour saisir les notes !", style1i)
    #
    li += 2
    li += 1
    ws0.write(li,1, "Nom", style3)
    co = 2
    for groupetype in groups_excel:
        ws0.write(li,co, sem['nom'+groupetype], style3)
        co += 1
    if with_codes:
        coc=co
        ws0.write(li,coc, "etudid", style3)
        ws0.write(li,coc+1, "code_nip", style3)
        ws0.write(li,coc+2, "code_ine", style3)
        co += 3
    ws0.write(li,co, "Date", style3)
    for i in range(4):
        ws0.write(li, co+1+i, '', style2b)
    n = 0
    for t in lines:
        n += 1
        li += 1
        ws0.write(li, 0, n, style1b)
        ws0.write(li, 1, t['nom'] + ' ' + t['prenom'], style2t3) 
        co = 2
        for groupetype in groups_excel:
            ws0.write(li,co, t[groupetype], style2t3)
            co += 1
        if with_codes:
            ws0.write(li,coc, t['etudid'], style2t3)
            ws0.write(li,coc+1, t['code_nip'], style2t3)
            ws0.write(li,coc+2, t['code_ine'], style2t3)
        ws0.write(li, co, '', style2tb) # vide
        for i in range(4):
            ws0.write(li, co+1+i, t['etath'], style2b) # etat
        ws0.row(li).height = 850 # sans effet ?
    #
    li += 2
    dt = time.strftime( '%d/%m/%Y à %Hh%M' )
    if server_name:
        dt += ' sur ' + server_name
    ws0.write(li, 1, 'Liste éditée le ' + dt, style1i)
    #
    ws0.col(0).width = 850
    ws0.col(1).width = 9000

    return wb.savetostr()
