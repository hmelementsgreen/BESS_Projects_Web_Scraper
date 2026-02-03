# UK BESS & Solar – Investment opportunity sources map

Aligned with **Elements Green** (greenfield solar + storage developer; land origination → planning → grid → build → operate/transact).  
Sources prioritised for **latest investment opportunities** and **regular updates**.

---

## 1. Government / Official / Public Data (Gemini + GPT)

| Source | What it provides | Why it fits Elements Green | In scraper? | Access |
|--------|------------------|----------------------------|-------------|--------|
| **DESNZ – REPD (Renewable Energy Planning Database)** | UK solar & storage projects: capacity, status (application/consented/operational) | Core pipeline visibility; early → operational | **Yes** | Free / UK |
| **NESO TEC Register (National Grid ESO)** | Transmission Entry Capacity: projects with grid connection agreements | Grid strategy; see who has transmission capacity | **Yes** | Free / UK |
| **Embedded Capacity Registers (ECR)** | DNO spreadsheets: distribution-connected projects (<50MW) | BESS/solar sweet spot; queue at substations | **Yes (UKPN)** | Free / UK |
| **Planning Inspectorate (PINS) NSIP** | Nationally Significant Infrastructure (>50MW solar, etc.) | Mega-solar pipeline; application progress | **Yes** | Free / UK |
| **EirGrid / ESB (Ireland)** | Connected & Contracted generators (PDF lists) | Ireland pipeline; 13 GW expansion | **Yes (links)** | Free / Ireland |
| UK Planning Portal | Live planning applications by LA | Newly submitted schemes | No (later) | Free / UK |
| Local Authority Planning Portals | Application documents, site plans | Land screening, substation proximity | No (later) | Free / UK |
| National Grid ET | Transmission network, substations | Substation-led land origination | No (manual) | Free / UK |
| Other DNOs (WPD, etc.) | ECR spreadsheets | Regional feasibility | No (later) | Free / UK |

---

## 2. Industry Bodies & Market Intelligence

| Source | What it provides | Why it fits Elements Green | In scraper? | Access |
|--------|------------------|----------------------------|-------------|--------|
| RenewableUK | UK BESS & renewables pipeline reports | Authoritative pipeline data | No (manual) | Mixed |
| Solar Energy UK | UK solar deployment, planning & grid | Large-scale solar development | No (manual) | Mixed |
| Cornwall Insight | Power markets, storage revenue | Investment & offtake strategy | No | Paid |
| BESS Analytics | Global & UK BESS pipeline | Storage deal sourcing | No | Paid |
| Solar Media | Events, reports, project tracking | Ecosystem visibility | No (manual) | Mixed |

---

## 3. News & Deal-Relevant Media

| Source | What it gives | Why it fits Elements Green | In scraper? | Access |
|--------|---------------|----------------------------|-------------|--------|
| **Energy-Storage.news** | UK & global BESS projects, M&A, financing | Best single source for BESS deals | **Yes** | Mostly free |
| **Solar Power Portal** | UK solar planning, construction & sales | RTB and in-construction solar | **Yes** | Mostly free |
| Current± | Solar + storage + grid reforms | Policy + project crossover | No (later) | Free |
| Recharge | M&A, developer sales, funds | Transaction intelligence | No | Paid |
| PV Tech | Utility-scale solar & storage | International benchmarking | No (later) | Free |

---

## 4. Developer / Operator Project Pages

| Developer / Operator | What it provides | In scraper? |
|----------------------|------------------|-------------|
| **EDF Renewables UK & Ireland** | Battery storage list | **Yes** |
| **British Solar Renewables** | UK battery storage projects | **Yes** |
| **Root Power** | BESS portfolio | **Yes** |
| **Fidra Energy** | UK energy storage (Thorpe Marsh, etc.) | **Yes** |
| **SSE Renewables** | Our-sites BESS entries | **Yes** |
| Lightsource bp | Global & UK solar + storage pipeline | No (later) |
| NextEnergy Capital | Fund acquisitions, operational assets | No (later) |
| Low Carbon | UK solar & BESS pipeline | No (later) |
| RES | Solar, storage, wind projects | No (later) |
| Harmony Energy | UK BESS portfolio | No (later) |
| Statkraft | UK solar/BESS developments | No (later) |

---

## 5. Deal Flow, Transactions & Land

| Source | What it gives | In scraper? | Access |
|--------|---------------|-------------|--------|
| IJGlobal | Project finance, acquisitions | No | Paid |
| Inframation | M&A, asset sales | No | Paid |
| Savills Energy | Land opportunities, developer mandates | No (manual) | Mostly free |
| BNP Paribas Real Estate | Solar & storage land and sales | No (manual) | Mostly free |

---

## Practical monitoring stack (Elements Green)

- **Automate / scrape:** REPD, TEC Register, ECR (UKPN), PINS NSIP, EirGrid (links), Energy-Storage.news, Solar Power Portal, developer project pages (EDF, BSR, Root Power, Fidra, SSE). **Deduplication:** same project (site + capacity + region) from multiple sources is merged into one row.
- **Weekly manual:** Current±, Recharge, more developer pipelines.
- **Monthly / strategic:** RenewableUK, Solar Energy UK, Cornwall Insight.
- **Deal-driven:** IJGlobal, Inframation, land agent bulletins.

---

## Legend

- **In scraper? Yes** = included in this repo’s multi-source UK scraper.
- **No (later)** = candidate for future scraping or integration.
- **No (manual)** = use manually or via RSS/bookmarks.
