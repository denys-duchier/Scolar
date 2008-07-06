
# Misc utilities for ScoDoc install shell scripts

to_lower() {
  echo $1 | tr "[:upper:]" "[:lower:]" 
} 

to_upper() {
  echo $1 | tr "[:lower:]" "[:upper:]" 
} 

check_uid_root() {
  if [ "$UID" != "0" ] 
  then
    echo "Erreur: le script $1 doit etre lance par root"
    exit 1
  fi
}

# --- Ensure postgres user www-data exists
init_postgres_user() { # run as root
  if [ -z $(echo "select usename from pg_user;" | su -c "$PSQL -d template1  -p $POSTGRES_PORT" $POSTGRES_SUPERUSER | grep $POSTGRES_USER) ]
  then
   # add database user
   echo "Creating postgresql user $POSTGRES_USER"
   su -c "createuser  -p $POSTGRES_PORT --no-superuser --no-createdb --no-adduser --no-createrole $POSTGRES_USER" $POSTGRES_SUPERUSER
  fi
}

# XXX inutilise 
gen_passwd() { 
  PASSWORD_LENGTH="8"
  ALLOWABLE_ASCII="~@#$%^&*()_+=-?><0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz"
  SEED=$(head -c4 /dev/urandom | od -t u4 | awk '{ print $2 }')
  RANDOM=$SEED
  n=1
  password=""
  while [ "$n" -le "$PASSWORD_LENGTH" ]
  do
    password="$password${ALLOWABLE_ASCII:$(($RANDOM%${#ALLOWABLE_ASCII})):1}"
  n=$((n+1))
  done
  echo $password
}
