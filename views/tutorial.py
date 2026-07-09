"""First-time product tour (spec §1 of the onboarding brief).

A lightweight, sequential coach-mark tour — NOT a modal wizard. It points at the
real navigation targets one hint at a time, dims the rest of the page slightly
with a spotlight, and can be skipped. It runs the JS entirely in the PARENT
document (Streamlit renders each component in an iframe) so the hints can point
at the sidebar links and the floating assistant.

Persistence:
  * signed-in users  — a `tutorial_done` flag in the DB (survives any browser),
  * everyone         — `localStorage` on the browser (survives sessions, and
                        stops the tour flashing between reruns),
  * the JS reports completion back to Python by clicking a hidden Streamlit
    button, which sets the DB flag (user) or a session flag (guest).

Targets are matched by STABLE selectors (sidebar hrefs + the assistant FAB key),
so a Streamlit rerun never breaks the tour.
"""

import json

import streamlit as st
from streamlit.components.v1 import html as st_html

import database as db

# (selector in the PARENT document, title, body) — one hint each, in order.
# `None` selector = a centred closing card with no spotlight.
_STEPS = [
    ('section[data-testid="stSidebar"] a[href*="assessment"]',
     "Start with your assessment",
     "Measure your water, electricity and carbon impact — as a guest, no "
     "account needed."),
    ('section[data-testid="stSidebar"] a[href*="chat"]',
     "Or talk it through",
     "Prefer talking to filling in forms? Complete the same assessment with "
     "the AI — same questions, same results."),
    ('section[data-testid="stSidebar"] a[href*="dashboard"]',
     "See your results",
     "Your dashboard shows your results, trends and biggest impact areas."),
    ('section[data-testid="stSidebar"] a[href*="goals"]',
     "Turn results into action",
     "Goals turns your results into practical weekly actions."),
    ('.st-key-assistant_fab button',
     "Ask the assistant anything",
     "Ask questions about your results, or get help improving your impact — "
     "any time, on any page."),
    ('section[data-testid="stSidebar"] a[href*="profile"]',
     "Watch your world grow",
     "Your avatar and its environment grow greener as your impact improves."),
    (None, "You're ready to explore",
     "That's the tour. Dive into your assessment whenever you like — you can "
     "always come back to any of these."),
]

# The tour JavaScript. Kept as a plain string (NO f-string) so the JS/CSS braces
# need no escaping; the step list is spliced in via a placeholder.
_TOUR_JS = r"""
<script>
(function () {
  const steps = __STEPS__;
  const doc = window.parent.document;
  const KEY = 'impact_tut_done';

  const syncDone = () => {
    const b = doc.querySelector('.st-key-tut_done button');
    if (b) b.click();
  };
  const finish = () => {
    try { localStorage.setItem(KEY, '1'); } catch (e) {}
    const ov = doc.getElementById('impact-tour');
    if (ov) ov.remove();
    syncDone();
  };

  // Already completed on this browser? sync Python state and stop.
  let seen = false;
  try { seen = localStorage.getItem(KEY) === '1'; } catch (e) {}
  if (seen) { syncDone(); return; }

  // Resume at the saved step if a rerun re-injected us mid-tour.
  let i = 0;
  try { i = parseInt(sessionStorage.getItem('impact_tut_step') || '0', 10) || 0; }
  catch (e) {}
  if (i < 0 || i >= steps.length) i = 0;

  const existing = doc.getElementById('impact-tour');
  if (existing) existing.remove();

  const ov = doc.createElement('div');
  ov.id = 'impact-tour';
  ov.innerHTML =
    '<div id="tut-ring"></div>' +
    '<div id="tut-card" role="dialog" aria-modal="false">' +
      '<div id="tut-step"></div>' +
      '<div id="tut-title"></div>' +
      '<div id="tut-text"></div>' +
      '<div id="tut-btns">' +
        '<button id="tut-skip" type="button">Skip</button>' +
        '<span style="flex:1"></span>' +
        '<button id="tut-back" type="button">Back</button>' +
        '<button id="tut-next" type="button"></button>' +
      '</div>' +
    '</div>';
  doc.body.appendChild(ov);

  const style = doc.createElement('style');
  style.textContent = `
    #impact-tour{position:fixed;inset:0;z-index:1000000;pointer-events:none;
      font-family:'Nunito',system-ui,sans-serif;}
    #tut-ring{position:absolute;border-radius:16px;border:3px solid #37B26F;
      box-shadow:0 0 0 9999px rgba(11,40,26,.30);
      transition:all .28s cubic-bezier(.34,1.3,.64,1);pointer-events:none;}
    #tut-card{position:absolute;width:300px;max-width:86vw;background:#fff;
      border:1.5px solid #cfe6d8;border-radius:18px;padding:16px 18px;
      box-shadow:0 20px 50px rgba(11,40,26,.34);pointer-events:auto;
      transition:top .28s ease,left .28s ease;}
    #tut-step{font-weight:800;font-size:.72rem;letter-spacing:.12em;
      text-transform:uppercase;color:#2E9E63;}
    #tut-title{font-family:'Baloo 2','Nunito',sans-serif;font-weight:800;
      font-size:1.18rem;color:#16342A;margin:.15rem 0 .3rem;line-height:1.1;}
    #tut-text{font-size:.98rem;color:#4c6155;line-height:1.45;}
    #tut-btns{display:flex;align-items:center;gap:.5rem;margin-top:1rem;}
    #tut-btns button{border-radius:999px;font-weight:800;
      font-family:'Nunito',sans-serif;font-size:.92rem;cursor:pointer;
      padding:.42rem .95rem;border:1.5px solid #cfe0d6;background:#fff;color:#2f6b4b;}
    #tut-skip{border:none;background:none;color:#8b978f;padding:.42rem .4rem;}
    #tut-next{background:linear-gradient(135deg,#35b26f,#59cd8c);color:#fff;
      border:none;box-shadow:0 5px 0 0 #1f8b52;}
    #tut-next:active{transform:translateY(3px);box-shadow:0 2px 0 0 #1f8b52;}
    #tut-back:disabled{opacity:.4;cursor:default;}
    @media (prefers-reduced-motion:reduce){#tut-ring,#tut-card{transition:none;}}
  `;
  ov.appendChild(style);

  const ring = ov.querySelector('#tut-ring');
  const card = ov.querySelector('#tut-card');
  const elStep = ov.querySelector('#tut-step');
  const elTitle = ov.querySelector('#tut-title');
  const elText = ov.querySelector('#tut-text');
  const bNext = ov.querySelector('#tut-next');
  const bBack = ov.querySelector('#tut-back');
  const bSkip = ov.querySelector('#tut-skip');

  function place() {
    const s = steps[i];
    elStep.textContent = 'Step ' + (i + 1) + ' of ' + steps.length;
    elTitle.textContent = s[1];
    elText.textContent = s[2];
    bNext.textContent = (i === steps.length - 1) ? 'Finish' : 'Next';
    bBack.disabled = (i === 0);

    const vw = window.parent.innerWidth, vh = window.parent.innerHeight;
    const target = s[0] ? doc.querySelector(s[0]) : null;
    const cw = 300, ch = card.offsetHeight || 172;

    if (target) {
      const r = target.getBoundingClientRect();
      const pad = 6;
      ring.style.display = 'block';
      ring.style.border = '3px solid #37B26F';
      ring.style.left = (r.left - pad) + 'px';
      ring.style.top = (r.top - pad) + 'px';
      ring.style.width = (r.width + pad * 2) + 'px';
      ring.style.height = (r.height + pad * 2) + 'px';
      let left = (r.left < vw / 2) ? (r.right + 16) : (r.left - cw - 16);
      left = Math.max(12, Math.min(left, vw - cw - 12));
      let top = r.top + r.height / 2 - ch / 2;
      top = Math.max(12, Math.min(top, vh - ch - 12));
      card.style.left = left + 'px';
      card.style.top = top + 'px';
    } else {
      ring.style.left = (vw / 2) + 'px'; ring.style.top = (vh / 2) + 'px';
      ring.style.width = '0px'; ring.style.height = '0px';
      ring.style.border = 'none';
      card.style.left = (vw / 2 - cw / 2) + 'px';
      card.style.top = Math.max(12, vh / 2 - ch / 2) + 'px';
    }
    try { sessionStorage.setItem('impact_tut_step', String(i)); } catch (e) {}
  }

  bNext.addEventListener('click', () => {
    if (i >= steps.length - 1) { finish(); return; }
    i++; place();
  });
  bBack.addEventListener('click', () => { if (i > 0) { i--; place(); } });
  bSkip.addEventListener('click', finish);
  window.parent.addEventListener('resize', place, { passive: true });

  place();
})();
</script>
"""


def _should_show(user):
    """True only for a genuine first-timer this account/session hasn't seen."""
    if user is not None:
        return not bool(user.get("tutorial_done"))
    return not st.session_state.get("tutorial_seen", False)


def render(user):
    """Render the tour (once) plus the hidden completion sink. Call once per
    run, after the sidebar and the floating assistant exist in the DOM."""
    if not _should_show(user):
        return

    # Hidden Streamlit button the JS clicks when the tour is finished/skipped.
    st.markdown(
        "<style>.st-key-tut_done{position:fixed!important;left:-9999px!important;"
        "top:-9999px!important;width:1px;height:1px;overflow:hidden;}</style>",
        unsafe_allow_html=True)
    with st.container(key="tut_done"):
        if st.button("done", key="tut_done_btn"):
            if user is not None:
                db.update_user(user["id"], tutorial_done=1)
                st.session_state["user"] = db.get_user(user["id"])
            st.session_state["tutorial_seen"] = True
            st.rerun()

    st_html(_TOUR_JS.replace("__STEPS__", json.dumps(_STEPS)), height=0)
