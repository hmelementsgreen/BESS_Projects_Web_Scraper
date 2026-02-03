#!/usr/bin/env python3
"""
BESS Projects Web Scraper – UK only, multiple sources.
Built for Elements Green (London): weekly runs, investment scope.
Scrapes REPD, TEC Register, PINS NSIP, ECR (UKPN), EDF, BSR, Root Power, Fidra, SSE, Energy-Storage.news, Solar Power Portal, EirGrid (Ireland). Deduplicates same project across sources.
Usage:
  python main.py
  python main.py --weekly
  python main.py --latest-only
"""

import argparse
import sys
from datetime import datetime, timezone

from scrapers.uk_run_all import run_all_uk_sources
from scrapers.investment_scope import write_investment_scope_summary
from config import COMPANY_NAME, COMPANY_LOCATION, OUTPUT_DIR, OUTPUT_UK_SUBDIR

LATEST_STATUSES = {"planned", "consented", "in-construction", "Planned", "Consented", "In-construction"}


def main() -> int:
    parser = argparse.ArgumentParser(
        description=f"UK BESS projects scraper – multiple sources, investment scope. Company: {COMPANY_NAME}, {COMPANY_LOCATION}."
    )
    parser.add_argument(
        "--weekly",
        action="store_true",
        help="Save dated output files (e.g. bess_uk_multi_source_2025-02-03.csv) for weekly comparison",
    )
    parser.add_argument(
        "--latest-only",
        action="store_true",
        help="Keep only pipeline projects (Planned / Consented / In-construction); exclude Operational",
    )
    parser.add_argument(
        "--no-csv",
        action="store_true",
        help="Do not write CSV output",
    )
    parser.add_argument(
        "--no-json",
        action="store_true",
        help="Do not write JSON output",
    )
    parser.add_argument(
        "--no-summary",
        action="store_true",
        help="Do not write investment scope summary CSV",
    )
    parser.add_argument(
        "--output-dir",
        default=OUTPUT_DIR,
        help=f"Output directory (default: {OUTPUT_DIR})",
    )
    args = parser.parse_args()

    save_csv = not args.no_csv
    save_json = not args.no_json
    date_suffix = datetime.now(timezone.utc).strftime("%Y-%m-%d") if args.weekly else None

    import config as cfg
    cfg.OUTPUT_DIR = f"{args.output_dir.rstrip('/')}/{OUTPUT_UK_SUBDIR}"

    uk_rows = run_all_uk_sources(
        save_merged_csv=save_csv,
        save_merged_json=save_json,
        date_suffix=date_suffix,
    )
    if args.latest_only:
        uk_rows = [r for r in uk_rows if (r.get("status") or "").strip() in LATEST_STATUSES]

    print(f"UK: scraped {len(uk_rows)} BESS projects (deduplicated across sources)" + (" (pipeline only)" if args.latest_only else ""))

    if uk_rows and not args.no_summary:
        summary_path = write_investment_scope_summary(
            uk_rows,
            output_dir=cfg.OUTPUT_DIR,
            date_suffix=date_suffix or datetime.now(timezone.utc).strftime("%Y-%m-%d"),
        )
        print(f"Investment scope summary: {summary_path}")

    print(f"Output: {cfg.OUTPUT_DIR}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
