"""Electricity section — collects electricity data and returns it as a dictionary."""

import streamlit as st


def _idx(options, value):
    """Return the index of value in options, or 0 if not present."""
    return options.index(value) if value in options else 0


def default_data():
    """The initial, empty electricity dictionary."""
    return {
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
    }


def render(data):
    """Render the electricity screen pre-filled with `data` and return the
    updated electricity dictionary."""
    st.header("⚡ Electricity")

    bill = st.file_uploader(
        "Upload an electricity bill or prepaid meter statement (optional)",
        type=["pdf", "png", "jpg", "jpeg"],
        key="elec_bill",
    )

    monthly_electricity_usage = st.number_input(
        "Monthly electricity consumption (kWh)", min_value=0.0,
        value=float(data["monthly_electricity_usage"]), step=10.0
    )
    monthly_electricity_bill = st.number_input(
        "Monthly electricity bill amount", min_value=0.0,
        value=float(data["monthly_electricity_bill"]), step=10.0
    )

    src = ["None", "Solar", "Wind"]
    renewable_source = st.selectbox(
        "Does your household generate renewable electricity?", src,
        index=_idx(src, data["renewable_source"])
    )
    renewable_percentage = st.slider(
        "Percentage of household electricity from renewable sources (%)", 0, 100,
        int(data["renewable_percentage"])
    )

    backup = ["None", "Generator", "Inverter and battery", "Solar battery backup", "UPS"]
    backup_power = st.selectbox(
        "Backup power used during loadshedding", backup,
        index=_idx(backup, data["backup_power"])
    )

    # Generator details
    fuel = ["N/A", "Petrol", "Diesel", "Gas", "Other"]
    generator_fuel_type = st.selectbox(
        "Generator fuel type (if applicable)", fuel,
        index=_idx(fuel, data["generator_fuel_type"])
    )
    generator_hours_per_month = st.number_input(
        "Generator hours used per month (if applicable)", min_value=0.0,
        value=float(data["generator_hours_per_month"]), step=1.0
    )
    generator_litres_per_month = st.number_input(
        "Generator litres of fuel per month (if applicable)", min_value=0.0,
        value=float(data["generator_litres_per_month"]), step=1.0
    )
    cover = ["N/A", "Whole home", "Essential loads only"]
    generator_coverage = st.selectbox(
        "Generator powers", cover, index=_idx(cover, data["generator_coverage"])
    )

    # Inverter / battery / solar backup details
    backup_share = st.slider(
        "Share of household electricity supplied during outages (%)", 0, 100,
        int(data["backup_share"])
    )
    charge = ["N/A", "Grid", "Solar", "Both"]
    backup_charge_source = st.selectbox(
        "Backup system is charged from", charge,
        index=_idx(charge, data["backup_charge_source"])
    )

    st.subheader("Electricity estimation questions (if no measured data)")
    home_size = st.text_input(
        "Home size (e.g. number of bedrooms or square metres)", value=data["home_size"]
    )
    electric_geyser = st.checkbox("Electric geyser", value=data["electric_geyser"])
    air_conditioner = st.checkbox("Air conditioner", value=data["air_conditioner"])
    electric_stove = st.checkbox("Electric stove", value=data["electric_stove"])
    pool_pump = st.checkbox("Pool pump", value=data["pool_pump"])

    return {
        "bill_uploaded": bill is not None or data["bill_uploaded"],
        "bill_filename": bill.name if bill is not None else data["bill_filename"],
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
    }
