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

# Se recharge car ce fichier peut avoir change durant le svn up !
if [ -z $SCODOC_UPGRADE_RUNNING ]
then
  export SCODOC_UPGRADE_RUNNING=1
  ./upgrade.sh
  exit 0
fi

# post-upgrade scripts
echo "Executing post-upgrade script..."
$SCODOC_DIR/config/postupgrade.py

echo "Executing post-upgrade database script..."
su -c "$SCODOC_DIR/config/postupgrade-db.py" $POSTGRES_USER

# 
echo
echo "Starting ScoDoc..."
/etc/init.d/scodoc start


