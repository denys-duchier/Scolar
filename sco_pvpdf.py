# -*- mode: python -*-
# -*- coding: iso8859-15 -*-

##############################################################################
#
# Gestion scolarite IUT
#
# Copyright (c) 2001 - 2006 Emmanuel Viennet.  All rights reserved.
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
#   Emmanuel Viennet      emmanuel.viennet@viennet.net
#
##############################################################################

"""Edition des PV de jury
"""

from sco_pdf import *
import sco_pvjury
import sco_codes_parcours
from sco_utils import *
from sco_pdf import PDFLOCK

LOGO_FOOTER_ASPECT = CONFIG.LOGO_FOOTER_ASPECT # XXX A AUTOMATISER
LOGO_FOOTER_HEIGHT = CONFIG.LOGO_FOOTER_HEIGHT * mm
LOGO_FOOTER_WIDTH  = LOGO_FOOTER_HEIGHT*CONFIG.LOGO_FOOTER_ASPECT

LOGO_HEADER_ASPECT = CONFIG.LOGO_HEADER_ASPECT # XXX logo IUTV (A AUTOMATISER)
LOGO_HEADER_HEIGHT = CONFIG.LOGO_HEADER_HEIGHT * mm
LOGO_HEADER_WIDTH  = LOGO_HEADER_HEIGHT*CONFIG.LOGO_HEADER_ASPECT

def pageFooter(canvas, doc, logo, preferences):
    "Add footer on page"
    width = doc.pagesize[0] # - doc.pageTemplate.left_p - doc.pageTemplate.right_p
    foot = Frame( 0.1*mm, 0.2*cm,
                  width-1*mm, 2*cm,
                  leftPadding=0, rightPadding=0,
                  topPadding=0, bottomPadding=0,                  
                  id="monfooter", showBoundary=0 )

    LeftFootStyle = reportlab.lib.styles.ParagraphStyle({})
    LeftFootStyle.fontName = preferences['SCOLAR_FONT']
    LeftFootStyle.fontSize = preferences['SCOLAR_FONT_SIZE_FOOT']
    LeftFootStyle.leftIndent = 0
    LeftFootStyle.firstLineIndent = 0
    LeftFootStyle.alignment = TA_RIGHT
    RightFootStyle = reportlab.lib.styles.ParagraphStyle({})
    RightFootStyle.fontName = preferences['SCOLAR_FONT']
    RightFootStyle.fontSize = preferences['SCOLAR_FONT_SIZE_FOOT']
    RightFootStyle.alignment = TA_RIGHT 

    p = makeParas( """<para>%s</para><para>%s</para>"""
                   % (preferences['INSTITUTION_NAME'], preferences['INSTITUTION_ADDRESS']),
                   LeftFootStyle)
    
    np = Paragraph( '<para fontSize="14">%d</para>' % doc.page, RightFootStyle)
    tabstyle = TableStyle( [ ('LEFTPADDING', (0,0), (-1,-1), 0 ),
                             ('RIGHTPADDING',(0,0), (-1,-1), 0 ),
                             ('ALIGN', (0,0), (-1, -1), 'RIGHT'),
                             #('INNERGRID', (0,0), (-1,-1), 0.25, black),
                             ('LINEABOVE', (0,0), (-1,0), 0.5, black),
                             ('VALIGN', (1,0), (1,0), 'MIDDLE' ),
                             ('RIGHTPADDING',(-1,0), (-1,0), 1*cm ),
                             ])
    tab = Table( [ (p, logo, np) ], style=tabstyle, colWidths=(None,LOGO_FOOTER_WIDTH+2*mm, 2*cm) )             
    canvas.saveState() # is it necessary ?
    foot.addFromList( [tab], canvas )
    canvas.restoreState()

def pageHeader(canvas, doc, logo, preferences):
    height = doc.pagesize[1]
    head = Frame( -22*mm, height - 13*mm - LOGO_FOOTER_HEIGHT,
                  10*cm, LOGO_HEADER_HEIGHT + 2*mm,
                  leftPadding=0, rightPadding=0,
                  topPadding=0, bottomPadding=0,                  
                  id="monheader", showBoundary=0 )
    canvas.saveState() # is it necessary ?
    head.addFromList([logo], canvas)
    canvas.restoreState()

class CourrierIndividuelTemplate(PageTemplate) :
    """Template pour courrier avisant des decisions de jury (1 page /etudiant)
    """
    def __init__(self, document, pagesbookmarks={},
                 author=None, title=None, subject=None,
                 margins = (0,0,0,0), # additional margins in mm (left,top,right, bottom)
                 image_dir = '',
                 preferences=None # dictionnary with preferences, required
                 ):
        """Initialise our page template."""
        self.pagesbookmarks = pagesbookmarks
        self.pdfmeta_author = author
        self.pdfmeta_title = title
        self.pdfmeta_subject = subject
        self.image_dir = image_dir 
        self.preferences = preferences
        # Our doc is made of a single frame
        left, top, right, bottom = margins # marge additionnelle en mm
        # marges du Frame principal
        self.bot_p = 2*cm 
        self.left_p = 2.5*cm
        self.right_p = 2.5*cm
        self.top_p = 0*cm
        log("margins=%s" % str(margins))
        content = Frame(
            self.left_p + left*mm,
            self.bot_p + bottom*mm,
            document.pagesize[0] - self.right_p-self.left_p - left*mm-right*mm,
            document.pagesize[1] - self.top_p-self.bot_p - top*mm-bottom*mm)
        
        PageTemplate.__init__(self, "PVJuryTemplate", [content])

        self.logo_footer = None
        
    def beforeDrawPage(self, canvas, doc) :
        """Draws a logo and an contribution message on each page."""        
        # ---- Add some meta data and bookmarks
        if self.pdfmeta_author:
            canvas.setAuthor(SU(self.pdfmeta_author))
        if self.pdfmeta_title:
            canvas.setTitle(SU(self.pdfmeta_title))
        if self.pdfmeta_subject:
            canvas.setSubject(SU(self.pdfmeta_subject))
        bm = self.pagesbookmarks.get(doc.page,None)
        if bm != None:
            key = bm
            txt = SU(bm)
            canvas.bookmarkPage(key)
            canvas.addOutlineEntry(txt,bm)


class PVTemplate(CourrierIndividuelTemplate):
    def __init__(self, document, 
                 author=None, title=None, subject=None,
                 margins = (0,23,0,5), # additional margins in mm (left,top,right, bottom)
                 image_dir = '',
                 preferences=None # dictionnary with preferences, required
                 ):
        
        CourrierIndividuelTemplate.__init__(self, document, author=author, title=title, subject=subject,
                                            margins=margins, image_dir=image_dir, 
                                            preferences=preferences)
        self.logo_footer = Image( image_dir + '/logo_footer.jpg', height=LOGO_FOOTER_HEIGHT, width=LOGO_FOOTER_WIDTH )
        self.logo_header = Image( image_dir + '/logo_header.jpg', height=LOGO_HEADER_HEIGHT, width=LOGO_HEADER_WIDTH )

    def beforeDrawPage(self, canvas, doc) :
        CourrierIndividuelTemplate.beforeDrawPage(self, canvas, doc)
        # --- Add footer
        pageFooter(canvas, doc, self.logo_footer, self.preferences )
        # --- Add header
        pageHeader(canvas, doc, self.logo_header, self.preferences )

def pdf_lettres_individuelles(context, formsemestre_id, etudids=None, dateJury='', signature=None):
    """Document PDF avec les lettres d'avis pour les etudiants mentionn�s
    (tous ceux du semestre, ou la liste indiqu�e par etudids)
    Renvoie pdf data
    """

    dpv = sco_pvjury.dict_pvjury(context, formsemestre_id, etudids=etudids, with_prev=True)
    if not dpv:
        return ''
    # Ajoute infos sur etudiants
    etuds = [ x['identite'] for x in dpv['decisions']]
    context.fillEtudsInfo(etuds)
    #
    sem = context.get_formsemestre(formsemestre_id)
    params = {
        'dateJury' : dateJury,
        'deptName' : context.get_preference('DeptName', formsemestre_id), 
        'DirectorName' : context.get_preference('DirectorName', formsemestre_id),
        'DirectorTitle' : context.get_preference('DirectorTitle', formsemestre_id),
        'titreFormation' : dpv['formation']['titre_officiel'],
        'htab1' : "8cm", # lignes � droite (entete, signature)
        'htab2' : "1cm",
    }
    
    bookmarks = {}
    objects = [] # list of PLATYPUS objects
    i = 1
    for e in dpv['decisions']:
        if e['decision_sem']: # decision prise
            etud = context.getEtudInfo(e['identite']['etudid'], filled=True)[0]
            params['nomEtud'] = etud['nomprenom']
            bookmarks[i] = etud['nomprenom']
            objects += pdf_lettre_individuelle( dpv['formsemestre'], e, etud, params, 
                                                signature, context=context ) 
            objects.append( PageBreak() )
            i += 1
    # Param�tres de mise en page
    margins = (context.get_preference('left_margin', formsemestre_id),
               context.get_preference('top_margin', formsemestre_id),
               context.get_preference('right_margin', formsemestre_id),
               context.get_preference('bottom_margin', formsemestre_id))  
    # ----- Build PDF
    report = cStringIO.StringIO() # in-memory document, no disk file
    document = BaseDocTemplate(report)
    document.addPageTemplates( CourrierIndividuelTemplate(
        document,
        author='%s %s (E. Viennet)' % (SCONAME, SCOVERSION),
        title='Lettres d�cision %s' % sem['titreannee'],
        subject='D�cision jury',
        margins=margins,
        pagesbookmarks=bookmarks,
        image_dir = context.file_path + '/logos/' ))
    
    document.build(objects)
    data = report.getvalue()
    return data


def _descr_jury(sem, semestre_non_terminal):
    if semestre_non_terminal:
        t = "passage de Semestre %d en Semestre %d" % (sem['semestre_id'],sem['semestre_id']+1)
        s = "passage de semestre"
    else:
        t = "d�livrance du dipl�me"
        s = t
    return t, s # titre long, titre court

def pdf_lettre_individuelle( sem, decision, etud, params, signature=None, context=None ):
    """
    Renvoie une liste d'objets PLATYPUS pour int�gration
    dans un autre document.
    """
    #
    formsemestre_id = sem['formsemestre_id']
    Se = decision['Se']
    t, s = _descr_jury(sem, Se.semestre_non_terminal)
    objects = []
    style = reportlab.lib.styles.ParagraphStyle({})
    style.fontSize= 12
    style.fontName= context.get_preference('PV_FONTNAME', formsemestre_id)
    style.leading = 18
    style.alignment = TA_JUSTIFY

    params['semestre_id'] = sem['semestre_id']
    params['decision_sem_descr'] = decision['decision_sem_descr']
    params['Type'] = t # type de jury (passage ou delivrance)
    params['TypeAbbrv'] = s # idem, abbr�g�
    params['decisions_ue_descr'] = decision['decisions_ue_descr']
    params['city'] = context.get_preference('INSTITUTION_CITY', formsemestre_id)
    if decision['prev_decision_sem']:
        params['prev_semestre_id'] = decision['prev']['semestre_id']
        params['prev_code_descr']  = decision['prev_code_descr']
    
    # Haut de la lettre:
    objects += makeParas("""
<para>%(DirectorName)s
</para>
<para>%(DirectorTitle)s
</para>

<para leftindent="%(htab1)s">%(city)s, le %(dateJury)s
</para>
<para leftindent="%(htab1)s" spaceBefore="10mm">� <b>%(nomEtud)s</b>
</para>""" % params, style)
    # Adresse �tudiant:
    i = decision['identite']
    objects += makeParas("""
    <para leftindent="%s">%s</para>
    <para leftindent="%s">%s %s</para>
    """ % (params['htab1'], i['domicile'],
           params['htab1'], i['codepostaldomicile'], i['villedomicile']),
           style)
    #
    objects += makeParas("""
<para spaceBefore="25mm" fontSize="14">
<b>Objet : jury de %(Type)s 
du d�partement %(deptName)s</b>
</para>
<para spaceBefore="10mm" fontSize="14">
Le jury de %(TypeAbbrv)s du d�partement %(deptName)s
s'est r�uni le %(dateJury)s. Les d�cisions vous concernant sont :
</para>""" % params, style )
    # Affichage de la d�cision du semestre pr�c�dent s'il existe:
    if decision['prev_decision_sem']:
        objects += makeParas("""
        <para leftindent="%(htab2)s" spaceBefore="5mm" fontSize="14">
        <b>D�cision du semestre ant�rieur S%(prev_semestre_id)s :</b> %(prev_code_descr)s
        </para>
        """ % params, style )                             
    
    # D�cision semestre courant:
    if sem['semestre_id'] >= 0:
        params['s'] = 'du semestre S%s' % sem['semestre_id']
    else:
        params['s'] = ''
    objects += makeParas("""
    <para leftindent="%(htab2)s" spaceBefore="5mm" fontSize="14">
    <b>D�cision %(s)s :</b> %(decision_sem_descr)s
    </para>""" % params, style )

    # UE capitalis�es:
    if decision['decisions_ue'] and decision['decisions_ue_descr']:
        objects += makeParas("""
    <para leftindent="%(htab2)s" spaceBefore="0mm" fontSize="14">
    <b>Unit�s d'Enseignement %(s)s capitalis�es : </b>%(decisions_ue_descr)s</b>
    </para>""" % params, style )
    
    # Informations sur compensations
    if decision['observation']:
        objects += makeParas("""
    <para leftindent="%s" spaceBefore="0mm" fontSize="14">
    <b>Observation :</b> %s.
    </para>""" % (params['htab2'], decision['observation']), style )
    
    # Autorisations de passage
    if decision['autorisations'] and Se.semestre_non_terminal:
        if len(decision['autorisations']) > 1:
            s = 's'
        else:
            s = ''
        objects += makeParas("""
    <para spaceBefore="10mm" fontSize="14">
    Vous �tes autoris�%s � continuer dans le%s semestre%s : <b>%s</b>
    </para>""" % (etud['ne'], s, s, decision['autorisations_descr']), style )

    if (not Se.semestre_non_terminal) and decision['decision_sem']:
        if sco_codes_parcours.CODES_SEM_VALIDES.has_key(decision['decision_sem']['code']):
            # Semestre terminal valid� => dipl�me
            objects += makeParas(""" <para spaceBefore="10mm" fontSize="14">
            Vous avez donc obtenu le dipl�me : <b>%(titreFormation)s</b>
            </para>""" % params, style ) 

    # Signature:
    # nota: si semestre terminal, signature par directeur IUT, sinon, signature par
    # chef de d�partement.
    if Se.semestre_non_terminal:
        sig = context.get_preference('PV_LETTER_PASSAGE_SIGNATURE', formsemestre_id) % params
        sig = _simulate_br(sig, '<para leftindent="%(htab1)s">')
        objects += makeParas(("""<para leftindent="%(htab1)s" spaceBefore="25mm">""" + sig + 
                             """</para>""") % params, style ) 
    else:
        sig = context.get_preference('PV_LETTER_DIPLOMA_SIGNATURE', formsemestre_id) % params
        sig = _simulate_br(sig, '<para leftindent="%(htab1)s">')
        objects += makeParas(("""<para leftindent="%(htab1)s" spaceBefore="25mm">""" + sig +
                              """</para>""") % params, style )
        
    if signature:
        objects.append( _make_signature_image(signature, params['htab1'], formsemestre_id, context=context) )
        
    return objects


def _simulate_br(p, para='<para>' ):
    """Reportlab bug turnaround (could be removed in a future version).
    p is a string with Reportlab intra-paragraph XML tags.
    Replaces <br/> (currently ignored by Reportlab) by </para><para>
    """
    l = re.split( r'<.*?br.*?/>', p)
    return ('</para>'+para).join(l)

def _make_signature_image(signature, leftindent, formsemestre_id, context=None):
    "cree un paragraphe avec l'image signature"
    # cree une image PIL pour avoir la taille (W,H)
    from PIL import Image as PILImage
    f = cStringIO.StringIO(signature)
    im = PILImage.open(f)
    width, height = im.size
    pdfheight = 1.1*cm
    f.seek(0,0)

    style = styles.ParagraphStyle( {} )    
    style.leading = 1.*context.get_preference('SCOLAR_FONT_SIZE', formsemestre_id) # vertical space
    style.leftIndent=leftindent
    return Table( [ ('', Image( f, width=width*pdfheight/float(height), height=pdfheight)) ],
                  colWidths = (9*cm, 7*cm) )
                  

    
# ----------------------------------------------
# PV complet, tableau en format paysage

def pvjury_pdf(context, dpv, REQUEST, dateCommission=None, numeroArrete=None, dateJury=None, showTitle=False):
    """Doc PDF r�capitulant les d�cisions de jury
    dpv: result of dict_pvjury
    """
    if not dpv:
        return {}
    formsemestre_id = dpv['formsemestre']['formsemestre_id']
    sem = dpv['formsemestre']
    
    objects = []
    style = reportlab.lib.styles.ParagraphStyle({})
    style.fontSize= 12
    style.fontName= context.get_preference('PV_FONTNAME', formsemestre_id)
    style.leading = 18
    style.alignment = TA_JUSTIFY

    indent = 1*cm
    bulletStyle = reportlab.lib.styles.ParagraphStyle({})
    bulletStyle.fontSize= 12
    bulletStyle.fontName= context.get_preference('PV_FONTNAME', formsemestre_id)
    bulletStyle.leading = 12
    bulletStyle.alignment = TA_JUSTIFY
    bulletStyle.firstLineIndent=0
    bulletStyle.leftIndent=indent
    bulletStyle.bulletIndent=indent
    bulletStyle.bulletFontName='Times-Roman'
    bulletStyle.bulletFontSize=11
    bulletStyle.spaceBefore=5*mm
    bulletStyle.spaceAfter=5*mm
                                   
    t, s = _descr_jury(sem, dpv['semestre_non_terminal'])
    objects += [ Spacer(0,5*mm) ]
    objects += makeParas("""
    <para align="center"><b>Proc�s-verbal de %s du d�partement %s - Session %s</b></para>    
    """ % (t, context.get_preference('DeptName', formsemestre_id), sem['annee']), style)

    if showTitle:
        objects += makeParas("""<para><b>Semestre: %s</b></para>"""%sem['titre'], style)
    if dateJury:
         objects += makeParas("""<para>Jury tenu le %s</para>""" % dateJury, style) 

    objects += makeParas('<para>' 
                         + context.get_preference('PV_INTRO', formsemestre_id)
                         % { 'Decnum' : numeroArrete,
                             'UnivName' : context.get_preference('UnivName', formsemestre_id),
                             'Type' : t,
                             'Date' : dateCommission,
                             } + '</para>', bulletStyle )
    
    objects += makeParas("""<para>Le jury propose les d�cisions suivantes :</para>""", style)
    objects += [ Spacer(0,4*mm) ]
    lines, titles, columns_ids = sco_pvjury.pvjury_table(context, dpv)
    # convert to lists of tuples:
    columns_ids=['etudid'] + columns_ids
    lines = [ [ line.get(x,'') for x in columns_ids ] for line in lines ]
    titles = [ titles.get(x,'') for x in columns_ids ]
    # Make a new cell style and put all cells in paragraphs    
    CellStyle = styles.ParagraphStyle( {} )
    CellStyle.fontSize= context.get_preference('SCOLAR_FONT_SIZE', formsemestre_id)
    CellStyle.fontName= context.get_preference('PV_FONTNAME', formsemestre_id)
    CellStyle.leading = 1.*context.get_preference('SCOLAR_FONT_SIZE', formsemestre_id) # vertical space
    LINEWIDTH = 0.5
    TableStyle = [ ('FONTNAME', (0,0), (-1,0), context.get_preference('PV_FONTNAME', formsemestre_id)),
                   ('LINEBELOW', (0,0), (-1,0), LINEWIDTH, Color(0,0,0)),
                   ('GRID', (0,0), (-1,-1), LINEWIDTH, Color(0,0,0)),
                   ('VALIGN', (0,0), (-1,-1), 'TOP') ]
    titles = [ '<para><b>%s</b></para>' % x for x in titles ]
    Pt = [ [Paragraph(SU(x),CellStyle) for x in line[1:] ] for line in ([titles] + lines) ]
    if dpv['has_prev']:
        widths = (6*cm, 2.8*cm, 2.8*cm, None, None, None)
    else:
        widths = (6*cm, 2.8*cm, None, None, None)
    objects.append( Table( Pt, repeatRows=1, colWidths = widths, style=TableStyle ) )

    # Signature du directeur
    objects += makeParas(
        """<para spaceBefore="10mm" align="right">
        Le %s, %s</para>""" % 
        (context.get_preference('DirectorTitle', formsemestre_id),
         context.get_preference('DirectorName', formsemestre_id)),
        style)

    # L�gende des codes
    codes = sco_codes_parcours.CODES_EXPL.keys()
    codes.sort()
    objects += makeParas( """<para spaceBefore="15mm" fontSize="14">
    <b>Codes utilis�s :</b></para>""", style )
    L = []
    for code in codes:
        L.append( (code, sco_codes_parcours.CODES_EXPL[code]))
    TableStyle2 = [ ('FONTNAME', (0,0), (-1,0), context.get_preference('PV_FONTNAME', formsemestre_id)),
                    ('LINEBELOW', (0,0), (-1,-1), LINEWIDTH, Color(0,0,0)),
                    ('LINEABOVE', (0,0), (-1,-1), LINEWIDTH, Color(0,0,0)),
                    ('LINEBEFORE', (0,0), (0,-1), LINEWIDTH, Color(0,0,0)),
                    ('LINEAFTER', (-1,0), (-1,-1), LINEWIDTH, Color(0,0,0)),
                    ]
    objects.append( Table( [ [Paragraph(SU(x),CellStyle) for x in line ] for line in L ],
                           colWidths = (2*cm, None),
                           style=TableStyle2 ) )
    

    # ----- Build PDF
    report = cStringIO.StringIO() # in-memory document, no disk file
    document = BaseDocTemplate(report)
    document.pagesize = landscape(A4)
    document.addPageTemplates( PVTemplate(
        document,
        author='%s %s (E. Viennet)' % (SCONAME, SCOVERSION),
        title=SU('PV du jury de %s' % sem['titre_num']),
        subject='PV jury',
        image_dir = context.file_path + '/logos/',
        preferences=context.get_preferences(formsemestre_id)))

    document.build(objects)
    data = report.getvalue()
    return data
