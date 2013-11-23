#!/bin/bash

#
# ScoDoc: save all user data (database, configs, images, archives...) in separate directory
# 
#  Utile pour migrer ScoDoc d'un serveur a un autre
#  Executer en tant que root sur le serveur d'origine
#
# E. Viennet, Sept 2011
#

# Destination directory
if [ ! $# -eq 1 ]
then
  echo "Usage: $0 destination_directory"
  exit 1
fi
DEST=$1
# remove trailing slashs if needed:
shopt -s extglob
DEST="${DEST%%+(/)}"

if [ ! -e "$DEST" ]
then
  echo Creating directory "$DEST"
  mkdir "$DEST"
else
  echo "Error: Directory " "$DEST"  " exists"
  echo "remove it or specify another destination !"
  exit 2
fi

INSTANCE_DIR=/opt/scodoc
SCODOC_DIR="$INSTANCE_DIR/Products/ScoDoc"

source utils.sh
check_uid_root $0

echo "Stopping ScoDoc..."
/etc/init.d/scodoc stop

# Dump all postgres databases
echo "Dumping SQL database..."
chown postgres "$DEST"
su -c "pg_dumpall > \"$DEST\"/scodoc.dump.txt" postgres
if [ ! $? -eq 0 ] 
then
  echo "Error dumping postgresql database\nPlease check that SQL server is running\nAborting."
  exit 1
fi
chown root "$DEST"

# Depts db config
echo "Copying depts configs..."
cp -rp "$SCODOC_DIR/config/depts" "$DEST"

# Zope DB and ScoDoc archives:
echo "Copying var/ ..." 
cp -rp "$INSTANCE_DIR/var" "$DEST"

# Photos des etudiants
echo "Copying photos..."
cp -rp "$SCODOC_DIR/static/photos" "$DEST"

echo "Copying logos..."
cp -rp "$SCODOC_DIR/logos" "$DEST"

echo "Copying configuration file..."
cp -p "$SCODOC_DIR/config/scodoc_config.py" "$DEST"

echo "Copying server logs..."
cp -rp "$INSTANCE_DIR/log" "$DEST"


# --- Archive all files in a tarball to ease transfer
echo
echo "Archiving backup files in a $DEST.tgz..."
base=$(basename "$DEST")
(cd "$DEST"/..; tar cfz "$DEST".tgz "$base")

echo "Done (you can copy " "$DEST"".tgz to destination machine)."
