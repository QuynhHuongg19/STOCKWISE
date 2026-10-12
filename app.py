"""STOCKWISE Art Gallery Light homepage; dashboard and data remain unchanged."""
import base64
import textwrap
import html
from datetime import date, timedelta
from pathlib import Path
import streamlit as st
st.set_page_config(page_title="STOCKWISE | Phân tích cổ phiếu", page_icon="✦", layout="wide", initial_sidebar_state="collapsed")
def _art_url(filename):
    p = Path(__file__).resolve().parent / "assets" / "art" / filename
    if not p.is_file():
        return "none"
    mime = "image/webp" if p.suffix.lower() == ".webp" else "image/png" if p.suffix.lower() == ".png" else "image/jpeg"
    return f'url("data:{mime};base64,{base64.b64encode(p.read_bytes()).decode("ascii")}")'

@st.cache_data(ttl=60, show_spinner=False)
def _market_snapshot():
    """Best-effort daily index observations; refresh checks every 60s, NOT tick-level prices."""
    try:
        from vnstock import Vnstock
    except Exception:
        return {key: None for key in ('VNINDEX', 'VN30', 'HNXINDEX', 'UPCOMINDEX')}
    result = {}
    end = date.today() + timedelta(days=1)
    start = date.today() - timedelta(days=14)
    for symbol in ('VNINDEX', 'VN30', 'HNXINDEX', 'UPCOMINDEX'):
        result[symbol] = None
        for source in ('VCI', 'KBS'):
            try:
                stock = Vnstock().stock(symbol=symbol, source=source)
                frame = stock.quote.history(start=start.isoformat(), end=end.isoformat(), interval='1D')
                if frame is None or len(frame) < 2:
                    continue
                cols = {str(c).lower(): c for c in frame.columns}
                price_col = cols.get('close')
                if price_col is None:
                    continue
                import pandas as pd
                cleaned = frame.copy()
                cleaned['_price'] = pd.to_numeric(cleaned[price_col], errors='coerce')
                cleaned = cleaned.dropna(subset=['_price'])
                cleaned = cleaned[cleaned['_price'] > 0]
                if len(cleaned) < 2:
                    continue
                time_col = cols.get('time') or cols.get('date')
                if time_col:
                    cleaned['_time'] = pd.to_datetime(cleaned[time_col], errors='coerce')
                    cleaned = cleaned.sort_values('_time')
                previous, latest = cleaned.iloc[-2], cleaned.iloc[-1]
                pct = (float(latest['_price']) / float(previous['_price']) - 1) * 100
                stamp = str(latest[time_col])[:10] if time_col else 'Không rõ ngày'
                result[symbol] = {'value': float(latest['_price']), 'change': pct, 'date': stamp, 'source': source}
                break
            except Exception:
                continue
    return result

@st.fragment(run_every='60s')
def render_market_overview():
    data = _market_snapshot()
    cards = []
    for symbol in ('VNINDEX', 'VN30', 'HNXINDEX', 'UPCOMINDEX'):
        record = data.get(symbol)
        if record:
            value = f"{record['value']:,.2f}"
            change = f"{record['change']:+.2f}%"
            meta = f"{change} · {record['date']} · {record['source']} (giá ngày)"
        else:
            value, meta = '—', 'Nguồn chưa cung cấp dữ liệu hợp lệ'
        cards.append(f'<div class="sw3-market"><h3>{symbol}</h3><div class="sw3-market-value">{html.escape(value)}</div><div class="sw3-market-meta">{html.escape(meta)}</div><div class="sw3-market-rule"></div></div>')
    cards.append('<div class="sw3-market"><h3>Top tăng mạnh</h3><div class="sw3-market-value">—</div><div class="sw3-market-meta">Chưa có bảng giá toàn thị trường được xác thực</div><div class="sw3-market-rule"></div></div>')
    st.markdown('<div class="sw3 sw3-market-grid">' + ''.join(cards) + '</div>', unsafe_allow_html=True)
    st.caption('Tự kiểm tra mỗi 60 giây · Nguồn Vnstock (nếu khả dụng) · Giá ngày, không phải giá realtime từng giây. Không có dữ liệu sẽ không hiển thị số liệu giả.')

def home():
    hero_image = _art_url("hero_starry_sky.webp")
    stock_image = _art_url("card_stock.webp")
    market_image = _art_url("card_market.webp")
    report_image = _art_url("card_report.webp")
    css = r"""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=DM+Sans:wght@400;500;600;700&family=Playfair+Display:wght@500;600;700&display=swap');
    [data-testid="stAppViewContainer"]{background:#faf9f6}
    [data-testid="stHeader"]{background:transparent}
    [data-testid="stSidebar"],[data-testid="stSidebarCollapsedControl"]{display:none}
    .block-container{max-width:1430px;padding:1rem 2rem 3rem}
    .sw3,.sw3 *{box-sizing:border-box}
    .sw3{color:#143457;font-family:'DM Sans',Arial,sans-serif}
    .sw3 a{text-decoration:none!important;color:inherit}
    .sw3-nav{display:flex;align-items:center;gap:24px;min-height:60px;border-bottom:1px solid #e8e7e3}
    .sw3-brand{font-weight:700;letter-spacing:.04em;font-size:1.25rem;white-space:nowrap}
    .sw3-brand b{color:#c49b46;font-size:1.7rem;font-weight:500;margin-right:8px}
    .sw3-links{display:flex;gap:27px;margin-left:auto;align-items:center}
    .sw3-links a{font-size:.83rem;font-weight:600;white-space:nowrap;padding:9px 0}
    .sw3-links a:first-child{border-bottom:2px solid #1a4575}
    .sw3-hero{position:relative;isolation:isolate;min-height:395px;display:flex;align-items:center;overflow:hidden;margin:9px 0 13px;border-radius:8px;background:#faf9f6}
    .sw3-hero:before{content:"";position:absolute;inset:0 0 0 26%;z-index:-2;background-image:var(--hero);background-position:center 52%;background-size:cover}
    .sw3-hero:after{content:"";position:absolute;inset:0;z-index:-1;background:linear-gradient(90deg,#faf9f6 0%,#faf9f6 19%,rgba(250,249,246,.94) 30%,rgba(250,249,246,.52) 47%,transparent 68%)}
    .sw3-hero-inner{padding:25px 3%;width:100%}
    .sw3-hero h1{font:600 clamp(3rem,7.6vw,7.3rem)/1.1 'Playfair Display',Georgia,serif;letter-spacing:-.067em;margin:0 0 22px;white-space:nowrap;color:#102f56}
    .sw3-gold{height:3px;width:68px;background:#d2a950;margin:0 0 20px}
    .sw3-actions{display:flex;gap:12px;flex-wrap:wrap}
    .sw3-primary,.sw3-secondary{display:inline-flex;align-items:center;justify-content:center;min-height:46px;padding:0 25px;border-radius:9px;font-size:.9rem;font-weight:700}
    .sw3-primary{background:#173f70;color:#fff!important;box-shadow:0 8px 18px #123d6333}
    .sw3-secondary{background:#ffffffd9;border:1px solid #c9d1d9;color:#15385f!important}
    .sw3-quick{display:grid;grid-template-columns:repeat(4,minmax(0,1fr));gap:13px;margin:6px 0 21px}
    .sw3-quick a{display:flex;align-items:center;gap:11px;min-width:0;min-height:80px;padding:13px 15px;background:#fff;border:1px solid #e6e9ed;border-radius:12px;box-shadow:0 9px 24px #23436316,0 2px 5px #2343630b;transition:transform .2s,box-shadow .2s}
    .sw3-quick a:hover,.sw3-tool:hover{transform:translateY(-3px);box-shadow:0 15px 28px #23436324}
    .sw3-icon{width:43px;height:43px;flex:none;display:grid;place-items:center;border-radius:12px;background:#e9f1fb;color:#2864a5;font-size:1.35rem}
    .sw3-quick a:nth-child(3) .sw3-icon{background:#fff3d9;color:#c4922d}
    .sw3-quick a:nth-child(4) .sw3-icon{background:#e9f1fb;color:#2864a5}
    .sw3-quick-text{min-width:0}.sw3-quick strong{display:block;font-size:.84rem;line-height:1.3}.sw3-quick small{display:block;color:#667a8c;font-size:.7rem;margin-top:4px;line-height:1.35}
    .sw3-arr{margin-left:auto;display:grid;place-items:center;flex:none;width:24px;height:24px;border-radius:50%;background:#e6eef6;color:#255887;font-size:.85rem}
    .sw3-heading{font:600 clamp(1.65rem,2.5vw,2.15rem)/1.2 'Playfair Display',Georgia,serif;margin:20px 0 5px}
    .sw3-heading-row{display:flex;align-items:end;justify-content:space-between;gap:12px}
    .sw3-heading-row>a{color:#2e6396;font-weight:700;font-size:.79rem;white-space:nowrap;padding-bottom:5px}
    .sw3-sub{font-size:.77rem;color:#81909d;margin:0 0 11px}
    .sw3-market-grid{display:grid;grid-template-columns:repeat(5,minmax(0,1fr));gap:12px;margin-bottom:21px}
    .sw3-market{position:relative;min-height:126px;background:#fff;border:1px solid #e6e9ee;border-radius:11px;padding:16px 16px 12px;box-shadow:0 7px 19px #24496b10;overflow:hidden}
    .sw3-market h3{font:700 .84rem 'DM Sans',sans-serif;margin:0 0 11px}
    .sw3-market-value{font:700 1.5rem 'DM Sans',sans-serif;letter-spacing:-.04em;color:#23466d}
    .sw3-market-meta{font-size:.74rem;color:#8797a6;margin-top:6px}
    .sw3-market-rule{height:3px;width:55%;border-radius:10px;background:#d5e6fa;margin-top:16px}
    .sw3-market:nth-child(2) .sw3-market-rule{background:#c9e9dc}
    .sw3-market:nth-child(3) .sw3-market-rule{background:#f7dfb2}
    .sw3-market:nth-child(4) .sw3-market-rule{background:#e1d3f5}
    .sw3-market:nth-child(5) .sw3-market-rule{background:#dce4ee}
    .sw3-tools{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:15px}
    .sw3-tool{display:block;overflow:hidden;background:#fff;border:1px solid #e4e8ed;border-radius:12px;box-shadow:0 8px 21px #24496b14;transition:transform .2s,box-shadow .2s}
    .sw3-art{height:150px;background-size:cover;background-position:center}
    .sw3-art-1{background-image:var(--stock);background-position:center 35%}
    .sw3-art-2{background-image:var(--market),linear-gradient(155deg,#dce8f0 5%,#b4c8d9 38%,#f4dfac 57%,#6085a9 100%);background-blend-mode:normal}
    .sw3-art-3{background-image:var(--report),linear-gradient(140deg,#d6b28b 0%,#f1dfb9 34%,#aec5d4 60%,#516f92 100%)}
    .sw3-tool-body{position:relative;min-height:110px;padding:17px 50px 18px 17px}
    .sw3-tool h3{font-size:.94rem;font-weight:700;margin:0 0 6px}
    .sw3-tool p{font-size:.76rem;color:#667b90;line-height:1.55;margin:0}
    .sw3-tool .sw3-arr{position:absolute;right:16px;top:26px;background:#d6e7f6}
    .sw3-footer{border-top:1px solid #e4e6e9;margin-top:35px;padding-top:15px;color:#83909d;font-size:.72rem}
    @media(max-width:1080px){.sw3-quick{grid-template-columns:repeat(2,minmax(0,1fr))}.sw3-market-grid{grid-template-columns:repeat(3,minmax(0,1fr))}.sw3-hero h1{font-size:clamp(3rem,8vw,6rem)}}
    @media(max-width:700px){.block-container{padding:1rem 1rem 3rem}.sw3-nav{flex-wrap:wrap;padding-bottom:9px}.sw3-links{width:100%;margin-left:0;overflow-x:auto;gap:15px}.sw3-hero{min-height:370px;align-items:end}.sw3-hero:before{inset:0;background-position:center}.sw3-hero:after{background:linear-gradient(0deg,#faf9f6 0%,rgba(250,249,246,.93) 30%,rgba(250,249,246,.18) 90%)}.sw3-hero-inner{padding:24px 16px}.sw3-hero h1{font-size:clamp(2.7rem,11vw,4.8rem)}.sw3-quick{grid-template-columns:1fr}.sw3-market-grid{grid-template-columns:repeat(2,minmax(0,1fr))}.sw3-tools{grid-template-columns:1fr}.sw3-heading-row{align-items:center}.sw3-market{min-height:118px}}
    /* STOCKWISE FONT UPGRADE V1 */
    .sw3-brand{font-size:1.45rem}
    .sw3-links a{font-size:1rem}
    .sw3-primary,.sw3-secondary{font-size:1.02rem;min-height:49px}
    .sw3-quick a{min-height:94px;padding:17px 17px}
    .sw3-quick strong{font-size:1.02rem;line-height:1.35}
    .sw3-quick small{font-size:.87rem;line-height:1.45}
    .sw3-icon{width:48px;height:48px;font-size:1.5rem}
    .sw3-arr{width:28px;height:28px;font-size:1rem}
    .sw3-heading{font-size:clamp(1.9rem,2.8vw,2.5rem)}
    .sw3-heading-row>a{font-size:.98rem}
    .sw3-sub{font-size:.98rem;line-height:1.6}
    .sw3-market{min-height:155px;padding:20px 18px 16px}
    .sw3-market h3{font-size:1rem}
    .sw3-market-value{font-size:1.8rem}
    .sw3-market-meta{font-size:.89rem;line-height:1.5}
    .sw3-art{height:175px}
    .sw3-tool-body{min-height:137px;padding:20px 54px 22px 20px}
    .sw3-tool h3{font-size:1.12rem;line-height:1.4}
    .sw3-tool p{font-size:.94rem;line-height:1.6}
    .sw3-footer{font-size:.88rem}
    @media(max-width:700px){.sw3-links a{font-size:.92rem}.sw3-quick strong{font-size:1rem}.sw3-quick small{font-size:.86rem}.sw3-market h3{font-size:.94rem}}
    </style>
    """
    css = css.replace('var(--hero)', hero_image).replace('var(--stock)', stock_image).replace('var(--market)', market_image).replace('var(--report)', report_image)
    st.markdown(css, unsafe_allow_html=True)
    homepage_html = textwrap.dedent("""
    <div class="sw3">
      <nav class="sw3-nav">
        <a class="sw3-brand" href="/trang-chu" target="_self"><b>✧</b>STOCKWISE</a>
        <div class="sw3-links">
          <a href="/trang-chu" target="_self">Trang chủ</a>
          <a href="/tra-cuu" target="_self">Phân tích cổ phiếu</a>
          <a href="/tra-cuu" target="_self">Thị trường</a>
          <a href="/tra-cuu" target="_self">Báo cáo</a>
        </div>
      </nav>
      <section class="sw3-hero"><div class="sw3-hero-inner">
        <h1>STOCKWISE</h1><div class="sw3-gold"></div>
        <div class="sw3-actions">
          <a class="sw3-primary" href="/tra-cuu" target="_self">Bắt đầu phân tích →</a>
          <a class="sw3-secondary" href="/tra-cuu" target="_self">Xem công cụ</a>
        </div>
      </div></section>
      <div class="sw3-quick">
        <a href="/tra-cuu" target="_self"><span class="sw3-icon">⌁</span><span class="sw3-quick-text"><strong>Phân tích cổ phiếu</strong><small>Biểu đồ, chỉ báo, tín hiệu</small></span><span class="sw3-arr">→</span></a>
        <a href="/tra-cuu" target="_self"><span class="sw3-icon">▥</span><span class="sw3-quick-text"><strong>Thị trường</strong><small>VNINDEX, VN30, ngành</small></span><span class="sw3-arr">→</span></a>
        <a href="/tra-cuu" target="_self"><span class="sw3-icon">♧</span><span class="sw3-quick-text"><strong>Đánh giá đầu tư</strong><small>Chỉ tiêu và rủi ro</small></span><span class="sw3-arr">→</span></a>
        <a href="/tra-cuu" target="_self"><span class="sw3-icon">▤</span><span class="sw3-quick-text"><strong>Báo cáo PDF</strong><small>Tạo và tải báo cáo</small></span><span class="sw3-arr">→</span></a>
      </div>
      <div class="sw3-heading-row"><h2 class="sw3-heading">Tổng quan thị trường</h2><a href="/tra-cuu" target="_self">Xem chi tiết →</a></div>
      <p class="sw3-sub">Số liệu thị trường được tra cứu trong hệ thống phân tích.</p>
      __MARKET_WIDGET__
      <h2 class="sw3-heading">Khám phá công cụ phân tích</h2>
      <div class="sw3-tools">
        <a class="sw3-tool" href="/tra-cuu" target="_self"><div class="sw3-art sw3-art-1"></div><div class="sw3-tool-body"><h3>Phân tích cổ phiếu</h3><p>Biểu đồ chuyên sâu, chỉ báo kỹ thuật và tín hiệu giao dịch.</p><span class="sw3-arr">→</span></div></a>
        <a class="sw3-tool" href="/tra-cuu" target="_self"><div class="sw3-art sw3-art-2"></div><div class="sw3-tool-body"><h3>Thị trường và ngành</h3><p>Tra cứu diễn biến giá và phân tích các nhóm ngành.</p><span class="sw3-arr">→</span></div></a>
        <a class="sw3-tool" href="/tra-cuu" target="_self"><div class="sw3-art sw3-art-3"></div><div class="sw3-tool-body"><h3>Báo cáo PDF</h3><p>Tạo, xem trước và tải xuống báo cáo phân tích.</p><span class="sw3-arr">→</span></div></a>
      </div>
      <footer class="sw3-footer">STOCKWISE · Nền tảng phân tích cổ phiếu</footer>
    </div>
    """)
    first, second = homepage_html.split('__MARKET_WIDGET__', 1)
    st.markdown(first, unsafe_allow_html=True)
    render_market_overview()
    st.markdown(second, unsafe_allow_html=True)
home_page = st.Page(home, title="TRANG CHỦ", url_path="trang-chu", default=True)
search_page = st.Page("stockwise_dashboard.py", title="TRA CỨU", url_path="tra-cuu")
selected = st.navigation([home_page, search_page], position="hidden")
selected.run()
