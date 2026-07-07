"""Feedback dashboard — an interactive consumer view, not a document (§9).

Layout: two-column top (mascot + scores | automatic short AI snapshot §10/§11),
KPI cards, relatable comparisons, trend + donut charts (§15), one merged
"Your plan for this week" section (§12) with a stable anchor for the Goals
shortcut (§14), achievements and a transparency expander. Sections alternate
between the plain background and semi-transparent green bands.

Guests get the same dashboard core (hero, KPIs, comparisons, donut,
transparency) rendered from their session-held results; account-bound
sections (trends, plan, achievements) explain themselves instead of erroring.
"""

import json
import random

import altair as alt
import pandas as pd
import streamlit as st

import ai
import database as db
import achievements as ach_mod
from benchmarks import BENCHMARKS
from comparisons import (water_comparison, electricity_comparison,
                         carbon_comparison)
from goals import pick_weekly_goals, find_duplicate
from views.common import (current_user, guest_assessment, PERIODS, from_month,
                          from_year, reminder_banner, achievement_toast,
                          render_achievement_cards)
from visuals import (kpi_card, render_mascot, score_ring, pill, icon,
                     celebrate, scroll_to_anchor)

_DONUT_COLORS = ["#2E9E63", "#7EC8E3", "#F2C14E", "#B0713C", "#1B5E3B",
                 "#57b97c", "#9aa3ad"]


def _delta(curr, prev):
    if prev in (None, 0):
        return None, True
    change = (curr - prev) / prev * 100
    good = change <= 0
    arrow = "▼" if good else "▲"
    return f"{arrow} {abs(change):.0f}% vs previous", good


def _fmt(v):
    return f"{v:,.0f}" if abs(v) >= 10 else f"{v:,.1f}"


def _benchmarks_info():
    return {k: {kk: v[kk] for kk in ("value", "label", "source", "scope")}
            for k, v in BENCHMARKS.items()}


def _ensure_eval(latest):
    """Automatic, cached short evaluation (§11): generated once per
    assessment, reused on every rerender, regenerated only on request."""
    if latest.get("ai_eval"):
        try:
            parsed = json.loads(latest["ai_eval"])
            if all(k in parsed for k in ("overall", "positive", "concern",
                                         "recommendation")):
                return parsed, True
        except (json.JSONDecodeError, TypeError):
            pass  # invalid cache -> regenerate below
    r = latest["results"]
    if ai.assistant_ready():
        with st.spinner(random.choice(ai.FRIENDLY_WAIT)):
            ok, ev = ai.short_eval(r, latest["inputs"]["general"],
                                   _benchmarks_info())
        if ok:
            db.set_assessment_eval(latest["id"], ev)
            return ev, True
    return ai.fallback_eval(r), False


def _ensure_eval_guest(results, inputs):
    """Same snapshot for guests, cached in the session instead of the DB."""
    cached = st.session_state.get("guest_eval")
    if cached:
        return cached, True
    if ai.assistant_ready():
        with st.spinner(random.choice(ai.FRIENDLY_WAIT)):
            ok, ev = ai.short_eval(results, inputs["general"],
                                   _benchmarks_info())
        if ok:
            st.session_state["guest_eval"] = ev
            return ev, True
    return ai.fallback_eval(results), False


# ======================== shared rendering helpers =========================

def _render_hero(score, snapshot, refresh_cb=None):
    """Top block: mascot + score ring + metric pills | short snapshot."""
    left, right = st.columns([1, 1.25], gap="large")
    with left:
        m1, m2 = st.columns([1.15, 1])
        with m1:
            render_mascot(score["total"], height=190, caption=False)
        with m2:
            st.markdown(score_ring(score["total"]), unsafe_allow_html=True)
        st.markdown(
            pill(f"Water {score['water']}", "water")
            + pill(f"Electricity {score['electricity']}", "bolt")
            + pill(f"Carbon {score['carbon']}", "cloud"),
            unsafe_allow_html=True)
    with right, st.container(key="band_snapshot"):
        head, refresh = st.columns([5, 1])
        head.markdown("#### Your snapshot")
        if refresh_cb is not None and refresh.button(
                "↻", key="btn_refresh_eval", help="Write a fresh evaluation"):
            refresh_cb()
            st.rerun()
        for icon_name, color, text in [
                ("leaf", "#2E9E63", snapshot["overall"]),
                ("check", "#1d8a4e", snapshot["positive"]),
                ("cloud", "#b7791f", snapshot["concern"]),
                ("target", "#1B5E3B", snapshot["recommendation"])]:
            st.markdown(
                f"<div style='display:flex;gap:.6rem;align-items:flex-start;"
                f"padding:.22rem 0'><span>{icon(icon_name, 17, color)}</span>"
                f"<span style='font-size:.95rem'>{text}</span></div>",
                unsafe_allow_html=True)


def _render_kpis(r, period, deltas=None):
    """KPI cards for water / electricity / carbon in the chosen period."""
    wtr, e, c = r["water"], r["electricity"], r["carbon"]
    wd, ed, cd = deltas or ((None, True), (None, True), (None, True))
    water_v = from_month(wtr["total_water_litres_month"], period)
    elec_v = from_month(e["total_electricity_kwh_month"], period)
    carbon_v = from_year(c["net_co2e_kg_year"], period)

    k1, k2, k3 = st.columns(3)
    k1.markdown(kpi_card(
        "water", "Water", _fmt(water_v), f"L / {period}",
        delta_text=wd[0], delta_good=wd[1],
        benchmark_text=f"{wtr['water_litres_person_day']:.0f} L/person/day · "
                       "SA benchmark 218",
        conf=wtr["confidence"]), unsafe_allow_html=True)
    k2.markdown(kpi_card(
        "bolt", "Electricity", _fmt(elec_v), f"kWh / {period}",
        delta_text=ed[0], delta_good=ed[1],
        benchmark_text=f"~350 kWh/month approx. SA household average · "
                       f"{e['renewable_share_percent']}% renewable",
        conf=e["confidence"]), unsafe_allow_html=True)
    k3.markdown(kpi_card(
        "cloud", "Carbon (net)", _fmt(carbon_v), f"kg CO₂e / {period}",
        delta_text=cd[0], delta_good=cd[1],
        benchmark_text=f"Per person {c['per_person_co2e_kg_year']:,.0f} kg/yr "
                       "(SA context ≈ 7,600 incl. industry)",
        conf=c["calculation_confidence"]), unsafe_allow_html=True)
    return water_v, elec_v, carbon_v


def _render_compare(water_v, elec_v, carbon_v, period):
    with st.container(key="band_compare"):
        st.markdown("**In everyday terms**")
        st.markdown("- " + water_comparison(water_v, period))
        st.markdown("- " + electricity_comparison(elec_v, period))
        st.markdown("- " + carbon_comparison(carbon_v, period))


def _render_donut(c):
    st.subheader("Where your carbon comes from")
    br = c["breakdown"]
    total = sum(br.values()) or 1.0
    rows = [{"Category": k.replace("_", " ").title(),
             "kg CO₂e/year": round(v, 1),
             "Share": f"{v / total * 100:.0f}%"}
            for k, v in br.items() if v / total >= 0.01 and v >= 1]
    if not rows:
        st.caption("No carbon sources captured yet.")
        return
    src = pd.DataFrame(rows)
    donut = alt.Chart(src).mark_arc(
        innerRadius=62, cornerRadius=5, padAngle=0.02,
    ).encode(
        theta=alt.Theta("kg CO₂e/year:Q"),
        color=alt.Color(
            "Category:N",
            scale=alt.Scale(range=_DONUT_COLORS),
            legend=alt.Legend(orient="bottom", columns=2,
                              labelLimit=180, title=None)),
        tooltip=["Category", "kg CO₂e/year", "Share"],
    ).properties(height=300)
    st.altair_chart(donut, use_container_width=True)
    biggest = max(br, key=br.get)
    st.caption(f"Largest source: **{biggest.replace('_', ' ')}** — "
               f"{br[biggest]:,.0f} kg/year "
               f"({br[biggest] / total * 100:.0f}%).")


# ====================== transparency, in plain language ====================

def _friendly_note(note):
    return (note.replace("([approximation])", "(approximate)")
                .replace("[approximation]", "approximate")
                .replace("([fallback assumption]", "(a standard assumption"
                         )
                .replace("[fallback assumption]", "a standard assumption")
                .replace("[MVP assumption]", "standard assumption"))


def _tblock(icon_name, title, entered, how, affects):
    """One category explanation with consistent typography and colours."""
    rows = ""
    for label, text in [("What you gave us", entered),
                        ("How we estimated your impact", how),
                        ("What can affect the estimate", affects)]:
        if text:
            rows += (f"<div style='font-size:.9rem;padding:.14rem 0;"
                     f"line-height:1.45'><span style='font-weight:700;"
                     f"color:#22423A'>{label}:</span> "
                     f"<span style='color:#3c4f48'>{text}</span></div>")
    st.markdown(
        f"<div style='padding:.55rem 0 .3rem 0'>"
        f"<div style='font-weight:800;color:#1B5E3B;font-size:1rem;"
        f"padding-bottom:.15rem'>{icon(icon_name, 16, '#2E9E63')} {title}"
        f"</div>{rows}</div>",
        unsafe_allow_html=True)


def _render_transparency(inputs, r):
    """§5/§18: a transparent explanation for a normal person — what went in,
    how it was converted, and why it might not be exact. No backend language."""
    g = inputs["general"]
    w_in, e_in = inputs["water"], inputs["electricity"]
    t_in, l_in = inputs["transport"], inputs["lifestyle"]
    wtr, e, c = r["water"], r["electricity"], r["carbon"]
    hh = max(1, int(g.get("household_size") or 1))
    people = "you" if hh == 1 else f"the {hh} people in your home"

    with st.expander("How your numbers were calculated"):
        st.markdown(
            "<div style='font-size:.92rem;color:#3c4f48;padding:.2rem 0 .4rem 0'>"
            "Every figure on this dashboard is an <b>estimate</b> built from "
            "the information you provided and published conversion factors. "
            "Measured numbers (a bill or meter reading) make it more precise; "
            "estimates fill the gaps honestly. Here's each category in plain "
            "language.</div>", unsafe_allow_html=True)

        # ---------------------------------------------------------- water
        method = wtr.get("calculation_method")
        if method in ("measured_bill", "measured_manual"):
            entered = ("the water reading from your bill"
                       if method == "measured_bill"
                       else "your monthly water amount") + \
                      f", and that {hh} " + \
                      ("person lives" if hh == 1 else "people live") + \
                      " in your home"
            how = (f"We used your measured amount directly and divided it "
                   f"across {people} to get a per-person figure, which we "
                   f"compare with the South African guide of 218 litres per "
                   f"person per day.")
        elif method == "bill_amount_tariff":
            label = wtr.get("tariff_label") or "your municipality's"
            entered = "the amount of your monthly water bill"
            how = (f"We converted the Rand amount into litres using "
                   f"{label} water prices, then divided it across {people} "
                   f"for a per-person figure.")
        else:
            entered = "no measured water numbers — that's okay"
            how = ("Without a measured number we started from the South "
                   "African average of 218 litres per person per day for "
                   f"your household of {hh}. Adding a bill later makes this "
                   "much more precise.")
        if wtr.get("rainwater_share_percent"):
            how += (f" The rainwater you harvest (about "
                    f"{wtr['rainwater_share_percent']}% of your use) is "
                    "counted separately from municipal water, because it "
                    "skips the municipal treatment system.")
        _tblock("water", "Water", entered, how,
                "Bill periods that don't match calendar months, estimated "
                "meter readings, recent price changes, visitors and shared "
                "household use can all shift the real number.")

        # ---------------------------------------------------- electricity
        method = e.get("calculation_method")
        if method in ("measured_bill", "measured_manual"):
            entered = ("the electricity reading from your bill"
                       if method == "measured_bill"
                       else "your monthly electricity units (kWh)")
            how = "We used your measured units directly."
        elif method == "bill_amount_tariff":
            label = e.get("tariff_label") or "your utility's"
            entered = "your monthly electricity spend"
            how = (f"We converted the Rand amount into units (kWh) using "
                   f"{label} electricity prices.")
        else:
            entered = ("which appliances you use — no measured number, and "
                       "that's okay")
            how = ("We added up typical usage for the appliances you told us "
                   "about (geyser, stove, pool pump…), plus a base amount "
                   "every home uses. This is deliberately rough, so it's "
                   "labelled low confidence.")
        how += (" Most South African electricity comes from coal, so each "
                "unit you buy from the grid causes roughly 0.9 kg of "
                "greenhouse gases — we multiplied your grid units by that "
                "official factor.")
        if e.get("renewable_share_percent"):
            how += (f" Your {e['renewable_share_percent']}% renewable share "
                    "is counted as clean and never billed with grid "
                    "emissions.")
        _tblock("bolt", "Electricity", entered, how,
                "Estimated appliance hours, seasonal changes (winter "
                "heating, summer pool pumps) and prepaid top-ups that don't "
                "line up with the month can move the result.")

        # --------------------------------------------------- backup power
        backup = e_in.get("backup_power", "None")
        if backup and backup != "None":
            if backup == "Generator":
                _tblock("battery", "Backup power",
                        "that you run a generator, and roughly how much fuel "
                        "or time it uses",
                        "We multiplied your generator's monthly fuel by the "
                        "greenhouse gases each litre creates when burned, "
                        "and added it to your footprint.",
                        "If you told us hours instead of litres, fuel use is "
                        "estimated from a typical consumption rate — actual "
                        "generators vary.")
            else:
                _tblock("battery", "Backup power",
                        f"that you use a {backup.lower()} for backup",
                        "Charging it from the grid is already inside your "
                        "electricity number, so we deliberately did not "
                        "count it twice. Solar charging counts as clean.",
                        None)

        # ------------------------------------------------------ transport
        v = t_in.get("vehicle", {})
        pt = t_in.get("public_transport", {})
        if v.get("owns_vehicle") or (pt.get("type", "None") != "None"):
            entered_bits = []
            if v.get("owns_vehicle"):
                entered_bits.append("your vehicle, the distance you drive "
                                    "and how many people usually ride along")
            if pt.get("type", "None") != "None":
                entered_bits.append("your weekly public-transport travel")
            how = ""
            if v.get("owns_vehicle"):
                how += ("We multiplied your yearly driving distance by a "
                        "fuel-use estimate for your vehicle, then by the "
                        "emissions each litre of fuel creates — and shared "
                        "the total between the people usually in the car. ")
            if pt.get("type", "None") != "None":
                how += ("Your public-transport kilometres use a published "
                        "per-kilometre emissions estimate for that transport "
                        "type.")
            _tblock("car", "Transport", " and ".join(entered_bits), how,
                    "Real-world fuel use differs from catalogue figures — "
                    "traffic, driving style and vehicle condition all "
                    "matter.")

        # --------------------------------------------------------- flights
        flights = t_in.get("flights") or []
        if flights:
            n = len(flights)
            _tblock("plane", "Flights",
                    f"{n} flight route{'s' if n != 1 else ''} with cabin "
                    "class and how often you fly",
                    "Each route gets an emissions estimate based on the "
                    "distance between the airports and your cabin class, "
                    "multiplied by how many times a year you fly it.",
                    "Aircraft type, how full the plane is and routing all "
                    "vary — per-seat flight numbers are honest averages, "
                    "not exact measurements.")

        # --------------------------------------------------------- heating
        hm = l_in.get("heating_method", "None")
        if hm and hm != "None":
            if hm in ("Electricity", "Heat pump"):
                _tblock("flame", "Heating",
                        f"that you heat with {hm.lower()}",
                        "Your heating runs on electricity, so it's already "
                        "inside your electricity number — we never count it "
                        "twice.", None)
            else:
                _tblock("flame", "Heating",
                        f"that you heat with {hm.lower()}, and roughly how "
                        "much fuel you use in a year",
                        "We multiplied your yearly fuel amount by the "
                        "greenhouse gases that fuel creates when burned.",
                        "Fuel estimates from memory are usually rough — a "
                        "season's receipts would sharpen this.")

        # ------------------------------------------------------------ diet
        _tblock("food", "Diet & lifestyle",
                f"your diet type ({l_in.get('diet', 'Average diet').lower()})"
                + (" and how much food gets wasted"
                   if l_in.get("food_waste") and l_in["food_waste"] != "None"
                   else ""),
                "Your diet type carries a published daily footprint estimate "
                "— meat-heavier diets sit higher, plant-based ones lower. "
                "Food waste increases it, because wasted food still had to "
                "be produced.",
                "These are category averages — your actual meals vary, so "
                "treat this as a fair ballpark rather than a measurement.")

        # --------------------------------------------------------- offsets
        if l_in.get("buys_offsets") and c.get("carbon_offsets_kg_year"):
            _tblock("leaf", "Carbon offsets",
                    "the certified offsets you buy each year",
                    f"We subtracted your {c['carbon_offsets_kg_year']:,.0f} "
                    f"kg of offsets from your gross total of "
                    f"{c['gross_co2e_kg_year']:,.0f} kg to reach your net "
                    f"figure of {c['net_co2e_kg_year']:,.0f} kg — the "
                    "before-and-after is always visible, never hidden.",
                    None)

        st.markdown("<hr style='margin:.6rem 0;border:none;border-top:1px "
                    "solid #e3edea'>", unsafe_allow_html=True)

        # ------------------------------------------- confidence explainer
        st.markdown(
            "<div style='font-size:.9rem;color:#3c4f48;line-height:1.5'>"
            "<span style='font-weight:700;color:#22423A'>What the "
            "confidence labels mean:</span> "
            "<span class='conf-badge conf-HIGH'>HIGH</span> comes from a "
            "bill or meter reading. "
            "<span class='conf-badge conf-MEDIUM'>MEDIUM</span> was "
            "converted from an amount you spent. "
            "<span class='conf-badge conf-LOW'>LOW</span> is a broad "
            "estimate from typical usage.</div>",
            unsafe_allow_html=True)
        if wtr.get("optional_water_co2e_kg_year"):
            st.markdown(
                "<div style='font-size:.9rem;color:#3c4f48;padding-top:.35rem;"
                "line-height:1.5'>Getting water to your tap and treating it "
                "afterwards also causes a small amount of emissions (about "
                f"{wtr['optional_water_co2e_kg_year']:,.0f} kg/year for your "
                "use). We show it for interest but leave it <b>out</b> of "
                "your headline footprint, following common practice.</div>",
                unsafe_allow_html=True)

        notes = [n for n in (wtr["notes"] + e["notes"] + c["notes"]) if n]
        if notes:
            st.markdown(
                "<div style='font-weight:700;color:#22423A;font-size:.9rem;"
                "padding-top:.45rem'>Assumptions we made along the way</div>",
                unsafe_allow_html=True)
            for note in notes:
                st.markdown(
                    f"<div style='font-size:.85rem;color:#5c7069;"
                    f"padding:.08rem 0 .08rem .6rem'>• "
                    f"{_friendly_note(note)}</div>", unsafe_allow_html=True)


# =============================== guest view ================================

def _render_guest():
    guest = guest_assessment()
    pages = st.session_state.get("pages", {})
    st.title("Your dashboard")

    if not guest:
        st.info("No results yet — try the assessment first. No account "
                "needed: your dashboard comes alive the moment it's done.")
        c1, c2 = st.columns(2)
        with c1:
            st.page_link(pages["assessment"],
                         label="Try the assessment — no account needed",
                         icon=":material/edit_note:")
        with c2:
            st.page_link(pages["account"], label="Sign in / Sign up",
                         icon=":material/person:")
        st.session_state.pop("scroll_to_goals", None)
        return

    if st.session_state.pop("postcalc_celebrate", False):
        celebrate()
        st.toast("Assessment complete — here's your picture.",
                 icon=":material/check_circle:")

    r = guest["results"]
    inputs = guest["inputs"]

    # clear but non-disruptive invitation — one quiet banner, no popups
    with st.container(border=True):
        c1, c2 = st.columns([3.2, 1.1])
        c1.markdown(
            "**These results live only in this browser session.** A free "
            "account saves this assessment, adds a weekly improvement plan, "
            "achievements, streaks and progress tracking over time.")
        with c2:
            st.page_link(pages["account"], label="Create a free account",
                         icon=":material/person_add:")

    snapshot, _live = _ensure_eval_guest(r, inputs)
    _render_hero(r["score"], snapshot)

    h1, h2 = st.columns([3, 1])
    h1.subheader("Your numbers")
    period = h2.selectbox("Show statistics per", PERIODS,
                          index=PERIODS.index("month"), key="dash_period",
                          label_visibility="collapsed",
                          help="Cards, charts and comparisons all follow "
                               "this period.")
    water_v, elec_v, carbon_v = _render_kpis(r, period)
    _render_compare(water_v, elec_v, carbon_v, period)

    ch1, ch2 = st.columns([1, 1.15], gap="large")
    with ch1:
        _render_donut(r["carbon"])
    with ch2:
        st.subheader("Your trends")
        st.markdown(
            f"{icon('chart', 20, '#9bb0a8')} Trends compare assessments over "
            "time, so they need somewhere to keep your history. Create a "
            "free account and this chart starts growing with your very next "
            "check-in.", unsafe_allow_html=True)

    with st.container(key="band_plan"):
        st.subheader("Your plan for this week", anchor="plan")
        st.markdown(
            "Weekly goals are generated from your own numbers and tracked "
            "between check-ins — that needs an account, so your plan can "
            "follow you across sessions. Everything you've entered today "
            "comes along when you sign up.")
        st.page_link(pages["account"],
                     label="Sign up to unlock your weekly plan",
                     icon=":material/target:")

    _render_transparency(inputs, r)

    if st.session_state.pop("scroll_to_goals", False):
        scroll_to_anchor("plan")


# ============================ authenticated view ===========================

def render():
    user = current_user()
    if user is None:
        _render_guest()
        return

    assessments = db.list_assessments(user["id"])
    if not assessments:
        st.title("Your dashboard")
        st.info("No assessment yet — your dashboard comes alive after the "
                "first one (under 10 minutes).")
        pages = st.session_state.get("pages", {})
        c1, c2 = st.columns(2)
        with c1:
            st.page_link(pages["assessment"], label="Guided questionnaire",
                         icon=":material/edit_note:")
        with c2:
            st.page_link(pages["chat"], label="Chat assessment",
                         icon=":material/forum:")
        st.session_state.pop("scroll_to_goals", None)
        return

    if st.session_state.pop("postcalc_celebrate", False):
        celebrate()
        st.toast("Assessment saved — here's your fresh picture.",
                 icon=":material/check_circle:")

    latest = assessments[-1]
    prev = assessments[-2] if len(assessments) > 1 else None
    r = latest["results"]

    st.title("Your dashboard")
    reminder_banner(user)

    # ================= TOP: mascot + scores | short AI snapshot (§10) ======
    def _refresh_eval():
        db.set_assessment_eval(latest["id"], None)

    snapshot, _live = _ensure_eval(latest)
    _render_hero(r["score"], snapshot, refresh_cb=_refresh_eval)

    # ================= KPI row with period selector ========================
    h1, h2 = st.columns([3, 1])
    h1.subheader("Your numbers")
    period = h2.selectbox(
        "Show statistics per", PERIODS,
        index=PERIODS.index(user.get("unit_period", "month")),
        key="dash_period", label_visibility="collapsed",
        help="Cards, charts and comparisons all follow this period.")

    deltas = None
    if prev:
        pr = prev["results"]
        deltas = (
            _delta(r["water"]["total_water_litres_month"],
                   pr["water"]["total_water_litres_month"]),
            _delta(r["electricity"]["total_electricity_kwh_month"],
                   pr["electricity"]["total_electricity_kwh_month"]),
            _delta(r["carbon"]["net_co2e_kg_year"],
                   pr["carbon"]["net_co2e_kg_year"]),
        )
    water_v, elec_v, carbon_v = _render_kpis(r, period, deltas)

    # ================= band: relatable comparisons =========================
    _render_compare(water_v, elec_v, carbon_v, period)

    # ================= charts: trends | carbon donut (§15) =================
    ch1, ch2 = st.columns([1.15, 1], gap="large")
    with ch1:
        st.subheader("Your trends")
        df = pd.DataFrame([{
            "date": a["created_at"][:16].replace("T", " "),
            "Water (L)": from_month(a["results"]["water"]["total_water_litres_month"], period),
            "Electricity (kWh)": from_month(a["results"]["electricity"]["total_electricity_kwh_month"], period),
            "Carbon (kg CO₂e)": from_year(a["results"]["carbon"]["net_co2e_kg_year"], period),
        } for a in assessments])
        if len(df) < 2:
            st.caption("Trends appear after your second check-in.")
        t1, t2, t3 = st.tabs(["Water", "Electricity", "Carbon"])
        with t1:
            st.line_chart(df, x="date", y="Water (L)", color="#7EC8E3",
                          height=230)
        with t2:
            st.line_chart(df, x="date", y="Electricity (kWh)", color="#F2C14E",
                          height=230)
        with t3:
            st.line_chart(df, x="date", y="Carbon (kg CO₂e)", color="#2E9E63",
                          height=230)
    with ch2:
        _render_donut(r["carbon"])

    # ================= band: merged plan (§12) — anchor for §14 ============
    with st.container(key="band_plan"):
        st.subheader("Your plan for this week", anchor="plan")
        week_goals = db.goals_for_week(user["id"])
        done_now = []
        for g in week_goals:
            cols = st.columns([0.07, 0.71, 0.22])
            checked = cols[0].checkbox(" ", value=(g["status"] == "completed"),
                                       key=f"goal_{g['id']}",
                                       label_visibility="collapsed")
            saving = (f" — saves ~{g['expected_saving']:.0f} "
                      f"{g['expected_saving_unit']}"
                      if g.get("expected_saving") else "")
            style = "~~" if g["status"] == "completed" else ""
            cols[1].markdown(f"{style}**{g['title']}**{style}{saving}")
            cols[2].markdown(pill(g["metric"]), unsafe_allow_html=True)
            if checked and g["status"] != "completed":
                db.set_goal_status(g["id"], "completed")
                done_now.append(g["id"])
            elif not checked and g["status"] == "completed":
                db.set_goal_status(g["id"], "active")
        if done_now:
            st.toast("Goal completed — nicely done.",
                     icon=":material/check_circle:")
            achievement_toast(ach_mod.evaluate_goal_completion(user["id"]))
            st.rerun()
        if not week_goals:
            st.caption("No goals yet this week — add one below.")

        # more opportunities from the deterministic engine, dedupe-filtered
        candidates = pick_weekly_goals(latest["inputs"], r, n=6)
        active = week_goals + [g for g in db.all_goals(user["id"])
                               if g["status"] == "active"]
        fresh = [g for g in candidates if not find_duplicate(g, active)][:3]
        if fresh:
            st.markdown("<div style='margin-top:.4rem;font-weight:700;"
                        "color:#1B5E3B'>More opportunities from your data</div>",
                        unsafe_allow_html=True)
            for i, g in enumerate(fresh):
                cc1, cc2 = st.columns([4.2, 1])
                why = f" — {g['rationale']}" if g.get("rationale") else ""
                saving = (f" · ~{g['expected_saving']:.0f} "
                          f"{g['expected_saving_unit']}"
                          if g.get("expected_saving") else "")
                cc1.markdown(f"**{g['title']}**{saving}  \n"
                             f"<span style='font-size:.82rem;color:#5c7069'>"
                             f"Why: it targets your data directly{why}.</span>",
                             unsafe_allow_html=True)
                if cc2.button("Add", key=f"add_cand_{i}",
                              use_container_width=True):
                    added, skipped = db.save_goals(user["id"], [g])
                    if added:
                        st.toast("Added to this week's plan.",
                                 icon=":material/check_circle:")
                    else:
                        st.toast("That's already in your plan.",
                                 icon=":material/info:")
                    st.rerun()

    if st.session_state.pop("scroll_to_goals", False):
        scroll_to_anchor("plan")

    # ================= achievements (§7) + transparency ====================
    head, side = st.columns([2.6, 1])
    head.subheader("Your achievements")
    streak = db.get_streak(user["id"])
    side.markdown(pill(f"Streak {streak['current']}", "flame")
                  + pill(f"Best {streak['best']}", "trophy"),
                  unsafe_allow_html=True)
    render_achievement_cards(user["id"])

    _render_transparency(latest["inputs"], r)
