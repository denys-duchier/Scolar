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

"""Pages HTML gestion absences 
   (la plupart portées du DTML)
"""

from notesdb import *
from sco_utils import *
from notes_log import log
import sco_groups

import ZAbsences

def doSignaleAbsence(context, datedebut, datefin, moduleimpl_id, demijournee, estjust=False, description=None, REQUEST=None): # etudid implied
    """Signalement d'une absence
    """
    etud = context.getEtudInfo(filled=1, REQUEST=REQUEST)[0]
    etudid = etud['etudid']
    
    description_abs = description
    dates = context.DateRangeISO(datedebut, datefin)
    nbadded = 0
    for jour in dates:
        if demijournee=='2':
            context._AddAbsence(etudid,jour,False,estjust,REQUEST,description_abs,moduleimpl_id)
            context._AddAbsence(etudid,jour,True,estjust,REQUEST,description_abs,moduleimpl_id)
            nbadded += 2
        else:
            matin = int(demijournee)
            context._AddAbsence(etudid,jour,matin,estjust,REQUEST,description_abs,moduleimpl_id)
            nbadded += 1
    #
    if estjust:
        J = ''
    else:
        J = 'NON '
    M = ''
    if moduleimpl_id and moduleimpl_id != "NULL":
        mod = context.Notes.do_moduleimpl_list(args={ 'moduleimpl_id':moduleimpl_id } )[0]
        formsemestre_id = mod['formsemestre_id']        
        nt = context.Notes._getNotesCache().get_NotesTable(context.Notes, formsemestre_id)
        ues = nt.get_ues(etudid=etudid)
        for ue in ues:
            modimpls = nt.get_modimpls(ue_id=ue['ue_id'])
            for modimpl in modimpls:
                if modimpl['moduleimpl_id'] == moduleimpl_id:
                    M = 'dans le module %s' % modimpl['module']['code']
    H = [ context.sco_header(REQUEST,page_title="Signalement d'une absence pour %(nomprenom)s" % etud ),
          """<h2>Signalement d'absences</h2>""" ]
    if dates:
        H.append("""<p>Ajout de %d absences <b>%sjustifiées</b> du %s au %s %s</p>"""
                 % (nbadded, J, datedebut, datefin, M ) )
    else:
        H.append("""<p class="warning">Aucune date ouvrable entre le %s et le %s !</p>"""
                 % (datedebut, datefin) )
    
    H.append("""<ul><li><a href="SignaleAbsenceEtud?etudid=%(etudid)s">Autre absence pour <b>%(nomprenom)s</b></a></li>
                    <li><a href="CalAbs?etudid=%(etudid)s">Calendrier de ses absences</a></li>
                </ul>
              <hr>""" % etud )
    H.append(context.formChercheEtud(REQUEST))
    H.append(context.sco_footer(REQUEST))
    return '\n'.join(H)

def SignaleAbsenceEtud(context, REQUEST=None): # etudid implied
    """Formulaire individuel simple de signalement d'une absence
    """
    # brute-force portage from very old dtml code ...
    etud = context.getEtudInfo(filled=1, REQUEST=REQUEST)[0]
    etudid = etud['etudid']
    if not etud['cursem']:
        menu_module = ''
    else:
        formsemestre_id = etud['cursem']['formsemestre_id']
        nt = context.Notes._getNotesCache().get_NotesTable(context.Notes, formsemestre_id)
        ues = nt.get_ues(etudid=etudid)
        menu_module = """<p><select name="moduleimpl_id">
        <option value="NULL" selected>(Module)</option>"""
        for ue in ues:
            modimpls = nt.get_modimpls(ue_id=ue['ue_id'])
            for modimpl in modimpls:
                menu_module += """<option value="%(modimpl_id)s">%(modname)s</option>\n""" % {'modimpl_id': modimpl['moduleimpl_id'], 'modname': modimpl['module']['code']}
        menu_module += """</select></p>"""

    H = [ context.sco_header(REQUEST,page_title="Signalement d'une absence pour %(nomprenom)s" % etud, init_jquery_ui=True ),
          """<table><tr><td>
          <h2>Signalement d'une absence pour %(nomprenom)s</h2>
          </td><td>
          """ % etud,
          """<a href="%s/ficheEtud?etudid=%s">""" % (context.ScoURL(), etud['etudid']),
          context.etud_photo_html(etudid=etudid, title='fiche de '+etud['nomprenom'], REQUEST=REQUEST),
          """</a></td></tr></table>""",
          """
<form action="doSignaleAbsence" method="get"> 
<input type="hidden" name="etudid" value="%(etudid)s">
<p>
<table><tr>
<td>Date d&eacute;but :  </td>
<td><input type="text" name="datedebut" size="10" class="datepicker"/> <em>j/m/a</em></td>
<td>&nbsp;&nbsp;&nbsp;Date Fin (optionnel):</td>
<td><input type="text" name="datefin" size="10" class="datepicker"/> <em>j/m/a</em></td>
</tr>
</table>
<br/>

%(menu_module)s

<input type="radio" name="demijournee" value="2" checked>journ&eacute;e(s)
&nbsp;<input type="radio" name="demijournee" value="1">Matin(s)
&nbsp;<input type="radio" name="demijournee" value="0">Apr&egrave;s midi

<p>
<input type="checkbox" name="estjust"/>Absence justifi&eacute;e.
<br/>
Raison: <input type="text" name="description" size="42"/> (optionnel)
</p>

<p>
<input type="submit" value="Envoyer"/> 

<p>(<em>toutes les dates au format jour/mois/annee</em>)</p>


</form> 
          """ % {'etudid': etud['etudid'], 'menu_module': menu_module},
          context.sco_footer(REQUEST)
          ]
    return '\n'.join(H)

    
def doJustifAbsence(context, datedebut, datefin, demijournee, description=None, REQUEST=None): # etudid implied
    """Justification d'une absence
    """
    etud = context.getEtudInfo(filled=1, REQUEST=REQUEST)[0]
    etudid = etud['etudid']
    description_abs = description
    dates = context.DateRangeISO(datedebut, datefin)
    nbadded = 0
    for jour in dates:
        if demijournee=='2':
            context._AddJustif(etudid=etudid, jour=jour, matin=False, REQUEST=REQUEST, description=description_abs)
            context._AddJustif(etudid=etudid, jour=jour, matin=True, REQUEST=REQUEST, description=description_abs)
            nbadded += 2
        else:
            matin = int(demijournee)
            context._AddJustif(etudid=etudid, jour=jour, matin=matin, REQUEST=REQUEST, description=description_abs)
            nbadded += 1
    #
    H = [ context.sco_header(REQUEST,page_title="Justification d'une absence pour %(nomprenom)s" % etud ),
          """<h2>Justification d'absences</h2>""" ]
    if dates:
        H.append("""<p>Ajout de %d <b>justifications</b> du %s au %s</p>"""
                 % (nbadded, datedebut, datefin ) )
    else:
        H.append("""<p class="warning">Aucune date ouvrable entre le %s et le %s !</p>"""
                 % (datedebut, datefin) )
    
    H.append("""<ul><li><a href="JustifAbsenceEtud?etudid=%(etudid)s">Autre justification pour <b>%(nomprenom)s</b></a></li>
<li><a href="SignaleAbsenceEtud?etudid=%(etudid)s">Signaler une absence</a></li>
<li><a href="CalAbs?etudid=%(etudid)s">Calendrier de ses absences</a></li>
<li><a href="ListeAbsEtud?etudid=%(etudid)s">Liste de ses absences</a></li>
</ul>
<hr>""" % etud )
    H.append(context.formChercheEtud(REQUEST))
    H.append(context.sco_footer(REQUEST))
    return '\n'.join(H)

def JustifAbsenceEtud(context, REQUEST=None): # etudid implied
    """Formulaire individuel simple de justification d'une absence
    """
    # brute-force portage from very old dtml code ...
    etud = context.getEtudInfo(filled=1, REQUEST=REQUEST)[0]
    etudid = etud['etudid']
    H = [ context.sco_header(REQUEST,page_title="Justification d'une absence pour %(nomprenom)s" % etud, init_jquery_ui=True ),
          """<table><tr><td>
          <h2>Signalement d'une absence pour %(nomprenom)s</h2>
          </td><td>
          """ % etud,
          """<a href="%s/ficheEtud?etudid=%s">""" % (context.ScoURL(), etud['etudid']),
          context.etud_photo_html(etudid=etudid, title='fiche de '+etud['nomprenom'], REQUEST=REQUEST),
          """</a></td></tr></table>""",
          """
<form action="doJustifAbsence" method="get"> 
<input type="hidden" name="etudid" value="%(etudid)s">

<p>
<table><tr>
<td>Date d&eacute;but :  </td>
<td>
<input type="text" name="datedebut" size="10" class="datepicker"/>
</td>
<td>&nbsp;&nbsp;&nbsp;Date Fin (optionnel):</td>
<td><input type="text" name="datefin" size="10" class="datepicker"/></td>
</tr>
</table>
<br/>

&nbsp; <select name="demijournee">
       <option value="2">Toute(s) la (ou les) journ&eacute;e(s)</option>
       <option value="1">Matin(s) seulement</option>
       <option value="0">Apr&egrave;s midi seulement</option>
       </select>

<br/><br/>
Raison: <input type="text" name="description" size="42"/> (optionnel)

<p>
<input type="submit" value="Envoyer"> 

</form> """ % etud,
          context.sco_footer(REQUEST)
          ]
    return '\n'.join(H)


def doAnnuleAbsence(context, datedebut, datefin, demijournee, REQUEST=None): # etudid implied
    """Annulation d'une absence
    """
    etud = context.getEtudInfo(filled=1, REQUEST=REQUEST)[0]
    etudid = etud['etudid']
    
    dates = context.DateRangeISO(datedebut, datefin)
    nbadded = 0
    for jour in dates:
        if demijournee=='2':
            context._AnnuleAbsence(etudid,jour,False,REQUEST)
            context._AnnuleAbsence(etudid,jour,True,REQUEST)
            nbadded += 2
        else:
            matin = int(demijournee)
            context._AnnuleAbsence(etudid,jour,matin,REQUEST)
            nbadded += 1
    #
    H = [ context.sco_header(REQUEST,page_title="Annulation d'une absence pour %(nomprenom)s" % etud ),
          """<h2>Annulation d'absences pour %(nomprenom)s</h2>"""%etud ]
    if dates:
        H.append("<p>Annulation sur %d demi-journées du %s au %s"
                 % (nbadded, datedebut, datefin) )
    else:
        H.append("""<p class="warning">Aucune date ouvrable entre le %s et le %s !</p>"""
                 % (datedebut, datefin) )
    
    H.append("""<ul><li><a href="AnnuleAbsenceEtud?etudid=%(etudid)s">Annulation d'une
autre absence pour <b>%(nomprenom)s</b></a></li>
                    <li><a href="SignaleAbsenceEtud?etudid=%(etudid)s">Ajout d'une absence</a></li>
                    <li><a href="CalAbs?etudid=%(etudid)s">Calendrier de ses absences</a></li>
                </ul>
              <hr>""" % etud )
    H.append(context.formChercheEtud(REQUEST))
    H.append(context.sco_footer(REQUEST))
    return '\n'.join(H)

def AnnuleAbsenceEtud(context, REQUEST=None): # etudid implied
    """Formulaire individuel simple d'annulation d'une absence
    """
    # brute-force portage from very old dtml code ...
    etud = context.getEtudInfo(filled=1, REQUEST=REQUEST)[0]
    etudid = etud['etudid']
    
    H = [ context.sco_header(REQUEST,page_title="Annulation d'une absence pour %(nomprenom)s" % etud, init_jquery_ui=True ),
          """<table><tr><td>
          <h2><font color="#FF0000">Annulation</font> d'une absence pour %(nomprenom)s</h2>
          </td><td>
          """ % etud,
          """<a href="%s/ficheEtud?etudid=%s">""" % (context.ScoURL(), etud['etudid']),
          context.etud_photo_html(etudid=etudid, title='fiche de '+etud['nomprenom'], REQUEST=REQUEST),
          """</a></td></tr></table>""",
          """<p>A n'utiliser que suite à une erreur de saisie ou lorsqu'il s'avère
      que l'étudiant était en fait présent. Dans les autres cas,
      <a href="JustifAbsenceEtud?etudid=%(etudid)s">justifier l'absence</a></p>
          """ % etud,
          """<table frame="border" border="1"><tr><td>
<form action="doAnnuleAbsence" method="get"> 
<input type="hidden" name="etudid" value="%(etudid)s">
<p>
<table><tr>
<td>Date d&eacute;but :  </td>
<td>
<input type="text" name="datedebut" size="10" class="datepicker"/> <em>j/m/a</em>
</td>
<td>&nbsp;&nbsp;&nbsp;Date Fin (optionnel):</td>
<td>
<input type="text" name="datefin" size="10" class="datepicker"/> <em>j/m/a</em>
</td>
</tr>
</table>

&nbsp; <select name="demijournee">
       <option value="2">Toute(s) la (ou les) journ&eacute;e(s)</option>
       <option value="1">Matin(s) seulement</option>
       <option value="0">Apr&egrave;s midi seulement</option>
       </select>


<p>
<input type="submit" value="Supprimer les absences"> 
</form> 
</td></tr>

<tr><td>
<form action="doAnnuleJustif" method="get"> 
<input type="hidden" name="etudid" value="%(etudid)s">
<p>
<table><tr>
<td>Date d&eacute;but :  </td>
<td>
<input type="text" name="datedebut0" size="10" class="datepicker"/> <em>j/m/a</em>
</td>
<td>&nbsp;&nbsp;&nbsp;Date Fin (optionnel):</td>
<td>
<input type="text" name="datefin0" size="10" class="datepicker"/> <em>j/m/a</em>
</td>
</tr>
</table>
<p>
<input type="submit" value="Supprimer les justificatifs"> 
<i>(utiliser ceci en cas de justificatif erron&eacute; saisi ind&eacute;pendemment d'une absence)</i>
</form> 
</td></tr></table>""" % etud,
          context.sco_footer(REQUEST)
          ]
    return '\n'.join(H)

def doAnnuleJustif(context, datedebut0, datefin0, REQUEST=None): # etudid implied
    """Annulation d'une justification 
    """
    etud = context.getEtudInfo(filled=1, REQUEST=REQUEST)[0]
    etudid = etud['etudid']
    dates = context.DateRangeISO(datedebut0, datefin0)
    nbadded = 0
    for jour in dates:
        # Attention: supprime matin et après midi
        context._AnnuleJustif(etudid, jour, False, REQUEST)
        context._AnnuleJustif(etudid, jour, True, REQUEST)
        nbadded += 2
    #
    H = [ context.sco_header(REQUEST,page_title="Annulation d'une justification pour %(nomprenom)s" % etud ),
          """<h2>Annulation de justifications pour %(nomprenom)s</h2>"""%etud ]
    
    if dates:
        H.append("<p>Annulation sur %d demi-journées du %s au %s"
                 % (nbadded, datedebut0, datefin0) )
    else:
        H.append("""<p class="warning">Aucune date ouvrable entre le %s et le %s !</p>"""
                 % (datedebut0, datefin0) )
    H.append("""<ul><li><a href="AnnuleAbsenceEtud?etudid=%(etudid)s">Annulation d'une
autre absence pour <b>%(nomprenom)s</b></a></li>
                    <li><a href="SignaleAbsenceEtud?etudid=%(etudid)s">Ajout d'une absence</a></li>
                    <li><a href="CalAbs?etudid=%(etudid)s">Calendrier de ses absences</a></li>
                </ul>
              <hr>""" % etud )
    H.append(context.formChercheEtud(REQUEST))
    H.append(context.sco_footer(REQUEST))
    return '\n'.join(H)


def EtatAbsences(context, REQUEST=None):
    """Etat des absences: choix du groupe"""
    # crude portage from 1999 DTML
    H = [ context.sco_header(REQUEST,page_title="Etat des absences", init_jquery_ui=True),
          """<h2>Etat des absences pour un groupe</h2>
<form action="EtatAbsencesGr" method="GET">""",
          formChoixSemestreGroupe(context),
          """<input type="submit" name="" value=" OK " width=100>

<table><tr><td>Date de début (j/m/a) : </td><td>

<input type="text" name="debut" size="10" value="01/09/%s" class="datepicker"/>

</td></tr><tr><td>Date de fin : </td><td>

<input type="text" name="fin" size="10" value="%s" class="datepicker"/>

</td></tr></table>
</form>""" % (context.AnneeScolaire(REQUEST), datetime.datetime.now().strftime('%d/%m/%Y')),
          context.sco_footer(REQUEST)
          ]
    return '\n'.join(H)

def formChoixSemestreGroupe(context, all=False):
    """partie de formulaire pour le choix d'un semestre et d'un groupe.
    Si all, donne tous les semestres (même ceux verrouillés).
    """
    # XXX assez primitif, à ameliorer
    if all:
        sems = context.Notes.do_formsemestre_list()
    else:
        sems = context.Notes.do_formsemestre_list( args={'etat':'1'} )
    H = [ '<select  name="group_id">' ]        
    nbgroups = 0
    for sem in sems:
        for p in sco_groups.get_partitions_list(context, sem['formsemestre_id']):
            for group in sco_groups.get_partition_groups(context, p):
                if group['group_name']:
                    group_tit = '%s %s' % (p['partition_name'], group['group_name'])
                else:
                    group_tit = 'tous'
                H.append('<option value="%s">%s: %s</option>' 
                         % (group['group_id'], sem['titremois'], group_tit))

    H.append('</select>')
    return '\n'.join(H)    



def CalAbs(context, REQUEST=None): # etud implied
    """Calendrier des absences d un etudiant
    """ 
    # crude portage from 1999 DTML
    etud = context.getEtudInfo(filled=1, REQUEST=REQUEST)[0]
    etudid = etud['etudid']
    AnneeScolaire = int(context.AnneeScolaire(REQUEST))
    datedebut = str(AnneeScolaire) +'-08-31'
    datefin = str(AnneeScolaire+1) +'-07-31'
    nbabs = context.CountAbs(etudid=etudid, debut=datedebut, fin=datefin)
    nbabsjust = context.CountAbsJust(etudid=etudid, debut=datedebut, fin=datefin)
    events = []
    for a in context.ListeAbsJust(etudid=etudid, datedebut=datedebut):
        events.append( (str(a['jour']), 'a', '#F8B7B0', '', a['matin'], a['description'] ) )
    for a in context.ListeAbsNonJust(etudid=etudid, datedebut=datedebut):
        events.append( (str(a['jour']), 'A', '#EE0000', '', a['matin'], a['description'] ) )

    CalHTML = ZAbsences.YearTable(context, AnneeScolaire, events=events, halfday=1 )
    
    #
    H = [ context.sco_header(REQUEST,
                             page_title="Calendrier des absences de %(nomprenom)s"%etud, 
                             cssstyles=['calabs.css']),
          """<table><tr><td><h2>Absences de <b>%(nomprenom)s (%(inscription)s)</h2><p>""" % etud,
          """<font color="#EE0000">A : absence NON justifiée</font><br>
             <font color="#F8B7B0">a : absence justifiée</font><br>
             %d absences sur l'année, dont %d justifiées (soit %d non justifiées)
           """  % (nbabs, nbabsjust, nbabs-nbabsjust),
           """</td>
<td><a href="%s/ficheEtud?etudid=%s">%s</a></td>
</tr>
</table>""" % (context.ScoURL(), etudid, context.etud_photo_html(etudid=etudid, title='fiche de '+etud['nomprenom'], REQUEST=REQUEST)),

          CalHTML,

          """<form method="GET" action="CalAbs" name="f">""",
          """<input type="hidden" name="etudid" value="%s"/>""" % etudid,
          """Année scolaire %s-%s""" % (AnneeScolaire, AnneeScolaire+1),
          """&nbsp;&nbsp;Changer année: <select name="sco_year" onChange="document.f.submit()">"""
          ]
    for y in range(AnneeScolaire, AnneeScolaire-10, -1):
        H.append("""<option value="%s" """ % y )
        if y == AnneeScolaire:
             H.append('selected')
        H.append(""">%s</option>""" % y )
    H.append("""</select></form>""")
    H.append(context.sco_footer(REQUEST))
    return '\n'.join(H)


def absences_index_html(context, REQUEST=None):
    """Gestionnaire absences, page principale"""
    # crude portage from 1999 DTML
    sems = context.Notes.do_formsemestre_list()
    authuser = REQUEST.AUTHENTICATED_USER
    
    H = [ context.sco_header(REQUEST,page_title="Gestion des absences",
                             cssstyles=['calabs.css'], javascripts=['js/calabs.js']),
          """<h2>Gestion des Absences</h2>""" ]
    if not sems:
        H.append("""<p class="warning">Aucun semestre défini (ou aucun groupe d'étudiant)</p>""")
    else:
        H.append("""<ul><li><a href="EtatAbsences">Afficher l'état des absences (pour tout un groupe)</a></li>""")
        if context.get_preference('handle_billets_abs'):
            H.append("""<li><a href="listeBillets">Traitement des billets d'absence en attente</a></li>""")
        H.append("""<p>Pour signaler, annuler ou justifier une absence, choisissez d'abord l'étudiant concerné:</p>""")
        H.append(context.formChercheEtud(REQUEST))
        if authuser.has_permission(ScoAbsChange,context):
            H.extend(("""<hr/>
<form action="SignaleAbsenceGrHebdo" id="formw">
<input type="hidden" name="destination" value="%s"/>
<p>
<span  style="font-weight: bold; font-size:120%%;">
 Saisie par semaine </span> - Choix du groupe:
	      <input name="datelundi" type="hidden" value="x"/>""" % REQUEST.URL0,
                      formChoixSemestreGroupe(context),
                      '</p>',
                      context.CalSelectWeek(REQUEST=REQUEST),
                      """<p class="help">Sélectionner le groupe d'étudiants, puis cliquez sur une semaine pour
saisir les absences de toute cette semaine.</p>
                      </form>""")
                     )
        else:
            H.append("""<p class="scoinfo">Vous n'avez pas l'autorisation d'ajouter, justifier ou supprimer des absences.</p>""")
    
    H.append(context.sco_footer(REQUEST))
    return '\n'.join(H)    
          
