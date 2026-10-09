"""Kiểm thử TV1 (unittest, không cần mạng: nguồn dữ liệu được mock).
Chạy: python -m unittest discover -s tests -v
LƯU Ý: các test này kiểm tra LOGIC của pipeline, không chứng minh nguồn thật hoạt động (dùng --probe cho việc đó)."""
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import config  # noqa: E402
import data_cleaning as dc  # noqa: E402
import data_loader as dl  # noqa: E402
import data_quality as dq  # noqa: E402
import run_pipeline as rp  # noqa: E402
import storage  # noqa: E402


def raw_prices(n=5, start="2024-01-02", **over):
    d = pd.bdate_range(start, periods=n)
    df = pd.DataFrame({"time": d, "open": 100.0, "high": 105.0, "low": 98.0, "close": 102.0, "volume": 1000})
    for k, v in over.items():
        df[k] = v
    return df


class Base(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        config.set_data_dir(self.tmp.name)
        config.ensure_dirs()
        self._p = [mock.patch.object(dl, "_sleep", lambda s: None),
                   mock.patch.object(config, "REQUEST_INTERVAL_SEC", 0.0),
                   mock.patch.object(config, "BATCH_PAUSE_SEC", 0.0)]
        for p in self._p:
            p.start()

    def tearDown(self):
        for p in self._p:
            p.stop()
        self.tmp.cleanup()


class TestCleaning(unittest.TestCase):
    def test_valid_standardization(self):
        df, iss = dc.standardize_price_frame(raw_prices(), " fpt ", "kbs", "2025-01-01T00:00:00Z")
        self.assertEqual(list(df.columns), config.PRICE_SCHEMA)
        self.assertEqual(df["symbol"].unique().tolist(), ["FPT"])
        self.assertEqual(df["source"].iloc[0], "KBS")
        self.assertEqual(len(df), 5)
        self.assertTrue(iss.empty)
        self.assertTrue(pd.api.types.is_datetime64_any_dtype(df["date"]))

    def test_missing_required_column(self):
        with self.assertRaises(dc.DataValidationError):
            dc.standardize_price_frame(raw_prices().drop(columns=["volume"]), "FPT", "KBS")

    def test_wrong_types_and_missing(self):
        r = raw_prices()
        r["close"] = r["close"].astype(object)
        r.loc[1, "close"] = "abc"
        r.loc[2, "open"] = np.nan
        r["time"] = r["time"].astype(object)
        r.loc[3, "time"] = "không phải ngày"
        df, iss = dc.standardize_price_frame(r, "FPT", "KBS")
        self.assertEqual(len(df), 2)
        self.assertEqual(set(iss["issue"]), {"missing_price", "invalid_date"})
        self.assertFalse(df[["open", "high", "low", "close"]].isna().any().any())  # không điền giả

    def test_duplicates_keep_last(self):
        r = pd.concat([raw_prices(3), raw_prices(1, close=101.0)], ignore_index=True)
        r.loc[3, "high"] = 110
        df, iss = dc.standardize_price_frame(r, "FPT", "KBS")
        self.assertEqual(len(df), 3)
        self.assertIn("duplicate_date", set(iss["issue"]))
        self.assertEqual(df.iloc[0]["close"], 101.0)

    def test_ohlc_invalid_negative_zero(self):
        r = raw_prices(5)
        r.loc[0, "high"] = 90          # high < low
        r.loc[1, "volume"] = -5
        r.loc[2, "open"] = -1
        r.loc[3, "close"] = 0
        df, iss = dc.standardize_price_frame(r, "FPT", "KBS")
        self.assertEqual(len(df), 1)
        self.assertTrue({"ohlc_inconsistent", "negative_volume", "negative_price", "non_positive_price"} >= set(iss["issue"]) - {"missing_volume"})
        self.assertEqual(len(iss), 4)

    def test_big_move_not_removed_and_zero_volume_kept(self):
        r = raw_prices(3)
        r.loc[1, ["open", "high", "low", "close"]] = [200, 210, 195, 205]   # +100% vẫn là dữ liệu hợp lệ
        r.loc[2, "volume"] = 0
        df, iss = dc.standardize_price_frame(r, "FPT", "KBS")
        self.assertEqual(len(df), 3)
        self.assertEqual(int(df.iloc[2]["volume"]), 0)

    def test_missing_volume_kept_as_nan(self):
        r = raw_prices(3)
        r.loc[1, "volume"] = np.nan
        df, iss = dc.standardize_price_frame(r, "FPT", "KBS")
        self.assertEqual(len(df), 3)
        self.assertTrue(pd.isna(df.iloc[1]["volume"]))
        self.assertIn("missing_volume", set(iss["issue"]))

    def test_empty_input(self):
        df, iss = dc.standardize_price_frame(pd.DataFrame(), "FPT", "KBS")
        self.assertTrue(df.empty and iss.empty)

    def test_timezone_aware_dates(self):
        r = raw_prices(2)
        r["time"] = pd.to_datetime(r["time"]).dt.tz_localize("Asia/Ho_Chi_Minh")
        df, _ = dc.standardize_price_frame(r, "FPT", "KBS")
        self.assertEqual(df["date"].iloc[0], pd.Timestamp("2024-01-02"))

    def test_symbol_classification(self):
        raw = pd.DataFrame({"symbol": ["fpt", "E1VFVN30", "CFPT2301", "VNM", "fpt", "XYZ1"],
                            "organ_name": list("abcdef"), "exchange": ["HOSE", "HOSE", "HOSE", "HOSE", "HOSE", "UPCOM"],
                            "type": ["stock", "etf", "cw", None, "stock", None]})
        t = dc.normalize_symbol_list(raw, "KBS", excluded={"CFPT2301"})
        m = t.set_index("symbol")["instrument_class"].to_dict()
        self.assertEqual(len(t), 5)                       # loại trùng
        self.assertEqual(m, {"FPT": "stock", "E1VFVN30": "non_stock", "CFPT2301": "non_stock", "VNM": "stock", "XYZ1": "unknown"})
        self.assertEqual(t.set_index("symbol").loc["VNM", "classification_basis"], "pattern_inferred")

    def test_statement_long_format(self):
        raw = pd.DataFrame({"item": ["Doanh thu", "LNST"], "item_id": ["rev", "np"], "unit": ["VND", "VND"],
                            "2024-Q1": [10.0, 2.0], "2023-Q4": [9.0, 1.0], "2023": [30.0, 5.0]})
        long = dc.statement_to_long(raw, "fpt", "income_statement", "quarter", "KBS")
        self.assertEqual(set(long["period_type"]), {"quarter"})          # không trộn năm vào quý
        self.assertEqual(len(long), 4)
        self.assertTrue(long["report_scope"].isna().all() and long["published_date"].isna().all())
        with self.assertRaises(dc.DataValidationError):
            dc.statement_to_long(pd.DataFrame({"a": [1]}), "FPT", "x", "year", "KBS")


class TestRetryAndLoader(Base):
    def test_retry_then_success(self):
        calls = {"n": 0}

        def f():
            calls["n"] += 1
            if calls["n"] < 3:
                raise ConnectionError("net down")
            return "ok"
        self.assertEqual(dl.call_with_retry(f, "t"), "ok")
        self.assertEqual(calls["n"], 3)

    def test_retry_exhausted_finite(self):
        calls = {"n": 0}

        def f():
            calls["n"] += 1
            raise TimeoutError("x")
        with self.assertRaises(dl.DataSourceError):
            dl.call_with_retry(f, "t")
        self.assertEqual(calls["n"], config.MAX_RETRIES + 1)

    def test_rate_limit_and_systemexit(self):
        with self.assertRaises(dl.RateLimitError):
            dl.call_with_retry(lambda: (_ for _ in ()).throw(Exception("429 Too Many Requests")), "t", max_retries=1)

        def ex():
            raise SystemExit("Rate limit exceeded")
        with self.assertRaises(dl.RateLimitError):
            dl.call_with_retry(ex, "t", max_retries=0)

    def test_fetch_prices_fallback_and_empty(self):
        def raw(sym, s, e, src):
            if src == "KBS":
                raise ConnectionError("down")
            return raw_prices()
        with mock.patch.object(dl, "_raw_price_history", raw):
            df = dl.fetch_stock_prices("fpt", "2024-01-01", "2024-02-01")
        self.assertEqual(df["source"].iloc[0], "VCI")
        with mock.patch.object(dl, "_raw_price_history", lambda *a: pd.DataFrame()):
            self.assertTrue(dl.fetch_stock_prices("ZZZ", "2024-01-01", "2024-02-01").empty)

    def test_all_sources_fail(self):
        with mock.patch.object(dl, "_raw_price_history", lambda *a: (_ for _ in ()).throw(ConnectionError("x"))):
            with self.assertRaises(dl.DataSourceError):
                dl.fetch_stock_prices("FPT", "2024-01-01", "2024-02-01")

    def test_symbols_discovery_and_save(self):
        raw = pd.DataFrame({"symbol": ["FPT", "VNM", "E1VFVN30", "CABC2401"], "organ_name": list("abcd"),
                            "exchange": ["HOSE", "HOSE", "HOSE", "HOSE"], "type": ["stock", "stock", "etf", "cw"]})
        with mock.patch.object(dl, "_raw_symbols", lambda s: raw), \
                mock.patch.object(dl, "_raw_non_stock_symbols", lambda s: set()), \
                mock.patch.object(dl, "_raw_industries", lambda s: None):
            syms = dl.get_all_stock_symbols(refresh=True)
        self.assertEqual(sorted(syms), ["FPT", "VNM"])
        self.assertTrue(config.SYMBOLS_CSV.exists() and config.SYMBOLS_UNCLASSIFIED_CSV.exists())
        self.assertEqual(sorted(dl.get_all_stock_symbols()), ["FPT", "VNM"])   # đọc lại từ file, không gọi nguồn

    def test_financial_statements_mocked(self):
        raw = pd.DataFrame({"item": ["Doanh thu"], "item_id": ["rev"], "unit": ["VND"], "2024": [100.0], "2023": [90.0]})
        with mock.patch.object(dl, "_raw_statement", lambda sym, src, st, p: raw):
            df, errs = dl.fetch_financial_statements("FPT", "year", statements=["income_statement"])
        self.assertEqual(len(df), 2)
        self.assertEqual(errs, [])
        dl.save_financial_statements("FPT", "year", df)
        self.assertEqual(len(dl.load_financial_statements("FPT", "year", "income_statement")), 2)


class TestStorageAndPipeline(Base):
    def _run(self, fn, symbols=("AAA", "BBB", "CCC"), **kw):
        with mock.patch.object(dl, "_raw_price_history", fn):
            return rp.run_pipeline(mode="full", symbols=list(symbols), start="2024-01-01", end="2024-03-01",
                                   export_csv=True, quality=True, **kw)

    def test_rerun_no_duplicates_and_skip(self):
        calls = []

        def fn(sym, s, e, src):
            calls.append(sym)
            return raw_prices(5)
        s1 = self._run(fn)
        self.assertEqual(s1["result_counts"]["success"], 3)
        n_calls = len(calls)
        s2 = self._run(fn)
        self.assertEqual(s2["result_counts"]["skipped"], 3)
        self.assertEqual(len(calls), n_calls)                    # không gọi lại API
        df = dl.load_stock_prices()
        self.assertEqual(len(df), 15)
        self.assertFalse(df.duplicated(["symbol", "date"]).any())

    def test_incremental_update_and_forced_overlap(self):
        def fn(sym, s, e, src):
            return raw_prices(5)
        self._run(fn)
        starts = []

        def fn2(sym, s, e, src):
            starts.append(s)
            return raw_prices(8)        # nguồn trả thêm vài phiên mới + phiên cũ (chồng)
        with mock.patch.object(dl, "_raw_price_history", fn2):
            rp.run_pipeline(mode="update", symbols=["AAA"], start="2024-01-01", end="2024-04-01", quality=False)
        self.assertEqual(starts, ["2024-01-08"])   # chỉ lấy từ ngày cuối đã có
        self.assertEqual(len(dl.load_stock_prices("AAA")), 8)

    def test_continue_after_failure_and_resume(self):
        def fn(sym, s, e, src):
            if sym == "BBB":
                raise ConnectionError("lỗi nguồn")
            if sym == "CCC":
                return pd.DataFrame()
            return raw_prices(5)
        s = self._run(fn)
        c = s["result_counts"]
        self.assertEqual((c["success"], c["source_error"], c["no_data"]), (1, 1, 1))
        st = storage.all_status().set_index("symbol")["status"].to_dict()
        self.assertEqual(st, {"AAA": "success", "BBB": "source_error", "CCC": "no_data"})
        # chạy lại: BBB hồi phục, chỉ BBB được gọi
        called = []

        def fn2(sym, s, e, src):
            called.append(sym)
            return raw_prices(5)
        self._run(fn2)
        self.assertEqual(called, ["BBB"])
        self.assertEqual(storage.get_status("BBB")["status"], "success")

    def test_circuit_breaker_on_rate_limit(self):
        def fn(sym, s, e, src):
            raise Exception("429 Too Many Requests")
        with mock.patch.object(config, "MAX_RETRIES", 0):
            s = self._run(fn, symbols=[f"S{c}" for c in "ABCDEF"])
        self.assertTrue(s["aborted"])
        self.assertEqual(s["result_counts"]["rate_limited"], config.MAX_CONSECUTIVE_BLOCKS)
        self.assertEqual(s["result_counts"]["not_attempted"], 3)

    def test_all_rows_invalid_is_data_error_not_no_data(self):
        s = self._run(lambda *a: raw_prices(3, high=1.0), symbols=["AAA"])   # high < low
        self.assertEqual(storage.get_status("AAA")["status"], "data_error")

    def test_read_saved_data_and_filters(self):
        self._run(lambda *a: raw_prices(10))
        df = dl.load_stock_prices(["AAA", "BBB"], "2024-01-05", "2024-01-10")
        self.assertEqual(sorted(df["symbol"].unique()), ["AAA", "BBB"])
        self.assertTrue((df["date"] >= "2024-01-05").all() and (df["date"] <= "2024-01-10").all())
        self.assertEqual(list(df.columns)[:9], config.PRICE_SCHEMA)
        self.assertTrue(dl.load_stock_prices(["NOPE"]).empty)
        self.assertTrue(config.STOCK_PRICES_CSV.exists())
        self.assertEqual(len(pd.read_csv(config.STOCK_PRICES_CSV)), 30)

    def test_extend_history_backwards_refetches(self):
        self._run(lambda *a: raw_prices(5), symbols=["AAA"])
        st = storage.get_status("AAA")
        act, start, _ = rp.plan_price_fetch(st, "2020-01-01", "2024-03-01")
        self.assertEqual((act, start), ("fetch", "2020-01-01"))

    def test_quality_report(self):
        self._run(lambda *a: raw_prices(6))
        rep = dq.build_quality_report()
        self.assertEqual(rep["price_data"]["rows"], 18)
        self.assertEqual(rep["price_data"]["duplicate_symbol_date"], 0)
        self.assertEqual(rep["completeness"]["status_counts"]["success"], 3)
        self.assertTrue(config.QUALITY_REPORT_JSON.exists())
        gap = dq.analyze_price_frame(pd.DataFrame({"date": ["2024-01-02", "2024-02-20"], "symbol": "X", "open": 1, "high": 2, "low": 1, "close": [1, 1.1], "volume": 1}))
        self.assertEqual(gap["gaps_over_threshold"], 1)


if __name__ == "__main__":
    unittest.main()
