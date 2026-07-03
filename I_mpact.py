"""
AI Environmental Impact Tracker — Data Collection Form (multi-step wizard)

This app ONLY collects user input and stores it in a Python dictionary
called `user_data`. It performs no calculations and includes no charts,
AI features, or dashboards.

The form is split into independent screens (General, Water, Electricity,
Transport, Lifestyle, Review). The user moves horizontally from one
section to the next using the Back / Next buttons. All answers are kept
in st.session_state so nothing is lost when switching screens.
"""

import streamlit as st

st.set_page_config(page_title="Environmental Impact Tracker — Data Collection", layout="centered")

# Order of the wizard screens.
STEPS = ["General", "Water", "Electricity", "Transport", "Lifestyle", "Review"]


def default_data():
    """The initial, empty user_data dictionary."""
    return {
        "general": {
            "household_size": 1,
            "country": "South Africa",
            "region": "",
            "municipality": "",
        },
        "water": {
            "bill_uploaded": False,
            "bill_filename": None,
            "monthly_water_usage": 0.0,
            "monthly_water_bill": 0.0,
            "uses_rainwater": False,
            "rainwater_percentage": 0,
            "shower_duration": 0.0,
            "showers_per_week": 0,
            "garden_irrigation": False,
            "swimming_pool": False,
        },
        "electricity": {
            "bill_uploaded": False,
            "bill_filename": None,
            "monthly_electricity_usage": 0.0,
            "monthly_electricity_bill": 0.0,
            "renewable_source": "None",
            "renewable_percentage": 0,
            "backup_power": "None",
            "generator_fuel_type": "N/A",
            "generator_hours_per_month": 0.0,
            "generator_litres_per_month": 0.0,
            "generator_coverage": "N/A",
            "backup_share": 0,
            "backup_charge_source": "N/A",
            "home_size": "",
            "electric_geyser": False,
            "air_conditioner": False,
            "electric_stove": False,
            "pool_pump": False,
        },
        "transport": {
            "num_flights": 0,
            "flights": [],
            "vehicle": {
                "manufacturer": "",
                "model": "",
                "year": 2020,
                "annual_distance": 0.0,
                "average_passengers": 1,
            },
            "public_transport": {
                "type": "None",
                "weekly_distance": 0.0,
            },
        },
        "lifestyle": {
            "heating_method": "None",
            "heating_months": 0,
            "heating_hours_per_day": 0.0,
            "diet": "Average diet",
            "food_waste": "None",
            "shopping_habits": "Average",
            "buys_offsets": False,
            "annual_offset_amount": 0.0,
        },
    }


# ---------------------------------------------------------------------------
# Persistent state: user_data holds every answer; step is the current screen.
# ---------------------------------------------------------------------------
if "user_data" not in st.session_state:
    st.session_state.user_data = default_data()
if "step" not in st.session_state:
    st.session_state.step = 0

user_data = st.session_state.user_data


def idx(options, value, default=0):
    """Return the index of value in options, or a default if not present."""
    return options.index(value) if value in options else default


# ---------------------------------------------------------------------------
# Screen renderers — each reads from and writes back into user_data.
# ---------------------------------------------------------------------------
def render_general():
    st.header("General Information")
    g = user_data["general"]
    g["household_size"] = st.number_input(
        "Household size (number of people)", min_value=1, value=int(g["household_size"]), step=1
    )
    g["country"] = st.text_input("Country", value=g["country"])
    g["region"] = st.text_input("Province, state, or region (optional)", value=g["region"])
    g["municipality"] = st.text_input(
        "Municipality or local utility (optional)", value=g["municipality"]
    )


def render_water():
    st.header("💧 Water")
    w = user_data["water"]

    bill = st.file_uploader(
        "Upload a municipal water bill or statement (optional)",
        type=["pdf", "png", "jpg", "jpeg"],
        key="water_bill",
    )
    if bill is not None:
        w["bill_uploaded"] = True
        w["bill_filename"] = bill.name

    w["monthly_water_usage"] = st.number_input(
        "Monthly water usage (kilolitres)", min_value=0.0, value=float(w["monthly_water_usage"]), step=1.0
    )
    w["monthly_water_bill"] = st.number_input(
        "Monthly water bill amount", min_value=0.0, value=float(w["monthly_water_bill"]), step=10.0
    )

    w["uses_rainwater"] = st.checkbox("Household uses rainwater harvesting", value=w["uses_rainwater"])
    w["rainwater_percentage"] = st.slider(
        "Approximate percentage of water from rainwater (%)", 0, 100, int(w["rainwater_percentage"])
    )

    st.subheader("Water estimation questions (if no measured data)")
    w["shower_duration"] = st.number_input(
        "Average shower duration (minutes)", min_value=0.0, value=float(w["shower_duration"]), step=1.0
    )
    w["showers_per_week"] = st.number_input(
        "Number of showers per week", min_value=0, value=int(w["showers_per_week"]), step=1
    )
    w["garden_irrigation"] = st.checkbox("Uses garden irrigation", value=w["garden_irrigation"])
    w["swimming_pool"] = st.checkbox("Owns a swimming pool", value=w["swimming_pool"])


def render_electricity():
    st.header("⚡ Electricity")
    e = user_data["electricity"]

    bill = st.file_uploader(
        "Upload an electricity bill or prepaid meter statement (optional)",
        type=["pdf", "png", "jpg", "jpeg"],
        key="elec_bill",
    )
    if bill is not None:
        e["bill_uploaded"] = True
        e["bill_filename"] = bill.name

    e["monthly_electricity_usage"] = st.number_input(
        "Monthly electricity consumption (kWh)", min_value=0.0,
        value=float(e["monthly_electricity_usage"]), step=10.0
    )
    e["monthly_electricity_bill"] = st.number_input(
        "Monthly electricity bill amount", min_value=0.0,
        value=float(e["monthly_electricity_bill"]), step=10.0
    )

    src = ["None", "Solar", "Wind"]
    e["renewable_source"] = st.selectbox(
        "Does your household generate renewable electricity?", src,
        index=idx(src, e["renewable_source"])
    )
    e["renewable_percentage"] = st.slider(
        "Percentage of household electricity from renewable sources (%)", 0, 100,
        int(e["renewable_percentage"])
    )

    backup = ["None", "Generator", "Inverter and battery", "Solar battery backup", "UPS"]
    e["backup_power"] = st.selectbox(
        "Backup power used during loadshedding", backup, index=idx(backup, e["backup_power"])
    )

    # Generator details
    fuel = ["N/A", "Petrol", "Diesel", "Gas", "Other"]
    e["generator_fuel_type"] = st.selectbox(
        "Generator fuel type (if applicable)", fuel, index=idx(fuel, e["generator_fuel_type"])
    )
    e["generator_hours_per_month"] = st.number_input(
        "Generator hours used per month (if applicable)", min_value=0.0,
        value=float(e["generator_hours_per_month"]), step=1.0
    )
    e["generator_litres_per_month"] = st.number_input(
        "Generator litres of fuel per month (if applicable)", min_value=0.0,
        value=float(e["generator_litres_per_month"]), step=1.0
    )
    cover = ["N/A", "Whole home", "Essential loads only"]
    e["generator_coverage"] = st.selectbox(
        "Generator powers", cover, index=idx(cover, e["generator_coverage"])
    )

    # Inverter / battery / solar backup details
    e["backup_share"] = st.slider(
        "Share of household electricity supplied during outages (%)", 0, 100,
        int(e["backup_share"])
    )
    charge = ["N/A", "Grid", "Solar", "Both"]
    e["backup_charge_source"] = st.selectbox(
        "Backup system is charged from", charge, index=idx(charge, e["backup_charge_source"])
    )

    st.subheader("Electricity estimation questions (if no measured data)")
    e["home_size"] = st.text_input(
        "Home size (e.g. number of bedrooms or square metres)", value=e["home_size"]
    )
    e["electric_geyser"] = st.checkbox("Electric geyser", value=e["electric_geyser"])
    e["air_conditioner"] = st.checkbox("Air conditioner", value=e["air_conditioner"])
    e["electric_stove"] = st.checkbox("Electric stove", value=e["electric_stove"])
    e["pool_pump"] = st.checkbox("Pool pump", value=e["pool_pump"])


def render_transport():
    st.header("🚗 Transport")
    t = user_data["transport"]

    st.subheader("Flights")
    t["num_flights"] = st.number_input(
        "How many flight routes do you want to add?", min_value=0, max_value=20,
        value=int(t["num_flights"]), step=1
    )
    # Grow or shrink the stored flight list to match the requested count.
    flights = t["flights"]
    while len(flights) < t["num_flights"]:
        flights.append(
            {"departure_airport": "", "arrival_airport": "", "cabin_class": "Economy",
             "trip_type": "One-way", "trips_per_year": 1}
        )
    while len(flights) > t["num_flights"]:
        flights.pop()

    cabins = ["Economy", "Premium Economy", "Business", "First"]
    trips = ["One-way", "Return"]
    for i, f in enumerate(flights):
        st.markdown(f"**Flight {i + 1}**")
        f["departure_airport"] = st.text_input("Departure airport", value=f["departure_airport"], key=f"dep_{i}")
        f["arrival_airport"] = st.text_input("Arrival airport", value=f["arrival_airport"], key=f"arr_{i}")
        f["cabin_class"] = st.selectbox("Cabin class", cabins, index=idx(cabins, f["cabin_class"]), key=f"cabin_{i}")
        f["trip_type"] = st.radio("Trip type", trips, index=idx(trips, f["trip_type"]), key=f"trip_{i}", horizontal=True)
        f["trips_per_year"] = st.number_input("Number of trips per year", min_value=0, value=int(f["trips_per_year"]), step=1, key=f"count_{i}")

    st.subheader("Personal Vehicle")
    v = t["vehicle"]
    v["manufacturer"] = st.text_input("Vehicle manufacturer", value=v["manufacturer"])
    v["model"] = st.text_input("Vehicle model", value=v["model"])
    v["year"] = st.number_input("Model year", min_value=1950, max_value=2100, value=int(v["year"]), step=1)
    v["annual_distance"] = st.number_input(
        "Annual distance driven (km)", min_value=0.0, value=float(v["annual_distance"]), step=100.0
    )
    v["average_passengers"] = st.number_input(
        "Average number of passengers", min_value=0, value=int(v["average_passengers"]), step=1
    )

    st.subheader("Public Transport")
    p = t["public_transport"]
    ptypes = ["None", "Bus", "Train", "Minibus taxi / taxi", "Subway", "Other"]
    p["type"] = st.selectbox("Transport type", ptypes, index=idx(ptypes, p["type"]))
    p["weekly_distance"] = st.number_input(
        "Average distance travelled each week (km)", min_value=0.0, value=float(p["weekly_distance"]), step=1.0
    )


def render_lifestyle():
    st.header("🏡 Lifestyle")
    l = user_data["lifestyle"]

    st.subheader("Home Heating")
    heat = ["None", "Electricity", "Gas", "Coal", "Wood", "Paraffin / kerosene", "Heat pump"]
    l["heating_method"] = st.selectbox("Primary heating method", heat, index=idx(heat, l["heating_method"]))
    l["heating_months"] = st.number_input(
        "Months used annually", min_value=0, max_value=12, value=int(l["heating_months"]), step=1
    )
    l["heating_hours_per_day"] = st.number_input(
        "Average hours used per day", min_value=0.0, max_value=24.0,
        value=float(l["heating_hours_per_day"]), step=0.5
    )

    st.subheader("Diet")
    diets = ["Heavy meat eater", "Average diet", "Mostly chicken", "Pescatarian", "Vegetarian", "Vegan"]
    l["diet"] = st.selectbox("Which best matches your diet?", diets, index=idx(diets, l["diet"]))

    st.subheader("Food Waste")
    waste = ["None", "Very little", "Around 10%", "Around 20%", "More than 30%"]
    l["food_waste"] = st.selectbox(
        "Estimated percentage of purchased food wasted", waste, index=idx(waste, l["food_waste"])
    )

    st.subheader("Shopping Habits")
    shop = ["Much less", "Less", "Average", "More", "Much more"]
    l["shopping_habits"] = st.selectbox(
        "Compared with the average person, your purchases (clothing, electronics, goods) are",
        shop, index=idx(shop, l["shopping_habits"])
    )

    st.subheader("Carbon Offsets")
    l["buys_offsets"] = st.checkbox("Purchases certified carbon offsets", value=l["buys_offsets"])
    l["annual_offset_amount"] = st.number_input(
        "Approximate annual amount of carbon offset (tonnes CO₂e)", min_value=0.0,
        value=float(l["annual_offset_amount"]), step=0.1
    )


def render_review():
    st.header("✅ Review")
    st.write("You have reached the end of the questionnaire. All collected data is stored below.")
    st.subheader("Collected data (user_data)")
    st.json(user_data)
    if st.button("Start over"):
        st.session_state.user_data = default_data()
        st.session_state.step = 0
        st.rerun()


RENDERERS = {
    "General": render_general,
    "Water": render_water,
    "Electricity": render_electricity,
    "Transport": render_transport,
    "Lifestyle": render_lifestyle,
    "Review": render_review,
}


# ---------------------------------------------------------------------------
# Horizontal stepper across the top.
# ---------------------------------------------------------------------------
def render_progress():
    cols = st.columns(len(STEPS))
    for i, (col, label) in enumerate(zip(cols, STEPS)):
        with col:
            if i == st.session_state.step:
                st.markdown(f"**🔵 {label}**")
            elif i < st.session_state.step:
                st.markdown(f"✅ {label}")
            else:
                st.markdown(f"⚪ {label}")
    st.progress(st.session_state.step / (len(STEPS) - 1))


# ---------------------------------------------------------------------------
# Back / Next navigation.
# ---------------------------------------------------------------------------
def render_nav():
    st.divider()
    left, _, right = st.columns([1, 2, 1])
    with left:
        if st.session_state.step > 0:
            if st.button("← Back", use_container_width=True):
                st.session_state.step -= 1
                st.rerun()
    with right:
        if st.session_state.step < len(STEPS) - 1:
            if st.button("Next →", use_container_width=True, type="primary"):
                st.session_state.step += 1
                st.rerun()


# ---------------------------------------------------------------------------
# Page layout.
# ---------------------------------------------------------------------------
st.title("🌍 Environmental Impact Tracker")
st.caption("Data collection only. No calculations are performed on this page.")

render_progress()
st.divider()
RENDERERS[STEPS[st.session_state.step]]()
render_nav()
