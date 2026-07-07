"""Information & education page (spec §12): greenhouse gases, electricity,
water — plus why individual action matters. Visual, short, no jargon."""

import streamlit as st


def render():
    st.title("Understand your impact")
    st.caption("Three short reads — no textbook required.")

    tab_ghg, tab_elec, tab_water, tab_why = st.tabs(
        ["Greenhouse gases", "Electricity", "Water", "Why you matter"])

    with tab_ghg:
        c1, c2 = st.columns([1.4, 1])
        with c1:
            st.markdown("""
### What is CO₂e, actually?
Greenhouse gases (carbon dioxide, methane, nitrous oxide…) trap heat in the
atmosphere like a blanket. Because they differ in strength, we convert them all
into one honest unit: **CO₂-equivalent (CO₂e)** — "as much warming as this many
kilograms of CO₂".

### Where does YOUR CO₂e come from?
The app covers the personal sources that dominate most household footprints:
- **Electricity** — South Africa's grid is coal-heavy: about **0.906 kg CO₂e
  per kWh** (official 2023 grid factor).
- **Transport** — every litre of petrol burns to ~**2.35 kg CO₂e**; diesel
  ~**2.66 kg**.
- **Flights** — a single return Cape Town–Johannesburg economy trip is about
  **320 kg CO₂e** per seat.
- **Diet** — a heavy-meat diet emits roughly **2.5× more** than a vegan one,
  day after day.
- **Heating & consumption** — paraffin, LPG, coal… and the things we buy.
            """)
        with c2:
            with st.container(border=True):
                st.markdown("#### Why cumulative emissions matter")
                st.markdown(
                    "CO₂ hangs around for **centuries** — the climate responds "
                    "to the *total* ever emitted, not this year's number. "
                    "That's also the good news: every kilogram avoided keeps "
                    "helping, forever. Cutting the *biggest* items (one flight, "
                    "a geyser schedule) beats a hundred tiny gestures.")
            with st.container(border=True):
                st.markdown("#### Quick scale check")
                st.markdown("- Boiling a kettle: ~0.1 kg CO₂e\n"
                            "- 10 km city drive: ~1.6 kg\n"
                            "- Month of a 350 kWh home: ~317 kg\n"
                            "- JNB→LHR return in economy: ~2,000 kg")

    with tab_elec:
        c1, c2 = st.columns([1.4, 1])
        with c1:
            st.markdown("""
### kWh is not the same as CO₂e
Your meter measures **consumption** (kWh). The **emissions** depend on how that
electricity was *generated* — the "grid mix". A coal-heavy grid like South
Africa's makes each kWh carry ~0.906 kg CO₂e; the same kWh from your solar
panels carries essentially none in daily operation.

### What actually moves the needle
- **The geyser** — usually the single biggest slice of a SA home's bill. A
  timer, a blanket, or 60 °C→55 °C all pay back fast.
- **Grid mix & renewables** — rooftop solar directly replaces coal-fired kWh.
- **Efficiency** — LED bulbs, full washing loads, pool pump hours.
- **Peak use & loadshedding** — inverters charged from the grid still use grid
  power (we're careful never to double count it); generators add fuel
  emissions on top.
            """)
        with c2:
            with st.container(border=True):
                st.markdown("#### Lower use = real money")
                st.markdown(
                    "On block tariffs, the *last* kWh you buy is the most "
                    "expensive one. Cutting 100 kWh/month can save roughly "
                    "R350-R450 at 2024/25 urban rates — and about **90 kg "
                    "CO₂e**. Same action, two wins.")
            with st.container(border=True):
                st.markdown("#### Uploading beats guessing")
                st.markdown(
                    "A single prepaid receipt or bill gives a HIGH-confidence "
                    "number. Our appliance estimator is honest but rough — "
                    "it says so on the label.")

    with tab_water:
        c1, c2 = st.columns([1.4, 1])
        with c1:
            st.markdown("""
### More than what leaves the tap
Municipal water is **collected, treated, pumped, and treated again** after you
use it — infrastructure and energy at every step. Heating water at home adds
electricity on top (a warm shower is a water *and* energy story).

### Scarcity is local
South Africa is a **water-scarce** country — average rainfall is roughly half
the world average, and Day Zero in Cape Town showed how real the limits are.
The national average sits around **218 litres per person per day**; every
litre below that is genuine headroom for your city.

### High-impact vs low-impact changes
- **Big win — shorter showers:** each minute is ~**8 litres**; a 15-minute
  family habit adds up to thousands of litres a month.
- **Big win — fix leaks:** a running toilet can waste 500+ L/day, silently.
- **Solid — pool cover:** cuts evaporation dramatically.
- **Solid — rainwater & greywater** for the garden.
- **Small — taps off while brushing:** good, but do the big ones first.
            """)
        with c2:
            with st.container(border=True):
                st.markdown("#### The 218 L benchmark")
                st.markdown(
                    "That's the current SA government per-person figure — "
                    "world average is closer to ~173 L. We compare your "
                    "measured use to it on your dashboard, per person, so "
                    "household size never skews the picture.")
            with st.container(border=True):
                st.markdown("#### Rainwater counts differently")
                st.markdown(
                    "Harvested rainwater skips the municipal treatment-and-"
                    "pumping chain, so we track it separately from municipal "
                    "supply instead of pretending it's the same thing.")

    with tab_why:
        st.markdown("""
### The honest answer about individual action

**No — you can't fix the climate alone.** Power stations, transport systems,
cities and industry need government and corporate action, and pretending
otherwise would be unfair to you.

**And yet your choices genuinely count, five ways:**
1. **Direct savings** — your kWh, litres and litres-of-petrol are real. A
   household that halves its geyser time removes actual coal-fired demand.
2. **Money in your pocket** — nearly every impact cut on this app also cuts a
   bill. Efficiency is the rare fight you win twice.
3. **Household ripple** — one person changes a home's defaults: the timer, the
   pool cover, the meal plan. Homes change streets.
4. **Social norms** — visible choices (solar, shared lifts, meat-free days)
   make the next person's choice easier. Norms move markets.
5. **Demand signals** — millions of small purchases pull lower-impact products,
   tariffs and policies into existence.

> Start with your biggest slice, not with perfection. One flight avoided, one
> geyser tamed, one commute shared — measured, tracked, and celebrated.
        """)
