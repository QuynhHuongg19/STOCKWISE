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

def _make_cover(w,h,symbol,title,period,date_text):
    from reportlab.lib.utils import ImageReader
    normal,bold=_font()
    buf=io.BytesIO(); c=canvas.Canvas(buf,pagesize=(w,h))
    c.setFillColorRGB(.025,.105,.245);c.rect(0,0,w,h,fill=1,stroke=0)
    if HERO.exists():
        from PIL import Image
        im=Image.open(HERO).convert('RGB'); iw,ih=im.size
        scale=max(w/iw,h/ih); nw,nh=iw*scale,ih*scale
        c.drawImage(ImageReader(im), (w-nw)/2,(h-nh)/2,nw,nh,mask='auto')
    # Navy overlay behind typography, with transparent ink
    c.setFillColorRGB(.02,.08,.19);c.setFillAlpha(.83);c.roundRect(32,h*.48,w-64,h*.42,15,fill=1,stroke=0);c.setFillAlpha(1)
    c.setStrokeColorRGB(.91,.73,.33);c.setLineWidth(2);c.line(52,h*.86,w-52,h*.86)
    c.setFillColorRGB(1,1,1);c.setFont(bold,24);c.drawString(52,h*.80,'STOCKWISE')
    c.setFont(normal,9);c.drawString(53,h*.765,'FINANCIAL ANALYTICS PLATFORM')
    c.drawString(52,h*.675,'B?O C?O PH?N T?CH')
    c.drawString(52,h*.626,'C? PHI?U')
    c.setFillColorRGB(1,1,1);c.setFont(bold,47);c.drawString(52,h*.54,str(symbol or 'STOCKWISE').upper())
    c.setFillColorRGB(.025,.105,.245);c.setFillAlpha(.90)
    c.roundRect(33,h*.342,w-66,99,11,fill=1,stroke=0)
    c.setFillAlpha(1)
    c.setFillColorRGB(1,1,1);c.setFont(normal,11)
    for i,line in enumerate((
        str(title or ''),
        f'K? ph?n t?ch: {period or "-"}',
        f'Ng?y l?p: {date_text or "-"}'
    )):
        c.drawString(53,h*.43-i*22,line[:75])
    c.setStrokeColorRGB(.91,.73,.33);c.line(52,51,w-52,51)
    c.setFillColorRGB(1,1,1);c.setFont(normal,8);c.drawString(52,36,'STOCKWISE  |  STARRY NIGHT EDITION')
    c.showPage();c.save();buf.seek(0)
    return fitz.open(stream=buf.read(),filetype='pdf')

def _metadata_from_original(doc):
    """Read real period/date from TOC and summary, including previously restyled PDFs."""
    sample = "\n".join(pg.get_text() for pg in list(doc)[:min(5,len(doc))])
    periods = re.findall(r"K? ph?n t?ch:\s*([A-Za-z0-9]+)", sample, re.I)
    dates = re.findall(r"Ng?y l?p:\s*(\d{2}/\d{2}/\d{4}(?:\s+\d{2}:\d{2})?)", sample)
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
