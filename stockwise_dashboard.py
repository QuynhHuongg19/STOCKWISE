
# ============================================================
# STOCKWISE 5.0 - VIBRANT OMBRE
# Financial Analytics Platform
# ============================================================

from __future__ import annotations

import numpy as np
import pandas as pd
import io
import re
import html
import base64
import textwrap
import xml.etree.ElementTree as ET
from urllib.parse import quote_plus, urlparse
from email.utils import parsedate_to_datetime
from pathlib import Path
from datetime import datetime
from xml.sax.saxutils import escape as xml_escape

import numpy as np
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import requests
import streamlit as st


# ============================================================
# 1. CONFIGURATION
# ============================================================

st.set_page_config(
    page_title="STOCKWISE | Financial Analytics",
    page_icon="☁️",
    layout="wide",
    initial_sidebar_state="expanded",
)

BASE_DIR = Path(__file__).resolve().parent
PRICE_DIR = BASE_DIR / "data_pipeline" / "data" / "prices"
SYMBOLS_FILE = BASE_DIR / "data_pipeline" / "data" / "symbols.csv"

NAVY = "#102A56"
BLUE = "#448FE6"
PINK = "#E66CAC"
PURPLE = "#9B79DC"
MINT = "#35B99B"

BANK_SYMBOLS = {
    "ACB", "BAB", "BID", "BVB", "CTG", "EIB",
    "HDB", "KLB", "LPB", "MBB", "MSB", "NAB",
    "NVB", "OCB", "PGB", "SGB", "SHB", "SSB",
    "STB", "TCB", "TPB", "VAB", "VCB", "VIB",
    "VPB",
}

COMPANY_NAMES = {
    "BAB": "Ngân hàng TMCP Bắc Á",
    "VCB": "Ngân hàng TMCP Ngoại thương Việt Nam",
    "TCB": "Ngân hàng TMCP Kỹ Thương Việt Nam",
    "BID": "Ngân hàng TMCP Đầu tư và Phát triển Việt Nam",
    "CTG": "Ngân hàng TMCP Công Thương Việt Nam",
    "MBB": "Ngân hàng TMCP Quân đội",
    "ACB": "Ngân hàng TMCP Á Châu",
    "VPB": "Ngân hàng TMCP Việt Nam Thịnh Vượng",
    "STB": "Ngân hàng TMCP Sài Gòn Thương Tín",
    "FPT": "Công ty Cổ phần FPT",
    "HPG": "Công ty Cổ phần Tập đoàn Hòa Phát",
    "VNM": "Công ty Cổ phần Sữa Việt Nam",
    "MWG": "Công ty Cổ phần Đầu tư Thế Giới Di Động",
    "PNJ": "Công ty Cổ phần Vàng bạc Đá quý Phú Nhuận",
    "SSI": "Công ty Cổ phần Chứng khoán SSI",
    "PVT": "Tổng Công ty Cổ phần Vận tải Dầu khí",
}

COMPANY_DOMAINS = {
    "FPT": "fpt.com",
    "VCB": "vietcombank.com.vn",
    "TCB": "techcombank.com",
    "MBB": "mbbank.com.vn",
    "ACB": "acb.com.vn",
    "BID": "bidv.com.vn",
    "CTG": "vietinbank.vn",
    "VPB": "vpbank.com.vn",
    "HPG": "hoaphat.com.vn",
    "VNM": "vinamilk.com.vn",
    "MWG": "mwg.vn",
    "PNJ": "pnj.com.vn",
    "SSI": "ssi.com.vn",
    "BAB": "baca-bank.vn",
    "STB": "sacombank.com.vn",
    "HDB": "hdbank.com.vn",
    "TPB": "tpb.vn",
    "VIB": "vib.com.vn",
    "PVT": "pvtrans.com",
}

TIME_OPTIONS = {
    "1W": 7,
    "1M": 30,
    "3M": 90,
    "6M": 180,
    "1Y": 365,
    "3Y": 1095,
    "ALL": None,
}


# ============================================================
# 2. CSS
# ============================================================

st.markdown(
    """
<style>
.stApp {
    background: linear-gradient(
        180deg,
        #F5FAFF 0%,
        #FFFFFF 48%,
        #FFF7FC 100%
    );
    color: #263B5C !important;
}

/* Leave room for Streamlit's fixed top toolbar so titles are never clipped. */
[data-testid="stMainBlockContainer"],
section.main .block-container,
.block-container {
    max-width: 1550px;
    padding-top: 5.5rem !important;
    padding-bottom: 2rem !important;
}
/* Keep sidebar branding visible beneath Streamlit's top toolbar. */
[data-testid="stSidebarUserContent"] {
    padding-top: 2.5rem !important;
}

.stApp h1,
.stApp h2,
.stApp h3,
.stApp h4 {
    color: #102A56 !important;
    font-weight: 800 !important;
}

.stApp p,
.stApp label,
.stApp li {
    color: #263B5C;
}

/* SIDEBAR */

[data-testid="stSidebar"] {
    background: linear-gradient(
        165deg,
        #F7B1D4 0%,
        #E9BFF6 46%,
        #C2DDFF 100%
    ) !important;
    border-right: 2px solid #E4A1D1 !important;
}

[data-testid="stSidebar"] > div {
    background: transparent !important;
}

[data-testid="stSidebar"] p,
[data-testid="stSidebar"] label {
    color: #263B5C !important;
    font-weight: 650 !important;
}

[data-testid="stSidebar"] input {
    background: #FFFFFF !important;
    color: #102A56 !important;
    font-weight: 750 !important;
    border-radius: 11px !important;
}

[data-testid="stSidebar"] [data-testid="stFileUploader"] {
    background: rgba(255,255,255,.4);
    border-radius: 15px;
    padding: 8px;
}

.brand-box {
    background: linear-gradient(120deg,#FFF8FD,#FFE5F2);
    border: 1px solid #F1B0D5;
    border-radius: 22px;
    padding: 23px 18px;
    margin-bottom: 22px;
    box-shadow: 0 8px 22px rgba(173,78,148,.12);
}

.brand-name {
    font-size: 1.55rem;
    font-weight: 850;
    color: #102A56;
}

.brand-caption {
    margin-top: 7px;
    font-size: .68rem;
    letter-spacing: 1.5px;
    color: #405B80;
    font-weight: 750;
}

.sidebar-menu {
    background: rgba(255,255,255,.32);
    border: 1px solid rgba(255,255,255,.6);
    border-radius: 17px;
    padding: 13px 14px;
    margin: 8px 0;
}

.sidebar-menu-title {
    font-weight: 850;
    color: #102A56;
    margin-bottom: 11px;
}

.sidebar-menu-item {
    padding: 7px 0;
    color: #294A78;
    font-size: .85rem;
    font-weight: 700;
}

/* HEADER */

.stock-header {
    background:
        radial-gradient(
            ellipse at 12% 12%,
            rgba(255,255,255,.88),
            transparent 35%
        ),
        radial-gradient(
            ellipse at 85% 78%,
            rgba(255,255,255,.68),
            transparent 42%
        ),
        linear-gradient(
            115deg,
            #A0D0FF 0%,
            #C6DFFF 42%,
            #E4CBFF 72%,
            #FFD4E8 100%
        );

    border: 1px solid #B9D8FA;
    border-radius: 25px;
    padding: 27px 31px;
    margin: 8px 0 19px;
    box-shadow: 0 13px 32px rgba(74,115,180,.13);
}

.header-top {
    display: flex;
    justify-content: space-between;
    align-items: center;
    gap: 12px;
    flex-wrap: wrap;
    margin-bottom: 15px;
}

.header-logo {
    color: #24548D;
    font-size: .85rem;
    font-weight: 850;
    letter-spacing: 1px;
}

.header-label {
    background: rgba(255,255,255,.67);
    color: #294A78;
    font-size: .71rem;
    font-weight: 750;
    padding: 8px 13px;
    border-radius: 30px;
}

.company-header-content {
    display: flex;
    align-items: center;
    gap: 22px;
    margin-top: 12px;
}

.company-logo-box {
    width: 104px;
    height: 104px;
    min-width: 104px;
    background: rgba(255,255,255,.96);
    border: 1px solid rgba(255,255,255,.9);
    border-radius: 24px;
    display: flex;
    align-items: center;
    justify-content: center;
    box-shadow: 0 8px 24px rgba(37,73,125,.13);
}

.company-logo-box img {
    width: 76px;
    height: 76px;
    object-fit: contain;
}

.company-header-info {
    flex: 1;
    min-width: 0;
}

.stock-name {
    color: #102A56;
    font-size: clamp(1.35rem,2.1vw,1.85rem);
    font-weight: 850;
    line-height: 1.35;
}

.stock-symbol {
    color: #294A78;
    font-size: .88rem;
    font-weight: 750;
    margin-top: 6px;
}

.stock-price-row {
    display: flex;
    align-items: center;
    flex-wrap: wrap;
    gap: 13px;
    margin-top: 15px;
}

.stock-price {
    color: #102A56;
    font-size: clamp(2rem,3.2vw,2.65rem);
    font-weight: 850;
    line-height: 1.15;
}

.stock-change {
    border-radius: 25px;
    padding: 7px 13px;
    font-size: .88rem;
    font-weight: 800;
}

.change-up {
    background: #C8F5DF;
    color: #086C4D;
}

.change-down {
    background: #FFD4E2;
    color: #B42F5E;
}

.change-flat {
    background: #E5EFFF;
    color: #294A78;
}

.stock-meta {
    margin-top: 13px;
    font-size: .79rem;
    color: #405B80;
    font-weight: 650;
}

/* KPI */

.kpi-grid {
    display: grid;
    grid-template-columns: repeat(4,minmax(0,1fr));
    gap: 15px;
    margin: 14px 0 18px;
}

.kpi-card {
    min-height: 124px;
    border-radius: 21px;
    padding: 20px;
    box-shadow: 0 9px 24px rgba(55,95,155,.09);
}

.kpi-pink {
    background: linear-gradient(125deg,#FFEAF4,#F8B9D8);
    border: 1px solid #EFA5CA;
}

.kpi-blue {
    background: linear-gradient(125deg,#E9F5FF,#AED8FF);
    border: 1px solid #99C9F5;
}

.kpi-purple {
    background: linear-gradient(125deg,#F3EBFF,#D4BEFA);
    border: 1px solid #C5AAF1;
}

.kpi-mint {
    background: linear-gradient(125deg,#E7FFF6,#B2EAD7);
    border: 1px solid #9ADFC9;
}

.kpi-label {
    color: #294A78;
    font-size: .84rem;
    font-weight: 750;
    margin-bottom: 12px;
}

.kpi-value {
    color: #102A56;
    font-size: clamp(1.2rem,1.8vw,1.75rem);
    font-weight: 850;
    overflow-wrap: anywhere;
}

.kpi-note {
    color: #405B80;
    font-size: .76rem;
    font-weight: 650;
    margin-top: 8px;
}

/* ANALYSIS */

.analysis-grid {
    display: grid;
    grid-template-columns: repeat(3,minmax(0,1fr));
    gap: 14px;
    margin: 12px 0 22px;
}

.analysis-card {
    border-radius: 20px;
    padding: 19px;
    min-height: 124px;
    box-shadow: 0 8px 21px rgba(60,100,155,.08);
}

.analysis-label {
    color: #294A78;
    font-size: .83rem;
    font-weight: 750;
}

.analysis-value {
    color: #102A56;
    font-size: clamp(1.25rem,2vw,1.8rem);
    font-weight: 850;
    margin-top: 10px;
    overflow-wrap: anywhere;
}

.analysis-note {
    color: #405B80;
    font-size: .77rem;
    font-weight: 650;
    margin-top: 8px;
    line-height: 1.55;
    overflow-wrap: anywhere;
}

.section-heading {
    color: #102A56;
    font-size: 1.22rem;
    font-weight: 850;
    margin: 22px 0 14px;
}

/* TABS */

.stTabs [data-baseweb="tab-list"] {
    background: rgba(255,255,255,.95);
    border: 1px solid #DCE7F6;
    border-radius: 16px;
    padding: 7px;
    gap: 5px;
    margin-bottom: 15px;
}

.stTabs [data-baseweb="tab"] {
    border-radius: 11px;
    padding: 10px 15px;
}

.stTabs [data-baseweb="tab"] p {
    color: #294A78 !important;
    font-weight: 750 !important;
}

.stTabs [aria-selected="true"] {
    background: linear-gradient(110deg,#CBE5FF,#F3D5F1)
        !important;
}

.stTabs [aria-selected="true"] p {
    color: #102A56 !important;
    font-weight: 850 !important;
}

/* METRICS */

[data-testid="stMetricLabel"] p {
    color: #294A78 !important;
    font-weight: 750 !important;
}

[data-testid="stMetricValue"] {
    color: #102A56 !important;
    font-weight: 850 !important;
}

/* CHARTS - raised gradient frame */
[data-testid="stPlotlyChart"] {
    background: linear-gradient(#FFFFFF,#FAFCFF) padding-box,
                linear-gradient(135deg,#FF82D5 0%,#BD9CFF 48%,#80C6FF 100%) border-box !important;
    border: 3px solid transparent !important;
    border-radius: 27px !important;
    padding: 13px !important;
    box-shadow: 0 20px 35px rgba(83,105,188,.28),
                -8px 15px 28px rgba(237,92,190,.23),
                0 0 22px rgba(181,147,255,.22) !important;
    overflow: hidden;
    transition: box-shadow .2s ease, transform .2s ease;
}
[data-testid="stPlotlyChart"]:hover {
    box-shadow: 0 24px 40px rgba(83,105,188,.34),
                -8px 16px 32px rgba(237,92,190,.30) !important;
}

/* TABLES */

[data-testid="stDataFrame"] {
    border: 1px solid #DCE7F5;
    border-radius: 15px;
    overflow: hidden;
}

/* BUTTONS */

div.stButton > button[kind="primary"] {
    background: linear-gradient(110deg,#EE89BF,#D66DAA)
        !important;
    border: none !important;
    color: white !important;
    border-radius: 12px;
    font-weight: 800;
}

div.stButton > button,
div.stDownloadButton > button {
    border-radius: 12px;
}

/* SESSION CARDS - raised pastel + wave decoration */
.info-card {
    --accent: #EE69AD;
    position: relative;
    isolation: isolate;
    overflow: hidden;
    min-height: 118px;
    border: 2px solid var(--accent);
    border-radius: 23px;
    padding: 17px 18px 17px 19px;
    margin-bottom: 17px;
    box-shadow: 0 13px 22px rgba(65,80,140,.15),
                0 12px 24px color-mix(in srgb, var(--accent) 35%, transparent),
                0 0 15px color-mix(in srgb, var(--accent) 20%, transparent);
    transition: transform .2s ease, box-shadow .2s ease;
}
.info-card:hover { transform: translateY(-3px); }
.info-card::before {
    content: "";
    position: absolute;
    z-index: -1;
    width: 65%; height: 80%;
    right: -11%; bottom: -43%;
    border-radius: 50% 42% 0 0;
    background: var(--wave);
    transform: rotate(-24deg);
}
.info-card::after {
    content: "";
    position: absolute;
    z-index: -1;
    width: 50%; height: 60%;
    right: -12%; bottom: -37%;
    border-radius: 48% 55% 0 0;
    background: var(--wave);
    opacity: .7;
    transform: rotate(17deg);
}
.info-pink { --accent:#F58BC7; --wave:rgba(245,103,177,.21); background:linear-gradient(120deg,#FFF5FB,#F9D2E8); }
.info-blue { --accent:#90C3FF; --wave:rgba(99,163,250,.23); background:linear-gradient(120deg,#F5FAFF,#D6E7FF); }
.info-purple { --accent:#C7A3FF; --wave:rgba(166,113,242,.23); background:linear-gradient(120deg,#FBF7FF,#E7D5FF); }
.info-mint { --accent:#85E5CB; --wave:rgba(47,202,165,.23); background:linear-gradient(120deg,#F1FFF9,#C6F3E5); }
.info-top { display:flex; align-items:center; gap:10px; margin-bottom:5px; }
.info-icon {
    display:flex; align-items:center; justify-content:center;
    width:39px; height:39px; flex-shrink:0;
    border-radius:12px;
    background:color-mix(in srgb, var(--accent) 28%, white);
    color: #264B85;
}
.info-icon svg { width:24px; height:24px; stroke:currentColor; fill:none; stroke-width:2.6; stroke-linecap:round; stroke-linejoin:round; }
.info-label { color:#243E69; font-size:.89rem; font-weight:800; }
.info-value { color:#102A56; font-size:1.65rem; font-weight:900; margin-left:49px; letter-spacing:-.4px; }
@media (max-width:700px) {
  .info-card { min-height:105px; padding:13px; }
  .info-value { font-size:1.3rem; margin-left:0; }
}

.soft-banner {
    background: linear-gradient(
        110deg,#FFD9EA,#E8D9FF,#D6EAFF
    );
    border: 1px solid #DFC7F2;
    border-radius: 20px;
    padding: 22px 24px;
    margin: 18px 0;
}

.soft-banner-title {
    color: #102A56;
    font-size: 1.09rem;
    font-weight: 850;
    margin-bottom: 9px;
}

.soft-banner-text {
    color: #294A78;
    font-size: .87rem;
    font-weight: 650;
    line-height: 1.65;
}

.footer {
    text-align: center;
    color: #486184;
    font-size: .81rem;
    font-weight: 650;
    padding: 18px;
}

@media (max-width:1000px) {
    .kpi-grid {
        grid-template-columns: repeat(2,minmax(0,1fr));
    }
}

@media (max-width:650px) {
    .kpi-grid,
    .analysis-grid {
        grid-template-columns: 1fr;
    }

    .stock-header {
        padding: 20px;
    }

    .company-logo-box {
        width: 72px;
        height: 72px;
        min-width: 72px;
        border-radius: 18px;
    }

    .company-logo-box img {
        width: 54px;
        height: 54px;
    }

    .company-header-content {
        gap: 13px;
    }
}

/* STOCKWISE sidebar navigation: selected = vibrant pink/purple */
section[data-testid="stSidebar"] div[data-testid="stButton"] button {
    border-radius: 13px !important;
    border: 1.5px solid #D7B8F5 !important;
    background: linear-gradient(115deg, #FFF1FA, #E6EDFF) !important;
    color: #17345F !important;
    font-weight: 750 !important;
    box-shadow: 0 5px 12px rgba(123, 78, 177, .16) !important;
    transition: transform .16s, box-shadow .16s !important;
}
section[data-testid="stSidebar"] div[data-testid="stButton"] button[kind="primary"] {
    background: linear-gradient(115deg, #F8A1D6, #C4AAFF, #ACD9FF) !important;
    border: 2px solid #C75AC5 !important;
    box-shadow: 0 8px 20px rgba(183, 65, 164, .38) !important;
    color: #102A56 !important;
}
section[data-testid="stSidebar"] div[data-testid="stButton"] button:hover {
    transform: translateY(-2px);
    border-color: #F06BB8 !important;
    box-shadow: 0 10px 22px rgba(167, 71, 173, .34) !important;
}


/* STOCKWISE STARRY GALLERY SAFE THEME: visuals only, no layout repositioning */
.stApp {background:#fff !important;}
[data-testid="stMainBlockContainer"],section.main .block-container,.block-container{
  max-width:1650px !important;width:100% !important;
  margin-left:auto !important;margin-right:auto !important;
}
section[data-testid="stSidebar"],section[data-testid="stSidebar"] > div {
  background:#fff !important;
}
section[data-testid="stSidebar"] {border-right:1px solid #d9e2ed !important;}
section[data-testid="stSidebar"] div[data-testid="stButton"] button{
  background:#fff !important;border:1px solid #d8e3ee !important;
  box-shadow:0 3px 9px rgba(12,40,75,.05) !important;color:#153862 !important;
}
section[data-testid="stSidebar"] div[data-testid="stButton"] button[kind="primary"]{
  background:#e8f2ff !important;border-color:#2875c8 !important;
  color:#123b73 !important;
}
.brand-box {background:#fff !important;border:1px solid #d8e3ee !important;}
.stApp .stock-header{
  background-image:linear-gradient(90deg,rgba(3,20,50,.88),rgba(3,28,66,.5) 70%,rgba(3,28,66,.18)),url("assets/art/hero_starry_sky.webp") !important;
  background-color:#082c61 !important;background-position:center !important;
  background-size:cover !important;border:1px solid #bd9c58 !important;
  border-radius:18px !important;min-height:200px !important;
}
.stApp .stock-header .header-logo,.stApp .stock-header .header-label,
.stApp .stock-header .stock-name,.stApp .stock-header .stock-symbol,
.stApp .stock-header .stock-meta,.stApp .stock-header .stock-price {
  color:#fff !important;text-shadow:0 2px 8px rgba(0,0,0,.4) !important;
}
.stApp .stock-header .stock-name{font-family:Georgia,serif !important;}
.stApp .stTabs [data-baseweb="tab-list"] {
 background:#fff !important;border:0 !important;display:flex !important;
 flex-wrap:nowrap !important;overflow-x:auto !important;gap:8px !important;
}
.stApp .stTabs [data-baseweb="tab"] {
 background:#fff !important;border:1px solid #dbe4ee !important;
 border-radius:12px !important;padding:10px 15px !important;
 min-height:48px !important;white-space:nowrap !important;
}
.stApp .stTabs [data-baseweb="tab"][aria-selected="true"]{
 background:#e8f2ff !important;border-color:#2875c8 !important;
}
.stApp .stTabs [data-baseweb="tab"] p{color:#143a70 !important;}
.stApp .stTabs [data-baseweb="tab-highlight"]{background:#c8a55b !important;}
.stApp .kpi-card,.stApp .info-card,.stApp .kpi-pink,.stApp .kpi-blue,
.stApp .kpi-purple,.stApp .kpi-mint,.stApp .info-pink,
.stApp .info-purple,.stApp .info-mint,.stApp .info-blue{
 background:#fff !important;border:1px solid #dbe4ee !important;
 box-shadow:0 4px 15px rgba(13,43,78,.06) !important;
}
.stApp .kpi-card::before,.stApp .kpi-card::after,
.stApp .info-card::before,.stApp .info-card::after {display:none !important;}

</style>
""",
    unsafe_allow_html=True,
)


# STAR GALLERY theme: safe CSS-only enhancement, keep all original render flow.
_star_art_path = next((q for q in (
    BASE_DIR / "assets" / "art" / "hero_starry_sky.webp",
    BASE_DIR / "assets" / "art" / "stockwise_starry_hero.webp",
) if q.is_file()), None)
if _star_art_path is not None:
    _star_art_b64 = base64.b64encode(_star_art_path.read_bytes()).decode("ascii")
    st.markdown(
        '<style>.stApp .stock-header{background-image:linear-gradient(90deg,rgba(3,20,50,.88),rgba(3,28,66,.5) 70%,rgba(3,28,66,.18)),url("data:image/webp;base64,'
        + _star_art_b64 + '") !important;}</style>',
        unsafe_allow_html=True,
    )

# UI-only stylesheet loaded after the original styles.
_sw_style = BASE_DIR / "stockwise_reference_v2.css"
if _sw_style.is_file():
    st.markdown("<style>" + _sw_style.read_text(encoding="utf-8") + "</style>", unsafe_allow_html=True)

# ============================================================
# 3. HELPERS
# ============================================================

def render_html(content):
    clean = textwrap.dedent(str(content)).strip()
    clean = "\n".join(
        line.lstrip()
        for line in clean.splitlines()
    )
    st.markdown(clean, unsafe_allow_html=True)


def safe_text(value):
    return html.escape(str(value))


def safe_float(value):
    try:
        number = float(value)
        return number if np.isfinite(number) else None
    except (TypeError, ValueError):
        return None


def fmt(value, decimals=2):
    number = safe_float(value)
    if number is None:
        return "N/A"
    return f"{number:,.{decimals}f}"


def fmt_percent(value, scale=1):
    number = safe_float(value)
    if number is None:
        return "N/A"
    return f"{number * scale:,.2f}%"




def financial_percent(value, scale=100):
    return fmt_percent(value, scale=scale)




def section_heading(text):
    render_html(
        f'<div class="section-heading">'
        f'{safe_text(text)}</div>'
    )


def info_card(label, value, color="blue"):
    color = color if color in {"pink", "blue", "purple", "mint"} else "blue"
    icons = {
        "pink": '<polyline points="3 17 9 11 13 15 21 5"/><polyline points="15 5 21 5 21 11"/>',
        "blue": '<path d="M12 20V4"/><path d="m5 11 7-7 7 7"/>',
        "purple": '<path d="M12 4v16"/><path d="m5 13 7 7 7-7"/>',
        "mint": '<rect x="3" y="14" width="4" height="7"/><rect x="10" y="9" width="4" height="12"/><rect x="17" y="3" width="4" height="18"/>',
    }
    render_html(
        f"""
        <div class="info-card info-{color}">
            <div class="info-top">
                <span class="info-icon" aria-hidden="true">
                    <svg viewBox="0 0 24 24">{icons[color]}</svg>
                </span>
                <div class="info-label">{safe_text(label)}</div>
            </div>
            <div class="info-value">{safe_text(value)}</div>
        </div>
        """
    )


def indicator_column(df, *names):
    lookup = {
        str(col).lower().replace("_", ""): col
        for col in df.columns
    }

    for name in names:
        key = name.lower().replace("_", "")
        if key in lookup:
            return lookup[key]

    return None


def shorten_status(value):
    if value is None:
        return "N/A", ""

    text = str(value).strip()
    if not text:
        return "N/A", ""

    match = re.match(
        r"^([^()]+)\s*\((.*)\)\s*$",
        text,
        flags=re.DOTALL,
    )

    if match:
        return (
            match.group(1).strip(),
            match.group(2).strip(),
        )

    if len(text) <= 32:
        return text, ""

    words = text.split()
    return " ".join(words[:3]), " ".join(words[3:])


# ============================================================

# ============================================================
# 4. AUTO COMPANY LOGO - STOCKWISE
# ============================================================

from urllib.parse import urljoin, urlparse, quote
from bs4 import BeautifulSoup

# Website đã xác minh hoặc được cấu hình sẵn.
# Các mã khác vẫn có thể được tra cứu tự động.
COMPANY_DOMAINS = {
    "FPT": "fpt.com",
    "VCB": "vietcombank.com.vn",
    "TCB": "techcombank.com",
    "MBB": "mbbank.com.vn",
    "ACB": "acb.com.vn",
    "BID": "bidv.com.vn",
    "CTG": "vietinbank.vn",
    "VPB": "vpbank.com.vn",
    "HPG": "hoaphat.com.vn",
    "VNM": "vinamilk.com.vn",
    "MWG": "mwg.vn",
    "PNJ": "pnj.com.vn",
    "SSI": "ssi.com.vn",
    "BAB": "baca-bank.vn",
    "STB": "sacombank.com.vn",
    "HDB": "hdbank.com.vn",
    "TPB": "tpb.vn",
    "VIB": "vib.com.vn",
    "PVT": "pvtrans.com",
}

LOGO_HEADERS = {
    "User-Agent": "Mozilla/5.0 STOCKWISE/1.0"
}


def image_to_data_uri(content, content_type):
    """Chuyển ảnh thành dạng nhúng HTML."""
    content_type = content_type.split(";")[0].lower().strip()

    allowed = {
        "image/png",
        "image/jpeg",
        "image/webp",
        "image/gif",
        "image/x-icon",
        "image/vnd.microsoft.icon",
    }

    if content_type not in allowed:
        return None

    if not content or len(content) > 1_000_000:
        return None

    encoded = base64.b64encode(content).decode("ascii")
    return f"data:{content_type};base64,{encoded}"


def download_logo(url):
    """Tải logo và hiển thị nguyên nhân khi thất bại."""
    try:
        response = requests.get(
            url,
            headers={
                "User-Agent": "Mozilla/5.0",
                "Accept": "image/png,image/jpeg,image/webp,image/*",
            },
            timeout=10,
            allow_redirects=True,
        )

        response.raise_for_status()

        content_type = response.headers.get(
            "Content-Type", ""
        ).split(";")[0].strip().lower()

        if content_type == "image/jpg":
            content_type = "image/jpeg"

        if content_type == "application/octet-stream":
            content_type = "image/x-icon"

        logo = image_to_data_uri(
            response.content,
            content_type,
        )

        if logo is None:
            print(
                f"[LOGO] Ảnh không hợp lệ: {url} "
                f"| Content-Type: {content_type} "
                f"| Bytes: {len(response.content)}"
            )

        return logo

    except requests.RequestException as exc:
        print(f"[LOGO] Lỗi tải {url}: {exc}")
        return None

def normalize_domain(website):
    """Chỉ chuẩn hóa và trả về tên miền."""
    if not website:
        return None

    website = str(website).strip()

    if not website.startswith(("http://", "https://")):
        website = "https://" + website

    parsed = urlparse(website)
    domain = (parsed.hostname or "").lower()

    if domain.startswith("www."):
        domain = domain[4:]

    if not domain or "." not in domain:
        return None

    return domain

def find_company_website(symbol):
    """
    Tra cứu website từ dữ liệu công ty.

    Ưu tiên danh sách cấu hình.
    Nếu không có, thử dữ liệu doanh nghiệp từ vnstock.
    """
    if symbol in COMPANY_DOMAINS:
        return COMPANY_DOMAINS[symbol]

    try:
        from vnstock import Vnstock

        stock = Vnstock().stock(
            symbol=symbol,
            source="VCI",
        )

        profile = stock.company.profile()

        if profile is None or profile.empty:
            return None

        possible_columns = [
            "website",
            "company_website",
            "companyWebsite",
            "web",
        ]

        for column in possible_columns:
            if column not in profile.columns:
                continue

            for value in profile[column].dropna():
                domain = normalize_domain(value)

                if domain:
                    return domain

    except Exception:
        pass

    return None


def get_website_icon(domain):
    """
    Tìm icon được khai báo trên website doanh nghiệp.
    """
    website = "https://" + domain

    try:
        response = requests.get(
            website,
            headers=LOGO_HEADERS,
            timeout=7,
        )

        response.raise_for_status()

        soup = BeautifulSoup(
            response.text,
            "html.parser",
        )

        icon_urls = []

        for link in soup.find_all("link"):
            rel = " ".join(
                link.get("rel", [])
            ).lower()

            href = link.get("href")

            if not href:
                continue

            if "icon" in rel:
                icon_urls.append(
                    urljoin(response.url, href)
                )

        icon_urls.append(
            urljoin(response.url, "/favicon.ico")
        )

        for icon_url in icon_urls:
            # Chỉ lấy ảnh từ website đang tra cứu.
            icon_domain = normalize_domain(icon_url)

            if icon_domain != domain:
                continue

            result = download_logo(icon_url)

            if result:
                return result

    except Exception:
        pass

    return None


@st.cache_data(ttl=86400, show_spinner=False)
def get_company_logo(symbol):
    """
    Tự động tìm logo theo mã cổ phiếu.

    Thứ tự:
    1. Website được cấu hình
    2. Website tra cứu từ vnstock
    3. Icon của website doanh nghiệp
    4. Favicon từ Google
    5. Không tìm được -> giao diện dùng icon dự phòng
    """
    symbol = str(symbol).strip().upper()

    domain = find_company_website(symbol)

    if not domain:
        return None

    # Ưu tiên icon trực tiếp từ website doanh nghiệp.
    logo = get_website_icon(domain)

    if logo:
        return logo

    # Fallback: Google favicon.
    google_icon_url = (
        "https://www.google.com/s2/favicons"
        f"?domain={quote(domain)}&sz=128"
    )

    logo = download_logo(google_icon_url)

    if logo:
        return logo

    return None


# ============================================================
# 5. PRICE DATA
# ============================================================

def normalize_prices(raw, symbol):
    df = raw.copy()

    df.columns = [
        str(col).strip().lower()
        for col in df.columns
    ]

    aliases = {
        "datetime": "date",
        "time": "date",
        "tradingdate": "date",
        "ticker": "symbol",
        "code": "symbol",
        "vol": "volume",
        "totalvolume": "volume",
    }

    for old, new in aliases.items():
        if old in df.columns and new not in df.columns:
            df = df.rename(columns={old: new})

    if "symbol" not in df.columns:
        df["symbol"] = symbol

    required = [
        "date", "symbol", "open", "high",
        "low", "close", "volume",
    ]

    missing = [
        col for col in required
        if col not in df.columns
    ]

    if missing:
        raise ValueError(
            "CSV thiếu các cột: "
            + ", ".join(missing)
        )

    df["date"] = pd.to_datetime(
        df["date"],
        errors="coerce",
    )

    df["symbol"] = (
        df["symbol"]
        .astype(str)
        .str.strip()
        .str.upper()
    )

    for col in [
        "open", "high", "low", "close", "volume"
    ]:
        df[col] = pd.to_numeric(
            df[col],
            errors="coerce",
        )

    df = df.dropna(
        subset=[
            "date", "open", "high",
            "low", "close",
        ]
    )

    valid = (
        (df["symbol"] == symbol)
        & (df["open"] > 0)
        & (df["high"] > 0)
        & (df["low"] > 0)
        & (df["close"] > 0)
        & (df["volume"] >= 0)
        & (
            df["high"]
            >= df[["open", "close", "low"]].max(axis=1)
        )
        & (
            df["low"]
            <= df[["open", "close", "high"]].min(axis=1)
        )
    )

    df = df[valid]

    return (
        df.sort_values("date")
        .drop_duplicates("date", keep="last")
        .reset_index(drop=True)
    )


@st.cache_data(show_spinner=False)
def read_local_csv(path, modified, symbol):
    raw = pd.read_csv(path)
    return normalize_prices(raw, symbol)


@st.cache_data(show_spinner=False)
def read_symbol_directory(path, modified):
    """Read TV1 symbol metadata without querying an external API."""
    frame = pd.read_csv(path, dtype=str, encoding="utf-8-sig")
    if "symbol" not in frame.columns:
        return {}
    frame["symbol"] = frame["symbol"].fillna("").str.strip().str.upper()
    name_col = next((c for c in ("organ_name", "en_organ_name") if c in frame.columns), None)
    if name_col is None:
        return {}
    frame = frame.dropna(subset=[name_col])
    frame = frame[frame["symbol"].str.fullmatch(r"[A-Z0-9]{2,10}")]
    return dict(zip(frame["symbol"], frame[name_col].astype(str)))


def company_display_name(symbol):
    if SYMBOLS_FILE.is_file():
        try:
            names = read_symbol_directory(str(SYMBOLS_FILE), SYMBOLS_FILE.stat().st_mtime)
            name = names.get(symbol)
            if name and name.strip():
                return name.strip()
        except (OSError, ValueError, KeyError, pd.errors.ParserError):
            pass
    return COMPANY_NAMES.get(symbol, f"Cổ phiếu {symbol}")


@st.cache_data(ttl=600, show_spinner=False)
def fetch_live_prices(symbol):
    """L?y gi? theo ng?y: ?u ti?n KBS, d? ph?ng VCI."""
    from datetime import date, timedelta
    from vnstock.api.quote import Quote

    symbol = str(symbol).strip().upper()
    start_date = (date.today() - timedelta(days=90)).isoformat()
    end_date = (date.today() + timedelta(days=1)).isoformat()

    for api_source in ("KBS", "VCI"):
        try:
            quote = Quote(symbol=symbol, source=api_source)
            raw = quote.history(
                start=start_date,
                end=end_date,
                interval="1D",
            )

            if raw is None or raw.empty:
                print(
                    f"[STOCKWISE API] {symbol}: {api_source} EMPTY",
                    flush=True,
                )
                continue

            raw = raw.rename(columns={"time": "date"}).copy()

            if "date" not in raw.columns:
                raise ValueError("API response missing date column")

            raw["date"] = pd.to_datetime(
                raw["date"], errors="coerce"
            ).dt.normalize()

            raw = raw.dropna(subset=["date"])
            live_df = normalize_prices(raw, symbol)

            if live_df.empty:
                print(
                    f"[STOCKWISE API] {symbol}: {api_source} NORMALIZED EMPTY",
                    flush=True,
                )
                continue

            print(
                f"[STOCKWISE API] {symbol}: {api_source} SUCCESS | "
                f"rows={len(live_df)} | "
                f"latest={live_df['date'].max()}",
                flush=True,
            )
            live_df.attrs["stockwise_source"] = api_source
            return live_df

        except Exception as exc:
            print(
                f"[STOCKWISE API] {symbol}: {api_source} FAILED | "
                f"{type(exc).__name__}: {exc}",
                flush=True,
            )

    return pd.DataFrame()



def load_prices(symbol):
    """Ưu tiên API mới, giữ CSV làm dữ liệu lịch sử và dự phòng."""
    candidates = [
        PRICE_DIR / f"{symbol}.csv",
        PRICE_DIR / f"{symbol.lower()}.csv",
        BASE_DIR / "data" / f"{symbol}.csv",
        BASE_DIR / f"{symbol}.csv",
    ]

    local_df = pd.DataFrame()
    local_source = ""

    for path in candidates:
        if not path.exists():
            continue

        df = read_local_csv(
            str(path),
            path.stat().st_mtime,
            symbol,
        )

        if not df.empty:
            local_df = df
            try:
                local_source = str(path.relative_to(BASE_DIR))
            except ValueError:
                local_source = str(path)
            break

    try:
        live_df = fetch_live_prices(symbol)

        if live_df.empty:
            print(
                f"[STOCKWISE API] {symbol}: API returned empty data",
                flush=True,
            )
        else:
            print(
                f"[STOCKWISE API] {symbol}: SUCCESS | "
                f"rows={len(live_df)} | "
                f"latest={live_df['date'].max()}",
                flush=True,
            )

    except Exception as exc:
        live_df = pd.DataFrame()

        print(
            f"[STOCKWISE API] {symbol}: FAILED | "
            f"{type(exc).__name__}: {exc}",
            flush=True,
        )

        st.warning(
            f"Không thể cập nhật giá trực tuyến cho {symbol}. "
            "Đang sử dụng dữ liệu CSV dự phòng."
        )

    if not live_df.empty:
        api_source = live_df.attrs.get("stockwise_source", "API")
        source_label = f"Vnstock {api_source}"

        if not local_df.empty:
            combined = pd.concat(
                [local_df, live_df],
                ignore_index=True,
            )
            combined = (
                combined.sort_values("date")
                .drop_duplicates(subset=["date"], keep="last")
                .reset_index(drop=True)
            )
            return combined, source_label + " + " + local_source

        return live_df, source_label

    return local_df, local_source
# ============================================================
# 6. CHARTS
# ============================================================

def style_plot(fig, height=450):
    fig.update_layout(
        template="plotly_white",
        height=height,
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="#FFFFFF",
        font=dict(
            family="Arial",
            size=12,
            color=NAVY,
        ),
        margin=dict(
            l=12, r=12, t=45, b=40
        ),
        hovermode="x unified",
        legend=dict(
            orientation="h",
            y=-0.18,
            x=0.5,
            xanchor="center",
        ),
    )

    fig.update_xaxes(
        gridcolor="#EAF0F8",
        showgrid=True,
    )

    fig.update_yaxes(
        gridcolor="#EAF0F8",
        showgrid=True,
        zeroline=False,
    )

    return fig


def create_price_chart(stock):
    data = stock.copy()

    fig = make_subplots(
        rows=2,
        cols=1,
        shared_xaxes=True,
        row_heights=[0.77, 0.23],
        vertical_spacing=0.055,
    )

    fig.add_trace(
        go.Candlestick(
            x=data["date"],
            open=data["open"],
            high=data["high"],
            low=data["low"],
            close=data["close"],
            name="Giá cổ phiếu",
            increasing_line_color=MINT,
            decreasing_line_color=PINK,
            increasing_fillcolor="#B6EBE1",
            decreasing_fillcolor="#F8C7DD",
        ),
        row=1,
        col=1,
    )

    bar_colors = np.where(
        data["close"] >= data["open"],
        "#7DD7C4",
        "#EEA0C6",
    )

    fig.add_trace(
        go.Bar(
            x=data["date"],
            y=data["volume"],
            marker_color=bar_colors,
            name="Khối lượng",
        ),
        row=2,
        col=1,
    )

    fig.update_layout(
        showlegend=False,
        xaxis_rangeslider_visible=False,
        xaxis2_rangeslider_visible=False,
    )

    fig.update_yaxes(
        title_text="Giá",
        row=1,
        col=1,
    )

    fig.update_yaxes(
        title_text="KL",
        row=2,
        col=1,
    )

    return style_plot(fig, 500)


# ============================================================
# 7. TECHNICAL ANALYSIS
# ============================================================

def technical_frame(stock):
    return stock.rename(
        columns={
            "date": "Date",
            "symbol": "Symbol",
            "open": "Open",
            "high": "High",
            "low": "Low",
            "close": "Close",
            "volume": "Volume",
        }
    )


@st.cache_data(show_spinner=False)
def run_technical(stock):
    from technical_analysis import (
        add_indicators,
        classify_symbol,
        check_data,
    )

    source = technical_frame(stock)
    indicators = add_indicators(source)
    signals, summary = classify_symbol(indicators)
    quality = check_data(source)

    return indicators, signals, summary, quality



def technical_input_for_scoring(stock):
    """Reuse actual TV2 signals in TV4 and PDF scoring; never infer missing signals."""
    _, signals, _, _ = run_technical(stock)
    mapping = {"Tích cực": 1, "Trung lập": 0, "Tiêu cực": -1}
    reasons = [
        {"rule": str(sig.get("Chỉ báo", "")),
         "score": mapping[sig["Tín hiệu"]],
         "label": sig["Tín hiệu"],
         "explain": sig.get("Giải thích", "")}
        for sig in signals
        if isinstance(sig, dict) and sig.get("Tín hiệu") in mapping
    ]
    return {"reasons": reasons} if reasons else None


def technical_chart(indicators):
    df = indicators.tail(250).copy()

    date_col = indicator_column(
        df, "Date", "date"
    )

    if date_col is None:
        df["Date"] = pd.RangeIndex(len(df))
        date_col = "Date"

    fig = make_subplots(
        rows=3,
        cols=1,
        shared_xaxes=True,
        row_heights=[0.56, 0.19, 0.25],
        vertical_spacing=0.075,
        subplot_titles=[
            "Giá và đường trung bình",
            "RSI",
            "MACD",
        ],
    )

    open_col = indicator_column(df, "Open")
    high_col = indicator_column(df, "High")
    low_col = indicator_column(df, "Low")
    close_col = indicator_column(df, "Close")

    if all(
        col is not None
        for col in [
            open_col, high_col,
            low_col, close_col,
        ]
    ):
        fig.add_trace(
            go.Candlestick(
                x=df[date_col],
                open=df[open_col],
                high=df[high_col],
                low=df[low_col],
                close=df[close_col],
                name="Giá",
                increasing_line_color=MINT,
                decreasing_line_color=PINK,
            ),
            row=1,
            col=1,
        )

    # SMA200: t?nh tr?n to?n b? l?ch s? tr??c khi v?
    if "SMA200" not in df.columns and "sma200" not in df.columns:
        close_col = next(
            (c for c in df.columns if str(c).lower() == "close"),
            None,
        )
        if close_col is not None:
            df = df.copy()
            df["SMA200"] = pd.to_numeric(
                df[close_col], errors="coerce"
            ).rolling(window=200, min_periods=200).mean()

    for name, color in [
        ("SMA20", BLUE),
        ("SMA50", PURPLE),
        ("SMA200", "#D4AF37"),
    ]:
        col = indicator_column(df, name)

        if col is not None:
            fig.add_trace(
                go.Scatter(
                    x=df[date_col],
                    y=df[col],
                    mode="lines",
                    name=name,
                    line=dict(
                        color=color,
                        width=2.5,
                    ),
                ),
                row=1,
                col=1,
            )

    rsi_col = indicator_column(
        df, "RSI14", "RSI"
    )

    if rsi_col is not None:
        fig.add_trace(
            go.Scatter(
                x=df[date_col],
                y=df[rsi_col],
                name="RSI",
                line=dict(
                    color=PURPLE,
                    width=2.5,
                ),
            ),
            row=2,
            col=1,
        )

        fig.add_hline(
            y=70,
            line_dash="dash",
            line_color=PINK,
            row=2,
            col=1,
        )

        fig.add_hline(
            y=30,
            line_dash="dash",
            line_color=MINT,
            row=2,
            col=1,
        )

    for name, color in [
        ("MACD", BLUE),
        ("MACD_Signal", PINK),
    ]:
        col = indicator_column(df, name)

        if col is not None:
            fig.add_trace(
                go.Scatter(
                    x=df[date_col],
                    y=df[col],
                    name=name,
                    line=dict(
                        color=color,
                        width=2.5,
                    ),
                ),
                row=3,
                col=1,
            )

    hist_col = indicator_column(
        df, "MACD_Hist"
    )

    if hist_col is not None:
        fig.add_trace(
            go.Bar(
                x=df[date_col],
                y=df[hist_col],
                name="MACD Histogram",
                marker_color="#A8D1FA",
            ),
            row=3,
            col=1,
        )

    fig.update_layout(
        xaxis_rangeslider_visible=False,
    )

    return style_plot(fig, 760)


# ============================================================
# 8. FINANCIAL ANALYSIS
# ============================================================

@st.cache_data(show_spinner=False, ttl=3600)
def run_financial(symbol, period, company_type):
    from fundamental_analysis import (
        run_fundamental_analysis,
    )

    return run_fundamental_analysis(
        ticker=symbol,
        period=period,
        company_type=company_type,
    )


def financial_line_chart(
    comparison,
    fields,
    title,
):
    if (
        not isinstance(comparison, pd.DataFrame)
        or comparison.empty
        or "period" not in comparison.columns
    ):
        return None

    df = comparison.copy()
    df["period"] = df["period"].astype(str)
    df = df.sort_values("period")

    fig = go.Figure()
    colors_list = [
        BLUE, PINK, PURPLE, MINT
    ]

    count = 0

    for i, field in enumerate(fields):
        if field not in df.columns:
            continue

        values = pd.to_numeric(
            df[field],
            errors="coerce",
        )

        if not values.notna().any():
            continue

        fig.add_trace(
            go.Scatter(
                x=df["period"],
                y=values,
                mode="lines+markers",
                name=field.upper(),
                line=dict(
                    color=colors_list[
                        i % len(colors_list)
                    ],
                    width=3,
                ),
                marker=dict(size=8),
            )
        )

        count += 1

    if count == 0:
        return None

    fig.update_layout(title=title)
    fig.update_xaxes(type="category")

    return style_plot(fig, 335)


# ============================================================
# 9. SIDEBAR
# ============================================================

with st.sidebar:
    render_html(
        """
        <div class="brand-box">
            <div class="brand-name">
                ☁️ STOCKWISE
            </div>
            <div class="brand-caption">
                FINANCIAL ANALYTICS PLATFORM
            </div>
        </div>
        """
    )

    st.markdown("### 🔎 Tra cứu cổ phiếu")

    symbol_input = st.text_input(
        "Mã cổ phiếu",
        value="BAB",
        placeholder="BAB, VCB, PVT, FPT...",
    )

    symbol = symbol_input.strip().upper()

    uploaded = st.file_uploader(
        "Hoặc tải CSV dữ liệu giá",
        type=["csv"],
    )

    st.divider()

    # Menu điều hướng tương tác: nút được chọn giữ màu nổi bật.
    NAV_TABS = [
        "🏠 Tổng quan", "📈 Kỹ thuật", "🏦 Tài chính",
        "🎯 Đánh giá", "📁 Dữ liệu", "📄 Báo cáo PDF", "🔍 So sánh",
    ]
    NAV_LABELS = [
        "📊 Tổng quan cổ phiếu", "📈 Phân tích kỹ thuật",
        "🏦 Phân tích tài chính", "🎯 Đánh giá tổng hợp",
        "📁 Dữ liệu", "📄 Báo cáo phân tích", "🔍 So sánh cổ phiếu",
    ]
    if "stockwise_active_tab" not in st.session_state:
        st.session_state["stockwise_active_tab"] = NAV_TABS[0]

    def stockwise_select_tab(tab_name):
        st.session_state["stockwise_active_tab"] = tab_name
        st.session_state["stockwise_tabs"] = tab_name

    render_html('<div class="sidebar-menu-title">🧭 Khám phá</div>')
    for tab_name, nav_label in zip(NAV_TABS, NAV_LABELS):
        st.button(
            nav_label,
            key=f"stockwise_nav_{NAV_TABS.index(tab_name)}",
            type="primary" if st.session_state["stockwise_active_tab"] == tab_name else "secondary",
            use_container_width=True,
            on_click=stockwise_select_tab,
            args=(tab_name,),
        )


# ============================================================
# 10. LOAD STOCK DATA
# ============================================================

if not re.fullmatch(
    r"[A-Z0-9]{2,10}",
    symbol,
):
    st.warning(
        "Vui lòng nhập mã cổ phiếu hợp lệ."
    )
    st.stop()

try:
    if uploaded is not None:
        raw = pd.read_csv(
            io.BytesIO(
                uploaded.getvalue()
            )
        )

        stock = normalize_prices(
            raw, symbol
        )

        source = (
            f"CSV tải lên: {uploaded.name}"
        )

    else:
        stock, source = load_prices(symbol)

except Exception as exc:
    st.error(
        f"Lỗi đọc dữ liệu: {exc}"
    )
    st.stop()

if stock.empty:
    st.warning(
        f"Chưa tìm thấy dữ liệu giá "
        f"cho mã {symbol}."
    )

    st.info(
        "Chọn mã có CSV trong "
        "data_pipeline/data/prices "
        "hoặc tải CSV lên."
    )

    st.stop()

stock = (
    stock.sort_values("date")
    .reset_index(drop=True)
)

latest = stock.iloc[-1]

latest_date = pd.Timestamp(
    latest["date"]
).strftime("%d/%m/%Y")

company_name = company_display_name(symbol)


# ============================================================
# 11. TIME RANGE
# ============================================================

st.markdown(
    "##### 📅 Khoảng thời gian phân tích"
)

selected_time = st.segmented_control(
    "Chọn khoảng thời gian",
    options=list(TIME_OPTIONS.keys()),
    default="1M",
    selection_mode="single",
    key="stock_time_range",
    label_visibility="collapsed",
)

if selected_time is None:
    selected_time = "1M"

days = TIME_OPTIONS[selected_time]

if days is None:
    filtered_stock = stock.copy()

else:
    end_date = stock["date"].max()

    start_date = (
        end_date - pd.Timedelta(days=days)
    )

    filtered_stock = stock[
        stock["date"] >= start_date
    ].copy()

if filtered_stock.empty:
    filtered_stock = stock.tail(1).copy()

start_price = safe_float(
    filtered_stock.iloc[0]["close"]
)

end_price = safe_float(
    filtered_stock.iloc[-1]["close"]
)

if (
    start_price is not None
    and start_price > 0
    and end_price is not None
    and len(filtered_stock) >= 2
):
    change_pct = (
        (end_price / start_price) - 1
    ) * 100
else:
    change_pct = None

if change_pct is None:
    change_text = "N/A"
    change_class = "change-flat"

elif change_pct > 0:
    change_text = (
        f"▲ +{change_pct:.2f}%"
    )
    change_class = "change-up"

elif change_pct < 0:
    change_text = (
        f"▼ {change_pct:.2f}%"
    )
    change_class = "change-down"

else:
    change_text = "● 0.00%"
    change_class = "change-flat"

delta_text = (
    f"{change_pct:+.2f}%"
    if change_pct is not None
    else "N/A"
)


# ============================================================
# 12. STOCK HEADER WITH LOGO
# ============================================================

company_logo = get_company_logo(symbol)
if company_logo:
    logo_html = (
        '<div class="company-logo-box">'
        f'<img src="{html.escape(company_logo, quote=True)}" '
        'alt="Company icon">'
        '</div>'
    )
else:
    logo_html = (
        '<div class="company-logo-box sw-logo-fallback">'
        '<img src="data:image/webp;base64,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IA0xKI9F696K8amBr3UAV9I14U1dV3rwAnvWoSisJxr4qNW0BqPQO9nUIioqD2HGvun7atoXr4jUDRV0j4190c3Wreka96RqAZSV44Gvun7auIGvCo1Aoq6dfBa8asAvUukA6gGVdA768rVtDX1DUAVdPOvClk6trvqJHOoFEAnbjXvR9tWLqRGoRlXSPjXhUfGrekE6+KgdtQhUU8686PnVwvm61901351LAU9OvQura19WpZCnoPxr4IRq6tfVqEKSh+NedH21fWvq1LIUhPtqQTVoGvPOoQh0d9fBB8as8HXo1AkOkX214UBv/TVngfrqfTfetQgOIQK5197erm15251CFJS9fFPtxq868PGoQH9s/Gvfb+2rzrzUAU+39jr7p1dr0AfGoQpKH4190/bV5HGvABqEKugnxrwJq/pHydfdI++oErCccjUSmrq190j5OoQoKE+Br3pIHI86u6QK5OvCBeoQoKa+6L8auIF19r15Q1AFYj1906t14dQhX06+K8dtWEa+A40SFITyPGvShI7atoa9IBvQIUBCKFf316V6geNXdyAQNeECuBWoEp6B8a86Bq6hxr6vGiAqCVVa8KDV1D419Q+NAhQEr8oGvOj5r+2r6Hxr4qLA+dQhQEBNXWpiOqrx51aFBGpdI4/TUIUCMc8d9SEYI7mtWUPjUq1CFAiPjXxiPH9tW1r3QIUmEfP7a86KBAHnV4GvqHOiQHKX3HjUlQedW1zr3o1AFXRwLN68KcWO/bV9AAGu+vWUA3541CA5TnUejRDKAf21UeL/AF1AlfT2/XTnZkP4We+3uD/TSlhpzs4AxZj59wf6agGFQ/TnY7H/AAzIf/0hru2Qtu4BHc9/9dcKX/8AKofvKv8AqNd3mX62F9iR21pw8My5dqAmsDiv21USASARWrnNk3qlyR8ftq4qP//Z" alt="Starry Night — hình thay thế logo doanh nghiệp">'
        '</div>'
    )

header_html = f"""
<div class="stock-header">

    <div class="header-top">
        <div class="header-logo">
            ☁️ STOCKWISE
        </div>

        <div class="header-label">
            FINANCIAL ANALYTICS PLATFORM
        </div>
    </div>

    <div class="company-header-content">

        {logo_html}

        <div class="company-header-info">

            <div class="stock-name">
                {safe_text(company_name)}
            </div>

            <div class="stock-symbol">
                {safe_text(symbol)} ·
                Thị trường chứng khoán Việt Nam
            </div>

            <div class="stock-price-row">

                <span class="stock-price">
                    {fmt(latest["close"])}
                </span>

                <span class="stock-change {change_class}">
                    {selected_time}: {change_text}
                </span>

            </div>

            <div class="stock-meta">
                Giá đóng cửa ·
                Phiên dữ liệu: {latest_date} ·
                Không phải báo giá thời gian thực
            </div>

        </div>

    </div>

</div>
"""

render_html(header_html)


# ============================================================
# 13. MAIN TABS
# ============================================================

# Đồng bộ hai chiều: click tab trên cùng cũng đổi màu menu trái.
def stockwise_tab_changed():
    st.session_state["stockwise_active_tab"] = st.session_state["stockwise_tabs"]

# st.tabs(key=..., on_change=...) yêu cầu Streamlit phiên bản mới.
tabs = st.tabs(
    NAV_TABS,
    key="stockwise_tabs",
    on_change=stockwise_tab_changed,
)


# ============================================================
# COMPANY SNAPSHOT & PUBLIC NEWS (opt-in network request)
# ============================================================

NEWS_FEEDS = {
    "CafeF": ["https://cafef.vn/thi-truong-chung-khoan.rss", "https://cafef.vn/doanh-nghiep.rss", "https://cafef.vn/tai-chinh-ngan-hang.rss"],
    "VnExpress": ["https://vnexpress.net/rss/kinh-doanh.rss"],
    "Thanh Niên": ["https://thanhnien.vn/rss/kinh-te/chung-khoan.rss", "https://thanhnien.vn/rss/kinh-te/doanh-nghiep.rss", "https://thanhnien.vn/rss/kinh-te/ngan-hang.rss"],
}
NEWS_DOMAINS = {"CafeF": "cafef.vn", "VnExpress": "vnexpress.net", "Thanh Niên": "thanhnien.vn"}
NEWS_ALIASES = {
    "FPT": ["fpt"], "HPG": ["hòa phát", "hoà phát"], "VNM": ["vinamilk"],
    "MWG": ["thế giới di động", "điện máy xanh"], "PNJ": ["phú nhuận", "pnj"],
    "VCB": ["vietcombank"], "TCB": ["techcombank"], "MBB": ["mb bank", "mbbank", "ngân hàng quân đội"],
    "ACB": ["ngân hàng á châu"], "BID": ["bidv"], "CTG": ["vietinbank"],
    "VPB": ["vpbank"], "STB": ["sacombank"], "SSI": ["chứng khoán ssi"],
}


def stockwise_news_matches(title, description, ticker, company):
    import unicodedata
    def normalize(value):
        value = unicodedata.normalize("NFD", str(value).lower())
        return "".join(c for c in value if unicodedata.category(c) != "Mn").replace("đ", "d")
    content = normalize(title + " " + description)
    # Avoid false positives for short symbols inside unrelated words.
    terms = [ticker] + NEWS_ALIASES.get(ticker, [])
    # Company full name is only useful when a real name was provided.
    if company and company != f"Cổ phiếu {ticker}":
        terms.append(company)
    return any(re.search(r"(?<![a-z0-9])" + re.escape(normalize(term)) + r"(?![a-z0-9])", content)
               for term in terms if len(normalize(term)) >= 3)


@st.cache_data(ttl=600, show_spinner=False)
def stockwise_direct_news(ticker, company):
    """Fetch publisher RSS; show ONLY direct publisher article links."""
    from concurrent.futures import ThreadPoolExecutor, as_completed
    from urllib.parse import urlsplit
    feeds = [(source, url) for source, urls in NEWS_FEEDS.items() for url in urls]
    def load_feed(source, feed_url):
        response = requests.get(feed_url, timeout=7, headers={"User-Agent": "Mozilla/5.0 (compatible; STOCKWISE-News/1.0)"})
        response.raise_for_status()
        root = ET.fromstring(response.content)
        result = []
        for entry in root.findall("./channel/item"):
            title = html.unescape((entry.findtext("title") or "").strip())
            description = re.sub(r"<[^>]+>", " ", entry.findtext("description") or "")
            link = (entry.findtext("link") or "").strip()
            host = (urlsplit(link).hostname or "").lower()
            allowed = NEWS_DOMAINS[source]
            if urlsplit(link).scheme != "https" or not (host == allowed or host.endswith("." + allowed)):
                continue
            if not stockwise_news_matches(title, description, ticker, company):
                continue
            raw_date = (entry.findtext("pubDate") or "").strip()
            try:
                dt = parsedate_to_datetime(raw_date)
                if dt.tzinfo is None:
                    from datetime import timezone
                    dt = dt.replace(tzinfo=timezone.utc)
                timestamp = dt.timestamp()
                date_label = dt.strftime("%d/%m/%Y %H:%M")
            except (TypeError, ValueError, OverflowError):
                timestamp, date_label = 0, "Không rõ ngày đăng"
            if title:
                result.append({"title": title, "url": link, "source": source, "date": date_label, "timestamp": timestamp})
        return result
    articles, errors = [], []
    with ThreadPoolExecutor(max_workers=6) as pool:
        tasks = {pool.submit(load_feed, source, url): source for source, url in feeds}
        for task in as_completed(tasks):
            try:
                articles.extend(task.result())
            except (requests.RequestException, ET.ParseError, ValueError) as exc:
                errors.append(tasks[task])
    unique = {article["url"].split("?")[0]: article for article in articles}
    return sorted(unique.values(), key=lambda item: item["timestamp"], reverse=True), sorted(set(errors))


@st.cache_data(ttl=3600, show_spinner=False)
def stockwise_news_thumbnail(article_url):
    """Optional article thumbnail for presentation only; price/news filtering unchanged."""
    from urllib.parse import urlsplit
    host = (urlsplit(article_url).hostname or "").lower()
    if not any(host == domain or host.endswith("." + domain) for domain in NEWS_DOMAINS.values()):
        return None
    try:
        response = requests.get(article_url, timeout=3, headers={"User-Agent": "Mozilla/5.0"})
        response.raise_for_status()
        # Metadata only, never scrape article text or alter the news source.
        match = re.search(
            r"<meta[^>]+(?:property|name)=[\"']og:image[\"'][^>]+content=[\"']([^\"']+)",
            response.text[:100000], re.I,
        )
        if not match:
            match = re.search(
                r"<meta[^>]+content=[\"']([^\"']+)[\"'][^>]+(?:property|name)=[\"']og:image",
                response.text[:100000], re.I,
            )
        if match:
            from urllib.parse import urljoin
            url = urljoin(article_url, html.unescape(match.group(1)))
            if urlsplit(url).scheme == "https":
                return url
    except (requests.RequestException, ValueError):
        pass
    return None


def render_stockwise_company_news(ticker, company, prices):
    """News Hub presentation: existing RSS source and filtering remain unchanged."""
    st.markdown('<div class="sw-panel-title">📰 STOCKWISE News Hub</div>', unsafe_allow_html=True)
    st.caption(f"Tin tức liên quan đến {ticker} từ các nguồn báo chính thống")
    chosen_sources = st.multiselect(
        "Chọn nguồn báo", list(NEWS_FEEDS), default=list(NEWS_FEEDS),
        key="stockwise_news_sources",
    )
    if st.button("↻ Làm mới tin tức", key=f"stockwise_news_refresh_{ticker}", use_container_width=True):
        stockwise_direct_news.clear()
    with st.spinner("Đang kiểm tra bài báo mới từ các tòa soạn..."):
        articles, errors = stockwise_direct_news(ticker, company)
    filtered = [a for a in articles if a["source"] in chosen_sources]
    st.session_state["sw_timeline_news"] = {
        "symbol": ticker, "articles": filtered, "errors": errors,
    }
    if not filtered:
        st.info("Chưa có tin tức phù hợp từ các nguồn đã chọn.")
    for i, article in enumerate(filtered[:5]):
        # Only publisher metadata from the original news function is used.
        # A decorative local image is explicitly not claimed to be an article photo.
        title = html.escape(article["title"])
        url = html.escape(article["url"], quote=True)
        source = html.escape(article["source"])
        date = html.escape(article["date"])
        thumb = stockwise_news_thumbnail(article["url"]) if i < 3 else None
        thumb_html = (
            f'<img class="sw-news-thumb sw-news-photo" src="{html.escape(thumb, quote=True)}" alt="Ảnh bài báo" loading="lazy"/>'
            if thumb else f'<div class="sw-news-thumb sw-news-thumb-{i % 3}">📰</div>'
        )
        st.markdown(
            f'<div class="sw-news-item">'
            f'{thumb_html}'
            f'<div class="sw-news-body"><a href="{url}" target="_blank" rel="noopener noreferrer">{title}</a>'
            f'<div class="sw-news-meta">{source} · {date}</div></div></div>',
            unsafe_allow_html=True,
        )
    if len(filtered) > 5:
        with st.expander(f"Xem thêm {min(len(filtered)-5, 7)} tin"):
            for article in filtered[5:12]:
                st.markdown(f"[{article['title']}]({article['url']})")
                st.caption(f"{article['source']} · {article['date']}")
    if errors:
        st.caption("Nguồn tin tạm thời không khả dụng: " + ", ".join(errors) + ".")


# ============================================================
# STOCKWISE SMART INSIGHTS: risk heatmap & news timeline
# ============================================================
def stockwise_risk_matrix(prices):
    """Historical volatility and drawdown by calendar month; descriptive, not forecast."""
    d = prices[['date', 'close']].copy()
    d['date'] = pd.to_datetime(d['date'], errors='coerce')
    d['close'] = pd.to_numeric(d['close'], errors='coerce')
    d = d.dropna().query('close > 0').sort_values('date').drop_duplicates('date')
    if len(d) < 25:
        return pd.DataFrame(), pd.DataFrame()
    d['return'] = d['close'].pct_change()
    d['year'] = d['date'].dt.year
    d['month'] = d['date'].dt.month
    grouped = d.groupby(['year', 'month'])
    vol = grouped['return'].agg(lambda x: x.std() * np.sqrt(252) * 100 if x.count() >= 5 else np.nan).unstack('month')
    # Monthly maximum drawdown relative to each month's running peak.
    dd = grouped['close'].agg(lambda x: ((x / x.cummax()) - 1).min() * 100 if len(x) >= 5 else np.nan).unstack('month')
    return vol, dd


def render_stockwise_risk_heatmap(prices):
    st.markdown('#### 🌡️ Risk Heatmap · Rủi ro lịch sử theo tháng')
    vol, dd = stockwise_risk_matrix(prices)
    if vol.empty:
        st.info('Cần ít nhất 25 phiên giá hợp lệ để tạo bản đồ rủi ro.')
        return
    metric = st.radio('Thước đo', ['Biến động năm hóa (%)', 'Drawdown nội tháng (%)'],
                      horizontal=True, key='sw_risk_heatmap_metric')
    data = vol if metric.startswith('Biến động') else dd
    data = data.reindex(columns=list(range(1, 13)))
    is_vol = metric.startswith('Biến động')
    # Mức giảm được hiển thị theo độ lớn tuyệt đối để màu đậm = rủi ro lớn hơn.
    plotted = data if is_vol else data.abs()
    finite_values = plotted.to_numpy(dtype=float)
    finite_values = finite_values[np.isfinite(finite_values)]
    if len(finite_values) == 0:
        st.info('Không đủ quan sát hợp lệ để hiển thị thước đo này.')
        return
    fig = go.Figure(go.Heatmap(
        z=plotted.to_numpy(dtype=float),
        x=[f'T{m}' for m in plotted.columns],
        y=[str(y) for y in plotted.index],
        colorscale=[[0, '#FFF0EB'], [0.25, '#FBC7CF'],
                    [0.5, '#F68EBA'], [0.75, '#CF3C9D'], [1, '#650078']],
        zmin=0,
        zmax=max(float(np.nanmax(finite_values)), 0.01),
        hovertemplate=('Năm %{y} · Tháng %{x}<br>Biến động năm hóa: %{z:.2f}%<extra></extra>'
                       if is_vol else
                       'Năm %{y} · Tháng %{x}<br>Mức giảm tối đa trong tháng: %{z:.2f}%<extra></extra>'),
        colorbar=dict(
            title=dict(text='Mức biến động (%)' if is_vol else 'Mức giảm (%)', side='top'),
            thickness=19, len=0.84, x=1.025, xanchor='left',
            tickfont=dict(size=12, color='#315078'),
            outlinewidth=0,
        ),
        xgap=3, ygap=3,
    ))
    fig.update_layout(
        height=max(390, min(660, 155 + 40 * len(data))),
        margin=dict(l=65, r=155, t=35, b=100),
        paper_bgcolor='rgba(0,0,0,0)',
        font=dict(color='#315078', size=13),
        xaxis=dict(title='Tháng trong năm', side='bottom',
                   tickmode='array', tickvals=[f'T{m}' for m in range(1, 13)],
                   ticktext=[f'T{m}' for m in range(1, 13)],
                   tickfont=dict(size=12), tickangle=0,
                   automargin=True, showgrid=False),
        yaxis=dict(title='Năm', type='category', automargin=True,
                   tickfont=dict(size=12), showgrid=False),
    )
    st.plotly_chart(fig, use_container_width=True)
    st.markdown(
        '**🎨 Chú thích màu:** '
        '⬜ **Hồng rất nhạt:** thấp · '
        '🩷 **Hồng:** trung bình · '
        '🟣 **Tím đậm:** cao. '
        'Màu được chuẩn hóa theo giá trị lớn nhất trong dữ liệu đang hiển thị.'
    )
    if not is_vol:
        st.caption('Drawdown được đổi sang độ lớn mức giảm (số dương) để màu đậm luôn tương ứng với mức giảm sâu hơn.')
    st.caption('Biến động = độ lệch chuẩn lợi suất ngày × √252; drawdown = mức giảm sâu nhất so với đỉnh giá trong từng tháng. Chỉ phản ánh dữ liệu lịch sử, không dự báo rủi ro tương lai.')


def render_stockwise_news_timeline(ticker, company, prices):
    st.markdown('#### 🗓️ News Impact Timeline · Tin tức & biến động giá')
    st.caption('Biểu đồ đặt thời điểm đăng tin cạnh giá đóng cửa. Không suy luận quan hệ nhân quả giữa tin và biến động giá.')
    days = st.select_slider('Khoảng thời gian', options=[30, 90, 180, 365], value=90,
                            format_func=lambda n: f'{n} ngày', key='sw_news_timeline_days')
    if st.button('📰 Tải tin cho Timeline', key=f'sw_news_timeline_fetch_{ticker}'):
        with st.spinner('Đang tải tin từ các RSS báo chí...'):
            try:
                articles, errors = stockwise_direct_news(ticker, company)
                st.session_state['sw_timeline_news'] = {'symbol': ticker, 'articles': articles, 'errors': errors}
            except Exception as exc:
                st.warning(f'Không tải được tin: {exc}')
    cached = st.session_state.get('sw_timeline_news', {})
    articles = cached.get('articles', []) if cached.get('symbol') == ticker else []
    d = prices[['date', 'close']].copy()
    d['date'] = pd.to_datetime(d['date'], errors='coerce')
    d['close'] = pd.to_numeric(d['close'], errors='coerce')
    d = d.dropna().sort_values('date')
    if d.empty:
        st.info('Không có giá hợp lệ để vẽ timeline.')
        return
    end = d['date'].max()
    d = d[d['date'] >= end - pd.Timedelta(days=days)]
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=d['date'], y=d['close'], mode='lines', name='Giá đóng cửa',
                             line=dict(color='#d35da7', width=2.5)))
    valid = []
    for a in articles:
        try:
            published = pd.to_datetime(a.get('timestamp'), unit='s', errors='coerce')
            if pd.isna(published):
                published = pd.to_datetime(a.get('date'), errors='coerce', dayfirst=True)
            if pd.isna(published) or not (d['date'].min() <= published <= end):
                continue
            nearest = d.iloc[(d['date'] - published).abs().argmin()]
            valid.append((published, float(nearest['close']), a))
        except (ValueError, TypeError, KeyError):
            continue
    if valid:
        fig.add_trace(go.Scatter(x=[v[0] for v in valid], y=[v[1] for v in valid],
            mode='markers', name='Bài báo', marker=dict(color='#8b6ad6', size=11, symbol='diamond', line=dict(color='white', width=1)),
            customdata=[[str(v[2].get('title', ''))[:110], str(v[2].get('source', ''))] for v in valid],
            hovertemplate='%{x|%d/%m/%Y}<br>%{customdata[0]}<br>Nguồn: %{customdata[1]}<extra></extra>'))
    fig.update_layout(height=360, margin=dict(l=10, r=10, t=20, b=20),
        paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)',
        yaxis_title='Giá đóng cửa (đơn vị dữ liệu gốc)', legend=dict(orientation='h', y=1.15))
    st.plotly_chart(fig, use_container_width=True)
    if valid:
        st.caption(f'{len(valid)} bài báo có ngày đăng nằm trong khoảng giá đang hiển thị:')
        for published, _, a in sorted(valid, key=lambda v: v[0], reverse=True)[:10]:
            st.markdown(f"• {published:%d/%m/%Y} · **[{html.escape(str(a.get('title', 'Tin tức')))}]({a.get('url', '')})** · {html.escape(str(a.get('source', '')))}")
    elif not articles:
        st.info('Nhấn “Tải tin cho Timeline” để hiển thị các mốc bài báo (nếu nguồn RSS có tin phù hợp).')
    else:
        st.info('Chưa có bài báo nào nằm trong giai đoạn giá được chọn.')
    if cached.get('symbol') == ticker and cached.get('errors'):
        st.caption('Một số nguồn RSS không truy cập được: ' + ', '.join(cached['errors']))

# ============================================================
# TAB 1 - OVERVIEW
# ============================================================

with tabs[0]:
    # Presentation-only layout; all numbers below come from existing data variables.
    _hero_photo = BASE_DIR / "assets" / "art" / "card_stock.webp"
    _hero_src = (
        "data:image/webp;base64," + base64.b64encode(_hero_photo.read_bytes()).decode("ascii")
        if _hero_photo.is_file() else ""
    )
    _picture = (
        f'<img src="{_hero_src}" alt="Starry Night" class="sw-company-photo"/>'
        if _hero_src else '<div class="sw-company-photo sw-photo-fallback">✦</div>'
    )
    render_html(f"""
        <div class="sw-company-card">
          {_picture}
          <div class="sw-company-description">
            <div class="sw-company-name">{safe_text(company_name)} <span class="sw-symbol-pill">{safe_text(symbol)}</span></div>
            <div class="sw-company-sub">{'Ngân hàng' if symbol in BANK_SYMBOLS else 'Doanh nghiệp'} · Thị trường chứng khoán Việt Nam</div>
            <div class="sw-company-note">Dữ liệu giao dịch đến {latest_date} · Không phải báo giá thời gian thực</div>
          </div>
          <div class="sw-company-quote">
            <div class="sw-small-label">Giá đóng cửa phiên {latest_date}</div>
            <div class="sw-big-price">{fmt(latest["close"])} <small>VND</small></div>
            <div class="sw-change">{selected_time}: {delta_text}</div>
          </div>
          <div class="sw-session-mini">
            <div><span>Mở cửa</span><b>{fmt(latest["open"])}</b></div>
            <div><span>Cao nhất</span><b>{fmt(latest["high"])}</b></div>
            <div><span>Thấp nhất</span><b>{fmt(latest["low"])}</b></div>
            <div><span>Khối lượng</span><b>{fmt(latest["volume"],0)}</b></div>
          </div>
        </div>
        <div class="sw-five-kpi">
          <div class="sw-kpi"><div class="sw-kpi-icon">◇</div><div><span>Mã cổ phiếu</span><strong>{safe_text(symbol)}</strong></div></div>
          <div class="sw-kpi"><div class="sw-kpi-icon">▤</div><div><span>Số phiên dữ liệu</span><strong>{len(filtered_stock):,}</strong></div></div>
          <div class="sw-kpi"><div class="sw-kpi-icon">◉</div><div><span>Nhóm ngành</span><strong>{'Ngân hàng' if symbol in BANK_SYMBOLS else 'Doanh nghiệp'}</strong></div></div>
          <div class="sw-kpi"><div class="sw-kpi-icon">▦</div><div><span>Giai đoạn dữ liệu</span><strong>{stock['date'].min():%d/%m/%Y} – {stock['date'].max():%d/%m/%Y}</strong></div></div>
          <div class="sw-kpi"><div class="sw-kpi-icon">▥</div><div><span>Giá đóng cửa</span><strong>{fmt(latest["close"])}</strong></div></div>
        </div>
    """)
    chart_col, news_col = st.columns([1.58, 1], gap="medium")
    with chart_col:
        st.markdown('<div class="sw-panel-title">📈 Diễn biến giá cổ phiếu</div>', unsafe_allow_html=True)
        st.caption("Biểu đồ giá và khối lượng giao dịch")
        st.plotly_chart(create_price_chart(filtered_stock), use_container_width=True)
    with news_col:
        render_stockwise_company_news(symbol, company_name, stock)
    with st.expander("News Impact Timeline", expanded=False):
        render_stockwise_news_timeline(symbol, company_name, stock)

# ============================================================
# TAB 2 - TECHNICAL
# ============================================================

with tabs[1]:
    st.markdown(
        f"### 📈 Phân tích kỹ thuật · {symbol}"
    )

    st.caption(
        "Theo dõi xu hướng giá, động lượng "
        "và các chỉ báo kỹ thuật."
    )

    try:
        with st.spinner(
            "Đang tính toán chỉ báo kỹ thuật..."
        ):
            (
                indicators,
                signals,
                summary,
                quality,
            ) = run_technical(stock)

        st.success(
            "Đã hoàn tất phân tích kỹ thuật."
        )

        if isinstance(summary, dict):
            summary_fields = [
                (
                    "Nhận định tổng hợp",
                    summary.get(
                        "Nhận định tổng hợp",
                        "N/A",
                    ),
                    "mint",
                ),
                (
                    "Xu hướng",
                    summary.get(
                        "Xu hướng",
                        "N/A",
                    ),
                    "blue",
                ),
                (
                    "Động lượng",
                    summary.get(
                        "Động lượng",
                        "N/A",
                    ),
                    "purple",
                ),
            ]

            cards_html = []

            for label, raw_value, color in summary_fields:
                value, note = shorten_status(
                    raw_value
                )

                cards_html.append(
                    f"""
                    <div class="analysis-card kpi-{color}">
                        <div class="analysis-label">
                            {safe_text(label)}
                        </div>
                        <div class="analysis-value">
                            {safe_text(value)}
                        </div>
                        <div class="analysis-note">
                            {safe_text(note)}
                        </div>
                    </div>
                    """
                )

            render_html(
                '<div class="analysis-grid">'
                + "".join(cards_html)
                + "</div>"
            )

        section_heading(
            "💗 Các chỉ báo gần nhất"
        )

        if (
            isinstance(indicators, pd.DataFrame)
            and not indicators.empty
        ):
            last_row = indicators.iloc[-1]

            indicator_specs = [
                ("SMA20", "pink"),
                ("SMA50", "blue"),
                ("RSI14", "purple"),
                ("MACD", "mint"),
            ]

            cards_html = []

            for name, color in indicator_specs:
                col = indicator_column(
                    indicators,
                    name,
                )

                value = (
                    last_row[col]
                    if col is not None
                    else None
                )

                cards_html.append(
                    f"""
                    <div class="kpi-card kpi-{color}">
                        <div class="kpi-label">
                            {name}
                        </div>
                        <div class="kpi-value">
                            {fmt(value)}
                        </div>
                        <div class="kpi-note">
                            Chỉ báo phiên gần nhất
                        </div>
                    </div>
                    """
                )

            render_html(
                '<div class="kpi-grid">'
                + "".join(cards_html)
                + "</div>"
            )

            section_heading(
                "📉 Biểu đồ phân tích kỹ thuật"
            )

            st.plotly_chart(
                technical_chart(indicators),
                use_container_width=True,
            )

        section_heading(
            "📝 Diễn giải tín hiệu"
        )

        # Chuyển các tín hiệu từ DataFrame / dict / list thành thẻ trực quan.
        if isinstance(signals, pd.DataFrame):
            signal_rows = signals.to_dict(orient="records")
        elif isinstance(signals, dict):
            signal_rows = [
                {"Chỉ báo": str(key), "Giá trị phiên gần nhất": str(value)}
                for key, value in signals.items()
            ]
        elif isinstance(signals, (list, tuple)):
            signal_rows = [
                row if isinstance(row, dict) else {"Chỉ báo": f"Tín hiệu {i + 1}", "Giải thích": str(row)}
                for i, row in enumerate(signals)
            ]
        else:
            signal_rows = [{"Chỉ báo": "Tín hiệu", "Giải thích": str(signals)}]

        if signal_rows:
            signal_colors = ["pink", "blue", "purple", "mint"]
            signal_cards = []
            for i, row in enumerate(signal_rows):
                indicator_name = row.get("Chỉ báo", row.get("indicator", row.get("name", f"Tín hiệu {i + 1}")))
                signal_status = row.get("Tín hiệu", row.get("signal", row.get("Kết quả", "")))
                latest_value = row.get("Giá trị phiên gần nhất", row.get("Giá trị", row.get("value", "")))
                explanation = row.get("Giải thích", row.get("explanation", ""))
                extra = " · ".join(
                    f"{key}: {value}" for key, value in row.items()
                    if key not in {"Chỉ báo", "indicator", "name", "Tín hiệu", "signal", "Kết quả", "Giá trị phiên gần nhất", "Giá trị", "value", "Giải thích", "explanation"}
                    and value is not None
                )
                details = " | ".join(str(x) for x in (latest_value, explanation, extra) if str(x).strip())
                color = signal_colors[i % len(signal_colors)]
                signal_cards.append(
                    f'<div class="analysis-card kpi-{color}" '
                    'style="border:2px solid rgba(137,115,208,.45);'
                    'box-shadow:0 13px 27px rgba(68,80,150,.20),0 5px 15px rgba(229,106,180,.16)">'
                    f'<div class="analysis-label">{safe_text(indicator_name)}</div>'
                    f'<div class="analysis-value">{safe_text(signal_status or latest_value or "Chi tiết")}</div>'
                    f'<div class="analysis-note">{safe_text(details)}</div>'
                    '</div>'
                )
            render_html('<div class="analysis-grid">' + ''.join(signal_cards) + '</div>')
        else:
            st.info("Chưa có tín hiệu để diễn giải.")

        with st.expander(
            "Xem chất lượng dữ liệu"
        ):
            st.write(quality)

        st.caption(
            "Các chỉ báo dựa trên dữ liệu "
            "lịch sử, không phải khuyến nghị "
            "giao dịch."
        )

    except Exception as exc:
        st.error(
            f"Không thể phân tích kỹ thuật: {exc}"
        )


# ============================================================
# TAB 3 - FINANCIAL
# ============================================================

with tabs[2]:
    st.markdown(
        f"### 🏦 Phân tích tài chính · {symbol}"
    )

    st.caption(
        "Đánh giá khả năng sinh lời, "
        "tăng trưởng và định giá doanh nghiệp."
    )

    a, b, c = st.columns(
        [1.5, 1, 1]
    )

    with a:
        company_label = st.selectbox(
            "Loại doanh nghiệp",
            [
                "Ngân hàng",
                "Doanh nghiệp thông thường",
            ],
            index=(
                0
                if symbol in BANK_SYMBOLS
                else 1
            ),
        )

    company_type = (
        "bank"
        if company_label == "Ngân hàng"
        else "regular"
    )

    with b:
        period_label = st.selectbox(
            "Kỳ báo cáo",
            ["Năm", "Quý"],
        )

    period = (
        "year"
        if period_label == "Năm"
        else "quarter"
    )

    with c:
        st.write("")
        st.write("")

        analyze = st.button(
            "🔍 Phân tích tài chính",
            type="primary",
            use_container_width=True,
        )

    analysis_key = (
        symbol,
        company_type,
        period,
    )

    if analyze:
        try:
            with st.spinner(
                "Đang lấy dữ liệu tài chính..."
            ):
                result = run_financial(
                    symbol,
                    period,
                    company_type,
                )

            st.session_state[
                "financial_result"
            ] = result

            st.session_state[
                "financial_key"
            ] = analysis_key


        except ModuleNotFoundError as exc:
            if exc.name == "vnstock":
                st.error(
                    "Không thể tải báo cáo tài chính vì "
                    "máy chủ chưa cài đặt thư viện VNStock."
                )
                st.info(
                    "Dữ liệu tài chính hiện chưa khả dụng "
                    "trên máy chủ. Vui lòng thử lại sau."
                )
            else:
                st.error(
                    f"Thiếu thư viện cần thiết: {exc.name}"
                )

            st.session_state.pop("financial_result", None)
            st.session_state.pop("financial_key", None)

        except Exception as exc:
            st.error(
                f"Không thể phân tích tài chính mã {symbol}: {exc}"
            )

            st.session_state.pop("financial_result", None)
            st.session_state.pop("financial_key", None)


    result = st.session_state.get(
        "financial_result"
    )

    valid_result = (
        isinstance(result, dict)
        and st.session_state.get(
            "financial_key"
        ) == analysis_key
    )

    if valid_result:
        analysis = result.get(
            "analysis", {}
        )

        comparison = result.get(
            "comparison_data",
            pd.DataFrame(),
        )

        profitability = analysis.get(
            "profitability", {}
        )

        valuation = analysis.get(
            "valuation", {}
        )

        growth = analysis.get(
            "growth", {}
        )

        st.success(
            f"Đã phân tích {symbol} · "
            f"Kỳ mới nhất: "
            f"{analysis.get('latest_period','N/A')}"
        )

        section_heading(
            "💗 Khả năng sinh lời & định giá"
        )

        
        finance_metrics = [
            (
                "ROE",
                financial_percent(
                    profitability.get("roe"),
                    scale=1,
                ),
                "pink",
            ),
            (
                "ROA",
                financial_percent(
                    profitability.get("roa"),
                    scale=1,
                ),
                "blue",
            ),
            (
                "P/E",
                fmt(
                    valuation.get("pe")
                ) + " lần",
                "purple",
            ),
            (
                "P/B",
                fmt(
                    valuation.get("pb")
                ) + " lần",
                "mint",
            ),
        ]


        cards_html = []

        for label, value, color in finance_metrics:
            cards_html.append(
                f"""
                <div class="kpi-card kpi-{color}">
                    <div class="kpi-label">
                        {safe_text(label)}
                    </div>
                    <div class="kpi-value">
                        {safe_text(value)}
                    </div>
                    <div class="kpi-note">
                        Kỳ tài chính gần nhất
                    </div>
                </div>
                """
            )

        render_html(
            '<div class="kpi-grid">'
            + "".join(cards_html)
            + "</div>"
        )

        section_heading(
            "📈 Các chỉ tiêu tăng trưởng"
        )

        if company_type == "bank":
            growth_fields = [
                (
                    "Tăng trưởng tín dụng",
                    "loan_growth",
                ),
                (
                    "Tăng trưởng huy động",
                    "deposit_growth",
                ),
                (
                    "Tăng trưởng lợi nhuận",
                    "profit_growth",
                ),
            ]
        else:
            growth_fields = [
                (
                    "Tăng trưởng doanh thu",
                    "revenue_growth",
                ),
                (
                    "Tăng trưởng lợi nhuận",
                    "profit_growth",
                ),
            ]

        cols = st.columns(
            len(growth_fields)
        )

        for col, (label, key) in zip(
            cols,
            growth_fields,
        ):
            with col:
                value = growth.get(key)

                render_html(
                    f"""
                    <div class="analysis-card kpi-blue">
                        <div class="analysis-label">
                            {safe_text(label)}
                        </div>
                        <div class="analysis-value">
                            {financial_percent(value)}
                        </div>
                        <div class="analysis-note">
                            So với kỳ tham chiếu
                        </div>
                    </div>
                    """
                )

        if company_type == "bank":
            section_heading(
                "🏦 Chỉ tiêu ngân hàng"
            )

            asset_quality = analysis.get(
                "asset_quality", {}
            )

            capital = analysis.get(
                "capital_funding", {}
            )

            bank_metrics = [
                (
                    "NIM",
                    profitability.get("nim"),
                    "pink",
                ),
                (
                    "LDR",
                    capital.get("ldr"),
                    "blue",
                ),
                (
                    "NPL",
                    asset_quality.get("npl"),
                    "purple",
                ),
                (
                    "CAR",
                    capital.get("car"),
                    "mint",
                ),
                (
                    "CASA",
                    capital.get("casa"),
                    "pink",
                ),
            ]

            cards_html = []

            for label, value, color in bank_metrics:
                cards_html.append(
                    f"""
                    <div class="kpi-card kpi-{color}">
                        <div class="kpi-label">
                            {label}
                        </div>
                        <div class="kpi-value">
                            {financial_percent(value)}
                        </div>
                        <div class="kpi-note">
                            Theo dữ liệu hiện có
                        </div>
                    </div>
                    """
                )

            render_html(
                '<div class="kpi-grid">'
                + "".join(cards_html)
                + "</div>"
            )

        section_heading(
            "📊 So sánh chỉ tiêu qua các kỳ"
        )

        if (
            isinstance(comparison, pd.DataFrame)
            and not comparison.empty
        ):
           

            # Clean invalid numeric values before rendering.
            comparison_display = comparison.copy().replace([np.inf, -np.inf], np.nan)
            comparison_display = comparison_display.astype(object).where(
                pd.notna(comparison_display), None
            )
            st.dataframe(comparison_display, use_container_width=True, hide_index=True)

            left, right = st.columns(2)

            with left:
                fig = financial_line_chart(
                    comparison,
                    ["roe", "roa"],
                    "Khả năng sinh lời",
                )

                if fig is not None:
                    st.plotly_chart(
                        fig,
                        use_container_width=True,
                    )

            with right:
                fig = financial_line_chart(
                    comparison,
                    ["pe", "pb"],
                    "Chỉ tiêu định giá",
                )

                if fig is not None:
                    st.plotly_chart(
                        fig,
                        use_container_width=True,
                    )

        section_heading(
            "📝 Nhận định tài chính"
        )

        observations = analysis.get(
            "observations", {}
        )

        left, right = st.columns(2)

        with left:
            st.markdown(
                "#### ✅ Điểm mạnh"
            )

            strengths = observations.get(
                "strengths", []
            )

            if strengths:
                for item in strengths:
                    st.write("•", item)
            else:
                st.info(
                    "Chưa có nhận định điểm mạnh."
                )

        with right:
            st.markdown(
                "#### ⚠️ Điểm cần theo dõi"
            )

            weaknesses = observations.get(
                "weaknesses", []
            )

            if weaknesses:
                for item in weaknesses:
                    st.write("•", item)
            else:
                st.info(
                    "Chưa có nhận định điểm yếu."
                )

        st.markdown(
            "#### Nhận định định giá"
        )

        for item in observations.get(
            "valuation_notes", []
        ):
            st.write("•", item)

        quality = analysis.get(
            "data_quality", {}
        )

        for warning in quality.get(
            "warnings", []
        ):
            st.warning(warning)

        for note in quality.get(
            "notes", []
        ):
            st.info(note)

        with st.expander(
            "Xem báo cáo tài chính chuẩn hóa"
        ):
            financial_data = result.get(
                "financial_data"
            )

            if isinstance(
                financial_data,
                pd.DataFrame,
            ):
                st.dataframe(
                    financial_data,
                    use_container_width=True,
                    hide_index=True,
                )

        st.caption(
            "Nguồn: Vnstock · "
            "Kết quả phụ thuộc dữ liệu "
            "được cung cấp."
        )

    else:
        st.info(
            "Chọn loại doanh nghiệp, "
            "kỳ báo cáo rồi nhấn "
            "'Phân tích tài chính'."
        )


# ============================================================
# TAB 4 - SCORING
# ============================================================

with tabs[3]:
    st.markdown("### 🎯 STOCKWISE | Investment Scoring & Risk")
    with st.expander("🌡️ Risk Heatmap · Bản đồ rủi ro", expanded=True):
        render_stockwise_risk_heatmap(stock)
    try:
        from investment_scoring import score_stock, ScoringError, PROFILE_LABELS
        from risk_analysis import drawdown_series, prepare_prices
    except ImportError as exc:
        st.error(f"Thiếu module phân tích: {exc}. Đặt risk_analysis.py và investment_scoring.py cạnh app.py.")
    else:
        profile_name = st.selectbox("Hồ sơ trọng số", list(PROFILE_LABELS),
                                    format_func=lambda k: PROFILE_LABELS[k], key="tv4_profile")
        load_financial_tv4 = st.checkbox("Tải dữ liệu tài chính để chấm đủ 4 trụ cột (cần kết nối nguồn dữ liệu)",
                                        value=False, key="tv4_financial_optin")
        if st.button("📊 Chấm điểm cổ phiếu", type="primary", key="tv4_run"):
            with st.spinner("Đang tính điểm và kiểm tra dữ liệu..."):
                try:
                    technical_input = None
                    try:
                        technical_input = technical_input_for_scoring(stock)
                    except Exception as exc:
                        st.warning(f"Chưa ghép được tín hiệu TV2: {exc}. Chỉ dùng động lượng giá nếu đủ dữ liệu.")

                    fundamental_input = None
                    if not load_financial_tv4:
                        st.info("Chưa bật tải dữ liệu tài chính. Điểm tổng chỉ dựa trên Kỹ thuật và Rủi ro.")

                    if load_financial_tv4:
                        ctype = "bank" if symbol in __import__("investment_scoring").BANK_TICKERS else "regular"
                        try:
                            fundamental_input = run_financial(symbol, "year", ctype)
                        except Exception as exc:
                            st.warning(f"Không lấy được dữ liệu tài chính: {exc}. Điểm có thể thiếu trụ cột.")

                    # Benchmark không tự động gọi mạng: không có VN-Index thì bỏ Beta, có cảnh báo độ phủ.
                    result_tv4 = score_stock(symbol, price_df=stock, benchmark=None,
                                             fundamentals=fundamental_input, technical=technical_input,
                                             profile=profile_name)
                    st.session_state["tv4_result"] = result_tv4
                    st.session_state["tv4_result_key"] = (symbol, profile_name, load_financial_tv4)
                except (ScoringError, ValueError, KeyError, TypeError) as exc:
                    st.error(f"Không thể chấm điểm: {exc}")
        tv4 = st.session_state.get("tv4_result")
        if tv4 and st.session_state.get("tv4_result_key") == (symbol, profile_name, load_financial_tv4):
            import html as _sw_html
            st.markdown('''
            <style>
            .sw4-card{background:linear-gradient(145deg,#fffafd 0%,#f5f0ff 52%,#eaf4ff 100%);
              border:1.5px solid #e9c7f1;border-radius:23px;padding:22px 23px;
              box-shadow:0 10px 25px rgba(167,94,173,.15),0 3px 9px rgba(81,118,186,.08);
              transition:transform .2s,box-shadow .2s;min-height:155px}
            .sw4-card:hover{transform:translateY(-2px);box-shadow:0 14px 30px rgba(167,94,173,.21)}
            .sw4-main{background:linear-gradient(120deg,#ffe3f3 0%,#f4e6ff 55%,#dceeff 100%);
              border:2px solid #e9a6ec;min-height:210px}
            .sw4-top{font-size:13px;font-weight:850;color:#31507a;letter-spacing:.2px}
            .sw4-score{font-size:clamp(43px,5vw,63px);font-weight:900;color:#d1359d;line-height:1.2;margin:14px 0}
            .sw4-score small{font-size:22px;color:#29466f}
            .sw4-value{font-size:clamp(22px,2.6vw,32px);font-weight:900;color:#1d3761;margin:17px 0 9px}
            .sw4-muted{font-size:12px;color:#667ca0;line-height:1.55}
            .sw4-tag{display:inline-block;background:#ffe6f4;border:1px solid #f5bfe0;
              border-radius:100px;padding:7px 13px;color:#9c3882;font-weight:800;font-size:13px}
            .sw4-bar{height:12px;background:#f0e8fa;border:1px solid #e5d7f5;border-radius:20px;overflow:hidden;margin:16px 0 5px}
            .sw4-fill{height:100%;border-radius:20px;background:linear-gradient(90deg,#ff85c0,#d05bd0,#9d89ed)}
            .sw4-pillars{display:grid;grid-template-columns:repeat(4,minmax(0,1fr));gap:13px;margin:15px 0 22px}
            .sw4-pillar{border-radius:19px;padding:17px 15px;border:1.5px solid var(--edge);
              background:linear-gradient(140deg,var(--bg),#ffffff);box-shadow:0 7px 17px rgba(97,85,150,.12)}
            .sw4-pillar-name{font-size:14px;font-weight:850;color:#27436e}
            .sw4-pillar-score{font-size:27px;font-weight:900;color:var(--ink);margin:9px 0}
            .sw4-pillar-score small{font-size:13px;font-weight:600;color:#7387a7}
            .sw4-pillar .sw4-bar{height:9px;margin:10px 0}
            .sw4-pillar .sw4-fill{background:var(--ink)}
            .sw4-section{font-size:21px;font-weight:900;color:#1d3761;margin:23px 0 13px}
            .sw4-summary{background:linear-gradient(120deg,#fff8fd,#f4f1ff,#edf6ff);
              border:1.5px solid #e7c8f0;border-radius:22px;padding:22px 24px;
              box-shadow:0 8px 20px rgba(124,99,171,.12);line-height:1.85;color:#344e73}
            div[data-testid="stPlotlyChart"]{border:1.5px solid #e7d0f5;border-radius:20px;
              background:linear-gradient(130deg,#fffafd,#f4f6ff);padding:9px;
              box-shadow:0 8px 20px rgba(131,101,173,.11)}
            @media(max-width:750px){.sw4-pillars{grid-template-columns:repeat(2,minmax(0,1fr))}}
            </style>''',unsafe_allow_html=True)
            _score=float(tv4["total_score"])
            _label=_sw_html.escape(str(tv4["label"]))
            _confidence=_sw_html.escape(str(tv4["confidence"]))
            _asof=_sw_html.escape(str(tv4.get("as_of") or "N/A"))
            _profile=_sw_html.escape(str(PROFILE_LABELS.get(profile_name,profile_name)))
            _maincol,_classcol,_trustcol,_weightcol=st.columns([1.75,1,1,1],gap="medium")
            with _maincol:
                st.markdown(f'''<div class="sw4-card sw4-main"><div class="sw4-top">🏆 ĐIỂM TỔNG HỢP · {_sw_html.escape(symbol)}</div>
                  <div class="sw4-score">{_score:.1f}<small> / 100</small></div>
                  <div class="sw4-bar"><div class="sw4-fill" style="width:{max(0,min(100,_score)):.1f}%"></div></div>
                  <div class="sw4-muted">Đánh giá tổng hợp dựa trên dữ liệu hiện có</div></div>''',unsafe_allow_html=True)
           
            with _classcol:
                st.markdown(f'''<div class="sw4-card"><div class="sw4-top">💗 PHÂN LOẠI</div>
                  <div class="sw4-value">{_label}</div></div>''', unsafe_allow_html=True)
            with _trustcol:
                st.markdown(f'''<div class="sw4-card"><div class="sw4-top">🛡️ ĐỘ TIN CẬY</div>
                  <div class="sw4-value">{_confidence}</div><div class="sw4-muted">Dữ liệu đến {_asof}</div></div>''', unsafe_allow_html=True)
            with _weightcol:

                st.markdown(f'''<div class="sw4-card"><div class="sw4-top">⚙️ HỒ SƠ TRỌNG SỐ</div>
                  <div class="sw4-value">{_profile}</div><div class="sw4-muted">Có thể đổi ở phía trên</div></div>''',unsafe_allow_html=True)
            st.markdown('<div class="sw4-section">💎 Điểm 4 trụ cột</div>',unsafe_allow_html=True)
            _keys=("technical","fundamental","valuation","risk")
            _names={"technical":"Kỹ thuật","fundamental":"Tài chính","valuation":"Định giá","risk":"Rủi ro"}
            _palette={"technical":("#fff0f8","#f4b8dc","#d83d99"),
                      "fundamental":("#edf4ff","#bdd6ff","#438bf0"),
                      "valuation":("#f4edff","#d8bbff","#9561e2"),
                      "risk":("#eafaf5","#a9e7d0","#2dba91")}
            _icons={"technical":"📈","fundamental":"🏦","valuation":"💎","risk":"🛡️"}
            _cards=[]
            for _k in _keys:
                _p=tv4["pillars"][_k]
                _v=_p.get("score")
                _bg,_edge,_ink=_palette[_k]
                _num=f"{_v:.1f}" if _v is not None else "N/A"
                _width=max(0,min(100,float(_v))) if _v is not None else 0
                _cards.append(f'''<div class="sw4-pillar" style="--bg:{_bg};--edge:{_edge};--ink:{_ink}">
                  <div class="sw4-pillar-name">{_icons[_k]} {_names[_k]}</div>
                  <div class="sw4-pillar-score">{_num}<small> /100</small></div>
                  <div class="sw4-bar"><div class="sw4-fill" style="width:{_width:.1f}%"></div></div>
                  <div class="sw4-muted">Trọng số {_p.get('weight_used',0):.0%} · Độ phủ {_p.get('coverage',0):.0%}</div></div>''')
            st.markdown('<div class="sw4-pillars">'+''.join(_cards)+'</div>',unsafe_allow_html=True)
            st.markdown('<div class="sw4-section">📊 So sánh điểm các trụ cột</div>',unsafe_allow_html=True)
            _vals=[tv4["pillars"][k].get("score") for k in _keys]
            _fig=go.Figure(go.Bar(x=[_names[k] for k in _keys],
                y=[v if v is not None else 0 for v in _vals],
                text=[f"{v:.1f}" if v is not None else "N/A" for v in _vals],
                textposition="outside",marker_color=[_palette[k][2] for k in _keys],
                marker_line=dict(color="#ffffff",width=1.2)))
            _fig.update_layout(height=325,margin=dict(l=20,r=20,t=25,b=20),
                yaxis=dict(range=[0,110],gridcolor="#eae4f5",title="Điểm (0–100)"),
                xaxis=dict(title=None),font=dict(color="#29466f"),
                paper_bgcolor="rgba(0,0,0,0)",plot_bgcolor="rgba(0,0,0,0)",showlegend=False)
            st.plotly_chart(_fig,use_container_width=True)
            st.markdown('<div class="sw4-section">💌 Nhận xét tổng quan</div>',unsafe_allow_html=True)
            st.markdown('<div class="sw4-summary">'+_sw_html.escape(tv4["summary"])+
                        '</div>',unsafe_allow_html=True)
            with st.expander("📋 Bảng trọng số & độ phủ dữ liệu",expanded=False):
                st.dataframe(tv4["pillar_table"],use_container_width=True,hide_index=True)
            with st.expander("🧮 Chi tiết từng chỉ số và đóng góp",expanded=False):
                st.dataframe(tv4["metric_table"],use_container_width=True,hide_index=True)
            with st.expander("📉 Biểu đồ drawdown và rủi ro", expanded=False):
                try:
                    price_clean = prepare_prices(stock)
                    dd = drawdown_series(price_clean["close"].tail(756)) * 100
                    fig_dd = go.Figure(go.Scatter(x=dd.index, y=dd.values, fill="tozeroy",
                                                  line=dict(color="#d66fa9"), name="Drawdown"))
                    fig_dd.update_layout(yaxis_title="Drawdown (%)", height=300,
                                         paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)")
                    st.plotly_chart(fig_dd, use_container_width=True)
                except Exception as exc:
                    st.warning(f"Không vẽ được drawdown: {exc}")
                st.dataframe(__import__("risk_analysis").risk_table(tv4["risk"]),
                             use_container_width=True, hide_index=True)
            with st.expander("🔎 Giải thích, cảnh báo và phương pháp"):
                st.write(tv4["methodology"])
                for message in tv4["warnings"]:
                    st.warning(message)
                for message in tv4["notes"]:
                    st.caption(message)
                st.caption(tv4["disclaimer"])
            st.download_button("⬇️ Tải bảng chấm điểm CSV",
                               data=tv4["metric_table"].to_csv(index=False).encode("utf-8-sig"),
                               file_name=f"{symbol}_investment_scoring.csv", mime="text/csv")
        else:
            st.info("Chọn hồ sơ trọng số và nhấn “Chấm điểm cổ phiếu” để xem kết quả.")


# ============================================================
# TAB 5 - DATA
# ============================================================

with tabs[4]:
    st.markdown(
        f"### 📁 Dữ liệu lịch sử · {symbol}"
    )


    st.dataframe(
        stock.sort_values(
            "date",
            ascending=False,
        ),
        use_container_width=True,
        hide_index=True,
    )

    csv_bytes = stock.to_csv(
        index=False
    ).encode("utf-8-sig")

    st.download_button(
        "⬇️ Tải dữ liệu CSV",
        data=csv_bytes,
        file_name=f"{symbol}_prices.csv",
        mime="text/csv",
    )


# ============================================================
# 14. PDF REPORT
# ============================================================

def create_pdf_report(symbol, stock, selected_time, change_pct,
                      include_overview=True, include_technical=True,
                      include_financial=True, include_scoring=True, report_title=None,
                      fetch_financial=False, compute_scoring=False,
                      include_heatmap=True, include_news=True):
    from stockwise_pdf_starry import build_starry_report as build_report
    financial = st.session_state.get("financial_result")
    fin_key = st.session_state.get("financial_key")
    if not (isinstance(financial, dict) and isinstance(fin_key, tuple) and fin_key[0] == symbol):
        financial = None
    if include_financial and financial is None and fetch_financial:
        company_type = "bank" if symbol in BANK_SYMBOLS else "regular"
        try:
            financial = run_financial(symbol, "year", company_type)
        except (ImportError, ModuleNotFoundError) as exc:
            # Không chặn toàn bộ báo cáo nếu thư viện tài chính chưa được cài.
            financial = None
            st.warning(f"Không thể tải dữ liệu tài chính ({exc}). PDF vẫn xuất các phần có dữ liệu.")
        except Exception as exc:
            financial = None
            st.warning(f"Nguồn dữ liệu tài chính không khả dụng ({exc}). PDF vẫn xuất các phần có dữ liệu.")
        if financial is not None:
            st.session_state["financial_result"] = financial
            st.session_state["financial_key"] = (symbol, company_type, "year")
    scoring = st.session_state.get("tv4_result")
    if not (isinstance(scoring, dict) and scoring.get("symbol") == symbol):
        scoring = None
    if include_scoring and scoring is None and compute_scoring:
        from investment_scoring import score_stock
        try:
            technical_input = technical_input_for_scoring(stock)
        except Exception as exc:
            technical_input = None
            st.warning(f"Không lấy được tín hiệu TV2 cho chấm điểm PDF ({exc}).")
        try:
            scoring = score_stock(symbol, price_df=stock, benchmark=None,
                                  fundamentals=financial, technical=technical_input,
                                  profile="balanced")
        except Exception as exc:
            scoring = None
            st.warning(f"Chưa thể tự chấm điểm ({exc}). PDF vẫn xuất các phần có dữ liệu.")
    technical = None
    if include_technical:
        try:
            technical = run_technical(stock)
        except Exception:
            technical = None
    # Source is selected dynamically for each ticker (local CSV or uploaded CSV).
    price_source_for_pdf = source if isinstance(source, str) and source.strip() else None
    return build_report(symbol, stock, selected_time, change_pct,
                        financial=financial, scoring=scoring, technical=technical,
                        include_overview=include_overview, include_technical=include_technical,
                        include_financial=include_financial, include_scoring=include_scoring,
                        report_title=company_display_name(symbol),
                        price_source=price_source_for_pdf,
                        risk_heatmap=stockwise_risk_matrix(stock) if include_heatmap else None,
                        news_articles=(st.session_state.get("sw_timeline_news", {}).get("articles", [])
                                       if st.session_state.get("sw_timeline_news", {}).get("symbol") == symbol else []) if include_news else None)


# ============================================================
# TAB 6 - PDF EXPORT
# ============================================================

with tabs[5]:
    # STOCKWISE_BANNER_REAL_IMAGE_V5: only PDF hero changed; PDF functions untouched.
    import base64 as _sw_art_base64
    from pathlib import Path as _sw_art_Path
    _sw_art_file = _sw_art_Path(__file__).resolve().parent / "assets" / "stockwise_starry_night.png"
    _sw_art_uri = _sw_art_base64.b64encode(_sw_art_file.read_bytes()).decode("ascii")
    st.markdown(('    <style>\n    /* White canvas and blue, painterly Starry Night accents. No global app restyling. */\n    .sw-report-hero {\n      position:relative; overflow:hidden; isolation:isolate;\n      background:\n        radial-gradient(ellipse at 77% 27%,#ffdf87 0 3%,transparent 3.3%),\n        radial-gradient(ellipse at 80% 28%,transparent 0 8%,#72b9e2 8.5% 9.5%,transparent 10%),\n        radial-gradient(ellipse at 38% 65%,transparent 0 18%,#3679b9 19% 22%,transparent 23%),\n        repeating-radial-gradient(ellipse at 88% 40%,transparent 0 19px,#3b78ba70 22px 25px,transparent 29px 49px),\n        linear-gradient(125deg,#071d50 0%,#123b83 52%,#0b245a 100%);\n      border:1px solid #c3d8ef; border-radius:22px;\n      padding:36px 38px; margin:12px 0 25px;\n      box-shadow:0 14px 34px #09275b20;\n    }\n    .sw-report-hero:after {content:\'✦  ·  ✧  ✦\';position:absolute;right:5%;top:12%;\n      color:#ffe2a0;font-size:29px;letter-spacing:18px;opacity:.85;pointer-events:none}\n    .sw-report-eyebrow {color:#ffe2a0!important;font-size:12px;font-weight:800;letter-spacing:2px}\n    .sw-report-heading {color:#fff!important;font-family:Georgia,serif;\n      font-size:clamp(25px,3vw,38px);font-weight:800;line-height:1.28;\n      margin:15px 0 10px;text-shadow:0 2px 8px #061b4a}\n    .sw-report-subtitle {color:#dcecff!important;font-size:14px;letter-spacing:.3px}\n    .sw-report-label {color:#103a77!important;font-size:20px;font-weight:800;\n      margin:24px 0 13px;padding-bottom:9px;border-bottom:1px solid #e4edf7}\n    /* All selectors below target ONLY widgets whose keys belong to the PDF tab. */\n    [class*=\'st-key-sw_pdf_title_\'] input {\n      background:#fff!important;border:1.5px solid #b7d2f0!important;\n      border-radius:12px!important;min-height:46px!important;color:#153b72!important;\n    }\n    .st-key-sw_pdf_overview,.st-key-sw_pdf_technical,.st-key-sw_pdf_financial,\n    .st-key-sw_pdf_scoring,.st-key-sw_pdf_heatmap,.st-key-sw_pdf_news,\n    .st-key-sw_pdf_fetch_financial,.st-key-sw_pdf_compute_scoring {\n      background:#fff!important;border:1px solid #c8dcf1!important;\n      border-radius:13px!important;padding:13px 14px!important;\n      margin:5px 0 9px!important;min-height:68px;\n      box-shadow:0 4px 15px #163c7510!important;\n      transition:border-color .18s,box-shadow .18s;\n    }\n    .st-key-sw_pdf_overview:hover,.st-key-sw_pdf_technical:hover,\n    .st-key-sw_pdf_financial:hover,.st-key-sw_pdf_scoring:hover,\n    .st-key-sw_pdf_heatmap:hover,.st-key-sw_pdf_news:hover,\n    .st-key-sw_pdf_fetch_financial:hover,.st-key-sw_pdf_compute_scoring:hover {\n      border-color:#438bd2!important;box-shadow:0 5px 18px #2467ac22!important;\n    }\n    .st-key-sw_generate_pdf button {\n      background:linear-gradient(105deg,#0b2b69,#13529d,#236db8)!important;\n      border:1px solid #cba958!important;border-radius:14px!important;\n      min-height:62px!important;color:white!important;\n      box-shadow:0 9px 24px #123b7b33!important;\n    }\n    .st-key-sw_generate_pdf button * {color:white!important;font-size:19px!important;font-weight:800!important}\n    .sw-report-preview-title {color:#103a77;font-size:21px;font-weight:800;\n      padding:15px 0 10px;border-bottom:1px solid #e4edf7;margin-top:20px}\n    </style>\n    <style>\n    /* STOCKWISE_BANNER_REAL_IMAGE_V5: real PNG is a child <img>, not CSS background. */\n    .sw-report-hero {min-height:255px!important;border:1px solid #d8bc70!important;\n       background:#09245b!important;display:flex;flex-direction:column;\n       justify-content:center;padding:35px 38px!important}\n    .sw-report-hero:before,.sw-report-hero:after {display:none!important}\n    .sw-report-hero .sw-art-photo {position:absolute;inset:0;width:100%;height:100%;\n       object-fit:cover;object-position:center 42%;z-index:0;pointer-events:none}\n    .sw-report-hero .sw-art-shade {position:absolute;inset:0;z-index:1;\n       background:linear-gradient(90deg,rgba(3,18,50,.90),rgba(5,24,59,.73) 46%,rgba(3,22,54,.14));\n       pointer-events:none}\n    .sw-report-hero .sw-report-eyebrow,.sw-report-hero .sw-report-heading,\n    .sw-report-hero .sw-report-subtitle {position:relative;z-index:2}\n    @media(max-width:700px){.sw-report-hero{min-height:210px!important;padding:25px!important}}\n    </style>\n    <div class="sw-report-hero">\n      <img class="sw-art-photo" src="data:image/png;base64,__STAR_IMAGE__" alt="Starry Night" />\n      <div class="sw-art-shade"></div>\n      <div class="sw-report-eyebrow">✦ STOCKWISE / REPORT STUDIO</div>\n      <div class="sw-report-heading">Báo cáo cổ phiếu của bạn.<br>Sẵn sàng để trình bày.</div>\n      <div class="sw-report-subtitle">Phân tích chuyên sâu · Trực quan · Dễ chia sẻ</div>\n    </div>\n    <div class="sw-report-label">✍️ Thiết lập báo cáo</div>\n').replace("__STAR_IMAGE__", _sw_art_uri), unsafe_allow_html=True)
    # STOCKWISE_PDF_FORM_FIX_V5: UI only, preserve original banner and PDF functions.
    from pathlib import Path as _sw5_Path
    _sw5_root = _sw5_Path(__file__).resolve().parent
    with st.expander("🖼️ Kiểm tra đường dẫn ảnh (mở nếu ảnh chưa hiển thị)", expanded=False):
        st.caption(f"Thư mục dự án đang chạy: {_sw5_root}")
        for _sw5_label, _sw5_file in (("Banner", "stockwise_starry_night.png"), ("Sunflower Sky", "stockwise_sunflower_sky.png")):
            _sw5_path = _sw5_root / "assets" / _sw5_file
            if _sw5_path.is_file():
                st.success(f"{_sw5_label}: {_sw5_path}")
            else:
                st.error(f"Không tìm thấy {_sw5_label}: {_sw5_path}")
    st.markdown("""
    <style>
    /* PDF form only. Never change hero/banner. */
    [class*="st-key-sw_pdf_title_"] input {
        background:#ffffff!important;color:#123e77!important;
        border:1px solid #b7cde7!important;border-radius:10px!important;
        min-height:45px!important;
    }
    .st-key-sw_pdf_overview,.st-key-sw_pdf_technical,.st-key-sw_pdf_financial,
    .st-key-sw_pdf_scoring,.st-key-sw_pdf_heatmap,.st-key-sw_pdf_news,
    .st-key-sw_pdf_fetch_financial,.st-key-sw_pdf_compute_scoring {
        box-sizing:border-box!important;width:100%!important;min-height:78px!important;
        display:flex!important;align-items:center!important;
        background:#fff!important;background-image:none!important;
        border:1px solid #c2d7ed!important;border-radius:12px!important;
        padding:12px 14px!important;margin:0 0 12px!important;
        box-shadow:0 3px 12px rgba(18,61,109,.06)!important;
    }
    .st-key-sw_pdf_overview label,.st-key-sw_pdf_technical label,
    .st-key-sw_pdf_financial label,.st-key-sw_pdf_scoring label,
    .st-key-sw_pdf_heatmap label,.st-key-sw_pdf_news label,
    .st-key-sw_pdf_fetch_financial label,.st-key-sw_pdf_compute_scoring label {
        width:100%!important;align-items:center!important;
    }
    .st-key-sw_pdf_overview:hover,.st-key-sw_pdf_technical:hover,
    .st-key-sw_pdf_financial:hover,.st-key-sw_pdf_scoring:hover,
    .st-key-sw_pdf_heatmap:hover,.st-key-sw_pdf_news:hover,
    .st-key-sw_pdf_fetch_financial:hover,.st-key-sw_pdf_compute_scoring:hover {
        border-color:#3b82c5!important;box-shadow:0 5px 18px rgba(40,105,165,.13)!important;
    }
    </style>
    """, unsafe_allow_html=True)
    pdf_title = st.text_input(
        "Tiêu đề báo cáo", value=f"Báo cáo phân tích cổ phiếu {symbol}",
        key=f"sw_pdf_title_{symbol}",
    )
    st.markdown('<div class="sw-report-label">📑 Nội dung cần xuất</div>', unsafe_allow_html=True)
    a, b, c = st.columns(3)
    with a:
        pdf_overview = st.checkbox("Tổng quan cổ phiếu", value=True, key="sw_pdf_overview")
        pdf_scoring = st.checkbox("🎯 Chấm điểm & rủi ro", value=True, key="sw_pdf_scoring")
        pdf_fetch_financial = st.checkbox("Tự tải tài chính nếu chưa có", value=True, key="sw_pdf_fetch_financial")
    with b:
        pdf_technical = st.checkbox("Phân tích kỹ thuật", value=True, key="sw_pdf_technical")
        pdf_heatmap = st.checkbox("🌡️ Risk Heatmap", value=True, key="sw_pdf_heatmap")
        pdf_compute_scoring = st.checkbox("Tự tính điểm nếu chưa có", value=True, key="sw_pdf_compute_scoring")
    with c:
        pdf_financial = st.checkbox("Phân tích tài chính", value=True, key="sw_pdf_financial")
        pdf_news = st.checkbox("🗓️ News Timeline", value=True, key="sw_pdf_news")
    if st.button("✨ Tạo báo cáo", type="primary", use_container_width=True, key="sw_generate_pdf"):
        if not any([pdf_overview, pdf_technical, pdf_financial, pdf_scoring, pdf_heatmap, pdf_news]):
            st.warning("Hãy chọn ít nhất một nội dung để xuất báo cáo.")
        else:
            try:
                pdf = create_pdf_report(
                    symbol, stock, selected_time, change_pct,
                    include_overview=pdf_overview,
                    include_technical=pdf_technical,
                    include_financial=pdf_financial,
                    include_scoring=pdf_scoring,
                    fetch_financial=pdf_fetch_financial,
                    compute_scoring=pdf_compute_scoring,
                    include_heatmap=pdf_heatmap, include_news=pdf_news,
                    report_title=pdf_title,
                )
                st.session_state["pdf_data"] = pdf
                st.session_state["pdf_symbol"] = symbol
                st.session_state["pdf_filename"] = (
                    f"STOCKWISE_{symbol}_{datetime.now():%Y%m%d_%H%M}.pdf"
                )
                st.success("Đã tạo báo cáo PDF thành công!")
            except Exception as exc:
                st.error(f"Không thể tạo PDF: {exc}")

    if (st.session_state.get("pdf_data") is not None
            and st.session_state.get("pdf_symbol") == symbol):
        st.download_button(
            "⬇️ TẢI BÁO CÁO PDF", data=st.session_state["pdf_data"],
            file_name=st.session_state["pdf_filename"],
            mime="application/pdf", use_container_width=True,
        )
        # Reliable server-side PDF preview. Avoid browser-blocked data: PDF iframe.
        # Render actual PDF pages with PyMuPDF, not a dummy empty iframe.
        st.markdown('<div class="sw-report-preview-title">👁️ Xem trước báo cáo PDF</div>', unsafe_allow_html=True)
        try:
            import fitz as _sw_fitz
            _sw_doc = _sw_fitz.open(stream=st.session_state["pdf_data"], filetype="pdf")
            _sw_count = len(_sw_doc)
            _sw_page = st.number_input(
                "Trang xem trước", min_value=1, max_value=_sw_count,
                value=1, step=1, key="sw_pdf_preview_page",
            )
            _sw_pix = _sw_doc[int(_sw_page)-1].get_pixmap(matrix=_sw_fitz.Matrix(1.65, 1.65), alpha=False)
            st.image(_sw_pix.tobytes("png"), caption=f"Trang {_sw_page}/{_sw_count}", use_container_width=True)
            _sw_doc.close()
        except Exception as _sw_preview_exc:
            st.warning(f"Không tạo được ảnh xem trước PDF: {_sw_preview_exc}")
            st.caption("Bạn vẫn có thể tải bản PDF bằng nút phía trên.")





# ============================================================
# TAB 7 - PEER COMPARISON V1
# ============================================================

def peer_available_symbols():
    """Use only symbols backed by local price CSV files."""
    paths = []
    for folder in (PRICE_DIR, BASE_DIR / "data", BASE_DIR):
        if folder.is_dir():
            paths.extend(folder.glob("*.csv"))
    return sorted({p.stem.upper() for p in paths
                   if re.fullmatch(r"[A-Z0-9]{2,10}", p.stem.upper())
                  and p.stem.lower() != "symbols"})


def peer_price_metrics(prices, start, end):
    """Align daily close prices by common trading dates, not calendar endpoints."""
    series = []
    for ticker, frame in prices.items():
        data = frame.loc[(frame["date"] >= start) & (frame["date"] <= end),
                         ["date", "close"]].dropna().copy()
        data = data.drop_duplicates("date", keep="last").set_index("date")["close"]
        data.name = ticker
        series.append(data)
    common = pd.concat(series, axis=1, join="inner").sort_index().dropna()
    common = common.loc[(common > 0).all(axis=1)]
    if len(common) < 2:
        return pd.DataFrame(), common
    returns = (common.iloc[-1] / common.iloc[0] - 1) * 100
    result = pd.DataFrame({"Mã": returns.index, "Hiệu suất giá (%)": returns.values})
    result["Giá đầu kỳ"] = [float(common[x].iloc[0]) for x in result["Mã"]]
    result["Giá cuối kỳ"] = [float(common[x].iloc[-1]) for x in result["Mã"]]
    return result, common


def peer_financial_metrics(ticker, period):
    """Reuse existing financial analysis; do not synthesize missing values."""
    kind = "bank" if ticker in BANK_SYMBOLS else "regular"
    output = run_financial(ticker, period, kind)
    analysis = output.get("analysis", {}) if isinstance(output, dict) else {}
    profit = analysis.get("profitability", {}) or {}
    value = analysis.get("valuation", {}) or {}
    growth = analysis.get("growth", {}) or {}
    return {
        "Mã": ticker,
        "Loại": "Ngân hàng" if kind == "bank" else "Doanh nghiệp",
        "Kỳ báo cáo": str(analysis.get("latest_period") or "N/A"),
        "ROE (%)": _peer_pct(profit.get("roe")),
        "ROA (%)": _peer_pct(profit.get("roa")),
        "P/E (lần)": safe_float(value.get("pe")),
        "P/B (lần)": safe_float(value.get("pb")),
        "Tăng trưởng lợi nhuận (%)": _peer_pct(growth.get("profit_growth")),
        "Tăng trưởng doanh thu/tín dụng (%)": _peer_pct(
            growth.get("loan_growth") if kind == "bank" else growth.get("revenue_growth")
        ),
    }


def _peer_pct(value):
    number = safe_float(value)
    return number * 100 if number is not None else None


with tabs[6]:
    st.markdown("### 🔍 STOCKWISE | Peer Comparison")
    options = peer_available_symbols()
    default_symbols = [x for x in (symbol, "FPT", "HPG") if x in options]
    default_symbols = list(dict.fromkeys(default_symbols))[:2]
    chosen = st.multiselect(
        "Chọn từ 2 đến 5 mã cổ phiếu", options=options,
        default=default_symbols, max_selections=5, key="peer_symbols",
    )
    period_choice = st.selectbox("Khoảng so sánh giá", ["1M", "3M", "6M", "1Y", "3Y", "ALL"],
                                 index=2, key="peer_range")
    financial_on = st.checkbox("Bổ sung chỉ tiêu tài chính (có thể cần tải dữ liệu từ Vnstock)",
                               value=False, key="peer_financial_on")
    financial_period = st.selectbox("Kỳ báo cáo tài chính", ["Năm", "Quý"],
                                    disabled=not financial_on, key="peer_financial_period")
    if len(chosen) < 2:
        st.info("Hãy chọn ít nhất 2 mã cổ phiếu để bắt đầu.")
    elif st.button("🔍 So sánh ngay", type="primary", key="peer_run"):
        with st.spinner("Đang đối chiếu dữ liệu..."):
            frames, missing = {}, []
            for ticker in chosen:
                try:
                    frame, _ = load_prices(ticker)
                    if frame.empty:
                        missing.append(ticker)
                    else:
                        frames[ticker] = frame
                except Exception as exc:
                    missing.append(f"{ticker} ({exc})")
            if missing:
                st.warning("Không đọc được dữ liệu giá: " + ", ".join(missing))
            if len(frames) >= 2:
                end = min(frame["date"].max() for frame in frames.values())
                days = TIME_OPTIONS[period_choice]
                start = max(frame["date"].min() for frame in frames.values())
                if days is not None:
                    start = max(start, end - pd.Timedelta(days=days))
                metrics, common = peer_price_metrics(frames, start, end)
                if metrics.empty:
                    st.warning("Không có ít nhất 2 phiên giao dịch chung trong khoảng đã chọn.")
                else:
                    st.caption(f"Các phiên chung: {len(common):,} · "
                               f"Từ {common.index.min():%d/%m/%Y} đến {common.index.max():%d/%m/%Y}")
                    st.dataframe(metrics.round(2), use_container_width=True, hide_index=True)
                    fig = go.Figure()
                    for ticker in common.columns:
                        normalized = common[ticker] / common[ticker].iloc[0] * 100
                        fig.add_trace(go.Scatter(x=common.index, y=normalized,
                                                 mode="lines", name=ticker))
                    fig.update_layout(title="Diễn biến giá chuẩn hóa (đầu kỳ = 100)",
                                      yaxis_title="Chỉ số giá", xaxis_title="Ngày")
                    st.plotly_chart(style_plot(fig, 430), use_container_width=True)
                    st.download_button("⬇️ Tải bảng so sánh giá CSV",
                                       metrics.to_csv(index=False).encode("utf-8-sig"),
                                       file_name="STOCKWISE_peer_prices.csv", mime="text/csv")
            if financial_on:
                st.markdown("#### 📑 Chỉ tiêu tài chính")
                st.caption("Chỉ tiêu theo dữ liệu và kỳ gần nhất từng mã; cần kiểm tra tính đồng nhất trước khi diễn giải.")
                rows = []
                for ticker in chosen:
                    try:
                        rows.append(peer_financial_metrics(
                            ticker, "year" if financial_period == "Năm" else "quarter"
                        ))
                    except Exception as exc:
                        st.warning(f"Không tải được tài chính {ticker}: {exc}")
                if rows:
                    fin = pd.DataFrame(rows)
                    periods = set(fin["Kỳ báo cáo"].dropna()) - {"N/A"}
                    kinds = set(fin["Loại"])
                    if len(periods) > 1:
                        st.warning("Các mã không cùng kỳ báo cáo; không nên so sánh trực tiếp.")
                    if len(kinds) > 1:
                        st.warning("Đang so sánh ngân hàng với doanh nghiệp thường; cơ cấu tài chính khác nhau.")
                    st.dataframe(fin.astype(object).where(pd.notna(fin), None),
                                 use_container_width=True, hide_index=True)
                    st.download_button("⬇️ Tải bảng tài chính CSV",
                                       fin.to_csv(index=False).encode("utf-8-sig"),
                                       file_name="STOCKWISE_peer_financials.csv", mime="text/csv")


# ============================================================
# 15. FOOTER
# ============================================================

st.divider()

render_html(
    """
    <div class="footer">
        ☁️ STOCKWISE · Financial Analytics Platform
        <div style="margin-top:6px;">
            Kiến thức hôm nay – Giá trị ngày mai ♡
        </div>
    </div>
    """
)


# Final presentation-only stylesheet: loaded after all seven tab bodies and legacy inline styles.
_sw_full_tabs_css = BASE_DIR / "stockwise_all_tabs.css"
if _sw_full_tabs_css.is_file():
    st.markdown("<style>" + _sw_full_tabs_css.read_text(encoding="utf-8") + "</style>", unsafe_allow_html=True)

# UI-only final white-background theme (last cascade layer).
_white_starlight_css = BASE_DIR / "stockwise_white_starlight.css"
if _white_starlight_css.is_file():
    st.markdown("<style>" + _white_starlight_css.read_text(encoding="utf-8") + "</style>", unsafe_allow_html=True)


# Final button and missing-logo presentation fixes.
_sw_no_pink_css = BASE_DIR / "stockwise_no_pink.css"
if _sw_no_pink_css.is_file():
    st.markdown("<style>" + _sw_no_pink_css.read_text(encoding="utf-8") + "</style>", unsafe_allow_html=True)
