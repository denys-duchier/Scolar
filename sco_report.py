# -*- mode: python -*-
# -*- coding: iso8859-15 -*-

##############################################################################
#
# Gestion scolarite IUT
#
# Copyright (c) 2001 - 2008 Emmanuel Viennet.  All rights reserved.
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
from sets import Set
from mx.DateTime import DateTime as mxDateTime
import mx.DateTime

def formsemestre_etuds_stats(context, sem):
    """Récupère liste d'etudiants avec etat et decision.
    """
    nt = context._getNotesCache().get_NotesTable(context, sem['formsemestre_id'])
    T = nt.get_table_moyennes_triees()
    # Construit liste d'étudiants du semestre avec leur decision
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
        # Ajout clé 'bac-specialite'
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

def _results_by_category(etuds, category='', result='', category_name=None):
    """Construit table: categories (eg types de bacs) en ligne, décisions jury en colonnes

    etuds est une liste d'etuds (dicts).
    category et result sont des clés de etud (category définie les lignes, result les colonnes).

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
    titles['DEM'] = 'Dém.' # démissions
    for i in range(len(categories)):
        if categories[i] == '':
            categories[i] = '?'
    lines_titles = [category_name] + categories + ['Total']
    return GenTable( titles=titles, columns_ids=codes, rows=C, lines_titles=lines_titles,
                     html_col_width='4em', html_sortable=True )


# pages
def formsemestre_report(context, formsemestre_id, etuds, REQUEST=None,
                        category='bac', result='codedecision', 
                        category_name='', result_name='',
                        title='Statistiques'):    
    """
    Tableau sur résultats (result) par type de category bac
    """
    sem = context.get_formsemestre(formsemestre_id)
    if not category_name:
        category_name = category
    if not result_name:
        result_name = result
    if result_name == 'codedecision':
        result_name = 'résultats'
    #
    tab = _results_by_category(etuds, category=category, category_name=category_name,
                               result=result)
    #
    tab.filename = make_filename('stats ' + sem['titreannee'])
    
    tab.origin = 'Généré par %s le ' % VERSION.SCONAME + timedate_human_repr() + ''
    tab.caption = 'Répartition des résultats par %s, semestre %s' % (category_name, sem['titreannee'])
    tab.html_caption = "Répartition des résultats par %s." % category_name
    tab.base_url = '%s?formsemestre_id=%s' % (REQUEST.URL0, formsemestre_id)
    return tab



# def formsemestre_report_bacs(context, formsemestre_id, format='html', REQUEST=None):
#     """
#     Tableau sur résultats par type de bac
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
#         title =  """<h2>Résultats de <a href="formsemestre_status?formsemestre_id=%(formsemestre_id)s">%(titreannee)s</a></h2>""" % sem,
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
    if etuds:
        if allkeys:
            keys = etuds[0].keys()
        else:
            # clés présentées à l'utilisateur:
            keys = ['annee_bac', 'annee_naissance', 'bac', 'specialite', 'bac-specialite',
                    'codedecision', 'etat', 'sexe', 'qualite', 'villelycee' ]
        keys.sort()
        F = [ """<form name="f" method="get"><p>
              Colonnes: <select name="result" onChange="document.f.submit()">""" ]
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
        title =  """<h2>Statistiques de <a href="formsemestre_status?formsemestre_id=%(formsemestre_id)s">%(titreannee)s</a></h2>""" % sem,
        format=format, REQUEST=REQUEST, with_html_headers=False)
    if format!='html':
        return t    
    H = [ context.sco_header(REQUEST, page_title=title),
          t, '\n'.join(F),
          context.sco_footer(REQUEST)
          ]
    return '\n'.join(H)

# --------------------------------------------------------------------------
def table_suivi_cohorte(context, formsemestre_id):
    """
    Tableau indicant le nombre d'etudiants de la cohorte dans chaque état:
    Etat     date_debut_Sn   date1  date2 ...
    S_n       #inscrits en Sn
    S_n+1
    ...
    S_last
    Diplome
    Sorties

    Determination des dates: on regroupe les semestres commençant à des dates proches

    """
    sem = context.get_formsemestre(formsemestre_id) # sem est le semestre origine
    # 1-- Liste des semestres posterieurs dans lesquels ont été les etudiants de sem
    nt = context._getNotesCache().get_NotesTable(context, formsemestre_id)
    etudids = nt.get_etudids()
    
    S = {} # set of formsemestre_id
    for etudid in etudids:
        etud = context.getEtudInfo(etudid=etudid, filled=True)[0]
        for s in etud['sems']:
            if DateDMYtoISO(s['date_debut']) > DateDMYtoISO(sem['date_debut']):
                S[s['formsemestre_id']] = s
    sems = S.values()
    # tri les semestres par date de debut
    for s in sems:
        d,m,y = [int(x) for x in s['date_debut'].split('/')]
        s['date_debut_mx'] = mxDateTime(y,m,d)
    sems.sort( lambda x,y: cmp( x['date_debut_mx'], y['date_debut_mx'] ) )
    
    # 2-- Pour chaque semestre, trouve l'ensemble des etudiants venant de sem
    orig_set = Set(etudids)
    sem['members'] = orig_set
    for s in sems:
        ins = context.do_formsemestre_inscription_listinscrits(s['formsemestre_id'])
        inset = Set([ i['etudid'] for i in ins ] )
        s['members'] = orig_set.intersection(inset)
        nb_dipl = 0             # combien de diplomes dans ce semestre ?
        if s['semestre_id'] == sco_codes_parcours.DUT_NB_SEM:
            nt = context._getNotesCache().get_NotesTable(context, s['formsemestre_id'])
            for etudid in s['members']:
                dec = nt.get_etud_decision_sem(etudid)
                if dec and dec['code'] == 'ADM':
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
    lines_titles=['', 'Origine: S%s' % sem['semestre_id'] ]
    L = [{ porigin.datedebut : len(sem['members']),  '_css_row_class' : 'sorttop' }]
    for idx_sem in indices_sems:
        if idx_sem >= 0:
            lines_titles.append('S%s' % idx_sem)
        else:
            lines_titles.append('Autre semestre')
        d = {}
        for p in P:
            etuds_period = Set()
            for s in p.sems:
                if s['semestre_id'] == idx_sem:
                    etuds_period = etuds_period.union(s['members'])
            nbetuds = len(etuds_period)
            d[p.datedebut] = nbetuds or '' # laisse case vide au lieu de 0
            if nbetuds and nbetuds < 10: # si peu d'etudiants, indique la liste
                etud_descr = _descr_etud_set(context, etuds_period)
                d['_%s_help' % p.datedebut] = etud_descr
        L.append(d)
    # nombre total d'etudiants par periode
    lines_titles.append('Inscrits')
    l = {'_css_row_class':'sortbottom', porigin.datedebut : len(sem['members']) }
    for p in P:
        l[p.datedebut] = p.nb_etuds
    L.append(l)
    # derniere ligne: nombre et pourcentage de diplomes
    lines_titles.append('Diplômes')
    NbDipl = {}
    for p in P:
        nb_dipl = 0
        for s in p.sems:
            nb_dipl += s['nb_dipl']
        if nb_dipl:
            NbDipl[p.datedebut] = '%s (%2.1f%%)' % (nb_dipl, 100. * nb_dipl / len(sem['members']))
    
    NbDipl['_css_row_class'] = 'sortbottom' # reste en bas de la table
    L.append(NbDipl)
    
    columns_ids = [porigin.datedebut] + [ p.datedebut for p in P ]
    titles = dict( [ (p.datedebut, p.datedebut.strftime('%d/%m/%y')) for p in P ] )
    titles[porigin.datedebut] = porigin.datedebut.strftime('%d/%m/%y')
    tab = GenTable( titles=titles, columns_ids=columns_ids,
                    rows=L, lines_titles=lines_titles,
                    html_col_width='4em', html_sortable=True,
                    filename=make_filename('cohorte ' + sem['titreannee']),
                    origin = 'Généré par %s le ' % VERSION.SCONAME + timedate_human_repr() + '',
                    caption = 'Suivi cohorte ' + sem['titreannee'],
                    page_title = 'Suivi cohorte ' + sem['titreannee'],
                    html_title =  """<h2>Suivi cohorte de <a href="formsemestre_status?formsemestre_id=%(formsemestre_id)s">%(titreannee)s</a></h2>""" % sem
                    )
    # Explication: liste des semestres associés à chaque date
    if not P:
        expl = ['<p class="help">(aucun étudiant trouvé dans un semestre ultérieur)</p>']
    else:
        expl = [ '<h3>Semestres associés à chaque date:</h3><ul>' ]
        for p in P:        
            expl.append( '<li><b>%s</b>:' %  p.datedebut.strftime('%d/%m/%y'))
            ls = []
            for s in p.sems:
                ls.append('<a href="formsemestre_status?formsemestre_id=%(formsemestre_id)s">%(titreannee)s</a>' % s )
            expl.append(', '.join(ls) + '</li>')
        expl.append('</ul>')
    return tab, '\n'.join(expl)

def formsemestre_suivi_cohorte(context, formsemestre_id, format='html', REQUEST=None):
    """Affiche suivi cohortes par numero de semestre
    """
    sem = context.get_formsemestre(formsemestre_id)
    tab, expl = table_suivi_cohorte(context, formsemestre_id)
    tab.base_url = '%s?formsemestre_id=%s' % (REQUEST.URL0, formsemestre_id)
    t = tab.make_page(context, format=format, with_html_headers=False, REQUEST=REQUEST)

    help = """<p class="help">Nombre d'étudiants dans chaque semestre. Les dates indiquées sont les dates approximatives de <b>début</b> de semestres (les semestres commençant à des dates proches sont groupés). Le nombre de diplômés est celui à la <b>fin</b> du semestre correspondant. Lorsqu'il y a moins de 10 étudiants dans une case, vous pouvez afficher leurs noms en passant le curseur sur le chiffre.</p>"""
    
    H = [ context.sco_header(REQUEST, page_title=tab.page_title),
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

                   
