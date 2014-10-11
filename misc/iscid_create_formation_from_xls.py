# -*- mode: python -*-
# -*- coding: utf-8 -*-

# Creation d'une formation ISCID à partir d'un xls listant les modules

import os, sys, pdb, pprint
from openpyxl import load_workbook # apt-get install python-openpyxl
import jaxml
SCO_ENCODING = 'utf-8'

INPUT_FILENAME = "/tmp/Bachelor.xlsx"
OUTPUT_FILENAME= os.path.splitext(INPUT_FILENAME)[0] + '.xml' 

FIRST_SHEET_IDX=1 # saute première feuille du classeur


# Code de ScoDoc (sco_utils.py)
UE_STANDARD = 0 # UE "fondamentale"
UE_SPORT = 1    # bonus "sport"
UE_STAGE_LP = 2 # ue "projet tuteuré et stage" dans les Lic. Pro.
UE_ELECTIVE = 4 # UE "élective" dans certains parcours (UCAC?, ISCID)
UE_PROFESSIONNELLE = 5 # UE "professionnelle" (ISCID, ...)

# Code du fichier Excel:
UE_TYPE2CODE = { u'UE F' : UE_STANDARD, u'UE E' : UE_ELECTIVE }

# Lecture du fichier Excel
UE = []
wb = load_workbook(filename=INPUT_FILENAME)
#print wb.get_sheet_names()

for sheet_name in wb.get_sheet_names()[FIRST_SHEET_IDX:]:
    print 'Importing sheet %s' % sheet_name
    sheet = wb.get_sheet_by_name(sheet_name)
    # Avance jusqu'à trouver le titre 'CODE' en premiere colonne
    i=0
    while i < len(sheet.rows) and sheet.rows[i][0].value != 'CODE':
        i = i + 1

    i = i + 1
    ue = None
    while i < len(sheet.rows):
        code = sheet.rows[i][0].value
        type_ue = sheet.rows[i][2].value
        if type_ue in UE_TYPE2CODE:
            if ue:
                UE.append(ue)
            # creation UE
            acronyme = code # ici l'acronyme d'UE est le code du module
            if not acronyme and (i < len(sheet.rows)-1):
                acronyme = sheet.rows[i+1][0].value # code module sur ligne suivante
                print acronyme
                if acronyme: # tres specifique: deduit l'acronyme d'UE du code module
                    parts = acronyme.split(u'-')
                    parts[-1] = parts[-1][-1] # ne garde que le dernier chiffre
                    acronyme = u'-'.join(parts) # B1-LV1-EN1 -> B1-LV1-1
                print '->', acronyme
            if not acronyme:
                acronyme = sheet.rows[i][3].value # fallback: titre
            ue = { 'acronyme' : acronyme,
                   'titre' : sheet.rows[i][3].value,
                   'ects' : sheet.rows[i][5].value or u"",
                   'type' : UE_TYPE2CODE[type_ue],
                   'modules' : []
                   }
            i_ue = i
        if code:
            ue['modules'].append( {
                'code' : code,
                'heures_td' : sheet.rows[i_ue][4].value or u"",
                'titre' : sheet.rows[i][3].value,
                'semestre_id' : sheet.rows[i][1].value,
                } )

        i += 1 # next line

    if ue:
        UE.append(ue)


def sstr(s):
    if type(s) is type(u''):
        return s.encode(SCO_ENCODING)
    else:
        return str(s)

# ----- Write to XML    
doc = jaxml.XML_document( encoding=SCO_ENCODING )

doc._push()
doc.formation( acronyme="Bachelor ISCID",
               code_specialite="",
               type_parcours="1001",
               titre_officiel="Bachelor ISCID",
               formation_code="FCOD4",
               version="1",
               titre="Bachelor ISCID",
               formation_id="FORM115"
               )

for ue in UE:
    doc._push()
    doc.ue( acronyme=sstr(ue['acronyme']), ects=sstr(ue['ects']), titre=sstr(ue['titre']) )
    doc._push()
    doc.matiere( titre=sstr(ue['titre']) ) # useless but necessary
    for m in ue['modules']:
        doc._push()
        doc.module( coefficient="1.0", code=sstr(m['code']), 
                    heures_td=sstr(m['heures_td']), 
                    titre=sstr(m['titre']), abbrev=sstr(m['titre']),
                    semestre_id=sstr(m['semestre_id'])
            )
        doc._pop() # /module
    doc._pop() # /matiere
    doc._pop() # /ue
    
doc._pop() # /formation

#---
print 'Writing XML file: ', OUTPUT_FILENAME
f = open(OUTPUT_FILENAME, 'w')
f.write(str(doc))
f.close()
