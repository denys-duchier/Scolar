# -*- mode: python -*-
# -*- coding: utf-8 -*-

"""Essais de base:

se connecte, accede a un semestre puis a un module,
et modifie les notes existantes dans la premiere evaluation

"""

from common import *
# ici on est sur la page d'accueil du departement !

links = browser.find_link_by_partial_text('DUT informatique en FI')
links[0].click()

# ---- Tableau bord semestre
print browser.url
# va dans module AP2 saisir des notes (dans la p1ere evaluation):
browser.find_link_by_partial_text('AP1').first.click()
browser.find_link_by_partial_text('Saisir notes').first.click()

# ---- Ici c'est complique car le bouton submit est disabled
# on construit l'url a la main:
url = browser.find_by_id('gr')[0]["action"]
evaluation_id = browser.find_by_name('evaluation_id').value
group_id = re.search( r'value="(.*?)".*?tous', browser.html ).group(1)
dest = urlparse.urljoin(url, 'notes_evaluation_formnotes?evaluation_id='+evaluation_id+'&group_ids:list='+group_id+'&note_method=form')
browser.visit(dest)

# ---- Change une note:
# browser.fill('note_EID3835', '15')
etudids = re.findall( r'name="note_(.*?)"', browser.html )[1:]
note_max = float(re.search( r'notes sur ([0-9]+?)</span>\)', browser.html ).group(1))
for etudid in etudids:
    # essaie d'ajouter 1 à la note !
    old_val = browser.find_by_name('note_%s' % etudid).value
    try:
        val = min(float(old_val) + 1, note_max)
        browser.fill('note_%s'%etudid, str(val))
        print etudid, old_val, '->', val
    except:
        pass

# ... et met la derniere au max (pour tester)
browser.fill('note_%s'%etudids[-1], str(note_max))
print etudids[-1], '->', note_max

# ---- Validation formulaire saisie notes:
browser.find_by_id('tf_submit').click()
browser.find_by_id('tf_submit').click()
