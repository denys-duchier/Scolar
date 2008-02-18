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

"""Opérations d'inscriptions aux semestres et modules
"""


from notesdb import *
from sco_utils import *
from notes_log import log
from TrivialFormulator import TrivialFormulator, TF
from notes_table import *

def do_formsemestre_inscription_with_modules(
    self, args=None, REQUEST=None,
    method='inscription_with_modules'
    ):
    """Inscrit cet etudiant a ce semestre et TOUS ses modules STANDARDS
    (donc sauf le sport)
    """
    etudid = args['etudid']
    formsemestre_id = args['formsemestre_id']
    # inscription au semestre
    self.do_formsemestre_inscription_create( args, REQUEST, method=method )
    log('do_formsemestre_inscription_with_modules: etudid=%s formsemestre_id=%s' % (etudid,formsemestre_id))
    # inscription a tous les modules de ce semestre
    modimpls = self.do_moduleimpl_withmodule_list(
        {'formsemestre_id':formsemestre_id} )
    for mod in modimpls:
        if mod['ue']['type'] == UE_STANDARD:
            self.do_moduleimpl_inscription_create(
                {'moduleimpl_id' : mod['moduleimpl_id'],
                 'etudid' : etudid} )


def formsemestre_inscription_with_modules_etud(self, formsemestre_id, etudid=None,
                                               groupetd=None, groupeanglais=None, groupetp=None,
                                               REQUEST=None):
    """Form. inscription d'un étudiant au semestre.
    Si etudid n'est pas specifié, form. choix etudiant.
    """
    if not etudid:
        return self.chercheEtud( title="Choix de l'étudiant à inscrire",
                                 dest_url='formsemestre_inscription_with_modules_etud',
                                 parameters={ 'formsemestre_id' : formsemestre_id },
                                 REQUEST=REQUEST )
    return formsemestre_inscription_with_modules(self, etudid, formsemestre_id, REQUEST=REQUEST,
                                                 groupetd=groupetd, groupeanglais=groupeanglais, groupetp=groupetp)

def formsemestre_inscription_with_modules_form(self,etudid,REQUEST):
    """Formulaire inscription de l'etud dans l'une des sessions existantes
    """
    etud = self.getEtudInfo(etudid=etudid,filled=1)[0]        
    H = [ self.sco_header(REQUEST)
          + "<h2>Inscription de %s</h2>" % etud['nomprenom']
          + "<p>L'étudiant sera inscrit à <em>tous</em> les modules de la session choisie (sauf Sport &amp; Culture).</p>" 
          ]
    F = self.sco_footer(REQUEST)
    sems = self.do_formsemestre_list( args={ 'etat' : '1' } )
    insem = self.do_formsemestre_inscription_list(
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
                         (etudid,sem['formsemestre_id'],sem['titreannee']))
        H.append('</ul>')
    else:
        H.append('<p>aucune session de formation !</p>')
    H.append('<a class="stdlink" href="%s/ficheEtud?etudid=%s">retour à la fiche de %s</a>'
             % (self.ScoURL(), etudid, etud['nomprenom']) )
    return '\n'.join(H) + F


def formsemestre_inscription_with_modules(
    self, etudid, formsemestre_id,
    groupetd=None, groupeanglais=None, groupetp=None,
    REQUEST=None):
    """
    Inscription de l'etud dans ce semestre.
    Formulaire avec choix groupe.
    """
    # log( 'formsemestre_inscription_with_modules: etudid=%s groupetd=%s' % (etudid,groupetd))
    sem = self.get_formsemestre(formsemestre_id)
    etud = self.getEtudInfo(etudid=etudid,filled=1)[0]
    H = [ self.sco_header(REQUEST)
          + "<h2>Inscription de %s dans %s</h2>" %
          (etud['nomprenom'],sem['titreannee']) ]
    F = self.sco_footer(REQUEST)
    # Check: déjà inscrit ?
    ins = self.Notes.do_formsemestre_inscription_list({'etudid':etudid})
    already = False
    for i in ins:
        if i['formsemestre_id'] == formsemestre_id:
            already = True
    if already:
        H.append('<p class="warning">%s est déjà inscrit dans le semestre %s</p>' % (etud['nomprenom'], sem['titreannee']))
        H.append("""<ul><li><a href="ficheEtud?etudid=%s">retour à la fiche de %s</a></li>
        <li><a href="formsemestre_status?formsemestre_id=%s">retour au tableau de bord de %s</a></li></ul>"""
                 % (etudid, etud['nomprenom'], formsemestre_id, sem['titreannee']) )
        return '\n'.join(H) + F
    #
    if groupetd:
        # OK, inscription
        self.do_formsemestre_inscription_with_modules(
            args={'formsemestre_id' : formsemestre_id,
                  'etudid' : etudid,
                  'etat' : 'I',
                  'groupetd' : groupetd, 'groupeanglais' : groupeanglais,
                  'groupetp' : groupetp
                  },
            REQUEST = REQUEST, method='formsemestre_inscription_with_modules')
        return REQUEST.RESPONSE.redirect(self.ScoURL()+'/ficheEtud?etudid='+etudid)
    else:
        # formulaire choix groupe
        # Liste des groupes existant (== ou il y a des inscrits)
        gr_td,gr_tp,gr_anglais = self.do_formsemestre_inscription_listegroupes(formsemestre_id=formsemestre_id)
        if not gr_td:
            gr_td = ['A']
        if not gr_anglais:
            gr_anglais = ['']
        if not gr_tp:
            gr_tp = ['']
        H.append("""<form method="GET" name="groupesel">
        <input type="hidden" name="etudid" value="%s">
        <input type="hidden" name="formsemestre_id" value="%s">
        <table>
        <tr><td>Groupe de %s</td><td>
        <select name="groupetdmenu" onChange="document.groupesel.groupetd.value=this.options[this.selectedIndex].value;">""" %(etudid,formsemestre_id,sem['nomgroupetd']))
        for g in gr_td:
            H.append('<option value="%s">%s</option>'%(g,g))
        H.append("""</select>
        </td><td><input type="text" name="groupetd" size="12" value="%s">
        </input></td></tr>
        """ % gr_td[0])
        # anglais
        H.append("""<tr><td>Groupe de %s</td><td>
        <select name="groupeanglaismenu" onChange="document.groupesel.groupeanglais.value=this.options[this.selectedIndex].value;">""" % sem['nomgroupeta'] )
        for g in gr_anglais:
            H.append('<option value="%s">%s</option>'%(g,g))
        H.append("""</select>
        </td><td><input type="text" name="groupeanglais" size="12" value="%s">
        </input></td></tr>
        """% gr_anglais[0])
        # tp
        H.append("""<tr><td>Groupe de %s</td><td>
        <select name="groupetpmenu" onChange="document.groupesel.groupetp.value=this.options[this.selectedIndex].value;">"""%sem['nomgroupetp'])
        for g in gr_tp:
            H.append('<option value="%s">%s</option>'%(g,g))
        H.append("""</select>
        </td><td><input type="text" name="groupetp" size="12" value="%s">
        </input></td></tr>
        """ % gr_tp[0])
        #
        H.append("""</table>
        <input type="submit" value="Inscrire"/>
        <p>Note: vous pouvez choisir l'un des groupes existants (figurant dans les menus) ou bien décider de créer un nouveau groupe (saisir son identifiant dans les champs textes).</p>
        <p>Note 2: le groupe primaire (%s) doit être non vide. Les autres groupes sont facultatifs.</p>
        </form>            
        """ % sem['nomgroupetd'])
        return '\n'.join(H) + F

def formsemestre_inscription_option(self, etudid, formsemestre_id, moduleimpls=[],
                                    REQUEST=None):
    """Dialogue pour (des)inscription a des modules optionnels
    """
    sem = self.get_formsemestre(formsemestre_id)
    if sem['etat'] != '1':
        raise ScoValueError('Modification impossible: semestre verrouille')

    etud = self.getEtudInfo(etudid=etudid,filled=1)[0]
    F = self.sco_footer(REQUEST)
    H = [ self.sco_header(REQUEST)
          + "<h2>Inscription de %s aux modules de %s (%s - %s)</h2>" %
          (etud['nomprenom'],sem['titre_num'],
           sem['date_debut'],sem['date_fin']) ]
    H.append("""<p>Voici la liste des modules du semestre choisi.</p><p>
    Les modules cochés sont ceux dans lesquels l'étudiant est inscrit. Vous pouvez l'inscrire ou le désincrire d'un ou plusieurs modules.</p>
    <p>Attention: cette méthode ne devrait être utilisée que pour les modules <b>optionnels</b> ou les activités culturelles et sportives.</p>
    """)
    # Cherche les moduleimpls et les inscriptions
    mods = self.do_moduleimpl_withmodule_list(
        {'formsemestre_id':formsemestre_id} )
    inscr= self.do_moduleimpl_inscription_list( args={'etudid':etudid} )
    # Formulaire
    modimpls_ids = []
    modimpl_names= []
    initvalues = { 'moduleimpls' : [] }
    for mod in mods:
        modimpls_ids.append(mod['moduleimpl_id'])
        if mod['ue']['type'] == UE_STANDARD:
            ue_type = ''
        else:
            ue_type = '<b>%s</b>' % UE_TYPE_NAME[mod['ue']['type']]
        modimpl_names.append('%s %s &nbsp;&nbsp;(%s %s)' % (
            mod['module']['code'], mod['module']['titre'],
            mod['ue']['acronyme'], ue_type))
        # inscrit ?
        for ins in inscr:
            if ins['moduleimpl_id'] == mod['moduleimpl_id']:
                initvalues['moduleimpls'].append(mod['moduleimpl_id'])
                break
    descr = [
        ('formsemestre_id', { 'input_type' : 'hidden' }),
        ('etudid', { 'input_type' : 'hidden' }),
        ('moduleimpls',
         { 'input_type' : 'checkbox', 'title':'',
           'allowed_values' : modimpls_ids, 'labels' : modimpl_names,
           'vertical' : True
           }),
    ]
    tf = TrivialFormulator( REQUEST.URL0, REQUEST.form, descr,
                            initvalues,
                            cancelbutton = 'Annuler', method='GET',
                            submitlabel = 'Modifier les inscriptions', cssclass='inscription',
                            name='tf' )
    if  tf[0] == 0:
        return '\n'.join(H) + '\n' + tf[1] + F
    elif tf[0] == -1:
        return REQUEST.RESPONSE.redirect( "%s/ficheEtud?etudid=%s" %(self.ScoURL(), etudid))
    else:
        # Inscriptions aux modules choisis
        # xxx moduleimpls = REQUEST.form['moduleimpls']
        # il faut desinscrire des modules qui ne figurent pas
        # et inscrire aux autres, sauf si deja inscrit
        a_desinscrire = {}.fromkeys( [ x['moduleimpl_id'] for x in mods ] )
        insdict = {}
        for ins in inscr:
            insdict[ins['moduleimpl_id']] = ins
        for moduleimpl_id in moduleimpls:                    
            if a_desinscrire.has_key(moduleimpl_id):
                del a_desinscrire[moduleimpl_id]
        # supprime ceux auxquel pas inscrit
        for moduleimpl_id in a_desinscrire.keys():
            if not insdict.has_key(moduleimpl_id):
                del a_desinscrire[moduleimpl_id]
        a_inscrire = {}.fromkeys( moduleimpls )
        for ins in inscr:
            if a_inscrire.has_key(ins['moduleimpl_id']):
                del a_inscrire[ins['moduleimpl_id']]
        # dict des modules:
        modsdict = {}
        for mod in mods:
            modsdict[mod['moduleimpl_id']] = mod
        #
        if (not a_inscrire) and (not a_desinscrire):
            H.append("""<h3>Aucune modification à effectuer</h3>
            <p><a class="stdlink" href="%s/ficheEtud?etudid=%s">retour à la fiche étudiant</a></p>""" % (self.ScoURL(), etudid))
            return '\n'.join(H) + F

        H.append("<h3>Confirmer les modifications</h3>")
        if a_desinscrire:
            H.append("<p>%s va être <b>désinscrit</b> des modules:"
                     %etud['nomprenom'])
            H.append( ', '.join([
                '%s (%s)' %
                (modsdict[x]['module']['titre'],
                 modsdict[x]['module']['code'])
                for x in a_desinscrire ]) + '</p>' )
        if a_inscrire:
            H.append("<p>%s va être <b>inscrit</b> aux modules:"
                     %etud['nomprenom'])
            H.append( ', '.join([
                '%s (%s)' %
                (modsdict[x]['module']['titre'],
                 modsdict[x]['module']['code'])
                for x in a_inscrire ]) + '</p>' )
        modulesimpls_ainscrire=','.join(a_inscrire)
        modulesimpls_adesinscrire=','.join(a_desinscrire)
        H.append("""<form action="do_moduleimpl_incription_options">
        <input type="hidden" name="etudid" value="%s"/>
        <input type="hidden" name="modulesimpls_ainscrire" value="%s"/>
        <input type="hidden" name="modulesimpls_adesinscrire" value="%s"/>
        <input type ="submit" value="Confirmer"/>
        <input type ="button" value="Annuler" onclick="document.location='%s/ficheEtud?etudid=%s';"/>
        </form>
        """ % (etudid,modulesimpls_ainscrire,modulesimpls_adesinscrire,self.ScoURL(),etudid))
        return '\n'.join(H) + F


def do_moduleimpl_incription_options(
    self,etudid,
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
        mod = self.do_moduleimpl_list({'moduleimpl_id':moduleimpl_id})
        if len(mod) != 1:
            raise ScoValueError('inscription: invalid moduleimpl_id: %s' % moduleimpl_id)
        self.do_moduleimpl_inscription_create(
            {'moduleimpl_id':moduleimpl_id, 'etudid' : etudid })
    # desinscriptions
    for moduleimpl_id in a_desinscrire:
        # verifie que ce module existe bien
        mod = self.do_moduleimpl_list({'moduleimpl_id':moduleimpl_id})
        if len(mod) != 1:
            raise ScoValueError('desinscription: invalid moduleimpl_id: %s' % moduleimpl_id)
        inscr = self.do_moduleimpl_inscription_list( args=
            {'moduleimpl_id':moduleimpl_id, 'etudid' : etudid })
        if not inscr:
            raise ScoValueError('pas inscrit a ce module ! (etudid=%s, moduleimpl_id=%)'%(etudid,moduleimpl_id))
        oid = inscr[0]['moduleimpl_inscription_id']
        self.do_moduleimpl_inscription_delete(oid)

    if REQUEST:
        H = [ self.sco_header(REQUEST),
              """<h3>Modifications effectuées</h3>
              <p><a class="stdlink" href="%s/ficheEtud?etudid=%s">
              Retour à la fiche étudiant</a></p>
              """ % (self.ScoURL(), etudid),
              self.sco_footer(REQUEST)]
        return '\n'.join(H)
