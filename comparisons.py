"""
Relatable equivalence comparisons (spec §13.5).

Each comparison is based on a defined, defensible conversion factor and is
chosen for sensible scale — a comparison is only used when the resulting
count lands between 0.3 and 900, avoiding absurd-but-true statements.
"""

from factors import F

# (threshold-friendly) factor definitions
WATER_EQUIV = [
    {"unit_l": 150.0, "singular": "full bathtub", "plural": "full bathtubs",
     "note": "150 L per standard tub"},
    {"unit_l": 40000.0, "singular": "small backyard swimming pool",
     "plural": "small backyard swimming pools", "note": "~40 kL pool"},
    {"unit_l": 2500000.0, "singular": "Olympic swimming pool",
     "plural": "Olympic swimming pools", "note": "2.5 ML"},
]

ELEC_EQUIV = [
    {"unit_kwh": 0.12, "singular": "kettle boil", "plural": "kettle boils",
     "note": "~0.12 kWh per 1.5 L boil"},
    {"unit_kwh": 30.0, "singular": "month of running an efficient fridge",
     "plural": "months of running an efficient fridge",
     "note": "~30 kWh/month for an A-rated fridge"},
    {"unit_kwh": 3.0, "singular": "hour of geyser heating",
     "plural": "hours of geyser heating", "note": "3 kW element"},
]

CARBON_EQUIV = [
    {"unit_kg": 319.0, "singular": "return Cape Town–Johannesburg economy flight",
     "plural": "return Cape Town–Johannesburg economy flights",
     "note": "1,269 km × 0.12576 kg/pkm × 2 (short-haul proxy factor)"},
    {"unit_kg": 0.165, "singular": "km driven in a typical petrol car",
     "plural": "km driven in a typical petrol car",
     "note": "7 L/100km × 2.354 kg CO2e/L"},
    {"unit_kg": 21.0, "singular": "year of carbon absorbed by a growing tree",
     "plural": "years of tree growth to absorb",
     "note": "~21 kg CO2/tree/year (widely used approximation)"},
]


def _pick(value, options, unit_key):
    """Pick the equivalence whose count lands in a relatable range."""
    best = None
    for opt in options:
        count = value / opt[unit_key]
        if 0.3 <= count <= 900:
            # prefer counts closest to ~20 for intuitiveness
            score = abs(count - 20)
            if best is None or score < best[0]:
                best = (score, count, opt)
    if best is None and options:
        opt = options[0]
        best = (0, value / opt[unit_key], opt)
    return best[1], best[2]


def _fmt(count):
    if count >= 20:
        return f"{count:,.0f}"
    if count >= 2:
        return f"{count:,.1f}".rstrip("0").rstrip(".")
    return f"{count:,.1f}"


def water_comparison(litres, period_label):
    count, opt = _pick(litres, WATER_EQUIV, "unit_l")
    name = opt["singular"] if 0.5 <= count < 1.5 else opt["plural"]
    return (f"Your water use per {period_label} is roughly **{_fmt(count)} "
            f"{name}** ({opt['note']}).")


def electricity_comparison(kwh, period_label):
    count, opt = _pick(kwh, ELEC_EQUIV, "unit_kwh")
    name = opt["singular"] if 0.5 <= count < 1.5 else opt["plural"]
    return (f"Your electricity per {period_label} equals about **{_fmt(count)} "
            f"{name}** ({opt['note']}).")


def carbon_comparison(kg, period_label):
    count, opt = _pick(kg, CARBON_EQUIV, "unit_kg")
    name = opt["singular"] if 0.5 <= count < 1.5 else opt["plural"]
    return (f"Your carbon footprint per {period_label} is comparable to "
            f"**{_fmt(count)} {name}** ({opt['note']}).")
