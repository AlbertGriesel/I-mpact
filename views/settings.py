"""Settings (spec §19): privacy & consent controls, reminder cadence, unit
period default, account details and AI connection."""

import json

import streamlit as st

import ai
import database as db
import avatar as av
from views.common import require_login, latest_score, privacy_note
from visuals import env_tier

PUBLIC_FIELD_CHOICES = ["score", "water", "electricity", "carbon", "streak",
                        "achievements"]

# Human-readable names for the small, curated avatar palettes (spec §11 —
# emotional ownership, not a complicated character creator).
_SKIN_NAMES = ["Porcelain", "Light", "Tan", "Amber", "Brown", "Deep"]
_HAIR_NAMES = ["Black", "Brown", "Chestnut", "Ginger", "Blonde", "Silver",
               "White", "Violet", "Rose", "Leaf"]
_TOP_NAMES = ["Leaf green", "Sky blue", "Grape", "Sunlight", "Coral", "Teal",
              "Rose"]
_STYLE_NAMES = {"short": "Short", "curly": "Curly", "bun": "Bun", "long": "Long",
                "wavy": "Wavy", "buzz": "Buzz", "bald": "None"}
_ACC_NAMES = {"none": "None", "glasses": "Glasses", "sunhat": "Sun hat",
              "flower": "Flower", "cap": "Cap"}


def _pick(label, names, values, current, key):
    """A named selectbox over a colour/option palette, returning the value."""
    idx = values.index(current) if current in values else 0
    chosen = st.selectbox(label, names, index=idx, key=key)
    return values[names.index(chosen)]


def _avatar_customizer(user):
    """Live Sprout customiser: choices on the right, a reactive preview on the
    left that reflects both the look AND the user's current impact mood."""
    cfg = av.config_from_user(user)
    tier = env_tier(latest_score(user["id"]))
    prev, ctrl = st.columns([1, 1.6], gap="large")
    with ctrl:
        c1, c2 = st.columns(2)
        with c1:
            skin = _pick("Skin", _SKIN_NAMES, av.SKINS, cfg["skin"], "av_skin")
            style = st.selectbox(
                "Hair", list(_STYLE_NAMES.values()),
                index=av.HAIR_STYLES.index(cfg["hair_style"]),
                key="av_style")
            style = av.HAIR_STYLES[list(_STYLE_NAMES.values()).index(style)]
        with c2:
            hair = _pick("Hair colour", _HAIR_NAMES, av.HAIRS, cfg["hair"],
                         "av_hair")
            top = _pick("Clothing", _TOP_NAMES, av.TOPS, cfg["top"], "av_top")
        acc = st.selectbox(
            "Accessory", list(_ACC_NAMES.values()),
            index=av.ACCESSORIES.index(cfg["accessory"]), key="av_acc")
        acc = av.ACCESSORIES[list(_ACC_NAMES.values()).index(acc)]
    new_cfg = {"skin": skin, "hair": hair, "hair_style": style, "top": top,
               "accessory": acc}
    with prev:
        st.markdown(
            f"<div style='display:flex;justify-content:center'>"
            f"{av.svg(new_cfg, tier=tier, size=150)}</div>",
            unsafe_allow_html=True)
        st.caption("Your character reacts to your impact — its mood and the "
                   "little habitat around it grow as your score improves.")
    return new_cfg


def render():
    user = require_login("Sign in to manage settings.")
    user = db.get_user(user["id"])
    st.session_state["user"] = user
    st.title("Settings")

    # ------------------------------------------------------------------ AI
    st.subheader("AI connection")
    available, msg = ai.ai_status()
    if available:
        # Standing status is a quiet caption (matches the sidebar's "● ready"),
        # NOT a success alert — so a live test shows exactly ONE success box,
        # never two green confirmations at once. A just-connected message is
        # shown once, then replaced by the caption on the next run.
        just_connected = st.session_state.pop("ai_connected_msg", None)
        if just_connected:
            st.success(just_connected)
        else:
            st.caption(f"● {msg}")
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
                    # hand the single confirmation to the rerun (shown once
                    # in the "available" branch above) — no duplicate box
                    st.session_state["ai_connected_msg"] = \
                        f"{result}  \n{test_msg}"
                    st.rerun()
                else:
                    st.error(f"Key saved, but the test call failed: {test_msg}")
    st.caption("Without a key the questionnaire, calculator, dashboard, goals "
               "and community features all keep working; AI chat, bill "
               "reading, analysis and the planner switch to clear fallbacks.")

    st.divider()

    # ------------------------------------------------------------- account
    st.subheader("Account")
    name = st.text_input("Display name", value=user["display_name"])
    country = st.text_input("Country", value=user.get("country") or "South Africa")

    st.markdown("**Your Sprout**")
    st.caption("Make the character your own — it's how you appear across the "
               "app and how your progress comes to life.")
    avatar_cfg = _avatar_customizer(user)
    avatar = av.config_to_str(avatar_cfg)

    # --------------------------------------------------------- appearance
    st.subheader("Appearance")
    cur_theme = st.session_state.get("theme", user.get("theme") or "light")
    theme_choice = st.radio(
        "Theme", ["light", "dark"],
        index=0 if cur_theme == "light" else 1, horizontal=True,
        format_func=lambda t: "☀️  Light" if t == "light" else "🌙  Dark",
        help="Also available any time from the sidebar. Your choice is saved "
             "to your account.")
    if theme_choice != cur_theme:
        st.session_state["theme"] = theme_choice
        db.update_user(user["id"], theme=theme_choice)
        st.rerun()

    # ------------------------------------------------------------- privacy
    st.subheader("Privacy and consent")
    privacy_note("settings")
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
