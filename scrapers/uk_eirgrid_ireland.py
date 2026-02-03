"""
Ireland – EirGrid / ESB Networks Connected & Contracted generators.
Lists are published as PDFs; this scraper records the source URLs and link text for manual use.
"""

from urllib.parse import urljoin

from .base import fetch_html, parse_html, save_results
from .uk_common import make_row
from config import SOURCES

EIRGRID_URL = "https://www.eirgrid.ie/industry/customer-information/connected-and-contracted-generators"
REQUEST_TIMEOUT = 30


def scrape_eirgrid_ireland(
    save_csv: bool = True,
    save_json: bool = True,
    date_suffix: str | None = None,
) -> list[dict]:
    """
    Scrape EirGrid Connected & Contracted page for PDF/list links.
    Returns one row per linked document (title + URL) so the source is in the dataset.
    Country = Ireland. Full project lists are in PDFs – use for pipeline visibility.
    """
    try:
        source = (SOURCES.get("ireland") or {}).get("eirgrid") or (SOURCES.get("uk") or {}).get("eirgrid")
    except Exception:
        source = None
    if not source:
        source = {
            "name": "EirGrid – Connected & Contracted Generators (Ireland)",
            "url": EIRGRID_URL,
            "country": "Ireland",
        }
    country = source.get("country", "Ireland")
    source_name = source["name"]

    rows = []
    try:
        html = fetch_html(EIRGRID_URL)
        soup = parse_html(html)
        for a in soup.find_all("a", href=True):
            href = (a.get("href") or "").strip()
            if not href or href.startswith("#"):
                continue
            text = (a.get_text(strip=True) or "").strip()
            if not text or len(text) < 5:
                continue
            # Focus on PDFs and generator/list links
            if ".pdf" in href.lower() or "contract" in href.lower() or "connect" in href.lower() or "generator" in href.lower():
                url = href if href.startswith("http") else urljoin(EIRGRID_URL, href)
                row = make_row(
                    site_name=text[:200],
                    source_name=source_name,
                    url=url,
                    region="Ireland",
                    capacity_mw="",
                    capacity_mw_numeric=None,
                    status="Reference",
                )
                row["country"] = country
                rows.append(row)
                if len(rows) >= 20:
                    break
    except Exception:
        pass

    if rows:
        save_results(rows, country.replace(" ", "_"), "eirgrid_ireland", csv=save_csv, json_file=save_json, date_suffix=date_suffix)
    return rows
