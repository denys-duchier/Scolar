CREATE TABLE "passwd" (
	"username" character varying(64) UNIQUE NOT NULL,
	"password" character varying(64) NOT NULL,
	"roles" character varying(255),
	Constraint "passwd_pkey" Primary Key ("username")
);

CREATE TABLE "userproperties" (
	"username" character varying(64) NOT NULL REFERENCES passwd (username) ON DELETE CASCADE ON UPDATE CASCADE,
	"key" character varying(128) NOT NULL,
	"value" text NOT NULL	
);

CREATE  INDEX "username_idx" on "userproperties" using btree ( "username" "varchar_ops" );
