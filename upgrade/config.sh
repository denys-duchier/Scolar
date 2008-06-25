

# ScoDoc: environment variables

SCODOC_DIR=${PWD%/*}

# Postgresql superuser:
POSTGRES_SUPERUSER=postgres

# Postgresql normal user: (by default, same a zope==www-data)
# IMPORTANT: must match SCO_DEFAULT_SQL_USER defined in sco_utils.py
POSTGRES_USER=www-data