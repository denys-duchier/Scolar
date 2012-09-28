# -*- mode: python -*-
# -*- coding: iso8859-15 -*-

##############################################################################
#
# Gestion scolarite IUT
#
# Copyright (c) 2001 - 2011 Emmanuel Viennet.  All rights reserved.
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

"""Ajout/Modification/Supression UE
(portage from DTML)
"""
from notesdb import *
from sco_utils import *
from notes_log import log
from TrivialFormulator import TrivialFormulator, TF
from gen_tables import GenTable
import sco_groups
import sco_formsemestre_validation
import sco_codes_parcours

def ue_create(context, formation_id=None, REQUEST=None):
    """Creation d'une UE
    """
    return ue_edit(context, create=True, formation_id=formation_id, REQUEST=REQUEST)

def ue_edit(context, ue_id=None, create=False, formation_id=None, REQUEST=None):
    """Modification ou creation d'une UE    
    """
    create = int(create)
    if not create:
        U = context.do_ue_list( args={ 'ue_id' : ue_id } )
        if not U:
            raise ScoValueError("UE inexistante !")
        U = U[0]
        formation_id = U['formation_id']
        title = "Modification de l'UE %(titre)s" % U
        initvalues = U
        submitlabel = 'Modifier les valeurs'
    else:
        title = "Creation d'une UE"
        initvalues = {}
        submitlabel = 'Cr�er cette UE'
    Fol = context.formation_list( args={ 'formation_id' : formation_id } )
    if not Fol:
        raise ScoValueError("Formation %s inexistante ! (si vous avez suivi un lien valide, merci de signaler le probl�me)" % formation_id)
    Fo = Fol[0]
    H = [ context.sco_header(REQUEST, page_title=title,
                             javascripts=[ 'jQuery/jquery.js', 
                                           'js/edit_ue.js' ]
                             ),
          "<h2>" + title,
          ' (formation %(acronyme)s, version %(version)s)</h2>' % Fo,
          """
<p class="help">Les UE sont des groupes de modules dans une formation donn�e, utilis�s pour l'�valuation (on calcule des moyennes par UE et applique des seuils ("barres")). 
</p>

<p class="help">Note: L'UE n'a pas de coefficient associ�. Seuls les <em>modules</em> ont des coefficients.
</p>""" ]

    ue_types = UE_TYPE_NAME.keys()
    ue_types.sort()
    ue_types_names = [ UE_TYPE_NAME[k] for k in ue_types ]
    ue_types = [ str(x) for x in ue_types ]

    fw = [
        ('ue_id', { 'input_type' : 'hidden' }),
        ('create', { 'input_type' : 'hidden', 'default' : create }),
        ('formation_id', { 'input_type' : 'hidden', 'default' : formation_id }),
        ('titre'    , { 'size' : 30, 'explanation' : 'nom de l\'UE' }),
        ('acronyme' , { 'size' : 8, 'explanation' : 'abbr�viation', 'allow_null' : False }),
        ('numero',    { 'size' : 2, 'explanation' : 'num�ro (1,2,3,4) de l\'UE pour l\'ordre d\'affichage',
                        'type' : 'int' }),
        ('type', { 'explanation': 'type d\'UE (normal, sport&culture)',
                   'input_type' : 'menu',
                   'allowed_values': ue_types,
                   'labels' : ue_types_names }),
        ('ue_code', { 'size' : 12, 'title' : 'Code UE', 'explanation' : 'code interne. Toutes les UE partageant le m�me code (et le m�me code de formation) sont compatibles (compensation de semestres, capitalisation d\'UE). Voir informations ci-desous.' }),
    ]
    if create:
        fw.append(  ('create_matiere',
                     { 'input_type' : 'boolcheckbox',
                       'default' : False,
                       'title' : 'Cr�er mati�re identique',                              
                       'explanation' : 'cr�er imm�diatement une mati�re dans cette UE (utile si on n\'utilise pas de mati�res)'}) )
    tf = TrivialFormulator(REQUEST.URL0, REQUEST.form, fw,
                           initvalues = initvalues,
                           submitlabel = submitlabel )
    if tf[0] == 0:
        X = """<div id="ue_list_code"></div>
        """
        return '\n'.join(H) + tf[1] + X + context.sco_footer(REQUEST)
    else:
        if create:
            if not tf[2]['ue_code']:
                del tf[2]['ue_code']
            ue_id = context.do_ue_create(tf[2],REQUEST)
            if tf[2]['create_matiere']:
                matiere_id = context.do_matiere_create( { 'ue_id' : ue_id, 'titre' : tf[2]['titre'], 'numero' : 1 }, REQUEST )
        else:
            ue_id = do_ue_edit(context, tf[2])
        return REQUEST.RESPONSE.redirect( REQUEST.URL1 + '/ue_list?formation_id=' + formation_id )


def ue_delete(context, ue_id=None, delete_validations=False, dialog_confirmed=False, REQUEST=None):
    """Delete an UE"""
    ue = context.do_ue_list( args={ 'ue_id' : ue_id } )
    if not ue:
        raise ScoValueError("UE inexistante !")
    ue = ue[0]
    
    if not dialog_confirmed:
        return context.confirmDialog( "<h2>Suppression de l'UE %(titre)s (%(acronyme)s))</h2>" % ue,
                                  dest_url="", REQUEST=REQUEST,
                                  parameters = { 'ue_id' : ue_id },
                                  cancel_url="ue_list?formation_id=%s"%ue['formation_id'] )

    return context._do_ue_delete( ue_id, delete_validations=delete_validations, REQUEST=REQUEST )


def ue_list(context, formation_id=None, msg='', REQUEST=None):
    """Liste des mati�res (dans une formation)
    """
    authuser = REQUEST.AUTHENTICATED_USER

    F = context.formation_list( args={ 'formation_id' : formation_id } )
    if not F:
        raise ScoValueError("invalid formation_id")
    F = F[0]
    parcours = sco_codes_parcours.get_parcours_from_code(F['type_parcours'])
    locked = context.formation_has_locked_sems(formation_id)

    perm_change = authuser.has_permission(ScoChangeFormation,context)
    # editable = (not locked) and perm_change
    # On autorise maintanant la modification des formations qui ont des semestres verrouill�s,
    # sauf si cela affect les notes pass�es (verrouill�es):
    #   - pas de modif des modules utilis�s dans des semestres verrouill�s
    #   - pas de changement des codes d'UE utilis�s dans des semestres verrouill�s
    editable = perm_change

    if locked:
        lockicon = icontag('lock32_img', title="verrouill�")
    else:
        lockicon = ''
    
    arrow_up, arrow_down, arrow_none = sco_groups.getArrowIconsTags(context, REQUEST)
    delete_icon = icontag('delete_small_img', title="Supprimer (module inutilis�)", alt="supprimer")
    delete_disabled_icon = icontag('delete_small_dis_img', title="Suppression impossible (module utilis�)")
    H = [ context.sco_header(REQUEST, page_title="Programme %s" % F['acronyme']),
          """<h2>Formation %(titre)s (%(acronyme)s) [version %(version)s] code %(formation_code)s""" % F,
          lockicon, '</h2>' ]
    if locked:
        H.append( """<p class="help">Cette formation est verrouill�e car %d semestres verrouill�s s'y r�ferent.
Si vous souhaitez modifier cette formation (par exemple pour y ajouter un module), vous devez:
</p>
<ul class="help">
<li>soit cr�er une nouvelle version de cette formation pour pouvoir l'�diter librement (vous pouvez passer par la fonction "Associer � une nouvelle version du programme" (menu "Semestre") si vous avez un semestre en cours);</li>
<li>soit d�verrouiller le ou les semestres qui s'y r�f�rent (attention, en principe ces semestres sont archiv�s 
    et ne devraient pas �tre modifi�s).</li>
</ul>""" % len(locked))
    if msg:
        H.append('<p class="msg">' + msg + '</p>' )

    # Description de la formation
    H.append('<div class="formation_descr">')
    H.append('<div class="fd_d"><span class="fd_t">Titre:</span><span class="fd_v">%(titre)s</span></div>' % F )
    H.append('<div class="fd_d"><span class="fd_t">Titre officiel:</span><span class="fd_v">%(titre_officiel)s</span></div>' % F )
    H.append('<div class="fd_d"><span class="fd_t">Acronyme:</span><span class="fd_v">%(acronyme)s</span></div>' % F )
    H.append('<div class="fd_d"><span class="fd_t">Code:</span><span class="fd_v">%(formation_code)s</span></div>' % F )
    H.append('<div class="fd_d"><span class="fd_t">Version:</span><span class="fd_v">%(version)s</span></div>' % F )
    H.append('<div class="fd_d"><span class="fd_t">Type parcours:</span><span class="fd_v">%s</span></div>' % sco_codes_parcours.get_parcours_from_code(F['type_parcours']).__doc__ )
    H.append('<div><a href="formation_edit?formation_id=%(formation_id)s" class="stdlink">modifier ces informations</a></div>' % F )
    H.append('</div>')
    # Description des UE/mati�res/modules
    H.append('<div class="ue_list_tit">Programme p�dagogique:</div>')
    H.append('<ul class="notes_ue_list">')
    ue_list = context.do_ue_list( args={ 'formation_id' : formation_id } )
    for UE in ue_list:
        H.append('<li class="notes_ue_list">%(acronyme)s %(titre)s <span class="ue_code">(code %(ue_code)s)</span>' % UE)
        if UE['type'] != UE_STANDARD:
            H.append('<span class="ue_type">%s</span>' % UE_TYPE_NAME[UE['type']])
        ue_editable = editable and not context.ue_is_locked(UE['ue_id'])
        if ue_editable:
            H.append('<a class="stdlink" href="ue_edit?ue_id=%(ue_id)s">modifier</a>' % UE)
        else:
            H.append('<span class="locked">[verrouill�]</span>')
        H.append('<ul class="notes_matiere_list">')
        Matlist = context.do_matiere_list( args={ 'ue_id' : UE['ue_id'] } )
        for Mat in Matlist:
            H.append('<li class="notes_matiere_list">%(titre)s' % Mat)
            if editable and not context.matiere_is_locked(Mat['matiere_id']):
                H.append('<a class="stdlink" href="matiere_edit?matiere_id=%(matiere_id)s">modifier</a>' % Mat)
            H.append('<ul class="notes_module_list">')
            Modlist = context.do_module_list( args={ 'matiere_id' : Mat['matiere_id'] } )
            im = 0
            for Mod in Modlist:
                Mod['nb_moduleimpls'] = context.module_count_moduleimpls(Mod['module_id'])
                H.append('<li class="notes_module_list">')
                if im != 0 and editable:
                    H.append('<a href="module_move?module_id=%s&after=0" class="aud">%s</a>' % (Mod['module_id'], arrow_up))
                else:
                    H.append(arrow_none)
                if im < len(Modlist) - 1 and editable:
                    H.append('<a href="module_move?module_id=%s&after=1" class="aud">%s</a>' % (Mod['module_id'], arrow_down))
                else:
                    H.append(arrow_none)
                im += 1
                if Mod['nb_moduleimpls'] == 0 and editable:
                    H.append('<a class="smallbutton" href="module_delete?module_id=%s">%s</a>'
                             % (Mod['module_id'], delete_icon))
                else:
                    H.append(delete_disabled_icon)
                mod_editable = editable and not context.module_is_locked(Mod['module_id'])
                if mod_editable:
                    H.append('<a class="discretelink" title="Modifier le module num�ro %(numero)s, utilis� par %(nb_moduleimpls)d sessions" href="module_edit?module_id=%(module_id)s">' % Mod)                    
                H.append('%(code)s %(titre)s' % Mod )
                if mod_editable:
                    H.append('</a>')
                heurescoef = '%(heures_cours)s/%(heures_td)s/%(heures_tp)s, coef. %(coefficient)s' % Mod
                if Mod['ects'] is not None:
                    heurescoef += ', %g ECTS' % Mod['ects']
                H.append(' (%s %s)' % (parcours.SESSION_NAME, Mod['semestre_id']) + ' (%s)' % heurescoef )
                H.append('</li>')
            if not Modlist:
                H.append('<li>Aucun module dans cette mati�re !')
                if editable:
                    H.append('<a class="stdlink" href="matiere_delete?matiere_id=%(matiere_id)s">supprimer cette mati�re</a>' % Mat)
                H.append('</li>')
            if editable:
                H.append('<li> <a class="stdlink" href="module_create?matiere_id=%(matiere_id)s">cr�er un module</a></li>' % Mat)            
            H.append('</ul>')
            H.append('</li>')
        if not Matlist:
            H.append('<li>Aucune mati�re dans cette UE ! ')
            if editable:
                H.append("""<a class="stdlink" href="ue_delete?ue_id=%(ue_id)s">supprimer l'UE</a>""" % UE)
            H.append('</li>')
        if editable:
            H.append('<li><a class="stdlink" href="matiere_create?ue_id=%(ue_id)s">cr�er une mati�re</a> </li>' % UE)
        H.append('</ul>')
    if editable:
        H.append('<a class="stdlink" href="ue_create?formation_id=%s">Ajouter une UE</a></li>' % formation_id)
    H.append('</ul>')

    H.append('<p><ul>')
    if editable:
        H.append("""
<li><a class="stdlink" href="formation_create_new_version?formation_id=%(formation_id)s">Cr�er une nouvelle version (non verrouill�e)</a></li>
""" % F)
    H.append("""
<li><a class="stdlink" href="formation_table_recap?formation_id=%(formation_id)s">Table r�capitulative de la formation</a></li>
    
<li><a class="stdlink" href="formation_export?formation_id=%(formation_id)s&format=xml">Export XML de la formation</a> (permet de la sauvegarder pour l'�changer avec un autre site)</li>
<li><a class="stdlink" href="module_list?formation_id=%(formation_id)s">Liste d�taill�e des modules de la formation</a> (debug) </li>
</ul>
</p>""" % F )
    if perm_change:
        H.append("""
        <h3> <a name="sems">Semestres ou sessions de cette formation</a></h3>
        <p><ul>""")
        for sem in context.do_formsemestre_list(args={ 'formation_id' : formation_id } ):
            H.append('<li><a class="stdlink" href="formsemestre_status?formsemestre_id=%(formsemestre_id)s">%(titremois)s</a>' % sem)
            if sem['etat'] != '1':
                H.append(' [verrouill�]')
            else:
                H.append(' <a class="stdlink" href="formsemestre_editwithmodules?formation_id=%(formation_id)s&formsemestre_id=%(formsemestre_id)s">Modifier</a>' % sem )
            H.append('</li>')
        H.append('</ul>')
    
    if authuser.has_permission(ScoImplement,context):
        H.append("""<ul>
        <li><a class="stdlink" href="formsemestre_createwithmodules?formation_id=%(formation_id)s&semestre_id=1">Mettre en place un nouveau semestre de formation %(acronyme)s</a>
 </li>

</ul>""" % F)
#   <li>(debug) <a class="stdlink" href="check_form_integrity?formation_id=%(formation_id)s">V�rifier coh�rence</a></li>


    warn, ue_multiples = sco_formsemestre_validation.check_formation_ues(context, formation_id)
    H.append(warn)
    
    H.append(context.sco_footer(REQUEST))
    return '\n'.join(H)


def ue_sharing_code(context, ue_code=None, ue_id=None, hide_ue_id=None):
    """HTML list of UE sharing this code
    Either ue_code or ue_id may be specified.
    """
    if ue_id:
        ue = context.do_ue_list( args={ 'ue_id' : ue_id } )[0]
        if not ue_code:
            ue_code = ue['ue_code']
        F = context.formation_list( args={ 'formation_id' : ue['formation_id'] } )[0]
        formation_code = F['formation_code']
        
    ue_list_all = context.do_ue_list( args={ 'ue_code' : ue_code } )
    if ue_id:
        # retire les UE d'autres formations:
        #log('checking ucode %s formation %s' % (ue_code, formation_code)) 
        ue_list = []
        for ue in ue_list_all:
            F = context.formation_list( args={ 'formation_id' : ue['formation_id'] } )[0]
            if formation_code == F['formation_code']:
                ue_list.append(ue)
    else:
        ue_list = ue_list_all
        
    if hide_ue_id: # enl�ve l'ue de depart
        ue_list = [ ue for ue in ue_list if ue['ue_id'] != hide_ue_id ]
    
    if not ue_list:
        if ue_id:
            return """<span class="ue_share">Seule UE avec code %s</span>""" % ue_code
        else:
            return """<span class="ue_share">Aucune UE avec code %s</span>""" % ue_code
    H = []
    if ue_id:
        H.append('<span class="ue_share">Autres UE avec le code %s:</span>' % ue_code)
    else:
        H.append('<span class="ue_share">UE avec le code %s:</span>' % ue_code)
    H.append('<ul>')
    for ue in ue_list:
        F = context.formation_list( args={ 'formation_id' : ue['formation_id'] } )[0]
        H.append( '<li>%s (%s) dans <a class="stdlink" href="ue_list?formation_id=%s">%s (%s)</a>, version %s</li>'
                  % (ue['acronyme'], ue['titre'], F['formation_id'], F['acronyme'], F['titre'], F['version']))
    H.append('</ul>')
    return '\n'.join(H)

def do_ue_edit(context, args):
    "edit an UE"
    # check
    ue_id = args['ue_id']
    ue = context.do_ue_list({ 'ue_id' : ue_id })[0]
    if context.ue_is_locked(ue['ue_id']):
        raise ScoLockedFormError()        
    # check: acronyme unique dans cette formation
    if args.has_key('acronyme'):
        new_acro = args['acronyme']
        ues = context.do_ue_list({'formation_id' : ue['formation_id'], 'acronyme' : new_acro })
        if ues and ues[0]['ue_id'] != ue_id:
            raise ScoValueError('Acronyme d\'UE "%s" d�j� utilis� !' % args['acronyme'])

    # On ne peut pas supprimer le code UE:
    if args.has_key('ue_code') and not args['ue_code']:
        del args['ue_code']
    
    cnx = context.GetDBConnexion()
    context._ueEditor.edit( cnx, args )
    
    # Invalide les semestres utilisant cette formation:
    for sem in context.do_formsemestre_list(args={ 'formation_id' : ue['formation_id'] } ):
        context._inval_cache(formsemestre_id=sem['formsemestre_id']) #> formation (ue) modif.  


# ---- Table recap formation
def formation_table_recap(context, formation_id, format='html', REQUEST=None):
    """
    """
    F = context.formation_list( args={ 'formation_id' : formation_id } )
    if not F:
        raise ScoValueError("invalid formation_id")
    F = F[0]
    T = []
    ue_list = context.do_ue_list( args={ 'formation_id' : formation_id } )
    for UE in ue_list:
        Matlist = context.do_matiere_list( args={ 'ue_id' : UE['ue_id'] } )
        for Mat in Matlist:
            Modlist = context.do_module_list( args={ 'matiere_id' : Mat['matiere_id'] } )
            for Mod in Modlist:
                Mod['nb_moduleimpls'] = context.module_count_moduleimpls(Mod['module_id'])
                #
                T.append( {
                    'UE_acro' : UE['acronyme'],
                    'Mat_tit' : Mat['titre'],
                    'Mod_tit' : Mod['abbrev'] or Mod['titre'],
                    'Mod_code' : Mod['code'],
                    'Mod_coef' : Mod['coefficient'],
                    'Mod_sem' : Mod['semestre_id'],
                    'nb_moduleimpls' : Mod['nb_moduleimpls']
                    })
    columns_ids = [ 'UE_acro', 'Mat_tit', 'Mod_tit', 'Mod_code', 'Mod_coef', 'Mod_sem', 'nb_moduleimpls' ]
    titles = { 'UE_acro' : 'UE',
               'Mat_tit' : 'Mati�re',
               'Mod_tit' : 'Module',
               'Mod_code' : 'Code',
               'Mod_coef' : 'Coef.',
               'Mod_sem' : 'Sem.',
               'nb_moduleimpls' : 'Nb utilis�' }
    
    title = """Formation %(titre)s (%(acronyme)s) [version %(version)s] code %(formation_code)s""" % F
    tab = GenTable(
        columns_ids=columns_ids, rows=T, titles=titles,
        origin = 'G�n�r� par %s le ' % VERSION.SCONAME + timedate_human_repr() + '',
        caption = title,
        html_caption = title,
        html_class='gt_table table_leftalign',
        base_url = '%s?formation_id=%s' % (REQUEST.URL0, formation_id),
        page_title = title,
        html_title = '<h2>' + title + '</h2>',
        pdf_title = title,
        preferences=context.get_preferences()
        )
    return  tab.make_page(context, format=format, REQUEST=REQUEST)      
