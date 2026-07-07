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
    """Return goal dicts ordered by expected weekly impact relevance.

    Each goal: {title, metric, target_value, target_unit,
                expected_saving, expected_saving_unit, rationale}
    """
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
        })
    elif water["water_litres_person_day"] > 218:
        goals.append({
            "title": "Track one week of showers — note minutes per shower",
            "metric": "water", "target_value": 7, "target_unit": "showers logged",
            "expected_saving": None, "expected_saving_unit": None,
            "rationale": "Measured habits unlock accurate water goals",
        })

    # --- Water: pool cover / irrigation context
    if w_in.get("swimming_pool"):
        goals.append({
            "title": "Cover the pool (or log evaporation top-ups this week)",
            "metric": "water", "target_value": 1, "target_unit": "action",
            "expected_saving": None, "expected_saving_unit": None,
            "rationale": "Pool evaporation varies too much to promise a number — "
                         "covering typically cuts top-up water sharply",
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
            })

    # --- Always-available fallback goals
    if not any(g["metric"] == "electricity" for g in goals):
        goals.append({
            "title": "Switch everything off at the wall overnight (no standby)",
            "metric": "electricity", "target_value": 7, "target_unit": "nights",
            "expected_saving": round(0.3 * 7, 1), "expected_saving_unit": "kWh/week",
            "rationale": "Typical standby load ~0.3 kWh/night ([approximation])",
        })
    if not any(g["metric"] == "water" for g in goals):
        goals.append({
            "title": "Catch cold shower-warm-up water in a bucket for the garden",
            "metric": "water", "target_value": 7, "target_unit": "showers",
            "expected_saving": round(5 * 7, 1), "expected_saving_unit": "L/week",
            "rationale": "~5 L of warm-up water per shower ([approximation])",
        })
    return goals


def pick_weekly_goals(inputs, results, n=3):
    """Top-N goals, biased toward the largest footprint contributors."""
    candidates = generate_goal_candidates(inputs, results)
    breakdown = results["carbon"]["breakdown"]
    biggest = max(breakdown, key=breakdown.get) if breakdown else None
    metric_bias = {"water": 0, "electricity": 0, "carbon": 0}
    if biggest in ("electricity", "generator"):
        metric_bias["electricity"] = -1
    elif biggest in ("personal_vehicle", "flights", "public_transport",
                     "diet_and_food_waste", "heating"):
        metric_bias["carbon"] = -1
    if results["water"]["water_litres_person_day"] > 218:
        metric_bias["water"] -= 1

    ranked = sorted(
        candidates,
        key=lambda goal: (metric_bias.get(goal["metric"], 0),
                          -(goal.get("expected_saving") or 0)))
    # keep at most two goals per metric for variety
    picked, per_metric = [], {}
    for goal in ranked:
        if per_metric.get(goal["metric"], 0) >= 2:
            continue
        picked.append(goal)
        per_metric[goal["metric"]] = per_metric.get(goal["metric"], 0) + 1
        if len(picked) >= n:
            break
    return picked
