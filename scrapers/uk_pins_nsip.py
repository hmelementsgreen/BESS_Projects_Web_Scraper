"""
UK BESS / Solar – Planning Inspectorate (PINS) NSIP register.
Nationally Significant Infrastructure Projects (>50MW solar, etc.).
"""

import re
from urllib.parse import urljoin

from .base import fetch_html, parse_html, requests_get_with_retry, save_results
from .uk_common import make_row, parse_capacity_mw, normalise_status
from config import SOURCES

PINS_SEARCH_URL = "https://national-infrastructure-consenting.planninginspectorate.gov.uk/project-search"
PINS_BASE = "https://national-infrastructure-consenting.planninginspectorate.gov.uk"
REQUEST_TIMEOUT = 45
USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
)


def _fetch_pins_energy_projects() -> list[dict]:
    """Fetch energy-sector projects from PINS (HTML or API). Returns list of raw project dicts."""
    # Try API download endpoint first (if available)
    api_url = f"{PINS_BASE}/api/applications-download"
    try:
        r = requests_get_with_retry(api_url, timeout=REQUEST_TIMEOUT, headers={"User-Agent": USER_AGENT})
    except Exception:
        r = None
    if r and r.status_code == 200 and r.text.strip():
        try:
            # Could be CSV or JSON
            ct = (r.headers.get("Content-Type") or "").lower()
            if "json" in ct:
                data = r.json()
                items = data if isinstance(data, list) else data.get("applications", data.get("data", []))
                if items:
                    return items
            if "csv" in ct or r.text.lstrip().startswith("Project") or "\n" in r.text:
                lines = r.text.strip().split("\n")
                if len(lines) < 2:
                    return []
                headers = [h.strip().strip('"') for h in lines[0].split(",")]
                out = []
                for line in lines[1:]:
                    vals = [v.strip().strip('"') for v in re.split(r',(?=(?:[^"]*"[^"]*")*[^"]*$)', line)]
                    if len(vals) >= len(headers):
                        out.append(dict(zip(headers, vals[:len(headers)])))
                    elif vals:
                        out.append({"raw": line, "Project Name": vals[0] if vals else ""})
                return out
        except Exception:
            pass
    # Fallback: scrape project search page (energy sector)
    try:
        html = fetch_html(f"{PINS_SEARCH_URL}?sector=energy&itemsPerPage=100")
        soup = parse_html(html)
        projects = []
        # Common patterns: project cards, table rows, or data attributes
        for card in soup.select("[data-project], .project-card, table tbody tr, article"):
            name_el = card.select_one("h2, h3, .project-name, [data-project-name], td:first-child, a")
            name = (name_el.get_text(strip=True) if name_el else "").strip()
            if not name or len(name) < 3:
                continue
            link = card.select_one("a[href*='project']")
            href = (link.get("href", "") if link else "").strip()
            url = urljoin(PINS_BASE, href) if href else PINS_SEARCH_URL
            stage_el = card.select_one(".stage, [data-stage], td:nth-child(2)")
            stage = (stage_el.get_text(strip=True) if stage_el else "").strip()
            projects.append({"Project Name": name, "Stage": stage, "url": url})
        if projects:
            return projects
        # Table layout
        for row in soup.select("table tr"):
            cells = row.find_all("td")
            if len(cells) >= 2:
                name = (cells[0].get_text(strip=True) or "").strip()
                stage = (cells[1].get_text(strip=True) if len(cells) > 1 else "").strip()
                a = row.find("a", href=True)
                url = urljoin(PINS_BASE, a["href"]) if a else PINS_SEARCH_URL
                if name:
                    projects.append({"Project Name": name, "Stage": stage, "url": url})
        return projects
    except Exception:
        pass
    return []


def scrape_uk_pins_nsip(
    save_csv: bool = True,
    save_json: bool = True,
    date_suffix: str | None = None,
) -> list[dict]:
    """Scrape PINS NSIP register for energy (solar/BESS) projects. Returns list of standard rows."""
    source = SOURCES["uk"].get("pins_nsip") or {
        "name": "Planning Inspectorate – NSIP (Nationally Significant Infrastructure)",
        "url": PINS_SEARCH_URL,
        "country": "UK",
    }
    country = source["country"]
    source_name = source["name"]

    raw = _fetch_pins_energy_projects()
    rows = []
    for p in raw:
        name = (p.get("Project Name") or p.get("project_name") or p.get("Name") or p.get("raw") or "").strip()
        if not name:
            continue
        stage = (p.get("Stage") or p.get("stage") or p.get("Development Status") or "").strip()
        url = (p.get("url") or p.get("Link") or PINS_SEARCH_URL).strip()
        std_status, _ = normalise_status(stage)
        if not std_status and stage:
            std_status = stage[:50]
        # NSIPs are typically large solar; try to parse capacity from name
        cap_num = parse_capacity_mw(name)
        cap_str = f"{cap_num} MW" if cap_num else ""
        row = make_row(
            site_name=name,
            source_name=source_name,
            url=url,
            region="",
            capacity_mw=cap_str,
            capacity_mw_numeric=cap_num,
            status=std_status,
        )
        rows.append(row)

    if rows:
        save_results(rows, country, "pins_nsip", csv=save_csv, json_file=save_json, date_suffix=date_suffix)
    return rows
