# -*- mode: python -*-
# -*- coding: iso8859-15 -*-

import pdb,os,sys,time,re,inspect
from sco_utils import SCO_ENCODING
from email.MIMEMultipart import MIMEMultipart
from email.MIMEText import MIMEText
from email.Header import Header

# Simple & stupid file logguer, used only to debug
# (logging to SQL is done in scolog)


LOG_FILENAME = 'notes.log' # empty to disable logging
DEFAULT_LOG_DIR = '/tmp' # clients should call set_log_directory to change this

ALARM_DESTINATION = 'emmanuel.viennet@univ-paris13.fr' # XXX a mettre en preference

class _logguer:
    def __init__(self):
        self.file = None
        self.set_log_directory( DEFAULT_LOG_DIR )
        
    def set_log_directory(self, directory):
        self.directory = directory

    def _open(self):
        if LOG_FILENAME:
            path = os.path.join( self.directory, LOG_FILENAME )
            self.file = open( path, 'a')
            self( 'new _logguer' )
        else:
            self.file = None # logging disabled
    
    def __call__(self, msg):
        if not self.file:
            self._open()
        if self.file:
            dept = retreive_dept()
            if dept:
                dept = ' (%s)' % dept
            self.file.write( '[%s]%s %s\n' %(time.strftime('%a %b %d %H:%M:%S %Y'), dept, msg) )
            #if not dept:
            #    import traceback
            #    traceback.print_stack(file=self.file) # hunt missing REQUESTS
            
            self.file.flush()


log = _logguer()

def retreive_request():
    """Try to retreive a REQUEST variable in caller stack"""
    def search(frame):
        if frame.f_locals.has_key('REQUEST'):
            return frame.f_locals['REQUEST']
        if frame.f_back:
            return search(frame.f_back)
        else:
            return None
    frame = inspect.currentframe()
    if frame: # not supported by all pythons
        return search(inspect.currentframe())
    else:
        return None

def retreive_dept():
    """Try to retreive departement (from REQUEST URL)"""
    REQUEST = retreive_request()
    if not REQUEST:
        return ''
    try:
        url = REQUEST.URL
        m = re.match('^.*ScoDoc/(\w+).*$', url)
        return m.group(1)
    except:
        return ''

# Alarms by email:
def sendAlarm( context, subj, txt ):
    msg = MIMEMultipart()
    subj = Header( subj,  SCO_ENCODING )
    msg['Subject'] = subj
    msg['From'] = context.get_preference('email_from_addr')
    msg['To'] = ALARM_DESTINATION
    msg.epilogue = ''
    txt = MIMEText( txt, 'plain', SCO_ENCODING )
    msg.attach(txt)
    context.sendEmail(msg)
