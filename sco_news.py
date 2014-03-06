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

"""Gestions des "nouvelles"
"""

from notesdb import *
from notes_log import log
import scolars
from sco_utils import SCO_ENCODING, SCO_ANNONCES_WEBSITE

import PyRSS2Gen
from cStringIO import StringIO
import datetime, re
from stripogram import html2text, html2safehtml
from email.MIMEMultipart import MIMEMultipart
from email.MIMEText import MIMEText
from email.Header import Header
from email import Encoders

_scolar_news_editor = EditableTable(
    'scolar_news',
    'news_id',
    ( 'date', 'authenticated_user', 'type', 'object', 'text', 'url' ),
    sortkey = 'date desc',
    output_formators = { 'date' : DateISOtoDMY },
    input_formators  = { 'date' : DateDMYtoISO },
    html_quote=False # no user supplied data, needed to store html links
)

NEWS_INSCR = 'INSCR' # inscription d'étudiants (object=None)
NEWS_NOTE = 'NOTES'  # saisie note (object=moduleimpl_id)
NEWS_FORM = 'FORM'   # modification formation (object=formation_id)
NEWS_SEM  =  'SEM'   # creation semestre (object=None)
NEWS_MISC = 'MISC'   # unused
NEWS_MAP = {
    NEWS_INSCR : "inscription d'étudiants",
    NEWS_NOTE : "saisie note",
    NEWS_FORM : "modification formation",
    NEWS_SEM :  "création semestre",
    NEWS_MISC : "opération", # unused
    }
NEWS_TYPES = NEWS_MAP.keys()

scolar_news_create = _scolar_news_editor.create
scolar_news_list   = _scolar_news_editor.list

def add(context, REQUEST, typ, object=None, text='', url=None ):
    """Ajoute une nouvelle
    """
    cnx = context.GetDBConnexion()
    args = {
        'authenticated_user' : str(REQUEST.AUTHENTICATED_USER),
        'user_info' : context.Users.user_info(user_name=str(REQUEST.AUTHENTICATED_USER), REQUEST=REQUEST),
        'type' : typ,
        'object' : object,
        'text' : text,
        'url' : url,
        }
    
    log('news: %s' % args)
    _send_news_by_mail(context, args)
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
    cursor = cnx.cursor(cursor_factory=ScoDocCursor)
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
        d = n['date']
        n['date822'] = n['date'].strftime("%a, %d %b %Y %H:%M:%S %z")
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
        mois = scolars.abbrvmonthsnames[int(m)-1]
        n['formatted_date'] = '%s %s %s' % (j,mois,n['hm'])
        # indication semestre si ajout notes:
        infos = _get_formsemestre_infos_from_news(context, n)
        if infos:                        
            n['text'] += ' (<a href="Notes/formsemestre_status?formsemestre_id=%(formsemestre_id)s">%(descr_sem)s</a>)' % infos
    return news

def _get_formsemestre_infos_from_news(context, n):
    if n['type'] != NEWS_NOTE:
        return {}
    moduleimpl_id = n['object']
    mods = context.Notes.do_moduleimpl_list({'moduleimpl_id' : moduleimpl_id})
    if not mods:
        return {} # module does not exists anymore
    mod = mods[0]
    sem = context.Notes.get_formsemestre(mod['formsemestre_id'])
    if sem['semestre_id'] > 0:
        descr_sem = 'S%d' % sem['semestre_id']
    else:
        descr_sem = ''
    if sem['modalite']:
        descr_sem += ' ' + sem['modalite']
    return { 'formsemestre_id' : mod['formsemestre_id'],
             'sem' : sem,
             'descr_sem' : descr_sem,
             }

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
    <a class="stdlink" href="%s">
    abonner à la liste de diffusion</a>.
    </div>
    """ % SCO_ANNONCES_WEBSITE)

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
            pubDate = n['date822'] ))
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

def _send_news_by_mail(context, n):
    """Notify by email
    """    
    infos = _get_formsemestre_infos_from_news(context, n)
    formsemestre_id = infos.get('formsemestre_id',None)
    prefs = context.get_preferences(formsemestre_id=formsemestre_id)
    destinations = prefs['emails_notifications'] or ''
    destinations = [ x.strip() for x in destinations.split(',') ]
    destinations = [ x for x in destinations if x ]
    if not destinations:
        return
    #
    txt = n['text']
    if infos:
        txt += '\n\nSemestre <a href="Notes/formsemestre_status?formsemestre_id=%(formsemestre_id)s">%(descr_sem)s</a>)' % infos
        txt += '\n\nEffectué par: %(nomcomplet)s\n' % n['user_info']
        
    txt = '\n' + txt + """\n
--- Ceci est un message de notification automatique issu de ScoDoc
--- vous recevez ce message car votre adresse est indiquée dans les paramètres de ScoDoc.
"""
    
    # Transforme les URL en URL absolue
    base = context.ScoURL()
    txt = re.sub( 'href=.*?"', 'href="'+base+'/', txt )

    # Transforme les liens HTML en texte brut: '<a href="url">texte</a>' devient 'texte: url'
    # (si on veut des messages non html)
    txt = re.sub( r'<a.*?href\s*=\s*"(.*?)".*?>(.*?)</a>', r'\2: \1', txt)
    
    msg = MIMEMultipart()
    msg['Subject'] = Header( '[ScoDoc] ' + NEWS_MAP.get(n['type'],'?'),  SCO_ENCODING )
    msg['From'] = prefs['email_from_addr']
    txt = MIMEText( txt, 'plain', SCO_ENCODING )
    msg.attach(txt)
    
    for email_addr in destinations:
        if email_addr:
            del msg['To']
            msg['To'] = email_addr
            #log('xxx mail: %s' % msg)
            context.sendEmail(msg)
    
