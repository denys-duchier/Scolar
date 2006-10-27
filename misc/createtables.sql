
-- Creation des tables pour gestion notes
-- E. Viennet, Sep 2005



-- creation de la base:
--  en tant qu'utilisateur postgres
--     createuser --pwprompt scogea
--     createdb -E latin1 -O scogea SCOGEA "scolarite GEA"
--
--

-- generation des id
CREATE SEQUENCE notes_idgen;

CREATE FUNCTION notes_newid( text ) returns text as '
	select $1 || to_char(  nextval(\'notes_idgen\'), \'FM999999999\' ) 
	as result;
	' language SQL;

CREATE SEQUENCE notes_idgen2;

CREATE FUNCTION notes_newid2( text ) returns text as '
	select $1 || to_char(  nextval(\'notes_idgen2\'), \'FM999999999\' ) 
	as result;
	' language SQL;

CREATE SEQUENCE notes_idgen_etud;

CREATE FUNCTION notes_newid_etud( text ) returns text as '
	select $1 || to_char(  nextval(\'notes_idgen_etud\'), \'FM999999999\' ) 
	as result;
	' language SQL;



CREATE TABLE identite (
    etudid text DEFAULT notes_newid_etud('EID'::text) UNIQUE NOT NULL,
    nom text,
    prenom text,
    sexe text,
    annee_naissance integer,
    nationalite text,
    foto text,
    code_nip text UNIQUE, -- code NIP Apogee (may be null)
    code_ine text UNIQUE  -- code INE Apogee
);

CREATE TABLE adresse (
    adresse_id text DEFAULT notes_newid_etud('ADR'::text) NOT NULL,
    etudid text NOT NULL,
    email text,
    domicile text,
    codepostaldomicile text,
    villedomicile text,
    paysdomicile text,
    telephone text,
    telephonemobile text,
    fax text,
    typeadresse text DEFAULT 'domicile'::text NOT NULL,
    entreprise_id integer,
    description text
);

CREATE TABLE admissions (
    adm_id text DEFAULT notes_newid_etud('ADM'::text) NOT NULL,
    etudid text NOT NULL,
    annee integer,
    bac text,
    specialite text,
    annee_bac integer,
    math real,
    physique real,
    anglais real,
    francais real,
    rang integer,
    qualite real,
    rapporteur text,
    decision text,
    score real,
    commentaire text,
    nomlycee text,
    villelycee text
);

CREATE TABLE absences (
    etudid text NOT NULL,
    jour date,
    estabs boolean,
    estjust boolean,
    matin boolean
);

CREATE TABLE scolog (
    date timestamp without time zone DEFAULT now(),
    authenticated_user text,
    remote_addr text,
    remote_host text,
    method text,
    etudid character(32),
    msg text
);


CREATE TABLE etud_annotations (
    id integer DEFAULT nextval('serial'::text) NOT NULL,
    date timestamp without time zone DEFAULT now(),
    etudid character(32),
    author text,
    comment text,
    zope_authenticated_user text,
    zope_remote_addr text
);




--  ------------ ENTREPRISES ------------

CREATE TABLE entreprises (
    entreprise_id serial NOT NULL,
    nom text,
    adresse text,
    ville text,
    codepostal text,
    pays text,
    contact_origine text,
    secteur text,
    note text,
    privee text,
    localisation text,
    qualite_relation integer, -- -1 inconnue, 0, 25, 50, 75, 100
    plus10salaries integer,
    date_creation timestamp without time zone DEFAULT now()
);


CREATE TABLE entreprise_correspondant (
    entreprise_corresp_id serial NOT NULL,
    nom text,
    prenom text,
    fonction text,
    phone1 text,
    phone2 text,
    mobile text,
    mail1 text,
    mail2 text,
    note text,
    entreprise_id integer,
    civilite text,
    fax text
);


--
--

CREATE TABLE entreprise_contact (
    entreprise_contact_id serial NOT NULL,
    date date,
    type_contact text,
    entreprise_id integer,
    entreprise_corresp_id integer,
    etudid text,
    description text,
    enseignant text
);


--  ------------ NOTES ------------


-- Description generique d'un module (eg infos du PPN)

CREATE TABLE notes_formations (
	formation_id text default notes_newid('FORM') PRIMARY KEY,
	acronyme text NOT NULL, -- 'DUT R&T', 'LPSQRT', ...	
	titre text NOT NULL,     -- titre complet
	version integer default 1, -- version de la formation
	UNIQUE(acronyme,titre,version)
);

CREATE TABLE notes_ue (
	ue_id text default notes_newid('UE') PRIMARY KEY,
	formation_id text REFERENCES notes_formations(formation_id),
	acronyme text NOT NULL,
	numero int, -- ordre de presentation
	titre text,
	type  int DEFAULT 0 -- 0 normal, 1 "sport"
	-- XXX manque certainement des infos (semestre?)
);

CREATE TABLE notes_matieres (
	matiere_id text default notes_newid('MAT') PRIMARY KEY,
	ue_id text REFERENCES notes_ue(ue_id),
	titre text,
	numero int, -- ordre de presentation
	UNIQUE(ue_id,titre)
	-- XXX manque certainement des infos (coef pour gestion absences?)
);

CREATE TABLE notes_semestres (
	-- une bete table 1,2,3,4 pour l'instant fera l'affaire...
	semestre_id int PRIMARY KEY
);

INSERT INTO notes_semestres (semestre_id) VALUES (1);
INSERT INTO notes_semestres (semestre_id) VALUES (2);
INSERT INTO notes_semestres (semestre_id) VALUES (3);
INSERT INTO notes_semestres (semestre_id) VALUES (4);

CREATE TABLE notes_modules (
	module_id text default notes_newid('MOD') PRIMARY KEY,
	titre text,
	code  text,
	heures_cours real, 
	heures_td real, 
	heures_tp real,
	coefficient real, -- coef PPN
	ue_id text REFERENCES notes_ue(ue_id),
	formation_id text REFERENCES notes_formations(formation_id),
	matiere_id text  REFERENCES notes_matieres(matiere_id),
	semestre_id integer REFERENCES notes_semestres(semestre_id),
	numero int, -- ordre de presentation
	abbrev text -- nom court
);

-- Mise en oeuvre d'un semestre de formation
CREATE TABLE notes_formsemestre (
	formsemestre_id text default notes_newid('SEM') PRIMARY KEY,
	formation_id text REFERENCES notes_formations(formation_id),
	semestre_id int REFERENCES notes_semestres(semestre_id),
	titre text,
	date_debut date,
        date_fin   date,
	responsable_id text,
        gestion_absence integer default 1,
	bul_show_decision integer default 1,
	bul_show_uevalid integer default 1,
        etat integer default 1, -- 1 ouvert, 0 ferme
 	nomgroupetd text default 'TD',
 	nomgroupetp text default 'TP',
 	nomgroupeta text default 'langues',
	bul_show_codemodules integer default 1
);

-- Mise en oeuvre d'un module pour une annee/semestre
CREATE TABLE notes_moduleimpl (
	moduleimpl_id  text default notes_newid('MIP') PRIMARY KEY,
	module_id text REFERENCES notes_modules(module_id),
	formsemestre_id text REFERENCES notes_formsemestre(formsemestre_id),
	responsable_id text,
	UNIQUE(module_id,formsemestre_id) -- ajoute
);

-- Enseignants (chargés de TD ou TP) d'un moduleimpl
CREATE TABLE notes_modules_enseignants (
	modules_enseignants_id text default notes_newid('ENS') PRIMARY KEY,
	moduleimpl_id text REFERENCES notes_moduleimpl(moduleimpl_id),
	ens_id text
);

-- Inscription a un semestre de formation
CREATE TABLE notes_formsemestre_inscription (
	formsemestre_inscription_id text default notes_newid2('SI') PRIMARY KEY,
	etudid text REFERENCES identite(etudid),
	formsemestre_id text REFERENCES notes_formsemestre(formsemestre_id),
	groupetd text,
	groupetp text,
	groupeanglais text,
	etat text, -- I inscrit, D demission en cours de semestre
	UNIQUE(formsemestre_id, etudid)
);

-- Inscription a un module  (etudiants,moduleimpl)
CREATE TABLE notes_moduleimpl_inscription (
	moduleimpl_inscription_id text default notes_newid2('MI') PRIMARY KEY,
	moduleimpl_id text REFERENCES notes_moduleimpl(moduleimpl_id),
	-- cherche les infos sur les etudiants dans la table "identites" SCOGTR
	-- Futur: a adapter dans d'autres departements...
	etudid text REFERENCES identite(etudid),
	UNIQUE( moduleimpl_id, etudid)
);

-- Evaluations (controles, examens, ...)
CREATE TABLE notes_evaluation (
	evaluation_id text default notes_newid('EVAL') PRIMARY KEY,
	moduleimpl_id text REFERENCES notes_moduleimpl(moduleimpl_id),
	jour date,      
	heure_debut time,
	heure_fin time,
	description text,
	note_max real,
	coefficient real,
        visibulletin integer default 1
);

-- Les notes...
CREATE TABLE notes_notes (
	etudid text REFERENCES identite(etudid),
	evaluation_id text REFERENCES notes_evaluation(evaluation_id),
	value real,	
	UNIQUE(etudid,evaluation_id),
	-- infos sur saisie de cette note:
	comment text,
	date timestamp default now(),
	uid text
);

-- Historique des modifs sur notes (anciennes entrees de notes_notes)
CREATE TABLE notes_notes_log (
	id 	SERIAL PRIMARY KEY,
	etudid text REFERENCES identite(etudid), 
	evaluation_id text,  -- REFERENCES notes_evaluation(evaluation_id),
	value real,
	comment text,
	date timestamp,
	uid text,
	-- pas de foreign key, sinon bug lors supression notes (et on 
	-- veut garder le log)
	-- FOREIGN KEY (etudid,evaluation_id) REFERENCES notes_notes(etudid,evaluation_id)
);


---------------------------------------------------------------------
-- Parcours d'un etudiant
--
-- etat: INSCRIPTION inscr. de l'etud dans ce semestre
--       DEM         l'etud demissionne EN COURS DE SEMESTRE
--       DIPLOME     en fin semestre, attribution du diplome correspondant
--                          (ou plutot, validation du semestre)
--       AUT_RED     en fin semestre, autorise a redoubler ce semestre
--       EXCLUS      exclus (== non autorise a redoubler)
--       VALID_SEM   obtention semestre après jury terminal
--       VALID_UE    obtention UE après jury terminal
--       ECHEC_SEM   echec a ce semestre
CREATE TABLE scolar_events (
	event_id     text default notes_newid('EVT') PRIMARY KEY,
	etudid text,
	event_date timestamp default now(),
	formsemestre_id text REFERENCES notes_formsemestre(formsemestre_id),
        ue_id text REFERENCES notes_ue(ue_id),
	event_type text -- 'CREATION', 'INSCRIPTION', 'DEMISSION', 
                        -- 'AUT_RED', 'EXCLUS', 'VALID_UE', 'VALID_SEM'
                        -- 'ECHEC_SEM'
);

---------------------------------------------------------------------
-- NOUVELLES (inutilise pour l'instant)
--
CREATE TABLE scolar_news (
	news_id text default notes_newid('NEWS') PRIMARY KEY,
	date timestamp default now(),
	authenticated_user text, 
	type text, -- 'INSCR', 'NOTES', 'FORM', 'SEM', 'MISC'
	object text, -- moduleimpl_id, formation_id, formsemestre_id, 
	text text, -- free text
	url text -- optional URL
);

-- Appreciations sur bulletins
CREATE TABLE notes_appreciations (
    id integer DEFAULT nextval('serial'::text) NOT NULL,
    date timestamp without time zone DEFAULT now(),
    etudid text REFERENCES identite(etudid),
    formsemestre_id text REFERENCES notes_formsemestre(formsemestre_id),
    author text,
    comment text,
    zope_authenticated_user text,
    zope_remote_addr text
);
