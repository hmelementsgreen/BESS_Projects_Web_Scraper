"""
Shared helpers for UK BESS scrapers – normalise status and capacity across sources.
Includes deduplication so the same project does not appear twice (e.g. REPD + developer).
"""

import re
from datetime import datetime, timezone

from config import INVESTMENT_OPPORTUNITY_MAP


def _normalize_for_key(text: str, max_len: int = 200) -> str:
    """Lowercase, strip, collapse whitespace, remove trailing punctuation."""
    if not text:
        return ""
    s = re.sub(r"\s+", " ", str(text).strip().lower())
    s = re.sub(r"[.,;:\-]+$", "", s)
    return s[:max_len] if max_len else s


# Generic site names that should not be merged with others (use url to keep distinct)
_DEDUP_GENERIC_SITE = frozenset({
    "view project", "our expertise", "why battery storage matters", "our expertise in battery storage",
    "article", "news", "read more", "home", "about",
})


def project_dedup_key(row: dict) -> tuple:
    """
    Return a hashable key for deduplication: (site_normalized, capacity_rounded, region_normalized).
    Same physical project from REPD and a developer page should get the same key.
    If site is empty or generic, include normalized url so we don't merge unrelated rows.
    """
    site = _normalize_for_key(row.get("site_name") or "", 200)
    cap = row.get("capacity_mw_numeric")
    if cap is not None:
        try:
            cap = round(float(cap), 1)
        except (TypeError, ValueError):
            cap = None
    region = _normalize_for_key(row.get("region") or "", 100)
    # Avoid merging rows with no site or generic text (e.g. "View Project") into one
    if not site or site in _DEDUP_GENERIC_SITE or len(site) < 3:
        url = (row.get("url") or "").strip().lower()
        url = url.split("?")[0].rstrip("/")[-120:] if url else ""
        return (site or "_", cap, region, url)
    return (site, cap, region)


def deduplicate_projects(rows: list[dict]) -> list[dict]:
    """
    Merge duplicate projects (same site + capacity + region) into one row.
    Prefers non-News source; merges source names into one 'source' field (e.g. 'REPD; EDF').
    Returns a new list with no duplicate keys.
    """
    if not rows:
        return []
    seen: dict[tuple, dict] = {}
    for r in rows:
        key = project_dedup_key(r)
        if key in seen:
            existing = seen[key]
            src_a = (existing.get("source") or "").strip()
            src_b = (r.get("source") or "").strip()
            # Prefer non-News row as canonical; merge sources
            if (r.get("status") or "").strip() != "News" and (existing.get("status") or "").strip() == "News":
                for k, v in r.items():
                    if v not in (None, ""):
                        existing[k] = v
                existing["source"] = f"{src_b}; {src_a}".strip("; ") if src_a else src_b
            else:
                if src_b and src_b not in src_a:
                    existing["source"] = f"{src_a}; {src_b}".strip("; ")
            continue
        seen[key] = dict(r)
    return list(seen.values())

# Map various source status phrases to our standard status
STATUS_NORMALISE = {
    "planned": "Planned",
    "planning": "Planned",
    "pre-construction": "Planned",
    "planning preparation": "Planned",
    "planning submitted": "Planned",
    "consented": "Consented",
    "advanced development": "Consented",
    "awaiting construction": "Consented",
    "in construction": "In-construction",
    "in-construction": "In-construction",
    "under construction": "In-construction",
    "operational": "Operational",
    "energised": "Operational",
    "development": "Planned",
}


def parse_capacity_mw(text: str) -> float | None:
    """Parse capacity from text: '50MW', 'c.25MW', '1.45GW', '150MW / 300MWh'."""
    if not text or not str(text).strip():
        return None
    s = re.sub(r"^c\.?\s*", "", str(text).strip(), flags=re.IGNORECASE)
    # GW first
    m = re.search(r"([\d.]+)\s*GW", s, re.IGNORECASE)
    if m:
        try:
            return float(m.group(1)) * 1000
        except ValueError:
            pass
    m = re.search(r"([\d.]+)\s*MW", s, re.IGNORECASE)
    if m:
        try:
            return float(m.group(1))
        except ValueError:
            return None
    return None


def normalise_status(raw: str) -> tuple[str, str]:
    """Return (standard_status, investment_opportunity)."""
    key = (raw or "").strip().lower().replace(" ", "-").replace("_", "-")
    for k, standard in STATUS_NORMALISE.items():
        if k in key or key in k:
            opp_key = standard.lower().replace(" ", "-")
            opp = INVESTMENT_OPPORTUNITY_MAP.get(opp_key, "")
            return standard, opp
    if "operation" in key or "energised" in key:
        return "Operational", INVESTMENT_OPPORTUNITY_MAP.get("operational", "")
    if "consent" in key:
        return "Consented", INVESTMENT_OPPORTUNITY_MAP.get("consented", "")
    if "construct" in key:
        return "In-construction", INVESTMENT_OPPORTUNITY_MAP.get("in-construction", "")
    return raw or "", ""


def make_row(
    site_name: str,
    source_name: str,
    url: str,
    *,
    region: str = "",
    capacity_mw: str = "",
    capacity_mw_numeric: float | None = None,
    status: str = "",
) -> dict:
    """Build a standard row dict. capacity_mw_numeric from capacity_mw if not provided."""
    scraped_at = datetime.now(timezone.utc).isoformat()
    if capacity_mw_numeric is None and capacity_mw:
        capacity_mw_numeric = parse_capacity_mw(capacity_mw)
    std_status, opportunity = normalise_status(status)
    return {
        "scraped_at": scraped_at,
        "country": "UK",
        "region": region or "",
        "site_name": (site_name or "").strip(),
        "capacity_mw": (capacity_mw or "").strip(),
        "capacity_mw_numeric": capacity_mw_numeric,
        "status": std_status,
        "investment_opportunity": opportunity,
        "source": source_name,
        "url": (url or "").strip(),
    }
