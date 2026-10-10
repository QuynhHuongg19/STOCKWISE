"""STOCKWISE entry point: adds a home page without editing the existing app.py.

Run: streamlit run stockwise_portal.py
Keep this file next to your ORIGINAL app.py.
"""
import streamlit as st


def home():
    st.markdown("""
    <style>
    [data-testid="stSidebar"] {display:none;}
    [data-testid="stSidebarCollapsedControl"] {display:none;}
    .block-container {max-width: 1200px; padding-top: 2rem;}
    .sw-hero {
      position:relative; overflow:hidden; min-height: 530px;
      display:flex; flex-direction:column; justify-content:center; align-items:center;
      text-align:center; border-radius:34px; margin: 28px 0 12px;
      background:linear-gradient(125deg,#c8e5ff 0%,#e3d4ff 49%,#f7c4e3 100%);
      border:1px solid rgba(255,255,255,.75);
      box-shadow:0 20px 55px rgba(114,96,169,.14);
    }
    .sw-hero:before,.sw-hero:after {content:"";position:absolute;border-radius:50%;pointer-events:none;}
    .sw-hero:before {width:360px;height:360px;top:-170px;right:-110px;
      background:rgba(255,255,255,.32);filter:blur(4px);}
    .sw-hero:after {width:300px;height:300px;bottom:-180px;left:-80px;
      background:rgba(255,255,255,.25);filter:blur(6px);}
    .sw-title {position:relative;z-index:1; font-size:clamp(3.5rem,10vw,8.5rem);
      line-height:1.1;letter-spacing:-.065em;font-weight:950;
      color:#17365f;text-shadow:4px 5px 0 rgba(255,255,255,.75),
      0 12px 28px rgba(69,84,143,.18);padding:0 15px;}
    .sw-line {position:relative;z-index:1;width:165px;height:7px;margin-top:22px;
      border-radius:30px;background:linear-gradient(90deg,#ef79bf,#9b86e9,#82bbf7);}
    .sw-star {position:absolute;color:#fff;font-size:46px;opacity:.85;}
    .sw-star.one {top:22%;left:12%;}.sw-star.two {bottom:22%;right:12%;font-size:32px;}
    @media(max-width:650px){.sw-hero{min-height:420px;border-radius:24px;}.sw-star.one{left:5%;}}
    </style>
    <div class="sw-hero">
      <span class="sw-star one">✦</span><span class="sw-star two">✧</span>
      <div class="sw-title">STOCKWISE</div>
      <div class="sw-line"></div>
    </div>
    """, unsafe_allow_html=True)
    _, center, _ = st.columns([2, 1.25, 2])
    with center:
        if st.button("BẮT ĐẦU TRA CỨU →", type="primary", use_container_width=True):
            st.switch_page(search_page)


home_page = st.Page(home, title="TRANG CHỦ", url_path="trang-chu", default=True)
search_page = st.Page("stockwise_dashboard.py", title="TRA CỨU", url_path="tra-cuu")
selected = st.navigation([home_page, search_page], position="hidden")

# Header: only the brand name and two navigation links.
brand, nav_home, nav_search = st.columns([5, 1.5, 1.5], vertical_alignment="center")
with brand:
    st.markdown('<span style="font-size:1.45rem;font-weight:900;color:#17365f">STOCKWISE</span>', unsafe_allow_html=True)
with nav_home:
    st.page_link(home_page, label="TRANG CHỦ", use_container_width=True)
with nav_search:
    st.page_link(search_page, label="TRA CỨU", use_container_width=True)

selected.run()
