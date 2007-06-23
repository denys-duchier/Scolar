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


def pageFooter(canvas, doc, logo):
    "Add footer on page"
    width = PAGE_WIDTH - doc.pageTemplate.left_p - doc.pageTemplate.right_p
    foot = Frame( doc.pageTemplate.left_p, 1.2*cm,
                  width, 1.3*cm,
                  leftPadding=0, rightPadding=0,
                  topPadding=0, bottomPadding=0,                  
                  id="monfooter", showBoundary=1 )

    LeftFootStyle = reportlab.lib.styles.ParagraphStyle({})
    LeftFootStyle.fontName = SCOLAR_FONT
    LeftFootStyle.fontSize = SCOLAR_FONT_SIZE_FOOT
    LeftFootStyle.leftIndent = 0
    LeftFootStyle.firstLineIndent = 0
    RightFootStyle = reportlab.lib.styles.ParagraphStyle({})
    RightFootStyle.fontName = SCOLAR_FONT
    RightFootStyle.fontSize =  SCOLAR_FONT_SIZE_FOOT
    RightFootStyle.alignment = TA_RIGHT 
    p = Paragraph( SU("Université Paris 13"), LeftFootStyle)
    # numero page: np = Paragraph( "%d" % doc.page, RightFootStyle)
    tabstyle = TableStyle( [ ('LEFTPADDING', (0,0), (-1,-1), 0 ),
                             ('RIGHTPADDING',(0,0), (-1,-1), 0 ),
                             ('ALIGN', (0,0), (-1, -1), 'RIGHT'),
                             ('INNERGRID', (0,0), (-1,-1), 0.25, black),
                             ])
    tab = Table( [ ( p, logo) ], style=tabstyle )             
    
    foot.addFromList( [tab], canvas )


class CourrierIndividuelTemplate(PageTemplate) :
    """Template pour courrier avisant des decisions de jury (1 page /etudiant)
    """
    def __init__(self, document, pagesbookmarks={},
                 author=None, title=None, subject=None,
                 margins = (0,0,0,0), # additional margins in mm (left,top,right, bottom)
                 image_dir = ''):
        """Initialise our page template."""
        self.pagesbookmarks = pagesbookmarks
        self.pdfmeta_author = author
        self.pdfmeta_title = title
        self.pdfmeta_subject = subject
        self.image_dir = image_dir 
        # Our doc is made of a single frame
        left, top, right, bottom = margins # marge additionnelle en mm
        # marges du Frame principal
        self.bot_p = 2.5*cm 
        self.left_p = 2.5*cm
        self.right_p = 2.5*cm
        self.top_p = 2*cm

        content = Frame(
            self.left_p + left*mm,
            self.bot_p + bottom*mm,
            document.pagesize[0] - self.right_p-self.left_p - left*mm-right*mm,
            document.pagesize[1] - self.top_p-self.bot_p - top*mm-bottom*mm)
        
        PageTemplate.__init__(self, "PVJuryTemplate", [content])

        # self.logo_footer = Image( image_dir + '/logo_footer.jpg', height=0.8*cm, width=1.5*cm )
        self.logo_footer = None
        
    def beforeDrawPage(self, canvas, doc) :
        """Draws a logo and an contribution message on each page."""        
        canvas.saveState()
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
        # ---- Footer
        #pageFooter(canvas, doc, self.logo_footer )
        #
        canvas.restoreState()

def pdf_lettres_individuelles(znotes, formsemestre_id, etudids=None):
    """Document PDF avec les lettres d'avis pour les etudiants mentionnés
    (tous ceux du semestre, ou la liste indiquée par etudids)
    Renvoie pdf data
    """

    dpv = sco_pvjury.dict_pvjury(znotes, formsemestre_id, etudids=etudids, with_prev=True)
    sem = znotes.do_formsemestre_list(args={ 'formsemestre_id' : formsemestre_id } )[0]
    params = {
        'dateJury' : dpv['date'],
        'deptName' : "Réseaux et Télécommunications",
        'nomDirecteur' : 'Joseph CERRATO',
        'htab1' : "10cm", # lignes à droite (entete, signature)
        'htab2' : "1cm",
    }
    
    bookmarks = {}
    objects = [] # list of PLATYPUS objects
    i = 1
    for e in dpv['decisions']:
        etud = znotes.getEtudInfo(e['identite']['etudid'], filled=True)[0]
        params['nomEtud'] = etud['nomprenom']
        bookmarks[i] = etud['nomprenom']
        objects += pdf_lettre_individuelle( dpv['formsemestre'], e, etud, params ) 
        objects.append( PageBreak() )
        i += 1
    
    # ----- Build PDF
    report = cStringIO.StringIO() # in-memory document, no disk file
    document = BaseDocTemplate(report)
    document.addPageTemplates( CourrierIndividuelTemplate(
        document,
        author='%s %s (E. Viennet)' % (SCONAME, SCOVERSION),
        title='Lettres décision %s' % sem['titre_num'],
        subject='Décision jury',
        pagesbookmarks=bookmarks,
        image_dir = znotes.file_path + '/logos/' ))
    
    document.build(objects)
    data = report.getvalue()
    return data


def pdf_lettre_individuelle( sem, decision, etud, params ):
    """
    Renvoie une liste d'objets PLATYPUS pour intégration
    dans un autre document.
    """    
    #
    Se = decision['Se']
    if Se.semestre_non_terminal:
        t = "jury de passage de Semestre %d en Semestre %d" % (sem['semestre_id'],sem['semestre_id']+1)
        s = "jury de passage de semestre"
    else:
        t = "jury de délivrance du diplôme"
        s = t
    objects = []
    style = reportlab.lib.styles.ParagraphStyle({})
    style.fontSize= 12
    style.fontName= 'Times-Roman'
    style.leading = 18
    style.alignment = TA_JUSTIFY

    params['prev_semestre_id'] = decision['prev']['semestre_id']
    params['prev_code_descr']  = decision['prev_code_descr']
    params['semestre_id'] = sem['semestre_id']
    params['decision_sem_descr'] = decision['decision_sem_descr']
    params['t'] = t
    params['s'] = s
    params['decisions_ue_descr'] = decision['decisions_ue_descr']
    # Haut de la lettre:
    objects += makeParas("""
<para leftindent="%(htab1)s">Villetaneuse, le %(dateJury)s
</para>
<para leftindent="%(htab1)s" spaceBefore="25mm">%(nomDirecteur)s
</para>
<para leftindent="%(htab1)s">Directeur de l'IUT
</para>
<para leftindent="%(htab1)s" spaceBefore="10mm">à <b>%(nomEtud)s</b>
</para>
<para spaceBefore="25mm" fontSize="14">
<b>Objet : %(t)s 
du département %(deptName)s</b>
</para>
<para spaceBefore="10mm" fontSize="14">
Le %(s)s du département %(deptName)s
s'est réuni le %(dateJury)s. Les décisions vous concernant sont :
</para>""" % params, style )
    # Affichage de la décision du semestre précédent s'il existe:
    if decision['prev_decision_sem']:
        objects += makeParas("""
        <para leftindent="%(htab2)s" spaceBefore="5mm" fontSize="14">
        <b>Décision du semestre antérieur S%(prev_semestre_id)s :</b> %(prev_code_descr)s
        </para>
        """ % params, style )                             
    
    # Décision semestre courant:
    objects += makeParas("""
    <para leftindent="%(htab2)s" spaceBefore="5mm" fontSize="14">
    <b>Décision du semestre S%(semestre_id)s :</b> %(decision_sem_descr)s
    </para>""" % params, style )

    # UE capitalisées:
    if decision['decisions_ue'] and decision['decisions_ue_descr']:
        objects += makeParas("""
    <para leftindent="%(htab2)s" spaceBefore="0mm" fontSize="14">
    <b>Unités d'Enseignement de S%(semestre_id)s capitalisées : </b>%(decisions_ue_descr)s</b>
    </para>""" % params, style )
    
    # Informations sur compensations
    if decision['observation']:
        objects += makeParas("""
    <para leftindent="%s" spaceBefore="0mm" fontSize="14">
    <b>Observation :</b> %s.
    </para>""" % (params['htab2'], decision['observation']), style )
    
    # Autorisations de passage
    if decision['autorisations']:
        if len(decision['autorisations']) > 1:
            s = 's'
        else:
            s = ''
        objects += makeParas("""
    <para spaceBefore="10mm" fontSize="14">
    Vous êtes autorisé%s à continuer dans le%s semestre%s : <b>%s</b>
    </para>""" % (etud['ne'], s, s, decision['autorisations_descr']), style )



    # Signature
    objects += makeParas("""
<para leftindent="%(htab1)s" spaceBefore="25mm">
Pour le Directeur de l'IUT
</para>
<para leftindent="%(htab1)s">
et par délégation
</para>
<para leftindent="%(htab1)s">
Le chef du département
</para>
    """ % params, style )
    return objects

    
