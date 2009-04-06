#!/bin/bash

#
# ScoDoc: creation initiale d'un departement
#
# Ce script prend en charge la creation de la base de donnees
# et doit être lancé par l'utilisateur unix root dans le repertoire .../config
#                          ^^^^^^^^^^^^^^^^^^^^^
# E. Viennet, Juin 2008
#


source config.sh
source utils.sh

check_uid_root $0


echo -n "Nom du departement (un mot sans ponctuation, exemple \"Info\"): "
read DEPT

if [[ ! "$DEPT" =~ ^[A-Za-z0-9]+$ ]]
then
 echo 'Nom de departement invalide !'
 exit 1
fi

export DEPT

export db_name=SCO$(to_upper "$DEPT")

cfg_pathname="$SCODOC_DIR/config/depts/$DEPT".cfg

if [ -e $cfg_pathname ]
then
  echo 'Erreur: Il existe deja une configuration pour "'$DEPT'"'
  exit 1
fi

# --- Ensure postgres user www-data exists
init_postgres_user

# -----------------------  Create database
su -c ./create_database.sh $POSTGRES_SUPERUSER 

# ----------------------- Create tables
# POSTGRES_USER == regular unix user (www-data)
su -c ./initialize_database.sh $POSTGRES_USER

# ----------------------- Enregistre fichier config
echo "dbname="$db_name > $cfg_pathname

# ----------------------- 
echo
echo " Departement $DEPT cree"
echo
echo " Attention: la base de donnees n'a pas de copies de sauvegarde"
echo 
echo " Maintenant, vous pouvez ajouter le departement via l'application web"
echo " en suivant le lien \"Administration de ScoDoc\" sur la page d\'accueil."
echo
