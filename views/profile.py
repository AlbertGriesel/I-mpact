"""Profile page (spec §5.3): identity, membership duration, score, metric
summaries, streaks, achievements and goal history."""

from datetime import datetime

import streamlit as st

import database as db
import achievements as ach_mod
from views.common import require_login
from visuals import render_mascot, score_ring, kpi_card, pill, icon


def render():
    user = require_login("Sign in to see your profile.")
    fresh = db.get_user(user["id"])  # settings may have changed
    st.session_state["user"] = fresh
    user = fresh

    assessments = db.list_assessments(user["id"])
    latest = assessments[-1] if assessments else None
    streak = db.get_streak(user["id"])
    gstats = db.goal_stats(user["id"])

    c1, c2, c3 = st.columns([1, 1.6, 1])
    with c1:
        st.markdown(f"<div style='font-size:5rem;text-align:center'>{user['avatar']}</div>",
                    unsafe_allow_html=True)
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
        st.info("No assessment yet — your profile fills up after the first one.")
        render_mascot(None, height=180)

    # ------------------------------------------------------------- badges
    st.subheader("Achievements")
    earned = {a["code"]: a for a in db.get_achievements(user["id"])}
    cols = st.columns(4)
    for i, (code, meta) in enumerate(ach_mod.ACHIEVEMENTS.items()):
        with cols[i % 4], st.container(border=True):
            if code in earned:
                st.markdown(icon(meta["icon"], 30, "#2E9E63"),
                            unsafe_allow_html=True)
                st.markdown(f"**{meta['name']}**")
                st.caption(f"{meta['desc']}  \n_{earned[code]['earned_at'][:10]}_")
            else:
                st.markdown(icon("lock", 30, "#9bb0a8"), unsafe_allow_html=True)
                st.markdown(f"**{meta['name']}**")
                st.caption(meta["desc"])

    # -------------------------------------------------------- goal history
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
