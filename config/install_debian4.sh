#!/bin/bash

#
# ScoDoc: install third-party software necessary for our installation
# starting for a minimal Debian (4.0) install.
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

# ------------ AJOUT DES PAQUETS NECESSAIRES
apt-get update
apt-get install apache2 ssl-cert postgresql-7.4 postgresql-client-7.4 
apt-get install firehol
apt-get install python-jaxml python-psycopg python-pyrss2gen python-imaging python-reportlab-accel python-crack python-pydot
 

# ------------ LOCALES
echo 
echo '---- Configuration des locales...'
echo

if [ ! -e /etc/locale.gen ]
then
touch /etc/locale.gen
fi


for locname in en_US.ISO-8859-15 en_US.ISO-8859-1
do
  if [ $(grep $locname /etc/locale.gen | wc -l) -le 1 ]
  then
    echo $locname >> /etc/locale.gen
  fi
done

/usr/sbin/locale-gen --keep-existing 
echo 'Done.'


# ------------ PYEXCELERATOR
echo
echo 'Installation de pyExcelerator'
echo

(cd /tmp; tar xfz $SCODOC_DIR/config/softs/pyExcelerator-0.6.3a.patched.tgz)
(cd /tmp/pyExcelerator-0.6.3a.patched; python setup.py install)

echo 'Done.'

# ------------ CONFIG FIREWALL
echo 
echo -n "Voulez vous installer un firewall minimal ? [y/n] "
read ans
if [ $(to_upper ${ans:0:1}) = 'Y' ]
then
    echo 'Installation du firewall IP (voir /etc/firehol/firehol.conf)'
    echo 'Attention: suppose que l\'interface reseau vers Internet est eth0'
    echo '  si ce n\'est pas le cas, editer /etc/firehol/firehol.conf'
    echo '  et relancer: /etc/init.d/firehol restart'
    echo
    cp $SCODOC_DIR/config/etc/firehol.conf /etc/firehol/
    /etc/init.d/firehol restart
fi

# ------------ CONFIG APACHE
a2enmod ssl
a2enmod proxy
a2enmod proxy_http
a2enmod rewrite

echo 
echo -n "Voulez vous configurer le serveur web Apache maintenant ? [y/n] "
read ans
if [ $(to_upper ${ans:0:1}) = 'Y' ]
then
    echo "Configuration d'Apache"
    echo -n "Nom complet de votre serveur (exemple: notes.univ.fr): "
    read server_name
    echo 'generation de /etc/apache2/sites-available/scodoc-site-ssl'
    cat $SCODOC_DIR/config/etc/scodoc-site-ssl.orig | sed -e "s:YOUR\.FULL\.HOST\.NAME:$server_name:g" > /etc/apache2/sites-available/scodoc-site-ssl
    echo 'activation du site...'
    a2ensite scodoc-site-ssl
    /etc/init.d/apache2 restart
fi


# ------------ CONFIG SERVICE SCODOC
echo 
echo -n "Voulez vous installer le service scodoc ? [y/n] "
read ans
if [ $(to_upper ${ans:0:1}) = 'Y' ]
then
    echo 'Installation du demarrage automatique de ScoDoc'
    cp $SCODOC_DIR/config/etc/scodoc /etc/init.d/
    update-rc.d scodoc defaults
fi

