DROP TABLE IF EXISTS passwd;
CREATE TABLE passwd (
	username varchar(64) NOT NULL PRIMARY KEY,
	password varchar(64) NOT NULL,
	roles varchar(255)
);

DROP TABLE IF EXISTS UserProperties;
CREATE TABLE UserProperties (
	username varchar(64) NOT NULL,
	prop_key varchar(128) NOT NULL,
	value text NOT NULL,
	istemporary int
);

CREATE UNIQUE INDEX username_prop_idx on UserProperties(username,prop_key );
CREATE INDEX username_idx on UserProperties(username);

