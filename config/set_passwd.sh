#!/bin/bash

#
# ScoDoc: reglage du mot de passe admin Zope
# (in Zope terminology, an emergency user)
#
# Doit �tre lanc� par l'utilisateur unix root dans le repertoire .../config
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

echo "Creation d'un utilisateur d'urgence pour ScoDoc"
echo "(utile en cas de perte de votre mot de passe admin)"

mdir=/opt/zope213/lib/python2.7/site-packages/Zope2-2.13.21-py2.7.egg/Zope2/utilities

python $mdir/zpasswd.py $SCODOC_DIR/../../access

echo
echo "redemarrer scodoc pour prendre en compte le mot de passe"
echo
