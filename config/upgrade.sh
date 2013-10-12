#!/bin/bash

# Upgrade ScoDoc installation using SVN
#   SVN must be properly configured and have read access to ScoDoc repository
# This script STOP and RESTART ScoDoc and should be runned as root
#
# Script pour ScoDoc 7
#
# E. Viennet, septembre 2013

source config.sh
source utils.sh

check_uid_root $0

apt-get update

echo "Stopping ScoDoc..."
/etc/init.d/scodoc stop

echo
echo "Using SVN to update $SCODOC_DIR..."
(cd "$SCODOC_DIR"; svn update)

SVNVERSION=$(cd ..; svnversion)
if [ -e "$SCODOC_DIR"/config/scodoc.sn ]
then
  SN=$(cat "$SCODOC_DIR"/config/scodoc.sn)
  if [[ -n "$SN" && ${SN:0:5} == '<body' ]]
  then
    SN='' # fix for invalid previous replies
  fi 
  mode=upgrade
else
  mode=install  
fi

SVERSION=$(curl --fail --connect-timeout 5 --silent http://notes.iutv.univ-paris13.fr/scodoc-installmgr/version?mode=$mode\&svn="$SVNVERSION"\&sn="$SN")
if [ $? == 0 ]; then
  echo "${SVERSION}" > "${SCODOC_DIR}"/config/scodoc.sn
else
  echo 'Warning: cannot connect to scodoc release server'
fi

# Check that no Zope "access" file has been forgotten in the way:
if [ -e $SCODOC_DIR/../../access ]
then
  mv $SCODOC_DIR/../../access $SCODOC_DIR/../../access.bak
fi

# Fix some permissions which may have been altered in the way:
chown -R root.root "$SCODOC_DIR"/config
chmod a+rx "$SCODOC_DIR"/config/postupgrade-db.py
chmod a+r "$SCODOC_DIR"/config/scodocutils.py
chmod a+r "$SCODOC_DIR"/*.py
chmod -R a+r "$SCODOC_DIR"/misc

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

# Important to create .pyc:
chgrp www-data "${SCODOC_DIR}"
chmod g+w "${SCODOC_DIR}"
chgrp -R www-data "${SCODOC_DIR}"/ZopeProducts
chmod -R g+w "${SCODOC_DIR}"/ZopeProducts

# post-upgrade scripts
echo "Executing post-upgrade script..."
"$SCODOC_DIR"/config/postupgrade.py

echo "Executing post-upgrade database script..."
su -c "$SCODOC_DIR/config/postupgrade-db.py" $POSTGRES_USER

# 
echo
echo "Starting ScoDoc..."
/etc/init.d/scodoc start


