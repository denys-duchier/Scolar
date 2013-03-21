A lot of this stuff is now covered in the Unenlightened Zopistas Guide to
exUserFolder, so this document is slightly redundant (but not completely).
It's also shockingly out of date...

A note on the version numbering... there's none of that odd/even 
numbering nonsense you find in Lin*x land. The numbers are based on

Major.Minor.Micro

A bump in Major means a milestone or set of milestones has been reached.
A bump in Minor means some piece of functionality has been added, or
a major bug was fixed.
A bump in Micro usually means bug fixes.

These numbers go from 0-99, and are not necessarily continuous or
monotonically increasing (but they are increasing).

What you consider major and what I consider major are probably two
different things.

Release candidates before a Major bump start at 99.. so;

0.99.0  is the first Release Candidate prior to 1.0.0
0.99.1  is the next Release Candidate
1.0.0 is the 'final' release.

It's possible that there will be no changes between final release candidate 
and release.

Sometimes due to the nature of the changes a release will be marked 
development. This usually means some core functionality was changed.

Extensible User Folder

Extensible User Folder is a user folder that requires the authentication 
of users to be removed from the storage of properties for users.

Writing new authentication or property sources is (almost) a trivial operation
and require no authentication knowledge to write, most simply return lists
of attributes, or dictionaries. You don't need to incorporate them into
the base exUserFolder code, they can be written as normal Zope Products,
(i.e. you can distribute new sources independently of exUserFolder).

There are three authentication sources provided OOTB;

o pgAuthSource -- Postgresql Authentication Source
Actually this is pretty generic, and could be used for most SQL databases,
the schema isn't all that advanced either.

This source allows you to specify the table, and the name of each of the
columns (username, password, roles), so you can use an existing database.


All ZSQL Methods are available inside the pgAuthSource folder for editing.
You need to have a DB Connection already in place for use.

o usAuthSource -- User Supplied Authentication
This is similar to Generic User Folder, or Generic User Sources for
Login Manager. You provide a set of methods;

createUser    -- if you want to create users.
cryptPassword -- if you want to encrypt passwords.
listUsers     -- return a list of userIds.
listOneUser   -- return a dictionary containing the username, password, and 
                 a list of roles
getUsers      -- return a list of users ala listOneUser but lots of them.

that's it. listOneUser is mandatory.

There is an example of ExternalMethods you could use to create an 'sql'
user source in the Extensions directory.

o etcAuthSource -- File Based Authentication
This is etcUserFolder reworked to be a plugin for this. Since I used
etcUserFolder as a base for this product, I might as well add the functionality
in.

Each of the plugins has a 'manage_addForm' that is called when the User Folder
is added, so that parameters can be garnered from the user (pg*Source e.g.
get the dbconnection)

etcAuthSource doesn't allow roles to be set, although it does ask for
a default role to be assigned to a user (which it dutifully does).


There are two property sources provided:

o pgPropertySource -- Postgresql Property Source
A very naive sql implementation for properties, works fine, I wouldn't want
to load it up too high though.

o zodbProperySource -- ZODB Property Source
This is a very simple property keeper, and is more available as an example
of what functionality needs to be provided.

There is a postUserCreate method which you can replace with anything really,
if you want to do something once a user is created (send an email to someone,
page someone...)

You can mix-n-match authentication methods and property methods.

You can have cookie or standard (Basic) authentication.

docLogin and docLogout methods are present in the ZODB for editing, because
you will hate the way the default login and logout pages look d8)

The various plugins need some more configurable options atm, but, it 
shouldn't be that much of a drama to add them in soon.

Arbitrary properties can be set on a user (at least if the PropertySource
is written correctly they can).

<dtml-call "AUTHENTICATED_USER.setProperty(key, value)">
<dtml-if "AUTHENTICATED_USER.hasProperty(key)">
<dtml-var "AUTHENTICATED_USER.getProperty(key, defaultValue)">
<dtml-var "AUTHENTICATED_USER['key']">

Will all work (assuming the user is logged in).

When creating a new user any fields with user_ will be set as properties.
So 'user_email' field will create an 'email' property. You just have to
provide the input form, and exUserFolder will do the rest.

This has only been lightly tested, but, it seems to work just fine.



