"""
SQLite persistence for users, assessments, history, goals, achievements,
streaks, stories and uploaded-bill records (spec §20 "Data and State
Requirements").

The database lives in data/impact.db (git-ignored). Uploaded bill images are
stored privately under data/uploads/<user_id>/ and are never exposed on
public pages.
"""

import json
import os
import sqlite3
import secrets
import hashlib
from datetime import datetime, date, timedelta

DATA_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data")
DB_PATH = os.path.join(DATA_DIR, "impact.db")
UPLOAD_DIR = os.path.join(DATA_DIR, "uploads")

_SCHEMA = """
CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    email TEXT UNIQUE NOT NULL,
    display_name TEXT NOT NULL,
    pw_hash TEXT NOT NULL,
    salt TEXT NOT NULL,
    created_at TEXT NOT NULL,
    privacy TEXT NOT NULL DEFAULT 'private',          -- 'public' | 'private'
    public_fields TEXT NOT NULL DEFAULT '[]',          -- JSON list of approved fields
    story_consent INTEGER NOT NULL DEFAULT 0,          -- separate from privacy
    reminder_cadence TEXT NOT NULL DEFAULT 'weekly',   -- 'weekly' | 'monthly'
    reminders_enabled INTEGER NOT NULL DEFAULT 1,
    unit_period TEXT NOT NULL DEFAULT 'month',         -- day|week|month|year
    avatar TEXT NOT NULL DEFAULT '🌱',
    country TEXT NOT NULL DEFAULT 'South Africa',
    is_demo INTEGER NOT NULL DEFAULT 0
);

CREATE TABLE IF NOT EXISTS assessments (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL REFERENCES users(id),
    created_at TEXT NOT NULL,
    inputs TEXT NOT NULL,        -- JSON assessment data (schema.py)
    results TEXT NOT NULL,       -- JSON engine output (calculations.py)
    ai_analysis TEXT,            -- cached LLM interpretation
    source TEXT NOT NULL DEFAULT 'questionnaire'  -- questionnaire | chat | update
);

CREATE TABLE IF NOT EXISTS goals (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL REFERENCES users(id),
    created_at TEXT NOT NULL,
    week_label TEXT NOT NULL,          -- ISO week the goal belongs to
    title TEXT NOT NULL,
    metric TEXT NOT NULL,              -- water | electricity | carbon
    target_value REAL,
    target_unit TEXT,
    expected_saving REAL,
    expected_saving_unit TEXT,
    status TEXT NOT NULL DEFAULT 'active',   -- active | completed | missed
    completed_at TEXT
);

CREATE TABLE IF NOT EXISTS achievements (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL REFERENCES users(id),
    code TEXT NOT NULL,
    earned_at TEXT NOT NULL,
    evidence TEXT,
    UNIQUE(user_id, code)
);

CREATE TABLE IF NOT EXISTS streaks (
    user_id INTEGER PRIMARY KEY REFERENCES users(id),
    cadence TEXT NOT NULL DEFAULT 'weekly',
    current INTEGER NOT NULL DEFAULT 0,
    best INTEGER NOT NULL DEFAULT 0,
    last_period TEXT
);

CREATE TABLE IF NOT EXISTS stories (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL REFERENCES users(id),
    created_at TEXT NOT NULL,
    title TEXT NOT NULL,
    challenge TEXT NOT NULL,
    actions TEXT NOT NULL,
    period TEXT,
    consented INTEGER NOT NULL DEFAULT 0,
    stats TEXT                       -- JSON verified stats snapshot
);

CREATE TABLE IF NOT EXISTS bills (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL REFERENCES users(id),
    created_at TEXT NOT NULL,
    kind TEXT NOT NULL,              -- water | electricity
    filename TEXT,
    file_path TEXT,                  -- private path under data/uploads
    extracted TEXT,                  -- JSON raw AI extraction
    corrected TEXT,                  -- JSON user-corrected values
    status TEXT NOT NULL DEFAULT 'pending'  -- pending | confirmed | discarded
);
"""


def _connect():
    os.makedirs(DATA_DIR, exist_ok=True)
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def init_db():
    with _connect() as conn:
        conn.executescript(_SCHEMA)
        # lightweight migration: cached short AI evaluation per assessment
        cols = [r["name"] for r in
                conn.execute("PRAGMA table_info(assessments)").fetchall()]
        if "ai_eval" not in cols:
            conn.execute("ALTER TABLE assessments ADD COLUMN ai_eval TEXT")


def _now():
    return datetime.now().isoformat(timespec="seconds")


def _row_to_dict(row):
    return dict(row) if row is not None else None


# --------------------------------------------------------------------- users

def hash_password(password, salt_hex=None):
    salt = bytes.fromhex(salt_hex) if salt_hex else secrets.token_bytes(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode(), salt, 200_000)
    return digest.hex(), salt.hex()


def create_user(email, display_name, password, privacy="private",
                reminder_cadence="weekly", country="South Africa",
                avatar="🌱", is_demo=0):
    pw_hash, salt = hash_password(password)
    with _connect() as conn:
        cur = conn.execute(
            "INSERT INTO users (email, display_name, pw_hash, salt, created_at,"
            " privacy, reminder_cadence, country, avatar, is_demo)"
            " VALUES (?,?,?,?,?,?,?,?,?,?)",
            (email.strip().lower(), display_name.strip(), pw_hash, salt, _now(),
             privacy, reminder_cadence, country, avatar, is_demo))
        user_id = cur.lastrowid
        conn.execute("INSERT INTO streaks (user_id, cadence) VALUES (?, ?)",
                     (user_id, reminder_cadence))
    return get_user(user_id)


def get_user(user_id):
    with _connect() as conn:
        row = conn.execute("SELECT * FROM users WHERE id=?", (user_id,)).fetchone()
    return _row_to_dict(row)


def get_user_by_email(email):
    with _connect() as conn:
        row = conn.execute("SELECT * FROM users WHERE email=?",
                           (email.strip().lower(),)).fetchone()
    return _row_to_dict(row)


def verify_login(email, password):
    user = get_user_by_email(email)
    if not user:
        return None
    pw_hash, _ = hash_password(password, user["salt"])
    return user if secrets.compare_digest(pw_hash, user["pw_hash"]) else None


def update_user(user_id, **fields):
    allowed = {"display_name", "privacy", "public_fields", "story_consent",
               "reminder_cadence", "reminders_enabled", "unit_period",
               "avatar", "country"}
    sets, vals = [], []
    for k, v in fields.items():
        if k in allowed:
            if k == "public_fields" and not isinstance(v, str):
                v = json.dumps(v)
            sets.append(f"{k}=?")
            vals.append(v)
    if not sets:
        return
    vals.append(user_id)
    with _connect() as conn:
        conn.execute(f"UPDATE users SET {', '.join(sets)} WHERE id=?", vals)
        if "reminder_cadence" in fields:
            conn.execute("UPDATE streaks SET cadence=? WHERE user_id=?",
                         (fields["reminder_cadence"], user_id))


def public_users():
    with _connect() as conn:
        rows = conn.execute(
            "SELECT * FROM users WHERE privacy='public' ORDER BY created_at").fetchall()
    return [_row_to_dict(r) for r in rows]


# --------------------------------------------------------------- assessments

def save_assessment(user_id, inputs, results, source="questionnaire",
                    created_at=None):
    with _connect() as conn:
        cur = conn.execute(
            "INSERT INTO assessments (user_id, created_at, inputs, results, source)"
            " VALUES (?,?,?,?,?)",
            (user_id, created_at or _now(), json.dumps(inputs),
             json.dumps(results), source))
        return cur.lastrowid


def set_assessment_analysis(assessment_id, text):
    with _connect() as conn:
        conn.execute("UPDATE assessments SET ai_analysis=? WHERE id=?",
                     (text, assessment_id))


def set_assessment_eval(assessment_id, eval_dict):
    """Cache the short 4-part dashboard evaluation (JSON)."""
    with _connect() as conn:
        conn.execute("UPDATE assessments SET ai_eval=? WHERE id=?",
                     (json.dumps(eval_dict) if eval_dict else None,
                      assessment_id))


def list_assessments(user_id):
    with _connect() as conn:
        rows = conn.execute(
            "SELECT * FROM assessments WHERE user_id=? ORDER BY created_at",
            (user_id,)).fetchall()
    out = []
    for r in rows:
        d = _row_to_dict(r)
        d["inputs"] = json.loads(d["inputs"])
        d["results"] = json.loads(d["results"])
        out.append(d)
    return out


def latest_assessment(user_id):
    items = list_assessments(user_id)
    return items[-1] if items else None


# --------------------------------------------------------------------- goals

def iso_week_label(d=None):
    d = d or date.today()
    y, w, _ = d.isocalendar()
    return f"{y}-W{w:02d}"


def save_goals(user_id, goals, week_label=None):
    """Add goals with central duplicate prevention (§13): a candidate that is
    semantically identical to a current-week or still-active goal is skipped.

    Returns (added_titles, skipped_titles)."""
    from goals import find_duplicate
    wk = week_label or iso_week_label()
    existing = goals_for_week(user_id, wk) + [
        g for g in all_goals(user_id)
        if g["status"] == "active" and g["week_label"] != wk]
    added, skipped = [], []
    with _connect() as conn:
        for goal in goals:
            if find_duplicate(goal, existing):
                skipped.append(goal["title"])
                continue
            conn.execute(
                "INSERT INTO goals (user_id, created_at, week_label, title, metric,"
                " target_value, target_unit, expected_saving, expected_saving_unit)"
                " VALUES (?,?,?,?,?,?,?,?,?)",
                (user_id, _now(), wk, goal["title"], goal["metric"],
                 goal.get("target_value"), goal.get("target_unit"),
                 goal.get("expected_saving"), goal.get("expected_saving_unit")))
            existing.append({"title": goal["title"], "metric": goal["metric"]})
            added.append(goal["title"])
    return added, skipped


def goals_for_week(user_id, week_label=None):
    wk = week_label or iso_week_label()
    with _connect() as conn:
        rows = conn.execute(
            "SELECT * FROM goals WHERE user_id=? AND week_label=? ORDER BY id",
            (user_id, wk)).fetchall()
    return [_row_to_dict(r) for r in rows]


def all_goals(user_id):
    with _connect() as conn:
        rows = conn.execute(
            "SELECT * FROM goals WHERE user_id=? ORDER BY created_at DESC",
            (user_id,)).fetchall()
    return [_row_to_dict(r) for r in rows]


def set_goal_status(goal_id, status):
    with _connect() as conn:
        conn.execute("UPDATE goals SET status=?, completed_at=? WHERE id=?",
                     (status, _now() if status == "completed" else None, goal_id))


def goal_stats(user_id):
    with _connect() as conn:
        total = conn.execute("SELECT COUNT(*) c FROM goals WHERE user_id=?",
                             (user_id,)).fetchone()["c"]
        done = conn.execute(
            "SELECT COUNT(*) c FROM goals WHERE user_id=? AND status='completed'",
            (user_id,)).fetchone()["c"]
    return {"total": total, "completed": done,
            "rate": (done / total * 100) if total else 0.0}


# -------------------------------------------------------------- achievements

def award(user_id, code, evidence=""):
    """Award an achievement once. Returns True if newly earned."""
    with _connect() as conn:
        try:
            conn.execute(
                "INSERT INTO achievements (user_id, code, earned_at, evidence)"
                " VALUES (?,?,?,?)", (user_id, code, _now(), evidence))
            return True
        except sqlite3.IntegrityError:
            return False


def get_achievements(user_id):
    with _connect() as conn:
        rows = conn.execute(
            "SELECT * FROM achievements WHERE user_id=? ORDER BY earned_at",
            (user_id,)).fetchall()
    return [_row_to_dict(r) for r in rows]


# ------------------------------------------------------------------- streaks

def _period_label(cadence, d=None):
    d = d or date.today()
    if cadence == "monthly":
        return d.strftime("%Y-%m")
    return iso_week_label(d)


def _previous_period_label(cadence, d=None):
    d = d or date.today()
    if cadence == "monthly":
        first = d.replace(day=1) - timedelta(days=1)
        return first.strftime("%Y-%m")
    return iso_week_label(d - timedelta(days=7))


def get_streak(user_id):
    with _connect() as conn:
        row = conn.execute("SELECT * FROM streaks WHERE user_id=?",
                           (user_id,)).fetchone()
        if row is None:
            conn.execute("INSERT INTO streaks (user_id) VALUES (?)", (user_id,))
            row = conn.execute("SELECT * FROM streaks WHERE user_id=?",
                               (user_id,)).fetchone()
    return _row_to_dict(row)


def check_in(user_id, on_date=None):
    """Register a valid check-in (assessment/update). Grows the streak when
    periods are consecutive, preserves 'best' regardless (spec §17.2)."""
    s = get_streak(user_id)
    cadence = s["cadence"]
    now_label = _period_label(cadence, on_date)
    prev_label = _previous_period_label(cadence, on_date)
    if s["last_period"] == now_label:
        return s  # already checked in this period
    current = s["current"] + 1 if s["last_period"] == prev_label else 1
    best = max(current, s["best"])
    with _connect() as conn:
        conn.execute(
            "UPDATE streaks SET current=?, best=?, last_period=? WHERE user_id=?",
            (current, best, now_label, user_id))
    return get_streak(user_id)


def streak_is_due(user_id):
    """True when the user has not checked in during the current period."""
    s = get_streak(user_id)
    return s["last_period"] != _period_label(s["cadence"])


# ------------------------------------------------------------------- stories

def save_story(user_id, title, challenge, actions, period, consented, stats):
    with _connect() as conn:
        conn.execute(
            "INSERT INTO stories (user_id, created_at, title, challenge, actions,"
            " period, consented, stats) VALUES (?,?,?,?,?,?,?,?)",
            (user_id, _now(), title, challenge, actions, period,
             1 if consented else 0, json.dumps(stats or {})))


def public_stories():
    """Published stories. Story publication consent is SEPARATE from profile
    visibility (§19): a deliberately published story stays visible even when
    the author's profile is private — it exposes only the story text and the
    stats snapshot the author consented to at publish time."""
    with _connect() as conn:
        rows = conn.execute(
            "SELECT s.*, u.display_name, u.avatar, u.privacy, u.story_consent"
            " FROM stories s JOIN users u ON u.id = s.user_id"
            " WHERE s.consented=1 AND u.story_consent=1"
            " ORDER BY s.created_at DESC").fetchall()
    out = []
    for r in rows:
        d = _row_to_dict(r)
        d["stats"] = json.loads(d["stats"] or "{}")
        out.append(d)
    return out


def stories_by_user(user_id):
    with _connect() as conn:
        rows = conn.execute(
            "SELECT * FROM stories WHERE user_id=? AND consented=1"
            " ORDER BY created_at DESC", (user_id,)).fetchall()
    out = []
    for r in rows:
        d = _row_to_dict(r)
        d["stats"] = json.loads(d["stats"] or "{}")
        out.append(d)
    return out


def community_members():
    """Everyone with a public presence: public profiles, plus private
    profiles that have deliberately published a story (story only)."""
    with _connect() as conn:
        rows = conn.execute(
            "SELECT DISTINCT u.* FROM users u"
            " LEFT JOIN stories s ON s.user_id = u.id AND s.consented=1"
            " WHERE u.privacy='public'"
            "    OR (s.id IS NOT NULL AND u.story_consent=1)"
            " ORDER BY u.created_at").fetchall()
    return [_row_to_dict(r) for r in rows]


# --------------------------------------------------------------------- bills

def save_bill(user_id, kind, filename, file_bytes, extracted):
    os.makedirs(os.path.join(UPLOAD_DIR, str(user_id)), exist_ok=True)
    safe = f"{datetime.now().strftime('%Y%m%d%H%M%S')}_{os.path.basename(filename)}"
    path = os.path.join(UPLOAD_DIR, str(user_id), safe)
    with open(path, "wb") as fh:
        fh.write(file_bytes)
    with _connect() as conn:
        cur = conn.execute(
            "INSERT INTO bills (user_id, created_at, kind, filename, file_path,"
            " extracted) VALUES (?,?,?,?,?,?)",
            (user_id, _now(), kind, filename, path, json.dumps(extracted or {})))
        return cur.lastrowid


def confirm_bill(bill_id, corrected):
    with _connect() as conn:
        conn.execute("UPDATE bills SET corrected=?, status='confirmed' WHERE id=?",
                     (json.dumps(corrected), bill_id))


def user_bills(user_id):
    with _connect() as conn:
        rows = conn.execute(
            "SELECT id, created_at, kind, filename, status FROM bills"
            " WHERE user_id=? ORDER BY created_at DESC", (user_id,)).fetchall()
    return [_row_to_dict(r) for r in rows]


# ------------------------------------------------------------ demo community

def seed_demo_data():
    """Create clearly-labelled demo community members so Explore, Stories and
    the Leaderboard are meaningful on first run. Demo history is produced by
    the real calculation engine so every number is consistent."""
    if get_user_by_email("thandi.demo@impact.app"):
        return
    from schema import default_assessment
    from calculations import run_assessment

    profiles = [
        {"email": "thandi.demo@impact.app", "name": "Thandi (demo)",
         "avatar": "🌻", "kwh": [520, 470, 430, 395, 370, 350],
         "water_kl": [16.0, 14.5, 13.0, 12.5, 11.8, 11.2], "hh": 4,
         "diet": "Average diet", "km": 12000,
         "story": ("Cutting our geyser bill in half",
                   "Loadshedding made us look hard at the geyser and pool pump.",
                   "Geyser timer, pool pump down to 4 hours, shorter showers.",
                   "6 months")},
        {"email": "sipho.demo@impact.app", "name": "Sipho (demo)",
         "avatar": "🌳", "kwh": [610, 600, 560, 540, 500, 480],
         "water_kl": [22.0, 21.0, 20.0, 19.0, 18.5, 18.0], "hh": 5,
         "diet": "Mostly chicken", "km": 18000,
         "story": ("From two cars to one plus the taxi",
                   "Fuel costs and a long commute across Joburg.",
                   "Car pooling twice a week and the minibus taxi for short trips.",
                   "4 months")},
        {"email": "anika.demo@impact.app", "name": "Anika (demo)",
         "avatar": "🌿", "kwh": [340, 330, 310, 300, 285, 275],
         "water_kl": [9.5, 9.0, 8.8, 8.5, 8.2, 8.0], "hh": 2,
         "diet": "Vegetarian", "km": 8000, "story": None},
    ]

    for p in profiles:
        user = create_user(p["email"], p["name"],
                           secrets.token_urlsafe(16),  # random pw; demo users are display-only
                           privacy="public", is_demo=1, avatar=p["avatar"])
        update_user(user["id"], public_fields=["score", "water", "electricity",
                                               "carbon", "streak", "achievements"],
                    story_consent=1 if p["story"] else 0)
        first_results = last_results = None
        for i, (kwh, kl) in enumerate(zip(p["kwh"], p["water_kl"])):
            data = default_assessment()
            data["general"]["household_size"] = p["hh"]
            data["water"]["water_kl_month"] = kl
            data["water"]["measured_source"] = "manual"
            data["electricity"]["kwh_month"] = float(kwh)
            data["electricity"]["measured_source"] = "manual"
            data["transport"]["vehicle"].update(
                {"owns_vehicle": True, "manufacturer": "Toyota",
                 "model": "Corolla", "annual_km": p["km"],
                 "average_passengers": 1})
            data["lifestyle"]["diet"] = p["diet"]
            results = run_assessment(data)
            created = (datetime.now() - timedelta(weeks=(len(p["kwh"]) - 1 - i))
                       ).isoformat(timespec="seconds")
            save_assessment(user["id"], data, results, source="questionnaire",
                            created_at=created)
            check_in(user["id"], (datetime.now()
                                  - timedelta(weeks=(len(p["kwh"]) - 1 - i))).date())
            if first_results is None:
                first_results = results
            last_results = results
        award(user["id"], "first_assessment", "demo seed")
        award(user["id"], "three_period_reduction", "demo seed")
        if p["story"]:
            improvement = round(
                100 * (first_results["electricity"]["total_electricity_kwh_month"]
                       - last_results["electricity"]["total_electricity_kwh_month"])
                / first_results["electricity"]["total_electricity_kwh_month"])
            title, challenge, actions, period = p["story"]
            save_story(user["id"], title, challenge, actions, period, True,
                       {"electricity_reduction_percent": improvement,
                        "from_kwh_month": first_results["electricity"]["total_electricity_kwh_month"],
                        "to_kwh_month": last_results["electricity"]["total_electricity_kwh_month"]})
