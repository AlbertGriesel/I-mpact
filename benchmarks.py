"""
Benchmarks and the impact score.

Benchmarks are shown only with a clear label of source and geographic scope
(spec §13.6), and comparisons that would mislead are flagged as context-only.
The impact score (0-100, higher = lighter footprint) drives the mascot and
wallpaper; 50 means "at the benchmark", and the transition is gradual.
"""

BENCHMARKS = {
    "water_l_person_day": {
        "value": 218.0,
        "label": "South African average (218 L/person/day)",
        "source": "South African government per-capita benchmark",
        "scope": "South Africa",
    },
    "water_l_person_day_global": {
        "value": 173.0,
        "label": "Rough global domestic average (~173 L/person/day)",
        "source": "Literature approximation — varies enormously by country",
        "scope": "Global (approximate)",
    },
    "electricity_kwh_household_month": {
        "value": 350.0,
        "label": "Approximate SA electrified household (~350 kWh/month)",
        "source": "Approximate midpoint of published SA residential figures "
                  "(literature range roughly 250-600 kWh/month)",
        "scope": "South Africa (approximate)",
    },
    "carbon_kg_person_year_sa": {
        "value": 7600.0,
        "label": "SA per-capita emissions (~7.6 t CO2e/year)",
        "source": "World Bank / national inventory, approximate. National "
                  "per-capita totals include industry and electricity "
                  "generation — personal footprints are a subset, so this is "
                  "context, not a exact like-for-like comparison.",
        "scope": "South Africa",
    },
    "carbon_kg_person_year_global": {
        "value": 4700.0,
        "label": "Global per-capita CO2 (~4.7 t/year)",
        "source": "Global Carbon Project, approximate",
        "scope": "Global",
    },
    "carbon_kg_person_year_africa": {
        "value": 1000.0,
        "label": "African per-capita CO2 (~1 t/year)",
        "source": "Global Carbon Project, approximate",
        "scope": "Africa",
    },
}


def get_benchmark(key):
    return BENCHMARKS[key]


def _component(value, benchmark):
    """Map user/benchmark ratio to 0-100 (benchmark -> 50, gradual)."""
    if benchmark <= 0:
        return 50.0
    ratio = max(0.0, float(value)) / benchmark
    return 100.0 / (1.0 + ratio)


def impact_score(water, electricity, carbon, household_size):
    """Composite 0-100 score vs labelled benchmarks (higher is better).

    Components: water L/person/day vs SA 218; household electricity vs the
    approximate SA household benchmark scaled by household size relative to
    the average household (~3.3 people); personal carbon vs SA per-capita
    (context benchmark — labelled as such in the UI).
    """
    w = _component(water["water_litres_person_day"],
                   BENCHMARKS["water_l_person_day"]["value"])

    hh_benchmark = BENCHMARKS["electricity_kwh_household_month"]["value"]
    scaled = hh_benchmark * max(0.5, household_size / 3.3)
    e = _component(electricity["total_electricity_kwh_month"], scaled)

    c = _component(carbon["per_person_co2e_kg_year"],
                   BENCHMARKS["carbon_kg_person_year_sa"]["value"])

    total = round((w + e + c) / 3.0)
    return {
        "total": int(total),
        "water": int(round(w)),
        "electricity": int(round(e)),
        "carbon": int(round(c)),
        "method": "Each component maps your value against a labelled benchmark "
                  "(benchmark = 50 points; lower use scores higher; gradual scale).",
    }


def score_mood(total_score):
    """Bucket used by the mascot/wallpaper: 'good' | 'ok' | 'poor'."""
    if total_score >= 55:
        return "good"
    if total_score >= 40:
        return "ok"
    return "poor"
