"""
Municipal tariff tables and reverse-tariff conversion.

A monetary bill amount may only be converted to consumption through a
municipality-specific progressive tariff — never a single national
R-per-litre or R-per-kWh rule (calc doc §2.2 / §3.2). The prototype supports
a small set of major municipalities; anywhere else the engine falls back to
behavioural estimation, exactly as the calculation document allows.

IMPORTANT: the numbers below are approximate 2024/25 residential snapshots
(VAT inclusive) intended for the prototype. They are labelled MEDIUM
confidence in results and should be re-verified before production use.
"""

# Water: rising-block tariffs, R per kL. block = (upper bound in kL, rate)
WATER_TARIFFS = {
    "cape town": {
        "label": "City of Cape Town (domestic full, approx. 2024/25)",
        "fixed_charge": 0.0,
        "blocks": [
            {"max_kl": 6.0, "rate_per_kl": 29.06},
            {"max_kl": 10.5, "rate_per_kl": 37.05},
            {"max_kl": 35.0, "rate_per_kl": 55.60},
            {"max_kl": None, "rate_per_kl": 102.98},
        ],
    },
    "johannesburg": {
        "label": "City of Johannesburg / Joburg Water (approx. 2024/25)",
        "fixed_charge": 0.0,
        "blocks": [
            {"max_kl": 6.0, "rate_per_kl": 29.93},
            {"max_kl": 10.0, "rate_per_kl": 31.98},
            {"max_kl": 15.0, "rate_per_kl": 33.85},
            {"max_kl": 20.0, "rate_per_kl": 39.10},
            {"max_kl": 30.0, "rate_per_kl": 53.86},
            {"max_kl": None, "rate_per_kl": 57.68},
        ],
    },
    "ethekwini": {
        "label": "eThekwini / Durban (approx. 2024/25)",
        "fixed_charge": 0.0,
        "blocks": [
            {"max_kl": 6.0, "rate_per_kl": 25.28},
            {"max_kl": 25.0, "rate_per_kl": 31.61},
            {"max_kl": 30.0, "rate_per_kl": 42.66},
            {"max_kl": None, "rate_per_kl": 93.83},
        ],
    },
    "tshwane": {
        "label": "City of Tshwane / Pretoria (approx. 2024/25)",
        "fixed_charge": 0.0,
        "blocks": [
            {"max_kl": 6.0, "rate_per_kl": 24.30},
            {"max_kl": 12.0, "rate_per_kl": 34.72},
            {"max_kl": 18.0, "rate_per_kl": 45.98},
            {"max_kl": 24.0, "rate_per_kl": 53.15},
            {"max_kl": None, "rate_per_kl": 60.83},
        ],
    },
}

# Electricity: rising-block tariffs, R per kWh.
ELECTRICITY_TARIFFS = {
    "cape town": {
        "label": "City of Cape Town Home tariff (approx. 2024/25)",
        "fixed_charge": 0.0,
        "blocks": [
            {"max_kwh": 600.0, "rate_per_kwh": 3.55},
            {"max_kwh": None, "rate_per_kwh": 4.32},
        ],
    },
    "johannesburg": {
        "label": "City Power Johannesburg prepaid (approx. 2024/25)",
        "fixed_charge": 0.0,
        "blocks": [
            {"max_kwh": 350.0, "rate_per_kwh": 2.72},
            {"max_kwh": 500.0, "rate_per_kwh": 3.19},
            {"max_kwh": None, "rate_per_kwh": 3.51},
        ],
    },
    "ethekwini": {
        "label": "eThekwini Electricity residential (approx. 2024/25)",
        "fixed_charge": 0.0,
        "blocks": [
            {"max_kwh": 350.0, "rate_per_kwh": 2.56},
            {"max_kwh": None, "rate_per_kwh": 3.20},
        ],
    },
    "tshwane": {
        "label": "City of Tshwane residential (approx. 2024/25)",
        "fixed_charge": 0.0,
        "blocks": [
            {"max_kwh": 100.0, "rate_per_kwh": 2.61},
            {"max_kwh": 400.0, "rate_per_kwh": 3.05},
            {"max_kwh": 650.0, "rate_per_kwh": 3.32},
            {"max_kwh": None, "rate_per_kwh": 3.58},
        ],
    },
    "eskom": {
        "label": "Eskom Homepower direct customers (approx. 2024/25)",
        "fixed_charge": 0.0,
        "blocks": [
            {"max_kwh": 600.0, "rate_per_kwh": 3.37},
            {"max_kwh": None, "rate_per_kwh": 4.10},
        ],
    },
}

_ALIASES = {
    "cape town": ["cape town", "kaapstad", "cct", "city of cape town"],
    "johannesburg": ["johannesburg", "joburg", "jhb", "city power", "joburg water"],
    "ethekwini": ["ethekwini", "durban", "dbn"],
    "tshwane": ["tshwane", "pretoria", "pta"],
    "eskom": ["eskom"],
}


def match_municipality(text, tariffs):
    """Match free-text municipality/utility input to a tariff key, or None."""
    if not text:
        return None
    t = str(text).lower()
    for key, aliases in _ALIASES.items():
        if key in tariffs and any(a in t for a in aliases):
            return key
    return None


def _reverse_blocks(amount, fixed_charge, blocks, cap_key, rate_key):
    """Walk a rising-block tariff backwards: money -> consumption."""
    spend = max(0.0, float(amount) - float(fixed_charge))
    if spend <= 0:
        return 0.0
    used, prev_cap = 0.0, 0.0
    for block in blocks:
        cap = block[cap_key]
        rate = block[rate_key]
        if rate <= 0:
            continue
        if cap is None:
            used += spend / rate
            return used
        size = cap - prev_cap
        cost_of_block = size * rate
        if spend >= cost_of_block:
            used += size
            spend -= cost_of_block
            prev_cap = cap
        else:
            used += spend / rate
            return used
    return used


def water_kl_from_bill(bill_rand, municipality_text):
    """Approximate monthly kL from a water bill amount.

    Returns (kl, tariff_label) or (None, None) when the municipality is not
    supported — the caller then uses the behavioural fallback.
    """
    key = match_municipality(municipality_text, WATER_TARIFFS)
    if key is None or not bill_rand or bill_rand <= 0:
        return None, None
    t = WATER_TARIFFS[key]
    kl = _reverse_blocks(bill_rand, t["fixed_charge"], t["blocks"], "max_kl", "rate_per_kl")
    return round(kl, 2), t["label"]


def electricity_kwh_from_bill(bill_rand, municipality_text):
    """Approximate monthly kWh from an electricity bill / prepaid spend.

    Returns (kwh, tariff_label) or (None, None) when unsupported.
    """
    key = match_municipality(municipality_text, ELECTRICITY_TARIFFS)
    if key is None or not bill_rand or bill_rand <= 0:
        return None, None
    t = ELECTRICITY_TARIFFS[key]
    kwh = _reverse_blocks(bill_rand, t["fixed_charge"], t["blocks"], "max_kwh", "rate_per_kwh")
    return round(kwh, 1), t["label"]


def supported_water_municipalities():
    return [t["label"] for t in WATER_TARIFFS.values()]


def supported_electricity_utilities():
    return [t["label"] for t in ELECTRICITY_TARIFFS.values()]
