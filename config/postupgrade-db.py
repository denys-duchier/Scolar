#!/usr/bin/env python

"""
ScoDoc post-upgrade script: databases housekeeping

This script is runned by upgrade.sh after each SVN update.

Runned as "www-data" with Zope shutted down and postgresql up.


Useful to update databse schema (eg add new tables or columns to 
existing scodoc instances).

E. Viennet, june 2008
"""

from scodocutils import *

for dept in get_depts():
    log('\nChecking database for dept %s' % dept)
    cnx = psycopg.connect( get_dept_cnx_str(dept) )
    cursor = cnx.cursor()
    # Apply upgrades:
    
    # SVN 564 -> 565
    # add resp_can_edit to notes_formsemestre:
    check_field(cnx, 'notes_formsemestre', 'resp_can_edit',
                ['alter table notes_formsemestre add column resp_can_edit int default 0',
                 'update notes_formsemestre set resp_can_edit=0'])

    # SVN 580 -> 581
    # add resp_can_change_ens to notes_formsemestre:
    check_field(cnx, 'notes_formsemestre', 'resp_can_change_ens',
                ['alter table notes_formsemestre add column resp_can_change_ens int default 1',
                 'update notes_formsemestre set resp_can_change_ens=1'])
    
    # SVN 651
    # Nouvelles donnees d'admission
    check_field(cnx, 'admissions', 'codelycee',
                ['alter table admissions add column codelycee text',
                 ])
    check_field(cnx, 'admissions', 'codepostallycee',
                ['alter table admissions add column codepostallycee text',
                 ])
    
    # New preferences system
    check_field(cnx, 'sco_prefs', 'formsemestre_id',
                ["alter table sco_prefs add column pref_id text DEFAULT notes_newid('PREF'::text) UNIQUE NOT NULL",
                 "update sco_prefs set pref_id=oid",
                 "alter table sco_prefs add column formsemestre_id text default NULL",
                 "alter table sco_prefs drop CONSTRAINT sco_prefs_pkey",
                 "alter table sco_prefs add unique( name, formsemestre_id)",
                 # copie anciennes prefs:
                 "insert into sco_prefs (name, value, formsemestre_id) select 'left_margin', left_margin, formsemestre_id from notes_formsemestre_pagebulletin",
                 "insert into sco_prefs (name, value, formsemestre_id) select 'top_margin', top_margin, formsemestre_id from notes_formsemestre_pagebulletin",
                 "insert into sco_prefs (name, value, formsemestre_id) select 'right_margin', right_margin, formsemestre_id from notes_formsemestre_pagebulletin",
                 "insert into sco_prefs (name, value, formsemestre_id) select 'bottom_margin', bottom_margin, formsemestre_id from notes_formsemestre_pagebulletin",
                 "insert into sco_prefs (name, value, formsemestre_id) select 'bul_title', title, formsemestre_id from notes_formsemestre_pagebulletin",
                 "insert into sco_prefs (name, value, formsemestre_id) select 'bul_intro_mail', intro_mail, formsemestre_id from notes_formsemestre_pagebulletin",
                 "drop table notes_formsemestre_pagebulletin",
                 # anciens champs de formsemestre:
                 "insert into sco_prefs (name, value, formsemestre_id) select 'bul_show_abs', gestion_absence, formsemestre_id from notes_formsemestre",
                 "alter table notes_formsemestre drop column gestion_absence",
                 
                 "insert into sco_prefs (name, value, formsemestre_id) select 'bul_show_decision', bul_show_decision, formsemestre_id from notes_formsemestre",
                 "alter table notes_formsemestre drop column bul_show_decision",
                 
                 "insert into sco_prefs (name, value, formsemestre_id) select 'bul_show_uevalid', bul_show_uevalid, formsemestre_id from notes_formsemestre",
                 "alter table notes_formsemestre drop column bul_show_uevalid",
                 
                 "insert into sco_prefs (name, value, formsemestre_id) select 'bul_show_codemodules', bul_show_codemodules, formsemestre_id from notes_formsemestre",
                 "alter table notes_formsemestre drop column bul_show_codemodules",

                 "insert into sco_prefs (name, value, formsemestre_id) select 'bul_show_rangs', bul_show_rangs, formsemestre_id from notes_formsemestre",
                 "alter table notes_formsemestre drop column bul_show_rangs",
                 
                 "insert into sco_prefs (name, value, formsemestre_id) select 'bul_show_ue_rangs', bul_show_ue_rangs, formsemestre_id from notes_formsemestre",
                 "alter table notes_formsemestre drop column bul_show_ue_rangs",
                 
                 "insert into sco_prefs (name, value, formsemestre_id) select 'bul_show_mod_rangs', bul_show_mod_rangs, formsemestre_id from notes_formsemestre",
                 "alter table notes_formsemestre drop column bul_show_mod_rangs",
                 ])
    # fixed previous bug (misspelled pref)
    cursor.execute("update sco_prefs set name = 'bul_show_codemodules' where name = 'bul_showcodemodules'")

    # billets d'absences
    check_table( cnx, 'billet_absence', [
            """CREATE SEQUENCE notes_idgen_billets;""",
            """CREATE FUNCTION notes_newid_billet( text ) returns text as '
	select $1 || to_char(  nextval(''notes_idgen_billets''), ''FM999999999'' ) 
	as result;
	' language SQL;
""",
            """CREATE TABLE billet_absence (
    billet_id text DEFAULT notes_newid_billet('B'::text) NOT NULL,
    etudid text NOT NULL,
    abs_begin timestamp with time zone,
    abs_end  timestamp with time zone,
    description text, -- "raison" de l'absence
    etat integer default 0 -- 0 new, 1 processed    
) WITH OIDS;
"""] )
    # description absence
    check_field(cnx, 'absences', 'description',
                ['alter table absences add column description text'
                 ])
    check_field(cnx, 'absences', 'entry_date',
                ['alter table absences add column entry_date timestamp with time zone DEFAULT now()'
                 ])
    check_field(cnx, 'billet_absence', 'entry_date',
                ['alter table billet_absence add column entry_date timestamp with time zone DEFAULT now()'
                 ])
    # Nouvelles preferences pour bulletins PDF: migre bul_show_chiefDept
    cursor.execute("update sco_prefs set name = 'bul_show_sig_right' where name = 'bul_show_chiefDept'")
    cursor.execute("insert into sco_prefs (name, value, formsemestre_id) select 'bul_show_sig_left', value, formsemestre_id from sco_prefs where name = 'bul_show_sig_right'")
    # date et lieu naissance (pour IFAG Sofia)
    check_field(cnx, 'identite', 'date_naissance',
                ['alter table identite add column date_naissance date',
                 "update identite set date_naissance=to_date(to_char( annee_naissance, 'FM9999') || '-01-01', 'YYYY-MM-DD')",
                 'alter table identite drop column annee_naissance'
                 ])
    check_field(cnx, 'identite', 'lieu_naissance',
                ['alter table identite add column lieu_naissance text'
                 ])
    
    # Add here actions to performs after upgrades:

    cnx.commit()
    cnx.close()


# Base utilisateurs:
log('\nChecking users database')
cnx = psycopg.connect( get_users_cnx_str() )
cursor = cnx.cursor()
check_field(cnx, 'sco_users', 'passwd_temp',
            ['alter table sco_users add column passwd_temp int default 0',
             'update sco_users set passwd_temp=0' ])
cnx.commit()
cnx.close()

# The end.
sys.exit(0)
