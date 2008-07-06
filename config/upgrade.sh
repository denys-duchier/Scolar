#!/bin/bash

# Upgrade ScoDoc installation using SVN
#   SVN must be properly configured and have read access to ScoDoc repository
# This script STOP and RESTART ScoDoc and should be runned as root
#
# E. Viennet, june 2008

source config.sh
source utils.sh

check_uid_root $0

echo "Stopping ScoDoc..."
/etc/init.d/scodoc stop

echo
echo "Using SVN to update $SCODOC_DIR..."
(cd $SCODOC_DIR; svn update)

# post-upgrade script
echo "Executing post-upgrade script..."
$SCODOC_DIR/install/postupgrade.py

# 
echo
echo "Starting ScoDoc..."
/etc/init.d/scodoc start


