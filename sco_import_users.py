# -*- mode: python -*-
# -*- coding: utf-8 -*-

##############################################################################
#
# Gestion scolarite IUT
#
# Copyright (c) 2001 - 2015 Emmanuel Viennet.  All rights reserved.
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

"""Import d'utilisateurs via fichier Excel
"""

from notesdb import *
from sco_utils import *
from notes_log import log
from TrivialFormulator import TrivialFormulator, TF
import sco_news
import sco_excel

TITLES = ( 'user_name', 'nom', 'prenom', 'email', 'roles', 'dept' )

def generate_excel_sample():
    """generates an excel document suitable to import users
    """
    style = sco_excel.Excel_MakeStyle(bold=True)
    titles = TITLES
    titlesStyles = [ style ] * len(titles)
    return sco_excel.Excel_SimpleTable( titles=titles,
                                        titlesStyles=titlesStyles,
                                        SheetName="Utilisateurs ScoDoc" )

def import_excel_file(datafile, REQUEST=None, context=None):
    "Create users from Excel file"
    authuser = REQUEST.AUTHENTICATED_USER
    auth_name = str(authuser)
    authuser_info = context._user_list( args={'user_name':auth_name} )
    zope_roles = authuser.getRolesInContext(context)
    if not authuser_info and not ('Manager' in zope_roles):
        # not admin, and not in database
        raise AccessDenied('invalid user (%s)' % auth_name)
    if authuser_info:
        auth_dept = authuser_info[0]['dept']
    else:
        auth_dept = ''
    log('sco_import_users.import_excel_file by %s' % auth_name )
    
    exceldata = datafile.read()
    if not exceldata:
        raise ScoValueError("Ficher excel vide ou invalide")
    diag, data = sco_excel.Excel_to_list(exceldata)
    if not data: # probably a bug
        raise ScoException('import_excel_file: empty file !')
    # 1-  --- check title line
    fs = [ strlower(stripquotes(s)) for s in data[0] ]
    log("excel: fs='%s'\ndata=%s" % (str(fs), str(data)))
    # check cols
    cols = {}.fromkeys(TITLES)
    unknown = []
    for tit in fs:
        if not cols.has_key(tit):
            unknown.append(tit)
        else:
            del cols[tit]
    if cols or unknown:
        raise ScoValueError('colonnes incorrectes (on attend %d, et non %d) <br/> (colonnes manquantes: %s, colonnes invalides: %s)'
                            %(len(TITLES),len(fs),cols.keys(),unknown ) )
    # ok, same titles...
    U = []
    for line in data[1:]:
        d = {}
        for i in range(len(fs)):
            d[fs[i]] = line[i]
        U.append(d)

    return import_users(U, auth_dept=auth_dept, context=context)

def import_users(U, auth_dept='', context=None):
    """Import des utilisateurs:
    Pour chaque utilisateur à créer:
    - vérifier données
    - générer mot de passe aléatoire
    - créer utilisateur et mettre le mot de passe
    - envoyer mot de passe par mail

    En cas d'erreur: supprimer tous les utilisateurs que l'on vient de créer.    
    """
    created = [] # liste de uid créés
    try:
        for u in U:
            ok, msg = context._check_modif_user(0, user_name=u['user_name'],
                                                nom=u['nom'], prenom=u['prenom'],
                                                email=u['email'], roles=u['roles'])
            if not ok:
                raise ScoValueError('données invalides pour %s: %s' % (u['user_name'], msg))
            u['passwd'] = generate_password()
            # si auth_dept, crée tous les utilisateurs dans ce departement
            if auth_dept:
                u['dept'] = auth_dept
            #
            context.create_user(u.copy())
	    created.append(u['user_name'])
    except:
        log('import_users: exception: deleting %s' % str(created))
        # delete created users
        for user_name in created:
            context._user_delete(user_name)
        raise # re-raise exception

    for u in U:
        mail_password(u, context=context)

    return 'ok'

#  --------- Génération du mot de passe initial -----------
# Adapté de http://aspn.activestate.com/ASPN/Cookbook/Python/Recipe/440564
# Alphabet tres simple pour des mots de passe simples...

import getpass, random, sha, string, md5, time, base64

ALPHABET=r"""ABCDEFGHIJKLMNPQRSTUVWXYZ123456789123456789AEIOU"""
PASSLEN=6
RNG = random.Random(time.time())

def generate_password():
    """This function creates a pseudo random number generator object, seeded with
    the cryptographic hash of the passString. The contents of the character set
    is then shuffled and a selection of passLength words is made from this list.
    This selection is returned as the generated password."""
    l = list(ALPHABET)  # make this mutable so that we can shuffle the characters
    RNG.shuffle(l)  # shuffle the character set
    # pick up only a subset from the available characters:
    return "".join(RNG.sample(l,PASSLEN))

from email.MIMEMultipart import MIMEMultipart
from email.MIMEText import MIMEText
from email.MIMEBase import MIMEBase
from email.Header import Header
from email import Encoders

def mail_password(u, context=None, reset=False):
    "Send password by email"
    if not u['email']:
        return

    u['url'] = context.ScoURL()

    txt = """
Bonjour %(prenom)s %(nom)s,

""" % u
    if reset:
        txt += """
votre mot de passe ScoDoc a été ré-initialisé.

Le nouveau mot de passe est:  %(passwd)s
Votre nom d'utilisateur est %(user_name)s

Vous devrez changer ce mot de passe lors de votre première connexion 
sur %(url)s
""" % u
    else:
        txt += """
vous avez été déclaré comme utilisateur du logiciel de gestion de scolarité ScoDoc.

Votre nom d'utilisateur est %(user_name)s
Votre mot de passe est: %(passwd)s

Le logiciel est accessible sur: %(url)s

Vous êtes invité à changer ce mot de passe au plus vite (cliquez sur
votre nom en haut à gauche de la page d'accueil).
""" % u

    txt += """
        
ScoDoc est un logiciel libre développé à l'Université Paris 13 par Emmanuel Viennet.
Pour plus d'informations sur ce logiciel, voir %s

""" % SCO_WEBSITE
    msg = MIMEMultipart()
    if reset:
        msg['Subject'] = Header( 'Mot de passe ScoDoc',  SCO_ENCODING )
    else:
        msg['Subject'] = Header( 'Votre accès ScoDoc',  SCO_ENCODING )
    msg['From'] = context.get_preference('email_from_addr')
    msg['To'] = u['email']
    msg.epilogue = ''
    txt = MIMEText( txt, 'plain', SCO_ENCODING )
    msg.attach(txt)
    context.sendEmail(msg)
