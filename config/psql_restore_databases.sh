#!/bin/bash

# aux script called by restore_scodoc_data.sh as "postgres" user
# DO NOT CALL DIRECTLY

PG_DUMPFILE=$1

# Check locale of installation. If invalid, reinitialize all system

is_latin1=$(psql -l | grep postgres | grep iso88591 | wc -l)
if [ $is_latin1 -gt 1 ]
then
  echo "Recreating postgres cluster using UTF-8"

  pg_dropcluster --stop 9.1 main

  pg_createcluster --locale en_US.UTF-8 --start 9.1 main
fi


# Drop all current ScoDoc databases, if any:
for f in $(psql -l --no-align --field-separator . | grep SCO | cut -f 1 -d.); do
  echo dropping $f
  dropdb $f
done
echo "Restoring postgres data..."
psql -f "$PG_DUMPFILE" postgres

