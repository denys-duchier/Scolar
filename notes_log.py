# -*- mode: python -*-
# -*- coding: iso8859-15 -*-

import pdb,os,sys,time
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
            self.file.write( '[%s] %s\n' %(time.strftime('%a %b %d %H:%M:%S %Y'), msg) )
            self.file.flush()


log = _logguer()


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
