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

# check and upgrade reportlab
./install_reportlab23.sh

# check and install simplejson
./install_simplejson.sh
export PYTHON_EGG_CACHE=/tmp/.egg_cache

# check and install psycopg2
./install_psycopg2.sh 

# check symlinks to our customized Zope products
for P in exUserFolder ZPsycopgDA
do
  if [ ! -h $SCODOC_DIR/../$P ]
  then
     dest=$SCODOC_DIR/../../Attic
     if [ ! -e "$dest" ]
     then
       mkdir $dest
     fi
     if [ -e $SCODOC_DIR/../$P ]
     then
       echo "Moving old product $P to $dest"
       mv "$SCODOC_DIR/../$P" "$dest"
     fi
     echo "creating symlink to product $P"
     (cd $SCODOC_DIR/..; ln -s ScoDoc/ZopeProducts/$P)
  fi
done

# post-upgrade scripts
echo "Executing post-upgrade script..."
"$SCODOC_DIR"/config/postupgrade.py

echo "Executing post-upgrade database script..."
su -c "$SCODOC_DIR/config/postupgrade-db.py" $POSTGRES_USER

# 
echo
echo "Starting ScoDoc..."
/etc/init.d/scodoc start


