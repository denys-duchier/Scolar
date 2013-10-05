#!/opt/zope213/bin/python
# -*- mode: python -*-
# -*- coding: iso8859-15 -*-

"""Essais de changements intensifs des notes
   (pour faire des tests en parallele)

se connecte, accede a un semestre puis a un module,
et modifie les notes existantes dans la premiere evaluation

ajoute puis soustrait 1 aux notes valides, N fois

"""
import time

from common import *
# -> ici on est sur la page d'accueil du departement !

links = browser.find_link_by_partial_text('DUT')
links[0].click() # va sur le 1er semestre de DUT trouve

# ---- Tableau bord semestre
print browser.url
# va dans module M1101 saisir des notes (dans la p1ere evaluation):
browser.find_link_by_partial_text('M1101').first.click()
browser.find_link_by_partial_text('Saisir notes').first.click()

# ---- Ici c'est complique car le bouton submit est disabled
# on construit l'url a la main:
url = browser.find_by_id('gr')[0]["action"]
evaluation_id = browser.find_by_name('evaluation_id').value
group_id = re.search( r'value="(.*?)".*?tous', browser.html ).group(1)
url_form = urlparse.urljoin(url, 'notes_evaluation_formnotes?evaluation_id='+evaluation_id+'&group_ids:list='+group_id+'&note_method=form')


# ---- Ajoute une constante aux notes valides:
# le browser doit etre sur le formulaire saisie note
def add_to_notes(increment):
    etudids = re.findall( r'name="note_(.*?)"', browser.html )[1:]
    note_max = float(re.search( r'notes sur ([0-9]+?)</span>\)', browser.html ).group(1))
    print 'add_to_notes: %d etudiants' % len(etudids)
    for etudid in etudids:
        # essaie d'ajouter 1 a la note !
        old_val = browser.find_by_name('note_%s' % etudid).value
        try:
            val = max(0,min(float(old_val) + increment, note_max))
            browser.fill('note_%s'%etudid, str(val))
            print etudid, old_val, '->', val
        except:
            pass
    
    # ---- Validation formulaire saisie notes:
    browser.find_by_id('tf_submit').click()
    browser.find_by_id('tf_submit').click()


for i in range(10):
    browser.visit(url_form) # va sur form saisie notes
    add_to_notes(1)
    #time.sleep(1)
    browser.visit(url_form) # va sur form saisie notes
    add_to_notes(-1)
    #time.sleep(1)

t1 = time.time()
print 'done in %gs' % (t1-t0)
