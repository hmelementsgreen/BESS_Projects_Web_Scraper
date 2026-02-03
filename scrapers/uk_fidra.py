"""
UK BESS – Fidra Energy our-projects (Thorpe Marsh, West Burton C, Bicker Fen).
"""

import re

from .base import fetch_html, parse_html, save_results
from .uk_common import make_row, parse_capacity_mw
from config import SOURCES


def scrape_uk_fidra(
    save_csv: bool = True,
    save_json: bool = True,
    date_suffix: str | None = None,
) -> list[dict]:
    """Scrape Fidra Energy UK BESS projects."""
    try:
        source = (SOURCES.get("uk") or {}).get("fidra_energy") or {"name": "Fidra Energy – UK Energy Storage", "url": "https://fidraenergy.com/our-projects/", "country": "UK"}
        url = source.get("url", "")
        country = source.get("country", "UK")
        source_name = source.get("name", "Fidra Energy")

        html = fetch_html(url)
        soup = parse_html(html)
        rows = []
        seen = set()

        # Primary: headings with project names (Thorpe Marsh, West Burton, Bicker Fen) + Size/Location in siblings
        for h in soup.find_all(["h1", "h2", "h3", "h4"]):
            text = (h.get_text(strip=True) or "").strip()
            if not text or len(text) < 3:
                continue
            name = re.sub(r"\s*\*\*$", "", text.replace("**", "").strip())
            if not name or len(name) > 120:
                continue
            region = ""
            cap_str = ""
            for sib in h.find_next_siblings():
                if getattr(sib, "name", None) in ("h1", "h2", "h3", "h4"):
                    break
                t = sib.get_text() if hasattr(sib, "get_text") else ""
                if "Size:" in t or "GW" in t or "MW" in t or "GWh" in t:
                    m = re.search(r"([\d.]+)\s*(GW|MW|GWh|MWh)", t, re.IGNORECASE)
                    if m:
                        cap_str = m.group(0)
                if "Location:" in t:
                    region = t.replace("Location:", "").strip().split("\n")[0].strip()[:80]
            num = parse_capacity_mw(cap_str) if cap_str else None
            key = name.lower()[:60]
            if key in seen:
                continue
            seen.add(key)
            rows.append(make_row(
                site_name=name,
                source_name=source_name,
                url=url,
                region=region,
                capacity_mw=cap_str or "",
                capacity_mw_numeric=num,
                status="Planned",
            ))

        # Fallback: any text block with "GW" or "MW" and a short heading-like line
        if not rows:
            for el in soup.find_all(["div", "section"]):
                t = el.get_text() if hasattr(el, "get_text") else ""
                if "Thorpe" not in t and "West Burton" not in t and "Bicker" not in t and "storage" not in t.lower():
                    continue
                m = re.search(r"([\d.]+)\s*(GW|MW)", t, re.IGNORECASE)
                cap_str = m.group(0) if m else ""
                for h in el.find_all(["h2", "h3", "strong"]):
                    name = (h.get_text(strip=True) or "").strip()
                    key = name.lower()[:60]
                    if 3 <= len(name) <= 80 and key not in seen:
                        seen.add(key)
                        rows.append(make_row(
                            site_name=name,
                            source_name=source_name,
                            url=url,
                            region="",
                            capacity_mw=cap_str,
                            capacity_mw_numeric=parse_capacity_mw(cap_str),
                            status="Planned",
                        ))
                    if len(rows) >= 15:
                        break
                if len(rows) >= 15:
                    break

        if rows:
            save_results(rows, country, "fidra_energy", csv=save_csv, json_file=save_json, date_suffix=date_suffix)
        return rows
    except Exception:
        return []
