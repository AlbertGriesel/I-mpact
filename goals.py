"""
Weekly goal generation (spec §13.7).

Goals are specific, measurable and practical. The expected environmental
saving comes from the deterministic factors in factors.py — the AI may help
phrase and discuss goals, but never invents the numbers.
"""

import re

from factors import F, DIET_FACTOR_KEYS, PUBLIC_TRANSPORT_FACTOR_KEYS

# ---------------------------------------------------------------------------
# Duplicate detection (§13): semantically identical goals must never be added
# twice. "Reduce showers to 8 minutes" == "Keep shower time under 8 minutes".
# ---------------------------------------------------------------------------

_STOPWORDS = {"the", "a", "an", "to", "of", "per", "and", "or", "in", "on",
              "for", "with", "this", "that", "your", "my", "our", "week",
              "day", "daily", "weekly", "each", "every", "at", "by", "it"}

# canonical forms so "cut ... one hour" matches "reduce ... 1 hour"
_CANON = {"one": "1", "two": "2", "three": "3", "four": "4", "five": "5",
          "six": "6", "seven": "7", "eight": "8", "nine": "9", "ten": "10",
          "cut": "reduce", "lower": "reduce", "trim": "reduce",
          "decrease": "reduce", "drop": "reduce", "shorten": "reduce",
          "keep": "limit", "cap": "limit", "under": "limit", "below": "limit",
          "min": "minute", "mins": "minute", "hr": "hour", "hrs": "hour"}


def _tokens(title):
    words = re.findall(r"[a-z0-9]+", (title or "").lower())
    out = set()
    for word in words:
        if word in _STOPWORDS:
            continue
        word = _CANON.get(word, word)
        if len(word) > 3 and word.endswith("s"):   # crude plural stem
            word = word[:-1]
        out.add(word)
    return out


def is_similar_goal(title_a, title_b):
    """True when two goal titles describe the same action."""
    ta, tb = _tokens(title_a), _tokens(title_b)
    if not ta or not tb:
        return False
    inter = len(ta & tb)
    jaccard = inter / len(ta | tb)
    containment = inter / min(len(ta), len(tb))
    return jaccard >= 0.5 or containment >= 0.65


def find_duplicate(candidate, existing_goals):
    """Return the existing goal that duplicates `candidate`, or None.
    `existing_goals` are DB rows or dicts with 'title' (and optional 'metric')."""
    for g in existing_goals:
        if g.get("metric") and candidate.get("metric") and \
                g["metric"] != candidate["metric"]:
            continue
        if is_similar_goal(candidate.get("title", ""), g.get("title", "")):
            return g
    return None


def generate_goal_candidates(inputs, results):
    """Return a small, ALREADY-RELEVANT candidate set (§2.5): each goal is only
    produced when the user's data makes it meaningful (e.g. a geyser goal needs
    an electric geyser; a flight goal needs flights). Every goal carries three
    ranking hints used by the priority model:

      * addresses    — the footprint sub-category it targets
      * feasibility   — 1 (hard to pull off) … 5 (very doable)
      * difficulty    — 1 (trivial) … 5 (major cost/effort/infrastructure)

    Each goal: {title, metric, target_value, target_unit, expected_saving,
                expected_saving_unit, rationale, addresses, feasibility,
                difficulty}
    """
    if inputs["general"].get("account_type") == "business":
        return _business_goal_candidates(inputs, results)

    goals = []
    w_in, e_in, t_in, l_in = (inputs["water"], inputs["electricity"],
                              inputs["transport"], inputs["lifestyle"])
    water, elec, carbon = results["water"], results["electricity"], results["carbon"]

    # --- Water: shower time (only when we know their shower habits)
    if w_in.get("shower_minutes") and w_in.get("showers_per_week"):
        weekly_min = float(w_in["shower_minutes"]) * float(w_in["showers_per_week"])
        cut = min(15.0, max(5.0, round(weekly_min * 0.15)))
        saving_l = cut * F("shower_l_per_minute")
        goals.append({
            "title": f"Trim {cut:.0f} shower-minutes off your week "
                     f"(saves ~{saving_l:.0f} L)",
            "metric": "water", "target_value": cut, "target_unit": "minutes/week",
            "expected_saving": round(saving_l, 1), "expected_saving_unit": "L/week",
            "rationale": "8 L/minute shower flow (Eskom assumption)",
            "addresses": "shower", "feasibility": 5, "difficulty": 2,
        })
    elif water["water_litres_person_day"] > 218:
        goals.append({
            "title": "Track one week of showers — note minutes per shower",
            "metric": "water", "target_value": 7, "target_unit": "showers logged",
            "expected_saving": None, "expected_saving_unit": None,
            "rationale": "Measured habits unlock accurate water goals",
            "addresses": "shower", "feasibility": 4, "difficulty": 1,
        })

    # --- Water: pool cover / irrigation context
    if w_in.get("swimming_pool"):
        goals.append({
            "title": "Cover the pool (or log evaporation top-ups this week)",
            "metric": "water", "target_value": 1, "target_unit": "action",
            "expected_saving": None, "expected_saving_unit": None,
            "rationale": "Pool evaporation varies too much to promise a number — "
                         "covering typically cuts top-up water sharply",
            "addresses": "pool", "feasibility": 3, "difficulty": 3,
        })

    # --- Electricity: geyser
    if e_in.get("electric_geyser"):
        saving_kwh = F("geyser_kw") * 1.0 * 7  # one hour less per day
        saving_co2 = saving_kwh * F("sa_grid_kgco2e_per_kwh")
        goals.append({
            "title": "Cut geyser heating by 1 hour/day (timer or manual)",
            "metric": "electricity", "target_value": 7, "target_unit": "hours/week",
            "expected_saving": round(saving_kwh, 1), "expected_saving_unit":
                f"kWh/week (~{saving_co2:.0f} kg CO2e)",
            "rationale": "3 kW element assumption × SA grid factor 0.906",
            "addresses": "geyser", "feasibility": 4, "difficulty": 2,
        })

    # --- Electricity: pool pump
    if e_in.get("pool_pump"):
        watts = float(e_in.get("pool_pump_watts") or 750)
        saving_kwh = watts / 1000.0 * 1.0 * 7
        goals.append({
            "title": "Run the pool pump 1 hour less per day",
            "metric": "electricity", "target_value": 7, "target_unit": "pump-hours/week",
            "expected_saving": round(saving_kwh, 1), "expected_saving_unit": "kWh/week",
            "rationale": f"{watts:.0f} W pump × 7 hours",
            "addresses": "pool_pump", "feasibility": 4, "difficulty": 2,
        })

    # --- Carbon: car trips
    v = t_in["vehicle"]
    if v.get("owns_vehicle") and v.get("annual_km"):
        detail = (carbon.get("detail") or {}).get("vehicle") or {}
        l100 = detail.get("l_per_100km") or v.get("l_per_100km")
        if l100:
            km_cut = 10.0  # two short trips
            fuel_l = km_cut * float(l100) / 100.0
            saving = fuel_l * F("petrol_kgco2e_per_l")
            goals.append({
                "title": "Replace two short car trips (~10 km) with walking, "
                         "cycling or shared transport",
                "metric": "carbon", "target_value": 2, "target_unit": "trips",
                "expected_saving": round(saving, 1),
                "expected_saving_unit": "kg CO2e/week",
                "rationale": f"{l100} L/100km × combustion factor",
                "addresses": "personal_vehicle", "feasibility": 3, "difficulty": 3,
            })

    # --- Carbon: flights (only for people who actually fly — §2.1 example)
    flights = t_in.get("flights") or []
    if flights:
        total_trips = sum(int(f.get("trips_per_year") or 0) for f in flights)
        fl_co2 = carbon["breakdown"].get("flights", 0.0)
        goals.append({
            "title": "Swap one short-haul trip for a video call, or offset a "
                     "flight you truly can't avoid",
            "metric": "carbon", "target_value": 1, "target_unit": "flight",
            "expected_saving": round(fl_co2 / total_trips, 1) if total_trips else None,
            "expected_saving_unit": "kg CO2e per flight avoided",
            "rationale": "Flights are a large, lumpy carbon source",
            "addresses": "flights", "feasibility": 2, "difficulty": 4,
        })

    # --- Carbon: one lower-impact meal that fits the current diet
    diet = l_in.get("diet", "Average diet")
    ladder = ["Heavy meat eater", "Average diet", "Mostly chicken",
              "Pescatarian", "Vegetarian", "Vegan"]
    if diet in ladder and diet != "Vegan":
        nxt = ladder[ladder.index(diet) + 1]
        delta_day = F(DIET_FACTOR_KEYS[diet]) - F(DIET_FACTOR_KEYS[nxt])
        saving = delta_day  # one full day per week eating one step lighter
        goals.append({
            "title": f"Plan one '{nxt.lower()}' day this week",
            "metric": "carbon", "target_value": 1, "target_unit": "day",
            "expected_saving": round(saving, 1), "expected_saving_unit": "kg CO2e/week",
            "rationale": "Difference between diet-category factors for one day",
            "addresses": "diet_and_food_waste", "feasibility": 4, "difficulty": 2,
        })

    # --- Carbon: generator dependence
    if e_in.get("backup_power") == "Generator" and elec.get("generator_litres_month"):
        litres_week = float(elec["generator_litres_month"]) * 12 / 52
        cut = round(litres_week * 0.2, 1)
        if cut >= 0.5:
            saving = cut * F("petrol_kgco2e_per_l")
            goals.append({
                "title": f"Shift {cut} L of generator run-time to daylight/battery "
                         "hours this week",
                "metric": "carbon", "target_value": cut, "target_unit": "litres",
                "expected_saving": round(saving, 1),
                "expected_saving_unit": "kg CO2e/week",
                "rationale": "20% of your typical weekly generator fuel",
                "addresses": "generator", "feasibility": 3, "difficulty": 3,
            })

    # --- Always-available fallback goals (low-effort maintenance; matter most
    #     for already-low-impact users who have no big lever to pull — §11 E)
    if not any(g["metric"] == "electricity" for g in goals):
        goals.append({
            "title": "Switch everything off at the wall overnight (no standby)",
            "metric": "electricity", "target_value": 7, "target_unit": "nights",
            "expected_saving": round(0.3 * 7, 1), "expected_saving_unit": "kWh/week",
            "rationale": "Typical standby load ~0.3 kWh/night ([approximation])",
            "addresses": "standby", "feasibility": 5, "difficulty": 1,
        })
    if not any(g["metric"] == "water" for g in goals):
        goals.append({
            "title": "Catch cold shower-warm-up water in a bucket for the garden",
            "metric": "water", "target_value": 7, "target_unit": "showers",
            "expected_saving": round(5 * 7, 1), "expected_saving_unit": "L/week",
            "rationale": "~5 L of warm-up water per shower ([approximation])",
            "addresses": "shower", "feasibility": 4, "difficulty": 1,
        })
    return goals


def _business_goal_candidates(inputs, results):
    """Business-appropriate weekly actions (spec §4-5). Sector-conditional, so
    a restaurant gets refrigeration/food-waste goals and an office doesn't.
    Savings are stated where the deterministic data supports them; otherwise
    the goal is an honest 'measure / act' step without an invented number."""
    from schema import business_sector_flags
    g = inputs["general"]
    e_in, b = inputs["electricity"], inputs.get("business", {})
    elec, carbon = results["electricity"], results["carbon"]
    flags = business_sector_flags(g.get("sector"))
    goals = []

    # --- Electricity efficiency (always relevant to a business)
    goals.append({
        "title": "Audit your biggest electrical loads and switch to LED + "
                 "timers/occupancy sensors",
        "metric": "electricity", "target_value": 1, "target_unit": "audit",
        "expected_saving": None, "expected_saving_unit": None,
        "rationale": "Lighting and always-on loads are common quick wins",
        "addresses": "electricity", "feasibility": 4, "difficulty": 2,
    })
    if e_in.get("renewable_source", "None") == "None":
        goals.append({
            "title": "Get a rooftop-solar or renewable-tariff quote for the "
                     "premises",
            "metric": "electricity", "target_value": 1, "target_unit": "quote",
            "expected_saving": None, "expected_saving_unit": None,
            "rationale": "Solar offsets grid emissions and loadshedding risk",
            "addresses": "electricity", "feasibility": 3, "difficulty": 4,
        })
    if flags["refrigeration"] and b.get("refrigeration"):
        goals.append({
            "title": "Service refrigeration seals, coils and setpoints this week",
            "metric": "electricity", "target_value": 1, "target_unit": "service",
            "expected_saving": None, "expected_saving_unit": None,
            "rationale": "Refrigeration is a major continuous load; maintenance "
                         "cuts waste",
            "addresses": "refrigeration", "feasibility": 4, "difficulty": 2,
        })

    # --- Water
    goals.append({
        "title": "Read the water meter at open and close for a week to catch "
                 "leaks and overnight flow",
        "metric": "water", "target_value": 7, "target_unit": "readings",
        "expected_saving": None, "expected_saving_unit": None,
        "rationale": "Overnight flow on a closed premises usually means a leak",
        "addresses": "water", "feasibility": 5, "difficulty": 1,
    })
    if flags["process_water"] and b.get("process_water_kl_month"):
        goals.append({
            "title": "Identify one process-water stream to reuse or recycle",
            "metric": "water", "target_value": 1, "target_unit": "stream",
            "expected_saving": None, "expected_saving_unit": None,
            "rationale": "Process water is often the largest business draw",
            "addresses": "process_water", "feasibility": 3, "difficulty": 3,
        })
    if flags["irrigation"] and b.get("irrigation_kl_month"):
        goals.append({
            "title": "Water landscaping at dawn/dusk and fix irrigation leaks "
                     "this week",
            "metric": "water", "target_value": 1, "target_unit": "check",
            "expected_saving": None, "expected_saving_unit": None,
            "rationale": "Irrigation timing and leaks are a large, controllable "
                         "outdoor draw",
            "addresses": "irrigation", "feasibility": 4, "difficulty": 2,
        })

    # --- Fleet
    fleet = inputs["transport"].get("fleet") or []
    fleet_co2 = carbon["breakdown"].get("fleet", 0.0)
    if fleet and fleet_co2 > 0:
        weekly = fleet_co2 / 52.0
        saving = round(weekly * 0.05, 1)   # ~5% from routing/tyres/idling
        goals.append({
            "title": "Cut fleet fuel ~5%: route planning, tyre pressure and "
                     "no-idling this week",
            "metric": "carbon", "target_value": 5, "target_unit": "% fuel",
            "expected_saving": saving if saving >= 0.5 else None,
            "expected_saving_unit": "kg CO2e/week" if saving >= 0.5 else None,
            "rationale": "5% of your weekly fleet emissions",
            "addresses": "fleet", "feasibility": 4, "difficulty": 2,
        })

    # --- Waste & operations
    if b.get("waste_kg_month") and not b.get("recycles"):
        goals.append({
            "title": "Set up separated recycling bins for staff and customers",
            "metric": "carbon", "target_value": 1, "target_unit": "setup",
            "expected_saving": None, "expected_saving_unit": None,
            "rationale": "Diverting waste from landfill cuts methane emissions",
            "addresses": "waste", "feasibility": 4, "difficulty": 2,
        })
    if flags["food_waste"] and b.get("food_waste_kg_month"):
        goals.append({
            "title": "Track and cut food waste by 20% (portioning, prep-to-order)",
            "metric": "carbon", "target_value": 20, "target_unit": "% food waste",
            "expected_saving": None, "expected_saving_unit": None,
            "rationale": "Food waste carries the emissions of producing it",
            "addresses": "food_waste", "feasibility": 3, "difficulty": 3,
        })

    # --- Always-available fallback
    goals.append({
        "title": "Assign one person to log monthly water and electricity bills",
        "metric": "electricity", "target_value": 1, "target_unit": "owner",
        "expected_saving": None, "expected_saving_unit": None,
        "rationale": "You can't manage what you don't measure",
        "addresses": "electricity", "feasibility": 5, "difficulty": 1,
    })
    return goals


# ---------------------------------------------------------------------------
# Priority model (§2): Priority = (Impact × Feasibility × Relevance) ÷ Difficulty
# All scores are 1–5. The model is deterministic and never raises, so ranking
# works offline; the AI layer can OPTIONALLY refine relevance + reason on top.
# ---------------------------------------------------------------------------

_CATEGORY_PHRASE = {
    "shower": "water use", "pool": "water use", "pool_pump": "electricity use",
    "geyser": "electricity use (the geyser is usually a home's biggest load)",
    "standby": "electricity use", "personal_vehicle": "driving",
    "diet_and_food_waste": "diet", "generator": "generator fuel use",
    "flights": "air travel",
}

# Business goal categories get their own explanation phrases and, below, their
# own prominence/relevance model — the household benchmarks (218 L/person/day,
# 350 kWh/household/month) do not describe an organisation (spec §5).
_BUSINESS_CATEGORY_PHRASE = {
    "electricity": "electricity use",
    "refrigeration": "refrigeration load",
    "water": "water use",
    "process_water": "process-water use",
    "irrigation": "irrigation water",
    "fleet": "fleet fuel use",
    "waste": "waste",
    "food_waste": "food waste",
}

# Which intensity domain a business goal's category is judged against.
_BIZ_ADDR_DOMAIN = {
    "electricity": "elec", "refrigeration": "elec",
    "water": "water", "process_water": "water", "irrigation": "water",
    "fleet": "carbon", "waste": "carbon", "food_waste": "carbon",
}
# Carbon-domain business categories → the carbon breakdown key they map to.
_BIZ_ADDR_BREAKDOWN = {"fleet": "fleet", "waste": "waste", "food_waste": "waste"}


def _is_business(inputs):
    return (inputs or {}).get("general", {}).get("account_type") == "business"


def _norm(title):
    return re.sub(r"\s+", " ", (title or "").strip().lower())


def _band(x, thresholds):
    """thresholds: descending [(cutoff, score), …]; returns 1 below the last."""
    for cut, score in thresholds:
        if x >= cut:
            return score
    return 1


def _prominence(goal, inputs, results):
    """How large is this goal's category FOR THIS USER (1–5)? Captures both
    'how big the problem is' and 'are they already doing well' (§2.1).

    Personal accounts judge against household benchmarks; business accounts
    judge against per-m² / per-employee sector intensities (see
    _business_prominence) — never household litres/person or kWh/household."""
    if _is_business(inputs):
        return _business_prominence(goal, inputs, results)
    m = goal["metric"]
    if m == "water":
        r = (results["water"]["water_litres_person_day"] or 0) / 218.0
        return _band(r, [(1.4, 5), (1.1, 4), (0.9, 3), (0.7, 2)])
    if m == "electricity":
        r = (results["electricity"]["total_electricity_kwh_month"] or 0) / 350.0
        return _band(r, [(1.6, 5), (1.15, 4), (0.8, 3), (0.5, 2)])
    bd = results["carbon"]["breakdown"]
    total = sum(bd.values()) or 1.0
    share = bd.get(goal.get("addresses"), 0.0) / total
    return _band(share, [(0.35, 5), (0.22, 4), (0.12, 3), (0.05, 2)])


def _business_prominence(goal, inputs, results):
    """Business category prominence (1–5) against the sector benchmark: water
    and electricity use their per-m² intensity vs the sector figure; fleet /
    waste / food-waste use their share of the business carbon breakdown. When
    the size context needed for an intensity is missing, returns a neutral 3
    (we can't fairly judge it) rather than borrowing a household benchmark."""
    from benchmarks import business_sector_benchmark
    bench = business_sector_benchmark(inputs["general"].get("sector"))
    domain = _BIZ_ADDR_DOMAIN.get(goal.get("addresses"), goal["metric"])
    if domain == "water":
        intensity = results["water"].get("litres_per_m2_year")
        b = bench.get("water_l_m2")
        if intensity and b:
            return _band(intensity / b, [(1.5, 5), (1.1, 4), (0.8, 3), (0.5, 2)])
        return 3
    if domain in ("elec", "electricity"):
        intensity = results["electricity"].get("kwh_per_m2_year")
        b = bench.get("kwh_m2")
        if intensity and b:
            return _band(intensity / b, [(1.5, 5), (1.15, 4), (0.8, 3), (0.5, 2)])
        return 3
    # carbon domain → share of the business carbon breakdown
    bd = results["carbon"]["breakdown"]
    total = sum(bd.values()) or 1.0
    key = _BIZ_ADDR_BREAKDOWN.get(goal.get("addresses"))
    share = (bd.get(key, 0.0) / total) if key else 0.0
    return _band(share, [(0.35, 5), (0.22, 4), (0.12, 3), (0.05, 2)])


def _impact(goal, inputs, results):
    """Environmental benefit (1–5): category prominence, nudged up when the
    concrete expected saving is large for its metric (§2.1). The saving nudge
    is personal-only — its thresholds are household weekly magnitudes and
    business savings are mostly qualitative."""
    base = _prominence(goal, inputs, results)
    if _is_business(inputs):
        return base
    sv = goal.get("expected_saving")
    if sv:
        big = {"water": 150, "electricity": 6, "carbon": 3}.get(goal["metric"], 0)
        if big and sv >= big:
            base = min(5, base + 1)
    return base


def _business_relevance(goal, inputs, results):
    """How directly a business goal applies to THIS organisation (1–5): driven
    by the sector flags and whether the user actually reported that operation,
    so a restaurant's refrigeration goal scores high while an office's doesn't
    (spec §5). Never falls through to a flat default the way the household model
    did for business categories."""
    from schema import business_sector_flags
    g = inputs["general"]
    b = inputs.get("business", {})
    flags = business_sector_flags(g.get("sector"))
    addr = goal.get("addresses")
    bd = results["carbon"]["breakdown"]
    total = sum(bd.values()) or 1.0
    if addr == "electricity":
        return 5                       # every business runs on electricity
    if addr == "refrigeration":
        return 5 if (flags["refrigeration"] and b.get("refrigeration")) else 2
    if addr == "water":
        return 4
    if addr == "process_water":
        return 5 if (flags["process_water"]
                     and b.get("process_water_kl_month")) else 2
    if addr == "irrigation":
        return 5 if (flags["irrigation"] and b.get("irrigation_kl_month")) else 2
    if addr == "fleet":
        fleet = inputs["transport"].get("fleet") or []
        if not fleet:
            return 1
        return _band(bd.get("fleet", 0.0) / total, [(0.25, 5), (0.12, 4), (0.04, 3)])
    if addr == "food_waste":
        return 5 if (flags["food_waste"] and b.get("food_waste_kg_month")) else 2
    if addr == "waste":
        return 4 if b.get("waste_kg_month") else 3
    return 3


def _relevance(goal, inputs, results):
    """How directly the goal matches THIS user's actual behaviour (1–5, §2.3).
    Deterministic proxy for the AI relevance judgement / fallback for it."""
    if _is_business(inputs):
        return _business_relevance(goal, inputs, results)
    addr = goal.get("addresses")
    w, t, l = inputs["water"], inputs["transport"], inputs["lifestyle"]
    if addr == "shower":
        if w.get("shower_minutes") and w.get("showers_per_week"):
            wk = float(w["shower_minutes"]) * float(w["showers_per_week"])
            return _band(wk, [(140, 5), (84, 4), (40, 3), (1, 2)])
        return 4 if results["water"]["water_litres_person_day"] > 218 else 2
    if addr in ("pool", "pool_pump"):
        return 4
    if addr == "geyser":
        return 5
    if addr == "standby":
        return 2
    if addr == "personal_vehicle":
        km = float((t.get("vehicle") or {}).get("annual_km") or 0)
        return _band(km, [(20000, 5), (12000, 4), (6000, 3), (1, 2)])
    if addr == "diet_and_food_waste":
        return {"Heavy meat eater": 5, "Average diet": 4, "Mostly chicken": 3,
                "Pescatarian": 3, "Vegetarian": 2, "Vegan": 1}.get(
                    l.get("diet", "Average diet"), 3)
    if addr == "generator":
        return 4
    if addr == "flights":
        trips = sum(int(f.get("trips_per_year") or 0)
                    for f in (t.get("flights") or []))
        return _band(trips, [(4, 5), (2, 4), (1, 3)])
    return 3


def _reason(goal, sc, inputs=None):
    """A short, user-facing 'why this goal' — no scores or jargon (§2.6).
    Uses the business phrase map for business accounts so the wording matches
    the organisation's categories (fleet, refrigeration, …)."""
    if inputs is not None and _is_business(inputs):
        cat = _BUSINESS_CATEGORY_PHRASE.get(goal.get("addresses"), "footprint")
    else:
        cat = _CATEGORY_PHRASE.get(goal.get("addresses"), "footprint")
    if sc["impact"] >= 4 and sc["relevance"] >= 4:
        lead = f"Recommended because your {cat} is one of your largest impact areas"
    elif sc["relevance"] >= 4:
        lead = f"Recommended because it directly matches your {cat}"
    elif sc["impact"] <= 2 and sc["relevance"] <= 2:
        lead = (f"A simple maintenance step — your {cat} is already fairly low, "
                "so this keeps it that way")
    else:
        lead = f"A practical step for your {cat}"
    if sc["feasibility"] >= 4 and sc["difficulty"] <= 2:
        tail = "and it's an easy change to start this week"
    elif sc["difficulty"] >= 4:
        tail = ("though it takes more effort or cost, so weigh it against "
                "quicker wins")
    else:
        tail = "and it's realistic based on your current habits"
    return f"{lead}, {tail}."


def score_goal(goal, inputs, results):
    """Return the four 1–5 factors and the combined priority for one goal."""
    imp = _impact(goal, inputs, results)
    feas = int(goal.get("feasibility", 3))
    rel = _relevance(goal, inputs, results)
    diff = max(1, int(goal.get("difficulty", 2)))
    return {"impact": imp, "feasibility": feas, "relevance": rel,
            "difficulty": diff, "priority": round(imp * feas * rel / diff, 2)}


def rank_candidate_goals(inputs, results, candidates=None, ai_overlay=None):
    """Rank candidates highest-priority first (§2.5). `ai_overlay`, when given,
    is a validated {normalised_title: {"relevance": int, "reason": str}} map
    from the AI relevance pass; anything missing or invalid simply falls back
    to the deterministic score, so Goals never breaks on bad AI output (§2.6).
    Each returned goal gains: impact, feasibility, relevance, difficulty,
    priority and a user-facing `reason`."""
    if candidates is None:
        candidates = generate_goal_candidates(inputs, results)
    out = []
    overlay = ai_overlay or {}
    for base in candidates:
        goal = dict(base)
        sc = score_goal(goal, inputs, results)
        ai_reason = None
        ov = overlay.get(_norm(goal.get("title")))
        if isinstance(ov, dict):
            rel = ov.get("relevance")
            if isinstance(rel, (int, float)) and 1 <= rel <= 5:
                sc["relevance"] = int(rel)
                sc["priority"] = round(
                    sc["impact"] * sc["feasibility"] * sc["relevance"]
                    / sc["difficulty"], 2)
            if isinstance(ov.get("reason"), str) and ov["reason"].strip():
                ai_reason = ov["reason"].strip()
        goal.update({k: sc[k] for k in ("impact", "feasibility", "relevance",
                                        "difficulty", "priority")})
        goal["reason"] = ai_reason or _reason(goal, sc, inputs)
        out.append(goal)
    out.sort(key=lambda g: (-g["priority"], -(g.get("expected_saving") or 0)))
    return out


def pick_weekly_goals(inputs, results, n=3):
    """Top-N goals by the priority model, keeping at most two per metric for
    variety. Deterministic (offline-safe); the AI overlay is applied by callers
    that have it (e.g. the dashboard)."""
    ranked = rank_candidate_goals(inputs, results)
    picked, per_metric = [], {}
    for goal in ranked:
        if per_metric.get(goal["metric"], 0) >= 2:
            continue
        picked.append(goal)
        per_metric[goal["metric"]] = per_metric.get(goal["metric"], 0) + 1
        if len(picked) >= n:
            break
    return picked


# ---------------------------------------------------------------------------
# Planner trust boundary (§2.6, spec appendix A): the LLM planner may PROPOSE an
# action and explain it, but it may NOT hand us an authoritative expected
# saving to persist. Every AI-proposed goal is run through this before it can
# reach db.save_goals: a proposal that maps to a deterministic candidate for
# THIS user inherits that candidate's factor-derived saving; anything else is
# kept as qualitative advice with NO number. An AI-supplied saving is always
# discarded — a fabricated figure never survives.
# ---------------------------------------------------------------------------

def _match_candidate(proposal, candidates):
    """Best deterministic candidate for an AI proposal, or None. Requires the
    same metric and a real overlap of meaningful title words (≥2), and only
    considers candidates that actually carry a factor-derived saving. Conserv-
    ative on purpose: a near-miss falls through to qualitative rather than
    borrowing another goal's number."""
    metric = proposal.get("metric")
    if metric not in ("water", "electricity", "carbon"):
        return None
    ptoks = _tokens(proposal.get("title", ""))
    if not ptoks:
        return None
    best, best_overlap = None, 0
    for c in candidates:
        if c.get("metric") != metric or c.get("expected_saving") is None:
            continue
        overlap = len(ptoks & _tokens(c.get("title", "")))
        if overlap > best_overlap:
            best, best_overlap = c, overlap
    return best if best_overlap >= 2 else None


def sanitize_planner_goals(proposed, inputs, results):
    """Validate AI-proposed goals before they can be saved.

    The LLM's own `expected_saving` / `expected_saving_unit` are ALWAYS
    discarded. A proposal that maps to a deterministic candidate for this user
    inherits that candidate's factor-derived saving, target and category; an
    unmapped proposal is kept as honest qualitative advice with an empty saving.
    Returns a list of clean goal dicts safe to hand to db.save_goals."""
    candidates = generate_goal_candidates(inputs, results)
    out = []
    for p in (proposed or []):
        if not isinstance(p, dict):
            continue
        title = str(p.get("title", "")).strip()
        if not title:
            continue
        match = _match_candidate(p, candidates)
        if match:
            out.append({
                "title": title,
                "metric": match["metric"],
                "target_value": match.get("target_value"),
                "target_unit": match.get("target_unit"),
                "expected_saving": match.get("expected_saving"),
                "expected_saving_unit": match.get("expected_saving_unit"),
                "addresses": match.get("addresses"),
                "source": "planner_verified",
            })
        else:
            metric = p.get("metric")
            out.append({
                "title": title,
                "metric": metric if metric in ("water", "electricity",
                                               "carbon") else "carbon",
                "target_value": None,
                "target_unit": None,
                "expected_saving": None,     # never fabricate a number
                "expected_saving_unit": None,
                "source": "planner_qualitative",
            })
    return out
