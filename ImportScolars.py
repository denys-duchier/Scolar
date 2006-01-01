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

""" Importation des etudiants à partir de fichiers CSV
"""

import os, sys, time, pdb

from notesdb import *
from notes_log import log
import scolars

# format description (relative to Product directory))
FORMAT_FILE = "misc/format_import_etudiants.txt"

# ----

def sco_import_format( product_file_path ):
    "returns tuples (Attribut, Type, Table, AllowNulls, Description)"
    r = []
    for l in open(product_file_path+'/'+FORMAT_FILE):
        l = l.strip()
        if l and l[0] != '#':
            fs = l.split(';')
            if len(fs) != 5:
                raise FormatError('file %s has invalid format (expected %d fields, got %d) (%s)'
                                  % (FORMAT_FILE,5,len(fs),l))
            r.append( tuple( [x.strip() for x in fs]) )
    return r

def scolars_import_csv_file( csvfile, product_file_path, Notes, REQUEST):
    """Importe etudiants depuis fichier CSV
    et les inscrit dans le semestre indiqué (et à TOUS ses modules)
    """
    cnx = Notes.GetDBConnexion()
    cursor = cnx.cursor()
    annee_courante = time.localtime()[0]
    # 1-  --- check title line
    titles = {}
    fmt = sco_import_format(product_file_path)
    for l in fmt:
        tit = l[0].lower() # titles in lowercase
        titles[tit] = l[1:] # title : (Type, Table, AllowNulls, Description)
    head = csvfile.readline()
    if not head:
        raise FormatError('check_csv_file: empty file !')
    fs = [ x.strip().lower() for x in head.split('\t') ]
    log("csv: fs='%s'" % str(fs))
    # remove quotes
    for i in range(len(fs)):
        if len(fs[i]) > 1:
            if (fs[i][0] == '"' and fs[i][-1] == '"') or (fs[i][0] == "'" and fs[i][-1] == "'"):
                fs[i] = fs[i][1:-1]
    
    # check columns titles    
    if len(fs) != len(titles):
        missing = {}.fromkeys(titles.keys())
        unknown = []
        for f in fs:
            if missing.has_key(f):
                del missing[f]
            else:
                unknown.append(f)
        raise FormatError('check_csv_file: invalid number of columns (should be %d, got %d) (missing columns: %s, unknown: %s)' %(len(titles),len(fs),missing.keys(),unknown ) )
    titleslist = []
    for t in fs:
        if not titles.has_key(t):
            raise FormatError('check_csv_file: unknown title "%s"' % fs)
        titleslist.append(t) # 
    # ok, same titles
    # Start inserting data, abort whole transaction in case of error
    created_etudids = []
    try: # --- begin DB transaction
        linenum = 0
        lines = csvfile.readlines() # small file, read it
        for line in lines:
            linenum += 1            
            # Read fields, check and convert type
            values = {} # { title : value } (for this line)
            if line and (line[-1] == '\n' or  line[-1] == '\r'):
                line = line[:-1]
            fs = line.split('\t')
            # remove quotes
            for i in range(len(fs)):
                if fs[i] and ((fs[i][0] == '"' and fs[i][-1] == '"')
                           or (fs[i][0] == "'" and fs[i][-1] == "'")):
                    fs[i] = fs[i][1:-1]
            assert len(fs) == len(titleslist)
            for i in range(len(fs)):
                val = fs[i].strip()
                table, typ, an, descr = tuple(titles[titleslist[i]])
                if not val and not an:
                    raise ValueError(
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
                            raise ValueError(
                                "invalid float value (%s) at line %d, column %s"
                                % (val, linenum, titleslist[i]))
                    elif typ == 'integer':
                        try:
                            val = int(val)
                        except:
                            raise ValueError(
                                "invalid integer value (%s) at line %d, column %s"
                                % (val, linenum, titleslist[i]))
                # xxx Ad-hoc checks (should be in format description)
                if  titleslist[i].lower() == 'sexe':
                    val = val.upper()
                    if not val in ('MR', 'MLLE'):
                        raise ValueError("invalid value for 'SEXE' (expecting 'MR' or 'MLLE', got '%s') at line %d, column %s" % (val, linenum, titleslist[i]))
                
                values[titleslist[i]] = val
            # Insert in DB tables
            log( 'csv inscription: values=%s' % str(values) ) 
            # Identite
            args = values.copy()
            etudid = scolars.identite_create(cnx,args)
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
            formsemestre_id = kw['args']['codesemestre']
            kw['args']['formsemestre_id'] = formsemestre_id
            Notes.do_formsemestre_inscription_with_modules(args=args,
                                                           REQUEST=REQUEST,
                                                           method='import_csv_file')
    except:
        cnx.rollback()
        log('csv: aborting transaction !')
        # Nota: db transaction is sometimes partly commited...
        # here we try to remove all created students
        cursor = cnx.cursor()
        for etudid in created_etudids:
            log('csv: deleting etudid=%s'%etudid)
            cursor.execute('delete from notes_moduleimpl_inscription where etudid=%(etudid)s', { 'etudid':etudid })
            cursor.execute('delete from notes_formsemestre_inscription where etudid=%(etudid)s', { 'etudid':etudid })
            cursor.execute('delete from adresse where etudid=%(etudid)s', { 'etudid':etudid })
            cursor.execute('delete from admissions where etudid=%(etudid)s', { 'etudid':etudid })
            cursor.execute('delete from identite where etudid=%(etudid)s', { 'etudid':etudid })
        cnx.commit()
        log('csv: re-raising exception')
        raise
    log('csv: completing transaction')
    cnx.commit()

