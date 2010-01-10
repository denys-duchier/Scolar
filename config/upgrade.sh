#!/bin/bash

# Upgrade ScoDoc installation using SVN
#   SVN must be properly configured and have read access to ScoDoc repository
# This script STOP and RESTART ScoDoc and should be runned as root
#
# E. Viennet, june 2008

source config.sh
source utils.sh

check_uid_root $0

if [ ! -e /usr/bin/curl ]; then
  apt-get update
  apt-get -y install curl # now necessary
fi

echo "Stopping ScoDoc..."
/etc/init.d/scodoc stop

echo
echo "Using SVN to update $SCODOC_DIR..."
(cd "$SCODOC_DIR"; svn update)

SVNVERSION=$(cd ..; svnversion)
if [ -e "$SCODOC_DIR"/config/scodoc.sn ]
then
  SN=$(cat "$SCODOC_DIR"/config/scodoc.sn)
  if [ ${SN:0:5} == '<body' ] 
  then
    SN='' # fix for invalid previous replies
  fi 
  mode=upgrade
else
  mode=install  
fi

SVERSION=$(curl --silent http://notes.iutv.univ-paris13.fr/scodoc-installmgr/version?mode=$mode\&svn="$SVNVERSION"\&sn="$SN")
if [ ! -z "$SVERSION" ]; then
  echo "${SVERSION}" > "${SCODOC_DIR}"/config/scodoc.sn
fi

# Se recharge car ce fichier peut avoir change durant le svn up !
if [ -z "$SCODOC_UPGRADE_RUNNING" ]
then
  export SCODOC_UPGRADE_RUNNING=1
  ./upgrade.sh
  exit 0
fi

# check permissions
# ScoDoc must be able to write to this directory:
chgrp -R www-data "${SCODOC_DIR}"/static/photos
chmod -R g+w "${SCODOC_DIR}"/static/photos

# check and upgrade reportlab
./install_reportlab23.sh

# post-upgrade scripts
echo "Executing post-upgrade script..."
"$SCODOC_DIR"/config/postupgrade.py

echo "Executing post-upgrade database script..."
su -c "$SCODOC_DIR/config/postupgrade-db.py" $POSTGRES_USER

# 
echo
echo "Starting ScoDoc..."
/etc/init.d/scodoc start


