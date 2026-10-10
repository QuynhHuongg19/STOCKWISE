"""STOCKWISE: discover *candidate* annual reports on bank-owned public websites.

Usage:
  python discover_bank_reports.py
  python discover_bank_reports.py --banks MBB,VCB,ACB --max-pages 15
  python discover_bank_reports.py --seeds data/bank_metrics/bank_websites.csv

Output: data/bank_metrics/report_sources_candidates.csv
Review links before copying selected rows into report_sources.csv and running
  python collect_bank_metrics.py --collect data/bank_metrics/report_sources.csv

Discovery is best-effort. Dynamic websites, robots restrictions and off-site PDF
CDNs can prevent finding some reports. No financial metrics are verified here.
"""
import argparse
import csv
import re
import time
import unicodedata
from collections import deque
from pathlib import Path
from urllib.parse import urljoin, urlparse, urldefrag

import requests
from bs4 import BeautifulSoup

BASE = Path(__file__).resolve().parent
DATA = BASE / 'data' / 'bank_metrics'
OUTPUT = DATA / 'report_sources_candidates.csv'

# Starting websites only, not assertions that reports exist at any URL.
BANK_WEBSITES = {
    'VCB': 'https://www.vietcombank.com.vn/',
    'BID': 'https://bidv.com.vn/',
    'CTG': 'https://www.vietinbank.vn/',
    'TCB': 'https://techcombank.com/',
    'MBB': 'https://www.mbbank.com.vn/',
    'ACB': 'https://acb.com.vn/',
    'VPB': 'https://www.vpbank.com.vn/',
    'HDB': 'https://hdbank.com.vn/',
    'STB': 'https://www.sacombank.com.vn/',
    'TPB': 'https://tpb.vn/',
    'VIB': 'https://www.vib.com.vn/',
    'SHB': 'https://www.shb.com.vn/',
    'LPB': 'https://lpbank.com.vn/',
    'OCB': 'https://www.ocb.com.vn/',
    'MSB': 'https://www.msb.com.vn/',
    'SSB': 'https://www.seabank.com.vn/',
    'EIB': 'https://eximbank.com.vn/',
    'NAB': 'https://www.namabank.com.vn/',
    'BAB': 'https://baca-bank.vn/',
    'ABB': 'https://abbank.vn/',
    'BVB': 'https://www.baovietbank.vn/',
    'KLB': 'https://kienlongbank.com/',
}
REPORT_TERMS = (
    'bao cao thuong nien', 'annual report', 'bao cao tai chinh',
    'financial statements', 'financial report', 'investor relations',
    'quan he nha dau tu', 'cong bo thong tin', 'bao cao', 'reports',
)
PDF_TERMS = ('bao cao thuong nien', 'annual report', 'bao cao tai chinh',
             'financial statements', 'financial report', 'bctc', 'bctn')
YEARS = ('2023', '2024', '2025', '2026')
FIELDS = ['ticker', 'year', 'url', 'link_text', 'found_on', 'review_status']


def normalize(value):
    value = unicodedata.normalize('NFD', str(value).lower())
    return ''.join(ch for ch in value if unicodedata.category(ch) != 'Mn').replace('đ', 'd')


def host(url):
    return (urlparse(url).hostname or '').lower().removeprefix('www.')


def allowed_site(url, root):
    hostname, base = host(url), host(root)
    return bool(hostname and base and (hostname == base or hostname.endswith('.' + base)))


def clean_url(raw, parent):
    url, _ = urldefrag(urljoin(parent, raw.strip()))
    parsed = urlparse(url)
    if parsed.scheme != 'https' or not parsed.netloc or parsed.username or parsed.password:
        return None
    return url


def is_pdf_link(url, label):
    path = urlparse(url).path.lower()
    query = urlparse(url).query.lower()
    if path.endswith('.pdf'):
        return True
    # Some bank CMS systems use download endpoints with query params.
    return ('download' in path or 'download' in query) and any(
        word in normalize(label + ' ' + url) for word in PDF_TERMS
    )


def years_in(text):
    return [year for year in YEARS if re.search(r'(?<!\d)' + year + r'(?!\d)', text)]


def discover_one(session, ticker, root, max_pages, delay):
    queue = deque([(root, 0)])
    seen = set()
    found = {}
    while queue and len(seen) < max_pages:
        url, depth = queue.popleft()
        if url in seen or not allowed_site(url, root):
            continue
        seen.add(url)
        try:
            response = session.get(url, timeout=(8, 15), allow_redirects=True)
            response.raise_for_status()
            if not allowed_site(response.url, root):
                continue
            if 'html' not in response.headers.get('content-type', '').lower():
                continue
            soup = BeautifulSoup(response.content, 'html.parser')
        except requests.RequestException as exc:
            print(f'  SKIP {url}: {type(exc).__name__}')
            continue
        for a in soup.select('a[href]'):
            target = clean_url(a.get('href', ''), response.url)
            if not target:
                continue
            label = ' '.join(a.get_text(' ', strip=True).split())[:180]
            normalized = normalize(label + ' ' + target)
            if is_pdf_link(target, label):
                if not allowed_site(target, root):
                    # Avoid treating third-party hosts as official without review.
                    continue
                if not any(term in normalized for term in PDF_TERMS):
                    continue
                for year in years_in(normalized):
                    found[(year, target)] = {
                        'ticker': ticker, 'year': year, 'url': target,
                        'link_text': label, 'found_on': response.url,
                        'review_status': 'UNVERIFIED_SOURCE',
                    }
            elif depth < 2 and allowed_site(target, root):
                if any(term in normalized for term in REPORT_TERMS):
                    if target not in seen and all(target != item[0] for item in queue):
                        queue.append((target, depth + 1))
        print(f'  {ticker}: scanned {len(seen)}/{max_pages} pages, found {len(found)} PDF-year links')
        if delay:
            time.sleep(delay)
    return list(found.values())


def read_seeds(path):
    with Path(path).open('r', encoding='utf-8-sig', newline='') as f:
        reader = csv.DictReader(f)
        if not {'ticker', 'url'}.issubset(reader.fieldnames or []):
            raise ValueError('Seeds CSV must have columns: ticker,url')
        return {r['ticker'].strip().upper(): r['url'].strip() for r in reader if r.get('ticker') and r.get('url')}


def main():
    parser = argparse.ArgumentParser(description='Find bank PDF report URL candidates; does not verify metrics')
    parser.add_argument('--banks', help='Comma-separated bank tickers; default: all configured banks')
    parser.add_argument('--seeds', help='Optional CSV with ticker,url starting bank websites')
    parser.add_argument('--max-pages', type=int, default=12, help='Maximum HTML pages per bank (default 12)')
    parser.add_argument('--delay', type=float, default=0.3, help='Pause between requests (default 0.3 seconds)')
    args = parser.parse_args()
    if not 1 <= args.max_pages <= 100 or not 0 <= args.delay <= 30:
        parser.error('Use max-pages 1..100 and delay 0..30')
    seeds = read_seeds(args.seeds) if args.seeds else BANK_WEBSITES
    if args.banks:
        requested = {s.strip().upper() for s in args.banks.split(',') if s.strip()}
        unknown = requested - seeds.keys()
        if unknown:
            parser.error('Missing website seed(s): ' + ', '.join(sorted(unknown)))
        seeds = {ticker: url for ticker, url in seeds.items() if ticker in requested}
    session = requests.Session()
    session.headers.update({'User-Agent': 'Mozilla/5.0 (compatible; STOCKWISE research; public pages)'})
    results = []
    for ticker, url in seeds.items():
        print(f'BANK {ticker} | {url}', flush=True)
        if not url.startswith('https://'):
            print('  SKIP: website seed must be HTTPS')
            continue
        results.extend(discover_one(session, ticker, url, args.max_pages, args.delay))
    DATA.mkdir(parents=True, exist_ok=True)
    with OUTPUT.open('w', encoding='utf-8-sig', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=FIELDS)
        writer.writeheader()
        writer.writerows(sorted(results, key=lambda r: (r['ticker'], r['year'], r['url'])))
    print(f'Banks checked: {len(seeds)} | PDF-year candidates: {len(results)}')
    print(f'Review source candidates: {OUTPUT}')
    print('Review links and reporting years before transferring rows to report_sources.csv.')
    print('Nothing was added to verified_metrics.csv.')


if __name__ == '__main__':
    main()
