"""Official economic data for Metric 2 (GTA V to GTA 6): world aggregates, one value a year.

World Bank WDI publishes actuals up to its latest year; the IMF World Economic Outlook
publishes world real GDP growth including the current year's estimate. Both land in one
raw table keyed by (provider, indicator, geo, year). A year a provider has not published
is absent, never zero.
"""

from __future__ import annotations

from gta6_impact.config import GTA_6_YEAR, GTA_V_YEAR, IMF_INDICATORS, WORLD_BANK_INDICATORS
from gta6_impact.http import Http

WORLD_BANK = "https://api.worldbank.org/v2/country/WLD/indicator/{indicator}"
IMF = "https://www.imf.org/external/datamapper/api/v1/{indicator}/WEOWORLD"


def run(http: Http) -> list[dict]:
    rows = []
    for indicator in WORLD_BANK_INDICATORS:
        payload = http.get_json(
            WORLD_BANK.format(indicator=indicator),
            params={"format": "json", "date": f"{GTA_V_YEAR}:{GTA_6_YEAR}", "per_page": 100},
        )
        if not payload or len(payload) < 2 or not payload[1]:
            raise RuntimeError(f"World Bank returned nothing for {indicator}")
        for record in payload[1]:
            if record["value"] is None:
                continue
            rows.append(
                {
                    "provider": "world_bank",
                    "indicator": indicator,
                    "geo": "WLD",
                    "year": int(record["date"]),
                    "value": float(record["value"]),
                    "last_updated": payload[0].get("lastupdated"),
                }
            )
    for indicator in IMF_INDICATORS:
        payload = http.get_json(IMF.format(indicator=indicator))
        series = (payload or {}).get("values", {}).get(indicator, {}).get("WEOWORLD")
        if not series:
            raise RuntimeError(f"IMF returned nothing for {indicator}")
        for year, value in series.items():
            if GTA_V_YEAR <= int(year) <= GTA_6_YEAR and value is not None:
                rows.append(
                    {
                        "provider": "imf_weo",
                        "indicator": indicator,
                        "geo": "WLD",
                        "year": int(year),
                        "value": float(value),
                        "last_updated": None,
                    }
                )
    return rows
