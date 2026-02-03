"""
UK BESS projects scraper – EDF Renewables UK & Ireland battery storage list.
Latest projects only; outputs sites and investment scope for Elements Green (London).
Designed for weekly runs.
"""

import re
from datetime import datetime, timezone
from urllib.parse import urljoin, urlparse

from .base import fetch_html, parse_html, save_results
from config import SOURCES, INVESTMENT_OPPORTUNITY_MAP

# Statuses that represent "latest" / investment pipeline (exclude operational for pipeline focus)
LATEST_STATUSES = {"planned", "consented", "in-construction"}


def _opportunity_type(status: str) -> str:
    """Map project status to investment opportunity type."""
    key = (status or "").strip().lower().replace(" ", "-")
    return INVESTMENT_OPPORTUNITY_MAP.get(key, "")


def _parse_capacity_mw(capacity: str) -> float | None:
    """Parse capacity string (e.g. '50MW', 'c.25MW', '47.5MW') to numeric MW."""
    if not capacity or not capacity.strip():
        return None
    s = re.sub(r"^c\.?\s*", "", capacity.strip(), flags=re.IGNORECASE)
    m = re.search(r"([\d.]+)\s*MW", s, re.IGNORECASE)
    if m:
        try:
            return float(m.group(1))
        except ValueError:
            return None
    return None


def scrape_uk_edf_bess(
    save_csv: bool = True,
    save_json: bool = True,
    latest_only: bool = False,
    date_suffix: str | None = None,
) -> list[dict]:
    """
    Scrape EDF Renewables UK & Ireland battery storage projects.
    Returns list of dicts with scraped_at, capacity_mw_numeric, investment_opportunity.
    latest_only: if True, keep only Planned / Consented / In-construction (pipeline focus).
    """
    try:
        source = (SOURCES.get("uk") or {}).get("edf_re_uk") or {
            "name": "EDF Renewables UK & Ireland – Battery Storage",
            "url": "https://www.edf-re.uk/our-sites/?view=list&project_types=battery-storage",
            "country": "UK",
        }
        url = source.get("url", "")
        country = source.get("country", "UK")
        source_name = source.get("name", "EDF Renewables UK & Ireland")
        scraped_at = datetime.now(timezone.utc).isoformat()
        base_url = urlparse(url).scheme + "://" + urlparse(url).netloc if url else ""

        html = fetch_html(url)
        soup = parse_html(html)

        rows = []
        table = soup.find("table")
        if table:
            tbody = table.find("tbody") or table
            for tr in tbody.find_all("tr"):
                cells = tr.find_all("td")
                if len(cells) < 2:
                    continue
                site_cell = cells[0]
                link = site_cell.find("a")
                site_name = (link.get_text(strip=True) if link else site_cell.get_text(strip=True)) or ""
                href = link.get("href", "") if link else ""
                project_url = urljoin(base_url, href) if href else url

                status = ""
                country_val = country
                capacity = ""
                if len(cells) >= 2:
                    status = cells[1].get_text(strip=True)
                if len(cells) >= 4:
                    country_val = cells[3].get_text(strip=True) or country
                if len(cells) >= 5:
                    capacity = cells[4].get_text(strip=True) or ""

                status_key = (status or "").strip().lower().replace(" ", "-")
                if latest_only and status_key not in LATEST_STATUSES:
                    continue

                opportunity = _opportunity_type(status)
                capacity_numeric = _parse_capacity_mw(capacity)
                rows.append({
                    "scraped_at": scraped_at,
                    "country": "UK",
                    "region": country_val,
                    "site_name": site_name,
                    "capacity_mw": capacity,
                    "capacity_mw_numeric": capacity_numeric,
                    "status": status,
                    "investment_opportunity": opportunity,
                    "source": source_name,
                    "url": project_url,
                })
        if not table:
            for a in soup.select('a[href*="/our-sites/"]'):
                if latest_only:
                    continue
                href = a.get("href", "")
                if href.count("/") < 4:
                    continue
                site_name = (a.get_text(strip=True) or "").strip()
                if not site_name or len(site_name) > 200:
                    continue
                project_url = urljoin(base_url, href) if href else url
                rows.append({
                    "scraped_at": scraped_at,
                    "country": "UK",
                    "region": "",
                    "site_name": site_name,
                    "capacity_mw": "",
                    "capacity_mw_numeric": None,
                    "status": "",
                    "investment_opportunity": "",
                    "source": source_name,
                    "url": project_url,
                })

        if rows:
            save_results(
                rows, country, "edf_re_uk",
                csv=save_csv, json_file=save_json,
                date_suffix=date_suffix,
            )
        return rows
    except Exception:
        return []
