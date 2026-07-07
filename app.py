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
                   information, profile, community, settings, assistant)
from views.common import latest_score
from visuals import inject_theme, enhance_ui, scroll_top, user_chip

st.set_page_config(
    page_title="I/mpact — Environmental Impact Tracker",
    page_icon="🌍",
    layout="wide",
    initial_sidebar_state="expanded",
)

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
inject_theme(score)


def _goals_page():
    """Goals is a real navigation destination (stays highlighted in the
    sidebar); its content is the Dashboard's plan section, reached via the
    stable 'plan' anchor. The scroll flag is set on arrival in the sidebar
    page-change handler below, so in-page interactions don't re-scroll."""
    dashboard.render()


# -------------------------------------------------------------- page graph
pages = {
    "home": st.Page(home.render, title="Home", icon=":material/home:",
                    url_path="home", default=True),
    "account": st.Page(account.render, title="Sign in / Sign up",
                       icon=":material/person:", url_path="account"),
    "assessment": st.Page(assessment.render, title="Assessment",
                          icon=":material/edit_note:", url_path="assessment"),
    "chat": st.Page(chat_assessment.render, title="Chat Assessment",
                    icon=":material/forum:", url_path="chat"),
    "dashboard": st.Page(dashboard.render, title="Dashboard",
                         icon=":material/dashboard:", url_path="dashboard"),
    "goals": st.Page(_goals_page, title="Goals",
                     icon=":material/target:", url_path="goals"),
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
    "Improve": [pages["dashboard"], pages["goals"]],
    "Community": [pages["community"], pages["explore"]],
    "More": [pages["information"], pages["profile"], pages["settings"]],
})

# ----------------------------------------------------------------- sidebar
with st.sidebar:
    st.markdown("<div class='wordmark'>I/mpact</div>", unsafe_allow_html=True)
    st.caption("Measure · Understand · Improve")
    if ai.assistant_ready():
        st.caption("● Assistant ready")
    else:
        st.caption("○ Assistant offline")
        st.page_link(pages["settings"], label="Connect AI",
                     icon=":material/key:")

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
    user_chip(user, score)

nav.run()

# ---------------------------------------------- floating assistant FAB (§18)
assistant.render_floating(user)
