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
import sco_groups

def do_formsemestre_recapcomplet(
    context=None, REQUEST=None, formsemestre_id=None,
    format='html', # html, xml, xls
    hidemodules=False, # ne pas montrer les modules (ignor� en XML)
    xml_nodate=False, # format XML sans dates (sert pour debug cache: comparaison de XML)
    modejury=False, # saisie d�cisions jury
    sortcol=None, # indice colonne a trier dans table T
    xml_with_decisions=False,
    disable_etudlink=False
    ):
    """Calcule et renvoie le tableau r�capitulatif.
    """
    data, filename, format = make_formsemestre_recapcomplet(**vars())
    if format == 'xml' or format == 'html':
        return data
    elif format == 'csv':
        return sendCSVFile(REQUEST, data, filename)
    elif format == 'xls':
        return sco_excel.sendExcelFile(REQUEST, data, filename )
    else:
        raise ValueError('unknown format %s' % format)

def make_formsemestre_recapcomplet(
    context=None, REQUEST=None, formsemestre_id=None,
    format='html', # html, xml, xls
    hidemodules=False, # ne pas montrer les modules (ignor� en XML)
    xml_nodate=False, # format XML sans dates (sert pour debug cache: comparaison de XML)
    modejury=False, # saisie d�cisions jury
    sortcol=None, # indice colonne a trier dans table T
    xml_with_decisions=False,
    disable_etudlink=False
    ):
    """Grand tableau r�capitulatif avec toutes les notes de modules
    pour tous les �tudiants, les moyennes par UE et g�n�rale,
    tri� par moyenne g�n�rale d�croissante.
    """
    if format=='xml':
        return _formsemestre_recapcomplet_xml(context, formsemestre_id,
                                              xml_nodate, xml_with_decisions=xml_with_decisions)
    if format == 'xls':
        keep_numeric = True # pas de conversion des notes en strings
    else:
        keep_numeric = False
    
    sem = context.do_formsemestre_list(args={ 'formsemestre_id' : formsemestre_id } )[0]
    nt = context._getNotesCache().get_NotesTable(context, formsemestre_id)    
    modimpls = nt.get_modimpls()
    ues = nt.get_ues() # incluant le(s) UE de sport
    #
    partitions, partitions_etud_groups = sco_groups.get_formsemestre_groups(context, formsemestre_id)
    
    #pdb.set_trace()
    T = nt.get_table_moyennes_triees()
    if not T:
        return '', '', format

    # Construit une liste de listes de chaines: le champs du tableau resultat (HTML ou CSV)
    F = []
    h = [ 'Rg', 'Nom' ]
    # Si CSV ou XLS, indique tous les groupes
    if format == 'xls' or format == 'csv':
        for partition in partitions:
            h.append( '%s' % partition['partition_name'] )
    else:
        h.append( 'Gr' )
    h.append( 'Moy' )
    # Ajoute rangs dans groupe seulement si CSV ou XLS
    if format == 'xls' or format == 'csv':
        for partition in partitions:
            h.append( 'rang_%s' % partition['partition_name'] )
    
    cod2mod ={} # code : moduleimpl
    for ue in ues:
        if ue['type'] == UE_STANDARD:            
            h.append( ue['acronyme'] )
        elif ue['type'] == UE_SPORT:
            # n'affiche pas la moyenne d'UE dans ce cas
            # mais laisse col. vide si modules affich�s (pour s�parer les UE)
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
                    cod2mod[code] = modimpl # pour fabriquer le lien
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
    # Compte les decisions de jury
    codes_nb = DictDefault(defaultvalue=0)    
    #
    is_dem = {} # etudid : bool
    for t in T:
        etudid = t[-1]
        dec = nt.get_etud_decision_sem(etudid)
        if dec:
            codes_nb[dec['code']] += 1
        if nt.get_etud_etat(etudid) == 'D':
            gr_name = 'dem'
            is_dem[etudid] = True
        else:
            group = sco_groups.get_etud_main_group(context, etudid, sem)
            gr_name = group['group_name'] or ''
            is_dem[etudid] = False
        l = [ nt.get_etud_rang(etudid),nt.get_nom_short(etudid) ]  # rang, nom, 
        if format == 'xls' or format == 'csv': # tous les groupes
            for partition in partitions:                
                group = partitions_etud_groups[partition['partition_id']].get(etudid, None)
                if group:
                    l.append(group['group_name'])
                else:
                    l.append('')
        else:
            l.append(gr_name) # groupe
              
        l.append(fmtnum(fmt_note(t[0],keep_numeric=keep_numeric))) # moy_gen
        # Ajoute rangs dans groupes seulement si CSV ou XLS
        if format == 'xls' or format == 'csv':
            rang_gr, ninscrits_gr, gr_name = sco_bulletins.get_etud_rangs_groups(
                context, etudid, formsemestre_id, partitions, partitions_etud_groups, nt)
            
            for partition in partitions:                
                l.append(rang_gr[partition['partition_id']])
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
    # Derni�re ligne: moyennes, min et max des UEs et modules
    if not hidemodules: # moy/min/max dans chaque module
        mods_stats = {} # moduleimpl_id : stats
        for modimpl in modimpls:
            mods_stats[modimpl['moduleimpl_id']] = nt.get_mod_stats(modimpl['moduleimpl_id'])
    
    def add_bottom_stat( key, title, corner_value='' ):
        l = [ '', title ] 
        if format == 'xls' or format == 'csv':
            l += ['']*len(partitions)
        else:
            l += ['']
        l.append(corner_value)
        if format == 'xls' or format == 'csv':
            for partition in partitions:
                l += [ '' ] # rangs dans les groupes
        for ue in ues:
            if ue['type'] == UE_STANDARD:
                l.append( fmt_note(ue[key], keep_numeric=keep_numeric) ) 
            elif ue['type'] == UE_SPORT:
                # n'affiche pas la moyenne d'UE dans ce cas
                if not hidemodules:
                    l.append('') 
            ue_index.append(len(l)-1)
            if not hidemodules:
                for modimpl in modimpls:
                    if modimpl['module']['ue_id'] == ue['ue_id']:
                        l.append(fmt_note(mods_stats[modimpl['moduleimpl_id']][key],
                                          keep_numeric=keep_numeric)) # moyenne du module
        if modejury:
            l.append('') # case vide sur ligne "Moyennes"
        F.append(l + [''] ) # ajoute cellule etudid inutilisee ici
    
    add_bottom_stat( 'moy', 'Moyennes', corner_value=fmt_note(nt.moy_moy, keep_numeric=keep_numeric) )
    add_bottom_stat( 'min', 'Min')
    add_bottom_stat( 'max', 'Max')
    
    # Generation table au format demand�
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
                cells += '<td class="%s"><a href="moduleimpl_status?moduleimpl_id=%s" title="%s">%s</a></td>' % (
                    cls,
                    cod2mod[F[0][i]]['moduleimpl_id'],
                    cod2mod[F[0][i]]['module']['titre'],
                    F[0][i])
            else:
                cells += '<td class="%s">%s</td>' % (cls, F[0][i])
        if modejury:
            cells += '<td class="recap_tit">D�cision</td>'
        ligne_titres = cells + '</tr>'
        H.append( ligne_titres ) # titres
        if disable_etudlink:
            etudlink = '%(name)s'
        else:
            etudlink='<a href="formsemestre_bulletinetud?formsemestre_id=%(formsemestre_id)s&etudid=%(etudid)s&version=selectedevals" title="%(nomprenom)s">%(name)s</a>'
        ir = 0
        nblines = len(F)-1
        for l in F[1:]:
            etudid = l[-1]
            if ir >= nblines-3:
                el = l[1] # derniere ligne
                styl = ( 'recap_row_moy', 'recap_row_min', 'recap_row_max')[ir-nblines+3]
                cells = '<tr class="%s sortbottom">' % styl
            else:
                el = etudlink % { 'formsemestre_id' : formsemestre_id, 'etudid' : etudid, 'name' : l[1],
                                  'nomprenom' :  nt.get_nom_long(etudid) }
                if ir % 2 == 0:
                    cells = '<tr class="recap_row_even" id="etudid%s">' % etudid
                else:
                    cells = '<tr class="recap_row_odd" id="etudid%s">' % etudid
            ir += 1
            nsn = [ x.replace('NA0', '-') for x in l[:-1] ] # notes sans le NA0
            cells += '<td class="recap_col">%s</td>' % nsn[0] # rang
            cells += '<td class="recap_col">%s</td>' % el # nom etud (lien)
            cells += '<td class="recap_col">%s</td>' % nsn[2] # group name
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
                    if ir < nblines - 2:
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
        # recap des decisions jury (nombre dans chaque code):
        if codes_nb:
            H.append('<h3>D�cisions du jury</h3><table>')
            cods = codes_nb.keys()
            cods.sort()
            for cod in cods:
                H.append('<tr><td>%s</td><td>%d</td></tr>' % (cod, codes_nb[cod]))
            H.append('</table>')
        return '\n'.join(H), '', 'html'
    elif format == 'csv':
        CSV = CSV_LINESEP.join( [ CSV_FIELDSEP.join(x[:-1]) for x in F ] )
        semname = sem['titre_num'].replace( ' ', '_' )
        date = time.strftime( '%d-%m-%Y')
        filename = 'notes_modules-%s-%s.csv' % (semname,date)
        return CSV, filename, 'csv'
    elif format == 'xls':
        semname = sem['titre_num'].replace( ' ', '_' )
        date = time.strftime( '%d-%m-%Y')
        filename = 'notes_modules-%s-%s.xls' % (semname,date)
        xls = sco_excel.Excel_SimpleTable(
            titles= ['etudid'] + F[0],
            lines = [ [x[-1]] + x[:-1] for x in F[1:] ], # reordonne cols (etudid en 1er)
            SheetName = 'notes %s %s' % (semname,date) )
        return xls, filename, 'xls'
    else:
        raise ValueError('unknown format %s' % format)

def _formsemestre_recapcomplet_xml(context, formsemestre_id, xml_nodate, xml_with_decisions=False):
    "XML export: liste tous les bulletins XML"
    # REQUEST.RESPONSE.setHeader('Content-type', XML_MIMETYPE)

    nt = context._getNotesCache().get_NotesTable(context, formsemestre_id)    
    T = nt.get_table_moyennes_triees()
    if not T:
        return '', '', 'xml'
    
    doc = jaxml.XML_document( encoding=SCO_ENCODING )
    if xml_nodate:
        docdate = ''
    else:
        docdate = datetime.datetime.now().isoformat()
    doc.recapsemestre( formsemestre_id=formsemestre_id,
                       date=docdate)
    evals=context.do_evaluation_etat_in_sem(formsemestre_id)[0]
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
            context, formsemestre_id, etudid,
            doc=doc, force_publishing=True,
            xml_nodate=xml_nodate, xml_with_decisions=xml_with_decisions )
        doc._pop()
    return repr(doc), '', 'xml'
