"""STOCKWISE: bulk download and review bank NPL/CAR/CASA from official PDF reports.

This collector produces *candidates*, never automatically verified metrics.
Usage:
  python collect_bank_metrics.py --download-csv data/bank_metrics/report_sources.csv
  python collect_bank_metrics.py --scan-pdf data/bank_metrics/reports
  python collect_bank_metrics.py --collect data/bank_metrics/report_sources.csv
  python collect_bank_metrics.py verified_input.csv
"""
import argparse
import csv
import json
import math
import re
import unicodedata
from datetime import date
from pathlib import Path
from urllib.parse import urlparse

from bank_metrics_provider import BankMetric

DATA_DIR = Path(__file__).resolve().parent / "data" / "bank_metrics"
OUTPUT_FILE = DATA_DIR / "verified_metrics.csv"
COLUMNS = ["ticker", "period", "metric", "value", "unit", "source_url", "report_date"]
SOURCE_COLUMNS = ["ticker", "year", "url"]

KEYWORDS = {
    "npl": ["ty le no xau", "no xau", "non-performing loan", "npl ratio"],
    "car": ["ty le an toan von", "capital adequacy ratio", "car ratio", "basel ii", "basel iii"],
    "casa": ["casa", "tien gui khong ky han", "current account savings account"],
}
PERCENT_RE = re.compile(r"(?<!\d)(\d{1,3}(?:[.,]\d{1,3})?)\s*%")


def normalize_text(text):
    text = unicodedata.normalize("NFD", str(text).lower())
    return "".join(c for c in text if unicodedata.category(c) != "Mn").replace("đ", "d")


def validate_source_url(url):
    parsed = urlparse(url.strip())
    if parsed.scheme != "https" or not parsed.netloc or parsed.username or parsed.password:
        raise ValueError("Source must be an HTTPS URL with a valid hostname")
    return url.strip()


def import_verified_metrics(input_file):
    """Import *human-reviewed* rows. URL format is checked, NOT source truthfulness."""
    input_file = Path(input_file)
    if not input_file.is_file():
        raise FileNotFoundError(input_file)
    if input_file.resolve() == OUTPUT_FILE.resolve():
        raise ValueError("Source file must be different from verified_metrics.csv")
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    existing = {}
    if OUTPUT_FILE.exists():
        with OUTPUT_FILE.open("r", encoding="utf-8-sig", newline="") as f:
            for row in csv.DictReader(f):
                if row.get("ticker"):
                    existing[(row["ticker"].strip().upper(), row["period"].strip(), row["metric"].strip().lower())] = row
    imported = rejected = 0
    with input_file.open("r", encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f)
        if not set(COLUMNS).issubset(reader.fieldnames or []):
            raise ValueError("Verified input CSV must contain: " + ",".join(COLUMNS))
        for row in reader:
            try:
                item = BankMetric(
                    ticker=row["ticker"], period=row["period"], metric=row["metric"],
                    value=float(row["value"]), unit=row["unit"],
                    source_url=validate_source_url(row["source_url"]),
                    report_date=row["report_date"],
                ).normalized()
                key = (item["ticker"], item["period"], item["metric"])
                existing[key] = {"ticker": item["ticker"], "period": item["period"],
                                 "metric": item["metric"], "value": row["value"],
                                 "unit": row["unit"], "source_url": item["source_url"],
                                 "report_date": item["report_date"]}
                imported += 1
            except (ValueError, TypeError, KeyError, AttributeError):
                rejected += 1
    with OUTPUT_FILE.open("w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=COLUMNS)
        writer.writeheader()
        writer.writerows(existing.values())
    print(f"Imported: {imported} | Rejected: {rejected} | Total: {len(existing)}")


def load_report_sources(csv_path):
    path = Path(csv_path)
    if not path.is_file():
        raise FileNotFoundError(path)
    records = []
    with path.open("r", encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f)
        if not set(SOURCE_COLUMNS).issubset(reader.fieldnames or []):
            raise ValueError("Sources CSV must have: ticker,year,url")
        for line, row in enumerate(reader, 2):
            try:
                ticker = row["ticker"].strip().upper()
                year = row["year"].strip()
                url = validate_source_url(row["url"])
                if not re.fullmatch(r"[A-Z0-9]{2,12}", ticker):
                    raise ValueError("invalid ticker")
                if not re.fullmatch(r"20\d{2}", year) or not 2023 <= int(year) <= date.today().year:
                    raise ValueError("year outside 2023-current")
                records.append({"ticker": ticker, "year": year, "url": url})
            except (KeyError, AttributeError, ValueError) as exc:
                print(f"SKIP source CSV line {line}: {exc}")
    return records


def download_bank_report(url, filename):
    import requests
    validate_source_url(url)
    folder = DATA_DIR / "reports"
    folder.mkdir(parents=True, exist_ok=True)
    destination = folder / Path(filename).name
    # Limit size while streaming, so a mistaken URL cannot exhaust disk memory.
    with requests.get(url, timeout=(15, 60), stream=True,
                      headers={"User-Agent": "Mozilla/5.0 STOCKWISE educational research"},
                      allow_redirects=True) as response:
        response.raise_for_status()
        if urlparse(response.url).scheme != "https":
            raise ValueError("Redirected to a non-HTTPS URL")
        temporary = destination.with_suffix(".part")
        try:
            size = 0
            with temporary.open("wb") as f:
                for chunk in response.iter_content(chunk_size=65536):
                    if not chunk:
                        continue
                    size += len(chunk)
                    if size > 60 * 1024 * 1024:
                        raise ValueError("PDF exceeds 60 MB limit")
                    f.write(chunk)
            with temporary.open("rb") as f:
                if f.read(5) != b"%PDF-":
                    raise ValueError("Downloaded response is not a PDF")
            temporary.replace(destination)
        finally:
            temporary.unlink(missing_ok=True)
    return destination


def download_reports_from_csv(csv_path):
    sources = load_report_sources(csv_path)
    manifest = []
    for i, source in enumerate(sources, 1):
        # Index avoids overwriting different reports of the same bank/year.
        filename = f"{source['ticker']}_{source['year']}_{i:04d}.pdf"
        try:
            path = download_bank_report(source["url"], filename)
            status = "downloaded"
            print(f"OK {source['ticker']} {source['year']}: {path.name}")
        except Exception as exc:
            path = None
            status = f"failed: {exc}"
            print(f"FAILED {source['ticker']} {source['year']}: {exc}")
        manifest.append({**source, "file": str(path) if path else "", "status": status})
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    with (DATA_DIR / "download_manifest.csv").open("w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=["ticker", "year", "url", "file", "status"])
        writer.writeheader()
        writer.writerows(manifest)
    print(f"Reports: {len(sources)} | Downloaded: {sum(x['status']=='downloaded' for x in manifest)}")
    return manifest


def extract_pdf_metric_candidates(pdf_path):
    import pdfplumber
    candidates = []
    with pdfplumber.open(pdf_path) as pdf:
        for page_number, page in enumerate(pdf.pages, 1):
            lines = (page.extract_text() or "").splitlines()
            for idx, line in enumerate(lines):
                normalized = normalize_text(line)
                for metric, phrases in KEYWORDS.items():
                    if any(phrase in normalized for phrase in phrases):
                        # Neighboring lines provide context for PDF tables.
                        context = " | ".join(lines[max(0, idx-1):min(len(lines), idx+2)])
                        percentages = PERCENT_RE.findall(context)
                        candidates.append({
                            "page": page_number, "metric": metric,
                            "text": line.strip(), "context": context[:1200],
                            "percentage_candidates": "; ".join(percentages),
                            "review_status": "UNVERIFIED",
                        })
    return candidates


def scan_bank_pdf_folder(folder_path):
    folder = Path(folder_path)
    if not folder.is_dir():
        raise FileNotFoundError(folder)
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    manifest_path = DATA_DIR / "download_manifest.csv"
    metadata = {}
    if manifest_path.exists():
        with manifest_path.open("r", encoding="utf-8-sig", newline="") as f:
            for row in csv.DictReader(f):
                if row.get("file"):
                    metadata[str(Path(row["file"]).resolve())] = row
    results = []
    files = sorted(p for p in folder.rglob("*") if p.is_file() and p.suffix.lower() == ".pdf")
    failures = 0
    for path in files:
        info = metadata.get(str(path.resolve()), {})
        print(f"Scanning: {path.name}", flush=True)
        try:
            for item in extract_pdf_metric_candidates(path):
                results.append({"file": str(path), "ticker": info.get("ticker", ""),
                                "year": info.get("year", ""), "source_url": info.get("url", ""),
                                **item})
        except Exception as exc:
            failures += 1
            print(f"ERROR {path.name}: {exc}")
    json_path = DATA_DIR / "pdf_candidates.json"
    json_path.write_text(json.dumps(results, ensure_ascii=False, indent=2), encoding="utf-8")
    csv_path = DATA_DIR / "pdf_candidates.csv"
    fields = ["ticker", "year", "metric", "percentage_candidates", "page", "text", "context", "source_url", "file", "review_status"]
    with csv_path.open("w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fields)
        writer.writeheader()
        writer.writerows(results)
    print(f"PDF scanned: {len(files)} | Failed: {failures} | Candidates: {len(results)}")
    print(f"Review candidates: {csv_path}")
    print("All candidate values are UNVERIFIED; verified_metrics.csv is unchanged.")
    return results


def main():
    parser = argparse.ArgumentParser(description="STOCKWISE multi-bank PDF metrics collector")
    parser.add_argument("source", nargs="?", help="Import a human-reviewed metrics CSV")
    group = parser.add_mutually_exclusive_group()
    group.add_argument("--download-csv", metavar="CSV", help="Download PDF reports from ticker,year,url CSV")
    group.add_argument("--scan-pdf", metavar="FOLDER", help="Scan local PDF reports")
    group.add_argument("--collect", metavar="CSV", help="Download and scan in one run")
    args = parser.parse_args()
    if args.collect:
        download_reports_from_csv(args.collect)
        scan_bank_pdf_folder(DATA_DIR / "reports")
    elif args.download_csv:
        download_reports_from_csv(args.download_csv)
    elif args.scan_pdf:
        scan_bank_pdf_folder(args.scan_pdf)
    elif args.source:
        import_verified_metrics(args.source)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
