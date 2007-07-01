# -*- mode: python -*-
# -*- coding: iso8859-15 -*-

##############################################################################
#
# Gestion scolarite IUT
#
# Copyright (c) 2001 - 2006 Emmanuel Viennet.  All rights reserved.
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

from sco_utils import *
from ScolarRolesNames import *

"""

"""


def sidebar_common(context, REQUEST=None):
    "partie commune a toutes les sidebar"
    params = {
        'ScoURL' : context.ScoURL(),
        }
    H = [
        context.sidebar_dept(context, REQUEST),
        """<h2 class="insidebar">Scolarit&eacute;</h2>
 <a href="%(ScoURL)s" class="sidebar">Semestres</a> <br/> 
 <a href="%(ScoURL)s/Notes" class="sidebar">Programmes</a> <br/> 
 <a href="%(ScoURL)s/Absences" class="sidebar">Absences</a> <br/>
 """ % params ]
    
    if REQUEST.AUTHENTICATED_USER.has_permission(ScoAdminUsers, context):
        H.append( """<a href="%(ScoURL)s/Users" class="sidebar">Utilisateurs</a> <br/>"""
                  % params )

    return ''.join(H)

def sidebar(context, REQUEST=None):
    "Main HTML page sidebar"
    # rewritten from legacy DTML code
    params = {
        'ScoURL' : context.ScoURL(),
        }

    H = [ '<div class="sidebar">',
          sidebar_common(context, REQUEST) ]
    
    H.append("""Chercher �tudiant:<br/>
<form action="%(ScoURL)s/chercheEtud">
<div><input type="text" size="12" name="expnom"></input></div>
</form>
<div class="etud-insidebar">
""" % params )
    # ---- s'il y a un etudiant selectionn�:
    if REQUEST.form.has_key('etudid'):
        etudid = REQUEST.form['etudid']
        etud = context.getEtudInfo(filled=1, etudid=etudid)[0]
        params.update(etud)
        # compte les absences de l'annee scolaire en cours (du 1 sept au 31 juil)
        annee = str(context.AnneeScolaire())
        date_debut = annee + '-08-31'
        date_fin = annee + '-07-31'
        params['nbabs']= context.Absences.CountAbs(etudid=etudid, debut=date_debut, fin=date_fin)
        params['nbabsjust'] = context.Absences.CountAbsJust(etudid=etudid, debut=date_debut, fin=date_fin)
        params['nbabsnj'] =  params['nbabs'] - params['nbabsjust']
        H.append("""<h2 id="insidebar-etud"><a href="%(ScoURL)s/ficheEtud?etudid=%(etudid)s" class="sidebar">
<font color="#FF0000">%(sexe)s %(nom)s</font></a>
</h2>
<b>Absences</b> (1/2 j.)<br/>%(nbabsjust)s J., %(nbabsnj)s N.J. 

<ul>""" % params ) # """
        if REQUEST.AUTHENTICATED_USER.has_permission(ScoAbsChange,context):
            H.append("""
<li>     <a href="%(ScoURL)s/Absences/SignaleAbsenceEtud?etudid=%(etudid)s">Ajouter</a>
<li>     <a href="%(ScoURL)s/Absences/JustifAbsenceEtud?etudid=%(etudid)s">Justifier</a>
<li>     <a href="%(ScoURL)s/Absences/AnnuleAbsenceEtud?etudid=%(etudid)s">Supprimer</a>
""" % params )
        H.append("""
<li>     <a href="%(ScoURL)s/Absences/CalAbs?etudid=<dtml-var etudid>">Calendrier</a>
</ul>
""" % params )
    else:
        H.append("(pas d'�tudiant en cours)")
    # ---------
    H.append('</div><br/>&nbsp;') # /etud-insidebar
    # Logo
    scologo_img = context.img.scologo_img.tag()
    H.append('<div class="logo-insidebar">%s<br/>' % scologo_img)
    H.append("""<a href="%(ScoURL)s/about" class="sidebar">A propos</a><br/>
<a href="https://www-gtr.iutv.univ-paris13.fr/ScoDoc/PageD'Accueil" class="sidebar">Aide</a><br/>
</div>

</div> <!-- end of sidebar -->
""" % params )
    #
    return ''.join(H)

    