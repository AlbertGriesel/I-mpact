"""
AI layer — the four roles from spec §11, with a pluggable provider so the app
runs on either a paid **Anthropic Claude** key or the **free Google Gemini**
tier:

  1. Conversational data collection  -> chat_collect()
  2. Environmental analysis          -> analyze_results()
  3. AI planning assistant           -> planner_reply()
  4. Bill / receipt image extraction -> extract_bill()

Provider selection (best-quality-first): if an Anthropic key/profile is
present it is used; otherwise a Gemini key activates the free tier; otherwise
every entry point degrades to a clear fallback.

Architecture rule (spec §11): the LLM is an advisor and interpreter, NOT the
source of truth for arithmetic. Every numeric footprint result comes from
calculations.py; extracted values are validated against schema.py (via
schema.merge_updates) and must be reviewed by the user before they are used —
regardless of which provider produced them.

Keys stay server-side: read from environment variables or
.streamlit/secrets.toml (both git-ignored). Chat history uses a neutral
format — [{"role": "user"|"assistant", "text": str}] — so the same UI works
for both providers.
"""

import json
import os

try:
    import anthropic
except ImportError:
    anthropic = None

try:
    from google import genai
    from google.genai import types as genai_types
except ImportError:
    genai = None
    genai_types = None

ANTHROPIC_MODEL = "claude-opus-4-8"
GEMINI_MODEL = "gemini-2.5-flash"   # free-tier, vision + JSON capable

_anthropic_client = None
_anthropic_error = None
_gemini_client = None
_gemini_error = None


# ===========================================================================
# Keys, providers, status
# ===========================================================================

def _secret(name):
    try:
        import streamlit as st
        return st.secrets.get(name)
    except Exception:
        return None


def _anthropic_key():
    return os.environ.get("ANTHROPIC_API_KEY") or _secret("ANTHROPIC_API_KEY")


def _gemini_key():
    return (os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY")
            or _secret("GEMINI_API_KEY") or _secret("GOOGLE_API_KEY"))


def _has_local_anthropic_profile():
    """True when an `ant auth login` credential profile exists on disk."""
    candidates = []
    if os.environ.get("APPDATA"):
        candidates.append(os.path.join(os.environ["APPDATA"], "Anthropic",
                                       "credentials"))
    candidates.append(os.path.join(os.path.expanduser("~"), ".config",
                                    "anthropic", "credentials"))
    return any(os.path.isdir(p) and os.listdir(p) for p in candidates
               if os.path.exists(p))


def _anthropic_available():
    if anthropic is None:
        return False
    return bool(_anthropic_key() or os.environ.get("ANTHROPIC_AUTH_TOKEN")
                or _has_local_anthropic_profile())


def _gemini_available():
    return genai is not None and bool(_gemini_key())


def active_provider():
    """Best available provider name, or None. Anthropic (quality) wins when a
    key is present; otherwise the free Gemini tier."""
    if _anthropic_available():
        return "anthropic"
    if _gemini_available():
        return "gemini"
    return None


def ai_status():
    """(available, human message) for UI badges."""
    prov = active_provider()
    if prov == "anthropic":
        return True, f"AI online — Claude ({ANTHROPIC_MODEL})"
    if prov == "gemini":
        return True, f"AI online — Gemini free tier ({GEMINI_MODEL})"
    missing = []
    if anthropic is None:
        missing.append("anthropic")
    if genai is None:
        missing.append("google-genai")
    if missing:
        return False, ("AI offline — install " + " / ".join(missing)
                       + " and connect a key under Settings.")
    return False, ("AI offline — connect a free Google Gemini key (or an "
                   "Anthropic key) under Settings to enable chat, bill "
                   "reading, analysis and planning.")


# Friendly, app-branded waiting copy — never expose the model provider in the
# consumer-facing interface (§11).
FRIENDLY_WAIT = [
    "Crunching your data…",
    "Growing your plan…",
    "Connecting the dots…",
    "Looking for your biggest opportunities…",
    "Checking where you can make the biggest difference…",
    "Think, think, think…",
]


def assistant_ready():
    """Neutral availability check for consumer-facing surfaces."""
    return active_provider() is not None


def provider_privacy_note():
    """A one-line caveat shown where users upload sensitive documents."""
    if active_provider() == "gemini":
        return ("Heads up: the free Gemini tier may use submitted content to "
                "improve Google's models. Avoid uploading bills you consider "
                "sensitive, or connect a paid key for stricter data handling.")
    return None


def reset_clients():
    global _anthropic_client, _anthropic_error, _gemini_client, _gemini_error
    _anthropic_client = _anthropic_error = None
    _gemini_client = _gemini_error = None


def _get_anthropic_client():
    global _anthropic_client, _anthropic_error
    if _anthropic_client is not None:
        return _anthropic_client
    if anthropic is None:
        _anthropic_error = "The 'anthropic' package is not installed."
        return None
    key = _anthropic_key()
    try:
        _anthropic_client = (anthropic.Anthropic(api_key=key) if key
                             else anthropic.Anthropic())
    except Exception as exc:  # noqa: BLE001
        _anthropic_error = str(exc)
        return None
    return _anthropic_client


def _get_gemini_client():
    global _gemini_client, _gemini_error
    if _gemini_client is not None:
        return _gemini_client
    if genai is None:
        _gemini_error = "The 'google-genai' package is not installed."
        return None
    key = _gemini_key()
    if not key:
        _gemini_error = "No Gemini API key configured."
        return None
    try:
        _gemini_client = genai.Client(api_key=key)
    except Exception as exc:  # noqa: BLE001
        _gemini_error = str(exc)
        return None
    return _gemini_client


# ===========================================================================
# Key management (used by Settings → Connect AI)
# ===========================================================================

def _save_secret(name, value):
    root = os.path.dirname(os.path.abspath(__file__))
    sdir = os.path.join(root, ".streamlit")
    os.makedirs(sdir, exist_ok=True)
    path = os.path.join(sdir, "secrets.toml")
    lines = []
    if os.path.exists(path):
        with open(path, encoding="utf-8") as fh:
            lines = [l for l in fh.read().splitlines()
                     if not l.strip().startswith(name)]
    lines.append(f'{name} = "{value}"')
    with open(path, "w", encoding="utf-8") as fh:
        fh.write("\n".join(lines) + "\n")


def save_api_key(key):
    """Persist an API key locally (git-ignored secrets.toml) and activate it
    this run. Provider is auto-detected from the key prefix.
    Returns (ok, message)."""
    key = (key or "").strip().strip('"').strip("'")
    if key.startswith("sk-ant-"):
        _save_secret("ANTHROPIC_API_KEY", key)
        os.environ["ANTHROPIC_API_KEY"] = key
        reset_clients()
        return True, ("Anthropic (Claude) key saved to "
                      ".streamlit/secrets.toml and activated.")
    # Google AI Studio keys: legacy "AIza…" and current "AQ.…" formats.
    if key.startswith("AIza") or key.startswith("AQ."):
        _save_secret("GEMINI_API_KEY", key)
        os.environ["GEMINI_API_KEY"] = key
        reset_clients()
        return True, ("Google Gemini key saved to .streamlit/secrets.toml and "
                      "activated — you're on the free tier.")
    return False, ("That key isn't recognised. Anthropic keys start with "
                   "sk-ant-; Google Gemini keys start with AQ. or AIza. Paste "
                   "one of those.")


def test_connection():
    """One tiny live request to prove the active provider works.
    Returns (ok, message)."""
    prov = active_provider()
    if prov is None:
        return False, "No AI provider is configured yet."
    try:
        if prov == "anthropic":
            client = _get_anthropic_client()
            if client is None:
                return False, _anthropic_error or "No Claude client."
            resp = client.messages.create(
                model=ANTHROPIC_MODEL, max_tokens=32,
                messages=[{"role": "user",
                           "content": "Reply with exactly: connected"}])
            if resp.stop_reason == "refusal":
                return False, "Unexpected refusal — please try again."
            reply = _anthropic_text(resp)
            label = f"Claude ({ANTHROPIC_MODEL})"
        else:
            client = _get_gemini_client()
            if client is None:
                return False, _gemini_error or "No Gemini client."
            resp = client.models.generate_content(
                model=GEMINI_MODEL, contents="Reply with exactly: connected")
            reply = (resp.text or "").strip()
            label = f"Gemini free tier ({GEMINI_MODEL})"
        return True, (f"{label} replied “{reply}” — chat, bill reading, "
                      "analysis and the planner are all live.")
    except Exception as exc:  # noqa: BLE001
        return False, _friendly_error(exc)


def _friendly_error(exc):
    msg = str(exc).lower()
    if "authentication method" in msg or "api key" in msg or "api_key" in msg:
        return ("AI is unavailable: the API key looks missing or invalid. "
                "Re-connect it under Settings.")
    if "quota" in msg or "rate" in msg or "429" in msg or "resource_exhausted" in msg:
        return ("The free tier is briefly rate-limited (a few requests per "
                "minute). Wait a moment and try again.")
    if "permission" in msg or "403" in msg:
        return "AI is unavailable: the key lacks permission for this model."
    if "connection" in msg or "network" in msg:
        return "AI is unreachable (network problem). The rest of the app still works."
    return (f"AI request failed ({exc.__class__.__name__}). The rest of the "
            "app still works.")


# ===========================================================================
# Provider primitives
# ===========================================================================

def _anthropic_text(response):
    return "".join(b.text for b in response.content if b.type == "text").strip()


def _gemini_config(system=None, json_mode=False):
    kwargs = {}
    if system:
        kwargs["system_instruction"] = system
    if json_mode:
        kwargs["response_mime_type"] = "application/json"
    return genai_types.GenerateContentConfig(**kwargs)


def _gemini_history(history):
    """Neutral history -> Gemini contents (roles: user / model)."""
    contents = []
    for h in history:
        role = "user" if h["role"] == "user" else "model"
        contents.append(genai_types.Content(
            role=role, parts=[genai_types.Part(text=h["text"])]))
    return contents


def _parse_json_lenient(text):
    """Parse a JSON object from model text, tolerating code fences / preamble."""
    if not text:
        return None
    t = text.strip()
    if t.startswith("```"):
        t = t.strip("`")
        if t.lower().startswith("json"):
            t = t[4:]
    try:
        return json.loads(t)
    except json.JSONDecodeError:
        start, end = t.find("{"), t.rfind("}")
        if 0 <= start < end:
            try:
                return json.loads(t[start:end + 1])
            except json.JSONDecodeError:
                return None
    return None


# ===========================================================================
# System prompts (shared by both providers)
# ===========================================================================

def _collect_system(data, missing):
    gaps = "\n".join(f"- {path}: {hint}" for path, hint in missing) \
        or "(none — you may finish)"
    return f"""You are Sprout, the friendly assessment assistant of an environmental
impact tracker built for South African and broader African households.

Your ONLY job is to collect the structured data the deterministic calculator
needs. You never calculate footprints and you NEVER invent, assume or round up
values the user did not state. If the user does not know a value, leave it
empty and move on — the calculator has defensible fallbacks.

STYLE
- Warm, plain language, no jargon. One short question at a time.
- Briefly explain why you ask when it isn't obvious.
- The user can type amounts in natural language ("about 800 bucks a month",
  "20-minute showers"). Extract them faithfully.
- Understand local realities: prepaid meters, loadshedding, generators,
  inverters, solar, boreholes, minibus taxis.

RULES
1. Record every usable value the user provides.
2. Ask ONLY about the gaps listed below, in order — they encode the
   conditional logic (measured data first; estimation questions only when
   measured data is missing). Do not ask about anything else.
3. Prefer measured data: bills, prepaid receipts, meter readings. Mention once
   that they can also upload bills on the Assessment page.
4. Convert city names to IATA airport codes when recording flights
   (Cape Town->CPT, Johannesburg->JNB, Durban->DUR, London Heathrow->LHR, ...).
5. When the user gives a bill amount in rand instead of consumption, record the
   rand amount — the calculator converts it with municipal tariffs.
6. Finish once every remaining gap is optional or the user can't answer. Keep
   it under about 10 minutes total.

CURRENT COLLECTED STATE (JSON):
{json.dumps(data, indent=1)}

REMAINING IMPORTANT GAPS (ask in this order):
{gaps}"""


_COLLECT_JSON_INSTRUCTIONS = """
OUTPUT FORMAT — respond with a single JSON object, nothing else:
{
  "reply": "your next warm, short message to the user",
  "updates": { ...only fields the user actually provided this turn... },
  "done": false
}
"updates" mirrors the assessment sections: general, water, electricity,
transport (with vehicle / public_transport objects and a flights array),
lifestyle. Include ONLY values the user stated; omit everything else; never
invent. Use null for a value the user says they don't know. Set "done": true
only when the remaining gaps are optional or unanswerable.
Example: {"reply":"Thanks! And roughly how many people live with you?",
"updates":{"electricity":{"bill_rand":900,"measured_source":"manual"}},
"done":false}"""

_ANALYSIS_SYSTEM = """You are an environmental sustainability advisor for a
South African / African audience. Do not recalculate the user's footprint —
use the deterministic results supplied. Your tasks:
1. Explain the results clearly and warmly, in simple language.
2. Identify the largest contributors and why they matter.
3. Compare with the supplied benchmarks, respecting their labels and scope
   caveats (never present a context benchmark as like-for-like).
4. Recommend the three to five highest-impact realistic improvements,
   prioritised by likely impact, feasibility and cost.
5. Estimate potential savings ONLY where the supplied data supports it; say so
   when it doesn't.
6. Distinguish HIGH-confidence measured results from LOW-confidence estimates.
7. Never invent missing numerical data.
8. Prioritise major changes over trivial ones; stay optimistic and practical —
   no guilt, no fear. Local context (loadshedding, prepaid meters, municipal
   tariffs, minibus taxis, boreholes) matters.
Respond in markdown, at most ~350 words, with short 'Where you stand', 'What
drives your footprint' and 'Highest-impact next steps' sections."""

_PLANNER_SYSTEM = """You are the planning assistant of an environmental impact
tracker for South African / African households. You help the user turn broad
intentions into specific, measurable, realistic weekly actions.

Ground every answer in the user's supplied results, goals, history and stated
constraints. Respect their circumstances (budget, renting vs owning,
loadshedding, transport options). Use concrete numbers ONLY when the supplied
deterministic data supports them; otherwise say what measurement is needed.
You never change the user's data or goals yourself — you propose, they confirm.
Keep replies under ~200 words, warm and practical. Never recalculate the
footprint; the app's engine owns the numbers."""

_PLANNER_JSON_INSTRUCTIONS = """
OUTPUT FORMAT — respond with a single JSON object, nothing else:
{
  "reply": "your practical, warm answer (markdown ok)",
  "proposed_goals": [
    {"title": "...", "metric": "water|electricity|carbon",
     "target_value": number-or-null, "target_unit": "string-or-null",
     "expected_saving": number-or-null, "expected_saving_unit": "string-or-null"}
  ]
}
Prefer goals from the deterministic candidate list you were given; only include
expected_saving when it comes from that list or the supplied results. Use an
empty array when you're not proposing a goal this turn."""

_EXTRACT_SYSTEM = """You read utility documents for an environmental tracker in
South Africa (municipal water bills, electricity bills, prepaid electricity
receipts, meter statements). Extract ONLY what is actually printed:
- null for anything not visible or not legible — never estimate or infer.
- Normalise units: water to kilolitres (1 kL = 1000 L), electricity to kWh,
  money to rand.
- If several prepaid receipts/purchases are shown, list them and sum the kWh.
- List every field you are unsure about in uncertain_fields.
The user reviews and corrects your extraction before anything is calculated."""

_WATER_BILL_JSON = """
Respond with a single JSON object, nothing else, with these keys:
{"period_start": str|null, "period_end": str|null, "water_kl": number|null,
 "consumption_is_printed": bool, "bill_amount_rand": number|null,
 "includes_non_water_charges": bool|null, "meter_reading_current": number|null,
 "meter_reading_previous": number|null, "municipality": str|null,
 "uncertain_fields": [str], "notes": str|null}"""

_ELEC_BILL_JSON = """
Respond with a single JSON object, nothing else, with these keys:
{"period_start": str|null, "period_end": str|null, "kwh": number|null,
 "bill_amount_rand": number|null, "includes_non_electricity_charges": bool|null,
 "is_prepaid": bool|null,
 "purchases": [{"kwh": number|null, "amount_rand": number|null}]|null,
 "tariff": str|null, "municipality_or_utility": str|null,
 "uncertain_fields": [str], "notes": str|null}"""


# ===========================================================================
# Anthropic tool schema (Claude uses tool calls for collection/planning)
# ===========================================================================

_COLLECT_TOOL = {
    "name": "record_assessment_data",
    "description": ("Record structured values the user has just provided. Call "
                    "this the moment the user gives usable information — never "
                    "wait, never guess, never fill fields the user did not "
                    "state. Values are validated against the app schema; "
                    "anything rejected is reported back to you."),
    "input_schema": {
        "type": "object",
        "properties": {"updates": {
            "type": "object",
            "description": "Nested updates keyed by section (general, water, "
                           "electricity, transport, lifestyle).",
            "additionalProperties": True}},
        "required": ["updates"],
    },
}
_FINISH_TOOL = {
    "name": "finish_collection",
    "description": ("Signal that enough meaningful data has been collected and "
                    "the footprint can be calculated. Call this instead of "
                    "asking further questions once the remaining gaps are only "
                    "optional."),
    "input_schema": {
        "type": "object",
        "properties": {"summary": {"type": "string"}},
        "required": ["summary"],
    },
}
_PLANNER_TOOL = {
    "name": "propose_goal",
    "description": ("Propose ONE specific, measurable weekly goal. The app "
                    "shows it with an 'Add goal' button — the user decides; you "
                    "never change their data directly."),
    "input_schema": {
        "type": "object",
        "properties": {
            "title": {"type": "string"},
            "metric": {"type": "string", "enum": ["water", "electricity", "carbon"]},
            "target_value": {"type": ["number", "null"]},
            "target_unit": {"type": ["string", "null"]},
            "expected_saving": {"type": ["number", "null"]},
            "expected_saving_unit": {"type": ["string", "null"]},
        },
        "required": ["title", "metric"],
    },
}


# ===========================================================================
# 1. Conversational data collection
# ===========================================================================

def chat_collect(history, data):
    """One conversational turn. `history` is neutral format with the latest
    user message already appended.

    Returns: ok, text, data (merged), applied, rejected, done, history."""
    prov = active_provider()
    if prov == "anthropic":
        return _anthropic_chat_collect(history, data)
    if prov == "gemini":
        return _gemini_chat_collect(history, data)
    return {"ok": False, "text": ai_status()[1], "data": data,
            "applied": [], "rejected": [], "done": False, "history": history}


def _anthropic_chat_collect(history, data):
    from schema import merge_updates, missing_important_fields
    client = _get_anthropic_client()
    if client is None:
        return {"ok": False, "text": _anthropic_error or "AI unavailable.",
                "data": data, "applied": [], "rejected": [], "done": False,
                "history": history}
    merged, applied_all, rejected_all, done = data, [], [], False
    messages = [{"role": h["role"], "content": h["text"]} for h in history]
    try:
        for _ in range(5):
            response = client.messages.create(
                model=ANTHROPIC_MODEL, max_tokens=6000,
                thinking={"type": "adaptive"},
                output_config={"effort": "low"},
                system=_collect_system(merged, missing_important_fields(merged)),
                tools=[_COLLECT_TOOL, _FINISH_TOOL], messages=messages)
            if response.stop_reason == "refusal":
                text = "Let's keep going — what would you like to tell me next?"
                return {"ok": True, "text": text, "data": merged,
                        "applied": applied_all, "rejected": rejected_all,
                        "done": done,
                        "history": history + [{"role": "assistant", "text": text}]}
            messages.append({"role": "assistant", "content": response.content})
            if response.stop_reason != "tool_use":
                text = _anthropic_text(response)
                return {"ok": True, "text": text, "data": merged,
                        "applied": applied_all, "rejected": rejected_all,
                        "done": done,
                        "history": history + [{"role": "assistant", "text": text}]}
            tool_results = []
            for block in response.content:
                if block.type != "tool_use":
                    continue
                if block.name == "record_assessment_data":
                    merged, applied, rejected = merge_updates(
                        merged, (block.input or {}).get("updates", {}))
                    applied_all += applied
                    rejected_all += rejected
                    tool_results.append({
                        "type": "tool_result", "tool_use_id": block.id,
                        "content": json.dumps({"recorded": applied,
                                               "rejected": rejected})})
                elif block.name == "finish_collection":
                    done = True
                    tool_results.append({
                        "type": "tool_result", "tool_use_id": block.id,
                        "content": "Collection complete — tell the user they "
                                   "can press 'Calculate my footprint'."})
            messages.append({"role": "user", "content": tool_results})
        return {"ok": True, "text": "Recorded — anything else to add?",
                "data": merged, "applied": applied_all,
                "rejected": rejected_all, "done": done,
                "history": history + [{"role": "assistant",
                                       "text": "Recorded — anything else?"}]}
    except Exception as exc:  # noqa: BLE001
        return {"ok": False, "text": _friendly_error(exc), "data": merged,
                "applied": applied_all, "rejected": rejected_all,
                "done": done, "history": history}


def _gemini_chat_collect(history, data):
    from schema import merge_updates, missing_important_fields
    client = _get_gemini_client()
    if client is None:
        return {"ok": False, "text": _gemini_error or "AI unavailable.",
                "data": data, "applied": [], "rejected": [], "done": False,
                "history": history}
    system = (_collect_system(data, missing_important_fields(data))
              + _COLLECT_JSON_INSTRUCTIONS)
    try:
        resp = client.models.generate_content(
            model=GEMINI_MODEL, contents=_gemini_history(history),
            config=_gemini_config(system=system, json_mode=True))
        parsed = _parse_json_lenient(resp.text) or {}
        text = (parsed.get("reply") or "").strip() or "Got it — anything else?"
        merged, applied, rejected = data, [], []
        if isinstance(parsed.get("updates"), dict) and parsed["updates"]:
            merged, applied, rejected = merge_updates(data, parsed["updates"])
        done = bool(parsed.get("done"))
        return {"ok": True, "text": text, "data": merged, "applied": applied,
                "rejected": rejected, "done": done,
                "history": history + [{"role": "assistant", "text": text}]}
    except Exception as exc:  # noqa: BLE001
        return {"ok": False, "text": _friendly_error(exc), "data": data,
                "applied": [], "rejected": [], "done": False,
                "history": history}


# ===========================================================================
# 2. Environmental analysis
# ===========================================================================

def analyze_results(results, general, benchmarks_info):
    """LLM interpretation of deterministic results. Returns (ok, text)."""
    prov = active_provider()
    payload = {"user_results": results, "household": general,
               "benchmarks": benchmarks_info}
    user_msg = "USER RESULTS:\n" + json.dumps(payload, indent=1)
    try:
        if prov == "anthropic":
            client = _get_anthropic_client()
            if client is None:
                return False, _anthropic_error or "AI unavailable."
            response = client.messages.create(
                model=ANTHROPIC_MODEL, max_tokens=12000,
                thinking={"type": "adaptive"}, system=_ANALYSIS_SYSTEM,
                messages=[{"role": "user", "content": user_msg}])
            if response.stop_reason == "refusal":
                return False, "AI analysis unavailable for this request."
            return True, _anthropic_text(response)
        if prov == "gemini":
            client = _get_gemini_client()
            if client is None:
                return False, _gemini_error or "AI unavailable."
            resp = client.models.generate_content(
                model=GEMINI_MODEL, contents=user_msg,
                config=_gemini_config(system=_ANALYSIS_SYSTEM))
            return True, (resp.text or "").strip()
        return False, ai_status()[1]
    except Exception as exc:  # noqa: BLE001
        return False, _friendly_error(exc)


_EVAL_SYSTEM = """You are the friendly voice of an environmental impact tracker
for South African / African households. You receive deterministic results —
never recalculate them, never invent numbers.

Produce a VERY SHORT evaluation as JSON with exactly these keys:
{"overall": "...", "positive": "...", "concern": "...", "recommendation": "..."}
- overall: one warm sentence summarising where the user stands (max 22 words).
- positive: their single biggest positive point (max 18 words).
- concern: their single biggest concern, stated kindly (max 18 words).
- recommendation: the single highest-priority practical action (max 18 words).
Ground every statement in the supplied numbers and confidence labels. Plain
language, no jargon, no guilt. Respond with the JSON object only."""

_EVAL_SCHEMA = {
    "type": "object",
    "properties": {
        "overall": {"type": "string"},
        "positive": {"type": "string"},
        "concern": {"type": "string"},
        "recommendation": {"type": "string"},
    },
    "required": ["overall", "positive", "concern", "recommendation"],
    "additionalProperties": False,
}


def short_eval(results, general, benchmarks_info):
    """Concise 4-part dashboard snapshot (§10). Returns (ok, dict|message).
    Generated automatically after each assessment and cached — never
    regenerated for mere page refreshes (§11)."""
    prov = active_provider()
    payload = {"user_results": results, "household": general,
               "benchmarks": benchmarks_info}
    user_msg = "USER RESULTS:\n" + json.dumps(payload, indent=1)
    try:
        if prov == "anthropic":
            client = _get_anthropic_client()
            if client is None:
                return False, _anthropic_error or "AI unavailable."
            response = client.messages.create(
                model=ANTHROPIC_MODEL, max_tokens=6000,
                thinking={"type": "adaptive"}, system=_EVAL_SYSTEM,
                output_config={"format": {"type": "json_schema",
                                          "schema": _EVAL_SCHEMA}},
                messages=[{"role": "user", "content": user_msg}])
            if response.stop_reason == "refusal":
                return False, "Evaluation unavailable."
            parsed = json.loads(next(b.text for b in response.content
                                     if b.type == "text"))
        elif prov == "gemini":
            client = _get_gemini_client()
            if client is None:
                return False, _gemini_error or "AI unavailable."
            resp = client.models.generate_content(
                model=GEMINI_MODEL, contents=user_msg,
                config=_gemini_config(system=_EVAL_SYSTEM, json_mode=True))
            parsed = _parse_json_lenient(resp.text)
        else:
            return False, ai_status()[1]
        if not parsed or not all(k in parsed for k in
                                 ("overall", "positive", "concern",
                                  "recommendation")):
            return False, "Evaluation came back incomplete."
        return True, {k: str(parsed[k]).strip() for k in
                      ("overall", "positive", "concern", "recommendation")}
    except Exception as exc:  # noqa: BLE001
        return False, _friendly_error(exc)


def fallback_eval(results):
    """Deterministic snapshot when the assistant is offline — same shape as
    short_eval so the dashboard renders identically."""
    w, e, c = results["water"], results["electricity"], results["carbon"]
    breakdown = c["breakdown"]
    biggest = max(breakdown, key=breakdown.get)
    per_day = w["water_litres_person_day"]
    positive = ("Water use is below the SA 218 L/person/day benchmark."
                if per_day <= 218 else
                f"Your data quality: {e['confidence']}-confidence electricity "
                "numbers make this footprint trustworthy.")
    concern = (f"{biggest.replace('_', ' ').title()} is your largest carbon "
               f"source ({breakdown[biggest]:,.0f} kg/year).")
    return {
        "overall": f"Net footprint {c['net_co2e_kg_year']:,.0f} kg CO₂e/year, "
                   f"water {per_day:,.0f} L/person/day, electricity "
                   f"{e['total_electricity_kwh_month']:,.0f} kWh/month.",
        "positive": positive,
        "concern": concern,
        "recommendation": "Work through this week's plan below — it targets "
                          "your biggest contributor first.",
    }


def fallback_analysis(results):
    """Deterministic, non-AI summary used when the API is unavailable."""
    c = results["carbon"]
    biggest = max(c["breakdown"], key=c["breakdown"].get)
    return "\n".join([
        "**Where you stand (offline summary)**",
        f"- Water: {results['water']['water_litres_person_day']:.0f} L/person/day "
        f"(SA benchmark 218) — confidence {results['water']['confidence']}.",
        f"- Electricity: {results['electricity']['total_electricity_kwh_month']:.0f} "
        f"kWh/month — confidence {results['electricity']['confidence']}.",
        f"- Carbon: {c['net_co2e_kg_year']:.0f} kg CO2e/year (net).",
        f"- Largest carbon contributor: **{biggest.replace('_', ' ')}** "
        f"({c['breakdown'][biggest]:.0f} kg/year).",
        "",
        "_AI interpretation is offline — connect a key under Settings to enable "
        "it. Your weekly goals below are generated deterministically and still "
        "apply._",
    ])


# ===========================================================================
# 3. AI planning assistant
# ===========================================================================

def planner_reply(history, grounding):
    """One planner turn. Returns dict: ok, text, proposed_goals, history."""
    prov = active_provider()
    if prov == "anthropic":
        return _anthropic_planner(history, grounding)
    if prov == "gemini":
        return _gemini_planner(history, grounding)
    return {"ok": False, "text": ai_status()[1], "proposed_goals": [],
            "history": history}


def _anthropic_planner(history, grounding):
    client = _get_anthropic_client()
    if client is None:
        return {"ok": False, "text": _anthropic_error or "AI unavailable.",
                "proposed_goals": [], "history": history}
    system = _PLANNER_SYSTEM + "\n\nUSER CONTEXT (JSON):\n" + json.dumps(grounding, indent=1)
    messages = [{"role": h["role"], "content": h["text"]} for h in history]
    proposed = []
    try:
        for _ in range(4):
            response = client.messages.create(
                model=ANTHROPIC_MODEL, max_tokens=8000,
                thinking={"type": "adaptive"}, output_config={"effort": "medium"},
                system=system, tools=[_PLANNER_TOOL], messages=messages)
            if response.stop_reason == "refusal":
                text = "Let's talk about your plan — what would you like to work on?"
                return {"ok": True, "text": text, "proposed_goals": proposed,
                        "history": history + [{"role": "assistant", "text": text}]}
            messages.append({"role": "assistant", "content": response.content})
            if response.stop_reason != "tool_use":
                text = _anthropic_text(response)
                return {"ok": True, "text": text, "proposed_goals": proposed,
                        "history": history + [{"role": "assistant", "text": text}]}
            tool_results = []
            for block in response.content:
                if block.type == "tool_use":
                    goal = dict(block.input or {})
                    goal.setdefault("metric", "carbon")
                    proposed.append(goal)
                    tool_results.append({
                        "type": "tool_result", "tool_use_id": block.id,
                        "content": "Proposed to the user — they confirm in the UI."})
            messages.append({"role": "user", "content": tool_results})
        text = "Anything else you'd like to plan?"
        return {"ok": True, "text": text, "proposed_goals": proposed,
                "history": history + [{"role": "assistant", "text": text}]}
    except Exception as exc:  # noqa: BLE001
        return {"ok": False, "text": _friendly_error(exc),
                "proposed_goals": proposed, "history": history}


def _gemini_planner(history, grounding):
    client = _get_gemini_client()
    if client is None:
        return {"ok": False, "text": _gemini_error or "AI unavailable.",
                "proposed_goals": [], "history": history}
    system = (_PLANNER_SYSTEM + "\n\nUSER CONTEXT (JSON):\n"
              + json.dumps(grounding, indent=1) + _PLANNER_JSON_INSTRUCTIONS)
    try:
        resp = client.models.generate_content(
            model=GEMINI_MODEL, contents=_gemini_history(history),
            config=_gemini_config(system=system, json_mode=True))
        parsed = _parse_json_lenient(resp.text) or {}
        text = (parsed.get("reply") or "").strip() or "Let's keep planning."
        goals = parsed.get("proposed_goals") or []
        clean = []
        for g in goals:
            if isinstance(g, dict) and g.get("title"):
                g.setdefault("metric", "carbon")
                clean.append(g)
        return {"ok": True, "text": text, "proposed_goals": clean,
                "history": history + [{"role": "assistant", "text": text}]}
    except Exception as exc:  # noqa: BLE001
        return {"ok": False, "text": _friendly_error(exc),
                "proposed_goals": [], "history": history}


# ===========================================================================
# 4. Bill / receipt image extraction
# ===========================================================================

_MEDIA_TYPES = {"png": "image/png", "jpg": "image/jpeg", "jpeg": "image/jpeg",
                "webp": "image/webp", "gif": "image/gif", "pdf": "application/pdf"}

_WATER_SCHEMA = {
    "type": "object",
    "properties": {
        "period_start": {"type": ["string", "null"]},
        "period_end": {"type": ["string", "null"]},
        "water_kl": {"type": ["number", "null"]},
        "consumption_is_printed": {"type": "boolean"},
        "bill_amount_rand": {"type": ["number", "null"]},
        "includes_non_water_charges": {"type": ["boolean", "null"]},
        "meter_reading_current": {"type": ["number", "null"]},
        "meter_reading_previous": {"type": ["number", "null"]},
        "municipality": {"type": ["string", "null"]},
        "uncertain_fields": {"type": "array", "items": {"type": "string"}},
        "notes": {"type": ["string", "null"]},
    },
    "required": ["period_start", "period_end", "water_kl", "consumption_is_printed",
                 "bill_amount_rand", "includes_non_water_charges",
                 "meter_reading_current", "meter_reading_previous",
                 "municipality", "uncertain_fields", "notes"],
    "additionalProperties": False,
}
_ELEC_SCHEMA = {
    "type": "object",
    "properties": {
        "period_start": {"type": ["string", "null"]},
        "period_end": {"type": ["string", "null"]},
        "kwh": {"type": ["number", "null"]},
        "bill_amount_rand": {"type": ["number", "null"]},
        "includes_non_electricity_charges": {"type": ["boolean", "null"]},
        "is_prepaid": {"type": ["boolean", "null"]},
        "purchases": {"type": ["array", "null"], "items": {
            "type": "object",
            "properties": {"kwh": {"type": ["number", "null"]},
                           "amount_rand": {"type": ["number", "null"]}},
            "required": ["kwh", "amount_rand"], "additionalProperties": False}},
        "tariff": {"type": ["string", "null"]},
        "municipality_or_utility": {"type": ["string", "null"]},
        "uncertain_fields": {"type": "array", "items": {"type": "string"}},
        "notes": {"type": ["string", "null"]},
    },
    "required": ["period_start", "period_end", "kwh", "bill_amount_rand",
                 "includes_non_electricity_charges", "is_prepaid", "purchases",
                 "tariff", "municipality_or_utility", "uncertain_fields", "notes"],
    "additionalProperties": False,
}


def extract_bill(file_bytes, filename, kind):
    """Extract structured fields from an uploaded bill (kind: water|electricity).

    Returns (ok, dict_or_error_message). The caller MUST show the values for
    user review before applying them (non-negotiable rule 6)."""
    prov = active_provider()
    if not file_bytes:
        return False, "That file appears to be empty — try uploading it again."
    if len(file_bytes) > 15 * 1024 * 1024:
        return False, ("That file is larger than 15 MB — a phone photo or a "
                       "single-page PDF works best.")
    ext = (filename or "").rsplit(".", 1)[-1].lower()
    media_type = _MEDIA_TYPES.get(ext, "image/jpeg")
    prompt = f"Extract the fields for this {kind} document."
    try:
        if prov == "anthropic":
            return _anthropic_extract(file_bytes, ext, media_type, kind, prompt)
        if prov == "gemini":
            return _gemini_extract(file_bytes, media_type, kind, prompt)
        return False, ai_status()[1]
    except Exception as exc:  # noqa: BLE001
        return False, _friendly_error(exc)


def _anthropic_extract(file_bytes, ext, media_type, kind, prompt):
    import base64
    client = _get_anthropic_client()
    if client is None:
        return False, _anthropic_error or "AI unavailable."
    data64 = base64.standard_b64encode(file_bytes).decode()
    if ext == "pdf":
        media_block = {"type": "document", "source": {
            "type": "base64", "media_type": "application/pdf", "data": data64}}
    else:
        media_block = {"type": "image", "source": {
            "type": "base64", "media_type": media_type, "data": data64}}
    schema = _WATER_SCHEMA if kind == "water" else _ELEC_SCHEMA
    response = client.messages.create(
        model=ANTHROPIC_MODEL, max_tokens=8000, thinking={"type": "adaptive"},
        system=_EXTRACT_SYSTEM,
        output_config={"format": {"type": "json_schema", "schema": schema}},
        messages=[{"role": "user", "content": [
            media_block, {"type": "text", "text": prompt}]}])
    if response.stop_reason == "refusal":
        return False, "The document could not be processed."
    text = next(b.text for b in response.content if b.type == "text")
    return True, json.loads(text)


def _gemini_extract(file_bytes, media_type, kind, prompt):
    client = _get_gemini_client()
    if client is None:
        return False, _gemini_error or "AI unavailable."
    schema_hint = _WATER_BILL_JSON if kind == "water" else _ELEC_BILL_JSON
    resp = client.models.generate_content(
        model=GEMINI_MODEL,
        contents=[genai_types.Part.from_bytes(data=file_bytes,
                                              mime_type=media_type),
                  prompt + "\n" + schema_hint],
        config=_gemini_config(system=_EXTRACT_SYSTEM, json_mode=True))
    parsed = _parse_json_lenient(resp.text)
    if parsed is None:
        return False, ("The document couldn't be read clearly — please enter "
                       "the values manually.")
    parsed.setdefault("uncertain_fields", [])
    return True, parsed
