#!/bin/bash

#
# ScoDoc: creation initiale d'un departement
#
# Ce script prend en charge la creation de la base de donnees
# et doit être lancé par l'utilisateur unix root dans le repertoire install
#
# E. Viennet, Juin 2008
#


source config.sh
source utils.sh


if [ "$UID" != "0" ] 
then
  echo "Erreur: le script $0 doit etre lance par root"
  exit 1
fi

echo "Nom du departement (un mot, exemple \"Info\"):"
read DEPT

export DEPT


# -----------------------  Create database
su $POSTGRES_SUPERUSER

# --- Ensure postgres user www-data exists
if [ -z $("select usename from pg_user;" | psql | grep $POSTGRES_USER) ]
then
 # add database user
 echo "Creating postgresql user $POSTGRES_USER"
 createuser --no-createdb --no-adduser "$POSTGRES_USER"
fi

# ---
dbuser=sco$(toLower "$DEPT")


createuser --pwprompt $dbuser


exit # exit su
# ----------------------- 
exit 0
