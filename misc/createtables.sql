
-- Creation des tables pour gestion notes
-- E. Viennet, Sep 2005

-- genereation des id
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


-- Description generique d'un module (eg infos du PPN)

CREATE TABLE notes_formations (
	formation_id text default notes_newid('FORM') PRIMARY KEY,
	acronyme text NOT NULL, -- 'DUT R&T', 'LPSQRT', ...	
	titre text NOT NULL,     -- titre complet
	UNIQUE(acronyme,titre)
);

CREATE TABLE notes_ue (
	ue_id text default notes_newid('UE') PRIMARY KEY,
	formation_id text REFERENCES notes_formations(formation_id),
	acronyme text NOT NULL,
	numero int, -- ordre de presentation
	titre text
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
	numero int -- ordre de presentation
	abbrev text, -- nom court
);

-- Mise en oeuvre d'un semestre de formation
CREATE TABLE notes_formsemestre (
	formsemestre_id text default notes_newid('SEM') PRIMARY KEY,
	formation_id text REFERENCES notes_formations(formation_id),
	semestre_id int REFERENCES notes_semestres(semestre_id),
	titre text,
	date_debut date,
        date_fin   date,
	responsable_id text REFERENCES notes_users(uid)
);

-- Mise en oeuvre d'un module pour une annee/semestre
CREATE TABLE notes_moduleimpl (
	moduleimpl_id  text default notes_newid('MIP') PRIMARY KEY,
	module_id text REFERENCES notes_modules(module_id),
	formsemestre_id text REFERENCES notes_formsemestre(formsemestre_id),
	responsable_id text REFERENCES notes_users(uid),
	UNIQUE(module_id,formsemestre_id) -- ajoute
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
	coefficient real
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
	uid text REFERENCES notes_users(uid)
);

-- Historique des modifs sur notes (anciennes entrees de notes_notes)
CREATE TABLE notes_notes_log (
	id 	SERIAL PRIMARY KEY,
	etudid text REFERENCES identite(etudid), 
	evaluation_id text REFERENCES notes_evaluation(evaluation_id),
	value real,
	comment text,
	date timestamp,
	uid text REFERENCES notes_users(uid),
	FOREIGN KEY (etudid,evaluation_id) REFERENCES notes_notes(etudid,evaluation_id)
);


---------------------------------------------------------------------
-- Parcours d'un etudiant
--
-- etat: INSCRIPTION inscr. de l'etud dans ce semestre
--       DEM         l'etud demissionne EN COURS DE SEMESTRE
--       DIPLOME     en fin semestre, attribution du diplome correspondant
--                          (ou plutot, validation du semestre)
--       AUT_RED     en fin semestre, autorise a redoubler ce semestre
--       EXCL        exclus (== non autorise a redoubler)
CREATE TABLE scolar_events (
	event_id     text default notes_newid('EVT') PRIMARY KEY,
	etudid text,
	event_date timestamp default now(),
	formsemestre_id text REFERENCES notes_formsemestre(formsemestre_id),
	event_type text -- 'CREATION', 'INSCRIPTION', 'DEMISSION', 'DIPLOME', 'AUT_RED', 'EXCLUS' 
);
