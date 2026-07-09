"""
Deterministic calculation engine.

Implements the "Environmental Impact Tracker Calculation Information"
document. The LLM never performs footprint arithmetic — it receives these
results and interprets them (non-negotiable rules 5 & appendix §20).

Data priority (calc doc, page 1):
  1. measured consumption  2. bill-extracted consumption
  3. money -> tariff conversion  4. behavioural estimates
  5. national averages / assumptions

Every metric carries a confidence label:
  HIGH   – meter/bill/statement or manually entered measured consumption
  MEDIUM – monetary bill via municipal tariff, or activity calculation
  LOW    – national average or broad appliance estimate

Internal units (calc doc §1): water L/month + L/person/day, electricity
kWh/month + kWh/year, carbon kg CO2e/year.
"""

from factors import (F, DIET_FACTOR_KEYS, FOOD_WASTE_FRACTIONS,
                     SHOPPING_INTENSITY, PUBLIC_TRANSPORT_FACTOR_KEYS)
from tariffs import water_kl_from_bill, electricity_kwh_from_bill
from vehicles import lookup_vehicle
from airports import route_distance_km, same_country

CONF_ORDER = {"HIGH": 3, "MEDIUM": 2, "LOW": 1, "VERY LOW": 0}


def _lowest_confidence(labels):
    labels = [l for l in labels if l]
    if not labels:
        return "LOW"
    return min(labels, key=lambda l: CONF_ORDER.get(l, 0))


# ===========================================================================
# WATER (calc doc §2)
# ===========================================================================

def calculate_water(data):
    g, w = data["general"], data["water"]
    hh = max(1, int(g.get("household_size") or 1))
    notes = []

    municipal_l = None
    method, confidence, tariff_label = None, None, None

    # 1-2. measured consumption (bill-extracted or manual), in kL/month
    if w.get("water_kl_month") is not None and w["water_kl_month"] > 0:
        municipal_l = float(w["water_kl_month"]) * 1000.0
        method = "measured_bill" if w.get("measured_source") == "bill" else "measured_manual"
        confidence = "HIGH"
    # 3. bill amount -> municipality-specific progressive tariff
    elif w.get("water_bill_rand"):
        kl, tariff_label = water_kl_from_bill(
            w["water_bill_rand"], g.get("municipality") or g.get("region"))
        if kl is not None:
            municipal_l = kl * 1000.0
            method = "bill_amount_tariff"
            confidence = "MEDIUM"
            notes.append(f"Water bill converted with {tariff_label} — approximate.")
        else:
            notes.append("Water bill amount given but municipality tariff is not "
                         "supported; used the national fallback instead.")

    rain_fraction = 0.0
    if w.get("uses_rainwater"):
        rain_fraction = min(0.9, max(0.0, float(w.get("rainwater_percentage") or 0) / 100.0))

    rainwater_l = 0.0
    if municipal_l is not None:
        # Measured value is municipal supply. With a stated rainwater share,
        # estimate the total: total = municipal / (1 - rain_fraction).
        if rain_fraction > 0:
            total_l = municipal_l / (1.0 - rain_fraction)
            rainwater_l = total_l - municipal_l
            notes.append("Total water approximated from municipal consumption "
                         "and stated rainwater share ([approximation]).")
        else:
            total_l = municipal_l
    elif g.get("account_type") == "business":
        # business fallback: sector water intensity × floor area (spec §5),
        # NOT the per-person household benchmark.
        from benchmarks import business_sector_benchmark
        bench = business_sector_benchmark(g.get("sector"))
        area = g.get("floor_area_m2")
        if area:
            total_l = bench["water_l_m2"] * float(area) / 12.0
            notes.append("No metered water — estimated from the sector's water "
                         "intensity × floor area ([sector benchmark, rough]).")
        elif g.get("employees"):
            total_l = 50.0 * float(g["employees"]) * 365.0 / 12.0
            notes.append("No metered water or floor area — estimated at roughly "
                         "50 L/employee/day ([assumption]).")
        else:
            total_l = 0.0
            notes.append("No water information provided for the business.")
        method = "business_sector_estimate"
        confidence = "LOW"
        rainwater_l = total_l * rain_fraction
        municipal_l = total_l - rainwater_l
    else:
        # 5. national fallback: 218 L/person/day is a TOTAL-use benchmark.
        total_l = F("water_national_l_person_day") * hh * 365.0 / 12.0
        method = "national_average"
        confidence = "LOW"
        notes.append("No measured water data — national benchmark of "
                     "218 L/person/day used (SA government figure).")
        rainwater_l = total_l * rain_fraction
        municipal_l = total_l - rainwater_l

    # business: add process / irrigation water to the premises total
    if g.get("account_type") == "business":
        b = data.get("business", {})
        add_l = 0.0
        if b.get("process_water_kl_month"):
            add_l += float(b["process_water_kl_month"]) * 1000.0
        if b.get("irrigation_kl_month"):
            add_l += float(b["irrigation_kl_month"]) * 1000.0
        if add_l:
            total_l += add_l
            municipal_l += add_l
            notes.append("Included process / irrigation water in the total.")

    # Shower estimate: separate category information, never added to the total.
    shower_l_month_pp = None
    shower_l_month_household = None
    if w.get("shower_minutes") and w.get("showers_per_week"):
        shower_l_month_pp = (float(w["shower_minutes"]) * float(w["showers_per_week"])
                             * F("shower_l_per_minute") * 52.0 / 12.0)
        shower_l_month_household = shower_l_month_pp * hh

    l_person_day = total_l * 12.0 / 365.0 / hh

    # Optional carbon proxy — reported separately, NOT in the headline footprint.
    optional_water_co2_year = (municipal_l / 1000.0) * F("water_combined_kgco2e_per_m3") * 12.0

    return {
        "total_water_litres_month": round(total_l, 1),
        "municipal_water_litres_month": round(municipal_l, 1),
        "rainwater_litres_month": round(rainwater_l, 1),
        "water_litres_person_day": round(l_person_day, 1),
        "shower_litres_month_estimated": round(shower_l_month_pp, 1) if shower_l_month_pp else None,
        "shower_litres_month_household": round(shower_l_month_household, 1) if shower_l_month_household else None,
        "rainwater_share_percent": round(rain_fraction * 100),
        "garden_irrigation": bool(w.get("garden_irrigation")),
        "pool_owned": bool(w.get("swimming_pool")),
        "calculation_method": method,
        "confidence": confidence,
        "tariff_label": tariff_label,
        "optional_water_co2e_kg_year": round(optional_water_co2_year, 1),
        "notes": notes,
    }


# ===========================================================================
# ELECTRICITY (calc doc §3-5)
# ===========================================================================

def _appliance_estimate_kwh_month(e, l):
    """Broad appliance estimate when nothing is measured (calc doc §4).
    Deliberately rough; the result is labelled LOW confidence."""
    days = F("days_per_month")
    breakdown = {"base_load": F("base_load_kwh_month")}
    if e.get("electric_geyser"):
        hours = float(e.get("geyser_hours_per_day") or 3.0)  # [MVP assumption] default
        breakdown["geyser"] = F("geyser_kw") * hours * days
    if e.get("air_conditioner"):
        kw = float(e.get("aircon_kw") or 1.5)
        hours = float(e.get("aircon_hours_per_day") or 0.0)
        months = float(e.get("aircon_months_per_year") or 0.0)
        breakdown["air_conditioner"] = kw * hours * days * months / 12.0
    if e.get("electric_stove"):
        minutes = float(e.get("stove_minutes_per_day") or 0.0)
        breakdown["stove"] = F("stove_plate_kw") * minutes / 60.0 * days
        oven_h = float(e.get("oven_hours_per_week") or 0.0)
        if oven_h:
            breakdown["oven"] = F("oven_kw") * oven_h * 52.0 / 12.0
    if e.get("pool_pump"):
        watts = float(e.get("pool_pump_watts") or 750.0)
        hours = float(e.get("pool_pump_hours_per_day") or 0.0)
        breakdown["pool_pump"] = watts / 1000.0 * hours * days
    # electric heater lives in the lifestyle section but is electricity
    if l.get("heating_method") == "Electricity" and l.get("heating_hours_per_day"):
        watts = float(l.get("heater_watts") or 2000.0)
        months = float(l.get("heating_months_per_year") or 0.0)
        breakdown["electric_heating"] = (watts / 1000.0 *
                                         float(l["heating_hours_per_day"]) *
                                         days * months / 12.0)
    return breakdown


def calculate_electricity(data):
    g, e, l = data["general"], data["electricity"], data["lifestyle"]
    notes = []
    method, confidence, tariff_label = None, None, None
    appliance_breakdown = None

    renewable_fraction = 0.0
    if e.get("renewable_source", "None") != "None":
        renewable_fraction = min(1.0, max(0.0, float(e.get("renewable_percentage") or 0) / 100.0))

    kwh, is_grid_import = None, True
    # 1-2. measured kWh
    if e.get("kwh_month") is not None and e["kwh_month"] > 0:
        kwh = float(e["kwh_month"])
        method = "measured_bill" if e.get("measured_source") == "bill" else "measured_manual"
        confidence = "HIGH"
        is_grid_import = e.get("kwh_kind", "").startswith("Grid import")
    # 3. bill amount -> tariff
    elif e.get("bill_rand"):
        est, tariff_label = electricity_kwh_from_bill(
            e["bill_rand"], g.get("municipality") or g.get("region"))
        if est is not None:
            kwh = est
            method = "bill_amount_tariff"
            confidence = "MEDIUM"
            is_grid_import = True  # a bill is always grid purchases
            notes.append(f"Electricity bill converted with {tariff_label} — approximate.")
        else:
            notes.append("Electricity spend given but the utility tariff is not "
                         "supported; used the appliance estimate instead.")
    # 4. estimate (no measured data): business uses a sector intensity, a
    # household uses the broad appliance model.
    if kwh is None and g.get("account_type") == "business":
        from benchmarks import business_sector_benchmark
        bench = business_sector_benchmark(g.get("sector"))
        area = g.get("floor_area_m2")
        if area:
            kwh = bench["kwh_m2"] * float(area) / 12.0
            notes.append("No metered electricity — estimated from the sector's "
                         "energy intensity × floor area ([sector benchmark, rough]).")
        elif g.get("employees"):
            kwh = 200.0 * float(g["employees"])
            notes.append("No metered electricity or floor area — estimated at "
                         "roughly 200 kWh/employee/month ([assumption]).")
        else:
            kwh = 0.0
            notes.append("No electricity information provided for the business.")
        method = "business_sector_estimate"
        confidence = "LOW"
        is_grid_import = False
    if kwh is None:
        appliance_breakdown = _appliance_estimate_kwh_month(e, l)
        kwh = sum(appliance_breakdown.values())
        method = "appliance_estimate"
        confidence = "LOW"
        is_grid_import = False  # represents whole-house consumption
        notes.append("No measured electricity — broad appliance estimate used "
                     "(includes a 150 kWh/month base-load assumption).")

    # Renewable split. Never subtract solar from a grid-import figure —
    # the bill already represents grid purchases (calc doc §3.1).
    if is_grid_import:
        grid_kwh = kwh
        renewable_kwh = 0.0
        total_kwh = kwh
        if renewable_fraction > 0:
            notes.append("Your kWh figure is grid import, so your renewable share "
                         "is kept as context and NOT subtracted again "
                         "(avoids double counting).")
    else:
        total_kwh = kwh
        renewable_kwh = total_kwh * renewable_fraction
        grid_kwh = total_kwh - renewable_kwh

    grid_co2_month = grid_kwh * F("sa_grid_kgco2e_per_kwh")
    electricity_co2_year = grid_co2_month * 12.0

    # --- generator (calc doc §5)
    generator_co2_year = 0.0
    generator_litres_month = None
    if e.get("backup_power") == "Generator":
        litres = e.get("generator_litres_per_month")
        if not litres and e.get("generator_hours_per_month"):
            rate = e.get("generator_fuel_rate_l_per_hour") or F("generator_l_per_hour_fallback")
            litres = float(e["generator_hours_per_month"]) * float(rate)
            notes.append(f"Generator fuel estimated from hours × {rate} L/hour "
                         "([fallback assumption] if no manufacturer rate).")
        if litres:
            generator_litres_month = float(litres)
            fuel = (e.get("generator_fuel_type") or "Petrol").lower()
            fuel_factor = {"petrol": F("petrol_kgco2e_per_l"),
                           "diesel": F("diesel_kgco2e_per_l"),
                           "lpg": F("lpg_kgco2e_per_l"),
                           "natural gas": F("natural_gas_kgco2e_per_m3")}.get(
                               fuel, F("petrol_kgco2e_per_l"))
            generator_co2_year = generator_litres_month * fuel_factor * 12.0

    # Grid-charged inverters/UPS are already inside the bill total (no extra
    # addition); solar-charged backup stays a separate renewable category.
    if e.get("backup_power") in ("Inverter and battery", "UPS") and \
            e.get("backup_charge_source") in ("Grid", "Both"):
        notes.append("Grid-charged backup is already included in your measured "
                     "electricity — nothing added (avoids double counting).")

    return {
        "total_electricity_kwh_month": round(total_kwh, 1),
        "grid_electricity_kwh_month": round(grid_kwh, 1),
        "renewable_electricity_kwh_month": round(renewable_kwh, 1),
        "renewable_share_percent": round(renewable_fraction * 100),
        "kwh_person_month": round(total_kwh / max(1, int(g.get("household_size") or 1)), 1),
        "electricity_co2e_kg_year": round(electricity_co2_year, 1),
        "backup_power_type": e.get("backup_power", "None"),
        "backup_coverage": e.get("generator_coverage"),
        "backup_charge_source": e.get("backup_charge_source"),
        "generator_litres_month": round(generator_litres_month, 1) if generator_litres_month else None,
        "generator_co2e_kg_year": round(generator_co2_year, 1),
        "appliance_breakdown_kwh_month": (
            {k: round(v, 1) for k, v in appliance_breakdown.items()}
            if appliance_breakdown else None),
        "calculation_method": method,
        "confidence": confidence,
        "tariff_label": tariff_label,
        "notes": notes,
    }


# ===========================================================================
# CARBON (calc doc §6-14)
# ===========================================================================

def calculate_vehicle(data):
    v = data["transport"]["vehicle"]
    notes = []
    if not v.get("owns_vehicle") or not v.get("annual_km"):
        return {"co2e_kg_year": 0.0, "confidence": None, "notes": notes,
                "detail": None}

    km = float(v["annual_km"])
    occupants = max(1, int(v.get("average_passengers") or 1))
    fuel, l100, kwh_km, matched = None, None, None, None

    db = lookup_vehicle(v.get("manufacturer"), v.get("model"), v.get("year"))
    if db is not None:
        matched = f"{db['make']} {db['model']}"
        fuel = db["fuel"]
        l100 = db.get("l_per_100km")
        kwh_km = db.get("kwh_per_km")
        notes.append(f"Vehicle matched to database entry: {matched} "
                     f"({fuel}, approximate combined-cycle figures).")
    # user-supplied fallback overrides missing db values
    if v.get("fuel_type"):
        fuel = v["fuel_type"]
    if v.get("l_per_100km"):
        l100 = float(v["l_per_100km"])
    if v.get("kwh_per_km"):
        kwh_km = float(v["kwh_per_km"])

    if fuel == "electric" and kwh_km:
        total = km * kwh_km * F("sa_grid_kgco2e_per_kwh")
    elif fuel in ("petrol", "diesel") and l100:
        annual_fuel_l = km * l100 / 100.0
        factor = F("petrol_kgco2e_per_l") if fuel == "petrol" else F("diesel_kgco2e_per_l")
        total = annual_fuel_l * factor
    else:
        notes.append("Vehicle owned but fuel economy unknown — vehicle emissions "
                     "could not be calculated. Add fuel type and L/100km.")
        return {"co2e_kg_year": 0.0, "confidence": "VERY LOW", "notes": notes,
                "detail": {"skipped": True}}

    personal = total / occupants
    if occupants > 1:
        notes.append(f"Vehicle emissions shared equally across {occupants} "
                     "occupants ([simplified equal-allocation]).")
    return {
        "co2e_kg_year": round(personal, 1),
        "vehicle_total_co2e_kg_year": round(total, 1),
        "confidence": "MEDIUM",
        "notes": notes,
        "detail": {"matched": matched, "fuel": fuel, "l_per_100km": l100,
                   "kwh_per_km": kwh_km, "annual_km": km, "occupants": occupants},
    }


def calculate_flights(data):
    flights = data["transport"].get("flights", [])
    notes, total, detail = [], 0.0, []
    for f in flights:
        dep, arr = f.get("departure_airport"), f.get("arrival_airport")
        dist = route_distance_km(dep, arr)
        if dist is None:
            notes.append(f"Flight {dep or '?'}→{arr or '?'} skipped — airport(s) "
                         "not recognised.")
            continue
        cabin = f.get("cabin_class", "Economy")
        domestic = same_country(dep, arr)
        if domestic:
            key = "flight_short_business" if cabin in ("Business", "First",
                                                       "Premium Economy") \
                else "flight_short_economy"
            if cabin in ("First", "Premium Economy"):
                notes.append(f"{cabin} on a domestic route uses the business-class "
                             "proxy factor.")
        else:
            key = {"Economy": "flight_intl_economy",
                   "Premium Economy": "flight_intl_premium",
                   "Business": "flight_intl_business",
                   "First": "flight_intl_first"}.get(cabin, "flight_intl_economy")
        direction = 2 if f.get("trip_type") == "Return" else 1
        trips = max(0, int(f.get("trips_per_year") or 0))
        co2 = dist * F(key) * direction * trips
        total += co2
        detail.append({"route": f"{dep}→{arr}", "km": round(dist),
                       "cabin": cabin, "trips_per_year": trips,
                       "return": direction == 2, "co2e_kg_year": round(co2, 1)})
    return {"co2e_kg_year": round(total, 1), "confidence": "MEDIUM" if detail else None,
            "notes": notes, "detail": detail}


def calculate_public_transport(data):
    p = data["transport"]["public_transport"]
    if p.get("type", "None") == "None" or not p.get("weekly_km"):
        return {"co2e_kg_year": 0.0, "confidence": None, "notes": [], "detail": None}
    key = PUBLIC_TRANSPORT_FACTOR_KEYS.get(p["type"], "pt_local_bus_kgco2e_per_pkm")
    annual_pkm = float(p["weekly_km"]) * 52.0
    co2 = annual_pkm * F(key)
    notes = ["Public-transport factors are UK passenger-km proxies; the minibus-"
             "taxi value is a temporary bus proxy."]
    return {"co2e_kg_year": round(co2, 1), "confidence": "MEDIUM", "notes": notes,
            "detail": {"mode": p["type"], "annual_passenger_km": round(annual_pkm)}}


def calculate_heating(data, electricity_measured):
    """Non-electric heating fuels only. Electric heating is part of household
    electricity (measured, or added inside the appliance estimate) — adding it
    here again would double count (calc doc §9)."""
    l = data["lifestyle"]
    hm = l.get("heating_method", "None")
    notes, co2, detail = [], 0.0, {"method": hm}
    if hm in ("None",):
        return {"co2e_kg_year": 0.0, "confidence": None, "notes": notes, "detail": detail}
    if hm in ("Electricity", "Heat pump"):
        notes.append("Electric/heat-pump heating is counted inside household "
                     "electricity — not added separately.")
        return {"co2e_kg_year": 0.0, "confidence": None, "notes": notes, "detail": detail}
    if hm == "Gas":
        if l.get("heating_lpg_litres_per_year"):
            co2 = float(l["heating_lpg_litres_per_year"]) * F("lpg_kgco2e_per_l")
            detail["lpg_litres_year"] = l["heating_lpg_litres_per_year"]
        elif l.get("heating_gas_m3_per_year"):
            co2 = float(l["heating_gas_m3_per_year"]) * F("natural_gas_kgco2e_per_m3")
            detail["gas_m3_year"] = l["heating_gas_m3_per_year"]
        else:
            notes.append("Gas heating selected but fuel quantity unknown — not "
                         "calculated. Add litres of LPG per year.")
    elif hm == "Paraffin / kerosene":
        if l.get("heating_paraffin_litres_per_year"):
            co2 = float(l["heating_paraffin_litres_per_year"]) * F("paraffin_kgco2e_per_l")
            detail["paraffin_litres_year"] = l["heating_paraffin_litres_per_year"]
        else:
            notes.append("Paraffin heating selected but litres/year unknown — not "
                         "calculated.")
    elif hm == "Coal":
        if l.get("heating_coal_kg_per_year"):
            co2 = float(l["heating_coal_kg_per_year"]) * F("coal_kgco2e_per_kg")
            detail["coal_kg_year"] = l["heating_coal_kg_per_year"]
        else:
            notes.append("Coal heating selected but kg/year unknown — not calculated.")
    elif hm == "Wood":
        notes.append("Wood heating has no defensible simple factor in this MVP — "
                     "kept as context for the AI advisor rather than a number.")
        detail["wood_kg_year"] = l.get("heating_wood_kg_per_year")
    conf = "MEDIUM" if co2 > 0 else ("VERY LOW" if hm != "Wood" else None)
    return {"co2e_kg_year": round(co2, 1), "confidence": conf, "notes": notes,
            "detail": detail}


def calculate_diet(data):
    l = data["lifestyle"]
    diet = l.get("diet", "Average diet")
    key = DIET_FACTOR_KEYS.get(diet, "diet_average_kg_day")
    base_year = F(key) * 365.0
    waste_fraction = FOOD_WASTE_FRACTIONS.get(l.get("food_waste", "None"), 0.0)
    with_waste = base_year / (1.0 - waste_fraction) if waste_fraction < 1 else base_year
    notes = ["Diet factors are UK dietary-study category proxies "
             "(2,000 kcal/day standardised)."]
    if waste_fraction:
        notes.append(f"Food waste of {int(waste_fraction*100)}% adds "
                     f"{round(with_waste - base_year)} kg CO2e/year "
                     "([simplified model]).")
    return {"co2e_kg_year": round(with_waste, 1),
            "diet_only_co2e_kg_year": round(base_year, 1),
            "food_waste_fraction": waste_fraction,
            "confidence": "MEDIUM", "notes": notes,
            "detail": {"diet": diet, "waste_fraction": waste_fraction}}


def calculate_fleet(data):
    """Business fleet emissions (spec §5 Transport & Fleet). Reuses the SAME
    fuel factors as the personal vehicle path — a litre of diesel is a litre of
    diesel — so there is no second engine, just a per-vehicle-type loop."""
    fleet = data.get("transport", {}).get("fleet", []) or []
    total, detail, notes = 0.0, [], []
    for fv in fleet:
        km = fv.get("annual_km_each")
        if not km:
            continue
        km = float(km)
        count = max(1, int(fv.get("count") or 1))
        fuel = (fv.get("fuel") or "diesel").lower()
        if fuel == "electric" and fv.get("kwh_per_km"):
            per = km * float(fv["kwh_per_km"]) * F("sa_grid_kgco2e_per_kwh")
            basis = "electric (grid)"
        elif fuel in ("petrol", "diesel") and fv.get("l_per_100km"):
            factor = F("petrol_kgco2e_per_l") if fuel == "petrol" else F("diesel_kgco2e_per_l")
            per = km * float(fv["l_per_100km"]) / 100.0 * factor
            basis = f"{fuel} at {fv['l_per_100km']:g} L/100km"
        else:
            per = km * F("fleet_default_kgco2e_per_km")
            basis = "default factor (consumption unknown)"
            notes.append(f"{fv.get('vehicle_type', 'Fleet vehicle')} used a "
                         "default emission factor — add fuel type and L/100km "
                         "for an accurate figure.")
        veh_total = per * count
        total += veh_total
        detail.append({"vehicle_type": fv.get("vehicle_type"), "count": count,
                       "annual_km_each": round(km), "fuel": fuel, "basis": basis,
                       "co2e_kg_year": round(veh_total, 1)})
    return {"co2e_kg_year": round(total, 1),
            "confidence": "MEDIUM" if detail else None,
            "notes": notes, "detail": detail}


def calculate_waste(data):
    """Business waste emissions (spec §5 Waste & Operations). Deterministic:
    general waste to landfill, less the recycled share, plus food waste where
    the sector reports it."""
    b = data.get("business", {})
    notes, detail = [], {}
    waste = b.get("waste_kg_month")
    food = b.get("food_waste_kg_month")
    if not waste and not food:
        return {"co2e_kg_year": 0.0, "confidence": None, "notes": notes,
                "detail": None}
    rec = 0.0
    if b.get("recycles"):
        rec = min(1.0, max(0.0, float(b.get("recycling_percent") or 0) / 100.0))
    total = 0.0
    if waste:
        w_year = float(waste) * 12.0
        landfill_kg = w_year * (1.0 - rec)
        recycled_kg = w_year * rec
        total += landfill_kg * F("waste_mixed_landfill_kgco2e_per_kg")
        total += recycled_kg * F("waste_recycling_kgco2e_per_kg")
        detail["general_waste_kg_year"] = round(w_year)
        detail["recycling_percent"] = round(rec * 100)
    if food:
        f_year = float(food) * 12.0
        total += f_year * F("waste_mixed_landfill_kgco2e_per_kg")
        detail["food_waste_kg_year"] = round(f_year)
        notes.append("Food waste uses the mixed-landfill factor as a proxy "
                     "([simplified] — real food-waste emissions vary).")
    return {"co2e_kg_year": round(total, 1), "confidence": "MEDIUM",
            "notes": notes, "detail": detail}


def calculate_carbon(data, electricity_result):
    g, l = data["general"], data["lifestyle"]
    hh = max(1, int(g.get("household_size") or 1))
    is_business = g.get("account_type") == "business"

    flights = calculate_flights(data)
    heating = calculate_heating(data, electricity_result["calculation_method"]
                                in ("measured_bill", "measured_manual",
                                    "bill_amount_tariff"))

    if is_business:
        return _carbon_business(data, electricity_result, flights, heating)

    vehicle = calculate_vehicle(data)
    public = calculate_public_transport(data)
    diet = calculate_diet(data)

    vehicle = calculate_vehicle(data)
    flights = calculate_flights(data)
    public = calculate_public_transport(data)
    heating = calculate_heating(data, electricity_result["calculation_method"]
                                in ("measured_bill", "measured_manual",
                                    "bill_amount_tariff"))
    diet = calculate_diet(data)

    breakdown = {
        "electricity": electricity_result["electricity_co2e_kg_year"],
        "generator": electricity_result["generator_co2e_kg_year"],
        "personal_vehicle": vehicle["co2e_kg_year"],
        "public_transport": public["co2e_kg_year"],
        "flights": flights["co2e_kg_year"],
        "heating": heating["co2e_kg_year"],
        "diet_and_food_waste": diet["co2e_kg_year"],
    }
    gross = sum(breakdown.values())

    offsets_kg = 0.0
    if l.get("buys_offsets") and l.get("offset_tonnes_per_year"):
        offsets_kg = float(l["offset_tonnes_per_year"]) * 1000.0
    net = max(gross - offsets_kg, 0.0)

    # Per-person view: household-level categories divided by household size,
    # personal categories kept whole (spec §7 normalisation).
    per_person = (breakdown["electricity"] / hh + breakdown["generator"] / hh +
                  breakdown["heating"] / hh + breakdown["personal_vehicle"] +
                  breakdown["public_transport"] + breakdown["flights"] +
                  breakdown["diet_and_food_waste"])

    confidences = [electricity_result["confidence"], vehicle["confidence"],
                   flights["confidence"], public["confidence"],
                   heating["confidence"], diet["confidence"]]
    overall_conf = _lowest_confidence(confidences)

    notes = (vehicle["notes"] + flights["notes"] + public["notes"] +
             heating["notes"] + diet["notes"])

    hh = max(1, int(g.get("household_size") or 1))
    return {
        "gross_co2e_kg_year": round(gross, 1),
        "net_co2e_kg_year": round(net, 1),
        # signed net (can go negative when offsets exceed gross) — drives the
        # net-zero / net-positive score semantics (spec §18)
        "net_signed_co2e_kg_year": round(gross - offsets_kg, 1),
        "per_person_net_co2e_kg_year": round(per_person - offsets_kg / hh, 1),
        "carbon_offsets_kg_year": round(offsets_kg, 1),
        "per_person_co2e_kg_year": round(per_person, 1),
        "breakdown": {k: round(v, 1) for k, v in breakdown.items()},
        "context": {
            "shopping_habit": l.get("shopping_habits", "Average"),
            "shopping_intensity_score": SHOPPING_INTENSITY.get(
                l.get("shopping_habits", "Average"), 1.0),
            "garden_irrigation": bool(data["water"].get("garden_irrigation")),
            "pool_owned": bool(data["water"].get("swimming_pool")),
            "home_size": data["electricity"].get("home_size"),
            "renewable_share": electricity_result["renewable_share_percent"],
            "backup_power_type": electricity_result["backup_power_type"],
            "wood_heating_kg_year": l.get("heating_wood_kg_per_year"),
            "province": g.get("region"),
            "municipality": g.get("municipality"),
        },
        "calculation_confidence": overall_conf,
        "detail": {"vehicle": vehicle.get("detail"), "flights": flights["detail"],
                   "public_transport": public["detail"],
                   "heating": heating["detail"], "diet": diet["detail"]},
        "notes": notes,
    }


def _carbon_business(data, electricity_result, flights, heating):
    """Business carbon: same electricity/generator/flights/heating pieces, but
    diet is dropped and fleet + waste are added. Per-employee is the headline
    normalisation (spec §5)."""
    g, l = data["general"], data["lifestyle"]
    fleet = calculate_fleet(data)
    waste = calculate_waste(data)

    breakdown = {
        "electricity": electricity_result["electricity_co2e_kg_year"],
        "generator": electricity_result["generator_co2e_kg_year"],
        "fleet": fleet["co2e_kg_year"],
        "flights": flights["co2e_kg_year"],
        "heating": heating["co2e_kg_year"],
        "waste": waste["co2e_kg_year"],
    }
    gross = sum(breakdown.values())

    offsets_kg = 0.0
    if l.get("buys_offsets") and l.get("offset_tonnes_per_year"):
        offsets_kg = float(l["offset_tonnes_per_year"]) * 1000.0
    net = max(gross - offsets_kg, 0.0)

    employees = g.get("employees")
    per_employee = round(gross / employees, 1) if employees else None
    per_employee_net = round((gross - offsets_kg) / employees, 1) if employees else None

    confidences = [electricity_result["confidence"], fleet["confidence"],
                   flights["confidence"], heating["confidence"], waste["confidence"]]
    overall_conf = _lowest_confidence(confidences)
    notes = fleet["notes"] + flights["notes"] + heating["notes"] + waste["notes"]

    return {
        "gross_co2e_kg_year": round(gross, 1),
        "net_co2e_kg_year": round(net, 1),
        "carbon_offsets_kg_year": round(offsets_kg, 1),
        # kept for downstream compatibility; for a business it equals the whole
        # business gross (household_size defaults to 1). per_employee is the
        # meaningful business figure.
        "per_person_co2e_kg_year": round(gross, 1),
        "net_signed_co2e_kg_year": round(gross - offsets_kg, 1),
        "per_employee_co2e_kg_year": per_employee,
        "per_employee_net_co2e_kg_year": per_employee_net,
        "breakdown": {k: round(v, 1) for k, v in breakdown.items()},
        "context": {
            "sector": g.get("sector"),
            "employees": employees,
            "floor_area_m2": g.get("floor_area_m2"),
            "premises_count": g.get("premises_count"),
            "operating_days_per_week": g.get("operating_days_per_week"),
            "operating_hours_per_day": g.get("operating_hours_per_day"),
            "renewable_share": electricity_result["renewable_share_percent"],
            "backup_power_type": electricity_result["backup_power_type"],
            "province": g.get("region"),
            "municipality": g.get("municipality"),
        },
        "calculation_confidence": overall_conf,
        "detail": {"fleet": fleet["detail"], "flights": flights["detail"],
                   "heating": heating["detail"], "waste": waste["detail"]},
        "notes": notes,
    }


# ===========================================================================
# Entry point
# ===========================================================================

def run_assessment(data):
    """Run the full deterministic assessment.

    Returns {"water": ..., "electricity": ..., "carbon": ..., "score": ...}
    following the output schemas in calc doc §15-17, plus the impact score.
    The ONE engine serves personal and business; business adds per-employee /
    per-m² normalisation and a sector-based score (spec §4-5)."""
    water = calculate_water(data)
    electricity = calculate_electricity(data)
    carbon = calculate_carbon(data, electricity)

    g = data["general"]
    from benchmarks import impact_score
    if g.get("account_type") == "business":
        employees = g.get("employees")
        area = g.get("floor_area_m2")
        annual_kwh = electricity["total_electricity_kwh_month"] * 12.0
        annual_water_l = water["total_water_litres_month"] * 12.0
        electricity["kwh_per_m2_year"] = round(annual_kwh / area, 1) if area else None
        electricity["kwh_per_employee_year"] = (
            round(annual_kwh / employees, 1) if employees else None)
        water["litres_per_m2_year"] = round(annual_water_l / area, 1) if area else None
        water["kl_per_employee_year"] = (
            round(annual_water_l / 1000.0 / employees, 2) if employees else None)
        score = impact_score(water, electricity, carbon,
                             max(1, int(g.get("household_size") or 1)),
                             account_type="business", sector=g.get("sector"),
                             employees=employees, floor_area_m2=area)
    else:
        score = impact_score(water, electricity, carbon,
                             max(1, int(g.get("household_size") or 1)))

    return {"water": water, "electricity": electricity, "carbon": carbon,
            "score": score}
