--
-- CREATION BASE DE DONNEES SCO GEA
--


-- creation de la base:
--  en tant qu'utilisateur postgres
--     createuser --pwprompt scogea
--     createdb -E latin1 -O scogea SCOGEA "scolarite GEA"
--
--

CREATE TABLE scolog (
    date timestamp without time zone DEFAULT now(),
    authenticated_user text,
    remote_addr text,
    remote_host text,
    method text,
    etudid character(32),
    msg text
);


--
--

CREATE TABLE etud_annotations (
    id integer DEFAULT nextval('serial'::text) NOT NULL,
    date timestamp without time zone DEFAULT now(),
    etudid character(32),
    author text,
    "comment" text,
    zope_authenticated_user text,
    zope_remote_addr text
);


--
--


CREATE TABLE temporary_tables (
    name text,
    numid integer,
    date timestamp without time zone,
    authenticated_user text,
    remote_addr text
);




--
--

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
    qualite_relation integer,
    plus10salaries integer,
    date_creation timestamp without time zone DEFAULT now()
);


--
--

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


--
--

CREATE SEQUENCE notes_idgen
    INCREMENT BY 1
    NO MAXVALUE
    NO MINVALUE
    CACHE 1;


--
--

CREATE FUNCTION notes_newid(text) RETURNS text
    AS '
	select ''GEA'' || $1 || to_char(  nextval(''notes_idgen''), ''FM999999999'' ) 
	as result;
	'
    LANGUAGE sql;



--
--

CREATE SEQUENCE notes_idgen2
    INCREMENT BY 1
    NO MAXVALUE
    NO MINVALUE
    CACHE 1;


--
--

CREATE FUNCTION notes_newid2(text) RETURNS text
    AS '
select ''GEA'' || $1 || to_char(  nextval(''notes_idgen2''), ''FM999999999'' ) 
as result;
'
    LANGUAGE sql;


--
--

CREATE TABLE notes_formations (
    formation_id text DEFAULT notes_newid('FORM'::text) NOT NULL,
    acronyme text NOT NULL,
    titre text NOT NULL
);


--
--

CREATE TABLE notes_ue (
    ue_id text DEFAULT notes_newid('UE'::text) NOT NULL,
    formation_id text,
    acronyme text NOT NULL,
    numero integer,
    titre text
);


--
--

CREATE TABLE notes_matieres (
    matiere_id text DEFAULT notes_newid('MAT'::text) NOT NULL,
    ue_id text,
    titre text,
    numero integer
);


--
--

CREATE TABLE notes_semestres (
    semestre_id integer NOT NULL
);


--
--

CREATE TABLE notes_modules (
    module_id text DEFAULT notes_newid('MOD'::text) NOT NULL,
    titre text,
    code text,
    heures_cours real,
    heures_td real,
    heures_tp real,
    ue_id text,
    formation_id text,
    matiere_id text,
    semestre_id integer,
    coefficient real,
    numero integer,
    abbrev text
);


--

CREATE TABLE notes_formsemestre (
    formsemestre_id text DEFAULT notes_newid('SEM'::text) NOT NULL,
    formation_id text,
    semestre_id integer,
    titre text,
    date_debut date,
    responsable_id text,
    date_fin date
);


--
--

CREATE TABLE notes_moduleimpl (
    moduleimpl_id text DEFAULT notes_newid('MIP'::text) NOT NULL,
    module_id text,
    formsemestre_id text,
    responsable_id text
);


--
--

CREATE TABLE notes_evaluation (
    evaluation_id text DEFAULT notes_newid('EVAL'::text) NOT NULL,
    moduleimpl_id text,
    jour date,
    heure_debut time without time zone,
    heure_fin time without time zone,
    description text,
    note_max real,
    coefficient real
);


--
--

CREATE TABLE notes_formsemestre_inscription (
    formsemestre_inscription_id text DEFAULT notes_newid2('SI'::text) NOT NULL,
    etudid text,
    formsemestre_id text,
    groupetd text,
    groupetp text,
    groupeanglais text,
    etat text
);


--
--

CREATE TABLE notes_moduleimpl_inscription (
    moduleimpl_inscription_id text DEFAULT notes_newid2('MI'::text) NOT NULL,
    moduleimpl_id text,
    etudid text
);


--
--

CREATE TABLE adresse (
    adresse_id text DEFAULT notes_newid('ADR'::text) NOT NULL,
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


--
--

CREATE TABLE identite (
    etudid text DEFAULT notes_newid('EID'::text) NOT NULL,
    nom text,
    prenom text,
    sexe text,
    annee_naissance integer,
    nationalite text,
    foto text
);



--
--

CREATE TABLE absences (
    etudid text NOT NULL,
    jour date,
    estabs boolean,
    estjust boolean,
    matin boolean
);


--
--

CREATE TABLE admissions (
    adm_id text DEFAULT notes_newid('ADM'::text) NOT NULL,
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


--
--

CREATE TABLE notes_notes (
    etudid text,
    evaluation_id text,
    value real,
    "comment" text,
    date timestamp without time zone DEFAULT now(),
    uid text
);


--
--

CREATE TABLE notes_notes_log (
    id serial NOT NULL,
    etudid text,
    evaluation_id text,
    value real,
    "comment" text,
    date timestamp without time zone,
    uid text
);


--
--

CREATE TABLE scolar_events (
    event_id text DEFAULT notes_newid('EVT'::text) NOT NULL,
    etudid text,
    event_date timestamp without time zone DEFAULT now(),
    formsemestre_id text,
    event_type text
);


--
--

ALTER TABLE ONLY etud_annotations
    ADD CONSTRAINT etud_annotations_pkey PRIMARY KEY (id);


--
ALTER TABLE ONLY entreprises
    ADD CONSTRAINT entreprises_pkey PRIMARY KEY (entreprise_id);


--
ALTER TABLE ONLY entreprise_correspondant
    ADD CONSTRAINT entreprise_correspondant_pkey PRIMARY KEY (entreprise_corresp_id);


--
ALTER TABLE ONLY entreprise_contact
    ADD CONSTRAINT entreprise_contact_pkey PRIMARY KEY (entreprise_contact_id);


--


ALTER TABLE ONLY notes_formations
    ADD CONSTRAINT notes_formations_pkey PRIMARY KEY (formation_id);


--

ALTER TABLE ONLY notes_formations
    ADD CONSTRAINT notes_formations_acronyme_key UNIQUE (acronyme, titre);


--

ALTER TABLE ONLY notes_ue
    ADD CONSTRAINT notes_ue_pkey PRIMARY KEY (ue_id);


--

ALTER TABLE ONLY notes_matieres
    ADD CONSTRAINT notes_matieres_pkey PRIMARY KEY (matiere_id);


--
--

ALTER TABLE ONLY notes_matieres
    ADD CONSTRAINT notes_matieres_ue_id_key UNIQUE (ue_id, titre);


--
--

ALTER TABLE ONLY notes_semestres
    ADD CONSTRAINT notes_semestres_pkey PRIMARY KEY (semestre_id);


--
--

ALTER TABLE ONLY notes_modules
    ADD CONSTRAINT notes_modules_pkey PRIMARY KEY (module_id);


--
--

ALTER TABLE ONLY notes_formsemestre
    ADD CONSTRAINT notes_formsemestre_pkey PRIMARY KEY (formsemestre_id);


--
--

ALTER TABLE ONLY notes_moduleimpl
    ADD CONSTRAINT notes_moduleimpl_pkey PRIMARY KEY (moduleimpl_id);


--
--

ALTER TABLE ONLY notes_moduleimpl
    ADD CONSTRAINT notes_moduleimpl_module_id_key UNIQUE (module_id, formsemestre_id);


--
--

ALTER TABLE ONLY notes_evaluation
    ADD CONSTRAINT notes_evaluation_pkey PRIMARY KEY (evaluation_id);


--
--

ALTER TABLE ONLY notes_formsemestre_inscription
    ADD CONSTRAINT notes_formsemestre_inscription_pkey PRIMARY KEY (formsemestre_inscription_id);


--
--

ALTER TABLE ONLY notes_formsemestre_inscription
    ADD CONSTRAINT notes_formsemestre_inscription_formsemestre_id_key UNIQUE (formsemestre_id, etudid);


--
--

ALTER TABLE ONLY notes_moduleimpl_inscription
    ADD CONSTRAINT notes_moduleimpl_inscription_pkey PRIMARY KEY (moduleimpl_inscription_id);


--
--

ALTER TABLE ONLY notes_moduleimpl_inscription
    ADD CONSTRAINT notes_moduleimpl_inscription_moduleimpl_id_key UNIQUE (moduleimpl_id, etudid);


--
--

ALTER TABLE ONLY adresse
    ADD CONSTRAINT new_adresse_pkey PRIMARY KEY (adresse_id);


--
--

ALTER TABLE ONLY identite
    ADD CONSTRAINT identite2_pkey PRIMARY KEY (etudid);


--
--


ALTER TABLE ONLY admissions
    ADD CONSTRAINT admissions3_pkey PRIMARY KEY (adm_id);


--
--

ALTER TABLE ONLY notes_notes
    ADD CONSTRAINT notes_notes_etudid_key UNIQUE (etudid, evaluation_id);


--
--

ALTER TABLE ONLY notes_notes_log
    ADD CONSTRAINT notes_notes_log_pkey PRIMARY KEY (id);


--
--

ALTER TABLE ONLY scolar_events
    ADD CONSTRAINT scolar_events_pkey PRIMARY KEY (event_id);


--
--

ALTER TABLE ONLY entreprise_correspondant
    ADD CONSTRAINT "$1" FOREIGN KEY (entreprise_id) REFERENCES entreprises(entreprise_id);


--
--

ALTER TABLE ONLY entreprise_contact
    ADD CONSTRAINT "$1" FOREIGN KEY (entreprise_id) REFERENCES entreprises(entreprise_id);


--
--

ALTER TABLE ONLY entreprise_contact
    ADD CONSTRAINT "$2" FOREIGN KEY (entreprise_corresp_id) REFERENCES entreprise_correspondant(entreprise_corresp_id);


--
--

ALTER TABLE ONLY entreprise_contact
    ADD CONSTRAINT "$3" FOREIGN KEY (etudid) REFERENCES identite(etudid);

--
--

ALTER TABLE ONLY notes_ue
    ADD CONSTRAINT "$1" FOREIGN KEY (formation_id) REFERENCES notes_formations(formation_id);


--
--

ALTER TABLE ONLY notes_matieres
    ADD CONSTRAINT "$1" FOREIGN KEY (ue_id) REFERENCES notes_ue(ue_id);


--
--

ALTER TABLE ONLY notes_modules
    ADD CONSTRAINT "$1" FOREIGN KEY (ue_id) REFERENCES notes_ue(ue_id);


--
--

ALTER TABLE ONLY notes_modules
    ADD CONSTRAINT "$2" FOREIGN KEY (formation_id) REFERENCES notes_formations(formation_id);


--
--

ALTER TABLE ONLY notes_modules
    ADD CONSTRAINT "$3" FOREIGN KEY (matiere_id) REFERENCES notes_matieres(matiere_id);


--
--

ALTER TABLE ONLY notes_modules
    ADD CONSTRAINT "$4" FOREIGN KEY (semestre_id) REFERENCES notes_semestres(semestre_id);


--
--

ALTER TABLE ONLY notes_formsemestre
    ADD CONSTRAINT "$1" FOREIGN KEY (formation_id) REFERENCES notes_formations(formation_id);


--
--

ALTER TABLE ONLY notes_formsemestre
    ADD CONSTRAINT "$2" FOREIGN KEY (semestre_id) REFERENCES notes_semestres(semestre_id);


--
--


ALTER TABLE ONLY notes_moduleimpl
    ADD CONSTRAINT "$1" FOREIGN KEY (module_id) REFERENCES notes_modules(module_id);


--
--

ALTER TABLE ONLY notes_moduleimpl
    ADD CONSTRAINT "$2" FOREIGN KEY (formsemestre_id) REFERENCES notes_formsemestre(formsemestre_id);


--
--


ALTER TABLE ONLY notes_evaluation
    ADD CONSTRAINT "$1" FOREIGN KEY (moduleimpl_id) REFERENCES notes_moduleimpl(moduleimpl_id);


--
--

ALTER TABLE ONLY notes_formsemestre_inscription
    ADD CONSTRAINT "$2" FOREIGN KEY (formsemestre_id) REFERENCES notes_formsemestre(formsemestre_id);


--
--

ALTER TABLE ONLY notes_moduleimpl_inscription
    ADD CONSTRAINT "$1" FOREIGN KEY (moduleimpl_id) REFERENCES notes_moduleimpl(moduleimpl_id);


--
--

ALTER TABLE ONLY admissions
    ADD CONSTRAINT "$1" FOREIGN KEY (etudid) REFERENCES identite(etudid);


--
--

ALTER TABLE ONLY notes_notes
    ADD CONSTRAINT "$1" FOREIGN KEY (etudid) REFERENCES identite(etudid);


--
--

ALTER TABLE ONLY notes_notes
    ADD CONSTRAINT "$2" FOREIGN KEY (evaluation_id) REFERENCES notes_evaluation(evaluation_id);


--
--


ALTER TABLE ONLY notes_notes_log
    ADD CONSTRAINT "$1" FOREIGN KEY (etudid) REFERENCES identite(etudid);


--
--

ALTER TABLE ONLY notes_notes_log
    ADD CONSTRAINT "$4" FOREIGN KEY (etudid, evaluation_id) REFERENCES notes_notes(etudid, evaluation_id);


--
--

ALTER TABLE ONLY notes_moduleimpl_inscription
    ADD CONSTRAINT "$2" FOREIGN KEY (etudid) REFERENCES identite(etudid);


--
--

ALTER TABLE ONLY notes_formsemestre_inscription
    ADD CONSTRAINT "$1" FOREIGN KEY (etudid) REFERENCES identite(etudid);


--
--

ALTER TABLE ONLY scolar_events
    ADD CONSTRAINT "$1" FOREIGN KEY (formsemestre_id) REFERENCES notes_formsemestre(formsemestre_id);




