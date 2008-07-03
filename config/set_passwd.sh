#!/bin/bash

#
# ScoDoc: reglage du mot de passe admin Zope
# (in Zope terminology, an emergency user)
#
# Doit être lancé par l'utilisateur unix root dans le repertoire .../config
#                       ^^^^^^^^^^^^^^^^^^^^^
# E. Viennet, Juin 2008
#

source config.sh
source utils.sh


if [ "$UID" != "0" ] 
then
  echo "Erreur: le script $0 doit etre lance par root"
  exit 1
fi

echo 'Reglage du compte administrateur Zope'

mdir=$SCODOC_DIR/../../../$ZOPE_VERSION/lib/python/Zope2/Startup/misc/

python $mdir/zpasswd.py $SCODOC_DIR/../../access

echo
echo "redemarrer scodoc pour prendre en compte le mot de passe"
echo
