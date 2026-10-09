"""Chuẩn hóa, kiểm tra và đưa dữ liệu thô từ nguồn về schema thống nhất của TV1.

Nguyên tắc: KHÔNG điền giá giả, KHÔNG nội suy, KHÔNG thay thiếu bằng 0.
Dòng sai bị loại khỏi bảng sạch nhưng LUÔN được ghi vào bảng `issues` để rà soát.
Biến động giá lớn KHÔNG bị xóa (có thể là biến động thật).
"""
from __future__ import annotations

import logging
import re
from datetime import datetime, timedelta, timezone
from typing import Iterable, Optional

import numpy as np
import pandas as pd

import config

logger = logging.getLogger(__name__)

ISSUE_COLUMNS = ["symbol", "date", "issue", "detail"]


class DataValidationError(Exception):
    """Dữ liệu nguồn sai cấu trúc (thiếu cột bắt buộc...)."""


# ------------------------------------------------------------------ tiện ích
def utc_now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def normalize_symbol(symbol) -> str:
    if symbol is None or (isinstance(symbol, float) and np.isnan(symbol)):
        return ""
    return str(symbol).strip().upper()


def empty_prices() -> pd.DataFrame:
    return pd.DataFrame({
        "date": pd.Series(dtype="datetime64[ns]"), "symbol": pd.Series(dtype="object"),
        "open": pd.Series(dtype="float64"), "high": pd.Series(dtype="float64"),
        "low": pd.Series(dtype="float64"), "close": pd.Series(dtype="float64"),
        "volume": pd.Series(dtype="float64"), "source": pd.Series(dtype="object"),
        "fetched_at": pd.Series(dtype="object"),
    })


def empty_issues() -> pd.DataFrame:
    return pd.DataFrame(columns=ISSUE_COLUMNS)


# ------------------------------------------------------------------ chuẩn hóa giá
_ALIASES = {
    "date": ["time", "date", "trading_date", "tradingdate", "ngay"],
    "open": ["open", "open_price", "openprice"],
    "high": ["high", "high_price", "highest", "highprice"],
    "low": ["low", "low_price", "lowest", "lowprice"],
    "close": ["close", "close_price", "closeprice"],
    "volume": ["volume", "total_volume", "vol", "match_volume"],
    "trading_value": ["value", "total_value", "trading_value"],
}
REQUIRED = ["date", "open", "high", "low", "close", "volume"]


def _map_columns(df: pd.DataFrame) -> pd.DataFrame:
    lowered = {c: str(c).strip().lower() for c in df.columns}
    inv = {}
    for std, cands in _ALIASES.items():
        for cand in cands:
            hit = [c for c, l in lowered.items() if l == cand]
            if hit:
                inv[hit[0]] = std
                break
    out = df.rename(columns=inv)
    return out.loc[:, ~out.columns.duplicated()]


def standardize_price_frame(raw: Optional[pd.DataFrame], symbol: str, source: str,
                            fetched_at: Optional[str] = None,
                            price_multiplier: Optional[float] = None):
    """Trả về (bảng_sạch, bảng_issues). Bảng sạch có schema config.PRICE_SCHEMA."""
    symbol = normalize_symbol(symbol)
    fetched_at = fetched_at or utc_now_iso()
    mult = config.PRICE_MULTIPLIER if price_multiplier is None else price_multiplier
    if raw is None or len(raw) == 0:
        return empty_prices(), empty_issues()

    df = _map_columns(raw)
    missing = [c for c in REQUIRED if c not in df.columns]
    if missing:
        raise DataValidationError(f"{symbol}: thiếu cột bắt buộc {missing}; cột nguồn = {list(raw.columns)}")

    issues: list[dict] = []
    n = len(df)
    dropped = np.zeros(n, dtype=bool)

    def flag(mask, issue, detail="", drop=True):
        mask = np.asarray(mask, dtype=bool)
        new = mask & ~dropped
        for idx in np.flatnonzero(new):
            d = df["date"].iloc[idx]
            issues.append({"symbol": symbol, "date": d.strftime("%Y-%m-%d") if pd.notna(d) else None,
                           "issue": issue, "detail": detail})
        if drop:
            dropped[:] = dropped | mask

    # ngày
    dates = pd.to_datetime(df["date"], errors="coerce")
    if getattr(dates.dt, "tz", None) is not None:
        dates = dates.dt.tz_convert("Asia/Ho_Chi_Minh").dt.tz_localize(None)
    df["date"] = dates.dt.normalize()
    flag(df["date"].isna().to_numpy(), "invalid_date", "không đọc được ngày")
    flag((df["date"] > pd.Timestamp.today().normalize() + pd.Timedelta(days=1)).fillna(False).to_numpy(),
         "future_date", "ngày ở tương lai")

    # số
    for c in ["open", "high", "low", "close", "volume"] + (["trading_value"] if "trading_value" in df else []):
        df[c] = pd.to_numeric(df[c], errors="coerce")
    if mult != 1.0:
        for c in ["open", "high", "low", "close"]:
            df[c] = df[c] * mult

    prices = df[["open", "high", "low", "close"]]
    flag(prices.isna().any(axis=1).to_numpy(), "missing_price", "thiếu một/nhiều giá OHLC (không điền giả)")
    flag((prices < 0).any(axis=1).to_numpy(), "negative_price", "giá âm")
    flag((prices <= 0).any(axis=1).to_numpy(), "non_positive_price", "giá bằng 0")
    flag((df["volume"] < 0).fillna(False).to_numpy(), "negative_volume", "khối lượng âm")
    flag(df["volume"].isna().to_numpy(), "missing_volume", "thiếu khối lượng (giữ dòng, volume=NaN)", drop=False)
    ohlc_bad = ((df["high"] < df[["open", "close", "low"]].max(axis=1)) |
                (df["low"] > df[["open", "close", "high"]].min(axis=1))).fillna(False).to_numpy()
    flag(ohlc_bad, "ohlc_inconsistent", "high < max(open,close,low) hoặc low > min(open,close,high)")

    keep = df.loc[~dropped].copy()
    # trùng (symbol, date): giữ bản cuối cùng
    dup = keep.duplicated(subset=["date"], keep="last")
    for d in keep.loc[dup, "date"]:
        issues.append({"symbol": symbol, "date": d.strftime("%Y-%m-%d"), "issue": "duplicate_date",
                       "detail": "trùng ngày, giữ bản ghi cuối"})
    keep = keep.loc[~dup]

    out = pd.DataFrame({"date": keep["date"], "symbol": symbol})
    for c in ["open", "high", "low", "close"]:
        out[c] = keep[c].astype("float64")
    vol = keep["volume"]
    out["volume"] = vol.astype("Int64") if vol.dropna().mod(1).eq(0).all() else vol.astype("float64")
    out["source"] = source.upper()
    out["fetched_at"] = fetched_at
    if "trading_value" in keep:
        out["trading_value"] = keep["trading_value"]
    out = out.sort_values("date").reset_index(drop=True)
    return out, (pd.DataFrame(issues, columns=ISSUE_COLUMNS) if issues else empty_issues())


# ------------------------------------------------------------------ danh sách mã
STOCK_TYPE_TOKENS = {"stock", "stocks", "equity", "co phieu", "cổ phiếu", "cp"}
NON_STOCK_TOKENS = ("etf", "fund", "quỹ", "quy ", "bond", "trái phiếu", "trai phieu", "warrant",
                    "chứng quyền", "chung quyen", "cw", "future", "phái sinh", "index", "chỉ số")
_STOCK_PATTERN = re.compile(r"^[A-Z]{3}$")  # mã cổ phiếu VN phổ biến: 3 chữ cái


def _first_col(df: pd.DataFrame, names: Iterable[str]) -> Optional[str]:
    low = {str(c).lower(): c for c in df.columns}
    for n in names:
        if n in low:
            return low[n]
    return None


def classify_instrument(symbol: str, raw_type, excluded: set[str]) -> tuple[str, str]:
    """Trả về (loại, cơ sở_phân_loại). loại ∈ {stock, non_stock, unknown}.

    - stock/'source_type'   : nguồn ghi rõ là cổ phiếu
    - non_stock/...         : nguồn ghi ETF/TP/CW... hoặc nằm trong danh sách ETF/TP/CW của nguồn
    - stock/'pattern_inferred': nguồn không nêu loại, mã 3 chữ cái -> SUY LUẬN (độ tin cậy thấp hơn)
    - unknown               : không xác định -> bị loại khỏi danh sách cổ phiếu, lưu file riêng để rà soát
    """
    t = "" if raw_type is None or (isinstance(raw_type, float) and np.isnan(raw_type)) else str(raw_type).strip().lower()
    if t in STOCK_TYPE_TOKENS:
        return "stock", "source_type"
    if t and any(tok in t for tok in NON_STOCK_TOKENS):
        return "non_stock", "source_type"
    if symbol in excluded:
        return "non_stock", "excluded_list(etf/bond/cw)"
    if not t and _STOCK_PATTERN.match(symbol):
        return "stock", "pattern_inferred"
    return "unknown", "unclassified"


def normalize_symbol_list(raw: pd.DataFrame, source: str, excluded: Optional[set[str]] = None,
                          industries: Optional[pd.DataFrame] = None, fetched_at: Optional[str] = None) -> pd.DataFrame:
    """Chuẩn hóa bảng danh sách mã từ nguồn. Bảng trả về chứa TẤT CẢ mã (kể cả non_stock/unknown)."""
    fetched_at = fetched_at or utc_now_iso()
    excluded = {normalize_symbol(s) for s in (excluded or set())}
    if raw is None or len(raw) == 0:
        raise DataValidationError("Danh sách mã rỗng")
    sym_c = _first_col(raw, ["symbol", "ticker", "code"])
    if sym_c is None:
        raise DataValidationError(f"Không có cột mã; cột nguồn = {list(raw.columns)}")
    name_c = _first_col(raw, ["organ_name", "company_name", "name", "organ_short_name"])
    en_c = _first_col(raw, ["en_organ_name", "en_name"])
    ex_c = _first_col(raw, ["exchange", "comgroupcode", "floor", "san"])
    ty_c = _first_col(raw, ["type", "instrument_type", "product_grp_id", "security_type"])

    out = pd.DataFrame({"symbol": raw[sym_c].map(normalize_symbol)})
    out["organ_name"] = raw[name_c].values if name_c else None
    out["en_organ_name"] = raw[en_c].values if en_c else None
    out["exchange"] = raw[ex_c].astype(str).str.strip().str.upper().replace({"UPCOM": "UPCOM", "UPCOM ": "UPCOM"}).values if ex_c else None
    out["source_type_raw"] = raw[ty_c].values if ty_c else None
    out = out[out["symbol"] != ""]
    cls = [classify_instrument(s, t, excluded) for s, t in zip(out["symbol"], out["source_type_raw"])]
    out["instrument_class"] = [c[0] for c in cls]
    out["classification_basis"] = [c[1] for c in cls]

    if industries is not None and len(industries):
        isym = _first_col(industries, ["symbol", "ticker"])
        if isym is not None:
            icols = [c for c in industries.columns if c != isym and
                     re.search(r"icb|industry|sector", str(c).lower()) and not str(c).lower().endswith("_id")]
            if icols:
                ind = industries[[isym] + icols].copy()
                ind[isym] = ind[isym].map(normalize_symbol)
                ind = ind.drop_duplicates(subset=[isym]).rename(columns={isym: "symbol", **{c: f"industry__{c}" for c in icols}})
                out = out.merge(ind, on="symbol", how="left")
    out["source"] = source.upper()
    out["fetched_at"] = fetched_at
    # loại trùng: ưu tiên bản có exchange, giữ bản đầu
    out["_has_ex"] = out["exchange"].notna()
    out = (out.sort_values("_has_ex", ascending=False, kind="stable")
              .drop_duplicates(subset=["symbol"], keep="first").drop(columns="_has_ex")
              .sort_values(["exchange", "symbol"]).reset_index(drop=True))
    return out


# ------------------------------------------------------------------ báo cáo tài chính -> dạng dài
_PERIOD_RE = re.compile(r"^(\d{4})(?:[-_ ]?Q([1-4]))?$", re.IGNORECASE)
_META_COLS = ["item", "item_id", "unit"]


def statement_to_long(raw: pd.DataFrame, symbol: str, statement: str, requested_period: str,
                      source: str, fetched_at: Optional[str] = None) -> pd.DataFrame:
    """Chuyển bảng báo cáo dạng rộng (mỗi kỳ một cột) sang dạng dài.

    Các trường nguồn KHÔNG cung cấp (ngày công bố, riêng/hợp nhất) được để trống (None),
    tuyệt đối không suy đoán. Dòng có kỳ không khớp loại yêu cầu (quý vs năm) bị loại và log.
    """
    fetched_at = fetched_at or utc_now_iso()
    if raw is None or len(raw) == 0:
        return pd.DataFrame()
    period_cols = [c for c in raw.columns if _PERIOD_RE.match(str(c).strip())]
    if not period_cols or "item" not in {str(c).lower() for c in raw.columns}:
        raise DataValidationError(
            f"{symbol}/{statement}: bố cục chưa hỗ trợ (không có cột kỳ dạng 2024 / 2024-Q1). Cột: {list(raw.columns)[:12]}")
    df = raw.rename(columns={c: str(c).lower() for c in raw.columns if str(c).lower() in _META_COLS})
    id_cols = [c for c in _META_COLS if c in df.columns]
    long = df.melt(id_vars=id_cols, value_vars=period_cols, var_name="period_label", value_name="value")
    long["period_label"] = long["period_label"].astype(str).str.strip().str.upper().str.replace("_", "-").str.replace(" ", "-")
    long["period_type"] = np.where(long["period_label"].str.contains("Q"), "quarter", "year")
    want = "quarter" if requested_period.lower().startswith("q") else "year"
    mism = long["period_type"] != want
    if mism.any():
        logger.warning("%s/%s: loại %d dòng có loại kỳ không khớp yêu cầu '%s'", symbol, statement, int(mism.sum()), want)
        long = long[~mism]
    long["value"] = pd.to_numeric(long["value"], errors="coerce")
    for c in ("item_id", "unit"):
        if c not in long:
            long[c] = None
    long.insert(0, "symbol", normalize_symbol(symbol))
    long.insert(1, "statement", statement)
    long["report_scope"] = None        # riêng/hợp nhất: nguồn không cung cấp rõ -> để trống
    long["published_date"] = None      # ngày công bố: nguồn không cung cấp -> để trống
    long["source"] = source.upper()
    long["fetched_at"] = fetched_at
    cols = ["symbol", "statement", "period_type", "period_label", "item", "item_id", "unit", "value",
            "report_scope", "published_date", "source", "fetched_at"]
    return long[cols].reset_index(drop=True)
