

# ScoDoc: environment variables

SCODOC_DIR=${PWD%/*}

ZOPE_VERSION=2.11.0

# Postgresql superuser:
POSTGRES_SUPERUSER=postgres

# Postgresql normal user: (by default, same a zope==www-data)
# IMPORTANT: must match SCO_DEFAULT_SQL_USER defined in sco_utils.py
POSTGRES_USER=www-data

# psql command: if various versions installed, force the one we want:
PSQL=/usr/lib/postgresql/8.1/bin/psql

# tcp port for SQL server (under Debian 5432, or 5433 for 8.1 if 7.4 also installed !)
# Important note: if changed, you should probably also change it in
#      sco_utils.py (SCO_DEFAULT_SQL_PORT).
POSTGRES_PORT=5432
