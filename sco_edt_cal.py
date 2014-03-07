# -*- mode: python -*-
# -*- coding: utf-8 -*-

##############################################################################
#
# Gestion scolarite IUT
#
# Copyright (c) 2001 - 2014 Emmanuel Viennet.  All rights reserved.
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

"""Accès aux emplois du temps

XXX usage uniquement experimental pour tests implémentations

"""

import urllib2
import icalendar

from sco_utils import *
import sco_groups
import sco_groups_view

def formsemestre_load_ics(context, sem):
    """Load ics data, from our cache or, when necessary, from external provider
    """
    # TODO: cacher le résultat
    ics_url = context.get_preference('edt_sem_ics_url', sem['formsemestre_id'])
    if not ics_url:
        ics_data = ''
    else:
        log('Loading edt from %s' % ics_url)
        f = urllib2.urlopen(ics_url)
        ics_data = f.read()
        f.close()
    
    cal = icalendar.Calendar.from_ical(ics_data)
    return cal

def formsemestre_edt_groups_used(context, sem):
    """L'ensemble des groupes EDT utilisés dans l'emplois du temps publié
    """
    cal = formsemestre_load_ics(context, sem)
    return { e['X-GROUP-ID'].decode('utf8') for e in events }

def get_edt_transcodage_groups(context, formsemestre_id):
    """ -> { nom_groupe_edt : nom_groupe_scodoc }
    """
    # TODO: valider ces données au moment où on enregistre les préférences
    txt = context.get_preference('edt_groups2scodoc', formsemestre_id)
    edt2sco = {}
    sco2edt = {}
    msg = '' # message erreur, '' si ok
    line_num = 1
    for line in txt.split('\n'):
        fs = [ s.strip() for s in line.split(';') ]
        if len(fs) == 1: # groupe 'tous'
            edt2sco[fs[0]] = None
            sco2edt[None] = fs[0]
        elif len(fs) == 2:
            edt2sco[fs[0]] = fs[1]
            sco2edt[fs[1]] = fs[0]
        else:
            msg = 'ligne %s invalide' % line_num
        line_num += 1

    log('sco2edt=%s' % pprint.pformat(sco2edt) )
    return edt2sco, sco2edt, msg

def group_edt_json(context, group_id, start='', end='', REQUEST=None):
    """EDT complet du semestre, au format JSON
    TODO: indiquer un groupe
    TODO: utiliser start et end (2 dates au format ISO YYYY-MM-DD)
    TODO: cacher
    """
    group = sco_groups.get_group(context, group_id)
    sem = context.Notes.get_formsemestre(group['formsemestre_id'])
    edt2sco, sco2edt, msg = get_edt_transcodage_groups(context, group['formsemestre_id'])

    edt_group_name = sco2edt.get(group['group_name'], group['group_name'])
    log('group scodoc=%s : edt=%s' % (group['group_name'], edt_group_name))
    
    cal = formsemestre_load_ics(context, sem)
    events = [ e for e in cal.walk() if e.name == 'VEVENT' ]
    J = []
    for e in events:
        if e['X-GROUP-ID'].encode('utf-8').strip() == edt_group_name:
            d = { 'title' : e['X-MODULE-CODE'].encode('utf-8') + '/' + e['X-GROUP-ID'].encode('utf-8'),
                  'start' : e.decoded('dtstart').isoformat(),
                  'end' : e.decoded('dtend').isoformat()
                  }
            J.append(d)
    
    return sendJSON(REQUEST, J)

def experimental_calendar(context, group_id=None, formsemestre_id=None, REQUEST=None):
    """experimental page
    """
    return '\n'.join([
        context.sco_header(
            REQUEST, 
            javascripts=[ 
                'libjs/purl.js',
                'libjs/moment.min.js',
                'libjs/fullcalendar/fullcalendar.min.js',
                ],
            cssstyles=[ 
#                'libjs/bootstrap-3.1.1-dist/css/bootstrap.min.css',
#                'libjs/bootstrap-3.1.1-dist/css/bootstrap-theme.min.css',
#                'libjs/bootstrap-multiselect/bootstrap-multiselect.css'
                'libjs/fullcalendar/fullcalendar.css',
                # media='print' 'libjs/fullcalendar/fullcalendar.print.css'
                ]
                ),
        """<style>
        #loading {
		display: none;
		position: absolute;
		top: 10px;
		right: 10px;
        }
        </style>
        """,
        """<form id="group_selector" method="get">
        <span style="font-weight: bold; font-siez:120%">Emplois du temps du groupe</span>""",
        sco_groups_view.menu_group_choice(context, group_id=group_id, formsemestre_id=formsemestre_id),
        """</form><div id="loading">loading...</div>
        <div id="calendar"></div>
        """,
        context.sco_footer(REQUEST),

        """<script>
$(document).ready(function() {

var group_id = $.url().param()['group_id'];

$('#calendar').fullCalendar({
  events: {
    url: 'group_edt_json?group_id=' + group_id,
    error: function() {
      $('#script-warning').show();
    }
   },
  timeFormat: 'HH:mm',
  timezone: 'local', // heure locale du client
  loading: function(bool) {
    $('#loading').toggle(bool);
  }
});
});
</script>
        """
        ])

