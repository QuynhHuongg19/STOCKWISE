
from pathlib import Path
from datetime import datetime, timezone
import json
from financial_ratios import get_financial_data

TICKERS = ["VNM"]
OUTPUT = Path("data/financial")
OUTPUT.mkdir(parents=True, exist_ok=True)

for ticker in TICKERS:
    try:
        data = get_financial_data(ticker, period="year")
        folder = OUTPUT / ticker
        folder.mkdir(parents=True, exist_ok=True)

        for name in ("income", "balance", "cashflow", "ratios"):
            df = data.get(name)
            if df is not None and not df.empty:
                df.to_csv(
                    folder / f"{name}.csv",
                    index=False,
                    encoding="utf-8-sig"
                )

        metadata = {
            "ticker": ticker,
            "source": "vnstock 4.0.9",
            "period": "year",
            "exported_at_utc": datetime.now(
                timezone.utc
            ).isoformat(),
        }
        (folder / "metadata.json").write_text(
            json.dumps(metadata, indent=2),
            encoding="utf-8"
        )
        print(f"OK: {ticker}")

    except Exception as e:
        print(f"ERROR {ticker}: {e}")
