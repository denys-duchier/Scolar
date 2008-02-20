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

"""Gestions des "nouvelles"
"""

from notesdb import *
from notes_log import log
from scolars import monthsnames, abbrvmonthsnames
from sco_utils import SCO_ENCODING

import PyRSS2Gen
from cStringIO import StringIO
import datetime
from stripogram import html2text, html2safehtml

_scolar_news_editor = EditableTable(
    'scolar_news',
    'news_id',
    ( 'date', 'authenticated_user', 'type', 'object', 'text', 'url' ),
    sortkey = 'date desc',
    output_formators = { 'date' : DateISOtoDMY },
    input_formators  = { 'date' : DateDMYtoISO },
    html_quote=False # no user supplied data, needed to store html links
)

NEWS_INSCR = 'INSCR'
NEWS_NOTE = 'NOTES'
NEWS_FORM = 'FORM'
NEWS_SEM  =  'SEM'
NEWS_MISC = 'MISC'
NEWS_TYPES = (NEWS_INSCR, NEWS_NOTE, NEWS_FORM, NEWS_SEM, NEWS_MISC)

scolar_news_create = _scolar_news_editor.create
scolar_news_list   = _scolar_news_editor.list

def add(REQUEST, cnx, typ, object=None, text='', url=None ):
    args = { 'authenticated_user' : str(REQUEST.AUTHENTICATED_USER),
             'type' : typ,
             'object' : object,
             'text' : text,
             'url' : url
             }
    log('news: %s' % args)
    return scolar_news_create(cnx,args,has_uniq_values=False)

def resultset(cursor):
    "generator"
    row = cursor.dictfetchone()
    while row:
        yield row
        row = cursor.dictfetchone()
        
def scolar_news_summary(context, n=5):
    """Return last n news.
    News are "compressed", ie redondant events are joined.
    """
    # XXX mauvais algo: oblige a extraire toutes les news pour faire le resume
    cnx = context.GetDBConnexion()
    cursor = cnx.cursor()
    cursor.execute( 'select * from scolar_news order by date asc' )
    selected_news = {} # (type,object) : news dict
    for r in resultset(cursor):
        # si on a deja une news avec meme (type,object)
        # et du meme jour, on la remplace
        dmy = DateISOtoDMY(r['date']) # round
        key = (r['type'],r['object'],dmy)
        selected_news[key] = r
            
    news = selected_news.values()
    # sort by date, descending
    news.sort( lambda x,y: cmp(y['date'],x['date']) )
    news = news[:n]
    # mimic EditableTable.list output formatting:
    for n in news:
        # heure
        n['hm'] = n['date'].strftime('%Hh%M')
        n['rssdate'] = n['date'].strftime('%d/%m %Hh%M') # pour affichage
        for k in n.keys():
            if n[k] is None:
                n[k] = ''
            if _scolar_news_editor.output_formators.has_key(k):
                n[k] = _scolar_news_editor.output_formators[k](n[k])
        # date resumee
        j, m = n['date'].split('/')[:2]
        mois = abbrvmonthsnames[int(m)-1]
        n['formatted_date'] = '%s %s %s' % (j,mois,n['hm'])
        # indication semestre si ajout notes:
        if n['type'] == NEWS_NOTE:
            moduleimpl_id = n['object']
            mod = context.Notes.do_moduleimpl_list({'moduleimpl_id' : moduleimpl_id})[0]
            sem = context.Notes.get_formsemestre(mod['formsemestre_id'])
            if sem['semestre_id'] > 0:
                descr_sem = 'S%d' % sem['semestre_id']
            else:
                descr_sem = ''
            if sem['modalite']:
                descr_sem += ' ' + sem['modalite']
            n['text'] += ' (<a href="Notes/formsemestre_status?formsemestre_id=%s">%s</a>)' % (mod['formsemestre_id'], descr_sem)
    return news

def scolar_news_summary_html(context, n=5, rssicon=None):
    """News summary, formated in HTML"""
    news = scolar_news_summary(context,n=n)
    if not news:
        return ''
    H= ['<div class="news"><span class="newstitle">Dernières opérations']
    if rssicon:
        H.append( '<a href="rssnews">' + rssicon + '</a>' )
    H.append( '</span><ul class="newslist">' )
    
    for n in news:
        H.append('<li class="newslist"><span class="newsdate">%(formatted_date)s</span><span class="newstext">%(text)s</span></li>' % n )
    H.append('</ul>')

    # Informations générales
    H.append( """<div>
    Pour être informé des évolutions de ScoDoc,
    vous pouvez vous
    <a class="stdlink" href="https://www-gtr.iutv.univ-paris13.fr/mailman/listinfo/notes">
    abonner à la liste de diffusion</a>.
    </div>
    """ )

    H.append('</div>')
    return '\n'.join(H)

    
def scolar_news_summary_rss(context, title, sco_url, n=5):
    """rss feed for scolar news"""
    news = scolar_news_summary(context,n=n)
    items = []
    for n in news:
        text = html2text(n['text'])
        items.append( PyRSS2Gen.RSSItem(
            title= unicode( '%s %s' % (n['rssdate'], text), SCO_ENCODING),
            link = sco_url + '/' + n['url'],
            pubDate = n['date'] ))
    rss = PyRSS2Gen.RSS2(
        title = unicode(title, SCO_ENCODING),
        link = sco_url,
        description = unicode(title, SCO_ENCODING),
        lastBuildDate = datetime.datetime.now(),
        items = items )
    f = StringIO()
    rss.write_xml(f)
    f.seek(0)
    data = f.read()
    f.close()
    return data
    
                      
            
