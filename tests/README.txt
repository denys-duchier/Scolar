
--- Tests avec splinter
http://splinter.cobrateam.info/docs/tutorial.html

Installation de Splinter:

apt-get install python-dev
apt-get install libxslt-dev
apt-get install libxml2-dev
curl -O https://raw.github.com/pypa/pip/master/contrib/get-pip.py
python get-pip.py
/usr/bin/easy_install zope.testbrowser
/usr/bin/easy_install cssselect       


J'ai du hacker /usr/local/lib/python2.6/dist-packages/mechanize-0.2.5-py2.6.egg/mechanize/_mechanize.py
ligne 218
url = _rfc3986.urljoin(self._response.geturl()+'/', url)
