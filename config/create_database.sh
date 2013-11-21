#!/bin/bash

# Create database for a ScoDoc instance
# This script must be executed as postgres user
#
# $db_name is passed ias an environment variable

source config.sh
source utils.sh

echo 'Creating postgresql database'

# ---
echo 'Creating postgresql database ' $db_name
createdb -E UTF-8  -p $POSTGRES_PORT -O $POSTGRES_USER $db_name

