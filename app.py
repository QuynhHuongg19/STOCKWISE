
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

</style>
""",
    unsafe_allow_html=True,
)


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


def load_prices(symbol):
    candidates = [
        PRICE_DIR / f"{symbol}.csv",
        PRICE_DIR / f"{symbol.lower()}.csv",
        BASE_DIR / "data" / f"{symbol}.csv",
        BASE_DIR / f"{symbol}.csv",
    ]

    for path in candidates:
        if not path.exists():
            continue

        df = read_local_csv(
            str(path),
            path.stat().st_mtime,
            symbol,
        )

        if not df.empty:
            try:
                source = str(
                    path.relative_to(BASE_DIR)
                )
            except ValueError:
                source = str(path)

            return df, source

    return pd.DataFrame(), ""


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

    for name, color in [
        ("SMA20", BLUE),
        ("SMA50", PURPLE),
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
        '<div class="company-logo-box">'
        '<span style="font-size:36px;">🏢</span>'
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
            title = (entry.findtext("title") or "").strip()
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


def render_stockwise_company_news(ticker, company, prices):
    st.markdown("#### 🏢 Giới thiệu & tin tức doanh nghiệp")
    left, right = st.columns([1, 1.5])
    with left:
        st.markdown(f"**{company}**")
        st.caption(f"Mã chứng khoán: {ticker}")
        st.write("**Nhóm dữ liệu:** " + ("Ngân hàng" if ticker in BANK_SYMBOLS else "Cổ phiếu doanh nghiệp"))
        st.write(f"**Dữ liệu giá hiện có:** {len(prices):,} phiên")
        st.write(f"**Giai đoạn:** {prices['date'].min():%d/%m/%Y} – {prices['date'].max():%d/%m/%Y}")
    with right:
        st.markdown("**📰 STOCKWISE News Hub · Báo chính thống**")
        chosen_sources = st.multiselect("Chọn nguồn báo", list(NEWS_FEEDS), default=list(NEWS_FEEDS), key="stockwise_news_sources")
        if st.button("🔄 Làm mới tin tức", key=f"stockwise_news_refresh_{ticker}", use_container_width=True):
            stockwise_direct_news.clear()
        with st.spinner("Đang kiểm tra bài báo mới từ các tòa soạn..."):
            articles, errors = stockwise_direct_news(ticker, company)
        filtered = [a for a in articles if a["source"] in chosen_sources]
        st.caption(f"{len(filtered)} bài liên quan tìm thấy · Sắp xếp theo thời gian đăng (mới nhất trước)")
        if not filtered:
            st.info("Chưa có tin tức phù hợp.")
        for article in filtered[:12]:
            st.markdown(f"**[{html.escape(article['title'])}]({article['url']})**")
            st.caption(f"{article['source']} · {article['date']} · Mở bài gốc ↗")
        if errors:
            st.caption("Nguồn tin tạm thời không khả dụng: " + ", ".join(errors) + ".")
    st.divider()



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
    section_heading(
        f"✨ Tổng quan cổ phiếu · {symbol}"
    )

    render_stockwise_company_news(symbol, company_name, stock)
    with st.expander("🗓️ News Impact Timeline", expanded=False):
        render_stockwise_news_timeline(symbol, company_name, stock)

    render_html(
        f"""
        <div class="kpi-grid">

            <div class="kpi-card kpi-pink">
                <div class="kpi-label">
                    Giá đóng cửa
                </div>
                <div class="kpi-value">
                    {fmt(latest["close"])}
                </div>
                <div class="kpi-note">
                    Biến động {selected_time}: {delta_text}
                </div>
            </div>

            <div class="kpi-card kpi-blue">
                <div class="kpi-label">
                    Khối lượng giao dịch
                </div>
                <div class="kpi-value">
                    {fmt(latest["volume"],0)}
                </div>
                <div class="kpi-note">
                    Phiên gần nhất
                </div>
            </div>

            <div class="kpi-card kpi-purple">
                <div class="kpi-label">
                    Số phiên dữ liệu
                </div>
                <div class="kpi-value">
                    {len(filtered_stock):,}
                </div>
                <div class="kpi-note">
                    Trong khoảng {selected_time}
                </div>
            </div>

            <div class="kpi-card kpi-mint">
                <div class="kpi-label">
                    Ngày cập nhật
                </div>
                <div class="kpi-value">
                    {latest_date}
                </div>
                <div class="kpi-note">
                    Phiên dữ liệu cuối cùng
                </div>
            </div>

        </div>
        """
    )

    st.caption(
        f"Nguồn: {source} · "
        f"Khoảng chọn: {selected_time} · "
        "Đơn vị giá theo dữ liệu nguồn."
    )

    section_heading(
        "📊 Diễn biến giá cổ phiếu"
    )

    chart_col, info_col = st.columns(
        [2.3, 1],
        gap="medium",
    )

    with chart_col:
        st.plotly_chart(
            create_price_chart(
                filtered_stock
            ),
            use_container_width=True,
        )

    with info_col:
        st.markdown(
            "#### Thông tin phiên"
        )

        info_card(
            "Giá mở cửa",
            fmt(latest["open"]),
            color="pink",
        )

        info_card(
            "Giá cao nhất",
            fmt(latest["high"]),
            color="blue",
        )

        info_card(
            "Giá thấp nhất",
            fmt(latest["low"]),
            color="purple",
        )

        info_card(
            "Giá đóng cửa",
            fmt(latest["close"]),
            color="mint",
        )


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
    st.caption("Chấm điểm theo 4 trụ cột: Kỹ thuật · Tài chính · Định giá · Rủi ro. Chỉ phục vụ phân tích tham khảo.")
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
                    # TV2 sử dụng classify_symbol(), không có evaluate_signals().
                    # Chuyển đúng định dạng 'signals' của TV2 sang 'reasons' của TV4.
                    technical_input = None
                    try:
                        _, signals_tv2, _, _ = run_technical(stock)
                        mapping = {"Tích cực": 1, "Trung lập": 0, "Tiêu cực": -1}
                        reasons = [{"rule": str(s.get("Chỉ báo", "")),
                                    "score": mapping.get(s.get("Tín hiệu"), 0),
                                    "label": s.get("Tín hiệu", "Trung lập"),
                                    "explain": s.get("Giải thích", "")}
                                   for s in signals_tv2 if isinstance(s, dict)]
                        if reasons:
                            technical_input = {"reasons": reasons}
                    except Exception as exc:
                        st.warning(f"Chưa ghép được tín hiệu TV2: {exc}. Sử dụng động lượng giá nếu đủ dữ liệu.")
                    
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

    st.caption(
        f"Nguồn: {source} · "
        f"{len(stock):,} phiên dữ liệu."
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
    from stockwise_pdf_report import build_report
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
            scoring = score_stock(symbol, price_df=stock, benchmark=None,
                                  fundamentals=financial, profile="balanced")
        except Exception as exc:
            scoring = None
            st.warning(f"Chưa thể tự chấm điểm ({exc}). PDF vẫn xuất các phần có dữ liệu.")
    technical = None
    if include_technical:
        try:
            technical = run_technical(stock)
        except Exception:
            technical = None
    return build_report(symbol, stock, selected_time, change_pct,
                        financial=financial, scoring=scoring, technical=technical,
                        include_overview=include_overview, include_technical=include_technical,
                        include_financial=include_financial, include_scoring=include_scoring,
                        report_title=report_title,
                        risk_heatmap=stockwise_risk_matrix(stock) if include_heatmap else None,
                        news_articles=(st.session_state.get("sw_timeline_news", {}).get("articles", [])
                                       if st.session_state.get("sw_timeline_news", {}).get("symbol") == symbol else []) if include_news else None)


# ============================================================
# TAB 6 - PDF EXPORT
# ============================================================

with tabs[5]:
    st.markdown("""
    <style>
    .sw-report-hero {
        background: linear-gradient(115deg,#FFE1F0 0%,#E9DFFF 55%,#D1EAFF 100%);
        border: 2px solid #E6A8EB;
        border-radius: 26px;
        padding: 32px 34px;
        margin: 12px 0 25px;
        box-shadow: 0 15px 32px rgba(170,100,180,.22), 0 5px 13px rgba(242,104,170,.14);
        color: #172E5A;
    }
    .sw-report-eyebrow {color:#9B368B;font-size:12px;font-weight:850;letter-spacing:2px;}
    .sw-report-heading {font-size:clamp(24px,3vw,36px);font-weight:900;line-height:1.3;margin:15px 0 10px;}
    .sw-report-desc {color:#53658A;font-size:14px;line-height:1.7;max-width:670px;}
    .sw-report-label {font-size:17px;font-weight:800;color:#17345F;margin:18px 0 9px;}
    /* Chi ap dung cho nut Tao bao cao, khong anh huong cac nut khac */
    div.st-key-sw_generate_pdf button {
        background: linear-gradient(110deg, #F9A6D5 0%, #F17BBD 52%, #E98CCF 100%) !important;
        color: #FFFFFF !important;
        border: 2px solid #F8D7EE !important;
        border-radius: 22px !important;
        min-height: 65px !important;
        font-size: 22px !important;
        font-weight: 900 !important;
        letter-spacing: .3px !important;
        text-shadow: 0 2px 5px rgba(108,35,92,.30);
        box-shadow: 0 10px 24px rgba(219,70,153,.35), 0 4px 10px rgba(115,67,162,.17) !important;
        transition: transform .2s ease, box-shadow .2s ease !important;
    }
    div.st-key-sw_generate_pdf button p {
        font-size: 22px !important;
        font-weight: 900 !important;
        color: #FFFFFF !important;
    }
    div.st-key-sw_generate_pdf button:hover {
        transform: translateY(-2px);
        background: linear-gradient(110deg,#F48AC6,#E95FAE,#DB7CC8) !important;
        box-shadow: 0 14px 30px rgba(211,56,142,.45) !important;
    }
    div[data-testid="stTabs"] div[data-testid="stCheckbox"] {background:#FFF7FC;border:1px solid #EBD0F3;border-radius:12px;padding:6px 12px;}
    </style>
    <div class="sw-report-hero">
        <div class="sw-report-eyebrow">✦ STOCKWISE / REPORT STUDIO</div>
        <div class="sw-report-heading">Báo cáo cổ phiếu của bạn.<br>Sẵn sàng để trình bày.</div>
        <div class="sw-report-desc">Tổng hợp dữ liệu thị trường, chỉ báo kỹ thuật và phân tích tài chính thành một báo cáo PDF tiếng Việt với nhận diện STOCKWISE.</div>
    </div>
    """, unsafe_allow_html=True)

    st.markdown('<div class="sw-report-label">✍️ Thiết lập báo cáo</div>', unsafe_allow_html=True)
    pdf_title = st.text_input(
        "Tiêu đề báo cáo", value=f"Báo cáo phân tích cổ phiếu {symbol}",
        key=f"sw_pdf_title_{symbol}",
    )
    st.caption(f"Mã cổ phiếu: {symbol} · Kỳ phân tích hiện tại: {selected_time} · Dữ liệu có sẵn trong STOCKWISE")
    st.markdown('<div class="sw-report-label">📑 Nội dung cần xuất</div>', unsafe_allow_html=True)
    a, b, c = st.columns(3)
    with a:
        pdf_overview = st.checkbox("Tổng quan cổ phiếu", value=True, key="sw_pdf_overview")
    with b:
        pdf_technical = st.checkbox("Phân tích kỹ thuật", value=True, key="sw_pdf_technical")
    with c:
        pdf_financial = st.checkbox("Phân tích tài chính", value=True, key="sw_pdf_financial")

    pdf_scoring = st.checkbox("🎯 Chấm điểm & rủi ro", value=True, key="sw_pdf_scoring")
    x, y = st.columns(2)
    with x:
        pdf_heatmap = st.checkbox("🌡️ Risk Heatmap", value=True, key="sw_pdf_heatmap")
    with y:
        pdf_news = st.checkbox("🗓️ News Timeline", value=True, key="sw_pdf_news")
    pdf_fetch_financial = st.checkbox("Tự tải tài chính nếu chưa có (cần Internet)", value=True, key="sw_pdf_fetch_financial")
    pdf_compute_scoring = st.checkbox("Tự tính điểm nếu chưa có", value=True, key="sw_pdf_compute_scoring")
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
