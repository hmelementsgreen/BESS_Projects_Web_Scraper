"""
UK BESS – DESNZ Renewable Energy Planning Database (REPD).
Fetches latest quarterly CSV from gov.uk and filters for electricity storage projects.
"""

import io
import re
from urllib.parse import urljoin

import pandas as pd

from .base import fetch_html, fetch_html_with_retry, parse_html, requests_get_with_retry, save_results
from .uk_common import make_row, normalise_status
from config import SOURCES

REPD_PUBLICATION_URL = "https://www.gov.uk/government/publications/renewable-energy-planning-database-monthly-extract"
ASSETS_BASE = "https://assets.publishing.service.gov.uk"
REQUEST_TIMEOUT = 60
USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
)


def _find_latest_csv_url() -> str | None:
    """Get the latest REPD CSV download link from the gov.uk publication page."""
    html = fetch_html_with_retry(REPD_PUBLICATION_URL, timeout=60)
    soup = parse_html(html)
    candidates = []
    for a in soup.find_all("a", href=True):
        href = (a.get("href") or "").strip()
        if not href.endswith(".csv"):
            continue
        if "REPD" in href.upper() or "renewable" in href.lower() or "planning" in href.lower():
            full = href if href.startswith("http") else (urljoin("https://www.gov.uk", href) if href.startswith("/") else urljoin(ASSETS_BASE, href))
            candidates.append(full)
    if candidates:
        return candidates[0]
    for a in soup.find_all("a", href=True):
        href = (a.get("href") or "").strip()
        if href.endswith(".csv") and ("gov" in href or "publishing" in href):
            full = href if href.startswith("http") else (urljoin("https://www.gov.uk", href) if href.startswith("/") else urljoin(ASSETS_BASE, href))
            return full
    return None


def _download_csv(url: str) -> pd.DataFrame:
    """Download CSV and return as DataFrame. Tries utf-8, then latin-1/cp1252 for gov.uk files."""
    resp = requests_get_with_retry(url, timeout=REQUEST_TIMEOUT, headers={"User-Agent": USER_AGENT})
    raw = resp.content
    for enc in ("utf-8", "utf-8-sig", "latin-1", "cp1252"):
        try:
            return pd.read_csv(io.BytesIO(raw), encoding=enc, low_memory=False)
        except UnicodeDecodeError:
            continue
    return pd.read_csv(io.BytesIO(raw), encoding="latin-1", low_memory=False)


def scrape_uk_repd(
    save_csv: bool = True,
    save_json: bool = True,
    date_suffix: str | None = None,
) -> list[dict]:
    """Scrape UK REPD for electricity storage projects. Returns list of standard rows."""
    try:
        source = (SOURCES.get("uk") or {}).get("uk_repd") or {
            "name": "DESNZ – Renewable Energy Planning Database (REPD)",
            "url": REPD_PUBLICATION_URL,
            "country": "UK",
        }
        country = source.get("country", "UK")
        source_name = source.get("name", "REPD")

        csv_url = _find_latest_csv_url()
        if not csv_url:
            return []

        df = _download_csv(csv_url)
        def find_col(*keywords):
            for c in df.columns:
                k = c.strip().lower()
                if all(w in k for w in keywords):
                    return c
            return None

        tech_col = find_col("technology", "type")
        if not tech_col:
            return []

        tech_vals = df[tech_col].astype(str).str.lower()
        storage_mask = tech_vals.str.contains("storage", na=False)
        df = df.loc[storage_mask].copy()
        if df.empty:
            return []

        site_col = find_col("site", "name") or find_col("project", "name") or find_col("name") or find_col("ref")
        if not site_col and len(df.columns):
            site_col = df.columns[0]
        cap_col = find_col("installed", "capacity") or find_col("capacity", "mwelec") or find_col("capacity")
        status_col = find_col("development", "status", "short") or find_col("development", "status") or find_col("status")
        region_col = find_col("region") or find_col("county")
        country_col = find_col("country")

        rows = []
        for _, r in df.iterrows():
            site_name = str(r[site_col]).strip() if site_col and site_col in r.index else ""
            if not site_name or site_name == "nan":
                continue
            cap_val = r[cap_col] if cap_col and cap_col in r.index else None
            try:
                capacity_mw_numeric = float(cap_val) if cap_val is not None and str(cap_val) != "nan" else None
            except (TypeError, ValueError):
                capacity_mw_numeric = None
            capacity_mw = f"{capacity_mw_numeric} MW" if capacity_mw_numeric is not None else ""
            status = str(r[status_col]).strip() if status_col and status_col in r.index else ""
            region = str(r[region_col]).strip() if region_col and region_col in r.index else ""
            country_val = str(r[country_col]).strip() if country_col and country_col in r.index else "UK"
            if region == "nan":
                region = ""
            if country_val == "nan":
                country_val = "UK"
            std_status, _ = normalise_status(status)
            row = make_row(
                site_name=site_name,
                source_name=source_name,
                url=REPD_PUBLICATION_URL,
                region=region,
                capacity_mw=capacity_mw,
                capacity_mw_numeric=capacity_mw_numeric,
                status=std_status,
            )
            row["country"] = country_val
            rows.append(row)

        if rows:
            save_results(rows, country, "uk_repd", csv=save_csv, json_file=save_json, date_suffix=date_suffix)
        return rows
    except Exception:
        return []
