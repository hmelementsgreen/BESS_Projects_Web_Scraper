# BESS Projects Web Scraper – UK Only

Web scraper for **latest UK BESS (Battery Energy Storage System)** projects, built for **Elements Green (London)**. Designed for **weekly runs** to track **investment scope** (sites and opportunity types).

## Company context

- **Elements Green** – London-based solar and energy storage developer with a 22-year track record.
- Pipeline in excess of **13 GW** across UK, EU, Australia and US.
- This scraper focuses on **UK only**, **latest projects**, run **weekly**, to understand **scopes of investment** (early-stage, construction/finance, M&A/offtake).

## What it does

- **UK + Ireland, multiple sources**: Scrapes **12** public/official sources and merges into one dataset (same project from multiple sources is **deduplicated**):
  - **Government / official:** DESNZ REPD, NESO TEC Register (transmission capacity), Planning Inspectorate (PINS) NSIP (>50MW solar), UK Power Networks ECR (embedded capacity), EirGrid Ireland (Connected & Contracted links)
  - **Developers:** EDF Renewables, British Solar Renewables, Root Power, Fidra Energy, SSE Renewables
  - **News:** Energy-Storage.news, Solar Power Portal
- **Deduplication:** Rows with the same site name + capacity + region (from REPD and a developer page, etc.) are merged into one row; source names are combined (e.g. "REPD; EDF").
- **Latest projects**: Optional filter `--latest-only` keeps only pipeline projects (Planned / Consented / In-construction) and excludes Operational.
- **Weekly runs**: Use `--weekly` to save dated files (e.g. `bess_uk_multi_source_2025-02-03.csv`) for week-over-week comparison.
- **Investment scope**: Each run appends one row to `uk_investment_scope_summary.csv` with counts by status, by opportunity type, and total MW.

## GitHub & Deploy

The repo is already initialized with a first commit. To put it on GitHub:

1. **Create a new repo on GitHub**: [github.com/new](https://github.com/new) → name it e.g. `BESS_Projects_Web_Scraper` → **don’t** add a README or .gitignore (you already have them) → Create repository.
2. **Add remote and push** (replace `YOUR_USERNAME` and `YOUR_REPO` with your GitHub user and repo name):

```bash
cd BESS_Projects_Web_Scraper
git remote add origin https://github.com/YOUR_USERNAME/YOUR_REPO.git
git branch -M main
git push -u origin main
```

Or with SSH: `git remote add origin git@github.com:YOUR_USERNAME/YOUR_REPO.git`

---

## Setup

```bash
cd BESS_Projects_Web_Scraper
python -m venv .venv
.venv\Scripts\activate   # Windows
# source .venv/bin/activate   # macOS/Linux
pip install -r requirements.txt
```

## Web app (for your manager)

Run the scraper from the browser: one button to start scraping, then download the data when it’s done.

```bash
pip install -r requirements.txt
python app.py
```

Open **http://localhost:5000**. Click **Start scraping**; wait 1–2 minutes (12 sources, including REPD, TEC, PINS, ECR, news). When it’s done you’ll see a summary and links to download the merged CSV and investment-scope summary.

### Deploy (Render / Railway / Heroku)

**Render (recommended)**

1. Push the repo to **GitHub**.
2. Go to [render.com](https://render.com) → New → Web Service → connect your repo.
3. Render will use the root `Procfile` or you can set:
   - **Build**: `pip install -r requirements.txt`
   - **Start**: `gunicorn -w 1 -b 0.0.0.0:$PORT --timeout 300 app:app` (timeout allows 1–2 min scrape).
4. Deploy. Share the app URL (e.g. `https://bess-pipeline.onrender.com`).

Alternatively, add a **Blueprint** by connecting the repo and using the included `render.yaml` for one-click deploy.

**Railway / Heroku**  
Use the same **Build** and **Start** commands; both read `Procfile` by default. Set `PORT` in the environment if required.

After deploy, open the app URL, click **Start scrape**, wait 1–2 minutes, then download **bess_uk_multi_source** for the full dataset.

---

## CLI usage

From the project root:

```bash
# Standard run (all UK projects, summary appended)
python main.py

# Weekly run: dated project files + summary row (recommended for weekly schedule)
python main.py --weekly

# Latest/pipeline only (exclude operational – focus on investment pipeline)
python main.py --latest-only

# Weekly + latest only
python main.py --weekly --latest-only

# Custom output directory
python main.py --output-dir my_output

# Skip CSV, JSON, or summary
python main.py --no-csv --no-json --no-summary
```

### Output files

- **Default**: `output/uk/bess_uk_multi_source.csv`, `.json` (merged from all sources, deduplicated), and `output/uk/uk_investment_scope_summary.csv`.
- **With `--weekly`**: Merged file named with date (e.g. `bess_uk_multi_source_2025-02-03.csv`); summary CSV appends one row per run with `run_date`.

### Investment scope summary

`uk_investment_scope_summary.csv` has one row per run with:

- `run_date`, `total_projects`, `total_mw`
- `count_planned`, `count_consented`, `count_in_construction`, `count_operational`
- `count_early_stage_development`, `count_construction_finance`, `count_ma_offtake`

Use it to compare weekly and understand how investment scope (early-stage vs construction/finance vs M&A) and total MW evolve.

## Sources

Aligned with [docs/SOURCES_MAP.md](docs/SOURCES_MAP.md) and Gemini (Government, News, Developers). Optional scrapers (TEC, PINS, ECR, EirGrid) run if modules load; failures are logged and do not stop the run.

| Source | Description |
|--------|-------------|
| DESNZ REPD | UK Renewable Energy Planning Database – solar & storage by status. |
| NESO TEC Register | Transmission Entry Capacity – projects with grid connection agreements. |
| PINS NSIP | Planning Inspectorate – Nationally Significant Infrastructure (>50MW solar). |
| UKPN ECR | UK Power Networks Embedded Capacity Register (distribution-connected). |
| EirGrid Ireland | Connected & Contracted generators (Ireland) – link list. |
| EDF, BSR, Root Power, Fidra, SSE | Developer project pages (BESS/solar). |
| Energy-Storage.news / Solar Power Portal | UK BESS & solar news headlines. |

## Investment opportunity mapping

- **Planned / Consented** → Early-stage development  
- **In-construction** → Construction / finance  
- **Operational** → M&A / offtake / operations  

## Project fields (CSV/JSON)

- `scraped_at` – run timestamp (UTC)
- `country`, `region`, `site_name`, `capacity_mw`, `capacity_mw_numeric` (parsed for sorting)
- `status`, `investment_opportunity`, `source`, `url`

## Requirements

- Python 3.10+
- `requests`, `beautifulsoup4`, `pandas`, `lxml` (see `requirements.txt`)

## License

Use in line with the terms of the data sources (EDF Renewables) and applicable law. Respect robots.txt and rate limits.
