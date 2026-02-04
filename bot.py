#!/usr/bin/env python3
"""
BESS Pipeline Automation Bot – runs the UK scraper on a schedule (process automation).
Use this for hands-off weekly/daily runs instead of the web app button.

Usage:
  python bot.py                    # Run once and exit
  python bot.py --once             # Same: run once and exit
  python bot.py --status           # Show last run summary and exit (no scrape)
  python bot.py --schedule         # Run on schedule (default: daily 06:00 UTC)
  python bot.py --schedule --time "09:00"
  python bot.py --schedule --interval 3600
  python bot.py --schedule --run-now   # Run once immediately, then on schedule

Logs: output/uk/bot_log.txt
Status: output/uk/bot_status.json (last run summary for --status)
"""

import argparse
import json
import os
import signal
import sys
from datetime import datetime, timezone
from pathlib import Path

import config as cfg
from scrapers.uk_run_all import run_all_uk_sources
from scrapers.investment_scope import write_investment_scope_summary, build_investment_scope_summary

# Default schedule: daily at 06:00 UTC
BOT_SCHEDULE_TIME = os.environ.get("BOT_SCHEDULE_TIME", "06:00")
BOT_LOG_PATH = None
BOT_STATUS_PATH = None


def _bot_log(msg: str):
    """Write to bot log file and to stdout."""
    ts = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")
    line = f"[{ts}] {msg}"
    print(line, flush=True)
    if BOT_LOG_PATH:
        try:
            with open(BOT_LOG_PATH, "a", encoding="utf-8") as f:
                f.write(line + "\n")
        except Exception:
            pass


def _write_status(summary: dict, error: str | None = None):
    """Write last run summary to bot_status.json."""
    if not BOT_STATUS_PATH:
        return
    payload = {
        "last_run_at": datetime.now(timezone.utc).isoformat(),
        "last_run_ok": error is None,
        "error": error,
        "total_projects": summary.get("total_projects", 0),
        "total_mw": summary.get("total_mw", 0),
        "by_status": {
            "planned": summary.get("count_planned", 0),
            "consented": summary.get("count_consented", 0),
            "in_construction": summary.get("count_in_construction", 0),
            "operational": summary.get("count_operational", 0),
        },
        "by_opportunity": {
            "early_stage": summary.get("count_early_stage_development", 0),
            "construction_finance": summary.get("count_construction_finance", 0),
            "ma_offtake": summary.get("count_ma_offtake", 0),
        },
    }
    try:
        with open(BOT_STATUS_PATH, "w", encoding="utf-8") as f:
            json.dump(payload, f, indent=2)
    except Exception:
        pass


def _read_status() -> dict | None:
    """Read last run summary from bot_status.json. Returns None if missing/invalid."""
    if not BOT_STATUS_PATH or not os.path.isfile(BOT_STATUS_PATH):
        return None
    try:
        with open(BOT_STATUS_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return None


def run_scrape():
    """
    Run the full UK scrape (same as web app / main.py).
    Returns (num_rows, summary_dict). On failure returns (-1, {}) and logs error.
    """
    base = os.path.dirname(os.path.abspath(__file__))
    os.chdir(base)
    cfg.OUTPUT_DIR = os.path.join(base, "output", cfg.OUTPUT_UK_SUBDIR)
    Path(cfg.OUTPUT_DIR).mkdir(parents=True, exist_ok=True)
    date_suffix = datetime.now(timezone.utc).strftime("%Y-%m-%d")

    _bot_log("Scrape starting...")
    try:
        rows = run_all_uk_sources(
            save_merged_csv=True,
            save_merged_json=True,
            date_suffix=date_suffix,
        )
        summary = build_investment_scope_summary(rows, run_date=date_suffix)
        write_investment_scope_summary(rows, output_dir=cfg.OUTPUT_DIR, date_suffix=date_suffix)

        n = len(rows)
        mw = summary.get("total_mw") or 0
        _bot_log(f"Scrape done. {n} projects, {mw:,.0f} MW. Output: {cfg.OUTPUT_DIR}")

        # Log breakdown
        _bot_log(
            f"  Status: planned={summary.get('count_planned',0)} consented={summary.get('count_consented',0)} "
            f"in_construction={summary.get('count_in_construction',0)} operational={summary.get('count_operational',0)}"
        )
        _bot_log(
            f"  Opportunity: early_stage={summary.get('count_early_stage_development',0)} "
            f"construction_finance={summary.get('count_construction_finance',0)} ma_offtake={summary.get('count_ma_offtake',0)}"
        )

        _write_status(summary, error=None)
        return n, summary
    except Exception as e:
        _bot_log(f"Scrape failed: {e}")
        _write_status({}, error=str(e))
        return -1, {}


def run_once():
    """Run scrape once and exit. Exit code 1 on scrape failure."""
    n, _ = run_scrape()
    if n >= 0:
        _bot_log("Bot (--once) finished. Exiting.")
        sys.exit(0)
    _bot_log("Bot (--once) finished with errors. Exiting.")
    sys.exit(1)


def show_status():
    """Print last run summary from bot_status.json and exit."""
    s = _read_status()
    if not s:
        print("No status file found. Run the bot once first: python bot.py --once")
        sys.exit(0)

    ok = s.get("last_run_ok", True)
    ts = s.get("last_run_at", "?")
    err = s.get("error")
    n = s.get("total_projects", 0)
    mw = s.get("total_mw", 0)
    by_status = s.get("by_status") or {}
    by_opp = s.get("by_opportunity") or {}

    print("--- BESS Bot Status ---")
    print(f"Last run:  {ts}")
    print(f"Result:    {'OK' if ok else 'FAILED'}" + (f" — {err}" if err else ""))
    print(f"Projects:  {n}")
    print(f"Total MW:  {mw:,.0f}")
    print("By status: planned={} consented={} in_construction={} operational={}".format(
        by_status.get("planned", 0), by_status.get("consented", 0),
        by_status.get("in_construction", 0), by_status.get("operational", 0)))
    print("By opportunity: early_stage={} construction_finance={} ma_offtake={}".format(
        by_opp.get("early_stage", 0), by_opp.get("construction_finance", 0), by_opp.get("ma_offtake", 0)))
    print("-----------------------")


def run_scheduled(time_str: str | None = None, interval_seconds: int | None = None, run_now: bool = False):
    """Run scrape on a schedule; keeps running until interrupted. Handles Ctrl+C gracefully."""
    import schedule
    import time as time_module

    run_at = time_str or BOT_SCHEDULE_TIME
    _bot_log(f"Bot started. Schedule: daily at {run_at} UTC" +
             (f" or every {interval_seconds}s" if interval_seconds else "") + ".")

    if interval_seconds and interval_seconds > 0:
        schedule.every(interval_seconds).seconds.do(run_scrape)
        _bot_log(f"Next run in {interval_seconds} seconds.")
    else:
        schedule.every().day.at(run_at).do(run_scrape)
        _bot_log(f"Next run: today at {run_at} UTC.")

    if run_now:
        _bot_log("Running once now (--run-now)...")
        run_scrape()

    shutdown = [False]  # closure so signal handler can set it

    def _handle_signal(signum, frame):
        shutdown[0] = True
        _bot_log("Shutting down gracefully (Ctrl+C or SIGTERM)...")

    signal.signal(signal.SIGINT, _handle_signal)
    if hasattr(signal, "SIGTERM"):
        signal.signal(signal.SIGTERM, _handle_signal)

    while not shutdown[0]:
        schedule.run_pending()
        time_module.sleep(30)
    _bot_log("Bot stopped.")


def main():
    global BOT_LOG_PATH, BOT_STATUS_PATH
    parser = argparse.ArgumentParser(
        description="BESS Pipeline Automation Bot – run scraper on schedule or once, show status."
    )
    parser.add_argument(
        "--once",
        action="store_true",
        help="Run scrape once and exit (default if no --schedule).",
    )
    parser.add_argument(
        "--status",
        action="store_true",
        help="Show last run summary from bot_status.json and exit (no scrape).",
    )
    parser.add_argument(
        "--schedule",
        action="store_true",
        help="Run on schedule and keep running until Ctrl+C.",
    )
    parser.add_argument(
        "--run-now",
        action="store_true",
        help="With --schedule: run one scrape immediately, then continue on schedule.",
    )
    parser.add_argument(
        "--time",
        default=BOT_SCHEDULE_TIME,
        metavar="HH:MM",
        help=f"Daily run time (UTC). Default: {BOT_SCHEDULE_TIME}",
    )
    parser.add_argument(
        "--interval",
        type=int,
        default=None,
        metavar="SECONDS",
        help="Run every N seconds instead of daily (e.g. 3600 for hourly).",
    )
    args = parser.parse_args()

    base = os.path.dirname(os.path.abspath(__file__))
    out_uk = os.path.join(base, "output", cfg.OUTPUT_UK_SUBDIR)
    Path(out_uk).mkdir(parents=True, exist_ok=True)
    BOT_LOG_PATH = os.path.join(out_uk, "bot_log.txt")
    BOT_STATUS_PATH = os.path.join(out_uk, "bot_status.json")

    if args.status:
        show_status()
        return
    if args.schedule:
        run_scheduled(time_str=args.time, interval_seconds=args.interval, run_now=args.run_now)
    else:
        run_once()


if __name__ == "__main__":
    main()
