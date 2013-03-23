#!/bin/bash

#
# ScoDoc: install third-party software necessary for our installation
# starting for a minimal Debian (Squeeze, 6.0) install.
#
# E. Viennet, Jun 2008, Apr 2009, Sept 2011
#

source config.sh
source utils.sh

check_uid_root $0

# ------------ VERIFIE VERSIONS POSTGRESQL
if [ ! -z "$(dpkg -l | grep postgresql-7.4)" ]
then
   echo
   echo "Attention:  postgresql-7.4 est deja installe"
   echo "ScoDoc va installer et utiliser postgresql-8.4"
   echo "Verifiez les ports dans postgresql.conf (5432 ou 5433)"
   echo "et dans ScoDoc: config.sh et sco_utils.py"
   echo
   echo -n "continuer ? (y/n) [y] "
   read ans
   if [ "$(norm_ans "$ans")" = 'N' ]
   then
     exit 1
   fi
   echo
   echo "Il est recommande de ne pas installer postgresql 7.4 et 8 en meme temps,"
   echo "sauf si vous avez deja des données sous postgres 7.4 (auquel cas vous devrez"
   echo "gerer votre configuration vous même)."
   echo 
   echo -n "Puis-je desinstaller postgresql 7.4 (recommande) ? (y/n) [n] "
   read ans
   if [ "$(norm_ans "$ans")" = 'Y' ]
   then
       apt-get --yes remove postgresql-7.4 postgresql-client-7.4
   fi
fi

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
  outname=$(echo ${locname//-/} | tr '[A-Z]' '[a-z]')
  if [ $(locale -a | egrep ^${outname}$ | wc -l) -le 1 ]
  then
    echo adding $locname
    echo "$locname ${locname##*.}" >> /etc/locale.gen
  fi
done

/usr/sbin/locale-gen --keep-existing 


if [ "$LANG" != "en_US.iso88591" ]
then
   # ceci est necessaire a cause de postgresql 8.3 qui 
   # cree son cluster lors de l'install avec la locale par defaut !
   echo "Attention: changement de la locale par defaut"
   mv /etc/default/locale /etc/default/locale.orig
   echo "LANG=\"en_US.iso88591\"" > /etc/default/locale
   export LANG=en_US.iso88591
fi
echo 'Done.'


# ------------ AJOUT DES PAQUETS NECESSAIRES
apt-get update
apt-get -y install subversion curl cracklib-runtime firehol
apt-get -y install apache2 ssl-cert postgresql-8.4 postgresql-client-8.4
apt-get -y install graphviz

# ------------ INSTALL DE PYTHON2.4
# apt-get -y install python2.4 python-jaxml python-psycopg python-pyrss2gen python-imaging python-reportlab python-crack python-pyparsing

SOFTS="$SCODOC_DIR/config/softs"
apt-get install -y build-essential g++ libpq-dev

echo Installing Python2.4
cd /tmp
tar xvfz "$SOFTS/Python-2.4.6-config.tgz" # sources avec module zlib active
cd Python-2.4.6
./configure && make && make install
ln -s /usr/local/bin/python2.4 /usr/bin/python2.4

PYTHON=/usr/local/bin/python2.4

# Python packages used by Zope and ScoDoc:
echo Installing jaxml
(cd $SOFTS/jaxml-3.01; $PYTHON setup.py install)

echo Installing mx-base
(cd /tmp; tar xfz "$SOFTS/egenix-mx-base-3.2.1.tar.gz"; cd egenix-mx-base-3.2.1; $PYTHON setup.py install)

echo Installing psycopg
cd /tmp
 tar xfz "$SOFTS/psycopg-1.1.21.tar.gz"
 cd psycopg-1.1.21
   ./configure --with-python-version=2.4 --with-python=$PYTHON --with-postgres-includes=/usr/include/postgresql  --with-mxdatetime-includes=/usr/local/lib/python2.4/site-packages/mx/DateTime/mxDateTime
   make install
cd "$SOFTS"

echo Installing PyRSS2Gen
(cd /tmp; tar xfz "$SOFTS/PyRSS2Gen-1.0.0.tar.gz"; cd PyRSS2Gen-1.0.0; $PYTHON setup.py install)

echo Installing PIL
apt-get install -y libjpeg62-dev zlib1g-dev libfreetype6-dev liblcms1-dev
(cd /tmp; tar xfz "$SOFTS/Imaging-1.1.7.tar.gz"; cd Imaging-1.1.7; $PYTHON setup.py install)

echo Installing Reportlab
apt-get -y install libfreetype6 libfreetype6-dev
(cd  /tmp; tar xfz "$SOFTS/reportlab-2.5.tar.gz"; cd reportlab-2.5; $PYTHON setup.py install)

echo Installing python-crack
apt-get -y install libcrack2-dev libcrack2 cracklib-runtime
(cd  /tmp; tar xfz "$SOFTS/setuptools-0.6c11.tar.gz"; cd setuptools-0.6c11; $PYTHON setup.py install)
(cd  /tmp; tar xfz "$SOFTS/cracklib-2.8.15.tar.gz"; cd cracklib-2.8.15; $PYTHON setup.py install)

echo Installing pyparsing
(cd /tmp; tar xfz "$SOFTS/pyparsing-1.5.6.tgz"; cd pyparsing-1.5.6;  $PYTHON setup.py install)

cd "$SOFTS"/..
./install_simplejson.sh

# ------------
SVNVERSION=$(cd ..; svnversion)
SVERSION=$(curl --silent http://notes.iutv.univ-paris13.fr/scodoc-installmgr/version?mode=install\&svn=$SVNVERSION)
echo $SVERSION > $SCODOC_DIR/config/scodoc.sn

# python-pydot is currently bugged in Debian 5: install our 0.9.10
# Le probleme: pydot v > 1 a change l'API : resultat de get_node est une liste. Resolu par sco_utils.pydot_get_node
# pydot 1.0.25 bug avec python 2.4 (get_node_list() renvoie toujours [])
#       1.0.3 idem (voir misc/testpydot.py)
echo '\nInstallation de pydot\n'
(cd /tmp; tar xfz $SCODOC_DIR/config/softs/pydot-0.9.10.tar.gz)
(cd /tmp/pydot-0.9.10;  $PYTHON setup.py install)

# ------------ PYEXCELERATOR
echo
echo 'Installation de pyExcelerator'
echo

(cd /tmp; tar xfz $SCODOC_DIR/config/softs/pyExcelerator-0.6.3a.patched.tgz)
(cd /tmp/pyExcelerator-0.6.3a.patched; $PYTHON setup.py install)

echo 'Done.'

# ------------ POSTFIX
echo 
echo "ScoDoc a besoin de pouvoir envoyer des messages par mail."
echo -n "Voulez vous configurer la messagerie (tres recommande) ? (y/n) [y] "
read ans
if [ "$(norm_ans "$ans")" != 'N' ]
then
    apt-get -y install postfix
fi

# ------------ CONFIG FIREWALL
echo 
echo "Le firewall aide a proteger votre serveur d'intrusions indesirables."
echo -n "Voulez vous installer un firewall minimal ? (y/n) [n] "
read ans
if [ "$(norm_ans "$ans")" = 'Y' ]
then
    echo 'Installation du firewall IP (voir /etc/firehol/firehol.conf)'
    echo "Attention: suppose que l'interface reseau vers Internet est eth0"
    echo "  si ce n'est pas le cas, editer /etc/firehol/firehol.conf"
    echo "  et relancer: /etc/init.d/firehol restart"
    echo
    cp $SCODOC_DIR/config/etc/firehol.conf /etc/firehol/
    mv /etc/default/firehol /etc/default/firehol.orig
    cat /etc/default/firehol.orig | sed 's/START_FIREHOL=NO/START_FIREHOL=YES/' > /tmp/firehol && mv /tmp/firehol /etc/default/firehol
fi

# Nota: after this point, the network may be unreachable 
# (if firewall config is wrong)

# ------------ CONFIG APACHE
a2enmod ssl
a2enmod proxy
a2enmod proxy_http
a2enmod rewrite

echo 
echo "La configuration du serveur web va modifier votre installation Apache pour supporter ScoDoc."
echo -n "Voulez vous configurer le serveur web Apache maintenant ? (y/n) [y] "
read ans
if [ "$(norm_ans "$ans")" != 'N' ]
then
    echo "Configuration d'Apache"
    server_name=""
    while [ -z $server_name ]
    do
        echo "Le nom de votre serveur doit normalement etre connu dans le DNS."
	echo -n "Nom complet de votre serveur (exemple: notes.univ.fr): "
	read server_name
    done
    # --- CERTIFICATS AUTO-SIGNES
    echo 
    echo "Il est possible d'utiliser des certificats cryptographiques"
    echo "auto-signes, qui ne seront pas reconnus comme de confiance"
    echo "par les navigateurs, mais offrent une certaine securite."
    echo -n 'Voulez vous generer des certificats ssl auto-signes ? (y/n) [y] '
    read ans
    if [ "$(norm_ans "$ans")" != 'N' ]
    then
        # attention: utilise dans scodoc-site-ssl.orig
	ssl_dir=/etc/apache2/scodoc-ssl 
	if [ ! -e $ssl_dir ]
	then
          mkdir $ssl_dir
	fi
	/usr/sbin/make-ssl-cert /usr/share/ssl-cert/ssleay.cnf $ssl_dir/apache.pem
    fi
    # ---
    echo 'generation de /etc/apache2/sites-available/scodoc-site-ssl'
    cat $SCODOC_DIR/config/etc/scodoc-site-ssl.orig | sed -e "s:YOUR\.FULL\.HOST\.NAME:$server_name:g" > /etc/apache2/sites-available/scodoc-site-ssl
    echo 'activation du site...'
    a2ensite scodoc-site-ssl

    echo 'Remplacement du site Apache par defaut (sic ! old saved as .bak)'
    fn=/etc/apache2/sites-available/default
    if [ -e $fn ]
    then
       mv $fn $fn.bak
    fi
    cp $SCODOC_DIR/config/etc/scodoc-site.orig $fn

    if [ -z "$(grep Listen /etc/apache2/ports.conf | grep 443)" ]
    then
      echo 'adding port 443'
      echo 'Listen 443' >> /etc/apache2/ports.conf
    fi

    echo 'configuring Apache proxy'
    mv /etc/apache2/mods-available/proxy.conf /etc/apache2/mods-available/proxy.conf.bak
    cat > /etc/apache2/mods-available/proxy.conf <<EOF
<IfModule mod_proxy.c>
# Proxy config for ScoDoc default installation
ProxyRequests Off
  <ProxyMatch http://localhost:8080>
          Order deny,allow
          Allow from all
  </ProxyMatch>
</IfModule>
EOF

    /etc/init.d/apache2 restart
fi


# ------------ CONFIG SERVICE SCODOC
echo 
echo "Installer le service scodoc permet de lancer automatiquement le serveur au demarrage."
echo -n "Voulez vous installer le service scodoc ? (y/n) [y] "
read ans
if [ "$(norm_ans "$ans")" != 'N' ]
then
    echo 'Installation du demarrage automatique de ScoDoc'
    cp $SCODOC_DIR/config/etc/scodoc /etc/init.d/
    insserv scodoc
fi

# ------------ THE END
echo
echo "Installation terminee."
echo
echo "Vous pouvez maintenant creer la base d'utilisateurs avec ./create_user_db.sh"
echo "puis creer un departement avec  ./create_dept.sh"
echo


