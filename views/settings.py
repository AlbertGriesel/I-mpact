"""Settings (spec §19): privacy & consent controls, reminder cadence, unit
period default, account details and AI connection."""

import json

import streamlit as st

import ai
import database as db
from views.common import require_login

PUBLIC_FIELD_CHOICES = ["score", "water", "electricity", "carbon", "streak",
                        "achievements"]
AVATARS = ["🌱", "🌻", "🌳", "🐝", "🦉", "🐬", "⛰️", "☀️"]


def render():
    user = require_login("Sign in to manage settings.")
    user = db.get_user(user["id"])
    st.session_state["user"] = user
    st.title("Settings")

    # ------------------------------------------------------------------ AI
    st.subheader("AI connection")
    available, msg = ai.ai_status()
    if available:
        st.success(msg)
        if st.button("Test the connection", key="btn_ai_test"):
            with st.spinner("Pinging Claude…"):
                ok, result = ai.test_connection()
            (st.success if ok else st.error)(result)
    else:
        st.warning(msg)
        st.markdown(
            "Paste an API key below — the app auto-detects which service it's "
            "from. Two options:\n\n"
            "- **Free — Google Gemini** (recommended to start): create a key at "
            "[aistudio.google.com/apikey](https://aistudio.google.com/apikey), "
            "no card needed. Keys start with `AQ.` (or older `AIza`). Generous "
            "free tier (~1,500 requests/day) covering bill reading, chat, "
            "analysis and planning.\n"
            "- **Paid — Anthropic Claude** (highest quality): create a key at "
            "[console.anthropic.com](https://console.anthropic.com/settings/keys). "
            "Keys start with `sk-ant-`.\n\n"
            "Whichever you paste is stored **only on this machine** in "
            "`.streamlit/secrets.toml` (git-ignored) and sent nowhere except "
            "that provider's API.")
        with st.form("connect_ai"):
            key_in = st.text_input("API key (Gemini AQ.… / AIza… or Anthropic sk-ant-…)",
                                   type="password", placeholder="AQ.… or sk-ant-…")
            connect = st.form_submit_button("Connect AI", type="primary")
        if connect:
            ok, result = ai.save_api_key(key_in)
            if not ok:
                st.error(result)
            else:
                with st.spinner("Verifying with a live request…"):
                    ok2, test_msg = ai.test_connection()
                if ok2:
                    st.success(f"{result}  \n{test_msg}")
                    st.rerun()
                else:
                    st.error(f"Key saved, but the test call failed: {test_msg}")
    st.caption("Without a key the questionnaire, calculator, dashboard, goals "
               "and community features all keep working; AI chat, bill "
               "reading, analysis and the planner switch to clear fallbacks.")

    st.divider()

    # ------------------------------------------------------------- account
    st.subheader("Account")
    c1, c2 = st.columns(2)
    with c1:
        name = st.text_input("Display name", value=user["display_name"])
    with c2:
        avatar = st.selectbox("Avatar", AVATARS,
                              index=(AVATARS.index(user["avatar"])
                                     if user["avatar"] in AVATARS else 0))
    country = st.text_input("Country", value=user.get("country") or "South Africa")

    # ------------------------------------------------------------- privacy
    st.subheader("Privacy and consent")
    public = st.toggle("Public account",
                       value=(user["privacy"] == "public"),
                       help="Public: the summary stats you approve below appear "
                            "on your profile, Explore and the Leaderboard. "
                            "Bills, raw household data and private chats are "
                            "NEVER public either way.")
    fields = json.loads(user["public_fields"] or "[]")
    if public:
        fields = st.multiselect(
            "Stats you approve for public display", PUBLIC_FIELD_CHOICES,
            default=[f for f in fields if f in PUBLIC_FIELD_CHOICES])
    story_consent = st.toggle(
        "Allow my submitted stories to be featured (separate consent)",
        value=bool(user["story_consent"]))
    if not public and (fields or user["privacy"] == "public"):
        st.caption("Switching to private hides your profile, stories and "
                   "leaderboard entries immediately.")

    # ----------------------------------------------------------- reminders
    st.subheader("Reminders and rhythm")
    c1, c2, c3 = st.columns(3)
    with c1:
        cadence = st.radio("Check-in cadence", ["weekly", "monthly"],
                           index=0 if user["reminder_cadence"] == "weekly" else 1,
                           horizontal=True,
                           help="Also sets your streak rhythm.")
    with c2:
        reminders_on = st.toggle("In-app reminders",
                                 value=bool(user["reminders_enabled"]))
    with c3:
        unit_period = st.selectbox("Default statistics period",
                                   ["day", "week", "month", "year"],
                                   index=["day", "week", "month", "year"].index(
                                       user.get("unit_period", "month")))

    if st.button("Save settings", type="primary", key="btn_save_settings"):
        db.update_user(user["id"], display_name=name.strip() or user["display_name"],
                       avatar=avatar, country=country,
                       privacy="public" if public else "private",
                       public_fields=fields if public else [],
                       story_consent=1 if story_consent else 0,
                       reminder_cadence=cadence,
                       reminders_enabled=1 if reminders_on else 0,
                       unit_period=unit_period)
        st.session_state["user"] = db.get_user(user["id"])
        st.success("Saved.")
        st.rerun()

    # ---------------------------------------------------------------- data
    st.subheader("Your data")
    bills = db.user_bills(user["id"])
    st.caption(f"{len(bills)} uploaded bill(s) stored privately on this "
               "server, visible only to you.")
    assessments = db.list_assessments(user["id"])
    if assessments:
        st.download_button(
            "Download my data (JSON)",
            data=json.dumps({"user": {k: user[k] for k in
                                      ("email", "display_name", "created_at")},
                             "assessments": assessments}, indent=1),
            file_name="impact_data.json", mime="application/json")
