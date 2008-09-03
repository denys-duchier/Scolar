"""
    Some utilities used by upgrade scripts
"""
import sys, os, psycopg, glob

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

def check_field(cnx, table, field, sql_create_commands):
    "if field does not exists in table, run sql commands"
    if not field_exists(cnx, table, field):
        log('missing field %s in table %s: trying to create it'%(field,table))
        cursor = cnx.cursor()
        try:
            for cmd in sql_create_commands:
                log('executing SQL: %s' % cmd)
                cursor.execute(cmd)
                cnx.commit()
        except:
            cnx.rollback()
            log('check_field: failure. Aborting transaction.')
        if not field_exists(cnx, table, field):
            log('check_field: new field still missing !')
            raise Exception('database configuration problem')
        else:
            log('field %s added successfully.' % field)
