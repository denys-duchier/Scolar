#!/bin/bash

#
# ScoDoc: creation de la base de donnees d'utilisateurs
#
# Ce script prend en charge la creation de la base de donnees
# et doit �tre lanc� par l'utilisateur unix root dans le repertoire .../config
#                          ^^^^^^^^^^^^^^^^^^^^^
# E. Viennet, Juin 2008
#

source config.sh
source utils.sh

if [ "$UID" != "0" ] 
then
  echo "Erreur: le script $0 doit etre lance par root"
  exit 1
fi

# --- Ensure postgres user www-data exists
init_postgres_user

db_name=BOBOSCOUSERS

echo 'Creating postgresql database ' $db_name
su -c "createdb -E LATIN1 -O $POSTGRES_USER $db_name" $POSTGRES_SUPERUSER 

echo 'Initializing tables in database ' $db_name
su -c "psql -h localhost -U $POSTGRES_USER  $db_name < $SCODOC_DIR/misc/create_user_table.sql" $POSTGRES_USER
