"""
AI Environmental Impact Tracker — Data Collection Form

This app ONLY collects user input and stores it in a Python dictionary
called `user_data`. It performs no calculations and includes no charts,
AI features, or dashboards.
"""

import streamlit as st

st.set_page_config(page_title="Environmental Impact Tracker — Data Collection", layout="centered")

st.title("🌍 Environmental Impact Tracker")
st.caption("Data collection only. No calculations are performed on this page.")

# ---------------------------------------------------------------------------
# Flight count lives OUTSIDE the form so the number of flight rows can update
# before the form is submitted.
# ---------------------------------------------------------------------------
num_flights = st.number_input(
    "How many flight routes do you want to add?",
    min_value=0,
    max_value=20,
    value=0,
    step=1,
    help="Set this first, then fill in each flight inside the form below.",
)

with st.form("environmental_data_form"):

    # -----------------------------------------------------------------------
    # General information
    # -----------------------------------------------------------------------
    st.header("General Information")
    household_size = st.number_input("Household size (number of people)", min_value=1, value=1, step=1)
    country = st.text_input("Country", value="South Africa")
    region = st.text_input("Province, state, or region (optional)")
    municipality = st.text_input("Municipality or local utility (optional)")

    # -----------------------------------------------------------------------
    # Water
    # -----------------------------------------------------------------------
    st.header("💧 Water")

    water_bill_file = st.file_uploader(
        "Upload a municipal water bill or statement (optional)",
        type=["pdf", "png", "jpg", "jpeg"],
    )
    monthly_water_usage = st.number_input(
        "Monthly water usage (kilolitres)", min_value=0.0, value=0.0, step=1.0
    )
    monthly_water_bill = st.number_input(
        "Monthly water bill amount", min_value=0.0, value=0.0, step=10.0
    )

    uses_rainwater = st.checkbox("Household uses rainwater harvesting")
    rainwater_percentage = st.slider(
        "Approximate percentage of water from rainwater (%)", 0, 100, 0
    )

    st.subheader("Water estimation questions (if no measured data)")
    shower_duration = st.number_input(
        "Average shower duration (minutes)", min_value=0.0, value=0.0, step=1.0
    )
    showers_per_week = st.number_input(
        "Number of showers per week", min_value=0, value=0, step=1
    )
    garden_irrigation = st.checkbox("Uses garden irrigation")
    swimming_pool = st.checkbox("Owns a swimming pool")

    # -----------------------------------------------------------------------
    # Electricity
    # -----------------------------------------------------------------------
    st.header("⚡ Electricity")

    electricity_bill_file = st.file_uploader(
        "Upload an electricity bill or prepaid meter statement (optional)",
        type=["pdf", "png", "jpg", "jpeg"],
    )
    monthly_electricity_usage = st.number_input(
        "Monthly electricity consumption (kWh)", min_value=0.0, value=0.0, step=10.0
    )
    monthly_electricity_bill = st.number_input(
        "Monthly electricity bill amount", min_value=0.0, value=0.0, step=10.0
    )

    renewable_source = st.selectbox(
        "Does your household generate renewable electricity?",
        ["None", "Solar", "Wind"],
    )
    renewable_percentage = st.slider(
        "Percentage of household electricity from renewable sources (%)", 0, 100, 0
    )

    backup_power = st.selectbox(
        "Backup power used during loadshedding",
        ["None", "Generator", "Inverter and battery", "Solar battery backup", "UPS"],
    )
    # Generator details
    generator_fuel_type = st.selectbox(
        "Generator fuel type (if applicable)", ["N/A", "Petrol", "Diesel", "Gas", "Other"]
    )
    generator_hours_per_month = st.number_input(
        "Generator hours used per month (if applicable)", min_value=0.0, value=0.0, step=1.0
    )
    generator_litres_per_month = st.number_input(
        "Generator litres of fuel per month (if applicable)", min_value=0.0, value=0.0, step=1.0
    )
    generator_coverage = st.selectbox(
        "Generator powers", ["N/A", "Whole home", "Essential loads only"]
    )
    # Inverter / battery / solar backup details
    backup_share = st.slider(
        "Share of household electricity supplied during outages (%)", 0, 100, 0
    )
    backup_charge_source = st.selectbox(
        "Backup system is charged from", ["N/A", "Grid", "Solar", "Both"]
    )

    st.subheader("Electricity estimation questions (if no measured data)")
    home_size = st.text_input("Home size (e.g. number of bedrooms or square metres)")
    electric_geyser = st.checkbox("Electric geyser")
    air_conditioner = st.checkbox("Air conditioner")
    electric_stove = st.checkbox("Electric stove")
    pool_pump = st.checkbox("Pool pump")

    # -----------------------------------------------------------------------
    # Transport
    # -----------------------------------------------------------------------
    st.header("🚗 Transport")

    st.subheader("Flights")
    flights = []
    for i in range(int(num_flights)):
        st.markdown(f"**Flight {i + 1}**")
        departure_airport = st.text_input("Departure airport", key=f"dep_{i}")
        arrival_airport = st.text_input("Arrival airport", key=f"arr_{i}")
        cabin_class = st.selectbox(
            "Cabin class", ["Economy", "Premium Economy", "Business", "First"], key=f"cabin_{i}"
        )
        trip_type = st.radio("Trip type", ["One-way", "Return"], key=f"trip_{i}", horizontal=True)
        trips_per_year = st.number_input(
            "Number of trips per year", min_value=0, value=1, step=1, key=f"count_{i}"
        )
        flights.append(
            {
                "departure_airport": departure_airport,
                "arrival_airport": arrival_airport,
                "cabin_class": cabin_class,
                "trip_type": trip_type,
                "trips_per_year": trips_per_year,
            }
        )

    st.subheader("Personal Vehicle")
    vehicle_manufacturer = st.text_input("Vehicle manufacturer")
    vehicle_model = st.text_input("Vehicle model")
    vehicle_year = st.number_input("Model year", min_value=1950, max_value=2100, value=2020, step=1)
    annual_distance = st.number_input(
        "Annual distance driven (km)", min_value=0.0, value=0.0, step=100.0
    )
    average_passengers = st.number_input(
        "Average number of passengers", min_value=0, value=1, step=1
    )

    st.subheader("Public Transport")
    public_transport_type = st.selectbox(
        "Transport type", ["None", "Bus", "Train", "Minibus taxi / taxi", "Subway", "Other"]
    )
    public_transport_distance = st.number_input(
        "Average distance travelled each week (km)", min_value=0.0, value=0.0, step=1.0
    )

    # -----------------------------------------------------------------------
    # Lifestyle
    # -----------------------------------------------------------------------
    st.header("🏡 Lifestyle")

    st.subheader("Home Heating")
    heating_method = st.selectbox(
        "Primary heating method",
        ["None", "Electricity", "Gas", "Coal", "Wood", "Paraffin / kerosene", "Heat pump"],
    )
    heating_months = st.number_input(
        "Months used annually", min_value=0, max_value=12, value=0, step=1
    )
    heating_hours_per_day = st.number_input(
        "Average hours used per day", min_value=0.0, max_value=24.0, value=0.0, step=0.5
    )

    st.subheader("Diet")
    diet = st.selectbox(
        "Which best matches your diet?",
        [
            "Heavy meat eater",
            "Average diet",
            "Mostly chicken",
            "Pescatarian",
            "Vegetarian",
            "Vegan",
        ],
    )

    st.subheader("Food Waste")
    food_waste = st.selectbox(
        "Estimated percentage of purchased food wasted",
        ["None", "Very little", "Around 10%", "Around 20%", "More than 30%"],
    )

    st.subheader("Shopping Habits")
    shopping_habits = st.selectbox(
        "Compared with the average person, your purchases (clothing, electronics, goods) are",
        ["Much less", "Less", "Average", "More", "Much more"],
    )

    st.subheader("Carbon Offsets")
    buys_offsets = st.checkbox("Purchases certified carbon offsets")
    annual_offset_amount = st.number_input(
        "Approximate annual amount of carbon offset (tonnes CO₂e)",
        min_value=0.0,
        value=0.0,
        step=0.1,
    )

    # -----------------------------------------------------------------------
    # Submit
    # -----------------------------------------------------------------------
    submitted = st.form_submit_button("Save my data")

# ---------------------------------------------------------------------------
# Collect everything into a single dictionary: user_data
# ---------------------------------------------------------------------------
if submitted:
    user_data = {
        "general": {
            "household_size": household_size,
            "country": country,
            "region": region,
            "municipality": municipality,
        },
        "water": {
            "bill_uploaded": water_bill_file is not None,
            "bill_filename": water_bill_file.name if water_bill_file else None,
            "monthly_water_usage": monthly_water_usage,
            "monthly_water_bill": monthly_water_bill,
            "uses_rainwater": uses_rainwater,
            "rainwater_percentage": rainwater_percentage,
            "shower_duration": shower_duration,
            "showers_per_week": showers_per_week,
            "garden_irrigation": garden_irrigation,
            "swimming_pool": swimming_pool,
        },
        "electricity": {
            "bill_uploaded": electricity_bill_file is not None,
            "bill_filename": electricity_bill_file.name if electricity_bill_file else None,
            "monthly_electricity_usage": monthly_electricity_usage,
            "monthly_electricity_bill": monthly_electricity_bill,
            "renewable_source": renewable_source,
            "renewable_percentage": renewable_percentage,
            "backup_power": backup_power,
            "generator_fuel_type": generator_fuel_type,
            "generator_hours_per_month": generator_hours_per_month,
            "generator_litres_per_month": generator_litres_per_month,
            "generator_coverage": generator_coverage,
            "backup_share": backup_share,
            "backup_charge_source": backup_charge_source,
            "home_size": home_size,
            "electric_geyser": electric_geyser,
            "air_conditioner": air_conditioner,
            "electric_stove": electric_stove,
            "pool_pump": pool_pump,
        },
        "transport": {
            "flights": flights,
            "vehicle": {
                "manufacturer": vehicle_manufacturer,
                "model": vehicle_model,
                "year": vehicle_year,
                "annual_distance": annual_distance,
                "average_passengers": average_passengers,
            },
            "public_transport": {
                "type": public_transport_type,
                "weekly_distance": public_transport_distance,
            },
        },
        "lifestyle": {
            "heating_method": heating_method,
            "heating_months": heating_months,
            "heating_hours_per_day": heating_hours_per_day,
            "diet": diet,
            "food_waste": food_waste,
            "shopping_habits": shopping_habits,
            "buys_offsets": buys_offsets,
            "annual_offset_amount": annual_offset_amount,
        },
    }

    st.success("Your data has been collected.")
    st.subheader("Collected data (user_data)")
    st.json(user_data)
