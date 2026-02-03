"""
Investment scope summary for UK BESS projects.
Produces a short report for weekly runs: counts by status, by opportunity type, total MW.
"""

import os
from datetime import datetime, timezone

from config import OUTPUT_DIR, DEFAULT_ENCODING, OUTPUT_UK_SUBDIR


# Minimum projects to consider a run "complete" and append to summary (avoids recording partial runs)
MIN_PROJECTS_FOR_SUMMARY = 50


def build_investment_scope_summary(rows: list[dict], run_date: str | None = None, run_at: str | None = None) -> dict:
    """
    Build summary: counts by status, by investment_opportunity, total capacity_mw_numeric.
    Fixed columns for easy week-over-week comparison. run_at = one reading per run (ISO timestamp).
    """
    count_planned = count_consented = count_in_construction = count_operational = 0
    count_early_stage = count_construction_finance = count_ma_offtake = 0
    total_mw = 0.0

    for r in rows:
        status = (r.get("status") or "").strip().lower().replace(" ", "-")
        if status == "planned":
            count_planned += 1
        elif status == "consented":
            count_consented += 1
        elif status == "in-construction":
            count_in_construction += 1
        elif status == "operational":
            count_operational += 1

        opp = (r.get("investment_opportunity") or "").strip()
        if "Early-stage" in opp:
            count_early_stage += 1
        elif "Construction" in opp or "finance" in opp:
            count_construction_finance += 1
        elif "M&A" in opp or "offtake" in opp:
            count_ma_offtake += 1

        cap = r.get("capacity_mw_numeric")
        if cap is not None:
            total_mw += float(cap)

    now = datetime.now(timezone.utc)
    run_date = run_date or now.strftime("%Y-%m-%d")
    run_at = run_at or now.isoformat()
    return {
        "run_date": run_date,
        "run_at": run_at,
        "total_projects": len(rows),
        "total_mw": round(total_mw, 1),
        "count_planned": count_planned,
        "count_consented": count_consented,
        "count_in_construction": count_in_construction,
        "count_operational": count_operational,
        "count_early_stage_development": count_early_stage,
        "count_construction_finance": count_construction_finance,
        "count_ma_offtake": count_ma_offtake,
    }


def write_investment_scope_summary(
    rows: list[dict],
    output_dir: str | None = None,
    date_suffix: str | None = None,
    run_at: str | None = None,
) -> str:
    """
    Append one summary row to uk_investment_scope_summary.csv (or create with header).
    Only appends if total_projects >= MIN_PROJECTS_FOR_SUMMARY so partial runs are not recorded.
    Each row has run_date and run_at (one reading per run).
    Returns path to written file.
    """
    import config as cfg
    out = output_dir or getattr(cfg, "OUTPUT_DIR", None) or OUTPUT_DIR
    if output_dir is None:
        out = os.path.join(out, getattr(cfg, "OUTPUT_UK_SUBDIR", None) or OUTPUT_UK_SUBDIR)
    os.makedirs(out, exist_ok=True)

    now = datetime.now(timezone.utc)
    run_date = date_suffix or now.strftime("%Y-%m-%d")
    run_at = run_at or now.isoformat()
    summary = build_investment_scope_summary(rows, run_date=run_date, run_at=run_at)

    if summary["total_projects"] < MIN_PROJECTS_FOR_SUMMARY:
        return os.path.join(out, "uk_investment_scope_summary.csv")

    import csv
    path = os.path.join(out, "uk_investment_scope_summary.csv")
    file_exists = os.path.isfile(path)
    fieldnames = list(summary.keys())
    if file_exists:
        with open(path, "r", newline="", encoding=DEFAULT_ENCODING) as f:
            reader = csv.DictReader(f)
            if reader.fieldnames and "run_at" not in (reader.fieldnames or []):
                fieldnames = [k for k in fieldnames if k != "run_at"]
    with open(path, "a", newline="", encoding=DEFAULT_ENCODING) as f:
        w = csv.DictWriter(f, fieldnames=fieldnames, extrasaction="ignore")
        if not file_exists:
            w.writeheader()
        w.writerow({k: summary[k] for k in fieldnames if k in summary})
    return path
