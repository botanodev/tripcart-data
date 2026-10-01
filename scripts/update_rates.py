#!/usr/bin/env python3
"""Fetch daily reference exchange rates and write rates.json.

Runs once a day from .github/workflows/update-rates.yml.

Rules (from the app spec, chapter 6):
  - Upstream order: fawazahmed0 exchange-api first (jsDelivr, then its
    Cloudflare Pages mirror), open.er-api.com as the backup.
  - Validation: every CORE currency must be present and positive.
    If validation fails, rates.json is NOT written - yesterday's file stays.
  - rates.json is only rewritten when something other than generatedAt
    changed, so the git history has one commit per real update.
  - Never move backwards: if the upstream date is older than the date
    already in rates.json, keep the existing file.

Standard library only, so the workflow needs no pip install.
"""

from __future__ import annotations

import datetime as dt
import json
import math
import re
import sys
import urllib.request
from pathlib import Path

SCHEMA_VERSION = 1

# Spec 6.1: at least these must exist and be positive, or nothing is written.
CORE = ['USD', 'EUR', 'JPY', 'KRW', 'TWD', 'CNY', 'HKD', 'GBP', 'THB', 'SGD', 'AUD']

FAWAZ_URLS = [
    'https://cdn.jsdelivr.net/npm/@fawazahmed0/currency-api@latest/v1/currencies/usd.json',
    'https://latest.currency-api.pages.dev/v1/currencies/usd.json',
]
ERAPI_URL = 'https://open.er-api.com/v6/latest/USD'

OUTPUT = Path(__file__).resolve().parent.parent / 'rates.json'
CODE_PATTERN = re.compile(r'^[A-Z]{3}$')


def fetch_json(url: str, timeout: int = 30) -> dict:
    req = urllib.request.Request(url, headers={'User-Agent': 'tripcart-data-updater'})
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return json.load(resp)


def clean_rates(raw: dict) -> dict:
    """Uppercase the codes; drop anything that is not a 3-letter code with a
    positive finite number. The app has its own currency table and ignores
    codes it does not know, so extra codes are harmless - bad numbers are not."""
    out = {}
    for code, value in raw.items():
        code = str(code).upper()
        if not CODE_PATTERN.match(code):
            continue
        if isinstance(value, bool) or not isinstance(value, (int, float)):
            continue
        if not math.isfinite(value) or value <= 0:
            continue
        out[code] = value
    return dict(sorted(out.items()))


def parse_fawaz(data: dict) -> tuple[str, dict]:
    # {"date": "2026-10-01", "usd": {"jpy": 148.2, ...}}  (lowercase codes)
    return str(data['date']), clean_rates(data['usd'])


def parse_erapi(data: dict) -> tuple[str, dict]:
    # {"result": "success", "time_last_update_unix": 1727740800, "rates": {"USD": 1, ...}}
    if data.get('result') != 'success':
        raise ValueError(f"open.er-api result: {data.get('result')}")
    ts = int(data['time_last_update_unix'])
    date = dt.datetime.fromtimestamp(ts, dt.timezone.utc).date().isoformat()
    return date, clean_rates(data['rates'])


def validate(date: str, rates: dict) -> list[str]:
    problems = []
    try:
        dt.date.fromisoformat(date)
    except ValueError:
        problems.append(f'bad date: {date!r}')
    for code in CORE:
        if code not in rates:
            problems.append(f'missing core currency {code}')
    if rates.get('USD') != 1:
        problems.append(f"USD must be 1 (base), got {rates.get('USD')!r}")
    return problems


def build(date: str, source: str, rates: dict, now: dt.datetime) -> dict:
    return {
        'schemaVersion': SCHEMA_VERSION,
        'date': date,
        'generatedAt': now.strftime('%Y-%m-%dT%H:%M:%SZ'),
        'base': 'USD',
        'source': source,
        'rates': rates,
    }


def decide(new: dict, old: dict | None) -> str:
    """Returns 'write', 'unchanged' or 'older'."""
    if old is None:
        return 'write'
    if str(new['date']) < str(old.get('date', '')):
        return 'older'
    strip = lambda d: {k: v for k, v in d.items() if k != 'generatedAt'}
    return 'unchanged' if strip(new) == strip(old) else 'write'


def candidates():
    """(source name, fetch-and-parse function) in spec order."""
    for url in FAWAZ_URLS:
        yield 'fawazahmed0', lambda url=url: parse_fawaz(fetch_json(url))
    yield 'open.er-api', lambda: parse_erapi(fetch_json(ERAPI_URL))


def main() -> int:
    chosen = None
    for source, load in candidates():
        try:
            date, rates = load()
        except Exception as e:  # network error, bad JSON, missing keys
            print(f'[{source}] fetch/parse failed: {e}')
            continue
        problems = validate(date, rates)
        if problems:
            print(f'[{source}] validation failed: ' + '; '.join(problems))
            continue
        chosen = build(date, source, rates, dt.datetime.now(dt.timezone.utc))
        print(f'[{source}] ok: date={date}, {len(rates)} currencies')
        break

    if chosen is None:
        # Fail the run so it shows up red in Actions; rates.json is untouched.
        print('All sources failed. rates.json NOT updated (previous file kept).')
        return 1

    old = json.loads(OUTPUT.read_text(encoding='utf-8')) if OUTPUT.exists() else None
    verdict = decide(chosen, old)
    if verdict == 'older':
        print(f"Upstream date {chosen['date']} is older than existing {old['date']}; keeping existing file.")
        return 0
    if verdict == 'unchanged':
        print('No change; not writing.')
        return 0
    OUTPUT.write_text(json.dumps(chosen, indent=2, ensure_ascii=True) + '\n', encoding='utf-8')
    print(f'Wrote {OUTPUT.name}.')
    return 0


if __name__ == '__main__':
    sys.exit(main())
