"""Refresh existing price CSV files using the project's authorized Vnstock access.
Runs separately from the public Streamlit app. Fails visibly if no API access.
"""
from datetime import date, timedelta
from pathlib import Path
import os
import sys
import time
import pandas as pd
from vnstock.api.quote import Quote

BASE = Path(__file__).resolve().parents[1]
PRICE_DIR = BASE / "data_pipeline" / "data" / "prices"
SYMBOLS = [s.strip().upper() for s in os.getenv("STOCKWISE_SYMBOLS", "BAB,FPT,VCB,TCB,MBB,ACB,HPG,VNM").split(",") if s.strip()]
COLUMNS = ["date", "symbol", "open", "high", "low", "close", "volume"]

def refresh(symbol):
    quote = Quote(symbol=symbol, source="VCI")
    raw = quote.history(
        start=(date.today()-timedelta(days=90)).isoformat(),
        end=(date.today()+timedelta(days=1)).isoformat(),
        interval="1D",
    )
    if raw is None or raw.empty:
        raise RuntimeError("API returned no rows")
    frame = raw.rename(columns={"time":"date"}).copy()
    frame["symbol"] = symbol
    frame = frame[COLUMNS]
    frame["date"] = pd.to_datetime(frame["date"],errors="coerce")
    for col in COLUMNS[2:]:
        frame[col] = pd.to_numeric(frame[col],errors="coerce")
    frame = frame.dropna(subset=["date","open","high","low","close","volume"])
    frame = frame[(frame["open"]>0)&(frame["high"]>0)&(frame["low"]>0)&(frame["close"]>0)&(frame["volume"]>=0)]
    frame = frame[(frame["high"]>=frame[["open","close","low"]].max(axis=1)) & (frame["low"]<=frame[["open","close","high"]].min(axis=1))]
    if frame.empty:
        raise RuntimeError("API returned no valid rows")
    PRICE_DIR.mkdir(parents=True,exist_ok=True)
    dest=PRICE_DIR/f"{symbol}.csv"
    if dest.exists():
        old=pd.read_csv(dest)
        old.columns=[str(c).lower() for c in old.columns]
        if set(COLUMNS).issubset(old.columns):
            frame=pd.concat([old[COLUMNS],frame],ignore_index=True)
    frame["date"]=pd.to_datetime(frame["date"],errors="coerce")
    frame=frame.dropna(subset=["date"]).sort_values("date").drop_duplicates("date",keep="last")
    frame["date"]=frame["date"].dt.strftime("%Y-%m-%d")
    frame.to_csv(dest,index=False,encoding="utf-8")
    print(f"[REFRESH] {symbol}: {len(frame)} rows, latest={frame['date'].max()}",flush=True)

def main():
    failures=[]
    for symbol in SYMBOLS:
        try:
            refresh(symbol)
        except Exception as exc:
            print(f"[REFRESH] {symbol}: FAILED {type(exc).__name__}: {exc}",flush=True)
            failures.append(symbol)
        time.sleep(1)
    if failures:
        print(f"Failed: {', '.join(failures)}",file=sys.stderr)
        sys.exit(1)

if __name__=="__main__":
    main()
