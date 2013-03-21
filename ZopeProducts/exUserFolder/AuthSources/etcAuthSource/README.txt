etcUserFolder

  The etcUserFolder product authenticates off of a standard UNIX
  password file.  The password file used can be specified in the
  product.  It is a bit misnamed, because etcUserFolder can
  authenticate off of any file whose first two colon delimited fields
  are uid and crypted password.

  This Product requires the crypt module.  There may, or may not be
  such a module for Win32.  This product may only be compatable with
  UNIX.  Zope does not come with the crypt module (because of the
  non-cross platform nature of it) so you will need to either get the
  cryptmodule.c (from Python) and compile it, or copy your existing
  cryptmodule.so file into Zope's path, or use the one that comes with 
  etcUserFolder which was compiled for RedHat Linux 5.2 (which may not 
  work on your platform).

