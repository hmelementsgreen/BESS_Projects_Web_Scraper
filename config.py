"""
Configuration for BESS Projects Web Scraper – UK only.
Built for Elements Green (London): latest UK BESS projects and investment scope.
Designed for weekly runs.
"""

# Company context
COMPANY_NAME = "Elements Green"
COMPANY_LOCATION = "London"
COMPANY_DESCRIPTION = "Solar and energy storage developer with 22-year track record; pipeline >13 GW (UK, EU, Australia, US)."

# UK-only sources (multiple sites for broader coverage)
SOURCES = {
    "uk": {
        "edf_re_uk": {
            "name": "EDF Renewables UK & Ireland – Battery Storage",
            "url": "https://www.edf-re.uk/our-sites/?view=list&project_types=battery-storage",
            "country": "UK",
        },
        "british_renewables": {
            "name": "British Solar Renewables – UK Battery Storage",
            "url": "https://britishrenewables.com/projects/battery-bess-projects",
            "country": "UK",
        },
        "root_power": {
            "name": "Root Power – BESS Projects",
            "url": "https://www.root-power.com/our-projects/",
            "country": "UK",
        },
        "fidra_energy": {
            "name": "Fidra Energy – UK Energy Storage",
            "url": "https://fidraenergy.com/our-projects/",
            "country": "UK",
        },
        "sse_renewables": {
            "name": "SSE Renewables – Battery Storage",
            "url": "https://www.sserenewables.com/our-sites/",
            "country": "UK",
        },
        "uk_repd": {
            "name": "DESNZ – Renewable Energy Planning Database (REPD)",
            "url": "https://www.gov.uk/government/publications/renewable-energy-planning-database-monthly-extract",
            "country": "UK",
        },
        "energy_storage_news": {
            "name": "Energy-Storage.news – UK BESS news",
            "url": "https://www.energy-storage.news/",
            "country": "UK",
        },
        "solar_power_portal": {
            "name": "Solar Power Portal – UK battery storage",
            "url": "https://www.solarpowerportal.co.uk/",
            "country": "UK",
        },
        "tec_register": {
            "name": "NESO – TEC Register (Transmission Entry Capacity)",
            "url": "https://www.nationalgrideso.com/data-portal/transmission-entry-capacity-tec-register",
            "country": "UK",
        },
        "pins_nsip": {
            "name": "Planning Inspectorate – NSIP (Nationally Significant Infrastructure)",
            "url": "https://national-infrastructure-consenting.planninginspectorate.gov.uk/project-search",
            "country": "UK",
        },
        "ecr_ukpn": {
            "name": "UK Power Networks – Embedded Capacity Register (ECR)",
            "url": "https://ukpowernetworks.opendatasoft.com/explore/dataset/ukpn-embedded-capacity-register",
            "country": "UK",
        },
    },
    "ireland": {
        "eirgrid": {
            "name": "EirGrid – Connected & Contracted Generators (Ireland)",
            "url": "https://www.eirgrid.ie/industry/customer-information/connected-and-contracted-generators",
            "country": "Ireland",
        },
    },
}

# Investment opportunity mapping (status -> opportunity type)
INVESTMENT_OPPORTUNITY_MAP = {
    "planned": "Early-stage development",
    "consented": "Early-stage development",
    "in-construction": "Construction / finance",
    "operational": "M&A / offtake / operations",
    "in operation": "M&A / offtake / operations",
}

# Output
OUTPUT_DIR = "output"
OUTPUT_UK_SUBDIR = "uk"  # output/uk/ for UK-only runs
DEFAULT_ENCODING = "utf-8"
DATE_FORMAT = "%Y-%m-%d"  # for weekly filenames
