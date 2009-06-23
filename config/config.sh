

# ScoDoc: environment variables

export SCODOC_DIR=${PWD%/*}

export ZOPE_VERSION=2.11.0

# Postgresql superuser:
export POSTGRES_SUPERUSER=postgres

# Postgresql normal user: (by default, same a zope==www-data)
# IMPORTANT: must match SCO_DEFAULT_SQL_USER defined in sco_utils.py
export POSTGRES_USER=www-data

# psql command: if various versions installed, force the one we want:
debian_version=$(cat /etc/debian_version)
debian_version=${debian_version// /}
if [ ${debian_version:0:1} = "5" ] 
then
   PSQL=/usr/lib/postgresql/8.3/bin/psql
else
   PSQL=/usr/lib/postgresql/8.1/bin/psql
fi

# tcp port for SQL server (under Debian 4, 5432 or 5433 for 8.1 if 7.4 also installed !)
# Important note: if changed, you should probably also change it in
#      sco_utils.py (SCO_DEFAULT_SQL_PORT).
export POSTGRES_PORT=5432
