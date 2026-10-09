"""Lưu trữ: CSV theo từng mã (ghi nguyên tử, gộp không trùng) + SQLite lưu trạng thái thu thập."""
from __future__ import annotations

import logging
import os
import sqlite3
from contextlib import contextmanager
from datetime import datetime, timezone
from typing import Optional

import pandas as pd

import config
from data_cleaning import ISSUE_COLUMNS, normalize_symbol

logger = logging.getLogger(__name__)


def atomic_write_csv(df: pd.DataFrame, path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    df.to_csv(tmp, index=False, encoding="utf-8-sig")
    os.replace(tmp, path)


# ------------------------------------------------------------------ giá
def price_path(symbol: str):
    return config.PRICES_DIR / f"{normalize_symbol(symbol)}.csv"


def read_symbol_prices(symbol: str) -> pd.DataFrame:
    p = price_path(symbol)
    if not p.exists():
        return pd.DataFrame(columns=config.PRICE_SCHEMA)
    df = pd.read_csv(p, encoding="utf-8-sig", dtype={"symbol": str})
    df["date"] = pd.to_datetime(df["date"], errors="coerce")
    return df


def save_symbol_prices(symbol: str, new: pd.DataFrame) -> dict:
    """Gộp dữ liệu mới vào file của mã; trùng (symbol,date) -> bản mới thay bản cũ. Idempotent."""
    old = read_symbol_prices(symbol)
    if len(old):
        comb = pd.concat([old, new], ignore_index=True) if len(new) else old
    else:
        comb = new.copy()
    comb["date"] = pd.to_datetime(comb["date"])
    comb = (comb.drop_duplicates(subset=["symbol", "date"], keep="last")
                .sort_values("date").reset_index(drop=True))
    out = comb.copy()
    out["date"] = out["date"].dt.strftime("%Y-%m-%d")
    atomic_write_csv(out, price_path(symbol))
    return {"rows": len(comb),
            "first_date": comb["date"].min().strftime("%Y-%m-%d") if len(comb) else None,
            "last_date": comb["date"].max().strftime("%Y-%m-%d") if len(comb) else None}


def save_issues(symbol: str, issues: pd.DataFrame) -> None:
    if issues is None or len(issues) == 0:
        return
    p = config.QUALITY_DIR / "issues" / f"{normalize_symbol(symbol)}.csv"
    if p.exists():
        issues = pd.concat([pd.read_csv(p, encoding="utf-8-sig"), issues], ignore_index=True)
    issues = issues.drop_duplicates(subset=["symbol", "date", "issue"], keep="last")
    atomic_write_csv(issues[ISSUE_COLUMNS], p)


def export_merged_prices(path=None) -> dict:
    """Gộp mọi file theo mã thành một stock_prices.csv (ghi từng phần, không nạp toàn bộ vào RAM)."""
    path = path or config.STOCK_PRICES_CSV
    tmp = path.with_suffix(".csv.tmp")
    files = sorted(config.PRICES_DIR.glob("*.csv"))
    rows, first = 0, True
    with open(tmp, "w", encoding="utf-8-sig", newline="") as fh:
        for f in files:
            df = pd.read_csv(f, encoding="utf-8-sig", dtype={"symbol": str})
            if df.empty:
                continue
            df.to_csv(fh, index=False, header=first)
            first = False
            rows += len(df)
    os.replace(tmp, path)
    return {"path": str(path), "symbols": len(files), "rows": rows}


# ------------------------------------------------------------------ trạng thái (SQLite)
_DDL = """
CREATE TABLE IF NOT EXISTS collection_status (
    symbol TEXT NOT NULL, dataset TEXT NOT NULL,
    exchange TEXT, status TEXT NOT NULL, rows INTEGER, first_date TEXT, last_date TEXT,
    requested_start TEXT, fetched_through TEXT, attempts INTEGER DEFAULT 0,
    last_error TEXT, source TEXT, updated_at TEXT,
    PRIMARY KEY (symbol, dataset)
)"""
STATUS_COLUMNS = ["symbol", "dataset", "exchange", "status", "rows", "first_date", "last_date",
                  "requested_start", "fetched_through", "attempts", "last_error", "source", "updated_at"]


@contextmanager
def _conn():
    config.DATA_DIR.mkdir(parents=True, exist_ok=True)
    c = sqlite3.connect(config.STATE_DB)
    c.row_factory = sqlite3.Row
    try:
        c.execute(_DDL)
        yield c
        c.commit()
    finally:
        c.close()


def get_status(symbol: str, dataset: str = "prices") -> Optional[dict]:
    with _conn() as c:
        r = c.execute("SELECT * FROM collection_status WHERE symbol=? AND dataset=?",
                      (normalize_symbol(symbol), dataset)).fetchone()
        return dict(r) if r else None


def set_status(symbol: str, dataset: str = "prices", **fields) -> None:
    symbol = normalize_symbol(symbol)
    fields["updated_at"] = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    cols = [k for k in fields if k in STATUS_COLUMNS]
    with _conn() as c:
        exists = c.execute("SELECT 1 FROM collection_status WHERE symbol=? AND dataset=?", (symbol, dataset)).fetchone()
        if exists:
            c.execute(f"UPDATE collection_status SET {', '.join(k + '=?' for k in cols)} WHERE symbol=? AND dataset=?",
                      [fields[k] for k in cols] + [symbol, dataset])
        else:
            c.execute(f"INSERT INTO collection_status (symbol, dataset, {', '.join(cols)}) "
                      f"VALUES (?, ?, {', '.join('?' for _ in cols)})", [symbol, dataset] + [fields[k] for k in cols])


def all_status() -> pd.DataFrame:
    with _conn() as c:
        rows = c.execute("SELECT * FROM collection_status ORDER BY dataset, symbol").fetchall()
    return pd.DataFrame([dict(r) for r in rows], columns=STATUS_COLUMNS)


def export_status_csv() -> pd.DataFrame:
    df = all_status()
    atomic_write_csv(df, config.COLLECTION_STATUS_CSV)
    return df
