"""
UK BESS – British Solar Renewables battery storage projects page.
"""

import re

from .base import fetch_html, parse_html, save_results
from .uk_common import make_row, parse_capacity_mw
from config import SOURCES


def scrape_uk_british_renewables(
    save_csv: bool = True,
    save_json: bool = True,
    date_suffix: str | None = None,
) -> list[dict]:
    """Scrape British Renewables battery projects (Fareham, Fideoak, Stocking Pelham, etc.)."""
    try:
        source = (SOURCES.get("uk") or {}).get("british_renewables") or {
            "name": "British Solar Renewables – UK Battery Storage",
            "url": "https://britishrenewables.com/projects/battery-bess-projects",
            "country": "UK",
        }
        url = source.get("url", "")
        country = source.get("country", "UK")
        source_name = source.get("name", "British Solar Renewables")

        html = fetch_html(url)
        soup = parse_html(html)
        rows = []
        seen_names = set()

        # Primary: h2 with "battery" (e.g. "Fareham Battery, Hampshire") and sibling with capacity
        for h2 in soup.find_all(["h2", "h3"]):
            text = (h2.get_text(strip=True) or "").strip()
            if "battery" not in text.lower() and "bess" not in text.lower():
                continue
            name = text.replace("Our Battery Projects", "").replace("Battery Projects", "").strip()
            if not name or len(name) < 3:
                continue
            region = ""
            if "," in name:
                parts = name.split(",", 1)
                name, region = parts[0].strip(), (parts[1].strip() if len(parts) > 1 else "")
            cap_text = ""
            for sib in h2.find_next_siblings():
                if getattr(sib, "name", None) in ("h2", "h3"):
                    break
                t = sib.get_text() if hasattr(sib, "get_text") else str(sib)
                if "capacity" in t.lower() or " MW" in t or "MWh" in t or "MW" in t:
                    m = re.search(r"([\d.]+)\s*MW", t, re.IGNORECASE)
                    if m:
                        cap_text = m.group(0)
                        break
            num = parse_capacity_mw(cap_text) if cap_text else None
            key = (name.lower(), num)
            if key in seen_names:
                continue
            seen_names.add(key)
            rows.append(make_row(
                site_name=name,
                source_name=source_name,
                url=url,
                region=region,
                capacity_mw=cap_text or "",
                capacity_mw_numeric=num,
                status="Operational",
            ))

        # Fallback: any block with "MW" and battery-like name
        if not rows:
            for el in soup.find_all(["div", "section", "article"]):
                t = (el.get_text() or "").strip()
                if " MW" not in t or ("battery" not in t.lower() and "bess" not in t.lower()):
                    continue
                m = re.search(r"([\d.]+)\s*MW", t, re.IGNORECASE)
                cap_text = m.group(0) if m else ""
                for h in el.find_all(["h2", "h3", "h4", "strong"]):
                    name = (h.get_text(strip=True) or "").strip()
                    if len(name) < 4 or len(name) > 120:
                        continue
                    if (name.lower(), parse_capacity_mw(cap_text)) in seen_names:
                        continue
                    seen_names.add((name.lower(), parse_capacity_mw(cap_text)))
                    rows.append(make_row(
                        site_name=name,
                        source_name=source_name,
                        url=url,
                        region="",
                        capacity_mw=cap_text,
                        capacity_mw_numeric=parse_capacity_mw(cap_text),
                        status="Operational",
                    ))
                    if len(rows) >= 20:
                        break
                if len(rows) >= 20:
                    break

        if rows:
            save_results(rows, country, "british_renewables", csv=save_csv, json_file=save_json, date_suffix=date_suffix)
        return rows
    except Exception:
        return []
