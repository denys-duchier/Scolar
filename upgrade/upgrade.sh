#!/bin/bash

# Upgrade ScoDoc installation using SVN
#   SVN must be properly configured and have read access to ScoDoc repository
# This script STOP and RESTART ScoDoc and should be runned as root
#
# E. Viennet, june 2008

SCODOC_DIR=/home/zope/instance/Products/Scolar

/etc/init.d/zope stop

echo "Using SVN to update $SCODOC_DIR..."
(cd $SCODOC_DIR; svn update)

# post-upgrade script
echo "Executing post-upgrade script..."
$SCODOC_DIR/upgrade/postupgrade.py

# 
echo "Starting Zope..."
/etc/init.d/zope stop


