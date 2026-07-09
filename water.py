"""Water section of the guided questionnaire.

Two clear paths (§2): EITHER upload a bill (AI extraction + user confirmation)
OR enter values manually — never both at once. Removing or replacing an
uploaded bill immediately clears every value that came from it, so stale
extractions can never linger invisibly in the assessment.

Estimation questions appear ONLY when no measured data exists (spec §8)."""

import streamlit as st

import ai
import database as db
import widgets as w
from tariffs import WATER_TARIFFS

_UPLOAD = "Upload a bill (photo or PDF)"
_MANUAL = "Enter usage manually"


def _clear_bill_values(data):
    """Wipe everything that was extracted from a water bill: assessment
    fields, widget state and the confirmation interface (§2)."""
    if data.get("measured_source") == "bill":
        data["water_kl_month"] = None
        data["measured_source"] = None
    data["water_bill_rand"] = None
    data["bill_uploaded"] = False
    w.set_value("water_kl", 0.0)
    w.set_value("water_rand", 0.0)
    st.session_state.water_extraction = None
    return data


def _upload_path(data):
    from views.common import privacy_note
    privacy_note("upload")
    note = ai.provider_privacy_note()
    if note:
        st.caption(note)
    up = st.file_uploader(
        "Upload a municipal water bill or statement",
        type=["pdf", "png", "jpg", "jpeg", "webp"], key="water_bill_file",
        help="We read it for you and you confirm every value before it counts.")

    sig = st.session_state.get("water_bill_sig")

    # file removed -> clear everything that bill produced
    if up is None and sig:
        st.session_state.water_bill_sig = None
        data = _clear_bill_values(data)
        st.info("Bill removed — all values extracted from it were cleared.")
        return data

    if up is not None:
        new_sig = f"{up.name}:{up.size}"
        if sig != new_sig:
            # a different bill replaces the previous one entirely
            if sig:
                data = _clear_bill_values(data)
            if not ai.assistant_ready():
                st.warning("The assistant is offline — connect a key under "
                           "Settings, or switch to manual entry below.")
                st.session_state.water_bill_sig = new_sig
            else:
                try:
                    with st.spinner("Reading your bill…"):
                        ok, extracted = ai.extract_bill(up.getvalue(), up.name,
                                                        "water")
                except Exception:  # noqa: BLE001 — never crash the wizard
                    ok, extracted = False, ("Something went wrong reading that "
                                            "file — try a clearer photo or "
                                            "manual entry.")
                st.session_state.water_bill_sig = new_sig
                if ok:
                    user = st.session_state.get("user")
                    bill_id = db.save_bill(user["id"], "water", up.name,
                                           up.getvalue(), extracted) if user else None
                    st.session_state.water_extraction = {"values": extracted,
                                                         "bill_id": bill_id}
                else:
                    st.error(extracted)

    pending = st.session_state.get("water_extraction")
    if pending:
        v = pending["values"]
        st.info("**Please review what we read from your bill** — correct "
                "anything that's wrong. Nothing counts until you confirm.")
        if v.get("uncertain_fields"):
            st.caption("Flagged as uncertain: " + ", ".join(v["uncertain_fields"]))
        with st.form("water_bill_review"):
            c1, c2 = st.columns(2)
            with c1:
                kl = st.number_input("Water consumption (kL for the period)",
                                     min_value=0.0, step=0.5, format="%g",
                                     value=float(v.get("water_kl") or 0.0))
                amount = st.number_input("Bill amount (R)", min_value=0.0,
                                         step=10.0, format="%g",
                                         value=float(v.get("bill_amount_rand") or 0.0))
            with c2:
                muni = st.text_input("Municipality on the bill",
                                     value=v.get("municipality") or "")
                st.text_input("Billing period", value=" – ".join(
                    x for x in [v.get("period_start"), v.get("period_end")] if x),
                    disabled=True)
            if v.get("notes"):
                st.caption(f"Notes: {v['notes']}")
            b1, b2 = st.columns(2)
            apply_it = b1.form_submit_button("Looks right — apply",
                                             type="primary",
                                             use_container_width=True)
            drop_it = b2.form_submit_button("Discard", use_container_width=True)
        if apply_it:
            corrected = {"water_kl": kl or None, "bill_amount_rand": amount or None,
                         "municipality": muni}
            if kl:
                data["water_kl_month"] = float(kl)
                data["measured_source"] = "bill"
                w.set_value("water_kl", float(kl))
            if amount:
                data["water_bill_rand"] = float(amount)
                w.set_value("water_rand", float(amount))
            data["bill_uploaded"] = True
            if muni:
                st.session_state.setdefault("pending_general", {})["municipality"] = muni
            if pending.get("bill_id"):
                db.confirm_bill(pending["bill_id"], corrected)
            user = st.session_state.get("user")
            if user:
                db.award(user["id"], "first_bill", "water bill confirmed")
            st.session_state.water_extraction = None
            st.rerun()
        if drop_it:
            st.session_state.water_extraction = None
            st.rerun()

    # confirmed-values card (visible while the bill's data is active)
    if data.get("bill_uploaded") and data.get("measured_source") == "bill":
        with st.container(border=True):
            st.markdown("**Applied from your bill**")
            bits = []
            if data.get("water_kl_month"):
                bits.append(f"{data['water_kl_month']:g} kL/month")
            if data.get("water_bill_rand"):
                bits.append(f"R{data['water_bill_rand']:g}")
            st.markdown(" · ".join(bits) or "—")
            st.caption("Remove the file above to clear these values.")
    return data


def _manual_path(data):
    c1, c2 = st.columns(2)
    with c1:
        kl = w.number(
            "Monthly water use (kilolitres) — 0 if unknown", "water_kl",
            data.get("water_kl_month"), minv=0.0, maxv=500.0, step=0.5,
            help="1 kL = 1,000 litres. Find it on your municipal bill or meter.")
    with c2:
        rand = w.number(
            "Monthly water bill (R) — fallback if kL unknown", "water_rand",
            data.get("water_bill_rand"), minv=0.0, maxv=100000.0, step=10.0,
            help="Converted with your municipality's block tariff. Supported: "
                 + "; ".join(t["label"].split(" (")[0] for t in WATER_TARIFFS.values()))
    data["water_kl_month"] = kl if kl > 0 else None
    data["measured_source"] = "manual" if kl > 0 else None
    data["water_bill_rand"] = rand if rand > 0 else None
    data["bill_uploaded"] = False
    return data


def render(data):
    """Render the water screen; mutates and returns the water section dict."""
    st.header("Water")
    st.caption("Measured data beats estimates — a bill or meter reading gives a "
               "HIGH-confidence result.")

    default_mode = (_MANUAL if (data.get("measured_source") == "manual"
                                or (data.get("water_bill_rand")
                                    and not data.get("bill_uploaded")))
                    else _UPLOAD)
    mode = w.radio("How would you like to add your water usage?", "water_mode",
                   [_UPLOAD, _MANUAL], default_mode)

    if mode == _UPLOAD:
        data = _upload_path(data)
    else:
        data = _manual_path(data)

    st.subheader("Rainwater harvesting")
    data["uses_rainwater"] = w.check(
        "We harvest rainwater", "rainwater", data.get("uses_rainwater"),
        help="Rainwater carries a far lower environmental burden than "
             "municipally treated water.")
    if data["uses_rainwater"]:
        data["rainwater_percentage"] = w.slider_int(
            "About what % of household water comes from rainwater?",
            "rain_pct", data.get("rainwater_percentage"), minv=0, maxv=90)
    else:
        data["rainwater_percentage"] = 0

    has_measured = bool(data.get("water_kl_month") or data.get("water_bill_rand"))
    if not has_measured:
        st.subheader("Quick estimate instead")
        st.caption("Only needed because we have no measured data — a handful of "
                   "questions, nothing more.")
        c1, c2 = st.columns(2)
        with c1:
            mins = w.slider_int("Average shower length (minutes)",
                                "shower_min", data.get("shower_minutes"),
                                minv=0, maxv=90)
        with c2:
            per_week = w.slider_int("Showers per week (per person)",
                                    "shower_wk", data.get("showers_per_week"),
                                    minv=0, maxv=21)
        data["shower_minutes"] = mins if mins > 0 else None
        data["showers_per_week"] = per_week if per_week > 0 else None
    else:
        st.success("Measured water data captured — estimation questions skipped.")

    c3, c4 = st.columns(2)
    with c3:
        data["garden_irrigation"] = w.check(
            "We irrigate a garden", "garden", data.get("garden_irrigation"))
    with c4:
        data["swimming_pool"] = w.check(
            "We have a swimming pool", "pool", data.get("swimming_pool"))
    st.caption("Garden and pool answers guide the assistant's advice — the app "
               "doesn't turn a yes/no into invented litres.")
    return data
