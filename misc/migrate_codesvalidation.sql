
INSERT INTO notes_semestres (semestre_id) VALUES (-1);

-- Ajout colonne code

CREATE SEQUENCE notes_idgen_fcod;
CREATE FUNCTION notes_newid_fcod( text ) returns text as '
	select $1 || to_char(  nextval(\'notes_idgen_fcod\'), \'FM999999999\' ) 
	as result;
	' language SQL;

ALTER TABLE notes_formations add column formation_code text;
ALTER TABLE notes_formations alter COLUMN formation_code SET DEFAULT notes_newid_fcod('FCOD');
UPDATE notes_formations set formation_code = DEFAULT;
ALTER TABLE notes_formations alter COLUMN formation_code SET NOT NULL;

ALTER TABLE notes_ue add column ue_code text;
ALTER TABLE notes_ue alter COLUMN ue_code SET DEFAULT notes_newid_fcod('UCOD');
UPDATE notes_ue set ue_code = DEFAULT;
ALTER TABLE notes_ue alter COLUMN ue_code SET NOT NULL;

ALTER TABLE notes_formsemestre add column gestion_semestrielle integer;
ALTER TABLE notes_formsemestre alter COLUMN gestion_semestrielle SET DEFAULT 0;
UPDATE notes_formsemestre set gestion_semestrielle = DEFAULT;


ALTER TABLE notes_formsemestre add column bul_bgcolor text;
ALTER TABLE notes_formsemestre alter COLUMN bul_bgcolor SET DEFAULT 'white';
UPDATE notes_formsemestre set bul_bgcolor = DEFAULT;


 +++ mettre a jour les codes des formations compatibles existantes.

-- fix owners
alter table scolar_autorisation_inscription OWNER to scotest;
alter table notes_idgen_fcod OWNER to scotest;
alter table notes_idgen_svalid OWNER to scotest;
alter table scolar_formsemestre_validation OWNER to scotest;

-- Passage de la table scolar_events a scolar_formsemestre_validation

-- VALID_SEM -> ADM
insert into scolar_formsemestre_validation 
            (etudid, formsemestre_id, code, assidu, event_date)
select etudid, formsemestre_id, 'ADM', 1, event_date
from scolar_events where event_type = 'VALID_SEM';

-- VALID_UE -> ADM ue
insert into scolar_formsemestre_validation 
            (etudid, formsemestre_id, ue_id, code, event_date)
select etudid, formsemestre_id, ue_id, 'ADM', event_date
from  scolar_events where event_type = 'VALID_UE';


XXX test requete


S2 2007  
formation_id=FORM1130
formsemestre_id=SEM4740
semestre_id=2
date_debut='2007-01-22'
K. Pach: etudid=10500853

Le SEM1784 est le S2 de 2006.

Liste de toutes les UE capitalisee pouvant servir dans le semestre
formsemestre_id:

select SFV.*, nue.ue_code from notes_ue nue, notes_formations nf, notes_formations nf2,
       scolar_formsemestre_validation SFV, notes_formsemestre sem
where nue.formation_id = nf.formation_id 
  and nf.formation_code = nf2.formation_code 
  and nf2.formation_id='FORM1130'
  and SFV.ue_id = nue.ue_id
  and SFV.code = 'ADM'
  and sem.formsemestre_id = SFV.formsemestre_id
  and sem.date_debut < '2007-01-22 '
  and sem.semestre_id = 2;

* Toutes les UE avec le même code formation que celui de formation_id:

select nue.* from notes_ue nue, notes_formations nf, notes_formations nf2
where nue.formation_id = nf.formation_id and nf.formation_code = nf2.formation_code and nf2.formation_id='FORM1703';

import pdb,os,sys,psycopg
DB = psycopg
cnx = DB.connect('host=localhost dbname=SCOGTR user=zopeuser password=')
cursor = cnx.cursor()
cursor.execute("select etudid, code, assidu from scolar_formsemestre_validation where formsemestre_id='SEM1784' and ue_id is NULL;")
r = cursor.dictfetchall()
print r
