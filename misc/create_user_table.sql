
CREATE SEQUENCE sco_users_idgen;

CREATE FUNCTION sco_users_newid( text ) returns text as '
	select $1 || to_char(  nextval(\'sco_users_idgen\'), \'FM999999999\' ) 
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
        email text
);

insert into sco_users (user_name, passwd, nom, prenom, email) 
values ('viennet', 'NqUrsimfzVSmTHk/k7qyVw==', 'viennet', 'emmanuel', 'viennet@lipn.univ-paris13.fr');

