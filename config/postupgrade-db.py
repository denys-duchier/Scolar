#!/opt/zope213/bin/python
# -*- coding: utf-8 -*-

"""
ScoDoc post-upgrade script: databases housekeeping

This script is runned by upgrade.sh after each SVN update.

Runned as "www-data" with Zope shutted down and postgresql up.


Useful to update database schema (eg add new tables or columns to 
existing scodoc instances).

E. Viennet, june 2008, sept 2013
"""

from scodocutils import *

for dept in get_depts():
    log('\nChecking database for dept %s' % dept)
    try:
        cnx = psycopg2.connect( get_dept_cnx_str(dept) )
    except:
        log('\n*** Error: departement %s not upgraded ! ***\n' % dept)
        continue
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
    if not sequence_exists(cnx, 'notes_idgen_billets'):
        log('creating sequence notes_idgen_billets')
        cursor.execute('CREATE SEQUENCE notes_idgen_billets;')
    
    if not function_exists(cnx, 'notes_newid_billet'):
        log('creating function notes_newid_billet')
        cursor.execute("""CREATE FUNCTION notes_newid_billet( text ) returns text as '
	select $1 || to_char(  nextval(''notes_idgen_billets''), ''FM999999999'' ) 
	as result;
	' language SQL;""")
    
    check_table( cnx, 'billet_absence', [            
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
    # cursor.execute("insert into sco_prefs (name, value, formsemestre_id) select 'bul_show_sig_left', value, formsemestre_id from sco_prefs where name = 'bul_show_sig_right'")
    # date et lieu naissance (pour IFAG Sofia)
    check_field(cnx, 'identite', 'date_naissance',
                ['alter table identite add column date_naissance date',
                 "update identite set date_naissance=to_date(to_char( annee_naissance, 'FM9999') || '-01-01', 'YYYY-MM-DD')",
                 'alter table identite drop column annee_naissance'
                 ])
    check_field(cnx, 'identite', 'lieu_naissance',
                ['alter table identite add column lieu_naissance text'
                 ])
    # justification billets:
    check_field(cnx, 'billet_absence', 'justified', 
                [ 'alter table billet_absence add column justified integer default 0',
                  'update billet_absence set justified=0'
                  ])
    
    # ----------------------- New groups
    # 1- Create new tables
    check_table( cnx, 'partition', [
            """CREATE TABLE partition(
       partition_id text default notes_newid2('P') PRIMARY KEY,
       formsemestre_id text REFERENCES notes_formsemestre(formsemestre_id),
       partition_name text, -- "TD", "TP", ...
       compute_ranks integer default 1, -- calcul rang etudiants dans les groupes
       numero SERIAL, -- ordre de presentation
       UNIQUE(formsemestre_id,partition_name)
) WITH OIDS;
"""] )
    check_table( cnx, 'group_descr', [
            """CREATE TABLE group_descr (
       group_id text default notes_newid2('G') PRIMARY KEY,
       partition_id text REFERENCES partition(partition_id),
       group_name text, -- "A", "C2", ...
       UNIQUE(partition_id, group_name)     
) WITH OIDS;
"""] )
    check_table( cnx, 'group_membership', [
            """CREATE TABLE group_membership(
       group_membership_id text default notes_newid2('GM') PRIMARY KEY,
       etudid text REFERENCES identite(etudid),       
       group_id text REFERENCES group_descr(group_id),
       UNIQUE(etudid, group_id)
) WITH OIDS;
"""] )

    # 2- For each sem, create 1 to 4 partitions: all, TD (if any), TP, TA
    # Here we have to deal with plain SQL, nasty...
    if field_exists(cnx, 'notes_formsemestre_inscription', 'groupetd'):
        # Some very old stduents didn't have addresses: it's now mandatory
        cursor.execute("insert into adresse (etudid) select etudid from identite i except select etudid from adresse")
        #
        cursor.execute("SELECT formsemestre_id from notes_formsemestre")
        formsemestre_ids = [ x[0] for x in cursor.fetchall() ]
        for formsemestre_id in formsemestre_ids:
            # create "all" partition (with empty name)
            cursor.execute("INSERT into partition (formsemestre_id, compute_ranks) VALUES (%(formsemestre_id)s, 1)", {'formsemestre_id' : formsemestre_id } )
            cursor.execute("select partition_id from partition where oid=%(oid)s", { 'oid' : cursor.lastoid() })
            partition_id = cursor.fetchone()[0]
            # create group "all" (without name)
            cursor.execute("INSERT into group_descr (partition_id) VALUES (%(pid)s)", { 'pid' : partition_id } )
            cursor.execute("SELECT group_id from group_descr where oid=%(oid)s", { 'oid' : cursor.lastoid() })
            group_id = cursor.fetchone()[0]
            # inscrit etudiants:
            cursor.execute("INSERT into group_membership (etudid, group_id) SELECT etudid, %(group_id)s from notes_formsemestre_inscription where formsemestre_id=%(formsemestre_id)s", { 'group_id' : group_id, 'formsemestre_id' : formsemestre_id } )
            
            # create TD, TP, TA
            cursor.execute("SELECT distinct(groupetd) from notes_formsemestre_inscription where formsemestre_id=%(formsemestre_id)s", { 'formsemestre_id' : formsemestre_id } )
            groupetds = [ x[0] for x in cursor.fetchall() if x[0] ]
            if len(groupetds) > 1 or (len(groupetds)==1 and groupetds[0] != 'A'):
                # TD : create partition
                cursor.execute("SELECT * from notes_formsemestre where formsemestre_id=%(formsemestre_id)s", { 'formsemestre_id' : formsemestre_id } )
                nomgroupetd = cursor.dictfetchone()['nomgroupetd']
                if not nomgroupetd: # pas de nom ??? on invente un nom stupide et unique
                    nomgroupetd = 'TD_'+str(time.time()).replace('.','')[-3:]
                cursor.execute("INSERT into partition (formsemestre_id, partition_name) VALUES (%(formsemestre_id)s,%(nomgroupetd)s)", { 'formsemestre_id' : formsemestre_id, 'nomgroupetd' : nomgroupetd } )
                cursor.execute("select partition_id from partition where oid=%(oid)s", { 'oid' : cursor.lastoid() })
                partition_id = cursor.fetchone()[0]
                # create groups
                for groupetd in groupetds:
                    cursor.execute("INSERT into group_descr (partition_id, group_name) VALUES (%(pid)s, %(group_name)s)", { 'pid' : partition_id, 'group_name' : groupetd } )
                    cursor.execute("SELECT group_id from group_descr where oid=%(oid)s", { 'oid' : cursor.lastoid() })
                    group_id = cursor.fetchone()[0]
                    # inscrit les etudiants
                    cursor.execute("INSERT into group_membership (etudid, group_id) SELECT etudid, %(group_id)s from notes_formsemestre_inscription where formsemestre_id=%(formsemestre_id)s and groupetd=%(groupetd)s", { 'group_id' : group_id, 'formsemestre_id' : formsemestre_id, 'groupetd' : groupetd } )
            # TA
            cursor.execute("SELECT distinct(groupeanglais) from notes_formsemestre_inscription where formsemestre_id=%(formsemestre_id)s", { 'formsemestre_id' : formsemestre_id } )
            groupetds = [ x[0] for x in cursor.fetchall() if x[0] ]            
            if len(groupetds) > 0:
                # TA : create partition
                cursor.execute("SELECT * from notes_formsemestre where formsemestre_id=%(formsemestre_id)s", { 'formsemestre_id' : formsemestre_id } )
                nomgroupetd = cursor.dictfetchone()['nomgroupeta']
                if not nomgroupetd: # pas de nom ??? on invente un nom stupide et unique
                    nomgroupetd = 'TA_'+str(time.time()).replace('.','')[-3:]
                cursor.execute("INSERT into partition (formsemestre_id, partition_name) VALUES (%(formsemestre_id)s,%(nomgroupeta)s)", { 'formsemestre_id' : formsemestre_id, 'nomgroupeta' : nomgroupetd } )
                cursor.execute("select partition_id from partition where oid=%(oid)s", { 'oid' : cursor.lastoid() })
                partition_id = cursor.fetchone()[0]
                # create groups
                for groupetd in groupetds:
                    cursor.execute("INSERT into group_descr (partition_id, group_name) VALUES (%(pid)s, %(group_name)s)", { 'pid' : partition_id, 'group_name' : groupetd } )
                    cursor.execute("SELECT group_id from group_descr where oid=%(oid)s", { 'oid' : cursor.lastoid() })
                    group_id = cursor.fetchone()[0]
                    # inscrit les etudiants
                    cursor.execute("INSERT into group_membership (etudid, group_id) SELECT etudid, %(group_id)s from notes_formsemestre_inscription where formsemestre_id=%(formsemestre_id)s and groupeanglais=%(groupetd)s", { 'group_id' : group_id, 'formsemestre_id' : formsemestre_id, 'groupetd' : groupetd } )
            
            # TP
            cursor.execute("SELECT distinct(groupetp) from notes_formsemestre_inscription where formsemestre_id=%(formsemestre_id)s", { 'formsemestre_id' : formsemestre_id } )
            groupetds = [ x[0] for x in cursor.fetchall() if x[0] ]
            if len(groupetds) > 0:
                # TP : create partition
                cursor.execute("SELECT * from notes_formsemestre where formsemestre_id=%(formsemestre_id)s", { 'formsemestre_id' : formsemestre_id } )
                nomgroupetd = cursor.dictfetchone()['nomgroupetp']
                if not nomgroupetd: # pas de nom ??? on invente un nom stupide et unique
                    nomgroupetd = 'TP_'+str(time.time()).replace('.','')[-3:]
                cursor.execute("INSERT into partition (formsemestre_id, partition_name) VALUES (%(formsemestre_id)s,%(nomgroupeta)s)", { 'formsemestre_id' : formsemestre_id, 'nomgroupeta' : nomgroupetd } )
                cursor.execute("select partition_id from partition where oid=%(oid)s", { 'oid' : cursor.lastoid() })
                partition_id = cursor.fetchone()[0]
                # create groups
                for groupetd in groupetds:
                    cursor.execute("INSERT into group_descr (partition_id, group_name) VALUES (%(pid)s, %(group_name)s)", { 'pid' : partition_id, 'group_name' : groupetd } )
                    cursor.execute("SELECT group_id from group_descr where oid=%(oid)s", { 'oid' : cursor.lastoid() })
                    group_id = cursor.fetchone()[0]
                    # inscrit les etudiants
                    cursor.execute("INSERT into group_membership (etudid, group_id) SELECT etudid, %(group_id)s from notes_formsemestre_inscription where formsemestre_id=%(formsemestre_id)s and groupetp=%(groupetd)s", { 'group_id' : group_id, 'formsemestre_id' : formsemestre_id, 'groupetd' : groupetd } )

        # 3- Suppress obsolete fields
        cursor.execute( """alter table notes_formsemestre drop column nomgroupetd""" ) 
        cursor.execute( """alter table notes_formsemestre drop column nomgroupetp""" ) 
        cursor.execute( """alter table notes_formsemestre drop column nomgroupeta""" )
        
        cursor.execute( """alter table notes_formsemestre_inscription drop column groupetd""" )
        cursor.execute( """alter table notes_formsemestre_inscription drop column groupetp""" )
        cursor.execute( """alter table notes_formsemestre_inscription drop column groupeanglais""" )
    # ----------------------- /New groups

    # Add moy_ue to validations:
    check_field(cnx, 'scolar_formsemestre_validation', 'moy_ue',
                ['alter table scolar_formsemestre_validation add column moy_ue real',
                 ])
    # Add photo_filename
    check_field(cnx, 'identite', 'photo_filename',
                ['alter table identite add column photo_filename text',
                 ])
    # Add module's ECTS
    check_field(cnx, 'notes_modules', 'ects',
                ['alter table notes_modules add column ects real',
                 ])
    # Add "statut" to identite (default to NULL)
    check_field(cnx, 'identite', 'statut',
                ['alter table identite add column statut text',
                 ])
    # Add user-defined expressions
    check_field(cnx, 'notes_moduleimpl', 'computation_expr',
                ['alter table notes_moduleimpl add column computation_expr text'])
    # Add semestre_id to scolar_formsemestre_validation
    check_field(cnx, 'scolar_formsemestre_validation', 'semestre_id',
                ['alter table scolar_formsemestre_validation add column semestre_id int'])

    # Add 
    check_table( cnx, 'absences_notifications', [ """
     CREATE TABLE absences_notifications (
       etudid text NOT NULL,
       notification_date timestamp with time zone DEFAULT now(),
       email text NOT NULL,
       nbabs integer,
       nbabsjust integer    
      ) WITH OIDS;
    """] )
    # rename old preference "send_mail_absence_to_chef"
    cursor.execute("update sco_prefs set name = 'abs_notify_chief' where name = 'send_mail_absence_to_chef'")
    
    check_table( cnx, 'notes_formsemestre_ue_computation_expr', [ """
     CREATE TABLE notes_formsemestre_ue_computation_expr (
	notes_formsemestre_ue_computation_expr_id text default notes_newid('UEXPR') PRIMARY KEY,
	formsemestre_id text REFERENCES notes_formsemestre(formsemestre_id),
	ue_id  text REFERENCES notes_ue(ue_id),
	computation_expr text, -- formule de calcul moyenne
	UNIQUE(formsemestre_id, ue_id)
       ) WITH OIDS;
     """] )
    

    # add moduleimpl_id to absences:
    check_field(cnx, 'absences', 'moduleimpl_id',
                ['alter table absences add column moduleimpl_id text'])

    # add type_parcours
    check_field(cnx, 'notes_formations', 'type_parcours',
                ['alter table notes_formations add column type_parcours int DEFAULT 0',
                 'update notes_formations set type_parcours=0 where type_parcours is NULL'
                 ])
    
    # add etape_apo2
    check_field(cnx, 'notes_formsemestre', 'etape_apo2',
                ['alter table notes_formsemestre add column etape_apo2 text'])
    # add etape_apo3
    check_field(cnx, 'notes_formsemestre', 'etape_apo3',
                ['alter table notes_formsemestre add column etape_apo3 text'])
    # add etape_apo4
    check_field(cnx, 'notes_formsemestre', 'etape_apo4',
                ['alter table notes_formsemestre add column etape_apo4 text'])
    # add publish_incomplete
    check_field(cnx, 'notes_evaluation', 'publish_incomplete',
                ['alter table notes_evaluation add column  publish_incomplete int DEFAULT 0',
                 'update notes_evaluation set publish_incomplete=0 where publish_incomplete is NULL'
                 ])

    # add ens_can_create_eval to notes_formsemestre:
    check_field(cnx, 'notes_formsemestre', 'ens_can_edit_eval',
                ['alter table notes_formsemestre add column ens_can_edit_eval int default 0',
                 'update notes_formsemestre set ens_can_edit_eval=0'])

    # add evaluation_type
    check_field(cnx, 'notes_evaluation', 'evaluation_type',
                ['alter table notes_evaluation add column evaluation_type int DEFAULT 0',
                 'update notes_evaluation set evaluation_type=0 where evaluation_type is NULL'
                 ])
    
    # add partition rank on bulletins
    check_field(cnx, 'partition', 'bul_show_rank',
                ['alter table partition add column bul_show_rank int DEFAULT 0',
                 'update partition set bul_show_rank=0 where bul_show_rank is NULL'])
    # add formsemestre to abs notifications
    check_field(cnx, 'absences_notifications', 'formsemestre_id',
                ['alter table absences_notifications add column formsemestre_id text DEFAULT NULL',
                 ])
    # Add "debouche" to admission
    check_field(cnx, 'admissions', 'debouche',
                ['alter table admissions add column debouche text DEFAULT NULL',
                 # et en profite pour corrige le From par defaut des mails:
                 "update sco_prefs set value='noreply@univ-paris13.fr' where name='email_from_addr' and value='noreply'"
                 ])
    # Increase semestre indices
    for i in range(5,9):
        cursor.execute("SELECT * from notes_semestres where semestre_id=%(i)s", { 'i' : i } )
        r = cursor.fetchall()
        if not r:
            log("adding semestre_id %s" % i)
            cursor.execute("INSERT INTO notes_semestres (semestre_id) VALUES (%(i)s)", { 'i' : i } )
    # ECTS associes aux UE:
    check_field(cnx, 'notes_ue', 'ects',
                ['alter table notes_ue add column ects float DEFAULT NULL',
                 ])
    # Numeros des evaluations:
    check_field(cnx, 'notes_evaluation', 'numero',
                ['alter table notes_evaluation add column numero int DEFAULT 0',
                 ])
    # add nom_usuel to identite
    check_field(cnx, 'identite', 'nom_usuel',
                ['alter table identite add column nom_usuel text DEFAULT NULL',
                 ])
    # add type_admission
    check_field(cnx, 'admissions', 'type_admission',
                ['alter table admissions add column type_admission text DEFAULT NULL',
                 ])
    check_field(cnx, 'admissions', 'boursier_prec',
                ['alter table admissions add column boursier_prec integer default NULL',
                 ])
    # add modalites formation
    check_table( cnx, 'notes_form_modalites', [
        """CREATE TABLE notes_form_modalites (
    form_modalite_id text default notes_newid('Md') PRIMARY KEY,
    modalite text, -- la clef dans notes_formsemestre
    titre text, -- le nom complet de la modalite pour les documents scodoc
    numero SERIAL -- integer, ordre de presentation
     );""",
    """INSERT INTO notes_form_modalites (modalite, titre) VALUES ('', 'Autres formations');""",
    """INSERT INTO notes_form_modalites (modalite, titre) VALUES ('FI', 'Formation Initiale');""",
    """INSERT INTO notes_form_modalites (modalite, titre) VALUES ('FC', 'Formation Continue');""",
    """INSERT INTO notes_form_modalites (modalite, titre) VALUES ('FAP', 'Apprentissage');""",
    """INSERT INTO notes_form_modalites (modalite, titre) VALUES ('DEC', 'Formation Décalées');""",
    """INSERT INTO notes_form_modalites (modalite, titre) VALUES ('LIC', 'Licence');"""
    ] )
    # Add code_specialite
    check_field( cnx, 'notes_formations', 'code_specialite',
                 [ 'alter table notes_formations add column code_specialite text default NULL',
                   ])
    # Fix modules without codes
    cursor.execute("UPDATE notes_modules SET code = 'M_' || coalesce(upper(substring(titre from 1 for 2)), '') || '_' || coalesce(semestre_id,'0') where code is NULL;");
    
    # Add here actions to performs after upgrades:
    
    cnx.commit()
    cnx.close()


# Base utilisateurs:
log('\nChecking users database')
cnx = psycopg2.connect( get_users_cnx_str() )
cursor = cnx.cursor()
check_field(cnx, 'sco_users', 'passwd_temp',
            ['alter table sco_users add column passwd_temp int default 0',
             'update sco_users set passwd_temp=0' ])
check_field(cnx, 'sco_users', 'status',
            ["alter table sco_users add column status text default NULL"])
check_field(cnx, 'sco_users', 'date_expiration',
            ["alter table sco_users add column date_expiration date",
             "update sco_users set status=NULL where status=''" # fix a bug in previous update...
             ])
check_field(cnx, 'sco_users', 'login_edt',
            ["alter table sco_users add column login_edt text default NULL",
             ])
cnx.commit()
cnx.close()

# The end.
sys.exit(0)
