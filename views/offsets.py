"""Carbon Offsets (spec §7) — lives in the Improve section.

Professional, balanced, concise: explains footprints and offsets, puts
reduction first, sets quality expectations, then lists reputable, verifiable
providers from a maintainable config. No guilt, no fabricated partnerships or
certifications.
"""

import streamlit as st

import database as db
from views.common import current_user, guest_assessment
from visuals import icon, pill
from offset_providers import active_providers

_DEEP = "#1B5E3B"
_GREEN = "#2E9E63"


def _net_carbon_tonnes():
    """The signed-in user's (or guest's) net CO2e in tonnes/year, or None."""
    user = current_user()
    results = None
    if user:
        a = db.latest_assessment(user["id"])
        results = a["results"] if a else None
    else:
        g = guest_assessment()
        results = g["results"] if g else None
    if not results:
        return None
    return results["carbon"]["net_co2e_kg_year"] / 1000.0


def _principle(ic, title, body):
    with st.container(border=True):
        st.markdown(f"{icon(ic, 20, _GREEN)} **{title}**", unsafe_allow_html=True)
        st.caption(body)


def _provider_card(p):
    with st.container(border=True):
        st.markdown(f"{icon('leaf', 18, _GREEN)} **{p['name']}**",
                    unsafe_allow_html=True)
        st.caption(p["blurb"])
        st.markdown(
            "<div style='display:flex;flex-wrap:wrap;gap:.3rem;margin:.2rem 0'>"
            + "".join(pill(t) for t in p["project_types"]) + "</div>",
            unsafe_allow_html=True)
        st.markdown(
            f"<div style='font-size:.82rem;color:#5c7069'>"
            f"{icon('map', 12, '#5c7069')} {p['regions']}<br>"
            f"{icon('check', 12, '#5c7069')} {p['standard']}</div>",
            unsafe_allow_html=True)
        st.link_button("Visit website ↗", p["url"], use_container_width=True)


def render():
    st.title("Carbon offsets")
    st.caption("Understand offsets, use them wisely, and choose credible "
               "providers — without the guilt.")

    tonnes = _net_carbon_tonnes()
    if tonnes is not None:
        with st.container(border=True):
            c1, c2 = st.columns([1, 2])
            with c1:
                st.markdown(f"{icon('cloud', 18, _GREEN)} **Your footprint**",
                            unsafe_allow_html=True)
                st.markdown(f"<div style='font-size:1.8rem;font-weight:800;"
                            f"color:{_DEEP}'>{tonnes:.1f} t</div>"
                            "<div style='color:#5c7069;font-size:.8rem'>"
                            "net CO₂e per year</div>", unsafe_allow_html=True)
            with c2:
                st.markdown(
                    "The most valuable thing you can do is **reduce** what you "
                    "can first — it's cheaper and permanent. Offsets are best "
                    "kept for the emissions you genuinely can't remove yet.")
                pages = st.session_state.get("pages", {})
                if "goals" in pages:
                    st.page_link(pages["goals"],
                                 label="See your personalised reduction goals",
                                 icon=":material/target:")

    st.subheader("The basics")
    c1, c2 = st.columns(2)
    with c1:
        _principle("cloud", "What a carbon footprint is",
                   "The total greenhouse gases your activities cause in a year, "
                   "expressed as kilograms or tonnes of CO₂-equivalent (CO₂e).")
    with c2:
        _principle("leaf", "What a carbon offset is",
                   "Paying for a project that avoids or removes an equivalent "
                   "amount of CO₂e elsewhere — for example renewable energy, "
                   "reforestation or clean cookstoves.")

    st.subheader("Use offsets well")
    c1, c2 = st.columns(2)
    with c1:
        _principle("trend-down", "Reduce first, then offset",
                   "Cutting avoidable emissions is cheaper and more certain "
                   "than offsetting. Treat offsets as the last step, for what's "
                   "genuinely hard to eliminate.")
        _principle("target", "For hard-to-avoid emissions",
                   "A flight you truly can't replace, or a process with no "
                   "clean alternative yet — that's where good offsets fit.")
    with c2:
        _principle("search", "Quality varies — a lot",
                   "Offsets are not all equal. Look for credible independent "
                   "verification, transparency, additionality (it wouldn't have "
                   "happened anyway), permanence and ongoing monitoring.")
        _principle("star", "What to look for",
                   "Recognised standards (e.g. Gold Standard, Verra), a public "
                   "project registry, clear reporting on where your money goes, "
                   "and honest permanence claims.")

    st.subheader("Reputable providers to explore")
    st.caption("A starting point of well-known, independently-verifiable "
               "organisations — not a ranking. Always check a specific "
               "project's current documentation before buying.")
    providers = active_providers()
    cols = st.columns(3)
    for i, p in enumerate(providers):
        with cols[i % 3]:
            _provider_card(p)

    st.divider()
    st.caption(
        "Transparency: I/mpact has **no partnership** with these organisations "
        "and earns **no commission** from them. They're listed for your "
        "convenience only. Verify each project's certification and claims "
        "independently before purchasing.")
