"""TV1 – data_loader: lấy danh sách mã, giá lịch sử, hồ sơ doanh nghiệp, báo cáo tài chính; đọc dữ liệu đã lưu.

API vnstock (3.x) đã đối chiếu với tài liệu chính thức:
  Listing(source="KBS").symbols_by_exchange(exchange="HOSE", to_df=True)  # cột: symbol, organ_name, en_organ_name, exchange, type, id
  Listing(source="KBS").all_etf() / all_bonds() / all_covered_warrant() / symbols_by_industries()
  Quote(symbol="ACB", source="VCI|KBS").history(start="YYYY-MM-DD", end="YYYY-MM-DD", interval="1D")
  Company(symbol=..., source=...).overview() / .profile()
  Finance(symbol=..., source="KBS").income_statement|balance_sheet|cash_flow|ratio(period="quarter"|"year")
Các lời gọi vnstock nằm gọn trong các hàm `_raw_*` để dễ thay/mock. Chưa chạy được với nguồn thật trong môi trường
phát triển (không có mạng) -> dùng `python run_pipeline.py --probe` để kiểm chứng trên máy bạn.
"""
from __future__ import annotations

import logging
import time
from datetime import datetime, timedelta
from typing import Iterable, Optional

import pandas as pd

import config
import storage
from data_cleaning import (DataValidationError, empty_issues, empty_prices, normalize_symbol,
                           normalize_symbol_list, standardize_price_frame, statement_to_long, utc_now_iso)

logger = logging.getLogger(__name__)

STATEMENTS = ("income_statement", "balance_sheet", "cash_flow", "ratio")


# =================================================================== lỗi & thử lại
class DataSourceError(Exception):
    def __init__(self, msg, kind="error"):
        super().__init__(msg)
        self.kind = kind          # "error" | "rate_limit" | "invalid"


class RateLimitError(DataSourceError):
    def __init__(self, msg):
        super().__init__(msg, kind="rate_limit")


_RATE_HINTS = ("429", "rate limit", "ratelimit", "too many", "quá nhiều", "quota", "giới hạn", "limit exceeded")
_sleep = time.sleep           # có thể patch trong kiểm thử
_last_request_ts = 0.0


def _is_rate_limit(exc: BaseException) -> bool:
    msg = f"{type(exc).__name__} {exc}".lower()
    return any(h in msg for h in _RATE_HINTS)


def _throttle() -> None:
    """Giữ khoảng cách tối thiểu giữa 2 request (một luồng, không gửi song song)."""
    global _last_request_ts
    wait = config.REQUEST_INTERVAL_SEC - (time.monotonic() - _last_request_ts)
    if wait > 0:
        _sleep(wait)
    _last_request_ts = time.monotonic()


def call_with_retry(fn, desc: str, max_retries: Optional[int] = None):
    """Gọi fn() với giới hạn tốc độ + thử lại hữu hạn, chờ tăng dần. Ném DataSourceError/RateLimitError khi hết lượt.

    Bắt cả SystemExit vì một số thư viện gọi sys.exit() khi vượt giới hạn.
    """
    max_retries = config.MAX_RETRIES if max_retries is None else max_retries
    for attempt in range(max_retries + 1):
        _throttle()
        try:
            return fn()
        except (Exception, SystemExit) as exc:  # noqa: BLE001
            rate = _is_rate_limit(exc)
            if isinstance(exc, ValueError) and not rate:
                raise DataSourceError(f"{desc}: {exc}", kind="invalid") from exc
            if attempt >= max_retries:
                cls = RateLimitError if rate else DataSourceError
                raise cls(f"{desc}: {type(exc).__name__}: {exc}") from exc
            wait = config.RATE_LIMIT_COOLDOWN_SEC if rate else config.BACKOFF_BASE_SEC * (2 ** attempt)
            logger.warning("%s lỗi (%s: %s). Thử lại %d/%d sau %.0fs", desc, type(exc).__name__, exc,
                           attempt + 1, max_retries, wait)
            _sleep(wait)


# =================================================================== lời gọi vnstock thô
def _vnstock():
    try:
        import vnstock  # noqa: F401
        return vnstock
    except ImportError as exc:
        raise DataSourceError("Chưa cài vnstock: pip install -U vnstock", kind="invalid") from exc


def _raw_symbols(source: str) -> pd.DataFrame:
    vn = _vnstock()
    lst = vn.Listing(source=source)
    if source.upper() == "KBS":
        frames = []
        for ex in config.EXCHANGES:
            df = lst.symbols_by_exchange(exchange=ex, to_df=True)
            if df is not None and len(df):
                df = df.copy()
                if "exchange" not in df.columns:
                    df["exchange"] = ex
                frames.append(df)
        return pd.concat(frames, ignore_index=True) if frames else pd.DataFrame()
    return lst.symbols_by_exchange()


def _raw_non_stock_symbols(source: str) -> set[str]:
    """ETF / trái phiếu / chứng quyền do nguồn liệt kê (chỉ KBS có). Lỗi từng phần được log và bỏ qua."""
    out: set[str] = set()
    if source.upper() != "KBS":
        return out
    lst = _vnstock().Listing(source=source)
    for name in ("all_etf", "all_bonds", "all_covered_warrant"):
        try:
            res = getattr(lst, name)()
            if isinstance(res, pd.DataFrame):
                col = next((c for c in res.columns if str(c).lower() in ("symbol", "ticker")), None)
                res = res[col] if col else pd.Series(dtype=str)
            out |= {normalize_symbol(s) for s in pd.Series(res).dropna()}
        except Exception as exc:  # noqa: BLE001
            logger.warning("Không lấy được %s từ %s: %s", name, source, exc)
    return out


def _raw_industries(source: str) -> Optional[pd.DataFrame]:
    try:
        return _vnstock().Listing(source=source).symbols_by_industries()
    except Exception as exc:  # noqa: BLE001
        logger.warning("Không lấy được ngành (symbols_by_industries) từ %s: %s", source, exc)
        return None


def _raw_price_history(symbol: str, start: str, end: str, source: str) -> pd.DataFrame:
    quote = _vnstock().Quote(symbol=symbol, source=source)
    return quote.history(start=start, end=end, interval="1D")


def _raw_company(symbol: str, source: str, method: str) -> pd.DataFrame:
    comp = _vnstock().Company(symbol=symbol, source=source)
    fn = getattr(comp, method, None)
    if fn is None:
        raise AttributeError(f"Company[{source}] không có phương thức {method}()")
    return fn()


def _raw_statement(symbol: str, source: str, statement: str, period: str) -> pd.DataFrame:
    fin = _vnstock().Finance(symbol=symbol, source=source)
    return getattr(fin, statement)(period=period)


# =================================================================== danh sách mã
def fetch_symbol_table(source: Optional[str] = None, with_industries: bool = True) -> pd.DataFrame:
    """Lấy từ nguồn và chuẩn hóa TOÀN BỘ mã (kể cả non_stock/unknown) kèm phân loại. Không ghi file."""
    sources = [source or config.PRIMARY_SOURCE] if source else [config.PRIMARY_SOURCE] + list(config.FALLBACK_SOURCES)
    last = None
    for src in sources:
        try:
            raw = call_with_retry(lambda s=src: _raw_symbols(s), f"listing[{src}]")
            if raw is None or len(raw) == 0:
                raise DataSourceError(f"listing[{src}] trả về rỗng")
            excluded = _raw_non_stock_symbols(src)
            inds = _raw_industries(src) if with_industries else None
            return normalize_symbol_list(raw, src, excluded, inds)
        except (DataSourceError, DataValidationError) as exc:
            logger.error("Nguồn danh sách %s thất bại: %s", src, exc)
            last = exc
    raise DataSourceError(f"Không lấy được danh sách mã từ bất kỳ nguồn nào: {last}")


def save_symbol_table(table: pd.DataFrame) -> None:
    config.ensure_dirs()
    stocks = table[table["instrument_class"] == "stock"]
    unclassified = table[table["instrument_class"].isin(["unknown", "non_stock"])]
    storage.atomic_write_csv(stocks.reset_index(drop=True), config.SYMBOLS_CSV)
    storage.atomic_write_csv(unclassified.reset_index(drop=True), config.SYMBOLS_UNCLASSIFIED_CSV)
    logger.info("Đã lưu %d cổ phiếu -> %s; %d mã non_stock/unknown -> %s", len(stocks), config.SYMBOLS_CSV,
                len(unclassified), config.SYMBOLS_UNCLASSIFIED_CSV)


def refresh_symbols() -> pd.DataFrame:
    table = fetch_symbol_table()
    save_symbol_table(table)
    return table[table["instrument_class"] == "stock"].reset_index(drop=True)


def symbols_file_age_days() -> Optional[float]:
    if not config.SYMBOLS_CSV.exists():
        return None
    return (time.time() - config.SYMBOLS_CSV.stat().st_mtime) / 86400


def get_stock_symbol_table(refresh: bool = False, exchanges: Optional[Iterable[str]] = None) -> pd.DataFrame:
    """Bảng cổ phiếu (symbol, organ_name, exchange, ...). Đọc file đã lưu; chưa có hoặc refresh=True thì lấy từ nguồn."""
    if refresh or not config.SYMBOLS_CSV.exists():
        df = refresh_symbols()
    else:
        df = pd.read_csv(config.SYMBOLS_CSV, encoding="utf-8-sig", dtype=str)
    if exchanges:
        want = {e.upper() for e in exchanges}
        df = df[df["exchange"].str.upper().isin(want)]
    return df.reset_index(drop=True)


def get_all_stock_symbols(refresh: bool = False, exchanges: Optional[Iterable[str]] = None) -> list[str]:
    """Danh sách mã cổ phiếu (HOSE/HNX/UPCOM) lấy tự động từ nguồn, loại ETF/TP/CW và mã chưa xác định."""
    return get_stock_symbol_table(refresh, exchanges)["symbol"].tolist()


# =================================================================== giá lịch sử
def fetch_stock_prices_with_issues(symbol: str, start_date: Optional[str] = None, end_date: Optional[str] = None,
                                   source: Optional[str] = None, use_fallback: bool = True):
    """Tải + chuẩn hóa giá một mã. Trả về (df_sạch, df_issues, nguồn_đã_dùng).

    Ném DataSourceError/RateLimitError nếu mọi nguồn đều lỗi. Trả về df rỗng nếu nguồn không có dữ liệu.
    """
    symbol = normalize_symbol(symbol)
    start = str(pd.Timestamp(start_date or config.DEFAULT_START_DATE).date())
    end = str(pd.Timestamp(end_date or config.default_end_date()).date())
    if start > end:
        raise ValueError(f"start_date {start} > end_date {end}")
    sources = [source or config.PRIMARY_SOURCE]
    if use_fallback and not source:
        sources += list(config.FALLBACK_SOURCES)
    last_exc: Optional[Exception] = None
    for i, src in enumerate(sources):
        try:
            fetched_at = utc_now_iso()
            raw = call_with_retry(lambda s=src: _raw_price_history(symbol, start, end, s), f"price[{symbol}@{src}]")
            clean, issues = standardize_price_frame(raw, symbol, src, fetched_at)
            if len(clean) == 0 and config.FALLBACK_ON_EMPTY and i < len(sources) - 1:
                continue
            return clean, issues, src
        except (DataSourceError, DataValidationError) as exc:
            last_exc = exc
            logger.warning("%s: nguồn %s thất bại (%s)%s", symbol, src, exc,
                           "; thử nguồn dự phòng" if i < len(sources) - 1 else "")
    raise last_exc if last_exc else DataSourceError(f"{symbol}: không có nguồn")


def fetch_stock_prices(symbol: str, start_date: Optional[str] = None, end_date: Optional[str] = None,
                       source: Optional[str] = None) -> pd.DataFrame:
    """Giá OHLCV đã chuẩn hóa của một mã (gọi API trực tiếp). Cột: date, symbol, open, high, low, close, volume, source, fetched_at."""
    clean, _, _ = fetch_stock_prices_with_issues(symbol, start_date, end_date, source)
    return clean


# =================================================================== hồ sơ doanh nghiệp
def fetch_company_info(symbol: str, source: Optional[str] = None) -> dict[str, pd.DataFrame]:
    """Trả về {'overview': df, 'profile': df} cho các phương thức nguồn hỗ trợ; phương thức lỗi bị bỏ qua và log."""
    symbol = normalize_symbol(symbol)
    src = source or config.PRIMARY_SOURCE
    out: dict[str, pd.DataFrame] = {}
    for method in ("overview", "profile"):
        try:
            df = call_with_retry(lambda m=method: _raw_company(symbol, src, m), f"company.{method}[{symbol}@{src}]")
        except RateLimitError:
            raise
        except DataSourceError as exc:
            logger.warning("%s: company.%s không khả dụng: %s", symbol, method, exc)
            continue
        if df is None or len(df) == 0:
            continue
        df = df.copy()
        df.insert(0, "symbol", symbol)
        df["source"] = src.upper()
        df["fetched_at"] = utc_now_iso()
        out[method] = df
    return out


def save_company_info(symbol: str, info: dict[str, pd.DataFrame]) -> list[str]:
    paths = []
    for name, df in info.items():
        p = config.PROFILES_DIR / f"{normalize_symbol(symbol)}_{name}.csv"
        storage.atomic_write_csv(df, p)
        paths.append(str(p))
    return paths


def load_company_info(symbol: str, kind: str = "overview") -> pd.DataFrame:
    p = config.PROFILES_DIR / f"{normalize_symbol(symbol)}_{kind}.csv"
    return pd.read_csv(p, encoding="utf-8-sig") if p.exists() else pd.DataFrame()


# =================================================================== báo cáo tài chính (cho TV3)
def fetch_financial_statements(symbol: str, period: str = "quarter", source: Optional[str] = None,
                               statements: Iterable[str] = STATEMENTS):
    """Tải KQKD/CĐKT/LCTT/chỉ số, đưa về dạng dài. Trả về (df_dài, danh_sách_lỗi).

    Cột: symbol, statement, period_type, period_label, item, item_id, unit, value, report_scope,
    published_date, source, fetched_at. `report_scope` và `published_date` để None vì nguồn KBS không cung cấp
    (không suy đoán). Quý và năm KHÔNG gộp: mỗi lần gọi một loại kỳ; kỳ không khớp bị loại.
    """
    if period not in ("quarter", "year"):
        raise ValueError("period phải là 'quarter' hoặc 'year'")
    symbol = normalize_symbol(symbol)
    src = source or config.PRIMARY_SOURCE
    frames, errors = [], []
    for st in statements:
        try:
            raw = call_with_retry(lambda s=st: _raw_statement(symbol, src, s, period), f"{st}[{symbol}@{src}]")
            long = statement_to_long(raw, symbol, st, period, src)
            if len(long):
                frames.append(long)
            else:
                errors.append(f"{st}: nguồn trả về rỗng")
        except RateLimitError:
            raise
        except (DataSourceError, DataValidationError) as exc:
            errors.append(f"{st}: {exc}")
            logger.warning("%s", errors[-1])
    df = pd.concat(frames, ignore_index=True) if frames else pd.DataFrame()
    return df, errors


def save_financial_statements(symbol: str, period: str, df: pd.DataFrame):
    p = config.FINANCIALS_DIR / f"{normalize_symbol(symbol)}_{period}.csv"
    storage.atomic_write_csv(df, p)
    return p


def load_financial_statements(symbol: str, period: str = "quarter", statement: Optional[str] = None) -> pd.DataFrame:
    """Đọc BCTC đã lưu (dạng dài). Dùng cho TV3, không gọi API."""
    p = config.FINANCIALS_DIR / f"{normalize_symbol(symbol)}_{period}.csv"
    if not p.exists():
        return pd.DataFrame()
    df = pd.read_csv(p, encoding="utf-8-sig")
    return df[df["statement"] == statement] if statement else df


# =================================================================== đọc dữ liệu đã thu thập (cho TV2/TV4)
def load_stock_prices(symbols: Optional[Iterable[str]] = None, start_date: Optional[str] = None,
                      end_date: Optional[str] = None) -> pd.DataFrame:
    """Đọc giá đã lưu (không gọi API). Trả về DataFrame chuẩn, sắp theo symbol, date. Mã chưa có dữ liệu được log cảnh báo."""
    if symbols is None:
        files = sorted(config.PRICES_DIR.glob("*.csv")) if config.PRICES_DIR.exists() else []
        syms = [f.stem for f in files]
    else:
        syms = [normalize_symbol(s) for s in ([symbols] if isinstance(symbols, str) else symbols)]
    frames = []
    for s in syms:
        df = storage.read_symbol_prices(s)
        if df.empty:
            logger.warning("Chưa có dữ liệu giá đã lưu cho %s", s)
            continue
        frames.append(df)
    if not frames:
        return empty_prices()
    out = pd.concat(frames, ignore_index=True)
    if start_date:
        out = out[out["date"] >= pd.Timestamp(start_date)]
    if end_date:
        out = out[out["date"] <= pd.Timestamp(end_date)]
    return out.sort_values(["symbol", "date"]).reset_index(drop=True)


def get_price_history(symbol: str, start_date: Optional[str] = None, end_date: Optional[str] = None,
                      auto_fetch: bool = False) -> pd.DataFrame:
    """Hàm tiện dụng cho TV2/TV4: ưu tiên dữ liệu đã lưu; nếu chưa có và auto_fetch=True thì tải trực tiếp."""
    df = load_stock_prices(symbol, start_date, end_date)
    if df.empty and auto_fetch:
        df = fetch_stock_prices(symbol, start_date, end_date)
    return df
