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
from sco_utils import SCO_ENCODING, XLS_MIMETYPE, unescape_html


def sendExcelFile(REQUEST,data,filename):
    """publication fichier.
    (on ne doit rien avoir émis avant, car ici sont générés les entetes)
    """
    from sco_utils import unescape_html
    filename = unescape_html(filename)
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
def Excel_SimpleTable( titles=[], lines=[[]], SheetName='feuille'):
    
    UnicodeUtils.DEFAULT_ENCODING = SCO_ENCODING
    
    wb = Workbook()
    ws0 = wb.add_sheet(SheetName)
    style_titres = XFStyle()
    font0 = Font()
    font0.bold = True
    font0.name = 'Times New Roman'
    font0.bold = True
    style_titres.font = font0

    style = XFStyle()
    # ligne de titres
    col = 0
    for it in titles:
        ws0.write(0, col, it, style_titres)
        col += 1
    # suite
    li = 1
    for l in lines:
        col = 0
        for it in l:
            ws0.write(li, col, it, style)
            col += 1
        li += 1
    #
    return wb.savetostr()

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
    
    style_ro = XFStyle() # cells read-only
    font_ro = Font()
    font_ro.name = 'Arial'
    font_ro.colour_index = 0x19 # mauve, voir exemple format.py
    style_ro.font = font_ro

    style_dem = XFStyle() # cells read-only
    font_dem = Font()
    font_dem.name = 'Arial'
    font_dem.colour_index = 0x3c # marron
    style_dem.font = font_dem

    style = XFStyle()
    font1 = Font()
    font1.name = 'Arial'
    style.font = font1
    # ligne de titres
    li = 0
    ws0.write(li,0, "Feuille saisie note (à enregistrer au format excel)",
              style_titres)
    li += 1
    ws0.write(li,0, "Saisir les notes dans la colonne E", style_expl)
    li += 1
    ws0.write(li,0, "Ne pas modifier les cases en mauve !",style_expl)
    li += 1
    # description evaluation    
    ws0.write(li,0, unescape_html(description), style_titres)
    li += 1
    ws0.write(li,0, 'Le %s (coef. %g)' % (E['jour'],E['coefficient']),
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
        st = style
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
        ws0.write(li,4, line[5], st ) # note
        ws0.write(li,5, line[6], st ) # comment
    # explication en bas
    li+=2
    ws0.write(li, 1, "Code notes", style_titres )
    ws0.write(li+1, 1, "ABS", style_expl )
    ws0.write(li+1, 2, "absent (0)", style_expl )
    ws0.write(li+2, 1, "NEUTRE", style_expl )
    ws0.write(li+2, 2, "pas prise en compte", style_expl )
    ws0.write(li+3, 1, "SUPR", style_expl )
    ws0.write(li+3, 2, "pour supprimer note déjà entrée", style_expl )
    ws0.write(li+4, 1, "", style_expl )
    ws0.write(li+4, 2, "cellule vide -> note non modifiée", style_expl )
    return wb.savetostr()

# Import -> liste de listes
def Excel_to_list( data ): # we may need 'encoding' argument ?
    P = parse_xls('', SCO_ENCODING, doc=data )
    diag = [] # liste de chaines pour former message d'erreur
    # n'utilise que la première feuille
    if len(P) < 1:
        diag.append('Aucune feuille trouvée dans le classeur !')
        return diag, None
    if len(P) > 1:
        diag.append('Attention: n\'utilise que la première feuille du classeur !')
    # fill matrix (inspired by Roman V. Kiseliov example)
    sheet_name, values = P[0]
    matrix = [[]]
    sheet_name = sheet_name.encode(SCO_ENCODING, 'backslashreplace')
    # diag.append(str(values))
    indexes = values.keys()
    indexes.sort()
    for row_idx, col_idx in indexes:
        v = values[(row_idx, col_idx)]
        if isinstance(v, unicode):
            v = v.encode(SCO_ENCODING, 'backslashreplace')
        else:
            v = str(v)
        last_row, last_col = len(matrix), len(matrix[-1])
        while last_row < row_idx:
            matrix.extend([[]])
            last_row = len(matrix)
        while last_col < col_idx:
            matrix[-1].extend([''])
            last_col = len(matrix[-1])
        matrix[-1].extend([v])
    diag.append('Feuille "%s", %d lignes' %
                (sheet_name,len(matrix)))
    #diag.append(str(matrix))
    #
    return diag, matrix

