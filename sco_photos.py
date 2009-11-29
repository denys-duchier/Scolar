# -*- mode: python -*-
# -*- coding: iso8859-15 -*-

##############################################################################
#
# Gestion scolarite IUT
#
# Copyright (c) 2001 - 2010 Emmanuel Viennet.  All rights reserved.
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA  02111-1307  USA
#
#   Emmanuel Viennet      emmanuel.viennet@gmail.com
#
##############################################################################

"""(Nouvelle) gestion des photos d'etudiants

Note: jusqu'à novembre 2009, les images étaient stockées dans Zope (ZODB). 

Les images sont maintenant stockées en dehors de Zope, dans static/photos
L'attribut "photo_filename" de la table identite donne le nom du fichier image, sans extension.
Toutes les images sont converties en jpg, et stockées dans photo_filename.jpg en taille originale.
Elles sont aussi réduites en 90 pixels de hauteur, et stockées dans photo_filename.h90.jpg

Opérations:
 - obtenir le tag html pour un etudiant (reduit ou entier)
 - stocker une nouvelle image

"""

import random
import urllib2
import traceback
from PIL import Image
from cStringIO import StringIO
import glob

from sco_utils import *
from notes_log import log
from notesdb import *
import scolars
import sco_portal_apogee
from scolog import logdb

REL_DIR = '/static/photos/' # path relative to base URL (must ends with /)
PHOTO_DIR = SCO_SRCDIR + '/' + REL_DIR # absolute path, ending with /
EXT = '.jpg'
JPG_QUALITY = 0.92
REDUCED_HEIGHT = 90 # pixels
MAX_FILE_SIZE = 1024*1024 # max allowed size for uploaded image, in bytes
H90 = '.h90' # suffix for reduced size images

def photo_portal_url(context, etud):
    """Returns external URL to retreive photo on portal,
    or None if no portal configured"""
    portal_url = sco_portal_apogee.get_portal_url(context)
    if portal_url and etud['code_nip']:
        return  portal_url + '/getPhoto.php?nip=' + etud['code_nip']
    else:
        return None

def url_from_rel_path(path):
    """Get URL path from relative path.
    Currently, relative paths are /static/photos/F*/*jpg
    and URL are /ScoDoc/static/...
    """
    return '/ScoDoc' + path

# Public access points:
def etud_photo_url(context, etud, REQUEST=None):
    """url (path) to the image of the student, in small size.
    If no available image, give a tag to default image.
    For backward compatibility, search for images in ZODB if not found in filesystem
    (ZODB image is copied to filesystem).
    If a portal is configured, link to it.
    """
    path = has_photo(context, etud, version=H90)
    if path:
        path = url_from_rel_path(path)
    else:
        # Image in ZODB ? (backward compatibility)
        if zope_has_photo(context, etud):
            # in ZODB: copy to fs and get new path
            path = url_from_rel_path(copy_zope_photo_to_fs(context, etud, REQUEST=REQUEST))
        else:
            # Portail ?
            path = photo_portal_url(context, etud)
            if not path:
                # fallback: Photo "inconnu"
                path = url_from_rel_path(unknown_image_path())
            else:
                # essaie de copier la photo du portail
                new_path, diag = copy_portal_photo_to_fs(context, etud, REQUEST=REQUEST)
                if new_path: # success, use local fs url:
                    path = url_from_rel_path(new_path)
    return path

def etud_photo_is_local(context, etud):
    return has_photo(context, etud)

def etud_photo_html(context, etud, title=None, REQUEST=None):
    """HTML img tag for the photo, in small size.
    """
    path = etud_photo_url(context, etud, REQUEST=REQUEST)
    nom = etud.get('nomprenom', etud['nom'])
    if title is None:
        title = nom
    return '<img src="%s" alt="photo %s" title="%s" height="%s" border="0" />' % (path, nom, title, REDUCED_HEIGHT)

def etud_photo_orig_html(context, etud):
    """HTML img tag for the photo, in full size.
    Full-size images are always stored locally in the filesystem.
    They are the original uploaded images, converted in jpeg.
    """
    path = has_photo(context, etud)
    if not path:
        path = unknown_image_path()
    return '<img src="%s" alt="photo %s" title="%s" border="0" />' % (path, etud['nomprenom'], etud['nomprenom'])

def has_photo(context, etud, version=''):
    """Returns (relative) path if etud has a photo (in the filesystem), or False"""
    path = get_photo_rel_path(etud)
    if path and os.path.exists(SCO_SRCDIR + '/' + path + version + EXT):
        return path + version + EXT
    else:
        return False

def store_photo(context, etud, data, REQUEST=None):
    """Store image for this etud.
    If there is an existing photo, it is erased and replaced.
    data is a string with image raw data.

    Update database to store filename.

    Returns (status, msg)
    """
    # basic checks
    filesize = len(data)
    if filesize < 10 or filesize > MAX_FILE_SIZE:
        return 0, 'Fichier image de taille invalide ! (%d)' % filesize
    filename = save_image(context, etud['etudid'], data)
    # update database:
    etud['photo_filename'] = filename
    etud['foto'] = None
    
    cnx = context.GetDBConnexion()
    scolars.identite_edit_nocheck(cnx, etud)
    cnx.commit()
    #
    if REQUEST:
        logdb(REQUEST,cnx,method='changePhoto',msg=filename,etudid=etud['etudid'])
    #
    return 1, 'ok'

def suppress_photo(context, etud, REQUEST=None):
    """Suppress a photo"""
    log('suppress_photo etudid=%s' % etud['etudid'])
    rel_path = has_photo(context, etud)
    # 1- remove ref. from database
    etud['photo_filename'] = None
    cnx = context.GetDBConnexion()
    scolars.identite_edit_nocheck(cnx, etud)
    cnx.commit()
    # 2- erase images files
    log('rel_path=%s'%rel_path)
    if rel_path:
        # remove extension and glob
        rel_path = rel_path[:-len(EXT)]
        filenames = glob.glob( SCO_SRCDIR + '/' + rel_path + '*' + EXT )
        for filename in filenames:
            log('removing file %s' % filename)
            os.remove(filename)
    # 3- log
    if REQUEST:
        logdb(REQUEST,cnx,method='changePhoto',msg='suppression', etudid=etud['etudid'])


# ---------------------------------------------------------------------------
# Internal functions

def unknown_image_path():
    """Relative path to default image, used when we don't have a photo."""
    return REL_DIR + 'unknown.jpg'

def save_image(context, etudid, data):
    """img_file is a file-like object.
    Save image in JPEG in 2 sizes (original and h90).
    Returns filename (relative to PHOTO_DIR), without extension.
    """
    data_file = StringIO()
    data_file.write(data)
    data_file.seek(0)
    img = Image.open(data_file)
    filename = get_new_filename(context, etudid)
    path = PHOTO_DIR + filename
    log('saving %dx%d jpeg to %s' % (img.size[0], img.size[1], path))
    img.save(path + EXT, format = 'JPEG', quality = 92.)
    # resize:
    img = scale_height(img)
    log('saving %dx%d jpeg to %s.h90' % (img.size[0], img.size[1], filename))
    img.save(path + H90 + EXT, format = 'JPEG', quality = 92.)
    return filename

def scale_height(img, W=None, H=REDUCED_HEIGHT):
    if W is None:
        # keep aspect
        W = (img.size[0] * H) / img.size[1]
    img.thumbnail((W, H), Image.ANTIALIAS)
    return img

def get_photo_rel_path(etud):
    if not etud['photo_filename']:
        return None
    else:
        return REL_DIR + etud['photo_filename']

def get_new_filename(context, etudid):
    """Constructs a random filename to store a new image.
    The path is constructed as: Fxx/etudid
    """
    dept = context.DeptId()
    return find_new_dir() + dept + '_' + etudid

def find_new_dir():
    """select randomly a new subdirectory to store a new file.
    We define 1000 subdirectories named from F00 to F99.
    Returns a path relative to the PHOTO_DIR.
    """
    d = 'F' + '%02d' % random.randint(0,99)
    path = PHOTO_DIR + d
    if not os.path.exists(path):
        # create subdirectory
        log('creating directory %s' % path)
        os.mkdir(path)
    return d + '/'

def zope_has_photo(context, etud):
    """True if photo in ZODB"""
    img = None
    try:
        img = getattr(context.Fotos, foto)
    except:
        try:
            img = getattr(context.Fotos, foto + '.h90.jpg' )
        except:
            pass
    return img is not None

def copy_zope_photo_to_fs(context, etud, REQUEST=None):
    """Copy the photo from ZODB to local fs
    Clear 'foto' attribute in DB,
    but does not change ZODB.
    """
    # get Zope photo
    foto = etud['foto']
    try:
        img = getattr(self.Fotos, foto)
    except:
        img = getattr(self.Fotos, foto + '.h90.jpg' )
    log('copying zope image %s to local fs' % foto)
    status, msg = store_photo(context, etud, img.data, REQUEST=REQUEST)
    return has_photo(context, etud)

def copy_portal_photo_to_fs(context, etud, REQUEST=None):
    """Copy the photo from portal (distant website) to local fs.
    Returns rel. path or None if copy failed, a a diagnotic message
    """
    etudid = etud['etudid']
    url = photo_portal_url(context, etud)
    if not url:
        return None, '%s: pas de code NIP' % context.nomprenom(etud)
    f = None
    try:
        log('copy_portal_photo_to_fs: getting %s' % url)
        f = urllib2.urlopen(url) # in python 2.6, should use a timeout
    except:
        log('download failed: exception:\n%s' % traceback.format_exc())        
        return None, '%s: erreur chargement de %s' % (context.nomprenom(etud), url)
    if not f:
        log('download failed')
        return None, '%s: erreur chargement de %s' % (context.nomprenom(etud), url)
    data = f.read()
    status, diag = store_photo(context, etud, data, REQUEST=REQUEST)
    if status == 1:
        log('copy_portal_photo_to_fs: copied %s' % url)
        return has_photo(context, etud), '%s: photo chargée' % context.nomprenom(etud)
    else:
        return None, '%s: <b>%s</b>' % (context.nomprenom(etud), diag)
