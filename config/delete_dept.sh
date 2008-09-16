#!/bin/bash

#
# ScoDoc: suppression d'un departement
#
# Ce script supprime la base de donnees ScoDoc d'un departement
# *** le departement doit au prealable avoir été supprime via l'interface web ! ***
#
# Ne fonctionne que pour les configurations "standards" (dbname=xxx)
#
# Il doit être lancé par l'utilisateur unix root dans le repertoire .../config
#                          ^^^^^^^^^^^^^^^^^^^^^
# E. Viennet, Sept 2008
#


source config.sh
source utils.sh

check_uid_root $0

echo
echo "Ce script supprime la base de donnees ScoDoc d'un departement"
echo
echo "Attention: le departement doit au prealable avoir ete supprime via l'interface web !"
echo "faites le AVANT d'executer ce script !!!"
echo
echo -n "Nom du departement a supprimer (un mot sans ponctuation, exemple \"Info\"): "
read DEPT

if [[ ! "$DEPT" =~ "^[A-Za-z0-9]+$" ]]
then
 echo "Nom de departement invalide !"
 exit 1
fi

export DEPT

cfg_pathname="$SCODOC_DIR/config/depts/$DEPT".cfg

if [ -e $cfg_pathname ]
then
  # suppression de la base postgres
  db_name=$(cat $cfg_pathname | sed '/^dbname=*/!d; s///;q')
  echo "suppression de la base postgres $db_name"
  su -c "dropdb $db_name" $POSTGRES_SUPERUSER || terminate "ne peux supprimer base de donnees $db_name"
  # suppression du fichier de config
  /bin/rm -f $cfg_pathname || terminate "ne peux supprimer $cfg_pathname"
  exit 0
else
  echo 'Erreur: pas de configuration trouvee pour "'$DEPT'"'
  exit 1
fi
