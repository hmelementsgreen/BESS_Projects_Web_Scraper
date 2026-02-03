"""
Run all UK BESS scrapers and merge results into one dataset.
Per-source errors are caught so one failure does not stop the rest.
Deduplication removes same project (site + capacity + region) from multiple sources.
"""

import logging
import os
from datetime import datetime, timezone

logger = logging.getLogger(__name__)

from .base import save_results
from .uk_edf_bess import scrape_uk_edf_bess
from .uk_british_renewables import scrape_uk_british_renewables
from .uk_root_power import scrape_uk_root_power
from .uk_fidra import scrape_uk_fidra
from .uk_sse_bess import scrape_uk_sse_bess
from .uk_repd import scrape_uk_repd
from .uk_news_energy_storage import scrape_uk_news_energy_storage
from .uk_news_solar_portal import scrape_uk_news_solar_portal
from .uk_common import deduplicate_projects
from .investment_scope import write_investment_scope_summary, build_investment_scope_summary
import config as cfg

# Optional Gemini/official sources (may fail if URLs or API change)
try:
    from .uk_tec_register import scrape_uk_tec_register
except ImportError:
    scrape_uk_tec_register = None
try:
    from .uk_pins_nsip import scrape_uk_pins_nsip
except ImportError:
    scrape_uk_pins_nsip = None
try:
    from .uk_ecr_ukpn import scrape_uk_ecr_ukpn
except ImportError:
    scrape_uk_ecr_ukpn = None
try:
    from .uk_eirgrid_ireland import scrape_eirgrid_ireland
except ImportError:
    scrape_eirgrid_ireland = None


def run_all_uk_sources(
    save_merged_csv: bool = True,
    save_merged_json: bool = True,
    date_suffix: str | None = None,
) -> list[dict]:
    """
    Run all UK BESS scrapers; merge and save one combined CSV/JSON.
    Per-source errors are caught so one failure does not stop the rest.
    Returns merged list of rows.
    """
    date_suffix = date_suffix or datetime.now(timezone.utc).strftime("%Y-%m-%d")
    all_rows = []

    # Call each scraper by function (no lambdas) so every source runs reliably
    def _run(name, fn, **kwargs):
        try:
            return fn(save_csv=False, save_json=False, date_suffix=None, **kwargs) or []
        except Exception as e:
            logger.warning("Scraper %s failed: %s", name, e, exc_info=True)
            return []

    scrapers = [
        ("REPD", scrape_uk_repd),
        ("EDF", scrape_uk_edf_bess, {"latest_only": False}),
        ("British Renewables", scrape_uk_british_renewables),
        ("Root Power", scrape_uk_root_power),
        ("Fidra", scrape_uk_fidra),
        ("SSE", scrape_uk_sse_bess),
        ("Energy-Storage.news", scrape_uk_news_energy_storage),
        ("Solar Power Portal", scrape_uk_news_solar_portal),
    ]
    if scrape_uk_tec_register:
        scrapers.append(("TEC Register", scrape_uk_tec_register))
    if scrape_uk_pins_nsip:
        scrapers.append(("PINS NSIP", scrape_uk_pins_nsip))
    if scrape_uk_ecr_ukpn:
        scrapers.append(("ECR UKPN", scrape_uk_ecr_ukpn))
    if scrape_eirgrid_ireland:
        scrapers.append(("EirGrid Ireland", scrape_eirgrid_ireland))

    for item in scrapers:
        name = item[0]
        fn = item[1]
        kwargs = item[2] if len(item) > 2 else {}
        rows = _run(name, fn, **kwargs)
        n = len(rows)
        all_rows.extend(rows)
        logger.info("Scraper %s: %d rows", name, n)

    # Remove duplicates (same site + capacity + region from multiple sources)
    all_rows = deduplicate_projects(all_rows)

    if all_rows:
        save_results(
            all_rows,
            "UK",
            "multi_source",
            csv=save_merged_csv,
            json_file=save_merged_json,
            output_dir=cfg.OUTPUT_DIR,
            date_suffix=date_suffix,
        )
    return all_rows
