"""
Benchmarks and the impact score.

Benchmarks are shown only with a clear label of source and geographic scope
(spec §13.6), and comparisons that would mislead are flagged as context-only.
The impact score (higher = lighter footprint) drives the mascot and wallpaper.
Semantics (spec §18): 50 ≈ the benchmark average, 100 = zero net impact under
the methodology, and >100 = genuinely net-positive (only the carbon component
can exceed 100, so a >100 total requires offsets/removals beyond emissions —
never mere better-than-average behaviour). The scale is open above 100.
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


# Approximate per-sector intensities for BUSINESS accounts (spec §5). These
# are deliberately labelled as rough benchmarking guides — commercial energy
# and water intensity vary enormously by building, equipment and country, so
# they are used the same careful way as the household benchmarks: a gradual
# comparison (sector benchmark = 50) and clearly-labelled context, never a
# hard verdict.
#   kwh_m2       — electricity use intensity, kWh per m² per year
#   water_l_m2   — water use intensity, litres per m² per year
#   co2_employee — operational CO2e, kg per employee per year (energy-led)
BUSINESS_SECTOR_BENCHMARKS = {
    "Office / professional services": {"kwh_m2": 200, "water_l_m2": 550, "co2_employee": 2500},
    "Retail / wholesale":             {"kwh_m2": 300, "water_l_m2": 600, "co2_employee": 3000},
    "Restaurant / café / hospitality":{"kwh_m2": 400, "water_l_m2": 2500, "co2_employee": 4000},
    "Manufacturing / industrial":     {"kwh_m2": 350, "water_l_m2": 3000, "co2_employee": 6000},
    "Agriculture / farming":          {"kwh_m2": 120, "water_l_m2": 9000, "co2_employee": 5000},
    "Warehouse / logistics":          {"kwh_m2": 120, "water_l_m2": 150, "co2_employee": 4000},
    "Education":                      {"kwh_m2": 150, "water_l_m2": 700, "co2_employee": 1500},
    "Healthcare":                     {"kwh_m2": 400, "water_l_m2": 1500, "co2_employee": 4000},
    "Construction":                   {"kwh_m2": 100, "water_l_m2": 300, "co2_employee": 5000},
    "IT / data / software":           {"kwh_m2": 350, "water_l_m2": 300, "co2_employee": 2500},
    "Other":                          {"kwh_m2": 200, "water_l_m2": 550, "co2_employee": 2500},
}

BUSINESS_BENCHMARK_LABEL = (
    "Approximate sector benchmarking figures (commercial energy & water "
    "intensity literature). They vary widely by building, equipment and "
    "country — treat them as rough context, not a precise like-for-like score.")


def business_sector_benchmark(sector):
    return BUSINESS_SECTOR_BENCHMARKS.get(
        sector, BUSINESS_SECTOR_BENCHMARKS["Other"])


def get_benchmark(key):
    return BENCHMARKS[key]


def _component(value, benchmark):
    """Map user/benchmark ratio to 0-100 (benchmark -> 50, gradual). At zero
    consumption this approaches 100 = 'zero impact' for that resource (§18)."""
    if benchmark <= 0:
        return 50.0
    ratio = max(0.0, float(value)) / benchmark
    return 100.0 / (1.0 + ratio)


def _carbon_component(net_per_capita, benchmark):
    """Carbon score component with net-zero / net-positive semantics (§18):
    positive net → 0..100 (benchmark = 50, zero net → ~100); a NEGATIVE net
    (offsets/removals exceed emissions) → above 100, scaled by how far below
    zero it goes. This is the only component that can exceed 100, so a >100
    overall score requires genuine net-positive contribution, not just being
    better than average."""
    if net_per_capita is None:
        return 50.0
    if net_per_capita > 0:
        return _component(net_per_capita, benchmark)
    if benchmark <= 0:
        return 100.0
    # net <= 0 → net zero (100) plus a capped bonus for genuine removal
    bonus = min(60.0, (abs(net_per_capita) / benchmark) * 100.0)
    return 100.0 + bonus


def impact_score(water, electricity, carbon, household_size,
                 account_type="personal", sector=None, employees=None,
                 floor_area_m2=None):
    """Composite score vs labelled benchmarks (higher is better; 50 ≈ average,
    100 = net zero, >100 = net positive via the carbon component only).

    Personal components: water L/person/day vs SA 218; household electricity vs
    the approximate SA household benchmark scaled by household size relative to
    the average household (~3.3 people); personal carbon vs SA per-capita
    (context benchmark — labelled as such in the UI).

    Business: delegates to a per-floor-area / per-employee comparison against
    the sector benchmark (spec §5)."""
    if account_type == "business":
        return _business_impact_score(water, electricity, carbon, sector,
                                      employees, floor_area_m2)
    w = _component(water["water_litres_person_day"],
                   BENCHMARKS["water_l_person_day"]["value"])

    hh_benchmark = BENCHMARKS["electricity_kwh_household_month"]["value"]
    scaled = hh_benchmark * max(0.5, household_size / 3.3)
    e = _component(electricity["total_electricity_kwh_month"], scaled)

    # net (offset-adjusted) per-person carbon → enables net-zero / net-positive
    net_pc = carbon.get("per_person_net_co2e_kg_year",
                        carbon["per_person_co2e_kg_year"])
    c = _carbon_component(net_pc, BENCHMARKS["carbon_kg_person_year_sa"]["value"])

    total = round((w + e + c) / 3.0)
    return {
        "total": int(total),
        "water": int(round(w)),
        "electricity": int(round(e)),
        "carbon": int(round(c)),
        "method": "Each component maps your value against a labelled benchmark "
                  "(benchmark = 50 points; lower use scores higher; gradual scale).",
    }


def _business_impact_score(water, electricity, carbon, sector, employees, area):
    """Business score: compares intensity (per m² / per employee) against the
    sector benchmark. Uses whichever measures are available; if a business gave
    no size context at all, returns a neutral 50 (can't fairly benchmark)."""
    bench = business_sector_benchmark(sector)
    e = w = c = None
    comps = []
    if area and electricity.get("kwh_per_m2_year") is not None:
        e = _component(electricity["kwh_per_m2_year"], bench["kwh_m2"])
        comps.append(e)
    if area and water.get("litres_per_m2_year") is not None:
        w = _component(water["litres_per_m2_year"], bench["water_l_m2"])
        comps.append(w)
    if employees and carbon.get("per_employee_co2e_kg_year") is not None:
        net_pe = carbon.get("per_employee_net_co2e_kg_year",
                            carbon["per_employee_co2e_kg_year"])
        c = _carbon_component(net_pe, bench["co2_employee"])
        comps.append(c)
    total = round(sum(comps) / len(comps)) if comps else 50
    return {
        "total": int(total),
        "water": int(round(w)) if w is not None else None,
        "electricity": int(round(e)) if e is not None else None,
        "carbon": int(round(c)) if c is not None else None,
        "method": "Each component maps your per-floor-area or per-employee "
                  "intensity against an approximate sector benchmark "
                  "(benchmark = 50 points; lower intensity scores higher).",
    }


def score_mood(total_score):
    """Bucket used by the mascot/wallpaper: 'good' | 'ok' | 'poor'.
    Aligned to §18 bands (≈50 = average)."""
    if total_score >= 60:
        return "good"
    if total_score >= 40:
        return "ok"
    return "poor"
