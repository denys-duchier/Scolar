# -*- mode: python -*-
# -*- coding: iso8859-15 -*-

##############################################################################
#
# Gestion scolarite IUT
#
# Copyright (c) 2001 - 2010 Emmanuel Viennet.  All rights reserved.
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

"""G�n�ration des bulletins de notes
"""
from email.MIMEMultipart import MIMEMultipart
from email.MIMEText import MIMEText
from email.MIMEBase import MIMEBase
from email.Header import Header
from email import Encoders

from notes_table import *
import htmlutils, time
import pdfbulletins
import sco_pvjury
from sco_pdf import PDFLOCK
import sco_formsemestre_status
import sco_photos
from ZAbsences import getAbsSemEtud

from reportlab.lib.colors import Color

def make_formsemestre_bulletinetud_pdf(context, formsemestre_id, etudid, I,
                                       version='long', # short, long, selectedevals
                                       format = 'pdf', # pdf or pdfpart
                                       REQUEST=None):
    """Bulletin en PDF

    Appelle une fonction g�n�rant le PDF � partir des informations "bulletin",
    selon les pr�f�rences du semestre.

    """
    if not version in ('short','long','selectedevals'):
        raise ValueError('invalid version code !')

    bul_pdf_style = 'classic' # � remplacer par preference

    pdf_generators = {
        'classic' : make_formsemestre_bulletinetud_pdf_classic,
        }
    
    func = pdf_generators.get(bul_pdf_style, None)
    if func:
        pdf_data, filename = func(context, formsemestre_id, etudid, I, version=version, format=format, REQUEST=REQUEST)
    else:
        raise ValueError('invalid PDF style for bulletins (%s)' % bul_pdf_style)
    
    return pdf_data, filename


def formsemestre_bulletinetud_dict(context, formsemestre_id, etudid, version='long', REQUEST=None):
    """Collecte informations pour bulletin de notes
    Retourne un dictionnaire.
    Le contenu du dictionnaire d�pend des options (rangs, ...) 
    et de la version choisie (short, long, selectedevals).
    """
    if not version in ('short','long','selectedevals'):
        raise ValueError('invalid version code !')
    
    I = { 'etudid' : etudid }
    if REQUEST:
        I['server_name'] = REQUEST.BASE0
    else:
        I['server_name'] = ''
    
    nt = context._getNotesCache().get_NotesTable(context, formsemestre_id) #> toutes notes
    
    # Infos sur l'etudiant
    I['etud'] = context.getEtudInfo(etudid=etudid,filled=1)[0] 
    I['descr_situation'] = I['etud']['inscriptionstr']
    if I['etud']['inscription_formsemestre_id']:
        I['descr_situation_html'] = """<a href="formsemestre_status?formsemestre_id=%s">%s</a>""" % (I['etud']['inscription_formsemestre_id'], I['descr_situation'])
    else:
        I['descr_situation_html'] = I['descr_situation']
    # Groupes:
    partitions = sco_groups.get_partitions_list(context, formsemestre_id, with_default=False)
    partitions_etud_groups = {} # { partition_id : { etudid : group } }
    for partition in partitions:
        pid=partition['partition_id']
        partitions_etud_groups[pid] = sco_groups.get_etud_groups_in_partition(context, pid)
    # --- Absences
    if context.get_preference('bul_show_abs', formsemestre_id):
        AbsSemEtud = getAbsSemEtud(context, formsemestre_id, etudid)
        I['nbabs'] =  AbsSemEtud.CountAbs()
        I['nbabsjust'] = AbsSemEtud.CountAbsJust()
    else:
        I['nbabs'] = ''
        I['nbabsjust'] = ''
    # --- Decision Jury
    infos, dpv = _etud_descr_situation_semestre(
        context, etudid, formsemestre_id,
        format='html',
        show_date_inscr=context.get_preference('bul_show_date_inscr', formsemestre_id),
        show_decisions=context.get_preference('bul_show_decision', formsemestre_id),
        show_uevalid=context.get_preference('bul_show_uevalid', formsemestre_id))
    if dpv:
        I['decision_sem'] = dpv['decisions'][0]['decision_sem']
    else:
        I['decision_sem'] = ''
    I['infos_jury'] = infos

    I['etud_etat_html'] = nt.get_etud_etat_html(etudid)
    I['etud_etat'] = nt.get_etud_etat(etudid)
    I['filigranne'] = ''    
    I['demission'] = ''
    if I['etud_etat'] == 'D':
        I['demission'] = '(D�mission)'
        I['filigranne'] = 'D�mission'
    elif context.get_preference('bul_show_temporary', formsemestre_id) and not I['decision_sem']:
        I['filigranne'] = 'Provisoire'
    
    # --- Appreciations
    cnx = context.GetDBConnexion()   
    apprecs = scolars.appreciations_list(
        cnx,
        args={'etudid':etudid, 'formsemestre_id' : formsemestre_id } )
    I['appreciations'] = apprecs 
    I['appreciations_txt'] = [ x['date'] + ': ' + x['comment'] for x in apprecs ]

    # --- Notes
    ues = nt.get_ues()
    modimpls = nt.get_modimpls()
    moy_gen = nt.get_etud_moy_gen(etudid)
    I['nb_inscrits'] = len(nt.rangs)
    I['moy_gen'] = fmt_note(moy_gen)
    I['moy_min'] = fmt_note(nt.moy_min)
    I['moy_max'] = fmt_note(nt.moy_max)
    I['moy_moy'] = fmt_note(nt.moy_moy) # moyenne des moyennes generales
    if type(moy_gen) != StringType and type(nt.moy_moy) != StringType:
        I['moy_gen_bargraph_html'] = '&nbsp;' + htmlutils.horizontal_bargraph(moy_gen*5, nt.moy_moy*5)
    else:
        I['moy_gen_bargraph_html'] = ''
    
    if nt.get_moduleimpls_attente() or context.get_preference('bul_show_rangs', formsemestre_id) == 0:
        # n'affiche pas le rang sur le bulletin s'il y a des
        # notes en attente dans ce semestre
        rang = '(attente)'
        rang_gr = {}
        ninscrits_gr = {}
    else:
        rang = str(nt.get_etud_rang(etudid))
        rang_gr, ninscrits_gr, gr_name = get_etud_rangs_groups(
            context, etudid, formsemestre_id, partitions, partitions_etud_groups, nt)
    I['rang'] = rang
    I['nbetuds'] = len(nt.rangs)
    if context.get_preference('bul_show_rangs', formsemestre_id):
        I['rang_txt'] = 'Rang %s / %d' % (rang, I['nbetuds']-nt.nb_demissions)
    else:
        I['rang_txt'] = ''
    I['note_max'] = 20. # notes toujours sur 20
    I['bonus_sport_culture'] = nt.bonus[etudid]
    # Liste les UE / modules /evals
    I['ues'] = []
    for ue in ues:
        u = ue.copy()
        I['ues'].append(u)
        ue_status = nt.get_etud_ue_status(etudid, ue['ue_id'])
        u['ue_status'] = ue_status # { 'moy_ue', 'coef_ue', ...}
        if ue['type'] != UE_SPORT:
            u['cur_moy_ue_txt'] = fmt_note(ue_status['cur_moy_ue'])
        else:
            u['cur_moy_ue_txt'] = '(note sp�ciale, bonus de %s points)' % nt.bonus[etudid]
        u['moy_ue_txt']  = fmt_note(ue_status['moy_ue'])
        u['coef_ue_txt'] = fmt_coef(ue_status['coef_ue'])
        
        if ue_status['is_capitalized']:
            sem_origin = context.get_formsemestre(ue_status['formsemestre_id'])
            u['ue_descr_txt'] =  'Capitalis�e le %s' % DateISOtoDMY(ue_status['event_date'])
            u['ue_descr_html'] = '<a href="formsemestre_bulletinetud?formsemestre_id=%s&etudid=%s" title="%s" class="bull_link">%s</a>' % (sem_origin['formsemestre_id'], etudid, sem_origin['titreannee'], u['ue_descr_txt'])
        else:
            if context.get_preference('bul_show_ue_rangs', formsemestre_id) and ue['type'] != UE_SPORT:
                if nt.get_moduleimpls_attente():
                     u['ue_descr_txt'] = '(attente)/%s' % (nt.ue_rangs[ue['ue_id']][1]-nt.nb_demissions)
                else:
                    u['ue_descr_txt'] = '%s/%s' % (nt.ue_rangs[ue['ue_id']][0][etudid], nt.ue_rangs[ue['ue_id']][1]-nt.nb_demissions)
                u['ue_descr_html'] = u['ue_descr_txt']
            else:
                u['ue_descr_txt'] = u['ue_descr_html'] = ''

        u['modules'] = [] # modules de l'UE (dans le semestre courant)
        u['modules_capitalized'] = [] # modules de l'UE capitalis�e (liste vide si pas capitalis�e)
        if ue_status['is_capitalized']:
            log('cap details   %s' % ue_status['moy_ue'])
            if ue_status['moy_ue'] != 'NA' and ue_status['formsemestre_id']:
                # detail des modules de l'UE capitalisee
                nt_cap = context._getNotesCache().get_NotesTable(context, ue_status['formsemestre_id']) #> toutes notes
                
                _ue_mod_bulletin(context, u['modules_capitalized'], etudid, formsemestre_id, ue_status['capitalized_ue_id'], nt_cap.get_modimpls(), nt_cap, version)
        
        if ue_status['cur_moy_ue'] != 'NA':
            # detail des modules courants
            _ue_mod_bulletin(context, u['modules'], etudid, formsemestre_id, ue['ue_id'], modimpls, nt, version)
    #
    return I

def _ue_mod_bulletin(context, mods, etudid, formsemestre_id, ue_id, modimpls, nt, version):
    """Infos sur les modules (et �valuations) dans une UE
    (ajoute les informations aux modimpls)
    """
    bul_show_mod_rangs = context.get_preference('bul_show_mod_rangs', formsemestre_id)
    bul_show_abs_modules = context.get_preference('bul_show_abs_modules', formsemestre_id)
    if bul_show_abs_modules:
        sem = context.Notes.get_formsemestre(formsemestre_id)
        debut_sem = DateDMYtoISO(sem['date_debut'])
        fin_sem = DateDMYtoISO(sem['date_fin'])
    
    ue_modimpls = [ mod for mod in modimpls if mod['module']['ue_id'] == ue_id ]
    for modimpl in ue_modimpls:
        mod = modimpl.copy()
        mod_moy = nt.get_etud_mod_moy(modimpl['moduleimpl_id'], etudid)  # peut etre 'NI'
        if bul_show_abs_modules:
            mod_abs = [context.Absences.CountAbs(etudid=etudid, debut=debut_sem, fin=fin_sem, moduleimpl_id=modimpl['moduleimpl_id']), context.Absences.CountAbsJust(etudid=etudid, debut=debut_sem, fin=fin_sem, moduleimpl_id=modimpl['moduleimpl_id'])]
            mod['mod_abs_txt'] = fmt_abs(mod_abs)
        
        mod['mod_moy_txt'] = fmt_note(mod_moy)
        if mod['mod_moy_txt'][:2] == 'NA':
            mod['mod_moy_txt'] = '-'
        mod['mod_coef_txt']= fmt_coef(modimpl['module']['coefficient'])
        
        if mod['mod_moy_txt'] != 'NI': # ne montre pas les modules 'non inscrit'
            mods.append(mod)
            mod['stats'] = nt.get_mod_stats(modimpl['moduleimpl_id'])
            mod['mod_descr_txt'] = 'Module %s, coef. %s (%s)' % (
                modimpl['module']['titre'],
                fmt_coef(modimpl['module']['coefficient']),
                context.Users.user_info(modimpl['responsable_id'])['nomcomplet'])
            link_mod = '<a class="bull_link" href="moduleimpl_status?moduleimpl_id=%s" title="%s">' % (
                modimpl['moduleimpl_id'], mod['mod_descr_txt'])
            if context.get_preference('bul_show_codemodules', formsemestre_id):
                mod['code'] = modimpl['module']['code']
                mod['code_html'] = link_mod + mod['code'] + '</a>'
            else:
                mod['code'] = mod['code_html'] = ''
            mod['name'] = modimpl['module']['abbrev'] or modimpl['module']['titre'] or ''
            mod['name_html'] = link_mod + mod['name'] + '</a>'
            if bul_show_mod_rangs and mod['mod_moy_txt'] != '-':
                rg = nt.mod_rangs[modimpl['moduleimpl_id']]
                if nt.get_moduleimpls_attente():
                    mod['mod_rang'] = '(attente)'
                else:
                    mod['mod_rang'] = rg[0][etudid]
                mod['mod_eff']   = rg[1] # effectif dans ce module
                mod['mod_rang_txt'] = '%s/%s' % (mod['mod_rang'], mod['mod_eff'])                    
            else:
                mod['mod_rang_txt'] = ''
            mod_descr = 'Module %s, coef. %s (%s)' % (
                modimpl['module']['titre'],
                fmt_coef(modimpl['module']['coefficient']),
                context.Users.user_info(modimpl['responsable_id'])['nomcomplet'])
            link_mod = '<a class="bull_link" href="moduleimpl_status?moduleimpl_id=%s" title="%s">' % (modimpl['moduleimpl_id'], mod_descr)
            if context.get_preference('bul_show_codemodules', formsemestre_id):
                mod['code_txt'] = modimpl['module']['code']
                mod['code_html'] = link_mod + mod['code_txt'] + '</a>'
            else:
                mod['code_txt'] = ''
                mod['code_html'] = ''
            # Evaluations: notes de chaque eval
            evals = nt.get_evals_in_mod(modimpl['moduleimpl_id'])
            mod['evaluations'] = []
            for e in evals:
                e = e.copy()
                mod['evaluations'].append(e)
                if e['visibulletin'] == '1' or version == 'long':
                    e['name'] = e['description'] or 'le %s' % e['jour']
                e['name_html'] = '<a class="bull_link" href="evaluation_listenotes?evaluation_id=%s&format=html&tf-submitted=1">%s</a>' % (e['evaluation_id'], e['name'])
                val = e['notes'].get(etudid, {'value':'NP'})['value'] # NA si etud demissionnaire
                if val == 'NP':
                    e['note_txt'] = 'nd'
                    e['note_html'] = '<span class="note_nd">nd</span>'
                    e['coef_txt'] = ''
                else:
                    e['note_txt'] = fmt_note(val, note_max=e['note_max'])
                    e['note_html'] = e['note_txt']
                    e['coef_txt'] = fmt_coef(e['coefficient'])                


def make_formsemestre_bulletinetud_html(
    context, formsemestre_id, etudid, I,
    version='long', # short, long, selectedevals
    REQUEST=None):
    """Bulletin en HTML
    Nouvelle version, mai 2010
    """
    if not version in ('short','long','selectedevals'):
        raise ValueError('invalid version code !')
    format = 'html'
    
    bul_show_abs_modules = context.get_preference('bul_show_abs_modules', formsemestre_id)
    
    sem = context.get_formsemestre(formsemestre_id)
    if sem['bul_bgcolor']:
        bgcolor = sem['bul_bgcolor']
    else:
        bgcolor = 'background-color: rgb(255,255,240)'
    authuser = REQUEST.AUTHENTICATED_USER

    linktmpl  = '<span onclick="toggle_vis_ue(this);" class="toggle_ue">%s</span>'
    minuslink = linktmpl % context.icons.minus_img.tag(border="0", alt="-")
    pluslink  = linktmpl % context.icons.plus_img.tag(border="0", alt="+")
    
    H = [ '<table class="notes_bulletin" style="background-color: %s;">' % bgcolor  ]
    
    if context.get_preference('bul_show_minmax', formsemestre_id):
        minmax = '<span class="bul_minmax" title="[min, max] promo">[%s, %s]</span>' % (I['moy_min'], I['moy_max'])
        bargraph = ''
    else:
        minmax = ''
        bargraph = I['moy_gen_bargraph_html']
    # 1ere ligne: titres
    H.append( '<tr><td class="note_bold">Moyenne</td><td class="note_bold cell_graph">%s%s%s%s</td>'
              % (I['moy_gen'], I['etud_etat_html'], minmax, bargraph) )
    H.append( '<td class="note_bold">%s</td>' % I['rang_txt'] )
    H.append( '<td class="note_bold">Note/20</td><td class="note_bold">Coef</td>')
    if bul_show_abs_modules:
        H.append( '<td class="note_bold">Abs (J. / N.J.)</td>' )
    H.append('</tr>')
    def list_modules(ue_modules, rowstyle):
        for mod in ue_modules:
            if mod['mod_moy_txt'] == 'NI':
                continue # saute les modules o� on n'est pas inscrit
            H.append('<tr class="notes_bulletin_row_mod%s">' % rowstyle)
            if context.get_preference('bul_show_minmax_mod', formsemestre_id):
                rang_minmax = '%s <span class="bul_minmax" title="[min, max] UE">[%s, %s]</span>' % (mod['mod_rang_txt'], fmt_note(mod['stats']['min']), fmt_note(mod['stats']['max']))
            else:
                rang_minmax = mod['mod_rang_txt'] # vide si pas option rang
            H.append('<td>%s</td><td>%s</td><td>%s</td><td class="note">%s</td><td>%s</td>'
                     % (mod['code_html'], mod['name_html'], 
                        rang_minmax, 
                        mod['mod_moy_txt'], mod['mod_coef_txt'] ))
            if bul_show_abs_modules:
                H.append('<td>%s</td>' % mod['mod_abs_txt'])
            H.append('</tr>')
            
            if version != 'short':
                # --- notes de chaque eval:
                for e in mod['evaluations']:
                    if e['visibulletin'] == '1' or version == 'long':
                        H.append('<tr class="notes_bulletin_row_eval%s">' % rowstyle)
                        H.append('<td>%s</td><td>%s</td><td class="bull_nom_eval">%s</td><td class="note">%s</td><td class="bull_coef_eval">%s</td></tr>'
                                 % ('','', e['name_html'], e['note_html'], e['coef_txt']))
    
    # Contenu table: UE apres UE
    for ue in I['ues']:
        ue_descr = ue['ue_descr_html']
        coef_ue  = ue['coef_ue_txt']
        rowstyle = ''
        plusminus = minuslink # 
        if ue['ue_status']['is_capitalized']:
            if context.get_preference('bul_show_ue_cap_details', formsemestre_id):
                plusminus = minuslink
                hide = ''
            else:
                plusminus = pluslink
                hide = 'sco_hide'
            H.append('<tr class="notes_bulletin_row_ue">' )
            H.append('<td class="note_bold">%s%s</td><td class="note_bold">%s</td><td>%s</td><td>%s</td><td>%s</td>' 
                     %  (plusminus, ue['acronyme'], ue['moy_ue_txt'], ue_descr, '', coef_ue))
            if bul_show_abs_modules:
                H.append('<td></td>')
            H.append('</tr>')
            list_modules(ue['modules_capitalized'], ' bul_row_ue_cap %s' % hide)
                         
            coef_ue  = ''
            ue_descr = '(en cours, non prise en compte)'
            rowstyle = ' bul_row_ue_cur' # style css pour indiquer UE non prise en compte

        H.append('<tr class="notes_bulletin_row_ue">' )
        if context.get_preference('bul_show_minmax', formsemestre_id):
            moy_txt = '%s <span class="bul_minmax" title="[min, max] UE">[%s, %s]</span>' % (ue['cur_moy_ue_txt'], ue['min'], ue['max'])
        else:
            moy_txt = ue['cur_moy_ue_txt']

        H.append('<td class="note_bold">%s%s</td><td class="note_bold">%s</td><td>%s</td><td>%s</td><td>%s</td>'
                 % (minuslink, ue['acronyme'], moy_txt, ue_descr, '', coef_ue))
        if bul_show_abs_modules:
            H.append('<td></td>')
        H.append('</tr>')
        list_modules(ue['modules'], rowstyle)

    
    H.append('</table>')
    # --- Absences
    H.append("""<p>
    <a href="../Absences/CalAbs?etudid=%(etudid)s" class="bull_link">
    <b>Absences :</b> %(nbabs)s demi-journ�es, dont %(nbabsjust)s justifi�es
    (pendant ce semestre).
    </a></p>
        """ % I )
    # --- Decision Jury
    if I['infos_jury']['situation']:
        H.append( """<p class="bull_situation">%(situation)s</p>""" % I['infos_jury'] )
    # --- Appreciations
    # le dir. des etud peut ajouter des appreciations,
    # mais aussi le chef (perm. ScoEtudInscrit)
    can_edit_app = ((str(authuser) == sem['responsable_id'])
                    or (authuser.has_permission(ScoEtudInscrit,context)))
    H.append('<div class="bull_appreciations">')
    if I['appreciations']:
        H.append('<p><b>Appr�ciations</b></p>')
    for app in I['appreciations']:
        if can_edit_app:
            mlink = '<a class="stdlink" href="appreciation_add_form?id=%s">modifier</a> <a class="stdlink" href="appreciation_add_form?id=%s&suppress=1">supprimer</a>'%(app['id'],app['id'])
        else:
            mlink = ''
        H.append('<p><span class="bull_appreciations_date">%s</span>%s<span class="bull_appreciations_link">%s</span></p>'
                     % (app['date'], app['comment'], mlink ) )
    if can_edit_app:
        H.append('<p><a class="stdlink" href="appreciation_add_form?etudid=%s&formsemestre_id=%s">Ajouter une appr�ciation</a></p>' % (etudid, formsemestre_id))
    H.append('</div>')

    # ---------------
    return '\n'.join(H)


def make_formsemestre_bulletinetud_pdf_classic(context, formsemestre_id, etudid, I,
                                               version='long', # short, long, selectedevals
                                               format = 'pdf', # pdf or pdfpart
                                               REQUEST=None):
    """Bulletin en PDF
    Format "classique ScoDoc".
    Rewritten, mai 2010.
    """    
    sem = context.get_formsemestre(formsemestre_id)

    bul_show_abs_modules = context.get_preference('bul_show_abs_modules', formsemestre_id)
    
    LINEWIDTH = 0.5

    class TableStyle:
        def __init__(self):
            self.PdfStyle = [ ('FONTNAME', (0,0), (-1,0), 'Helvetica-Bold'),
                              ('LINEBELOW', (0,0), (-1,0), LINEWIDTH, Color(0,0,0)),
                            ]
            self.tabline = 0
        def newline(self, ue_type=None):
            self.tabline += 1
            if ue_type == 'cur': # UE courante non prise en compte (car capitalisee)
                self.PdfStyle.append(('BACKGROUND', (0,self.tabline), (-1,self.tabline),
                                  Color(210/255.,210/255.,210/255.) ))
            
        def ueline(self): # met la ligne courante du tableau pdf en style 'UE'
            self.newline()
            i = self.tabline
            self.PdfStyle.append(('FONTNAME', (0,i), (-1,i), 'Helvetica-Bold'))
            self.PdfStyle.append(('BACKGROUND', (0,i), (-1,i),
                                  Color(170/255.,187/255.,204/255.) ))
        def modline(self, ue_type=None): # met la ligne courante du tableau pdf en style 'Module'
            self.newline(ue_type=ue_type)
            i = self.tabline
            self.PdfStyle.append(('LINEABOVE', (0,i), (-1,i),
                             1, Color(170/255.,170/255.,170/255.)))            
    
    S = TableStyle()
    P = [] # elems pour gen. pdf

    if context.get_preference('bul_show_minmax', formsemestre_id):
        minmax = ' <font size="8">[%s, %s]</font>' % (I['moy_min'], I['moy_max'])
    else:
        minmax = ''

    t = ['Moyenne', '%s%s%s' % (I['moy_gen'], I['etud_etat_html'], minmax),
         I['rang_txt'], 
         'Note/20', 
         'Coef']
    if bul_show_abs_modules:
        t.append( 'Abs (J. / N.J.)')
    P.append(t)
    
    def list_modules(ue_modules, ue_type=None):
        for mod in ue_modules:
            if mod['mod_moy_txt'] == 'NI':
                continue # saute les modules o� on n'est pas inscrit
            S.modline(ue_type=ue_type)
            if context.get_preference('bul_show_minmax_mod', formsemestre_id):
                rang_minmax = '%s <font size="8">[%s, %s]</font>' % (mod['mod_rang_txt'], fmt_note(mod['stats']['min']), fmt_note(mod['stats']['max']))
            else:
                rang_minmax = mod['mod_rang_txt'] # vide si pas option rang
            t = [mod['code'], mod['name'], rang_minmax, mod['mod_moy_txt'], mod['mod_coef_txt']]
            if bul_show_abs_modules:
                t.append(mod['mod_abs_txt'])
            P.append(t)
            if version != 'short':
                # --- notes de chaque eval:
                for e in mod['evaluations']:
                    if e['visibulletin'] == '1' or version == 'long':
                        S.newline(ue_type=ue_type)
                        t = ['','', e['name'], e['note_txt'], e['coef_txt']]
                        if bul_show_abs_modules:
                            t.append('')
                        P.append(t)
    
    for ue in I['ues']:
        ue_descr = ue['ue_descr_txt']
        coef_ue  = ue['coef_ue_txt']
        ue_type = None
        if ue['ue_status']['is_capitalized']:
            t = [ue['acronyme'], ue['moy_ue_txt'], ue_descr, '', coef_ue]
            if bul_show_abs_modules:
                t.append('')
            P.append(t)
            coef_ue = ''
            ue_descr = '(en cours, non prise en compte)'
            S.ueline()
            if context.get_preference('bul_show_ue_cap_details', formsemestre_id):
                list_modules(ue['modules_capitalized'])
            ue_type = 'cur'
        
        if context.get_preference('bul_show_minmax', formsemestre_id):
            moy_txt = '%s <font size="8">[%s, %s]</font>' % (ue['cur_moy_ue_txt'], ue['min'], ue['max'])
        else:
            moy_txt = ue['cur_moy_ue_txt']
        t = [ue['acronyme'], moy_txt, ue_descr, '', coef_ue]
        if bul_show_abs_modules:
            t.append('')
        P.append(t)
        S.ueline()
        list_modules(ue['modules'], ue_type=ue_type)
    
    #
    etud = I['etud']
    if context.get_preference('bul_show_abs', formsemestre_id):
        etud['nbabs'] = I['nbabs']
        etud['nbabsjust'] = I['nbabsjust']
    stand_alone = (format != 'pdfpart')

    I['infos_jury'].update( {
            'appreciations' :  I['appreciations_txt'],
            'situation_jury' : I['infos_jury']['situation'],
            'demission' : I['demission'],
            'filigranne' : I['filigranne'],            
            } )
    diag = ''
    try:
        PDFLOCK.acquire()
        pdfbul, diag = pdfbulletins.pdfbulletin_etud(
            etud, sem, P, S.PdfStyle,
            I['infos_jury'], stand_alone=stand_alone, filigranne=I['filigranne'],
            server_name=I['server_name'], 
            context=context )
    finally:
        PDFLOCK.release()
    if diag:
        log('pdf_error: %s' % diag )
        raise NoteProcessError(diag)
    
    dt = time.strftime( '%Y-%m-%d' )
    filename = 'bul-%s-%s-%s.pdf' % (sem['titre_num'], dt, etud['nom'])
    filename = unescape_html(filename).replace(' ','_').replace('&','')
    return pdfbul, filename


# -------- Bulletin en XML
# (fonction s�par�e pour simplifier le code,
#  mais attention a la maintenance !)
def make_xml_formsemestre_bulletinetud(
    context, formsemestre_id, etudid,
    doc=None, # XML document
    force_publishing=False,
    xml_nodate=False,
    REQUEST=None,
    xml_with_decisions=False, # inlue les decisions m�me si non publi�es
    version='long'
    ):
    "bulletin au format XML"
    log('xml_bulletin( formsemestre_id=%s, etudid=%s )' % (formsemestre_id, etudid))
    if REQUEST:
        REQUEST.RESPONSE.setHeader('Content-type', XML_MIMETYPE)
    if not doc:            
        doc = jaxml.XML_document( encoding=SCO_ENCODING )
    
    sem = context.get_formsemestre(formsemestre_id)
    if sem['bul_hide_xml'] == '0' or force_publishing:
        published=1
    else:
        published=0
    if xml_nodate:
        docdate = ''
    else:
        docdate = datetime.datetime.now().isoformat()
    
    doc.bulletinetud( etudid=etudid, formsemestre_id=formsemestre_id,
                      date=docdate,
                      publie=published,
                      etape_apo=sem['etape_apo'] or '',
                      etape_apo2=sem['etape_apo2'] or '')

    # Infos sur l'etudiant
    etudinfo = context.getEtudInfo(etudid=etudid,filled=1)[0]
    doc._push()
    doc.etudiant(
        etudid=etudid, code_nip=etudinfo['code_nip'], code_ine=etudinfo['code_ine'],
        nom=quote_xml_attr(etudinfo['nom']),
        prenom=quote_xml_attr(etudinfo['prenom']),
        sexe=quote_xml_attr(etudinfo['sexe']),
        photo_url=quote_xml_attr(sco_photos.etud_photo_url(context, etudinfo)),
        email=quote_xml_attr(etudinfo['email']))    
    doc._pop()

    # Disponible pour publication ?
    if not published:
        return doc # stop !

    # Groupes:
    partitions = sco_groups.get_partitions_list(context, formsemestre_id, with_default=False)
    partitions_etud_groups = {} # { partition_id : { etudid : group } }
    for partition in partitions:
        pid=partition['partition_id']
        partitions_etud_groups[pid] = sco_groups.get_etud_groups_in_partition(context, pid)

    nt = context._getNotesCache().get_NotesTable(context, formsemestre_id) #> toutes notes
    ues = nt.get_ues()
    modimpls = nt.get_modimpls()
    nbetuds = len(nt.rangs)
    mg = fmt_note(nt.get_etud_moy_gen(etudid))
    if nt.get_moduleimpls_attente() or context.get_preference('bul_show_rangs', formsemestre_id) == 0:
        # n'affiche pas le rang sur le bulletin s'il y a des
        # notes en attente dans ce semestre
        rang = ''
        rang_gr = {}
        ninscrits_gr = {}
    else:
        rang = str(nt.get_etud_rang(etudid))
        rang_gr, ninscrits_gr, gr_name = get_etud_rangs_groups(
            context, etudid, formsemestre_id, partitions, partitions_etud_groups, nt)
    
    doc._push()
    doc.note( value=mg, min=fmt_note(nt.moy_min), max=fmt_note(nt.moy_max), moy=fmt_note(nt.moy_moy) )
    doc._pop()
    doc._push()
    doc.rang( value=rang, ninscrits=nbetuds )
    doc._pop()
    if rang_gr:
        for partition in partitions:
            doc._push()
            doc.rang_group( group_type=partition['partition_name'],
                            group_name=gr_name[partition['partition_id']],
                            value=rang_gr[partition['partition_id']], 
                            ninscrits=ninscrits_gr[partition['partition_id']] )
            doc._pop()
    doc._push()
    doc.note_max( value=20 ) # notes toujours sur 20
    doc._pop()
    doc._push()
    doc.bonus_sport_culture( value=nt.bonus[etudid] )
    doc._pop()
    # Liste les UE / modules /evals
    for ue in ues:
        ue_status = nt.get_etud_ue_status(etudid, ue['ue_id'])
        doc._push()
        doc.ue( id=ue['ue_id'],
                numero=quote_xml_attr(ue['numero']),
                acronyme=quote_xml_attr(ue['acronyme']),
                titre=quote_xml_attr(ue['titre']) )            
        doc._push()
        doc.note( value=fmt_note(ue_status['cur_moy_ue']), 
                  min=fmt_note(ue['min']), max=fmt_note(ue['max']) )
        doc._pop()
        doc._push()
        doc.rang( value=str(nt.ue_rangs[ue['ue_id']][0][etudid]) )
        doc._pop()
        doc._push()
        doc.effectif( value=str(nt.ue_rangs[ue['ue_id']][1] - nt.nb_demissions) )
        doc._pop()
        # Liste les modules de l'UE 
        ue_modimpls = [ mod for mod in modimpls if mod['module']['ue_id'] == ue['ue_id'] ]
        for modimpl in ue_modimpls:
            mod_moy = fmt_note(nt.get_etud_mod_moy(modimpl['moduleimpl_id'], etudid))
            if mod_moy == 'NI': # ne mentionne pas les modules ou n'est pas inscrit
                continue
            mod = modimpl['module']
            doc._push()
            doc.module( id=modimpl['moduleimpl_id'], code=mod['code'],
                        coefficient=mod['coefficient'],
                        numero=mod['numero'],
                        titre=quote_xml_attr(mod['titre']),
                        abbrev=quote_xml_attr(mod['abbrev']) )
            doc._push()
            modstat = nt.get_mod_stats(modimpl['moduleimpl_id'])
            doc.note( value=mod_moy, 
                      min=fmt_note(modstat['min']), max=fmt_note(modstat['max'])
                      )
            doc._pop()
            if context.get_preference('bul_show_mod_rangs', formsemestre_id):
                doc._push()
                doc.rang( value=nt.mod_rangs[modimpl['moduleimpl_id']][0][etudid] )
                doc._pop()
                doc._push()
                doc.effectif( value=nt.mod_rangs[modimpl['moduleimpl_id']][1] )
                doc._pop()
            # --- notes de chaque eval:
            evals = nt.get_evals_in_mod(modimpl['moduleimpl_id'])
            if version != 'short':
                for e in evals:
                    if e['visibulletin'] == '1' or version == 'long':
                        doc._push()
                        doc.evaluation(jour=DateDMYtoISO(e['jour'], null_is_empty=True),
                               heure_debut=TimetoISO8601(e['heure_debut'], null_is_empty=True),
                               heure_fin=TimetoISO8601(e['heure_fin'], null_is_empty=True),
                               coefficient=e['coefficient'],
                               description=quote_xml_attr(e['description']))
                        val = e['notes'].get(etudid, {'value':'NP'})['value'] # NA si etud demissionnaire
                        val = fmt_note(val, note_max=e['note_max'] )
                        doc.note( value=val )
                        doc._pop()
            doc._pop()
        doc._pop()
        # UE capitalisee (listee seulement si meilleure que l'UE courante)
        if ue_status['is_capitalized']:
            doc._push()
            doc.ue_capitalisee( id=ue['ue_id'],
                                numero=quote_xml_attr(ue['numero']),
                                acronyme=quote_xml_attr(ue['acronyme']),
                                titre=quote_xml_attr(ue['titre']) )
            doc._push()
            doc.note( value=fmt_note(ue_status['moy_ue']) )
            doc._pop()
            doc._push()
            doc.coefficient_ue( value=fmt_note(ue_status['coef_ue']) )
            doc._pop()
            doc._push()
            doc.date_capitalisation(
                value=DateDMYtoISO(ue_status['event_date']) )
            doc._pop()
            doc._pop()
    # --- Absences
    if  context.get_preference('bul_show_abs', formsemestre_id):
        debut_sem = DateDMYtoISO(sem['date_debut'])
        fin_sem = DateDMYtoISO(sem['date_fin'])
        AbsEtudSem = getAbsSemEtud(context, formsemestre_id, etudid)
        nbabs = AbsEtudSem.CountAbs()
        nbabsjust = AbsEtudSem.CountAbsJust()
        doc._push()
        doc.absences(nbabs=nbabs, nbabsjust=nbabsjust )
        doc._pop()
    # --- Decision Jury
    if context.get_preference('bul_show_decision', formsemestre_id) or xml_with_decisions:
        infos, dpv = _etud_descr_situation_semestre(
            context, etudid, formsemestre_id, format='xml',
            show_uevalid=context.get_preference('bul_show_uevalid',formsemestre_id))
        doc.situation( quote_xml_attr(infos['situation']) )
        if dpv:
            decision = dpv['decisions'][0]
            etat = decision['etat']
            if decision['decision_sem']:
                code = decision['decision_sem']['code']
            else:
                code = ''
            doc._push()
            doc.decision( code=code, etat=etat)
            doc._pop()
            if decision['decisions_ue']: # and context.get_preference('bul_show_uevalid', formsemestre_id): always publish (car utile pour export Apogee)
                for ue_id in decision['decisions_ue'].keys():                
                    ue = context.do_ue_list({ 'ue_id' : ue_id})[0]
                    doc._push()
                    doc.decision_ue( ue_id=ue['ue_id'],
                                     numero=quote_xml_attr(ue['numero']),
                                     acronyme=quote_xml_attr(ue['acronyme']),
                                     titre=quote_xml_attr(ue['titre']),
                                     code=decision['decisions_ue'][ue_id]['code']
                                     )
                    doc._pop()
            
            for aut in decision['autorisations']:
                doc._push()
                doc.autorisation_inscription( semestre_id=aut['semestre_id'] )
                doc._pop()
        else:
            doc._push()
            doc.decision( code='', etat='DEM' )
            doc._pop()
    # --- Appreciations
    cnx = context.GetDBConnexion() 
    apprecs = scolars.appreciations_list(
        cnx,
        args={'etudid':etudid, 'formsemestre_id' : formsemestre_id } )
    for app in apprecs:
        doc.appreciation( quote_xml_attr(app['comment']), date=DateDMYtoISO(app['date']))
    return doc


def get_etud_rangs_groups(context, etudid, formsemestre_id, 
                           partitions, partitions_etud_groups, 
                           nt):
    """Ramene rang et nb inscrits dans chaque partition
    """
    rang_gr, ninscrits_gr, gr_name = {}, {}, {}
    for partition in partitions:
        if partition['partition_name'] != None:
            partition_id = partition['partition_id']

            if etudid in partitions_etud_groups[partition_id]:
                group = partitions_etud_groups[partition_id][etudid]
            
                rang_gr[partition_id], ninscrits_gr[partition_id] =\
                    nt.get_etud_rang_group(etudid, group['group_id'])
                gr_name[partition_id] = group['group_name']
            else: # etudiant non present dans cette partition
                rang_gr[partition_id], ninscrits_gr[partition_id] = '', ''
                gr_name[partition_id] = ''

    return rang_gr, ninscrits_gr, gr_name


def _etud_descr_situation_semestre(context, etudid, formsemestre_id, ne='',
                                   format='html', # currently unused
                                   show_decisions=True,
                                   show_uevalid=True,
                                   show_date_inscr=True
                                  ):
    """Dict d�crivant la situation de l'�tudiant dans ce semestre.
    Si format == 'html', peut inclure du balisage html (actuellement inutilis�)

    situation : chaine r�sumant en fran�ais la situation de l'�tudiant.
                Par ex. "Inscrit le 31/12/1999. D�cision jury: Valid�. ..."
    
    date_inscription : (vide si show_date_inscr est faux)
    date_demission   : (vide si pas demission ou si show_date_inscr est faux)
    descr_inscription : "Inscrit" ou "Pas inscrit[e]"
    descr_demission   : "D�mission le 01/02/2000" ou vide si pas de d�mission
    decision_jury     :  "Valid�", "Ajourn�", ... (code semestre)
    descr_decision_jury : "D�cision jury: Valid�" (une phrase)
    decisions_ue        : noms (acronymes) des UE valid�es, s�par�es par des virgules.
    descr_decisions_ue  : ' UE acquises: UE1, UE2', ou vide si pas de dec. ou si pas show_uevalid
    """
    cnx = context.GetDBConnexion()
    infos = DictDefault(defaultvalue='')
    
    # --- Situation et d�cisions jury

    # demission/inscription ?
    events = scolars.scolar_events_list(
        cnx, args={'etudid':etudid, 'formsemestre_id':formsemestre_id} )
    date_inscr = None
    date_dem = None
    date_echec = None
    for event in events:
        event_type = event['event_type']
        if event_type == 'INSCRIPTION':
            if date_inscr:
                # plusieurs inscriptions ???
                #date_inscr += ', ' +   event['event_date'] + ' (!)'
                # il y a eu une erreur qui a laiss� un event 'inscription'
                # on l'efface:
                log('etud_descr_situation_semestre: removing duplicate INSCRIPTION event !')
                scolars.scolar_events_delete( cnx, event['event_id'] )
            else:
                date_inscr = event['event_date']
        elif event_type == 'DEMISSION':
            assert date_dem == None, 'plusieurs d�missions !'
            date_dem = event['event_date']
    if show_date_inscr: 
        if not date_inscr:
            infos['date_inscription'] = ''
            infos['descr_inscription'] = 'Pas inscrit%s.' % ne            
        else:
            infos['date_inscription'] = date_inscr            
            infos['descr_inscription'] = 'Inscrit%s le %s.' % (ne, date_inscr)
    else:
        infos['date_inscription'] = ''
        infos['descr_inscription'] = ''

    infos['situation'] = infos['descr_inscription']
    if date_dem:
        infos['descr_demission'] = 'D�mission le %s.' % date_dem
        infos['date_demission'] = date_dem
        infos['descr_decision_jury'] = 'D�mission'
        infos['situation'] += ' ' + infos['descr_demission']
        return infos, None # ne donne pas les dec. de jury pour les demissionnaires
    
    dpv = sco_pvjury.dict_pvjury(context, formsemestre_id, etudids=[etudid])

    if not show_decisions:
        return infos, dpv

    # Decisions de jury:
    pv = dpv['decisions'][0]
    dec = ''
    if pv['decision_sem_descr']:
        infos['decision_jury'] = pv['decision_sem_descr']
        infos['descr_decision_jury'] = 'D�cision jury: ' + pv['decision_sem_descr'] + '. ' 
        dec = infos['descr_decision_jury']
    
    if pv['decisions_ue_descr'] and show_uevalid:
        infos['decisions_ue'] = pv['decisions_ue_descr']
        infos['descr_decisions_ue'] = ' UE acquises: ' + pv['decisions_ue_descr']
        dec += infos['descr_decisions_ue']

    infos['situation'] += ' ' + dec + '.'
    if pv['autorisations_descr']:
        infos['situation'] += " Autoris� � s'inscrire en %s." % pv['autorisations_descr']
    
    return infos, dpv



# ------ Page bulletin
def formsemestre_bulletinetud(context, etudid=None, formsemestre_id=None,
                              format='html', version='long',
                              xml_with_decisions=False,
                              REQUEST=None):
    "page bulletin de notes"
    try:
        etud = context.getEtudInfo(filled=1, REQUEST=REQUEST)[0]
        etudid = etud['etudid']
    except:
        return context.log_unknown_etud(REQUEST, format=format)
    
    sem = context.get_formsemestre(formsemestre_id)

    R = []
    if format == 'html' or format == 'mailpdf':
        R.append( _formsemestre_bulletinetud_header_html(context, etud, etudid, sem,
                                                   formsemestre_id, format, version, REQUEST) )
    
    R.append( do_formsemestre_bulletinetud(context, formsemestre_id, etudid,
                                           format=format, version=version,
                                           xml_with_decisions=xml_with_decisions,
                                           REQUEST=REQUEST)[0])
    
    if format == 'html' or format == 'mailpdf':
        R.append("""<p>Situation actuelle: """)
        if etud['inscription_formsemestre_id']:
            R.append("""<a href="formsemestre_status?formsemestre_id=%s">"""
                     % etud['inscription_formsemestre_id'])
        R.append(etud['inscriptionstr'])
        if etud['inscription_formsemestre_id']:
            R.append("""</a>""")
        R.append("""</p>""")

        # --- Pied de page
        R.append( context.sco_footer(REQUEST) )

    return ''.join(R)



def do_formsemestre_bulletinetud(context, formsemestre_id, etudid,
                                 version='long', # short, long, selectedevals
                                 format='html',
                                 REQUEST=None,
                                 nohtml=False,
                                 xml_with_decisions=False # force decisions dans XML
                                 ):
    """G�n�re le bulletin au format demand�.
    Retourne: (bul, filigranne)
    o� bul est au format demand� (html, pdf, xml)
    et filigranne est un message � placer en "filigranne" (eg "Provisoire").
    """
    I = formsemestre_bulletinetud_dict(context, formsemestre_id, etudid, REQUEST=REQUEST)
    etud = I['etud']
    
    if format == 'xml':
        bul = repr(make_xml_formsemestre_bulletinetud(
            context, formsemestre_id,  etudid, REQUEST=REQUEST,
            xml_with_decisions=xml_with_decisions, version=version))
        return bul, I['filigranne']
    
    elif format == 'html':            
        htm = make_formsemestre_bulletinetud_html(
            context, formsemestre_id, etudid, I,
            version=version, REQUEST=REQUEST)
        return htm, I['filigranne']
    
    elif format == 'pdf' or format == 'pdfpart':
        bul, filename = make_formsemestre_bulletinetud_pdf(
            context, formsemestre_id, etudid, I, version=version, format=format,
            REQUEST=REQUEST)
        if format == 'pdf':
            return sendPDFFile(REQUEST, bul, filename), I['filigranne'] # unused ret. value
        else:
            return bul, I['filigranne']
    
    elif format == 'mailpdf':
        # format mailpdf: envoie le pdf par mail a l'etud, et affiche le html
        if nohtml:
            htm = '' # speed up if html version not needed
        else:
            htm = make_formsemestre_bulletinetud_html(
                context, formsemestre_id, etudid, I, version=version, REQUEST=REQUEST)
        
        pdfdata, filename = make_formsemestre_bulletinetud_pdf(
            context, formsemestre_id, etudid, I, version=version, format='pdf', REQUEST=REQUEST)

        if not etud['email']:
            return ('<div class="boldredmsg">%s n\'a pas d\'adresse e-mail !</div>'
                    % etud['nomprenom']) + htm, I['filigranne']
        #
        mail_bulletin(context, formsemestre_id, I, pdfdata, filename)
        
        return ('<div class="head_message">Message mail envoy� � %s</div>'
                % (etud['emaillink'])) + htm, I['filigranne']
    
    else:
        raise ValueError("do_formsemestre_bulletinetud: invalid format (%s)" % format)


def mail_bulletin(context, formsemestre_id, I, pdfdata, filename):
    """Send bulletin by email to etud
    """
    etud = I['etud']
    webmaster = context.get_preference('bul_mail_contact_addr', formsemestre_id)
    dept = unescape_html(context.get_preference('DeptName',formsemestre_id))
    copy_addr = context.get_preference('email_copy_bulletins',formsemestre_id)            
    intro_mail = context.get_preference('bul_intro_mail', formsemestre_id)
    
    if intro_mail:
        hea = intro_mail % { 'nomprenom' : etud['nomprenom'], 'dept':dept, 'webmaster':webmaster }
    else:
        hea = ''
    
    msg = MIMEMultipart()
    subj = Header( 'Relev� de note de %s' % etud['nomprenom'],  SCO_ENCODING )
    recipients = [ etud['email'] ] 
    msg['Subject'] = subj
    msg['From'] = context.get_preference('email_from_addr',formsemestre_id)
    msg['To'] = ' ,'.join(recipients)
    if copy_addr:
        msg['Bcc'] = copy_addr.strip()
    # Guarantees the message ends in a newline
    msg.epilogue = ''
    # Text
    txt = MIMEText( hea, 'plain', SCO_ENCODING )
    msg.attach(txt)
    # Attach pdf
    att = MIMEBase('application', 'pdf')
    att.add_header('Content-Disposition', 'attachment', filename=filename)
    att.set_payload( pdfdata )
    Encoders.encode_base64(att)
    msg.attach(att)
    log('mail bulletin a %s' % msg['To'] )
    context.sendEmail(msg)


def _formsemestre_bulletinetud_header_html(context, etud, etudid, sem,
                                           formsemestre_id=None, format=None, version=None, REQUEST=None):
    authuser = REQUEST.AUTHENTICATED_USER
    uid = str(authuser)
    H = [ context.sco_header(page_title='Bulletin de %(nomprenom)s' % etud, REQUEST=REQUEST,
                             javascripts=['jQuery/jquery.js', 'js/bulletin.js']),
          """<table class="bull_head"><tr><td>
          <h2><a class="discretelink" href="ficheEtud?etudid=%(etudid)s">%(nomprenom)s</a></h2>
          """ % etud,
          """
          <form name="f" method="GET" action="%s">"""%REQUEST.URL0,
          """Bulletin <span class="bull_liensemestre"><a href="formsemestre_status?formsemestre_id=%(formsemestre_id)s">
          %(titremois)s</a></span> 
          <br/>""" % sem,
          """<table><tr>""",
          """<td>�tabli le %s (notes sur 20)</td>""" % time.strftime('%d/%m/%Y � %Hh%M'),
          """<td><span class="rightjust">
             <input type="hidden" name="formsemestre_id" value="%s"></input>""" % formsemestre_id,
          """<input type="hidden" name="etudid" value="%s"></input>""" % etudid,
          """<input type="hidden" name="format" value="%s"></input>""" % format,
          """<select name="version" onChange="document.f.submit()" class="noprint">""",
          ]
    for (v,e) in ( ('short', 'Version courte'),
                   ('selectedevals', 'Version interm�diaire'),
                   ('long', 'Version compl�te')):
        if v == version:
            selected = ' selected'
        else:
            selected = ''
        H.append('<option value="%s"%s>%s</option>' % (v, selected, e))
    H.append("""</select></td>""")
    # Menu
    url = REQUEST.URL0
    qurl = urllib.quote_plus( url + '?' + REQUEST.QUERY_STRING )
    
    menuBul = [
        { 'title' : 'R�glages bulletins',
          'url' : 'formsemestre_edit_options?formsemestre_id=%s&target_url=%s' % (formsemestre_id, qurl),
          'enabled' : (uid == sem['responsable_id']) or authuser.has_permission(ScoImplement, context),
          },
        { 'title' : 'Version papier (pdf)',
          'url' : url + '?formsemestre_id=%s&etudid=%s&format=pdf&version=%s' % (formsemestre_id,etudid,version),
          },
        { 'title' : "Envoi par mail � l'�tudiant",
          'url' : url + '?formsemestre_id=%s&etudid=%s&format=mailpdf&version=%s' % (formsemestre_id,etudid,version),
          'enabled' : etud['email'] # possible slt si on a un mail...
          },
        { 'title' : 'Version XML',
          'url' : url + '?formsemestre_id=%s&etudid=%s&format=xml&version=%s' % (formsemestre_id,etudid,version),
          },
        { 'title' : 'Ajouter une appr�ciation',
          'url' : 'appreciation_add_form?etudid=%s&formsemestre_id=%s' % (etudid, formsemestre_id),
          'enabled' : ((authuser == sem['responsable_id'])
                       or (authuser.has_permission(ScoEtudInscrit,context)))
          },
        { 'title' : "Enregistrer une validation d'UE ant�rieure",
          'url' : 'formsemestre_validate_previous_ue?etudid=%s&formsemestre_id=%s' % (etudid, formsemestre_id),
          'enabled' : context.can_validate_sem(REQUEST, formsemestre_id)
          },
        { 'title' : 'Entrer d�cisions jury',
          'url' : 'formsemestre_validation_etud_form?formsemestre_id=%s&etudid=%s'%(formsemestre_id,etudid),
          'enabled' : context.can_validate_sem(REQUEST, formsemestre_id)
        },
        { 'title' : 'Editer PV jury',
          'url' : 'formsemestre_pvjury_pdf?formsemestre_id=%s&etudid=%s' % (formsemestre_id,etudid),
          'enabled' : True
          }
        ]
    
    H.append("""<td class="bulletin_menubar"><div class="bulletin_menubar">""")
    H.append( sco_formsemestre_status.makeMenu( 'Autres op�rations', menuBul) )
    H.append("""</div></td></tr></table>""")
    #
    H.append("""</form></span></td><td class="bull_photo">
    <a href="%s/ficheEtud?etudid=%s">%s</a>
    """ % (context.ScoURL(), etudid, sco_photos.etud_photo_html(context, etud, title='fiche de '+etud['nom'], REQUEST=REQUEST)))
    H.append("""</td></tr>
    </table>
    """)
    
    return ''.join(H)


def formsemestre_bulletins_choice(context, REQUEST, formsemestre_id, 
                                  title='', explanation=''):
    """Choix d'une version de bulletin
    """
    sem = context.get_formsemestre(formsemestre_id)
    H = [context.html_sem_header(REQUEST, title, sem),
         """
      <form name="f" method="GET" action="%s">
      <input type="hidden" name="formsemestre_id" value="%s"></input>
      <select name="version" class="noprint">""" % (REQUEST.URL0,formsemestre_id),
         ]
    for (v,e) in ( ('short', 'Version courte'),
                   ('selectedevals', 'Version interm�diaire'),
                   ('long', 'Version compl�te')):
        H.append('<option value="%s">%s</option>' % (v, e))
    H.append("""</select>&nbsp;&nbsp;<input type="submit" value="G�n�rer"/></form><p class="help">""" + explanation + '</p>',)

    return '\n'.join(H) + context.sco_footer(REQUEST)

expl_bull = """Versions des bulletins:<ul><li><bf>courte</bf>: moyennes des modules</li><li><bf>interm�diaire</bf>: moyennes des modules et notes des �valuations s�lectionn�es</li><li><bf>compl�te</bf>: toutes les notes</li><ul>"""

def formsemestre_bulletins_pdf_choice(context, REQUEST, formsemestre_id, version=None):
    """Choix version puis envois classeur bulletins pdf"""
    if version:
        return context.formsemestre_bulletins_pdf(formsemestre_id, REQUEST, version=version)
    return formsemestre_bulletins_choice(
        context, REQUEST, formsemestre_id, 
        title='Choisir la version des bulletins � g�n�rer',
        explanation = expl_bull)

def formsemestre_bulletins_mailetuds_choice(context, REQUEST, formsemestre_id, version=None, dialog_confirmed=False):
    """Choix version puis envois classeur bulletins pdf"""
    if version:
        return context.formsemestre_bulletins_mailetuds(formsemestre_id, REQUEST, version=version, dialog_confirmed=dialog_confirmed)
    return formsemestre_bulletins_choice(
        context, REQUEST, formsemestre_id, 
        title='Choisir la version des bulletins � envoyer par mail',
        explanation = 'Chaque �tudiant ayant une adresse mail connue de ScoDoc recevra une copie PDF de son bulletin de notes, dans la version choisie.</p><p>' + expl_bull)
