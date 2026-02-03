"""
UK BESS / Solar – UK Power Networks Embedded Capacity Register (ECR).
Distribution-connected projects (1MW+ and under 1MW) in UKPN area.
"""

import io
import re

import pandas as pd

from .base import save_results, requests_get_with_retry
from .uk_common import make_row, parse_capacity_mw
from config import SOURCES

# UKPN OpenDataSoft – ECR 1MW and above (BESS/solar relevant)
UKPN_ECR_API = "https://ukpowernetworks.opendatasoft.com/api/explore/v2.1/catalog/datasets/ukpn-embedded-capacity-register/records"
UKPN_ECR_CSV = "https://ukpowernetworks.opendatasoft.com/api/explore/v2.1/catalog/datasets/ukpn-embedded-capacity-register/exports/csv"
REQUEST_TIMEOUT = 60
USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
)


def _fetch_ukpn_ecr() -> list[dict]:
    """Fetch UKPN ECR records (CSV or API). Returns list of record dicts."""
    # Try CSV export first (simplest)
    try:
        r = requests_get_with_retry(UKPN_ECR_CSV, timeout=REQUEST_TIMEOUT, headers={"User-Agent": USER_AGENT}, params={"limit": -1})
        df = pd.read_csv(io.BytesIO(r.content), encoding="utf-8", low_memory=False)
        return df.to_dict("records")
    except Exception:
        pass
    # Try JSON API with pagination
    try:
        all_records = []
        start = 0
        limit = 100
        while True:
            r = requests_get_with_retry(
                UKPN_ECR_API,
                timeout=REQUEST_TIMEOUT,
                headers={"User-Agent": USER_AGENT},
                params={"limit": limit, "offset": start},
            )
            data = r.json()
            results = data.get("results", [])
            if not results:
                break
            for rec in results:
                # OpenDataSoft wraps in 'record' with 'fields'
                fields = rec.get("record", {}).get("fields", rec) if isinstance(rec.get("record"), dict) else rec
                if isinstance(fields, dict):
                    all_records.append(fields)
                else:
                    all_records.append(rec)
            if len(results) < limit:
                break
            start += limit
            if start > 10000:
                break
        return all_records
    except Exception:
        pass
    return []


def _find_col(record: dict, *keywords) -> str | None:
    """Return first key in record that contains all keywords (case-insensitive)."""
    keys = [k for k in record if isinstance(k, str)]
    for k in keys:
        lower = k.lower()
        if all(w in lower for w in keywords):
            return k
    return None


def scrape_uk_ecr_ukpn(
    save_csv: bool = True,
    save_json: bool = True,
    date_suffix: str | None = None,
) -> list[dict]:
    """Scrape UKPN Embedded Capacity Register. Returns list of standard rows."""
    source = SOURCES["uk"].get("ecr_ukpn") or {
        "name": "UK Power Networks – Embedded Capacity Register (ECR)",
        "url": "https://ukpowernetworks.opendatasoft.com/explore/dataset/ukpn-embedded-capacity-register",
        "country": "UK",
    }
    country = source["country"]
    source_name = source["name"]

    records = _fetch_ukpn_ecr()
    if not records:
        return []

    # Infer column names from first record
    sample = records[0]
    name_col = _find_col(sample, "site") or _find_col(sample, "name") or _find_col(sample, "project") or _find_col(sample, "customer")
    cap_col = _find_col(sample, "capacity") or _find_col(sample, "mw") or _find_col(sample, "export")
    tech_col = _find_col(sample, "technology") or _find_col(sample, "type") or _find_col(sample, "energy")
    region_col = _find_col(sample, "region") or _find_col(sample, "primary") or _find_col(sample, "substation")

    rows = []
    seen = set()
    for rec in records:
        name = ""
        if name_col and name_col in rec:
            name = str(rec[name_col]).strip()
        if not name or name == "nan":
            continue
        key = (name.lower(), rec.get(cap_col) if cap_col else None)
        if key in seen:
            continue
        seen.add(key)
        cap_val = rec.get(cap_col) if cap_col else None
        try:
            capacity_mw_numeric = float(cap_val) if cap_val is not None and str(cap_val) != "nan" else None
        except (TypeError, ValueError):
            capacity_mw_numeric = parse_capacity_mw(str(cap_val)) if cap_val else None
        capacity_mw = f"{capacity_mw_numeric} MW" if capacity_mw_numeric is not None else ""
        region = str(rec.get(region_col, "")).strip() if region_col else ""
        if region == "nan":
            region = ""
        # ECR = distribution connection; treat as Consented/Operational depending on data
        status = "Consented"
        row = make_row(
            site_name=name,
            source_name=source_name,
            url=source.get("url") or UKPN_ECR_CSV,
            region=region,
            capacity_mw=capacity_mw,
            capacity_mw_numeric=capacity_mw_numeric,
            status=status,
        )
        rows.append(row)

    if rows:
        save_results(rows, country, "ecr_ukpn", csv=save_csv, json_file=save_json, date_suffix=date_suffix)
    return rows
