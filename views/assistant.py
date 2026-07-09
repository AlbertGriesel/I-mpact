"""Floating AI assistant (§18/brief §7).

A clearly AI/chat launcher (a speech-bubble-with-spark, distinct from the daisy
mascot and the user avatar) fixed in the bottom-right corner opens a floating
chat panel on every page. The assistant is grounded in the user's live results,
goals and history, can explain their impact, plan improvements and propose
measurable goals — which are added only on explicit confirmation and pass
through the central duplicate check (§13)."""

import random

import streamlit as st

import ai
import database as db
from goals import (generate_goal_candidates, find_duplicate,
                   sanitize_planner_goals)
from visuals import pill, scroll_chat_to_prompt

_GREETING = ("Hi — I'm the **I/mpact assistant**. Ask me anything about your "
             "results — *“why is my carbon so high?”*, *“how do I cut water "
             "use without killing the garden?”* — and I'll turn it into "
             "practical, measurable steps.")


def _grounding(user):
    latest = db.latest_assessment(user["id"])
    history = db.list_assessments(user["id"])
    week_goals = db.goals_for_week(user["id"])
    streak = db.get_streak(user["id"])
    g = {
        "display_name": user["display_name"],
        "account_type": user.get("account_type", "personal"),
        "reminder_cadence": user["reminder_cadence"],
        "current_week_goals": [
            {"title": x["title"], "metric": x["metric"], "status": x["status"]}
            for x in week_goals],
        "active_goals_all": [
            {"title": x["title"], "metric": x["metric"]}
            for x in db.all_goals(user["id"]) if x["status"] == "active"],
        "streak": {"current": streak["current"], "best": streak["best"]},
        "assessments_count": len(history),
        "note": "Never propose a goal that duplicates current_week_goals or "
                "active_goals_all — say it's already in their plan instead.",
    }
    if latest:
        g["latest_results"] = latest["results"]
        g["household"] = latest["inputs"]["general"]
        g["data_completeness"] = ai.data_completeness(latest["results"])
        g["deterministic_goal_candidates"] = generate_goal_candidates(
            latest["inputs"], latest["results"])
        if len(history) > 1:
            g["previous_results_summary"] = {
                "water_l_month": history[-2]["results"]["water"]["total_water_litres_month"],
                "electricity_kwh_month": history[-2]["results"]["electricity"]["total_electricity_kwh_month"],
                "net_co2e_kg_year": history[-2]["results"]["carbon"]["net_co2e_kg_year"],
            }
    return g


def _existing_goals(user):
    return (db.goals_for_week(user["id"])
            + [g for g in db.all_goals(user["id"]) if g["status"] == "active"])


def render_floating(user):
    """FAB + panel. Rendered on every page from app.py; survives reruns
    because visibility is plain session state."""
    with st.container(key="assistant_fab"):
        if st.button("Assistant", key="fab_btn",
                     help="Ask I/mpact — questions about your results and how "
                          "to improve"):
            st.session_state["assistant_open"] = \
                not st.session_state.get("assistant_open", False)

    if not st.session_state.get("assistant_open"):
        return

    with st.container(key="assistant_panel"):
        with st.container(border=True):
            head, close = st.columns([5, 1])
            head.markdown("**I/mpact assistant** · AI help with your results")
            if close.button("✕", key="assistant_close"):
                st.session_state["assistant_open"] = False
                st.rerun()

            if user is None:
                st.info("Sign in to chat — the assistant grounds every answer "
                        "in your own numbers.")
                return
            if not ai.assistant_ready():
                st.warning("The assistant is offline. Connect a free key "
                           "under Settings → AI connection.")
                return
            if not db.latest_assessment(user["id"]):
                st.info("Complete your first assessment so I have real "
                        "numbers to work with.")
                return

            history = st.session_state.setdefault("assistant_history", [])
            with st.container(height=280):
                st.chat_message("assistant").markdown(_GREETING)
                for m in history:
                    role = "user" if m["role"] == "user" else "assistant"
                    st.chat_message(role).markdown(m.get("text", ""))
            # §5: after a NEW answer, park the user's prompt at the top of the
            # scroll box — once, so manual scrolling on later reruns is free.
            if st.session_state.pop("assistant_scroll", False):
                scroll_chat_to_prompt()

            # proposed goals: Add once -> confirmation -> box disappears (§13)
            proposals = st.session_state.get("assistant_proposals", [])
            for i, goal in enumerate(list(proposals)):
                with st.container(border=True):
                    saving = (f" · ~{goal['expected_saving']:.0f} "
                              f"{goal.get('expected_saving_unit') or ''}"
                              if goal.get("expected_saving") else "")
                    st.markdown(f"**{goal['title']}** "
                                f"{pill(goal.get('metric', 'carbon'))}{saving}",
                                unsafe_allow_html=True)
                    b1, b2 = st.columns(2)
                    if b1.button("Add goal", key=f"fab_add_{i}",
                                 type="primary", use_container_width=True):
                        proposals.remove(goal)          # box disappears first
                        st.session_state["assistant_proposals"] = proposals
                        added, _skipped = db.save_goals(user["id"], [goal])
                        st.toast("Added to this week's plan."
                                 if added else "That's already in your plan.",
                                 icon=":material/check_circle:" if added
                                 else ":material/info:")
                        st.rerun()
                    if b2.button("Cancel", key=f"fab_drop_{i}",
                                 use_container_width=True):
                        proposals.remove(goal)
                        st.session_state["assistant_proposals"] = proposals
                        st.rerun()

            with st.form("assistant_form", clear_on_submit=True):
                q = st.text_input("Message", key="assistant_q",
                                  placeholder="Ask about your impact…",
                                  label_visibility="collapsed")
                sent = st.form_submit_button("Send", type="primary",
                                             use_container_width=True)
            if sent and q.strip():
                history.append({"role": "user", "text": q.strip()})
                with st.spinner(random.choice(ai.FRIENDLY_WAIT)):
                    out = ai.planner_reply(history, _grounding(user))
                if out["ok"]:
                    st.session_state["assistant_history"] = out["history"]
                    if out["proposed_goals"]:
                        # Trust boundary: strip any AI-supplied saving and
                        # re-derive it deterministically before anything can be
                        # added to the plan (see goals.sanitize_planner_goals).
                        latest = db.latest_assessment(user["id"])
                        verified = (sanitize_planner_goals(
                            out["proposed_goals"], latest["inputs"],
                            latest["results"]) if latest else [])
                        existing = _existing_goals(user)
                        fresh, dup = [], 0
                        for g in verified:
                            if find_duplicate(g, existing):
                                dup += 1
                            else:
                                fresh.append(g)
                        st.session_state["assistant_proposals"] = \
                            st.session_state.get("assistant_proposals", []) + fresh
                        if dup:
                            st.toast("One suggestion was already in your plan.",
                                     icon=":material/info:")
                else:
                    history.append({"role": "assistant", "text": out["text"]})
                st.session_state["assistant_scroll"] = True   # §5: reposition once
                st.rerun()
            st.caption("The assistant proposes — you decide. Goals are only "
                       "saved when you press *Add goal*.")
