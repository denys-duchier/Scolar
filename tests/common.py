# -*- mode: python -*-
# -*- coding: iso8859-15 -*-

"""Partie commune:

se connecte et accede a la page d'accueil du premier departement
"""
from splinter import Browser
import re
import urlparse
import pdb

from conn_info import *

browser = Browser('zope.testbrowser')
browser.visit(SCODOC)
print browser.title
print browser.url
# print browser.html

links = browser.find_link_by_partial_text('Scolarit')
print '%d departements' % len(links)

links[0].click()

# ---- Formulaire authentification
print browser.url

browser.fill('__ac_name', USER)
browser.fill('__ac_password', PASSWD)
button = browser.find_by_id('submit')
button[0].click()

# ---- Page accueil Dept
print browser.url

links = browser.find_link_by_partial_text('DUT informatique en FI')
links[0].click()
