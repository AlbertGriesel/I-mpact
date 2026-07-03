"""
AI Environmental Impact Tracker — Data Collection Form (multi-step wizard)

This app ONLY collects user input and stores it in a Python dictionary
called `user_data`. It performs no calculations and includes no charts,
AI features, or dashboards.

Each category lives in its own module (water.py, electricity.py,
transport.py, lifestyle.py). Every module renders its own screen and
returns a dictionary; app.py combines them into user_data.

The user moves horizontally from section to section using the
Back / Next buttons. All answers are kept in st.session_state so
nothing is lost when switching screens.
"""

import streamlit as st

import water
import electricity
import transport
import lifestyle

st.set_page_config(page_title="Environmental Impact Tracker — Data Collection", layout="centered")

# Order of the wizard screens.
STEPS = ["General", "Water", "Electricity", "Transport", "Lifestyle", "Review"]


def default_general():
    """The initial, empty general-information dictionary."""
    return {
        "household_size": 1,
        "country": "South Africa",
        "region": "",
        "municipality": "",
    }


def render_general(data):
    """Render the general screen pre-filled with `data` and return the
    updated general dictionary."""
    st.header("General Information")
    household_size = st.number_input(
        "Household size (number of people)", min_value=1,
        value=int(data["household_size"]), step=1
    )
    country = st.text_input("Country", value=data["country"])
    region = st.text_input("Province, state, or region (optional)", value=data["region"])
    municipality = st.text_input(
        "Municipality or local utility (optional)", value=data["municipality"]
    )
    return {
        "household_size": household_size,
        "country": country,
        "region": region,
        "municipality": municipality,
    }


# ---------------------------------------------------------------------------
# Persistent state: user_data holds every answer; step is the current screen.
# ---------------------------------------------------------------------------
def default_user_data():
    return {
        "general": default_general(),
        "water": water.default_data(),
        "electricity": electricity.default_data(),
        "transport": transport.default_data(),
        "lifestyle": lifestyle.default_data(),
    }


if "user_data" not in st.session_state:
    st.session_state.user_data = default_user_data()
if "step" not in st.session_state:
    st.session_state.step = 0

user_data = st.session_state.user_data


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

# Each section module renders its screen and returns its dictionary;
# the result is combined into user_data.
current = STEPS[st.session_state.step]
if current == "General":
    user_data["general"] = render_general(user_data["general"])
elif current == "Water":
    user_data["water"] = water.render(user_data["water"])
elif current == "Electricity":
    user_data["electricity"] = electricity.render(user_data["electricity"])
elif current == "Transport":
    user_data["transport"] = transport.render(user_data["transport"])
elif current == "Lifestyle":
    user_data["lifestyle"] = lifestyle.render(user_data["lifestyle"])
elif current == "Review":
    st.header("✅ Review")
    st.write("You have reached the end of the questionnaire. All collected data is stored below.")
    st.subheader("Collected data (user_data)")
    st.json(user_data)
    if st.button("Start over"):
        st.session_state.user_data = default_user_data()
        st.session_state.step = 0
        st.rerun()

render_nav()
