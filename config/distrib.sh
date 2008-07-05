#!/bin/bash

# Pense bete pour tout nettoyer avant de faire une distribution...
#
#
# E. Viennet, jul 2008

source config.sh
source utils.sh

if [ "$UID" != "0" ] 
then
  echo "Erreur: le script $0 doit etre lance par root"
  exit 1
fi


echo "Changing to directory " $SCODOC_DIR/config
cd  $SCODOC_DIR/config

echo "Stopping ScoDoc..."
/etc/init.d/scodoc stop

# DROITS
echo -n "Verification des droits: proprietaire www-data ? [y/n] "
read ans
if [ "$(to_upper ${ans:0:1})" = 'Y' ]
then
  echo 'changing owner to www-data'
  chown -R www-data.www-data ..
fi

# SVN
echo -n "svn update ? [y/n] "
read ans
if [ "$(to_upper ${ans:0:1})" = 'Y' ]
then
  echo 'Updating from SVN...'
  (cd ..; svn update)
fi


# DEPARTEMENTS
echo -n "Supprimer les configs de departements ? [y/n] "
read ans
if [ "$(to_upper ${ans:0:1})" = 'Y' ]
then
   echo "moving " depts/*.cfg "to /tmp"
   mv depts/*.cfg /tmp
fi

# LOGS ZOPE
echo -n "Effacer les logs de Zope et ScoDoc  ? [y/n] "
read ans
if [ "$(to_upper ${ans:0:1})" = 'Y' ]
then
    (cd ../../../log/; ./purge)
fi

# IMAGE Data.fs
echo -n "Recopier le Data.fs original  ? [y/n] "
read ans
if [ "$(to_upper ${ans:0:1})" = 'Y' ]
then
   echo "moving Data.fs to /tmp"
   mv ../../../var/Data.fs ../../../var/Data.fs.index /tmp
   DATAFS=../../../var/Data.fs.ok-to-distrib-545
   echo "copying $DATAFS to Data.fs"
   cp -p $DATAFS ../../../var/Data.fs
fi

#
echo
echo "OK, vous pouvez archiver la distribution !"
echo
