"""
    Some utilities used by upgrade scripts
"""
import sys, os, psycopg, glob, subprocess, traceback, time

sys.path.append('..')

def log(msg):
    sys.stdout.flush()
    sys.stderr.write(msg+'\n')
    sys.stderr.flush()

SCODOC_DIR=os.environ.get('SCODOC_DIR', '')
if not SCODOC_DIR:
    log('Error: environment variable SCODOC_DIR is not defined')
    sys.exit(1)


def get_dept_cnx_str(dept):
    "db cnx string for dept"
    f = os.path.join(SCODOC_DIR,'config/depts',dept+'.cfg')
    try:
        return open(f).readline().strip()
    except:
        log("Error: can't read connexion string for dept %s" % dept)
        log("(tried to open %s)" % f)
        raise

def get_users_cnx_str():
    "db cnx string for users database (used only during upgrades to modify db schema)"
    # uses default in sco_utils
    # For customized installs, define the value here (used only during upgrades)
    import sco_utils 
    return sco_utils.SCO_DEFAULT_SQL_USERS_CNX

def get_depts():
    "list of defined depts"    
    files=glob.glob(SCODOC_DIR+'/config/depts/*.cfg')
    return [ os.path.splitext(os.path.split(f)[1])[0] for f in files ]

def field_exists(cnx, table, field):
    "true if field exists in sql table"
    cursor = cnx.cursor()
    cursor.execute("SELECT column_name FROM information_schema.columns WHERE table_name = '%s'" % table)
    r = cursor.fetchall()
    fields = [ f[0] for f in r ]
    return field in fields

def _run_sql( sql, cnx ):
    cursor = cnx.cursor()
    error = False
    try:
        for cmd in sql:
            log('executing SQL: %s' % cmd)
            cursor.execute(cmd)
            cnx.commit()
    except:
        cnx.rollback()
        log('check_field: failure. Aborting transaction.')
        error = True
        traceback.print_exc()    
    return error

def check_field(cnx, table, field, sql_create_commands):
    "if field does not exists in table, run sql commands"
    if not field_exists(cnx, table, field):
        log('missing field %s in table %s: trying to create it'%(field,table))
        error = _run_sql( sql_create_commands, cnx )
        if not field_exists(cnx, table, field):
            log('check_field: new field still missing !')
            raise Exception('database configuration problem')
        elif error:
            log('\n\nAN UNEXPECTED ERROR OCCURRED WHILE UPGRADING DATABASE !\n\n')
        else:
            log('field %s added successfully.' % field)


def table_exists(cnx, table):
    "true if SQL table exists"
    cursor = cnx.cursor()
    cursor.execute("SELECT table_name FROM information_schema.tables where table_name='%s'" % table)
    r = cursor.fetchall()    
    return len(r) > 0

def check_table(cnx, table, sql_create_commands):
    "if table does not exists in table, run sql commands"
    if not table_exists(cnx, table):
        log('missing table %s: trying to create it'%(table))
        error = _run_sql( sql_create_commands, cnx )
        if not table_exists(cnx, table):
            log('check_table: new table still missing !')
            raise Exception('database configuration problem')
        elif error:
            log('\n\nAN UNEXPECTED ERROR OCCURRED WHILE UPGRADING DATABASE !\n\n')
        else:
            log('table %s added successfully.' % table)

def sequence_exists(cnx, seq_name):
    "true if SQL sequence exists"
    cursor = cnx.cursor()
    cursor.execute("""SELECT relname FROM pg_class
     WHERE relkind = 'S' and relname = '%s'
     AND relnamespace IN (
        SELECT oid FROM pg_namespace WHERE nspname NOT LIKE 'pg_%%' AND nspname != 'information_schema'
     );
    """ % seq_name )
    r = cursor.fetchall()
    return len(r) > 0

def function_exists(cnx, func_name):
    "true if SQL function exists"
    cursor = cnx.cursor()
    cursor.execute("""SELECT routine_name FROM information_schema.routines
      WHERE specific_schema NOT IN ('pg_catalog', 'information_schema')
      AND type_udt_name != 'trigger' 
      AND routine_name = '%s';""" % func_name )
    r = cursor.fetchall()
    return len(r) > 0

