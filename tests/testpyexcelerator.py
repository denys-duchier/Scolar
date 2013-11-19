# -*- mode: python -*-
# -*- coding: utf-8 -*-

import sys
from pyExcelerator import *

#UnicodeUtils.DEFAULT_ENCODING = 'utf-8'

wb = Workbook()

title = "Essai"

ws = wb.add_sheet(u"çelé")

ws.write(1,1, "çeci où".decode('utf-8'))
ws.write(2,2, "Hélène".decode('utf-8'))

wb.save("toto.xls")

