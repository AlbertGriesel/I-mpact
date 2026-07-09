"""Shared helpers for the view modules."""

import copy

import streamlit as st

import database as db
import achievements as ach
import locations as loc
import widgets as w
from calculations import run_assessment
from goals import pick_weekly_goals
from visuals import icon

# placeholder option meaning "not specified" in the dependent location pickers
_LOC_PLACEHOLDER = "— Select —"


_PRIVACY_CORE = (
    "Your data will not be shared with third parties without your permission. "
    "It's kept in a local database on the app's server. AI features send your "
    "inputs (like a bill image or your answers) to the AI provider to read and "
    "advise — never your password. Public sharing is opt-in and limited to the "
    "summary stats you approve; bills, raw data and chats always stay private.")

_PRIVACY_NOTES = {
    "general": ("Private by default — your data isn't shared without your "
                "permission.", _PRIVACY_CORE),
    "signup": ("Private by default. You choose if anything is ever shared.",
               _PRIVACY_CORE),
    "chat": ("This chat is private — Sprout only uses it to build your "
             "assessment.",
             _PRIVACY_CORE + "\n\nThe conversation is used only to fill your "
             "own assessment fields; it isn't shown to anyone else."),
    "submit": ("Your results are saved privately to your account.",
               _PRIVACY_CORE),
    "upload": ("We read the bill to fill your assessment — you confirm every "
               "value.",
               "**Why we process it:** to read your consumption and amount so "
               "you don't have to type them.\n\n**What we extract:** usage "
               "(kWh or kL), the bill amount, the municipality/utility and the "
               "billing period.\n\n**How it's used:** it pre-fills your "
               "assessment *after you confirm* — nothing counts until you do.\n\n"
               "**Storage:** the file is stored privately under your account "
               "and is never shown on public pages. " + _PRIVACY_CORE),
    "settings": ("You're in control of what's private and what's shared.",
                 _PRIVACY_CORE),
}


def privacy_note(context="general", *, expanded=False):
    """A small, accurate privacy reassurance with an expandable detail
    (spec §10). Wording matches the app's real data practices — no invented
    guarantees."""
    line, detail = _PRIVACY_NOTES.get(context, _PRIVACY_NOTES["general"])
    st.markdown(
        f"<div style='display:flex;align-items:center;gap:.4rem;"
        f"color:#5c7069;font-size:.82rem;margin:.1rem 0'>"
        f"{icon('lock', 13, '#5c7069')} {line}</div>", unsafe_allow_html=True)
    with st.expander("How your data is handled", expanded=expanded):
        st.markdown(detail)


def measure_intro(active):
    """The two-ways-to-assess chooser (spec §1), shown at the top of both the
    Assessment and Chat Assessment pages. `active` is 'manual' or 'chat'."""
    pages = st.session_state.get("pages", {})
    st.markdown("#### Two ways to tell us about your impact")
    st.caption("Both ask the same questions, use the **same calculations** and "
               "produce the **same results** — pick whichever feels easier, and "
               "you can switch any time.")
    cards = [
        ("manual", "assessment", "edit", "Fill it in myself",
         "Answer a structured set of questions about your water, electricity, "
         "travel and lifestyle. Upload a bill and we read it for you."),
        ("chat", "chat", "chat", "AI Assessment",
         "Chat naturally with our AI assistant. It asks the same questions in "
         "conversation and fills in your assessment as you talk."),
    ]
    # keyed wrapper so the two cards share equal height and their action links
    # bottom-align, whichever description wraps longer (brief §5)
    with st.container(key="measure_cards"):
        c1, c2 = st.columns(2)
        for col, (kind, page_key, ic, title, desc) in zip((c1, c2), cards):
            with col, st.container(border=True):
                here = (" <span class='pill' style='font-size:.68rem'>"
                        "you're here</span>") if kind == active else ""
                st.markdown(f"{icon(ic, 20, '#2E9E63')} **{title}**{here}",
                            unsafe_allow_html=True)
                st.caption(desc)
                if kind != active and page_key in pages:
                    st.page_link(pages[page_key], label=f"Switch to “{title}”",
                                 icon=":material/swap_horiz:")


def location_picker(general, *, key_prefix="loc"):
    """Dependent Country → Region → Municipality selectors (spec §6).

    Country is a validated searchable list (no free text). Region is disabled
    until a country with known regions is chosen; Municipality is disabled
    until a region with known local authorities is chosen. Where we don't hold
    the data we say so plainly instead of faking it. Writes validated values
    back into `general` (country/region/municipality)."""
    country_ph = "Select your country…"
    countries = [country_ph] + loc.country_options()
    cur_c = general.get("country") if loc.is_country(general.get("country")) else country_ph
    picked_c = w.select(
        "Country", f"{key_prefix}_country", countries, cur_c,
        help="Start typing to search. Only listed countries can be chosen.")
    general["country"] = "" if picked_c == country_ph else picked_c
    country = general["country"]

    # --- region (level 1) — disabled until a country is chosen (§3) ---
    if not country:
        st.selectbox("Province / Region", ["Select a country first"],
                     disabled=True, key=f"aw_{key_prefix}_region_gate",
                     help="Choose a country above to enable this field.")
        st.selectbox("Municipality / local authority",
                     ["Select a country first"], disabled=True,
                     key=f"aw_{key_prefix}_muni_gate")
        general["region"] = ""
        general["municipality"] = ""
        return general
    if loc.has_regions(country):
        opts = [_LOC_PLACEHOLDER] + loc.region_options(country)
        cur = general.get("region") or _LOC_PLACEHOLDER
        pick = w.select(loc.region_term(country), f"{key_prefix}_region",
                        opts, cur if cur in opts else _LOC_PLACEHOLDER)
        general["region"] = "" if pick in (_LOC_PLACEHOLDER, loc.NOT_LISTED) else pick
    else:
        st.selectbox(
            loc.region_term(country), ["Regional list not available yet"],
            disabled=True, key=f"aw_{key_prefix}_region_off",
            help="We don't hold regions for this country yet — you can "
                 "continue without it; national figures are used.")
        # Visible, honest explanation (brief §4) — never leave a mysteriously
        # empty selector; say plainly what will be used instead.
        st.caption(f"Detailed regional data isn't available for {country} yet. "
                   "National factors will be used.")
        general["region"] = ""

    # --- municipality (level 2, depends on region) ---
    region = general.get("region")
    if region and loc.has_municipalities(country, region):
        opts = [_LOC_PLACEHOLDER] + loc.municipality_options(country, region)
        cur = general.get("municipality") or _LOC_PLACEHOLDER
        pick = w.select(
            loc.municipality_term(country), f"{key_prefix}_muni", opts,
            cur if cur in opts else _LOC_PLACEHOLDER,
            help="Lets us convert bill amounts with the right local block tariff.")
        general["municipality"] = "" if pick in (_LOC_PLACEHOLDER, loc.NOT_LISTED) else pick
    else:
        needs_region = loc.has_regions(country) and not region
        st.selectbox(
            loc.municipality_term(country),
            [f"Choose a {loc.region_term(country).lower()} first" if needs_region
             else "Local-authority list not available yet"],
            disabled=True, key=f"aw_{key_prefix}_muni_off")
        if not needs_region:
            # Honest note (brief §4): we don't itemise local authorities here,
            # rather than fabricating them.
            st.caption("Local-authority data isn't available for this area "
                       "yet. Regional or national factors will be used.")
        general["municipality"] = ""
    # Defense-in-depth: run the picker's result through the SAME canonical rule
    # the chat path uses, so neither flow can leave an inconsistent triple.
    general["country"], general["region"], general["municipality"] = \
        loc.resolve_location(general.get("country"), general.get("region"),
                             general.get("municipality"))
    return general

# period conversion: internal units are water L/month, elec kWh/month,
# carbon kg/year (calc doc §1)
PERIODS = ["day", "week", "month", "year"]
_FROM_MONTH = {"day": 12 / 365, "week": 12 / 52, "month": 1.0, "year": 12.0}
_FROM_YEAR = {"day": 1 / 365, "week": 1 / 52, "month": 1 / 12, "year": 1.0}


def from_month(value, period):
    return value * _FROM_MONTH[period]


def from_year(value, period):
    return value * _FROM_YEAR[period]


def current_user():
    return st.session_state.get("user")


def require_login(message="Sign in to use this page — it's free and quick."):
    user = current_user()
    if user is None:
        st.info(message, icon=":material/lock:")
        pages = st.session_state.get("pages", {})
        if "account" in pages:
            st.page_link(pages["account"], label="Go to Sign in / Sign up",
                         icon=":material/person:")
        st.stop()
    return user


def latest_score(user_id):
    a = db.latest_assessment(user_id)
    return a["results"]["score"]["total"] if a else None


# Session keys holding a guest's (not-signed-in) completed assessment.
GUEST_KEYS = ("guest_inputs", "guest_results", "guest_eval")


def complete_assessment(user, data, source):
    """The single completion pipeline used by BOTH assessment methods:
    run the deterministic engine, persist, generate weekly goals, register the
    streak check-in and evaluate achievements.

    Guests (user is None) run the SAME deterministic engine — nothing is
    simplified — but the result lives in the session instead of the database,
    and account-bound extras (goals, streaks, achievements) are skipped."""
    results = run_assessment(data)
    if user is None:
        st.session_state["guest_inputs"] = copy.deepcopy(data)
        st.session_state["guest_results"] = results
        st.session_state.pop("guest_eval", None)   # snapshot follows the data
        st.session_state["latest_results"] = results
        return None, results, []
    assessment_id = db.save_assessment(user["id"], data, results, source=source)
    if not db.goals_for_week(user["id"]):
        picked = pick_weekly_goals(data, results, 3)
        db.save_goals(user["id"], picked)   # central dedupe inside
    db.check_in(user["id"])
    new_achievements = ach.evaluate_after_assessment(user["id"])
    st.session_state["latest_results"] = results
    return assessment_id, results, new_achievements


def guest_assessment():
    """The guest's completed assessment ({'inputs', 'results'}) or None."""
    results = st.session_state.get("guest_results")
    if not results:
        return None
    return {"inputs": st.session_state.get("guest_inputs"), "results": results}


def clear_guest_assessment():
    for k in GUEST_KEYS:
        st.session_state.pop(k, None)


def adopt_guest_assessment(user):
    """Attach a completed guest assessment to a brand-new account so nothing
    the guest did is lost. Only runs against an account with NO history —
    never merges into an existing account's records. Returns True if adopted."""
    data = st.session_state.get("guest_inputs")
    results = st.session_state.get("guest_results")
    if not data or not results:
        return False
    if db.list_assessments(user["id"]):
        return False
    db.save_assessment(user["id"], data, results, source="questionnaire")
    if not db.goals_for_week(user["id"]):
        db.save_goals(user["id"], pick_weekly_goals(data, results, 3))
    db.check_in(user["id"])
    ach.evaluate_after_assessment(user["id"])
    st.session_state["latest_results"] = results
    clear_guest_assessment()
    return True


def reminder_banner(user):
    """Weekly/monthly reminder to keep data current (spec §14), snoozable."""
    if not user.get("reminders_enabled"):
        return
    if st.session_state.get("reminder_snoozed"):
        return
    if not db.list_assessments(user["id"]):
        return
    if db.streak_is_due(user["id"]):
        cadence = user.get("reminder_cadence", "weekly")
        with st.container(border=True):
            c1, c2, c3 = st.columns([5, 1.4, 1.2])
            c1.markdown(f"**Time for your {cadence} check-in.** Update what "
                        "changed (a new bill, new habits) — no need to redo the "
                        "whole assessment; your last answers are pre-filled.")
            pages = st.session_state.get("pages", {})
            if "assessment" in pages:
                with c2:
                    st.page_link(pages["assessment"], label="Update now",
                                 icon=":material/edit_note:")
            if c3.button("Snooze", key="snooze_reminder"):
                st.session_state["reminder_snoozed"] = True
                st.rerun()


def achievement_toast(codes):
    from achievements import ACHIEVEMENTS
    for code in codes:
        meta = ACHIEVEMENTS.get(code)
        if meta:
            st.toast(f"Achievement unlocked: **{meta['name']}**",
                     icon=":material/emoji_events:")


def render_achievement_cards(user_id, columns=4):
    """The one achievement component (Dashboard + Profile): a responsive grid
    of cards, each stating the name, an icon, how it is earned, its
    earned/locked state and progress where that is measurable."""
    earned = {a["code"]: a for a in db.get_achievements(user_id)}
    progress = ach.progress_for(user_id)

    if not earned:
        st.markdown(
            "You haven't earned any achievements yet — they unlock as you "
            "assess, improve and check in. Here's what you can work toward:")

    cols = st.columns(columns)
    for i, (code, meta) in enumerate(ach.ACHIEVEMENTS.items()):
        with cols[i % columns], st.container(border=True):
            got = earned.get(code)
            if got:
                st.markdown(
                    f"<div style='display:flex;justify-content:space-between;"
                    f"align-items:center'>{icon(meta['icon'], 26, '#2E9E63')}"
                    f"<span class='pill' style='font-size:.72rem;"
                    f"background:#d9f2e3;color:#1d8a4e;border-color:#c2e8d2'>"
                    f"{icon('check', 11, '#1d8a4e')} Earned</span></div>",
                    unsafe_allow_html=True)
                st.markdown(f"**{meta['name']}**")
                st.caption(f"{meta['desc']}  \n_{got['earned_at'][:10]}_")
            else:
                st.markdown(
                    f"<div style='display:flex;justify-content:space-between;"
                    f"align-items:center'>{icon(meta['icon'], 26, '#9bb0a8')}"
                    f"<span class='pill' style='font-size:.72rem;"
                    f"color:#7d8f88'>{icon('lock', 11, '#7d8f88')} "
                    f"Locked</span></div>", unsafe_allow_html=True)
                st.markdown(f"**{meta['name']}**")
                st.caption(meta.get("how", meta["desc"]))
                p = progress.get(code)
                if p and p["pct"] > 0:
                    st.progress(min(1.0, p["pct"] / 100), text=p["detail"])
