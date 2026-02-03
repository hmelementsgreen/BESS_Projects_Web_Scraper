"""
UK BESS / Grid – NESO (National Grid ESO) TEC Register.
Transmission Entry Capacity: projects with grid connection agreements.
"""

import io
import re
from urllib.parse import urljoin

import pandas as pd

from .base import save_results, requests_get_with_retry
from .uk_common import make_row, parse_capacity_mw
from config import SOURCES

TEC_PORTAL_URL = "https://www.nationalgrideso.com/data-portal/transmission-entry-capacity-tec-register"
# NESO CKAN-style API (dataset UUID from data portal)
TEC_API_BASE = "https://api.nationalgrideso.com"
TEC_PACKAGE_ID = "cbd45e54-e6e2-4a38-99f1-8de6fd96d7c1"
# Fallback: known resource ID for CSV (filename date may vary)
TEC_RESOURCE_ID = "17becbab-e3e8-473f-b303-3806f43a6a10"
TEC_FALLBACK_CSV = f"{TEC_API_BASE}/dataset/{TEC_PACKAGE_ID}/resource/{TEC_RESOURCE_ID}/download/tec-register.csv"
REQUEST_TIMEOUT = 60
USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
)


def _get_tec_csv_url() -> str | None:
    """Get latest TEC Register CSV URL from NESO API or portal page."""
    # Try CKAN package_show to get resource list
    try:
        r = requests_get_with_retry(
            f"{TEC_API_BASE}/api/3/action/package_show",
            params={"id": TEC_PACKAGE_ID},
            timeout=REQUEST_TIMEOUT,
            headers={"User-Agent": USER_AGENT},
        )
        data = r.json()
        if not data.get("success") or not data.get("result"):
            return None
        resources = data.get("result", {}).get("resources", [])
        csv_resources = [res for res in resources if (res.get("format") or "").upper() == "CSV"]
        if not csv_resources:
            return None
        # Prefer resource with download URL
        for res in sorted(csv_resources, key=lambda x: x.get("created", ""), reverse=True):
            url = res.get("url") or res.get("url_type")
            if url:
                return url
            # Build download URL if we have resource id
            rid = res.get("id")
            if rid:
                return f"{TEC_API_BASE}/dataset/{TEC_PACKAGE_ID}/resource/{rid}/download/tec-register.csv"
        return None
    except Exception:
        pass
    # Fallback: fetch portal HTML and look for CSV link
    try:
        from .base import fetch_html, parse_html
        html = fetch_html(TEC_PORTAL_URL)
        soup = parse_html(html)
        for a in soup.find_all("a", href=True):
            href = (a.get("href") or "").strip()
            if "tec" in href.lower() and (href.endswith(".csv") or "download" in href.lower()):
                if href.startswith("http"):
                    return href
                return urljoin(TEC_PORTAL_URL, href)
    except Exception:
        pass
    # Fallback: try known resource download (may redirect to dated file)
    try:
        r = requests_get_with_retry(TEC_FALLBACK_CSV, timeout=20, headers={"User-Agent": USER_AGENT})
        if r.ok:
            return r.url or TEC_FALLBACK_CSV
    except Exception:
        pass
    return None


def _download_csv(url: str) -> pd.DataFrame:
    """Download CSV and return as DataFrame."""
    resp = requests_get_with_retry(url, timeout=REQUEST_TIMEOUT, headers={"User-Agent": USER_AGENT})
    raw = resp.content
    for enc in ("utf-8", "utf-8-sig", "latin-1", "cp1252"):
        try:
            return pd.read_csv(io.BytesIO(raw), encoding=enc, low_memory=False)
        except UnicodeDecodeError:
            continue
    return pd.read_csv(io.BytesIO(raw), encoding="latin-1", low_memory=False)


def scrape_uk_tec_register(
    save_csv: bool = True,
    save_json: bool = True,
    date_suffix: str | None = None,
) -> list[dict]:
    """Scrape NESO TEC Register for transmission-connected projects. Returns list of standard rows."""
    source = SOURCES["uk"].get("tec_register") or {
        "name": "NESO – TEC Register (Transmission Entry Capacity)",
        "url": TEC_PORTAL_URL,
        "country": "UK",
    }
    country = source["country"]
    source_name = source["name"]

    csv_url = _get_tec_csv_url()
    if not csv_url:
        return []

    df = _download_csv(csv_url)
    # TEC columns vary; common names: Project Name, ProjectName, Capacity (MW), Technology Type, etc.
    def find_col(*keywords):
        for c in df.columns:
            k = str(c).strip().lower()
            if all(w in k for w in keywords):
                return c
        return None

    name_col = find_col("project", "name") or find_col("name") or find_col("project")
    cap_col = find_col("capacity") or find_col("tec") or find_col("mw")
    tech_col = find_col("technology") or find_col("tech")
    region_col = find_col("region") or find_col("zone") or find_col("area")

    rows = []
    for _, r in df.iterrows():
        site_name = ""
        if name_col and name_col in r.index:
            site_name = str(r[name_col]).strip()
        if not site_name or site_name == "nan":
            continue
        cap_val = r[cap_col] if cap_col and cap_col in r.index else None
        try:
            capacity_mw_numeric = float(cap_val) if cap_val is not None and str(cap_val) != "nan" else None
        except (TypeError, ValueError):
            capacity_mw_numeric = parse_capacity_mw(str(cap_val)) if cap_val else None
        capacity_mw = f"{capacity_mw_numeric} MW" if capacity_mw_numeric is not None else ""
        region = ""
        if region_col and region_col in r.index:
            region = str(r[region_col]).strip()
        if region == "nan":
            region = ""
        # TEC = grid connection agreement; treat as Consented / early-stage for investment mapping
        status = "Consented"
        row = make_row(
            site_name=site_name,
            source_name=source_name,
            url=TEC_PORTAL_URL,
            region=region,
            capacity_mw=capacity_mw,
            capacity_mw_numeric=capacity_mw_numeric,
            status=status,
        )
        rows.append(row)

    if rows:
        save_results(rows, country, "tec_register", csv=save_csv, json_file=save_json, date_suffix=date_suffix)
    return rows
