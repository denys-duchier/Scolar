#!/usr/bin/env python2.4

"""
ScoDoc post-upgrade script.

This script is runned by upgrade.sh after each SVN update.

Runned as "root" with Zope shutted down and postgresql up.

E. Viennet, june 2008
"""

from scodocutils import *


if os.getuid() != 0:
    log('postupgrade.py: must be run as root')
    sys.exit(1)

# ---

# Upgrade Apache config to serve Static content (svn 706)
log('Trying to upgrade your Apache configuration...')

cfg_file = '/etc/apache2/sites-available/scodoc-site-ssl'
try:
    txt = open(cfg_file).read()
except:
    txt = None
    log('\n*** standard configuration file not found, ignoring')
    log('%s not found' % cfg_file)
    log('(you will have to upgrade your Apache configuration by hand)\n\n')

if txt:
    try:
        if txt.find('Products/ScoDoc/static') == -1:
            txt = txt.replace( 'RewriteRule', """# ScoDoc static content, served directly:
RewriteCond %{HTTP:Authorization}  ^(.*)
RewriteRule ^/ScoDoc/static/(.*) /opt/scodoc/instance/Products/ScoDoc/static/$1 [L]

RewriteRule""", 1)
            log('Renaming config file %s to %s.bak...' % (cfg_file,cfg_file))
            os.rename(cfg_file, cfg_file+'.bak')
            log('Creating new config file...')
            open(cfg_file,'w').write(txt)
            log('Restarting Apache...')
            os.system('/etc/init.d/apache2 restart')
    except:
        log('\n\n*** Failure (upgrading Apache configuration) ***\n')
        raise

# add here actions to perform...

# ---
sys.exit(0)
