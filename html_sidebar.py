# -*- mode: python -*-
# -*- coding: utf-8 -*-

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

from sco_utils import *
from ZAbsences import getAbsSemEtud

"""
Génération de la "sidebar" (marge gauche des pages HTML)
"""


def sidebar_common(context, REQUEST=None):
    "partie commune a toutes les sidebar"
    authuser = REQUEST.AUTHENTICATED_USER
    params = {
        'ScoURL' : context.ScoURL(),
        'authuser' :  str(authuser),
        }
    H = [
        '<a class="scodoc_title" href="about">ScoDoc</a>',
        '<div id="authuser"><a id="authuserlink" href="%(ScoURL)s/Users/userinfo">%(authuser)s</a><br/><a id="deconnectlink" href="%(ScoURL)s/acl_users/logout">déconnexion</a></div>' % params,
        
        context.sidebar_dept(REQUEST),
        """<h2 class="insidebar">Scolarit&eacute;</h2>
 <a href="%(ScoURL)s" class="sidebar">Semestres</a> <br/> 
 <a href="%(ScoURL)s/Notes" class="sidebar">Programmes</a> <br/> 
 <a href="%(ScoURL)s/Absences" class="sidebar">Absences</a> <br/>
 """ % params ]
    
    if authuser.has_permission(ScoUsersAdmin, context) or authuser.has_permission(ScoUsersView, context):
        H.append( """<a href="%(ScoURL)s/Users" class="sidebar">Utilisateurs</a> <br/>"""
                  % params )

    if 0: # XXX experimental
        H.append( """<a href="%(ScoURL)s/Notes/Services" class="sidebar">Services</a> <br/>"""
                  % params )

    if authuser.has_permission(ScoChangePreferences, context):
        H.append( """<a href="%(ScoURL)s/edit_preferences" class="sidebar">Paramétrage</a> <br/>"""
                  % params )

    return ''.join(H)

def sidebar(context, REQUEST=None):
    "Main HTML page sidebar"
    # rewritten from legacy DTML code
    params = {
        'ScoURL' : context.ScoURL(),
        'SCO_WEBSITE' : SCO_WEBSITE
        }

    H = [ '<div class="sidebar">',
          sidebar_common(context, REQUEST) ]
    
    H.append("""Chercher étudiant:<br/>
<form action="%(ScoURL)s/chercheEtud">
<div><input type="text" size="12" name="expnom"></input></div>
</form>
<div class="etud-insidebar">
""" % params )
    # ---- s'il y a un etudiant selectionné:
    if REQUEST.form.has_key('etudid'):
        etudid = REQUEST.form['etudid']
        etud = context.getEtudInfo(filled=1, etudid=etudid)[0]
        params.update(etud)
        # compte les absences du semestre en cours
        H.append("""<h2 id="insidebar-etud"><a href="%(ScoURL)s/ficheEtud?etudid=%(etudid)s" class="sidebar">
    <font color="#FF0000">%(sexe)s %(nom_disp)s</font></a>
    </h2>
    <b>Absences</b>""" % params)
        if etud['cursem']:
            AbsEtudSem = getAbsSemEtud(context, etud['cursem']['formsemestre_id'], etudid)
            params['nbabs']= AbsEtudSem.CountAbs()
            params['nbabsjust'] = AbsEtudSem.CountAbsJust()
            params['nbabsnj'] =  params['nbabs'] - params['nbabsjust']
            params['date_debut'] = etud['cursem']['date_debut']
            params['date_fin'] = etud['cursem']['date_fin']
            H.append("""<span title="absences du %(date_debut)s au %(date_fin)s">(1/2 j.)<br/>%(nbabsjust)s J., %(nbabsnj)s N.J.</span>"""
                     % params)
            
        H.append('<ul>')
        if REQUEST.AUTHENTICATED_USER.has_permission(ScoAbsChange,context):
            H.append("""
<li>     <a href="%(ScoURL)s/Absences/SignaleAbsenceEtud?etudid=%(etudid)s">Ajouter</a></li>
<li>     <a href="%(ScoURL)s/Absences/JustifAbsenceEtud?etudid=%(etudid)s">Justifier</a></li>
<li>     <a href="%(ScoURL)s/Absences/AnnuleAbsenceEtud?etudid=%(etudid)s">Supprimer</a></li>
""" % params )
            if context.get_preference('handle_billets_abs'):
                H.append("""<li>     <a href="%(ScoURL)s/Absences/listeBilletsEtud?etudid=%(etudid)s">Billets</a></li>""" % params )
            H.append("""
<li>     <a href="%(ScoURL)s/Absences/CalAbs?etudid=%(etudid)s">Calendrier</a></li>
<li>     <a href="%(ScoURL)s/Absences/ListeAbsEtud?etudid=%(etudid)s">Liste</a></li>
</ul>
""" % params )
    else:
        pass # H.append("(pas d'étudiant en cours)")
    # ---------
    H.append('</div><br/>&nbsp;') # /etud-insidebar
    # Logo
    scologo_img = context.icons.scologo_img.tag()
    H.append('<div class="logo-insidebar">%s<br/>' % scologo_img)
    H.append("""<a href="%(ScoURL)s/about" class="sidebar">A propos</a><br/>
<a href="%(SCO_WEBSITE)s" class="sidebar">Aide</a><br/>
</div>

</div> <!-- end of sidebar -->
""" % params ) # '
    #
    return ''.join(H)


def sidebar_dept(context, REQUEST=None):
    """Partie supérieure de la marge de gauche
    """
    infos = {
        'BASE0' : REQUEST.BASE0,
        'DeptIntranetTitle' : context.get_preference('DeptIntranetTitle'),
        'DeptIntranetURL' : context.get_preference('DeptIntranetURL'),
        'DeptName' : context.get_preference('DeptName'),
        'ScoURL' : context.ScoURL() }
    
    H = [ """<h2 class="insidebar">Dépt. %(DeptName)s</h2>
 <a href="%(BASE0)s" class="sidebar">Accueil</a> <br/> """ % infos ]
    if infos['DeptIntranetURL']:
        H.append('<a href="%(DeptIntranetURL)s" class="sidebar">%(DeptIntranetTitle)s</a> <br/>'
                 % infos )
    H.append("""<br/><a href="%(ScoURL)s/Entreprises" class="sidebar">Entreprises</a> <br/>""" % infos)
    return '\n'.join(H)


    
