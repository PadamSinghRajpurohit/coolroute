import os
import matplotlib
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.units import mm
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.enums import TA_LEFT
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import (BaseDocTemplate, PageTemplate, Frame, Paragraph, Spacer, Table, TableStyle,
                                Image, Preformatted, KeepTogether, PageBreak, ListFlowable, ListItem)

FD = os.path.join(os.path.dirname(matplotlib.__file__), "mpl-data/fonts/ttf")
pdfmetrics.registerFont(TTFont("DV", f"{FD}/DejaVuSans.ttf"))
pdfmetrics.registerFont(TTFont("DV-B", f"{FD}/DejaVuSans-Bold.ttf"))
pdfmetrics.registerFont(TTFont("DV-I", f"{FD}/DejaVuSans-Oblique.ttf"))
pdfmetrics.registerFont(TTFont("DV-BI", f"{FD}/DejaVuSans-BoldOblique.ttf"))
pdfmetrics.registerFont(TTFont("DVM", f"{FD}/DejaVuSansMono.ttf"))
pdfmetrics.registerFontFamily("DV", normal="DV", bold="DV-B", italic="DV-I", boldItalic="DV-BI")

COOL = colors.HexColor("#0b7f86")
HEAT = colors.HexColor("#d4501a")
TREE = colors.HexColor("#3f9a52")
INK = colors.HexColor("#12262e")
MUTED = colors.HexColor("#546a73")
SOFT = colors.HexColor("#e8f1f3")
LINE = colors.HexColor("#c9d8dd")

W, H = A4
M = 18 * mm

ST = {
    "body": ParagraphStyle("body", fontName="DV", fontSize=9.6, leading=14.2, textColor=INK, spaceAfter=5),
    "small": ParagraphStyle("small", fontName="DV", fontSize=8.2, leading=11.5, textColor=MUTED),
    "h1": ParagraphStyle("h1", fontName="DV-B", fontSize=16, leading=20, textColor=COOL, spaceBefore=12, spaceAfter=6),
    "h2": ParagraphStyle("h2", fontName="DV-B", fontSize=11.5, leading=15, textColor=INK, spaceBefore=9, spaceAfter=4),
    "cell": ParagraphStyle("cell", fontName="DV", fontSize=8.6, leading=11.6, textColor=INK),
    "cellb": ParagraphStyle("cellb", fontName="DV-B", fontSize=8.6, leading=11.6, textColor=colors.white),
    "code": ParagraphStyle("code", fontName="DVM", fontSize=7.6, leading=10.2, textColor=INK),
    "bullet": ParagraphStyle("bullet", fontName="DV", fontSize=9.6, leading=14, textColor=INK),
    "call": ParagraphStyle("call", fontName="DV", fontSize=9.3, leading=13.5, textColor=INK),
}


def P(t, s="body"):
    return Paragraph(t, ST[s])


def H1(t):
    return P(t, "h1")


def H2(t):
    return P(t, "h2")


def bullets(items, s="bullet"):
    return ListFlowable([ListItem(Paragraph(i, ST[s]), leftIndent=12, bulletColor=COOL) for i in items],
                        bulletType="bullet", start="•", leftIndent=12, bulletFontSize=9)


def table(rows, widths, header=True, zebra=True, align_right_cols=()):
    data = []
    for ri, r in enumerate(rows):
        data.append([Paragraph(str(c), ST["cellb"] if (header and ri == 0) else ST["cell"]) for c in r])
    t = Table(data, colWidths=widths, repeatRows=1 if header else 0)
    style = [("VALIGN", (0, 0), (-1, -1), "TOP"), ("LINEBELOW", (0, 0), (-1, -1), 0.4, LINE),
             ("TOPPADDING", (0, 0), (-1, -1), 4), ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
             ("LEFTPADDING", (0, 0), (-1, -1), 5), ("RIGHTPADDING", (0, 0), (-1, -1), 5)]
    if header:
        style += [("BACKGROUND", (0, 0), (-1, 0), COOL)]
    if zebra:
        for i in range(1 if header else 0, len(rows)):
            if i % 2 == 0:
                style.append(("BACKGROUND", (0, i), (-1, i), SOFT))
    t.setStyle(TableStyle(style))
    return t


def callout(text, color=COOL):
    t = Table([[Paragraph(text, ST["call"])]], colWidths=[W - 2 * M])
    t.setStyle(TableStyle([("BACKGROUND", (0, 0), (-1, -1), SOFT), ("LINEBEFORE", (0, 0), (0, -1), 3, color),
                           ("LEFTPADDING", (0, 0), (-1, -1), 10), ("RIGHTPADDING", (0, 0), (-1, -1), 10),
                           ("TOPPADDING", (0, 0), (-1, -1), 7), ("BOTTOMPADDING", (0, 0), (-1, -1), 7)]))
    return t


def code(text):
    t = Table([[Preformatted(text.strip("\n"), ST["code"])]], colWidths=[W - 2 * M])
    t.setStyle(TableStyle([("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#f1f5f6")),
                           ("BOX", (0, 0), (-1, -1), 0.4, LINE), ("LEFTPADDING", (0, 0), (-1, -1), 8),
                           ("TOPPADDING", (0, 0), (-1, -1), 6), ("BOTTOMPADDING", (0, 0), (-1, -1), 6)]))
    return t


def fig(path, width_mm=150, caption=None):
    from PIL import Image as PI
    w, h = PI.open(path).size
    wd = width_mm * mm
    img = Image(path, width=wd, height=wd * h / w)
    img.hAlign = "CENTER"
    items = [img]
    if caption:
        items.append(Paragraph(caption, ParagraphStyle("cap", parent=ST["small"], alignment=1, spaceBefore=2, spaceAfter=8)))
    return KeepTogether(items)


def build(filename, title, subtitle, story, tag):
    def on_page(c, d):
        c.saveState()
        c.setFont("DV", 7.5)
        c.setFillColor(MUTED)
        c.drawString(M, 10 * mm, "CoolRoute  ·  Code-E-Manipal 2.0  ·  Track 08 Smart City  ·  PS 31")
        c.drawRightString(W - M, 10 * mm, f"{tag}  ·  Page {d.page}")
        c.setStrokeColor(LINE)
        c.line(M, 14 * mm, W - M, 14 * mm)
        c.restoreState()

    def on_first(c, d):
        c.saveState()
        c.setFillColor(INK)
        c.rect(0, H - 52 * mm, W, 52 * mm, stroke=0, fill=1)
        c.setFillColor(COOL)
        c.rect(0, H - 52 * mm, 8 * mm, 52 * mm, stroke=0, fill=1)
        c.setFillColor(colors.white)
        c.setFont("DV-B", 22)
        c.drawString(M + 4 * mm, H - 28 * mm, title)
        c.setFont("DV", 10.5)
        c.setFillColor(colors.HexColor("#b9d4da"))
        c.drawString(M + 4 * mm, H - 37 * mm, subtitle)
        c.setFont("DV", 8)
        c.drawString(M + 4 * mm, H - 46 * mm, "CoolRoute: Pedestrian Routing with Shade and Heat-Exposure Budgets")
        c.restoreState()
        on_page(c, d)

    doc = BaseDocTemplate(filename, pagesize=A4, leftMargin=M, rightMargin=M, topMargin=M, bottomMargin=20 * mm,
                          title=f"CoolRoute: {title}", author="Team CoolRoute")
    first = Frame(M, 20 * mm, W - 2 * M, H - 20 * mm - 60 * mm, id="f1", leftPadding=0, rightPadding=0, topPadding=0, bottomPadding=0)
    later = Frame(M, 20 * mm, W - 2 * M, H - 20 * mm - M, id="f2", leftPadding=0, rightPadding=0, topPadding=0, bottomPadding=0)
    doc.addPageTemplates([PageTemplate(id="first", frames=[first], onPage=on_first, autoNextPageTemplate="later"),
                          PageTemplate(id="later", frames=[later], onPage=on_page)])
    doc.build(story)
