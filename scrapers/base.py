"""Base utilities for BESS scrapers."""

import csv as csv_module
import json
import os
import time
from pathlib import Path

import pandas as pd
import requests
from bs4 import BeautifulSoup

from config import OUTPUT_DIR, DEFAULT_ENCODING

USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
)
REQUEST_TIMEOUT = 45
REQUEST_RETRIES = 3
REQUEST_BACKOFF = 2


def fetch_html_with_retry(
    url: str,
    params: dict | None = None,
    timeout: int = REQUEST_TIMEOUT,
    retries: int = REQUEST_RETRIES,
    backoff: float = REQUEST_BACKOFF,
) -> str:
    """Fetch HTML with retries and backoff. Raises on repeated failure."""
    last_err = None
    for attempt in range(retries):
        try:
            resp = requests.get(
                url,
                params=params,
                headers={"User-Agent": USER_AGENT, "Accept": "text/html,application/xhtml+xml"},
                timeout=timeout,
            )
            resp.raise_for_status()
            return resp.text
        except (requests.RequestException, requests.HTTPError) as e:
            last_err = e
            if attempt < retries - 1:
                time.sleep(backoff ** attempt)
    raise last_err


def fetch_html(url: str, params: dict | None = None) -> str:
    """Fetch HTML from URL (with retries). Raises on non-2xx."""
    return fetch_html_with_retry(url, params=params)


def requests_get_with_retry(
    url: str,
    retries: int = REQUEST_RETRIES,
    backoff: float = REQUEST_BACKOFF,
    timeout: int = REQUEST_TIMEOUT,
    **kwargs,
) -> requests.Response:
    """requests.get with retries and backoff. Raises on repeated failure."""
    last_err = None
    headers = kwargs.pop("headers", {})
    headers.setdefault("User-Agent", USER_AGENT)
    for attempt in range(retries):
        try:
            r = requests.get(url, headers=headers, timeout=timeout, **kwargs)
            r.raise_for_status()
            return r
        except (requests.RequestException, requests.HTTPError) as e:
            last_err = e
            if attempt < retries - 1:
                time.sleep(backoff ** attempt)
    raise last_err


def parse_html(html: str, parser: str = "lxml") -> BeautifulSoup:
    """Parse HTML string into BeautifulSoup."""
    return BeautifulSoup(html, parser)


def save_results(
    rows: list[dict],
    country: str,
    source: str,
    *,
    csv: bool = True,
    json_file: bool = True,
    output_dir: str | None = None,
    date_suffix: str | None = None,
) -> list[str]:
    """Save scraped rows to output/ as CSV and/or JSON. date_suffix (e.g. 2025-02-03) for weekly runs."""
    import config as cfg
    out = (output_dir or getattr(cfg, "OUTPUT_DIR", None) or OUTPUT_DIR)
    Path(out).mkdir(parents=True, exist_ok=True)
    saved = []
    safe_country = country.replace(" ", "_").lower()
    safe_source = source.replace(" ", "_").lower().replace("-", "_")
    base_name = f"bess_{safe_country}_{safe_source}"
    if date_suffix:
        base_name = f"{base_name}_{date_suffix}"

    if csv and rows:
        path = os.path.join(out, f"{base_name}.csv")
        df = pd.DataFrame(rows)
        # UTF-8 BOM so Excel opens with correct encoding; quote non-numeric so commas in text don't merge columns
        df.to_csv(
            path,
            index=False,
            encoding="utf-8-sig",
            quoting=csv_module.QUOTE_NONNUMERIC,
            date_format="%Y-%m-%dT%H:%M:%S",
        )
        saved.append(path)

    if json_file and rows:
        path = os.path.join(out, f"{base_name}.json")
        with open(path, "w", encoding=DEFAULT_ENCODING) as f:
            json.dump(rows, f, indent=2, ensure_ascii=False)
        saved.append(path)

    return saved
