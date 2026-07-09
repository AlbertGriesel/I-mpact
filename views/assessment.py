"""Guided questionnaire (assessment method 1).

First-time users walk the full wizard. Returning users (§6) start from a
friendly review hub pre-filled with their previous answers: stable
information (household, vehicle, infrastructure) is reused, monthly-changing
sections are flagged for update, and every section has an Edit action (§8).
Confirming the calculation runs the engine, saves, and goes STRAIGHT to the
dashboard where the AI evaluation starts automatically (§7)."""

import copy

import streamlit as st

import database as db
import water
import electricity
import transport
import lifestyle
import business
import widgets as w
from schema import default_assessment
from views.common import (current_user, complete_assessment, achievement_toast,
                          location_picker, measure_intro)
from visuals import icon

STEPS = ["General", "Water", "Electricity", "Transport", "Lifestyle", "Review"]
REVIEW = len(STEPS) - 1


def _account_type(data):
    return data.get("general", {}).get("account_type", "personal")


def _steps(acct):
    return business.STEPS if acct == "business" else STEPS

# review sections: (title, icon, wizard step, monthly-update hint)
_SECTIONS = [
    ("General information", "users", 0, False),
    ("Water", "water", 1, True),
    ("Electricity", "bolt", 2, True),
    ("Backup power", "battery", 2, False),
    ("Transport", "car", 3, True),
    ("Flights", "plane", 3, True),
    ("Heating", "flame", 4, False),
    ("Diet & lifestyle", "food", 4, False),
]


def _fmt(v, suffix=""):
    if v is None or v == "" or v is False:
        return None
    if v is True:
        return "Yes"
    if isinstance(v, float):
        return f"{v:g}{suffix}"
    return f"{v}{suffix}"


def _section_rows(title, data):
    """Humanized label→value rows per category — no JSON, no code formatting
    (§8). Only meaningful values are shown."""
    g, wa, e, t, l = (data["general"], data["water"], data["electricity"],
                      data["transport"], data["lifestyle"])
    rows = []
    if title == "General information":
        rows = [("People in household", _fmt(g.get("household_size"))),
                ("Country", _fmt(g.get("country"))),
                ("Province / region", _fmt(g.get("region"))),
                ("Municipality", _fmt(g.get("municipality")))]
    elif title == "Water":
        src = {"bill": "from your bill", "manual": "entered manually"}.get(
            wa.get("measured_source"), None)
        rows = [("Monthly use", _fmt(wa.get("water_kl_month"), " kL")
                 and f"{wa['water_kl_month']:g} kL ({src})" if wa.get("water_kl_month") else None),
                ("Monthly bill", _fmt(wa.get("water_bill_rand")) and
                 f"R{wa['water_bill_rand']:g}"),
                ("Rainwater share", _fmt(wa.get("rainwater_percentage") or None, "%")),
                ("Shower habit", (f"{wa['shower_minutes']:g} min × "
                                  f"{wa['showers_per_week']}/week")
                 if wa.get("shower_minutes") and wa.get("showers_per_week") else None),
                ("Garden irrigation", _fmt(wa.get("garden_irrigation") or None)),
                ("Swimming pool", _fmt(wa.get("swimming_pool") or None))]
        if not any(v for _, v in rows):
            rows = [("Method", "National benchmark (218 L/person/day)")]
    elif title == "Electricity":
        src = {"bill": "from your bill", "manual": "entered manually"}.get(
            e.get("measured_source"), None)
        rows = [("Monthly use", f"{e['kwh_month']:g} kWh ({src})"
                 if e.get("kwh_month") else None),
                ("Monthly spend", f"R{e['bill_rand']:g}" if e.get("bill_rand") else None),
                ("Renewables", f"{e['renewable_source']} · "
                               f"{e.get('renewable_percentage') or 0}%"
                 if e.get("renewable_source", "None") != "None" else None)]
        if not e.get("kwh_month") and not e.get("bill_rand"):
            appl = [n for n, k in [("geyser", "electric_geyser"),
                                   ("stove", "electric_stove"),
                                   ("aircon", "air_conditioner"),
                                   ("pool pump", "pool_pump")] if e.get(k)]
            rows.append(("Method", "Appliance estimate ("
                         + (", ".join(appl) if appl else "base load only") + ")"))
    elif title == "Backup power":
        if e.get("backup_power", "None") == "None":
            rows = [("Backup", "None")]
        else:
            rows = [("Type", e["backup_power"]),
                    ("Generator fuel", f"{e['generator_litres_per_month']:g} L/month"
                     if e.get("generator_litres_per_month") else
                     (f"{e['generator_hours_per_month']:g} h/month"
                      if e.get("generator_hours_per_month") else None)),
                    ("Coverage", _fmt(e.get("generator_coverage"))),
                    ("Charged from", _fmt(e.get("backup_charge_source"))
                     if e["backup_power"] != "Generator" else None)]
    elif title == "Transport":
        v = t["vehicle"]
        rows = [("Vehicle", f"{v.get('manufacturer', '')} {v.get('model', '')}".strip()
                 if v.get("owns_vehicle") else "No personal vehicle"),
                ("Distance", f"{v['annual_km']:,.0f} km/year"
                 if v.get("owns_vehicle") and v.get("annual_km") else None),
                ("People in car", _fmt(v.get("average_passengers"))
                 if v.get("owns_vehicle") else None),
                ("Public transport", f"{t['public_transport']['type']} · "
                                     f"{t['public_transport']['weekly_km']:g} km/week"
                 if t["public_transport"].get("type", "None") != "None"
                 and t["public_transport"].get("weekly_km") else None)]
    elif title == "Flights":
        fl = t.get("flights", [])
        if not fl:
            rows = [("Flights", "None")]
        else:
            rows = [(f"Route {i + 1}",
                     f"{f['departure_airport']} → {f['arrival_airport']} · "
                     f"{f['cabin_class']} · {f['trip_type']} × "
                     f"{f['trips_per_year']}/yr") for i, f in enumerate(fl)]
    elif title == "Heating":
        hm = l.get("heating_method", "None")
        if hm in ("None",):
            rows = [("Heating", "None")]
        else:
            qty = (f"{l['heating_lpg_litres_per_year']:g} L LPG/yr" if l.get("heating_lpg_litres_per_year")
                   else f"{l['heating_gas_m3_per_year']:g} m³ gas/yr" if l.get("heating_gas_m3_per_year")
                   else f"{l['heating_paraffin_litres_per_year']:g} L/yr" if l.get("heating_paraffin_litres_per_year")
                   else f"{l['heating_coal_kg_per_year']:g} kg/yr" if l.get("heating_coal_kg_per_year")
                   else f"{l['heating_wood_kg_per_year']:g} kg/yr" if l.get("heating_wood_kg_per_year")
                   else None)
            rows = [("Method", hm), ("Fuel", qty),
                    ("Usage", f"{l['heating_hours_per_day']:g} h/day, "
                              f"{l.get('heating_months_per_year') or 0} months/yr"
                     if l.get("heating_hours_per_day") else None)]
    elif title == "Diet & lifestyle":
        rows = [("Diet", _fmt(l.get("diet"))),
                ("Food waste", _fmt(l.get("food_waste"))),
                ("Shopping", _fmt(l.get("shopping_habits"))),
                ("Carbon offsets", f"{l['offset_tonnes_per_year']:g} t/yr"
                 if l.get("buys_offsets") and l.get("offset_tonnes_per_year")
                 else None)]
    return [(label, val) for label, val in rows if val]


def _reset_assessment_session():
    for k in ("assessment_data", "wizard_step", "assessment_returning",
              "water_bill_sig", "elec_bill_sig", "water_extraction",
              "elec_extraction", "aw_flight_store", "aw_fleet_store"):
        st.session_state.pop(k, None)
    w.clear_all()


def _go_to_step(step):
    st.session_state.wizard_step = step
    st.session_state["_scroll_top"] = True   # §6: next section loads at the top
    st.rerun()


# --- empty-section confirmation (§12): ZERO and UNKNOWN are not the same ---
# Personal wizard steps that map to a data section we can meaningfully check.
_STEP_SECTION = {1: "water", 2: "electricity", 3: "transport"}
_SECTION_LABEL = {"water": "water", "electricity": "electricity",
                  "transport": "transport"}
# Sections where a genuine zero is conceptually valid (a household can truly
# have no transport; it cannot have literally zero water/electricity).
_SECTION_ZERO_OK = {"transport"}


def _section_empty(sec, data):
    """True when the user left an entire section untouched (no answer at all)."""
    d = data.get(sec, {})
    if sec == "water":
        return not (d.get("water_kl_month") or d.get("water_bill_rand")
                    or d.get("shower_minutes") or d.get("uses_rainwater")
                    or d.get("garden_irrigation") or d.get("swimming_pool"))
    if sec == "electricity":
        appliance = any(d.get(k) for k in ("electric_geyser", "air_conditioner",
                        "electric_stove", "pool_pump"))
        return not (d.get("kwh_month") or d.get("bill_rand") or appliance
                    or d.get("renewable_source", "None") not in ("None", None)
                    or d.get("backup_power", "None") not in ("None", None))
    if sec == "transport":
        v = d.get("vehicle", {})
        pt = d.get("public_transport", {})
        return not (v.get("owns_vehicle") or d.get("flights")
                    or pt.get("type", "None") not in ("None", None)
                    or d.get("fleet"))
    return False


@st.dialog("Nothing entered for this section")
def _empty_section_dialog(sec, next_step):
    label = _SECTION_LABEL.get(sec, sec)
    data = st.session_state.assessment_data
    st.markdown(f"You haven't entered any **{label}** information yet.")
    st.caption("“Zero” and “skip” are recorded differently — a skipped section "
               "is treated as unknown and estimated, never counted as zero.")
    if sec in _SECTION_ZERO_OK:
        if st.button(f"My {label} impact here is zero", type="primary",
                     use_container_width=True, key="empty_zero"):
            data.setdefault("section_status", {})[sec] = "zero"
            st.session_state.assessment_data = data
            st.session_state.pop("_empty_confirm", None)
            _go_to_step(next_step)
    if st.button("Skip for now — I don't know", use_container_width=True,
                 key="empty_skip"):
        data.setdefault("section_status", {})[sec] = "skipped"
        st.session_state.assessment_data = data
        st.session_state.pop("_empty_confirm", None)
        _go_to_step(next_step)
    if st.button("Go back and add information", use_container_width=True,
                 key="empty_back"):
        st.session_state.pop("_empty_confirm", None)
        st.rerun()


def _stepper(step, steps):
    cols = st.columns(len(steps))
    for i, (col, label) in enumerate(zip(cols, steps)):
        with col:
            if i == step:
                col.markdown(
                    f"<div style='font-weight:800;color:#1B5E3B;"
                    f"border-bottom:3px solid #2E9E63;padding-bottom:4px;"
                    f"display:inline-block'>{label}</div>",
                    unsafe_allow_html=True)
            elif i < step:
                col.markdown(
                    f"<div style='color:#1d8a4e;font-weight:600'>"
                    f"{icon('check', 14, '#1d8a4e')} {label}</div>",
                    unsafe_allow_html=True)
            else:
                col.markdown(f"<div style='color:#9bb0a8'>{label}</div>",
                             unsafe_allow_html=True)
    st.progress(step / (len(steps) - 1))


def _new_account_type(user):
    """The account type a fresh assessment should use: the signed-in user's
    type, or a guest's chosen type (defaults to personal)."""
    if user:
        return user.get("account_type", "personal")
    return st.session_state.get("guest_account_type", "personal")


def render():
    # No account needed to try the core product: guests walk the same wizard
    # and the same engine; only persistence differs (see complete_assessment).
    user = current_user()
    st.title("Your assessment")
    if user is None:
        st.caption("You're trying I/mpact as a guest — same questions, same "
                   "calculations, full results. A free account (any time "
                   "later) saves them and unlocks goals and streaks.")
        # guests can still choose to assess a business before signing up
        gtype = st.radio(
            "Who is this assessment for?", ["personal", "business"],
            index=0 if _new_account_type(user) == "personal" else 1,
            format_func=lambda t: "A household (personal)" if t == "personal"
            else "A business / organisation", horizontal=True,
            key="guest_account_type_pick")
        if gtype != st.session_state.get("guest_account_type"):
            st.session_state["guest_account_type"] = gtype
            st.session_state.pop("assessment_data", None)   # reshape the form

    if "assessment_data" not in st.session_state:
        prev = db.latest_assessment(user["id"]) if user else None
        if prev:
            # returning user (§6): reuse everything, land on the review hub
            st.session_state.assessment_data = copy.deepcopy(prev["inputs"])
            st.session_state.assessment_returning = True
        elif user is None and st.session_state.get("guest_inputs"):
            # returning guest in the same session: same review-hub treatment
            st.session_state.assessment_data = copy.deepcopy(
                st.session_state["guest_inputs"])
            st.session_state.assessment_returning = True
        else:
            st.session_state.assessment_data = default_assessment(
                _new_account_type(user))
            st.session_state.assessment_returning = False
        acct0 = _account_type(st.session_state.assessment_data)
        st.session_state.wizard_step = (len(_steps(acct0)) - 1
                                        if st.session_state.assessment_returning
                                        else 0)
    data = st.session_state.assessment_data
    acct = _account_type(data)
    steps = _steps(acct)
    review_idx = len(steps) - 1
    step = min(st.session_state.get("wizard_step", 0), review_idx)
    returning = st.session_state.get("assessment_returning", False)

    # §1: make the two assessment methods obvious at the very start.
    if step == 0 and not returning:
        measure_intro("manual")

    # One readable band per wizard screen (§1-§2): the step's questions live
    # on a content-sized panel and the illustrated world stays visible around
    # it, instead of one page-length white sheet.
    with st.container(key="band_wizard"):
        _stepper(step, steps)
        st.divider()

        if step == review_idx:
            _render_review(user, data, returning, acct)
        elif acct == "business":
            renderers = [business.render_general, business.render_water,
                         business.render_electricity, business.render_transport,
                         business.render_operations]
            data = renderers[step](data)
        else:
            if step == 0:
                data["general"] = _render_general(data["general"])
            elif step == 1:
                data["water"] = water.render(data["water"])
            elif step == 2:
                data["electricity"] = electricity.render(data["electricity"])
            elif step == 3:
                data["transport"] = transport.render(data["transport"])
            elif step == 4:
                data["lifestyle"] = lifestyle.render(data["lifestyle"])

        st.session_state.assessment_data = data

        if step < review_idx:
            st.divider()
            left, mid, right = st.columns([1, 3, 1])
            with left:
                if step > 0 and st.button("← Back", use_container_width=True,
                                          key="nav_back"):
                    _go_to_step(step - 1)
            with mid:
                if returning and st.button("Done — back to review",
                                           use_container_width=True,
                                           key="nav_review"):
                    _go_to_step(review_idx)
            with right:
                if st.button("Next →", type="primary",
                             use_container_width=True, key="nav_next"):
                    # §12: if a whole section is blank, confirm zero vs skip
                    # before advancing — never silently treat blank as zero.
                    sec = _STEP_SECTION.get(step) if acct != "business" else None
                    if (sec and _section_empty(sec, data)
                            and data.get("section_status", {}).get(sec) is None):
                        st.session_state["_empty_confirm"] = (sec, step + 1)
                        st.rerun()
                    else:
                        if sec:
                            data.get("section_status", {}).pop(sec, None)
                        _go_to_step(step + 1)

    # §12: raise the confirmation dialog when a blank section was flagged above
    if st.session_state.get("_empty_confirm"):
        _empty_section_dialog(*st.session_state["_empty_confirm"])


def _render_general(data):
    st.header("General")
    st.caption("Just enough to pick the right regional factors — nothing more.")
    data["household_size"] = w.slider_int(
        "How many people live in your household?", "hh_size",
        data.get("household_size") or 1, minv=1, maxv=16,
        help="Used to show fair per-person numbers next to household totals.")
    pending = st.session_state.get("pending_general")
    if pending and pending.get("municipality"):
        st.info(f"Your bill looks like it's from **{pending['municipality']}** — "
                "pick the closest match below.")
    st.subheader("Location")
    location_picker(data, key_prefix="loc")
    return data


def _render_review(user, data, returning, acct="personal"):
    if returning:
        st.header("Welcome back — quick update")
        st.markdown(
            "We kept your stable information. Sections marked **updates "
            "monthly** usually change between check-ins — tap **Edit** on "
            "anything that's different, then recalculate.")
    else:
        st.header("Review your answers")
        st.caption("Everything in one place — tap Edit to change a section.")

    sections = business.SECTIONS if acct == "business" else _SECTIONS
    row_fn = business.section_rows if acct == "business" else _section_rows
    cols = st.columns(2)
    for idx, (title, icon_name, target_step, monthly) in enumerate(sections):
        with cols[idx % 2], st.container(border=True):
            head, edit = st.columns([4, 1.1])
            badge = ("<span class='pill' style='font-size:.7rem'>updates "
                     "monthly</span>" if monthly and returning else "")
            head.markdown(f"{icon(icon_name, 16, '#2E9E63')} **{title}** "
                          f"{badge}", unsafe_allow_html=True)
            if edit.button("Edit", key=f"edit_{idx}", use_container_width=True):
                _go_to_step(target_step)
            rows = row_fn(title, data)
            if not rows:
                st.caption("Nothing captured yet.")
            for label, val in rows:
                st.markdown(
                    f"<div style='display:flex;justify-content:space-between;"
                    f"gap:1rem;padding:.12rem 0;font-size:.9rem'>"
                    f"<span style='color:#5c7069'>{label}</span>"
                    f"<span style='font-weight:600;color:#22423A;"
                    f"text-align:right'>{val}</span></div>",
                    unsafe_allow_html=True)

    st.divider()
    from views.common import privacy_note
    privacy_note("submit")
    c1, c2 = st.columns([2.2, 1])
    with c1:
        if st.button("Calculate my footprint", type="primary",
                     use_container_width=True, key="btn_calculate"):
            with st.spinner("Running the calculations…"):
                _, _results, new_ach = complete_assessment(
                    user, data, source="update" if returning else "questionnaire")
            achievement_toast(new_ach)
            # §7: straight to the dashboard; it celebrates and starts the
            # AI evaluation automatically.
            _reset_assessment_session()
            st.session_state["postcalc_celebrate"] = True
            pages = st.session_state.get("pages", {})
            st.switch_page(pages["dashboard"])
    with c2:
        if st.button("Start fresh instead", use_container_width=True,
                     key="btn_restart"):
            _reset_assessment_session()
            st.session_state.assessment_data = default_assessment(acct)
            st.session_state.assessment_returning = False
            st.session_state.wizard_step = 0
            st.rerun()
