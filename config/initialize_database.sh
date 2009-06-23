#!/bin/bash

# Initialize database (create tables) for a ScoDoc instance
# This script must be executed as www-data user
#
# $db_name and $DEPT passed as environment variables

source config.sh
source utils.sh

if [ $(id -nu) != $POSTGRES_USER ]
then
 echo "$0: script must be runned as user $POSTGRES_USER"
 exit 1
fi

echo 'Initializing tables in database ' $db_name
$PSQL -U $POSTGRES_USER -p $POSTGRES_PORT $db_name < $SCODOC_DIR/misc/createtables.sql


# Set DeptName in preferences:
echo "insert into sco_prefs (name, value) values ('DeptName', '"${DEPT}\'\) | $PSQL -U $POSTGRES_USER  -p $POSTGRES_PORT $db_name