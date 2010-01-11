
"""Simple image resize using PIL"""

from PIL import Image as PILImage
from cStringIO import StringIO

def ImageScale(img_file, maxx, maxy):
    im = PILImage.open(img_file)
    im.thumbnail((maxx, maxy), PILImage.ANTIALIAS)
    out_file_str = StringIO()
    im.save(out_file_str, im.format)
    out_file_str.seek(0)
    tmp=out_file_str.read()
    out_file_str.close()
    return tmp

def ImageScaleH(img_file, W=None, H=90):
    im = PILImage.open(img_file)
    if W is None:
        # keep aspect
        W = (im.size[0] * H) / im.size[1]
    im.thumbnail((W, H), PILImage.ANTIALIAS)
    out_file_str = StringIO()
    im.save(out_file_str, im.format)
    out_file_str.seek(0)
    tmp=out_file_str.read()
    out_file_str.close()
    return tmp
