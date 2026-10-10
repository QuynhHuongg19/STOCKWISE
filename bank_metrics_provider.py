
"""Bank metrics provider for STOCKWISE.

Supports:
- Verified metrics stored in CSV.
- Official Techcombank annual NPL, CAR and CASA metrics.
- Source attribution and validation.
- Daily caching.
"""

from dataclasses import dataclass
from datetime import date
from functools import lru_cache
from pathlib import Path
from urllib.parse import urlparse
import csv
import math
import re
import unicodedata

import requests
from bs4 import BeautifulSoup


SUPPORTED_METRICS = {"npl", "car", "casa"}
METRICS = SUPPORTED_METRICS


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
        ticker = str(self.ticker).strip().upper()
        metric = str(self.metric).strip().lower()
        period = str(self.period).strip()
        source_url = str(self.source_url).strip()

        if not ticker or not ticker.isalnum():
            raise ValueError("Invalid ticker")

        if metric not in SUPPORTED_METRICS:
            raise ValueError(
                f"Unsupported metric: {metric}"
            )

        if not period.isdigit() or len(period) != 4:
            raise ValueError("Period must be YYYY")

        year = int(period)

        if year < 2000 or year > date.today().year:
            raise ValueError("Invalid reporting year")

        parsed_url = urlparse(source_url)

        if (
            parsed_url.scheme != "https"
            or not parsed_url.netloc
        ):
            raise ValueError(
                "Source must be a valid HTTPS URL"
            )

        try:
            reported = date.fromisoformat(
                str(self.report_date).strip()
            )
        except ValueError as exc:
            raise ValueError(
                "Invalid report date"
            ) from exc

        if reported.year < year:
            raise ValueError(
                "Report date precedes reporting year"
            )

        if reported > date.today():
            raise ValueError(
                "Report date cannot be in the future"
            )

        value = float(self.value)

        if not math.isfinite(value):
            raise ValueError(
                "Metric must be finite"
            )

        unit = str(self.unit).strip().lower()

        if unit == "percent":
            value /= 100.0
        elif unit != "decimal":
            raise ValueError(
                "Unit must be percent or decimal"
            )

        if not 0 <= value <= 1:
            raise ValueError(
                "Metric outside valid range"
            )

        return {
            "ticker": ticker,
            "period": period,
            "metric": metric,
            "value": value,
            "source_url": source_url,
            "report_date": reported.isoformat(),
        }


def _normalize_label(value):
    """Normalize text for matching HTML labels."""
    value = unicodedata.normalize(
        "NFC",
        str(value)
    )
    return " ".join(value.lower().split())


@lru_cache(maxsize=8)
def _get_tcb_html_cached(url, cache_day):
    """Download Techcombank HTML once per day."""
    response = requests.get(
        url,
        timeout=20,
        headers={
            "User-Agent": "Mozilla/5.0"
        },
    )

    response.raise_for_status()
    return response.content


def fetch_tcb_bank_metrics(year: int):
    """Extract annual NPL, CAR and CASA from TCB website."""
    year = int(year)

    if year < 2000 or year > date.today().year:
        return {}

    url = (
        "https://techcombank.com/nha-dau-tu/"
        "thong-tin-tai-chinh/chi-so-noi-bat"
    )

    html = _get_tcb_html_cached(
        url,
        date.today().toordinal()
    )

    soup = BeautifulSoup(
        html.decode("utf-8", errors="replace")
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

    normalized_labels = {
        _normalize_label(label): metric
        for metric, label in labels.items()
    }

    results = {}

    for table in soup.find_all("table"):
        column_index = None

        for row in table.find_all("tr"):
            cells = [
                cell.get_text(" ", strip=True)
                for cell in row.find_all(["th", "td"])
                if cell.find_parent("tr") is row
            ]

            if not cells:
                continue

            # Identify the annual column.
            normalized_cells = [
                cell.strip().upper()
                for cell in cells
            ]

            if target in normalized_cells:
                column_index = normalized_cells.index(
                    target
                )
                continue

            if column_index is None:
                continue

            label = _normalize_label(cells[0])
            metric = normalized_labels.get(label)

            if metric is None:
                continue

            if column_index >= len(cells):
                continue

            raw = cells[column_index].strip()

            if not re.fullmatch(
                r"\d+(?:[.,]\d+)?\s*%",
                raw
            ):
                continue

            number = float(
                raw.replace("%", "")
                .strip()
                .replace(",", ".")
            )

            value = number / 100.0

            if not math.isfinite(value):
                continue

            if not 0 <= value <= 1:
                continue

            results[metric] = {
                "value": value,
                "raw_value": raw,
                "period": target,
                "source_url": url,
            }

        if len(results) == 3:
            break

    return results


@lru_cache(maxsize=8)
def _load_verified_bank_metrics(cache_day):
    """Load validated bank metrics from CSV."""
    path = (
        Path(__file__).resolve().parent
        / "data"
        / "bank_metrics"
        / "verified_metrics.csv"
    )

    if not path.is_file():
        return {}

    results = {}

    with path.open(
        "r",
        encoding="utf-8-sig",
        newline=""
    ) as file:
        reader = csv.DictReader(file)

        for row in reader:
            if not row.get("ticker"):
                continue

            try:
                item = BankMetric(
                    ticker=row["ticker"],
                    period=row["period"],
                    metric=row["metric"],
                    value=float(row["value"]),
                    unit=row["unit"],
                    source_url=row["source_url"],
                    report_date=row["report_date"],
                ).normalized()

            except (
                ValueError,
                TypeError,
                KeyError,
                OverflowError
            ):
                continue

            key = (
                item["ticker"],
                int(item["period"])
            )

            results.setdefault(key, {})[
                item["metric"]
            ] = {
                "value": item["value"],
                "source_url": item["source_url"],
                "report_date": item["report_date"],
            }

    return results


@lru_cache(maxsize=256)
def _fetch_bank_metrics_cached(
    ticker,
    year,
    cache_day
):
    """Combine validated CSV and official provider data."""
    verified_data = _load_verified_bank_metrics(
        cache_day
    )

    results = {
        metric: info.copy()
        for metric, info in verified_data.get(
            (ticker, year), {}
        ).items()
    }

    providers = {
        "TCB": fetch_tcb_bank_metrics,
    }

    provider = providers.get(ticker)

    if provider is not None:
        try:
            official_data = provider(year)
        except (
            requests.RequestException,
            ValueError,
            UnicodeError
        ):
            official_data = {}

        for metric, info in official_data.items():
            if metric in SUPPORTED_METRICS:
                results.setdefault(
                    metric,
                    info.copy()
                )

    return results


def fetch_bank_metrics(ticker: str, year: int):
    """Public API: retrieve annual bank metrics."""
    ticker = str(ticker).strip().upper()
    year = int(year)

    if not ticker or not ticker.isalnum():
        return {}

    if year < 2000 or year > date.today().year:
        return {}

    result = _fetch_bank_metrics_cached(
        ticker,
        year,
        date.today().toordinal()
    )

    return {
        metric: info.copy()
        for metric, info in result.items()
    }
