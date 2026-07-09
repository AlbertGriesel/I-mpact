"""Home page (§16) — redesigned as the entry to a living environmental world.

Logged out — an oversized, asymmetric hero with the daisy guide, one strong
primary CTA and a friendly stepped "journey" (not a bullet list).
Logged in — the user's own Sprout character greets them, with their impact
told as ecological scenes (a filling reservoir, a clearing sky, a blooming
week) rather than dashboard number tiles. Education lives in a world band.
"""

from datetime import datetime

import streamlit as st

import database as db
import avatar as av
from views.common import current_user, latest_score
from visuals import (icon, score_ring, energy_tile, reservoir,
                     sky_clearing, meadow, brand_lockup, env_tier, TIER_LABEL,
                     GREEN, RIVER)


def _greeting():
    h = datetime.now().hour
    if h < 12:
        return "Good morning"
    if h < 18:
        return "Good afternoon"
    return "Good evening"


def _cta(label, page_key, primary=True, key=None):
    pages = st.session_state.get("pages", {})
    if st.button(label, type="primary" if primary else "secondary",
                 use_container_width=True, key=key or f"cta_{page_key}"):
        st.switch_page(pages[page_key])


_JOURNEY = [
    ("edit", "Tell us about your impact", "bills, habits, travel — in minutes"),
    ("chart", "See your footprint", "honestly calculated, never guilt-tripped"),
    ("target", "Get a personal plan", "small wins tailored to your home"),
    ("trend-down", "Watch it grow greener", "track your progress week by week"),
]


def _journey_html():
    steps = "".join(
        f"<div class='journey-step'><span class='journey-num'>{i}</span>"
        f"<span>{icon(ic, 18, GREEN)}</span>"
        f"<span class='jt'>{title} "
        f"<span style='color:#5c7069;font-weight:600'>— {sub}</span></span></div>"
        for i, (ic, title, sub) in enumerate(
            [(ic, t, s) for ic, t, s in _JOURNEY], start=1))
    return f"<div class='journey'>{steps}</div>"


def _logged_out_hero():
    left, right = st.columns([1.35, 1], gap="large")
    with left:
        st.markdown(brand_lockup(), unsafe_allow_html=True)
        st.title("Understand your impact. Grow something better.")
        st.markdown(
            "<p class='hero-sub'>Measure <b>water</b>, <b>electricity</b> and "
            "<b>carbon</b> impact for your <b>home or business</b>. Get clear "
            "results, practical goals and AI-guided ways to improve.</p>",
            unsafe_allow_html=True)
        st.markdown(
            "<p class='hero-note'>Built for individuals, households and "
            "businesses across South Africa and Africa.</p>",
            unsafe_allow_html=True)
        st.markdown("<div style='height:.5rem'></div>", unsafe_allow_html=True)
        _cta("Try the assessment — no account needed", "assessment",
             primary=True, key="cta_guest")
        c1, c2 = st.columns(2)
        with c1:
            _cta("Sign up — it's free", "account", primary=False,
                 key="cta_signup")
        with c2:
            _cta("Log in", "account", primary=False, key="cta_login")
        st.caption("Complete the whole thing as a guest and see your results — "
                   "create an account any time to save them.")
        st.markdown(_journey_html(), unsafe_allow_html=True)
    with right:
        # An environmental scene (the illustrated world) — NOT the daisy mascot,
        # which is reserved for guidance/loading/achievement contexts (brief §1).
        st.markdown("<div style='height:1.4rem'></div>", unsafe_allow_html=True)
        st.markdown(meadow(0.85, "A greener world, together",
                           caption="Water, energy and carbon — for homes and "
                                   "businesses alike."),
                    unsafe_allow_html=True)
        st.markdown(sky_clearing("Clear skies", "lower carbon, cleaner air",
                                 "What improvement looks like", 0.82),
                    unsafe_allow_html=True)


def _eco_stats(r, score):
    """Impact told as three living scenes instead of number tiles (§8).
    The score→t mapping lives in ONE place (visuals.scene_params) so this can
    never drift from the mascot/wallpaper interpretation."""
    from visuals import scene_params
    t = scene_params(score)["t"]
    water = r["water"]["water_litres_person_day"]
    elec = r["electricity"]["total_electricity_kwh_month"]
    carbon = r["carbon"]["net_co2e_kg_year"]
    # reservoir fills as usage drops below ~2× the SA benchmark (218 L)
    water_fill = max(0.05, min(1.0, 1 - water / 436))
    c1, c2, c3 = st.columns(3)
    c1.markdown(reservoir(water_fill, f"{water:,.0f}", "L/person/day", "Water",
                          sublabel="Fuller is better"),
                unsafe_allow_html=True)
    c2.markdown(energy_tile(f"{elec:,.0f}", "kWh/month", "Electricity",
                            sublabel="Cleaner as renewables rise"),
                unsafe_allow_html=True)
    c3.markdown(sky_clearing(f"{carbon:,.0f}", "kg CO₂e/yr", "Net carbon", t,
                             sublabel="Clearer sky as it falls"),
                unsafe_allow_html=True)


def _identity_block(user, tier, score):
    """WHO — the avatar with the user's name directly beneath it and a short
    environmental status (brief §9/§12). One coherent identity group."""
    mood = TIER_LABEL[tier] if score is not None else "Ready when you are"
    return (
        f"<div class='hero-identity'>{av.avatar_html(user, tier=tier, size=150)}"
        f"<div class='hero-name'>{user['display_name']}</div>"
        f"<div class='hero-mood'>{mood}</div></div>")


def _logged_in_hero(user):
    latest = db.latest_assessment(user["id"])
    score = latest_score(user["id"])
    tier = env_tier(score)

    st.markdown(f"<div class='eyebrow'>{_greeting()}, "
                f"{user['display_name'].split(' ')[0]}</div>",
                unsafe_allow_html=True)

    if latest:
        # WHO | HOW | NEXT — one intentional, aligned grid (brief §8/§12)
        who, how, nxt = st.columns([1, 1, 1.05], gap="large")
        with who:
            st.markdown(_identity_block(user, tier, score),
                        unsafe_allow_html=True)
        with how:
            st.markdown(
                f"<div style='display:flex;justify-content:center;"
                f"padding-top:.3rem'>{score_ring(score, 'Impact score')}</div>",
                unsafe_allow_html=True)
        with nxt:
            streak = db.get_streak(user["id"])
            st.markdown(
                f"<div class='chip-row' style='justify-content:flex-start'>"
                f"<span class='soft-chip'>{icon('flame',14,'#c8961e')} "
                f"{streak['current']}-check-in streak</span>"
                f"<span class='soft-chip blue'>{icon('trophy',14,RIVER)} "
                f"Best {streak['best']}</span></div>", unsafe_allow_html=True)
            st.markdown("<p class='hero-sub' style='margin-top:.4rem;"
                        "font-size:1rem'>Here's how your world is doing right "
                        "now — pick up where you left off.</p>",
                        unsafe_allow_html=True)
        # primary actions in one clearly aligned row beneath (brief §8)
        b1, b2 = st.columns(2)
        with b1:
            _cta("Update assessment", "assessment", primary=True)
        with b2:
            _cta("Open dashboard", "dashboard", primary=False)
        st.markdown("<div style='height:.6rem'></div>", unsafe_allow_html=True)
        _eco_stats(latest["results"], score)
    else:
        who, msg = st.columns([1, 1.6], gap="large")
        with who:
            st.markdown(_identity_block(user, tier, score),
                        unsafe_allow_html=True)
        with msg:
            st.markdown("<p class='hero-sub'>Your first assessment takes under "
                        "10 minutes — then your dashboard, plan and your "
                        "living world all come alive.</p>",
                        unsafe_allow_html=True)
            _cta("Start your assessment", "assessment", primary=True)


def _fact_tile(icon_name, tone_bg, tone_col, title, text):
    return (
        f"<div style='background:{tone_bg};border-radius:24px;padding:1.2rem "
        f"1.3rem;height:100%;border:1px solid rgba(27,94,59,.06)'>"
        f"<div style='width:46px;height:46px;border-radius:14px;background:#fff;"
        f"display:flex;align-items:center;justify-content:center;"
        f"box-shadow:0 4px 12px rgba(27,94,59,.1);margin-bottom:.7rem'>"
        f"{icon(icon_name, 24, tone_col)}</div>"
        f"<div style='font-family:\"Baloo 2\",sans-serif;font-weight:700;"
        f"font-size:1.12rem;color:#1B5E3B;margin-bottom:.3rem'>{title}</div>"
        f"<div style='color:#4a5f57;font-size:.93rem;line-height:1.5'>{text}"
        f"</div></div>")


def _education():
    st.markdown("<div style='height:1.6rem'></div>", unsafe_allow_html=True)
    st.markdown("<div class='eyebrow'>Why this matters</div>",
                unsafe_allow_html=True)
    st.markdown("<h2 style='margin-top:0'>Small homes, real weather.</h2>",
                unsafe_allow_html=True)
    c1, c2, c3 = st.columns(3)
    c1.markdown(_fact_tile(
        "cloud", "#eef7fd", RIVER, "Greenhouse gases",
        "CO₂ lingers for centuries, so every kilogram avoided keeps helping. "
        "SA's coal-heavy grid means each kWh carries ~0.9 kg CO₂e — energy "
        "choices are climate choices."), unsafe_allow_html=True)
    c2.markdown(_fact_tile(
        "bolt", "#fff7e3", "#c8961e", "Electricity",
        "The geyser is usually a SA home's biggest slice. Cutting 100 kWh/month "
        "saves roughly R350–R450 — and about 90 kg CO₂e. Same action, two "
        "wins."), unsafe_allow_html=True)
    c3.markdown(_fact_tile(
        "water", "#eafaf4", GREEN, "Water",
        "South Africa gets about half the world's average rainfall. The "
        "national benchmark is 218 L/person/day — every litre below it is real "
        "headroom for your city."), unsafe_allow_html=True)

    st.markdown("<div style='height:1rem'></div>", unsafe_allow_html=True)
    with st.container(key="band_home_why"):
        b1, b2 = st.columns([2.4, 1])
        with b1:
            st.markdown(
                "<h3 style='margin-top:.2rem'>Can one household really "
                "matter?</h3>", unsafe_allow_html=True)
            st.markdown(
                "Systemic change — grids, transport, industry — does the heavy "
                "lifting, and we'll never pretend otherwise. But personal "
                "changes cut real resource use, save real money, set your "
                "household's defaults, normalise better choices for neighbours, "
                "and add up to demand for cleaner systems. **Start with your "
                "biggest slice, not with perfection.**")
        with b2:
            st.markdown(meadow(0.8, "Every action counts",
                               caption="More flowers, more pollinators — your "
                               "world responds to what you do."),
                        unsafe_allow_html=True)


def render():
    user = current_user()
    if user:
        _logged_in_hero(user)
    else:
        _logged_out_hero()
    _education()
