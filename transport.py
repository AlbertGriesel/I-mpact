"""Transport section — collects transport data and returns it as a dictionary."""

import streamlit as st


def _idx(options, value):
    """Return the index of value in options, or 0 if not present."""
    return options.index(value) if value in options else 0


def default_data():
    """The initial, empty transport dictionary."""
    return {
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
    }


def render(data):
    """Render the transport screen pre-filled with `data` and return the
    updated transport dictionary."""
    st.header("🚗 Transport")

    st.subheader("Flights")
    num_flights = st.number_input(
        "How many flight routes do you want to add?", min_value=0, max_value=20,
        value=int(data["num_flights"]), step=1
    )

    # Grow or shrink the stored flight list to match the requested count.
    flights = [dict(f) for f in data["flights"]]
    while len(flights) < num_flights:
        flights.append(
            {"departure_airport": "", "arrival_airport": "", "cabin_class": "Economy",
             "trip_type": "One-way", "trips_per_year": 1}
        )
    while len(flights) > num_flights:
        flights.pop()

    cabins = ["Economy", "Premium Economy", "Business", "First"]
    trips = ["One-way", "Return"]
    for i, f in enumerate(flights):
        st.markdown(f"**Flight {i + 1}**")
        f["departure_airport"] = st.text_input(
            "Departure airport", value=f["departure_airport"], key=f"dep_{i}"
        )
        f["arrival_airport"] = st.text_input(
            "Arrival airport", value=f["arrival_airport"], key=f"arr_{i}"
        )
        f["cabin_class"] = st.selectbox(
            "Cabin class", cabins, index=_idx(cabins, f["cabin_class"]), key=f"cabin_{i}"
        )
        f["trip_type"] = st.radio(
            "Trip type", trips, index=_idx(trips, f["trip_type"]), key=f"trip_{i}", horizontal=True
        )
        f["trips_per_year"] = st.number_input(
            "Number of trips per year", min_value=0, value=int(f["trips_per_year"]),
            step=1, key=f"count_{i}"
        )

    st.subheader("Personal Vehicle")
    v = data["vehicle"]
    manufacturer = st.text_input("Vehicle manufacturer", value=v["manufacturer"])
    model = st.text_input("Vehicle model", value=v["model"])
    year = st.number_input(
        "Model year", min_value=1950, max_value=2100, value=int(v["year"]), step=1
    )
    annual_distance = st.number_input(
        "Annual distance driven (km)", min_value=0.0,
        value=float(v["annual_distance"]), step=100.0
    )
    average_passengers = st.number_input(
        "Average number of passengers", min_value=0,
        value=int(v["average_passengers"]), step=1
    )

    st.subheader("Public Transport")
    p = data["public_transport"]
    ptypes = ["None", "Bus", "Train", "Minibus taxi / taxi", "Subway", "Other"]
    public_type = st.selectbox("Transport type", ptypes, index=_idx(ptypes, p["type"]))
    weekly_distance = st.number_input(
        "Average distance travelled each week (km)", min_value=0.0,
        value=float(p["weekly_distance"]), step=1.0
    )

    return {
        "num_flights": num_flights,
        "flights": flights,
        "vehicle": {
            "manufacturer": manufacturer,
            "model": model,
            "year": year,
            "annual_distance": annual_distance,
            "average_passengers": average_passengers,
        },
        "public_transport": {
            "type": public_type,
            "weekly_distance": weekly_distance,
        },
    }
