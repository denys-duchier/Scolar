#!/bin/bash

#
# ScoDoc:  restore data (saved by save_scodoc_data) into current install
# 
#  Utile pour migrer ScoDoc d'un serveur a un autre
#  A executer en tant que root sur le nouveau serveur
#
# E. Viennet, Sept 2011
#


INSTANCE_DIR=/opt/scodoc/instance
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
  tmp=$(mktemp)
  cd $tmp
  tar xfz "$SRC" 
  SRC="$tmp/*"
fi

echo "Source is $SRC"
echo "Stopping ScoDoc..."
/etc/init.d/scodoc stop

# Erase all postgres databases and load data
export PG_DUMPFILE="$SRC/scodoc.dump.txt"
su postgres<<EOF
 for f in $(psql -l --no-align --field-separator . | grep SCO | cut -f 1 -d.); do
  echo dropping $f
  dropdb $f
 done
 echo "Restoring postgres data..."
 psql -f "$PG_DUMPFILE" postgres
EOF

# 
rm -rf "$SCODOC_DIR/config/depts" 
cp -rp "$SRC/depts" "$SCODOC_DIR/config/depts"

rm -rf "$INSTANCE_DIR/var"
cp -rp "$SRC/var" "$INSTANCE_DIR"

rm -rf  "$SCODOC_DIR/static/photos" 
cp -rp "$SRC/photos" "$SCODOC_DIR/static/" 

rm -rf "$SCODOC_DIR/logos"
cp -rp "$SRC/logos" "$SCODOC_DIR/"

mv "$SCODOC_DIR/config/scodoc_config.py"  "$SCODOC_DIR/config/scodoc_config.py.bak" 
cp -p "$SRC/scodoc_config.py" "$SCODOC_DIR/config/"

rm -rf "$INSTANCE_DIR/log"
cp -rp "$SRC/log" "$INSTANCE_DIR/"

