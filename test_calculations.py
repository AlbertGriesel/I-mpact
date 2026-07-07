"""Sanity tests for the deterministic engine (run: python test_calculations.py)."""

import copy

from schema import default_assessment, merge_updates, missing_important_fields
from calculations import run_assessment
from tariffs import water_kl_from_bill, electricity_kwh_from_bill
from airports import route_distance_km, same_country, resolve_airport
from vehicles import lookup_vehicle
from goals import pick_weekly_goals
from benchmarks import score_mood
from comparisons import water_comparison, electricity_comparison, carbon_comparison


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
