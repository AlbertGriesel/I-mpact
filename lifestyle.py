"""Lifestyle section — collects lifestyle data and returns it as a dictionary."""

import streamlit as st


def _idx(options, value):
    """Return the index of value in options, or 0 if not present."""
    return options.index(value) if value in options else 0


def default_data():
    """The initial, empty lifestyle dictionary."""
    return {
        "heating_method": "None",
        "heating_months": 0,
        "heating_hours_per_day": 0.0,
        "diet": "Average diet",
        "food_waste": "None",
        "shopping_habits": "Average",
        "buys_offsets": False,
        "annual_offset_amount": 0.0,
    }


def render(data):
    """Render the lifestyle screen pre-filled with `data` and return the
    updated lifestyle dictionary."""
    st.header("🏡 Lifestyle")

    st.subheader("Home Heating")
    heat = ["None", "Electricity", "Gas", "Coal", "Wood", "Paraffin / kerosene", "Heat pump"]
    heating_method = st.selectbox(
        "Primary heating method", heat, index=_idx(heat, data["heating_method"])
    )
    heating_months = st.number_input(
        "Months used annually", min_value=0, max_value=12,
        value=int(data["heating_months"]), step=1
    )
    heating_hours_per_day = st.number_input(
        "Average hours used per day", min_value=0.0, max_value=24.0,
        value=float(data["heating_hours_per_day"]), step=0.5
    )

    st.subheader("Diet")
    diets = ["Heavy meat eater", "Average diet", "Mostly chicken",
             "Pescatarian", "Vegetarian", "Vegan"]
    diet = st.selectbox(
        "Which best matches your diet?", diets, index=_idx(diets, data["diet"])
    )

    st.subheader("Food Waste")
    waste = ["None", "Very little", "Around 10%", "Around 20%", "More than 30%"]
    food_waste = st.selectbox(
        "Estimated percentage of purchased food wasted", waste,
        index=_idx(waste, data["food_waste"])
    )

    st.subheader("Shopping Habits")
    shop = ["Much less", "Less", "Average", "More", "Much more"]
    shopping_habits = st.selectbox(
        "Compared with the average person, your purchases (clothing, electronics, goods) are",
        shop, index=_idx(shop, data["shopping_habits"])
    )

    st.subheader("Carbon Offsets")
    buys_offsets = st.checkbox(
        "Purchases certified carbon offsets", value=data["buys_offsets"]
    )
    annual_offset_amount = st.number_input(
        "Approximate annual amount of carbon offset (tonnes CO₂e)", min_value=0.0,
        value=float(data["annual_offset_amount"]), step=0.1
    )

    return {
        "heating_method": heating_method,
        "heating_months": heating_months,
        "heating_hours_per_day": heating_hours_per_day,
        "diet": diet,
        "food_waste": food_waste,
        "shopping_habits": shopping_habits,
        "buys_offsets": buys_offsets,
        "annual_offset_amount": annual_offset_amount,
    }
