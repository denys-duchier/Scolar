#!/bin/bash

# Upgrade ScoDoc installation from ScoDoc 6 to ScoDoc 7
#   
# This script should be runned as root (with scodoc stopped)
#

# E. Viennet, march 2013

if [ -e /opt/scodoc/upgraded_to_v7 ]
then
 exit 0
fi

# ensure we are stopped:
/etc/init.d/scodoc stop 


# Add some missing linux packages:
apt-get update && apt-get dist-upgrade
apt-get install python-psycopg2


# Upgrade Scodoc...
cd /tmp

# Get archive:

XXXX tests XXXX

#curl --fail -O http://www-l2ti.univ-paris13.fr/~viennet/ScoDoc/builds/scodoc7-upgrade.tgz
#if [ $? != 0 ]; then
#  echo "Erreur: echec du telechargement de la mise a jour vers ScoDoc 7"
#  exit 1
#fi

# Open and place directories
tar xfz scodoc7-upgrade.tgz
mv zope213 /opt
mv scodoc7 /opt

# Move current scodoc dirs to new tree:
for d in var log Products
do
   echo "Moving ScoDoc $d to new tree"
   mv "/opt/scodoc/instance/$d" /opt/scodoc7/
done

echo "Old scodoc files moved to /opt/scodoc6"
mv /opt/scodoc /opt/scodoc6
mv /opt/scodoc7 /opt/scodoc

# done
touch /opt/scodoc/upgraded_to_v7

echo "Upgrade to ScoDoc 7 completed"
