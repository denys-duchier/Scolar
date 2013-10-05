
--- Tests avec splinter
http://splinter.cobrateam.info/docs/tutorial.html

Installation de Splinter:

apt-get install python-dev
apt-get install libxslt-dev
apt-get install libxml2-dev
apt-get install python-lxml python-cssselect


/opt/zope213/bin/easy_install zope.testbrowser
/opt/zope213/bin/easy_install cssselect
/opt/zope213/bin/easy_install splinter


J'ai du hacker _mechanize.py
ligne 218

vi +218 /opt/zope213/lib/python2.7/site-packages/mechanize-0.2.5-py2.7.egg/mechanize/_mechanize.py 

url = _rfc3986.urljoin(self._response.geturl()+'/', url)
(ajouter le + '/')

Essais:
/opt/zope213/bin/python common.py  
ne doit pas déclencher d'erreur



