CREATE SEQUENCE "passwd_userid_seq" start 1 increment 1 maxvalue 2147483647 minvalue 1  cache 1 ;

--
-- TOC Entry ID 6 (OID 24949)
--
-- Name: passwd Type: TABLE Owner: akm
--

CREATE TABLE "passwd" (
	"userid" integer DEFAULT nextval('"passwd_userid_seq"'::text) NOT NULL,
	"username" character varying(64) NOT NULL,
	"password" character varying(64) NOT NULL,
	"roles" character varying(255),
	Constraint "passwd_pkey" Primary Key ("userid")
);

--
-- TOC Entry ID 4 (OID 24965)
--
-- Name: userproperties_propertyid_seq Type: SEQUENCE Owner: akm
--

CREATE SEQUENCE "userproperties_propertyid_seq" start 1 increment 1 maxvalue 2147483647 minvalue 1  cache 1 ;

--
-- TOC Entry ID 7 (OID 24984)
--
-- Name: userproperties Type: TABLE Owner: akm
--

CREATE TABLE "userproperties" (
	"propertyid" integer DEFAULT nextval('"userproperties_propertyid_seq"'::text) NOT NULL,
	"username" character varying(64) NOT NULL,
	"key" character varying(128) NOT NULL,
	"value" text NOT NULL,
	"istemporary" integer,
	Constraint "userproperties_pkey" Primary Key ("propertyid")
);

--
-- TOC Entry ID 8 (OID 24984)
--
-- Name: "username_idx" Type: INDEX Owner: akm
--

CREATE  INDEX "username_idx" on "userproperties" using btree ( "username" "varchar_ops" );
