"""Which macro factors are relevant to which KMI-30 company.

This is a hand-curated, best-effort categorization by each company's
evident business activity (from its official name — "Oil & Gas Development
Company", "Lucky Cement", "Engro Fertilizers", etc.), NOT scraped or
exhaustively researched. PSX's own `/sector-summary` page (which would give
official sector groupings) turned out to be client-rendered with no data in
the static HTML, and `companies.sector` has been NULL since Phase 1 for the
same reason. Treat this mapping as a reasonable target for refinement once
a real sector source is found, not a source of truth.
"""

SECTOR_SENSITIVITY: dict[str, list[str]] = {
    # Oil & gas E&P / refining / marketing
    "OGDC": ["oil_wti", "oil_brent"],
    "PPL": ["oil_wti", "oil_brent"],
    "MARI": ["oil_wti", "oil_brent"],
    "ATRL": ["oil_wti", "oil_brent"],
    "NRL": ["oil_wti", "oil_brent"],
    "PRL": ["oil_wti", "oil_brent"],
    "PSO": ["oil_wti", "oil_brent"],
    # Gas utilities / power (import-linked fuel costs)
    "SNGP": ["usd_pkr"],
    "SSGC": ["usd_pkr"],
    "HUBC": ["usd_pkr", "oil_wti"],
    # Cement (imported coal/fuel)
    "LUCK": ["usd_pkr"],
    "DGKC": ["usd_pkr"],
    "FCCL": ["usd_pkr"],
    "MLCF": ["usd_pkr"],
    # Fertilizer (gas feedstock/imports)
    "EFERT": ["usd_pkr"],
    "FFC": ["usd_pkr"],
    # Textiles / autos / electronics / pharma / food (import- or export-exposed)
    "NML": ["usd_pkr"],
    "GAL": ["usd_pkr"],
    "GHNI": ["usd_pkr"],
    "HCAR": ["usd_pkr"],
    "SAZEW": ["usd_pkr"],
    "AIRLINK": ["usd_pkr"],
    "PAEL": ["usd_pkr"],
    "CPHL": ["usd_pkr"],
    "SEARL": ["usd_pkr"],
    "FFL": ["usd_pkr"],
    "TREET": ["usd_pkr"],
    "SYS": ["usd_pkr"],  # IT exporter, PKR-sensitive in the opposite direction
    "ENGROH": ["usd_pkr"],
    # Banks
    "MEBL": ["sbp_policy_rate"],
}

# Relevant to every company, regardless of sector.
UNIVERSAL_FACTORS: list[str] = ["cpi_inflation", "sp500"]


def get_relevant_factor_types(ticker: str) -> list[str]:
    return SECTOR_SENSITIVITY.get(ticker, []) + UNIVERSAL_FACTORS
