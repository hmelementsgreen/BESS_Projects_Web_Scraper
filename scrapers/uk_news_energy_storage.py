"""
UK BESS – Energy-Storage.news latest headlines (deal/news intelligence).
Outputs article titles, dates, URLs as rows for latest opportunity signals.
"""

import re
from datetime import datetime, timezone

from .base import fetch_html, parse_html, save_results
from .uk_common import make_row, parse_capacity_mw
from config import SOURCES

BASE_URL = "https://www.energy-storage.news"
NEWS_URL = "https://www.energy-storage.news/category/news/"
MAX_ARTICLES = 30
UK_KEYWORDS = ("uk", "britain", "british", "england", "scotland", "wales", "ireland")


def scrape_uk_news_energy_storage(
    save_csv: bool = True,
    save_json: bool = True,
    date_suffix: str | None = None,
    uk_only: bool = False,
) -> list[dict]:
    """Scrape Energy-Storage.news for latest articles. If uk_only, keep only UK-relevant headlines."""
    try:
        source = (SOURCES.get("uk") or {}).get("energy_storage_news") or {"name": "Energy-Storage.news – UK BESS news", "url": NEWS_URL, "country": "UK"}
        country = source.get("country", "UK")
        source_name = source.get("name", "Energy-Storage.news")

        try:
            html = fetch_html(NEWS_URL)
        except Exception:
            html = fetch_html(BASE_URL)
        soup = parse_html(html)
        rows = []
        scraped_at = datetime.now(timezone.utc).isoformat()
        seen_hrefs = set()

        # Articles: links to article pages (exclude nav, category, newsletter)
        for a in soup.find_all("a", href=True):
            href = (a.get("href") or "").strip()
            if not href or href in seen_hrefs:
                continue
            if "energy-storage.news" not in href:
                continue
            if "/category/" in href or "/newsletter/" in href or "/premium/" in href or "/tag/" in href or "/author/" in href:
                continue
            if href.count("/") < 4:
                continue
            title = (a.get_text(strip=True) or "").strip()
            if len(title) < 12 or len(title) > 300:
                continue
            seen_hrefs.add(href)
            if uk_only:
                t_lower = title.lower()
                if not any(k in t_lower for k in UK_KEYWORDS):
                    continue
            cap_str = ""
            m = re.search(r"[\d.]+\s*MW|[\d.]+\s*GWh|[\d.]+\s*MWh", title, re.IGNORECASE)
            if m:
                cap_str = m.group(0)
            cap_num = parse_capacity_mw(cap_str) if cap_str else None
            row = make_row(
                site_name=title,
                source_name=source_name,
                url=href if href.startswith("http") else f"{BASE_URL}{href}",
                capacity_mw=cap_str,
                capacity_mw_numeric=cap_num,
                status="News",
            )
            row["scraped_at"] = scraped_at
            rows.append(row)
            if len(rows) >= MAX_ARTICLES:
                break

        # Fallback: any link with long-enough text that looks like a headline
        if not rows:
            for a in soup.find_all("a", href=True):
                href = (a.get("href") or "").strip()
                if "energy-storage.news" not in href or "/category/" in href or "/newsletter/" in href:
                    continue
                title = (a.get_text(strip=True) or "").strip()
                if 15 <= len(title) <= 280 and ("storage" in title.lower() or "battery" in title.lower() or "MW" in title or "GWh" in title):
                    full_url = href if href.startswith("http") else f"{BASE_URL}{href}"
                    cap_str = ""
                    m = re.search(r"[\d.]+\s*MW|[\d.]+\s*GWh|[\d.]+\s*MWh", title, re.IGNORECASE)
                    if m:
                        cap_str = m.group(0)
                    rows.append(make_row(
                        site_name=title,
                        source_name=source_name,
                        url=full_url,
                        capacity_mw=cap_str,
                        capacity_mw_numeric=parse_capacity_mw(cap_str) if cap_str else None,
                        status="News",
                    ))
                    if len(rows) >= MAX_ARTICLES:
                        break

        if rows:
            save_results(rows, country, "energy_storage_news", csv=save_csv, json_file=save_json, date_suffix=date_suffix)
        return rows
    except Exception:
        return []
