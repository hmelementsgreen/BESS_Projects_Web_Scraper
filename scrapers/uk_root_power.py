"""
UK BESS – Root Power our-projects page (BESS portfolio).
"""

import re
from urllib.parse import urljoin

from .base import fetch_html, parse_html, save_results
from .uk_common import make_row, parse_capacity_mw
from config import SOURCES

BASE = "https://www.root-power.com"


def scrape_uk_root_power(
    save_csv: bool = True,
    save_json: bool = True,
    date_suffix: str | None = None,
) -> list[dict]:
    """Scrape Root Power BESS projects (Site Name, Size, Status)."""
    try:
        source = (SOURCES.get("uk") or {}).get("root_power") or {"name": "Root Power – BESS Projects", "url": "https://www.root-power.com/our-projects/", "country": "UK"}
        url = source.get("url", BASE)
        country = source.get("country", "UK")
        source_name = source.get("name", "Root Power")

        html = fetch_html(url)
        soup = parse_html(html)
        rows = []
        seen = set()

        # Primary: links to /projects/ or /our-projects/ with BESS
        for a in soup.find_all("a", href=True):
            href = a.get("href", "")
            if "/projects/" not in href and "/our-projects/" not in href:
                continue
            if "bess" not in href.lower() and "battery" not in href.lower():
                txt = (a.get_text(strip=True) or "").lower()
                if "bess" not in txt and "battery" not in txt and "mw" not in txt:
                    continue
            project_url = urljoin(BASE, href)
            link_text = (a.get_text(strip=True) or "").strip()
            name = link_text
            cap_str = ""
            m = re.search(r"([\d.]+)\s*MW", link_text, re.IGNORECASE)
            if m:
                cap_str = m.group(0)
                name = re.sub(r"\s*[—–-]\s*[\d.]+\s*MW\s*$", "", link_text, flags=re.IGNORECASE).strip()
            if not name or len(name) > 150:
                continue
            key = (name.lower()[:80], cap_str)
            if key in seen:
                continue
            seen.add(key)
            parent = a.find_parent("article") or a.find_parent("div", class_=re.compile(r"project|card|item")) or a.find_parent("li")
            status = ""
            if parent:
                for p in parent.find_all(["p", "span", "div"]):
                    t = (p.get_text(strip=True) or "").strip()
                    if "MW" in t and not cap_str:
                        mm = re.search(r"([\d.]+)\s*MW", t)
                        if mm:
                            cap_str = mm.group(0)
                    if any(x in t.lower() for x in ("construction", "consented", "advanced", "planning", "energised", "operational")):
                        status = t[:80]
                        break
            num = parse_capacity_mw(cap_str) if cap_str else None
            rows.append(make_row(
                site_name=name,
                source_name=source_name,
                url=project_url,
                capacity_mw=cap_str or "",
                capacity_mw_numeric=num,
                status=status,
            ))

        if rows:
            save_results(rows, country, "root_power", csv=save_csv, json_file=save_json, date_suffix=date_suffix)
        return rows
    except Exception:
        return []
