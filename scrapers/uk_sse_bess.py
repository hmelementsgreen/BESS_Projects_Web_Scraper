"""
UK BESS – SSE Renewables our-sites (filter for BESS entries).
"""

import re
from urllib.parse import urljoin

from .base import fetch_html, parse_html, save_results
from .uk_common import make_row, parse_capacity_mw, normalise_status
from config import SOURCES

BASE = "https://www.sserenewables.com"


def scrape_uk_sse_bess(
    save_csv: bool = True,
    save_json: bool = True,
    date_suffix: str | None = None,
) -> list[dict]:
    """Scrape SSE Renewables site list for BESS projects."""
    try:
        source = (SOURCES.get("uk") or {}).get("sse_renewables") or {"name": "SSE Renewables – Battery Storage", "url": "https://www.sserenewables.com/our-sites/", "country": "UK"}
        url = source.get("url", BASE)
        country = source.get("country", "UK")
        source_name = source.get("name", "SSE Renewables")

        html = fetch_html(url)
        soup = parse_html(html)
        rows = []
        seen = set()

        # Primary: links with "BESS" or "battery" and capacity in parent/sibling
        for a in soup.find_all("a", href=True):
            link_text = (a.get_text(strip=True) or "").strip()
            href = a.get("href", "")
            if not href or href.startswith("#"):
                continue
            if "BESS" not in link_text and "battery" not in link_text.lower() and "storage" not in link_text.lower():
                continue
            project_url = urljoin(BASE, href)
            name = link_text
            if not name or len(name) > 200:
                continue
            key = (name.lower()[:80], href)
            if key in seen:
                continue
            seen.add(key)
            cap_str = ""
            parent = a.find_parent()
            for _ in range(6):
                if not parent:
                    break
                t = parent.get_text() if hasattr(parent, "get_text") else ""
                m = re.search(r"(\d+(?:\.\d+)?)\s*MW\s*(?:/\s*\d+\s*MWh)?", t)
                if m:
                    cap_str = m.group(1) + " MW"
                    break
                parent = parent.find_parent() if hasattr(parent, "find_parent") else None
            num = parse_capacity_mw(cap_str) if cap_str else None
            status = "Planned"
            if parent and hasattr(parent, "get_text"):
                pt = parent.get_text().lower()
                if "operational" in pt or "energised" in pt:
                    status = "Operational"
                elif "construction" in pt:
                    status = "In-construction"
                elif "consent" in pt:
                    status = "Consented"
            std_status, _ = normalise_status(status)
            rows.append(make_row(
                site_name=name,
                source_name=source_name,
                url=project_url,
                capacity_mw=cap_str or "",
                capacity_mw_numeric=num,
                status=std_status,
            ))

        # Fallback: any link to /our-sites/ or /sites/ with MW in surrounding text
        if not rows:
            for a in soup.find_all("a", href=True):
                href = a.get("href", "")
                if "/our-sites/" not in href and "/sites/" not in href:
                    continue
                name = (a.get_text(strip=True) or "").strip()
                if not name or len(name) > 200:
                    continue
                parent = a.find_parent()
                cap_str = ""
                for _ in range(5):
                    if not parent:
                        break
                    t = parent.get_text() if hasattr(parent, "get_text") else ""
                    if re.search(r"\d+\s*MW", t):
                        mm = re.search(r"(\d+(?:\.\d+)?)\s*MW", t)
                        cap_str = (mm.group(1) + " MW") if mm else ""
                        break
                    parent = parent.find_parent() if hasattr(parent, "find_parent") else None
                if (name.lower()[:80], href) in seen:
                    continue
                seen.add((name.lower()[:80], href))
                rows.append(make_row(
                    site_name=name,
                    source_name=source_name,
                    url=urljoin(BASE, href),
                    capacity_mw=cap_str,
                    capacity_mw_numeric=parse_capacity_mw(cap_str),
                    status="Planned",
                ))

        if rows:
            save_results(rows, country, "sse_renewables", csv=save_csv, json_file=save_json, date_suffix=date_suffix)
        return rows
    except Exception:
        return []
