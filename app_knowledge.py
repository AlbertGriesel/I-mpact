"""
The chatbot's knowledge of the app itself (spec §3).

A single, maintainable description of every page and feature, plus where it
lives in the sidebar, so the assistant can ANSWER a question and then point the
user to the right place — never a bare "go to the Goals page". Keep this in
sync with app.py's navigation when pages change.
"""

# section -> list of (page, what it does / where to find things)
PAGES = {
    "Start": [
        ("Home", "Landing page: a quick overview, your greeting and shortcuts "
                 "into the assessment and dashboard."),
        ("Sign in / Sign up", "Create a free account or sign in. Sign-up is "
                              "where you choose Personal or Business — that "
                              "choice shapes the questions and benchmarks."),
    ],
    "Measure": [
        ("Assessment", "The guided questionnaire: fill in water, electricity, "
                       "transport, flights and lifestyle yourself, step by "
                       "step. You can upload a water or electricity bill and "
                       "we read it for you (you confirm every value)."),
        ("Chat Assessment", "The SAME assessment, done as a natural chat with "
                            "Sprout. It asks the same questions, uses the same "
                            "calculations and produces the same results — just "
                            "conversationally. Pick whichever you prefer."),
    ],
    "Improve": [
        ("Dashboard", "Your results: impact score, water / electricity / "
                      "carbon breakdowns, everyday comparisons, trends over "
                      "time and an automatic AI snapshot. Water, electricity "
                      "and carbon each have their own section here."),
        ("Goals", "Your personalised weekly plan — the highest-impact actions "
                  "for your situation, with expected savings, plus the "
                  "Carbon Offsets guidance. Found under Improve."),
    ],
    "Community": [
        ("Leaderboard", "See how you rank among people who share publicly "
                        "(opt-in only)."),
        ("Explore", "Read other people's improvement stories for ideas."),
    ],
    "More": [
        ("Information", "Plain-language explainers: greenhouse gases, "
                        "electricity, water and why individual action matters."),
        ("Profile", "Your identity and progress: your avatar, eco-level, "
                    "achievements, goal history and public-sharing settings."),
        ("Settings", "Account details, light/dark theme, privacy and data "
                     "controls, reminders, the AI connection, and a full "
                     "download of your own data."),
    ],
}

# Cross-cutting features that aren't a single page.
FEATURES = {
    "How calculations work": "Every number comes from a deterministic engine "
        "using published conversion factors — the AI never invents your "
        "footprint, it only explains the calculated results. Measured data "
        "(bills, meter readings) beats estimates, and each result carries a "
        "confidence label.",
    "Progress tracking": "Redo the assessment any time (your answers are "
        "pre-filled) to log a new check-in. Streaks, trends and achievements "
        "update automatically.",
    "The avatar": "Your avatar is your character in the app — it's separate "
        "from Daisy, the app's guide mascot. Its surroundings grow greener as "
        "your impact score improves. You set it up on the Profile page.",
    "Privacy": "Your data stays in a local database and is never shared with "
        "third parties without your permission. Bills and raw data stay "
        "private; only summary stats you explicitly approve can appear "
        "publicly. See Settings for the controls.",
    "Repeating an assessment": "Go to the Assessment (or Chat Assessment) page "
        "again — returning users land on a review hub with everything "
        "pre-filled, so you only update what changed.",
    "Carbon offsets": "Under Improve, the Carbon Offsets guidance explains "
        "what offsets are, why cutting avoidable emissions comes first, and "
        "lists reputable, verifiable providers for the emissions you can't yet "
        "eliminate.",
}


def _pages_block():
    lines = []
    for section, pages in PAGES.items():
        for name, desc in pages:
            lines.append(f"- {name} (sidebar: {section}): {desc}")
    return "\n".join(lines)


def _features_block():
    return "\n".join(f"- {k}: {v}" for k, v in FEATURES.items())


def assistant_knowledge(account_type="personal"):
    """The app-knowledge block appended to the assistant's system prompt."""
    who = ("This user has a BUSINESS account, so frame guidance for an "
           "organisation (per-employee / per-m² intensities, sector "
           "benchmarks, operations) rather than a household."
           if account_type == "business" else
           "This user has a PERSONAL (household) account.")
    return f"""
YOU KNOW THIS APP. When the user asks where to find or how to do something,
FIRST answer their actual question helpfully, THEN tell them where in the app
to go (name the sidebar section). Never reply with only "go to X".

{who}

PAGES:
{_pages_block()}

FEATURES:
{_features_block()}
"""


def analysis_context(account_type="personal"):
    """Short account-type framing appended to analysis / eval prompts."""
    if account_type == "business":
        return ("\n\nThis is a BUSINESS: talk about per-employee and per-m² "
                "intensity vs the sector benchmark, operational costs, "
                "efficiency and payback — not household or per-person framing. "
                "Do not mention diet.")
    return ("\n\nThis is a PERSONAL household: use per-person framing and "
            "household benchmarks.")
