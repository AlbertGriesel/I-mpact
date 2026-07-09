"""Electricity section of the guided questionnaire.

Two clear paths (§3): EITHER upload a bill / prepaid receipt (AI extraction +
user confirmation) OR enter values manually — never both at once. Removing or
replacing an uploaded document immediately clears every value that came from
it. Works for municipal bills, statements and prepaid receipts.

Appliance questions appear only when nothing is measured (spec §9)."""

import streamlit as st

import ai
import database as db
import widgets as w
from schema import OPTIONS
from tariffs import ELECTRICITY_TARIFFS

_UPLOAD = "Upload a bill or prepaid receipt"
_MANUAL = "Enter usage manually"


def _clear_bill_values(data):
    """Wipe everything extracted from an electricity document (§3)."""
    if data.get("measured_source") == "bill":
        data["kwh_month"] = None
        data["measured_source"] = None
        data["kwh_kind"] = OPTIONS["electricity_value_kind"][0]
    data["bill_rand"] = None
    data["bill_uploaded"] = False
    w.set_value("kwh", 0.0)
    w.set_value("elec_rand", 0.0)
    st.session_state.elec_extraction = None
    return data


def _upload_path(data):
    # Consent-critical provider warning stays inline; fuller data-handling
    # detail moves to the section bottom (brief §4/§13).
    note = ai.provider_privacy_note()
    if note:
        st.caption(note)
    up = st.file_uploader(
        "Upload an electricity bill, statement or prepaid receipt(s)",
        type=["pdf", "png", "jpg", "jpeg", "webp"], key="elec_bill_file",
        help="Several prepaid purchases on one photo are summed automatically.")

    sig = st.session_state.get("elec_bill_sig")

    if up is None and sig:
        st.session_state.elec_bill_sig = None
        data = _clear_bill_values(data)
        st.info("Document removed — all values extracted from it were cleared.")
        return data

    if up is not None:
        new_sig = f"{up.name}:{up.size}"
        if sig != new_sig:
            if sig:
                data = _clear_bill_values(data)
            if not ai.assistant_ready():
                st.warning("The assistant is offline — connect a key under "
                           "Settings, or switch to manual entry below.")
                st.session_state.elec_bill_sig = new_sig
            else:
                try:
                    with st.spinner("Reading your document…"):
                        ok, extracted = ai.extract_bill(up.getvalue(), up.name,
                                                        "electricity")
                except Exception:  # noqa: BLE001
                    ok, extracted = False, ("Something went wrong reading that "
                                            "file — try a clearer photo or "
                                            "manual entry.")
                st.session_state.elec_bill_sig = new_sig
                if ok:
                    user = st.session_state.get("user")
                    bill_id = db.save_bill(user["id"], "electricity", up.name,
                                           up.getvalue(), extracted) if user else None
                    st.session_state.elec_extraction = {"values": extracted,
                                                        "bill_id": bill_id}
                else:
                    st.error(extracted)

    pending = st.session_state.get("elec_extraction")
    if pending:
        v = pending["values"]
        st.info("**Please review what we read** — correct anything wrong. "
                "Nothing counts until you confirm.")
        if v.get("uncertain_fields"):
            st.caption("Flagged as uncertain: " + ", ".join(v["uncertain_fields"]))
        if v.get("purchases"):
            st.caption("Prepaid purchases found: " + "; ".join(
                f"{p.get('kwh') or '?'} kWh @ R{p.get('amount_rand') or '?'}"
                for p in v["purchases"]))
        with st.form("elec_bill_review"):
            c1, c2 = st.columns(2)
            with c1:
                kwh = st.number_input("Electricity for the period (kWh)",
                                      min_value=0.0, step=10.0, format="%g",
                                      value=float(v.get("kwh") or 0.0))
                amount = st.number_input("Amount (R)", min_value=0.0, step=10.0,
                                         format="%g",
                                         value=float(v.get("bill_amount_rand") or 0.0))
            with c2:
                utility = st.text_input("Municipality / utility",
                                        value=v.get("municipality_or_utility") or "")
                prepaid = st.checkbox("This is prepaid electricity",
                                      value=bool(v.get("is_prepaid")))
            if v.get("notes"):
                st.caption(f"Notes: {v['notes']}")
            b1, b2 = st.columns(2)
            apply_it = b1.form_submit_button("Looks right — apply",
                                             type="primary",
                                             use_container_width=True)
            drop_it = b2.form_submit_button("Discard", use_container_width=True)
        if apply_it:
            corrected = {"kwh": kwh or None, "bill_amount_rand": amount or None,
                         "municipality_or_utility": utility, "is_prepaid": prepaid}
            if kwh:
                data["kwh_month"] = float(kwh)
                data["measured_source"] = "bill"
                data["kwh_kind"] = "Grid import (bill / prepaid / meter)"
                w.set_value("kwh", float(kwh))
            if amount:
                data["bill_rand"] = float(amount)
                w.set_value("elec_rand", float(amount))
            data["bill_uploaded"] = True
            if utility:
                st.session_state.setdefault("pending_general", {})["municipality"] = utility
            if pending.get("bill_id"):
                db.confirm_bill(pending["bill_id"], corrected)
            user = st.session_state.get("user")
            if user:
                db.award(user["id"], "first_bill", "electricity bill confirmed")
            st.session_state.elec_extraction = None
            st.rerun()
        if drop_it:
            st.session_state.elec_extraction = None
            st.rerun()

    if data.get("bill_uploaded") and data.get("measured_source") == "bill":
        with st.container(border=True):
            st.markdown("**Applied from your document**")
            bits = []
            if data.get("kwh_month"):
                bits.append(f"{data['kwh_month']:g} kWh/month (grid import)")
            if data.get("bill_rand"):
                bits.append(f"R{data['bill_rand']:g}")
            st.markdown(" · ".join(bits) or "—")
            st.caption("Remove the file above to clear these values.")
    return data


def _manual_path(data):
    c1, c2 = st.columns(2)
    with c1:
        kwh = w.number("Monthly electricity (kWh) — 0 if unknown", "kwh",
                       data.get("kwh_month"), minv=0.0, maxv=20000.0, step=10.0)
    with c2:
        rand = w.number(
            "Monthly spend (R) — fallback if kWh unknown", "elec_rand",
            data.get("bill_rand"), minv=0.0, maxv=100000.0, step=50.0,
            help="Converted with a utility-specific tariff. Supported: "
                 + "; ".join(t["label"].split(" (")[0]
                             for t in ELECTRICITY_TARIFFS.values()))
    data["kwh_month"] = kwh if kwh > 0 else None
    data["measured_source"] = "manual" if kwh > 0 else None
    data["bill_rand"] = rand if rand > 0 else None
    data["bill_uploaded"] = False

    if data["kwh_month"]:
        data["kwh_kind"] = w.radio(
            "That kWh figure is…", "kwh_kind", OPTIONS["electricity_value_kind"],
            data.get("kwh_kind"),
            help="Matters for solar: a bill already shows only grid purchases, "
                 "so we never subtract your solar share twice.")
    return data


def render(data):
    st.header("Electricity")
    st.caption("Prepaid receipts and bills give the best numbers — kWh beats "
               "rands, rands beat guessing.")

    default_mode = (_MANUAL if (data.get("measured_source") == "manual"
                                or (data.get("bill_rand")
                                    and not data.get("bill_uploaded")))
                    else _UPLOAD)
    mode = w.radio("How would you like to add your electricity usage?",
                   "elec_mode", [_UPLOAD, _MANUAL], default_mode)

    if mode == _UPLOAD:
        data = _upload_path(data)
    else:
        data = _manual_path(data)

    data = renewable_and_backup(data)

    has_measured = bool(data.get("kwh_month") or data.get("bill_rand"))
    if not has_measured:
        _appliance_estimate_form(data)
    else:
        st.success("Measured electricity captured — appliance questions skipped.")

    # data-handling detail at the bottom of the section (brief §4/§13)
    if mode == _UPLOAD:
        from views.common import privacy_note
        st.divider()
        privacy_note("upload")
    return data


def renewable_and_backup(data, *, renewable_label=None):
    """Renewable + backup-power sub-section, shared by the household and
    business electricity steps (solar, generators and loadshedding backup
    matter for both)."""
    st.subheader("Renewable electricity")
    data["renewable_source"] = w.select(
        renewable_label or "Do you generate renewable electricity?", "renew_src",
        OPTIONS["renewable_source"], data.get("renewable_source", "None"))
    if data["renewable_source"] != "None":
        data["renewable_percentage"] = w.slider_int(
            "Roughly what % of your electricity does it supply?", "renew_pct",
            data.get("renewable_percentage"), minv=0, maxv=100)
    else:
        data["renewable_percentage"] = 0

    st.subheader("Backup power and loadshedding")
    data["backup_power"] = w.select(
        "What do you use during outages?", "backup",
        OPTIONS["backup_power"], data.get("backup_power", "None"))

    if data["backup_power"] == "Generator":
        c1, c2, c3 = st.columns(3)
        with c1:
            data["generator_fuel_type"] = w.select(
                "Generator fuel", "gen_fuel", OPTIONS["generator_fuel_type"],
                data.get("generator_fuel_type", "Petrol"))
        with c2:
            litres = w.number("Fuel per month (litres) — best answer",
                              "gen_litres", data.get("generator_litres_per_month"),
                              minv=0.0, maxv=2000.0, step=1.0)
            data["generator_litres_per_month"] = litres if litres > 0 else None
        with c3:
            hours = w.number("…or hours run per month", "gen_hours",
                             data.get("generator_hours_per_month"),
                             minv=0.0, maxv=744.0, step=1.0,
                             help="Used only if litres are unknown (falls back "
                                  "to 1.5 L/hour, or your generator's own rate "
                                  "below).")
            data["generator_hours_per_month"] = hours if hours > 0 else None
        if data["generator_hours_per_month"] and not data["generator_litres_per_month"]:
            rate = w.slider_float("Manufacturer fuel rate (L/hour), if known",
                                  "gen_rate",
                                  data.get("generator_fuel_rate_l_per_hour") or 0.0,
                                  minv=0.0, maxv=10.0, step=0.1)
            data["generator_fuel_rate_l_per_hour"] = rate if rate > 0 else None
        data["generator_coverage"] = w.radio(
            "It powers…", "gen_cov", OPTIONS["generator_coverage"],
            data.get("generator_coverage", "Essential loads only"))
    elif data["backup_power"] in ("Inverter and battery", "Solar battery backup",
                                  "UPS"):
        c1, c2, c3 = st.columns(3)
        with c1:
            data["backup_share_percent"] = w.slider_int(
                "Share of electricity it supplies during outages (%)",
                "backup_share", data.get("backup_share_percent"), minv=0, maxv=100)
        with c2:
            data["generator_coverage"] = w.radio(
                "It powers…", "backup_cov", OPTIONS["generator_coverage"],
                data.get("generator_coverage", "Essential loads only"))
        with c3:
            default_charge = ("Solar" if data["backup_power"] == "Solar battery backup"
                              else data.get("backup_charge_source", "Grid"))
            data["backup_charge_source"] = w.radio(
                "Charged from…", "backup_chg", OPTIONS["backup_charge_source"],
                default_charge)
        st.caption("Grid-charged backup is already inside your bill's kWh — we "
                   "never count it twice.")
    return data


def _appliance_estimate_form(data):
    st.subheader("Quick estimate instead")
    st.caption("No measured data, so we estimate from your major appliances "
               "(labelled LOW confidence — a single bill upload beats this).")
    if True:
        data["home_size"] = w.text(
            "Home size (e.g. 3-bedroom house, 80 m² flat)", "home_size",
            data.get("home_size"))
        g1, g2 = st.columns(2)
        with g1:
            data["electric_geyser"] = w.check("Electric geyser", "geyser",
                                              data.get("electric_geyser"))
            if data["electric_geyser"]:
                data["geyser_hours_per_day"] = w.slider_float(
                    "Geyser heating hours per day", "geyser_h",
                    data.get("geyser_hours_per_day") or 3.0, minv=0.0, maxv=24.0)
            data["electric_stove"] = w.check("Electric stove / oven", "stove",
                                             data.get("electric_stove"))
            if data["electric_stove"]:
                data["stove_minutes_per_day"] = w.slider_int(
                    "Stove-plate minutes per day", "stove_min",
                    data.get("stove_minutes_per_day") or 45, minv=0, maxv=180,
                    step=5)
                oven = w.slider_float("Oven hours per week", "oven_h",
                                      data.get("oven_hours_per_week") or 2.0,
                                      minv=0.0, maxv=20.0)
                data["oven_hours_per_week"] = oven if oven > 0 else None
        with g2:
            data["air_conditioner"] = w.check("Air conditioner", "aircon",
                                              data.get("air_conditioner"))
            if data["air_conditioner"]:
                data["aircon_kw"] = w.slider_float(
                    "Aircon rated power (kW)", "aircon_kw",
                    data.get("aircon_kw") or 1.5, minv=0.5, maxv=10.0)
                data["aircon_hours_per_day"] = w.slider_float(
                    "Hours per day when used", "aircon_h",
                    data.get("aircon_hours_per_day") or 4.0, minv=0.0, maxv=24.0)
                data["aircon_months_per_year"] = w.slider_int(
                    "Months per year you use it", "aircon_m",
                    data.get("aircon_months_per_year") or 4, minv=0, maxv=12)
            data["pool_pump"] = w.check("Pool pump", "pump",
                                        data.get("pool_pump"))
            if data["pool_pump"]:
                data["pool_pump_watts"] = w.slider_int(
                    "Pump wattage (W)", "pump_w",
                    data.get("pool_pump_watts") or 750, minv=100, maxv=2500,
                    step=50)
                data["pool_pump_hours_per_day"] = w.slider_float(
                    "Pump hours per day", "pump_h",
                    data.get("pool_pump_hours_per_day") or 6.0, minv=0.0,
                    maxv=24.0)
        st.caption("A 150 kWh/month base load (fridge, lights, electronics) is "
                   "added automatically — a rough MVP assumption.")
    return data
