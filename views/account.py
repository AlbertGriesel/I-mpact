"""Sign up / sign in (spec §5). Passwords are salted PBKDF2 hashes; privacy
defaults to private and public sharing is opt-in consent."""

import streamlit as st

import database as db
from views.common import (adopt_guest_assessment, clear_guest_assessment,
                          guest_assessment)

AVATARS = ["🌱", "🌻", "🌳", "🐝", "🦉", "🐬", "⛰️", "☀️"]


def _login(user, adopt_guest=False):
    st.session_state["user"] = user
    st.session_state.pop("reminder_snoozed", None)
    if adopt_guest:
        # brand-new account: carry the guest assessment over (safe: the
        # account has no history yet, so nothing can be corrupted or merged)
        st.session_state["guest_adopted"] = adopt_guest_assessment(user)
    else:
        # existing account: guest session data must never attach to it
        clear_guest_assessment()
    st.rerun()


def _post_signup(user):
    """Success confirmation with an unmissable next action (one screen, no
    hunting through the sidebar)."""
    st.success(f"Account created — welcome, **{user['display_name']}**! "
               "You're signed in and ready to go.")
    pages = st.session_state.get("pages", {})
    if st.session_state.get("guest_adopted"):
        st.info("Your guest assessment came with you — it's saved to your "
                "new account, along with your first weekly goals.")
    if st.button("Start your assessment", type="primary",
                 use_container_width=True, key="btn_post_signup_assessment"):
        st.session_state.pop("just_signed_up", None)
        st.session_state.pop("guest_adopted", None)
        st.switch_page(pages["assessment"])
    if st.session_state.get("guest_adopted") and "dashboard" in pages:
        st.page_link(pages["dashboard"], label="…or see your results dashboard",
                     icon=":material/dashboard:")
    st.caption("It takes under 10 minutes — your dashboard, weekly plan and "
               "daisy all come alive right after.")


def render():
    st.title("Your account")
    user = st.session_state.get("user")
    if user:
        if st.session_state.get("just_signed_up"):
            _post_signup(user)
            return
        st.success(f"Signed in as **{user['display_name']}** ({user['email']}).")
        st.caption("Use the sidebar to get around — everything's one click "
                   "away.")
        if st.button("Sign out", use_container_width=False):
            st.session_state.pop("user", None)
            for k in ("assessment_data", "chat_history", "chat_data",
                      "assistant_history", "assistant_proposals",
                      "assistant_open", "latest_results", "wizard_step",
                      "assessment_returning", "water_bill_sig",
                      "elec_bill_sig", "water_extraction", "elec_extraction"):
                st.session_state.pop(k, None)
            # a fresh guest must never see the previous account's data
            clear_guest_assessment()
            import widgets as w
            w.clear_all()
            st.rerun()
        return

    if guest_assessment():
        st.info("Your guest assessment is safe — it stays available while "
                "you're here, and creating an account below saves it "
                "permanently.", icon=":material/eco:")

    tab_in, tab_up = st.tabs(["Sign in", "Create account"])

    with tab_in:
        with st.form("signin"):
            email = st.text_input("Email")
            password = st.text_input("Password", type="password")
            ok = st.form_submit_button("Sign in", type="primary",
                                       use_container_width=True)
        if ok:
            user = db.verify_login(email, password)
            if user and not user["is_demo"]:
                _login(user)
            else:
                st.error("Email or password incorrect.")

    with tab_up:
        with st.form("signup"):
            name = st.text_input("Display name")
            email = st.text_input("Email", key="su_email")
            password = st.text_input("Password (min 8 characters)",
                                     type="password", key="su_pw")
            c1, c2 = st.columns(2)
            with c1:
                privacy = st.radio(
                    "Account privacy", ["private", "public"], horizontal=True,
                    help="Private: results are visible only to you. Public: the "
                         "summary stats you approve can appear on Explore and "
                         "the Leaderboard. Raw data, bills and chats stay "
                         "private either way. Change any time in Settings.")
            with c2:
                cadence = st.radio(
                    "Check-in reminders", ["weekly", "monthly"], horizontal=True,
                    help="Sets your reminder cadence and your streak rhythm.")
            avatar = st.selectbox("Pick an avatar", AVATARS)
            agreed = st.checkbox(
                "I understand my bills, raw household data and private chats "
                "are never shown publicly, and public sharing needs my "
                "explicit consent.")
            ok = st.form_submit_button("Create account", type="primary",
                                       use_container_width=True)
        if ok:
            if not name.strip() or "@" not in email or len(password) < 8:
                st.error("Please provide a name, a valid email and a password "
                         "of at least 8 characters.")
            elif not agreed:
                st.error("Please confirm the privacy note.")
            elif db.get_user_by_email(email):
                st.error("That email already has an account — sign in instead.")
            else:
                user = db.create_user(email, name, password, privacy=privacy,
                                      reminder_cadence=cadence, avatar=avatar)
                st.session_state["just_signed_up"] = True
                _login(user, adopt_guest=True)

    st.divider()
    st.caption("Your data stays in a local database. AI features call the "
               "Anthropic API with your inputs (never your password) to read "
               "bills and to advise you — the API key lives server-side only.")
