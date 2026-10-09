
from __future__ import annotations

from pathlib import Path
import io
import re

import pandas as pd
import numpy as np
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import streamlit as st

from technical_analysis import add_indicators, classify_symbol, check_data


# ============================================================
# 1. CẤU HÌNH DASHBOARD
# ============================================================

st.set_page_config(
    page_title="STOCKWISE | Phân tích cổ phiếu",
    page_icon="📈",
    layout="wide"
)

st.markdown("""
<style>
.stApp {
    background: #f5f9ff;
    color: #163453;
}

.block-container {
    padding-top: 1.4rem;
    max-width: 1500px;
}

h1, h2, h3 {
    color: #164a7c !important;
}

[data-testid="stMetric"] {
    background: white;
    padding: 14px;
    border-radius: 14px;
    border: 1px solid #d9e7f7;
}

[data-testid="stSidebar"] {
    background: #eaf3ff;
}

.stButton button {
    background: #f59e0b;
    color: white;
    border: none;
    border-radius: 10px;
    font-weight: 700;
}

.stButton button:hover {
    background: #e58b05;
    color: white;
}
</style>
""", unsafe_allow_html=True)


# ============================================================
# 2. ĐƯỜNG DẪN DỮ LIỆU TV1
# ============================================================

BASE = Path(__file__).resolve().parent

TV1_DATA = BASE / "data_pipeline" / "data"

REQUIRED = {
    "date",
    "symbol",
    "open",
    "high",
    "low",
    "close",
    "volume"
}


# ============================================================
# 3. CHUẨN HÓA DỮ LIỆU
# ============================================================

def normalize_prices(
    raw: pd.DataFrame,
    default_symbol: str = ""
) -> pd.DataFrame:

    d = raw.copy()

    d.columns = [
        str(c).strip().lower()
        for c in d.columns
    ]

    aliases = {
        "datetime": "date",
        "time": "date",
        "ticker": "symbol",
        "code": "symbol",
        "vol": "volume"
    }

    d = d.rename(
        columns={
            k: v
            for k, v in aliases.items()
            if k in d.columns and v not in d.columns
        }
    )

    if "symbol" not in d.columns and default_symbol:
        d["symbol"] = default_symbol

    missing = REQUIRED - set(d.columns)

    if missing:
        raise ValueError(
            "Thiếu cột dữ liệu: "
            + ", ".join(sorted(missing))
        )

    d["date"] = pd.to_datetime(
        d["date"],
        errors="coerce"
    )

    d["symbol"] = (
        d["symbol"]
        .astype(str)
        .str.strip()
        .str.upper()
    )

    for col in [
        "open",
        "high",
        "low",
        "close",
        "volume"
    ]:
        d[col] = pd.to_numeric(
            d[col],
            errors="coerce"
        )

    d = d.dropna(
        subset=[
            "date",
            "symbol",
            "open",
            "high",
            "low",
            "close"
        ]
    )

    d = d[
        (d["close"] > 0)
        & (d["symbol"] != "")
    ]

    return (
        d.sort_values(["symbol", "date"])
        .drop_duplicates(
            ["symbol", "date"],
            keep="last"
        )
        .reset_index(drop=True)
    )


@st.cache_data(show_spinner=False)
def read_csv_cached(
    path: str,
    modified: float,
    default_symbol: str = ""
) -> pd.DataFrame:

    return normalize_prices(
        pd.read_csv(path),
        default_symbol
    )


# ============================================================
# 4. ĐỌC DỮ LIỆU TV1
# ============================================================

def load_local(symbol: str) -> tuple[pd.DataFrame, str]:

    candidates = [
        TV1_DATA / "prices" / f"{symbol}.csv",
        TV1_DATA / "prices" / f"{symbol.lower()}.csv",
        TV1_DATA / "stock_prices.csv",
        BASE / "data" / "stock_prices.csv",
        BASE / "stock_prices.csv"
    ]

    for p in candidates:

        if p.is_file():

            try:
                df = read_csv_cached(
                    str(p),
                    p.stat().st_mtime,
                    symbol if p.parent.name == "prices" else ""
                )

                df = df[
                    df["symbol"] == symbol
                ].copy()

                if not df.empty:
                    return df, str(p.relative_to(BASE))

            except Exception as exc:

                st.sidebar.warning(
                    f"Không đọc được {p.name}: {exc}"
                )

    return pd.DataFrame(), ""


# ============================================================
# 5. BIỂU ĐỒ GIÁ VÀ KHỐI LƯỢNG
# ============================================================

def price_figure(
    df: pd.DataFrame,
    symbol: str
) -> go.Figure:

    d = df.tail(250)

    fig = make_subplots(
        rows=2,
        cols=1,
        shared_xaxes=True,
        row_heights=[0.75, 0.25],
        vertical_spacing=0.07
    )

    fig.add_trace(
        go.Candlestick(
            x=d["date"],
            open=d["open"],
            high=d["high"],
            low=d["low"],
            close=d["close"],
            name=symbol,
            increasing_line_color="#0d9488",
            decreasing_line_color="#e76f51"
        ),
        row=1,
        col=1
    )

    colors = np.where(
        d["close"] >= d["open"],
        "#0d9488",
        "#e76f51"
    )

    fig.add_trace(
        go.Bar(
            x=d["date"],
            y=d["volume"],
            marker_color=colors,
            name="Khối lượng"
        ),
        row=2,
        col=1
    )

    fig.update_layout(
        height=590,
        template="plotly_white",
        xaxis_rangeslider_visible=False,
        margin=dict(
            l=10,
            r=10,
            t=35,
            b=15
        ),
        legend=dict(orientation="h")
    )

    return fig


# ============================================================
# 6. BIỂU ĐỒ CHỈ BÁO KỸ THUẬT TV2
# ============================================================

def indicator_figure(
    df: pd.DataFrame,
    symbol: str
) -> go.Figure:

    d = df.tail(250)

    fig = make_subplots(
        rows=3,
        cols=1,
        shared_xaxes=True,
        row_heights=[0.56, 0.20, 0.24],
        vertical_spacing=0.07,
        subplot_titles=(
            f"{symbol} · Giá / SMA / Bollinger",
            "RSI14",
            "MACD"
        )
    )

    fig.add_trace(
        go.Candlestick(
            x=d["Date"],
            open=d["Open"],
            high=d["High"],
            low=d["Low"],
            close=d["Close"],
            name="Giá",
            increasing_line_color="#0d9488",
            decreasing_line_color="#e76f51"
        ),
        row=1,
        col=1
    )

    for col, color in [
        ("SMA20", "#f59e0b"),
        ("SMA50", "#2563eb"),
        ("BB_Upper", "#94a3b8"),
        ("BB_Lower", "#94a3b8")
    ]:

        fig.add_trace(
            go.Scatter(
                x=d["Date"],
                y=d[col],
                name=col,
                line=dict(
                    color=color,
                    width=1.4,
                    dash=(
                        "dot"
                        if col.startswith("BB_")
                        else "solid"
                    )
                )
            ),
            row=1,
            col=1
        )

    fig.add_trace(
        go.Scatter(
            x=d["Date"],
            y=d["RSI14"],
            name="RSI14",
            line=dict(color="#7c3aed")
        ),
        row=2,
        col=1
    )

    fig.add_hline(
        y=70,
        line_dash="dash",
        line_color="#e76f51",
        row=2,
        col=1
    )

    fig.add_hline(
        y=30,
        line_dash="dash",
        line_color="#0d9488",
        row=2,
        col=1
    )

    fig.add_trace(
        go.Bar(
            x=d["Date"],
            y=d["MACD_Hist"],
            name="MACD Histogram",
            marker_color="#8dbde9"
        ),
        row=3,
        col=1
    )

    fig.add_trace(
        go.Scatter(
            x=d["Date"],
            y=d["MACD"],
            name="MACD",
            line=dict(color="#2563eb")
        ),
        row=3,
        col=1
    )

    fig.add_trace(
        go.Scatter(
            x=d["Date"],
            y=d["MACD_Signal"],
            name="Signal",
            line=dict(color="#f59e0b")
        ),
        row=3,
        col=1
    )

    fig.update_layout(
        height=830,
        template="plotly_white",
        xaxis_rangeslider_visible=False,
        margin=dict(
            l=10,
            r=10,
            t=60,
            b=15
        ),
        legend=dict(orientation="h")
    )

    fig.update_yaxes(
        range=[0, 100],
        row=2,
        col=1
    )

    return fig


# ============================================================
# 7. TIÊU ĐỀ DASHBOARD
# ============================================================

st.title("📈 STOCKWISE")

st.caption(
    "Nền tảng phân tích cổ phiếu Việt Nam · "
    "Dashboard TV5 · Phân tích kỹ thuật TV2"
)


# ============================================================
# 8. SIDEBAR - NHẬP MÃ CỔ PHIẾU
# ============================================================

with st.sidebar:

    st.markdown("### 🔎 Tra cứu cổ phiếu")

    entered = st.text_input(
        "Nhập mã cổ phiếu",
        value="FPT",
        help="Ví dụ: FPT, HPG, VCB, VNM..."
    ).strip().upper()

    symbol = (
        entered
        if re.fullmatch(r"[A-Z0-9]{2,10}", entered)
        else ""
    )

    uploaded = st.file_uploader(
        "Hoặc tải CSV dữ liệu giá thực",
        type=["csv"],
        help=(
            "CSV có date, symbol, open, "
            "high, low, close, volume"
        )
    )

    st.caption(
        "Ưu tiên CSV tải lên; "
        "nếu không có, đọc dữ liệu đã lưu của TV1."
    )

    st.divider()

    st.info(
        "Chỉ sử dụng dữ liệu thật. "
        "Chưa hỗ trợ tải giá trực tuyến "
        "khi TV1 thiếu VNStock."
    )


# ============================================================
# 9. TẢI DỮ LIỆU CỔ PHIẾU
# ============================================================

if not symbol:

    st.warning(
        "Vui lòng nhập mã cổ phiếu hợp lệ "
        "(chữ cái và số, không có khoảng trắng)."
    )

    st.stop()


stock = pd.DataFrame()
source = ""

if uploaded is not None:

    try:

        all_uploaded = normalize_prices(
            pd.read_csv(
                io.BytesIO(uploaded.getvalue())
            ),
            default_symbol=symbol
        )

        stock = all_uploaded[
            all_uploaded["symbol"] == symbol
        ].copy()

        source = f"CSV tải lên: {uploaded.name}"

    except Exception as exc:

        st.error(f"CSV không hợp lệ: {exc}")
        st.stop()

else:

    stock, source = load_local(symbol)


if stock.empty:

    st.warning(
        f"Chưa có dữ liệu giá thực cho mã **{symbol}**."
    )

    st.markdown(
        "**Để hiển thị biểu đồ:** "
        "Tải lên file CSV có các cột "
        "`date, symbol, open, high, low, close, volume`, "
        "hoặc đặt dữ liệu TV1 trong "
        "`data_pipeline/data/prices/` "
        "hay `data_pipeline/data/stock_prices.csv`."
    )

    st.caption(
        "STOCKWISE đã sẵn sàng; "
        "chưa thể tính chỉ báo hoặc đưa ra "
        "tín hiệu khi thiếu dữ liệu."
    )

    st.stop()


# ============================================================
# 10. TỔNG QUAN CỔ PHIẾU
# ============================================================

stock = (
    stock.sort_values("date")
    .reset_index(drop=True)
)

last = stock.iloc[-1]

prev = (
    stock.iloc[-2]
    if len(stock) > 1
    else None
)

pct = (
    (last["close"] / prev["close"] - 1) * 100
    if prev is not None and prev["close"] > 0
    else None
)

st.subheader(
    f"{symbol} · Tổng quan dữ liệu"
)

c1, c2, c3, c4 = st.columns(4)

c1.metric(
    "Giá đóng cửa gần nhất",
    f"{last['close']:,.2f}",
    f"{pct:+.2f}%" if pct is not None else None
)

c2.metric(
    "Khối lượng gần nhất",
    f"{last['volume']:,.0f}"
)

c3.metric(
    "Số phiên",
    f"{len(stock):,}"
)

c4.metric(
    "Ngày dữ liệu cuối",
    pd.Timestamp(
        last["date"]
    ).strftime("%d/%m/%Y")
)

st.caption(
    f"Nguồn: {source} · "
    "Đơn vị giá theo dữ liệu nguồn, "
    "chưa xác minh là VND."
)


# ============================================================
# 11. HỆ THỐNG 6 TAB
# ============================================================


tabs = st.tabs([
    "📈 Tổng quan",
    "📊 Phân tích kỹ thuật TV2",
    "🏦 Phân tích cơ bản TV3",
    "🎯 Chấm điểm TV4",
    "🛡️ Rủi ro",
    "📁 Dữ liệu",
    "📄 Xuất báo cáo PDF"
])



# ============================================================
# TAB 1 - TỔNG QUAN
# ============================================================

with tabs[0]:

    st.subheader(
        f"Biểu đồ giá cổ phiếu {symbol}"
    )

    st.plotly_chart(
        price_figure(stock, symbol),
        use_container_width=True
    )


# ============================================================
# TAB 2 - PHÂN TÍCH KỸ THUẬT TV2
# ============================================================

with tabs[1]:

    st.subheader(
        f"Phân tích kỹ thuật · {symbol}"
    )

    try:

        # Chuẩn hóa tên cột cho TV2
        tv2_input = stock.rename(
            columns={
                "date": "Date",
                "symbol": "Symbol",
                "open": "Open",
                "high": "High",
                "low": "Low",
                "close": "Close",
                "volume": "Volume"
            }
        )

        # Chạy thuật toán TV2
        indicators = add_indicators(tv2_input)

        signals, summary = classify_symbol(
            indicators
        )

        quality = check_data(tv2_input)

        # Nhận định tổng hợp
        a, b, c = st.columns(3)

        a.metric(
            "Nhận định tổng hợp",
            summary["Nhận định tổng hợp"]
        )

        b.metric(
            "Xu hướng",
            summary["Xu hướng"]
        )

        c.metric(
            "Động lượng",
            summary["Động lượng"]
        )

        st.caption(
            f"Phân tích từ {len(indicators)} phiên · "
            f"{summary['Nhận định tổng hợp']} · "
            "Tín hiệu kỹ thuật không phải "
            "khuyến nghị đầu tư."
        )

        # Các chỉ báo kỹ thuật
        st.markdown(
            "#### Các chỉ báo kỹ thuật"
        )

        latest = indicators.iloc[-1]

        m1, m2, m3, m4 = st.columns(4)

        for target, label, field in [
            (m1, "SMA20", "SMA20"),
            (m2, "SMA50", "SMA50"),
            (m3, "RSI14", "RSI14"),
            (m4, "MACD", "MACD")
        ]:

            val = latest[field]

            target.metric(
                label,
                (
                    f"{val:,.2f}"
                    if pd.notna(val)
                    else "Chưa đủ dữ liệu"
                )
            )

        # Biểu đồ kỹ thuật
        st.markdown(
            "#### Biểu đồ phân tích kỹ thuật"
        )

        st.plotly_chart(
            indicator_figure(indicators, symbol),
            use_container_width=True
        )

        # Tín hiệu chi tiết
        st.markdown(
            "#### Giải thích tín hiệu"
        )

        st.dataframe(
            pd.DataFrame(signals)[
                [
                    "Chỉ báo",
                    "Giá trị phiên gần nhất",
                    "Tín hiệu",
                    "Giải thích"
                ]
            ],
            use_container_width=True,
            hide_index=True
        )

        # Chất lượng dữ liệu
        if (
            not quality.empty
            and quality.iloc[0]["Cảnh báo dữ liệu"]
        ):

            st.warning(
                "Chất lượng dữ liệu: "
                + str(
                    quality.iloc[0]["Cảnh báo dữ liệu"]
                )
            )

    except Exception as exc:

        st.warning(
            f"Chưa thể phân tích kỹ thuật: {exc}"
        )


# ============================================================
# TAB 3 - PHÂN TÍCH CƠ BẢN TV3
# ============================================================

with tabs[2]:

    st.subheader(
        "Phân tích cơ bản · TV3"
    )

    st.info(
        "Chưa tích hợp module TV3 hoặc dữ liệu "
        "báo cáo tài chính. "
        "Không hiển thị chỉ tiêu giả."
    )


# ============================================================
# TAB 4 - CHẤM ĐIỂM TV4
# ============================================================

with tabs[3]:

    st.subheader(
        "Chấm điểm đầu tư · TV4"
    )

    st.info(
        "Chưa tích hợp module chấm điểm TV4. "
        "Không tự tạo điểm hay khuyến nghị mua/bán."
    )


# ============================================================
# TAB 5 - QUẢN TRỊ RỦI RO
# ============================================================

with tabs[4]:

    st.subheader(
        "Thống kê rủi ro từ giá lịch sử"
    )

    if len(stock) >= 2:

        returns = (
            stock["close"]
            .pct_change()
            .dropna()
        )

        vol = (
            returns.std() * np.sqrt(252) * 100
            if len(returns) >= 2
            else np.nan
        )

        drawdown = (
            stock["close"]
            / stock["close"].cummax()
            - 1
        ).min() * 100

        x, y = st.columns(2)

        x.metric(
            "Biến động năm hóa",
            (
                f"{vol:.2f}%"
                if pd.notna(vol)
                else "Chưa đủ dữ liệu"
            )
        )

        y.metric(
            "Maximum drawdown",
            f"{drawdown:.2f}%"
        )

        st.caption(
            "Ước tính từ dữ liệu quá khứ, "
            "không phải dự báo rủi ro tương lai."
        )

    else:

        st.info(
            "Cần thêm phiên giao dịch "
            "để tính chỉ số rủi ro."
        )


# ============================================================
# TAB 6 - DỮ LIỆU
# ============================================================

with tabs[5]:

    st.subheader(
        "Dữ liệu giá đang sử dụng"
    )

    st.dataframe(
        stock.sort_values(
            "date",
            ascending=False
        ),
        use_container_width=True,
        hide_index=True
    )

    st.download_button(
        "⬇️ Tải CSV dữ liệu đang xem",
        stock.to_csv(
            index=False
        ).encode("utf-8-sig"),
        file_name=f"{symbol}_prices.csv",
        mime="text/csv"
    )

# ============================================================
# TAB 7 - XUẤT BÁO CÁO PDF
# ============================================================

with tabs[6]:
    import io
    from datetime import datetime

    
    from reportlab.lib import colors
    from reportlab.lib.enums import TA_CENTER, TA_LEFT
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.units import cm
    from reportlab.platypus import (
        SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
    )

    # Font Arial có sẵn trên Windows, hỗ trợ tiếng Việt
    from reportlab.pdfbase import pdfmetrics
    from reportlab.pdfbase.ttfonts import TTFont

    pdfmetrics.registerFont(
        TTFont("ArialVN", "C:/Windows/Fonts/arial.ttf")
    )
    pdfmetrics.registerFont(
        TTFont("ArialVN-Bold", "C:/Windows/Fonts/arialbd.ttf")
    )
    pdfmetrics.registerFontFamily(
        "ArialVN",
        normal="ArialVN",
        bold="ArialVN-Bold"
    )


    st.subheader("📄 Báo cáo phân tích cổ phiếu STOCKWISE")
    st.caption("Tạo báo cáo PDF từ dữ liệu giá và các chỉ số hiện có trên Dashboard.")

    # Chọn nội dung báo cáo
    include_overview = st.checkbox("Tổng quan cổ phiếu", value=True)
    include_technical = st.checkbox("Phân tích kỹ thuật TV2", value=True)
    include_risk = st.checkbox("Quản trị rủi ro", value=True)
    include_prices = st.checkbox("Bảng giá gần nhất", value=False)

    report_title = st.text_input(
        "Tên báo cáo",
        value=f"Báo cáo phân tích cổ phiếu {symbol}"
    )

    if st.button("📄 Tạo báo cáo PDF", type="primary"):
        try:
            buffer = io.BytesIO()

            doc = SimpleDocTemplate(
                buffer,
                pagesize=A4,
                rightMargin=1.7 * cm,
                leftMargin=1.7 * cm,
                topMargin=1.7 * cm,
                bottomMargin=1.7 * cm,
            )

            styles = getSampleStyleSheet()
            styles.add(ParagraphStyle(
                name="VNTitle",
                parent=styles["Title"],
                fontName="Helvetica-Bold",
                fontSize=19,
                leading=25,
                alignment=TA_CENTER,
                textColor=colors.HexColor("#C2185B"),
                spaceAfter=16,
            ))
            styles.add(ParagraphStyle(
                name="VNBody",
                parent=styles["BodyText"],
                fontSize=10,
                leading=15,
                spaceAfter=7,
            ))

            story = [
                Paragraph("STOCKWISE", styles["VNTitle"]),
                Paragraph(report_title, styles["Heading2"]),
                Paragraph(
                    f"Mã cổ phiếu: <b>{symbol}</b>",
                    styles["VNBody"]
                ),
                Paragraph(
                    f"Ngày tạo báo cáo: {datetime.now().strftime('%d/%m/%Y %H:%M')}",
                    styles["VNBody"]
                ),
                Paragraph(
                    "Nguồn: dữ liệu giá đang được sử dụng trên Dashboard. "
                    "Báo cáo chỉ phục vụ tham khảo, không phải khuyến nghị đầu tư.",
                    styles["VNBody"]
                ),
                Spacer(1, 10),
            ]

            if include_overview:
                story.append(Paragraph("1. Tổng quan cổ phiếu", styles["Heading2"]))
                latest = stock.sort_values("date").iloc[-1]
                overview_data = [
                    ["Chỉ tiêu", "Giá trị"],
                    ["Mã cổ phiếu", str(symbol)],
                    ["Ngày giao dịch gần nhất", str(latest["date"])[:10]],
                    ["Giá đóng cửa", f"{float(latest['close']):,.2f}"],
                    ["Giá cao nhất trong kỳ", f"{float(stock['high'].max()):,.2f}"],
                    ["Giá thấp nhất trong kỳ", f"{float(stock['low'].min()):,.2f}"],
                    ["Số phiên dữ liệu", str(len(stock))],
                ]
                table = Table(overview_data, colWidths=[7 * cm, 8 * cm])
                table.setStyle(TableStyle([
                    ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#C2185B")),
                    ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                    ("GRID", (0, 0), (-1, -1), 0.4, colors.grey),
                    ("PADDING", (0, 0), (-1, -1), 7),
                ]))
                story.extend([table, Spacer(1, 12)])

            if include_technical:
                story.append(Paragraph("2. Phân tích kỹ thuật", styles["Heading2"]))
                story.append(Paragraph(
                    "Các chỉ số dưới đây được tính từ chuỗi giá đóng cửa hiện có.",
                    styles["VNBody"]
                ))

                close = stock.sort_values("date")["close"].astype(float)
                sma20 = close.rolling(20).mean().iloc[-1]
                sma50 = close.rolling(50).mean().iloc[-1]
                returns = close.pct_change().dropna()
                rsi_text = "Chưa tính trong báo cáo cơ bản"

                tech_data = [
                    ["Chỉ tiêu", "Giá trị"],
                    ["SMA20", f"{sma20:.2f}" if pd.notna(sma20) else "Chưa đủ dữ liệu"],
                    ["SMA50", f"{sma50:.2f}" if pd.notna(sma50) else "Chưa đủ dữ liệu"],
                    ["Số phiên có lợi suất", str(len(returns))],
                    ["RSI", rsi_text],
                ]
                table = Table(tech_data, colWidths=[7 * cm, 8 * cm])
                table.setStyle(TableStyle([
                    ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#C2185B")),
                    ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                    ("GRID", (0, 0), (-1, -1), 0.4, colors.grey),
                    ("PADDING", (0, 0), (-1, -1), 7),
                ]))
                story.extend([table, Spacer(1, 12)])

            if include_risk:
                story.append(Paragraph("3. Quản trị rủi ro", styles["Heading2"]))
                close = stock.sort_values("date")["close"].astype(float)
                returns = close.pct_change().dropna()

                if len(returns) >= 2:
                    volatility = returns.std() * (252 ** 0.5) * 100
                    drawdown = (close / close.cummax() - 1).min() * 100
                    risk_text = (
                        f"Biến động lịch sử năm hóa: {volatility:.2f}%. "
                        f"Maximum drawdown: {drawdown:.2f}%. "
                        "Đây là thống kê lịch sử, không phải dự báo."
                    )
                else:
                    risk_text = "Chưa đủ dữ liệu để tính các chỉ số rủi ro."

                story.append(Paragraph(risk_text, styles["VNBody"]))

            if include_prices:
                story.append(Paragraph("4. Dữ liệu giá gần nhất", styles["Heading2"]))
                recent = stock.sort_values("date", ascending=False).head(15)
                price_data = [["Ngày", "Mở cửa", "Cao nhất", "Thấp nhất", "Đóng cửa", "KL"]]
                for _, row in recent.iterrows():
                    price_data.append([
                        str(row["date"])[:10],
                        f"{float(row['open']):,.2f}",
                        f"{float(row['high']):,.2f}",
                        f"{float(row['low']):,.2f}",
                        f"{float(row['close']):,.2f}",
                        f"{float(row['volume']):,.0f}",
                    ])

                table = Table(
                    price_data,
                    repeatRows=1,
                    colWidths=[2.1*cm, 2.1*cm, 2.1*cm, 2.1*cm, 2.1*cm, 2*cm]
                )
                table.setStyle(TableStyle([
                    ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#C2185B")),
                    ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                    ("GRID", (0, 0), (-1, -1), 0.3, colors.grey),
                    ("FONTSIZE", (0, 0), (-1, -1), 7),
                    ("PADDING", (0, 0), (-1, -1), 4),
                ]))
                story.append(table)

            doc.build(story)
            pdf_bytes = buffer.getvalue()
            buffer.close()

            st.success("Đã tạo báo cáo PDF!")
            st.download_button(
                "⬇️ Tải báo cáo PDF",
                data=pdf_bytes,
                file_name=f"STOCKWISE_{symbol}_{datetime.now():%Y%m%d_%H%M}.pdf",
                mime="application/pdf",
            )

        except Exception as exc:
            st.error(f"Không thể tạo báo cáo PDF: {exc}")
