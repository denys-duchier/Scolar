# -*- mode: python -*-
# -*- coding: utf-8 -*-

"""Partie commune:

se connecte et accede a la page d'accueil du premier departement
"""
from splinter import Browser
import re, sys, time
import urlparse
import pdb
from optparse import OptionParser

from conn_info import *

parser = OptionParser()
parser.add_option("-d", "--dept", dest="dept_index", default=0, help="indice du departement")
options, args = parser.parse_args()

dept_index = int(options.dept_index)

t0 = time.time()
browser = Browser('zope.testbrowser')
browser._browser.mech_browser.set_handle_robots(False) # must ignore ScoDoc robots.txt
browser.visit(SCODOC)
print 'Start: title:', browser.title
print 'URL: ', browser.url
# print browser.html

links = browser.find_link_by_partial_text('Scolarit')
print '%d departements' % len(links)

links[dept_index].click() # va sur le premier departement

# ---- Formulaire authentification
print 'Authentification: ', browser.url

browser.fill('__ac_name', USER)
browser.fill('__ac_password', PASSWD)
button = browser.find_by_id('submit')
button[0].click()

# ---- Page accueil Dept
print browser.url

links = browser.find_link_by_partial_text('DUT')
links[0].click()
print 'Starting test from %s' % browser.url
print browser.title
