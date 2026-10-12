"""STOCKWISE Report Studio v2. Export real dashboard results, no invented metrics."""
from __future__ import annotations
import io, math
from pathlib import Path
from datetime import datetime
from xml.sax.saxutils import escape
import pandas as pd
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.enums import TA_JUSTIFY, TA_CENTER
from reportlab.lib.units import cm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak, Image, KeepTogether, CondPageBreak, Flowable

PINK='#ED469A'; NAVY='#000000'; LAV='#DB88CE'; BLUE='#F7ACD0'; MINT='#F7C4DF'

class _BackCover(Flowable):
    """Draw the back cover edge-to-edge, on its own final page."""
    def __init__(self, image_path, page_size):
        super().__init__()
        self.image_path = image_path
        self.page_width, self.page_height = page_size
        self.width = 1
        self.height = 1

    def drawOn(self, canvas, x, y, _sW=0):
        # Use absolute page coordinates so the image covers headers and footers.
        canvas.saveState()
        canvas.drawImage(str(self.image_path), 0, 0,
                         width=self.page_width, height=self.page_height,
                         preserveAspectRatio=False, mask='auto')
        canvas.restoreState()


def _font():
    """Use real Times New Roman on Windows, metrically compatible Tinos elsewhere."""
    candidates = [
        ('C:/Windows/Fonts/times.ttf', 'C:/Windows/Fonts/timesbd.ttf'),
        ('/usr/share/fonts/truetype/msttcorefonts/Times_New_Roman.ttf', '/usr/share/fonts/truetype/msttcorefonts/Times_New_Roman_Bold.ttf'),
        ('/usr/share/fonts/truetype/croscore/Tinos-Regular.ttf', '/usr/share/fonts/truetype/croscore/Tinos-Bold.ttf'),
    ]
    for regular, bold in candidates:
        if Path(regular).exists() and Path(bold).exists():
            if 'SWR2' not in pdfmetrics.getRegisteredFontNames():
                pdfmetrics.registerFont(TTFont('SWR2', regular))
                pdfmetrics.registerFont(TTFont('SWB2', bold))
                pdfmetrics.registerFontFamily('SWR2', normal='SWR2', bold='SWB2')
            return
    raise RuntimeError('Cần font Times New Roman (Windows) hoặc Tinos (Linux).')

def _str(v):
    if v is None: return 'Không có dữ liệu'
    try:
        if pd.isna(v): return 'Không có dữ liệu'
    except (ValueError,TypeError): pass
    return str(v)

def _fmt(v,digits=2,suffix=''):
    try:
        x=float(v)
        if not math.isfinite(x): return 'Không có dữ liệu'
        return f'{x:,.{digits}f}{suffix}'
    except (ValueError,TypeError): return 'Không có dữ liệu'

def _pct(v):
    try: return _fmt(float(v)*100,2,'%')
    except (ValueError,TypeError): return 'Không có dữ liệu'

def _figure(prices, kind='price', pillars=None):
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    fig,ax=plt.subplots(figsize=(8.3,2.7),dpi=150)
    fig.patch.set_facecolor('#FFFFFF');ax.set_facecolor('#FFFFFF')
    if kind=='price':
        ax.plot(prices['date'],prices['close'],color=PINK,linewidth=2)
        ax.set_title('Diễn biến giá đóng cửa trong kỳ',fontsize=11,color=NAVY,weight='bold')
        ax.set_ylabel('Giá (đơn vị dữ liệu)',fontsize=8)
    elif kind=='drawdown':
        p=prices.copy();p['drawdown']=p['close']/p['close'].cummax()-1
        ax.fill_between(p['date'],p['drawdown']*100,0,color=PINK,alpha=.33)
        ax.plot(p['date'],p['drawdown']*100,color='#BD4F99',linewidth=1.3)
        ax.set_title('Drawdown trong kỳ dữ liệu',fontsize=11,color=NAVY,weight='bold')
        ax.set_ylabel('%',fontsize=8)
    else:
        names=['Kỹ thuật','Tài chính','Định giá','Rủi ro']; keys=['technical','fundamental','valuation','risk']
        vals=[pillars.get(k,{}).get('score') for k in keys]
        ax.barh(names,[v if v is not None else 0 for v in vals],color=[PINK,BLUE,LAV,MINT])
        ax.invert_yaxis();ax.set_xlim(0,110)
        for i,v in enumerate(vals): ax.text((v or 0)+2,i,'N/A' if v is None else f'{v:.1f}',va='center',fontsize=9)
        ax.set_title('Điểm 4 trụ cột (0–100)',fontsize=11,color=NAVY,weight='bold')
    ax.grid(axis='y' if kind!='pillars' else 'x',alpha=.18);ax.tick_params(labelsize=8)
    for spine in ax.spines.values(): spine.set_visible(False)
    fig.autofmt_xdate(rotation=20);fig.tight_layout()
    b=io.BytesIO();fig.savefig(b,format='png',dpi=150,bbox_inches='tight');plt.close(fig);b.seek(0)
    return b

def build_report(symbol,stock,selected_time,change_pct,financial=None,scoring=None,technical=None,
                 include_overview=True,include_technical=True,include_financial=True,include_scoring=True,
                 report_title=None, risk_heatmap=None, news_articles=None, **kwargs):
    _font();buffer=io.BytesIO();w,h=A4
    doc=SimpleDocTemplate(buffer,pagesize=A4,leftMargin=3.0*cm,rightMargin=2.0*cm,
                          topMargin=2.0*cm,bottomMargin=2.0*cm,title=report_title or f'STOCKWISE {symbol}')
    usable=w-5.0*cm
    title=ParagraphStyle('t',fontName='SWB2',fontSize=18,leading=26,textColor=colors.HexColor(NAVY),spaceAfter=13)
    h1=ParagraphStyle('h',fontName='SWB2',fontSize=15,leading=22,textColor=colors.HexColor(NAVY),spaceBefore=15,spaceAfter=8,keepWithNext=True)
    body=ParagraphStyle('b',fontName='SWR2',fontSize=13,leading=19,textColor=colors.black,spaceAfter=10,alignment=TA_JUSTIFY)
    cell=ParagraphStyle('c',fontName='SWR2',fontSize=13,leading=18,textColor=colors.HexColor(NAVY))
    story=[PageBreak()]  # Reserve page 1 for the full-bleed approved cover.
    section_style=ParagraphStyle('sectionBox',fontName='SWB2',fontSize=15,leading=20,textColor=colors.black)
    sub_style=ParagraphStyle('subBox',fontName='SWB2',fontSize=13,leading=18,textColor=colors.black)
    def p(t):
        text=_str(t).strip()
        if text: story.append(Paragraph(escape(text),body))
    def head(t):
        story.append(CondPageBreak(3.2*cm))
        banner=Table([[Paragraph(escape(t),section_style)]],colWidths=[usable])
        banner.setStyle(TableStyle([('BACKGROUND',(0,0),(-1,-1),colors.HexColor('#F6B7D7')),
            ('BOX',(0,0),(-1,-1),.6,colors.HexColor('#ED83B8')),
            ('LEFTPADDING',(0,0),(-1,-1),13),('RIGHTPADDING',(0,0),(-1,-1),12),
            ('TOPPADDING',(0,0),(-1,-1),10),('BOTTOMPADDING',(0,0),(-1,-1),10)]))
        story.append(Spacer(1,11));story.append(banner);story.append(Spacer(1,12))
    def subhead(t):
        story.append(CondPageBreak(2.5*cm))
        banner=Table([[Paragraph(escape(t),sub_style)]],colWidths=[usable])
        banner.setStyle(TableStyle([('BACKGROUND',(0,0),(-1,-1),colors.HexColor('#F8D2E5')),
            ('LINEBEFORE',(0,0),(0,0),3,colors.HexColor(PINK)),
            ('LEFTPADDING',(0,0),(-1,-1),12),('TOPPADDING',(0,0),(-1,-1),7),
            ('BOTTOMPADDING',(0,0),(-1,-1),7)]))
        story.append(Spacer(1,9));story.append(banner);story.append(Spacer(1,8))
    def table(rows):
        cells=[[Paragraph(escape(_str(x)),cell) for x in row] for row in rows]
        tab=Table(cells,colWidths=[usable*.44,usable*.56],repeatRows=1,hAlign='LEFT',splitByRow=1)
        tab.setStyle(TableStyle([('BACKGROUND',(0,0),(-1,0),colors.HexColor('#F6B7D7')),
            ('ROWBACKGROUNDS',(0,1),(-1,-1),[colors.white,colors.HexColor('#FCE7F1')]),
            ('LINEBELOW',(0,0),(-1,0),.8,colors.HexColor('#E96CAD')),
            ('VALIGN',(0,0),(-1,-1),'TOP'),('LEFTPADDING',(0,0),(-1,-1),10),
            ('RIGHTPADDING',(0,0),(-1,-1),10),('TOPPADDING',(0,0),(-1,-1),10),('BOTTOMPADDING',(0,0),(-1,-1),10)]))
        story.append(tab);story.append(Spacer(1,9))
    def chart(df,kind='price',pillars=None):
        try:
            b=_figure(df,kind,pillars);story.append(Image(b,width=usable,height=usable*0.37));story.append(Spacer(1,10))
        except Exception as e:p('Không thể dựng biểu đồ: '+str(e))
    d=stock.copy();d['date']=pd.to_datetime(d['date'],errors='coerce');d['close']=pd.to_numeric(d['close'],errors='coerce')
    d=d.dropna(subset=['date','close']).sort_values('date');d=d[d['close']>0]
    if d.empty:raise ValueError('Không có giá hợp lệ để tạo PDF.')
    period_days={'1M':30,'3M':90,'6M':180,'1Y':365,'3Y':1095,'5Y':1825,'ALL':None}.get(selected_time)
    selected=d if period_days is None else d[d['date']>=d['date'].max()-pd.Timedelta(days=period_days)]
    if selected.empty:selected=d.tail(1)
    latest=d.iloc[-1]
    # Mục lục riêng; các mục tùy chọn phụ thuộc dữ liệu và cấu hình xuất báo cáo.
    toc = ['Tổng quan cổ phiếu']
    if include_technical: toc.append('Phân tích kỹ thuật')
    if include_financial: toc.append('Phân tích tài chính và định giá')
    if include_scoring: toc.append('Chấm điểm đầu tư và rủi ro')
    if risk_heatmap is not None: toc.append('Bản đồ nhiệt rủi ro')
    if news_articles: toc.append('Tin tức và sự kiện')
    toc += ['Kết luận và điều cần theo dõi', 'Nguồn dữ liệu và giới hạn']
    head('MỤC LỤC')
    p(f'Mã cổ phiếu: {symbol} | Kỳ phân tích: {selected_time} | Ngày lập: {datetime.now():%d/%m/%Y}')
    for idx, name in enumerate(toc, 1):
        entry=Table([[Paragraph(f'<b>{idx:02d}</b>',cell),Paragraph(escape(name),cell)]],colWidths=[1.5*cm,usable-1.5*cm])
        entry.setStyle(TableStyle([('BACKGROUND',(0,0),(0,0),colors.HexColor('#F6B7D7')),
            ('BACKGROUND',(1,0),(1,0),colors.HexColor('#FCE7F1')),
            ('TOPPADDING',(0,0),(-1,-1),9),('BOTTOMPADDING',(0,0),(-1,-1),9),
            ('LEFTPADDING',(0,0),(-1,-1),11),('LINEBELOW',(0,0),(-1,-1),.5,colors.HexColor('#F5D3E4'))]))
        story.append(entry);story.append(Spacer(1,4))
    story.append(PageBreak())
    story.append(Spacer(1,.35*cm));story.append(Paragraph('STOCKWISE',h1))
    story.append(Paragraph(escape(report_title or f'Báo cáo phân tích cổ phiếu {symbol}'),title))
    p(f'Mã: {symbol}  |  Kỳ phân tích: {selected_time}  |  Ngày lập: {datetime.now():%d/%m/%Y %H:%M}')
    p(f'Dữ liệu giá đến: {latest["date"]:%d/%m/%Y}  |  {len(selected):,} phiên trong kỳ đã chọn')
    story.append(Spacer(1,.45*cm))
    table([['TÓM TẮT NHANH','GIÁ TRỊ'],['Giá đóng cửa',_fmt(latest['close'])],
           ['Biến động kỳ chọn',_fmt(change_pct,2,'%') if change_pct is not None else 'Không có dữ liệu'],
           ['Điểm tổng hợp',_fmt(scoring.get('total_score'),1,'/100') if scoring else 'Chưa có kết quả'],
           ['Phân loại',scoring.get('label') if scoring else 'Chưa có kết quả']])
    p('Báo cáo được tổng hợp từ dữ liệu đang có trong ứng dụng. Các mục thiếu dữ liệu được ghi rõ, không nội suy hoặc tạo chỉ tiêu giả.')
    story.append(PageBreak())
    n=0
    if include_overview:
        n+=1;head(f'{n}. Tổng quan cổ phiếu')
        table([['Chỉ tiêu','Giá trị'],['Mã cổ phiếu',symbol],['Ngày dữ liệu cuối',f'{latest["date"]:%d/%m/%Y}'],
               ['Giá đóng cửa',_fmt(latest['close'])],['Khối lượng',_fmt(latest.get('volume'),0)],
               ['Kỳ phân tích',selected_time],['Số phiên trong kỳ',str(len(selected))],
               ['Số phiên toàn bộ dữ liệu',str(len(d))],['Biến động kỳ chọn',_fmt(change_pct,2,'%') if change_pct is not None else 'N/A']])
        if len(selected)>1:chart(selected,'price')
    if include_technical:
        n+=1;head(f'{n}. Phân tích kỹ thuật')
        if technical:
            indicators,signals,summary,quality=technical
            last=indicators.iloc[-1] if isinstance(indicators,pd.DataFrame) and not indicators.empty else {}
            rows=[['Chỉ báo','Giá trị']]
            for label in ['SMA20','SMA50','RSI14','MACD','MACD_signal','MACD_hist','BB_upper','BB_lower']:
                col=next((x for x in getattr(indicators,'columns',[]) if str(x).lower().replace('_','')==label.lower().replace('_','')),None)
                if col is not None:rows.append([label,_fmt(last[col])])
            if len(rows)>1:table(rows)
            if isinstance(summary,dict):
                subhead('Nhận định kỹ thuật')
                clean_names={'overall_signal':'Nhận định tổng hợp','trend':'Xu hướng',
                    'momentum':'Động lượng','rsi_zone':'Vùng RSI','last_session_events':'Sự kiện phiên cuối',
                    'recommendation':'Nhận định tổng hợp','_explanation':'Giải thích'}
                selected_fields={'overall_signal','trend','momentum','rsi_zone','last_session_events','recommendation','_explanation',
                                 'Nhận định tổng hợp','Xu hướng','Động lượng','Vùng RSI','Sự kiện phiên cuối'}
                for k,v in summary.items():
                    if k in selected_fields and isinstance(v,(str,int,float)):
                        p(f'{clean_names.get(k,k)}: {v}')
            if isinstance(signals,list) and signals:
                subhead('Chi tiết tín hiệu')
                for sig in signals[:14]:
                    if isinstance(sig,dict):
                        label=sig.get('Chỉ báo',sig.get('indicator','Chỉ báo'))
                        status=sig.get('Tín hiệu',sig.get('signal',''))
                        explanation=sig.get('Giải thích',sig.get('explanation',''))
                        p(f'{label} — {status}. {explanation}')
            if isinstance(quality,dict):
                for warning in quality.get('warnings',[]):p('Cảnh báo kỹ thuật: '+str(warning))
        else:p('Không có kết quả kỹ thuật hợp lệ tại thời điểm xuất báo cáo.')
    if include_financial:
        n+=1;head(f'{n}. Phân tích tài chính và định giá')
        analysis=financial.get('analysis',{}) if isinstance(financial,dict) else {}
        if analysis:
            period=analysis.get('latest_period') or financial.get('period') or 'Chưa xác định'
            p('Kỳ báo cáo tài chính: '+str(period))
            metric_names={
                'loan_growth':'Tăng trưởng dư nợ (%)','deposit_growth':'Tăng trưởng huy động (%)',
                'profit_growth':'Tăng trưởng lợi nhuận (%)','roe':'ROE (%)','roa':'ROA (%)',
                'nim':'Biên lãi ròng NIM (%)','eps':'EPS (đồng/cổ phiếu)',
                'pe':'P/E (lần)','pb':'P/B (lần)',
                'historical_pe_median':'Trung vị P/E lịch sử (lần)',
                'historical_pb_median':'Trung vị P/B lịch sử (lần)',
                'npl':'Tỷ lệ nợ xấu NPL (%)','llr':'Tỷ lệ bao phủ nợ xấu LLR (%)',
                'car':'Hệ số an toàn vốn CAR (%)','casa':'Tỷ lệ CASA (%)',
                'ldr':'Tỷ lệ cho vay/huy động LDR (%)'}
            percent_fraction={'loan_growth','deposit_growth','profit_growth','nim','npl','llr','car','casa','ldr'}
            percent_as_given={'roe','roa'}
            labels={'growth':'Tăng trưởng','profitability':'Sinh lời','financial_health':'Sức khỏe tài chính',
                    'valuation':'Định giá','asset_quality':'Chất lượng tài sản','capital_funding':'Vốn và huy động'}
            for key,heading in labels.items():
                section=analysis.get(key)
                if isinstance(section,dict) and section:
                    subhead(heading)
                    rows=[['Chỉ tiêu','Giá trị']]
                    for metric,value in section.items():
                        if metric.endswith('_trend') or metric not in metric_names:
                            continue
                        if isinstance(value,(int,float)) and not isinstance(value,bool):
                            if metric in percent_fraction: shown=_pct(value)
                            elif metric in percent_as_given: shown=_fmt(value,2,'%')
                            elif metric=='eps': shown=_fmt(value,2)
                            else: shown=_fmt(value,2)
                            rows.append([metric_names[metric],shown])
                        elif value is None: rows.append([metric_names[metric],'Không có dữ liệu'])
                    if len(rows)>1:table(rows)
            observations=analysis.get('observations',{})
            if isinstance(observations,dict):
                for key,label in [('strengths','Điểm mạnh'),('weaknesses','Điểm cần theo dõi'),('valuation_notes','Nhận xét định giá')]:
                    items=observations.get(key,[])
                    if items:
                        subhead(label)
                        for item in items[:12]:p('• '+str(item))
            quality=analysis.get('data_quality',{})
            if isinstance(quality,dict):
                for warning in quality.get('warnings',[]):p('Cảnh báo tài chính: '+str(warning))
        else:p('Chưa có kết quả phân tích tài chính cho mã này. Cần chạy phân tích tài chính hoặc bật tải dữ liệu trong Report Studio.')
    if include_scoring:
        n+=1;head(f'{n}. Chấm điểm đầu tư và rủi ro')
        if scoring:
            table([['Chỉ tiêu','Kết quả'],['Điểm tổng',_fmt(scoring.get('total_score'),1,'/100')],
                   ['Phân loại',scoring.get('label')],['Độ tin cậy',scoring.get('confidence')],
                   ['Độ phủ trọng số',_pct(scoring.get('coverage_weight'))],['Ngày dữ liệu',scoring.get('as_of')]])
            summary_text=str(scoring.get('summary',''))
            if 'ROA 66.0%' in summary_text:
                p('Lưu ý kiểm định: Phần giải thích điểm đang ghi ROA 66,0%, chưa khớp với chỉ tiêu ROA của bảng tài chính. Cần đối chiếu quy đổi đơn vị trong module chấm điểm.')
            p(summary_text)
            pillars=scoring.get('pillars',{})
            if pillars:
                chart(selected,'pillars',pillars)
                table([['Trụ cột','Điểm / Độ phủ / Trọng số']]+[
                    [pillars[k].get('label',k),f"{_fmt(pillars[k].get('score'),1)}/100 | { _pct(pillars[k].get('coverage'))} | {_pct(pillars[k].get('weight_used'))}"]
                    for k in ['technical','fundamental','valuation','risk'] if k in pillars])
            for key,label in [('drivers_up','Yếu tố đóng góp tích cực'),('drivers_down','Yếu tố đóng góp tiêu cực')]:
                if scoring.get(key):
                    subhead(label)
                    for item in scoring[key]:p(item.get('text') or item.get('metric'))
            risk=scoring.get('risk',{})
            if isinstance(risk,dict):
                subhead('Các thước đo rủi ro')
                table([['Chỉ tiêu','Giá trị']]+[[m.get('label'),m.get('display')] for m in risk.get('metrics',[])]) if risk.get('metrics') else p('Thiếu các thước đo rủi ro.')
                if len(selected)>2:chart(selected,'drawdown')
            for warn in scoring.get('warnings',[]):
                msg=str(warn)
                if 'AttributeError:' in msg or 'evaluate_signals' in msg:
                    p('Lưu ý kỹ thuật: Chưa đồng bộ được một chức năng đánh giá tín hiệu giữa các module; cần kiểm tra kết quả kỹ thuật.')
                else: p('Cảnh báo: '+msg)
            if scoring.get('caps'):p('Giới hạn nhãn: '+'; '.join(scoring['caps']))
            subhead('Phương pháp chấm điểm');p(scoring.get('methodology',''))
        else:p('Chưa có kết quả chấm điểm hợp lệ. Hãy chấm điểm trong tab Đánh giá hoặc bật tính điểm khi xuất PDF.')
    if risk_heatmap is not None:
        n+=1; head(f'{n}. Bản đồ nhiệt rủi ro')
        if isinstance(risk_heatmap, pd.DataFrame) and not risk_heatmap.empty:
            data = risk_heatmap.head(12)
            for _, row in data.iterrows():
                p(' | '.join(f'{k}: {_str(v)}' for k,v in row.items()))
        elif isinstance(risk_heatmap, dict):
            for key, value in list(risk_heatmap.items())[:16]:
                if isinstance(value, (str, int, float)):
                    p(f'{key}: {value}')
                elif isinstance(value, (list, tuple)):
                    for item in value[:10]: p(f'{key}: {_str(item)}')
        else:
            p('Dữ liệu bản đồ nhiệt được cung cấp bởi dashboard; không có bảng giá trị phù hợp để in.')
    if news_articles:
        n+=1; head(f'{n}. Tin tức và sự kiện')
        for article in news_articles[:12]:
            if isinstance(article, dict):
                title_text = article.get('title') or article.get('headline') or 'Tin tức'
                date_text = article.get('published_at') or article.get('date') or ''
                source_text = article.get('source') or ''
                p(f'{title_text} | {source_text} | {date_text}')
            else: p(_str(article))
    n+=1; head(f'{n}. Kết luận và điều cần theo dõi')
    if isinstance(scoring, dict):
        p('Kết quả chấm điểm hiện tại: ' + _str(scoring.get('label')) + '; điểm tổng hợp: ' + _fmt(scoring.get('total_score'),1,'/100') + '.')
        if scoring.get('summary'): p(scoring.get('summary'))
    else:
        p('Chưa có đủ dữ liệu chấm điểm để đưa ra kết luận tổng hợp; cần đối chiếu kết quả kỹ thuật, tài chính và mức độ rủi ro.')
    p('Cần tiếp tục theo dõi biến động giá, khối lượng giao dịch, các báo cáo tài chính mới nhất và thay đổi trong các chỉ báo rủi ro.')
    subhead('Nguồn dữ liệu và giới hạn')
    p('Dữ liệu giá: tập dữ liệu STOCKWISE đang tải; chỉ báo kỹ thuật: module TV2; tài chính: TV3 nếu có; điểm đầu tư và rủi ro: mô hình chấm điểm nếu có. Dữ liệu có thể không đồng nhất về ngày và kỳ báo cáo.')
    p('Đây là công cụ hỗ trợ học tập và nghiên cứu, không phải khuyến nghị mua hoặc bán chứng khoán.')
    # The ending cover is a separate full-bleed page, distinct from the front.
    back_cover = Path(__file__).resolve().parent / 'stockwise_report_assets' / 'back_cover.png'
    if back_cover.is_file():
        story.append(PageBreak())
        story.append(_BackCover(back_cover, A4))

    def page(canvas,doc):
        canvas.saveState()
        if doc.page == 1:
            cover = Path(__file__).resolve().parent / 'stockwise_report_assets' / 'cover.png'
            if cover.exists():
                canvas.drawImage(str(cover), 0, 0, width=w, height=h, preserveAspectRatio=False, mask='auto')
            else:
                canvas.setFillColor(colors.HexColor('#F8E9F7'));canvas.rect(0,0,w,h,fill=1,stroke=0)
                canvas.setFillColor(colors.HexColor(NAVY));canvas.setFont('SWB2',35)
                canvas.drawCentredString(w/2,h*.66,'STOCKWISE')
                canvas.setFont('SWB2',20);canvas.drawCentredString(w/2,h*.60,'BÁO CÁO PHÂN TÍCH')
            canvas.restoreState()
            return
        canvas.setFillColor(colors.white);canvas.rect(0,0,w,h,stroke=0,fill=1)
        canvas.setFillColor(colors.HexColor('#F6B7D7'));canvas.roundRect(3.0*cm,h-1.25*cm,w-5.0*cm,.72*cm,7,stroke=0,fill=1)
        canvas.setFillColor(colors.black);canvas.setFont('SWB2',13);canvas.drawString(3.2*cm,h-1.03*cm,'STOCKWISE  |  BÁO CÁO PHÂN TÍCH')
        canvas.setStrokeColor(colors.HexColor('#F0A2C9'));canvas.line(3.0*cm,1.25*cm,w-2.0*cm,1.25*cm)
        canvas.setFont('SWR2',11);canvas.drawRightString(w-2.0*cm,.88*cm,f'Trang {doc.page-1}')
        canvas.restoreState()
    doc.build(story,onFirstPage=page,onLaterPages=page)
    return buffer.getvalue()
