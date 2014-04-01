# -*- mode: python -*-
# -*- coding: utf-8 -*-

##############################################################################
#
# Gestion scolarite IUT
#
# Copyright (c) 2001 - 2014 Emmanuel Viennet.  All rights reserved.
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
import sco_evaluations
import sco_formsemestre_status
import sco_bulletins_xml

def formsemestre_recapcomplet(context, formsemestre_id=None, 
                              modejury=False, # affiche lien saisie decision jury
                              hidemodules=False, # cache colonnes notes modules
                              tabformat='html',
                              sortcol=None,
                              xml_with_decisions=False, # XML avec decisions
                              rank_partition_id=None, # si None, calcul rang global 
                              REQUEST=None
                              ):
    """Page récapitulant les notes d'un semestre.
    Grand tableau récapitulatif avec toutes les notes de modules
    pour tous les étudiants, les moyennes par UE et générale,
    trié par moyenne générale décroissante.
    """
    # traduit du DTML
    modejury=int(modejury)
    hidemodules=int(hidemodules)
    xml_with_decisions=int(xml_with_decisions)
    isFile = tabformat in ('csv','xls','xml', 'xlsall')
    H = []
    if not isFile:
        H += [ context.sco_header(REQUEST, 
                                  page_title='Récapitulatif', 
                                  no_side_bar=True,
                                  init_qtip = True,
                                  javascripts=['js/etud_info.js'],
                                  ),
               sco_formsemestre_status.formsemestre_status_head(
                context, formsemestre_id=formsemestre_id, REQUEST=REQUEST),
                 '<form name="f" method="get" action="%s">' % REQUEST.URL0,
                 '<input type="hidden" name="formsemestre_id" value="%s"></input>' % formsemestre_id ]
        if modejury:
            H.append('<input type="hidden" name="modejury" value="%s"></input>' % modejury)
        H.append('<select name="tabformat" onchange="document.f.submit()" class="noprint">')
        for (format, label) in (('html', 'HTML'), 
                                ('xls', 'Fichier tableur (Excel)'),
                                ('xlsall', 'Fichier tableur avec toutes les évals'),
                                ('csv', 'Fichier tableur (CSV)'),
                                ('xml', 'Fichier XML')):
            if format == tabformat:
                selected = ' selected'
            else:
                selected = ''
            H.append('<option value="%s"%s>%s</option>' % (format, selected, label))
        H.append('</select>')
        
        H.append("""(cliquer sur un nom pour afficher son bulletin ou <a class="stdlink" href="%s/Notes/formsemestre_bulletins_pdf?formsemestre_id=%s">ici avoir le classeur papier</a>)""" % (context.ScoURL(), formsemestre_id))
        H.append( """<input type="checkbox" name="hidemodules" value="1" onchange="document.f.submit()" """)
        if hidemodules:
            H.append('checked')
        H.append(""" >cacher les modules</input>""")

    if tabformat == 'xml':
        REQUEST.RESPONSE.setHeader('content-type', 'text/xml')
    
    H.append( do_formsemestre_recapcomplet(
            context, REQUEST, 
            formsemestre_id, format=tabformat, hidemodules=hidemodules, 
            modejury=modejury, sortcol=sortcol, xml_with_decisions=xml_with_decisions,
            rank_partition_id=rank_partition_id
            ) )
    
    if not isFile:
        H.append('</form>')
        H.append("""<p><a class="stdlink" href="formsemestre_pvjury?formsemestre_id=%s">Voir les décisions du jury</a></p>""" % formsemestre_id)
        if context.can_validate_sem(REQUEST, formsemestre_id):
            H.append('<p>')
            if modejury:
                H.append("""<a class="stdlink" href="formsemestre_validation_auto?formsemestre_id=%s">Calcul automatique des décisions du jury</a></p><p><a class="stdlink" href="formsemestre_fix_validation_ues?formsemestre_id=%s">Vérification décisions UE</a> 
<span style="font-size: 75%%;">(corrige incohérences éventuelles introduites avant juin 2008)<span>
</p>""" % (formsemestre_id, formsemestre_id))
            else:
                H.append("""<a class="stdlink" href="formsemestre_recapcomplet?formsemestre_id=%s&amp;modejury=1&amp;hidemodules=1">Saisie des décisions du jury</a>""" % formsemestre_id)
            H.append('</p>')
        H.append(context.sco_footer(REQUEST))
    return ''.join(H) # HTML or binary data...


def do_formsemestre_recapcomplet(
    context=None, REQUEST=None, formsemestre_id=None,
    format='html', # html, xml, xls, xlsall
    hidemodules=False, # ne pas montrer les modules (ignoré en XML)
    xml_nodate=False, # format XML sans dates (sert pour debug cache: comparaison de XML)
    modejury=False, # saisie décisions jury
    sortcol=None, # indice colonne a trier dans table T
    xml_with_decisions=False,
    disable_etudlink=False,
    rank_partition_id=None # si None, calcul rang global 
    ):
    """Calcule et renvoie le tableau récapitulatif.
    """
    data, filename, format = make_formsemestre_recapcomplet(**vars())
    if format == 'xml' or format == 'html':
        return data
    elif format == 'csv':
        return sendCSVFile(REQUEST, data, filename)
    elif format[:3] == 'xls':
        return sco_excel.sendExcelFile(REQUEST, data, filename )
    else:
        raise ValueError('unknown format %s' % format)

def make_formsemestre_recapcomplet(
    context=None, REQUEST=None, formsemestre_id=None,
    format='html', # html, xml, xls, xlsall
    hidemodules=False, # ne pas montrer les modules (ignoré en XML)
    xml_nodate=False, # format XML sans dates (sert pour debug cache: comparaison de XML)
    modejury=False, # saisie décisions jury
    sortcol=None, # indice colonne a trier dans table T
    xml_with_decisions=False,
    disable_etudlink=False,
    rank_partition_id=None # si None, calcul rang global 
    ):
    """Grand tableau récapitulatif avec toutes les notes de modules
    pour tous les étudiants, les moyennes par UE et générale,
    trié par moyenne générale décroissante.
    """
    if format=='xml':
        return _formsemestre_recapcomplet_xml(context, formsemestre_id,
                                              xml_nodate, xml_with_decisions=xml_with_decisions)
    if format[:3] == 'xls':
        keep_numeric = True # pas de conversion des notes en strings
    else:
        keep_numeric = False
    
    sem = context.do_formsemestre_list(args={ 'formsemestre_id' : formsemestre_id } )[0]
    nt = context._getNotesCache().get_NotesTable(context, formsemestre_id) #>  get_modimpls, get_ues, get_table_moyennes_triees, get_etud_decision_sem, get_etud_etat, get_etud_rang, get_nom_short, get_mod_stats, nt.moy_moy, get_nom_long, get_etud_decision_sem, 
    modimpls = nt.get_modimpls()
    ues = nt.get_ues() # incluant le(s) UE de sport
    #
    partitions, partitions_etud_groups = sco_groups.get_formsemestre_groups(context, formsemestre_id)
    if rank_partition_id and format=='html': 
        # Calcul rang sur une partition et non sur l'ensemble
        # seulement en format HTML (car colonnes rangs toujours presentes en xls)
        rank_partition = sco_groups.get_partition(context, rank_partition_id)
        rank_label = 'Rg (%s)' % rank_partition['partition_name']
    else:
        rank_partition = sco_groups.get_default_partition(context, formsemestre_id)
        rank_label = 'Rg'    
    #pdb.set_trace()
    T = nt.get_table_moyennes_triees()
    if not T:
        return '', '', format

    # Construit une liste de listes de chaines: le champs du tableau resultat (HTML ou CSV)
    F = []
    h = [ rank_label, 'Nom' ]
    # Si CSV ou XLS, indique tous les groupes
    if format[:3] == 'xls' or format == 'csv':
        for partition in partitions:
            h.append( '%s' % partition['partition_name'] )
    else:
        h.append( 'Gr' )
    h.append( 'Moy' )
    # Ajoute rangs dans groupe seulement si CSV ou XLS
    if format[:3] == 'xls' or format == 'csv':
        for partition in partitions:
            h.append( 'rang_%s' % partition['partition_name'] )
    
    cod2mod ={} # code : moduleimpl
    mod_evals = {} # moduleimpl_id : liste de toutes les evals de ce module
    for ue in ues:
        if ue['type'] != UE_SPORT:
            h.append( ue['acronyme'] )
        else: # UE_SPORT:
            # n'affiche pas la moyenne d'UE dans ce cas
            # mais laisse col. vide si modules affichés (pour séparer les UE)
            if not hidemodules:
                h.append('')
            pass
        
        if not hidemodules:
            for modimpl in modimpls:
                if modimpl['module']['ue_id'] == ue['ue_id']:
                    code = modimpl['module']['code']
                    h.append( code )
                    cod2mod[code] = modimpl # pour fabriquer le lien
                    if format == 'xlsall':
                        evals = context.do_evaluation_list( {'moduleimpl_id' : modimpl['moduleimpl_id']})
                        for e in evals:
                            e['eval_state'] = sco_evaluations.do_evaluation_etat(context, e['evaluation_id'])
                        mod_evals[modimpl['moduleimpl_id']] = evals
                        h += _list_notes_evals_titles(context, code, evals)
    h += ['code_nip', 'etudid']
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
        etud_etat = nt.get_etud_etat(etudid)
        if etud_etat == 'D':
            gr_name = 'Dém.'
            is_dem[etudid] = True
        elif etud_etat == 'DEF':
            gr_name = 'Déf.'
            is_dem[etudid] = False
        else:
            group = sco_groups.get_etud_main_group(context, etudid, sem)
            gr_name = group['group_name'] or ''
            is_dem[etudid] = False
        if rank_partition_id:
            rang_gr, ninscrits_gr, rank_gr_name = sco_bulletins.get_etud_rangs_groups(
                context, etudid, formsemestre_id, partitions, partitions_etud_groups, nt)
            if rank_gr_name[rank_partition_id]:
                rank = '%s %s' % (rank_gr_name[rank_partition_id], rang_gr[rank_partition_id])
            else:
                rank = ''
        else:
            rank = nt.get_etud_rang(etudid)
        
        l = [ rank, nt.get_nom_short(etudid) ]  # rang, nom, 
        if format[:3] == 'xls' or format == 'csv': # tous les groupes
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
        if format[:3] == 'xls' or format == 'csv':
            rang_gr, ninscrits_gr, gr_name = sco_bulletins.get_etud_rangs_groups(
                context, etudid, formsemestre_id, partitions, partitions_etud_groups, nt)
            
            for partition in partitions:                
                l.append(rang_gr[partition['partition_id']])
        i = 0
        for ue in ues:
            i += 1
            if ue['type'] !=UE_SPORT:
                l.append( fmtnum(t[i]) ) # moyenne etud dans ue
            else: # UE_SPORT:
                # n'affiche pas la moyenne d'UE dans ce cas
                if not hidemodules:
                    l.append('')
            ue_index.append(len(l)-1)
            if not hidemodules:
                j = 0
                for modimpl in modimpls:
                    if modimpl['module']['ue_id'] == ue['ue_id']:
                        l.append( fmtnum(t[j+len(ues)+1]) ) # moyenne etud dans module
                        if format == 'xlsall':
                            l += _list_notes_evals(context, mod_evals[modimpl['moduleimpl_id']], etudid)
                    j += 1
        l.append(nt.identdict[etudid]['code_nip'] or '') # avant-derniere colonne = code_nip
        l.append(etudid) # derniere colonne = etudid
        F.append(l)
    # Dernière ligne: moyennes, min et max des UEs et modules
    if not hidemodules: # moy/min/max dans chaque module
        mods_stats = {} # moduleimpl_id : stats
        for modimpl in modimpls:
            mods_stats[modimpl['moduleimpl_id']] = nt.get_mod_stats(modimpl['moduleimpl_id'])
    
    def add_bottom_stat( key, title, corner_value='' ):
        l = [ '', title ] 
        if format[:3] == 'xls' or format == 'csv':
            l += ['']*len(partitions)
        else:
            l += ['']
        l.append(corner_value)
        if format[:3] == 'xls' or format == 'csv':
            for partition in partitions:
                l += [ '' ] # rangs dans les groupes
        for ue in ues:
            if ue['type'] != UE_SPORT:
                if key == 'coef' or key == 'nb_valid_evals':
                    l.append('')
                else:
                    l.append( fmt_note(ue[key], keep_numeric=keep_numeric) ) 
            else: # UE_SPORT:
                # n'affiche pas la moyenne d'UE dans ce cas
                if not hidemodules:
                    l.append('') 
            ue_index.append(len(l)-1)
            if not hidemodules:
                for modimpl in modimpls:
                    if modimpl['module']['ue_id'] == ue['ue_id']:
                        if key == 'coef':
                            coef = modimpl['module']['coefficient']
                            if format[:3] != 'xls':
                                coef = str(coef)
                            l.append(coef)
                        else:
                            val = mods_stats[modimpl['moduleimpl_id']][key]
                            if key == 'nb_valid_evals':
                                if format[:3] != 'xls': # garde val numerique pour excel
                                    val = str(val)
                            else: # moyenne du module
                                val = fmt_note(val, keep_numeric=keep_numeric)
                            l.append(val) 
                            
                        if format == 'xlsall':
                            l += _list_notes_evals_stats(context, mod_evals[modimpl['moduleimpl_id']], key)
        if modejury:
            l.append('') # case vide sur ligne "Moyennes"
        F.append(l + ['', ''] ) # ajoute cellules code_nip et etudid inutilisees ici
    
    add_bottom_stat( 'min', 'Min')
    add_bottom_stat( 'max', 'Max')
    add_bottom_stat( 'moy', 'Moyennes', corner_value=fmt_note(nt.moy_moy, keep_numeric=keep_numeric) )
    add_bottom_stat( 'coef', 'Coef')
    add_bottom_stat( 'nb_valid_evals', 'Nb évals')
    
    # Generation table au format demandé
    if format == 'html':
        # Table format HTML
        H = [ """
        <script type="text/javascript">
        function va_saisir(formsemestre_id, etudid) {
        loc = 'formsemestre_validation_etud_form?formsemestre_id='+formsemestre_id+'&amp;etudid='+etudid;
        if (SORT_COLUMN_INDEX) {
           loc += '&amp;sortcol=' + SORT_COLUMN_INDEX;
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
            eid = document.location.hash;
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
        for i in range(len(F[0])-2):
            if i in ue_index:
                cls = 'recap_tit_ue'
            else:
                cls = 'recap_tit'
            if i == 0: # Rang: force tri numerique pour sortable
                cls = cls + ' sortnumeric'
            if cod2mod.has_key(F[0][i]): # lien vers etat module
                mod = cod2mod[F[0][i]]
                cells += '<td class="%s"><a href="moduleimpl_status?moduleimpl_id=%s" title="%s (%s)">%s</a></td>' % (
                    cls,
                    mod['moduleimpl_id'],
                    mod['module']['titre'],
                    context.Users.user_info(mod['responsable_id'])['nomcomplet'],
                    F[0][i])
            else:
                cells += '<td class="%s">%s</td>' % (cls, F[0][i])
        if modejury:
            cells += '<td class="recap_tit">Décision</td>'
        ligne_titres = cells + '</tr>'
        H.append( ligne_titres ) # titres
        if disable_etudlink:
            etudlink = '%(name)s'
        else:
            etudlink='<a href="formsemestre_bulletinetud?formsemestre_id=%(formsemestre_id)s&amp;etudid=%(etudid)s&amp;version=selectedevals" id="%(etudid)s" class="etudinfo">%(name)s</a>'
        ir = 0
        nblines = len(F)-1
        for l in F[1:]:
            etudid = l[-1]
            if ir >= nblines-5:
                # dernieres lignes:
                el = l[1] 
                styl = ('recap_row_min', 'recap_row_max', 'recap_row_moy', 'recap_row_coef', 'recap_row_nbeval')[ir-nblines+5]
                cells = '<tr class="%s sortbottom">' % styl
            else:
                el = etudlink % { 'formsemestre_id' : formsemestre_id, 'etudid' : etudid, 'name' : l[1],
                                  'nomprenom' :  nt.get_nom_long(etudid) }
                if ir % 2 == 0:
                    cells = '<tr class="recap_row_even" id="etudid%s">' % etudid
                else:
                    cells = '<tr class="recap_row_odd" id="etudid%s">' % etudid
            ir += 1
            nsn = [ x.replace('NA0', '-') for x in l[:-2] ] # notes sans le NA0
            cells += '<td class="recap_col">%s</td>' % nsn[0] # rang
            cells += '<td class="recap_col">%s</td>' % el # nom etud (lien)
            cells += '<td class="recap_col">%s</td>' % nsn[2] # group name
            # Style si moyenne generale < barre
            cssclass = 'recap_col_moy'
            try:
                if float(nsn[3]) < NOTES_BARRE_GEN:
                    cssclass = 'recap_col_moy_inf'
            except:
                pass
            cells += '<td class="%s">%s</td>' % (cssclass,nsn[3])
            ue_number = 0
            for i in range(4,len(nsn)):
                if i in ue_index:
                    cssclass = 'recap_col_ue'
                    # grise si moy UE < barre
                    ue = ues[ue_number]
                    ue_number += 1
                    
                    if (ir < (nblines-5)) or (ir == nblines - 2):
                        try:                            
                            if float(nsn[i]) < nt.parcours.get_barre_ue(ue['type']): # NOTES_BARRE_UE
                                cssclass = 'recap_col_ue_inf'
                            elif float(nsn[i]) >= nt.parcours.NOTES_BARRE_VALID_UE:
                                cssclass = 'recap_col_ue_val'
                        except:
                            pass
                else:
                    cssclass = 'recap_col'
                    if ir == nblines - 2: # si moyenne generale module < barre ue, surligne:
                        try:
                            if float(nsn[i]) < nt.parcours.get_barre_ue(ue['type']):
                                cssclass = 'recap_col_moy_inf'
                        except:
                            pass
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
                    #cells += ' <a href="formsemestre_validation_etud_form?formsemestre_id=%s&amp;etudid=%s">%s</a>' % (formsemestre_id, etudid, act)
                    cells += ''' <a href="#" onclick="va_saisir('%s', '%s')">%s</a>''' % (formsemestre_id, etudid, act)
                cells += '</td>'
            H.append( cells + '</tr>' )
        
        H.append( ligne_titres )
        H.append('</table>')
        
        # Form pour choisir partition de classement:
        if not modejury and partitions:
            H.append('Afficher le rang des groupes de: ')
            if not rank_partition_id:
                checked = 'checked'
            else:
                checked = ''
            H.append('<input type="radio" name="rank_partition_id" value="" onchange="document.f.submit()" %s/>tous ' 
                     %(checked))
            for p in partitions:
                if p['partition_id'] == rank_partition_id:
                    checked = 'checked'
                else:
                    checked = ''
                H.append('<input type="radio" name="rank_partition_id" value="%s" onchange="document.f.submit()" %s/>%s ' 
                         %(p['partition_id'], checked, p['partition_name']))
        
        # recap des decisions jury (nombre dans chaque code):
        if codes_nb:
            H.append('<h4>Décisions du jury</h4><table>')
            cods = codes_nb.keys()
            cods.sort()
            for cod in cods:
                H.append('<tr><td>%s</td><td>%d</td></tr>' % (cod, codes_nb[cod]))
            H.append('</table>')
        return '\n'.join(H), '', 'html'
    elif format == 'csv':
        CSV = CSV_LINESEP.join( [ CSV_FIELDSEP.join(x) for x in F ] )
        semname = sem['titre_num'].replace( ' ', '_' )
        date = time.strftime( '%d-%m-%Y')
        filename = 'notes_modules-%s-%s.csv' % (semname,date)
        return CSV, filename, 'csv'
    elif format[:3] == 'xls':
        semname = sem['titre_num'].replace( ' ', '_' )
        date = time.strftime( '%d-%m-%Y')
        if format == 'xls':
            filename = 'notes_modules-%s-%s.xls' % (semname,date)
        else:
            filename = 'notes_modules_evals-%s-%s.xls' % (semname,date)
        xls = sco_excel.Excel_SimpleTable(
            titles= ['etudid', 'code_nip' ] + F[0],
            lines = [ [x[-1], x[-2] ] + x[:-2] for x in F[1:] ], # reordonne cols (etudid et nip en 1er)
            SheetName = 'notes %s %s' % (semname,date) )
        return xls, filename, 'xls'
    else:
        raise ValueError('unknown format %s' % format)

def _list_notes_evals(context, evals, etudid):
    """Liste des notes des evaluations completes de ce module"""
    L = []
    for e in evals:
        if e['eval_state']['evalcomplete']:
            NotesDB = context._notes_getall(e['evaluation_id'])
            if NotesDB.has_key(etudid):
                val = NotesDB[etudid]['value']
            else:
                val = None
            val_fmt = fmt_note(val, keep_numeric=True)
            L.append(val_fmt)
    return L

def _list_notes_evals_titles(context, codemodule, evals):
    """Liste des titres des evals completes"""
    L = []
    for e in evals:
        e['eval_state'] = sco_evaluations.do_evaluation_etat(context, e['evaluation_id'], keep_numeric=True)
        if e['eval_state']['evalcomplete']:
            L.append(codemodule+'-'+e['jour'])
    return L

def _list_notes_evals_stats(context, evals, key):
    """Liste des stats (moy, ou rien!) des evals completes"""
    L = []
    for e in evals:
        if e['eval_state']['evalcomplete']:
            if key == 'moy':
                val = e['eval_state']['moy']
                L.append( fmt_note(val, keep_numeric=True) )
            elif key == 'max':
                L.append( e['note_max'] )
            elif key == 'min':
                L.append(0.)
            elif key == 'coef':
                L.append( e['coefficient'] )
            else:
                L.append('') # on n'a pas sous la main min/max
    return L
    
def _formsemestre_recapcomplet_xml(context, formsemestre_id, xml_nodate, xml_with_decisions=False):
    "XML export: liste tous les bulletins XML"
    # REQUEST.RESPONSE.setHeader('content-type', XML_MIMETYPE)

    nt = context._getNotesCache().get_NotesTable(context, formsemestre_id) #> get_table_moyennes_triees   
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
    evals=sco_evaluations.do_evaluation_etat_in_sem(context, formsemestre_id)
    doc._push()
    doc.evals_info( nb_evals_completes=evals['nb_evals_completes'],
                    nb_evals_en_cours=evals['nb_evals_en_cours'],
                    nb_evals_vides=evals['nb_evals_vides'],
                    date_derniere_note=evals['last_modif'])
    doc._pop()
    for t in T:
        etudid = t[-1]
        doc._push()
        sco_bulletins_xml.make_xml_formsemestre_bulletinetud(
            context, formsemestre_id, etudid,
            doc=doc, force_publishing=True,
            xml_nodate=xml_nodate, xml_with_decisions=xml_with_decisions )
        doc._pop()
    return repr(doc), '', 'xml'
