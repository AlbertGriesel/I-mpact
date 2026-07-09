"""AI conversation assessment (method 2). Same schema, same conditional
logic, same calculator as the questionnaire — Sprout only asks what still
matters and records values through validated tool calls (spec §6.2, §11.1)."""

import streamlit as st

import ai
from schema import (default_assessment, missing_important_fields,
                    is_calculable, completeness)
from views.common import (require_login, complete_assessment,
                          achievement_toast, measure_intro, privacy_note)
from visuals import icon, GREEN


def _collected_summary(data):
    """Friendly, human-readable snapshot of what's been collected (brief §2/§16)
    — grouped by section with ✓ for answered and 'Not answered yet' for empty.
    Reuses the questionnaire's humanizer so no raw JSON / schema keys leak."""
    from views.assessment import _SECTIONS, _section_rows
    import business
    acct = data.get("general", {}).get("account_type", "personal")
    sections = business.SECTIONS if acct == "business" else _SECTIONS
    row_fn = business.section_rows if acct == "business" else _section_rows
    for entry in sections:
        title, icon_name = entry[0], entry[1]
        rows = row_fn(title, data)
        st.markdown(
            f"<div style='font-weight:800;color:#1B5E3B;font-size:.98rem;"
            f"margin:.5rem 0 .15rem'>{icon(icon_name, 15, GREEN)} {title}</div>",
            unsafe_allow_html=True)
        if rows:
            for label, val in rows:
                st.markdown(
                    f"<div style='display:flex;gap:.5rem;font-size:.95rem;"
                    f"padding:.06rem 0'><span style='color:#1d8a4e'>✓</span>"
                    f"<span style='color:#5c7069'>{label}:</span>"
                    f"<span style='font-weight:600;color:#22423A'>{val}</span>"
                    f"</div>", unsafe_allow_html=True)
        else:
            st.markdown(
                "<div style='display:flex;gap:.5rem;font-size:.95rem;"
                "padding:.06rem 0;color:#8b978f'><span>○</span>"
                "<span>Not answered yet</span></div>", unsafe_allow_html=True)

_GREETING = ("Hi! I'm your **I/mpact assistant** — let's figure out your "
             "environmental footprint together, in plain language.\n\n"
             "Tell me a bit about your household to start: how many people "
             "live with you, and do you know your monthly electricity or "
             "water numbers (a prepaid receipt or bill amount works too)? "
             "If you don't know something, just say so — I'll work around it.")

_GREETING_BUSINESS = (
    "Hi! I'm your **I/mpact assistant** — let's work out your business's "
    "environmental footprint together, in plain language.\n\n"
    "To start: what sector is the business in, roughly how many staff, and do "
    "you know your monthly electricity or water figures (a bill amount works "
    "too)? If you don't know something, just say so — I'll work around it.")


def _greeting(data):
    return (_GREETING_BUSINESS
            if data.get("general", {}).get("account_type") == "business"
            else _GREETING)


def _display_history(history, data):
    st.chat_message("assistant").markdown(_greeting(data))
    for msg in history:
        role = "user" if msg["role"] == "user" else "assistant"
        st.chat_message(role).markdown(msg.get("text", ""))


def render():
    user = require_login("Sign in to use the AI Assessment.")
    st.title("AI Assessment")

    if not ai.assistant_ready():
        st.warning("The assistant is offline. The guided questionnaire works "
                   "fully without it — use that instead, or connect a key "
                   "under Settings.")
        pages = st.session_state.get("pages", {})
        c1, c2 = st.columns(2)
        with c1:
            st.page_link(pages["assessment"],
                         label="Open the guided questionnaire",
                         icon=":material/edit_note:")
        with c2:
            st.page_link(pages["settings"], label="Connect AI",
                         icon=":material/key:")
        return

    if "chat_data" not in st.session_state:
        st.session_state.chat_data = default_assessment(
            user.get("account_type", "personal"))
        st.session_state.chat_history = []
        st.session_state.chat_done = False

    data = st.session_state.chat_data

    # §1: show the two-methods chooser before the conversation has begun.
    # (Privacy note lives at the BOTTOM of the page now — brief §4/§13 — so it
    #  never competes with the main task.)
    if not st.session_state.chat_history:
        measure_intro("chat")
        st.divider()

    # progress + collected-data panel
    pct = completeness(data)
    c1, c2 = st.columns([3, 1])
    with c1:
        st.progress(min(100, pct) / 100,
                    text=f"Assessment progress: about {pct}% of the important "
                         "questions covered")
    with c2:
        with st.popover("Collected so far"):
            _collected_summary(data)
            gaps = missing_important_fields(data)
            if gaps:
                st.caption("Still useful to add: "
                           + "; ".join(h for _, h in gaps[:4]))

    _display_history(st.session_state.chat_history, data)

    ready = is_calculable(data) and (st.session_state.chat_done or pct >= 40)
    if ready:
        st.info("Sprout has enough to work with — calculate whenever you like. "
                "More detail = better accuracy, so feel free to keep chatting.")
        if st.button("Calculate my footprint", type="primary",
                     key="btn_chat_calculate"):
            with st.spinner("Running the calculations…"):
                _, _results, new_ach = complete_assessment(user, data,
                                                           source="chat")
            achievement_toast(new_ach)
            for k in ("chat_data", "chat_history", "chat_done"):
                st.session_state.pop(k, None)
            # §7: straight to the dashboard; evaluation starts automatically
            st.session_state["postcalc_celebrate"] = True
            pages = st.session_state.get("pages", {})
            st.switch_page(pages["dashboard"])

    prompt = st.chat_input("Type naturally — e.g. “we're 4 people, prepaid "
                           "electricity about R900/month, 15-min showers”")
    if prompt:
        st.chat_message("user").markdown(prompt)
        history = st.session_state.chat_history + [
            {"role": "user", "text": prompt}]
        with st.chat_message("assistant"):
            with st.spinner("Sprout is thinking…"):
                out = ai.chat_collect(history, data)
            st.markdown(out["text"] or "…")
            if out["applied"]:
                st.caption("Recorded: " + ", ".join(out["applied"]))
            if out["rejected"]:
                st.caption("Not recorded (failed validation): "
                           + "; ".join(out["rejected"][:3]))
        if out["ok"]:
            st.session_state.chat_history = out["history"]
            st.session_state.chat_data = out["data"]
            if out["done"]:
                st.session_state.chat_done = True
        st.rerun()

    with st.expander("Prefer buttons and forms?"):
        pages = st.session_state.get("pages", {})
        st.markdown("Both methods collect the same data and produce identical "
                    "results — pick whichever feels easier.")
        st.page_link(pages["assessment"], label="Switch to the guided "
                     "questionnaire", icon=":material/edit_note:")
        if st.button("Reset this conversation", key="btn_chat_reset"):
            for k in ("chat_data", "chat_history", "chat_done"):
                st.session_state.pop(k, None)
            st.rerun()

    # data-handling info sits at the very bottom, out of the task flow (§4/§13)
    st.divider()
    privacy_note("chat")
