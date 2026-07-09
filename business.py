"""Business assessment (spec §4-5).

This is NOT a second assessment engine — it feeds the exact same schema and
`calculations.run_assessment` as the personal flow. It only renders the
business-shaped questions, conditioned by sector via
`schema.business_sector_flags` so a restaurant is asked about refrigeration and
food waste while an office is not. Water/electricity reuse the personal
bill-or-manual components; flights reuse the shared flights editor.
"""

import streamlit as st

import widgets as w
import water as water_mod
import electricity as elec_mod
import transport as transport_mod
from schema import OPTIONS, business_sector_flags, default_fleet_vehicle
from views.common import location_picker

# Business wizard steps (mirrors the personal STEPS shape used by assessment.py)
STEPS = ["Business", "Water", "Electricity", "Fleet & travel", "Operations",
         "Review"]

# review hub sections: (title, icon, wizard step, updates-monthly)
SECTIONS = [
    ("Business profile", "users", 0, False),
    ("Water", "water", 1, True),
    ("Electricity", "bolt", 2, True),
    ("Backup power", "battery", 2, False),
    ("Fleet & travel", "car", 3, True),
    ("Waste & operations", "leaf", 4, True),
]


# --------------------------------------------------------------------------
# Step 0 — business profile + location
# --------------------------------------------------------------------------

def render_general(data):
    g = data["general"]
    st.header("About the business")
    st.caption("A little context lets us compare you fairly to similar "
               "businesses and ask only the questions that apply to your sector.")
    c1, c2 = st.columns(2)
    with c1:
        g["business_name"] = w.text("Business name (optional)", "biz_name",
                                    g.get("business_name"))
        g["sector"] = w.select(
            "Sector / industry", "biz_sector", OPTIONS["business_sector"],
            g.get("sector") or OPTIONS["business_sector"][0],
            help="Determines which questions apply and which sector benchmark "
                 "we compare you against.")
        emp = w.number_int("Number of employees / staff", "biz_emp",
                           g.get("employees") or 1, minv=1, maxv=1_000_000)
        g["employees"] = emp
    with c2:
        g["premises_count"] = w.number_int(
            "Number of premises / sites", "biz_prem",
            g.get("premises_count") or 1, minv=1, maxv=10_000)
        area = w.number("Approx. total floor area (m²) — a rough figure is fine",
                        "biz_area", g.get("floor_area_m2"), minv=0.0,
                        maxv=5_000_000.0, step=10.0,
                        help="Used for per-m² intensity vs the sector benchmark.")
        g["floor_area_m2"] = area if area > 0 else None
    c3, c4 = st.columns(2)
    with c3:
        g["operating_days_per_week"] = w.slider_int(
            "Operating days per week", "biz_days",
            g.get("operating_days_per_week") or 5, minv=1, maxv=7)
    with c4:
        g["operating_hours_per_day"] = w.slider_int(
            "Typical operating hours per day", "biz_hours",
            g.get("operating_hours_per_day") or 9, minv=1, maxv=24)

    st.subheader("Location")
    location_picker(g, key_prefix="bizloc")
    data["general"] = g
    return data


# --------------------------------------------------------------------------
# Step 1 — water
# --------------------------------------------------------------------------

def render_water(data):
    ws, g, b = data["water"], data["general"], data["business"]
    flags = business_sector_flags(g.get("sector"))
    st.header("Water")
    st.caption("A water bill or meter reading gives the most accurate result. "
               "If you don't have one, we estimate from your sector and floor "
               "area (clearly labelled).")

    default_mode = (water_mod._MANUAL
                    if (ws.get("measured_source") == "manual"
                        or (ws.get("water_bill_rand") and not ws.get("bill_uploaded")))
                    else water_mod._UPLOAD)
    mode = w.radio("How would you like to add your water usage?", "water_mode",
                   [water_mod._UPLOAD, water_mod._MANUAL], default_mode)
    ws = water_mod._upload_path(ws) if mode == water_mod._UPLOAD \
        else water_mod._manual_path(ws)

    if flags["process_water"]:
        st.subheader("Process / production water")
        proc = w.number(
            "Water used for production or processing per month (kL) — 0 if none",
            "biz_procw", b.get("process_water_kl_month"), minv=0.0,
            maxv=5_000_000.0, step=1.0,
            help="Counted on top of general premises water.")
        b["process_water_kl_month"] = proc if proc > 0 else None

    if flags["irrigation"]:
        st.subheader("Irrigation / landscaping")
        b["irrigation"] = w.check("We irrigate grounds / crops", "biz_irr",
                                  b.get("irrigation"))
        if b["irrigation"]:
            irr = w.number("Irrigation water per month (kL)", "biz_irrkl",
                           b.get("irrigation_kl_month"), minv=0.0,
                           maxv=5_000_000.0, step=1.0)
            b["irrigation_kl_month"] = irr if irr > 0 else None

    st.subheader("Rainwater & recycling")
    c1, c2 = st.columns(2)
    with c1:
        ws["uses_rainwater"] = w.check("We harvest rainwater", "biz_rain",
                                       ws.get("uses_rainwater"))
        if ws["uses_rainwater"]:
            ws["rainwater_percentage"] = w.slider_int(
                "% of water from rainwater", "biz_rainpct",
                ws.get("rainwater_percentage"), minv=0, maxv=90)
        else:
            ws["rainwater_percentage"] = 0
    with c2:
        b["recycled_water_percent"] = w.slider_int(
            "% of water recycled / reused", "biz_recw",
            b.get("recycled_water_percent") or 0, minv=0, maxv=100,
            help="Context for the advisor — how much water you reuse on site.")

    data["water"], data["business"] = ws, b
    return data


# --------------------------------------------------------------------------
# Step 2 — electricity
# --------------------------------------------------------------------------

def render_electricity(data):
    es, g, b = data["electricity"], data["general"], data["business"]
    flags = business_sector_flags(g.get("sector"))
    st.header("Electricity")
    st.caption("A bill or meter reading is best. Without one, we estimate from "
               "your sector's energy intensity and floor area (clearly labelled).")

    default_mode = (elec_mod._MANUAL
                    if (es.get("measured_source") == "manual"
                        or (es.get("bill_rand") and not es.get("bill_uploaded")))
                    else elec_mod._UPLOAD)
    mode = w.radio("How would you like to add your electricity usage?",
                   "elec_mode", [elec_mod._UPLOAD, elec_mod._MANUAL], default_mode)
    es = elec_mod._upload_path(es) if mode == elec_mod._UPLOAD \
        else elec_mod._manual_path(es)

    es = elec_mod.renewable_and_backup(
        es, renewable_label="Does the business generate renewable electricity "
                            "(e.g. rooftop solar)?")

    # sector-conditional context (guides advice; not double-counted against a
    # metered total)
    extras = []
    if flags["refrigeration"]:
        extras.append(("refrigeration", "Significant refrigeration / cold storage"))
    if flags["machinery"]:
        extras.append(("has_machinery", "Heavy machinery / equipment"))
    if flags["servers"]:
        extras.append(("server_load", "Server room / significant IT load"))
    if extras:
        st.subheader("Major loads (helps us tailor advice)")
        cols = st.columns(len(extras))
        for col, (field, label) in zip(cols, extras):
            with col:
                b[field] = w.check(label, f"biz_{field}", b.get(field))

    data["electricity"], data["business"] = es, b
    return data


# --------------------------------------------------------------------------
# Step 3 — fleet & business travel
# --------------------------------------------------------------------------

def _fleet_editor(data):
    st.subheader("Company vehicles / fleet")
    flags = business_sector_flags(data["general"].get("sector"))
    st.caption("Add each vehicle type once. Emissions use the same fuel factors "
               "as everywhere else in the app." +
               (" Fleet tends to be a big share for your sector, so it's worth "
                "getting roughly right." if flags["fleet_prominent"] else ""))
    t = data["transport"]
    store = st.session_state.setdefault(
        "aw_fleet_store", [dict(f) for f in t.get("fleet", [])])
    n = w.slider_int("How many distinct vehicle types are in the fleet?",
                     "fleet_count", len(store), minv=0, maxv=15)
    while len(store) < n:
        store.append(default_fleet_vehicle())
    while len(store) > n:
        store.pop()

    for i, fv in enumerate(store):
        with st.container(border=True):
            st.markdown(f"**Vehicle type {i + 1}**")
            c1, c2, c3 = st.columns(3)
            with c1:
                fv["vehicle_type"] = w.select(
                    "Type", f"fleet_vt_{i}", OPTIONS["fleet_vehicle_type"],
                    fv.get("vehicle_type", "Car / bakkie"))
            with c2:
                fv["fuel"] = w.select("Fuel", f"fleet_fuel_{i}",
                                      OPTIONS["fleet_fuel"], fv.get("fuel", "diesel"))
            with c3:
                fv["count"] = w.number_int("How many", f"fleet_n_{i}",
                                           fv.get("count") or 1, minv=1, maxv=100_000)
            c4, c5 = st.columns(2)
            with c4:
                km = w.number("Km per year (each)", f"fleet_km_{i}",
                              fv.get("annual_km_each"), minv=0.0, maxv=1_000_000.0,
                              step=500.0)
                fv["annual_km_each"] = km if km > 0 else None
            with c5:
                if fv["fuel"] == "electric":
                    val = w.slider_float("Consumption (kWh/km)", f"fleet_kwh_{i}",
                                         fv.get("kwh_per_km") or 0.25, minv=0.05,
                                         maxv=1.5, step=0.01)
                    fv["kwh_per_km"], fv["l_per_100km"] = val, None
                else:
                    val = w.slider_float("Consumption (L/100km)", f"fleet_l_{i}",
                                         fv.get("l_per_100km") or 10.0, minv=2.0,
                                         maxv=60.0, step=0.5)
                    fv["l_per_100km"], fv["kwh_per_km"] = val, None
            if not fv["annual_km_each"]:
                st.caption("Add km/year for this type or it won't be counted.")
    t["fleet"] = [dict(f) for f in store if f.get("annual_km_each")]
    data["transport"] = t
    return data


def render_transport(data):
    st.header("Fleet & business travel")
    data = _fleet_editor(data)
    data["transport"] = transport_mod.flights_editor(
        data["transport"],
        caption="Add recurring business flights — search airports by city or "
                "code; distance is computed automatically.")
    return data


# --------------------------------------------------------------------------
# Step 4 — waste & operations
# --------------------------------------------------------------------------

def render_operations(data):
    b, l = data["business"], data["lifestyle"]
    flags = business_sector_flags(data["general"].get("sector"))
    st.header("Waste & operations")
    st.caption("Optional but useful — waste is often an easy win.")

    c1, c2 = st.columns(2)
    with c1:
        waste = w.number("General waste per month (kg) — 0 if unknown",
                         "biz_waste", b.get("waste_kg_month"), minv=0.0,
                         maxv=5_000_000.0, step=10.0)
        b["waste_kg_month"] = waste if waste > 0 else None
    with c2:
        b["recycles"] = w.check("We recycle", "biz_rec", b.get("recycles"))
        if b["recycles"]:
            b["recycling_percent"] = w.slider_int(
                "% of waste recycled", "biz_recpct",
                b.get("recycling_percent") or 0, minv=0, maxv=100)

    if flags["food_waste"]:
        food = w.number("Food waste per month (kg)", "biz_food",
                        b.get("food_waste_kg_month"), minv=0.0, maxv=5_000_000.0,
                        step=5.0)
        b["food_waste_kg_month"] = food if food > 0 else None

    st.subheader("Premises heating")
    l["heating_method"] = w.select(
        "Main heating for the premises", "biz_heat", OPTIONS["heating_method"],
        l.get("heating_method", "None"),
        help="Electric heating is counted inside electricity; fuels are added "
             "separately.")
    if l["heating_method"] == "Gas":
        lpg = w.number("LPG per year (litres)", "biz_lpg",
                       l.get("heating_lpg_litres_per_year"), minv=0.0,
                       maxv=500_000.0, step=10.0)
        l["heating_lpg_litres_per_year"] = lpg if lpg > 0 else None

    st.subheader("Carbon offsets")
    l["buys_offsets"] = w.check("The business already buys carbon offsets",
                                "biz_off", l.get("buys_offsets"))
    if l["buys_offsets"]:
        t = w.number("Tonnes CO₂e offset per year", "biz_offt",
                     l.get("offset_tonnes_per_year"), minv=0.0, maxv=1_000_000.0,
                     step=1.0)
        l["offset_tonnes_per_year"] = t if t > 0 else None

    data["business"], data["lifestyle"] = b, l
    return data


# --------------------------------------------------------------------------
# Review rows (assessment.py renders the shared review hub with these)
# --------------------------------------------------------------------------

def _fmt(v, suffix=""):
    if v is None or v == "" or v is False:
        return None
    if v is True:
        return "Yes"
    if isinstance(v, float):
        return f"{v:g}{suffix}"
    return f"{v}{suffix}"


def section_rows(title, data):
    g, ws, es, t, b = (data["general"], data["water"], data["electricity"],
                       data["transport"], data["business"])
    rows = []
    if title == "Business profile":
        rows = [("Business", _fmt(g.get("business_name"))),
                ("Sector", _fmt(g.get("sector"))),
                ("Employees", _fmt(g.get("employees"))),
                ("Premises", _fmt(g.get("premises_count"))),
                ("Floor area", _fmt(g.get("floor_area_m2"), " m²")),
                ("Country", _fmt(g.get("country"))),
                ("Region", _fmt(g.get("region"))),
                ("Municipality", _fmt(g.get("municipality"))),
                ("Operating", (f"{g.get('operating_days_per_week')} days/wk · "
                               f"{g.get('operating_hours_per_day')} h/day"))]
    elif title == "Water":
        src = {"bill": "from your bill", "manual": "entered manually"}.get(
            ws.get("measured_source"))
        rows = [("Monthly use", f"{ws['water_kl_month']:g} kL ({src})"
                 if ws.get("water_kl_month") else None),
                ("Monthly bill", f"R{ws['water_bill_rand']:g}"
                 if ws.get("water_bill_rand") else None),
                ("Process water", _fmt(b.get("process_water_kl_month"), " kL/mo")),
                ("Irrigation", _fmt(b.get("irrigation_kl_month"), " kL/mo")),
                ("Recycled", _fmt(b.get("recycled_water_percent") or None, "%"))]
        if not ws.get("water_kl_month") and not ws.get("water_bill_rand"):
            rows.append(("Method", "Sector estimate from floor area"))
    elif title == "Electricity":
        src = {"bill": "from your bill", "manual": "entered manually"}.get(
            es.get("measured_source"))
        rows = [("Monthly use", f"{es['kwh_month']:g} kWh ({src})"
                 if es.get("kwh_month") else None),
                ("Monthly spend", f"R{es['bill_rand']:g}"
                 if es.get("bill_rand") else None),
                ("Renewables", f"{es['renewable_source']} · "
                               f"{es.get('renewable_percentage') or 0}%"
                 if es.get("renewable_source", "None") != "None" else None)]
        if not es.get("kwh_month") and not es.get("bill_rand"):
            rows.append(("Method", "Sector estimate from floor area"))
    elif title == "Backup power":
        rows = ([("Backup", "None")] if es.get("backup_power", "None") == "None"
                else [("Type", es["backup_power"])])
    elif title == "Fleet & travel":
        fleet = t.get("fleet", [])
        rows = [(f"{f.get('vehicle_type')} ×{f.get('count', 1)}",
                 f"{f['annual_km_each']:,.0f} km/yr each · {f.get('fuel')}")
                for f in fleet if f.get("annual_km_each")]
        fl = t.get("flights", [])
        for i, f in enumerate(fl):
            rows.append((f"Flight {i + 1}",
                         f"{f['departure_airport']} → {f['arrival_airport']} × "
                         f"{f['trips_per_year']}/yr"))
        if not rows:
            rows = [("Fleet & flights", "None")]
    elif title == "Waste & operations":
        rows = [("General waste", _fmt(b.get("waste_kg_month"), " kg/mo")),
                ("Recycling", _fmt(b.get("recycling_percent") or None, "%")
                 if b.get("recycles") else None),
                ("Food waste", _fmt(b.get("food_waste_kg_month"), " kg/mo")),
                ("Premises heating", _fmt(data["lifestyle"].get("heating_method")
                                          if data["lifestyle"].get("heating_method",
                                                                   "None") != "None"
                                          else None)),
                ("Offsets", _fmt(data["lifestyle"].get("offset_tonnes_per_year"),
                                 " t/yr")
                 if data["lifestyle"].get("buys_offsets") else None)]
    return [(label, val) for label, val in rows if val]
