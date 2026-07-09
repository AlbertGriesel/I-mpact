"""Sanity tests for the deterministic engine (run: python test_calculations.py)."""

import copy

from schema import default_assessment, merge_updates, missing_important_fields
from calculations import run_assessment
from tariffs import water_kl_from_bill, electricity_kwh_from_bill
from airports import route_distance_km, same_country, resolve_airport
from vehicles import lookup_vehicle
from goals import (pick_weekly_goals, generate_goal_candidates,
                   rank_candidate_goals, sanitize_planner_goals)
from benchmarks import score_mood
from comparisons import water_comparison, electricity_comparison, carbon_comparison
import locations as loc


def approx(a, b, tol=0.02):
    return abs(a - b) <= tol * max(abs(a), abs(b), 1)


def test_water_measured():
    d = default_assessment()
    d["general"]["household_size"] = 4
    d["water"]["water_kl_month"] = 18.0
    d["water"]["measured_source"] = "manual"
    r = run_assessment(d)["water"]
    assert r["total_water_litres_month"] == 18000.0
    assert r["confidence"] == "HIGH"
    # 18000 * 12 / 365 / 4 = 147.9
    assert approx(r["water_litres_person_day"], 18000 * 12 / 365 / 4)


def test_water_fallback_218():
    d = default_assessment()
    d["general"]["household_size"] = 3
    r = run_assessment(d)["water"]
    expected = 218 * 3 * 365 / 12
    assert approx(r["total_water_litres_month"], expected)
    assert r["confidence"] == "LOW"
    assert approx(r["water_litres_person_day"], 218)


def test_water_shower_not_added():
    d = default_assessment()
    d["general"]["household_size"] = 2
    d["water"]["shower_minutes"] = 10
    d["water"]["showers_per_week"] = 7
    r = run_assessment(d)["water"]
    # total stays the 218 benchmark; shower is separate category info
    assert approx(r["total_water_litres_month"], 218 * 2 * 365 / 12)
    assert approx(r["shower_litres_month_estimated"], 10 * 7 * 8 * 52 / 12)


def test_water_rainwater_split_from_municipal():
    d = default_assessment()
    d["general"]["household_size"] = 1
    d["water"]["water_kl_month"] = 9.0
    d["water"]["measured_source"] = "bill"
    d["water"]["uses_rainwater"] = True
    d["water"]["rainwater_percentage"] = 25
    r = run_assessment(d)["water"]
    assert approx(r["total_water_litres_month"], 9000 / 0.75)
    assert approx(r["rainwater_litres_month"], 9000 / 0.75 - 9000)


def test_electricity_measured_grid_import_no_double_subtract():
    d = default_assessment()
    d["general"]["household_size"] = 4
    d["electricity"]["kwh_month"] = 550.0
    d["electricity"]["measured_source"] = "bill"
    d["electricity"]["kwh_kind"] = "Grid import (bill / prepaid / meter)"
    d["electricity"]["renewable_source"] = "Solar"
    d["electricity"]["renewable_percentage"] = 20
    r = run_assessment(d)["electricity"]
    # grid import must NOT be reduced by the solar share
    assert r["grid_electricity_kwh_month"] == 550.0
    assert approx(r["electricity_co2e_kg_year"], 550 * 0.906 * 12)
    assert r["confidence"] == "HIGH"


def test_electricity_whole_house_renewable_subtracted():
    d = default_assessment()
    d["electricity"]["kwh_month"] = 500.0
    d["electricity"]["measured_source"] = "manual"
    d["electricity"]["kwh_kind"] = "Whole-house total (my own estimate)"
    d["electricity"]["renewable_source"] = "Solar"
    d["electricity"]["renewable_percentage"] = 30
    r = run_assessment(d)["electricity"]
    assert approx(r["grid_electricity_kwh_month"], 350.0)
    assert approx(r["renewable_electricity_kwh_month"], 150.0)


def test_electricity_appliance_estimate():
    d = default_assessment()
    d["electricity"]["electric_geyser"] = True
    d["electricity"]["geyser_hours_per_day"] = 2
    d["electricity"]["pool_pump"] = True
    d["electricity"]["pool_pump_watts"] = 750
    d["electricity"]["pool_pump_hours_per_day"] = 6
    r = run_assessment(d)["electricity"]
    expected = 150 + 3 * 2 * 30.42 + 0.75 * 6 * 30.42
    assert approx(r["total_electricity_kwh_month"], expected)
    assert r["confidence"] == "LOW"
    assert r["appliance_breakdown_kwh_month"] is not None


def test_generator():
    d = default_assessment()
    d["electricity"]["kwh_month"] = 400.0
    d["electricity"]["measured_source"] = "manual"
    d["electricity"]["backup_power"] = "Generator"
    d["electricity"]["generator_fuel_type"] = "Diesel"
    d["electricity"]["generator_litres_per_month"] = 20.0
    r = run_assessment(d)["electricity"]
    assert approx(r["generator_co2e_kg_year"], 20 * 2.66155 * 12)
    # hours fallback
    d["electricity"]["generator_litres_per_month"] = None
    d["electricity"]["generator_hours_per_month"] = 10.0
    r2 = run_assessment(d)["electricity"]
    assert approx(r2["generator_co2e_kg_year"], 10 * 1.5 * 2.66155 * 12)


def test_vehicle_db_and_occupants():
    d = default_assessment()
    d["transport"]["vehicle"].update({
        "owns_vehicle": True, "manufacturer": "Volkswagen",
        "model": "Polo Vivo", "annual_km": 15000, "average_passengers": 2})
    r = run_assessment(d)["carbon"]
    total = 15000 * 5.7 / 100 * 2.35372
    assert approx(r["breakdown"]["personal_vehicle"], total / 2)


def test_vehicle_manual_fallback():
    d = default_assessment()
    d["transport"]["vehicle"].update({
        "owns_vehicle": True, "manufacturer": "Tazz", "model": "Unknown 1.3",
        "annual_km": 10000, "average_passengers": 1,
        "fuel_type": "petrol", "l_per_100km": 7.2})
    r = run_assessment(d)["carbon"]
    assert approx(r["breakdown"]["personal_vehicle"], 10000 * 7.2 / 100 * 2.35372)


def test_flights_domestic_vs_international():
    d = default_assessment()
    d["transport"]["flights"] = [
        {"departure_airport": "CPT", "arrival_airport": "JNB",
         "cabin_class": "Economy", "trip_type": "Return", "trips_per_year": 2},
        {"departure_airport": "JNB", "arrival_airport": "LHR",
         "cabin_class": "Business", "trip_type": "Return", "trips_per_year": 1},
    ]
    r = run_assessment(d)["carbon"]
    dist_dom = route_distance_km("CPT", "JNB")
    dist_int = route_distance_km("JNB", "LHR")
    assert 1200 < dist_dom < 1350          # ~1270 km
    assert 8500 < dist_int < 9500          # ~9000 km
    expected = dist_dom * 0.12576 * 2 * 2 + dist_int * 0.31656 * 2 * 1
    assert approx(r["breakdown"]["flights"], expected)
    assert same_country("CPT", "JNB") and not same_country("JNB", "LHR")


def test_public_transport():
    d = default_assessment()
    d["transport"]["public_transport"] = {"type": "Minibus taxi / taxi",
                                          "weekly_km": 100.0}
    r = run_assessment(d)["carbon"]
    assert approx(r["breakdown"]["public_transport"], 100 * 52 * 0.12552)


def test_diet_and_waste():
    d = default_assessment()
    d["lifestyle"]["diet"] = "Vegetarian"
    d["lifestyle"]["food_waste"] = "Around 20%"
    r = run_assessment(d)["carbon"]
    base = 3.81 * 365
    assert approx(r["breakdown"]["diet_and_food_waste"], base / 0.8)


def test_offsets_and_net():
    d = default_assessment()
    d["lifestyle"]["buys_offsets"] = True
    d["lifestyle"]["offset_tonnes_per_year"] = 100.0  # absurdly high
    r = run_assessment(d)["carbon"]
    assert r["net_co2e_kg_year"] == 0.0            # floor at zero
    assert r["gross_co2e_kg_year"] > 0             # gross still visible
    assert r["carbon_offsets_kg_year"] == 100000.0


def test_heating_fuels():
    d = default_assessment()
    d["lifestyle"]["heating_method"] = "Paraffin / kerosene"
    d["lifestyle"]["heating_paraffin_litres_per_year"] = 60
    r = run_assessment(d)["carbon"]
    assert approx(r["breakdown"]["heating"], 60 * 2.54016)
    # electric heating never double counts
    d2 = default_assessment()
    d2["electricity"]["kwh_month"] = 500
    d2["electricity"]["measured_source"] = "bill"
    d2["lifestyle"]["heating_method"] = "Electricity"
    d2["lifestyle"]["heating_hours_per_day"] = 5
    r2 = run_assessment(d2)["carbon"]
    assert r2["breakdown"]["heating"] == 0.0


def test_electric_heater_in_appliance_estimate():
    d = default_assessment()
    d["lifestyle"]["heating_method"] = "Electricity"
    d["lifestyle"]["heater_watts"] = 2000
    d["lifestyle"]["heating_hours_per_day"] = 4
    d["lifestyle"]["heating_months_per_year"] = 3
    r = run_assessment(d)["electricity"]
    assert "electric_heating" in r["appliance_breakdown_kwh_month"]
    assert approx(r["appliance_breakdown_kwh_month"]["electric_heating"],
                  2.0 * 4 * 30.42 * 3 / 12)


def test_tariff_reverse():
    kl, label = water_kl_from_bill(500, "City of Cape Town")
    assert kl is not None and 5 < kl < 20 and "Cape Town" in label
    kwh, label2 = electricity_kwh_from_bill(1000, "Johannesburg City Power")
    assert kwh is not None and 200 < kwh < 500
    none_kl, _ = water_kl_from_bill(500, "Some Rural Municipality")
    assert none_kl is None


def test_bill_amount_flow():
    d = default_assessment()
    d["general"]["municipality"] = "Cape Town"
    d["water"]["water_bill_rand"] = 400.0
    r = run_assessment(d)["water"]
    assert r["calculation_method"] == "bill_amount_tariff"
    assert r["confidence"] == "MEDIUM"


def test_merge_updates_validation():
    d = default_assessment()
    merged, applied, rejected = merge_updates(d, {
        "water": {"water_kl_month": 12, "rainwater_percentage": 150},
        "electricity": {"backup_power": "Generator"},
        "bogus": {"x": 1},
        "transport": {"flights": [{"departure_airport": "cpt",
                                   "arrival_airport": "JNB",
                                   "cabin_class": "economy",
                                   "trip_type": "return",
                                   "trips_per_year": 3}]},
    })
    assert merged["water"]["water_kl_month"] == 12
    assert merged["water"]["rainwater_percentage"] == 0        # rejected
    assert any("rainwater" in x for x in rejected)
    assert any("unknown section" in x for x in rejected)
    assert merged["electricity"]["backup_power"] == "Generator"
    f = merged["transport"]["flights"][0]
    assert f["departure_airport"] == "CPT" and f["cabin_class"] == "Economy"


def test_missing_fields_conditional():
    d = default_assessment()
    gaps = [p for p, _ in missing_important_fields(d)]
    assert "water.water_kl_month" in gaps
    d["water"]["water_kl_month"] = 10.0
    gaps2 = [p for p, _ in missing_important_fields(d)]
    # measured water removes the estimation questions
    assert "water.shower_minutes" not in gaps2


def test_goals_and_score_and_comparisons():
    d = default_assessment()
    d["general"]["household_size"] = 4
    d["water"]["water_kl_month"] = 30.0
    d["water"]["shower_minutes"] = 15
    d["water"]["showers_per_week"] = 7
    d["electricity"]["kwh_month"] = 700.0
    d["electricity"]["electric_geyser"] = True
    d["transport"]["vehicle"].update({"owns_vehicle": True,
                                      "manufacturer": "Toyota",
                                      "model": "Hilux 2.4 GD-6",
                                      "annual_km": 20000})
    results = run_assessment(d)
    score = results["score"]
    assert 0 <= score["total"] <= 100
    assert score_mood(score["total"]) in ("good", "ok", "poor")
    picked = pick_weekly_goals(d, results, 3)
    assert 1 <= len(picked) <= 3
    assert all(g["title"] for g in picked)
    assert water_comparison(results["water"]["total_water_litres_month"], "month")
    assert electricity_comparison(700, "month")
    assert carbon_comparison(results["carbon"]["net_co2e_kg_year"], "year")


def test_airport_resolver():
    assert resolve_airport("Cape Town") == "CPT"
    assert resolve_airport("jnb") == "JNB"
    assert resolve_airport("Heathrow") == "LHR"
    assert resolve_airport("Nowhereville") is None


def test_vehicle_lookup():
    assert lookup_vehicle("Toyota", "Hilux 2.4 GD-6")["fuel"] == "diesel"
    assert lookup_vehicle("volkswagen", "polo vivo")["l_per_100km"] == 5.7
    assert lookup_vehicle("BYD", "Atto 3")["fuel"] == "electric"
    assert lookup_vehicle("Fiat", "Uno 1990") is None


def test_business_default_and_gate():
    from schema import is_calculable, business_sector_flags
    b = default_assessment("business")
    assert b["general"]["account_type"] == "business"
    assert "business" in b and "fleet" in b["transport"]
    assert is_calculable(b) is False           # needs sector + size
    b["general"].update({"sector": "Office / professional services",
                         "employees": 10, "floor_area_m2": 300})
    assert is_calculable(b) is True
    flags = business_sector_flags("Restaurant / café / hospitality")
    assert flags["refrigeration"] and flags["food_waste"] and flags["process_water"]
    assert business_sector_flags("Office / professional services")["food_waste"] is False


def test_business_engine_reuses_factors():
    b = default_assessment("business")
    b["general"].update({"sector": "Manufacturing / industrial",
                         "employees": 25, "floor_area_m2": 1000})
    b, applied, rejected = merge_updates(b, {
        "electricity": {"kwh_month": 8000, "measured_source": "bill"},
        "water": {"water_kl_month": 120, "measured_source": "bill"},
        "transport": {"fleet": [
            {"vehicle_type": "Truck / heavy", "fuel": "diesel", "count": 3,
             "annual_km_each": 40000, "l_per_100km": 28}]},
        "business": {"waste_kg_month": 1000, "recycles": True,
                     "recycling_percent": 50, "process_water_kl_month": 40},
    })
    assert not rejected, rejected
    r = run_assessment(b)
    c, e, w = r["carbon"], r["electricity"], r["water"]
    # diet excluded, fleet + waste included
    assert "diet_and_food_waste" not in c["breakdown"]
    assert c["breakdown"]["fleet"] > 0 and c["breakdown"]["waste"] > 0
    # electricity CO2e uses the SAME grid factor as personal (0.906)
    assert approx(e["electricity_co2e_kg_year"], 8000 * 0.906 * 12)
    # process water added to the 120 kL total -> 160 kL/month
    assert approx(w["total_water_litres_month"], 160000)
    # normalisation present
    assert e["kwh_per_m2_year"] is not None and c["per_employee_co2e_kg_year"] is not None
    # the scale is open above 100 (net positive); this fixture has no offsets
    assert 0 <= r["score"]["total"] <= 100


def test_business_no_meter_uses_sector_estimate():
    b = default_assessment("business")
    b["general"].update({"sector": "Office / professional services",
                         "employees": 20, "floor_area_m2": 500})
    r = run_assessment(b)
    assert r["electricity"]["calculation_method"] == "business_sector_estimate"
    assert r["water"]["calculation_method"] == "business_sector_estimate"
    # 200 kWh/m2/yr * 500 / 12 = 8333.3 kWh/month
    assert approx(r["electricity"]["total_electricity_kwh_month"], 200 * 500 / 12)


# --------------------------------------------------------------------------
# Location validation — the shared canonical layer that the manual picker AND
# the AI/chat path (schema.merge_updates) now both run through.
# --------------------------------------------------------------------------

def test_location_valid_sa_province_municipality():
    c, r, m = loc.resolve_location("south africa", "western cape",
                                   "City of Cape Town (metro)")
    assert c == "South Africa"
    assert r == "Western Cape"
    assert m == "City of Cape Town (metro)"


def test_location_invalid_province_for_sa():
    assert loc.canonical_region("South Africa", "Bavaria") is None
    c, r, m = loc.resolve_location("South Africa", "Bavaria", "Somewhere")
    assert c == "South Africa" and r == "" and m == ""


def test_location_country_alias():
    assert loc.canonical_country("USA") == "United States"
    assert loc.canonical_country("uk") == "United Kingdom"
    assert loc.canonical_country("Narnia") is None


def test_location_regions_from_iso_dataset():
    # France's first-level regions now come from the comprehensive ISO 3166-2
    # dataset (pycountry), so the region validates; we hold no municipality data
    # for France, so that level stays empty rather than invented.
    assert loc.canonical_country("France") == "France"
    assert loc.has_regions("France") is True
    c, r, m = loc.resolve_location("France", "Ile-de-France", "Paris")
    assert c == "France"
    assert r == "Île-de-France"          # tolerant match, canonical accent
    assert m == ""                        # no municipality data invented


def test_location_iso_rejects_junk_region():
    # A non-existent region for a real country resolves to empty, never guessed.
    assert loc.canonical_region("Nigeria", "Atlantis") is None
    assert loc.canonical_region("Nigeria", "Lagos") == "Lagos"


def test_chat_rejects_arbitrary_municipality():
    d = default_assessment()
    d["general"]["country"] = "South Africa"
    d["general"]["region"] = "Western Cape"
    merged, applied, rejected = merge_updates(
        d, {"general": {"municipality": "Atlantis Free State Utopia"}})
    assert merged["general"]["municipality"] == ""
    assert any("municipality" in r for r in rejected)


def test_chat_maps_country_and_rejects_bad_region():
    d = default_assessment()
    # a valid country given informally is canonicalised; bogus province rejected
    merged, applied, rejected = merge_updates(
        d, {"general": {"country": "south africa", "region": "Nowhere"}})
    assert merged["general"]["country"] == "South Africa"
    assert merged["general"]["region"] == ""
    assert any("region" in r for r in rejected)
    # a real city name maps to the canonical municipality
    merged2, _, _ = merge_updates(
        merged, {"general": {"region": "Gauteng",
                             "municipality": "Johannesburg"}})
    assert merged2["general"]["region"] == "Gauteng"
    assert merged2["general"]["municipality"] == "City of Johannesburg (metro)"


def test_location_region_cleared_when_country_changes():
    d = default_assessment()
    d["general"].update({"country": "South Africa", "region": "Gauteng",
                         "municipality": "City of Tshwane (metro)"})
    # user now says they're in the United States — old province/muni must clear
    merged, applied, rejected = merge_updates(
        d, {"general": {"country": "United States"}})
    assert merged["general"]["country"] == "United States"
    assert merged["general"]["region"] == ""
    assert merged["general"]["municipality"] == ""


def test_location_municipality_cleared_when_region_changes():
    d = default_assessment()
    d["general"].update({"country": "South Africa", "region": "Western Cape",
                         "municipality": "City of Cape Town (metro)"})
    # switch province; the municipality from the old province must clear
    merged, _, _ = merge_updates(
        d, {"general": {"region": "KwaZulu-Natal"}})
    assert merged["general"]["region"] == "KwaZulu-Natal"
    assert merged["general"]["municipality"] == ""


def test_location_tariff_receives_canonical_name():
    # the canonical municipality name still resolves through the tariff matcher
    kl, label = water_kl_from_bill(500.0, "City of Cape Town (metro)")
    assert kl is not None and label is not None


# --------------------------------------------------------------------------
# Business goal ranking — must use sector intensities/benchmarks, NOT the
# household per-person / per-household benchmarks (audit fix).
# --------------------------------------------------------------------------

def _biz(sector, **general):
    b = default_assessment("business")
    b["general"]["sector"] = sector
    b["general"].update(general)
    return b


def test_business_office_electricity_relevance():
    b = _biz("Office / professional services", employees=20, floor_area_m2=500)
    b["electricity"]["kwh_month"] = 8000
    b["electricity"]["measured_source"] = "manual"
    r = run_assessment(b)
    ranked = rank_candidate_goals(b, r)
    elec = [g for g in ranked if g["metric"] == "electricity"]
    # business electricity goals get a real relevance (5), not the old default 3
    assert elec and any(g["relevance"] == 5 for g in elec)
    # an office is not a refrigeration/food-waste sector -> no such goals
    addrs = {g.get("addresses") for g in ranked}
    assert "refrigeration" not in addrs and "food_waste" not in addrs
    # reasons use business phrasing, never the household "diet"/"shower" wording
    assert all("shower" not in g["reason"] and "diet" not in g["reason"]
               for g in ranked)


def test_business_restaurant_categories():
    b = _biz("Restaurant / café / hospitality", employees=15, floor_area_m2=300)
    b["electricity"]["kwh_month"] = 12000
    b["electricity"]["measured_source"] = "manual"
    b["business"]["refrigeration"] = True
    b["business"]["food_waste_kg_month"] = 400
    b["business"]["waste_kg_month"] = 800
    r = run_assessment(b)
    ranked = rank_candidate_goals(b, r)
    by_addr = {g.get("addresses"): g for g in ranked}
    assert "refrigeration" in by_addr and "food_waste" in by_addr
    # both are material for a restaurant -> top relevance
    assert by_addr["refrigeration"]["relevance"] == 5
    assert by_addr["food_waste"]["relevance"] == 5


def test_business_water_intensive_prominence():
    b = _biz("Agriculture / farming", employees=10, floor_area_m2=1000)
    b["water"]["water_kl_month"] = 900          # very high per-m² intensity
    b["water"]["measured_source"] = "manual"
    b["business"]["process_water_kl_month"] = 500
    r = run_assessment(b)
    ranked = rank_candidate_goals(b, r)
    water_goals = [g for g in ranked if g["metric"] == "water"]
    # high water intensity vs the sector benchmark -> high impact/prominence
    assert water_goals and max(g["impact"] for g in water_goals) >= 4


def test_business_fleet_heavy_relevance():
    b = _biz("Warehouse / logistics", employees=30, floor_area_m2=2000)
    b["electricity"]["kwh_month"] = 5000
    b["electricity"]["measured_source"] = "manual"
    b["transport"]["fleet"] = [{
        "vehicle_type": "Truck", "fuel": "diesel", "count": 10,
        "annual_km_each": 60000, "l_per_100km": 30, "kwh_per_km": None}]
    r = run_assessment(b)
    ranked = rank_candidate_goals(b, r)
    fleet = [g for g in ranked if g.get("addresses") == "fleet"]
    # fleet dominates this business's carbon -> strong relevance
    assert fleet and fleet[0]["relevance"] >= 4


def test_personal_ranking_regression():
    d = default_assessment()
    d["general"]["household_size"] = 3
    d["electricity"]["electric_geyser"] = True
    d["water"]["shower_minutes"] = 12
    d["water"]["showers_per_week"] = 7
    r = run_assessment(d)
    ranked = rank_candidate_goals(d, r)
    geyser = [g for g in ranked if g.get("addresses") == "geyser"]
    # personal geyser relevance is unchanged by the business work
    assert geyser and geyser[0]["relevance"] == 5


# --------------------------------------------------------------------------
# Planner trust boundary — AI may propose actions but never persist an
# unvalidated numerical saving (audit fix).
# --------------------------------------------------------------------------

def _geyser_user():
    d = default_assessment()
    d["general"]["household_size"] = 3
    d["electricity"]["electric_geyser"] = True
    d["water"]["shower_minutes"] = 12
    d["water"]["showers_per_week"] = 7
    return d, run_assessment(d)


def test_planner_grounded_supported_goal():
    d, r = _geyser_user()
    cand = next(c for c in generate_goal_candidates(d, r)
                if c.get("addresses") == "geyser")
    out = sanitize_planner_goals(
        [{"title": "Reduce geyser heating time each day",
          "metric": "electricity"}], d, r)
    assert len(out) == 1 and out[0]["source"] == "planner_verified"
    # the saving comes from the deterministic candidate, not the LLM
    assert out[0]["expected_saving"] == cand["expected_saving"]
    assert out[0]["expected_saving_unit"] == cand["expected_saving_unit"]


def test_planner_unsupported_qualitative():
    d, r = _geyser_user()
    out = sanitize_planner_goals(
        [{"title": "Encourage the family to carpool", "metric": "carbon"}], d, r)
    assert len(out) == 1 and out[0]["source"] == "planner_qualitative"
    assert out[0]["expected_saving"] is None


def test_planner_discards_invented_saving():
    d, r = _geyser_user()
    out = sanitize_planner_goals(
        [{"title": "Plant an indigenous garden", "metric": "water",
          "expected_saving": 420, "expected_saving_unit": "L/week"}], d, r)
    assert out[0]["source"] == "planner_qualitative"
    assert out[0]["expected_saving"] is None


def test_planner_wrong_unit_overridden():
    d, r = _geyser_user()
    cand = next(c for c in generate_goal_candidates(d, r)
                if c.get("addresses") == "geyser")
    out = sanitize_planner_goals(
        [{"title": "Reduce geyser heating time", "metric": "electricity",
          "expected_saving": 5, "expected_saving_unit": "kg CO2e/week"}], d, r)
    # a matched goal takes the app's verified unit + value, not the LLM's
    assert out[0]["expected_saving_unit"] == cand["expected_saving_unit"]
    assert out[0]["expected_saving"] == cand["expected_saving"]


def test_planner_malformed_number_safe():
    d, r = _geyser_user()
    out = sanitize_planner_goals(
        [{"title": "Meditate on sustainability", "metric": "carbon",
          "expected_saving": "loads", "expected_saving_unit": 999}], d, r)
    assert out[0]["expected_saving"] is None
    assert out[0]["source"] == "planner_qualitative"


# --------------------------------------------------------------------------
# Score semantics (§18): 50 ≈ average, 100 = net zero, >100 only for genuine
# net-positive contribution — never for merely-better-than-average behaviour.
# --------------------------------------------------------------------------

def test_score_above_100_requires_net_positive():
    from visuals import env_tier, score_label
    # an extremely light household WITHOUT offsets must stay below 100
    d = default_assessment()
    d["general"]["household_size"] = 2
    d["water"].update({"water_kl_month": 2.0, "measured_source": "manual"})
    d["electricity"].update({"kwh_month": 40, "measured_source": "manual"})
    d["lifestyle"]["diet"] = "Vegan"
    r = run_assessment(d)
    assert r["score"]["total"] < 100
    # the same household buying offsets beyond its emissions goes net positive
    d2 = {**d}
    d2 = default_assessment()
    d2["general"]["household_size"] = 2
    d2["water"].update({"water_kl_month": 2.0, "measured_source": "manual"})
    d2["electricity"].update({"kwh_month": 40, "measured_source": "manual"})
    d2["lifestyle"].update({"diet": "Vegan", "buys_offsets": True,
                            "offset_tonnes_per_year": 15.0})
    r2 = run_assessment(d2)
    assert r2["score"]["carbon"] > 100
    assert r2["score"]["total"] > r["score"]["total"]
    # tier + label agree with the semantics
    assert env_tier(100) == "NET_ZERO" and env_tier(105) == "NET_POSITIVE"
    assert env_tier(99) == "EXCELLENT" and env_tier(50) == "AVERAGE"
    assert score_label(101) == "Net positive"
    assert score_label(100) == "Net zero impact"


def main():
    tests = [v for k, v in sorted(globals().items()) if k.startswith("test_")]
    failed = 0
    for t in tests:
        try:
            t()
            print(f"PASS {t.__name__}")
        except AssertionError as exc:
            failed += 1
            print(f"FAIL {t.__name__}: {exc}")
        except Exception as exc:  # noqa: BLE001
            failed += 1
            print(f"ERROR {t.__name__}: {type(exc).__name__}: {exc}")
    print(f"\n{len(tests) - failed}/{len(tests)} passed")
    raise SystemExit(1 if failed else 0)


if __name__ == "__main__":
    main()
