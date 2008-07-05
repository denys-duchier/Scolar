

# ScoDoc: environment variables

SCODOC_DIR=${PWD%/*}

ZOPE_VERSION=2.11.0

# Postgresql superuser:
POSTGRES_SUPERUSER=postgres

# Postgresql normal user: (by default, same a zope==www-data)
# IMPORTANT: must match SCO_DEFAULT_SQL_USER defined in sco_utils.py
POSTGRES_USER=www-data

# tcp port for SQL server (under Debian 5434 for 7.4, 5433 for 8.1)
# Important note: if changed, you should probably also change it in
#      sco_utils.py (SCO_DEFAULT_SQL_PORT).
POSTGRES_PORT=5433
