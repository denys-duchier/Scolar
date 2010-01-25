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
#   Emmanuel Viennet      emmanuel.viennet@gmail.com
#
##############################################################################

"""Gestion des groupes, nouvelle mouture (juin/nov 2009)

TODO:

* Groupes:

 - changement de groupe d'un seul etudiant:
     formChangeGroupe: pour l'instant supprimé, pas vraiment utile ?
     doChangeGroupe

Optimisation possible:
 revoir do_evaluation_listeetuds_groups() pour extraire aussi les groupes (de chaque etudiant)
 et eviter ainsi l'appel ulterieur à get_etud_groups() dans _make_table_notes

"""

import re, sets
# XML generation package (apt-get install jaxml)
import jaxml
import xml.dom.minidom

from odict import odict

from sco_utils import *
from notesdb import *
from notes_log import log
from scolog import logdb
from TrivialFormulator import TrivialFormulator, TF
import scolars
import sco_parcours_dut


def checkGroupName(groupName): # XXX unused: now allow any string as a  gropu or partition name
    "Raises exception if not a valid group name"
    if groupName and (
        not re.match( '^\w+$', groupName ) 
        or (simplesqlquote(groupName) != groupName)):
        log('!!! invalid group name: ' + groupName)
        raise ValueError('invalid group name: ' + groupName)

partitionEditor = EditableTable(
    'partition',
    'partition_id',
    ('partition_id', 'formsemestre_id', 'partition_name', 'compute_ranks', 'numero'))

groupEditor = EditableTable(
    'group_descr',
    'group_id',
    ( 'group_id', 'partition_id', 'group_name' ))

group_list = groupEditor.list

def get_group(context, group_id):
    """Returns group object, with partition"""
    r = SimpleDictFetch(context, 'SELECT gd.*, p.* FROM group_descr gd, partition p WHERE gd.group_id=%(group_id)s AND p.partition_id = gd.partition_id', {'group_id' : group_id })
    if not r:
        raise ValueError('invalid group_id (%s)' % group_id)
    return r[0]

def group_delete(context, group, force=False):
    """Delete a group.
    group 'all' cannot be deleted
    """
    if not group['group_name'] and not force:
        raise ValueError('cannot suppress this group')
    # remove memberships:
    SimpleQuery(context, "DELETE FROM group_membership WHERE group_id=%(group_id)s", group)
    # delete group:
    SimpleQuery(context, "DELETE FROM group_descr WHERE group_id=%(group_id)s", group)

def get_partition(context, partition_id):
    r = SimpleDictFetch(context, 'SELECT p.* FROM partition p WHERE p.partition_id = %(partition_id)s', {'partition_id' : partition_id })
    if not r:
        raise ValueError('invalid partition_id (%s)' % partition_id)
    return r[0]

def get_partitions_list(context, formsemestre_id, with_default=True):
    """Liste des partitions pour ce semestre (list of dicts)"""
    partitions = SimpleDictFetch(context, 'SELECT * FROM partition WHERE formsemestre_id=%(formsemestre_id)s order by numero', { 'formsemestre_id' : formsemestre_id } )
    # Move 'all' at end of list (for menus)
    R = [ p for p in partitions if p['partition_name'] != None ]
    if with_default:
        R += [ p for p in partitions if p['partition_name'] == None ]
    return R

def get_default_partition(context, formsemestre_id):
    """Get partition for 'all' students (this one always exists, with NULL name)"""
    r = SimpleDictFetch(context, 'SELECT * FROM partition WHERE formsemestre_id=%(formsemestre_id)s AND partition_name is NULL', {'formsemestre_id' : formsemestre_id} )
    if len(r) != 1:
        raise ScoException('inconsistent partition: %d with NULL name for formsemestre_id=%s'%(len(r),formsemestre_id))
    return r[0]

def get_formsemestre_groups(context, formsemestre_id):
    """Returns  { partition_id : { etudid : group } }
    """
    partitions = get_partitions_list(context, formsemestre_id, with_default=False)
    partitions_etud_groups = {} # { partition_id : { etudid : group } }
    for partition in partitions:
        pid=partition['partition_id']
        partitions_etud_groups[pid] = get_etud_groups_in_partition(context, pid)
    return partitions, partitions_etud_groups

def get_partition_groups(context, partition):
    """List of groups in this partition (list of dicts).
    Some groups may be empty."""    
    return SimpleDictFetch(context, 'SELECT gd.*, p.* FROM group_descr gd, partition p WHERE gd.partition_id=%(partition_id)s AND gd.partition_id=p.partition_id ORDER BY group_name', partition)

def get_default_group(context, formsemestre_id):
    """Returns group_id for default ('tous') group"""
    r = SimpleDictFetch(context, 'SELECT gd.group_id FROM group_descr gd, partition p WHERE p.formsemestre_id=%(formsemestre_id)s AND p.partition_name is NULL AND p.partition_id = gd.partition_id', {'formsemestre_id' : formsemestre_id })
    # debug check
    if len(r) != 1:
        raise ScoException('invalid group structure for %s' % formsemestre_id)
    group_id = r[0]['group_id']
    return group_id

def get_sem_groups(context, formsemestre_id): 
    """Returns groups for this sem."""
    return SimpleDictFetch(context, 'SELECT gd.*, p.* FROM group_descr gd, partition p WHERE p.formsemestre_id=%(formsemestre_id)s AND p.partition_id = gd.partition_id', {'formsemestre_id' : formsemestre_id })

def get_group_members(context, group_id, etat=None):  
    """Liste des etudiants d'un groupe.
    Si etat, filtre selon l'état de l'inscription
    """
    req = "SELECT i.*, a.*, gm.*, ins.etat FROM identite i, adresse a, group_membership gm, group_descr gd, partition p, notes_formsemestre_inscription ins WHERE i.etudid = gm.etudid and a.etudid = i.etudid and ins.etudid = i.etudid and ins.formsemestre_id = p.formsemestre_id and p.partition_id = gd.partition_id and gd.group_id = gm.group_id and gm.group_id=%(group_id)s"
    if etat is not None:
        req += " and ins.etat = %(etat)s"
    req +=  " ORDER BY i.nom"
    return SimpleDictFetch(context, req, { 'group_id' : group_id, 'etat' : etat} )

def get_group_infos(context, group_id, etat=None): # was _getlisteetud
    """legacy code: used by  listegroupe and trombino
    """
    cnx = context.GetDBConnexion()
    cursor = cnx.cursor()
    group = get_group(context, group_id)
    sem = context.Notes.get_formsemestre(group['formsemestre_id'])
    other_partitions = [ p for p in get_partitions_list(context, sem['formsemestre_id'] ) if p['partition_id'] != group['partition_id'] and p['partition_name'] ]
    members = get_group_members(context, group_id, etat=etat)
    # add human readable description of state:
    nbdem = 0
    for t in members:
        if t['etat'] == 'I':
            t['etath'] = '' # etudiant inscrit, ne l'indique pas dans la liste HTML
        elif t['etat'] == 'D':
            events = scolars.scolar_events_list(
                cnx, args={'etudid':t['etudid'], 'formsemestre_id':group['formsemestre_id']} )
            for event in events:
                event_type = event['event_type']
                if event_type == 'DEMISSION':
                    t['date_dem'] = event['event_date']
                    break            
            if 'date_dem' in t:
                t['etath'] = 'démission le %s' % t['date_dem']
            else:
                t['etath'] = '(dem.)'
            nbdem += 1
    # Add membership for all partitions, 'partition_id' : group
    for etud in members: # long: comment eviter ces boucles ?  
        etud_add_group_infos(context, etud, sem)
    
    if group['group_name'] != None:
        group_tit = '%s %s' % (group['partition_name'], group['group_name'])
    else:
        group_tit = 'tous'

    return members, group, group_tit, sem, nbdem, other_partitions

def get_etud_groups(context, etudid, sem, exclude_default=False):
    """Infos sur groupes de l'etudiant dans ce semestre
    [ group + partition_name ]
    """
    req = "SELECT p.*, g.* from group_descr g, partition p, group_membership gm WHERE gm.etudid=%(etudid)s and gm.group_id = g.group_id and g.partition_id = p.partition_id and p.formsemestre_id = %(formsemestre_id)s"
    if exclude_default:
        req += " and p.partition_name is not NULL"
    groups = SimpleDictFetch(context, req + " ORDER BY p.numero", { 'etudid' : etudid, 'formsemestre_id' : sem['formsemestre_id']})
    return _sortgroups(groups)

def get_etud_main_group(context, etudid, sem):
    """Return main group (the first one) for etud, or default one if no groups"""
    groups = get_etud_groups(context, etudid, sem, exclude_default=True)
    if groups:
        return groups[0]
    else:
        return get_group(context, get_default_group(context, sem['formsemestre_id']))

def formsemestre_get_main_partition(context, formsemestre_id):
    """Return main partition (the first one) for etud, or default one if no groups
    (rappel: default == tous, main == principale (groupes TD habituellement)
    """
    return get_partitions_list(context, formsemestre_id, with_default=True)[0]

def formsemestre_get_etud_groupnames(context, formsemestre_id, attr='group_name'):
    """Recupere les groupes de tous les etudiants d'un semestre
    { etudid : { partition_id : group_name  }}  (attr=group_name or group_id)
    """
    infos = SimpleDictFetch(context,"select i.etudid, p.partition_id, gd.group_name, gd.group_id from notes_formsemestre_inscription i, partition p, group_descr gd, group_membership gm where i.formsemestre_id=%(formsemestre_id)s and i.formsemestre_id=p.formsemestre_id and p.partition_id=gd.partition_id and gm.etudid=i.etudid and gm.group_id = gd.group_id and p.partition_name is not NULL", { 'formsemestre_id' : formsemestre_id } )
    R = {}
    for info in infos:
        if info['etudid'] in R:            
            R[info['etudid']][info['partition_id']] = info[attr]
        else:
            R[info['etudid']] = { info['partition_id'] : info[attr] }
    return R

def etud_add_group_infos(context, etud, sem):
    """Add informations on partitions and group memberships to etud (a dict with an etudid)
    """
    etud['partitions'] = odict() # partition_id : group + partition_name
    if not sem:
        etud['groupes'] = ''
        return etud
    
    infos = SimpleDictFetch(context, "SELECT p.partition_name, g.* from group_descr g, partition p, group_membership gm WHERE gm.etudid=%(etudid)s and gm.group_id = g.group_id and g.partition_id = p.partition_id and p.formsemestre_id = %(formsemestre_id)s ORDER BY p.numero", { 'etudid' : etud['etudid'], 'formsemestre_id' : sem['formsemestre_id']})

    for info in infos:
        if info['partition_name']:
            etud['partitions'][info['partition_id']] = info
    
    # resume textuel des groupes:        
    etud['groupes'] = ' '.join( [ g['group_name'] for g in infos if g['group_name'] != None ] )

    return etud

def get_etud_groups_in_partition(context, partition_id):
    """Returns { etudid : group }, with all students in this partition"""
    infos = SimpleDictFetch(context, "SELECT gd.*, etudid from group_descr gd, group_membership gm where gd.partition_id = %(partition_id)s and gm.group_id = gd.group_id", { 'partition_id': partition_id})
    R = {}
    for i in infos:
        R[i['etudid']] = i
    return R

def XMLgetGroupsInPartition(context, partition_id, REQUEST=None): # was XMLgetGroupesTD
    """Liste des étudiants dans chaque groupe de cette partition.
    <group partition_id="" partition_name="" group_id="" group_name="">
    <etud etuid="" sexe="" nom="" prenom="" origin=""/>
    </groupe>
    """
    t0 = time.time()
    partition = get_partition(context, partition_id)
    formsemestre_id = partition['formsemestre_id']
    sem = context.Notes.get_formsemestre(formsemestre_id)
    groups = get_partition_groups(context, partition)
    nt = context.Notes._getNotesCache().get_NotesTable(context.Notes, formsemestre_id) #> inscrdict
    etuds_set = set(nt.inscrdict)
    # XML response:
    REQUEST.RESPONSE.setHeader('Content-type', XML_MIMETYPE)
    doc = jaxml.XML_document( encoding=SCO_ENCODING )
    doc._text( '<ajax-response><response type="object" id="MyUpdater">' )
    doc._push()

    for group in groups:
        doc._push()
        doc.group( partition_id=partition_id, partition_name=partition['partition_name'], 
                    group_id = group['group_id'], group_name = group['group_name'] )
        for e in get_group_members(context, group['group_id']):
            etud = context.getEtudInfo(etudid=e['etudid'], filled=1)[0]          
            doc._push()
            doc.etud( etudid=e['etudid'],
                      sexe=scolars.format_sexe(etud['sexe']),
                      nom=scolars.format_nom(etud['nom']),
                      prenom=scolars.format_prenom(etud['prenom']),
                      origin=comp_origin(etud, sem)
                      )
            if e['etudid'] in etuds_set:
                etuds_set.remove(e['etudid']) # etudiant vu dans un groupe
            doc._pop()
        doc._pop()
    
    # Ajoute les etudiants inscrits au semestre mais dans aucun groupe de cette partition:
    if etuds_set:
        doc._push()
        doc.group( partition_id=partition_id, partition_name=partition['partition_name'], 
                   group_id = '_none_', group_name = '' )
        for etudid in etuds_set:
            etud = context.getEtudInfo(etudid=etudid, filled=1)[0]
            doc._push()
            doc.etud( etudid=etud['etudid'],
                      sexe=scolars.format_sexe(etud['sexe']),
                      nom=scolars.format_nom(etud['nom']),
                      prenom=scolars.format_prenom(etud['prenom']),
                      origin=comp_origin(etud, sem)
                      )
            doc._pop()
        doc._pop()
    doc._pop()
    
    doc._text( '</response></ajax-response>' )
    log('XMLgetGroupsInPartition: %s seconds' % (time.time() - t0))
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



def set_group(context, etudid, group_id):
    """Inscrit l'étudiant au groupe.
    Return True if ok, False si deja inscrit.
    Warning: don't check if group_id exists (the caller should check).
    """
    cnx = context.GetDBConnexion()
    cursor = cnx.cursor()
    args = { 'etudid' : etudid, 'group_id' : group_id }
    # déjà inscrit ?
    r = SimpleDictFetch(context, "SELECT * FROM group_membership gm WHERE etudid=%(etudid)s and group_id=%(group_id)s", args, cursor=cursor)
    if len(r):
        return False
    # inscrit
    SimpleQuery(context, "INSERT INTO group_membership (etudid, group_id) VALUES (%(etudid)s, %(group_id)s)", args, cursor=cursor)
    return True


def change_etud_group_in_partition(context, etudid, group_id, partition, REQUEST=None):
    """Inscrit etud au group de cette partition, et le desinscrit d'autres groupes de cette partition.
    """
    log('change_etud_group_in_partition: etudid=%s group_id=%s' % (etudid, group_id))
    formsemestre_id = partition['formsemestre_id']
    # 0- verifie que le groupe est bien dans cette partition
    group = get_group(context, group_id)
    if group['partition_id'] != partition['partition_id']:
        raise ValueError('inconsistent group/partition (group_id=%s, partition_id=%s)' % (group_id,partition['partition_id']))
    
    # 1- supprime membreship dans cette partition
    SimpleQuery(context, "DELETE FROM group_membership WHERE group_membership_id IN (SELECT gm.group_membership_id FROM group_membership gm, group_descr gd WHERE gm.etudid=%(etudid)s AND gm.group_id=gd.group_id AND gd.partition_id=%(partition_id)s)", { 'etudid' : etudid, 'partition_id' : partition['partition_id'] })
    
    # 2- associe au nouveau groupe
    set_group(context, etudid, group_id)
    
    # 3- log
    if REQUEST:
        cnx = context.GetDBConnexion()
        logdb(REQUEST, cnx, method='changeGroup', etudid=etudid,
              msg='formsemestre_id=%s,partition_name=%s, group_name=%s' %
              (formsemestre_id,partition['partition_name'],group['group_name']))
        cnx.commit()
    # 4- invalidate cache
    context.Notes._inval_cache(formsemestre_id=formsemestre_id) #> change etud group

def setGroups(context, partition_id,
              groupsLists='',  # members of each existing group
              groupsToCreate='', # name and members of new groups
              groupsToDelete='', # groups to delete
              REQUEST=None):
    """Affect groups (Ajax request)
    groupsLists: lignes de la forme "group_id;etudid;...\n"
    groupsToCreate: lignes "group_name;etudid;...\n"
    groupsToDelete: group_id;group_id;...
    """
    partition = get_partition(context, partition_id)
    formsemestre_id = partition['formsemestre_id']
    if not context.Notes.can_change_groups(REQUEST, formsemestre_id):
            raise AccessDenied("Vous n'avez pas le droit d'effectuer cette opération !")
    log('***setGroups: partition_id=%s' % partition_id)
    log('groupsLists=%s' % groupsLists)
    log('groupsToCreate=%s' % groupsToCreate )
    log('groupsToDelete=%s' % groupsToDelete )
    sem = context.Notes.get_formsemestre(formsemestre_id)        
    if sem['etat'] != '1':
        raise AccessDenied('Modification impossible: semestre verrouillé')

    groupsToDelete = [ g for g in groupsToDelete.split(';') if g ]

    etud_groups = formsemestre_get_etud_groupnames(context, formsemestre_id, attr='group_id')    
    for line in groupsLists.split('\n'): # for each group_id (one per line)
        fs = line.split(';')
        group_id = fs[0].strip()
        if not group_id:
            continue
        group = get_group(context,group_id)
        # Anciens membres du groupe:
        old_members = get_group_members(context, group_id)
        old_members_set = set( [ x['etudid'] for x in old_members ] )
        # Place dans ce groupe les etudiants indiqués:
        for etudid in fs[1:-1]:
            if etudid in old_members_set:
                old_members_set.remove(etudid) # a nouveau dans ce groupe, pas besoin de l'enlever
            if (etudid not in etud_groups) or (group_id != etud_groups[etudid].get(partition_id,'')): # pas le meme groupe qu'actuel
                change_etud_group_in_partition(context, etudid, group_id, partition, REQUEST=REQUEST)
        # Retire les anciens membres:
        cnx = context.GetDBConnexion()
        cursor = cnx.cursor()
        for etudid in old_members_set:            
            log('removing %s from group %s' % (etudid,group_id))
            SimpleQuery(context, "DELETE FROM group_membership WHERE etudid=%(etudid)s and group_id=%(group_id)s", { 'etudid' : etudid, 'group_id' : group_id }, cursor=cursor)
            logdb(REQUEST, cnx, method='removeFromGroup', etudid=etudid,
              msg='formsemestre_id=%s,partition_name=%s, group_name=%s' %
              (formsemestre_id,partition['partition_name'],group['group_name']))

    # Supprime les groupes indiqués comme supprimés:
    for group_id in groupsToDelete:
        suppressGroup(context, group_id,  partition_id=partition_id, REQUEST=REQUEST)

    # Crée les nouveaux groupes
    for line in groupsToCreate.split('\n'): # for each group_name (one per line)
        fs = line.split(';')
        group_name = fs[0].strip()        
        if not group_name:
            continue
        # ajax arguments are encoded in utf-8:
        group_name = unicode(group_name, 'utf-8').encode(SCO_ENCODING)
        group_id = createGroup(context, partition_id, group_name, REQUEST=REQUEST)
        # Place dans ce groupe les etudiants indiqués:
        for etudid in fs[1:-1]:
            change_etud_group_in_partition(context, etudid, group_id, partition, REQUEST=REQUEST)
    
    REQUEST.RESPONSE.setHeader('Content-type', XML_MIMETYPE)
    return 'Groupes enregistrés'


def createGroup(context, partition_id, group_name='', default=False, REQUEST=None):
    """Create a new group in this partition
    (called from JS)
    """
    partition = get_partition(context, partition_id)
    formsemestre_id = partition['formsemestre_id']
    if not context.Notes.can_change_groups(REQUEST, formsemestre_id):
        raise AccessDenied("Vous n'avez pas le droit d'effectuer cette opération !")
    #
    if group_name:
        group_name = group_name.strip()
    if not group_name and not default:
        raise ValueError('invalid group name: ()')
    # checkGroupName(group_name)
    if group_name in [ g['group_name'] for g in get_partition_groups(context, partition) ]:
        raise ValueError('group_name %s already exists in partition'%group_name) # XXX FIX: incorrect error handling (in AJAX)
    cnx = context.GetDBConnexion()
    group_id = groupEditor.create(cnx,  {'partition_id': partition_id, 'group_name' : group_name})
    log('createGroup: created group_id=%s' % group_id)
    #
    return group_id 

def suppressGroup(context, group_id,  partition_id=None, REQUEST=None):
    """form suppression d'un groupe.
    (ne desinscrit pas les etudiants, change juste leur
    affectation aux groupes)
    partition_id est optionnel et ne sert que pour verifier que le groupe
    est bien dans cette partition.
    """
    group = get_group(context, group_id)
    if partition_id:
        if partition_id != group['partition_id']:
            raise ValueError('inconsistent partition/group')
    else:
        partition_id = group['partition_id']
    partition = get_partition(context, partition_id)
    if not context.Notes.can_change_groups(REQUEST, partition['formsemestre_id']):
        raise AccessDenied("Vous n'avez pas le droit d'effectuer cette opération !")
    log( 'suppressGroup: group_id=%s group_name=%s partition_name=%s' % (group_id, group['group_name'], partition['partition_name'] ) )
    group_delete(context, group )

def partition_create(context, formsemestre_id, partition_name='', default=False, numero=None, REQUEST=None, redirect=1):
    """Create a new partition"""
    if not context.Notes.can_change_groups(REQUEST, formsemestre_id):
        raise AccessDenied("Vous n'avez pas le droit d'effectuer cette opération !")
    if partition_name:
        partition_name = partition_name.strip()
    if default:
        partition_name = None
    if not partition_name and not default:
        raise ScoValueError('Nom de partition invalide (vide)')
    redirect = int(redirect)
    # checkGroupName(partition_name)
    if partition_name in [ p['partition_name'] for p in get_partitions_list(context, formsemestre_id) ]:
        raise ScoValueError('Il existe déjà une partition %s dans ce semestre'%partition_name) 
    
    cnx = context.GetDBConnexion()
    partition_id = partitionEditor.create(cnx, {'formsemestre_id':formsemestre_id, 'partition_name':partition_name} )
    log('createPartition: created partition_id=%s' % partition_id)
    #
    if redirect:
        return REQUEST.RESPONSE.redirect('editPartitionForm?formsemestre_id='+formsemestre_id)
    else:
        return partition_id 

def checkLastIcon(context, REQUEST):
    """Check that most recent icon is installed.
    If not, rebuild icons in Zope.
    XXX now unnecessary (was for Zope icons), we now use icontag() from sco_utils.py
    """
    try: 
        a = context.icons.delete_small_img
    except:
        context.do_build_icons_folder(REQUEST)

def getArrowIconsTags(context, REQUEST):
    """returns html tags for arrows"""
    # check that we have new icons:
    checkLastIcon(context,REQUEST)
    #
    arrow_up   = icontag('arrow_up', title='remonter')
    arrow_down = icontag('arrow_down', title='descendre')
    arrow_none = icontag('arrow_none', title='')
    
    return arrow_up, arrow_down, arrow_none

def editPartitionForm(context, formsemestre_id=None, REQUEST=None):
    """Form to create/suppress partitions"""
    # ad-hoc form 
    canedit = context.Notes.can_change_groups(REQUEST, formsemestre_id)
    partitions = get_partitions_list(context, formsemestre_id)
    arrow_up, arrow_down, arrow_none = getArrowIconsTags(context, REQUEST)
    #
    H = [ context.sco_header(REQUEST, page_title="Partitions..."),
          """<script type="text/javascript">
          function checkname() {
 var val = document.editpart.partition_name.value.replace(/^\s+/, "").replace(/\s+$/, "");
 if (val.length > 0) {
   document.editpart.ok.disabled = false;
 } else {
   document.editpart.ok.disabled = true;
 }
}
          </script>
          """,
          """<h2>Partitions du semestre</h2>
          <form name="editpart" id="editpart" method="POST" action="partition_create">
          <table><tr><th></th><th></th><th>Nom</th><th>Groupes</th><th></th><th></th><th></th></tr>
    """ ]
    i = 0
    for p in partitions:
        if p['partition_name'] is not None:
            H.append('<tr><td>')
            if i != 0:
                H.append('<a href="partition_move?partition_id=%s&after=0">%s</a>' % (p['partition_id'], arrow_up))
            H.append('</td><td>')
            if i < len(partitions) - 2:
                H.append('<a href="partition_move?partition_id=%s&after=1">%s</a>' % (p['partition_id'], arrow_down))
            i += 1
            H.append('</td>')
            pname = p['partition_name'] or ''
            H.append('<td>%s</td>' % pname)
            H.append('<td>')
            for group in get_partition_groups(context, p):
                n = len(get_group_members(context, group['group_id']))
                H.append( '%s (%d)' % (group['group_name'], n))
            H.append('</td><td><a class="stdlink" href="affectGroups?partition_id=%s">répartir</a></td>' % p['partition_id'] )     
            H.append('<td><a class="stdlink" href="partition_rename?partition_id=%s">renommer</a></td>' % p['partition_id'] )
            H.append('<td><a class="stdlink" href="partition_delete?partition_id=%s">supprimer</a></td>' % p['partition_id'] )
            H.append('</tr>')
    H.append('</table>')
    H.append('<div class="form_rename_partition">')
    H.append('<input type="hidden" name="formsemestre_id" value="%s"/>' % formsemestre_id)
    H.append('<input type="hidden" name="redirect" value="1"/>')
    H.append('<input type="text" name="partition_name" size="12" onkeyup="checkname();"/>')
    H.append('<input type="submit" name="ok" disabled="1" value="Nouvelle partition"/>')
    H.append('</div></form>')
    H.append("""<p class="help">Les partitions sont des découpages de l'ensemble des étudiants. Par exemple, les "groupes de TD" sont une partition. On peut créer autant de partitions que nécessaire. Dans chaque partition, un nombre de groupes quelconque peuvent être créés (suivre le lien "répartir").</p>""")
    return '\n'.join(H) + context.sco_footer(REQUEST)

def partition_delete(context, partition_id, REQUEST=None, force=False, redirect=1, dialog_confirmed=False):
    """Suppress a partition (and all groups within).
    default partition cannot be suppressed (unless force)"""
    partition = get_partition(context, partition_id)
    formsemestre_id = partition['formsemestre_id']
    if not context.Notes.can_change_groups(REQUEST, formsemestre_id):
        raise AccessDenied("Vous n'avez pas le droit d'effectuer cette opération !")

    if not partition['partition_name'] and not force:
        raise ValueError('cannot suppress this partition')
    redirect = int(redirect)
    cnx = context.GetDBConnexion()
    groups = get_partition_groups(context, partition)
    
    if not dialog_confirmed:
        if groups:
            grnames = '(' + ', '.join( [ g['group_name'] for g in groups ] ) + ')'
        else:
            grnames = ''
        return context.confirmDialog(
                """<h2>Supprimer la partition "%s" ?</h2>
                <p>Les groupes %s de cette partition seront supprimés</p>
                """ % (partition['partition_name'], grnames),
                dest_url="", REQUEST=REQUEST,
                cancel_url="editPartitionForm?formsemestre_id=%s" % formsemestre_id,
                parameters={'redirect':redirect, 'partition_id' : partition_id})
    
    log('partition_delete: partition_id=%s' % partition_id)
    # 1- groups
    for group in groups:
        group_delete(context, group, force=force)
    # 2- partition
    partitionEditor.delete(cnx, partition_id)
    
    # redirect to partition edit page:
    if redirect:
        return REQUEST.RESPONSE.redirect('editPartitionForm?formsemestre_id='+formsemestre_id)

def partition_move(context, partition_id, after=0, REQUEST=None, redirect=1):
    """Move before/after previous one (decrement/increment numero)"""
    partition = get_partition(context, partition_id)
    formsemestre_id = partition['formsemestre_id']
    if not context.Notes.can_change_groups(REQUEST, formsemestre_id):
        raise AccessDenied("Vous n'avez pas le droit d'effectuer cette opération !")
    #
    redirect = int(redirect)
    after = int(after) # 0: deplace avant, 1 deplace apres
    if after not in (0,1):
        raise ValueError('invalid value for "after"')
    others = get_partitions_list(context, formsemestre_id)
    if len(others) > 1:        
        pidx = [ p['partition_id'] for p in others ].index(partition_id)
        log('partition_move: after=%s pidx=%s' % (after, pidx))
        neigh = None # partition to swap with
        if after == 0 and pidx > 0:
            neigh = others[pidx-1]            
        elif after == 1 and pidx < len(others)-1:
            neigh = others[pidx+1]
        if neigh: # 
            # swap numero between partition and its neighbor
            log('moving partition %s' % partition_id)
            cnx = context.GetDBConnexion()
            partition['numero'], neigh['numero'] = neigh['numero'], partition['numero']
            partitionEditor.edit(cnx, partition)
            partitionEditor.edit(cnx, neigh)
            
    # redirect to partition edit page:
    if redirect:
        return REQUEST.RESPONSE.redirect('editPartitionForm?formsemestre_id='+formsemestre_id)

def partition_rename(context, partition_id, REQUEST=None):
    """Form to rename a partition"""
    partition = get_partition(context, partition_id)
    formsemestre_id = partition['formsemestre_id']
    if not context.Notes.can_change_groups(REQUEST, formsemestre_id):
        raise AccessDenied("Vous n'avez pas le droit d'effectuer cette opération !")
    H = [ '<h2>Renommer une partition</h2>' ]
    tf = TrivialFormulator( REQUEST.URL0, REQUEST.form,
                            ( ('partition_id', { 'default' : partition_id, 'input_type' : 'hidden' }),
                              ('partition_name', { 'title' : 'Nouveau nom', 'default' : partition['partition_name'],
                                                   'size' : 12 })
                              ),
                            submitlabel = 'Renommer',
                            cancelbutton = 'Annuler')
    if  tf[0] == 0:
        return context.sco_header(REQUEST) + '\n'.join(H) + '\n' + tf[1] + context.sco_footer(REQUEST)
    elif tf[0] == -1:
            return REQUEST.RESPONSE.redirect('editPartitionForm?formsemestre_id='+formsemestre_id)
    else:
        # form submission
        return partition_set_name(context, partition_id, tf[2]['partition_name'], REQUEST=REQUEST, redirect=1)

def partition_set_name(context, partition_id, partition_name, REQUEST=None, redirect=1):
    """Set partition name"""
    partition = get_partition(context, partition_id)
    if partition['partition_name'] is None:
        raise ValueError("can't set a name to default partition")
    formsemestre_id = partition['formsemestre_id']
    if not context.Notes.can_change_groups(REQUEST, formsemestre_id):
        raise AccessDenied("Vous n'avez pas le droit d'effectuer cette opération !")
    redirect = int(redirect)
    cnx = context.GetDBConnexion()
    partitionEditor.edit(cnx, { 'partition_id' : partition_id, 'partition_name' : partition_name })
    
    # redirect to partition edit page:
    if redirect:
        return REQUEST.RESPONSE.redirect('editPartitionForm?formsemestre_id='+formsemestre_id)

def group_set_name(context, group_id, group_name, REQUEST=None, redirect=1):
    """Set group name"""
    group = get_group(context, group_id)
    if group['group_name'] is None:
        raise ValueError("can't set a name to default group")
    formsemestre_id = group['formsemestre_id']
    if not context.Notes.can_change_groups(REQUEST, formsemestre_id):
        raise AccessDenied("Vous n'avez pas le droit d'effectuer cette opération !")
    redirect = int(redirect)
    cnx = context.GetDBConnexion()
    groupEditor.edit(cnx, { 'group_id' : group_id, 'group_name' : group_name })
    
    # redirect to partition edit page:
    if redirect:
        return REQUEST.RESPONSE.redirect('affectGroups?partition_id='+group['partition_id'])

def group_rename(context, group_id, REQUEST=None):
    """Form to rename a group"""
    group = get_group(context, group_id)
    formsemestre_id = group['formsemestre_id']
    if not context.Notes.can_change_groups(REQUEST, formsemestre_id):
        raise AccessDenied("Vous n'avez pas le droit d'effectuer cette opération !")
    H = [ '<h2>Renommer un groupe de %s</h2>' % group['partition_name'] ]
    tf = TrivialFormulator( REQUEST.URL0, REQUEST.form,
                            ( ('group_id', { 'default' : group_id, 'input_type' : 'hidden' }),
                              ('group_name', { 'title' : 'Nouveau nom', 'default' : group['group_name'],
                                               'size' : 12 })
                              ),
                            submitlabel = 'Renommer',
                            cancelbutton = 'Annuler')
    if  tf[0] == 0:
        return context.sco_header(REQUEST) + '\n'.join(H) + '\n' + tf[1] + context.sco_footer(REQUEST)
    elif tf[0] == -1:
            return REQUEST.RESPONSE.redirect('affectGroups?partition_id='+group['partition_id'])
    else:
        # form submission
        return group_set_name(context, group_id, tf[2]['group_name'], REQUEST=REQUEST, redirect=1)

def groups_auto_repartition(context, partition_id=None, REQUEST=None):
    """Reparti les etudiants dans des groupes dans une partition, en respectant le niveau
    et la mixité.
    """
    partition = get_partition(context, partition_id)
    formsemestre_id = partition['formsemestre_id']
    if not context.Notes.can_change_groups(REQUEST, formsemestre_id):
        raise AccessDenied("Vous n'avez pas le droit d'effectuer cette opération !")    
    sem = context.Notes.get_formsemestre(formsemestre_id)
    
    descr = [
        ('partition_id', { 'input_type' : 'hidden' }),
        ('groupNames', { 'size' : 40, 'title' : 'Groupes à créer',
                         'explanation' : "noms des groupes à former, séparés par des virgules (les groupes existants seront effacés)"})
       ]
    
    H = [ context.sco_header(REQUEST, page_title='Répartition des groupes' ),
          '<h2>Répartition des groupes de %s</h2>' % partition['partition_name'],
          '<p>Semestre %s</p>' % sem['titreannee'],
          """<p class="help">Les groupes existants seront <b>effacés</b> et remplacés par
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
        log('groups_auto_repartition( partition_id=%s partition_name=%s' % (partition_id, partition['partition_name']))
        groupNames = tf[2]['groupNames']
        group_names = [ x.strip() for x in groupNames.split(',') ]
        # Détruit les groupes existant de cette partition
        for old_group in get_partition_groups(context, partition):
            group_delete(context, old_group)
        # Crée les nouveaux groupes
        group_ids = []
        for group_name in group_names:
            # try:
            #     checkGroupName(group_name)
            # except:
            #     H.append('<p class="warning">Nom de groupe invalide: %s</p>'%group_name)
            #     return '\n'.join(H) + tf[1] + context.sco_footer(REQUEST)
            group_ids.append(createGroup(context, partition_id, group_name, REQUEST=REQUEST))
        #
        nt = context.Notes._getNotesCache().get_NotesTable(context.Notes,formsemestre_id ) #> identdict 
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
        nbgroups = len(group_ids)
        while n > 0:
            for sexe in sexes:
                if len(listes[sexe]):
                    n -= 1
                    etudid = listes[sexe].pop()[1]
                    group_id = group_ids[igroup]
                    igroup = (igroup+1) % nbgroups
                    change_etud_group_in_partition(context, etudid, group_id, partition, REQUEST=REQUEST)
                    log('%s in group %s' % (etudid,group_id) )
        # envoie sur page edition groupes
        return REQUEST.RESPONSE.redirect('affectGroups?partition_id=%s' % partition_id)


def get_prev_moy(znotes, etudid, formsemestre_id):
    """Donne la derniere moyenne generale calculee pour cette étudiant,
    ou 0 si on n'en trouve pas (nouvel inscrit,...).
    """
    import sco_parcours_dut
    info = znotes.getEtudInfo(etudid=etudid, filled=True)
    if not info:
        raise ScoValueError("etudiant invalide: etudid=%s" % etudid)
    etud = info[0]
    Se = sco_parcours_dut.SituationEtudParcours(znotes, etud, formsemestre_id)
    if Se.prev:
        nt = znotes._getNotesCache().get_NotesTable(znotes, Se.prev['formsemestre_id'] ) #> get_etud_moy_gen
        return nt.get_etud_moy_gen(etudid)
    else:
        return 0.

def do_evaluation_listeetuds_groups(context, evaluation_id, groups=None,
                                    getallstudents=False,
                                    include_dems=False):
    """Donne la liste des etudids inscrits a cette evaluation dans les
    groupes indiqués.
    Si getallstudents==True, donne tous les etudiants inscrits a cette
    evaluation.
    Si include_dems, compte aussi les etudiants démissionnaires
    (sinon, par défaut, seulement les 'I')
    """
    fromtables = [ 'notes_moduleimpl_inscription Im', 
                   'notes_formsemestre_inscription Isem', 
                   'notes_moduleimpl M', 
                   'notes_evaluation E' ]
    # construit condition sur les groupes
    if not getallstudents:
        if not groups:
            return [] # no groups, so no students
        rg = [ "gm.group_id = '%(group_id)s'" % g for g in groups ]
        rq = "and Isem.etudid = gm.etudid and gd.partition_id = p.partition_id and p.formsemestre_id = Isem.formsemestre_id"
        r = rq + ' AND (' + ' or '.join(rg) + ' )'
        fromtables += [ 'group_membership gm', 'group_descr gd', 'partition p' ]
    else:
        r = ''        

    # requete complete
    req = "SELECT distinct Im.etudid from " + ', '.join(fromtables) + " WHERE Isem.etudid=Im.etudid and Im.moduleimpl_id=M.moduleimpl_id and Isem.formsemestre_id=M.formsemestre_id and E.moduleimpl_id=M.moduleimpl_id and E.evaluation_id = %(evaluation_id)s"
    if not include_dems:
        req += " and Isem.etat='I'"
    req += r
    cnx = context.GetDBConnexion()
    cursor = cnx.cursor()
    cursor.execute( req, { 'evaluation_id' : evaluation_id } )
    #log('listeetuds_groups: getallstudents=%s  groups=%s' % (getallstudents,groups))
    #log('req=%s' % (req % { 'evaluation_id' : "'"+evaluation_id+"'" }))
    res = cursor.fetchall()
    return [ x[0] for x in res ]


def do_evaluation_listegroupes(context, evaluation_id, include_default=False):
    """Donne la liste des groupes dans lesquels figurent des etudiants inscrits 
    au module/semestre auquel appartient cette evaluation.
    Si include_default, inclue aussi le groupe par defaut ('tous')
    [ group ]
    """
    if include_default:
        c = ''
    else:
        c =  ' AND p.partition_name is not NULL'
    cnx = context.GetDBConnexion()
    cursor = cnx.cursor()    
    cursor.execute( "SELECT DISTINCT gd.group_id FROM group_descr gd, group_membership gm, partition p, notes_moduleimpl m, notes_evaluation e WHERE gm.group_id = gd.group_id and gd.partition_id = p.partition_id and p.formsemestre_id = m.formsemestre_id and m.moduleimpl_id = e.moduleimpl_id and e.evaluation_id = %(evaluation_id)s" + c, { 'evaluation_id' : evaluation_id } )
    res = cursor.fetchall()
    group_ids = [ x[0] for x in res ]
    return listgroups(context, group_ids)

def listgroups(context, group_ids):
    cnx = context.GetDBConnexion()
    cursor = cnx.cursor()
    groups = []
    for group_id in group_ids:
        cursor.execute( "SELECT gd.*, p.* FROM group_descr gd, partition p WHERE p.partition_id = gd.partition_id AND gd.group_id = %(group_id)s",
                        { 'group_id' : group_id } )
        groups.append(cursor.dictfetchall()[0])
    return _sortgroups(groups)

def _sortgroups(groups):
    # Tri: place 'all' en tête, puis groupe par partition / nom de groupe
    R = [ g for g in groups if g['partition_name'] is None ]
    o = [  g for g in groups if g['partition_name'] != None ]    
    o.sort( key=lambda x: (x['numero'], x['group_name']) )
    
    return R + o

def listgroups_filename(groups):
    """Build a filename representing groups"""
    return 'gr' + '+'.join( [ g['group_name'] or 'tous' for g in groups ] )

def listgroups_abbrev(groups):
    """Human readable abbreviation descring groups (eg "A / AB / B3")"""
    return ' / '.join( [ g['group_name'] for g in groups if g['group_name']] )


# form_group_choice replaces formChoixGroupe
def form_group_choice(context, formsemestre_id, 
                      allow_none=True, #  offre un choix vide dans chaque partition
                      select_default=True, # Le groupe par defaut est mentionné (hidden).
                      display_sem_title=False
                      ):
    """Partie de formulaire pour le choix d'un ou plusieurs groupes.
    Variable : group_ids
    """
    sem = context.Notes.get_formsemestre(formsemestre_id)
    if display_sem_title:
        sem_title = '%s: ' % sem['titremois']
    else:
        sem_title = ''
    #
    H = [ """<table>""" ]
    for p in get_partitions_list(context, formsemestre_id):
        if p['partition_name'] is None:
            if select_default:
                H.append('<input type="hidden" name="group_ids:list" value="%s"/>'
                         % get_partition_groups(context, p)[0]['group_id'])
        else:
            H.append('<tr><td>Groupe de %(partition_name)s</td><td>' % p )
            H.append('<select name="group_ids:list">')
            if allow_none:
                H.append('<option value="">aucun</option>')
            for group in get_partition_groups(context, p):
                H.append('<option value="%s">%s %s</option>' % (group['group_id'], sem_title, group['group_name']))
            H.append('</select></td></tr>')
    H.append("""</table>""")
    return '\n'.join(H) 

def make_query_groups(group_ids):
    if group_ids:
        return '&'.join( [ 'group_ids%3Alist=' + group_id for group_id in group_ids ] )
    else:
        return ''

class GroupIdInferer:
    def __init__(self, context, formsemestre_id):
        groups = get_sem_groups(context, formsemestre_id)
        name2group_id = {}
        for group in groups:
            name2group_id[group['group_name']] = group['group_id']
        self.name2group_id = name2group_id
    
    def __getitem__(self, name):
        """Get group_id from group_name, or None is nonexistent"""
        group_id = self.name2group_id.get(name, None)
        if group_id is None and name[-2:] == '.0':
            # si nom groupe numerique, excel ajoute parfois ".0" !
            name = name[:-2]
            group_id = self.name2group_id.get(name, None)
        return group_id

