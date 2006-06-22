# -*- mode: python -*-


import pdb,os,sys,psycopg
from notes_log import log
from sco_exceptions import *
from types import *
from cgi import escape

def quote_dict( d ):
    "quote all values in dict"
    for k in d.keys():
        v = d[k]
        if type(v) == StringType:
            d[k] = escape(v)

def unquote(s):
    "inverse of quote"
    # pas d'inverse de cgi.escape
    # ne traite que &
    return s.replace('&amp;', '&')

DB = psycopg

def DBInsertDict( cnx, table, vals, commit=0,convert_empty_to_nulls=1):
    "insert into table values in dict 'vals'"
    cursor = cnx.cursor()
    if convert_empty_to_nulls:
        for col in vals.keys():
            if vals[col] == '':
                vals[col] = None
    # open('/tmp/vals','a').write( str(vals) + '\n' )
    cols = vals.keys()
    colnames= ','.join(cols)
    fmt = ','.join([ '%%(%s)s' % col for col in cols ])
    #print 'insert into %s (%s) values (%s)' % (table,colnames,fmt)
    try:
        cursor.execute('insert into %s (%s) values (%s)' % (table,colnames,fmt),
                       vals )
    except:
        log('DBInsertDict: EXCEPTION !')
        log('DBInsertDict: table=%s, vals=%s' % (str(table),str(vals)))
        log('DBInsertDict: commit (exception)')
        cnx.commit() # get rid of this transaction
        raise        # and re-raise exception
    if commit:
        log('DBInsertDict: commit (requested)')
        cnx.commit()
    return cnx

def DBSelectArgs(cnx, table, vals, what=['*'], sortkey=None,
                  test='=', operator='and', distinct=True,
                  aux_tables = [], id_name=None ):
    """Select * from table where values match dict vals.
    Returns cnx, columns_names, list of tuples
    aux_tables = ( tablename, id_name )
    """
    cursor = cnx.cursor()
    if sortkey:
        orderby = ' order by ' + sortkey
    else:
        orderby = ''
    if distinct:
        distinct = ' distinct '
    else:
        distinct = ''
    operator = ' ' + operator + ' '
    # liste des tables (apres "from")
    tables = [table] + [ x[0] for x in aux_tables ]
    for i in range(len(tables)):
        tables[i] = '%s T%d' % (tables[i], i)
    tables = ', '.join(tables)
    # condition (apres "where")
    if vals or aux_tables:
        cond = ' where '
    else:
        cond = ''
    i=1
    cl=[]
    for (aux_tab, aux_id) in aux_tables:
        cl.append( 'T0.%s = T%d.%s' % (id_name, i, aux_id) )
        i = i + 1
    cond += ' and '.join(cl)
    if vals:
        if aux_tables: # paren
            cond +=  ' AND ( '
        cond += operator.join( ['T0.%s%s%%(%s)s' %(x,test,x) for x in vals.keys() if vals[x] != None ])
        cnuls = ' and '.join( ['%s is NULL' % x for x in vals.keys() if vals[x] is None ])
        if cnuls:
            cond = cond + ' and ' + cnuls
        # close paren
        if aux_tables:
            cond += ') '
    #
    req = 'select ' +distinct+ ', '.join(what) + ' from '+tables+cond+orderby
    #open('/tmp/select.log','a').write( req % vals + '\n' )
    cursor.execute( req, vals )
    return [ x[0] for x in cursor.description ], cursor.fetchall()

def DBUpdateArgs(cnx, table, vals, where=None, commit=False,
                  convert_empty_to_nulls=1 ):
    if not vals or where is None:
        return
    cursor = cnx.cursor()
    if convert_empty_to_nulls:
        for col in vals.keys():
            if vals[col] == '':
                vals[col] = None
    s = ', '.join([ '%s=%%(%s)s' % (x,x) for x in vals.keys() ])
    try:
        req = 'update ' + table + ' set ' + s + ' where ' + where
        cursor.execute( req, vals )
        #open('/tmp/toto','a').write('req=%s\n'%req)
        #open('/tmp/toto','a').write('vals=%s\n'%vals)
    except:
        cnx.commit() # get rid of this transaction
        raise        # and re-raise exception
    if commit:
        cnx.commit()

def DBDelete(cnx, table, colid, val, commit=False ):
    cursor = cnx.cursor()
    try:
        cursor.execute('delete from ' + table + ' where %s=%%(%s)s'%(colid,colid),
                       { colid: val })
    except:
        cnx.commit() # get rid of this transaction
        raise        # and re-raise exception
    if commit:
        cnx.commit()

# --------------------------------------------------------------------

class AccessDenied(Exception):
    pass

GrantAccess = None

class EditableTable:
    """ --- generic class: SQL table with create/edit/list/delete
    """
    def __init__(self, table_name, id_name,
                 dbfields,
                 sortkey = None,
                 output_formators = {}, input_formators = {},
                 aux_tables = [],
                 convert_null_outputs_to_empty=True,
                 callback_on_write = None,
                 allow_set_id = False
                 ):
        self.table_name = table_name
        self.id_name = id_name
        self.aux_tables = aux_tables
        self.dbfields = dbfields
        self.sortkey = sortkey
        self.output_formators = output_formators
        self.input_formators = input_formators
        self.convert_null_outputs_to_empty = convert_null_outputs_to_empty
        self.callback_on_write = callback_on_write # called after each modification
        self.allow_set_id = allow_set_id
    
    def create(self, cnx, args, has_uniq_values=True):
        "create object in table"        
        vals = dictfilter(args, self.dbfields)        
        if vals.has_key(self.id_name) and not self.allow_set_id:
            del vals[self.id_name]        
        quote_dict(vals) # quote all HTML markup
        
        # format value
        for title in vals.keys():
            if self.input_formators.has_key(title):
                vals[title] = self.input_formators[title](vals[title])
        DBInsertDict(cnx, self.table_name, vals, commit=True )
        if has_uniq_values:
            # get new id (assume all tuples are UNIQUE !)
            titles, res = DBSelectArgs(cnx,
                self.table_name, vals, what=[self.id_name] )
            if self.callback_on_write:
                self.callback_on_write()
            if len(res) != 1:
                # BUG !
                log('create: BUG table_name=%s args=%s' % (self.table_name,str(args)))
                assert len(res) == 1, 'len(res) = %d != 1 !' % len(res)
            return res[0][0]
    
    def delete(self, cnx, oid, commit=True ):
        # get info
        titles, res = DBSelectArgs( cnx, self.table_name, {self.id_name : oid} )
        d = {}
        for i in range(len(titles)):
            d[titles[i]] = res[0][i]
        DBDelete(cnx, self.table_name, self.id_name, oid, commit=commit )
        if self.callback_on_write:
            self.callback_on_write()
    
    def list(self, cnx, args={}, operator = 'and', test='=', sortkey=None,
             disable_formatting=False ):
        "returns list of dicts"
        vals = dictfilter(args, self.dbfields)
        if not sortkey:
            sortkey = self.sortkey
        titles, res = DBSelectArgs( cnx, self.table_name, 
                                    vals, sortkey=sortkey,
                                    test=test, operator=operator,
                                    aux_tables=self.aux_tables,
                                    id_name=self.id_name)
        R = []
        for r in res:
            d = {}
            for i in range(len(titles)):
                v = r[i]
                if self.convert_null_outputs_to_empty:
                    if v is None:
                        v = ''
                # format value
                if not disable_formatting and self.output_formators.has_key(titles[i]):
                    try: # XXX debug "isodate"
                        v = self.output_formators[titles[i]](v)
                    except:
                        log('*** list: vars=%s' % str(vars()))
                        log('*** list: titles=%s i=%s v=%s' % (str(titles),str(i),str(v)))
                        log('*** list: res=%s' % str(res))
                        raise
                d[titles[i]] = v
            R.append(d)
        return R

    def edit(self, cnx, args):
        """Change fields"""
        vals = dictfilter(args, self.dbfields)
        quote_dict(vals) # quote HTML
        # format value
        for title in vals.keys():
            if self.input_formators.has_key(title):
                vals[title] = self.input_formators[title](vals[title])                
        
        DBUpdateArgs( cnx, self.table_name, vals,
                      where="%s=%%(%s)s" % (self.id_name,self.id_name),
                      commit=True )
        if self.callback_on_write:
            self.callback_on_write()


def dictfilter( d, fields ):
    # returns a copy of d with only keys listed in "fields" and non null values
    r = {}
    for f in fields:
        if d.has_key(f) and d[f] != None and d[f] != '':
            r[f] = d[f]
    return r

# --------------------------------------------------------------------
# --- Misc Tools

def DateDMYtoISO(dmy):
    "convert date string from french format to ISO"
    if not dmy:
        return None
    t = dmy.split('/')
    if len(t) != 3:
        raise ScoValueError('Format de date (j/m/a) invalide: "%s"' % str(dmy))
    day, month, year = t
    year = int(year)
    month = int(month)
    day = int(day)
    # accept years YYYY or YY, uses 1970 as pivot
    if year < 1970:
        if year > 100:
            raise ScoValueError('année invalide ! (%s)' % year)
        if year < 70:
            year = year + 2000
        else:
            year = year + 1900
    if month < 1 or month > 12:
        raise ScoValueError('mois de la date invalide ! (%s)' % month)
    # compute nb of day in month:
    mo = month
    if mo > 7:
        mo = mo+1
    if mo % 2:
        MonthNbDays = 31
    elif mo == 2:
        if year % 4 == 0 and (year % 100 <> 0 or year % 400 == 0):
            MonthNbDays = 29 # leap
        else:
            MonthNbDays = 28
    else:
        MonthNbDays = 30    
    if day < 1 or day > MonthNbDays:
        raise ScoValueError('jour de la date invalide ! (%s)'% day)
    return '%04d-%02d-%02d' % (year, month, day)

def DateISOtoDMY(isodate):    
    if not isodate:
        return ''
    # si isodate est une instance de DateTime !
    try:
        isodate = str(isodate.date)
    except:
        pass
    # drop time from isodate and split
    t = str(isodate).split()[0].split('-')
    if len(t) != 3:
        # XXX recherche bug intermittent assez etrange
        log('*** DateISOtoDMY: invalid isodate %s'%str(isodate))
        raise NoteProcessError('invalid isodate: "%s"' % str(isodate))
    year, month, day = t
    year = int(year)
    month = int(month)
    day = int(day)
    if month < 1 or month > 12:
        raise ValueError, 'invalid month'
    if day < 1 or day > 31:
        raise ValueError, 'invalid day'
    return '%02d/%02d/%04d' % (day,month,year)

def TimetoISO8601(t):
    "convert time string to ISO 8601 (allow 16:03, 16h03, 16)"
    t = t.strip().upper().replace('H', ':')
    if t and t.count(':') == 0 and len(t) < 3:
        t = t + ':00'
    return t


def TimefromISO8601(t):
    "convert time string from ISO 8601 to our display format"
    if not t:
        return t
    fs = str(t).split(':') 
    return fs[0] + 'h' + fs[1] # discard seconds

def float_null_is_zero(x):
    if x is None or x == '':
        return 0.
    else:
        return float(x)

def int_null_is_zero(x):
    if x is None or x == '':
        return 0
    else:
        return int(x)
    
# post filtering
#
def UniqListofDicts( L, key ):
    """L is a list of dicts.
    Remove from L all items which share the same key/value
    """
    # well, code is simpler than documentation:
    d={}
    for item in L:
        d[item[key]] = item
    return d.values()
