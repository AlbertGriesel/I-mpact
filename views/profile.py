"""Profile page (spec §5.3): identity, membership duration, score, metric
summaries, streaks, achievements and goal history."""

from datetime import datetime

import streamlit as st

import ai
import database as db
import avatar as av
from views.common import require_login, render_achievement_cards, privacy_note
from visuals import (render_mascot, score_ring, kpi_card, pill, icon,
                     env_tier, TIER_LABEL, GREEN)


_AV_UPLOAD_CSS = """
<style>
.av-uploadhead{background:rgba(126,200,227,0.14);border:1.5px dashed rgba(46,158,99,.45);
  border-radius:22px;padding:1.1rem 1.2rem;margin:.2rem 0 .6rem;text-align:center}
.av-uploadhead .t{font-family:'Baloo 2',sans-serif;font-weight:800;color:#1B5E3B;
  font-size:1.15rem;margin:.35rem 0 .15rem}
.av-uploadhead .s{color:#4a5f57;font-size:.92rem;line-height:1.45}
.st-key-av_upwrap [data-testid="stFileUploaderDropzone"]{border-radius:18px;
  background:rgba(255,255,255,0.6);border:1px solid rgba(46,158,99,.25)}
</style>
"""


def _mime_of(name):
    ext = name.lower().rsplit(".", 1)[-1]
    return "image/jpeg" if ext in ("jpg", "jpeg") else f"image/{ext}"


def _avatar_reset(*keys):
    for k in ("av_src", "av_src_name", "avatar_preview", "avatar_error", *keys):
        st.session_state.pop(k, None)


def _avatar_section(user, tier):
    """Create-avatar-from-photo (spec §5): an obvious, friendly, staged flow —
    upload → preview the source (replace/remove) → generate → preview the
    result → save / regenerate / different photo / cancel. Uploading is
    optional; the illustrated Sprout is always available. A failed or unwanted
    generation never replaces the current avatar (§20)."""
    import base64
    st.markdown(_AV_UPLOAD_CSS, unsafe_allow_html=True)
    st.subheader("Your avatar")
    # The single primary avatar is shown once at the top of the page (§6); this
    # section holds the controls only — no duplicate persistent avatar image.
    if True:
        if not ai.avatar_generation_ready():
            st.info("Create a personalised avatar from a photo by adding a free "
                    "Google Gemini key under Settings → AI connection. Until "
                    "then you're using the illustrated Sprout — customise it "
                    "(skin, hair, accessories) in Settings. No photo required.")
            return

        preview = st.session_state.get("avatar_preview")
        src = st.session_state.get("av_src")

        # ---- Step 3: generated avatar preview → decide ----
        if preview is not None:
            st.markdown("**Here's your avatar** — happy with it?")
            pc1, pc2 = st.columns(2)
            with pc1:
                st.caption("New avatar")
                st.image(preview, width=160)
            with pc2:
                st.caption("Current")
                st.markdown(av.avatar_html(user, tier=tier, size=150),
                            unsafe_allow_html=True)
            st.caption("Once saved, it keeps this face and gains its eco "
                       "surroundings as your score improves.")
            b1, b2 = st.columns(2)
            if b1.button("Save avatar", type="primary", use_container_width=True,
                         key="av_save"):
                db.save_avatar_photo(user["id"], preview)
                st.session_state["user"] = db.get_user(user["id"])
                _avatar_reset("av_upkey")
                st.toast("Avatar saved.", icon=":material/check_circle:")
                st.rerun()
            if b2.button("Regenerate", use_container_width=True, key="av_regen"):
                with st.spinner("Creating another version…"):
                    ok, res = ai.generate_avatar(src, st.session_state.get(
                        "av_src_mime", "image/png")) if src else (False, "")
                if ok:
                    st.session_state["avatar_preview"] = res
                else:
                    st.session_state["avatar_error"] = res or "Couldn't regenerate."
                    st.session_state.pop("avatar_preview", None)
                st.rerun()
            b3, b4 = st.columns(2)
            if b3.button("Upload a different photo", use_container_width=True,
                         key="av_diff"):
                _avatar_reset()
                st.session_state["av_upkey"] = st.session_state.get("av_upkey", 0) + 1
                st.rerun()
            if b4.button("Cancel — keep my current avatar",
                         use_container_width=True, key="av_cancel"):
                _avatar_reset("av_upkey")
                st.rerun()
            return

        # ---- Step 2: source photo uploaded → preview, replace/remove, generate ----
        if src is not None:
            st.markdown("**Check your photo, then create your avatar**")
            pc1, pc2 = st.columns([1, 1.6])
            with pc1:
                st.image(src, width=150, caption="Your photo")
            with pc2:
                st.markdown("We'll turn this into a **stylised illustrated "
                            "avatar** that keeps your recognisable features — "
                            "not a photo.")
                privacy_note("upload")
            g1, g2 = st.columns([1.4, 1])
            if g1.button("Create my avatar", type="primary",
                         use_container_width=True, key="av_generate"):
                with st.spinner("Creating your avatar…"):
                    ok, res = ai.generate_avatar(
                        src, st.session_state.get("av_src_mime", "image/png"))
                if ok:
                    st.session_state["avatar_preview"] = res
                    st.session_state.pop("avatar_error", None)
                else:
                    st.session_state["avatar_error"] = res
                st.rerun()
            if g2.button("Remove photo", use_container_width=True,
                         key="av_remove"):
                _avatar_reset()
                st.session_state["av_upkey"] = st.session_state.get("av_upkey", 0) + 1
                st.rerun()
            if st.session_state.get("avatar_error"):
                st.error(st.session_state["avatar_error"])
            return

        # ---- Step 1: the friendly, illustrated area — upload OR selfie ----
        st.markdown(
            f"<div class='av-uploadhead'>{icon('users', 30, GREEN)}"
            "<div class='t'>Create your personal avatar</div>"
            "<div class='s'>Upload a photo or take a selfie, and we'll turn it "
            "into an illustrated character for your environmental journey.</div>"
            "</div>", unsafe_allow_html=True)
        upkey = st.session_state.get("av_upkey", 0)
        tab_up, tab_cam = st.tabs(["📷  Upload a photo", "🤳  Take a selfie"])
        with tab_up, st.container(key="av_upwrap"):
            up = st.file_uploader(
                "Choose a clear, front-facing photo (PNG/JPG/WebP, up to ~10 MB)",
                type=["png", "jpg", "jpeg", "webp"],
                key=f"av_uploader_{upkey}")
            if up is not None:
                st.session_state["av_src"] = up.getvalue()
                st.session_state["av_src_name"] = up.name
                st.session_state["av_src_mime"] = _mime_of(up.name)
                st.rerun()
        with tab_cam:
            cam = st.camera_input("Take a selfie", key=f"av_camera_{upkey}")
            if cam is not None:
                st.session_state["av_src"] = cam.getvalue()
                st.session_state["av_src_name"] = "selfie.jpg"
                st.session_state["av_src_mime"] = getattr(cam, "type",
                                                          "image/jpeg")
                st.rerun()
        privacy_note("upload")
        st.caption("Prefer not to use a photo? That's fine — you can use and "
                   "customise the illustrated **Sprout** character in Settings "
                   "instead. A photo is completely optional.")
        if av.has_photo(user):
            if st.button("Switch back to my Sprout character",
                         key="avatar_to_sprout"):
                db.use_sprout_avatar(user["id"])
                st.session_state["user"] = db.get_user(user["id"])
                st.rerun()


def render():
    user = require_login("Sign in to see your profile.")
    fresh = db.get_user(user["id"])  # settings may have changed
    st.session_state["user"] = fresh
    user = fresh

    assessments = db.list_assessments(user["id"])
    latest = assessments[-1] if assessments else None
    streak = db.get_streak(user["id"])
    gstats = db.goal_stats(user["id"])

    score = latest["results"]["score"]["total"] if latest else None
    tier = env_tier(score)

    # ---- identity band: the ONE primary avatar on this page (§6) ----
    id_band = st.container(key="band_profile_id")
    with id_band:
        c1, c2, c3 = st.columns([1, 1.6, 1])
    with c1:
        label = (TIER_LABEL[tier] if score is not None
                 else ("Your avatar" if av.has_photo(user) else "Your Sprout"))
        st.markdown(
            f"<div style='display:flex;flex-direction:column;align-items:center'>"
            f"{av.avatar_html(user, tier=tier, size=170)}"
            f"<div style='font-family:\"Baloo 2\",sans-serif;font-weight:800;"
            f"color:{GREEN};font-size:.95rem;margin-top:.2rem'>{label}</div>"
            f"</div>", unsafe_allow_html=True)
    with c2:
        st.title(user["display_name"])
        joined = datetime.fromisoformat(user["created_at"])
        days = max(0, (datetime.now() - joined).days)
        st.markdown(
            pill(f"Member for {days} days", "calendar")
            + pill("Public profile" if user["privacy"] == "public"
                   else "Private profile",
                   "users" if user["privacy"] == "public" else "lock")
            + pill(f"{user['reminder_cadence']} check-ins", "calendar"),
            unsafe_allow_html=True)
        st.markdown(
            pill(f"Streak {streak['current']}", "flame")
            + pill(f"Best streak {streak['best']}", "trophy")
            + pill(f"Goals {gstats['completed']}/{gstats['total']} "
                   f"({gstats['rate']:.0f}%)", "target"),
            unsafe_allow_html=True)
    with c3:
        if latest:
            st.markdown(score_ring(latest["results"]["score"]["total"]),
                        unsafe_allow_html=True)

    if latest:
        r = latest["results"]
        with id_band:
            k1, k2, k3 = st.columns(3)
        k1.markdown(kpi_card("water", "Water",
                             f"{r['water']['water_litres_person_day']:.0f}",
                             "L/person/day", conf=r["water"]["confidence"]),
                    unsafe_allow_html=True)
        k2.markdown(kpi_card("bolt", "Electricity",
                             f"{r['electricity']['total_electricity_kwh_month']:.0f}",
                             "kWh/month", conf=r["electricity"]["confidence"]),
                    unsafe_allow_html=True)
        k3.markdown(kpi_card("cloud", "Net carbon",
                             f"{r['carbon']['net_co2e_kg_year']:,.0f}",
                             "kg CO₂e/yr", conf=r["carbon"]["calculation_confidence"]),
                    unsafe_allow_html=True)
    else:
        with id_band:
            st.info("No assessment yet — your profile fills up after the "
                    "first one.")

    # ---- avatar controls band (upload / selfie / regenerate — §4-§5) ----
    with st.container(key="band_profile_avatar"):
        _avatar_section(user, tier)

    # ------------------------------------------------------------- badges
    with st.container(key="band_profile_badges"):
        st.subheader("Achievements")
        render_achievement_cards(user["id"])

    # -------------------------------------------------------- goal history
    with st.container(key="band_profile_goals"):
        st.subheader("Goal history")
        goals = db.all_goals(user["id"])
        if not goals:
            st.caption("Goals appear with your first assessment.")
        for g in goals[:12]:
            mark = {"completed": icon("check", 14, "#1d8a4e"),
                    "active": icon("target", 14, "#b7791f"),
                    "missed": icon("scissors", 14, "#c05621")}.get(
                        g["status"], icon("target", 14, "#b7791f"))
            st.markdown(f"{mark} **{g['title']}** — week {g['week_label']} "
                        f"{pill(g['metric'])}", unsafe_allow_html=True)

    # ------------------------------------------------------- public fields
    if user["privacy"] == "public":
        import json
        fields = json.loads(user["public_fields"] or "[]")
        st.caption("Public profile: sharing " +
                   (", ".join(fields) if fields else "no fields yet — choose "
                    "them in Settings") + ". Raw data and bills stay private.")
    else:
        st.caption("Private profile — nothing is shared. You can opt in "
                   "under Settings.")
