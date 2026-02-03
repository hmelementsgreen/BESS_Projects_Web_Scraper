"""
UK BESS / Solar – Solar Power Portal latest headlines (UK solar & storage news).
"""

import re
from datetime import datetime, timezone

from .base import fetch_html, parse_html, save_results
from .uk_common import make_row, parse_capacity_mw
from config import SOURCES

BASE_URL = "https://www.solarpowerportal.co.uk"
# Try battery/energy-storage section; fallback to homepage
BATTERY_SECTIONS = [
    "https://www.solarpowerportal.co.uk/energy-storage/battery-storage",
    "https://www.solarpowerportal.co.uk/energy-storage",
    "https://www.solarpowerportal.co.uk/keyword/battery-storage",
    "https://www.solarpowerportal.co.uk",
]
MAX_ARTICLES = 25


def scrape_uk_news_solar_portal(
    save_csv: bool = True,
    save_json: bool = True,
    date_suffix: str | None = None,
) -> list[dict]:
    """Scrape Solar Power Portal for battery storage / UK solar headlines."""
    try:
        source = (SOURCES.get("uk") or {}).get("solar_power_portal") or {"name": "Solar Power Portal – UK battery storage", "url": BASE_URL, "country": "UK"}
        country = source.get("country", "UK")
        source_name = source.get("name", "Solar Power Portal")

        html = None
        url = BASE_URL
        for try_url in BATTERY_SECTIONS:
            try:
                html = fetch_html(try_url)
                url = try_url
                break
            except Exception:
                continue
        if not html:
            return []
        soup = parse_html(html)
        rows = []
        scraped_at = datetime.now(timezone.utc).isoformat()
        seen = set()

        for a in soup.find_all("a", href=True):
            href = (a.get("href") or "").strip()
            if "solarpowerportal.co.uk" not in href:
                continue
            if href in seen or "/tag/" in href or "/author/" in href or "/page/" in href or "/category/" in href:
                continue
            title = (a.get_text(strip=True) or "").strip()
            if len(title) < 10 or len(title) > 280:
                continue
            # Keep articles about solar, storage, battery, renewable, or capacity (MW)
            tl = title.lower()
            if not any(k in tl for k in ("battery", "storage", "solar", "renewable", "pv", "mw", "grid", "energy")):
                continue
            seen.add(href)
            full_url = href if href.startswith("http") else f"{BASE_URL}{href}"
            m = re.search(r"[\d.]+\s*MW|[\d.]+\s*GW|[\d.]+\s*MWh", title, re.IGNORECASE)
            cap_str = m.group(0) if m else ""
            cap_num = parse_capacity_mw(cap_str) if cap_str else None
            row = make_row(
                site_name=title,
                source_name=source_name,
                url=full_url,
                capacity_mw=cap_str,
                capacity_mw_numeric=cap_num,
                status="News",
            )
            row["scraped_at"] = scraped_at
            rows.append(row)
            if len(rows) >= MAX_ARTICLES:
                break

        if rows:
            save_results(rows, country, "solar_power_portal", csv=save_csv, json_file=save_json, date_suffix=date_suffix)
        return rows
    except Exception:
        return []
