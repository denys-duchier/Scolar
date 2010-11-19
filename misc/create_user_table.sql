
CREATE SEQUENCE sco_users_idgen;

CREATE FUNCTION sco_users_newid( text ) returns text as '
	select $1 || to_char(  nextval(''sco_users_idgen''), ''FM999999999'' ) 
	as result;
	' language SQL;


-- Source pour Zope User Folder

CREATE TABLE sco_users (
	user_id text default sco_users_newid('U') PRIMARY KEY,
	user_name text unique,
	passwd text not null,
	roles text,
	date_modif_passwd date default now(),
	nom text,
	prenom text,
        email text,
	dept text, -- departement d'appartenance
	passwd_temp int default 0, -- 0 ok, 1 mot de passe temporaire
	status text default '', -- NULL actif, 'old' ancien (pas de login possible)
) with oids;

