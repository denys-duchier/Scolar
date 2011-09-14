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
#   Emmanuel Viennet      emmanuel.viennet@viennet.net
#
##############################################################################

"""Rapports suivi:
  - statistiques decisions
  - suivi cohortes
"""
from notesdb import *
from sco_utils import *
from notes_log import log
from gen_tables import GenTable
import sco_excel, sco_pdf
import sco_codes_parcours
from sco_codes_parcours import code_semestre_validant
from mx.DateTime import DateTime as mxDateTime
import mx.DateTime
import tempfile, urllib, re
import sco_formsemestre_status
from sco_pdf import SU

def formsemestre_etuds_stats(context, sem):
    """R�cup�re liste d'etudiants avec etat et decision.
    """
    nt = context._getNotesCache().get_NotesTable(context, sem['formsemestre_id']) #> get_table_moyennes_triees, identdict, get_etud_decision_sem, get_etud_etat, 
    T = nt.get_table_moyennes_triees()
    # Construit liste d'�tudiants du semestre avec leur decision
    etuds = []
    for t in T:
        etudid = t[-1]
        etud= nt.identdict[etudid].copy()
        decision = nt.get_etud_decision_sem(etudid)
        if decision:
            etud['codedecision'] = decision['code']
        etud['etat'] = nt.get_etud_etat(etudid)
        if etud['etat'] == 'D':
            etud['codedecision'] = 'DEM'
        if not etud.has_key('codedecision'):
            etud['codedecision'] = '(nd)' # pas de decision jury
        # Ajout cl� 'bac-specialite'
        bs = []
        if etud['bac']:
            bs.append(etud['bac'])
        if etud['specialite']:
            bs.append(etud['specialite'])
        etud['bac-specialite'] = ' '.join(bs)
        #
        etuds.append(etud)
    return etuds


def _categories_and_results(etuds, category, result):
    categories = {}
    results = {}
    for etud in etuds:
        categories[etud[category]] = True
        results[etud[result]] = True
    categories = categories.keys()
    categories.sort()
    results = results.keys()
    results.sort()
    return categories, results

def _results_by_category(etuds, category='', result='', category_name=None,
                         context=None, formsemestre_id=None):
    """Construit table: categories (eg types de bacs) en ligne, d�cisions jury en colonnes

    etuds est une liste d'etuds (dicts).
    category et result sont des cl�s de etud (category d�finie les lignes, result les colonnes).

    Retourne une table.
    """
    if category_name is None:
        category_name = category
    # types de bacs differents:
    categories, results = _categories_and_results(etuds, category, result)
    #
    Count = {} # { bac : { decision : nb_avec_ce_bac_et_ce_code } }
    results = {} # { result_value : True }
    for etud in etuds:
        results[etud[result]] = True
        if Count.has_key(etud[category]):
            Count[etud[category]][etud[result]] += 1
        else:            
            Count[etud[category]] = DictDefault( kv_dict={ etud[result] : 1 } )
    # conversion en liste de dict
    C = [ Count[cat] for cat in categories ]
    # 
    codes = results.keys()
    codes.sort()
    # Totaux par lignes et colonnes
    tot = 0
    for l in C:
        l['sum'] = sum(l.values())
        tot += l['sum']
    # pourcentages sur chaque total de ligne
    for l in C:
        l['sumpercent'] = '%2.1f%%' % ((100. * l['sum']) / tot)
    if C: # ligne du bas avec totaux:
        s = {}
        for code in codes:
            s[code] = sum([ l[code] for l in C])
        s['sum'] = tot
        s['sumpercent'] = '100%'
        s['_css_row_class'] = 'sortbottom'
        C.append(s)
    #
    codes.append('sum')
    codes.append('sumpercent')
    titles = {}
    # on veut { 'ADM' : 'ADM' }, peu elegant en python 2.3:
    map( lambda x,titles=titles: titles.__setitem__(x[0],x[1]), zip(codes,codes) )
    titles['sum'] = 'Total'
    titles['sumpercent'] = '%'
    titles['DEM'] = 'D�m.' # d�missions
    for i in range(len(categories)):
        if categories[i] == '':
            categories[i] = '?'
    lines_titles = [category_name] + categories + ['Total']
    return GenTable( titles=titles, columns_ids=codes, rows=C, lines_titles=lines_titles,
                     html_col_width='4em', html_sortable=True, 
                     preferences=context.get_preferences(formsemestre_id) )


# pages
def formsemestre_report(context, formsemestre_id, etuds, REQUEST=None,
                        category='bac', result='codedecision', 
                        category_name='', result_name='',
                        title='Statistiques'):    
    """
    Tableau sur r�sultats (result) par type de category bac
    """
    sem = context.get_formsemestre(formsemestre_id)
    if not category_name:
        category_name = category
    if not result_name:
        result_name = result
    if result_name == 'codedecision':
        result_name = 'r�sultats'
    #
    tab = _results_by_category(etuds, category=category, category_name=category_name,
                               result=result, 
                               context=context, formsemestre_id=formsemestre_id)
    #
    tab.filename = make_filename('stats ' + sem['titreannee'])
    
    tab.origin = 'G�n�r� par %s le ' % VERSION.SCONAME + timedate_human_repr() + ''
    tab.caption = 'R�partition des r�sultats par %s, semestre %s' % (category_name, sem['titreannee'])
    tab.html_caption = "R�partition des r�sultats par %s." % category_name
    tab.base_url = '%s?formsemestre_id=%s' % (REQUEST.URL0, formsemestre_id)
    return tab



# def formsemestre_report_bacs(context, formsemestre_id, format='html', REQUEST=None):
#     """
#     Tableau sur r�sultats par type de bac
#     """
#     sem = context.get_formsemestre(formsemestre_id)
#     title = 'Statistiques bacs ' + sem['titreannee']
#     etuds = formsemestre_etuds_stats(context, sem)
#     tab = formsemestre_report(context, formsemestre_id, etuds, REQUEST=REQUEST,
#                               category='bac', result='codedecision',
#                               category_name='Bac',
#                               title=title)
#     return tab.make_page(
#         context, 
#         title =  """<h2>R�sultats de <a href="formsemestre_status?formsemestre_id=%(formsemestre_id)s">%(titreannee)s</a></h2>""" % sem,
#         format=format, page_title = title, REQUEST=REQUEST )

def formsemestre_report_counts(context, formsemestre_id, format='html', REQUEST=None,
                               category='bac', result='codedecision', allkeys=False):
    """
    Tableau comptage avec choix des categories
    """
    sem = context.get_formsemestre(formsemestre_id)
    category_name = category.capitalize()
    title = "Comptages " + category_name
    etuds = formsemestre_etuds_stats(context, sem)
    tab = formsemestre_report(context, formsemestre_id, etuds, REQUEST=REQUEST,
                              category=category, result=result,
                              category_name=category_name,
                              title=title)
    if not etuds:
        F = [ """<p><em>Aucun �tudiant</em></p>""" ]
    else:
        if allkeys:
            keys = etuds[0].keys()
        else:
            # cl�s pr�sent�es � l'utilisateur:
            keys = ['annee_bac', 'annee_naissance', 'bac', 'specialite', 'bac-specialite',
                    'codedecision', 'etat', 'sexe', 'qualite', 'villelycee' ]
        keys.sort()
        F = [ """<form name="f" method="get" action="%s"><p>
              Colonnes: <select name="result" onChange="document.f.submit()">""" % REQUEST.URL0]
        for k in keys:
            if k == result:
                selected = 'selected'
            else:
                selected = ''
            F.append('<option value="%s" %s>%s</option>' % (k,selected,k))
        F.append('</select>')
        F.append(' Lignes: <select name="category" onChange="document.f.submit()">')
        for k in keys:
            if k == category:
                selected = 'selected'
            else:
                selected = ''
            F.append('<option value="%s" %s>%s</option>' % (k,selected,k))
        F.append('</select>')
        F.append('<input type="hidden" name="formsemestre_id" value="%s"/>' % formsemestre_id)        
        F.append('<input type="submit" value="OK"/>')
        F.append('</p></form>')

    t = tab.make_page(
        context, 
        title =  """<h2 class="formsemestre">Comptes crois�s</h2>""",
        format=format, REQUEST=REQUEST, with_html_headers=False)
    if format!='html':
        return t    
    H = [ context.sco_header(REQUEST, page_title=title),
          t, '\n'.join(F),
          """<p class="help">Le tableau affiche le nombre d'�tudiants de ce semestre dans chacun
          des cas choisis: � l'aide des deux menus, vous pouvez choisir les cat�gories utilis�es
          pour les lignes et les colonnes. Le <tt>codedecision</tt> est le code de la d�cision 
          du jury.
          </p>""",
          context.sco_footer(REQUEST)
          ]
    return '\n'.join(H)

# --------------------------------------------------------------------------
def table_suivi_cohorte(context, formsemestre_id, percent=False,
                        bac='', # selection sur type de bac
                        bacspecialite='', sexe='',
                        only_primo=False
                        ):
    """
    Tableau indicant le nombre d'etudiants de la cohorte dans chaque �tat:
    Etat     date_debut_Sn   date1  date2 ...
    S_n       #inscrits en Sn
    S_n+1
    ...
    S_last
    Diplome
    Sorties

    Determination des dates: on regroupe les semestres commen�ant � des dates proches

    """
    sem = context.get_formsemestre(formsemestre_id) # sem est le semestre origine
    t0 = time.time()
    def logt(op):
        if 0: # debug, set to 0 in production
            log('%s: %s' % (op, time.time()-t0))
    logt('table_suivi_cohorte: start')
    # 1-- Liste des semestres posterieurs dans lesquels ont �t� les etudiants de sem
    nt = context._getNotesCache().get_NotesTable(context, formsemestre_id) #> get_etudids, get_etud_decision_sem
    etudids = nt.get_etudids()

    logt('A: orig etuds set')
    S = { formsemestre_id : sem  } # ensemble de formsemestre_id
    orig_set = Set() # ensemble d'etudid du semestre d'origine
    bacs = Set()
    bacspecialites = Set()
    sexes = Set()
    for etudid in etudids:
        etud = context.getEtudInfo(etudid=etudid, filled=True)[0]
        bacspe = etud['bac'] + ' / ' + etud['specialite']
        # s�lection sur bac:
        if ((not bac or (bac == etud['bac']))
            and (not bacspecialite or (bacspecialite == bacspe))
            and (not sexe or (sexe == etud['sexe']))
            and (not only_primo or context.isPrimoEtud(etud,sem))):
            orig_set.add(etudid)
            # semestres suivants:
            for s in etud['sems']:
                if DateDMYtoISO(s['date_debut']) > DateDMYtoISO(sem['date_debut']):
                    S[s['formsemestre_id']] = s
        bacs.add(etud['bac'])
        bacspecialites.add(bacspe)
        sexes.add(etud['sexe'])
    sems = S.values()
    # tri les semestres par date de debut
    for s in sems:
        d,m,y = [int(x) for x in s['date_debut'].split('/')]
        s['date_debut_mx'] = mxDateTime(y,m,d)
    sems.sort( lambda x,y: cmp( x['date_debut_mx'], y['date_debut_mx'] ) )
    
    # 2-- Pour chaque semestre, trouve l'ensemble des etudiants venant de sem
    logt('B: etuds sets')
    sem['members'] = orig_set
    for s in sems:
        ins = context.do_formsemestre_inscription_list(
            args={'formsemestre_id' : s['formsemestre_id']}) # avec dems
        inset = Set([ i['etudid'] for i in ins ] )
        s['members'] = orig_set.intersection(inset)
        nb_dipl = 0 # combien de diplomes dans ce semestre ?
        if s['semestre_id'] == nt.parcours.NB_SEM:
            nt = context._getNotesCache().get_NotesTable(context, s['formsemestre_id']) #> get_etud_decision_sem
            for etudid in s['members']:
                dec = nt.get_etud_decision_sem(etudid)
                if dec and code_semestre_validant(dec['code']):
                    nb_dipl += 1
        s['nb_dipl'] = nb_dipl
    
    # 3-- Regroupe les semestres par date de debut
    P = [] #  liste de periodsem
    class periodsem:
        pass
    # semestre de depart:
    porigin = periodsem()
    d,m,y = [int(x) for x in sem['date_debut'].split('/')]
    porigin.datedebut = mxDateTime(y,m,d)
    porigin.sems = [sem]
    
    #
    tolerance = mx.DateTime.DateTimeDelta(45) # 45 days
    for s in sems:
        merged=False
        for p in P:
            if abs(s['date_debut_mx']-p.datedebut) < tolerance:
                p.sems.append(s)
                merged=True
                break
        if not merged:
            p = periodsem()
            p.datedebut = s['date_debut_mx']
            p.sems = [s]
            P.append(p)
    
    # 4-- regroupe par indice de semestre S_i
    indices_sems = list(Set([s['semestre_id'] for s in sems]))
    indices_sems.sort()
    for p in P:
        p.nb_etuds = 0 # nombre total d'etudiants dans la periode
        p.sems_by_id = DictDefault(defaultvalue=[])
        for s in p.sems:
            p.sems_by_id[s['semestre_id']].append(s)
            p.nb_etuds += len(s['members'])
    
    # 5-- Contruit table
    logt('C: build table')
    nb_initial = len(sem['members'])
    def fmtval(x):
        if not x:
            return '' # ne montre pas les 0
        if percent:
            return '%2.1f%%' % (100. * x / nb_initial)
        else:
            return x
    
    L = [{ 'row_title' : 'Origine: S%s' % sem['semestre_id'],
           porigin.datedebut : nb_initial,  '_css_row_class' : 'sorttop' }]
    if nb_initial < 10:
        etud_descr = _descr_etud_set(context, sem['members'])
        L[0]['_%s_help' % porigin.datedebut] = etud_descr
    for idx_sem in indices_sems:
        if idx_sem >= 0:
            d = { 'row_title' : 'S%s' % idx_sem }
        else:
            d = { 'row_title' : 'Autre semestre' }
        
        for p in P:
            etuds_period = Set()
            for s in p.sems:
                if s['semestre_id'] == idx_sem:
                    etuds_period = etuds_period.union(s['members'])
            nbetuds = len(etuds_period)
            if nbetuds:
                d[p.datedebut] = fmtval(nbetuds)
                if nbetuds < 10: # si peu d'etudiants, indique la liste
                    etud_descr = _descr_etud_set(context, etuds_period)
                    d['_%s_help' % p.datedebut] = etud_descr
        L.append(d)
    # Compte nb de d�missions et de r�-orientation par p�riode
    logt('D: cout dems reos')
    sem['dems'], sem['reos'] = _count_dem_reo(context, formsemestre_id, sem['members'])
    for p in P:
        p.dems = Set()
        p.reos = Set()
        for s in p.sems:
            d, r = _count_dem_reo(context, s['formsemestre_id'], s['members'])
            p.dems.update(d)
            p.reos.update(r)
    # Nombre total d'etudiants par periode
    l = { 'row_title' : 'Inscrits',
          'row_title_help' : "Nombre d'�tudiants inscrits",
          '_css_row_class':'sortbottom',
          porigin.datedebut : fmtval(nb_initial) }    
    for p in P:
        l[p.datedebut] = fmtval(p.nb_etuds)        
    L.append(l)
    # Nombre de d�missions par p�riode
    l = {'row_title' :'D�missions',
         'row_title_help' : 'Nombre de d�missions pendant la p�riode',
         '_css_row_class':'sortbottom',
         porigin.datedebut : fmtval(len(sem['dems'])) }
    if len(sem['dems']) < 10:
        etud_descr = _descr_etud_set(context, sem['dems'])
        l['_%s_help' % porigin.datedebut] = etud_descr
    for p in P:
        l[p.datedebut] = fmtval(len(p.dems))
        if len(p.dems) < 10:
            etud_descr = _descr_etud_set(context, p.dems)
            l['_%s_help' % p.datedebut] = etud_descr
    L.append(l)
    # Nombre de r�orientations par p�riode
    l = { 'row_title' : 'Echecs',
          'row_title_help' : 'R�-orientations (d�cisions NAR)',
          '_css_row_class':'sortbottom',
          porigin.datedebut : fmtval(len(sem['reos'])) }
    if len(sem['reos']) < 10:
        etud_descr = _descr_etud_set(context, sem['reos'])
        l['_%s_help' % porigin.datedebut] = etud_descr
    for p in P:
        l[p.datedebut] = fmtval(len(p.reos))
        if len(p.reos) < 10:
            etud_descr = _descr_etud_set(context, p.reos)
            l['_%s_help' % p.datedebut] = etud_descr
    L.append(l)
    # derniere ligne: nombre et pourcentage de diplomes
    l = { 'row_title' : 'Dipl�mes',
          'row_title_help' : 'Nombre de dipl�m�s � la fin de la p�riode',
          '_css_row_class' :'sortbottom'}
    for p in P:
        nb_dipl = 0
        for s in p.sems:
            nb_dipl += s['nb_dipl']
        l[p.datedebut] = fmtval(nb_dipl)
    L.append(l)
    
    columns_ids = [ p.datedebut for p in P ]
    titles = dict( [ (p.datedebut, p.datedebut.strftime('%d/%m/%y')) for p in P ] )
    titles[porigin.datedebut] = porigin.datedebut.strftime('%d/%m/%y')
    if percent:
        pp = '(en % de la population initiale) '
        titles['row_title'] = '%'
    else:
        pp = ''
        titles['row_title'] = ''
    if bac:
        dbac = ' (bacs %s)' % bac
    else:
        dbac = ''
    if bacspecialite:
        dbac += ' (sp�cialit� %s)' % bacspecialite
    if sexe:
        dbac += ' genre: %s' % sexe
    tab = GenTable( titles=titles, columns_ids=columns_ids,
                    rows=L, 
                    html_col_width='4em', html_sortable=True,
                    filename=make_filename('cohorte ' + sem['titreannee']),
                    origin = 'G�n�r� par %s le ' % VERSION.SCONAME + timedate_human_repr() + '',
                    caption = 'Suivi cohorte ' + pp + sem['titreannee'] + dbac,
                    page_title = 'Suivi cohorte ' + sem['titreannee'],
                    html_class='gt_table table_cohorte',
                    preferences=context.get_preferences(formsemestre_id)
                    )
    # Explication: liste des semestres associ�s � chaque date
    if not P:
        expl = ['<p class="help">(aucun �tudiant trouv� dans un semestre ult�rieur)</p>']
    else:
        expl = [ '<h3>Semestres associ�s � chaque date:</h3><ul>' ]
        for p in P:        
            expl.append( '<li><b>%s</b>:' %  p.datedebut.strftime('%d/%m/%y'))
            ls = []
            for s in p.sems:
                ls.append('<a href="formsemestre_status?formsemestre_id=%(formsemestre_id)s">%(titreannee)s</a>' % s )
            expl.append(', '.join(ls) + '</li>')
        expl.append('</ul>')
    logt('Z: table_suivi_cohorte done')
    return tab, '\n'.join(expl), bacs, bacspecialites, sexes

def formsemestre_suivi_cohorte(context, formsemestre_id, format='html', percent=1,
                               bac='', bacspecialite='', sexe='',
                               only_primo=False,
                               REQUEST=None):
    """Affiche suivi cohortes par numero de semestre
    """
    percent = int(percent)
    sem = context.get_formsemestre(formsemestre_id)
    tab, expl, bacs, bacspecialites, sexes = table_suivi_cohorte(
        context, formsemestre_id, percent=percent,
        bac=bac, bacspecialite=bacspecialite, sexe=sexe, only_primo=only_primo)
    tab.base_url = '%s?formsemestre_id=%s&percent=%s&bac=%s&bacspecialite=%s&sexe=%s' % (REQUEST.URL0, formsemestre_id, percent, bac, bacspecialite, sexe)
    t = tab.make_page(context, format=format, with_html_headers=False, REQUEST=REQUEST)
    if format != 'html':
        return t

    bacs = list(bacs)
    bacs.sort()
    bacspecialites = list(bacspecialites)
    bacspecialites.sort()
    sexes = list(sexes)
    sexes.sort()

    base_url = REQUEST.URL0
    burl = '%s?formsemestre_id=%s&bac=%s&bacspecialite=%s&sexe=%s' % (
        base_url, formsemestre_id, bac, bacspecialite, sexe)
    if percent:
        pplink = '<p><a href="%s&percent=0">Afficher les r�sultats bruts</a></p>' % burl
    else:
        pplink = '<p><a href="%s&percent=1">Afficher les r�sultats en pourcentages</a></p>' % burl
    help = pplink + """    
    <p class="help">Nombre d'�tudiants dans chaque semestre. Les dates indiqu�es sont les dates approximatives de <b>d�but</b> des semestres (les semestres commen�ant � des dates proches sont group�s). Le nombre de dipl�m�s est celui � la <b>fin</b> du semestre correspondant. Lorsqu'il y a moins de 10 �tudiants dans une case, vous pouvez afficher leurs noms en passant le curseur sur le chiffre.</p>
<p class="help">Les menus permettent de n'�tudier que certaines cat�gories d'�tudiants (titulaires d'un type de bac, gar�ons ou filles). La case "restreindre aux primo-entrants" permet de ne consid�rer que les �tudiants qui n'ont jamais �t� inscrits dans ScoDoc avant le semestre consid�r�.</p>
    """

    # form choix bac et/ou bacspecialite
    if bac:
        selected = ''
    else:
        selected = 'selected'
    F = [ """<form name="f" method="get" action="%s">
    <p>Bac: <select name="bac" onChange="document.f.submit()">
    <option value="" %s>tous</option>
    """ % (base_url,selected) ]
    for b in bacs:
        if bac == b:
            selected = 'selected'
        else:
            selected = ''
        F.append('<option value="%s" %s>%s</option>' % (b, selected, b))
    F.append('</select>')
    if bacspecialite:
        selected = ''
    else:
        selected = 'selected'
    F.append("""&nbsp; Bac/Specialit�: <select name="bacspecialite" onChange="document.f.submit()">
    <option value="" %s>tous</option>
    """ % selected)
    for b in bacspecialites:
        if bacspecialite == b:
            selected = 'selected'
        else:
            selected = ''
        F.append('<option value="%s" %s>%s</option>' % (b, selected, b))
    F.append('</select>')
    F.append("""&nbsp; Genre: <select name="sexe" onChange="document.f.submit()">
    <option value="" %s>tous</option>
    """ % selected)
    for b in sexes:
        if sexe == b:
            selected = 'selected'
        else:
            selected = ''
        F.append('<option value="%s" %s>%s</option>' % (b, selected, b))
    F.append('</select>')
    if only_primo:
        checked='checked=1'
    else:
        checked=''
    F.append('<br/><input type="checkbox" name="only_primo" onChange="document.f.submit()" %s>Restreindre aux primo-entrants</input>' % checked)
    F.append('<input type="hidden" name="formsemestre_id" value="%s"/>' % formsemestre_id)
    F.append('<input type="hidden" name="percent" value="%s"/>' % percent)
    F.append('</p></form>')
    
    H = [ context.sco_header(REQUEST, page_title=tab.page_title),
          """<h2 class="formsemestre">Suivi cohorte: devenir des �tudiants de ce semestre</h2>""",
          '\n'.join(F),
          t, help, expl,
          context.sco_footer(REQUEST)
          ]
    return '\n'.join(H)

def _descr_etud_set(context, etudids):
    "textual html description of a set of etudids"
    etuds = []
    for etudid in etudids:
        etuds.append(context.getEtudInfo(etudid=etudid, filled=True)[0])
    # sort by name
    etuds.sort( lambda x,y: cmp(x['nom'],y['nom']) )
    return ', '.join( [ e['nomprenom'] for e in etuds ] )

                   
def _count_dem_reo(context, formsemestre_id, etudids):
    "count nb of demissions and reorientation in this etud set"
    nt = context._getNotesCache().get_NotesTable(context, formsemestre_id) #> get_etud_etat, get_etud_decision_sem 
    dems = Set()
    reos = Set()
    for etudid in etudids:
        if nt.get_etud_etat(etudid) == 'D':
            dems.add(etudid)
        dec = nt.get_etud_decision_sem(etudid)
        if dec and dec['code'] in sco_codes_parcours.CODES_SEM_REO:
            reos.add(etudid)
    return dems, reos

"""OLDGEA:
27s pour  S1 F.I. classique Semestre 1 2006-2007
B 2.3s
C 5.6s
D 5.9s
Z 27s  => cache des semestres pour nt

� chaud: 3s
B: etuds sets: 2.4s => lent: N x getEtudInfo (non cach�)
"""

EXP_LIC = re.compile( r'licence', re.I )
EXP_LPRO = re.compile( r'professionnelle', re.I )

def _codesem(sem, short=True, prefix=''):
    "code semestre: S1 ou S1d"
    idx = sem['semestre_id']
    # semestre d�cal� ?
    # les semestres pairs normaux commencent entre janvier et mars
    # les impairs normaux entre aout et decembre
    d = ''
    if idx and idx > 0 and sem['date_debut']:
        mois_debut = int(sem['date_debut'].split('/')[1])
        if (idx % 2 and mois_debut < 3) or (idx % 2 == 0 and mois_debut >= 8):
            d = 'd'
    if idx == -1:
        if short:
            idx = 'Autre '
        else:
            idx = sem['titre'] + ' '
            idx = EXP_LPRO.sub('pro.', idx)
            idx = EXP_LIC.sub('Lic.', idx)
            prefix = '' # indique titre au lieu de Sn
    return '%s%s%s' % (prefix, idx, d)

def _codeparcoursetud(context, etud):
    """calcule un code de parcours pour un etudiant
    exemples:
       1234A pour un etudiant ayant effectu� S1, S2, S3, S4 puis diplome
       12D   pour un �tudiant en S1, S2 puis d�mission en S2
       12R   pour un etudiant en S1, S2 r�orient� en fin de S2    
    """
    p = []
    # �limine les semestres sp�ciaux sans parcours (LP...)
    sems = [ s for s in etud['sems'] if s['semestre_id'] >= 0 ]
    i = len(sems)-1
    while i >= 0:
        s = sems[i] # 'sems' est a l'envers, du plus recent au plus ancien        
        nt = context._getNotesCache().get_NotesTable(context, s['formsemestre_id']) #> get_etud_etat, get_etud_decision_sem
        p.append( _codesem(s) )
        # code etat sur dernier semestre seulement
        if i == 0:
            # D�mission
            if nt.get_etud_etat(etud['etudid']) == 'D':
                p.append( ':D' )
            else:
                dec = nt.get_etud_decision_sem(etud['etudid'])
                if dec and dec['code'] in sco_codes_parcours.CODES_SEM_REO:
                    p.append(':R')
                if dec and s['semestre_id'] == nt.parcours.NB_SEM and code_semestre_validant(dec['code']):
                    p.append(':A')
        i -= 1
    return ''.join(p)

def table_suivi_parcours(context, formsemestre_id):
    """Tableau recapitulant tous les parcours
    """
    sem = context.get_formsemestre(formsemestre_id)
    nt = context._getNotesCache().get_NotesTable(context, formsemestre_id) #> get_etudids, 
    etudids = nt.get_etudids()
    codes_etuds = DictDefault(defaultvalue=[])
    for etudid in etudids:
        etud = context.getEtudInfo(etudid=etudid, filled=True)[0]
        etud['codeparcours'] = _codeparcoursetud(context, etud)
        codes_etuds[etud['codeparcours']].append(etud)

    parcours = codes_etuds.keys()
    parcours.sort()
    L = []
    for p in parcours:
        nb = len(codes_etuds[p])
        l = { 'parcours' : p, 'nb' : nb }
        if nb < 10:
            l['_nb_help'] = _descr_etud_set(context,
                                            [e['etudid'] for e in codes_etuds[p]])
        L.append(l)
                
    # tri par effectifs d�croissants
    L.sort( lambda x,y: cmp(y['nb'], x['nb']) )
    tab = GenTable( columns_ids=('parcours', 'nb'), rows=L,
                    titles={ 'parcours' : 'Code parcours',
                             'nb' : "Nombre d'�tudiants" },
                    origin = 'G�n�r� par %s le ' % VERSION.SCONAME + timedate_human_repr() + '',
                    caption = 'Parcours suivis, �tudiants pass�s dans le semestre ' + sem['titreannee'],
                    page_title = 'Parcours ' + sem['titreannee'],
                    html_title = '<h2 class="formsemestre">Parcours suivis par les �tudiants de ce semestre</h2>',
                    html_next_section="""<table class="help">
                    <tr><td><tt>1, 2, ...</tt></td><td> num�ros de semestres</td></tr>
                    <tr><td><tt>1d, 2d, ...</tt></td><td>semestres "d�cal�s"</td></tr>
                    <tr><td><tt>:A</tt></td><td> �tudiants dipl�m�s</td></tr>
                    <tr><td><tt>:R</tt></td><td> �tudiants r�orient�s</td></tr>
                    <tr><td><tt>:D</tt></td><td> �tudiants d�missionnaires</td></tr>
                    </table>""",
                    bottom_titles =  { 'parcours' : 'Total', 'nb' : len(etudids) },
                    preferences=context.get_preferences(formsemestre_id)
                    )
    return tab

def formsemestre_suivi_parcours(context, formsemestre_id, format='html', REQUEST=None):
    """Effectifs dans les differents parcours possibles.
    """
    sem = context.get_formsemestre(formsemestre_id)
    tab = table_suivi_parcours(context, formsemestre_id)
    tab.base_url = '%s?formsemestre_id=%s' % (REQUEST.URL0, formsemestre_id)
    t = tab.make_page(context, format=format, with_html_headers=True, REQUEST=REQUEST)
    return t

# -------------
def graph_parcours(context, formsemestre_id, format='svg'):
    """
    """
    if not WITH_PYDOT:
        raise ScoValueError('pydot module is not installed')
    sem = context.get_formsemestre(formsemestre_id)
    nt = context._getNotesCache().get_NotesTable(context, formsemestre_id) #> get_etudids, get_etud_decision_sem, 
    etudids = nt.get_etudids()
    log('graph_parcours: %s etuds' % len(etudids))
    if not etudids:
        return ''
    edges = DictDefault(defaultvalue=Set()) # {(formsemestre_id_origin, formsemestre_id_dest) : etud_set}
    sems = {}
    effectifs = DictDefault(defaultvalue=Set()) # formsemestre_id : etud_set
    isolated_nodes = []
    connected_nodes = Set()
    diploma_nodes = []
    dem_nodes = {} # formsemestre_id : noeud pour demissionnaires
    nar_nodes = {} # formsemestre_id : noeud pour NAR
    for etudid in etudids:
        etud = context.getEtudInfo(etudid=etudid, filled=True)[0]
        next = None
        for s in etud['sems']: # du plus recent au plus ancien
            nt = context._getNotesCache().get_NotesTable(context, s['formsemestre_id']) #> get_etud_decision_sem, get_etud_etat
            dec = nt.get_etud_decision_sem(etudid)
            if next:
                if s['semestre_id'] == nt.parcours.NB_SEM and dec and code_semestre_validant(dec['code']) and nt.get_etud_etat(etudid) == 'I':
                    # cas particulier du diplome puis poursuite etude
                    edges[('_dipl_'+s['formsemestre_id'], next['formsemestre_id'])].add(etudid)
                else:
                    edges[(s['formsemestre_id'], next['formsemestre_id'])].add(etudid)
                connected_nodes.add(s['formsemestre_id'])
                connected_nodes.add(next['formsemestre_id'])
            else:
                isolated_nodes.append(s['formsemestre_id'])
            sems[s['formsemestre_id']] = s
            effectifs[s['formsemestre_id']].add(etudid)
            next = s
            # ajout noeud pour demissionnaires
            if nt.get_etud_etat(etudid) == 'D':
                nid = '_dem_' + s['formsemestre_id']
                dem_nodes[s['formsemestre_id']] = nid
                edges[(s['formsemestre_id'], nid)].add(etudid)
            # ajout noeud pour NAR (seulement pour noeud de depart)
            if s['formsemestre_id'] == formsemestre_id and dec and dec['code'] == 'NAR':
                nid = '_nar_' + s['formsemestre_id']
                nar_nodes[s['formsemestre_id']] = nid
                edges[(s['formsemestre_id'], nid)].add(etudid)
            # si "terminal", ajoute noeud pour diplomes
            if s['semestre_id'] == nt.parcours.NB_SEM:                
                if dec and code_semestre_validant(dec['code']) and nt.get_etud_etat(etudid) == 'I':
                    nid = '_dipl_'+s['formsemestre_id']
                    edges[(s['formsemestre_id'], nid)].add(etudid)
                    diploma_nodes.append(nid)
    #
    g = pydot.graph_from_edges(edges.keys())
    for fid in isolated_nodes:
        if not fid in connected_nodes:
            n = pydot.Node(name=fid)
            g.add_node(n)
    g.set('rankdir', 'LR') # left to right
    g.set_fontname('Helvetica')
    if format == 'svg':
        g.set_bgcolor('#fffff0') # ou 'transparent'
    # titres des semestres:
    for s in sems.values():
        n = pydot_get_node(g, s['formsemestre_id'])
        log("s['formsemestre_id'] = %s" % s['formsemestre_id'])
        log('n=%s' % n)
        log('get=%s' % g.get_node(s['formsemestre_id']))
        log('nodes names = %s' % [ x.get_name() for x in g.get_node_list() ])
        if s['modalite'] and s['modalite'] != 'FI':
            modalite = ' ' + s['modalite']
        else:
            modalite = ''
        label = ('%s%s\\n%d/%s - %d/%s\\n%d' %
                 (_codesem(s, short=False, prefix='S'), modalite,
                  s['mois_debut_ord'], s['annee_debut'][2:],
                  s['mois_fin_ord'], s['annee_fin'][2:],
                  len(effectifs[s['formsemestre_id']])))
        n.set( 'label', suppress_accents(label) )
        n.set_fontname('Helvetica')
        n.set_fontsize(8.0)
        n.set_width(1.2)
        n.set_shape('box')
        n.set_URL('formsemestre_status?formsemestre_id=' + s['formsemestre_id'])
    # semestre de depart en vert
    n = pydot_get_node(g, formsemestre_id)
    n.set_color('green')
    # demissions en rouge, octagonal
    for nid in dem_nodes.values():
        n = pydot_get_node(g, nid)
        n.set_color('red')
        n.set_shape('octagon')
        n.set('label', 'Dem.')
        
    # NAR en rouge, Mcircle
    for nid in nar_nodes.values():
        n = pydot_get_node(g, nid)
        n.set_color('red')
        n.set_shape('Mcircle')
        n.set('label', 'NAR')
    # diplomes:
    for nid in diploma_nodes:
        n = pydot_get_node(g, nid)
        n.set_color('red')
        n.set_shape('ellipse')
        n.set('label', 'Diplome') # bug si accent (pas compris pourquoi)
    # Ar�tes:
    bubbles = {} # substitue titres pour bulle aides: src_id:dst_id : etud_descr
    for (src_id,dst_id) in edges.keys():
        e = g.get_edge(src_id, dst_id)
        e.set('arrowhead','normal')
        e.set( 'arrowsize', 1 )
        e.set_label(len(edges[(src_id,dst_id)]))
        e.set_fontname('Helvetica')
        e.set_fontsize(8.0)
        # bulle avec liste etudiants
        if len(edges[(src_id, dst_id)]) < 10:
            etud_descr = _descr_etud_set(context, edges[(src_id, dst_id)])
            bubbles[src_id+':'+dst_id] = etud_descr
            e.set_URL('__xxxetudlist__?' + src_id+':'+dst_id)
    # Genere graphe    
    f, path = tempfile.mkstemp('.gr')
    g.write(path=path, format=format)
    data = open(path,'r').read()
    log('dot generated %d bytes in %s format' % (len(data),format))
    if not data:
        log('graph.to_string=%s' % g.to_string() )
        raise ValueError('Erreur lors de la g�n�ration du document au format %s' % format)
    os.unlink(path)
    if format == 'svg':
        # dot g�n�re un document XML complet, il faut enlever l'en-t�te
        data = '<svg' + '<svg'.join( data.split('<svg')[1:])
        # Substitution des titres des URL des aretes pour bulles aide
        def repl(m):
            return '<a title="%s"' % bubbles[m.group('sd')]
        exp = re.compile(r'<a.*?href="__xxxetudlist__\?(?P<sd>\w*:\w*).*?".*?xlink:title=".*?"', re.M)
        data = exp.sub(repl, data)
        # Substitution des titres des boites (semestres)
        exp1 = re.compile(r'<a xlink:href="formsemestre_status\?formsemestre_id=(?P<fid>\w*).*?".*?xlink:title="(?P<title>.*?)"', re.M|re.DOTALL)
        def repl_title(m):            
            return '<a xlink:href="formsemestre_status?formsemestre_id=%s" xlink:title="%s"' % (m.group('fid'), suppress_accents(sems[m.group('fid')]['titreannee'])) # evite accents car svg utf-8 vs page en latin1...
        data = exp1.sub(repl_title, data)
        # Substitution de Arial par Helvetica (new prblem in Debian 5) ???
        # bug turnaround: il doit bien y avoir un endroit ou regler cela ?
        # cf http://groups.google.com/group/pydot/browse_thread/thread/b3704c53e331e2ec
        data = data.replace( 'font-family:Arial', 'font-family:Helvetica' )
        
    return data

def formsemestre_graph_parcours(context, formsemestre_id, format='html', REQUEST=None):
    """Graphe suivi cohortes
    """
    sem = context.get_formsemestre(formsemestre_id)
    if format == 'pdf':
        doc = graph_parcours(context, formsemestre_id, format='pdf')
        filename = make_filename('flux ' + sem['titreannee'])
        return sco_pdf.sendPDFFile(REQUEST, doc, filename + '.pdf' )
    elif format == 'png':
        # 
        doc = graph_parcours(context, formsemestre_id, format='png')
        filename = make_filename('flux ' + sem['titreannee'])
        REQUEST.RESPONSE.setHeader('Content-Disposition', 'attachment; filename=%s' % filename)
        REQUEST.RESPONSE.setHeader('Content-type', 'image/png' )
        return doc
    elif format == 'html':
        url = urllib.quote("formsemestre_graph_parcours?formsemestre_id=%(formsemestre_id)s&format="%sem)
        H = [ context.sco_header(REQUEST, page_title='Parcours �tudiants de %(titreannee)s'%sem, no_side_bar=True),
              """<h2 class="formsemestre">Parcours des �tudiants de ce semestre</h2>""",

              graph_parcours(context, formsemestre_id),

              """<p>Origine et devenir des �tudiants inscrits dans %(titreannee)s""" % sem,
              # En Debian 4, dot ne genere pas du pdf, et epstopdf ne marche pas sur le .ps ou ps2 g�n�r�s par dot
              # mais c'est OK en Debian 5
              """(<a href="%spdf">version pdf</a> <span class="help">[non disponible partout]</span>""" % url,
              """, <a href="%spng">image PNG</a>)""" % url,
              """</p>""",
              """<p class="help">Cette page ne s'affiche correctement que sur les navigateurs r�cents.</p>""",

              """<p class="help">Le graphe permet de suivre les �tudiants inscrits dans le semestre
              s�lectionn� (dessin� en vert). Chaque rectangle repr�sente un semestre (cliquez dedans
              pour afficher son tableau de bord). Les fl�ches indiquent le nombre d'�tudiants passant
              d'un semestre � l'autre (s'il y en a moins de 10, vous pouvez visualiser leurs noms en
              passant la souris sur le chiffre).
              </p>""",
              context.sco_footer(REQUEST)
              ]
        REQUEST.RESPONSE.setHeader('Content-type', 'application/xhtml+xml' )
        return '\n'.join(H)
    else:
        raise ValueError('invalid format: %s' % format)

