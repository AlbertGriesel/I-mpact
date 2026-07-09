"""Sign up / sign in (spec §5). Passwords are salted PBKDF2 hashes; privacy
defaults to private and public sharing is opt-in consent."""

import streamlit as st

import database as db
import avatar as av
from views.common import (adopt_guest_assessment, clear_guest_assessment,
                          guest_assessment)
from visuals import LOGO_FULL

# A few friendly starter Sprouts to pick at sign-up; fully customisable later
# in Settings (spec §11).
_STARTERS = {
    "Fern": {"skin": av.SKINS[1], "hair": av.HAIRS[9], "hair_style": "short",
             "top": av.TOPS[0], "accessory": "none"},
    "Marigold": {"skin": av.SKINS[2], "hair": av.HAIRS[4], "hair_style": "long",
                 "top": av.TOPS[3], "accessory": "flower"},
    "River": {"skin": av.SKINS[4], "hair": av.HAIRS[0], "hair_style": "curly",
              "top": av.TOPS[1], "accessory": "glasses"},
    "Ash": {"skin": av.SKINS[0], "hair": av.HAIRS[5], "hair_style": "wavy",
            "top": av.TOPS[2], "accessory": "cap"},
}


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
    st.caption("Tip: on your Profile you can **create a personal avatar from a "
               "photo** — or keep the illustrated Sprout. Entirely optional.")


def render():
    user = st.session_state.get("user")

    # -------- signed in: one compact card, no leftover sign-in furniture ----
    # (§2: the page sizes to its actual content and the scenery shows around
    # it — no giant white sheet for what is a two-line status.)
    if user:
        if st.session_state.get("just_signed_up"):
            _c = st.columns([1, 2, 1])[1]
            _c.image(LOGO_FULL, width=160)
            st.title("Your account")
            _post_signup(user)
            return
        mid = st.columns([1, 1.5, 1])[1]
        with mid, st.container(key="band_account_in"):
            face = av.avatar_html(user, tier="GOOD", size=96)
            st.markdown(f"<div style='text-align:center'>{face}</div>",
                        unsafe_allow_html=True)
            st.markdown(f"<h2 style='text-align:center;margin:.2rem 0 0'>"
                        f"{user['display_name']}</h2>"
                        f"<p style='text-align:center;color:#5c7069;margin:0'>"
                        f"{user['email']}</p>", unsafe_allow_html=True)
            st.caption("You're signed in — use the sidebar to get around; "
                       "everything's one click away.")
            pages = st.session_state.get("pages", {})
            if "dashboard" in pages:
                st.page_link(pages["dashboard"], label="Open your dashboard",
                             icon=":material/dashboard:")
            if st.button("Sign out", use_container_width=True,
                         key="btn_signout"):
                st.session_state.pop("user", None)
                for k in ("assessment_data", "chat_history", "chat_data",
                          "assistant_history", "assistant_proposals",
                          "assistant_open", "latest_results", "wizard_step",
                          "assessment_returning", "water_bill_sig",
                          "elec_bill_sig", "water_extraction",
                          "elec_extraction"):
                    st.session_state.pop(k, None)
                # a fresh guest must never see the previous account's data
                clear_guest_assessment()
                import widgets as w
                w.clear_all()
                st.rerun()
        return

    # -------- logged out: a centred, content-sized account card -------------
    _c = st.columns([1, 2, 1])[1]
    _c.image(LOGO_FULL, width=160)
    st.title("Your account")

    if guest_assessment():
        st.info("Your guest assessment is safe — it stays available while "
                "you're here, and creating an account below saves it "
                "permanently.", icon=":material/eco:")

    tab_in, tab_up = st.tabs(["Sign in", "Create account"])

    with tab_in:
        # §2: a sign-in form is small — centre it and let the scenery breathe
        # at the sides instead of stretching a near-empty white row.
        mid_in = st.columns([1, 1.6, 1])[1]
        with mid_in, st.form("signin"):
            email = st.text_input("Email")
            password = st.text_input("Password", type="password")
            ok = st.form_submit_button("Sign in", type="primary",
                                       use_container_width=True)
        if ok:
            user = db.verify_login(email, password)
            if user and not user["is_demo"]:
                _login(user)
            else:
                mid_in.error("Email or password incorrect.")

    with tab_up:
        mid_up = st.columns([1, 2.6, 1])[1]
        with mid_up, st.form("signup"):
            # §4: account type is an explicit, visible choice — not a hidden
            # dropdown. It shapes the whole experience (assessment questions,
            # benchmarks, advice), so it comes first.
            st.markdown("**What are you tracking?**")
            default_type = st.session_state.get("guest_account_type", "personal")
            account_type = st.radio(
                "Account type", ["personal", "business"],
                index=0 if default_type == "personal" else 1,
                horizontal=True, label_visibility="collapsed",
                format_func=lambda t: ("🏠  Personal — a household"
                                       if t == "personal"
                                       else "🏢  Business — an organisation"),
                help="Personal compares you to household benchmarks; Business "
                     "asks sector-appropriate questions and compares you to "
                     "per-employee / per-m² sector benchmarks. You can't change "
                     "this later, so pick the one that fits.")
            st.caption("Both use the same measurement engine and give the same "
                       "kind of results — just tuned to who you are.")
            st.divider()
            name = st.text_input("Display name" if account_type == "personal"
                                 else "Your name or the business name")
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
            st.markdown("**Pick a starter Sprout** — your character in the app "
                        "(customise it any time in Settings)")
            def _starter_card(nm, cfg):
                face = av.svg(cfg, tier="GOOD", size=64, halo=False,
                              animate=False)
                return (f"<div style='text-align:center'>{face}"
                        f"<div style='font-weight:700;font-size:.8rem;"
                        f"color:#5c7069'>{nm}</div></div>")
            gallery = "".join(_starter_card(nm, cfg)
                              for nm, cfg in _STARTERS.items())
            st.markdown(
                f"<div style='display:flex;gap:1.1rem;justify-content:center;"
                f"margin:.2rem 0 .5rem'>{gallery}</div>", unsafe_allow_html=True)
            starter = st.radio("Starter", list(_STARTERS), horizontal=True,
                               label_visibility="collapsed")
            avatar = av.config_to_str(_STARTERS[starter])
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
                                      reminder_cadence=cadence, avatar=avatar,
                                      account_type=account_type)
                st.session_state["just_signed_up"] = True
                _login(user, adopt_guest=True)

    st.divider()
    from views.common import privacy_note
    privacy_note("signup")
