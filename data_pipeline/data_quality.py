"""Thống kê chất lượng dữ liệu: thiếu, trùng, sai, khoảng trống, bất thường và mức độ hoàn thành."""
from __future__ import annotations

import json
import logging
from datetime import datetime, timezone

import numpy as np
import pandas as pd

import config
import storage

logger = logging.getLogger(__name__)


def analyze_price_frame(df: pd.DataFrame) -> dict:
    """Kiểm tra một bảng giá (đã đọc từ file). Chỉ THỐNG KÊ, không sửa/xóa dữ liệu."""
    if df is None or df.empty:
        return {"rows": 0}
    d = df.copy()
    d["date"] = pd.to_datetime(d["date"], errors="coerce")
    px = d[["open", "high", "low", "close"]].apply(pd.to_numeric, errors="coerce")
    vol = pd.to_numeric(d["volume"], errors="coerce")
    d = d.sort_values("date")
    gaps = d["date"].diff().dt.days
    ret = pd.to_numeric(d["close"], errors="coerce").pct_change()
    big_gap = gaps[gaps > config.GAP_DAYS_THRESHOLD]
    return {
        "rows": int(len(d)),
        "first_date": d["date"].min().strftime("%Y-%m-%d") if d["date"].notna().any() else None,
        "last_date": d["date"].max().strftime("%Y-%m-%d") if d["date"].notna().any() else None,
        "invalid_dates": int(d["date"].isna().sum()),
        "duplicate_symbol_date": int(d.duplicated(subset=["symbol", "date"]).sum()),
        "missing_price_cells": int(px.isna().sum().sum()),
        "missing_volume": int(vol.isna().sum()),
        "negative_price_or_volume": int(((px < 0).any(axis=1) | (vol < 0)).sum()),
        "ohlc_inconsistent": int(((px["high"] < px[["open", "close", "low"]].max(axis=1)) |
                                  (px["low"] > px[["open", "close", "high"]].min(axis=1))).sum()),
        "zero_volume_days": int((vol == 0).sum()),
        "gaps_over_threshold": int(len(big_gap)),
        "largest_gap_days": int(gaps.max()) if gaps.notna().any() else 0,
        "outlier_return_days": int((ret.abs() > config.OUTLIER_ABS_RETURN).sum()),
    }


def build_quality_report(write: bool = True) -> dict:
    """Tổng hợp chất lượng toàn bộ dữ liệu đã lưu + mức hoàn thành theo trạng thái thu thập."""
    status = storage.all_status()
    prices_status = status[status["dataset"] == "prices"] if len(status) else status
    per_symbol, totals = {}, {"rows": 0, "duplicate_symbol_date": 0, "ohlc_inconsistent": 0,
                              "negative_price_or_volume": 0, "missing_volume": 0, "gaps_over_threshold": 0,
                              "outlier_return_days": 0}
    first_dates, last_dates = [], []
    files = sorted(config.PRICES_DIR.glob("*.csv")) if config.PRICES_DIR.exists() else []
    for f in files:
        df = pd.read_csv(f, encoding="utf-8-sig", dtype={"symbol": str})
        r = analyze_price_frame(df)
        per_symbol[f.stem] = r
        for k in totals:
            totals[k] += r.get(k, 0)
        if r.get("first_date"):
            first_dates.append(r["first_date"])
            last_dates.append(r["last_date"])

    counts = prices_status["status"].value_counts().to_dict() if len(prices_status) else {}
    symbols_detected = None
    if config.SYMBOLS_CSV.exists():
        symbols_detected = int(len(pd.read_csv(config.SYMBOLS_CSV, encoding="utf-8-sig")))
    issues_files = list((config.QUALITY_DIR / "issues").glob("*.csv")) if (config.QUALITY_DIR / "issues").exists() else []
    quarantined = {}
    for f in issues_files:
        iss = pd.read_csv(f, encoding="utf-8-sig")
        for k, v in iss["issue"].value_counts().items():
            quarantined[k] = quarantined.get(k, 0) + int(v)

    report = {
        "generated_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "completeness": {
            "symbols_detected": symbols_detected,
            "symbols_with_price_files": len(files),
            "status_counts": {k: int(v) for k, v in counts.items()},
            "success_ratio_of_detected": (round(counts.get("success", 0) / symbols_detected, 4)
                                          if symbols_detected else None),
        },
        "price_data": {**totals, "earliest_date": min(first_dates) if first_dates else None,
                       "latest_date": max(last_dates) if last_dates else None},
        "rows_rejected_by_cleaning": quarantined,
        "notes": [
            "Khoảng trống >%d ngày lịch chỉ để rà soát: có thể là nghỉ Tết/tạm ngừng giao dịch, không tự kết luận lỗi." % config.GAP_DAYS_THRESHOLD,
            "Ngày không giao dịch, mã chưa niêm yết và lỗi truy xuất KHÔNG thể tách hoàn toàn nếu nguồn không cung cấp lịch giao dịch/ngày niêm yết; "
            "trạng thái no_data/source_error trong collection_status.csv là thông tin phân biệt tốt nhất hiện có.",
            "Biến động |lợi suất ngày|>%d%% chỉ được đánh dấu, không bị xóa." % int(config.OUTLIER_ABS_RETURN * 100),
            "Chưa kiểm chứng giá có điều chỉnh hay không (xem README, mục Giới hạn).",
        ],
        "per_symbol": per_symbol,
    }
    if write:
        config.QUALITY_REPORT_JSON.parent.mkdir(parents=True, exist_ok=True)
        with open(config.QUALITY_REPORT_JSON, "w", encoding="utf-8") as fh:
            json.dump(report, fh, ensure_ascii=False, indent=2, default=str)
    return report
