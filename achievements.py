"""
Achievement definitions and award logic (spec §17.1).

Achievements reward actual progress and consistency — never raw clicking.
"""

import database as db

# "icon" is a key into visuals.icon() — the app's stroke-SVG icon set.
# "desc" reads as what the member did (earned state); "how" explains how to
# unlock it (locked state).
ACHIEVEMENTS = {
    "first_assessment": {
        "icon": "target", "name": "First footprint",
        "desc": "Completed your first assessment.",
        "how": "Finish one full assessment — questionnaire or chat."},
    "first_bill": {
        "icon": "file", "name": "Verified numbers",
        "desc": "Uploaded and confirmed your first bill.",
        "how": "Upload a water or electricity bill and confirm the reading."},
    "week_of_goals": {
        "icon": "check", "name": "Clean sweep",
        "desc": "Completed every goal in a week.",
        "how": "Tick off every goal in your weekly plan."},
    "three_period_reduction": {
        "icon": "trend-down", "name": "Trend setter",
        "desc": "Reduced a metric three assessments in a row.",
        "how": "Lower your water, electricity or carbon on three "
               "check-ins in a row."},
    "personal_best": {
        "icon": "star", "name": "Personal best",
        "desc": "Reached your best impact score yet.",
        "how": "Beat your own highest impact score."},
    "streak_4": {
        "icon": "flame", "name": "One month strong",
        "desc": "Four consecutive check-ins.",
        "how": "Check in four periods in a row at your own cadence."},
    "streak_12": {
        "icon": "sun", "name": "Season of consistency",
        "desc": "Twelve consecutive check-ins.",
        "how": "Keep your check-in streak alive for twelve periods."},
    "big_cut": {
        "icon": "scissors", "name": "Deep cut",
        "desc": "Reduced a major footprint category by 10%+.",
        "how": "Cut one big carbon category (like driving or electricity) "
               "by at least 10% between assessments."},
}


def _series(assessments, getter):
    return [getter(a["results"]) for a in assessments]


def evaluate_after_assessment(user_id):
    """Check all data-driven achievements after a new assessment is saved.
    Returns list of newly-earned codes."""
    earned = []
    assessments = db.list_assessments(user_id)
    if not assessments:
        return earned

    if db.award(user_id, "first_assessment",
                f"assessment #{assessments[0]['id']}"):
        earned.append("first_assessment")

    # three consecutive reductions in any metric
    metrics = {
        "water": lambda r: r["water"]["total_water_litres_month"],
        "electricity": lambda r: r["electricity"]["total_electricity_kwh_month"],
        "carbon": lambda r: r["carbon"]["net_co2e_kg_year"],
    }
    for name, getter in metrics.items():
        vals = _series(assessments, getter)
        if len(vals) >= 4:
            tail = vals[-4:]
            if tail[0] > tail[1] > tail[2] > tail[3]:
                if db.award(user_id, "three_period_reduction",
                            f"{name}: {tail[0]:.0f}→{tail[3]:.0f}"):
                    earned.append("three_period_reduction")
                break
        elif len(vals) == 3 and vals[0] > vals[1] > vals[2]:
            # three assessments each lower than the previous counts too
            if db.award(user_id, "three_period_reduction",
                        f"{name}: {vals[0]:.0f}→{vals[2]:.0f}"):
                earned.append("three_period_reduction")
            break

    # personal best score (needs history to be meaningful)
    scores = _series(assessments, lambda r: r["score"]["total"])
    if len(scores) >= 2 and scores[-1] >= max(scores):
        if db.award(user_id, "personal_best", f"score {scores[-1]}"):
            earned.append("personal_best")

    # 10%+ cut in a major carbon category vs previous assessment
    if len(assessments) >= 2:
        prev = assessments[-2]["results"]["carbon"]["breakdown"]
        curr = assessments[-1]["results"]["carbon"]["breakdown"]
        for cat, prev_v in prev.items():
            if prev_v >= 200 and curr.get(cat, 0) <= prev_v * 0.9:
                if db.award(user_id, "big_cut",
                            f"{cat}: {prev_v:.0f}→{curr.get(cat, 0):.0f} kg"):
                    earned.append("big_cut")
                break

    # streak milestones
    streak = db.get_streak(user_id)
    if streak["current"] >= 4 and db.award(user_id, "streak_4",
                                           f"streak {streak['current']}"):
        earned.append("streak_4")
    if streak["current"] >= 12 and db.award(user_id, "streak_12",
                                            f"streak {streak['current']}"):
        earned.append("streak_12")
    return earned


def progress_for(user_id):
    """Progress toward not-yet-earned achievements where it is measurable:
    {code: {"pct": 0-100, "detail": str}}. Codes with no meaningful partial
    progress are simply absent."""
    out = {}
    assessments = db.list_assessments(user_id)

    streak = db.get_streak(user_id)
    out["streak_4"] = {"pct": min(100, streak["current"] / 4 * 100),
                       "detail": f"{streak['current']}/4 check-ins"}
    out["streak_12"] = {"pct": min(100, streak["current"] / 12 * 100),
                        "detail": f"{streak['current']}/12 check-ins"}

    week_goals = db.goals_for_week(user_id)
    if week_goals:
        done = sum(1 for g in week_goals if g["status"] == "completed")
        out["week_of_goals"] = {"pct": done / len(week_goals) * 100,
                                "detail": f"{done}/{len(week_goals)} goals "
                                          "this week"}

    # longest tail run of consecutive reductions across the three metrics
    metrics = {
        "water": lambda r: r["water"]["total_water_litres_month"],
        "electricity": lambda r: r["electricity"]["total_electricity_kwh_month"],
        "carbon": lambda r: r["carbon"]["net_co2e_kg_year"],
    }
    best_run = 0
    for getter in metrics.values():
        vals = _series(assessments, getter)
        run = 0
        for a, b in zip(reversed(vals[:-1]), reversed(vals[1:])):
            if b < a:
                run += 1
            else:
                break
        best_run = max(best_run, run)
    out["three_period_reduction"] = {
        "pct": min(100, best_run / 3 * 100),
        "detail": f"{best_run}/3 reductions in a row"}
    return out


def evaluate_goal_completion(user_id):
    """Award 'week of goals' when every goal of the current week is done."""
    week_goals = db.goals_for_week(user_id)
    if week_goals and all(g["status"] == "completed" for g in week_goals):
        if db.award(user_id, "week_of_goals", db.iso_week_label()):
            return ["week_of_goals"]
    return []
