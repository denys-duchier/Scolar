#!/bin/bash

# ScoDoc use Zope which runs only on Python2.4
# and Python2.4 does not include json module in std libs
# -> we must install an old simplejson 2.1 ourself (from python egg)

if [ -e /usr/lib/python2.4/site-packages/simplejson-2.1.0-py2.4-linux-i686.egg ]
then
  echo "simplejson is installed"
  exit 0
fi

SRCFILE=/opt/scodoc/instance/Products/ScoDoc/config/softs/simplejson-2.1.0.tar.gz

cd /tmp
tar xfz $SRCFILE
cd simplejson-2.1.0
python2.4 setup.py install
# nb: needs gcc, already installed by install_reportlab23.sh

# Configure Zope tmp egg directory
ZC=/opt/scodoc/instance/bin/zopectl
if [ $(grep -c PYTHON_EGG_CACHE $ZC) -lt 1 ]
then 
  mv $ZC $ZC.before_json
  cat $ZC.before_json | sed 's/^exec/export PYTHON_EGG_CACHE=\/tmp\/.egg_cache\nexec/' > $ZC
  chmod a+x $ZC
fi

echo 'simplejson installed'

