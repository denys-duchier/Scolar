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

"""Opérations d'inscriptions aux semestres et modules
"""


from notesdb import *
from sco_utils import *
from notes_log import log
from TrivialFormulator import TrivialFormulator, TF
from notes_table import *

def do_formsemestre_inscription_with_modules(
    context, formsemestre_id, etudid, group_ids=[], etat='I', REQUEST=None,
    method='inscription_with_modules'
    ):
    """Inscrit cet etudiant a ce semestre et TOUS ses modules STANDARDS
    (donc sauf le sport)
    """
    # inscription au semestre
    args = {'formsemestre_id': formsemestre_id, 'etudid' : etudid }
    if etat is not None:
        args['etat'] = etat
    context.do_formsemestre_inscription_create(args, REQUEST, method=method )
    log('do_formsemestre_inscription_with_modules: etudid=%s formsemestre_id=%s' % (etudid,formsemestre_id))
    # inscriptions aux groupes
    # 1- inscrit au groupe 'tous'
    group_id = sco_groups.get_default_group(context, formsemestre_id)
    sco_groups.set_group(context, etudid, group_id)
    gdone = { group_id : 1 } # empeche doublons
    
    # 2- inscrit aux groupes
    for group_id in group_ids:
        if group_id and not group_id in gdone:
            sco_groups.set_group(context, etudid, group_id)
            gdone[group_id] = 1
    
    # inscription a tous les modules de ce semestre
    modimpls = context.do_moduleimpl_withmodule_list(
        {'formsemestre_id':formsemestre_id} )
    for mod in modimpls:
        if mod['ue']['type'] == UE_STANDARD:
            context.do_moduleimpl_inscription_create(
                {'moduleimpl_id' : mod['moduleimpl_id'],
                 'etudid' : etudid},  REQUEST=REQUEST, formsemestre_id=formsemestre_id)


def formsemestre_inscription_with_modules_etud(context, formsemestre_id, etudid=None, group_ids=None,
                                               REQUEST=None):
    """Form. inscription d'un étudiant au semestre.
    Si etudid n'est pas specifié, form. choix etudiant.
    """
    if not etudid:
        return context.formChercheEtud( title="Choix de l'étudiant à inscrire dans ce semestre",
                                     add_headers=True,
                                     dest_url='formsemestre_inscription_with_modules_etud',
                                     parameters={ 'formsemestre_id' : formsemestre_id },
                                     REQUEST=REQUEST )
    return formsemestre_inscription_with_modules(context, etudid, formsemestre_id, REQUEST=REQUEST,
                                                 group_ids=group_ids)

def formsemestre_inscription_with_modules_form(context,etudid,REQUEST):
    """Formulaire inscription de l'etud dans l'un des semestres existants
    """
    etud = context.getEtudInfo(etudid=etudid,filled=1)[0]        
    H = [ context.sco_header(REQUEST)
          + "<h2>Inscription de %s</h2>" % etud['nomprenom']
          + "<p>L'étudiant sera inscrit à <em>tous</em> les modules de la session choisie (sauf Sport &amp; Culture).</p>" 
          ]
    F = context.sco_footer(REQUEST)
    sems = context.do_formsemestre_list( args={ 'etat' : '1' } )
    insem = context.do_formsemestre_inscription_list(
        args={ 'etudid' : etudid, 'etat' : 'I' } )
    if sems:
        H.append('<ul>')
        for sem in sems:
            # Ne propose que les semestres ou etudid n'est pas déjà inscrit
            inscrit = False
            for i in insem:
                if i['formsemestre_id'] == sem['formsemestre_id']:
                    inscrit = True
            if not inscrit:
                H.append('<li><a href="formsemestre_inscription_with_modules?etudid=%s&formsemestre_id=%s">%s</a>' %
                         (etudid,sem['formsemestre_id'],sem['titremois']))
        H.append('</ul>')
    else:
        H.append('<p>aucune session de formation !</p>')
    H.append('<a class="stdlink" href="%s/ficheEtud?etudid=%s">retour à la fiche de %s</a>'
             % (context.ScoURL(), etudid, etud['nomprenom']) )
    return '\n'.join(H) + F


def formsemestre_inscription_with_modules(
    context, etudid, formsemestre_id, group_ids=None, multiple_ok=False, REQUEST=None):
    """
    Inscription de l'etud dans ce semestre.
    Formulaire avec choix groupe.
    """
    log('formsemestre_inscription_with_modules: etudid=%s formsemestre_id=%s group_ids=%s'
        % (etudid, formsemestre_id, group_ids))
    if multiple_ok:
        multiple_ok = int(multiple_ok)
    sem = context.get_formsemestre(formsemestre_id)
    etud = context.getEtudInfo(etudid=etudid,filled=1)[0]
    H = [ context.html_sem_header(REQUEST, 'Inscription de %s dans ce semestre' % etud['nomprenom'], sem) ]
    F = context.sco_footer(REQUEST)
    # Check 1: déjà inscrit ici ?
    ins = context.Notes.do_formsemestre_inscription_list({'etudid':etudid})
    already = False
    for i in ins:
        if i['formsemestre_id'] == formsemestre_id:
            already = True
    if already:
        H.append('<p class="warning">%s est déjà inscrit dans le semestre %s</p>' % (etud['nomprenom'], sem['titremois']))
        H.append("""<ul><li><a href="ficheEtud?etudid=%s">retour à la fiche de %s</a></li>
        <li><a href="formsemestre_status?formsemestre_id=%s">retour au tableau de bord de %s</a></li></ul>"""
                 % (etudid, etud['nomprenom'], formsemestre_id, sem['titremois']) )
        return '\n'.join(H) + F
    # Check 2: déjà inscrit dans un semestre recouvrant les même dates ?
    # Informe et propose dé-inscriptions
    others = est_inscrit_ailleurs(context, etudid, formsemestre_id)
    if others and not multiple_ok:
        l = []
        for s in others:
            l.append('<a class="discretelink" href="formsemestre_status?formsemestre_id=%(formsemestre_id)s">%(titremois)s</a>'%s)
        
        H.append('<p class="warning">Attention: %s est déjà inscrit sur la même période dans: %s.</p>'
                 % (etud['nomprenom'], ', '.join(l)))
        H.append('<ul>')
        for s in others:
            H.append('<li><a href="formsemestre_desinscription?formsemestre_id=%s&etudid=%s">déinscrire de %s</li>' % (s['formsemestre_id'],etudid,s['titreannee']))
        H.append('</ul>')
        H.append("""<p><a href="formsemestre_inscription_with_modules?etudid=%s&formsemestre_id=%s&multiple_ok=1&%s">Continuer quand même l'inscription</a></p>""" % (etudid, formsemestre_id, sco_groups.make_query_groups(group_ids)))
        return '\n'.join(H) + F
    #
    if group_ids is not None:
        # OK, inscription
        do_formsemestre_inscription_with_modules(
            context, formsemestre_id, etudid, group_ids=group_ids, etat='I', 
            REQUEST = REQUEST, method='formsemestre_inscription_with_modules' )
        return REQUEST.RESPONSE.redirect(context.ScoURL()+'/ficheEtud?etudid='+etudid)
    else:
        # formulaire choix groupe
        H.append("""<form method="GET" name="groupesel" action="%s">
        <input type="hidden" name="etudid" value="%s">
        <input type="hidden" name="formsemestre_id" value="%s">
        """ %(REQUEST.URL0,etudid,formsemestre_id))

        H.append( sco_groups.form_group_choice(context, formsemestre_id, allow_none=True) )

        #
        H.append("""
        <input type="submit" value="Inscrire"/>
        <p>Note: l'étudiant sera inscrit dans les groupes sélectionnés</p>
        </form>            
        """ )
        return '\n'.join(H) + F



def formsemestre_inscription_option(context, etudid, formsemestre_id, REQUEST=None):
    """Dialogue pour (des)inscription a des modules optionnels
    """
    sem = context.get_formsemestre(formsemestre_id)
    if sem['etat'] != '1':
        raise ScoValueError('Modification impossible: semestre verrouille')

    etud = context.getEtudInfo(etudid=etudid,filled=1)[0]
    nt = context._getNotesCache().get_NotesTable(context, formsemestre_id) #> get_etud_ue_status

    F = context.sco_footer(REQUEST)
    H = [ context.sco_header(REQUEST)
          + "<h2>Inscription de %s aux modules de %s (%s - %s)</h2>" %
          (etud['nomprenom'],sem['titre_num'],
           sem['date_debut'],sem['date_fin']) ]

    # Cherche les moduleimpls et les inscriptions
    mods = context.do_moduleimpl_withmodule_list(
        {'formsemestre_id':formsemestre_id} )
    inscr= context.do_moduleimpl_inscription_list( args={'etudid':etudid} )
    # Formulaire
    modimpls_by_ue_ids = DictDefault(defaultvalue=[])  # ue_id : [ moduleimpl_id ]
    modimpls_by_ue_names= DictDefault(defaultvalue=[]) # ue_id : [ moduleimpl_name ]
    ues = []
    ue_ids = Set()
    initvalues = {}
    for mod in mods:
        ue_id = mod['ue']['ue_id']
        if not ue_id in ue_ids:
            ues.append(mod['ue'])
            ue_ids.add(ue_id)
        modimpls_by_ue_ids[ue_id].append(mod['moduleimpl_id'])
                
        modimpls_by_ue_names[ue_id].append('%s %s' % (
                mod['module']['code'], mod['module']['titre']))
        if not REQUEST.form.get('tf-submitted', False):
            # inscrit ?
            for ins in inscr:
                if ins['moduleimpl_id'] == mod['moduleimpl_id']:
                    key = 'moduleimpls_%s' % ue_id
                    if key in initvalues:
                        initvalues[key].append(mod['moduleimpl_id'])
                    else:
                        initvalues[key] = [mod['moduleimpl_id']]
                    break
    
    descr = [
        ('formsemestre_id', { 'input_type' : 'hidden' }),
        ('etudid', { 'input_type' : 'hidden' }) ]
    for ue in ues:
        ue_id = ue['ue_id']
        ue_descr = ue['acronyme']
        if ue['type'] != UE_STANDARD:
            ue_descr += ' <em>%s</em>' % UE_TYPE_NAME[ue['type']]
        ue_status = nt.get_etud_ue_status(etudid, ue_id)
        if ue_status['is_capitalized']:
            sem_origin = context.do_formsemestre_list(args={ 'formsemestre_id' : ue_status['formsemestre_id'] } )[0]
            ue_descr += ' <a class="discretelink" href="formsemestre_bulletinetud?formsemestre_id=%s&etudid=%s" title="%s">(capitalisée le %s)' % (sem_origin['formsemestre_id'], 
etudid, sem_origin['titreannee'], DateISOtoDMY(ue_status['event_date']))
        descr.append( 
            ('sec_%s' % ue_id, 
             { 'input_type' : 'separator', 
               'title' : """<b>%s :</b>  <a href="#" onclick="chkbx_select('%s', true);">inscrire</a>|<a href="#" onclick="chkbx_select('%s', false);">désinscrire</a> à tous les modules""" % (ue_descr, ue_id, ue_id) }))
        descr.append(
            ('moduleimpls_%s' % ue_id,
             { 'input_type' : 'checkbox', 'title':'',
               'dom_id' : ue_id,
               'allowed_values' : modimpls_by_ue_ids[ue_id], 
               'labels' : modimpls_by_ue_names[ue_id],
               'vertical' : True
               }) )
    
    H.append("""<script type="text/javascript">
function chkbx_select(field_id, state) {
   var elems = document.getElementById(field_id).getElementsByTagName("input");
   for (var i=0; i < elems.length; i++) { 
      elems[i].checked=state; 
   }
}
    </script>
    """)
    tf = TrivialFormulator( REQUEST.URL0, REQUEST.form, descr,
                            initvalues,
                            cancelbutton = 'Annuler', method='post',
                            submitlabel = 'Modifier les inscriptions', cssclass='inscription',
                            name='tf' )
    if  tf[0] == 0:
        H.append("""<p>Voici la liste des modules du semestre choisi.</p><p>
    Les modules cochés sont ceux dans lesquels l'étudiant est inscrit. Vous pouvez l'inscrire ou le désincrire d'un ou plusieurs modules.</p>
    <p>Attention: cette méthode ne devrait être utilisée que pour les modules <b>optionnels</b> (ou les activités culturelles et sportives) et pour désinscrire les étudiants dispensés (UE validées).</p>
    """)
        return '\n'.join(H) + '\n' + tf[1] + F
    elif tf[0] == -1:
        return REQUEST.RESPONSE.redirect( "%s/ficheEtud?etudid=%s" %(context.ScoURL(), etudid))
    else:
        # Inscriptions aux modules choisis
        # il faut desinscrire des modules qui ne figurent pas
        # et inscrire aux autres, sauf si deja inscrit
        a_desinscrire = {}.fromkeys( [ x['moduleimpl_id'] for x in mods ] )
        insdict = {}
        for ins in inscr:
            insdict[ins['moduleimpl_id']] = ins
        for ue in ues:
            ue_id = ue['ue_id']
            for moduleimpl_id in tf[2]['moduleimpls_%s'%ue_id]:
                if a_desinscrire.has_key(moduleimpl_id):
                    del a_desinscrire[moduleimpl_id]
        # supprime ceux auxquel pas inscrit
        for moduleimpl_id in a_desinscrire.keys():
            if not insdict.has_key(moduleimpl_id):
                del a_desinscrire[moduleimpl_id]
        
        a_inscrire = Set()
        for ue in ues:
            ue_id = ue['ue_id']
            a_inscrire.update(tf[2]['moduleimpls_%s'%ue_id])
        # supprime ceux auquel deja inscrit:
        for ins in inscr:
            if ins['moduleimpl_id'] in a_inscrire:
                a_inscrire.remove(ins['moduleimpl_id'])
        # dict des modules:
        modsdict = {}
        for mod in mods:
            modsdict[mod['moduleimpl_id']] = mod
        #
        if (not a_inscrire) and (not a_desinscrire):
            H.append("""<h3>Aucune modification à effectuer</h3>
            <p><a class="stdlink" href="%s/ficheEtud?etudid=%s">retour à la fiche étudiant</a></p>""" % (context.ScoURL(), etudid))
            return '\n'.join(H) + F

        H.append("<h3>Confirmer les modifications:</h3>")
        if a_desinscrire:
            H.append("<p>%s va être <b>désinscrit%s</b> des modules:<ul><li>"
                     %(etud['nomprenom'],etud['ne']))
            H.append( '</li><li>'.join([
                '%s (%s)' %
                (modsdict[x]['module']['titre'],
                 modsdict[x]['module']['code'])
                for x in a_desinscrire ]) + '</p>' )
            H.append( '</li></ul>' )
        if a_inscrire:
            H.append("<p>%s va être <b>inscrit%s</b> aux modules:<ul><li>"
                     %(etud['nomprenom'],etud['ne']))
            H.append( '</li><li>'.join([
                '%s (%s)' %
                (modsdict[x]['module']['titre'],
                 modsdict[x]['module']['code'])
                for x in a_inscrire ]) + '</p>' )
            H.append( '</li></ul>' )
        modulesimpls_ainscrire=','.join(a_inscrire)
        modulesimpls_adesinscrire=','.join(a_desinscrire)
        H.append("""<form action="do_moduleimpl_incription_options">
        <input type="hidden" name="etudid" value="%s"/>
        <input type="hidden" name="modulesimpls_ainscrire" value="%s"/>
        <input type="hidden" name="modulesimpls_adesinscrire" value="%s"/>
        <input type ="submit" value="Confirmer"/>
        <input type ="button" value="Annuler" onclick="document.location='%s/ficheEtud?etudid=%s';"/>
        </form>
        """ % (etudid,modulesimpls_ainscrire,modulesimpls_adesinscrire,context.ScoURL(),etudid))
        return '\n'.join(H) + F


def do_moduleimpl_incription_options(
    context,etudid,
    modulesimpls_ainscrire,modulesimpls_adesinscrire,
    REQUEST=None):
    """
    Effectue l'inscription et la description aux modules optionnels
    """
    if modulesimpls_ainscrire:
        a_inscrire = modulesimpls_ainscrire.split(',')
    else:
        a_inscrire = []
    if modulesimpls_adesinscrire:
        a_desinscrire = modulesimpls_adesinscrire.split(',')
    else:
        a_desinscrire = []
    # inscriptions
    for moduleimpl_id in a_inscrire:
        # verifie que ce module existe bien
        mod = context.do_moduleimpl_list({'moduleimpl_id':moduleimpl_id})
        if len(mod) != 1:
            raise ScoValueError('inscription: invalid moduleimpl_id: %s' % moduleimpl_id)
        context.do_moduleimpl_inscription_create(
            {'moduleimpl_id':moduleimpl_id, 'etudid' : etudid }, 
            REQUEST=REQUEST, formsemestre_id=mod['formsemestre_id'])
    # desinscriptions
    for moduleimpl_id in a_desinscrire:
        # verifie que ce module existe bien
        mod = context.do_moduleimpl_list({'moduleimpl_id':moduleimpl_id})
        if len(mod) != 1:
            raise ScoValueError('desinscription: invalid moduleimpl_id: %s' % moduleimpl_id)
        inscr = context.do_moduleimpl_inscription_list( args=
            {'moduleimpl_id':moduleimpl_id, 'etudid' : etudid })
        if not inscr:
            raise ScoValueError('pas inscrit a ce module ! (etudid=%s, moduleimpl_id=%)'%(etudid,moduleimpl_id))
        oid = inscr[0]['moduleimpl_inscription_id']
        context.do_moduleimpl_inscription_delete(oid, formsemestre_id=mod['formsemestre_id'])

    if REQUEST:
        H = [ context.sco_header(REQUEST),
              """<h3>Modifications effectuées</h3>
              <p><a class="stdlink" href="%s/ficheEtud?etudid=%s">
              Retour à la fiche étudiant</a></p>
              """ % (context.ScoURL(), etudid),
              context.sco_footer(REQUEST)]
        return '\n'.join(H)


def est_inscrit_ailleurs(context, etudid, formsemestre_id):
    """Vrai si l'étudiant est inscrit dans un semestre en même
    temps que celui indiqué (par formsemestre_id).
    Retourne la liste des semestres concernés (ou liste vide).
    """
    etud = context.getEtudInfo(etudid=etudid,filled=1)[0]
    sem = context.get_formsemestre(formsemestre_id)
    debut_s = sem['dateord']
    fin_s = DateDMYtoISO(sem['date_fin'])
    r = []
    for s in etud['sems']:
        if s['formsemestre_id'] != formsemestre_id:
            debut = s['dateord']
            fin = DateDMYtoISO(s['date_fin'])
            if debut < fin_s and fin > debut_s:
                r.append(s) # intersection
    return r

def list_inscrits_ailleurs(context, formsemestre_id):
    """Liste des etudiants inscrits ailleurs en même temps que formsemestre_id.
    Pour chacun, donne la liste des semestres.
    { etudid : [ liste de sems ] }
    """
    nt = context._getNotesCache().get_NotesTable(context, formsemestre_id) #> get_etudids
    etudids = nt.get_etudids()
    d = {}
    for etudid in etudids:
        d[etudid] = est_inscrit_ailleurs(context, etudid, formsemestre_id)
    return d

def formsemestre_inscrits_ailleurs(context,formsemestre_id, REQUEST=None):
    """Page listant les étudiants inscrits dans un autre semestre
    dont les dates recouvrent le semestre indiqué.
    """
    sem = context.get_formsemestre(formsemestre_id)
    H = [ context.html_sem_header(REQUEST, 'Inscriptions multiples parmi les étudiants du semestre ', sem) ]
    insd = list_inscrits_ailleurs(context, formsemestre_id)
    # liste ordonnée par nom
    etudlist = [ context.getEtudInfo(etudid=etudid,filled=1)[0] for etudid in insd.keys() if insd[etudid] ]
    etudlist.sort(key=lambda x:x['nom'])
    if etudlist:
        H.append('<ul>')
        for etud in etudlist:
            H.append('<li><a href="ficheEtud?etudid=%(etudid)s" class="discretelink">%(nomprenom)s</a> : ' % etud )
            l = []
            for s in insd[etud['etudid']]:
                l.append('<a class="discretelink" href="formsemestre_status?formsemestre_id=%(formsemestre_id)s">%(titremois)s</a>'%s)
            H.append( ', '.join(l))
            H.append('</li>')
        H.append('</ul>')
        H.append('<p>Total: %d étudiants concernés.</p>' % len(etudlist))
        H.append("""<p class="help">Ces étudiants sont inscrits dans le semestre sélectionné et aussi dans d'autres semestres qui se déroulent en même temps ! <br/>Sauf exception, cette situation est anormale et doit être réglée en désinscrivant l'étudiant de l'un des semestres (via sa fiche individuelle).</p>""")
    else:
        H.append("""<p>Aucun étudiant en inscription multiple (c'est normal) !</p>""")
    return '\n'.join(H) + context.sco_footer(REQUEST)
