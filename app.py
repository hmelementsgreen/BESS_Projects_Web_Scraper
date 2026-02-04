"""
Simple web app for UK BESS scraper.
Press a button to start scraping; get status and download results.
"""

import json
import logging
import os
import sys
import threading
from datetime import datetime, timezone
from pathlib import Path

from flask import Flask, jsonify, request, send_file, send_from_directory

import config as cfg

# Force terminal output to show immediately (no buffering)
if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(line_buffering=True)
        sys.stderr.reconfigure(line_buffering=True)
    except Exception:
        pass

# Show scraper progress in the terminal when running a scrape; quiet noisy libs on startup
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    datefmt="%H:%M:%S",
    stream=sys.stdout,
)
logging.getLogger("scrapers").setLevel(logging.INFO)
logging.getLogger("urllib3").setLevel(logging.WARNING)
logging.getLogger("numexpr").setLevel(logging.WARNING)
logging.getLogger("werkzeug").setLevel(logging.WARNING)
from scrapers.uk_run_all import run_all_uk_sources
from scrapers.investment_scope import write_investment_scope_summary, build_investment_scope_summary

app = Flask(__name__, static_folder="static", static_url_path="")

# In-memory state for scrape status (single worker)
_scrape_state = {
    "status": "idle",  # idle | running | done | error
    "started_at": None,
    "finished_at": None,
    "project_count": None,
    "summary": None,
    "scrape_summary": None,  # short 1–2 line summary for UI after scrape
    "error": None,
}
_lock = threading.Lock()
_scrape_log_path = None  # set when output dir is known


def _scrape_log(msg: str):
    """Write scrape message to terminal and to a log file (so you always have a record)."""
    print(msg, flush=True)
    path = _scrape_log_path
    if path:
        try:
            with open(path, "a", encoding="utf-8") as f:
                f.write(msg + "\n")
        except Exception:
            pass


def _run_scraper():
    global _scrape_state, _scrape_log_path
    with _lock:
        _scrape_state["status"] = "running"
        _scrape_state["started_at"] = datetime.now(timezone.utc).isoformat()
        _scrape_state["finished_at"] = None
        _scrape_state["project_count"] = None
        _scrape_state["summary"] = None
        _scrape_state["scrape_summary"] = None
        _scrape_state["error"] = None

    try:
        base = os.path.dirname(os.path.abspath(__file__))
        os.chdir(base)
        cfg.OUTPUT_DIR = os.path.join(base, "output", cfg.OUTPUT_UK_SUBDIR)
        Path(cfg.OUTPUT_DIR).mkdir(parents=True, exist_ok=True)
        _scrape_log_path = os.path.join(cfg.OUTPUT_DIR, "scrape_log.txt")

        _scrape_log("[Scrape] Starting...")
        _scrape_log(f"[Scrape] Output dir: {cfg.OUTPUT_DIR}")
        date_suffix = datetime.now(timezone.utc).strftime("%Y-%m-%d")

        rows = run_all_uk_sources(
            save_merged_csv=True,
            save_merged_json=True,
            date_suffix=date_suffix,
        )
        _scrape_log(f"[Scrape] Gathered {len(rows)} rows (deduplicated)")
        summary = build_investment_scope_summary(rows, run_date=date_suffix)
        write_investment_scope_summary(rows, output_dir=cfg.OUTPUT_DIR, date_suffix=date_suffix)

        total_mw = summary.get("total_mw") or 0
        finished_at = datetime.now(timezone.utc)
        finished_str = finished_at.strftime("%H:%M") if finished_at else ""
        scrape_summary = (
            f"{len(rows)} unique projects (deduplicated) · {total_mw:,.0f} MW total · "
            f"Completed at {finished_str}. Download bess_uk_multi_source for the full dataset."
        )
        # Write bot_status and bot_log BEFORE updating state so when client sees "done", files exist
        _write_bot_status(summary, output_dir=cfg.OUTPUT_DIR)
        _scrape_log(f"[Scrape] Done. {len(rows)} projects, {total_mw:,.0f} MW. Files saved to {cfg.OUTPUT_DIR}")
        with _lock:
            _scrape_state["status"] = "done"
            _scrape_state["finished_at"] = finished_at.isoformat()
            _scrape_state["project_count"] = len(rows)
            _scrape_state["summary"] = summary
            _scrape_state["scrape_summary"] = scrape_summary
            _scrape_state["error"] = None
    except Exception as e:
        _scrape_log(f"[Scrape] Error: {e}")
        _write_bot_status({}, error=str(e))
        with _lock:
            _scrape_state["status"] = "error"
            _scrape_state["finished_at"] = datetime.now(timezone.utc).isoformat()
            _scrape_state["error"] = str(e)


@app.route("/")
def index():
    return send_from_directory(app.static_folder, "index.html")


@app.route("/api/status", methods=["GET"])
def api_status():
    """Return scrape state. When idle, include disk-backed summary so UI shows latest run (e.g. 355)."""
    with _lock:
        state = dict(_scrape_state)
    if state.get("status") == "idle" and state.get("summary") is None:
        out_uk = _out_uk_dir()
        disk = _load_summary_from_multi_source_csv(out_uk) or _load_latest_summary_from_disk(out_uk)
        if disk and (disk.get("total_projects") or 0) >= 50:
            state["summary"] = disk
            state["project_count"] = disk.get("total_projects")
            state["scrape_summary"] = state.get("scrape_summary") or (
                f"{disk.get('total_projects')} unique projects (deduplicated) · "
                f"{disk.get('total_mw') or 0:,.0f} MW total · From latest run on disk."
            )
    return jsonify(state)


@app.route("/api/scrape", methods=["POST"])
def api_scrape():
    with _lock:
        if _scrape_state["status"] == "running":
            return jsonify({"status": "running", "message": "Scrape already in progress"}), 409
    out_uk = _out_uk_dir()
    if os.path.isdir(out_uk):
        global _scrape_log_path
        _scrape_log_path = os.path.join(out_uk, "scrape_log.txt")
    _scrape_log("\n[Scrape] Button clicked - starting scrape in background...")
    thread = threading.Thread(target=_run_scraper)
    thread.start()
    return jsonify({"status": "running", "message": "Scrape started"})


def _out_uk_dir():
    """Absolute path to output/uk, always relative to app.py (same place scraper writes)."""
    base = os.path.dirname(os.path.abspath(os.path.realpath(__file__)))
    return os.path.join(base, "output", cfg.OUTPUT_UK_SUBDIR)


def _write_bot_status(summary: dict, error: str | None = None, output_dir: str | None = None):
    """Write last run summary to bot_status.json (same format as bot.py) so Bot card stays in sync."""
    out_uk = output_dir if output_dir else _out_uk_dir()
    path = os.path.join(out_uk, "bot_status.json")
    Path(out_uk).mkdir(parents=True, exist_ok=True)
    now = datetime.now(timezone.utc).isoformat()
    payload = {
        "last_run_at": now,
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
        with open(path, "w", encoding="utf-8") as f:
            json.dump(payload, f, indent=2)
    except Exception:
        pass
    # Append to bot_log.txt so "Recent log" in UI shows web app runs too
    log_path = os.path.join(out_uk, "bot_log.txt")
    ts = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")
    line = f"[{ts}] [Web app] Scrape done. {payload['total_projects']} projects, {payload['total_mw']:,.0f} MW." if error is None else f"[{ts}] [Web app] Scrape failed: {error}"
    try:
        with open(log_path, "a", encoding="utf-8") as f:
            f.write(line + "\n")
    except Exception:
        pass


def _load_summary_from_multi_source_csv(out_uk: str, multi_source_path: str = None):
    """Build summary from bess_uk_multi_source*.csv. If multi_source_path is given, read that file; else find latest in out_uk."""
    import csv
    path = multi_source_path
    if not path and out_uk and os.path.isdir(out_uk):
        candidates = []
        for name in os.listdir(out_uk):
            if "multi_source" in name and name.endswith(".csv"):
                p = os.path.join(out_uk, name)
                if os.path.isfile(p):
                    try:
                        candidates.append((p, os.path.getmtime(p)))
                    except OSError:
                        pass
        if candidates:
            path = max(candidates, key=lambda x: x[1])[0]
    if not path or not os.path.isfile(path):
        return None
    try:
        with open(path, "r", newline="", encoding="utf-8-sig") as f:
            rows = list(csv.DictReader(f))
    except Exception:
        return None
    if not rows:
        return None
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
        try:
            cap = r.get("capacity_mw_numeric")
            if cap is not None and str(cap).strip():
                total_mw += float(cap)
        except (TypeError, ValueError):
            pass
    n = len(rows)
    return {
        "run_date": "",
        "run_at": "",
        "total_projects": n,
        "total_mw": round(total_mw, 1),
        "count_planned": count_planned,
        "count_consented": count_consented,
        "count_in_construction": count_in_construction,
        "count_operational": count_operational,
        "count_early_stage_development": count_early_stage,
        "count_construction_finance": count_construction_finance,
        "count_ma_offtake": count_ma_offtake,
    }


def _load_latest_summary_from_disk(out_uk: str):
    """Read the best summary row (max total_projects >= 50) from uk_investment_scope_summary.csv."""
    import csv
    path = os.path.join(out_uk, "uk_investment_scope_summary.csv")
    if not path or not os.path.isfile(path):
        return None
    try:
        with open(path, "r", newline="", encoding="utf-8-sig") as f:
            reader = csv.DictReader(f)
            rows = list(reader)
        if not rows:
            return None
        best = None
        best_total = 0
        for row in rows:
            raw = row.get("total_projects") or row.get("Total_projects") or ""
            try:
                total = int(str(raw).strip())
            except (TypeError, ValueError):
                continue
            if total >= 50 and total > best_total:
                best_total = total
                best = row
        if not best:
            return None
        def _int(key):
            v = best.get(key) or best.get(key.replace("_", " ")) or 0
            try:
                return int(float(str(v).strip()))
            except (TypeError, ValueError):
                return 0
        def _float(key):
            v = best.get(key) or 0
            try:
                return float(str(v).strip())
            except (TypeError, ValueError):
                return 0.0
        return {
            "run_date": (best.get("run_date") or "").strip(),
            "run_at": (best.get("run_at") or "").strip(),
            "total_projects": best_total,
            "total_mw": _float("total_mw"),
            "count_planned": _int("count_planned"),
            "count_consented": _int("count_consented"),
            "count_in_construction": _int("count_in_construction"),
            "count_operational": _int("count_operational"),
            "count_early_stage_development": _int("count_early_stage_development"),
            "count_construction_finance": _int("count_construction_finance"),
            "count_ma_offtake": _int("count_ma_offtake"),
        }
    except Exception:
        return None


@app.route("/api/results", methods=["GET"])
def api_results():
    """List latest result files and summary. Summary is built from the multi_source CSV in this directory (source of truth)."""
    out_uk = _out_uk_dir()
    if not os.path.isdir(out_uk):
        return jsonify({"files": [], "summary": None, "scrape_summary": None})

    files = []
    multi_source_candidates = []
    for name in os.listdir(out_uk):
        if name.endswith((".csv", ".json")):
            path = os.path.join(out_uk, name)
            if os.path.isfile(path):
                try:
                    mtime = os.path.getmtime(path)
                    files.append({"name": name, "updated": datetime.fromtimestamp(mtime, tz=timezone.utc).isoformat()})
                    if "multi_source" in name and name.endswith(".csv"):
                        multi_source_candidates.append((path, mtime))
                except OSError:
                    files.append({"name": name, "updated": None})
    multi_source_csv_path = max(multi_source_candidates, key=lambda x: x[1])[0] if multi_source_candidates else None

    summary = _load_summary_from_multi_source_csv(out_uk, multi_source_path=multi_source_csv_path)
    if summary is None:
        summary = _load_latest_summary_from_disk(out_uk)
    scrape_summary = None
    with _lock:
        in_mem = _scrape_state.get("summary")
        scrape_summary = _scrape_state.get("scrape_summary")
    if summary is None:
        summary = in_mem
    if summary and not scrape_summary and (summary.get("total_projects") or 0) >= 50:
        n = summary.get("total_projects") or 0
        mw = summary.get("total_mw") or 0
        scrape_summary = (
            f"{n} unique projects (deduplicated) · {mw:,.0f} MW total · "
            "From latest run on disk. Download bess_uk_multi_source for the full dataset."
        )
    return jsonify({
        "files": sorted(files, key=lambda x: x["updated"] or "", reverse=True),
        "summary": summary,
        "scrape_summary": scrape_summary,
    })


@app.route("/api/download/<path:filename>")
def api_download(filename):
    """Serve file from output/uk/ for download. Only allow CSV/JSON."""
    if ".." in filename or not (filename.endswith(".csv") or filename.endswith(".json")):
        return jsonify({"error": "Invalid file"}), 400
    out_uk = _out_uk_dir()
    path = os.path.join(out_uk, filename)
    if not os.path.isfile(path):
        return jsonify({"error": "File not found"}), 404
    return send_file(path, as_attachment=True, download_name=filename)


@app.route("/api/bot/status", methods=["GET"])
def api_bot_status():
    """Return last bot run summary from bot_status.json. 200 with last_run_at null if missing."""
    out_uk = _out_uk_dir()
    path = os.path.join(out_uk, "bot_status.json")
    if not os.path.isfile(path):
        return jsonify({"last_run_at": None})
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        return jsonify(data)
    except Exception:
        return jsonify({"last_run_at": None})


@app.route("/api/bot/log", methods=["GET"])
def api_bot_log():
    """Return last N lines of bot_log.txt. Query param tail (default 50, max 500)."""
    tail = request.args.get("tail", 50, type=int)
    tail = max(0, min(500, tail))
    out_uk = _out_uk_dir()
    path = os.path.join(out_uk, "bot_log.txt")
    if not os.path.isfile(path):
        return jsonify({"lines": []})
    try:
        with open(path, "r", encoding="utf-8") as f:
            lines = f.readlines()
        lines = [line.rstrip("\n\r") for line in lines[-tail:]]
        return jsonify({"lines": lines})
    except Exception:
        return jsonify({"lines": []})


@app.route("/api/debug", methods=["GET"])
def api_debug():
    """Return out_uk path, whether it exists, and summary from multi_source CSV (for troubleshooting)."""
    out_uk = _out_uk_dir()
    multi_source_path = None
    if os.path.isdir(out_uk):
        for name in os.listdir(out_uk):
            if "multi_source" in name and name.endswith(".csv"):
                multi_source_path = os.path.join(out_uk, name)
                break
    summary = _load_summary_from_multi_source_csv(out_uk, multi_source_path=multi_source_path)
    return jsonify({
        "out_uk": out_uk,
        "out_uk_exists": os.path.isdir(out_uk),
        "multi_source_path": multi_source_path,
        "summary_total_projects": summary.get("total_projects") if summary else None,
        "in_mem_total_projects": (_scrape_state.get("summary") or {}).get("total_projects"),
    })


if __name__ == "__main__":
    # use_reloader=False so all output (including from the scrape thread) goes to this terminal
    app.run(host="0.0.0.0", port=5000, debug=False, use_reloader=False)
