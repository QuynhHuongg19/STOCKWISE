
"""Validate bank metrics obtained from verified sources."""

from dataclasses import dataclass
from datetime import date
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
    """Fetch annual TCB metrics from Techcombank's public HTML tables."""
    import requests
    from bs4 import BeautifulSoup

    url = (
        "https://techcombank.com/nha-dau-tu/"
        "thong-tin-tai-chinh/chi-so-noi-bat"
    )

    html = _get_tcb_html_cached(
        url,
        date.today().toordinal(),
    )
    soup = BeautifulSoup(html, "html.parser")

    target_period = f"FY{str(year)[-2:]}"
    metric_labels = {
        "npl": "tỷ lệ nợ xấu (npl)",
        "car": "tỷ lệ an toàn vốn theo basel ii",
        "casa": "chỉ số casa",
    }

    for table in soup.find_all("table"):
        rows = table.find_all("tr")

        header = None
        values = {}

        for row in rows:
            cells = [
                cell.get_text(" ", strip=True)
                for cell in row.find_all(["th", "td"])
            ]

            if not cells:
                continue

            if target_period in cells:
                header = cells
                continue

            if header is None:
                continue

            label = cells[0].strip().lower()

            for metric, expected_label in metric_labels.items():
                if label != expected_label:
                    continue

                column_index = header.index(target_period)

                if column_index >= len(cells):
                    continue

                raw_value = cells[column_index]

                if not raw_value.endswith("%"):
                    continue

                number = float(
                    raw_value.replace("%", "").replace(",", "").strip()
                )

                values[metric] = {
                    "value": number / 100,
                    "raw_value": raw_value,
                    "period": target_period,
                    "source_url": url,
                }

        if len(values) == 3:
            return values

    return {}


def validate_tcb_metrics(year: int):
    """Validate the completeness and ranges of annual TCB metrics."""
    data = fetch_tcb_bank_metrics(year)

    required = {"npl", "car", "casa"}

    if set(data) != required:
        return {
            "valid": False,
            "reason": "Missing required bank metrics",
            "data": data,
        }

    expected_period = f"FY{str(year)[-2:]}"

    for metric, info in data.items():
        value = info.get("value")
        period = info.get("period")
        source = info.get("source_url", "")

        if period != expected_period:
            return {
                "valid": False,
                "reason": f"Wrong reporting period: {metric}",
                "data": data,
            }

        if not isinstance(value, (int, float)) or not math.isfinite(value):
            return {
                "valid": False,
                "reason": f"Invalid value: {metric}",
                "data": data,
            }

        if not 0 <= value <= 1:
            return {
                "valid": False,
                "reason": f"Out-of-range value: {metric}",
                "data": data,
            }

        if not source.startswith("https://techcombank.com/"):
            return {
                "valid": False,
                "reason": f"Unexpected source: {metric}",
                "data": data,
            }

    return {
        "valid": True,
        "reason": "All bank metrics validated",
        "data": data,
    }


def fetch_bank_metrics(ticker: str, year: int):
    """Get bank metrics with daily cache."""
    from datetime import date
    ticker = str(ticker).strip().upper()
    year = int(year)

    result = _fetch_bank_metrics_cached(
        ticker, year, date.today().toordinal()
    )

    return {
        key: value.copy()
        for key, value in result.items()
    }


from functools import lru_cache


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
        headers={"User-Agent": "Mozilla/5.0"},
    )
    response.raise_for_status()

    return response.content
