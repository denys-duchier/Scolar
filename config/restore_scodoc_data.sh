#!/bin/bash

#
# ScoDoc:  restore data (saved by save_scodoc_data) into current install
# 
#  Utile pour migrer ScoDoc d'un serveur a un autre
#  A executer en tant que root sur le nouveau serveur
#
# E. Viennet, Sept 2011
#


INSTANCE_DIR=/opt/scodoc/
SCODOC_DIR="$INSTANCE_DIR/Products/ScoDoc"

source utils.sh
check_uid_root $0

# Safety check
echo "Ce script va remplacer les donnees de votre installation ScoDoc par celles"
echo "enregistrees dans le fichier fourni."
echo "Ce fichier doit avoir ete cree par le script save_scodoc_data.sh, sur une autre machine."
echo 
echo "Attention: TOUTES LES DONNEES DE CE SERVEUR SERONT REMPLACEES !"
echo "Notamment, tous les utilisateurs et departements existants seront effaces !"
echo
echo "TOUTES LES BASES POSTGRESQL SERONT EFFACEES !!!"
echo 
echo -n "Voulez vous poursuivre cette operation ? (y/n) [n]"
read ans
if [ ! "$(norm_ans "$ans")" = 'Y' ]
then
   echo "Annulation"
   exit 1
fi

# Usage
if [ ! $# -eq 1 ]
then
  echo "Usage: $0 directory_or_archive"
  exit 1
fi

# Source directory
SRC=$1
if [ ${SRC##*.} = 'tgz' ]
then
  echo "Opening tgz archive..."
  tmp=$(mktemp -d)
  chmod a+rx "$tmp"
  cd "$tmp"
  tar xfz "$SRC" 
  SRC=$(ls -1d "$tmp"/*)
  IS_TMP=1
  # If source is a tgz, can use mv
  COPY="mv"
else
  IS_TMP=0
  # If source is a directory, does not modify its content
  COPY="cp -rp"
fi

echo "Source is $SRC"
echo "Stopping ScoDoc..."
/etc/init.d/scodoc stop

# Erase all postgres databases and load data
chmod a+rx "$SRC"
chmod a+r "$SRC"/scodoc.dump.txt
PG_DUMPFILE="$SRC/scodoc.dump.txt"

su -c "$SCODOC_DIR/config/psql_restore_databases.sh $PG_DUMPFILE" postgres

# 
echo Copying data files...
rm -rf "$SCODOC_DIR/config/depts" 
$COPY "$SRC/depts" "$SCODOC_DIR/config/depts"

rm -rf "$INSTANCE_DIR/var"
$COPY "$SRC/var" "$INSTANCE_DIR"

rm -rf  "$SCODOC_DIR/static/photos" 
$COPY "$SRC/photos" "$SCODOC_DIR/static/" 

rm -rf "$SCODOC_DIR/logos"
$COPY "$SRC/logos" "$SCODOC_DIR/"

mv "$SCODOC_DIR/config/scodoc_config.py"  "$SCODOC_DIR/config/scodoc_config.py.bak" 
$COPY "$SRC/scodoc_config.py" "$SCODOC_DIR/config/"

rm -rf "$INSTANCE_DIR/log"
$COPY "$SRC/log" "$INSTANCE_DIR/"

# Remove tmp directory
if [ $IS_TMP = "1" ]
then
  cd /
  rm -rf $tmp
fi
#
echo
echo "Ok. Run \"/etc/init.d/scodoc start\" to start ScoDoc."

