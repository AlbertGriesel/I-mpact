"""Lifestyle section: home heating (with fuel quantities — hours alone can't
give emissions), diet, food waste, shopping habits and carbon offsets
(spec §10.4-10.8)."""

import streamlit as st

import widgets as w
from schema import OPTIONS


def render(data):
    st.header("Lifestyle")

    # ------------------------------------------------------------- heating
    st.subheader("Home heating")
    hm = w.select("Primary heating method", "heat_method",
                  OPTIONS["heating_method"], data.get("heating_method", "None"))
    data["heating_method"] = hm

    if hm == "Electricity":
        c1, c2, c3 = st.columns(3)
        with c1:
            data["heater_watts"] = w.slider_int(
                "Heater power (watts)", "heat_w",
                data.get("heater_watts") or 2000, minv=200, maxv=6000, step=100)
        with c2:
            hrs = w.slider_float("Hours per day", "heat_h",
                                 data.get("heating_hours_per_day") or 0.0,
                                 minv=0.0, maxv=24.0)
            data["heating_hours_per_day"] = hrs if hrs > 0 else None
        with c3:
            data["heating_months_per_year"] = w.slider_int(
                "Months per year", "heat_m",
                data.get("heating_months_per_year") or 3, minv=0, maxv=12)
        st.caption("If your electricity is measured, heating is already inside "
                   "it — we never double count.")
    elif hm == "Heat pump":
        st.caption("Heat pumps run on electricity — covered by your electricity "
                   "numbers, and far more efficient than element heating.")
    elif hm == "Gas":
        c1, c2 = st.columns(2)
        with c1:
            v = w.number("LPG used per year (litres)", "heat_lpg",
                         data.get("heating_lpg_litres_per_year"),
                         minv=0.0, maxv=5000.0, step=5.0,
                         help="A 9 kg bottle is roughly 17.6 litres.")
            data["heating_lpg_litres_per_year"] = v if v > 0 else None
        with c2:
            v = w.number("…or piped gas (m³/year)", "heat_gas",
                         data.get("heating_gas_m3_per_year"),
                         minv=0.0, maxv=5000.0, step=5.0)
            data["heating_gas_m3_per_year"] = v if v > 0 else None
    elif hm == "Paraffin / kerosene":
        v = w.number("Paraffin per year (litres)", "heat_para",
                     data.get("heating_paraffin_litres_per_year"),
                     minv=0.0, maxv=5000.0, step=5.0)
        data["heating_paraffin_litres_per_year"] = v if v > 0 else None
    elif hm == "Coal":
        v = w.number("Coal per year (kg)", "heat_coal",
                     data.get("heating_coal_kg_per_year"),
                     minv=0.0, maxv=20000.0, step=10.0)
        data["heating_coal_kg_per_year"] = v if v > 0 else None
    elif hm == "Wood":
        v = w.number("Wood per year (kg, rough guess)", "heat_wood",
                     data.get("heating_wood_kg_per_year"),
                     minv=0.0, maxv=20000.0, step=10.0)
        data["heating_wood_kg_per_year"] = v if v > 0 else None
        st.caption("Biomass carbon accounting is genuinely complicated — we keep "
                   "wood as context for the AI advisor rather than pretending "
                   "it's zero.")
    if hm in ("Gas", "Paraffin / kerosene", "Coal", "Wood"):
        c1, c2 = st.columns(2)
        with c1:
            data["heating_months_per_year"] = w.slider_int(
                "Months used per year", "heat_m2",
                data.get("heating_months_per_year") or 3, minv=0, maxv=12)
        with c2:
            hrs = w.slider_float("Hours per day", "heat_h2",
                                 data.get("heating_hours_per_day") or 0.0,
                                 minv=0.0, maxv=24.0)
            data["heating_hours_per_day"] = hrs if hrs > 0 else None

    # ---------------------------------------------------------------- diet
    st.subheader("Food")
    c1, c2 = st.columns(2)
    with c1:
        data["diet"] = w.select("Which best matches your diet?", "diet",
                                OPTIONS["diet"], data.get("diet", "Average diet"))
    with c2:
        data["food_waste"] = w.select(
            "How much of the food you buy gets wasted?", "waste",
            OPTIONS["food_waste"], data.get("food_waste", "None"),
            help="Wasted food means extra food must be bought and produced — "
                 "we adjust your diet footprint accordingly.")

    # ------------------------------------------------------------ shopping
    st.subheader("Shopping habits")
    data["shopping_habits"] = w.select_slider(
        "Compared with the average person, you buy (clothing, electronics, "
        "household goods)…", "shopping", OPTIONS["shopping_habits"],
        data.get("shopping_habits", "Average"))
    st.caption("Kept qualitative — it guides the AI's advice instead of "
               "inventing a CO₂ number.")

    # ------------------------------------------------------------- offsets
    st.subheader("Carbon offsets")
    data["buys_offsets"] = w.check("I buy certified carbon offsets", "offsets",
                                   data.get("buys_offsets"))
    if data["buys_offsets"]:
        v = w.number("Tonnes of CO₂e offset per year", "offset_t",
                     data.get("offset_tonnes_per_year"), minv=0.0, maxv=1000.0,
                     step=0.5)
        data["offset_tonnes_per_year"] = v if v > 0 else None
        st.caption("We always show your gross footprint too — offsets reduce "
                   "the net number, never hide the categories.")
    else:
        data["offset_tonnes_per_year"] = None
    return data
