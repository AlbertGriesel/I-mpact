"""
Design language (spec §3 & §16): light blue / green / white / soft grey,
rounded friendly cards, a consistent stroke-icon set (no emoji chrome), and
the reactive visuals — a daisy growing on a small Earth plus a nature
wallpaper, both shifting GRADUALLY with the user's impact score.

Interactive niceties that Streamlit doesn't offer natively are installed by
`enhance_ui()`, a tiny embedded web component:
  * press-and-hold auto-repeat on number-input steppers
  * select-all on focus for text/number inputs
  * dropdowns become select-only (no free text editing)
It runs once per browser page load and is idempotent.
"""

import html
import os
import re

import streamlit as st


def _flat(svg):
    """Collapse inline SVG to one line, no HTML comments — prevents Streamlit's
    markdown from leaking stray closing tags as visible text (§7)."""
    svg = re.sub(r"<!--.*?-->", "", svg, flags=re.DOTALL)
    return re.sub(r">\s+<", "><", svg).strip()

# --- brand logo assets (the half-Earth-and-sprout "I/mpact" mark) ---
_ROOT = os.path.dirname(os.path.abspath(__file__))
LOGO_FULL = os.path.join(_ROOT, "Logos", "logowithtext-removebg-preview.png")
LOGO_ICON = os.path.join(_ROOT, "Logos", "logonotext-removebg-preview.png")

# palette
GREEN = "#2E9E63"
DEEP = "#1B5E3B"
BLUE = "#7EC8E3"
SOFT = "#F4F7F6"

# --- "Living Atlas" design tokens (redesign): a daylight-ecology palette.
# One saturated action-green; natural daylight accents used sparingly so CTAs
# and key states pop. These are the single source of colour for the new
# components and are also emitted as CSS custom properties in inject_theme.
LEAF = "#33B06A"        # brighter action green (gradients pair with GREEN)
SKY = "#8FD3F4"         # pale sky
RIVER = "#3E9BD6"       # river/water blue
SUN = "#FFC94D"         # sunlight yellow
SOIL = "#9C6B3F"        # soil brown
CORAL = "#EF6F5B"       # warnings ONLY
TEAL = "#22B3A0"        # soft teal
MIST = "#F3F8F4"        # leaf-tinted neutral
CREAM = "#fdfbf3"       # warm off-white base
DAY_SKY = "#8BD3F2"     # solid, lighter, cheerful daylight blue (brief §2/§10)
NIGHT_SKY = "#0e2233"   # solid deep navy for the dark theme

# ---------------------------------------------------------------------------
# Central environmental-state model (spec §6, §40)
# ---------------------------------------------------------------------------
# ONE source of truth mapping the impact score (0–100) to a tier. The
# landscape, mascot, avatar treatment and the top-right indicator ALL derive
# their state from env_tier() so they can never disagree. Thresholds are
# documented here and used everywhere.
#
# Aligned to the scoring semantics (spec §18): 50 ≈ average impact, 100 = net
# zero, >100 = genuinely net-positive (offsets/removals exceed emissions — the
# score itself is never capped at 100). Thresholds match the score bands so
# the scene's richness always agrees with the score.
#   score is None  -> NO_ASSESSMENT   (welcoming, hopeful default scene)
#   score  < 25    -> VERY_POOR       (very high impact)
#   25 <= s < 40   -> POOR            (high impact)
#   40 <= s < 60   -> AVERAGE         (around average — pleasant, room to grow)
#   60 <= s < 80   -> GOOD            (lower impact)
#   80 <= s < 100  -> EXCELLENT       (very low impact)
#   100 <= s < 101 -> NET_ZERO        (zero net impact under the methodology)
#   s   >= 101     -> NET_POSITIVE    (net-positive contribution)
ENV_TIERS = ("NO_ASSESSMENT", "VERY_POOR", "POOR", "AVERAGE", "GOOD",
             "EXCELLENT", "NET_ZERO", "NET_POSITIVE")
_TIER_THRESHOLDS = ((25, "VERY_POOR"), (40, "POOR"), (60, "AVERAGE"),
                    (80, "GOOD"), (100, "EXCELLENT"), (101, "NET_ZERO"),
                    (10 ** 9, "NET_POSITIVE"))
TIER_LABEL = {
    "NO_ASSESSMENT": "Not assessed yet",
    "VERY_POOR": "Needs urgent care",
    "POOR": "Room to improve",
    "AVERAGE": "Doing okay",
    "GOOD": "Healthy",
    "EXCELLENT": "Thriving",
    "NET_ZERO": "Net zero",
    "NET_POSITIVE": "Net positive",
}


def env_tier(score):
    """The single environmental tier for a score (or None → NO_ASSESSMENT)."""
    if score is None:
        return "NO_ASSESSMENT"
    for cutoff, name in _TIER_THRESHOLDS:
        if score < cutoff:
            return name
    return "NET_POSITIVE"


# Vibrant score spectrum (spec §17/§19) — NO muddy "sludge" tones. Worst → best
# runs neon-red → orange → amber → yellow-green → bright green → neon green,
# with a distinct premium green for genuine net-positive (>100).
def score_color(score):
    if score is None:
        return "#9aa3ad"          # neutral grey — not assessed
    s = score
    if s < 25:   return "#FF3B30"  # neon red — very high impact
    if s < 40:   return "#FF7A1A"  # bright orange — high impact
    if s < 60:   return "#F4C020"  # amber/yellow — around average
    if s < 80:   return "#9BD435"  # yellow-green — lower impact
    if s < 100:  return "#34C759"  # bright green — very low impact
    if s < 101:  return "#00E676"  # neon green — net zero
    return "#00B050"               # premium deep green — net positive


def score_label(score):
    """The §18 impact-band label for a score (semantics consistent app-wide)."""
    if score is None:
        return "Not assessed yet"
    s = score
    if s >= 101:  return "Net positive"
    if s >= 100:  return "Net zero impact"
    if s >= 80:   return "Very low impact"
    if s >= 60:   return "Lower impact"
    if s >= 40:   return "Around average"
    if s >= 25:   return "High impact"
    return "Very high impact"


# Darker, high-contrast counterparts of score_color — safe for TEXT on light
# backgrounds (brief §5: light yellow on light blue is unreadable, so status
# text uses a deep amber, never the bright fill colour).
def score_text_color(score):
    if score is None:
        return "#5c7069"
    s = score
    if s < 25:   return "#C21A10"   # deep red
    if s < 40:   return "#C2560A"   # deep orange
    if s < 60:   return "#8A6300"   # deep amber (readable, not light yellow)
    if s < 80:   return "#4E7A00"   # deep yellow-green
    if s < 100:  return "#1E8E3E"   # green
    if s < 101:  return "#00994D"   # bright green
    return "#00753A"                # premium deep green — net positive


def score_hint(score):
    """One-sentence, scoring-logic-backed explanation for the ring's hover
    tooltip (brief §14). Only states what the 50/100/>100 semantics support."""
    if score is None:
        return "Complete an assessment to see your impact score."
    val = int(round(score))
    if val >= 101:
        return (f"{val} — Net positive. Your offsets and removals exceed your "
                "emissions under the app's methodology.")
    if val >= 100:
        return f"{val} — Net zero environmental impact under the app's methodology."
    if val >= 60:
        return (f"{val} — Lower impact than the average benchmark of 50: a "
                "smaller footprint than a typical household.")
    if val >= 40:
        rel = "just above" if val >= 50 else "slightly below"
        return f"{val} — Around the average benchmark of 50 ({rel} it)."
    return (f"{val} — Below the average benchmark of 50: a higher impact, with "
            "clear room to improve.")

# ---------------------------------------------------------------------------
# Icon set — small stroke SVGs (feather-style), consistent and quiet
# ---------------------------------------------------------------------------

_ICON_PATHS = {
    "water": "<path d='M12 2.7C8.8 7 6 10.4 6 14a6 6 0 0 0 12 0c0-3.6-2.8-7-6-11.3z'/>",
    "bolt": "<path d='M13 2 4.5 14H11l-1 8L18.5 10H12l1-8z'/>",
    "cloud": "<path d='M6.8 18.5h10.4a4 4 0 0 0 .5-8A6 6 0 0 0 6 12.2a3.6 3.6 0 0 0 .8 6.3z'/>",
    "leaf": "<path d='M20 4C11 4 5.5 9.5 5.5 19c9.5 0 15-5.5 14.5-15z'/><path d='M5.5 19C9 13 13 9 18 6.5'/>",
    "flame": "<path d='M12 3c1 3 5 5 5 9.5a5 5 0 0 1-10 0C7 8.5 10 7.5 12 3z'/>",
    "trophy": "<path d='M8 21h8M12 17v4M7 4h10v5a5 5 0 0 1-10 0V4z'/><path d='M7 6H4v1a3 3 0 0 0 3 3M17 6h3v1a3 3 0 0 1-3 3'/>",
    "check": "<path d='M4 12.5 9.5 18 20 6.5'/>",
    "target": "<circle cx='12' cy='12' r='9'/><circle cx='12' cy='12' r='4.5'/>",
    "calendar": "<rect x='4' y='5' width='16' height='16' rx='2'/><path d='M8 3v4M16 3v4M4 11h16'/>",
    "lock": "<rect x='5' y='11' width='14' height='9' rx='2'/><path d='M8 11V7a4 4 0 0 1 8 0v4'/>",
    "star": "<path d='M12 3.5l2.6 5.3 5.9.9-4.2 4.1 1 5.8-5.3-2.8-5.3 2.8 1-5.8L3.5 9.7l5.9-.9L12 3.5z'/>",
    "file": "<path d='M14 3H7a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h10a2 2 0 0 0 2-2V8l-5-5z'/><path d='M14 3v5h5'/>",
    "trend-down": "<path d='M3 7l7 7 4-4 7 7'/><path d='M21 11v6h-6'/>",
    "scissors": "<circle cx='6' cy='6' r='2.5'/><circle cx='6' cy='18' r='2.5'/><path d='M8.2 7.8 20 19M8.2 16.2 20 5'/>",
    "sun": "<circle cx='12' cy='12' r='4.5'/><path d='M12 2.5v3M12 18.5v3M2.5 12h3M18.5 12h3M5 5l2 2M17 17l2 2M19 5l-2 2M7 17l-2 2'/>",
    "users": "<circle cx='9' cy='8' r='3.5'/><path d='M3 20c0-3.3 2.7-6 6-6s6 2.7 6 6'/><circle cx='17' cy='9' r='2.5'/><path d='M16.5 14.5c2.8.3 4.5 2.6 4.5 5.5'/>",
    "car": "<path d='M5 15l1.4-4.6A2 2 0 0 1 8.3 9h7.4a2 2 0 0 1 1.9 1.4L19 15'/><rect x='3.5' y='15' width='17' height='4' rx='1.5'/><circle cx='7.5' cy='19' r='1.5'/><circle cx='16.5' cy='19' r='1.5'/>",
    "plane": "<path d='M2.5 11.5 21 3l-6.5 18-3-7.5-9-2z'/><path d='M21 3 11.5 13.5'/>",
    "food": "<path d='M4 13a8 8 0 0 0 16 0H4z'/><path d='M9 13V7M15 13V5M12 13V8'/>",
    "map": "<path d='M9 4 3 6v14l6-2 6 2 6-2V4l-6 2-6-2z'/><path d='M9 4v14M15 6v14'/>",
    "chat": "<path d='M21 11.5a8 8 0 0 1-8 8H5.5L3 22V11.5a8 8 0 0 1 8-8h2a8 8 0 0 1 8 8z'/>",
    "edit": "<path d='M17 3l4 4L8 20l-5 1 1-5L17 3z'/>",
    "chart": "<path d='M4 20V10M10 20V4M16 20v-7M21 20H3'/>",
    "key": "<circle cx='8' cy='15' r='4'/><path d='M11 12 21 2M16 7l3 3'/>",
    "battery": "<rect x='2.5' y='8' width='16' height='8.5' rx='2'/><path d='M21.5 10.5v3.5'/><path d='M11 9.5 8.5 12.4h4L10 15.2'/>",
    "search": "<circle cx='10.5' cy='10.5' r='6.5'/><path d='M15.5 15.5 21 21'/>",
    "circle": "<circle cx='12' cy='12' r='7.5'/>",
}


def icon(name, size=16, color=DEEP, stroke=2.0):
    path = _ICON_PATHS.get(name, _ICON_PATHS["leaf"])
    return (f"<svg width='{size}' height='{size}' viewBox='0 0 24 24' "
            f"fill='none' stroke='{color}' stroke-width='{stroke}' "
            f"stroke-linecap='round' stroke-linejoin='round' "
            f"style='vertical-align:-{size // 6}px'>{path}</svg>")


def pill(text, icon_name=None, color=DEEP):
    ic = icon(icon_name, 13, color) + " " if icon_name else ""
    return (f"<span class='pill'>{ic}{text}</span>")


def brand_lockup():
    """A crisp, self-contained vector brand mark (brief §2): a small Earth with
    a sprout (environment + growth) and a rising measurement arrow, beside the
    'I/mpact' wordmark. Pure SVG + themed HTML text, so it stays sharp at any
    size and reads on both light and dark themes."""
    return _flat(f"""
<div class="brand-lockup">
  <svg class="brand-icon" viewBox="0 0 64 64" width="66" height="66"
       role="img" aria-label="I/mpact logo">
    <circle cx="30" cy="34" r="27" fill="rgba(51,176,106,.12)"/>
    <circle cx="30" cy="40" r="18" fill="{RIVER}"/>
    <path d="M13 40 q6 -5 12 -2 q8 3 16 -1 q0 12 -14 12 q-12 0 -14 -9z"
          fill="{LEAF}"/>
    <path d="M30 41 C 30 31 29 24 30 15" stroke="{GREEN}" stroke-width="3.6"
          fill="none" stroke-linecap="round"/>
    <path d="M30 27 q-10 -2 -13 -11 q10 -1 13 6z" fill="{GREEN}"/>
    <path d="M30 22 q10 -3 13 -12 q-10 -1 -13 7z" fill="{LEAF}"/>
    <circle cx="30" cy="40" r="18" fill="none" stroke="#ffffff"
            stroke-opacity=".65" stroke-width="1.4"/>
    <path d="M44 30 l7 -7 M51 23 l-5 0 M51 23 l0 5" stroke="{SUN}"
          stroke-width="3" fill="none" stroke-linecap="round"
          stroke-linejoin="round"/>
  </svg>
  <span class="brand-text">
    <span class="brand-name">I<span class="brand-slash">/</span>mpact</span>
    <span class="brand-tag">Measure · Understand · Improve</span>
  </span>
</div>""")


# ---------------------------------------------------------------------------
# Reactive scene parameters (gradual, never binary)
# ---------------------------------------------------------------------------

def _lerp(a, b, t):
    return a + (b - a) * t


def _hex_lerp(h1, h2, t):
    c1 = [int(h1[i:i + 2], 16) for i in (1, 3, 5)]
    c2 = [int(h2[i:i + 2], 16) for i in (1, 3, 5)]
    return "#" + "".join(f"{int(round(_lerp(a, b, t))):02x}" for a, b in zip(c1, c2))


def scene_params(score, theme="light"):
    """Continuous (never binary) visual parameters for the given score and
    theme. `t` runs 0 (very poor) → 1 (net zero, score 100) so every visual
    trait can be interpolated for GRADUAL progression (spec §12); colour lerps
    stay inside [0,1] while the separate `netpos` flag unlocks the premium
    treatment for genuine >100 net-positive scores (spec §18) — richness keeps
    responding above 100 instead of silently flattening. Theme only swaps the
    day/night palette — environmental health is independent (spec §17)."""
    t = max(0.0, min(1.0, (score if score is not None else 55) / 100.0))
    netpos = score is not None and score >= 100
    night = theme == "dark"
    if night:
        # nighttime nature: navy sky, moonlight; greens deepen with health
        sky_top = _hex_lerp("#0a1626", "#0e2340", t)
        sky_bottom = _hex_lerp("#241f1a", "#123249", t)
        hill_far = _hex_lerp("#2a3330", "#1c4a34", t)
        hill_near = _hex_lerp("#1a211d", "#123b22", t)
        grass = _hex_lerp("#20281f", "#17532f", t)
        sun_color = "#eaf2ff"          # the moon
    else:
        # daytime: ONE solid, vibrant, cheerful light blue for the sky —
        # never a gradient or washed-out transition (brief §2 hard requirement).
        # Environmental health shows in the SCENERY (hills/plants/clouds), not
        # by fading the sky, so the sky colour is deliberately score-independent.
        sky_top = sky_bottom = DAY_SKY
        hill_far = _hex_lerp("#bcd3ac", "#a8e7ab", t)
        hill_near = _hex_lerp("#9cc084", "#63d089", t)
        grass = _hex_lerp("#8fb673", "#46c66f", t)
        sun_color = "#FFDE7A"
    return {
        "t": t,
        "tier": env_tier(score),
        "netpos": netpos,
        "night": night,
        # --- legacy keys (mascot / score_ring rely on these) ---
        "sky_top": sky_top,
        "sky_bottom": sky_bottom,
        "sun_opacity": round((0.35 + 0.6 * t) if night else (0.2 + 0.8 * t), 2),
        "cloud_opacity": round(max(0.08, 0.9 - 1.05 * t), 2),
        "haze_opacity": round(max(0.0, 0.5 - 0.95 * t), 2),
        "earth_bright": round((0.6 + 0.4 * t) if night else (0.9 + 0.28 * t), 2),
        "droop": round((1 - t) * 55),
        # Low-end colours stay CLEAR, not muddy (§17): a pale ivory petal and a
        # soft-but-clean green leaf — the struggle shows in droop and scenery,
        # never in sludge tones.
        "petal": _hex_lerp("#f4ecdc", "#ffffff", t) if not night
                 else _hex_lerp("#98a2b8", "#dbe6f2", t),
        "leaf": _hex_lerp("#9cc47e", "#4fc47a", t) if not night
                else _hex_lerp("#3d5a45", "#2f9457", t),
        "fire_opacity": round(max(0.0, (0.3 - t)) / 0.3 * 0.7, 2) if t < 0.3 else 0.0,
        "sway": t > 0.45,
        # --- new scene keys (landscape) ---
        "hill_far": hill_far,
        "hill_near": hill_near,
        "grass": grass,
        "sun_color": sun_color,
        "star_opacity": round(max(0.0, 0.85 * (0.4 + 0.6 * t)), 2) if night else 0.0,
        "litter_opacity": round(max(0.0, 0.75 - 1.1 * t), 2),   # more litter when poor
        "smoke_opacity": round(max(0.0, 0.6 - 1.0 * t), 2),     # smoke fades as it recovers
    }


# ---------------------------------------------------------------------------
# Global theme + reactive wallpaper
# ---------------------------------------------------------------------------

def _a(x):
    """opacity 0–1 → 2-digit hex alpha."""
    return f"{max(0, min(255, int(round(x * 255)))):02x}"


def _bottom_scene(p):
    """A lightweight, peripheral horizon scene for the page bottom (spec §3–§13):
    layered rolling hills, simplified trees, soft clouds, and — only as the
    score worsens — gentle smoke, litter and a distant fire glow. Stays behind
    content so reading areas remain calm (spec §5)."""
    night = p["night"]
    foliage = _hex_lerp("#20402e", "#2f8f57", p["t"]) if not night \
        else _hex_lerp("#16261c", "#215f3a", p["t"])
    trunk = "#7a5230" if not night else "#4a3320"
    parts = []

    # soft clouds / moonlit clouds near the horizon top
    cloud_fill = "#ffffff" if not night else "#c9d6e6"
    for cx, cy, rx, dly in [(230, 46, 34, 0), (250, 40, 22, 0), (1080, 60, 30, -5)]:
        parts.append(f"<ellipse cx='{cx}' cy='{cy}' rx='{rx}' ry='{rx * 0.42:.0f}' "
                     f"fill='{cloud_fill}' opacity='{min(0.85, p['cloud_opacity']):.2f}'/>")
    # stars (night only)
    if night and p["star_opacity"] > 0:
        for x, y in [(120, 40), (330, 66), (540, 34), (770, 58), (995, 44),
                     (1190, 70), (1330, 36), (430, 92), (900, 96)]:
            parts.append(f"<circle cx='{x}' cy='{y}' r='1.8' fill='#ffffff' "
                         f"opacity='{p['star_opacity']:.2f}'/>")

    # far + near hills
    parts.append(f"<path d='M0 150 Q 300 70 620 130 T 1200 120 T 1440 135 "
                 f"L1440 320 L0 320 Z' fill='{p['hill_far']}' opacity='0.9'/>")
    parts.append(f"<path d='M0 205 Q 360 130 720 195 T 1440 190 "
                 f"L1440 320 L0 320 Z' fill='{p['hill_near']}'/>")
    # grass foreground
    parts.append(f"<rect x='0' y='262' width='1440' height='58' fill='{p['grass']}'/>")

    # trees — more of them, and taller, as health improves
    n_trees = 2 + round(4 * p["t"])
    for i in range(n_trees):
        x = 90 + i * (1260 / max(1, n_trees - 1)) if n_trees > 1 else 700
        x = int(x)
        s = 0.8 + 0.5 * p["t"]
        base = 248
        parts.append(
            f"<rect x='{x - 3}' y='{base}' width='6' height='{int(20 * s)}' rx='3' fill='{trunk}'/>"
            f"<circle cx='{x}' cy='{base - int(8 * s)}' r='{int(15 * s)}' fill='{foliage}'/>"
            f"<circle cx='{x - int(11 * s)}' cy='{base}' r='{int(11 * s)}' fill='{foliage}'/>"
            f"<circle cx='{x + int(11 * s)}' cy='{base}' r='{int(11 * s)}' fill='{foliage}'/>")

    # flowers dotting the grass when thriving
    if p["t"] > 0.55:
        for fx in range(120, 1440, 180):
            parts.append(f"<circle cx='{fx}' cy='288' r='4' fill='#ffd45e'/>"
                         f"<circle cx='{fx}' cy='288' r='2' fill='#fff3c0'/>")

    # litter (poor states) — small scattered coloured bits on the grass
    if p["litter_opacity"] > 0.02:
        for lx, lc in [(210, '#c96'), (480, '#a97'), (760, '#b85'), (1030, '#9a7'),
                       (1250, '#c86'), (350, '#aa8')]:
            parts.append(f"<rect x='{lx}' y='290' width='9' height='5' rx='2' "
                         f"fill='{lc}' opacity='{p['litter_opacity']:.2f}'/>")

    # distant factory + smoke (poor states) — whimsical, not grim (§4)
    if p["smoke_opacity"] > 0.02:
        so = p["smoke_opacity"]
        parts.append(
            f"<g opacity='{so:.2f}'>"
            f"<rect x='1300' y='150' width='60' height='60' fill='#6b7280'/>"
            f"<rect x='1312' y='132' width='12' height='24' fill='#565f6b'/>"
            f"<rect x='1338' y='140' width='12' height='16' fill='#565f6b'/>"
            f"<circle cx='1318' cy='120' r='12' fill='#8a919b'/>"
            f"<circle cx='1332' cy='108' r='14' fill='#9aa0aa'/>"
            f"<circle cx='1348' cy='98' r='10' fill='#aab0b8'/></g>")

    # distant fire glow (very poor only)
    if p["fire_opacity"] > 0.02:
        parts.append(f"<ellipse cx='120' cy='250' rx='70' ry='24' fill='#ff8a3c' "
                     f"opacity='{p['fire_opacity']:.2f}'/>")

    svg = ("<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 1440 320' "
           "preserveAspectRatio='xMidYMax slice'>" + "".join(parts) + "</svg>")
    return "data:image/svg+xml;utf8," + svg.replace("#", "%23")


# Dark-theme overrides (spec §14/§16). A nature-night skin for the MAIN
# surfaces — inserted only when the dark theme is active, so light mode is
# untouched. Plain string (normal CSS braces): it is interpolated verbatim
# into the inject_theme f-string, so its braces are not re-parsed.
_DARK_CSS = """
    .stApp, .stApp p, .stApp li, .stApp label, .stApp span,
    [data-testid="stMarkdownContainer"], [data-testid="stMarkdownContainer"] * {
        color: #e6edf0;
    }
    h1, h2, h3 { color: #8fe0ad !important; }
    section[data-testid="stSidebar"] {
        background: linear-gradient(180deg, #0f1b28 0%, #0b141d 100%) !important;
        border-right: 1px solid #24323d;
    }
    section[data-testid="stSidebar"] * { color: #d6e0e3; }
    .wordmark { color: #8fe0ad !important; }
    div[data-testid="stVerticalBlockBorderWrapper"],
    div[data-testid="stLayoutWrapper"]:has(> [data-testid="stVerticalBlock"]),
    .impact-kpi {
        background: #15202b !important; border-color: #25323d !important;
        box-shadow: 0 4px 18px rgba(0,0,0,0.35) !important;
    }
    .impact-kpi .t, .impact-kpi .u { color: #9fb0ad; }
    .impact-kpi .v { color: #eaf3ee; }
    .impact-kpi .b { color: #8fa39c; }
    input, textarea, div[data-baseweb="select"] > div:first-child {
        background: #101a24 !important; color: #e6edf0 !important;
    }
    div[data-baseweb="popover"] div, ul[role="listbox"], li[role="option"] {
        background: #15202b !important; color: #e6edf0 !important;
    }
    .pill { background: #1b2833 !important; border-color: #2b3a45 !important;
            color: #cfe9db !important; }
    div[class*="st-key-band"] {
        background: rgba(46,158,99,0.12) !important;
        border-color: rgba(46,158,99,0.24) !important;
    }
    div[class*="st-key-band"] div[data-testid="stVerticalBlockBorderWrapper"],
    div[class*="st-key-band"] div[data-testid="stLayoutWrapper"] {
        background: #15202b !important;
    }
    .impact-userchip {
        background: rgba(21,32,43,0.92) !important; border-color: #2b3a45 !important;
        color: #e6edf0 !important;
    }
    .impact-userchip .avatar { background: #1b2833; border-color: #2b3a45; }
    .stButton > button, .stFormSubmitButton > button {
        color: #e6edf0; border-color: #2b3a45; background: #16222d;
    }
    .stButton > button[kind="primary"], .stFormSubmitButton > button[kind="primary"] {
        color: #062012;
    }
    [data-testid="stCaptionContainer"], [data-testid="stCaptionContainer"] * ,
    small { color: #9fb0ad !important; }
    [data-testid="stExpander"] { background: #15202b !important;
        border-color: #25323d !important; }
    .st-key-assistant_panel { background: #15202b !important;
        border-color: #2b3a45 !important; }
    .st-key-assistant_panel [data-testid="stChatMessage"] { background: #1b2833 !important; }
    .st-key-assistant_panel [data-testid="stChatMessage"]:has(
        [data-testid="stChatMessageAvatarUser"]) { background: #16303f !important; }
    .st-key-assistant_panel [data-testid="stTextInputRootElement"],
    .st-key-assistant_panel [data-testid="stTextInput"] input {
        background: #101a24 !important;
    }
"""


def inject_theme(score=None, theme="light"):
    p = scene_params(score, theme)
    night = theme == "dark"
    scene = _bottom_scene(p)
    # design tokens (spec §43) — one place for both themes
    bg = "#0d1620" if night else "#fdfbf3"   # warm off-white / cream (light)
    sun_glow = f"{p['sun_color']}{_a(p['sun_opacity'] * (0.6 if night else 0.5))}"
    sky_solid = NIGHT_SKY if night else DAY_SKY
    # single soft reading surface behind page content (brief §1): light, airy,
    # semi-opaque, softly rounded — keeps text legible over the solid sky and
    # scenery without turning the app into a wall of separate cards.
    surface = "rgba(17,28,38,0.86)" if night else "rgba(255,253,247,0.86)"
    surface_border = ("rgba(43,58,69,0.6)" if night
                      else "rgba(255,255,255,0.65)")
    dark_overrides = _DARK_CSS if night else ""
    st.markdown(f"""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Baloo+2:wght@500;600;700;800&family=Nunito:wght@400;500;600;700;800&display=swap');
    :root {{
        --imp-bg: {bg};
        --imp-card: {"#15202b" if night else "#ffffff"};
        --imp-text: {"#e6edf0" if night else "#264a3b"};
        --imp-muted: {"#9fb0ad" if night else "#5c7069"};
        --imp-border: {"#25323d" if night else "#e6efe0"};
        --imp-green: {GREEN};
        --imp-deep: {"#8fe0ad" if night else DEEP};
    }}
    /* friendly rounded typography (spec §4). Set only on .stApp so text
       elements INHERIT it — icon fonts keep their own font-family. */
    .stApp {{ font-family: 'Nunito', 'Source Sans Pro', system-ui, sans-serif; }}
    h1, h2, h3, h4, [data-testid="stHeading"], .wordmark,
    .stButton > button, .stFormSubmitButton > button,
    .impact-kpi .v {{
        font-family: 'Baloo 2', 'Nunito', sans-serif !important;
        letter-spacing: 0;
    }}
    /* SKY: one solid, vibrant light blue — no gradient (brief §2). The only
       overlay is a small, localised sun glow (a sunlight element, allowed). */
    .stApp {{
        background:
            radial-gradient(30vw 26vw at 86% 3%, {sun_glow} 0%, transparent 58%),
            {sky_solid};
        background-attachment: fixed;
    }}
    .stApp::before {{
        content: ""; position: fixed; left: 0; right: 0; bottom: 0; height: 44vh;
        max-height: 340px;
        background: url("{scene}") bottom center / cover no-repeat;
        pointer-events: none; z-index: 0; opacity: {0.92 if not night else 0.85};
    }}
    @media (prefers-reduced-motion: reduce) {{
        .cloud, .sunrays, .daisy, .st-key-assistant_fab button,
        .st-key-assistant_fab::before {{ animation: none !important; }}
        .st-key-assistant_fab::before {{ opacity: 0 !important; }}
    }}
    section.main > div {{ position: relative; z-index: 1; }}
    /* NO full-page white sheet — the content column is transparent so the
       illustrated sky + scenery show BETWEEN sections (brief §1). Readability
       comes from per-section translucent panels (below), not one big card,
       and the block sizes to its content (fixes sparse-page empty space §2). */
    [data-testid="stMainBlockContainer"], section.main .block-container {{
        background: transparent;
        padding-top: 1.4rem; padding-bottom: 2rem;
        max-width: 1180px;
    }}
    /* loose headings/text sit directly on the sky — keep them crisp & legible */
    .stApp [data-testid="stMarkdownContainer"] h1,
    .stApp [data-testid="stMarkdownContainer"] h2,
    .stApp [data-testid="stMarkdownContainer"] h3 {{
        text-shadow: {"none" if night else "0 1px 2px rgba(255,255,255,0.55)"};
    }}

    h1, h2, h3 {{ color: {DEEP}; }}
    /* hide the "Press Enter to apply" hint — values apply on their own */
    div[data-testid="InputInstructions"] {{ display: none; }}
    /* tooltips are informational — make them click-through so a tooltip that
       pops up under the cursor can never steal the hover from its trigger
       (the enter/leave loop users see as "flicker") */
    div[data-testid="stTooltipContent"], div[data-baseweb="tooltip"],
    div[data-baseweb="popover"][role="tooltip"], div[role="tooltip"] {{
        pointer-events: none !important;
    }}
    .stButton > button, .stFormSubmitButton > button {{
        border-radius: 999px !important; border: 1.5px solid {GREEN}44;
        font-weight: 700;
        transition: transform .16s cubic-bezier(.34,1.4,.64,1),
                    box-shadow .16s ease, filter .16s ease;
    }}
    /* HOVER STABILITY RULE (applies app-wide): hover must never MOVE the
       element it is bound to — a cursor resting near an edge would fall out
       of the moved hitbox and re-enter it in a loop (visible flicker).
       Buttons respond with shadow + brightness only. */
    .stButton > button:hover, .stFormSubmitButton > button:hover {{
        box-shadow: 0 9px 22px rgba(46,158,99,0.30);
        filter: brightness(1.03);
    }}
    .stButton > button:active, .stFormSubmitButton > button:active {{
        filter: brightness(0.97);
    }}
    .stButton > button[kind="primary"], .stFormSubmitButton > button[kind="primary"] {{
        background: linear-gradient(135deg, #35b26f, #59cd8c); border: none;
        color: #ffffff;
    }}
    .stButton > button[kind="primary"]:hover, .stFormSubmitButton > button[kind="primary"]:hover {{
        filter: brightness(1.05);
    }}
    .stButton > button:disabled {{
        background: #eef2f0 !important; color: #9bb0a8 !important;
        border-color: #e3edea; transform: none !important; box-shadow: none !important;
    }}
    /* section panels: readable warm-white (or dark) over the sky/scenery,
       softly rounded, with breathing room so the background shows between
       them (brief §1). Not a wall of tiny cards — these wrap real sections.
       NOTE: this Streamlit build renders border=True containers as
       stLayoutWrapper (stVerticalBlockBorderWrapper kept for older builds). */
    div[data-testid="stVerticalBlockBorderWrapper"],
    div[data-testid="stLayoutWrapper"]:has(> [data-testid="stVerticalBlock"]) {{
        background: {surface}; border-radius: 22px;
        border: 1px solid {surface_border};
        box-shadow: 0 8px 26px rgba(20,60,42,0.10);
        transition: transform .18s ease, box-shadow .18s ease;
    }}
    /* §10 read-only tier: containers respond subtly to presence — shadow
       only, never movement (see HOVER STABILITY RULE) */
    div[data-testid="stVerticalBlockBorderWrapper"]:hover,
    div[data-testid="stLayoutWrapper"]:has(> [data-testid="stVerticalBlock"]):hover {{
        box-shadow: 0 14px 32px rgba(20,60,42,0.16);
    }}
    section[data-testid="stSidebar"] {{
        background: linear-gradient(180deg, #ffffff 0%, #eef7e8 100%);
        border-right: 1px solid #e6efe0;
    }}
    /* §8 — a larger, clearly readable app logo in the top-left (both the
       expanded-sidebar and collapsed/header placements) */
    [data-testid="stSidebarHeader"] {{ padding-top: .6rem; padding-bottom: .2rem; }}
    [data-testid="stSidebarHeader"] img, [data-testid="stLogo"],
    [data-testid="stSidebarLogo"], [data-testid="stHeaderLogo"] {{
        height: 78px !important; width: auto !important;
        max-width: none !important;
        image-rendering: -webkit-optimize-contrast;
    }}
    /* §9 — larger, darker, easier-to-scan sidebar navigation */
    [data-testid="stSidebarNav"] a {{
        padding: .38rem .55rem !important; margin: .14rem 0 !important;
        border-radius: 12px;
    }}
    [data-testid="stSidebarNav"] a span,
    [data-testid="stSidebarNav"] a p {{
        font-size: 1.08rem !important; font-weight: 700 !important;
        color: {"#e2ecef" if night else "#1c3a30"} !important;
    }}
    /* section headers ("Start", "Measure", …) readable, not faint microtext */
    [data-testid="stSidebarNav"] header,
    [data-testid="stSidebarNav"] [data-testid="stNavSectionHeader"] {{
        font-size: .84rem !important; font-weight: 800 !important;
        letter-spacing: .08em; color: {"#9fb0ad" if night else "#48635a"} !important;
    }}
    [data-testid="stSidebarNav"] a:hover {{
        background: {"rgba(143,224,173,0.12)" if night else "rgba(46,158,99,0.12)"};
    }}
    [data-testid="stSidebarNav"] a[aria-current="page"],
    [data-testid="stSidebarNav"] a[aria-current="true"] {{
        background: {"rgba(143,224,173,0.20)" if night else "rgba(46,158,99,0.18)"};
    }}
    [data-testid="stSidebarNav"] a[aria-current] span,
    [data-testid="stSidebarNav"] a[aria-current] p {{
        color: {"#8fe0ad" if night else "#155e3b"} !important; font-weight: 800 !important;
    }}
    section[data-testid="stSidebar"] [data-testid="stSidebarNav"] {{ margin-bottom: .4rem; }}
    /* §20 / KPI symmetry — paired columns stretch to equal height, and the
       whole wrapper chain down to the card/tile fills that height so three
       side-by-side KPI tiles align top AND bottom regardless of text length. */
    [data-testid="stHorizontalBlock"] {{ align-items: stretch; }}
    [data-testid="stColumn"] > div[data-testid="stVerticalBlock"] {{ height: 100%; }}
    [data-testid="stColumn"] div[data-testid="stVerticalBlockBorderWrapper"],
    [data-testid="stColumn"] > div[data-testid="stLayoutWrapper"] {{ height: 100%; }}
    /* the KPI tile lives 4 wrappers deep inside a flex-column vertical block;
       make each wrapper fill so the tile reaches the stretched column height */
    [data-testid="stColumn"] div[data-testid="stElementContainer"]:has(.stat-tile),
    [data-testid="stColumn"] div[data-testid="stElementContainer"]:has(.impact-kpi) {{
        flex: 1 0 auto; height: 100%;
    }}
    /* §5 — the two assessment-method cards: equal height, action links
       bottom-aligned so the pair reads as one symmetrical choice. */
    .st-key-measure_cards [data-testid="stColumn"] > div[data-testid="stVerticalBlock"],
    .st-key-measure_cards div[data-testid="stVerticalBlockBorderWrapper"],
    .st-key-measure_cards div[data-testid="stLayoutWrapper"] {{ height: 100%; }}
    .st-key-measure_cards div[data-testid="stLayoutWrapper"]
        > div[data-testid="stVerticalBlock"] {{
        height: 100%; display: flex; flex-direction: column;
    }}
    .st-key-measure_cards [data-testid="stPageLink"] {{ margin-top: auto; }}
    [data-testid="stColumn"] .stMarkdown:has(.stat-tile),
    [data-testid="stColumn"] .stMarkdown:has(.stat-tile) > div,
    [data-testid="stColumn"] div[data-testid="stMarkdownContainer"]:has(.stat-tile),
    [data-testid="stColumn"] .stMarkdown:has(.impact-kpi),
    [data-testid="stColumn"] .stMarkdown:has(.impact-kpi) > div,
    [data-testid="stColumn"] div[data-testid="stMarkdownContainer"]:has(.impact-kpi) {{
        height: 100%;
    }}
    /* §10 — editable fields respond gently to focus */
    .stTextInput input:focus, .stNumberInput input:focus,
    .stTextArea textarea:focus {{
        box-shadow: 0 0 0 3px rgba(46,158,99,0.18) !important;
        border-color: {GREEN} !important;
    }}
    /* AI-Assessment prompt box: give the block AROUND the typing field a
       darker, clearly-defined green frame so it stands out from the page
       (the default was a near-white wrapper that blended in), with a clean
       light field inside. */
    [data-testid="stChatInput"] > div {{
        background: #cddcd2 !important;
        border: 2px solid {GREEN} !important;
        border-radius: 16px !important;
        padding: 4px !important;
        box-shadow: 0 6px 18px rgba(20,60,42,0.12);
    }}
    [data-testid="stChatInput"] textarea {{
        background: #ffffff !important;
        border-radius: 11px !important;
        color: #16342A !important;
    }}
    [data-testid="stChatInput"]:focus-within > div {{
        border-color: {DEEP} !important;
        box-shadow: 0 0 0 3px rgba(46,158,99,0.22) !important;
    }}
    div[data-testid="stFileUploader"] section {{ border-radius: 14px; }}
    /* §4 — no fullscreen viewer on images (e.g. avatar/selfie previews) */
    button[title="View fullscreen"], button[aria-label="Fullscreen"],
    [data-testid="StyledFullScreenButton"],
    [data-testid="stElementToolbarButton"] button[aria-label="Fullscreen"] {{
        display: none !important;
    }}
    [data-testid="stImageContainer"] [data-testid="stElementToolbar"],
    [data-testid="stImage"] + [data-testid="stElementToolbar"] {{ display: none !important; }}
    .impact-kpi {{
        background: #ffffff; border: 1px solid #e6efe0; border-radius: 20px;
        padding: 1rem 1.2rem; box-shadow: 0 6px 20px rgba(27,94,59,0.07);
        height: 100%;
        transition: transform .18s ease, box-shadow .18s ease;
    }}
    .impact-kpi:hover {{
        box-shadow: 0 14px 30px rgba(27,94,59,0.16);
    }}
    .impact-kpi .t {{ font-size: .85rem; color: #5c7069; font-weight: 600;
                      letter-spacing: .02em; }}
    .impact-kpi .v {{ font-size: 1.9rem; font-weight: 800; color: {DEEP};
                      line-height: 1.15; }}
    .impact-kpi .u {{ font-size: .95rem; color: #5c7069; font-weight: 600; }}
    .impact-kpi .d-good {{ color: #1d8a4e; font-weight: 700; font-size: .9rem; }}
    .impact-kpi .d-bad {{ color: #c05621; font-weight: 700; font-size: .9rem; }}
    .impact-kpi .b {{ font-size: .85rem; color: #63756e; margin-top: .35rem; }}
    .stat-tile .b {{ font-size: .85rem; color: #63756e; margin-top: .3rem;
                     line-height: 1.4; }}
    /* confidence labels: calm and secondary — never alarming red (§9).
       Red is reserved for genuine errors via st.error. */
    /* §14 — raise the minimum readable size for small secondary text */
    [data-testid="stCaptionContainer"], [data-testid="stCaptionContainer"] p,
    [data-testid="stCaptionContainer"] * {{ font-size: .84rem !important; }}
    .conf-badge {{
        display: inline-block; padding: .1rem .6rem; border-radius: 999px;
        font-size: .8rem; font-weight: 700; letter-spacing: 0;
        cursor: default;
    }}
    .conf-HIGH {{ background: #e4f4ea; color: #2b7a4b; }}    /* calm green */
    .conf-MEDIUM {{ background: #fbf3e2; color: #9a7b3f; }}  /* soft amber */
    .conf-LOW, .conf-VERY.LOW, .conf-VERYLOW {{
        background: #eef1f0; color: #6b7d75;                 /* muted grey */
    }}
    .pill {{
        display:inline-block; padding:.25rem .8rem; border-radius:999px;
        background:{SOFT}; border:1px solid #e3edea; font-size:.88rem;
        margin: 0 .3rem .3rem 0; color:{DEEP}; font-weight:600;
        transition: box-shadow .15s ease;
    }}
    .pill:hover {{ box-shadow: 0 4px 10px rgba(27,94,59,.14); }}
    .story-card {{ border-left: 4px solid {GREEN}; padding-left: .9rem; }}
    .inline-label {{ padding-top: .45rem; font-weight: 600; color: #22423A; }}
    .wordmark {{ font-size: 1.5rem; font-weight: 800; color: {DEEP};
                 letter-spacing: -.02em; }}

    /* section bands: a readable translucent panel that groups a whole section,
       with margin so the scenery breaks through between sections (brief §1). */
    div[class*="st-key-band"] {{
        background: {surface};
        border: 1px solid {surface_border};
        border-radius: 24px;
        padding: 1.2rem 1.4rem .8rem 1.4rem;
        /* generous bottom margin so the illustrated world shows BETWEEN
           sections — the page reads as scenes in one landscape (brief §1) */
        margin: .5rem 0 2.2rem;
        box-shadow: 0 8px 26px rgba(20,60,42,0.10);
    }}
    div[class*="st-key-band"] div[data-testid="stVerticalBlockBorderWrapper"],
    div[class*="st-key-band"] div[data-testid="stLayoutWrapper"] {{
        background: {"rgba(255,255,255,0.55)" if not night else "rgba(255,255,255,0.05)"};
        box-shadow: none;
    }}
    /* §10 (UX pass) — consistent spacing rhythm inside section intros: a tidy
       gap between a heading and its description, and between grouped options,
       so the top box breathes without becoming oversized. */
    div[class*="st-key-band"] [data-testid="stHeading"] {{ margin-bottom: .15rem; }}
    div[class*="st-key-band"] [data-testid="stCaptionContainer"] {{
        margin-top: 0; margin-bottom: .5rem;
    }}

    /* top-right user chip: mascot → username → avatar */
    .impact-userchip {{
        position: fixed; top: 8px; right: 64px; z-index: 999990;
        display: flex; align-items: center; gap: .55rem;
        background: rgba(255,255,255,0.9); border: 1px solid #e3edea;
        border-radius: 999px; padding: .24rem .7rem .24rem .4rem;
        box-shadow: 0 4px 14px rgba(27,94,59,0.10);
        backdrop-filter: blur(6px);
        font-family: "Source Sans Pro", sans-serif; font-size: .88rem;
        font-weight: 700; color: {DEEP};
    }}
    .impact-userchip {{ cursor: pointer; transition: box-shadow .15s ease,
                        background .15s ease; }}
    .impact-userchip:hover {{
        box-shadow: 0 6px 20px rgba(27,94,59,0.22);
        background: rgba(255,255,255,0.98);
    }}
    .impact-userchip:focus-visible {{ outline: 2px solid {GREEN}; outline-offset: 2px; }}
    .impact-userchip .mascot {{ display: flex; align-items: center; }}
    .impact-userchip .mascot svg {{ display: block; }}
    .impact-userchip .name {{
        max-width: 150px; overflow: hidden; text-overflow: ellipsis;
        white-space: nowrap;
    }}
    .impact-userchip .avatar {{
        font-size: 1.05rem; line-height: 1;
        background: {SOFT}; border: 1px solid #e3edea; border-radius: 50%;
        width: 26px; height: 26px; display: flex; align-items: center;
        justify-content: center;
    }}
    @media (max-width: 760px) {{
        .impact-userchip .name {{ max-width: 84px; }}
    }}

    /* ---- shared design system: selects & dropdowns (one central rule) ----
       Clear interactive affordance: visible green border, hover/focus states
       and a pointer cursor on the trigger. Text inputs keep the text caret. */
    div[data-baseweb="select"] > div:first-child {{
        border: 2px solid {GREEN} !important;
        border-radius: 12px !important;
        background: #ffffff !important;
        cursor: pointer;
        transition: border-color .15s ease, box-shadow .15s ease;
    }}
    div[data-baseweb="select"] > div:first-child:hover {{
        border-color: {DEEP} !important;
        box-shadow: 0 1px 8px rgba(46,158,99,0.28) !important;
    }}
    div[data-baseweb="select"]:focus-within > div:first-child {{
        border-color: {GREEN} !important;
        box-shadow: 0 0 0 3px rgba(46,158,99,0.28) !important;
    }}
    div[data-baseweb="select"] input[readonly] {{ cursor: pointer; }}
    div[data-baseweb="select"] svg {{ color: {GREEN}; }}
    /* §3 — dependent fields (Province/Region, Municipality) must look
       obviously disabled while gated on a parent selection, not just be
       functionally unclickable. */
    div[data-baseweb="select"]:has(input:disabled) > div:first-child {{
        border: 2px dashed {"#3a4a44" if night else "#aab6ae"} !important;
        background: {"rgba(255,255,255,0.04)" if night else "rgba(120,132,124,0.08)"} !important;
        cursor: not-allowed !important;
    }}
    div[data-baseweb="select"]:has(input:disabled) > div:first-child:hover {{
        border-color: {"#3a4a44" if night else "#aab6ae"} !important;
        box-shadow: none !important;
    }}
    div[data-baseweb="select"] input:disabled {{
        cursor: not-allowed !important;
        color: var(--imp-muted) !important;
        opacity: 1 !important;
    }}
    div[data-baseweb="select"]:has(input:disabled) svg {{
        color: {"#3a4a44" if night else "#aab6ae"} !important; cursor: not-allowed !important;
    }}
    div[data-baseweb="select"]:has(input:disabled) label,
    label[disabled] {{ color: var(--imp-muted) !important; }}

    /* floating AI-assistant launcher (brief §7): a clearly AI/chat identity —
       a speech bubble with a spark — kept DISTINCT from the daisy mascot and
       the user avatar. Deliberately STATIC at rest (no idle animation) so it
       never reads as flicker/jitter; it only responds to hover. */
    .st-key-assistant_fab {{
        position: fixed; bottom: 26px; right: 26px; z-index: 999991;
        width: 64px; height: 64px;
    }}
    /* static affordance ring — never changes, so nothing moves on its own */
    .st-key-assistant_fab::before {{
        content: ""; position: absolute; left: -4px; top: -4px;
        width: 72px; height: 72px; border-radius: 50%;
        background: {GREEN}; opacity: .16; z-index: -1;
        pointer-events: none;
    }}
    .st-key-assistant_fab button {{
        width: 64px !important; height: 64px !important; border-radius: 50% !important;
        border: none !important; padding: 0 !important; min-height: 0 !important;
        background:
            url("data:image/svg+xml;utf8,<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 48 48'><path d='M10 9h28a4 4 0 0 1 4 4v16a4 4 0 0 1-4 4H22l-9 7v-7h-3a4 4 0 0 1-4-4V13a4 4 0 0 1 4-4z' fill='white'/><circle cx='19' cy='21' r='2.3' fill='%232E9E63'/><circle cx='27' cy='21' r='2.3' fill='%232E9E63'/><circle cx='35' cy='21' r='2.3' fill='%232E9E63'/><path d='M38 6l1.4 3.6L43 11l-3.6 1.4L38 16l-1.4-3.6L33 11l3.6-1.4z' fill='%23FFC94D'/></svg>")
            center / 34px 34px no-repeat,
            linear-gradient(135deg, {GREEN}, #46b87c) !important;
        box-shadow: 0 10px 26px rgba(27,94,59,0.35);
        /* STABILITY FIRST (brief §2): the launcher's layout box NEVER changes —
           no idle animation, and hover changes ONLY shadow + brightness, never
           transform / size / position. A cursor resting on it therefore cannot
           fall out of the hitbox, so there is no enter/leave flicker loop. The
           !important on transform defeats the global button-hover translateY. */
        transform: none !important;
        transition: box-shadow .18s ease, filter .18s ease;
    }}
    .st-key-assistant_fab button:hover {{
        transform: none !important;
        filter: brightness(1.06);
        box-shadow: 0 15px 34px rgba(27,94,59,0.5);
    }}
    .st-key-assistant_fab button:active {{
        transform: none !important; filter: brightness(0.98);
    }}
    .st-key-assistant_fab button p {{ display: none; }}

    /* floating assistant panel — a fully OPAQUE overlay (§4). The solid
       backing is set on the keyed container itself (reliable across Streamlit
       versions) so page content behind it never bleeds into the chat text. */
    .st-key-assistant_panel {{
        position: fixed; bottom: 102px; right: 26px; z-index: 999991;
        width: 400px; max-width: 92vw;
        background: #ffffff !important;
        border: 1px solid #cfe6d8 !important;
        border-radius: 18px !important;
        box-shadow: 0 18px 48px rgba(27,94,59,0.22) !important;
        padding: .35rem .7rem !important;
    }}
    /* §7 stability: the panel is a FIXED overlay — the read-only hover-lift
       (which moves containers up 2px) must never apply to it or its inner
       border wrappers, or hovering the close button shifts the whole panel and
       triggers an enter/leave flicker loop. Pin every transform to none. */
    .st-key-assistant_panel:hover,
    .st-key-assistant_panel [data-testid="stVerticalBlockBorderWrapper"]:hover,
    .st-key-assistant_panel [data-testid="stLayoutWrapper"]:hover {{
        transform: none !important;
    }}
    /* chat bubbles: assistant on very light green, user on light blue —
       both fully opaque and readable on the white panel. */
    .st-key-assistant_panel [data-testid="stChatMessage"] {{
        background: #f3faf5 !important; border-radius: 14px; margin-bottom: .3rem;
    }}
    .st-key-assistant_panel [data-testid="stChatMessage"]:has(
        [data-testid="stChatMessageAvatarUser"]) {{
        background: #eef6fb !important;
    }}
    /* input row stays opaque too */
    .st-key-assistant_panel [data-testid="stTextInputRootElement"],
    .st-key-assistant_panel [data-testid="stTextInput"] input {{
        background: #ffffff !important;
    }}
    {dark_overrides}
    </style>
    """, unsafe_allow_html=True)

    # --- redesign layers (order matters: v2 overrides base where needed) ---
    import avatar as _av
    st.markdown(_av.css(), unsafe_allow_html=True)
    st.markdown(_v2_css(p, night), unsafe_allow_html=True)
    st.markdown(ambient_layer(night), unsafe_allow_html=True)


# ===========================================================================
# REDESIGN — "Living Atlas" design-system layer
# ===========================================================================
# A single supplementary stylesheet layered on top of the base theme. It is
# mostly STRUCTURAL (radius / spacing / type scale / motion) so it adapts to
# both themes; colour-rich, daylight-only rules are gated to light mode.

def _v2_css(p, night):
    token_vars = (
        ":root{"
        f"--imp-sun:{SUN};--imp-river:{RIVER};--imp-teal:{TEAL};"
        f"--imp-coral:{CORAL};--imp-soil:{SOIL};--imp-sky:{SKY};"
        f"--imp-leaf:{LEAF};--imp-cream:{CREAM};--imp-mist:{MIST};"
        "--imp-r-lg:28px;--imp-r-xl:34px;--imp-spring:cubic-bezier(.34,1.56,.64,1);"
        "}")

    # -- structural + type + motion (both themes) --------------------------
    structural = """
    /* breathe: a wider, calmer reading column with real vertical rhythm */
    .stApp .block-container { max-width: 1140px; padding-top: 3.2rem;
        padding-bottom: 5rem; }
    .stApp [data-testid="stVerticalBlock"] { gap: 1.15rem; }

    /* --- oversized, friendly display type (Duolingo weight, humanist warmth) */
    .stApp h1 { font-size: clamp(2.4rem, 5.2vw, 3.9rem) !important;
        line-height: 1.02 !important; font-weight: 800 !important;
        letter-spacing: -.015em; margin-bottom: .3rem; }
    .stApp h2 { font-size: clamp(1.7rem, 3vw, 2.4rem) !important;
        font-weight: 800 !important; letter-spacing: -.01em; }
    .stApp h3 { font-weight: 700 !important; }

    .eyebrow { display:inline-flex; align-items:center; gap:.4rem;
        font-family:'Nunito',sans-serif; font-weight:800; font-size:.74rem;
        letter-spacing:.14em; text-transform:uppercase;
        color: var(--imp-green); background: rgba(51,176,106,.12);
        padding:.28rem .7rem; border-radius:999px; margin-bottom:.7rem; }
    .hero-sub { font-size: clamp(1.02rem,1.5vw,1.22rem); line-height:1.5;
        color: var(--imp-muted); max-width: 40ch; }
    .hero-note { font-size:.98rem; font-weight:700; color: var(--imp-green);
        margin:.5rem 0 0; max-width: 42ch; }

    /* landing brand lockup (brief §2) — crisp vector mark + wordmark */
    .brand-lockup { display:flex; align-items:center; gap:.7rem;
        margin-bottom:.6rem; }
    .brand-lockup .brand-icon { flex:0 0 auto;
        filter: drop-shadow(0 6px 14px rgba(27,94,59,.18)); }
    .brand-text { display:flex; flex-direction:column; line-height:1; }
    .brand-name { font-family:'Baloo 2',sans-serif; font-weight:800;
        font-size:2.15rem; letter-spacing:-.01em; color: var(--imp-deep); }
    .brand-name .brand-slash { color: var(--imp-green); margin:0 .02em; }
    .brand-tag { font-family:'Nunito',sans-serif; font-weight:800;
        font-size:.66rem; letter-spacing:.16em; text-transform:uppercase;
        color: var(--imp-green); margin-top:.28rem; }

    /* logged-in hero identity group — avatar with the name directly beneath
       it, so the identity reads as ONE unit (brief §9/§12) */
    .hero-identity { display:flex; flex-direction:column; align-items:center;
        text-align:center; gap:.15rem; padding-top:.2rem; }
    .hero-name { font-family:'Baloo 2',sans-serif; font-weight:800;
        font-size:1.28rem; line-height:1.15; color: var(--imp-deep);
        margin-top:.35rem; overflow-wrap:anywhere; }
    .hero-mood { font-family:'Baloo 2',sans-serif; font-weight:800;
        font-size:.98rem; color: var(--imp-green); }
    /* dashboard hero row: snapshot card anchors the centre; avatar + score ring
       align to the same top edge, so the row reads as one composed unit. */
    .st-key-hero_row .st-key-band_snapshot { margin: 0 !important; }
    .st-key-hero_row [data-testid="stColumn"] { align-self: flex-start; }

    /* --- cards: soft, organic, NOT a uniform SaaS grid -------------------
       near-invisible borders + layered green-tinted shadow + big radius, so
       blocks feel like paper resting on the world rather than boxed tiles. */
    .stApp div[data-testid="stVerticalBlockBorderWrapper"],
    .stApp div[data-testid="stLayoutWrapper"]:has(> [data-testid="stVerticalBlock"]) {
        border-radius: var(--imp-r-lg) !important;
        border: 1px solid rgba(27,94,59,.06) !important;
        box-shadow: 0 10px 30px rgba(27,94,59,.09),
                    0 2px 6px rgba(27,94,59,.05) !important;
    }
    /* CTAs: bigger, bolder, with a Duolingo-style raised base + spring press */
    .stApp .stButton > button, .stApp .stFormSubmitButton > button {
        padding: .62rem 1.15rem !important; font-size: 1rem !important;
        font-weight: 800 !important;
    }
    .stApp .stButton > button[kind="primary"],
    .stApp .stFormSubmitButton > button[kind="primary"] {
        box-shadow: 0 5px 0 0 #1f8b52, 0 12px 22px rgba(31,139,82,.28) !important;
    }
    /* hover never moves the button (see HOVER STABILITY RULE) — the raised
       base "presses" via shadow depth alone */
    .stApp .stButton > button[kind="primary"]:hover,
    .stApp .stFormSubmitButton > button[kind="primary"]:hover {
        transform: none !important;
        filter: brightness(1.05);
        box-shadow: 0 5px 0 0 #1f8b52, 0 16px 28px rgba(31,139,82,.40) !important;
    }
    .stApp .stButton > button[kind="primary"]:active,
    .stApp .stFormSubmitButton > button[kind="primary"]:active {
        transform: none !important;
        filter: brightness(0.96);
        box-shadow: 0 2px 0 0 #1f8b52, 0 6px 12px rgba(31,139,82,.24) !important;
    }

    /* --- reusable world building blocks (used by the redesigned views) --- */
    .hero-wrap { position: relative; }
    .chip-row { display:flex; flex-wrap:wrap; gap:.5rem; margin:.2rem 0 .1rem; }
    .soft-chip { display:inline-flex; align-items:center; gap:.4rem;
        background:#fff; border:1px solid rgba(27,94,59,.1); border-radius:999px;
        padding:.34rem .8rem; font-weight:700; font-size:.92rem;
        color: var(--imp-deep); box-shadow:0 3px 10px rgba(27,94,59,.07); }
    .soft-chip.blue  { background:#eef7fd; border-color:#cfe8f8; color:#1f6f9e; }
    .soft-chip.sun   { background:#fff7e3; border-color:#f6e3b0; color:#8a6a1e; }
    .soft-chip.coral { background:#fdeeec; border-color:#f6cfc8; color:#b0432f; }

    /* the user chip now carries the Sprout character, not an emoji circle */
    .impact-userchip .avatar { width:32px !important; height:32px !important;
        background:transparent !important; border:none !important;
        overflow:visible !important; }
    .impact-userchip .avatar .avatar-shell svg { width:32px; height:32px; }

    /* the "journey" path — a friendly stepped trail, not a bullet list */
    .journey { display:flex; flex-direction:column; gap:.2rem; margin-top:.4rem;}
    .journey-step { display:flex; align-items:center; gap:.85rem;
        padding:.55rem .8rem; border-radius:16px; transition:background .2s; }
    .journey-step:hover { background: rgba(51,176,106,.08); }
    .journey-num { flex:0 0 auto; width:30px; height:30px; border-radius:50%;
        display:flex; align-items:center; justify-content:center;
        font-weight:800; color:#fff;
        background: linear-gradient(135deg,#35b26f,#59cd8c);
        box-shadow:0 4px 10px rgba(46,158,99,.35); }
    .journey-step .jt { font-weight:600; }

    /* playful stat tiles (ecological alternative to dashboard number tiles) */
    .stat-tile { position:relative; overflow:hidden; border-radius:24px;
        padding:1.1rem 1.2rem 1.15rem; background:#fff;
        border:1px solid rgba(27,94,59,.07);
        box-shadow:0 10px 28px rgba(27,94,59,.10); height:100%;
        transition: transform .18s ease, box-shadow .18s ease; }
    /* §10 read-only tier: a quiet glow, information emphasis only (no
       movement — see HOVER STABILITY RULE) */
    .stat-tile:hover { box-shadow: 0 16px 34px rgba(27,94,59,.18); }
    @media (prefers-reduced-motion: reduce) {
      .stat-tile, .stat-tile:hover, .pill, .pill:hover {
        transition: none !important; }
    }
    .stat-tile .st-ico { position:absolute; right:.7rem; top:.6rem; opacity:.9; }
    .stat-tile .st-lab { font-weight:800; font-size:.82rem; letter-spacing:.02em;
        color: var(--imp-muted); }
    .stat-tile .st-val { font-family:'Baloo 2',sans-serif; font-weight:800;
        font-size:2.1rem; line-height:1.05; color: var(--imp-deep);
        overflow-wrap:anywhere; }
    .stat-tile .st-un  { font-size:.95rem; font-weight:700; color:var(--imp-muted);}
    .stat-tile .st-viz { margin-top:.5rem; }
    /* the text column must be free to shrink so a large business-scale value
       (e.g. 1,268,400) never pushes the illustration out of the card (§13) */
    .stat-tile .st-text { min-width:0; flex:1 1 auto; }
    /* Paired KPI tiles read as one row of equal cards (brief §13/§20).
       Streamlit sizes columns to content, so a shared min-height is the robust
       way to keep side-by-side cards level rather than one ending early. */
    .stat-tile { min-height: 190px; }

    /* clean, aligned score ring (brief §5/§14) — number centred in the ring,
       caption + high-contrast status chip stacked beneath, nothing overlaps */
    .score-ring { display:flex; flex-direction:column; align-items:center;
        gap:.15rem; text-align:center; cursor:default; }
    .score-ring svg { transition: transform .18s ease; }
    .score-ring:hover svg { transform: scale(1.04); }
    .score-ring-cap { font-family:'Nunito',sans-serif; font-size:.9rem;
        font-weight:700; color:var(--imp-muted); letter-spacing:.01em; }
    .score-ring-status { display:inline-flex; align-items:center; gap:.4rem;
        font-family:'Baloo 2',sans-serif; font-weight:800; font-size:1rem;
        line-height:1.2; }
    .score-ring-status .dot { width:9px; height:9px; border-radius:50%;
        flex:0 0 auto; box-shadow:0 0 0 3px rgba(0,0,0,.04); }
    .score-ring-dir { font-family:'Nunito',sans-serif; font-size:.8rem;
        font-weight:600; color:var(--imp-muted); margin-top:.1rem; }
    @media (prefers-reduced-motion: reduce) {
      .score-ring:hover svg { transform:none !important; }
    }

    /* bloom-open reveal for progress/data as it enters */
    @keyframes imp-bloom { from{transform:scale(.86);opacity:0}
        to{transform:scale(1);opacity:1} }
    .imp-bloom { animation: imp-bloom .5s var(--imp-spring) both; }
    .water-wave { animation: imp-wave 3.4s ease-in-out infinite; }
    @keyframes imp-wave { 0%,100%{transform:translateX(0)}
        50%{transform:translateX(-12px)} }
    .smoke-puff { animation: imp-rise 5s ease-in-out infinite; }
    @keyframes imp-rise { 0%{transform:translateY(0);opacity:.85}
        100%{transform:translateY(-14px);opacity:0} }

    @media (prefers-reduced-motion: reduce) {
      .imp-bloom,.water-wave,.smoke-puff { animation: none !important; }
    }
    @media (max-width: 640px) {
      .stApp .block-container { padding-top: 2rem; }
      .hero-sub { max-width: none; }
    }
    """

    # -- daylight-only atmosphere (light theme) ----------------------------
    light_only = """
    /* full-bleed "world bands": each major section reads as a small
       illustrated ecosystem, not a boxed card grid */
    .stApp div[class*="st-key-band"] {
        border-radius: var(--imp-r-xl) !important;
        border: 1px solid rgba(51,176,106,.14) !important;
        background:
            radial-gradient(120% 90% at 12% -10%,
                            rgba(143,211,244,.28), transparent 60%),
            radial-gradient(120% 90% at 105% 120%,
                            rgba(51,176,106,.18), transparent 55%),
            linear-gradient(180deg,#ffffff 0%, #f2fbf5 100%) !important;
        box-shadow: 0 16px 40px rgba(27,94,59,.10) !important;
        padding: 1.5rem 1.6rem 1.1rem !important;
    }
    /* headline glow on hero titles */
    .stApp h1 { text-shadow: 0 2px 22px rgba(255,255,255,.6); }
    """

    return ("<style>" + token_vars + structural
            + (light_only if not night else "") + "</style>")


def ambient_layer(night=False):
    """A global, behind-content atmosphere of gently drifting leaves + pollen
    (fireflies at night). Kurzgesagt-style ambient depth that keeps the app
    feeling alive at rest. Fixed, non-interactive, reduced-motion safe."""
    leaf = ("<svg viewBox='0 0 24 24' width='100%' height='100%'>"
            "<path d='M20 4C11 4 5.5 9.5 5.5 19c9.5 0 15-5.5 14.5-15z' "
            "fill='%COL%'/></svg>")
    dot = "<span style='display:block;width:100%;height:100%;border-radius:50%;background:%COL%'></span>"

    specs = [  # left%, top%, size, dur, delay, kind, colour, opacity
        (6, 12, 26, 26, 0, "leaf", "#7fce9a", .5),
        (18, 70, 16, 32, -6, "leaf", "#a9e0bd", .45),
        (34, 24, 10, 20, -3, "dot", "#ffd873", .6),
        (52, 60, 22, 30, -12, "leaf", "#8fd3a6", .4),
        (70, 16, 12, 24, -8, "dot", "#bfe9cf", .6),
        (83, 54, 20, 34, -2, "leaf", "#7fce9a", .42),
        (91, 28, 9, 18, -10, "dot", "#ffe08a", .55),
        (44, 84, 14, 28, -5, "leaf", "#a9e0bd", .4),
        (26, 44, 8, 22, -14, "dot", "#cdeecf", .5),
    ]
    if night:
        specs = [(x, y, max(6, s * .5), d, dl, "dot",
                  "#bfe9ff", .8) for x, y, s, d, dl, *_ in specs]

    sprites = []
    for i, (x, y, s, dur, dly, kind, col, op) in enumerate(specs):
        inner = (leaf if kind == "leaf" else dot).replace("%COL%", col)
        glow = ("box-shadow:0 0 8px 2px #bfe9ff;" if night else "")
        sprites.append(
            f"<div class='imp-flo imp-flo{i % 3}' style='left:{x}%;top:{y}%;"
            f"width:{s}px;height:{s}px;opacity:{op};{glow}'>{inner}</div>")

    return f"""
<div class="imp-ambient" aria-hidden="true">{''.join(sprites)}</div>
<style>
.imp-ambient {{ position:fixed; inset:0; pointer-events:none; z-index:0;
    overflow:hidden; }}
.imp-flo {{ position:absolute; }}
.imp-flo0 {{ animation: imp-drift0 var(--d,28s) ease-in-out infinite; }}
.imp-flo1 {{ animation: imp-drift1 var(--d,32s) ease-in-out infinite; }}
.imp-flo2 {{ animation: imp-float2 var(--d,22s) ease-in-out infinite; }}
@keyframes imp-drift0 {{ 0%{{transform:translate(0,0) rotate(0)}}
   50%{{transform:translate(26px,18px) rotate(120deg)}}
   100%{{transform:translate(0,0) rotate(360deg)}} }}
@keyframes imp-drift1 {{ 0%{{transform:translate(0,0) rotate(0)}}
   50%{{transform:translate(-22px,24px) rotate(-140deg)}}
   100%{{transform:translate(0,0) rotate(-360deg)}} }}
@keyframes imp-float2 {{ 0%,100%{{transform:translate(0,0)}}
   50%{{transform:translate(0,-16px)}} }}
@media (prefers-reduced-motion: reduce) {{ .imp-flo {{ animation:none!important; }} }}
</style>"""


# ---------------------------------------------------------------------------
# Ecological data visualisations (spec §8) — data told as living scenes.
# Each returns HTML for st.markdown so the CSS animations run in the page.
# ---------------------------------------------------------------------------

def _val_fs(value):
    """Responsive number size so large business-scale values (e.g. 1,268,400)
    still fit a KPI tile cleanly (brief §13/§16)."""
    n = len(str(value))
    if n <= 6:   return "2.1rem"
    if n <= 8:   return "1.7rem"
    if n <= 10:  return "1.4rem"
    return "1.2rem"


def reservoir(pct, value, unit, label, sublabel=None):
    """Water as a filling clear reservoir jar — fuller & clearer = better.
    `pct` 0..1 fills the jar; `value`/`unit`/`label` label it."""
    pct = max(0.0, min(1.0, pct))
    top_y = 132 - pct * 104          # water surface
    sub = f"<div class='b'>{sublabel}</div>" if sublabel else ""
    return _flat(f"""
<div class="stat-tile imp-bloom">
  <div class="st-lab">{icon('water', 15, RIVER)} {label}</div>
  <div style="display:flex;align-items:center;gap:1rem">
    <div class="st-text"><div class="st-val" style="font-size:{_val_fs(value)}">{value}</div><div class="st-un">{unit}</div>{sub}</div>
    <svg width="76" height="96" viewBox="0 0 120 150" style="flex:0 0 auto">
      <defs><clipPath id="jar{int(pct*1000)}">
        <path d="M28 20 h64 v96 a26 26 0 0 1 -26 26 h-12 a26 26 0 0 1 -26 -26 z"/>
      </clipPath></defs>
      <g clip-path="url(#jar{int(pct*1000)})">
        <rect x="20" y="{top_y:.0f}" width="100" height="150" fill="#8fd3f4"/>
        <g class="water-wave" fill="#a9e2f8">
          <path d="M0 {top_y:.0f} q15 -8 30 0 t30 0 t30 0 t30 0 t30 0 v20 h-180 z"/>
        </g>
        <circle cx="52" cy="{top_y+30:.0f}" r="3" fill="#cfeefc" opacity=".8"/>
        <circle cx="74" cy="{top_y+52:.0f}" r="2.2" fill="#cfeefc" opacity=".7"/>
      </g>
      <path d="M28 20 h64 v96 a26 26 0 0 1 -26 26 h-12 a26 26 0 0 1 -26 -26 z"
            fill="none" stroke="#bcdff0" stroke-width="3"/>
      <rect x="24" y="14" width="72" height="9" rx="4.5" fill="#d6eef8"/>
    </svg>
  </div>
</div>""")


def sky_clearing(value, unit, label, cleanliness, sublabel=None):
    """Carbon as a clearing sky: a bright sun, and a smoke puff that shrinks /
    fades as `cleanliness` (0..1) rises. Lower emissions = cleaner sky."""
    c = max(0.0, min(1.0, cleanliness))
    smoke_op = round((1 - c) * 0.8, 2)
    smoke_scale = 0.5 + (1 - c) * 0.9
    sun_op = round(0.35 + 0.6 * c, 2)
    sub = f"<div class='b'>{sublabel}</div>" if sublabel else ""
    return _flat(f"""
<div class="stat-tile imp-bloom">
  <div class="st-lab">{icon('cloud', 15, RIVER)} {label}</div>
  <div style="display:flex;align-items:center;gap:1rem">
    <div class="st-text"><div class="st-val" style="font-size:{_val_fs(value)}">{value}</div><div class="st-un">{unit}</div>{sub}</div>
    <svg width="96" height="76" viewBox="0 0 130 100" style="flex:0 0 auto">
      <defs><linearGradient id="skg" x1="0" y1="0" x2="0" y2="1">
        <stop offset="0" stop-color="#cdeafb"/><stop offset="1" stop-color="#eafbf1"/>
      </linearGradient></defs>
      <rect x="0" y="0" width="130" height="100" rx="16" fill="url(#skg)"/>
      <circle cx="98" cy="30" r="16" fill="#FFD86B" opacity="{sun_op}"/>
      <g stroke="#FFD86B" stroke-width="3" stroke-linecap="round" opacity="{sun_op}">
        <line x1="98" y1="6" x2="98" y2="0"/><line x1="120" y1="30" x2="128" y2="30"/>
        <line x1="83" y1="15" x2="78" y2="10"/><line x1="113" y1="15" x2="118" y2="10"/>
      </g>
      <g class="smoke-puff" transform="translate(34 60) scale({smoke_scale:.2f})"
         opacity="{smoke_op}" fill="#9aa0aa">
        <circle cx="0" cy="0" r="11"/><circle cx="14" cy="-8" r="9"/>
        <circle cx="-12" cy="-6" r="8"/><circle cx="4" cy="-14" r="7"/>
      </g>
      <path d="M6 84 q18 -10 34 0 t34 0 t40 0" fill="none"
            stroke="#8fd3a6" stroke-width="4" stroke-linecap="round"/>
    </svg>
  </div>
</div>""")


def meadow(pct, label, caption=None):
    """Progress as a blooming meadow: more flowers + returning pollinators as
    `pct` (0..1) rises. A warm way to show a goal / improvement rate (§8)."""
    pct = max(0.0, min(1.0, pct))
    n = round(2 + 8 * pct)
    flowers = []
    cols = ["#ffd45e", "#ff9db0", "#8ad0ff", "#c9a2ff", "#ff8f5e"]
    for i in range(n):
        x = 16 + i * (288 / max(1, n))
        h = 20 + (i % 3) * 6
        col = cols[i % len(cols)]
        flowers.append(
            f"<g transform='translate({x:.0f} 70)'>"
            f"<path d='M0 0 V-{h}' stroke='#5fae5a' stroke-width='2.4'/>"
            + "".join(f"<ellipse cx='0' cy='-{h+4}' rx='2.8' ry='5' fill='{col}' "
                      f"transform='rotate({a} 0 -{h})'/>" for a in range(0, 360, 72))
            + f"<circle cx='0' cy='-{h}' r='2.6' fill='#fff0b0'/></g>")
    bee = ("<g class='av-flit' transform='translate(250 26)'>"
           "<ellipse rx='5' ry='3.4' fill='#ffcf4d'/>"
           "<rect x='-3' y='-3.4' width='2' height='6.8' fill='#3a3128'/>"
           "<rect x='1' y='-3.4' width='2' height='6.8' fill='#3a3128'/>"
           "<ellipse cx='0' cy='-3' rx='5' ry='3' fill='#ffffff' opacity='.6'/>"
           "</g>") if pct > 0.5 else ""
    cap = f"<div class='b' style='margin-top:.3rem'>{caption}</div>" if caption else ""
    return _flat(f"""
<div class="imp-bloom">
  <div class="st-lab" style="margin-bottom:.3rem">{icon('leaf',15,GREEN)} {label}</div>
  <svg width="100%" viewBox="0 0 320 84" preserveAspectRatio="xMidYMax meet">
    <rect x="0" y="66" width="320" height="18" rx="9" fill="#bfe3a8"/>
    <rect x="0" y="70" width="320" height="14" fill="#a9d98f"/>
    {''.join(flowers)}{bee}
  </svg>{cap}
</div>""")


def energy_tile(value, unit, label, sublabel=None):
    """Electricity as a small sunlit rooftop-solar scene — structurally matched
    to reservoir() and sky_clearing() so the three KPI cards read as one aligned
    set (brief §13). Value/unit/sublabel keep every bit of the old tile."""
    sub = f"<div class='b'>{sublabel}</div>" if sublabel else ""
    return _flat(f"""
<div class="stat-tile imp-bloom">
  <div class="st-lab">{icon('bolt', 15, '#c8961e')} {label}</div>
  <div style="display:flex;align-items:center;gap:1rem">
    <div class="st-text"><div class="st-val" style="font-size:{_val_fs(value)}">{value}</div><div class="st-un">{unit}</div>{sub}</div>
    <svg width="96" height="76" viewBox="0 0 130 100" style="flex:0 0 auto">
      <defs><linearGradient id="eskg" x1="0" y1="0" x2="0" y2="1">
        <stop offset="0" stop-color="#e9f6ff"/><stop offset="1" stop-color="#fff6df"/>
      </linearGradient></defs>
      <rect x="0" y="0" width="130" height="100" rx="16" fill="url(#eskg)"/>
      <circle cx="98" cy="30" r="15" fill="#FFD23F"/>
      <g stroke="#FFC94D" stroke-width="3" stroke-linecap="round">
        <line x1="98" y1="7" x2="98" y2="1"/><line x1="121" y1="30" x2="128" y2="30"/>
        <line x1="82" y1="14" x2="77" y2="9"/><line x1="114" y1="14" x2="119" y2="9"/>
      </g>
      <g transform="translate(20 52)">
        <rect x="0" y="0" width="60" height="30" rx="3" fill="#2f7fb8"
              transform="skewX(-12)"/>
        <g stroke="#bfe0f4" stroke-width="1.4">
          <line x1="20" y1="0" x2="20" y2="30" transform="skewX(-12)"/>
          <line x1="40" y1="0" x2="40" y2="30" transform="skewX(-12)"/>
          <line x1="-3" y1="10" x2="55" y2="10" transform="skewX(-12)"/>
          <line x1="-6" y1="20" x2="52" y2="20" transform="skewX(-12)"/>
        </g>
      </g>
      <path d="M6 90 q18 -9 34 0 t34 0 t40 0" fill="none"
            stroke="#8fd3a6" stroke-width="4" stroke-linecap="round"/>
    </svg>
  </div>
</div>""")


def stat_tile(icon_name, value, unit, label, tone="green", sublabel=None):
    """A playful, breathable stat tile — the friendly counterpart to kpi_card
    for hero/summary rows. `tone`: green|blue|sun|teal|coral."""
    tone_col = {"green": GREEN, "blue": RIVER, "sun": "#c8961e",
                "teal": TEAL, "coral": CORAL}.get(tone, GREEN)
    sub = f"<div class='b'>{sublabel}</div>" if sublabel else ""
    return _flat(f"""
<div class="stat-tile imp-bloom">
  <span class="st-ico">{icon(icon_name, 22, tone_col)}</span>
  <div class="st-lab">{label}</div>
  <div class="st-val" style="color:{tone_col};font-size:{_val_fs(value)}">{value}
    <span class="st-un">{unit}</span></div>
  {sub}
</div>""")


# Calm, user-friendly confidence wording (§9) with a short hover explanation.
# The internal confidence grade still reflects real data-source quality
# (bill/meter → HIGH, spend-converted → MEDIUM, typical-usage estimate → LOW);
# only the presentation is softened.
_CONF_LABEL = {
    "HIGH": ("Measured",
             "Based on a bill or meter reading you gave us."),
    "MEDIUM": ("Estimated",
               "Worked out from an amount you spent — a close estimate."),
    "LOW": ("Approximate estimate",
            "Estimated from typical usage. Enter a recent bill to make it "
            "more precise."),
    "VERYLOW": ("Rough estimate",
                "A broad estimate with limited detail — more information "
                "will sharpen it."),
}


def confidence_badge(conf):
    if not conf:
        return ""
    cls = str(conf).replace(" ", "")
    label, tip = _CONF_LABEL.get(
        cls, ("Estimate", "An estimate based on the information you provided."))
    return f"<span class='conf-badge conf-{cls}' title=\"{tip}\">{label}</span>"


def kpi_card(icon_name, title, value, unit, delta_text=None, delta_good=True,
             benchmark_text=None, conf=None):
    delta_html = ""
    if delta_text:
        cls = "d-good" if delta_good else "d-bad"
        delta_html = f"<div class='{cls}'>{delta_text}</div>"
    bench_html = f"<div class='b'>{benchmark_text}</div>" if benchmark_text else ""
    return _flat(f"""
    <div class="impact-kpi">
      <div class="t">{icon(icon_name, 15, GREEN)} {title} {confidence_badge(conf)}</div>
      <div class="v" style="font-size:{_val_fs(value)}">{value} <span class="u">{unit}</span></div>
      {delta_html}{bench_html}
    </div>""")


# ---------------------------------------------------------------------------
# Browser enhancements (embedded web component, runs once per page load)
# ---------------------------------------------------------------------------

def enhance_ui():
    # The component's iframe can be re-created whenever the sidebar re-renders,
    # which destroys listeners registered by the previous copy. So instead of
    # a run-once flag, every render tears down the prior installation and
    # re-installs from the live iframe realm.
    st.html("""<script>
(function () {
  const P = window;
  const doc = P.document;
  if (P.__impactCleanup) { try { P.__impactCleanup(); } catch (err) {} }

  const handlers = [];
  const on = (target, ev, fn, opts) => {
    target.addEventListener(ev, fn, opts);
    handlers.push([target, ev, fn, opts]);
  };

  /* 1. Select-all on focus: numbers and text highlight for instant overtype */
  on(doc, 'focusin', (e) => {
    const t = e.target;
    if (t.tagName === 'INPUT' && !t.readOnly &&
        (t.type === 'text' || t.type === 'number')) {
      setTimeout(() => { try { t.select(); } catch (err) {} }, 0);
    }
  });

  /* 2. Press-and-hold auto-repeat on number steppers */
  let holdDelay = null, holdTimer = null;
  const stepSel = 'button[data-testid="stNumberInputStepUp"],' +
                  'button[data-testid="stNumberInputStepDown"]';
  function refindStepper(dir, label) {
    return [...doc.querySelectorAll('button[data-testid="' + dir + '"]')]
      .find(b => {
        const input = b.closest('div[data-testid="stNumberInput"]')
          ?.querySelector('input');
        return input && input.getAttribute('aria-label') === label;
      });
  }
  on(doc, 'pointerdown', (e) => {
    const btn = e.target.closest ? e.target.closest(stepSel) : null;
    if (!btn) return;
    const dir = btn.getAttribute('data-testid');
    const input = btn.closest('div[data-testid="stNumberInput"]')
      ?.querySelector('input');
    const label = input ? input.getAttribute('aria-label') : null;
    holdDelay = setTimeout(() => {
      holdTimer = setInterval(() => {
        const live = refindStepper(dir, label);
        if (live) live.click();
      }, 140);
    }, 420);
  }, true);
  const stopHold = () => {
    clearTimeout(holdDelay); clearInterval(holdTimer);
    holdDelay = holdTimer = null;
  };
  ['pointerup', 'pointercancel', 'dragstart'].forEach(ev =>
    on(doc, ev, stopHold, true));
  on(P, 'blur', stopHold);

  /* 3. Short dropdowns are select-only (no confusing free-text editing);
        LONG lists keep type-to-search so nobody scrolls hundreds of rows. */
  const SEARCHABLE = new Set(['From', 'To', 'Manufacturer']);
  function lockSelects() {
    doc.querySelectorAll('div[data-baseweb="select"] input').forEach(inp => {
      const label = inp.getAttribute('aria-label') || '';
      if (SEARCHABLE.has(label)) return;
      if (!inp.readOnly) {
        inp.readOnly = true;
        inp.setAttribute('inputmode', 'none');
        inp.style.caretColor = 'transparent';
        inp.style.cursor = 'pointer';   /* select-only: act like a button */
      }
    });
  }
  lockSelects();
  const mo = new MutationObserver(lockSelects);
  mo.observe(doc.body, { subtree: true, childList: true });

  P.__impactCleanup = () => {
    handlers.forEach(([t, ev, fn, opts]) => t.removeEventListener(ev, fn, opts));
    mo.disconnect();
    stopHold();
  };
})();
</script>""")


def scroll_to_anchor(anchor):
    """Scroll the app to a heading anchor (e.g. the Goals section) and keep
    re-asserting it briefly, because charts that finish laying out after the
    first scroll push the target back down."""
    st.html(f"""<script>
(function () {{
  const doc = document;
  let tries = 0;
  const timer = setInterval(() => {{
    tries += 1;
    const el = doc.getElementById('{anchor}');
    if (el) {{
      el.scrollIntoView({{behavior: tries < 3 ? 'smooth' : 'instant',
                          block: 'start'}});
      const r = el.getBoundingClientRect();
      if (tries > 3 && r.top > -40 && r.top < 200) {{
        clearInterval(timer);   // settled in view
      }}
    }}
    if (tries > 12) clearInterval(timer);
  }}, 450);
}})();
</script>""")


def scroll_chat_to_prompt():
    """After a new Sprout answer, bring the user's latest prompt to the TOP of
    the chat's own scroll box (§5), so the reader starts at the question and
    the beginning of the reply — not dumped at the end of a long answer.

    Scoped to the assistant panel's scroll container only; it does NOT move
    the whole page, and it self-terminates so it never fights manual scrolling
    on later rerenders (the caller sets the trigger flag exactly once)."""
    st.html("""<script>
(function () {
  const doc = document;
  let box = null, lastUser = null, finds = 0;

  function locate() {
    const panel = doc.querySelector('.st-key-assistant_panel');
    if (!panel) return false;
    const users = [...panel.querySelectorAll('[data-testid="stChatMessage"]')]
      .filter(m => m.querySelector('[data-testid="stChatMessageAvatarUser"]'));
    lastUser = users[users.length - 1];
    if (!lastUser) return false;
    let b = lastUser.parentElement;
    while (b && b !== panel) {
      const oy = getComputedStyle(b).overflowY;
      if ((oy === 'auto' || oy === 'scroll') && b.scrollHeight > b.clientHeight + 4)
        break;
      b = b.parentElement;
    }
    if (!b || b === panel) return false;
    box = b; return true;
  }

  // Park the user's prompt at the top of the scroll box and hold it there
  // against Streamlit's one-time auto-scroll-to-bottom — but ABORT the moment
  // the user scrolls, so we never fight someone reading the answer (§5).
  function start() {
    let aborted = false, tries = 0;
    const abort = () => { aborted = true; };
    box.addEventListener('wheel', abort, {passive: true});
    box.addEventListener('touchmove', abort, {passive: true});
    box.addEventListener('keydown', abort);
    const timer = setInterval(() => {
      tries += 1;
      if (aborted || tries > 22) {   // ~3.3s ceiling, then release fully
        clearInterval(timer);
        box.removeEventListener('wheel', abort);
        box.removeEventListener('touchmove', abort);
        box.removeEventListener('keydown', abort);
        return;
      }
      const delta = lastUser.getBoundingClientRect().top
                    - box.getBoundingClientRect().top;
      if (Math.abs(delta - 8) > 10) box.scrollTop += delta - 8;
    }, 150);
  }

  const boot = setInterval(() => {
    finds += 1;
    if (locate()) { clearInterval(boot); start(); }
    else if (finds > 15) clearInterval(boot);
  }, 100);
})();
</script>""")


def active_theme():
    """Current UI theme from session ('light'|'dark'), safe outside a run."""
    try:
        return st.session_state.get("theme", "light")
    except Exception:  # noqa: BLE001
        return "light"


def mini_mascot_svg(score, size=26, theme="light"):
    """Tiny half-Earth-and-daisy status indicator for the top-right chip —
    the SAME scene parameters as the full mascot so surfaces tell one story.
    Only the curved top of the globe shows; the daisy grows from it (§19)."""
    p = scene_params(score, theme)
    orb = "#eef3ff" if p["night"] else "#FFD966"
    return _flat(f"""
<svg width="{size}" height="{size}" viewBox="0 0 32 32" xmlns="http://www.w3.org/2000/svg">
  <defs><clipPath id="mc"><circle cx="16" cy="44" r="22"/></clipPath></defs>
  <circle cx="25" cy="7" r="3" fill="{orb}" opacity="{p['sun_opacity']}"/>
  <circle cx="16" cy="44" r="22" fill="{'#1f4468' if p['night'] else '#4bb4e8'}" style="filter:brightness({p['earth_bright']})"/>
  <g clip-path="url(#mc)" style="filter:brightness({p['earth_bright']})">
    <path d="M2 26 q8 -5 15 -1 q7 3 15 0 l0 8 l-30 0z" fill="{p['leaf']}"/>
  </g>
  <g transform="rotate({-p['droop'] * 0.6} 16 24)">
    <line x1="16" y1="24" x2="16" y2="11" stroke="{p['leaf']}" stroke-width="1.6"/>
    {"".join(f'<ellipse cx="16" cy="8" rx="1.5" ry="3" fill="{p["petal"]}" transform="rotate({a} 16 11)"/>' for a in range(0, 360, 45))}
    <circle cx="16" cy="11" r="2" fill="#FFD966"/>
  </g>
</svg>""")


def user_chip(user, score, theme="light"):
    """Compact fixed user-info control in the top-right corner (§32).
    Order: mascot (environmental state) → username → avatar. The whole chip is
    clickable and navigates to Profile via the sidebar link (in-app, so no
    full reload wipes the session). Mascot is larger than the avatar so state
    stays readable, and the two never swap roles."""
    import html as _html
    import avatar as _av
    name = _html.escape(user["display_name"])
    if _av.has_photo(user):
        sprout = _av.avatar_html(user, tier=env_tier(score), size=30,
                                 animate=False)
    else:
        cfg = _av.config_from_user(user)
        sprout = _av.svg(cfg, tier=env_tier(score), size=30, halo=False)
    st.markdown(
        f"<div class='impact-userchip' role='button' tabindex='0' "
        f"title='Open your profile'>"
        f"<span class='mascot'>{mini_mascot_svg(score, 34, theme)}</span>"
        f"<span class='name'>{name}</span>"
        f"<span class='avatar'>{sprout}</span></div>",
        unsafe_allow_html=True)
    # wire the click to the sidebar Profile nav link (client-side nav)
    st.html("""<script>
(function () {
  const doc = document;
  const chip = doc.querySelector('.impact-userchip');
  if (!chip || chip.dataset.wired) return;
  const link = [...doc.querySelectorAll('section[data-testid="stSidebar"] a')]
    .find(a => /(^|\\/)profile(\\/|$|\\?)/i.test(a.getAttribute('href') || '')
            || /\\bProfile\\b/.test(a.textContent || ''));
  if (!link) return;
  chip.dataset.wired = '1';
  chip.style.cursor = 'pointer';
  const go = () => link.click();
  chip.addEventListener('click', go);
  chip.addEventListener('keydown', e => {
    if (e.key === 'Enter' || e.key === ' ') { e.preventDefault(); go(); }
  });
})();
</script>""")


def scroll_top():
    """Scroll the app back to the top (used on page/step changes)."""
    st.html("""<script>
(function () {
  const doc = document;
  const targets = [
    doc.querySelector('section[data-testid="stMain"]'),
    doc.querySelector('section.main'),
    doc.querySelector('div[data-testid="stAppViewContainer"]'),
    doc.scrollingElement,
  ];
  targets.forEach(t => { if (t && t.scrollTo) t.scrollTo({top: 0, left: 0, behavior: 'instant'}); });
})();
</script>""")


def celebrate():
    """Themed celebration: leaves and water droplets drift down — replaces
    st.balloons()."""
    st.html("""<script>
(function () {
  const doc = document;
  if (doc.getElementById('impact-celebrate')) return;
  const wrap = doc.createElement('div');
  wrap.id = 'impact-celebrate';
  wrap.style.cssText =
    'position:fixed;inset:0;pointer-events:none;z-index:99999;overflow:hidden;';
  const style = doc.createElement('style');
  style.textContent =
    '@keyframes impactFall{0%{transform:translate3d(0,-10vh,0) rotate(0deg);opacity:0}' +
    '8%{opacity:.95}85%{opacity:.95}100%{transform:translate3d(var(--dx),108vh,0) ' +
    'rotate(var(--rot));opacity:0}}';
  wrap.appendChild(style);
  const shapes = [
    '<svg viewBox="0 0 24 24" fill="#2E9E63" opacity="0.9"><path d="M20 4C11 4 5.5 9.5 5.5 19c9.5 0 15-5.5 14.5-15z"/></svg>',
    '<svg viewBox="0 0 24 24" fill="#7fc98f" opacity="0.9"><path d="M20 4C11 4 5.5 9.5 5.5 19c9.5 0 15-5.5 14.5-15z"/></svg>',
    '<svg viewBox="0 0 24 24" fill="#7EC8E3" opacity="0.85"><path d="M12 2.7C8.8 7 6 10.4 6 14a6 6 0 0 0 12 0c0-3.6-2.8-7-6-11.3z"/></svg>'
  ];
  for (let i = 0; i < 28; i++) {
    const el = doc.createElement('div');
    el.innerHTML = shapes[i % shapes.length];
    const svg = el.firstChild;
    const size = 13 + Math.random() * 15;
    svg.setAttribute('width', size); svg.setAttribute('height', size);
    const dur = 3 + Math.random() * 2.6;
    const delay = Math.random() * 1.4;
    el.style.cssText =
      'position:absolute;top:0;left:' + (Math.random() * 100) + '%;' +
      '--dx:' + ((Math.random() * 160 - 80).toFixed(0)) + 'px;' +
      '--rot:' + ((Math.random() * 520 - 260).toFixed(0)) + 'deg;' +
      'animation:impactFall ' + dur + 's ' + delay + 's cubic-bezier(.25,.4,.6,.95) forwards;';
    wrap.appendChild(el);
  }
  doc.body.appendChild(wrap);
  setTimeout(() => wrap.remove(), 7500);
})();
</script>""")


# ---------------------------------------------------------------------------
# Mascot: a daisy on a small Earth, reacting gradually to the score
# ---------------------------------------------------------------------------

def mascot_html(score, height=260, caption=True, theme="light"):
    """A daisy growing from a CURVED EARTH HORIZON (spec §19): only the top
    cap of the globe is shown (big circle centred far below the frame), so the
    flower reads as growing *from* the Earth, not floating above a full planet.
    Health, atmosphere, clouds, sun/moon and stress all still track the score
    (spec §20), in day or night palette."""
    p = scene_params(score, theme)
    night = p["night"]
    sway = ("daisy-sway 5s ease-in-out infinite alternate" if p["sway"]
            else "none")
    cap = ""
    if caption:
        # No "/100" denominator — the scale is open above 100 (net positive).
        s = int(score) if score is not None else "—"
        cap_col = "#cfe9db" if night else "#1B5E3B"
        sub_col = "#9fb0ad" if night else "#5c7069"
        mood_txt = (TIER_LABEL[env_tier(score)] if score is not None
                    else "Complete an assessment to wake your daisy")
        cap = (f"<div style='text-align:center;font-family:sans-serif;"
               f"color:{cap_col};font-weight:700;font-size:15px'>Impact score: {s}"
               f"<div style='color:{sub_col};font-weight:600;font-size:13px'>{mood_txt}</div></div>")
    # sun (day) or moon (night) in the upper corner
    if night:
        orb = ('<circle cx="230" cy="72" r="24" fill="#eef3ff" '
               f'opacity="{p["sun_opacity"]}"/>'
               '<circle cx="222" cy="66" r="20" fill="#dfe7f5" '
               f'opacity="{p["sun_opacity"] * 0.6:.2f}"/>')
        stars = "".join(
            f'<circle cx="{x}" cy="{y}" r="1.6" fill="#ffffff" '
            f'opacity="{p["star_opacity"]:.2f}"/>'
            for x, y in [(56, 60), (92, 76), (150, 54), (250, 102), (66, 122),
                         (246, 58), (120, 92)])
    else:
        orb = (f'<g class="sunrays" opacity="{p["sun_opacity"]}">'
               '<circle cx="228" cy="72" r="21" fill="#FFD86B"/>'
               '<g stroke="#FFD86B" stroke-width="4" stroke-linecap="round">'
               '<line x1="228" y1="40" x2="228" y2="50"/>'
               '<line x1="196" y1="72" x2="204" y2="72"/>'
               '<line x1="252" y1="72" x2="260" y2="72"/>'
               '<line x1="205" y1="49" x2="211" y2="55"/>'
               '<line x1="251" y1="49" x2="245" y2="55"/></g></g>')
        stars = ""
    return f"""
<div style="width:100%;display:flex;flex-direction:column;align-items:center">
<style>
@keyframes daisy-sway {{ from {{ transform: rotate(-2.5deg); }} to {{ transform: rotate(2.5deg); }} }}
@keyframes cloud-drift {{ from {{ transform: translateX(-12px); }} to {{ transform: translateX(12px); }} }}
@keyframes sun-pulse {{ from {{ opacity: {max(0.05, p['sun_opacity'] - 0.15)}; }} to {{ opacity: {p['sun_opacity']}; }} }}
.mascot-svg * {{ transition: all 1.2s ease; }}
.cloud {{ animation: cloud-drift 9s ease-in-out infinite alternate; }}
.sunrays {{ animation: sun-pulse 4s ease-in-out infinite alternate; transform-origin: 228px 72px; }}
.daisy {{ transform-origin: 150px 230px; animation: {sway}; }}
@media (prefers-reduced-motion: reduce) {{
  .cloud, .sunrays, .daisy {{ animation: none !important; }}
}}
</style>
<svg class="mascot-svg" viewBox="38 42 224 224" width="{height}" height="{height}" xmlns="http://www.w3.org/2000/svg" role="img" aria-label="Daisy growing from the Earth, reflecting your environmental score">
  <!-- viewBox crops tight onto the daisy + horizon (§16: zoomed-in, face-first
       composition, minimal empty sky) -->
  <defs>
    <linearGradient id="sky" x1="0" y1="0" x2="0" y2="1">
      <stop offset="0%" stop-color="{p['sky_top']}"/>
      <stop offset="100%" stop-color="{p['sky_bottom']}"/>
    </linearGradient>
    <radialGradient id="oceanG" cx="40%" cy="28%" r="95%">
      <stop offset="0%" stop-color="{'#2f5885' if night else '#9fe2f7'}"/>
      <stop offset="100%" stop-color="{'#14263f' if night else '#4bb4e8'}"/>
    </radialGradient>
    <clipPath id="earthClip"><circle cx="150" cy="470" r="250"/></clipPath>
  </defs>

  <rect x="38" y="42" width="224" height="224" rx="22" fill="url(#sky)"/>
  {stars}
  {orb}

  <g class="cloud" opacity="{p['cloud_opacity']}" fill="{'#c9d6e6' if night else '#ffffff'}">
    <ellipse cx="88" cy="74" rx="30" ry="12"/>
    <ellipse cx="108" cy="67" rx="21" ry="10"/>
    <ellipse cx="70" cy="67" rx="17" ry="9"/>
  </g>

  <!-- soft atmosphere glow along the curved horizon (a gentle halo, no hard line) -->
  <circle cx="150" cy="470" r="256" fill="none"
          stroke="{'#bfeeff' if not night else '#3d6fa6'}" stroke-opacity="0.28"
          stroke-width="16"/>
  <!-- the Earth: a big globe cropped so only its top cap (a curved horizon) shows -->
  <g style="filter: brightness({p['earth_bright']});">
    <circle cx="150" cy="470" r="250" fill="url(#oceanG)"/>
    <g clip-path="url(#earthClip)">
      <!-- simplified organic continents (smooth beziers, brighter fresh greens) -->
      <path d="M52 258 C 52 244 78 236 100 244 C 122 251 130 268 116 279
               C 99 290 68 286 58 271 C 52 263 51 261 52 258 Z"
            fill="{p['leaf']}"/>
      <path d="M168 262 C 170 247 202 242 224 251 C 245 260 247 274 231 284
               C 212 294 181 289 172 276 C 166 268 166 265 168 262 Z"
            fill="{p['leaf']}"/>
      <path d="M122 284 C 122 277 140 274 152 279 C 164 284 164 293 151 297
               C 138 301 122 297 122 290 Z" fill="{p['grass']}"/>
      <ellipse cx="92" cy="252" rx="13" ry="6" fill="{p['grass']}" opacity="0.7"/>
      <ellipse cx="206" cy="258" rx="14" ry="6" fill="{p['grass']}" opacity="0.7"/>
    </g>
  </g>

  <!-- distant fire glow on the horizon (very poor only) -->
  <g opacity="{p['fire_opacity']}" transform="translate(-14 0)">
    <ellipse cx="235" cy="258" rx="42" ry="14" fill="#ff8a3c"/>
    <path d="M226 258 q4 -14 10 -18 q-2 11 4 15 q6 -4 6 -13 q9 13 0 24 q-11 11 -20 -8z" fill="#ff9c54"/>
  </g>

  <!-- the daisy, growing from the horizon surface (~y=238) -->
  <g class="daisy" transform="rotate({-p['droop']} 150 236)">
    <path d="M150 238 C 150 205, 146 175, 150 150" stroke="{p['leaf']}" stroke-width="6" fill="none" stroke-linecap="round"/>
    <path d="M150 200 q-18 -5 -24 -18 q18 -2 24 9z" fill="{p['leaf']}"/>
    <path d="M150 184 q18 -5 24 -18 q-18 -2 -24 9z" fill="{p['leaf']}"/>
    <g transform="rotate({-p['droop'] * 0.5} 150 132)">
      <!-- petals: fuller, more vibrant, with a soft two-tone for depth -->
      {"".join(f'<ellipse cx="150" cy="101" rx="12.5" ry="29" fill="{p["petal"]}" stroke="{("#3a4658" if night else "#efe6cf")}" stroke-width="1.2" transform="rotate({a} 150 132)"/>' for a in range(0, 360, 30))}
      {"".join(f'<ellipse cx="150" cy="112" rx="6" ry="13" fill="#fff7d6" opacity="0.55" transform="rotate({a} 150 132)"/>' for a in range(0, 360, 30))}
      <!-- face disc: bigger and a vibrant gold, stronger silhouette -->
      <circle cx="150" cy="132" r="22" fill="#FFCE1F" stroke="#EDA600" stroke-width="2.6"/>
      <circle cx="150" cy="129" r="20" fill="none" stroke="#FFE58A" stroke-width="1.4" opacity="0.7"/>
      <!-- rosy cheeks -->
      <circle cx="137.5" cy="137" r="3.4" fill="#ff9db0" opacity="{round(min(0.85, 0.3 + p['t'] * 0.7), 2)}"/>
      <circle cx="162.5" cy="137" r="3.4" fill="#ff9db0" opacity="{round(min(0.85, 0.3 + p['t'] * 0.7), 2)}"/>
      <!-- expressive brows (lift with a better score → curious/optimistic) -->
      <path d="M141 {round(122 - p['t'] * 1.5, 1)} q3.5 -2.4 7 -0.4" stroke="#c98a00" stroke-width="1.8" fill="none" stroke-linecap="round"/>
      <path d="M152 {round(121.6 - p['t'] * 1.5, 1)} q3.5 -2 7 0.4" stroke="#c98a00" stroke-width="1.8" fill="none" stroke-linecap="round"/>
      <!-- big friendly eyes: larger whites, bold pupils, twin catch-lights -->
      <ellipse cx="143.5" cy="129" rx="3.7" ry="4.7" fill="#ffffff"/>
      <ellipse cx="156.5" cy="129" rx="3.7" ry="4.7" fill="#ffffff"/>
      <circle cx="144" cy="129.9" r="2.5" fill="#3c2c05"/>
      <circle cx="156" cy="129.9" r="2.5" fill="#3c2c05"/>
      <circle cx="145" cy="128.4" r="1.05" fill="#ffffff"/>
      <circle cx="157" cy="128.4" r="1.05" fill="#ffffff"/>
      <circle cx="143.2" cy="130.8" r="0.5" fill="#ffffff" opacity="0.7"/>
      <circle cx="155.2" cy="130.8" r="0.5" fill="#ffffff" opacity="0.7"/>
      <!-- mouth: gentle when struggling → open happy smile when thriving -->
      <path d="M142 {round(138 - p['t'] * 0.5, 1)} q8 {round(_lerp(-1.5, 10.0, p['t']), 1)} 16 0" stroke="#8a5a08" stroke-width="2.3" fill="none" stroke-linecap="round"/>
      {'<path d="M150 140 q4 5 8 0 q-4 3 -8 0z" fill="#e2596b"/>' if p['t'] > 0.6 else ''}
      {'<path d="M182 95 l2.6 6 6 2.6 -6 2.6 -2.6 6 -2.6 -6 -6 -2.6 6 -2.6z" fill="#fff3b0"/>' if p['t'] > 0.8 else ''}
    </g>
  </g>
</svg>
{cap}
</div>"""


def render_mascot(score, height=260, caption=True, theme=None):
    if theme is None:
        theme = active_theme()
    h = height + (48 if caption else 8)
    st.html(f'<div style="height:{h}px;overflow:hidden">'
            + mascot_html(score, height=height, caption=caption, theme=theme)
            + '</div>')


def score_ring(score, label="Impact score"):
    """A clean score ring (brief §5/§14): ONLY the number sits inside the ring
    (never overlapped by the status), the caption and a high-contrast status
    chip sit clearly beneath it, and a hover tooltip explains the value."""
    val = int(round(score)) if score is not None else None
    color = score_color(val)                # vibrant spectrum, no sludge (§17/§19)
    txt = score_text_color(val)             # dark, readable status text (§5)
    circ = 2 * 3.14159 * 42
    shown = 0 if val is None else max(0, min(100, val))
    dash = circ * shown / 100               # ring fills to 100; value can exceed
    plus = "+" if (val or 0) > 100 else ""
    num = f"{val}{plus}" if val is not None else "—"
    glow = (f'<circle cx="50" cy="50" r="42" fill="none" stroke="{color}" '
            f'stroke-width="14" opacity="0.18"/>') if (val or 0) >= 100 else ""
    tip = html.escape(score_hint(val))
    return _flat(f"""
    <div class="score-ring" title="{tip}">
      <svg viewBox="0 0 100 100" width="120" height="120" aria-hidden="true">
        {glow}
        <circle cx="50" cy="50" r="42" fill="none" stroke="#e6efeb" stroke-width="10"/>
        <circle cx="50" cy="50" r="42" fill="none" stroke="{color}" stroke-width="10"
                stroke-linecap="round" stroke-dasharray="{dash:.1f} {circ:.1f}"
                transform="rotate(-90 50 50)"/>
        <text x="50" y="50" text-anchor="middle" dominant-baseline="central"
              font-size="30" font-weight="800" fill="{DEEP}"
              font-family="'Baloo 2',sans-serif">{num}</text>
      </svg>
      <div class="score-ring-cap">{label}</div>
      <div class="score-ring-status" style="color:{txt}">
        <span class="dot" style="background:{color}"></span>{score_label(val)}
      </div>
      <div class="score-ring-dir">Higher is better · 50 avg · 100 net&nbsp;zero</div>
    </div>""")
