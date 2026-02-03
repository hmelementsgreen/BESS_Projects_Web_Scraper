"""
Germany BESS projects scraper – ECO STOR Storage Monitor (MaStR-based).
Large-scale battery storage >1 MW. Outputs sites and investment opportunity tags.
"""

import re

from .base import fetch_html, parse_html, save_results
from config import SOURCES, INVESTMENT_OPPORTUNITY_MAP

SOURCE_KEY = "eco_stor_monitor"


def _opportunity_type(status: str) -> str:
    """Map operation status to investment opportunity type."""
    s = (status or "").strip().lower()
    if "operation" in s or "in operation" in s:
        return INVESTMENT_OPPORTUNITY_MAP.get("in operation", "M&A / offtake / operations")
    if "planned" in s or "construction" in s:
        return "Construction / finance" if "construction" in s else "Early-stage development"
    return INVESTMENT_OPPORTUNITY_MAP.get(s, "")


def _parse_number(text: str) -> str:
    """Extract numeric value from cell text (e.g. '1.125' or '1.82')."""
    if not text:
        return ""
    text = text.strip().replace(",", ".")
    m = re.search(r"[\d.]+", text)
    return m.group(0) if m else text.strip()


def scrape_germany_ecostor(
    save_csv: bool = True,
    save_json: bool = True,
    max_pages: int | None = None,
) -> list[dict]:
    """
    Scrape ECO STOR Storage Monitor (Germany MaStR data).
    Returns list of dicts: unit_name, technology, power_mw, capacity_mwh, status, operator, etc.
    Note: The monitor may load data via JavaScript; if the table is empty, consider using
    browser automation (e.g. Selenium/Playwright) or MaStR API.
    """
    source = SOURCES["germany"][SOURCE_KEY]
    url = source["url"]
    country = source["country"]
    source_name = source["name"]

    html = fetch_html(url)
    soup = parse_html(html)

    rows = []
    # ECO STOR table: Unit name | Battery technology | Grid level | Gross power | Net power |
    # Effective storage capacity | Status of operation | Commissioning date | Planned commissioning date |
    # Unit operator name | Grid operator name | Feed-in
    table = soup.find("table")
    if table:
        tbody = table.find("tbody") or table
        for tr in tbody.find_all("tr"):
            cells = tr.find_all("td")
            if len(cells) < 6:
                continue
            # Map columns by typical order (may need adjustment if site structure differs)
            unit_name = cells[0].get_text(strip=True) if len(cells) > 0 else ""
            technology = cells[1].get_text(strip=True) if len(cells) > 1 else ""
            grid_level = cells[2].get_text(strip=True) if len(cells) > 2 else ""
            gross_power = _parse_number(cells[3].get_text()) if len(cells) > 3 else ""
            net_power = _parse_number(cells[4].get_text()) if len(cells) > 4 else ""
            capacity_mwh = _parse_number(cells[5].get_text()) if len(cells) > 5 else ""
            status = cells[6].get_text(strip=True) if len(cells) > 6 else ""
            commissioning_date = cells[7].get_text(strip=True) if len(cells) > 7 else ""
            planned_date = cells[8].get_text(strip=True) if len(cells) > 8 else ""
            operator = cells[9].get_text(strip=True) if len(cells) > 9 else ""
            grid_operator = cells[10].get_text(strip=True) if len(cells) > 10 else ""
            feed_in = cells[11].get_text(strip=True) if len(cells) > 11 else ""

            opportunity = _opportunity_type(status)
            rows.append({
                "country": "Germany",
                "site_name": unit_name,
                "battery_technology": technology,
                "grid_level": grid_level,
                "power_mw": gross_power or net_power,
                "capacity_mwh": capacity_mwh,
                "status": status,
                "commissioning_date": commissioning_date,
                "planned_commissioning_date": planned_date,
                "operator": operator,
                "grid_operator": grid_operator,
                "feed_in": feed_in,
                "investment_opportunity": opportunity,
                "source": source_name,
                "url": url,
            })

    if rows:
        save_results(rows, country, "eco_stor_monitor", csv=save_csv, json_file=save_json)

    return rows
