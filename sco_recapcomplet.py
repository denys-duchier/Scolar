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

"""Tableau recapitulatif des notes d'un semestre
"""

from notes_table import *
import sco_bulletins, sco_excel

def do_formsemestre_recapcomplet(
    znotes,REQUEST,formsemestre_id,
    format='html', # html, xml, xls
    hidemodules=False, # ne pas montrer les modules (ignoré en XML)
    xml_nodate=False, # format XML sans dates (sert pour debug cache: comparaison de XML)
    modejury=False, # saisie décisions jury
    sortcol=None # indice colonne a trier dans table T
    ):
    """Grand tableau récapitulatif avec toutes les notes de modules
    pour tous les étudiants, les moyennes par UE et générale,
    trié par moyenne générale décroissante.
    """
    if format=='xml':
        return _formsemestre_recapcomplet_xml(znotes, formsemestre_id, xml_nodate)
    if format == 'xls':
        keep_numeric = True # pas de conversion des notes en strings
    else:
        keep_numeric = False
    
    sem = znotes.do_formsemestre_list(args={ 'formsemestre_id' : formsemestre_id } )[0]
    nt = znotes._getNotesCache().get_NotesTable(znotes, formsemestre_id)    
    modimpls = nt.get_modimpls()
    ues = nt.get_ues() # incluant le(s) UE de sport
    #pdb.set_trace()
    T = nt.get_table_moyennes_triees()
    # Construit une liste de listes de chaines: le champs du tableau resultat (HTML ou CSV)
    F = []
    h = [ 'Rg', 'Nom', 'Gr', 'Moy' ]
    cod2mod ={} # code : moduleimpl_id
    for ue in ues:
        if ue['type'] == UE_STANDARD:            
            h.append( ue['acronyme'] )
        elif ue['type'] == UE_SPORT:
            # n'affiche pas la moyenne d'UE dans ce cas
            # mais laisse col. vide si modules affichés (pour séparer les UE)
            if not hidemodules:
                h.append('')
            pass
        else:
            raise ScoValueError('type UE invalide !')
        if not hidemodules:
            for modimpl in modimpls:
                if modimpl['module']['ue_id'] == ue['ue_id']:
                    code = modimpl['module']['code']
                    h.append( code )
                    cod2mod[code] = modimpl['moduleimpl_id'] # pour fabriquer le lien
    F.append(h)
    ue_index = [] # indices des moy UE dans l (pour appliquer style css)
    def fmtnum(val): # conversion en nombre pour cellules excel
        if keep_numeric:
            try:
                return float(val)
            except:
                return val
        else:
            return val
    #
    is_dem = {} # etudid : bool
    for t in T:
        etudid = t[-1]
        if nt.get_etud_etat(etudid) == 'D':
            gr = 'dem'
            is_dem[etudid] = True
        else:
            gr = nt.get_groupetd(etudid)
            is_dem[etudid] = False
        l = [ nt.get_etud_rang(etudid),nt.get_nom_short(etudid),
              gr,
              fmtnum(fmt_note(t[0],keep_numeric=keep_numeric))] # rang, nom,  groupe, moy_gen
        i = 0
        for ue in ues:
            i += 1
            if ue['type'] == UE_STANDARD:
                l.append( fmtnum(t[i]) ) # moyenne etud dans ue
            elif ue['type'] == UE_SPORT:
                # n'affiche pas la moyenne d'UE dans ce cas
                if not hidemodules:
                    l.append('')
            ue_index.append(len(l)-1)
            if not hidemodules:
                j = 0
                for modimpl in modimpls:
                    if modimpl['module']['ue_id'] == ue['ue_id']:
                        l.append( fmtnum(t[j+len(ues)+1]) ) # moyenne etud dans module
                    j += 1
        l.append(etudid) # derniere colonne = etudid
        F.append(l)
    # Dernière ligne: moyennes UE et modules
    l = [ '', 'Moyennes', '', fmt_note(nt.moy_moy) ] 
    i = 0
    for ue in ues:
        i += 1
        if ue['type'] == UE_STANDARD:
            l.append( fmt_note(ue['moy'], keep_numeric=keep_numeric) ) 
        elif ue['type'] == UE_SPORT:
            # n'affiche pas la moyenne d'UE dans ce cas
            if not hidemodules:
                l.append('') 
        ue_index.append(len(l)-1)
        if not hidemodules:
            for modimpl in modimpls:
                if modimpl['module']['ue_id'] == ue['ue_id']:
                    l.append(fmt_note(nt.get_mod_moy(modimpl['moduleimpl_id'])[0],
                                      keep_numeric=keep_numeric)) # moyenne du module
    if modejury:
        l.append('') # case vide sur ligne "Moyennes"
    F.append(l + [''] ) # ajoute cellule etudid inutilisee ici
    # Generation table au format demandé
    if format == 'html':
        # Table format HTML
        H = [ """
        <script type="text/javascript">
        function va_saisir(formsemestre_id, etudid) {
        loc = 'formsemestre_validation_etud_form?formsemestre_id='+formsemestre_id+'&etudid='+etudid;
        if (SORT_COLUMN_INDEX) {
           loc += '&sortcol=' + SORT_COLUMN_INDEX;
        }
        loc += '#etudid' + etudid;   
        document.location=loc;
        }
        </script>        
        <table class="notes_recapcomplet sortable" id="recapcomplet">
        """ ]
        if sortcol: # sort table using JS sorttable
            H.append("""<script type="text/javascript">
            function resort_recap() {
            var clid = %d;
            // element <a place par sorttable (ligne de titre)
            lnk = document.getElementById("recap_trtit").childNodes[clid].childNodes[0];
            ts_resortTable(lnk,clid);
            // Scroll window:
            eid = document.location.hash
            if (eid) {
              var eid = eid.substring(1); // remove #
              var e = document.getElementById(eid);
              if (e) {
                var y = e.offsetTop + e.offsetParent.offsetTop;            
                window.scrollTo(0,y);                
                } 
              
            }
            }
            addEvent(window, "load", resort_recap);
            </script>
            """ % (int(sortcol)) )
        cells = '<tr class="recap_row_tit sortbottom" id="recap_trtit">'
        for i in range(len(F[0])):
            if i in ue_index:
                cls = 'recap_tit_ue'
            else:
                cls = 'recap_tit'
            if i == 0: # Rang: force tri numerique pour sortable
                cls = cls + ' sortnumeric'
            if cod2mod.has_key(F[0][i]): # lien vers etat module
                cells += '<td class="%s"><a href="moduleimpl_status?moduleimpl_id=%s">%s</a></td>' % (cls,cod2mod[F[0][i]], F[0][i])
            else:
                cells += '<td class="%s">%s</td>' % (cls, F[0][i])
        if modejury:
            cells += '<td class="recap_tit">Décision</td>'
        ligne_titres = cells + '</tr>'
        H.append( ligne_titres ) # titres

        etudlink='<a href="formsemestre_bulletinetud?formsemestre_id=%s&etudid=%s&version=selectedevals">%s</a>'
        ir = 0
        nblines = len(F)-1
        for l in F[1:]:
            etudid = l[-1]
            if ir == nblines-1:
                el = l[1] # derniere ligne
                cells = '<tr class="recap_row_moy sortbottom">'
            else:
                el = etudlink % (formsemestre_id,etudid,l[1])
                if ir % 2 == 0:
                    cells = '<tr class="recap_row_even" id="etudid%s">' % etudid
                else:
                    cells = '<tr class="recap_row_odd" id="etudid%s">' % etudid
            ir += 1
            nsn = [ x.replace('NA0', '-') for x in l[:-1] ] # notes sans le NA0
            cells += '<td class="recap_col">%s</td>' % nsn[0] # rang
            cells += '<td class="recap_col">%s</td>' % el # nom etud (lien)
            cells += '<td class="recap_col">%s</td>' % nsn[2] # groupetd
            # grise si moyenne generale < barre
            cssclass = 'recap_col_moy'
            try:
                if float(nsn[3]) < NOTES_BARRE_GEN:
                    cssclass = 'recap_col_moy_inf'
            except:
                pass
            cells += '<td class="%s">%s</td>' % (cssclass,nsn[3])
            for i in range(4,len(nsn)):
                if i in ue_index:
                    cssclass = 'recap_col_ue'
                    # grise si moy UE < barre
                    try:
                        if float(nsn[i]) < NOTES_BARRE_UE:
                            cssclass = 'recap_col_ue_inf'
                        elif float(nsn[i]) >= NOTES_BARRE_VALID_UE:
                            cssclass = 'recap_col_ue_val'
                    except:
                        pass
                else:
                    cssclass = 'recap_col'
                cells += '<td class="%s">%s</td>' % (cssclass,nsn[i])
            if modejury and etudid:
                decision_sem = nt.get_etud_decision_sem(etudid)
                if is_dem[etudid]:
                    code = 'DEM'
                    act = ''
                elif decision_sem:
                    code = decision_sem['code']
                    act = '(modifier)'
                else:
                    code = ''
                    act = 'saisir'
                cells += '<td class="decision">%s' % code
                if act:
                    #cells += ' <a href="formsemestre_validation_etud_form?formsemestre_id=%s&etudid=%s">%s</a>' % (formsemestre_id, etudid, act)
                    cells += ''' <a href="#" onclick="va_saisir('%s', '%s')">%s</a>''' % (formsemestre_id, etudid, act)
                cells += '</td>'
            H.append( cells + '</tr>' )
            #H.append( '<tr><td class="recap_col">%s</td><td class="recap_col">%s</td><td class="recap_col">' % (l[0],el) +  '</td><td class="recap_col">'.join(nsn) + '</td></tr>')
        H.append( ligne_titres )
        H.append('</table>')
        return '\n'.join(H)
    elif format == 'csv':
        CSV = CSV_LINESEP.join( [ CSV_FIELDSEP.join(x[:-1]) for x in F ] )
        semname = sem['titre_num'].replace( ' ', '_' )
        date = time.strftime( '%d-%m-%Y')
        filename = 'notes_modules-%s-%s.csv' % (semname,date)
        return sendCSVFile(REQUEST,CSV, filename )
    elif format == 'xls':
        semname = sem['titre_num'].replace( ' ', '_' )
        date = time.strftime( '%d-%m-%Y')
        filename = 'notes_modules-%s-%s.xls' % (semname,date)
        xls = sco_excel.Excel_SimpleTable(
            titles= F[0],
            lines = [ x[:-1] for x in F[1:] ], # sup. dern. col (etudid)
            SheetName = 'notes %s %s' % (semname,date) )
        return sco_excel.sendExcelFile(REQUEST, xls, filename )
    else:
        raise ValueError, 'unknown format %s' % format

def _formsemestre_recapcomplet_xml(znotes, formsemestre_id, xml_nodate):
    "XML export: liste tous les bulletins XML"
    # REQUEST.RESPONSE.setHeader('Content-type', XML_MIMETYPE)

    nt = znotes._getNotesCache().get_NotesTable(znotes, formsemestre_id)    
    T = nt.get_table_moyennes_triees()

    doc = jaxml.XML_document( encoding=SCO_ENCODING )
    if xml_nodate:
        docdate = ''
    else:
        docdate = datetime.datetime.now().isoformat()
    doc.recapsemestre( formsemestre_id=formsemestre_id,
                       date=docdate)
    evals=znotes.do_evaluation_etat_in_sem(formsemestre_id)[0]
    doc._push()
    doc.evals_info( nb_evals_completes=evals['nb_evals_completes'],
                    nb_evals_en_cours=evals['nb_evals_en_cours'],
                    nb_evals_vides=evals['nb_evals_vides'],
                    date_derniere_note=evals['last_modif'])
    doc._pop()
    for t in T:
        etudid = t[-1]
        doc._push()
        sco_bulletins.make_xml_formsemestre_bulletinetud(
            znotes, formsemestre_id, etudid,
            doc=doc, force_publishing=True, xml_nodate=xml_nodate )
        doc._pop()
    return repr(doc)
