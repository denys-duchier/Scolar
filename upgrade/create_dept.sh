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

echo -n "Nom du departement (un mot, exemple \"Info\"): "
read DEPT

export DEPT

export db_name=SCO$(to_upper "$DEPT")

# -----------------------  Create database
su -c ./create_database.sh $POSTGRES_SUPERUSER 

# ----------------------- Create tables
# POSTGRES_USER == regular unix user (www-data)
su -c ./initialize_database.sh $POSTGRES_USER



