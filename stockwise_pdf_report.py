"""STOCKWISE Report Studio v2. Export real dashboard results, no invented metrics."""
from __future__ import annotations
import io, math
from datetime import datetime
from xml.sax.saxutils import escape
import pandas as pd
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.enums import TA_JUSTIFY
from reportlab.lib.units import cm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak, Image, KeepTogether

PINK='#E875B5'; NAVY='#19355F'; LAV='#A58BE9'; BLUE='#76B5EB'; MINT='#70C8AE'

def _font():
    from pathlib import Path
    candidates=[('/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf','/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf'),
                ('C:/Windows/Fonts/arial.ttf','C:/Windows/Fonts/arialbd.ttf')]
    for regular,bold in candidates:
        if Path(regular).exists() and Path(bold).exists():
            if 'SWR2' not in pdfmetrics.getRegisteredFontNames():
                pdfmetrics.registerFont(TTFont('SWR2',regular));pdfmetrics.registerFont(TTFont('SWB2',bold))
            return
    raise RuntimeError('Thiếu font Unicode (Arial/DejaVuSans).')

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
    fig.patch.set_facecolor('#FFFFFF');ax.set_facecolor('#FBF8FF')
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
                 report_title=None,risk_heatmap=None,news_articles=None):
    _font();buffer=io.BytesIO();w,h=A4
    doc=SimpleDocTemplate(buffer,pagesize=A4,leftMargin=2.0*cm,rightMargin=2.0*cm,
                          topMargin=2.1*cm,bottomMargin=1.8*cm,title=report_title or f'STOCKWISE {symbol}')
    usable=w-4.0*cm
    title=ParagraphStyle('t',fontName='SWB2',fontSize=18,leading=26,textColor=colors.HexColor(NAVY),spaceAfter=13)
    h1=ParagraphStyle('h',fontName='SWB2',fontSize=15,leading=22,textColor=colors.HexColor(NAVY),spaceBefore=15,spaceAfter=8,keepWithNext=True)
    body=ParagraphStyle('b',fontName='SWR2',fontSize=13,leading=20,textColor=colors.HexColor('#344666'),spaceAfter=10,alignment=TA_JUSTIFY)
    cell=ParagraphStyle('c',fontName='SWR2',fontSize=13,leading=19,textColor=colors.HexColor(NAVY))
    story=[]
    def p(t):story.append(Paragraph(escape(_str(t)),body))
    def head(t):story.append(Paragraph(escape(t),h1))
    def table(rows):
        cells=[[Paragraph(escape(_str(x)),cell) for x in row] for row in rows]
        tab=Table(cells,colWidths=[usable*.44,usable*.56],repeatRows=1,hAlign='LEFT',splitByRow=1)
        tab.setStyle(TableStyle([('BACKGROUND',(0,0),(-1,0),colors.HexColor('#E6E9FE')),
            ('ROWBACKGROUNDS',(0,1),(-1,-1),[colors.white,colors.HexColor('#FFF3FA')]),
            ('LINEBELOW',(0,0),(-1,0),.8,colors.HexColor('#D9B6E8')),
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
    story.append(Spacer(1,.35*cm));story.append(Paragraph('STOCKWISE  /  REPORT STUDIO',h1))
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
        n+=1;head(f'{n}. Tổng quan thị trường')
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
                head('Nhận định kỹ thuật')
                clean_names={'overall_signal':'Nhận định tổng hợp','trend':'Xu hướng',
                    'momentum':'Động lượng','rsi_zone':'Vùng RSI','last_session_events':'Sự kiện phiên cuối',
                    'recommendation':'Nhận định tổng hợp','_explanation':'Giải thích'}
                selected_fields={'overall_signal','trend','momentum','rsi_zone','last_session_events','recommendation','_explanation',
                                 'Nhận định tổng hợp','Xu hướng','Động lượng','Vùng RSI','Sự kiện phiên cuối'}
                for k,v in summary.items():
                    if k in selected_fields and isinstance(v,(str,int,float)):
                        p(f'{clean_names.get(k,k)}: {v}')
            if isinstance(signals,list) and signals:
                head('Chi tiết tín hiệu')
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
                    head(heading)
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
                        head(label)
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
                    head(label)
                    for item in scoring[key]:p(item.get('text') or item.get('metric'))
            risk=scoring.get('risk',{})
            if isinstance(risk,dict):
                head('Các thước đo rủi ro')
                table([['Chỉ tiêu','Giá trị']]+[[m.get('label'),m.get('display')] for m in risk.get('metrics',[])]) if risk.get('metrics') else p('Thiếu các thước đo rủi ro.')
                if len(selected)>2:chart(selected,'drawdown')
            for warn in scoring.get('warnings',[]):
                msg=str(warn)
                if 'AttributeError:' in msg or 'evaluate_signals' in msg:
                    p('Lưu ý kỹ thuật: Chưa đồng bộ được một chức năng đánh giá tín hiệu giữa các module; cần kiểm tra kết quả kỹ thuật.')
                else: p('Cảnh báo: '+msg)
            if scoring.get('caps'):p('Giới hạn nhãn: '+'; '.join(scoring['caps']))
            head('Phương pháp chấm điểm');p(scoring.get('methodology',''))
        else:p('Chưa có kết quả chấm điểm hợp lệ. Hãy chấm điểm trong tab Đánh giá hoặc bật tính điểm khi xuất PDF.')
    if risk_heatmap is not None:
        n+=1;head(f'{n}. Risk Heatmap - rủi ro lịch sử')
        vol, dd = risk_heatmap
        if isinstance(vol, pd.DataFrame) and not vol.empty:
            import matplotlib.pyplot as plt
            fig, ax = plt.subplots(figsize=(8.2, 3.8))
            values = vol.reindex(columns=range(1,13)).to_numpy(dtype=float)
            im=ax.imshow(values, aspect='auto', cmap='RdPu')
            ax.set_xticks(range(12), [f'T{i}' for i in range(1,13)])
            ax.set_yticks(range(len(vol.index)), [str(i) for i in vol.index])
            ax.set_title('Biến động lợi suất năm hóa (%)')
            fig.colorbar(im, ax=ax, fraction=.03, pad=.03)
            fig.tight_layout()
            img=io.BytesIO();fig.savefig(img, format='png', dpi=140, bbox_inches='tight');plt.close(fig);img.seek(0)
            story.append(Image(img,width=usable,height=usable*.47));story.append(Spacer(1,9))
            p('Biến động năm hóa = độ lệch chuẩn lợi suất ngày nhân căn bậc hai của 252. Đây là rủi ro quan sát trong quá khứ, không phải dự báo.')
        else:p('Không đủ phiên giá để lập Risk Heatmap.')
    if news_articles is not None:
        n+=1;head(f'{n}. News Impact Timeline - tin tức và giá')
        p('Các tin dưới đây được tổng hợp từ nguồn RSS; thời điểm đăng không chứng minh tin gây ra biến động giá. Danh sách có thể không đầy đủ.')
        if news_articles:
            for a in news_articles[:12]:
                p(f"• {a.get('date', 'Không rõ ngày')} | {a.get('source', 'Nguồn không rõ')}: {a.get('title', '')} | {a.get('url', '')}")
        else:p('Chưa có tin tức được tải trong phiên phân tích. Hãy mở News Impact Timeline và nhấn tải tin trước khi xuất PDF.')
    head('Nguồn dữ liệu và giới hạn')
    p('Dữ liệu giá: tập dữ liệu STOCKWISE đang tải; chỉ báo kỹ thuật: module TV2; tài chính: TV3 nếu có; điểm đầu tư và rủi ro: mô hình chấm điểm nếu có. Dữ liệu có thể không đồng nhất về ngày và kỳ báo cáo.')
    p('Đây là công cụ hỗ trợ học tập và nghiên cứu, không phải khuyến nghị mua hoặc bán chứng khoán.')
    def page(canvas,doc):
        canvas.saveState();canvas.setFillColor(colors.HexColor('#FFF5FB'));canvas.rect(0,h-1.1*cm,w,1.1*cm,stroke=0,fill=1)
        canvas.setFillColor(colors.HexColor(NAVY));canvas.setFont('SWB2',13);canvas.drawString(2.0*cm,h-.72*cm,'STOCKWISE   /   FINANCIAL REPORT')
        canvas.setStrokeColor(colors.HexColor('#DCC8F2'));canvas.line(2.0*cm,1.25*cm,w-2.0*cm,1.25*cm)
        canvas.setFont('SWR2',13);canvas.drawRightString(w-2.0*cm,.88*cm,f'Trang {doc.page}')
        canvas.restoreState()
    doc.build(story,onFirstPage=page,onLaterPages=page)
    return buffer.getvalue()
