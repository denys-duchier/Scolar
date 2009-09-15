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

"""Gestion des groupes TD/TP/TA
"""

import re, sets
# XML generation package (apt-get install jaxml)
import jaxml
import xml.dom.minidom

from sco_utils import *
from notesdb import *
from notes_log import log
from TrivialFormulator import TrivialFormulator, TF
from scolars import format_nom, format_prenom, format_sexe, format_lycee
from scolars import format_telephone, format_pays, make_etud_args
import sco_parcours_dut

def checkGroupName(groupName):
    "Raises exception if not a valid group name"
    if groupName and (
        not re.match( '^\w+$', groupName ) 
        or (simplesqlquote(groupName) != groupName)):
        log('!!! invalid group name: ' + groupName)
        raise ValueError('invalid group name: ' + groupName)

def fixGroupName(groupName):
    """bacward compat: fix old group names wich can be invalid"""    
    try:
        checkGroupName(groupName)
    except:
        log('fixing groupe name: %s' % groupName)
        if groupName[-2:] == '.0':
            groupName = groupName[:-2]
        groupName = re.sub('[^a-zA-Z0-9_]', '_', groupName)
        log('new group name: %s' % groupName)
    return groupName


def getGroupsFromList(groups_list):
    """Get list of groups (td, tp, ta) from list
    groups_list : [ 'tdA', 'tpC', 'taX', ... ] (usually coming from web request)
    Returns: gr_td, gr_tp, gr_anglais, gr_title
    """
    if groups_list is None:
        return [], [], [], ''
    gr_td = [ x[2:] for x in groups_list if x[:2] == 'td' ]
    gr_tp = [ x[2:] for x in groups_list if x[:2] == 'tp' ]
    gr_anglais = [ x[2:] for x in groups_list if x[:2] == 'ta' ]
    g = gr_td+gr_tp+gr_anglais
    if len(g) > 1:
        gr_title = 'groupes ' + ', '.join(g)                
    elif len(g) == 1:            
        gr_title = 'groupe ' + g[0]
    else:
        gr_title = ''
    return gr_td, gr_tp, gr_anglais, gr_title




def XMLgetGroupesTD(context, formsemestre_id, groupType, REQUEST):
    "Liste des etudiants dans chaque groupe de TD"
    t0 = time.time()
    if not groupType in ('TD', 'TP', 'TA'):
        raise ValueError( 'invalid group type: ' + groupType)
    cnx = context.GetDBConnexion()
    sem = context.Notes.do_formsemestre_list({'formsemestre_id':formsemestre_id})[0]
    REQUEST.RESPONSE.setHeader('Content-type', XML_MIMETYPE)
    doc = jaxml.XML_document( encoding=SCO_ENCODING )
    doc._text( '<ajax-response><response type="object" id="MyUpdater">' )
    doc._push()


    # --- Infos sur les groupes existants
    gr_td,gr_tp,gr_anglais = context.Notes.do_formsemestre_inscription_listgroupnames(formsemestre_id=formsemestre_id)
    nt = context.Notes._getNotesCache().get_NotesTable(context.Notes,
                                                    formsemestre_id)
    inscrlist = nt.inscrlist # liste triee par nom
    
    # -- groupes TD 
    if groupType == 'TD':
        gr, key = gr_td, 'groupetd'
    elif groupType == 'TP':
        gr, key = gr_tp, 'groupetp'
    else:
        gr, key = gr_anglais, 'groupeanglais'
    inscr_nogroups = [ e for e in inscrlist if not e[key] ]
    if inscr_nogroups:
        # ajoute None pour avoir ceux non affectes a un groupe
        gr.append(None)
    for g in gr: 
        doc._push()
        if g:
            gname = g
        else:
            gname = 'Aucun'
        doc.groupe( type=groupType, displayName=gname, groupName=g )
        for e in inscrlist:
            if (g and e[key] == g) or (not g and not e[key]):
                ident = nt.identdict[e['etudid']]
                etud = context.getEtudInfo(etudid=e['etudid'], filled=1)
                if not etud:
                    log('*** ouch: etud %s inscrit mais inconnu !' % e['etudid'])
                    log(e)
                    continue
                else:
                    etud = etud[0]
                doc._push()
                doc.etud( etudid=e['etudid'],
                          sexe=format_sexe(ident['sexe']),
                          nom=format_nom(ident['nom']),
                          prenom=format_prenom(ident['prenom']),
                          origin=comp_origin(etud, sem)
                          )
                doc._pop()    
        doc._pop()
    doc._pop()
    doc._text( '</response></ajax-response>' )
    log('XMLgetGroupesTD: %s seconds' % (time.time() - t0))
    return repr(doc)

def comp_origin(etud, cur_sem):
    """breve description de l'origine de l'étudiant (sem. precedent)
    (n'indique l'origine que si ce n'est pas le semestre precedent normal)
    """
    # cherche le semestre suivant le sem. courant dans la liste
    cur_sem_idx = None
    for i in range(len(etud['sems'])):
        if etud['sems'][i]['formsemestre_id'] == cur_sem['formsemestre_id']:
            cur_sem_idx = i
            break
    
    if cur_sem_idx is None or (cur_sem_idx+1) >= (len(etud['sems'])-1):
        return '' # on pourrait indiquer le bac mais en general on ne l'a pas en debut d'annee
    
    prev_sem = etud['sems'][cur_sem_idx+1] 
    if prev_sem['semestre_id'] != (cur_sem['semestre_id'] - 1):
        return ' (S%s)' % prev_sem['semestre_id']
    else:
        return '' # parcours normal, ne le signale pas
    

def setGroupes(context, groupslists, formsemestre_id=None, groupType=None,
               REQUEST=None):
    "affect groups (Ajax request)"
    if not context.Notes.can_change_groups(REQUEST, formsemestre_id):
        raise ScoValueError("Vous n'avez pas le droit d'effectuer cette opération !")
    
    log('***setGroupes\nformsemestre_id=%s' % formsemestre_id)
    log('groupType=%s' % groupType )
    log(groupslists)
    if not groupType in ('TD', 'TP', 'TA'):
        raise ValueError, 'invalid group type: ' + groupType
    if groupType == 'TD':
        grn = 'groupetd'
    elif groupType == 'TP':
        grn = 'groupetp'
    else:
        grn = 'groupeanglais'
    args = { 'REQUEST' : REQUEST, 'redirect' : False }
    for line in groupslists.split('\n'):
        fs = line.split(';')
        groupName = fs[0].strip()
        checkGroupName(groupName)
        args[grn] = groupName
        for etudid in fs[1:-1]:
            context.doChangeGroupe( etudid, formsemestre_id, **args )

    REQUEST.RESPONSE.setHeader('Content-type', XML_MIMETYPE)
    return '<ajax-response><response type="object" id="ok"/></ajax-response>'


def suppressGroup(context, REQUEST, formsemestre_id=None,
                  groupType=None, groupTypeName=None ):
    """form suppression d'un groupe.
    (ne desisncrit pas les etudiants, change juste leur
    affectation aux groupes)
    """
    if not context.Notes.can_change_groups(REQUEST, formsemestre_id):
        raise ScoValueError("Vous n'avez pas le droit d'effectuer cette opération !")

    gr_td,gr_tp,gr_anglais = context.Notes.do_formsemestre_inscription_listgroupnames(formsemestre_id=formsemestre_id)
    if groupType == 'TD':
        groupes = gr_td
    elif groupType == 'TP':
        groupes = gr_tp
    elif groupType == 'TA':
        groupes = gr_anglais
    else:
        raise ValueError, 'invalid group type: ' + groupType
    labels = ['aucun'] + groupes
    groupeskeys = [''] + groupes
    if gr_td:
        gr_td.sort()
        default_group = gr_td[0]
    else:
        default_group = 'aucun'
    #
    header = context.sco_header(REQUEST, page_title='Suppression d\'un groupe' )
    H = [ '<h2>Suppression d\'un groupe de %s</h2>' % groupTypeName ]
    if groupType == 'TD':
        if len(gr_td) > 1:
            H.append( '<p>Les étudiants doivent avoir un groupe de TD. Si vous supprimer ce groupe, il seront affectés au groupe destination choisi (vous pourrez les changer par la suite)</p>'  )
        else:
            H.append('<p>Il n\'y a qu\'un seul groupe défini, vous ne pouvez pas le supprimer.</p><p><a class="stdlink" href="Notes/formsemestre_status?formsemestre_id=%s">Revenir au semestre</a>' % formsemestre_id )
            return  header + '\n'.join(H) + context.sco_footer(REQUEST)

    descr = [
        ('formsemestre_id', { 'input_type' : 'hidden' }),
        ('groupType', { 'input_type' : 'hidden' }),
        ('groupTypeName', { 'input_type' : 'hidden' }),
        ('groupName', { 'title' : 'Nom du groupe',
                        'input_type' : 'menu',
                        'allowed_values' : groupeskeys, 'labels' : labels })
       ]
    if groupType == 'TD':
        descr.append(
            ('groupDest', { 'title' : 'Groupe destination',
                            'explanation' : 'les étudiants du groupe supprimé seront inscrits dans ce groupe',
                            'input_type' : 'menu',
                            'allowed_values' : groupes }) )

    tf = TrivialFormulator( REQUEST.URL0, REQUEST.form, descr,
                            {},
                            cancelbutton = 'Annuler', method='GET',
                            submitlabel = 'Supprimer ce groupe',
                            name='tf' )
    if  tf[0] == 0:
        return header + '\n'.join(H) + '\n' + tf[1] + context.sco_footer(REQUEST)
    elif tf[0] == -1:
        return REQUEST.RESPONSE.redirect( REQUEST.URL1 )
    else:
        # form submission
        formsemestre_id = tf[2]['formsemestre_id']
        groupType = tf[2]['groupType']
        groupName = tf[2]['groupName']
        if groupType=='TD':
            default_group = tf[2]['groupDest']
            req = 'update notes_formsemestre_inscription set groupetd=%(default_group)s where formsemestre_id=%(formsemestre_id)s and groupetd=%(groupName)s'
        elif groupType=='TP':
            default_group = None
            req = 'update notes_formsemestre_inscription set groupetp=%(default_group)s where formsemestre_id=%(formsemestre_id)s and groupetp=%(groupName)s'
        elif groupType=='TA':
            default_group = None
            req = 'update notes_formsemestre_inscription set groupeanglais=%(default_group)s where formsemestre_id=%(formsemestre_id)s and groupeanglais=%(groupName)s'
        else:
            raise ValueError, 'invalid group type: ' + groupType
        cnx = context.GetDBConnexion()
        cursor = cnx.cursor()
        aa = { 'formsemestre_id' : formsemestre_id,
               'groupName' : groupName,
               'default_group' : default_group }
        quote_dict(aa)
        log('suppressGroup( req=%s, args=%s )' % (req, aa) )
        cursor.execute( req, aa )
        cnx.commit()
        context.Notes._inval_cache(formsemestre_id=formsemestre_id)
        return REQUEST.RESPONSE.redirect( 'Notes/formsemestre_status?formsemestre_id=%s' % formsemestre_id )

def getGroupTypeName(sem, groupType):
    if groupType == 'TD':
        return sem['nomgroupetd']
    elif groupType == 'TP':
        return sem['nomgroupetp']
    elif groupType == 'TA':
        return sem['nomgroupeta']
    raise ValueError( 'invalid group type: ' + groupType)

def groupes_auto_repartition(context, formsemestre_id=None, groupType=None, REQUEST=None):
    """Reparti les etudiants dans des groupes, en respectant le niveau
    et la mixité.
    """
    if not context.Notes.can_change_groups(REQUEST, formsemestre_id):
        raise ScoValueError("Vous n'avez pas le droit d'effectuer cette opération !")
    sem = context.Notes.get_formsemestre(formsemestre_id)
    groupTypeName = getGroupTypeName(sem, groupType)
    if groupType == 'TD':
        grn = 'groupetd'
    elif groupType == 'TP':
        grn = 'groupetp'
    else:
        grn = 'groupeanglais'
    descr = [
        ('formsemestre_id', { 'input_type' : 'hidden' }),
        ('groupType', { 'input_type' : 'hidden' }),
        ('groupNames', { 'size' : 40, 'title' : 'Groupes à créer',
                         'explanation' : "noms des groupes à former, séparés par des virgules (il peut s'agir de groupes existant ou de nouveaux)"})
       ]
    
    H = [ context.sco_header(REQUEST, page_title='Répartition des groupes' ),
          '<h2>Répartition des groupes de %s</h2>' % groupTypeName,
          '<p>Semestre %s</p>' % sem['titreannee'],
          """<p class="help">Les groupes existants seront <b>détruits</b> et remplacés par
          ceux créés ici. La répartition aléatoire tente d'uniformiser le niveau
          des groupes (en utilisant la dernière moyenne générale disponible pour
          chaque étudiant) et de maximiser la mixité de chaque groupe.</p>"""
          ]
    
    tf = TrivialFormulator( REQUEST.URL0, REQUEST.form, descr,
                            {},
                            cancelbutton = 'Annuler', method='GET',
                            submitlabel = 'Créer et peupler les groupes',
                            name='tf' )
    if  tf[0] == 0:
        return '\n'.join(H) + '\n' + tf[1] + context.sco_footer(REQUEST)
    elif tf[0] == -1:
        return REQUEST.RESPONSE.redirect( REQUEST.URL1 )
    else:
        # form submission
        groupNames = tf[2]['groupNames']
        groupNames = [ x.strip() for x in groupNames.split(',') ]
        for groupName in groupNames:
            try:
                checkGroupName(groupName)
            except:
                H.append('<p class="warning">Nom de groupe invalide: %s</p>'%groupName)
                return '\n'.join(H) + tf[1] + context.sco_footer(REQUEST)
        
        nt = context.Notes._getNotesCache().get_NotesTable(context.Notes,formsemestre_id )
        identdict = nt.identdict
        # build:  { sexe : liste etudids trie par niveau croissant }
        sexes = sets.Set([ x['sexe'] for x in identdict.values() ])
        listes = {}
        for sexe in sexes:
            listes[sexe] = [ (get_prev_moy(context.Notes,x['etudid'],formsemestre_id),
                              x['etudid'])
                             for x in identdict.values() if x['sexe'] == sexe ]
            listes[sexe].sort()
            log('listes[%s] = %s' % (sexe,listes[sexe]) )
        # affect aux groupes:
        n = len(identdict)
        igroup = 0
        nbgroups = len(groupNames)
        while n > 0:
            for sexe in sexes:
                if len(listes[sexe]):
                    n -= 1
                    etudid = listes[sexe].pop()[1]
                    args = { 'REQUEST' : REQUEST, 'redirect' : False }
                    args[grn] = groupNames[igroup]
                    igroup = (igroup+1) % nbgroups
                    context.doChangeGroupe(etudid, formsemestre_id, **args)
                    log('%s in group %s' % (etudid,args[grn]) )
        # envoie sur page edition groupes
        return REQUEST.RESPONSE.redirect(
            'affectGroupes?formsemestre_id=%s&groupType=%s&groupTypeName=%s'
            % (formsemestre_id,groupType,groupTypeName) )

def get_prev_moy(znotes, etudid, formsemestre_id):
    """Donne la derniere moyenne generale calculee pour cette étudiant,
    ou 0 si on n'en trouve pas (nouvel inscrit,...).
    """
    info = znotes.getEtudInfo(etudid=etudid, filled=True)
    if not info:
        raise ScoValueError("etudiant invalide: etudid=%s" % etudid)
    etud = info[0]
    Se = sco_parcours_dut.SituationEtudParcours(znotes, etud, formsemestre_id)
    if Se.prev:
        nt = znotes._getNotesCache().get_NotesTable(znotes, Se.prev['formsemestre_id'] )
        return nt.get_etud_moy_gen(etudid)
    else:
        return 0.
