# -*- mode: python -*-
# -*- coding: iso8859-15 -*-

import pdb,os,sys,time

# Simple & stupid file logguer, used only to debug
# (logging to SQL is done in scolog)


LOG_FILENAME = '/tmp/notes2.log' # empty to disable logging

class _logguer:
    def __init__(self, filename):
        if filename:
            self.file = open(filename, 'a')
            self( 'new _logguer' )
        else:
            self.file = None
    
    def __call__(self, msg):
        if self.file:
            self.file.write( '[%s] %s\n' %(time.strftime('%a %b %d %H:%M:%S %Y'), msg) )
            self.file.flush()


log = _logguer( LOG_FILENAME )

