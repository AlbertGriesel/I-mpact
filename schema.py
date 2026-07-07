"""
The shared assessment schema.

Non-negotiable rule 3 (spec appendix A): the guided questionnaire and the AI
conversation collect the SAME structured data and feed the SAME deterministic
calculation engine. This module is that single source of truth:

  * default_assessment()      – the empty structure
  * OPTIONS                   – every enumerated choice
  * merge_updates()           – validated merging of AI-extracted values
  * missing_important_fields()– drives conversational conditional logic
  * is_calculable()           – the minimum-data gate before calculating
"""

import copy

OPTIONS = {
    "renewable_source": ["None", "Solar", "Wind"],
    "backup_power": ["None", "Generator", "Inverter and battery",
                     "Solar battery backup", "UPS"],
    "generator_fuel_type": ["Petrol", "Diesel", "LPG", "Natural gas"],
    "generator_coverage": ["Whole home", "Essential loads only"],
    "backup_charge_source": ["Grid", "Solar", "Both"],
    "electricity_value_kind": ["Grid import (bill / prepaid / meter)",
                               "Whole-house total (my own estimate)"],
    "cabin_class": ["Economy", "Premium Economy", "Business", "First"],
    "trip_type": ["One-way", "Return"],
    "public_transport": ["None", "Bus", "Train", "Minibus taxi / taxi",
                         "Subway", "Other"],
    "vehicle_fuel": ["petrol", "diesel", "electric"],
    "heating_method": ["None", "Electricity", "Gas", "Coal", "Wood",
                       "Paraffin / kerosene", "Heat pump"],
    "diet": ["Heavy meat eater", "Average diet", "Mostly chicken",
             "Pescatarian", "Vegetarian", "Vegan"],
    "food_waste": ["None", "Very little", "Around 10%", "Around 20%",
                   "More than 30%"],
    "shopping_habits": ["Much less", "Less", "Average", "More", "Much more"],
}


def default_assessment():
    """Empty assessment. None means 'not provided'; the engine falls back
    down the data-priority ladder for anything missing."""
    return {
        "general": {
            "household_size": 1,
            "country": "South Africa",
            "region": "",
            "municipality": "",
        },
        "water": {
            # measured (priority 1-2)
            "water_kl_month": None,          # kL/month, manual or bill-extracted
            "water_bill_rand": None,         # R/month (tariff conversion fallback)
            "measured_source": None,         # "bill" | "manual" | None
            "bill_uploaded": False,
            # rainwater
            "uses_rainwater": False,
            "rainwater_percentage": 0,
            # estimation questions (only used when no measured data)
            "shower_minutes": None,
            "showers_per_week": None,
            "garden_irrigation": False,
            "swimming_pool": False,
        },
        "electricity": {
            "kwh_month": None,               # kWh/month
            # whether kwh_month is grid import (bill) or whole-house estimate —
            # decides whether the renewable share may be subtracted (calc doc §3.1)
            "kwh_kind": "Grid import (bill / prepaid / meter)",
            "bill_rand": None,
            "measured_source": None,         # "bill" | "manual" | None
            "bill_uploaded": False,
            # renewables
            "renewable_source": "None",
            "renewable_percentage": 0,
            # backup power / loadshedding
            "backup_power": "None",
            "generator_fuel_type": "Petrol",
            "generator_litres_per_month": None,
            "generator_hours_per_month": None,
            "generator_fuel_rate_l_per_hour": None,   # manufacturer rate if known
            "generator_coverage": "Essential loads only",
            "backup_share_percent": 0,
            "backup_charge_source": "Grid",
            # appliance estimation (only when no measured kWh)
            "home_size": "",
            "electric_geyser": False,
            "geyser_hours_per_day": None,
            "air_conditioner": False,
            "aircon_kw": None,
            "aircon_hours_per_day": None,
            "aircon_months_per_year": None,
            "electric_stove": False,
            "stove_minutes_per_day": None,
            "oven_hours_per_week": None,
            "pool_pump": False,
            "pool_pump_watts": None,
            "pool_pump_hours_per_day": None,
        },
        "transport": {
            "flights": [],   # {departure_airport, arrival_airport, cabin_class,
                             #  trip_type, trips_per_year}
            "vehicle": {
                "owns_vehicle": False,
                "manufacturer": "",
                "model": "",
                "year": 2020,
                "annual_km": None,
                "average_passengers": 1,
                # fallback when the database lookup fails (calc doc §6.2)
                "fuel_type": None,           # petrol | diesel | electric
                "l_per_100km": None,
                "kwh_per_km": None,
            },
            "public_transport": {
                "type": "None",
                "weekly_km": None,
            },
        },
        "lifestyle": {
            "heating_method": "None",
            "heating_months_per_year": None,
            "heating_hours_per_day": None,
            "heater_watts": None,            # electric heating
            # fuel heating quantities (hours alone can't give emissions)
            "heating_lpg_litres_per_year": None,
            "heating_gas_m3_per_year": None,
            "heating_paraffin_litres_per_year": None,
            "heating_coal_kg_per_year": None,
            "heating_wood_kg_per_year": None,
            "diet": "Average diet",
            "food_waste": "None",
            "shopping_habits": "Average",
            "buys_offsets": False,
            "offset_tonnes_per_year": None,
        },
    }


def default_flight():
    return {"departure_airport": "", "arrival_airport": "",
            "cabin_class": "Economy", "trip_type": "Return",
            "trips_per_year": 1}


# --------------------------------------------------------------------------
# Validation and merging (used by the AI conversation and bill extraction)
# --------------------------------------------------------------------------

_NUMERIC_BOUNDS = {
    # section, field: (min, max)
    ("general", "household_size"): (1, 30),
    ("water", "water_kl_month"): (0, 500),
    ("water", "water_bill_rand"): (0, 100000),
    ("water", "rainwater_percentage"): (0, 100),
    ("water", "shower_minutes"): (0, 120),
    ("water", "showers_per_week"): (0, 50),
    ("electricity", "kwh_month"): (0, 20000),
    ("electricity", "bill_rand"): (0, 100000),
    ("electricity", "renewable_percentage"): (0, 100),
    ("electricity", "generator_litres_per_month"): (0, 2000),
    ("electricity", "generator_hours_per_month"): (0, 744),
    ("electricity", "generator_fuel_rate_l_per_hour"): (0, 20),
    ("electricity", "backup_share_percent"): (0, 100),
    ("electricity", "geyser_hours_per_day"): (0, 24),
    ("electricity", "aircon_kw"): (0, 20),
    ("electricity", "aircon_hours_per_day"): (0, 24),
    ("electricity", "aircon_months_per_year"): (0, 12),
    ("electricity", "stove_minutes_per_day"): (0, 600),
    ("electricity", "oven_hours_per_week"): (0, 60),
    ("electricity", "pool_pump_watts"): (0, 5000),
    ("electricity", "pool_pump_hours_per_day"): (0, 24),
    ("lifestyle", "heating_months_per_year"): (0, 12),
    ("lifestyle", "heating_hours_per_day"): (0, 24),
    ("lifestyle", "heater_watts"): (0, 10000),
    ("lifestyle", "heating_lpg_litres_per_year"): (0, 5000),
    ("lifestyle", "heating_gas_m3_per_year"): (0, 5000),
    ("lifestyle", "heating_paraffin_litres_per_year"): (0, 5000),
    ("lifestyle", "heating_coal_kg_per_year"): (0, 20000),
    ("lifestyle", "heating_wood_kg_per_year"): (0, 20000),
    ("lifestyle", "offset_tonnes_per_year"): (0, 1000),
}

_ENUM_FIELDS = {
    ("electricity", "renewable_source"): "renewable_source",
    ("electricity", "backup_power"): "backup_power",
    ("electricity", "generator_fuel_type"): "generator_fuel_type",
    ("electricity", "generator_coverage"): "generator_coverage",
    ("electricity", "backup_charge_source"): "backup_charge_source",
    ("electricity", "kwh_kind"): "electricity_value_kind",
    ("lifestyle", "heating_method"): "heating_method",
    ("lifestyle", "diet"): "diet",
    ("lifestyle", "food_waste"): "food_waste",
    ("lifestyle", "shopping_habits"): "shopping_habits",
}


def _coerce(section, field, value, current):
    """Coerce one incoming value to the schema type. Raises ValueError."""
    if value is None:
        return None
    if (section, field) in _NUMERIC_BOUNDS:
        lo, hi = _NUMERIC_BOUNDS[(section, field)]
        v = float(value)
        if not (lo <= v <= hi):
            raise ValueError(f"{field}={v} outside plausible range [{lo}, {hi}]")
        if field in ("household_size", "showers_per_week"):
            return int(round(v))
        return v
    if (section, field) in _ENUM_FIELDS:
        allowed = OPTIONS[_ENUM_FIELDS[(section, field)]]
        sv = str(value).strip()
        for option in allowed:
            if sv.lower() == option.lower():
                return option
        raise ValueError(f"{field}='{value}' not one of {allowed}")
    if isinstance(current, bool):
        if isinstance(value, bool):
            return value
        return str(value).strip().lower() in ("true", "yes", "y", "1")
    if isinstance(current, str) or current is None:
        return str(value).strip()
    return value


def merge_updates(data, updates):
    """Merge a nested updates dict (as produced by the AI collection tool)
    into an assessment dict, validating every field.

    Returns (merged, applied, rejected) where applied/rejected are lists of
    human-readable strings. Unknown fields are rejected, never invented
    (non-negotiable rule: the LLM may not invent values).
    """
    merged = copy.deepcopy(data)
    applied, rejected = [], []

    for section, fields in (updates or {}).items():
        if section == "flights":
            # allow a top-level flights list as a convenience
            fields = {"flights": fields}
            section = "transport"
        if section not in merged or not isinstance(fields, dict):
            rejected.append(f"unknown section '{section}'")
            continue
        for field, value in fields.items():
            try:
                if section == "transport" and field == "flights":
                    flights = []
                    for f in (value or []):
                        nf = default_flight()
                        nf["departure_airport"] = str(f.get("departure_airport", "")).strip().upper()
                        nf["arrival_airport"] = str(f.get("arrival_airport", "")).strip().upper()
                        cabin = str(f.get("cabin_class", "Economy")).title()
                        nf["cabin_class"] = cabin if cabin in OPTIONS["cabin_class"] else "Economy"
                        trip = str(f.get("trip_type", "Return")).title()
                        nf["trip_type"] = trip if trip in OPTIONS["trip_type"] else "Return"
                        nf["trips_per_year"] = max(0, min(365, int(f.get("trips_per_year", 1))))
                        flights.append(nf)
                    merged["transport"]["flights"] = flights
                    applied.append(f"flights ({len(flights)} route(s))")
                elif section == "transport" and field in ("vehicle", "public_transport"):
                    sub = merged["transport"][field]
                    for k, v in (value or {}).items():
                        if k not in sub:
                            rejected.append(f"unknown field transport.{field}.{k}")
                            continue
                        if k == "type":
                            sv = str(v).strip()
                            match = next((o for o in OPTIONS["public_transport"]
                                          if o.lower() == sv.lower()), None)
                            if match is None:
                                rejected.append(f"public_transport.type='{v}' invalid")
                                continue
                            sub[k] = match
                        elif k == "fuel_type" and v is not None:
                            sv = str(v).strip().lower()
                            if sv not in OPTIONS["vehicle_fuel"]:
                                rejected.append(f"vehicle.fuel_type='{v}' invalid")
                                continue
                            sub[k] = sv
                        elif k in ("annual_km", "l_per_100km", "kwh_per_km", "weekly_km"):
                            fv = float(v)
                            if fv < 0 or fv > 500000:
                                rejected.append(f"{field}.{k}={v} out of range")
                                continue
                            sub[k] = fv
                        elif k in ("average_passengers", "year"):
                            sub[k] = int(v)
                        elif k == "owns_vehicle":
                            sub[k] = bool(v) if isinstance(v, bool) else \
                                str(v).lower() in ("true", "yes", "1")
                        else:
                            sub[k] = str(v).strip()
                        applied.append(f"{field}.{k}")
                else:
                    if field not in merged[section]:
                        rejected.append(f"unknown field {section}.{field}")
                        continue
                    merged[section][field] = _coerce(
                        section, field, value, merged[section][field])
                    applied.append(f"{section}.{field}")
            except (ValueError, TypeError) as exc:
                rejected.append(f"{section}.{field}: {exc}")
    return merged, applied, rejected


# --------------------------------------------------------------------------
# Conditional logic: what still matters? (drives chat + minimum-data gate)
# --------------------------------------------------------------------------

def missing_important_fields(data):
    """Ordered list of (field_path, question_hint) still worth asking.

    Mirrors the questionnaire's progressive disclosure: estimation questions
    only appear when measured data is unavailable (spec §2.1). The AI
    conversation must stop once this list is empty or only optional items
    remain.
    """
    missing = []
    g, w, e, t, l = (data["general"], data["water"], data["electricity"],
                     data["transport"], data["lifestyle"])

    if not g.get("household_size"):
        missing.append(("general.household_size", "How many people live in the household?"))

    # --- water: measured beats estimated
    if w.get("water_kl_month") is None:
        if w.get("water_bill_rand") is None:
            missing.append(("water.water_kl_month",
                            "Monthly water use in kilolitres (from a bill/meter), "
                            "or the monthly water bill amount in rand — or say you don't know."))
        if w.get("shower_minutes") is None:
            missing.append(("water.shower_minutes", "Average shower length in minutes."))
        if w.get("showers_per_week") is None:
            missing.append(("water.showers_per_week", "Showers per week (per person)."))
    if w.get("uses_rainwater") and not w.get("rainwater_percentage"):
        missing.append(("water.rainwater_percentage",
                        "Approximate % of household water that comes from rainwater."))

    # --- electricity
    if e.get("kwh_month") is None:
        if e.get("bill_rand") is None:
            missing.append(("electricity.kwh_month",
                            "Monthly electricity in kWh (bill/prepaid), or the monthly "
                            "spend in rand — or say you don't know."))
        else:
            pass
        # appliance estimation only when nothing measured
        if e.get("bill_rand") is None:
            if e.get("electric_geyser") and e.get("geyser_hours_per_day") is None:
                missing.append(("electricity.geyser_hours_per_day",
                                "Roughly how many hours a day does the geyser heat?"))
            if e.get("air_conditioner") and e.get("aircon_hours_per_day") is None:
                missing.append(("electricity.aircon_hours_per_day",
                                "Aircon: rated kW (approx), hours/day and months/year used."))
            if e.get("pool_pump") and e.get("pool_pump_hours_per_day") is None:
                missing.append(("electricity.pool_pump_hours_per_day",
                                "Pool pump wattage and hours per day."))
    if e.get("renewable_source", "None") != "None" and not e.get("renewable_percentage"):
        missing.append(("electricity.renewable_percentage",
                        "Approximate % of household electricity from your renewable source."))
    if e.get("backup_power") == "Generator" and \
            e.get("generator_litres_per_month") is None and \
            e.get("generator_hours_per_month") is None:
        missing.append(("electricity.generator_litres_per_month",
                        "Generator fuel: litres used in a typical month "
                        "(or hours/month if litres unknown)."))

    # --- transport
    v = t["vehicle"]
    if v.get("owns_vehicle"):
        if v.get("annual_km") is None:
            missing.append(("transport.vehicle.annual_km", "Kilometres driven per year."))
        from vehicles import lookup_vehicle
        if lookup_vehicle(v.get("manufacturer"), v.get("model")) is None and \
                v.get("l_per_100km") is None and v.get("kwh_per_km") is None:
            missing.append(("transport.vehicle.fuel_type",
                            "Vehicle not in our database: fuel type and average "
                            "consumption (L/100km, or kWh/km if electric)."))
    if t["public_transport"].get("type", "None") != "None" and \
            t["public_transport"].get("weekly_km") is None:
        missing.append(("transport.public_transport.weekly_km",
                        "Average km travelled by public transport each week."))

    # --- lifestyle heating fuel quantities
    hm = l.get("heating_method", "None")
    if hm == "Electricity" and l.get("heating_hours_per_day") is None:
        missing.append(("lifestyle.heating_hours_per_day",
                        "Electric heating: hours/day and months/year used."))
    if hm == "Gas" and l.get("heating_lpg_litres_per_year") is None and \
            l.get("heating_gas_m3_per_year") is None:
        missing.append(("lifestyle.heating_lpg_litres_per_year",
                        "Gas heating: roughly how many litres of LPG (or m³ of gas) per year?"))
    if hm == "Paraffin / kerosene" and l.get("heating_paraffin_litres_per_year") is None:
        missing.append(("lifestyle.heating_paraffin_litres_per_year",
                        "Roughly how many litres of paraffin per year?"))
    if hm == "Coal" and l.get("heating_coal_kg_per_year") is None:
        missing.append(("lifestyle.heating_coal_kg_per_year",
                        "Roughly how many kg of coal per year?"))
    if l.get("buys_offsets") and l.get("offset_tonnes_per_year") is None:
        missing.append(("lifestyle.offset_tonnes_per_year",
                        "Approximate tonnes of CO2e offset per year."))
    return missing


def is_calculable(data):
    """Minimum meaningful data: household size known and each metric can at
    least fall back to a defensible method. Water and electricity always have
    national/appliance fallbacks, so household size is the true gate; we also
    require diet (defaulted) which is always present."""
    return bool(data["general"].get("household_size"))


def completeness(data):
    """Rough % of the important questions answered — for progress UI."""
    total_gaps = len(missing_important_fields(default_assessment()))
    now_gaps = len(missing_important_fields(data))
    if total_gaps == 0:
        return 100
    return int(round(100 * max(0, total_gaps - now_gaps) / total_gaps))
