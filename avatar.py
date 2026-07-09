"""
The user's avatar — "Sprout" (spec §11).
==========================================

A cute, expressive, nature-human *character* that represents the USER (never a
generic emoji or profile circle). It is deliberately a different creature from
the daisy mascot, which represents the APP:

  * the daisy grows on the Earth and is the friendly guide/coach (see visuals.py)
  * the Sprout is a rounded little person with a living sprig growing from their
    hair — the user, part of the living world. It CHANGES with the person: it
    is customisable, and its expression + habitat react to their impact score.

The whole character is one reusable, layered inline SVG so it stays crisp and
identical from a 26px chip to a 200px profile hero. Emotion, idle motion
(breathing + blinking), a hover reaction and a habitat halo that blooms with
progress are all built in and honour `prefers-reduced-motion`.

Storage is backward compatible: the DB `avatar` column historically held an
emoji. `config_from_user()` reads either a JSON config (new) or a legacy emoji
(mapped to a pleasant default), so nothing needs migrating.
"""

from __future__ import annotations

import base64
import html
import json
import os
import re


def _flat(svg):
    """Collapse an inline SVG to a single line with no HTML comments. Streamlit's
    markdown renderer can otherwise split multi-line inline SVG and leak a stray
    closing tag (e.g. '</g>') as visible text (§7). Purely cosmetic on the
    string — the rendered graphic is identical."""
    svg = re.sub(r"<!--.*?-->", "", svg, flags=re.DOTALL)
    svg = re.sub(r">\s+<", "><", svg)
    return svg.strip()

# --------------------------------------------------------------------------- #
# Customisation palettes (kept small on purpose — emotional ownership, not a
# full character creator, per the brief).
# --------------------------------------------------------------------------- #
SKINS = ["#ffd9b8", "#f6c391", "#e0a656", "#c78a4e", "#a06a3a", "#6f4726"]

HAIRS = ["#2b2018", "#4a3120", "#7a4a24", "#b06a2e", "#d7a13f", "#8f8f9a",
         "#e8e2d8", "#6c5cff", "#e0568c", "#2fa96b"]

TOPS = ["#2E9E63", "#3E9BD6", "#6C5CE7", "#F2A73B", "#EF6F5B", "#22B3A0",
        "#E8558C"]

HAIR_STYLES = ["short", "curly", "bun", "long", "wavy", "buzz", "bald"]
ACCESSORIES = ["none", "glasses", "sunhat", "flower", "cap"]

DEFAULT_CONFIG = {
    "skin": SKINS[1],
    "hair": HAIRS[1],
    "hair_style": "short",
    "top": TOPS[0],
    "accessory": "none",
}

# Legacy single-emoji avatars → a friendly default character, tinted so old
# demo accounts still look distinct from one another.
_EMOJI_MAP = {
    "🌱": {"top": "#2E9E63", "hair_style": "short", "hair": HAIRS[9]},
    "🌻": {"top": "#F2A73B", "hair_style": "long", "hair": HAIRS[4],
           "accessory": "flower"},
    "🌳": {"top": "#22B3A0", "hair_style": "curly", "hair": HAIRS[0]},
    "🐝": {"top": "#F2A73B", "hair_style": "buzz", "hair": HAIRS[0]},
    "🦉": {"top": "#6C5CE7", "hair_style": "wavy", "hair": HAIRS[5],
           "accessory": "glasses"},
    "🐬": {"top": "#3E9BD6", "hair_style": "short", "hair": HAIRS[1]},
    "⛰️": {"top": "#8f8f9a", "hair_style": "bun", "hair": HAIRS[2],
           "accessory": "sunhat"},
    "☀️": {"top": "#EF6F5B", "hair_style": "short", "hair": HAIRS[3],
           "accessory": "cap"},
}


def config_from_user(user) -> dict:
    """Return a full avatar config from a user row (or a raw stored value).

    Accepts the new JSON config or a legacy emoji; always returns every key so
    callers never KeyError."""
    raw = user["avatar"] if isinstance(user, dict) else user
    cfg = dict(DEFAULT_CONFIG)
    if not raw:
        return cfg
    raw = raw.strip()
    if raw.startswith("{"):
        try:
            cfg.update({k: v for k, v in json.loads(raw).items() if k in cfg})
        except (ValueError, TypeError):
            pass
        return cfg
    # legacy emoji
    cfg.update(_EMOJI_MAP.get(raw, {}))
    return cfg


def config_to_str(cfg: dict) -> str:
    """Compact JSON for the DB `avatar` column."""
    return json.dumps({k: cfg.get(k, DEFAULT_CONFIG[k]) for k in DEFAULT_CONFIG},
                      separators=(",", ":"))


# --------------------------------------------------------------------------- #
# Emotion model — derived from the environmental tier, overridable by an
# explicit state (thinking / celebrate / wave …). Never guilt-heavy: the low
# end is gently *thoughtful*, not sad or accusing (spec §11, §9).
# --------------------------------------------------------------------------- #
#   mouth  : path 'd' for the mouth
#   brow   : vertical nudge for eyebrows (– = raised/happy, + = concerned)
#   cheeks : rosy-cheek opacity 0..1
#   eyes   : 'open' | 'happy' (closed-up smile eyes) | 'up' (looking up/thinking)
_EMOTIONS = {
    "thoughtful": {"mouth": "M42 61 Q50 58 58 61", "brow": 1.5,
                   "cheeks": 0.0, "eyes": "open", "look": (0.0, 0.6)},
    "neutral":    {"mouth": "M43 60 Q50 63 57 60", "brow": 0.0,
                   "cheeks": 0.25, "eyes": "open", "look": (0.0, 0.0)},
    "happy":      {"mouth": "M41 59 Q50 68 59 59", "brow": -1.0,
                   "cheeks": 0.55, "eyes": "open", "look": (0.0, 0.0)},
    "celebrate":  {"mouth": "M40 58 Q50 72 60 58 Q50 66 40 58", "brow": -2.2,
                   "cheeks": 0.8, "eyes": "happy", "look": (0.0, 0.0)},
    "thinking":   {"mouth": "M45 61 Q50 60 55 62", "brow": -0.5,
                   "cheeks": 0.2, "eyes": "up", "look": (0.35, -0.5)},
}

# score tier (from visuals.env_tier) → resting emotion
TIER_EMOTION = {
    "NO_ASSESSMENT": "neutral",
    "VERY_POOR": "thoughtful",
    "POOR": "thoughtful",
    "AVERAGE": "neutral",
    "GOOD": "happy",
    "EXCELLENT": "celebrate",
    "NET_ZERO": "celebrate",
    "NET_POSITIVE": "celebrate",
}

# tier → habitat richness 0..1 (halo blooms as impact improves; the two
# net-impact tiers keep the fullest habitat — spec §18)
_TIER_BLOOM = {
    "NO_ASSESSMENT": 0.15, "VERY_POOR": 0.0, "POOR": 0.25,
    "AVERAGE": 0.5, "GOOD": 0.75, "EXCELLENT": 1.0,
    "NET_ZERO": 1.0, "NET_POSITIVE": 1.0,
}

_uid_counter = [0]


def _uid():
    _uid_counter[0] += 1
    return f"av{_uid_counter[0]}"


def _hair(style, color, skin):
    """Front hair shape by style. Coordinates are in the 100×100 face space;
    head is centred ~ (50, 40), radius ~24."""
    c = color
    if style == "bald":
        return ""
    if style == "buzz":
        return (f"<path d='M28 38 Q30 17 50 15 Q70 17 72 38 Q66 27 50 26 "
                f"Q34 27 28 38 Z' fill='{c}' opacity='0.92'/>")
    if style == "short":
        return (f"<path d='M27 40 Q26 15 50 13 Q74 15 73 40 Q72 30 64 27 "
                f"Q64 20 50 19 Q40 19 38 26 Q30 28 27 40 Z' fill='{c}'/>")
    if style == "curly":
        return ("".join(
            f"<circle cx='{cx}' cy='{cy}' r='{r}' fill='{c}'/>"
            for cx, cy, r in [(32, 30, 8), (30, 40, 7), (40, 22, 9),
                              (50, 19, 9), (60, 22, 9), (70, 30, 8),
                              (71, 40, 7)]))
    if style == "bun":
        return (f"<circle cx='50' cy='13' r='8' fill='{c}'/>"
                f"<path d='M27 40 Q26 16 50 15 Q74 16 73 40 Q71 30 62 27 "
                f"Q60 22 50 22 Q40 22 38 27 Q30 30 27 40 Z' fill='{c}'/>")
    if style == "long":
        return (f"<path d='M24 34 Q24 12 50 12 Q76 12 76 34 L76 66 Q76 72 70 72 "
                f"L70 40 Q68 30 60 27 Q60 21 50 21 Q40 21 40 27 Q32 30 30 40 "
                f"L30 72 Q24 72 24 66 Z' fill='{c}'/>")
    if style == "wavy":
        return (f"<path d='M26 42 Q24 14 50 13 Q76 14 74 42 Q70 34 68 40 "
                f"Q66 30 58 27 Q58 21 50 21 Q42 21 42 27 Q34 30 32 40 "
                f"Q30 34 26 42 Z' fill='{c}'/>")
    return ""


def _accessory(kind, top, uid):
    if kind == "glasses":
        return ("<g stroke='#3a3a44' stroke-width='2.2' fill='#ffffff' "
                "fill-opacity='0.28'>"
                "<circle cx='41' cy='43' r='7'/><circle cx='59' cy='43' r='7'/>"
                "<path d='M48 43 h4' stroke-linecap='round'/>"
                "<path d='M34 41 l-5 -1' stroke-linecap='round'/>"
                "<path d='M66 41 l5 -1' stroke-linecap='round'/></g>")
    if kind == "flower":
        return ("<g transform='translate(69 22)'>"
                + "".join(f"<ellipse cx='0' cy='-5' rx='2.6' ry='4.4' "
                          f"fill='#ffb3c9' transform='rotate({a})'/>"
                          for a in range(0, 360, 72))
                + "<circle r='3' fill='#ffd45e'/></g>")
    if kind == "sunhat":
        return ("<g><ellipse cx='50' cy='20' rx='30' ry='7' fill='#e9c27a'/>"
                "<path d='M34 20 Q34 6 50 6 Q66 6 66 20 Z' fill='#f0d090'/>"
                "<path d='M34 19 Q50 24 66 19' stroke='#cf9a4a' "
                "stroke-width='2' fill='none'/></g>")
    if kind == "cap":
        return (f"<g><path d='M28 24 Q30 9 50 9 Q70 9 72 24 Z' fill='{top}'/>"
                f"<path d='M28 24 Q18 24 16 28 Q30 27 40 26 Z' fill='{top}' "
                f"style='filter:brightness(0.85)'/></g>")
    return ""


def _halo(bloom, uid):
    """A small habitat that accumulates behind the character as impact
    improves: buds → flowers → flowers + a butterfly + sparkles (spec §11)."""
    if bloom <= 0.02:
        # struggling: one tiny, hopeful sprout — never barren/punishing
        return ("<g class='av-halo' opacity='0.9'>"
                "<path d='M50 92 q-4 -5 0 -9 q4 4 0 9' fill='#8fca7e'/></g>")
    parts = ["<g class='av-halo'>"]
    # arc of flowers along the ground line
    n = 2 + round(4 * bloom)
    for i in range(n):
        t = i / max(1, n - 1)
        x = 14 + t * 72
        y = 90 - (abs(t - 0.5) * -6)   # gentle arc
        col = ["#ffd45e", "#ff9db0", "#8ad0ff", "#c9a2ff"][i % 4]
        parts.append(
            f"<g transform='translate({x:.0f} {y:.0f})'>"
            f"<path d='M0 6 V0' stroke='#5fae5a' stroke-width='1.6'/>"
            + "".join(f"<ellipse cx='0' cy='-3.4' rx='1.7' ry='2.9' fill='{col}' "
                      f"transform='rotate({a})'/>" for a in range(0, 360, 72))
            + "<circle r='1.7' fill='#fff0b0'/></g>")
    # butterfly + sparkles when thriving
    if bloom > 0.7:
        parts.append(
            "<g class='av-flit' transform='translate(78 30)'>"
            "<path d='M0 0 q-6 -6 -9 -1 q0 6 9 3 z' fill='#ff9db0'/>"
            "<path d='M0 0 q6 -6 9 -1 q0 6 -9 3 z' fill='#8ad0ff'/>"
            "<circle r='1.4' fill='#3a3a44'/></g>"
            "<path class='av-spark' d='M20 22 l1.4 3 3 1.4 -3 1.4 -1.4 3 "
            "-1.4 -3 -3 -1.4 3 -1.4z' fill='#fff3b0'/>")
    parts.append("</g>")
    return "".join(parts)


def css() -> str:
    """One-time keyframes/transitions for every avatar on the page. Scoped to
    `.avatar-shell` and reduced-motion-aware."""
    return """
<style>
.avatar-shell { display:inline-block; line-height:0; }
.avatar-shell svg { display:block; overflow:visible; }
.av-body { transform-box: fill-box; transform-origin: 50% 100%;
           animation: av-breathe 4.6s ease-in-out infinite; }
.av-eyelid { transform-box: fill-box; transform-origin: 50% 0%;
             animation: av-blink 5.2s infinite; }
.av-sprig { transform-box: fill-box; transform-origin: 50% 100%;
            animation: av-sway 4s ease-in-out infinite alternate; }
.av-flit { transform-box: fill-box; transform-origin: 50% 50%;
           animation: av-flit 3.4s ease-in-out infinite; }
.av-spark { transform-box: fill-box; transform-origin: 50% 50%;
            animation: av-spark 2.2s ease-in-out infinite; }
.avatar-shell .av-inner { transform-box: fill-box; transform-origin: 50% 90%;
    transition: transform .3s cubic-bezier(.34,1.56,.64,1); }
.avatar-shell:hover .av-inner { transform: rotate(-4deg) scale(1.05); }
.avatar-shell.celebrate .av-inner { animation: av-bounce .9s ease-in-out 2; }
@keyframes av-breathe { 0%,100%{transform:translateY(0) scaleY(1)}
    50%{transform:translateY(-0.6px) scaleY(1.02)} }
@keyframes av-blink { 0%,92%,100%{transform:scaleY(0)}
    94%,98%{transform:scaleY(1)} }
@keyframes av-sway { from{transform:rotate(-6deg)} to{transform:rotate(6deg)} }
@keyframes av-flit { 0%,100%{transform:translate(0,0) rotate(-6deg)}
    50%{transform:translate(-5px,-6px) rotate(6deg)} }
@keyframes av-spark { 0%,100%{opacity:0;transform:scale(0.4)}
    50%{opacity:1;transform:scale(1)} }
@keyframes av-bounce { 0%,100%{transform:translateY(0)}
    30%{transform:translateY(-10%)} 60%{transform:translateY(-3%)} }
@media (prefers-reduced-motion: reduce) {
  .av-body,.av-eyelid,.av-sprig,.av-flit,.av-spark,
  .avatar-shell .av-inner,.avatar-shell.celebrate .av-inner {
    animation: none !important; }
}
</style>"""


def svg(cfg=None, tier="NO_ASSESSMENT", size=96, state=None, animate=True,
        halo=True):
    """The Sprout character.

    cfg      : customisation dict (see DEFAULT_CONFIG); None → default
    tier     : env tier string (from visuals.env_tier) → resting emotion + halo
    state    : explicit override — 'thinking' | 'celebrate' | 'happy' | …
    animate  : idle breathing/blinking/sway (still CSS-gated by reduced-motion)
    halo     : draw the blooming habitat behind the character
    """
    cfg = {**DEFAULT_CONFIG, **(cfg or {})}
    emotion_name = state if state in _EMOTIONS else TIER_EMOTION.get(tier,
                                                                     "neutral")
    e = _EMOTIONS[emotion_name]
    bloom = _TIER_BLOOM.get(tier, 0.4)
    uid = _uid()
    skin = cfg["skin"]
    skin_shadow = _shade(skin, 0.9)
    top = cfg["top"]
    top_shadow = _shade(top, 0.86)
    lx, ly = e["look"]           # pupil offset

    a = "" if animate else " style='animation:none'"
    body_cls = "av-body" if animate else ""
    lid_cls = "av-eyelid" if animate else ""
    sprig_cls = "av-sprig" if animate else ""
    shell_cls = "avatar-shell" + (" celebrate" if emotion_name == "celebrate"
                                  and animate else "")

    # eyes
    if e["eyes"] == "happy":
        eyes = ("<path d='M36 43 Q41 39 46 43' stroke='#3a3128' "
                "stroke-width='2.4' fill='none' stroke-linecap='round'/>"
                "<path d='M54 43 Q59 39 64 43' stroke='#3a3128' "
                "stroke-width='2.4' fill='none' stroke-linecap='round'/>")
    else:
        eyes = (
            # whites
            "<ellipse cx='41' cy='43' rx='4.6' ry='5.2' fill='#ffffff'/>"
            "<ellipse cx='59' cy='43' rx='4.6' ry='5.2' fill='#ffffff'/>"
            # pupils (follow 'look')
            f"<circle cx='{41 + lx * 2.4:.1f}' cy='{43 + ly * 2.2:.1f}' "
            f"r='2.7' fill='#3a3128'/>"
            f"<circle cx='{59 + lx * 2.4:.1f}' cy='{43 + ly * 2.2:.1f}' "
            f"r='2.7' fill='#3a3128'/>"
            # catch-lights
            f"<circle cx='{42.4 + lx * 2.4:.1f}' cy='{41.8 + ly * 2.2:.1f}' "
            f"r='0.9' fill='#ffffff'/>"
            f"<circle cx='{60.4 + lx * 2.4:.1f}' cy='{41.8 + ly * 2.2:.1f}' "
            f"r='0.9' fill='#ffffff'/>"
            # blinking eyelids (skin-coloured shades dropping over the eyes)
            f"<rect class='{lid_cls}' x='36' y='37.6' width='9.2' height='5.6' "
            f"rx='2.8' fill='{skin}'/>"
            f"<rect class='{lid_cls}' x='54.4' y='37.6' width='9.2' "
            f"height='5.6' rx='2.8' fill='{skin}'/>")

    # thought bubble for 'thinking'
    think = ""
    if emotion_name == "thinking":
        think = ("<g opacity='0.95'><circle cx='74' cy='24' r='7' "
                 "fill='#ffffff' stroke='#d7e4dc'/>"
                 "<circle cx='66' cy='31' r='3' fill='#ffffff' "
                 "stroke='#d7e4dc'/>"
                 "<circle cx='71' cy='23' r='1.1' fill='#2E9E63'/>"
                 "<circle cx='74' cy='24' r='1.1' fill='#2E9E63'/>"
                 "<circle cx='77' cy='25' r='1.1' fill='#2E9E63'/></g>")

    hair_front = _hair(cfg["hair_style"], cfg["hair"], skin)
    accessory = _accessory(cfg["accessory"], top, uid)

    inner = f"""
  <g class="av-inner">
    <!-- shoulders / body -->
    <g class="{body_cls}"{a}>
      <path d="M20 100 Q20 78 34 72 Q42 84 50 84 Q58 84 66 72 Q80 78 80 100 Z"
            fill="{top}"/>
      <path d="M50 84 Q58 84 66 72 Q72 75 76 82 Q64 86 50 86 Q36 86 24 82
               Q28 75 34 72 Q42 84 50 84 Z" fill="{top_shadow}" opacity="0.5"/>
      <!-- collar leaf motif -->
      <path d="M50 86 q-6 -3 -3 -9 q6 2 3 9z" fill="{top_shadow}"
            opacity="0.55"/>
    </g>
    <!-- neck -->
    <rect x="45.5" y="60" width="9" height="14" rx="4.5" fill="{skin_shadow}"/>
    <!-- head -->
    <g transform="translate(0 {'-1' if animate else '0'})">
      <path d="M27 40 Q27 17 50 16 Q73 17 73 40 Q73 60 50 63 Q27 60 27 40 Z"
            fill="{skin}"/>
      <!-- ears -->
      <ellipse cx="27.5" cy="45" rx="3.4" ry="4.4" fill="{skin}"/>
      <ellipse cx="72.5" cy="45" rx="3.4" ry="4.4" fill="{skin}"/>
      <!-- the living sprig — the Sprout's signature (grows from the crown) -->
      <g class="{sprig_cls}">
        <path d="M50 17 Q50 8 50 4" stroke="#4fb06a" stroke-width="2.2"
              fill="none" stroke-linecap="round"/>
        <path d="M50 9 Q43 7 40 10 Q45 14 50 11 Z" fill="#57c078"/>
        <path d="M50 6 Q57 4 60 7 Q55 11 50 8 Z" fill="#6bd08c"/>
      </g>
      {hair_front}
      <!-- brows -->
      <path d="M36 {36.5 + e['brow']:.1f} Q41 {34.5 + e['brow']:.1f} 46 {36 + e['brow']:.1f}"
            stroke="{_shade(cfg['hair'], 0.8)}" stroke-width="1.8"
            fill="none" stroke-linecap="round"/>
      <path d="M54 {36 + e['brow']:.1f} Q59 {34.5 + e['brow']:.1f} 64 {36.5 + e['brow']:.1f}"
            stroke="{_shade(cfg['hair'], 0.8)}" stroke-width="1.8"
            fill="none" stroke-linecap="round"/>
      <!-- cheeks -->
      <circle cx="36" cy="51" r="3.6" fill="#ff9db0" opacity="{e['cheeks']:.2f}"/>
      <circle cx="64" cy="51" r="3.6" fill="#ff9db0" opacity="{e['cheeks']:.2f}"/>
      {eyes}
      <!-- nose -->
      <path d="M49.4 47 Q48.6 52 50 53 Q51.4 52 50.6 47"
            stroke="{skin_shadow}" stroke-width="1.2" fill="none"
            stroke-linecap="round"/>
      <!-- mouth -->
      <path d="{e['mouth']}" stroke="#9a4b3b" stroke-width="2.2"
            fill="none" stroke-linecap="round"/>
      {accessory}
    </g>
    {think}
  </g>"""

    halo_svg = _halo(bloom, uid) if halo else ""
    return _flat(
        f"<span class='{shell_cls}'>"
        f"<svg width='{size}' height='{size}' viewBox='0 0 100 105' "
        f"xmlns='http://www.w3.org/2000/svg' role='img' "
        f"aria-label='Your Sprout character'>"
        f"{halo_svg}{inner}</svg></span>")


def _shade(hexc, factor):
    """Multiply an #rrggbb colour toward black by `factor` (0..1)."""
    hexc = hexc.lstrip("#")
    if len(hexc) != 6:
        return "#" + hexc
    r, g, b = (int(hexc[i:i + 2], 16) for i in (0, 2, 4))
    return "#" + "".join(f"{max(0, min(255, int(v * factor))):02x}"
                         for v in (r, g, b))


# --------------------------------------------------------------------------- #
# Photo avatar (spec §12) with an eco-progression FRAME (spec §13).
#
# Key rule: a generated photo-avatar's IDENTITY never changes with progress —
# we keep the same portrait and only grow the environment AROUND it (a ring
# that blooms with tier, small plants, and a gentle glow at the top tier),
# mirroring the Sprout's habitat halo. This avoids identity drift and repeated
# generation cost. Gentle idle motion respects prefers-reduced-motion (§14).
# --------------------------------------------------------------------------- #

def _photo_frame(data_uri, tier, size, animate):
    bloom = _TIER_BLOOM.get(tier, 0.4)
    uid = _uid()
    ring = "#8fca7e" if bloom > 0.25 else "#cfe0d4"
    glow = bloom > 0.9
    pad = max(6, int(size * 0.12))          # room for the ring + plants
    inner = size - pad * 2
    cx = size / 2
    # a small arc of leaves along the bottom that grows with the tier
    n = round(6 * bloom)
    leaves = ""
    import math
    for i in range(n):
        frac = (i + 1) / (n + 1)
        ang = math.pi * (0.15 + 0.7 * frac)     # lower arc
        lx = cx - (size / 2 - 3) * math.cos(ang)
        ly = (size / 2) + (size / 2 - 3) * math.sin(ang) * 0.62
        leaves += (f"<path d='M{lx:.1f} {ly:.1f} q-3 -5 0 -9 q3 4 0 9' "
                   f"fill='#6bbf59' opacity='0.9'/>")
    anim_cls = "uav-anim" if animate else ""
    glow_svg = (f"<circle cx='{cx}' cy='{cx}' r='{inner/2 + pad*0.6:.1f}' "
                f"fill='none' stroke='#ffe9a8' stroke-width='{pad*0.5:.0f}' "
                f"opacity='0.55'/>") if glow else ""
    return _flat(f"""<span class='uav {anim_cls}' style='display:inline-block;width:{size}px;height:{size}px'>
<style>
.uav {{position:relative}}
.uav-anim .uav-inner {{animation:uav-breathe 5s ease-in-out infinite;transform-origin:50% 60%}}
.uav:hover .uav-inner {{transform:scale(1.04)}}
@keyframes uav-breathe {{0%,100%{{transform:scale(1)}}50%{{transform:scale(1.02)}}}}
@media (prefers-reduced-motion: reduce) {{.uav-anim .uav-inner{{animation:none}}}}
</style>
<svg viewBox='0 0 {size} {size}' width='{size}' height='{size}'>
  <defs><clipPath id='clip{uid}'><circle cx='{cx}' cy='{cx}' r='{inner/2:.1f}'/></clipPath></defs>
  {glow_svg}
  <circle cx='{cx}' cy='{cx}' r='{inner/2 + 3:.1f}' fill='none' stroke='{ring}' stroke-width='3'/>
  <g class='uav-inner'>
    <image href='{data_uri}' x='{pad}' y='{pad}' width='{inner}' height='{inner}'
           preserveAspectRatio='xMidYMid slice' clip-path='url(#clip{uid})'/>
  </g>
  {leaves}
</svg></span>""")


def has_photo(user):
    if not isinstance(user, dict):
        return False
    return (user.get("avatar_mode") == "photo"
            and user.get("avatar_photo")
            and os.path.exists(user["avatar_photo"]))


def avatar_html(user, tier="NO_ASSESSMENT", size=96, animate=True):
    """Single render entry point for the USER avatar: a generated photo-avatar
    (in its eco-progression frame) when the user has one, otherwise the
    procedural Sprout. Both react to `tier` (§13)."""
    if has_photo(user):
        try:
            with open(user["avatar_photo"], "rb") as fh:
                data = base64.b64encode(fh.read()).decode()
            return _photo_frame(f"data:image/png;base64,{data}", tier, size,
                                animate)
        except OSError:
            pass   # fall through to the Sprout — never a broken image (§20)
    return svg(config_from_user(user), tier=tier, size=size, animate=animate)
