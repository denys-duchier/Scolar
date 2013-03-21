CREATE TABLE "security_user" (
        "username" VARCHAR(64) PRIMARY KEY NOT NULL,
        "password" VARCHAR(64) NOT NULL,
);


CREATE TABLE "security_role" (
        "rolename" VARCHAR(64) PRIMARY KEY NOT NULL
);


CREATE TABLE "security_userrole" (
        "username" VARCHAR(64) NOT NULL,
        "rolename" VARCHAR(64) NOT NULL,
        CONSTRAINT "userrole_pkey" PRIMARY KEY ("username", "rolename"),
        CONSTRAINT "username_fkey" FOREIGN KEY ("username")
                REFERENCES "security_user" ("username"),
        CONSTRAINT "rolename_fkey" FOREIGN KEY ("rolename")
                REFERENCES "security_role" ("rolename")
);


CREATE INDEX "user_username_index" on "security_user" ("username");
CREATE INDEX "userrole_username_index" on "security_userrole" ("username");
