"""Shared helpers for the view modules."""

import copy

import streamlit as st

import database as db
import achievements as ach
from calculations import run_assessment
from goals import pick_weekly_goals
from visuals import icon

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
