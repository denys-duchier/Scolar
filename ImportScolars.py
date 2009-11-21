# -*- mode: python -*-
# -*- coding: iso8859-15 -*-

##############################################################################
#
# Gestion scolarite IUT
#
# Copyright (c) 2001 - 2007 Emmanuel Viennet.  All rights reserved.
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

""" Importation des etudiants à partir de fichiers CSV
"""

import os, sys, time, pdb

from sco_utils import *
from notesdb import *
from notes_log import log
import scolars
import sco_excel
import sco_groups
import sco_news
from sco_news import NEWS_INSCR, NEWS_NOTE, NEWS_FORM, NEWS_SEM, NEWS_MISC
from sco_formsemestre_inscriptions import do_formsemestre_inscription_with_modules

# format description (relative to Product directory))
FORMAT_FILE = "misc/format_import_etudiants.txt"

# Champs modifiables via "Import données admission"
ADMISSION_MODIFIABLE_FIELDS = (
    'date_naissance', 'lieu_naissance',
    'bac', 'specialite', 'annee_bac',
    'math', 'physique', 'anglais', 'francais',
    'qualite', 'rapporteur', 'score', 'commentaire',
    'nomlycee', 'villelycee', 'codepostallycee', 'codelycee' )

# ----

def sco_import_format( product_file_path, with_codesemestre=True ):
    "returns tuples (Attribut, Type, Table, AllowNulls, Description)"
    r = []
    for l in open(product_file_path+'/'+FORMAT_FILE):
        l = l.strip()
        if l and l[0] != '#':
            fs = l.split(';')
            if len(fs) != 5:
                raise FormatError('file %s has invalid format (expected %d fields, got %d) (%s)'
                                  % (FORMAT_FILE,5,len(fs),l))
            if with_codesemestre or fs[0].strip().lower() != 'codesemestre':
                r.append( tuple( [x.strip() for x in fs]) )
    return r

def sco_import_generate_excel_sample( format,
                                      with_codesemestre=True,
                                      only_tables=None,
                                      exclude_cols=[],
                                      formsemestre_id=None,
                                      context=None):
    """generates an excel document based on format
    (format is the result of sco_import_format())
    If not None, only_tables can specify a list of sql table names
    (only columns from these tables will be generated)
    If formsemestre_id, indique les codes nom et prenom des etudiants du semestre
    """    
    style = sco_excel.Excel_MakeStyle(bold=True)
    style_required = sco_excel.Excel_MakeStyle(bold=True, color='red')
    titles = []
    titlesStyles = []
    for l in format:
        name = l[0].lower()
        if (not with_codesemestre) and name == 'codesemestre':
            continue # pas de colonne codesemestre
        if only_tables is not None and l[2].lower() not in only_tables:
            continue # table non demandée
        if name in exclude_cols:
            continue # colonne exclue
        if int(l[3]):
            titlesStyles.append(style)
        else:
            titlesStyles.append(style_required)
        titles.append(name)
    
    if formsemestre_id and context:
        nt = context.Notes._getNotesCache().get_NotesTable(context, formsemestre_id)
        inscrlist = nt.inscrlist
        titles = [ 'etudid' ] + titles
        titlesStyles = [ style ] + titlesStyles
        #log('(%d) titles=%s' %(len(titles), titles))  # XXX
        # rempli table avec données actuelles 
        lines = []
        for i in inscrlist:
            etud = context.getEtudInfo(etudid=i['etudid'], filled=True)[0]
            #log('etud=%s' % etud)
            l = []
            for field in titles:
                l.append(etud.get(field.lower(), ''))
            lines.append(l)
    else:
        lines = [[]] # empty content, titles only
    #log('(%d) lines[0]=%s' % (len(lines[0]),lines[0]))
    return sco_excel.Excel_SimpleTable( titles=titles,
                                        titlesStyles=titlesStyles,
                                        SheetName="Etudiants",
                                        lines=lines)


def scolars_import_excel_file( datafile, product_file_path, Notes, REQUEST,
                               formsemestre_id=None, check_homonyms=True):
    """Importe etudiants depuis fichier Excel
    et les inscrit dans le semestre indiqué (et à TOUS ses modules)
    """
    log('scolars_import_excel_file: formsemestre_id=%s'%formsemestre_id)
    cnx = Notes.GetDBConnexion()
    cursor = cnx.cursor()
    annee_courante = time.localtime()[0]
    exceldata = datafile.read()
    if not exceldata:
        raise ScoValueError("Ficher excel vide ou invalide")
    diag, data = sco_excel.Excel_to_list(exceldata)
    if not data: # probably a bug
        raise FormatError('scolars_import_excel_file: empty file !')
    # 1-  --- check title line
    titles = {}
    fmt = sco_import_format(product_file_path)
    for l in fmt:
        tit = l[0].lower().split()[0] # titles in lowercase, and take 1st word
        if (not formsemestre_id) or (tit != 'codesemestre'):
            titles[tit] = l[1:] # title : (Type, Table, AllowNulls, Description)

    #log("titles=%s" % titles)
    # remove quotes, downcase and keep only 1st word
    try:
        fs = [ stripquotes(s).lower().split()[0] for s in data[0] ]
    except:
        raise ScoValueError("Titres de colonnes invalides (ou vides ?)")
    #log("excel: fs='%s'\ndata=%s" % (str(fs), str(data)))
    
    # check columns titles    
    if len(fs) != len(titles):
        missing = {}.fromkeys(titles.keys())
        unknown = []
        for f in fs:
            if missing.has_key(f):
                del missing[f]
            else:
                unknown.append(f)
        raise ScoValueError('Nombre de colonnes incorrect (devrait être %d, et non %d) <br/> (colonnes manquantes: %s, colonnes invalides: %s)' %(len(titles),len(fs),missing.keys(),unknown ) )
    titleslist = []
    for t in fs:
        if not titles.has_key(t):
            raise ScoValueError('Colonne invalide: "%s"' % t)
        titleslist.append(t) # 
    # ok, same titles
    # Start inserting data, abort whole transaction in case of error
    created_etudids = []    
    NbImportedHomonyms = 0
    GroupIdInferers = {}
    try: # --- begin DB transaction
        linenum = 0
        for line in data[1:]:
            linenum += 1            
            # Read fields, check and convert type
            values = {}
            fs = line
            # remove quotes
            for i in range(len(fs)):
                if fs[i] and ((fs[i][0] == '"' and fs[i][-1] == '"')
                           or (fs[i][0] == "'" and fs[i][-1] == "'")):
                    fs[i] = fs[i][1:-1]
            for i in range(len(fs)):
                val = fs[i].strip()
                typ, table, an, descr = tuple(titles[titleslist[i]])
                #log('field %s: %s %s %s %s'%(titleslist[i], table, typ, an, descr))
                if not val and not an:
                    raise ScoValueError(
                        "line %d: null value not allowed in column %s"
                        % (linenum, titleslist[i]))
                if val == '':
                    val = None
                else:
                    if typ == 'real':
                        val = val.replace(',','.') # si virgule a la française
                        try:
                            val = float(val)
                        except:
                            raise ScoValueError(
                                "valeur nombre reel invalide (%s) sur line %d, colonne %s"
                                % (val, linenum, titleslist[i]))
                    elif typ == 'integer':
                        try:
                            # on doit accepter des valeurs comme "2006.0"
                            val = val.replace(',','.') # si virgule a la française
                            val = float(val)
                            if val % 1.0 > 1e-4:
                                raise ValueError()
                            val = int(val)
                        except:
                            raise ScoValueError(
                                "valeur nombre entier invalide (%s) sur ligne %d, colonne %s"
                                % (val, linenum, titleslist[i]))
                # xxx Ad-hoc checks (should be in format description)
                if  titleslist[i].lower() == 'sexe':
                    if val:
                        val = val.upper()
                    if not val in ('MR', 'MLLE'):
                        raise ScoValueError("valeur invalide pour 'SEXE' (doit etre 'MR' ou 'MLLE', pas '%s') ligne %d, colonne %s" % (val, linenum, titleslist[i]))
                # Excel date conversion:
                if titleslist[i].lower() == 'date_naissance':
                    if val:
                        if re.match('^[0-9]*\.?[0-9]*$', str(val)):
                            val = sco_excel.xldate_as_datetime(float(val))                        
                # --
                values[titleslist[i]] = val
            # Check nom/prenom
            ok, NbHomonyms = scolars.check_nom_prenom(cnx, nom=values['nom'], prenom=values['prenom'])
            if not ok:
                raise ScoValueError("nom ou prénom invalide sur la ligne %d" % (linenum))
            if NbHomonyms:
                NbImportedHomonyms += 1
            # Insert in DB tables
            log( 'scolars_import_excel_file: values=%s' % str(values) ) 
            # Identite
            args = values.copy()
            etudid = scolars.identite_create(cnx,args, context=Notes)
            
            created_etudids.append(etudid)
            # Admissions
            args['etudid'] = etudid
            args['annee'] = annee_courante                        
            adm_id = scolars.admission_create(cnx, args)
            # Adresse
            args['typeadresse'] = 'domicile'
            args['description'] = '(infos admission)'
            adresse_id = scolars.adresse_create(cnx,args)
            # Inscription au semestre
            args['etat'] = 'I' # etat insc. semestre
            if formsemestre_id:
                args['formsemestre_id'] = formsemestre_id
            else:
                args['formsemestre_id'] = values['codesemestre']
            # recupere liste des groupes:
            if formsemestre_id not in GroupIdInferers:
                GroupIdInferers[formsemestre_id] = sco_groups.GroupIdInferer(context, formsemestre_id)
            gi = GroupIdInferers[formsemestre_id]
            groupes = args['groupes'].split(';')
            group_ids = [ gi[group_name] for group_name in groupes ]
            group_ids = {}.fromkeys(group_ids).keys() # uniq
            if None in group_ids:
                raise ScoValueError("groupe invalide sur la ligne %d" % (linenum))
            
            do_formsemestre_inscription_with_modules(context, formsemestre_id, etudid, group_ids,
                                                     etat='I',
                                                     REQUEST=REQUEST,
                                                     method='import_csv_file')
        # Verification proportion d'homonymes: si > 10%, abandonne
        log('scolars_import_excel_file: detected %d homonyms' % NbImportedHomonyms)
        if check_homonyms and NbImportedHomonyms > len(created_etudids) / 10:
            log('scolars_import_excel_file: too many homonyms')
            raise ScoValueError("Il y a trop d'homonymes (%d étudiants)" % NbImportedHomonyms)
    except:
        cnx.rollback()
        log('scolars_import_excel_file: aborting transaction !')
        # Nota: db transaction is sometimes partly commited...
        # here we try to remove all created students
        cursor = cnx.cursor()
        for etudid in created_etudids:
            log('scolars_import_excel_file: deleting etudid=%s'%etudid)
            cursor.execute('delete from notes_moduleimpl_inscription where etudid=%(etudid)s', { 'etudid':etudid })
            cursor.execute('delete from notes_formsemestre_inscription where etudid=%(etudid)s', { 'etudid':etudid })
            cursor.execute('delete from scolar_events where etudid=%(etudid)s', { 'etudid':etudid })
            cursor.execute('delete from adresse where etudid=%(etudid)s', { 'etudid':etudid })
            cursor.execute('delete from admissions where etudid=%(etudid)s', { 'etudid':etudid })
            cursor.execute('delete from identite where etudid=%(etudid)s', { 'etudid':etudid })
        cnx.commit()
        log('scolars_import_excel_file: re-raising exception')
        raise
    log('scolars_import_excel_file: completing transaction')
    
    sco_news.add(REQUEST, cnx, typ=NEWS_INSCR,
                 text='Inscription de %d étudiants' # peuvent avoir ete inscrits a des semestres differents
                 % len(created_etudids))
    cnx.commit()    
    return diag


def scolars_import_admission( datafile, product_file_path, Notes, REQUEST,
                               formsemestre_id=None):
    """Importe données admission depuis fichier Excel
    """
    log('scolars_import_admission: formsemestre_id=%s'%formsemestre_id)
    cnx = Notes.GetDBConnexion()
    cursor = cnx.cursor()
    annee_courante = time.localtime()[0]
    exceldata = datafile.read()
    if not exceldata:
        raise ScoValueError("Ficher excel vide ou invalide")
    diag, data = sco_excel.Excel_to_list(exceldata)
    if not data: # probably a bug
        raise FormatError('scolars_import_admission: empty file !')
    #
    titles = data[0]
    ietudid= titles.index('etudid')

    modifiable_fields = Set( ADMISSION_MODIFIABLE_FIELDS )
    
    for line in data[1:]:        
        args = scolars.admission_list(cnx, args={'etudid':line[ietudid]})
        if not args:
            raise ScoValueError('etudiant inconnu: etudid=%s' % line[ietudid])
        args = args[0]
        i = 0
        for tit in titles:
            if tit in modifiable_fields:
                args[tit] = line[i]
            i += 1
        scolars.etudident_edit(cnx, args )

