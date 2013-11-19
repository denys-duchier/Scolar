# -*- mode: python -*-
# -*- coding: utf-8 -*-

"""Modification decision de jury
"""
from common import *
# -> ici on est sur la page d'accueil du departement !
DeptURL = browser.url

# Cherche un formsemestre_id:
links = browser.find_link_by_partial_text('DUT')
u = links[0]['href']
formsemestre_id = re.search( r'formsemestre_id=(SEM[0-9]*)', u ).group(1)

# Cherche les etudids
browser.visit( urlparse.urljoin(DeptURL, 'formsemestre_recapcomplet?modejury=1&hidemodules=1&formsemestre_id=' + formsemestre_id) )

#u = browser.find_link_by_partial_href('formsemestre_bulletinetud')[0]['href']
#etudid = re.search( r'etudid=([A-Za-z0-9]*)', u ).group(1)

L = browser.find_link_by_partial_href('formsemestre_bulletinetud')
etudids = [ re.search(r'etudid=([A-Za-z0-9_]*)', x['href']).group(1) for x in L ]

def suppress_then_set( etudid, formsemestre_id, code='ADM' ):
    """Supprime decision de jury pour cet étudiant dans ce semestre
    puis saisie de la decision (manuelle) indiquée par code
    """
    # Suppression décision existante
    browser.visit( urlparse.urljoin(DeptURL, 'formsemestre_validation_suppress_etud?etudid=%s&formsemestre_id=%s&dialog_confirmed=1' % (etudid, formsemestre_id)))
    
    # Saisie décision
    browser.visit( urlparse.urljoin(DeptURL, 'formsemestre_validation_etud_form?etudid=%s&formsemestre_id=%s' % (etudid, formsemestre_id)))
    browser.fill('code_etat', [code])
    browser.find_by_name('formvalidmanu_submit').first.click()
    # pas de verification de la page résultat

# Change decisions de jury de tous les étudiants:
for etudid in etudids:
    print 'decision pour %s' % etudid
    suppress_then_set( etudid, formsemestre_id, code='ADM')

t1 = time.time()
print '%d etudiants traites en %gs' % (len(etudids),t1-t0)

