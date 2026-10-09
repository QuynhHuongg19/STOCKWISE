"""TV1 – chạy pipeline thu thập toàn thị trường.

Ví dụ:
  python run_pipeline.py --probe                      # kiểm chứng API/đơn vị giá trên vài mã thật (CHẠY ĐẦU TIÊN)
  python run_pipeline.py --mode full                  # tải lịch sử toàn thị trường (có thể dừng/chạy tiếp)
  python run_pipeline.py --mode update                # cập nhật hằng ngày
  python run_pipeline.py --symbols FPT,VNM --with-profiles --with-financials
"""
from __future__ import annotations

import argparse
import json
import logging
import sys
from datetime import datetime, timedelta, timezone
from typing import Iterable, Optional

import pandas as pd

import config
import data_loader as dl
import data_quality
import storage
from data_cleaning import normalize_symbol

logger = logging.getLogger("tv1.pipeline")

SKIP, FETCH = "skip", "fetch"


def setup_logging(verbose: bool = False) -> None:
    config.ensure_dirs()
    fmt = logging.Formatter("%(asctime)s %(levelname)s %(name)s: %(message)s")
    root = logging.getLogger()
    root.setLevel(logging.DEBUG if verbose else logging.INFO)
    for h in list(root.handlers):
        root.removeHandler(h)
    fh = logging.FileHandler(config.LOGS_DIR / f"tv1_{datetime.now():%Y%m%d}.log", encoding="utf-8")
    sh = logging.StreamHandler(sys.stdout)
    for h in (fh, sh):
        h.setFormatter(fmt)
        root.addHandler(h)


def _age_days(ts: Optional[str]) -> float:
    if not ts:
        return 1e9
    return (datetime.now(timezone.utc) - datetime.strptime(ts, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc)).total_seconds() / 86400


def plan_price_fetch(state: Optional[dict], start: str, end: str, force: bool = False) -> tuple[str, Optional[str], str]:
    """Quyết định tải hay bỏ qua một mã. Trả về (hành_động, ngày_bắt_đầu, lý_do). Hàm thuần, dễ kiểm thử."""
    if force or state is None:
        return FETCH, start, "force" if force else "mã mới"
    st = state.get("status")
    if st == "success":
        # người dùng lùi ngày bắt đầu về sớm hơn lần đã tải -> tải lại từ đầu
        if state.get("requested_start") and start < state["requested_start"]:
            return FETCH, start, "mở rộng lịch sử về trước"
        if (state.get("fetched_through") or "") >= end:
            return SKIP, None, "đã cập nhật đến ngày kết thúc"
        last = state.get("last_date")
        return FETCH, max(start, last) if last else start, "cập nhật phần mới"   # chồng 1 phiên để bắt hiệu chỉnh
    if st == "no_data":
        if _age_days(state.get("updated_at")) < config.NO_DATA_RECHECK_DAYS and (state.get("fetched_through") or "") >= end:
            return SKIP, None, "no_data đã kiểm tra gần đây"
        return FETCH, start, "kiểm tra lại no_data"
    last = state.get("last_date")                     # source_error / rate_limited / data_error / pending
    return FETCH, (max(start, last) if last else start), f"thử lại sau trạng thái {st}"


def collect_prices_for_symbol(symbol: str, exchange: Optional[str], start: str, end: str, force: bool = False) -> str:
    """Tải + lưu một mã, cập nhật trạng thái. Trả về trạng thái cuối. RateLimitError được ném lên để pipeline xử lý."""
    state = storage.get_status(symbol, "prices")
    action, fstart, why = plan_price_fetch(state, start, end, force)
    if action == SKIP:
        logger.info("%s: bỏ qua (%s)", symbol, why)
        return "skipped"
    attempts = (state or {}).get("attempts", 0) or 0
    try:
        clean, issues, src = dl.fetch_stock_prices_with_issues(symbol, fstart, end)
    except dl.RateLimitError as exc:
        storage.set_status(symbol, "prices", exchange=exchange, status="rate_limited", attempts=attempts + 1, last_error=str(exc)[:500])
        raise
    except Exception as exc:  # noqa: BLE001  (không bỏ qua lỗi: log + ghi trạng thái, rồi đi tiếp mã khác)
        kind = "data_error" if exc.__class__.__name__ == "DataValidationError" else "source_error"
        logger.error("%s: %s -> %s", symbol, kind, exc)
        storage.set_status(symbol, "prices", exchange=exchange, status=kind, attempts=attempts + 1, last_error=str(exc)[:500])
        return kind
    storage.save_issues(symbol, issues)
    keep_start = (state or {}).get("requested_start") or start
    req_start = min(keep_start, start)
    if len(clean) == 0:
        raw_had_rows = len(issues) > 0
        if raw_had_rows:    # nguồn có dữ liệu nhưng toàn bộ bị loại do sai -> lỗi dữ liệu, KHÔNG gọi là "không có dữ liệu"
            storage.set_status(symbol, "prices", exchange=exchange, status="data_error", attempts=attempts + 1,
                               last_error=f"{len(issues)} dòng bị loại hết (xem quality/issues/{symbol}.csv)", source=src)
            return "data_error"
        existing = storage.read_symbol_prices(symbol)
        status = "success" if len(existing) else "no_data"
        storage.set_status(symbol, "prices", exchange=exchange, status=status, rows=len(existing),
                           first_date=existing["date"].min().strftime("%Y-%m-%d") if len(existing) else None,
                           last_date=existing["date"].max().strftime("%Y-%m-%d") if len(existing) else None,
                           requested_start=req_start, fetched_through=end, attempts=0, last_error=None, source=src)
        return status
    info = storage.save_symbol_prices(symbol, clean)
    storage.set_status(symbol, "prices", exchange=exchange, status="success", rows=info["rows"], first_date=info["first_date"],
                       last_date=info["last_date"], requested_start=req_start, fetched_through=end, attempts=0,
                       last_error=None, source=src)
    logger.info("%s: +%d dòng (tổng %d, %s → %s) nguồn %s", symbol, len(clean), info["rows"], info["first_date"], info["last_date"], src)
    return "success"


def _should_refresh(sym: str, dataset: str, max_age_days: float) -> bool:
    s = storage.get_status(sym, dataset)
    return not (s and s.get("status") == "success" and _age_days(s.get("updated_at")) < max_age_days)


def collect_profile(sym: str, exchange: Optional[str]) -> str:
    if not _should_refresh(sym, "profile", config.PROFILE_REFRESH_DAYS):
        return "skipped"
    try:
        info = dl.fetch_company_info(sym)
    except dl.RateLimitError:
        raise
    except Exception as exc:  # noqa: BLE001
        storage.set_status(sym, "profile", exchange=exchange, status="source_error", last_error=str(exc)[:500])
        return "source_error"
    if not info:
        storage.set_status(sym, "profile", exchange=exchange, status="no_data", last_error="overview/profile đều rỗng hoặc không hỗ trợ")
        return "no_data"
    dl.save_company_info(sym, info)
    storage.set_status(sym, "profile", exchange=exchange, status="success", rows=sum(len(v) for v in info.values()), last_error=None)
    return "success"


def collect_financials(sym: str, exchange: Optional[str], periods=("quarter", "year")) -> str:
    if not _should_refresh(sym, "financials", config.FINANCIAL_REFRESH_DAYS):
        return "skipped"
    total, errs = 0, []
    try:
        for p in periods:
            df, e = dl.fetch_financial_statements(sym, p)
            errs += [f"{p}/{x}" for x in e]
            if len(df):
                dl.save_financial_statements(sym, p, df)
                total += len(df)
    except dl.RateLimitError:
        raise
    except Exception as exc:  # noqa: BLE001
        storage.set_status(sym, "financials", exchange=exchange, status="source_error", last_error=str(exc)[:500])
        return "source_error"
    status = "success" if total else "no_data"
    storage.set_status(sym, "financials", exchange=exchange, status=status, rows=total, last_error="; ".join(errs)[:500] or None)
    return status


def run_pipeline(mode: str = "update", symbols: Optional[Iterable[str]] = None, start: Optional[str] = None,
                 end: Optional[str] = None, exchanges: Optional[Iterable[str]] = None, limit: Optional[int] = None,
                 refresh_symbol_list: bool = False, force: bool = False, with_profiles: bool = False,
                 with_financials: bool = False, export_csv: bool = True, quality: bool = True,
                 batch_size: Optional[int] = None) -> dict:
    config.ensure_dirs()
    started = datetime.now(timezone.utc)
    start = str(pd.Timestamp(start or config.DEFAULT_START_DATE).date())
    end = str(pd.Timestamp(end or config.default_end_date()).date())
    batch_size = batch_size or config.BATCH_SIZE
    summary = {"mode": mode, "start": start, "end": end, "started_at": started.strftime("%Y-%m-%dT%H:%M:%SZ"),
               "aborted": False, "abort_reason": None, "symbol_source": None}

    # 1) danh sách mã
    if symbols:
        wanted = [normalize_symbol(s) for s in symbols]
        table = pd.DataFrame({"symbol": list(dict.fromkeys(wanted))})
        table["exchange"] = None
        if config.SYMBOLS_CSV.exists():
            known = pd.read_csv(config.SYMBOLS_CSV, encoding="utf-8-sig", dtype=str)[["symbol", "exchange"]]
            table = table[["symbol"]].merge(known, on="symbol", how="left")
        summary["symbol_source"] = "manual --symbols (CHỈ để thử nghiệm; không phải toàn thị trường)"
    else:
        age = dl.symbols_file_age_days()
        need = refresh_symbol_list or age is None or (mode == "update" and age > config.SYMBOL_REFRESH_DAYS)
        try:
            table = dl.get_stock_symbol_table(refresh=need, exchanges=exchanges)
            summary["symbol_source"] = "auto-detected from source" if need else "symbols.csv đã lưu"
        except dl.DataSourceError as exc:
            if config.SYMBOLS_CSV.exists():     # nguồn lỗi nhưng còn danh sách cũ -> dùng tiếp, ghi rõ
                logger.error("Không làm mới được danh sách mã (%s); dùng symbols.csv cũ", exc)
                table = dl.get_stock_symbol_table(refresh=False, exchanges=exchanges)
                summary["symbol_source"] = "symbols.csv cũ (làm mới thất bại)"
            else:
                raise
    if limit:
        table = table.head(limit)
    summary["symbols_detected"] = int(len(table))
    logger.info("Bắt đầu mode=%s, %d mã, %s → %s", mode, len(table), start, end)

    # 2) vòng lặp thu thập
    result = {"success": 0, "no_data": 0, "source_error": 0, "data_error": 0, "rate_limited": 0, "skipped": 0, "not_attempted": 0}
    consecutive_blocks = 0
    rows = list(zip(table["symbol"], table["exchange"] if "exchange" in table else [None] * len(table)))
    for i, (sym, ex) in enumerate(rows, 1):
        ex = ex if isinstance(ex, str) else None
        try:
            r = collect_prices_for_symbol(sym, ex, start, end, force)
            consecutive_blocks = 0
            if with_profiles:
                collect_profile(sym, ex)
            if with_financials:
                collect_financials(sym, ex)
            result[r] = result.get(r, 0) + 1
        except dl.RateLimitError as exc:
            result["rate_limited"] += 1
            consecutive_blocks += 1
            logger.error("%s: bị giới hạn truy cập (%d liên tiếp): %s", sym, consecutive_blocks, exc)
            if consecutive_blocks >= config.MAX_CONSECUTIVE_BLOCKS:
                summary["aborted"] = True
                summary["abort_reason"] = (f"Nguồn từ chối/giới hạn {consecutive_blocks} mã liên tiếp tại {sym}. "
                                           "Dừng để tránh bị chặn; chạy lại sau ít phút, pipeline sẽ tiếp tục từ chỗ dừng.")
                result["not_attempted"] = len(rows) - i
                logger.error(summary["abort_reason"])
                break
        if i % batch_size == 0:
            storage.export_status_csv()
            logger.info("--- Hết lô %d/%d mã: %s", i, len(rows), result)
            if i < len(rows):
                dl._sleep(config.BATCH_PAUSE_SEC)

    # 3) tổng hợp
    status_df = storage.export_status_csv()
    summary["result_counts"] = result
    if export_csv:
        summary["export"] = storage.export_merged_prices()
    if quality:
        q = data_quality.build_quality_report()
        summary["quality_headline"] = {"rows": q["price_data"]["rows"], "earliest": q["price_data"]["earliest_date"],
                                       "latest": q["price_data"]["latest_date"], "completeness": q["completeness"]}
    summary["finished_at"] = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    rp = config.RUN_REPORTS_DIR / f"run_{started:%Y%m%dT%H%M%SZ}.json"
    rp.write_text(json.dumps(summary, ensure_ascii=False, indent=2, default=str), encoding="utf-8")
    summary["report_path"] = str(rp)
    return summary


def probe(symbols=("FPT", "VNM", "ACB")) -> int:
    """Kiểm chứng API thật: danh sách mã + giá vài mã; in cột/kiểu/mẫu để đối chiếu đơn vị giá."""
    config.ensure_dirs()
    print("== Listing ==")
    try:
        tbl = dl.fetch_symbol_table()
        print(tbl["instrument_class"].value_counts().to_string())
        print(tbl.groupby(["exchange", "instrument_class"]).size().to_string())
        print("Giá trị type thô của nguồn:", tbl["source_type_raw"].astype(str).value_counts().head(10).to_dict())
        print("Cột:", list(tbl.columns))
    except Exception as exc:  # noqa: BLE001
        print("LISTING LỖI:", exc)
        return 1
    print("\n== Giá (2024-01-01 → 2024-01-31) ==")
    start, end = "2024-01-01", "2024-01-31"
    for s in symbols:
        try:
            raw = dl.call_with_retry(lambda s=s: dl._raw_price_history(s, start, end, config.PRIMARY_SOURCE), f"probe {s}")
            print(f"\n{s}: cột thô = {list(raw.columns)}; dtypes = {raw.dtypes.astype(str).to_dict()}; {len(raw)} dòng")
            print(raw.head(3).to_string())
            clean, issues, _ = dl.fetch_stock_prices_with_issues(s, start, end)
            print(f"-> sau chuẩn hóa: {len(clean)} dòng, {len(issues)} vấn đề; close mẫu = {clean['close'].head(3).tolist()}")
        except Exception as exc:  # noqa: BLE001
            print(f"{s}: LỖI {exc}")
    print("\nĐối chiếu đơn vị: so sánh 'close' với giá thực tế trên bảng giá (vd. FPT ~ 100.000đ). "
          "Nếu close ~ 100 -> nguồn dùng nghìn đồng; đặt TV1_PRICE_MULTIPLIER=1000 nếu muốn quy về VND.")
    return 0


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="TV1 data pipeline")
    ap.add_argument("--mode", choices=["full", "update"], default="update")
    ap.add_argument("--symbols", help="Danh sách mã cách nhau bởi dấu phẩy (chỉ để thử nghiệm)")
    ap.add_argument("--exchanges", help="HOSE,HNX,UPCOM (mặc định: cả ba)")
    ap.add_argument("--start"), ap.add_argument("--end")
    ap.add_argument("--limit", type=int, help="Chỉ chạy N mã đầu (thử nghiệm)")
    ap.add_argument("--refresh-symbols", action="store_true")
    ap.add_argument("--force", action="store_true", help="Tải lại từ --start bất kể trạng thái")
    ap.add_argument("--with-profiles", action="store_true")
    ap.add_argument("--with-financials", action="store_true")
    ap.add_argument("--no-export", action="store_true", help="Không gộp stock_prices.csv")
    ap.add_argument("--data-dir")
    ap.add_argument("--probe", action="store_true")
    ap.add_argument("-v", "--verbose", action="store_true")
    a = ap.parse_args(argv)
    if a.data_dir:
        config.set_data_dir(a.data_dir)
    setup_logging(a.verbose)
    if a.probe:
        return probe()
    s = run_pipeline(mode=a.mode, symbols=a.symbols.split(",") if a.symbols else None, start=a.start, end=a.end,
                     exchanges=a.exchanges.split(",") if a.exchanges else None, limit=a.limit,
                     refresh_symbol_list=a.refresh_symbols, force=a.force, with_profiles=a.with_profiles,
                     with_financials=a.with_financials, export_csv=not a.no_export)
    print(json.dumps({k: v for k, v in s.items() if k != "quality_headline"}, ensure_ascii=False, indent=2, default=str))
    return 2 if s["aborted"] else 0


if __name__ == "__main__":
    sys.exit(main())
