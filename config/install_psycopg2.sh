#!/bin/bash

# Install pyscopg2 postgresql driver

# This script installs from shipped archive

PYTHON=python2.4

SRC_ARCHIVE="/opt/scodoc/instance/Products/ScoDoc/config/softs/psycopg2-2.4.6.tar.gz"

# Test if psycopg2 installed
ver=$($PYTHON <<EOF
try:
    import psycopg2
    print psycopg2.__version__.split()[0]
except:
    print '0'
EOF
)

if [ "$ver" != "2.4.6" ]
then
 echo "Installing pyscopg2"
 apt-get install gcc
 cd /tmp
 tar xfz $SRC_ARCHIVE 
 cd  psycopg2-2.4.6
 $PYTHON setup.py install
fi

