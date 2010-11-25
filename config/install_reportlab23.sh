#!/bin/bash

# Debian 5 '(lenny) is shipped with Reportlab 2.1
# We need 2.3 to use the new <img> tag (in PDF bulletins)

# This script checks the installed version and try to install the 2.3 from sources.
# Internet access (web) is required.

PYTHON=python2.4
REPORTLAB_SRC_URL=http://www.reportlab.com/ftp/reportlab-2.3.tar.gz

REPORTLAB_VERSION=$($PYTHON -c "import reportlab; print reportlab.Version")
if [ $REPORTLAB_VERSION == "2.1" ]
then
 echo "Trying to install reportlab version 2.3"
 apt-get -y install wget
 pushd /tmp
 wget $REPORTLAB_SRC_URL
 if [ $? != 0 ]
 then
   echo "Error: cannot download reportlab sources"
   echo "from url" $REPORTLAB_SRC_URL
   exit 1
 fi
 tar xfz ReportLab_2_3.tar.gz
 apt-get -y install gcc python2.4-dev
 apt-get -y remove python-reportlab
 cd ReportLab_2_3
 python2.4 setup.py install
 popd
fi
