"""Ví dụ tích hợp TV1 -> TV2 / TV3 / TV4 (đọc dữ liệu đã lưu, KHÔNG gọi API).
Chạy sau khi pipeline đã thu thập dữ liệu:  python examples_integration.py FPT
"""
import sys

import pandas as pd

from data_loader import (get_all_stock_symbols, get_price_history, load_company_info,
                         load_financial_statements, load_stock_prices)


def tv2_technical(symbol: str) -> pd.DataFrame:
    """TV2: lấy OHLCV để tính SMA/EMA/RSI/MACD/Bollinger."""
    df = get_price_history(symbol, "2023-01-01").set_index("date")
    df["sma20"] = df["close"].rolling(20).mean()          # ví dụ nhỏ; TV2 tự triển khai đầy đủ
    return df


def tv3_fundamental(symbol: str) -> pd.DataFrame:
    """TV3: BCTC dạng dài (tách quý/năm, có item, unit, source, fetched_at). report_scope/published_date có thể trống."""
    q = load_financial_statements(symbol, "quarter", "income_statement")
    if q.empty:
        print(f"{symbol}: chưa có BCTC đã lưu (chạy với --with-financials hoặc nguồn không hỗ trợ)")
        return q
    return q.pivot_table(index="item", columns="period_label", values="value", aggfunc="first")


def tv4_scoring(symbols: list[str]) -> pd.DataFrame:
    """TV4: nạp nhiều mã một lần để tính biến động/maximum drawdown/thanh khoản."""
    px = load_stock_prices(symbols, start_date="2023-01-01")
    out = {}
    for s, g in px.groupby("symbol"):
        r = g["close"].pct_change().dropna()
        peak = g["close"].cummax()
        out[s] = {"annual_vol": r.std() * (252 ** 0.5), "max_drawdown": (g["close"] / peak - 1).min(),
                  "avg_volume_20d": g["volume"].tail(20).mean()}
    return pd.DataFrame(out).T


if __name__ == "__main__":
    sym = sys.argv[1] if len(sys.argv) > 1 else "FPT"
    print("Số cổ phiếu trong symbols.csv:", len(get_all_stock_symbols()))
    print(tv2_technical(sym).tail())
    print(tv3_fundamental(sym).head())
    print(load_company_info(sym, "overview").head())
    print(tv4_scoring([sym]))
