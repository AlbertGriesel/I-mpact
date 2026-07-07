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

import streamlit as st
from streamlit.components.v1 import html as st_html

# palette
GREEN = "#2E9E63"
DEEP = "#1B5E3B"
BLUE = "#7EC8E3"
SOFT = "#F4F7F6"

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


# ---------------------------------------------------------------------------
# Reactive scene parameters (gradual, never binary)
# ---------------------------------------------------------------------------

def _lerp(a, b, t):
    return a + (b - a) * t


def _hex_lerp(h1, h2, t):
    c1 = [int(h1[i:i + 2], 16) for i in (1, 3, 5)]
    c2 = [int(h2[i:i + 2], 16) for i in (1, 3, 5)]
    return "#" + "".join(f"{int(round(_lerp(a, b, t))):02x}" for a, b in zip(c1, c2))


def scene_params(score):
    t = max(0.0, min(1.0, (score if score is not None else 55) / 100.0))
    return {
        "t": t,
        "sky_top": _hex_lerp("#9aa3ad", "#8fd3f2", t),
        "sky_bottom": _hex_lerp("#e8ddd2", "#eafaf0", t),
        "sun_opacity": round(0.15 + 0.85 * t, 2),
        "cloud_opacity": round(max(0.08, 0.95 - 1.1 * t), 2),
        "haze_opacity": round(max(0.0, 0.45 - 0.9 * t), 2),
        "earth_bright": round(0.72 + 0.38 * t, 2),
        "droop": round((1 - t) * 60),
        "petal": _hex_lerp("#cfc4a9", "#ffffff", t),
        "leaf": _hex_lerp("#8a8f6a", "#3fae6a", t),
        "fire_opacity": round(max(0.0, (0.35 - t)) / 0.35 * 0.75, 2) if t < 0.35 else 0.0,
        "sway": t > 0.45,
    }


# ---------------------------------------------------------------------------
# Global theme + reactive wallpaper
# ---------------------------------------------------------------------------

def inject_theme(score=None):
    p = scene_params(score)
    hills = (
        "data:image/svg+xml;utf8,"
        "<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 1440 220' preserveAspectRatio='none'>"
        "<path d='M0 160 Q 240 80 480 150 T 960 140 T 1440 150 L 1440 220 L 0 220 Z' fill='%232E9E63' opacity='0.10'/>"
        "<path d='M0 190 Q 320 120 640 180 T 1440 175 L 1440 220 L 0 220 Z' fill='%231B5E3B' opacity='0.10'/>"
        "</svg>")
    st.markdown(f"""
    <style>
    .stApp {{
        background:
            linear-gradient(180deg, {p['sky_top']}26 0%, {p['sky_bottom']}59 45%, #ffffff 100%),
            #ffffff;
    }}
    .stApp::before {{
        content: ""; position: fixed; left: 0; right: 0; bottom: 0; height: 220px;
        background: url("{hills}") bottom / 100% 220px no-repeat;
        pointer-events: none; z-index: 0;
    }}
    section.main > div {{ position: relative; z-index: 1; }}

    h1, h2, h3 {{ color: {DEEP}; }}
    /* hide the "Press Enter to apply" hint — values apply on their own */
    div[data-testid="InputInstructions"] {{ display: none; }}
    .stButton > button, .stFormSubmitButton > button {{
        border-radius: 999px !important; border: 1.5px solid {GREEN}33;
        font-weight: 600;
    }}
    .stButton > button[kind="primary"], .stFormSubmitButton > button[kind="primary"] {{
        background: linear-gradient(135deg, {GREEN}, #46b87c); border: none;
    }}
    .stButton > button:disabled {{
        background: #eef2f0 !important; color: #9bb0a8 !important; border-color: #e3edea;
    }}
    div[data-testid="stVerticalBlockBorderWrapper"] {{
        background: rgba(255,255,255,0.88); border-radius: 18px;
        border: 1px solid #e3edea;
        box-shadow: 0 4px 18px rgba(27,94,59,0.07);
    }}
    section[data-testid="stSidebar"] {{
        background: linear-gradient(180deg, #ffffff 0%, {SOFT} 100%);
        border-right: 1px solid #e3edea;
    }}
    div[data-testid="stFileUploader"] section {{ border-radius: 14px; }}
    .impact-kpi {{
        background: #ffffff; border: 1px solid #e3edea; border-radius: 18px;
        padding: 1rem 1.2rem; box-shadow: 0 4px 16px rgba(27,94,59,0.06);
        height: 100%;
    }}
    .impact-kpi .t {{ font-size: .85rem; color: #5c7069; font-weight: 600;
                      letter-spacing: .02em; }}
    .impact-kpi .v {{ font-size: 1.9rem; font-weight: 800; color: {DEEP};
                      line-height: 1.15; }}
    .impact-kpi .u {{ font-size: .95rem; color: #5c7069; font-weight: 600; }}
    .impact-kpi .d-good {{ color: #1d8a4e; font-weight: 700; font-size: .9rem; }}
    .impact-kpi .d-bad {{ color: #c05621; font-weight: 700; font-size: .9rem; }}
    .impact-kpi .b {{ font-size: .78rem; color: #7d8f88; margin-top: .35rem; }}
    .conf-badge {{
        display: inline-block; padding: .1rem .55rem; border-radius: 999px;
        font-size: .72rem; font-weight: 700; letter-spacing: .03em;
    }}
    .conf-HIGH {{ background: #d9f2e3; color: #1d8a4e; }}
    .conf-MEDIUM {{ background: #fdf0d5; color: #b7791f; }}
    .conf-LOW, .conf-VERY.LOW, .conf-VERYLOW {{ background: #fde8e0; color: #c05621; }}
    .pill {{
        display:inline-block; padding:.25rem .8rem; border-radius:999px;
        background:{SOFT}; border:1px solid #e3edea; font-size:.85rem;
        margin: 0 .3rem .3rem 0; color:{DEEP}; font-weight:600;
    }}
    .story-card {{ border-left: 4px solid {GREEN}; padding-left: .9rem; }}
    .inline-label {{ padding-top: .45rem; font-weight: 600; color: #22423A; }}
    .wordmark {{ font-size: 1.5rem; font-weight: 800; color: {DEEP};
                 letter-spacing: -.02em; }}

    /* alternating dashboard bands: semi-transparent light green sections */
    div[class*="st-key-band"] {{
        background: rgba(46,158,99,0.09);
        border: 1px solid rgba(46,158,99,0.16);
        border-radius: 22px;
        padding: 1.1rem 1.25rem .6rem 1.25rem;
        backdrop-filter: blur(2px);
    }}
    div[class*="st-key-band"] div[data-testid="stVerticalBlockBorderWrapper"] {{
        background: rgba(255,255,255,0.85);
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
        border: 1.5px solid rgba(46,158,99,0.55) !important;
        border-radius: 12px !important;
        background: #ffffff !important;
        cursor: pointer;
        transition: border-color .15s ease, box-shadow .15s ease;
    }}
    div[data-baseweb="select"] > div:first-child:hover {{
        border-color: {GREEN} !important;
        box-shadow: 0 1px 6px rgba(46,158,99,0.18);
    }}
    div[data-baseweb="select"]:focus-within > div:first-child {{
        border-color: {GREEN} !important;
        box-shadow: 0 0 0 3px rgba(46,158,99,0.20) !important;
    }}
    div[data-baseweb="select"] input[readonly] {{ cursor: pointer; }}
    div[data-baseweb="select"] svg {{ color: {GREEN}; }}

    /* floating assistant button (green circle, white daisy) */
    .st-key-assistant_fab {{
        position: fixed; bottom: 26px; right: 26px; z-index: 999991;
        width: 64px;
    }}
    .st-key-assistant_fab button {{
        width: 64px; height: 64px; border-radius: 50% !important;
        border: none !important;
        background:
            url("data:image/svg+xml;utf8,<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 48 48'><g><ellipse cx='24' cy='11' rx='4.6' ry='9' fill='white'/><ellipse cx='24' cy='37' rx='4.6' ry='9' fill='white'/><ellipse cx='11' cy='24' rx='9' ry='4.6' fill='white'/><ellipse cx='37' cy='24' rx='9' ry='4.6' fill='white'/><ellipse cx='14.8' cy='14.8' rx='4.2' ry='8' transform='rotate(-45 14.8 14.8)' fill='white'/><ellipse cx='33.2' cy='33.2' rx='4.2' ry='8' transform='rotate(-45 33.2 33.2)' fill='white'/><ellipse cx='33.2' cy='14.8' rx='4.2' ry='8' transform='rotate(45 33.2 14.8)' fill='white'/><ellipse cx='14.8' cy='33.2' rx='4.2' ry='8' transform='rotate(45 14.8 33.2)' fill='white'/><circle cx='24' cy='24' r='7.2' fill='%23FFD966'/></g></svg>")
            center / 34px 34px no-repeat,
            linear-gradient(135deg, {GREEN}, #46b87c) !important;
        box-shadow: 0 10px 26px rgba(27,94,59,0.35);
        animation: fab-sway 4.5s ease-in-out infinite;
    }}
    .st-key-assistant_fab button:hover {{ transform: scale(1.06); }}
    .st-key-assistant_fab button p {{ display: none; }}
    @keyframes fab-sway {{
        0%, 100% {{ transform: rotate(-5deg); }}
        50% {{ transform: rotate(5deg); }}
    }}

    /* floating assistant panel */
    .st-key-assistant_panel {{
        position: fixed; bottom: 102px; right: 26px; z-index: 999991;
        width: 400px; max-width: 92vw;
    }}
    .st-key-assistant_panel > div[data-testid="stVerticalBlockBorderWrapper"] {{
        box-shadow: 0 18px 48px rgba(27,94,59,0.22);
        background: rgba(255,255,255,0.97);
    }}
    </style>
    """, unsafe_allow_html=True)


def confidence_badge(conf):
    if not conf:
        return ""
    cls = str(conf).replace(" ", "")
    return f"<span class='conf-badge conf-{cls}'>{conf} confidence</span>"


def kpi_card(icon_name, title, value, unit, delta_text=None, delta_good=True,
             benchmark_text=None, conf=None):
    delta_html = ""
    if delta_text:
        cls = "d-good" if delta_good else "d-bad"
        delta_html = f"<div class='{cls}'>{delta_text}</div>"
    bench_html = f"<div class='b'>{benchmark_text}</div>" if benchmark_text else ""
    return f"""
    <div class="impact-kpi">
      <div class="t">{icon(icon_name, 15, GREEN)} {title} {confidence_badge(conf)}</div>
      <div class="v">{value} <span class="u">{unit}</span></div>
      {delta_html}{bench_html}
    </div>"""


# ---------------------------------------------------------------------------
# Browser enhancements (embedded web component, runs once per page load)
# ---------------------------------------------------------------------------

def enhance_ui():
    # The component's iframe can be re-created whenever the sidebar re-renders,
    # which destroys listeners registered by the previous copy. So instead of
    # a run-once flag, every render tears down the prior installation and
    # re-installs from the live iframe realm.
    st_html("""<script>
(function () {
  const P = window.parent;
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
</script>""", height=0)


def scroll_to_anchor(anchor):
    """Scroll the app to a heading anchor (e.g. the Goals section) and keep
    re-asserting it briefly, because charts that finish laying out after the
    first scroll push the target back down."""
    st_html(f"""<script>
(function () {{
  const doc = window.parent.document;
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
</script>""", height=0)


def mini_mascot_svg(score, size=26):
    """Tiny Earth-and-daisy status indicator for the top-right user chip —
    derived from the SAME scene parameters as the full mascot so every
    surface tells one consistent story."""
    p = scene_params(score)
    return f"""
<svg width="{size}" height="{size}" viewBox="0 0 32 32" xmlns="http://www.w3.org/2000/svg">
  <circle cx="16" cy="20" r="11" fill="#2b7fb8" style="filter:brightness({p['earth_bright']})"/>
  <path d="M9 17 q4 -3 8 -1 q3 2 -1 5 q-5 3 -8 -1z" fill="#3fae6a"
        style="filter:brightness({p['earth_bright']})"/>
  <g transform="rotate({-p['droop'] * 0.7} 16 10)">
    <line x1="16" y1="10" x2="16" y2="4.5" stroke="{p['leaf']}" stroke-width="1.6"/>
    {"".join(f'<ellipse cx="16" cy="2.6" rx="1.5" ry="3" fill="{p["petal"]}" transform="rotate({a} 16 4.5)"/>' for a in range(0, 360, 45))}
    <circle cx="16" cy="4.5" r="1.9" fill="#FFD966"/>
  </g>
</svg>"""


def user_chip(user, score):
    """Compact fixed user-info chip in the top-right corner (§17).
    Order: mascot (environmental state) → username → avatar. The mascot is
    deliberately larger than the avatar so its state stays readable, and the
    two never swap roles."""
    import html as _html
    name = _html.escape(user["display_name"])
    st.markdown(
        f"<div class='impact-userchip'>"
        f"<span class='mascot'>{mini_mascot_svg(score, 34)}</span>"
        f"<span class='name' title='{name}'>{name}</span>"
        f"<span class='avatar'>{user['avatar']}</span></div>",
        unsafe_allow_html=True)


def scroll_top():
    """Scroll the app back to the top (used on page/step changes)."""
    st_html("""<script>
(function () {
  const doc = window.parent.document;
  const targets = [
    doc.querySelector('section[data-testid="stMain"]'),
    doc.querySelector('section.main'),
    doc.querySelector('div[data-testid="stAppViewContainer"]'),
    doc.scrollingElement,
  ];
  targets.forEach(t => { if (t && t.scrollTo) t.scrollTo({top: 0, left: 0, behavior: 'instant'}); });
})();
</script>""", height=0)


def celebrate():
    """Themed celebration: leaves and water droplets drift down — replaces
    st.balloons()."""
    st_html("""<script>
(function () {
  const doc = window.parent.document;
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
</script>""", height=0)


# ---------------------------------------------------------------------------
# Mascot: a daisy on a small Earth, reacting gradually to the score
# ---------------------------------------------------------------------------

def mascot_html(score, height=260, caption=True):
    p = scene_params(score)
    sway = ("daisy-sway 5s ease-in-out infinite alternate" if p["sway"]
            else "none")
    cap = ""
    if caption:
        s = int(score) if score is not None else "—"
        if score is None:
            mood_txt = "Complete an assessment to wake your daisy"
        else:
            mood_txt = ("Thriving — keep it up" if p["t"] >= 0.55 else
                        "Doing okay — small steps count" if p["t"] >= 0.40 else
                        "Your daisy needs you — one action at a time")
        cap = (f"<div style='text-align:center;font-family:sans-serif;"
               f"color:#1B5E3B;font-weight:700;font-size:14px'>Impact score: {s}/100"
               f"<div style='color:#5c7069;font-weight:600;font-size:12px'>{mood_txt}</div></div>")
    return f"""
<div style="width:100%;display:flex;flex-direction:column;align-items:center">
<style>
@keyframes daisy-sway {{ from {{ transform: rotate(-2.5deg); }} to {{ transform: rotate(2.5deg); }} }}
@keyframes cloud-drift {{ from {{ transform: translateX(-12px); }} to {{ transform: translateX(12px); }} }}
@keyframes sun-pulse {{ from {{ opacity: {max(0.05, p['sun_opacity'] - 0.15)}; }} to {{ opacity: {p['sun_opacity']}; }} }}
.mascot-svg * {{ transition: all 1.2s ease; }}
.cloud {{ animation: cloud-drift 9s ease-in-out infinite alternate; }}
.sunrays {{ animation: sun-pulse 4s ease-in-out infinite alternate; transform-origin: 60px 58px; }}
.daisy {{ transform-origin: 150px 178px; animation: {sway}; }}
</style>
<svg class="mascot-svg" viewBox="0 0 300 300" width="{height}" height="{height}" xmlns="http://www.w3.org/2000/svg" role="img" aria-label="Daisy mascot reflecting your impact">
  <defs>
    <linearGradient id="sky" x1="0" y1="0" x2="0" y2="1">
      <stop offset="0%" stop-color="{p['sky_top']}"/>
      <stop offset="100%" stop-color="{p['sky_bottom']}"/>
    </linearGradient>
    <radialGradient id="oceanG" cx="35%" cy="30%" r="80%">
      <stop offset="0%" stop-color="#7ec8e3"/>
      <stop offset="100%" stop-color="#2b7fb8"/>
    </radialGradient>
    <clipPath id="earthClip"><circle cx="150" cy="252" r="86"/></clipPath>
  </defs>

  <rect x="0" y="0" width="300" height="300" rx="24" fill="url(#sky)"/>

  <g class="sunrays" opacity="{p['sun_opacity']}">
    <circle cx="60" cy="58" r="22" fill="#FFD966"/>
    <g stroke="#FFD966" stroke-width="4" stroke-linecap="round">
      <line x1="60" y1="24" x2="60" y2="12"/><line x1="60" y1="104" x2="60" y2="92"/>
      <line x1="26" y1="58" x2="14" y2="58"/><line x1="106" y1="58" x2="94" y2="58"/>
      <line x1="36" y1="34" x2="27" y2="25"/><line x1="93" y1="91" x2="84" y2="82"/>
      <line x1="84" y1="34" x2="93" y2="25"/><line x1="27" y1="91" x2="36" y2="82"/>
    </g>
  </g>

  <g class="cloud" opacity="{p['cloud_opacity']}" fill="#ffffff">
    <ellipse cx="205" cy="52" rx="34" ry="14"/>
    <ellipse cx="228" cy="44" rx="24" ry="12"/>
    <ellipse cx="185" cy="44" rx="20" ry="11"/>
  </g>
  <g class="cloud" style="animation-delay:-4s" opacity="{min(0.95, p['cloud_opacity'] + 0.05)}" fill="#eef2f3">
    <ellipse cx="95" cy="112" rx="30" ry="12"/>
    <ellipse cx="117" cy="105" rx="20" ry="10"/>
  </g>

  <g style="filter: brightness({p['earth_bright']});">
    <circle cx="150" cy="252" r="86" fill="url(#oceanG)"/>
    <g clip-path="url(#earthClip)" fill="#3fae6a">
      <path d="M96 214 q20 -16 44 -8 q16 6 10 22 q-8 18 -30 14 q-26 -4 -24 -28z"/>
      <path d="M176 238 q24 -10 40 4 q12 12 2 26 q-14 16 -34 6 q-18 -10 -8 -36z"/>
      <path d="M128 268 q14 -8 26 0 q10 8 2 18 q-12 12 -26 4 q-12 -8 -2 -22z" fill="#57b97c"/>
    </g>
    <circle cx="150" cy="252" r="86" fill="none" stroke="#ffffff" stroke-opacity="0.55" stroke-width="3"/>
  </g>

  <g opacity="{p['fire_opacity']}">
    <path d="M84 214 q4 -12 10 -16 q-2 10 4 14 q6 -4 6 -12 q8 12 0 22 q-10 10 -20 -8z" fill="#ff9c54"/>
    <path d="M212 216 q3 -10 8 -13 q-1 8 3 11 q5 -3 5 -10 q7 10 0 18 q-8 8 -16 -6z" fill="#ffb27a"/>
  </g>

  <g class="daisy" transform="rotate({-p['droop']} 150 178)">
    <path d="M150 178 C 150 150, 146 132, 150 112" stroke="{p['leaf']}" stroke-width="6" fill="none" stroke-linecap="round"/>
    <path d="M150 150 q-16 -4 -22 -16 q16 -2 22 8z" fill="{p['leaf']}"/>
    <path d="M150 138 q16 -4 22 -16 q-16 -2 -22 8z" fill="{p['leaf']}"/>
    <g transform="rotate({-p['droop'] * 0.5} 150 108)">
      {"".join(f'<ellipse cx="150" cy="88" rx="9" ry="22" fill="{p["petal"]}" stroke="#e8e4d8" stroke-width="1" transform="rotate({a} 150 108)"/>' for a in range(0, 360, 30))}
      <circle cx="150" cy="108" r="14" fill="#FFD966" stroke="#eec643" stroke-width="2"/>
      <circle cx="145" cy="105" r="2.2" fill="#7a5c10"/>
      <circle cx="155" cy="105" r="2.2" fill="#7a5c10"/>
      <path d="M144 112 q6 {max(2, int(6 * p['t']))} 12 0" stroke="#7a5c10" stroke-width="2" fill="none" stroke-linecap="round"/>
    </g>
  </g>
</svg>
{cap}
</div>"""


def render_mascot(score, height=260, caption=True):
    st_html(mascot_html(score, height=height, caption=caption),
            height=height + (48 if caption else 8))


def score_ring(score, label="Impact score"):
    s = max(0, min(100, int(score)))
    p = scene_params(s)
    color = _hex_lerp("#c05621", "#1d8a4e", p["t"])
    circ = 2 * 3.14159 * 42
    dash = circ * s / 100
    return f"""
    <div style="text-align:center">
      <svg viewBox="0 0 100 100" width="110" height="110">
        <circle cx="50" cy="50" r="42" fill="none" stroke="#e8efec" stroke-width="10"/>
        <circle cx="50" cy="50" r="42" fill="none" stroke="{color}" stroke-width="10"
                stroke-linecap="round" stroke-dasharray="{dash:.1f} {circ:.1f}"
                transform="rotate(-90 50 50)"/>
        <text x="50" y="55" text-anchor="middle" font-size="24" font-weight="800"
              fill="{DEEP}" font-family="sans-serif">{s}</text>
      </svg>
      <div style="font-family:sans-serif;font-size:.8rem;color:#5c7069;font-weight:600">{label}</div>
    </div>"""
