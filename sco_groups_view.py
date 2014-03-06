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

"""Affichage étudiants d'un ou plusieurs groupes
   sous forme: de liste html (table exportable), de trombinoscope (exportable en pdf)
"""

# Re-ecriture en 2014 (re-organisation de l'interface, modernisation du code)
import collections

from sco_utils import *
from gen_tables import GenTable
import scolars
import ZAbsences
import sco_excel
import sco_groups
import sco_trombino
import sco_portal_apogee

def groups_view(
        context, group_ids=[], 
        format='html', REQUEST=None,
        # Options pour listes:
        with_codes=0,
        etat=None,
        with_paiement=0, # si vrai, ajoute colonne infos paiement droits inscription (lent car interrogation portail)
        with_archives=0, # ajoute colonne avec noms fichiers archivés
        with_annotations=0,
        formsemestre_id=None # utilise si aucun groupe selectionné
        ):
    """Affichage des étudiants des groupes indiqués
    group_ids: liste de group_id
    """    
    # Informations sur les groupes à afficher:
    groups_infos = DisplayedGroupsInfos(context, group_ids, formsemestre_id=formsemestre_id,
                                        etat=etat, REQUEST=REQUEST)
    # Formats spéciaux: download direct
    if format != 'html':
        return groups_table(context=context, groups_infos=groups_infos, 
                            format=format, REQUEST=REQUEST,
                            with_codes=with_codes,
                            etat=etat,
                            with_paiement=with_paiement, 
                            with_archives=with_archives, 
                            with_annotations=with_annotations)
    
    H = [ context.sco_header(
        REQUEST, 
        javascripts=[ 'libjs/bootstrap-3.1.1-dist/js/bootstrap.min.js',
                      'libjs/bootstrap-multiselect/bootstrap-multiselect.js',
                      'libjs/purl.js',
                      'js/etud_info.js',
                      'js/groups_view.js' ],
        cssstyles=[ 'libjs/bootstrap-3.1.1-dist/css/bootstrap.min.css',
                    'libjs/bootstrap-3.1.1-dist/css/bootstrap-theme.min.css',
                    'libjs/bootstrap-multiselect/bootstrap-multiselect.css'
                    ],
        init_qtip = True,
                      )]
    # Menu choix groupe
    H.append("""<div id="group-tabs">""")
    H.append( menu_groups_choice(context, groups_infos) )
    
    # Tabs
    #H.extend( ("""<span>toto</span><ul id="toto"><li>item 1</li><li>item 2</li></ul>""",) )
    H.extend( ("""<ul class="nav nav-tabs">
    <li class="active"><a href="#tab-listes" data-toggle="tab">Listes</a></li>
    <li><a href="#tab-photos" data-toggle="tab">Photos</a></li>
    <li><a href="#tab-abs" data-toggle="tab">Absences et feuilles...</a></li>
    </ul>
    </div>
    <!-- Tab panes -->
    <div class="tab-content">
    <div class="tab-pane active" id="tab-listes">
    """,
    groups_table(context=context, groups_infos=groups_infos, format=format, REQUEST=REQUEST,
                with_codes=with_codes,
                etat=etat,
                with_paiement=with_paiement, 
                with_archives=with_archives, 
                with_annotations=with_annotations),
    '</div>',
    
    """<div class="tab-pane" id="tab-photos">""",
    tab_photos_html(context, groups_infos, etat=etat, REQUEST=REQUEST),
    #'<p>hello</p>',
    '</div>',

    '<div class="tab-pane" id="tab-abs">',
    tab_absences_html(context, groups_infos, etat=etat, REQUEST=REQUEST),
    '</div>',    
    ))
    
    H.append( context.sco_footer(REQUEST) )
    return '\n'.join(H)

def menu_groups_choice(context, groups_infos):
    """form pour selection groupes
    group_ids est la liste des groupes actuellement sélectionnés
    et doit comporter au moins un élément, sauf si formsemestre_id est spécifié.
    (utilisé pour retrouver le semestre et proposer la liste des autres groupes)
    """
    default_group_id = sco_groups.get_default_group(context, groups_infos.formsemestre_id)
    
    H = [ """<form id="group_selector" method="get">
    <input type="hidden" name="formsemestre_id" id="formsemestre_id" value="%s"/>
    <input type="hidden" name="default_group_id" id="default_group_id" value="%s"/>
    Groupes: <select name="group_ids" id="group_ids_sel" class="multiselect" multiple="multiple">
    """ % (groups_infos.formsemestre_id, default_group_id) ]

    for partition in groups_infos.partitions:
        H.append('<optgroup label="%s">' % partition['partition_name'] )

        # Les groupes dans cette partition:
        for g in sco_groups.get_partition_groups(context, partition):
            if g['group_id'] in groups_infos.group_ids:
                selected = 'selected'
            else:
                selected = ''
            if g['group_name']:
                n_members = len(sco_groups.get_group_members(context, g['group_id']))
                H.append('<option value="%s" %s>%s (%s)</option>' 
                         % (g['group_id'], selected, g['group_name'], n_members) )
        H.append('</optgroup>')
    H.append('</select> ')
    H.append("""<input type="button" value="sélectionner tous" onmousedown="select_tous();"/>""")
    H.append('</form>')
    H.append("""
    <script type="text/javascript">
  $(document).ready(function() {
  $('#group_ids_sel').multiselect(
    {
    includeSelectAllOption: false,
    nonSelectedText:'choisir...',
    onChange: function(element, checked){
    submit_group_selector();
      }
    }
    );
    });
    </script>
    """)
    return '\n'.join(H)


class DisplayedGroupsInfos:
    """Container with attributes describing groups to display in the page
    .groups_query_args : 'group_ids=xxx&group_ids=yyy'
    .base_url : url de la requete, avec les groupes, sans les autres paramètres
    .formsemestre_id : semestre "principal" (en fait celui du 1er groupe de la liste)
    .members
    .groups_titles
    """
    def __init__(self, context, 
                 group_ids=[], # groupes specifies dans l'URL
                 formsemestre_id=None, 
                 etat=None, 
                 REQUEST=None):
        log('DisplayedGroupsInfos %s' % group_ids)
        if type(group_ids) == str:
            if group_ids:
                group_ids = [group_ids] # cas ou un seul parametre, pas de liste
            else:
                group_ids = []

        if not group_ids: # appel sans groupe (eg page accueil)
            if not formsemestre_id:
                raise Exception('missing parameter') # formsemestre_id or group_ids
            # selectionne le permier groupe trouvé, s'il y en a un
            partition = sco_groups.get_partitions_list(context, formsemestre_id, with_default=True)[0]
            groups = sco_groups.get_partition_groups(context, partition)
            if groups:
                group_ids = [groups[0]['group_id']]
            else:
                group_ids = [ sco_groups.get_default_group(context, formsemestre_id) ]
        
        self.base_url = REQUEST.URL0 + '?'
        gq = []
        for group_id in group_ids:
            gq.append('group_ids=' + group_id)
        self.groups_query_args = '&'.join(gq)
        self.base_url = REQUEST.URL0 + '?' + self.groups_query_args
        self.group_ids = group_ids
        self.groups = []
        groups_titles = []
        self.members = []
        self.tous_les_etuds_du_sem = False # affiche tous les etuds du semestre ? (si un seul semestre)
        self.sems = collections.OrderedDict() # formsemestre_id : sem
        self.formsemestre = None 
        self.formsemestre_id = formsemestre_id
        self.nbdem = 0 # nombre d'étudiants démissionnaires en tout
        for group_id in group_ids:
            group_members, group, group_tit, sem, nbdem, other_partitions = sco_groups.get_group_infos(context, group_id, etat=etat)
            self.groups.append(group)
            self.nbdem += nbdem
            self.sems[sem['formsemestre_id']] = sem
            if not self.formsemestre_id:
                self.formsemestre_id = sem['formsemestre_id']
                self.formsemestre = sem
            self.members.extend(group_members)
            groups_titles.append( group_tit )
            if group['group_name'] == None:
                self.tous_les_etuds_du_sem = True
        
        if not self.formsemestre: # aucun groupe selectionne
            self.formsemestre = context.Notes.get_formsemestre(formsemestre_id)
            
        self.sortuniq()
                
        if len(self.sems) > 1:
            self.tous_les_etuds_du_sem = False # plusieurs semestres
        if self.tous_les_etuds_du_sem:
            self.groups_titles = 'tous'
            self.groups_filename = 'tous'
        else:    
            self.groups_titles = ', '.join(groups_titles)
            self.groups_filename = '_'.join(groups_titles).replace(' ', '_')
            # Sanitize filename:
            self.groups_filename = self.groups_filename.translate(None, ':/\\')
        
        # colonnes pour affichages nom des groupes:
        # gère le cas où les étudiants appartiennent à des semestres différents
        self.partitions = [] # les partitions, sans celle par defaut
        for formsemestre_id in self.sems:
            for partition in sco_groups.get_partitions_list(context, formsemestre_id):
                if partition['partition_name']:
                    self.partitions.append( partition )
        
    def sortuniq(self):
        "Trie les étudiants (de plusieurs groupes) et elimine les doublons"
        if (len(self.group_ids) <= 1) or len(self.members) <= 1:
            return # on suppose que les etudiants d'un groupe sont deja triés
        self.members.sort(key=operator.itemgetter('nom_disp', 'prenom')) # tri selon nom_usuel ou nom
        to_remove = []
        T = self.members
        for i in range(len(T)-1, 0, -1):
            if T[i-1]['etudid'] == T[i]['etudid']:
                to_remove.append(i)
        for i in to_remove:
            del T[i]

    def get_form_elem(self):
        """html hidden input with groups"""
        H=[]
        for group_id in self.group_ids:
            H.append('<input type="hidden" name="group_ids" value="%s"/>' % group_id)
        return '\n'.join(H)

# Ancien ZScolar.group_list renommé ici en group_table
def groups_table(
        context=None, REQUEST=None,
        groups_infos=None, # instance of DisplayedGroupsInfos
        with_codes=0,
        etat=None,
        format='html',
        with_paiement=0, # si vrai, ajoute colonne infos paiement droits inscription (lent car interrogation portail)
        with_archives=0, # ajoute colonne avec noms fichiers archivés
        with_annotations=0
        ):
    """liste etudiants inscrits dans ce semestre
    format: html, csv, xls, xml, allxls, pdf, json
    Si with_codes, ajoute 3 colonnes avec les codes etudid, NIP, INE
    """
    authuser = REQUEST.AUTHENTICATED_USER
    
    with_codes = int(with_codes)
    with_paiement= int(with_paiement)
    with_archives= int(with_archives)
    with_annotations = int(with_annotations)
    
    base_url_np = groups_infos.base_url + '&with_codes=%s' % with_codes
    base_url = base_url_np + '&with_paiement=%s&with_archives=%s&with_annotations=%s' % (with_paiement, with_archives, with_annotations)
    #
    columns_ids=['nom_disp', 'prenom' ] # colonnes a inclure
    titles = { 'nom_disp' : 'Nom',
               'prenom' : 'Prénom',
               'email' : 'Mail',
               'etat':'Etat',
               'etudid':'etudid',
               'code_nip':'code_nip', 'code_ine':'code_ine',
               'paiementinscription_str' : 'Paiement',
               'etudarchive' : 'Fichiers',
               'annotations_str' : 'Annotations'
               }


    # ajoute colonnes pour groupes
    columns_ids.extend( [p['partition_id'] for p in groups_infos.partitions] )
    titles.update( dict( [ (p['partition_id'], p['partition_name']) for p in groups_infos.partitions]))
    
    if format != 'html': # ne mentionne l'état que en Excel (style en html)
        columns_ids.append('etat')
    columns_ids.append('email')
    if with_codes:
        columns_ids += ['etudid', 'code_nip', 'code_ine']
    if with_paiement:
        sco_portal_apogee.check_paiement_etuds(context, groups_infos.members)
        columns_ids += ['paiementinscription_str']
    if with_archives:
        import sco_archives_etud
        sco_archives_etud.add_archives_info_to_etud_list(context, groups_infos.members)
        columns_ids += ['etudarchive']
    if with_annotations:
        scolars.add_annotations_to_etud_list(context, groups_infos.members)
        columns_ids += ['annotations_str']
    # ajoute liens
    for etud in groups_infos.members:
        if  etud['email']:
            etud['_email_target'] = 'mailto:' + etud['email']
        else:
            etud['_email_target'] = ''
        etud['_nom_disp_target'] = 'ficheEtud?etudid=' + etud['etudid']
        etud['_prenom_target'] = 'ficheEtud?etudid=' + etud['etudid']

        etud['_nom_disp_td_attrs'] = 'id="%s" class="etudinfo"' % (etud['etudid'])

        if etud['etat'] == 'D':                
            etud['_css_row_class'] = 'etuddem'
        # et groupes:
        for partition_id in etud['partitions']:
            etud[partition_id] = etud['partitions'][partition_id]['group_name']

    if groups_infos.nbdem > 1:
        s = 's'
    else:
        s = ''

    tab = GenTable( rows=groups_infos.members, columns_ids=columns_ids, titles=titles,
                    caption='soit %d étudiants inscrits et %d démissionaire%s.' 
                    % (len(groups_infos.members)-groups_infos.nbdem,groups_infos.nbdem,s),
                    base_url=base_url,
                    pdf_link=False, # pas d'export pdf
                    html_sortable=True,
                    html_class='gt_table table_leftalign table_listegroupe',
                    xml_outer_tag='group_list',
                    xml_row_tag='etud',
                    preferences=context.get_preferences(groups_infos.formsemestre_id) )
    #
    if format == 'html':
        amail=','.join([x['email'] for x in groups_infos.members if x['email'] ])

        if len(groups_infos.members):
            if groups_infos.tous_les_etuds_du_sem:
                htitle = 'Les %d étudiants inscrits' % len(groups_infos.members)
            else:
                htitle = 'Groupe %s (%d étudiants)' % (groups_infos.groups_titles,len(groups_infos.members))
        else:
            htitle = 'Aucun étudiant !'
        H = [ 
            '<div class="tab-content"><form>'
            '<h3 class="formsemestre"><span>', htitle, '</span>' 
            ]
        if groups_infos.members:
            Of = []
            options = {  "with_paiement" : "Paiement inscription", 
                         "with_archives" : "Fichiers archivés", 
                         "with_annotations" : "Annotations", 
                         "with_codes" : "Codes" }
            for option in options:
                if locals().get(option, False):
                    selected = "selected"
                else:
                    selected = ""
                Of.append( """<option value="%s" %s>%s</option>""" % (option, selected, options[option]))
                
            H.extend([
                """<span style="margin-left: 2em;"><select name="group_list_options" id="group_list_options" class="multiselect" multiple="multiple">""",
                '\n'.join(Of),
                """
            </select></span>
            <script type="text/javascript">
  $(document).ready(function() {
  $('#group_list_options').multiselect(
  {
    includeSelectAllOption: false,
    nonSelectedText:'Options...',
    onChange: function(element, checked){
        change_list_options();
    }
    }
  );
  });
  </script>
                """ ])
        H.append('</h3></form>')
        if groups_infos.members:
            H.extend([
                tab.html(),
                
                '<ul><li><a class="stdlink" href="mailto:?bcc=%s">Envoyer un mail collectif au groupe de %s</a></li></ul>' 
                % (amail, groups_infos.groups_titles)
                ])
        
        return ''.join(H) + '</div>'

    elif format=='pdf' or format=='xml' or format=='json':
        return tab.make_page(context, format=format, REQUEST=REQUEST)

    elif format == 'xls':
        xls = sco_excel.Excel_feuille_listeappel(context, 
                                                 groups_infos.formsemestre, # le 1er semestre, serait à modifier si plusieurs
                                                 groups_infos.groups_titles, 
                                                 groups_infos.members,
                                                 partitions = groups_infos.partitions,
                                                 with_codes=with_codes,
                                                 with_paiement=with_paiement,
                                                 server_name=REQUEST.BASE0)
        filename = 'liste_%s' % groups_infos.groups_filename + '.xls'
        return sco_excel.sendExcelFile(REQUEST, xls, filename )
    elif format == 'allxls':
        # feuille Excel avec toutes les infos etudiants
        if not groups_infos.members:
            return ''            
        keys = ['etudid', 'code_nip', 'etat',
                'sexe', 'nom', 'nom_usuel', 'prenom',
                'inscriptionstr']
        if with_paiement:
            keys.append('paiementinscription')
        keys += [ 'email', 'domicile', 'villedomicile', 'codepostaldomicile', 'paysdomicile',
                  'telephone', 'telephonemobile', 'fax',
                  'date_naissance', 'lieu_naissance',
                  'bac', 'specialite', 'annee_bac',
                  'nomlycee', 'villelycee', 'codepostallycee', 'codelycee',
                  'type_admission', 'boursier_prec',
                  'debouche',
                  'parcours', 'codeparcours'
                ]
        titles = keys[:]
        keys += [ p['partition_id'] for p in other_partitions ]
        titles += [ p['partition_name'] for p in other_partitions ]
        # remplis infos lycee si on a que le code lycée
        # et ajoute infos inscription
        for m in groups_infos.members:
            etud = context.getEtudInfo(m['etudid'], filled=True)[0]
            m.update(etud)
            scolars.etud_add_lycee_infos(etud)
            # et ajoute le parcours
            Se = sco_parcours_dut.SituationEtudParcours(context.Notes, etud, groups_infos.formsemestre_id)
            m['parcours'] = Se.get_parcours_descr() 
            m['codeparcours'] = sco_report.get_codeparcoursetud(context.Notes, etud)

        def dicttakestr(d, keys):
            r = []
            for k in keys:
                r.append(str(d.get(k, '')))
            return r
        L = [ dicttakestr(m, keys) for m in groups_infos.members ]            
        title = 'etudiants_%s' % groups_infos.groups_filename
        xls = sco_excel.Excel_SimpleTable(
            titles=titles,
            lines = L,
            SheetName = title )
        filename = title + '.xls'
        return sco_excel.sendExcelFile(REQUEST, xls, filename)
    else:
        raise ValueError('unsupported format')


def tab_absences_html(context, groups_infos, etat=None, REQUEST=None):
    """contenu du tab "absences et feuilles diverses"
    """
    authuser = REQUEST.AUTHENTICATED_USER
    H = [ '<div class="tab-content">' ]
    if not groups_infos.members:
        return ''.join(H) + '<h3>Aucun étudiant !</h3></div>'
    H.extend( [
          '<h3>Absences</h3>',
          '<ul class="ul_abs">',
          '<li>', form_choix_jour_saisie_hebdo(context, groups_infos, REQUEST=REQUEST), '</li>',          
          """<li><a class="stdlink" href="Absences/EtatAbsencesGr?%s&debut=%s&fin=%s">Etat des absences du groupe</a></li>"""
          % (groups_infos.groups_query_args, groups_infos.formsemestre['date_debut'], groups_infos.formsemestre['date_fin']),
          '</ul>',
          
          '<h3>Feuilles</h3>',
          '<ul class="ul_feuilles">',

          """<li><a class="stdlink" href="%s&format=xls">Feuille d'émargement %s (Excel)</a></li>""" 
          % (groups_infos.base_url, groups_infos.groups_titles),
          """<li><a class="stdlink" href="trombino?%s&format=pdf">Trombinoscope en PDF</a></li>"""
          % groups_infos.groups_query_args,
          """<li><a class="stdlink" href="pdf_trombino_tours?%s&format=pdf">Trombinoscope en PDF (format "IUT de Tours", beta)</a></li>"""
          % groups_infos.groups_query_args,
          """<li><a class="stdlink" href="pdf_feuille_releve_absences?%s&format=pdf">Feuille relevé absences hebdomadaire (beta)</a></li>"""
          % groups_infos.groups_query_args,
          """<li><a class="stdlink" href="trombino?%s&format=pdflist">Liste d'appel avec photos</a></li>"""
          % groups_infos.groups_query_args,
          '</ul>'
    ] )

    H.append('<h3>Opérations diverses</h3><ul class="ul_misc">')
    # Lien pour verif codes INE/NIP
    # (pour tous les etudiants du semestre)
    group_id = sco_groups.get_default_group(context, groups_infos.formsemestre_id)
    if authuser.has_permission(ScoEtudInscrit,context):
        H.append('<li><a class="stdlink" href="check_group_apogee?group_id=%s&etat=%s">Vérifier codes Apogée</a> (de tous les groupes)</li>'
                 % (group_id,etat or ''))
    # Lien pour ajout fichiers étudiants
    if authuser.has_permission(ScoEtudAddAnnotations,context):
        H.append("""<li><a class="stdlink" href="etudarchive_import_files_form?group_id=%s">Télécharger des fichiers associés aux étudiants (e.g. dossiers d'admission)</a></li>"""
                 % (group_id)) 

    H.append('</ul></div>')
    return ''.join(H)

def tab_photos_html(context, groups_infos, etat=None, REQUEST=None):
    """contenu du tab "photos"
    """
    if not groups_infos.members:
        return '<div class="tab-content"><h3>Aucun étudiant !</h3></div>'
    
    return sco_trombino.trombino_html(context, groups_infos, REQUEST=REQUEST)


# Formulaire choix jour semaine pour saisie 
def form_choix_jour_saisie_hebdo(context, groups_infos, REQUEST=None):
    authuser = REQUEST.AUTHENTICATED_USER
    if not authuser.has_permission(ScoAbsChange,context):
        return ''
    sem = groups_infos.formsemestre
    first_monday = ZAbsences.ddmmyyyy(sem['date_debut']).prev_monday()
    today_idx = datetime.date.today().weekday()
    
    FA = [] # formulaire avec menu saisi absences
    FA.append('<form id="form_choix_jour_saisie_hebdo" action="Absences/SignaleAbsenceGrSemestre" method="get">')
    FA.append('<input type="hidden" name="datefin" value="%(date_fin)s"/>'
              % sem )
    FA.append(groups_infos.get_form_elem())

    FA.append('<input type="hidden" name="destination" value=""/>')
    
    FA.append("""<input type="button" onclick="$('#form_choix_jour_saisie_hebdo')[0].destination.value=get_current_url(); $('#form_choix_jour_saisie_hebdo').submit();" value="Saisir absences du "/>""")
    FA.append("""<select name="datedebut">""")
    date = first_monday
    i = 0
    for jour in context.Absences.day_names():
        if i == today_idx:
            sel = 'selected'
        else:
            sel = ''
        i += 1
        FA.append('<option value="%s" %s>%s</option>' % (date, sel, jour) )
        date = date.next()
    FA.append('</select>')
    FA.append('</form>')
    return '\n'.join(FA)
