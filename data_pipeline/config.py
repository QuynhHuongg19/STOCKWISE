"""Cấu hình TV1 – Thu thập & chuẩn hóa dữ liệu cổ phiếu Việt Nam.

Mọi đường dẫn đều tính lại được bằng set_data_dir() (dùng cho kiểm thử).
Không lưu token/mật khẩu ở đây: nếu có API key (vd. vnstock), đặt qua biến môi trường.
"""
from __future__ import annotations

import os
from datetime import date
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent

# ----------------------------------------------------------------- nguồn dữ liệu
PRIMARY_SOURCE = os.getenv("TV1_SOURCE", "KBS")          # nguồn chính (vnstock khuyến nghị cho độ ổn định)
FALLBACK_SOURCES = ["VCI"]                                # chỉ dùng khi nguồn chính LỖI (không dùng khi rỗng)
FALLBACK_ON_EMPTY = False                                 # True: thử nguồn dự phòng cả khi nguồn chính trả rỗng
EXCHANGES = ["HOSE", "HNX", "UPCOM"]

# ----------------------------------------------------------------- thời gian
DEFAULT_START_DATE = "2015-01-01"


def default_end_date() -> str:
    return date.today().isoformat()


# ----------------------------------------------------------------- giới hạn truy cập (CHƯA kiểm chứng giới hạn thật -> để bảo thủ)
REQUEST_INTERVAL_SEC = float(os.getenv("TV1_INTERVAL", "3.1"))  # ~19 request/phút
MAX_RETRIES = 3                  # số lần thử lại cho lỗi tạm thời
BACKOFF_BASE_SEC = 2.0           # chờ 2s, 4s, 8s...
RATE_LIMIT_COOLDOWN_SEC = 65.0   # chờ khi bị giới hạn tốc độ
MAX_CONSECUTIVE_BLOCKS = 3       # N mã liên tiếp bị chặn -> dừng pipeline, giữ trạng thái để chạy tiếp
BATCH_SIZE = 100                 # sau mỗi lô: ghi trạng thái/log tổng kết + nghỉ
BATCH_PAUSE_SEC = 5.0

# ----------------------------------------------------------------- làm mới
SYMBOL_REFRESH_DAYS = 7
NO_DATA_RECHECK_DAYS = 7
PROFILE_REFRESH_DAYS = 30
FINANCIAL_REFRESH_DAYS = 7

# ----------------------------------------------------------------- chuẩn hóa / kiểm tra
# Hệ số nhân giá về VND. Mặc định 1.0 = giữ nguyên đơn vị nguồn trả về.
# Đơn vị thật của nguồn phải được kiểm chứng bằng `python run_pipeline.py --probe` (xem README).
PRICE_MULTIPLIER = float(os.getenv("TV1_PRICE_MULTIPLIER", "1.0"))
PRICE_UNIT_NOTE = "As returned by source (unverified; check with --probe)"
GAP_DAYS_THRESHOLD = 12          # khoảng trống > 12 ngày lịch giữa 2 phiên liên tiếp -> báo để rà soát
OUTLIER_ABS_RETURN = 0.5         # |lợi suất ngày| > 50% -> đánh dấu rà soát (KHÔNG xóa)
PRICE_SCHEMA = ["date", "symbol", "open", "high", "low", "close", "volume", "source", "fetched_at"]

# ----------------------------------------------------------------- đường dẫn
DATA_DIR = SYMBOLS_CSV = SYMBOLS_UNCLASSIFIED_CSV = PRICES_DIR = STOCK_PRICES_CSV = None
PROFILES_DIR = FINANCIALS_DIR = LOGS_DIR = QUALITY_DIR = QUALITY_REPORT_JSON = None
STATE_DB = COLLECTION_STATUS_CSV = RUN_REPORTS_DIR = None


def set_data_dir(path) -> Path:
    g = globals()
    d = Path(path)
    g["DATA_DIR"] = d
    g["SYMBOLS_CSV"] = d / "symbols.csv"
    g["SYMBOLS_UNCLASSIFIED_CSV"] = d / "symbols_unclassified.csv"
    g["PRICES_DIR"] = d / "prices"
    g["STOCK_PRICES_CSV"] = d / "stock_prices.csv"
    g["PROFILES_DIR"] = d / "company_profiles"
    g["FINANCIALS_DIR"] = d / "financial_statements"
    g["LOGS_DIR"] = d / "logs"
    g["QUALITY_DIR"] = d / "quality"
    g["QUALITY_REPORT_JSON"] = d / "data_quality_report.json"
    g["STATE_DB"] = d / "state.sqlite"
    g["COLLECTION_STATUS_CSV"] = d / "collection_status.csv"
    g["RUN_REPORTS_DIR"] = d / "run_reports"
    return d


def ensure_dirs() -> None:
    for p in (DATA_DIR, PRICES_DIR, PROFILES_DIR, FINANCIALS_DIR, LOGS_DIR, QUALITY_DIR, RUN_REPORTS_DIR):
        p.mkdir(parents=True, exist_ok=True)


set_data_dir(os.getenv("TV1_DATA_DIR", BASE_DIR / "data"))
