"""Water section — collects water data and returns it as a dictionary."""

import streamlit as st


def default_data():
    """The initial, empty water dictionary."""
    return {
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
    }


def render(data):
    """Render the water screen pre-filled with `data` and return the
    updated water dictionary."""
    st.header("💧 Water")

    bill = st.file_uploader(
        "Upload a municipal water bill or statement (optional)",
        type=["pdf", "png", "jpg", "jpeg"],
        key="water_bill",
    )

    monthly_water_usage = st.number_input(
        "Monthly water usage (kilolitres)", min_value=0.0,
        value=float(data["monthly_water_usage"]), step=1.0
    )
    monthly_water_bill = st.number_input(
        "Monthly water bill amount", min_value=0.0,
        value=float(data["monthly_water_bill"]), step=10.0
    )

    uses_rainwater = st.checkbox(
        "Household uses rainwater harvesting", value=data["uses_rainwater"]
    )
    rainwater_percentage = st.slider(
        "Approximate percentage of water from rainwater (%)", 0, 100,
        int(data["rainwater_percentage"])
    )

    st.subheader("Water estimation questions (if no measured data)")
    shower_duration = st.number_input(
        "Average shower duration (minutes)", min_value=0.0,
        value=float(data["shower_duration"]), step=1.0
    )
    showers_per_week = st.number_input(
        "Number of showers per week", min_value=0,
        value=int(data["showers_per_week"]), step=1
    )
    garden_irrigation = st.checkbox("Uses garden irrigation", value=data["garden_irrigation"])
    swimming_pool = st.checkbox("Owns a swimming pool", value=data["swimming_pool"])

    return {
        "bill_uploaded": bill is not None or data["bill_uploaded"],
        "bill_filename": bill.name if bill is not None else data["bill_filename"],
        "monthly_water_usage": monthly_water_usage,
        "monthly_water_bill": monthly_water_bill,
        "uses_rainwater": uses_rainwater,
        "rainwater_percentage": rainwater_percentage,
        "shower_duration": shower_duration,
        "showers_per_week": showers_per_week,
        "garden_irrigation": garden_irrigation,
        "swimming_pool": swimming_pool,
    }
