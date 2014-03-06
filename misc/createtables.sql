
-- Creation des tables pour gestion notes
-- E. Viennet, Sep 2005



-- creation de la base:
--  en tant qu'utilisateur postgres
--     createuser --pwprompt scogea
--     createdb -E latin1 -O scogea SCOGEA "scolarite GEA"
--
--

-- generation des id
CREATE SEQUENCE serial;
CREATE SEQUENCE notes_idgen;

CREATE FUNCTION notes_newid( text ) returns text as '
	select $1 || to_char(  nextval(''notes_idgen''), ''FM999999999'' ) 
	as result;
	' language SQL;

CREATE SEQUENCE notes_idgen2;

CREATE FUNCTION notes_newid2( text ) returns text as '
	select $1 || to_char(  nextval(''notes_idgen2''), ''FM999999999'' ) 
	as result;
	' language SQL;

CREATE SEQUENCE notes_idgen_etud;

CREATE FUNCTION notes_newid_etud( text ) returns text as '
	select $1 || to_char(  nextval(''notes_idgen_etud''), ''FM999999999'' ) 
	as result;
	' language SQL;

-- Preferences
CREATE TABLE sco_prefs (
    pref_id text DEFAULT notes_newid('PREF'::text) UNIQUE NOT NULL,
    name text NOT NULL,
    value text,
    formsemestre_id text default NULL,
    UNIQUE(name,formsemestre_id)
) WITH OIDS;


CREATE TABLE identite (
    etudid text DEFAULT notes_newid_etud('EID'::text) UNIQUE NOT NULL,
    nom text,
    prenom text,
    sexe text,
    date_naissance date, -- new: date en texte
    lieu_naissance text,
    nationalite text,   
    statut text, -- NULL ou 'SALARIE' 
    foto text, -- deprecated
    photo_filename text,
    code_nip text UNIQUE, -- code NIP Apogee (may be null)
    code_ine text UNIQUE,  -- code INE Apogee    
    nom_usuel text -- optionnel (si present, affiché à la place du nom)
)  WITH OIDS;

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
) WITH OIDS;

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
    villelycee text,
    codepostallycee text,
    codelycee text,
    debouche text, -- situation APRES etre passe par chez nous (texte libre)
    type_admission text, -- 'APB', 'APC-PC', 'CEF', 'Direct', '?' (autre)
    boursier_prec integer default NULL -- etait boursier dans le cycle precedent (lycee) ?
) WITH OIDS;

CREATE TABLE absences (
    etudid text NOT NULL,
    jour date, -- jour de l'absence
    estabs boolean, -- vrai si absent
    estjust boolean, -- vrai si justifie
    matin boolean, -- vrai si concerne le matin, faux si apres midi
    description text,  -- "raison" de l'absence
    entry_date timestamp with time zone DEFAULT now(),
    moduleimpl_id text -- moduleimpid concerne (optionnel)
) WITH OIDS;

CREATE TABLE absences_notifications (    
    etudid text NOT NULL,
    notification_date timestamp with time zone DEFAULT now(),
    email text NOT NULL,
    nbabs integer,
    nbabsjust integer,
    formsemestre_id text -- semestre concerne par cette notification    
) WITH OIDS;

CREATE SEQUENCE notes_idgen_billets;
CREATE FUNCTION notes_newid_billet( text ) returns text as '
	select $1 || to_char(  nextval(''notes_idgen_billets''), ''FM999999999'' ) 
	as result;
	' language SQL;

CREATE TABLE billet_absence (
    billet_id text DEFAULT notes_newid_billet('B'::text) NOT NULL,
    etudid text NOT NULL,
    abs_begin timestamp with time zone,
    abs_end  timestamp with time zone,
    description text, -- "raison" de l'absence
    etat integer default 0, -- 0 new, 1 processed    
    entry_date timestamp with time zone DEFAULT now(),
    justified integer default 0 -- 1 si l'absence pourrait etre justifiée
) WITH OIDS;


-- --- Log des actions (journal modif etudiants)
CREATE TABLE scolog (
    date timestamp without time zone DEFAULT now(),
    authenticated_user text,
    remote_addr text,
    remote_host text,
    method text,
    etudid character(32),
    msg text
) WITH OIDS;


CREATE TABLE etud_annotations (
    id integer DEFAULT nextval('serial'::text) NOT NULL,
    date timestamp without time zone DEFAULT now(),
    etudid character(32),
    author text,
    comment text,
    zope_authenticated_user text,
    zope_remote_addr text
) WITH OIDS;

--  ------------ Nouvelle gestion des absences ------------
CREATE SEQUENCE abs_idgen;
CREATE FUNCTION abs_newid( text ) returns text as '
	select $1 || to_char(  nextval(''abs_idgen''), ''FM999999999'' ) 
	as result;
	' language SQL;

CREATE TABLE abs_absences (
    absid text default abs_newid('AB') PRIMARY KEY,
    etudid character(32),
    abs_begin timestamp with time zone,
    abs_end  timestamp with time zone
) WITH OIDS;

CREATE TABLE abs_presences (
    absid text default abs_newid('PR') PRIMARY KEY,
    etudid character(32),
    abs_begin timestamp with time zone,
    abs_end  timestamp with time zone
) WITH OIDS;

CREATE TABLE abs_justifs (
    absid text default abs_newid('JU') PRIMARY KEY,
    etudid character(32),
    abs_begin timestamp with time zone,
    abs_end  timestamp with time zone,
    category text,
    description text
) WITH OIDS;



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
) WITH OIDS;


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
) WITH OIDS;


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
) WITH OIDS;


--  ------------ NOTES ------------


-- Description generique d'un module (eg infos du PPN)
CREATE SEQUENCE notes_idgen_fcod;
CREATE FUNCTION notes_newid_fcod( text ) returns text as '
	select $1 || to_char(  nextval(''notes_idgen_fcod''), ''FM999999999'' ) 
	as result;
	' language SQL;

CREATE TABLE notes_formations (
	formation_id text default notes_newid('FORM') PRIMARY KEY,
	acronyme text NOT NULL, -- 'DUT R&T', 'LPSQRT', ...	
	titre text NOT NULL,     -- titre complet
	titre_officiel text NOT NULL, -- "DUT Gestion des Entreprises et Admininistration"
	version integer default 1, -- version de la formation
	formation_code text default notes_newid_fcod('FCOD') NOT NULL,
	type_parcours  int DEFAULT 0, -- 0 DUT, 100 Lic Pro
	UNIQUE(acronyme,titre,version)
) WITH OIDS;

CREATE TABLE notes_ue (
	ue_id text default notes_newid('UE') PRIMARY KEY,
	formation_id text REFERENCES notes_formations(formation_id),
	acronyme text NOT NULL,
	numero int, -- ordre de presentation
	titre text,
	type  int DEFAULT 0, -- 0 normal, 1 "sport", 2 "projet et stage (LP)"
	ue_code text default notes_newid_fcod('UCOD') NOT NULL,
    ects real -- nombre de credits ECTS
) WITH OIDS;

CREATE TABLE notes_matieres (
	matiere_id text default notes_newid('MAT') PRIMARY KEY,
	ue_id text REFERENCES notes_ue(ue_id),
	titre text,
	numero int, -- ordre de presentation
	UNIQUE(ue_id,titre)
) WITH OIDS;

CREATE TABLE notes_semestres (
	-- une bete table 1,2,3,4 pour l'instant fera l'affaire...
	semestre_id int PRIMARY KEY
) WITH OIDS;
INSERT INTO notes_semestres (semestre_id) VALUES (-1); -- denote qu'il n'y a pas de semestres dans ce diplome
INSERT INTO notes_semestres (semestre_id) VALUES (1);
INSERT INTO notes_semestres (semestre_id) VALUES (2);
INSERT INTO notes_semestres (semestre_id) VALUES (3);
INSERT INTO notes_semestres (semestre_id) VALUES (4);
INSERT INTO notes_semestres (semestre_id) VALUES (5);
INSERT INTO notes_semestres (semestre_id) VALUES (6);
INSERT INTO notes_semestres (semestre_id) VALUES (7);
INSERT INTO notes_semestres (semestre_id) VALUES (8);

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
	abbrev text, -- nom court
	ects real -- nombre de credits ECTS (inutilises: ils sont associes aux UE)
) WITH OIDS;

-- Mise en oeuvre d'un semestre de formation
CREATE TABLE notes_formsemestre (
	formsemestre_id text default notes_newid('SEM') PRIMARY KEY,
	formation_id text REFERENCES notes_formations(formation_id),
	semestre_id int REFERENCES notes_semestres(semestre_id),
	titre text,
	date_debut date,
        date_fin   date,
	responsable_id text,
        -- gestion_absence integer default 1,   -- XXX obsolete
	-- bul_show_decision integer default 1, -- XXX obsolete
	-- bul_show_uevalid integer default 1,  -- XXX obsolete
        etat integer default 1, -- 1 ouvert, 0 ferme (verrouille)
	-- nomgroupetd text default 'TD',  -- XXX obsolete
 	-- nomgroupetp text default 'TP',  -- XXX obsolete 
 	-- nomgroupeta text default 'langues', -- XXX obsolete
	-- bul_show_codemodules integer default 1, -- XXX obsolete
	-- bul_show_rangs integer default 1,  -- XXX obsolete
	-- bul_show_ue_rangs integer default 1, -- XXX obsolete
        -- bul_show_mod_rangs integer default 1, -- XXX obsolete
        gestion_compensation integer default 0, -- gestion compensation sem DUT
	bul_hide_xml integer default 0, --  ne publie pas le bulletin XML
	gestion_semestrielle integer default 0, -- semestres decales (pour gestion jurys)
	bul_bgcolor text default 'white', -- couleur fond bulletins HTML
	etape_apo text, -- code etape Apogée
	etape_apo2 text,-- code etape Apogée secondaire (si deux etapes pour meme semestre)
	etape_apo3 text,-- code etape Apogée secondaire (si trois etapes pour meme semestre)
	etape_apo4 text,-- code etape Apogée secondaire (si quatre etapes pour meme semestre)
	modalite text,   -- FI, FC, APP, ''
	resp_can_edit integer default 0, -- autorise resp. a modifier semestre
	resp_can_change_ens integer default 1, -- autorise resp. a modifier slt les enseignants
	ens_can_edit_eval int default 0 -- autorise les ens a creer des evals
) WITH OIDS;

CREATE TABLE notes_form_modalites (
    form_modalite_id text default notes_newid('Md') PRIMARY KEY,
    modalite text, -- la clef dans notes_formsemestre
    titre text, -- le nom complet de la modalite pour les documents scodoc
    numero SERIAL -- integer, ordre de presentation
);
INSERT INTO notes_form_modalite (modalite, titre) VALUES ('', 'Autres formations');
INSERT INTO notes_form_modalite (modalite, titre) VALUES ('FI', 'Formation Initiale');
INSERT INTO notes_form_modalite (modalite, titre) VALUES ('FC', 'Formation Continue');
INSERT INTO notes_form_modalite (modalite, titre) VALUES ('FAP', 'Apprentissage');
INSERT INTO notes_form_modalite (modalite, titre) VALUES ('DEC', 'Formation Décalées');
INSERT INTO notes_form_modalite (modalite, titre) VALUES ('LIC', 'Licence');

-- Coef des UE capitalisees arrivant dans ce semestre:
CREATE TABLE notes_formsemestre_uecoef (
	formsemestre_uecoef_id text default notes_newid('SEM') PRIMARY KEY,
	formsemestre_id text REFERENCES notes_formsemestre(formsemestre_id),
	ue_id  text REFERENCES notes_ue(ue_id),
	coefficient real NOT NULL,
	UNIQUE(formsemestre_id, ue_id)
) WITH OIDS;


-- Formules utilisateurs pour calcul moyenne UE
CREATE TABLE notes_formsemestre_ue_computation_expr (
	notes_formsemestre_ue_computation_expr_id text default notes_newid('UEXPR') PRIMARY KEY,
	formsemestre_id text REFERENCES notes_formsemestre(formsemestre_id),
	ue_id  text REFERENCES notes_ue(ue_id),
	computation_expr text, -- formule de calcul moyenne
	UNIQUE(formsemestre_id, ue_id)
) WITH OIDS;

-- Menu custom associe au semestre
CREATE TABLE notes_formsemestre_custommenu (
	custommenu_id text default notes_newid('CMENU') PRIMARY KEY,
	formsemestre_id text REFERENCES notes_formsemestre(formsemestre_id),
	title text,
	url text,
	idx integer default 0 -- rang dans le menu	
) WITH OIDS;

-- Mise en oeuvre d'un module pour une annee/semestre
CREATE TABLE notes_moduleimpl (
	moduleimpl_id  text default notes_newid('MIP') PRIMARY KEY,
	module_id text REFERENCES notes_modules(module_id),
	formsemestre_id text REFERENCES notes_formsemestre(formsemestre_id),
	responsable_id text,
	computation_expr text, -- formule de calcul moyenne
	UNIQUE(module_id,formsemestre_id) -- ajoute
) WITH OIDS;

-- Enseignants (chargés de TD ou TP) d'un moduleimpl
CREATE TABLE notes_modules_enseignants (
	modules_enseignants_id text default notes_newid('ENS') PRIMARY KEY,
	moduleimpl_id text REFERENCES notes_moduleimpl(moduleimpl_id),
	ens_id text -- est le user_name de sco_users (de la base SCOUSERS)
) WITH OIDS;

-- Inscription a un semestre de formation
CREATE TABLE notes_formsemestre_inscription (
	formsemestre_inscription_id text default notes_newid2('SI') PRIMARY KEY,
	etudid text REFERENCES identite(etudid),
	formsemestre_id text REFERENCES notes_formsemestre(formsemestre_id),
	etat text, -- I inscrit, D demission en cours de semestre, DEF si "defaillant"
	UNIQUE(formsemestre_id, etudid)
) WITH OIDS;

-- Inscription a un module  (etudiants,moduleimpl)
CREATE TABLE notes_moduleimpl_inscription (
	moduleimpl_inscription_id text default notes_newid2('MI') PRIMARY KEY,
	moduleimpl_id text REFERENCES notes_moduleimpl(moduleimpl_id),
	etudid text REFERENCES identite(etudid),
	UNIQUE( moduleimpl_id, etudid)
) WITH OIDS;


CREATE TABLE partition(
       partition_id text default notes_newid2('P') PRIMARY KEY,
       formsemestre_id text REFERENCES notes_formsemestre(formsemestre_id),
       partition_name text, -- "TD", "TP", ... (NULL for 'all')
       compute_ranks integer default 1, -- calcul rang etudiants dans les groupes (currently unused)
       numero SERIAL, -- ordre de presentation
       bul_show_rank integer default 0,
       UNIQUE(formsemestre_id,partition_name)
) WITH OIDS;

CREATE TABLE group_descr (
       group_id text default notes_newid2('G') PRIMARY KEY,
       partition_id text REFERENCES partition(partition_id),
       group_name text, -- "A", "C2", ...  (NULL for 'all')
       UNIQUE(partition_id, group_name)     
) WITH OIDS;

CREATE TABLE group_membership(
       group_membership_id text default notes_newid2('GM') PRIMARY KEY,
       etudid text REFERENCES identite(etudid),       
       group_id text REFERENCES group_descr(group_id),
       UNIQUE(etudid, group_id)
) WITH OIDS;

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
    visibulletin integer default 1,
	publish_incomplete integer default 0, -- prise en compte meme si incomplete
	evaluation_type integer default 0, -- type d'evaluation: 0 normale, 1 rattrapage
    numero int -- ordre de presentation (le plus petit numero est normalement la plus ancienne eval)
) WITH OIDS;

-- Les notes...
CREATE TABLE notes_notes (
	etudid text REFERENCES identite(etudid),
	evaluation_id text REFERENCES notes_evaluation(evaluation_id),
	value real,	-- null si absent, voir valeurs speciales dans notes_table.py
	UNIQUE(etudid,evaluation_id),
	-- infos sur saisie de cette note:
	comment text,
	date timestamp default now(),
	uid text
) WITH OIDS;

-- Historique des modifs sur notes (anciennes entrees de notes_notes)
CREATE TABLE notes_notes_log (
	id 	SERIAL PRIMARY KEY,
	etudid text REFERENCES identite(etudid), 
	evaluation_id text,  -- REFERENCES notes_evaluation(evaluation_id),
	value real,
	comment text,
	date timestamp,
	uid text
	-- pas de foreign key, sinon bug lors supression notes (et on 
	-- veut garder le log)
	-- FOREIGN KEY (etudid,evaluation_id) REFERENCES notes_notes(etudid,evaluation_id)
) WITH OIDS;


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
--       UTIL_COMPENSATION utilise formsemestre_id pour compenser et valider
--                         comp_formsemestre_id
CREATE TABLE scolar_events (
	event_id     text default notes_newid('EVT') PRIMARY KEY,
	etudid text,
	event_date timestamp default now(),
	formsemestre_id text REFERENCES notes_formsemestre(formsemestre_id),
        ue_id text REFERENCES notes_ue(ue_id),
	event_type text, -- 'CREATION', 'INSCRIPTION', 'DEMISSION', 
                         -- 'AUT_RED', 'EXCLUS', 'VALID_UE', 'VALID_SEM'
                         -- 'ECHEC_SEM'
	                 -- 'UTIL_COMPENSATION'
        comp_formsemestre_id text REFERENCES notes_formsemestre(formsemestre_id)
                         -- semestre compense par formsemestre_id
) WITH OIDS;

-- Stockage des codes d'etat apres jury
CREATE SEQUENCE notes_idgen_svalid;

CREATE FUNCTION notes_newidsvalid( text ) returns text as '
	select $1 || to_char(  nextval(''notes_idgen_svalid''), ''FM999999999'' ) 
	as result;
	' language SQL;

CREATE TABLE scolar_formsemestre_validation (
	formsemestre_validation_id text default notes_newidsvalid('VAL') PRIMARY KEY,
	etudid text NOT NULL,
	formsemestre_id text REFERENCES notes_formsemestre(formsemestre_id), -- NULL si validation d'une UE hors ScoDoc
	ue_id text REFERENCES notes_ue(ue_id), -- NULL si validation de semestre
	code text NOT NULL,
	assidu integer, -- NULL pour les UE, 0|1 pour les semestres
	event_date timestamp default now(),
	compense_formsemestre_id text, -- null sauf si compense un semestre
	moy_ue real, -- moyenne UE capitalisee (/20, NULL si non calculee)
	semestre_id int, -- (normalement NULL) indice du semestre, utile seulement pour UE "antérieures" et si la formation définit des UE utilisées dans plusieurs semestres (cas R&T IUTV v2)
	UNIQUE(etudid,formsemestre_id,ue_id) -- une seule decision
) WITH OIDS;

CREATE TABLE scolar_autorisation_inscription (
	autorisation_inscription_id text default notes_newidsvalid('AUT') PRIMARY KEY,
	etudid text NOT NULL,
	formation_code text NOT NULL,
	semestre_id int REFERENCES notes_semestres(semestre_id), -- semestre ou on peut s'inscrire
	date timestamp default now(),
	origin_formsemestre_id text REFERENCES notes_formsemestre(formsemestre_id)
) WITH OIDS;

---------------------------------------------------------------------
-- NOUVELLES (pour page d'accueil et flux rss associe)
--
CREATE TABLE scolar_news (
	news_id text default notes_newid('NEWS') PRIMARY KEY,
	date timestamp default now(),
	authenticated_user text, 
	type text, -- 'INSCR', 'NOTES', 'FORM', 'SEM', 'MISC'
	object text, -- moduleimpl_id, formation_id, formsemestre_id, 
	text text, -- free text
	url text -- optional URL
) WITH OIDS;

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
) WITH OIDS;



