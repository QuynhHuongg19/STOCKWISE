
"""Validate bank metrics obtained from verified sources."""

from dataclasses import dataclass
from datetime import date
from functools import lru_cache
import math


METRICS = {"npl", "car", "casa"}


@dataclass(frozen=True)
class BankMetric:
    ticker: str
    period: str
    metric: str
    value: float
    unit: str
    source_url: str
    report_date: str

    def normalized(self):
        ticker = self.ticker.strip().upper()
        metric = self.metric.strip().lower()
        period = str(self.period).strip()

        if not ticker or not ticker.isalnum():
            raise ValueError("Invalid ticker")

        if metric not in METRICS:
            raise ValueError(f"Unsupported metric: {metric}")

        if not period.isdigit() or len(period) != 4:
            raise ValueError("Period must be YYYY")

        year = int(period)

        if year < 2000 or year > date.today().year:
            raise ValueError("Invalid reporting year")

        if not self.source_url.startswith("https://"):
            raise ValueError("Source must use HTTPS")

        try:
            reported = date.fromisoformat(self.report_date)
        except ValueError as exc:
            raise ValueError("Invalid report date") from exc

        if reported.year < year:
            raise ValueError("Report date precedes reporting year")

        value = float(self.value)

        if not math.isfinite(value):
            raise ValueError("Metric must be finite")

        if self.unit == "percent":
            value /= 100.0
        elif self.unit != "decimal":
            raise ValueError("Unit must be percent or decimal")

        if not 0 <= value <= 1:
            raise ValueError("Metric outside valid range")

        return {
            "ticker": ticker,
            "period": period,
            "metric": metric,
            "value": value,
            "source_url": self.source_url,
            "report_date": self.report_date,
        }


def fetch_tcb_bank_metrics(year: int):
    """Extract annual TCB metrics from official HTML tables."""
    from bs4 import BeautifulSoup
    import re

    url = (
        "https://techcombank.com/nha-dau-tu/"
        "thong-tin-tai-chinh/chi-so-noi-bat"
    )

    html = _get_tcb_html_cached(
        url,
        date.today().toordinal()
    )

    soup = BeautifulSoup(
        html.decode("utf-8")
        if isinstance(html, bytes)
        else html,
        "html.parser"
    )

    target = f"FY{year % 100:02d}"

    labels = {
        "npl": "tỷ lệ nợ xấu (npl)",
        "car": "tỷ lệ an toàn vốn theo basel ii",
        "casa": "chỉ số casa",
    }

    results = {}

    for table in soup.find_all("table"):
        column_index = None

        for row in table.find_all("tr"):
            cells = [
                c.get_text(" ", strip=True)
                for c in row.find_all(["th", "td"])
            ]

            if not cells:
                continue

            label = " ".join(
                cells[0].lower().split()
            )

            if label in labels.values():
                if column_index is None:
                    continue

                if column_index >= len(cells):
                    continue

                raw = cells[column_index].strip()

                if not re.fullmatch(
                    r"-?\d+(?:[.,]\d+)?%",
                    raw
                ):
                    continue

                number = float(
                    raw[:-1].replace(",", ".")
                )

                metric = next(
                    key
                    for key, value in labels.items()
                    if value == label
                )

                results[metric] = {
                    "value": number / 100,
                    "raw_value": raw,
                    "period": target,
                    "source_url": url,
                }

                continue

            # Header rows identify the annual column.
            if target in cells:
                column_index = cells.index(target)

        if len(results) == 3:
            return results

    return results


def fetch_bank_metrics(ticker: str, year: int):
    """Get bank metrics with daily cache."""
    ticker = str(ticker).strip().upper()
    year = int(year)

    result = _fetch_bank_metrics_cached(
        ticker,
        year,
        date.today().toordinal()
    )

    return {
        key: value.copy()
        for key, value in result.items()
    }


@lru_cache(maxsize=256)
def _fetch_bank_metrics_cached(ticker, year, cache_day):
    """Load verified metrics once per bank, year and day."""
    providers = {
        "TCB": fetch_tcb_bank_metrics,
    }

    provider = providers.get(ticker)

    if provider is None:
        return {}

    return provider(year)


@lru_cache(maxsize=8)
def _get_tcb_html_cached(url, cache_day):
    """Download Techcombank HTML once per day."""
    import requests

    response = requests.get(
        url,
        timeout=20,
        headers={
            "User-Agent": "Mozilla/5.0"
        },
    )

    response.raise_for_status()

    # Temporary diagnostics for Streamlit Cloud.
    print(
        "TCB DEBUG:",
        "status =", response.status_code,
        "bytes =", len(response.content),
        "tables =", response.text.lower().count("<table"),
        flush=True,
    )

    return response.content
