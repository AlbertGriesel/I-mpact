"""
I/mpact — AI Environmental Impact Tracker
=========================================

A friendly, AI-powered platform for measuring, understanding, planning and
reducing personal environmental impact, built for South African and broader
African households.

    streamlit run app.py

Architecture (per the project specification):
  * schema.py + calculations.py — ONE schema and ONE deterministic engine
    shared by the guided questionnaire and the AI conversation.
  * ai.py — a pluggable LLM layer (free Gemini tier or Anthropic) powers
    conversational collection, bill image extraction, the automatic dashboard
    evaluation and the floating assistant; it never performs the arithmetic.
  * database.py — accounts, history, goals, achievements, streaks, stories.
  * visuals.py — the reactive daisy-on-Earth mascot, wallpaper, icon set and
    browser enhancements, embedded as web components.
"""

import streamlit as st

import ai
import database as db
from views import (home, account, assessment, chat_assessment, dashboard,
                   information, profile, community, settings, assistant,
                   offsets, tutorial)
from views.common import latest_score
from visuals import (inject_theme, enhance_ui, scroll_top, user_chip,
                     LOGO_FULL, LOGO_ICON)

st.set_page_config(
    page_title="I/mpact — Environmental Impact Tracker",
    page_icon=LOGO_ICON,
    layout="wide",
    initial_sidebar_state="expanded",
)

# Brand mark in the top-left (above the sidebar nav); the compact icon shows
# when the sidebar is collapsed.
try:
    st.logo(LOGO_FULL, icon_image=LOGO_ICON, size="large")
except Exception:  # noqa: BLE001 — older Streamlit without st.logo / size arg
    try:
        st.logo(LOGO_FULL, icon_image=LOGO_ICON)
    except Exception:  # noqa: BLE001
        pass

# ---------------------------------------------------------------- bootstrap
db.init_db()
if "demo_seeded" not in st.session_state:
    db.seed_demo_data()
    st.session_state["demo_seeded"] = True

# Re-validate the session user each run: picks up settings changes and drops
# sessions whose account no longer exists.
user = st.session_state.get("user")
if user:
    user = db.get_user(user["id"])
    if user is None:
        st.session_state.pop("user", None)
    else:
        st.session_state["user"] = user
if user:
    score = latest_score(user["id"])
elif st.session_state.get("guest_results"):
    # guests get the same reactive theme from their session-held results
    score = st.session_state["guest_results"]["score"]["total"]
else:
    score = None

# ------------------------------------------------------------------ theme
# Resolve the active theme ONCE (single source of truth): session wins, then
# the saved account preference, else light. Persisted for guests in session
# and for users in the DB (spec §15). Theme and environmental score are
# independent systems (spec §17).
if "theme" not in st.session_state:
    st.session_state["theme"] = (user.get("theme") if user else None) or "light"
theme = st.session_state["theme"]
inject_theme(score, theme)


def _goals_page():
    """Goals is a real navigation destination (stays highlighted in the
    sidebar). It renders the shared dashboard in GOALS-FIRST mode, so the
    weekly plan shows at the top of the page immediately — no load-at-top-then-
    scroll (§8). Same components and goal logic as the dashboard, no duplicate."""
    dashboard.render(goals_first=True)


# -------------------------------------------------------------- page graph
pages = {
    "home": st.Page(home.render, title="Home", icon=":material/home:",
                    url_path="home", default=True),
    "account": st.Page(account.render, title="Sign in / Sign up",
                       icon=":material/person:", url_path="account"),
    "assessment": st.Page(assessment.render, title="Assessment",
                          icon=":material/edit_note:", url_path="assessment"),
    "chat": st.Page(chat_assessment.render, title="AI Assessment",
                    icon=":material/forum:", url_path="chat"),
    "dashboard": st.Page(dashboard.render, title="Dashboard",
                         icon=":material/dashboard:", url_path="dashboard"),
    "goals": st.Page(_goals_page, title="Goals",
                     icon=":material/target:", url_path="goals"),
    "offsets": st.Page(offsets.render, title="Carbon Offsets",
                       icon=":material/forest:", url_path="offsets"),
    "community": st.Page(community.render_leaderboard, title="Leaderboard",
                         icon=":material/social_leaderboard:",
                         url_path="community"),
    "explore": st.Page(community.render_explore, title="Explore",
                       icon=":material/travel_explore:", url_path="explore"),
    "information": st.Page(information.render, title="Information",
                           icon=":material/menu_book:", url_path="information"),
    "profile": st.Page(profile.render, title="Profile",
                       icon=":material/account_circle:", url_path="profile"),
    "settings": st.Page(settings.render, title="Settings",
                        icon=":material/settings:", url_path="settings"),
}
st.session_state["pages"] = pages

nav = st.navigation({
    "Start": [pages["home"], pages["account"]],
    "Measure": [pages["assessment"], pages["chat"]],
    "Improve": [pages["dashboard"], pages["goals"], pages["offsets"]],
    "Community": [pages["community"], pages["explore"]],
    "More": [pages["information"], pages["profile"], pages["settings"]],
})

# ----------------------------------------------------------------- sidebar
with st.sidebar:
    st.caption("Measure · Understand · Improve")
    if ai.assistant_ready():
        st.caption("● Assistant ready")
    else:
        st.caption("○ Assistant offline")
        st.page_link(pages["settings"], label="Connect AI",
                     icon=":material/key:")

    # appearance: Light / Dark (spec §14–§17). Available everywhere, including
    # logged out and mid guest assessment; the current theme's button is
    # disabled so the active choice is obvious.
    st.caption("Appearance")
    tcol1, tcol2 = st.columns(2)

    def _set_theme(t):
        st.session_state["theme"] = t
        if user:
            db.update_user(user["id"], theme=t)
        st.rerun()

    if tcol1.button("Light", use_container_width=True,
                    disabled=(theme == "light"), key="theme_light"):
        _set_theme("light")
    if tcol2.button("Dark", use_container_width=True,
                    disabled=(theme == "dark"), key="theme_dark"):
        _set_theme("dark")

    # browser enhancements: hold-to-repeat steppers, select-all on focus,
    # searchable long dropdowns / locked short ones. Runs once per page load.
    enhance_ui()

    # scroll to top on page change or wizard step change — unless a jump to
    # the Goals anchor is pending (it would fight the anchor scroll)
    if st.session_state.get("_last_page") != nav.title:
        st.session_state["_last_page"] = nav.title
        st.session_state["_scroll_top"] = True
        # arriving on Goals: jump to the plan anchor exactly once
        if nav.title == "Goals":
            st.session_state["scroll_to_goals"] = True
        # the post-sign-up confirmation only lives on the account page
        if nav.title != "Sign in / Sign up":
            st.session_state.pop("just_signed_up", None)
            st.session_state.pop("guest_adopted", None)
    if st.session_state.pop("_scroll_top", False) and \
            not st.session_state.get("scroll_to_goals"):
        scroll_top()

# ------------------------------------------------- top-right user chip (§17)
if user:
    user_chip(user, score, theme)

nav.run()

# ---------------------------------------------- floating assistant FAB (§18)
assistant.render_floating(user)

# ------------------------------------------- first-time product tour (§1)
# Rendered last so the sidebar nav and the assistant FAB it points at already
# exist in the DOM; shows once per new user/guest, then persists as done.
tutorial.render(user)
