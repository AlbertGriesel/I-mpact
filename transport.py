"""Transport section: flights (airport database + auto distance), personal
vehicle (vehicle database with manual fallback) and public transport
(spec §10.1-10.3)."""

import streamlit as st

import widgets as w
from airports import airport_options, code_from_option, AIRPORTS, route_distance_km
from schema import OPTIONS, default_flight
from vehicles import lookup_vehicle, vehicle_makes

_AIRPORT_OPTIONS = ["—"] + airport_options()


def _airport_select(label, current_code, key):
    display = "—"
    if current_code and current_code in AIRPORTS:
        name, city, country, _, _ = AIRPORTS[current_code]
        display = f"{current_code} — {city}, {country} ({name})"
    choice = w.select(label, key, _AIRPORT_OPTIONS, display,
                      help="Type to search by city or code — distance is "
                           "calculated automatically from coordinates.")
    return code_from_option(choice) if choice != "—" else ""


def render(data):
    st.header("Transport")

    # ------------------------------------------------------------- flights
    st.subheader("Flights")
    st.caption("Add each recurring route once — type in the boxes to search "
               "airports by city or code; distance is computed from "
               "coordinates. Cabin class matters: a first-class seat carries "
               "up to 4× the emissions of economy on the same route.")
    # working store: rows persist while being edited, but ONLY complete
    # routes (both airports set) are saved into the assessment (§4)
    store = st.session_state.setdefault(
        "aw_flight_store", [dict(f) for f in data.get("flights", [])])
    n = w.slider_int("How many flight routes do you fly per year?",
                     "flight_count", len(store), minv=0, maxv=12)
    while len(store) < n:
        store.append(default_flight())
    while len(store) > n:
        store.pop()

    incomplete = 0
    for i, f in enumerate(store):
        with st.container(border=True):
            st.markdown(f"**Route {i + 1}**")
            c1, c2 = st.columns(2)
            with c1:
                f["departure_airport"] = _airport_select(
                    "From", f.get("departure_airport"), key=f"dep_{i}")
            with c2:
                f["arrival_airport"] = _airport_select(
                    "To", f.get("arrival_airport"), key=f"arr_{i}")
            c3, c4, c5 = st.columns(3)
            with c3:
                f["cabin_class"] = w.select(
                    "Cabin", f"cabin_{i}", OPTIONS["cabin_class"],
                    f.get("cabin_class", "Economy"))
            with c4:
                f["trip_type"] = w.radio(
                    "Trip", f"trip_{i}", OPTIONS["trip_type"],
                    f.get("trip_type", "Return"))
            with c5:
                f["trips_per_year"] = w.slider_int(
                    "Trips per year", f"tripcount_{i}",
                    f.get("trips_per_year") or 1, minv=1, maxv=52)
            complete = bool(f["departure_airport"] and f["arrival_airport"])
            if complete:
                dist = route_distance_km(f["departure_airport"],
                                         f["arrival_airport"])
                if dist:
                    st.caption(f"Great-circle distance: **{dist:,.0f} km** "
                               "each way.")
            else:
                incomplete += 1
                st.error("Both airports are required — this route is not "
                         "saved until you choose a departure AND a "
                         "destination.", icon=":material/flight:")
    # only complete flights enter the assessment
    data["flights"] = [dict(f) for f in store
                       if f["departure_airport"] and f["arrival_airport"]]
    if incomplete:
        st.warning(f"{incomplete} route(s) still missing an airport — they "
                   "won't be counted until completed.")

    # ------------------------------------------------------------- vehicle
    st.subheader("Personal vehicle")
    v = data["vehicle"]
    v["owns_vehicle"] = w.check("I drive a personal vehicle", "owns_car",
                                v.get("owns_vehicle"))
    if v["owns_vehicle"]:
        c1, c2, c3 = st.columns(3)
        makes = ["(other)"] + vehicle_makes()
        with c1:
            picked = w.select("Manufacturer", "car_make", makes,
                              v.get("manufacturer") or "(other)")
            if picked == "(other)":
                v["manufacturer"] = w.text("Manufacturer name", "car_make_txt",
                                           v.get("manufacturer"))
            else:
                v["manufacturer"] = picked
        with c2:
            v["model"] = w.text("Model", "car_model", v.get("model"),
                                placeholder="e.g. Polo Vivo, Hilux 2.4 GD-6")
        with c3:
            v["year"] = w.number_int("Model year", "car_year",
                                     v.get("year") or 2020, minv=1980, maxv=2030)
        c4, c5 = st.columns(2)
        with c4:
            km = w.number("Distance driven per year (km)", "car_km",
                          v.get("annual_km"), minv=0.0, maxv=200000.0,
                          step=500.0)
            v["annual_km"] = km if km > 0 else None
        with c5:
            v["average_passengers"] = w.slider_int(
                "Average people in the car (incl. you)", "car_pax",
                v.get("average_passengers") or 1, minv=1, maxv=8,
                help="Emissions are shared across occupants.")

        match = lookup_vehicle(v.get("manufacturer"), v.get("model"), v.get("year"))
        if match:
            spec = (f"{match.get('kwh_per_km')} kWh/km" if match["fuel"] == "electric"
                    else f"{match.get('l_per_100km')} L/100km")
            st.success(f"Matched **{match['make']} {match['model']}** — "
                       f"{match['fuel']}, ~{spec} (approximate combined cycle). "
                       "Fuel economy handled automatically.")
            v["fuel_type"], v["l_per_100km"], v["kwh_per_km"] = None, None, None
        elif v.get("model"):
            st.warning("Not in our vehicle database — two quick fallback "
                       "questions instead:")
            c6, c7 = st.columns(2)
            with c6:
                v["fuel_type"] = w.select("Fuel type", "car_fuel",
                                          OPTIONS["vehicle_fuel"],
                                          v.get("fuel_type") or "petrol")
            with c7:
                if v["fuel_type"] == "electric":
                    val = w.slider_float("Consumption (kWh/km)", "car_kwhkm",
                                         v.get("kwh_per_km") or 0.18,
                                         minv=0.05, maxv=0.5, step=0.01)
                    v["kwh_per_km"], v["l_per_100km"] = val, None
                else:
                    val = w.slider_float("Average consumption (L/100km)",
                                         "car_l100",
                                         v.get("l_per_100km") or 8.0,
                                         minv=2.0, maxv=25.0, step=0.1)
                    v["l_per_100km"], v["kwh_per_km"] = val, None
    else:
        v["annual_km"] = None
    data["vehicle"] = v

    # ----------------------------------------------------- public transport
    st.subheader("Public transport")
    p = data["public_transport"]
    p["type"] = w.select("Main type you use", "pt_type",
                         OPTIONS["public_transport"], p.get("type", "None"))
    if p["type"] != "None":
        km = w.number("Average distance per week (km)", "pt_km",
                      p.get("weekly_km"), minv=0.0, maxv=3000.0, step=5.0)
        p["weekly_km"] = km if km > 0 else None
        if p["type"] == "Minibus taxi / taxi":
            st.caption("Minibus taxis use a temporary bus-proxy factor — an "
                       "honest stand-in until better SA data lands.")
    else:
        p["weekly_km"] = None
    data["public_transport"] = p
    return data
