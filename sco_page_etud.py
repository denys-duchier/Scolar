# -*- mode: python -*-
# -*- coding: iso8859-15 -*-

##############################################################################
#
# Gestion scolarite IUT
#
# Copyright (c) 2001 - 2013 Emmanuel Viennet.  All rights reserved.
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

"""ScoDoc ficheEtud

   Fiche description d'un étudiant et de son parcours

"""

from sco_utils import *
from notesdb import *
import scolars
import sco_photos
import sco_groups
from scolars import format_telephone, format_pays, make_etud_args
from sco_formsemestre_status import makeMenu
from sco_bulletins import etud_descr_situation_semestre
import sco_parcours_dut
from sco_formsemestre_validation import formsemestre_recap_parcours_table
import sco_archives_etud


def _menuScolarite(context, authuser, sem, etudid):
    """HTML pour menu "scolarite" pour un etudiant dans un semestre.
    Le contenu du menu depend des droits de l'utilisateur et de l'état de l'étudiant.
    """
    locked = (sem['etat'] != '1')
    if locked: 
        lockicon = context.icons.lock32_img.tag(title="verrouillé", border='0')
        return lockicon # no menu
    if not authuser.has_permission(ScoEtudInscrit,context) and not authuser.has_permission(ScoEtudChangeGroups,context):
        return '' # no menu
    ins = sem['ins']
    args = { 'etudid' : etudid,
             'formsemestre_id' : ins['formsemestre_id'] }

    if ins['etat'] != 'D':
        dem_title = 'Démission'
        dem_url = 'formDem?etudid=%(etudid)s&formsemestre_id=%(formsemestre_id)s' % args
    else:
        dem_title = 'Annuler la démission'
        dem_url = 'doCancelDem?etudid=%(etudid)s&formsemestre_id=%(formsemestre_id)s' % args

    # Note: seul un etudiant inscrit (I) peut devenir défaillant.
    if ins['etat'] != 'DEF':
        def_title = 'Déclarer défaillance'
        def_url = 'formDef?etudid=%(etudid)s&formsemestre_id=%(formsemestre_id)s' % args
    elif ins['etat'] == 'DEF':
        def_title = 'Annuler la défaillance'
        def_url = 'doCancelDef?etudid=%(etudid)s&formsemestre_id=%(formsemestre_id)s' % args
    def_enabled = (ins['etat'] != 'D') and authuser.has_permission(ScoEtudInscrit,context) and not locked
    items = [
#        { 'title' : 'Changer de groupe',
#          'url' : 'formChangeGroup?etudid=%s&formsemestre_id=%s' % (etudid,ins['formsemestre_id']),
#          'enabled' : authuser.has_permission(ScoEtudChangeGroups,context) and not locked,
#        },
        { 'title' : dem_title,
          'url' : dem_url,
          'enabled' : authuser.has_permission(ScoEtudInscrit,context) and not locked
        },
        { 'title' : "Validation du semestre (jury)",
          'url' : "Notes/formsemestre_validation_etud_form?etudid=%(etudid)s&formsemestre_id=%(formsemestre_id)s" % args,
          'enabled' : authuser.has_permission(ScoEtudInscrit,context) and not locked
        },
        { 'title' : def_title,
          'url' : def_url,
          'enabled' : def_enabled
        },
        { 'title' : "Inscrire à un module optionnel (ou au sport)",
          'url' : "Notes/formsemestre_inscription_option?formsemestre_id=%(formsemestre_id)s&etudid=%(etudid)s" % args,
          'enabled' : authuser.has_permission(ScoEtudInscrit,context) and not locked
        },
        { 'title' : "Désinscrire (en cas d'erreur)",
          'url' : "Notes/formsemestre_desinscription?formsemestre_id=%(formsemestre_id)s&etudid=%(etudid)s" % args,
          'enabled' : authuser.has_permission(ScoEtudInscrit,context) and not locked
        },

        { 'title' : "Inscrire à un autre semestre",
          'url' : "Notes/formsemestre_inscription_with_modules_form?etudid=%(etudid)s" % args,
          'enabled' : authuser.has_permission(ScoEtudInscrit,context)
        },        
        ]

    return makeMenu( "Scolarité", items, cssclass="direction_etud", elem='span' )

def ficheEtud(context, etudid=None, REQUEST=None):
    "fiche d'informations sur un etudiant"
    authuser = REQUEST.AUTHENTICATED_USER
    cnx = context.GetDBConnexion()
    args = make_etud_args(etudid=etudid,REQUEST=REQUEST)
    etuds = scolars.etudident_list(cnx, args)
    if not etuds:
        raise ScoValueError('Etudiant inexistant !')
    etud = etuds[0]
    etudid = etud['etudid']
    context.fillEtudsInfo([etud])
    #
    info = etud
    info['ScoURL'] = context.ScoURL()
    info['authuser'] = authuser
    info['info_naissance'] = info['date_naissance']
    if info['lieu_naissance']:
        info['info_naissance'] += ' à ' + info['lieu_naissance']
    info['etudfoto'] = sco_photos.etud_photo_html(context, etud, REQUEST=REQUEST)
    if ((not info['domicile']) and (not info['codepostaldomicile'])
        and (not info['villedomicile'])):
        info['domicile'] ='<em>inconnue</em>'
    if info['paysdomicile']:
        pays = format_pays(info['paysdomicile'])
        if pays:
            info['paysdomicile'] = '(%s)' % pays
        else:
            info['paysdomicile'] = ''
    if info['telephone'] or info['telephonemobile']:
        info['telephones'] = '<br/>%s &nbsp;&nbsp; %s' % (info['telephonestr'],
                                                         info['telephonemobilestr']) 
    else:
        info['telephones'] = ''
    # champs dependant des permissions
    if authuser.has_permission(ScoEtudChangeAdr,context):
        info['modifadresse'] = '<a class="stdlink" href="formChangeCoordonnees?etudid=%s">modifier adresse</a>' % etudid
    else:
        info['modifadresse'] = ''

    # Groupes:
    sco_groups.etud_add_group_infos(context, info, info['cursem'])

    # Parcours de l'étudiant
    if info['sems']:
        info['last_formsemestre_id'] = info['sems'][0]['formsemestre_id']
    else:
        info['last_formsemestre_id'] = ''
    sem_info={}
    for sem in info['sems']: 
        if sem['ins']['etat'] != 'I':
            descr, junk = etud_descr_situation_semestre(context.Notes, etudid, sem['formsemestre_id'], info['ne'], show_date_inscr=False)
            grlink = '<span class="fontred">%s</span>' % descr['situation']
        else:       
            group = sco_groups.get_etud_main_group(context, etudid, sem)
            if group['partition_name']:
                gr_name = group['group_name']
            else:
                gr_name = 'tous'
            grlink = '<a class="discretelink" href="group_list?group_id=%s" title="Liste du groupe">groupe %s</a>' % (group['group_id'], gr_name)
        # infos ajoutées au semestre dans le parcours (groupe, menu)
        menu =  _menuScolarite(context, authuser, sem, etudid)
        if menu:
            sem_info[sem['formsemestre_id']] = '<table><tr><td>'+grlink + '</td><td>' + menu + '</td></tr></table>'
        else:
            sem_info[sem['formsemestre_id']] = grlink

    if info['sems']:
        Se = sco_parcours_dut.SituationEtudParcours(context.Notes, etud, info['last_formsemestre_id'])
        info['liste_inscriptions'] = formsemestre_recap_parcours_table(
            context.Notes, Se, etudid, with_links=False, sem_info=sem_info, with_all_columns=False,
            a_url='Notes/')
    else:
        # non inscrit
        l = ['<p><b>Etudiant%s non inscrit%s'%(info['ne'],info['ne'])]
        if authuser.has_permission(ScoEtudInscrit,context):
            l.append('<a href="%s/Notes/formsemestre_inscription_with_modules_form?etudid=%s">inscrire</a></li>'%(context.ScoURL(),etudid))
        l.append('</b></b>')
        info['liste_inscriptions'] = '\n'.join(l)
    # Liste des annotations
    alist = []
    annos = scolars.etud_annotations_list(cnx, args={ 'etudid' : etudid })
    i = 0
    for a in annos:
        if i % 2: # XXX refaire avec du CSS
            a['bgcolor']="#EDEDED"
        else:
            a['bgcolor'] = "#DEDEDE"
        i += 1
        if not context.canSuppressAnnotation(a['id'], REQUEST):
            a['dellink'] = ''
        else:
            a['dellink'] = '<td bgcolor="%s" class="annodel"><a href="doSuppressAnnotation?etudid=%s&annotation_id=%s">%s</a></td>' % (a['bgcolor'], etudid, a['id'], context.icons.delete_img.tag(border="0", alt="suppress", title="Supprimer cette annotation"))
        alist.append('<tr><td bgcolor="%(bgcolor)s">Le %(date)s par <b>%(author)s</b> (%(zope_authenticated_user)s) :<br/>%(comment)s</td>%(dellink)s</tr>' % a )
    info['liste_annotations'] = '\n'.join(alist)
    # fiche admission
    has_adm_notes = info['math'] or info['physique'] or info['anglais'] or info['francais']
    has_bac_info = info['bac'] or info['specialite'] or info['annee_bac'] or info['rapporteur'] or info['commentaire']
    if has_bac_info or has_adm_notes:
        if has_adm_notes:
            adm_tmpl = """<!-- Donnees admission -->
<div class="ficheadmission">
<div class="fichetitre">Informations admission</div>
<table>
<tr><th>Bac</th><th>Année</th><th>Math</th><th>Physique</th><th>Anglais</th><th>Français</th></tr>
<tr>
<td>%(bac)s (%(specialite)s)</td>
<td>%(annee_bac)s </td>
<td>%(math)s</td><td>%(physique)s</td><td>%(anglais)s</td><td>%(francais)s</td>
</tr>
</table>
<div>%(ilycee)s <em>%(rap)s</em></div>
</div>
"""
        else:
            adm_tmpl = """<!-- Donnees admission (pas de notes) -->
<div class="ficheadmission">
<div class="fichetitre">Informations admission</div>
<div>Bac %(bac)s (%(specialite)s) obtenu en %(annee_bac)s </div>
<div>%(ilycee)s <em>%(rap)s</em></div>
</div>
"""
    else:
        adm_tmpl = '' # pas de boite "info admission"
    info['adm_data'] = adm_tmpl % info

    # Fichiers archivés:
    info['fichiers_archive_htm'] = '<div class="ficheadmission"><div class="fichetitre">Fichiers associés</div>' + sco_archives_etud.etud_list_archives_html(context, REQUEST, etudid) + '</div>'
    
    # Devenir de l'étudiant:
    has_debouche =  info['debouche']
    if has_debouche:
        info['debouche_html'] = """<div class="fichedebouche"><span class="debouche_tit">Devenir:</span><span>%s</span></div>""" % info['debouche']
    else:
        info['debouche_html'] = '' # pas de boite "devenir"
    #
    if info['liste_annotations']:
        info['tit_anno'] = '<div class="fichetitre">Annotations</div>'
    else:
        info['tit_anno'] = ''
    # Inscriptions
    if info['sems']:
        rcl = """(<a href="%(ScoURL)s/Notes/formsemestre_validation_etud_form?check=1&etudid=%(etudid)s&formsemestre_id=%(last_formsemestre_id)s&desturl=ficheEtud?etudid=%(etudid)s">récapitulatif parcours</a>)""" % info
    else:
        rcl = ''
    info['inscriptions_mkup'] = """<div class="ficheinscriptions" id="ficheinscriptions">
<div class="fichetitre">Parcours</div>%s
</div>""" % info['liste_inscriptions']
        
    #      
    if info['groupes'].strip():
        info['groupes_row'] = '<tr><td class="fichetitre2">Groupe :</td><td>%(groupes)s</td></tr>'%info
    else:
        info['groupes_row'] = ''
    info['menus_etud'] = menus_etud(context,REQUEST)
    tmpl = """<div class="menus_etud">%(menus_etud)s</div>
<div class="ficheEtud" id="ficheEtud"><table>
<tr><td>
<h2>%(nomprenom)s (%(inscription)s)</h2>

<span>%(emaillink)s</span> 
</td><td class="photocell">
<a href="etud_photo_orig_page?etudid=%(etudid)s">%(etudfoto)s</a>
</td></tr></table>

<div class="fichesituation">
<div class="fichetablesitu">
<table>
<tr><td class="fichetitre2">Situation :</td><td>%(situation)s</td></tr>
%(groupes_row)s
<tr><td class="fichetitre2">Né%(ne)s le :</td><td>%(info_naissance)s</td></tr>
</table>


<!-- Adresse -->
<div class="ficheadresse" id="ficheadresse">
<table><tr>
<td class="fichetitre2">Adresse :</td><td> %(domicile)s %(codepostaldomicile)s %(villedomicile)s %(paysdomicile)s
%(modifadresse)s
%(telephones)s
</td></tr></table>
</div>
</div>
</div>

%(inscriptions_mkup)s

%(adm_data)s

%(fichiers_archive_htm)s

%(debouche_html)s

<div class="ficheannotations">
%(tit_anno)s
<table width="95%%">%(liste_annotations)s</table>

<form action="doAddAnnotation" method="GET" class="noprint">
<input type="hidden" name="etudid" value="%(etudid)s">
<b>Ajouter une annotation sur %(nomprenom)s: </b>
<table><tr>
<tr><td><textarea name="comment" rows="4" cols="50" value=""></textarea>
<br/><font size=-1><i>Balises HTML autorisées: b, a, i, br, p. Ces annotations sont lisibles par tous les enseignants et le secrétariat.</i></font>
</td></tr>
<tr><td>Auteur : <input type="text" name="author" width=12 value="%(authuser)s">&nbsp;
<input type="submit" value="Ajouter annotation"></td></tr>
</table>
</form>
</div>

<div class="code_nip">code NIP: %(code_nip)s</div>

</div>
        """                           
    header = context.sco_header(
                REQUEST,
                page_title='Fiche étudiant %(prenom)s %(nom)s'%info,
                javascripts=['jQuery/jquery.js', 'js/recap_parcours.js'])
    return header + tmpl % info + context.sco_footer(REQUEST)



def menus_etud(context, REQUEST=None):
    """Menu etudiant (operations sur l'etudiant)
    """
    if not REQUEST.form.has_key('etudid'):
        return ''
    authuser = REQUEST.AUTHENTICATED_USER

    etud = context.getEtudInfo(filled=1, REQUEST=REQUEST)[0]

    menuEtud = [
        { 'title' : '%(sexe)s %(prenom)s %(nom)s' % etud,
          'url' : 'ficheEtud?etudid=%(etudid)s' % etud,
          'enabled' : True,
          'helpmsg' : 'Fiche étudiant'
          },
        { 'title' : 'Changer la photo',
          'url' : 'formChangePhoto?etudid=%(etudid)s' % etud,
          'enabled' : authuser.has_permission(ScoEtudChangeAdr,context),
          },
        { 'title' : 'Changer les données identité/admission',
          'url' : 'etudident_edit_form?etudid=%(etudid)s' % etud,
          'enabled' : authuser.has_permission(ScoEtudInscrit,context),
          },
        { 'title' : 'Supprimer cet étudiant...',
          'url' : 'etudident_delete?etudid=%(etudid)s' % etud,
          'enabled' : authuser.has_permission(ScoEtudInscrit,context),
          },
        { 'title' : 'Voir le journal...',
          'url' : 'showEtudLog?etudid=%(etudid)s' % etud,
          'enabled' : True,
          },
        ]
       
    return makeMenu( 'Etudiant', menuEtud, base_url=context.absolute_url() + '/')


def etud_info_html(context, etudid, REQUEST=None, debug=False):
    """An HTML div with basic information and links about this etud.
    Used for popups information windows.
    """
    etud = context.getEtudInfo(filled=1, REQUEST=REQUEST)[0]
    photo_html = sco_photos.etud_photo_html(context, etud, title='fiche de '+etud['nom'], REQUEST=REQUEST)
    
    etud['photo_html'] = photo_html
    H = """<div class="etud_info_div">
    <div class="eid_left">
     <span class="eid_nom">%(nomprenom)s</span>
    </div>
    <span class="eid_right">
    %(photo_html)s
    </span>
    </div>""" % etud
    if debug:
        return context.standard_html_header(context) + H + context.standard_html_footer(context)
    else:
        return H
