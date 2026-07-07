"""Home page (§16): an obvious next step for everyone.

Logged out — two primary calls to action and a four-step journey.
Logged in — a personalized summary (mascot, score, latest stats) with big
Go-to buttons. Environmental education lives below the action area for both."""

import streamlit as st

import database as db
from views.common import current_user, latest_score
from visuals import render_mascot, icon, pill, score_ring


def _cta(label, page_key, primary=True, key=None):
    pages = st.session_state.get("pages", {})
    if st.button(label, type="primary" if primary else "secondary",
                 use_container_width=True, key=key or f"cta_{page_key}"):
        st.switch_page(pages[page_key])


def _logged_out_hero():
    left, right = st.columns([1.5, 1], gap="large")
    with left:
        st.title("I/mpact")
        st.markdown("### Understand your footprint. Grow something better.")
        st.markdown(
            "A friendly tracker for **water**, **electricity** and **carbon** "
            "— built for South African and African households.")
        c1, c2 = st.columns(2)
        with c1:
            _cta("Sign up — it's free", "account", primary=True, key="cta_signup")
        with c2:
            _cta("Log in", "account", primary=False, key="cta_login")
        st.markdown("")
        for n, (icon_name, text) in enumerate([
                ("edit", "Tell us about your impact — bills, habits, travel."),
                ("chart", "See your footprint, honestly calculated."),
                ("target", "Get a personalized improvement plan."),
                ("trend-down", "Track your progress week by week.")], start=1):
            st.markdown(
                f"<div style='display:flex;gap:.7rem;align-items:center;"
                f"padding:.18rem 0'><span style='font-weight:800;"
                f"color:#2E9E63'>{n}</span>{icon(icon_name, 17, '#2E9E63')}"
                f"<span>{text}</span></div>", unsafe_allow_html=True)
    with right:
        render_mascot(None, height=250, caption=False)
        st.caption("Meet your daisy — it thrives as your impact improves.")


def _logged_in_hero(user):
    latest = db.latest_assessment(user["id"])
    score = latest_score(user["id"])
    left, mid, right = st.columns([1, 1.35, 1.15], gap="large")
    with left:
        render_mascot(score, height=210, caption=False)
    with mid:
        st.title(f"Welcome back, {user['display_name'].split(' ')[0]}")
        if latest:
            r = latest["results"]
            st.markdown(score_ring(score, "Impact score"), unsafe_allow_html=True)
            st.markdown(
                pill(f"{r['water']['water_litres_person_day']:.0f} L/person/day", "water")
                + pill(f"{r['electricity']['total_electricity_kwh_month']:.0f} kWh/month", "bolt")
                + pill(f"{r['carbon']['net_co2e_kg_year']:,.0f} kg CO₂e/yr", "cloud"),
                unsafe_allow_html=True)
            streak = db.get_streak(user["id"])
            st.markdown(pill(f"Streak {streak['current']}", "flame"),
                        unsafe_allow_html=True)
        else:
            st.markdown("Your first assessment takes under 10 minutes — "
                        "your daisy is waiting.")
    with right:
        st.markdown("<div style='height:2.2rem'></div>", unsafe_allow_html=True)
        _cta("Go to Assessment", "assessment", primary=True)
        st.markdown("")
        _cta("Go to Dashboard", "dashboard", primary=False)


def _education():
    st.divider()
    st.markdown("#### Why this matters")
    c1, c2, c3 = st.columns(3)
    for col, (icon_name, title, text) in zip([c1, c2, c3], [
            ("cloud", "Greenhouse gases",
             "CO₂ lingers for centuries, so every kilogram avoided keeps "
             "helping. SA's coal-heavy grid means each kWh carries ~0.9 kg "
             "CO₂e — energy choices are climate choices."),
            ("bolt", "Electricity",
             "The geyser is usually a SA home's biggest slice. Cutting "
             "100 kWh/month saves roughly R350–R450 — and about 90 kg CO₂e. "
             "Same action, two wins."),
            ("water", "Water",
             "South Africa gets about half the world's average rainfall. The "
             "national benchmark is 218 L/person/day — every litre below it "
             "is real headroom for your city.")]):
        with col, st.container(border=True):
            st.markdown(icon(icon_name, 26, "#2E9E63"), unsafe_allow_html=True)
            st.markdown(f"**{title}**")
            st.caption(text)

    with st.container(key="band_home_why"):
        st.markdown("**Can one household really matter?** Systemic change — "
                    "grids, transport, industry — does the heavy lifting, and "
                    "we'll never pretend otherwise. But personal changes cut "
                    "real resource use, save real money, set your household's "
                    "defaults, normalise better choices for neighbours, and "
                    "add up to demand for cleaner systems. Start with your "
                    "biggest slice, not with perfection.")


def render():
    user = current_user()
    if user:
        _logged_in_hero(user)
    else:
        _logged_out_hero()
    _education()
