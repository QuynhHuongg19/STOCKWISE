"""Presentation-only postprocessor for STOCKWISE PDF output. Preserves original text and metrics."""
from __future__ import annotations
import io
import re
from pathlib import Path
import fitz
from reportlab.pdfgen import canvas
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont

ROOT = Path(__file__).resolve().parent
HERO = ROOT / 'assets' / 'art' / 'hero_starry_sky.webp'
REGULAR = Path('/usr/share/fonts/truetype/noto/NotoSans-Regular.ttf')
BOLD = Path('/usr/share/fonts/truetype/noto/NotoSans-Bold.ttf')
# For Windows, ship fonts separately only when permitted. System fallbacks are used otherwise.

def _font():
    candidates = [
        (ROOT / 'assets' / 'fonts' / 'SW-Regular.ttf',
         ROOT / 'assets' / 'fonts' / 'SW-Bold.ttf'),
        (Path('C:/Windows/Fonts/arial.ttf'), Path('C:/Windows/Fonts/arialbd.ttf')),
        (Path('C:/Windows/Fonts/segoeui.ttf'), Path('C:/Windows/Fonts/segoeuib.ttf')),
        (REGULAR, BOLD),
    ]
    for regular, bold in candidates:
        if regular.is_file() and bold.is_file():
            pdfmetrics.registerFont(TTFont('SW-Regular', str(regular)))
            pdfmetrics.registerFont(TTFont('SW-Bold', str(bold)))
            return 'SW-Regular', 'SW-Bold'
    return 'Helvetica', 'Helvetica-Bold'

# ReportLab stores vectors as RGB triplets before rg/RG operators. Change only
# presentation colors, leaving all text, table data, and chart calculations intact.
COLOR = re.compile(rb'(?<![\d.])((?:\d*\.\d+|\d+))\s+((?:\d*\.\d+|\d+))\s+((?:\d*\.\d+|\d+))\s+(rg|RG)\b')
def _map_color(match):
    r,g,b=(float(match.group(i)) for i in (1,2,3))
    # Pink / magenta fills and strokes (exclude dark black and other chart hues)
    if r > .72 and b > .48 and r > g*1.14 and b > g*1.12:
        if g > .83: target=(.906,.953,1.0) # alternating table rows
        elif g > .70: target=(.76,.865,.99) # light headers
        elif g > .53: target=(.12,.40,.77) # vivid accent / lines
        else: target=(.035,.18,.42) # strong navy
        return ('%.5f %.5f %.5f %s' % (*target,match.group(4).decode())).encode()
    return match.group(0)


def _make_cover(w, h, symbol, title, period, date_text):
    from reportlab.lib.utils import ImageReader
    from reportlab.lib.colors import Color
    from PIL import Image
    from datetime import datetime
    import textwrap

    normal, bold = _font()
    buf = io.BytesIO()
    c = canvas.Canvas(buf, pagesize=(w, h))

    c.setFillColorRGB(.02, .09, .20)
    c.rect(0, 0, w, h, fill=1, stroke=0)

    if HERO.exists():
        im = Image.open(HERO).convert("RGB")
        iw, ih = im.size
        scale = max(w / iw, h / ih)
        nw, nh = iw * scale, ih * scale
        c.drawImage(ImageReader(im), (w-nw)/2, (h-nh)/2,
                    nw, nh, mask="auto")

    # Main translucent panel
    c.setFillColor(Color(.015, .055, .14, alpha=.88))
    c.roundRect(w*.04, h*.48, w*.92, h*.42, 15,
                fill=1, stroke=0)

    left = w*.075
    gold = Color(.96, .78, .38)

    c.setFillColorRGB(1, 1, 1)
    c.setFont(bold, 19)
    c.drawString(left, h*.865, "STOCKWISE")

    c.setStrokeColor(gold)
    c.setLineWidth(2)
    c.line(left, h*.846, w-left, h*.846)

    # Ticker gold badge
    ticker = str(symbol or "STOCKWISE").upper()
    c.setFont(bold, 26)
    badge_width = max(105, pdfmetrics.stringWidth(
        ticker, bold, 26) + 25)

    c.setFillColor(Color(.61, .51, .29, alpha=.95))
    c.roundRect(left, h*.755, badge_width, 46, 22,
                fill=1, stroke=0)

    c.setFillColorRGB(1, 1, 1)
    c.drawString(left+13, h*.770, ticker)

    # Report heading
    c.setFillColor(gold)
    c.setFont(normal, 22)
    c.drawString(left+8, h*.716,
                 "B\u00c1O C\u00c1O PH\u00c2N T\u00cdCH")

    # Company name

    # Use the company name supplied by STOCKWISE for every ticker.
    company = str(title or "").strip()

    import re
    company = re.sub(
        r"(?i)^b?o c?o ph?n t?ch(?: c? phi?u)?\\s*",
        "",
        company
    ).strip(" -|:")

    if not company or company.upper() == ticker:
        company = ticker

    # Align company name to the same left margin as other text.
    max_width = w * .78
    name_x = left + 8
    name_top = h * .626

    size = 35
    words = company.split()

    def wrap_name(font_size):
        rows = []
        current = ""
        for word in words:
            trial = (current + " " + word).strip()
            if current and pdfmetrics.stringWidth(
                trial, bold, font_size
            ) > max_width:
                rows.append(current)
                current = word
            else:
                current = trial
        if current:
            rows.append(current)
        return rows

    rows = wrap_name(size)

    while len(rows) > 2 and size > 26:
        size -= 1
        rows = wrap_name(size)

    if len(rows) == 1:
        name_top = h * .615
    else:
        name_top = h * .645

    c.setFillColorRGB(1, 1, 1)
    c.setFont(bold, size)

    for i, row in enumerate(rows):
        c.drawString(name_x, name_top - i * (size + 12), row)

    # Information panel
    c.setFillColor(Color(.015, .055, .14, alpha=.91))
    c.roundRect(w*.04, h*.335, w*.92, h*.118,
                11, fill=1, stroke=0)

    if not date_text:
        date_text = datetime.now().strftime("%d/%m/%Y")

    info = [
        f"B\u00e1o c\u00e1o ph\u00e2n t\u00edch c\u1ed5 phi\u1ebfu {ticker}",
        f"K\u1ef3 ph\u00e2n t\u00edch: {period or '-'}",
        f"Ng\u00e0y l\u1eadp: {date_text}",
    ]

    c.setFillColorRGB(1, 1, 1)
    c.setFont(normal, 11)
    for i, line in enumerate(info):
        c.drawString(left, h*.422-i*21, line)

    c.setStrokeColor(gold)
    c.line(left, 49, w-left, 49)

    c.setFont(normal, 8)
    c.drawString(left, 34,
                 "STOCKWISE | STARRY NIGHT EDITION")

    c.showPage()
    c.save()
    buf.seek(0)
    return fitz.open(stream=buf.read(), filetype="pdf")

def _metadata_from_original(doc):
    """Read real period/date from TOC and summary, including previously restyled PDFs."""
    sample = "\n".join(pg.get_text() for pg in list(doc)[:min(5,len(doc))])
    periods = re.findall('Kỳ phân tích:\\s*([A-Za-z0-9]+)', sample, re.I)
    dates = re.findall('Ngày lập:\\s*(\\d{2}/\\d{2}/\\d{4}(?:\\s+\\d{2}:\\d{2})?)', sample)
    return (periods[0] if periods else '', dates[0] if dates else '')


def restyle_pdf(pdf_bytes, symbol='', report_title='', period='', date_text=''):
    doc=fitz.open(stream=bytes(pdf_bytes),filetype='pdf')
    detected_period, detected_date = _metadata_from_original(doc)
    period = period or detected_period
    date_text = date_text or detected_date
    # Change existing vector backgrounds, strokes, and plot paths, preserving searchable text.
    for pg in doc:
        for xref in pg.get_contents():
            stream=doc.xref_stream(xref)
            replaced=COLOR.sub(_map_color,stream)
            if replaced!=stream:doc.update_stream(xref,replaced)
    # Replace old image-only pink back cover if present.
    if len(doc) > 1 and len(doc[-1].get_images()) > 0 and (
        len(doc[-1].get_text().strip()) < 120
        or any((img[0] for img in doc[-1].get_images()))
    ):
        last=doc[-1]
        back=_make_cover(last.rect.width,last.rect.height,symbol,'STOCKWISE • Báo cáo phân tích',period,date_text)
        doc.delete_page(len(doc)-1)
        doc.insert_pdf(back)
        back.close()
    if len(doc):
        page=doc[0]
        cover=_make_cover(page.rect.width,page.rect.height,symbol,report_title,period,date_text)
        doc.delete_page(0)
        doc.insert_pdf(cover,start_at=0)
        cover.close()
    result=doc.tobytes(garbage=4,deflate=True)
    doc.close()
    return result

def build_starry_report(*args, **kwargs):
    """Wrap the existing stockwise_pdf_report.build_report without changing its logic."""
    from stockwise_pdf_report import build_report
    original=build_report(*args,**kwargs)
    if hasattr(original,'getvalue'):original=original.getvalue()
    if not isinstance(original,(bytes,bytearray)):
        return original
    symbol=kwargs.get('symbol',args[0] if args else '')
    title=kwargs.get('report_title','')
    period=kwargs.get('selected_time','')
    return restyle_pdf(original,symbol,title,period)
