"""Community (§19), as two clear destinations under one sidebar group:

* Leaderboard — one ranked list of members with public stats and medals.
* Explore — search and browse member profile cards, open public profiles
  and published stories.

Privacy model (unchanged): profile visibility and story publication are
SEPARATE consents. A deliberately published story stays viewable even when
the author's profile is private — but a private profile exposes nothing
beyond that story and its consented stats snapshot."""

import json

import streamlit as st

import database as db
import avatar as av
from views.common import current_user
from visuals import pill, icon, score_ring, env_tier


def _face(u, size=34, animate=False, halo=False, score=None):
    """Inline Sprout for community lists/dialogs (replaces the old emoji)."""
    return av.svg(av.config_from_user(u), tier=env_tier(score), size=size,
                  animate=animate, halo=halo)

def _fmt_improvement(v):
    """Direction-aware, no double negatives (brief §14): a positive value is a
    reduction (good), a negative value is an increase (worse)."""
    if v >= 0:
        return f"↓ {abs(v):.0f}% lower impact"
    return f"↑ {abs(v):.0f}% higher impact"


_RANKS = {
    "Improvement": ("improvement", True, _fmt_improvement,
                    "Net-carbon change since first assessment — higher "
                    "reduction is better."),
    "Impact score": ("score", True, lambda v: f"{v:.0f}",
                     "Composite score vs labelled benchmarks (higher is "
                     "better; 50 ≈ average, 100 = net zero). Context, not a "
                     "race — improvement is the fairest comparison."),
    "Goal completion": ("goal_rate", True, lambda v: f"{v:.0f}%",
                        "Share of weekly goals completed."),
    "Streaks": ("streak", True, lambda v: f"{v:.0f}",
                "Consecutive check-ins at each member's own cadence."),
}
_MEDAL_COLORS = ["#D4A017", "#9aa3ad", "#B0713C"]


def _member_rows():
    rows = []
    for u in db.community_members():
        assessments = db.list_assessments(u["id"])
        stories = db.stories_by_user(u["id"]) if u["story_consent"] else []
        is_public = u["privacy"] == "public"
        if not assessments and not stories:
            continue
        fields = set(json.loads(u["public_fields"] or "[]")) if is_public else set()
        row = {"user": u, "is_public": is_public, "fields": fields,
               "stories": stories, "improvement": None, "score": None,
               "goal_rate": None, "streak": None, "latest": None,
               "assessments": len(assessments)}
        if is_public and assessments:
            first = assessments[0]["results"]["carbon"]["net_co2e_kg_year"]
            last = assessments[-1]["results"]["carbon"]["net_co2e_kg_year"]
            if first > 0 and len(assessments) > 1:
                row["improvement"] = (first - last) / first * 100
            row["score"] = assessments[-1]["results"]["score"]["total"]
            row["latest"] = assessments[-1]["results"]
            gs = db.goal_stats(u["id"])
            row["goal_rate"] = gs["rate"]
            row["streak"] = db.get_streak(u["id"])["current"]
        rows.append(row)
    return rows


@st.dialog("Community story")
def _story_dialog(story, author):
    st.markdown(f"### {story['title']}")
    st.markdown(
        f"<div style='display:flex;align-items:center;gap:.4rem'>"
        f"{_face(author, 26)}<span style='color:#5c7069;font-size:.9rem'>by "
        f"{author['display_name']} · {story.get('period') or ''}</span></div>",
        unsafe_allow_html=True)
    st.markdown(f"**The challenge:** {story['challenge']}")
    st.markdown(f"**What they did:** {story['actions']}")
    stats = story.get("stats") or {}
    if stats.get("electricity_reduction_percent"):
        st.markdown(pill(
            f"Verified in-app: electricity down "
            f"{abs(stats['electricity_reduction_percent'])}% "
            f"({stats.get('from_kwh_month', '?')} → "
            f"{stats.get('to_kwh_month', '?')} kWh/month)", "check"),
            unsafe_allow_html=True)
    if author["privacy"] != "public":
        st.caption("This member's profile is private — they chose to share "
                   "this story only.")


@st.dialog("Member profile")
def _profile_dialog(row):
    u = row["user"]
    st.markdown(f"<div style='display:flex;justify-content:center'>"
                f"{_face(u, 96, animate=True, halo=True, score=row.get('score'))}"
                f"</div>", unsafe_allow_html=True)
    st.markdown(f"<div style='text-align:center;font-weight:800;"
                f"font-size:1.2rem;color:#1B5E3B'>{u['display_name']}</div>",
                unsafe_allow_html=True)
    if not row["is_public"]:
        st.info("This profile is private. Only their published stories are "
                "shared with the community.")
    else:
        fields, latest = row["fields"], row["latest"]
        if "score" in fields and row["score"] is not None:
            st.markdown(score_ring(row["score"]), unsafe_allow_html=True)
        pills = []
        if row["improvement"] and row["improvement"] > 0:
            pills.append(pill(f"{row['improvement']:.0f}% lower carbon since "
                              "joining", "trend-down"))
        if "streak" in fields and row["streak"] is not None:
            pills.append(pill(f"{row['streak']} streak", "flame"))
        if latest and "water" in fields:
            pills.append(pill(f"{latest['water']['water_litres_person_day']:.0f}"
                              " L/p/day", "water"))
        if latest and "electricity" in fields:
            pills.append(pill(f"{latest['electricity']['total_electricity_kwh_month']:.0f}"
                              " kWh/m", "bolt"))
        if latest and "carbon" in fields:
            pills.append(pill(f"{latest['carbon']['net_co2e_kg_year']:,.0f}"
                              " kg CO₂e/yr", "cloud"))
        if "achievements" in fields:
            n = len(db.get_achievements(u["id"]))
            pills.append(pill(f"{n} badges", "trophy"))
        st.markdown("".join(pills) or pill("Sharing soon…"),
                    unsafe_allow_html=True)
    for s in row["stories"]:
        if st.button(f"Read story: {s['title']}", key=f"pstory_{s['id']}",
                     use_container_width=True):
            st.session_state["community_open_story"] = s["id"]
            st.rerun()


def _handle_open_story(rows):
    """Deferred story open (a profile dialog can queue one before closing)."""
    open_story = st.session_state.pop("community_open_story", None)
    if open_story:
        for row in rows:
            for s in row["stories"]:
                if s["id"] == open_story:
                    _story_dialog(s, row["user"])


def _member_pills(row):
    """The public-safe badge set used on list rows and Explore cards."""
    pills = []
    if row["stories"]:
        pills.append(pill("Story", "file"))
    if row["is_public"] and "streak" in row["fields"] and row["streak"]:
        pills.append(pill(f"{row['streak']} streak", "flame"))
    if row["is_public"] and "achievements" in row["fields"]:
        n = len(db.get_achievements(row["user"]["id"]))
        if n:
            pills.append(pill(f"{n} badges", "trophy"))
    if not row["is_public"]:
        pills.append(pill("Private profile", "lock"))
    return pills


# =============================== Leaderboard ===============================

def render_leaderboard():
    st.title("Leaderboard")
    st.caption("Real households, real progress — everyone here chose what "
               "to share.")

    rows = _member_rows()
    if not rows:
        st.info("Nobody has opted in yet. Turn on a public profile — or "
                "publish a story — under Settings.")
        return

    _handle_open_story(rows)

    # a comfortable, responsive width — not a full-page empty box
    sel, _spacer = st.columns([1.15, 2.85])
    rank_name = sel.selectbox("Rank by", list(_RANKS), key="community_rank")
    key, fmt, note = (_RANKS[rank_name][0], _RANKS[rank_name][2],
                      _RANKS[rank_name][3])

    ranked = sorted([r for r in rows if r.get(key) is not None],
                    key=lambda r: r[key], reverse=True)
    story_only = [r for r in rows if r.get(key) is None and r["stories"]]

    for i, row in enumerate(ranked + story_only):
        u = row["user"]
        with st.container(border=True):
            c1, c2, c3, c4 = st.columns([0.5, 2.6, 1.6, 1.1])
            with c1:
                # Rank number derives from the current sorted order, so it
                # updates whenever Rank By / sorting changes (§3). Top 3 get a
                # subtle medal badge; the rest get a plain number; unranked
                # (story-only) members show a dash.
                if row.get(key) is not None:
                    rank = i + 1
                    if rank <= 3:
                        c = _MEDAL_COLORS[rank - 1]
                        st.markdown(
                            f"<div style='display:flex;align-items:center;"
                            f"justify-content:center;width:34px;height:34px;"
                            f"border-radius:50%;background:{c}22;"
                            f"border:2px solid {c};color:{c};font-weight:800;"
                            f"font-size:1rem'>{rank}</div>",
                            unsafe_allow_html=True)
                    else:
                        st.markdown(
                            f"<div style='width:34px;text-align:center;"
                            f"font-weight:800;color:#7d8f88;font-size:1.05rem'>"
                            f"{rank}</div>", unsafe_allow_html=True)
                else:
                    st.markdown(
                        "<div style='width:34px;text-align:center;"
                        "color:#c3cdc8' title='Not ranked — shared a story "
                        "only'>—</div>", unsafe_allow_html=True)
            with c2:
                st.markdown(
                    f"<div style='display:flex;align-items:center;gap:.5rem'>"
                    f"{_face(u, 34, score=row.get('score'))}"
                    f"<span style='font-weight:800;color:#1B5E3B'>"
                    f"{u['display_name']}</span></div>", unsafe_allow_html=True)
                st.markdown("".join(_member_pills(row)),
                            unsafe_allow_html=True)
            with c3:
                if row.get(key) is not None:
                    st.markdown(f"### {fmt(row[key])}")
            with c4:
                if st.button("View", key=f"member_{u['id']}",
                             use_container_width=True):
                    _profile_dialog(row)
                if row["stories"] and st.button(
                        "Story", key=f"story_{u['id']}",
                        use_container_width=True, type="primary"):
                    _story_dialog(row["stories"][0], u)
    st.caption(note)


# ================================= Explore =================================

def render_explore():
    st.title("Explore the community")
    st.caption("Find members and see what they've chosen to share — public "
               "stats and published stories only.")

    rows = _member_rows()
    if not rows:
        st.info("Nobody has opted in yet. Turn on a public profile — or "
                "publish a story — under Settings.")
        return

    _handle_open_story(rows)

    sc, _spacer = st.columns([1.6, 2.4])
    query = sc.text_input(
        "Search members", key="explore_search",
        placeholder="Search by name…",
        help="Matches display names of members with a public presence.")

    q = (query or "").strip().lower()
    matches = [r for r in rows
               if q in r["user"]["display_name"].lower()] if q else rows

    if q and not matches:
        st.info(f'No members match "{query.strip()}". Try a shorter part of '
                "the name — only members with a public profile or a "
                "published story appear here.")
    elif q:
        st.caption(f"{len(matches)} member{'s' if len(matches) != 1 else ''} "
                   f"match your search.")

    cols = st.columns(3)
    for i, row in enumerate(matches):
        u = row["user"]
        with cols[i % 3], st.container(border=True):
            st.markdown(
                f"<div style='display:flex;align-items:center;gap:.6rem'>"
                f"{_face(u, 40, score=row.get('score'))}"
                f"<span style='font-weight:800;color:#1B5E3B;"
                f"overflow:hidden;text-overflow:ellipsis;white-space:nowrap'>"
                f"{u['display_name']}</span></div>",
                unsafe_allow_html=True)
            if row["is_public"] and "score" in row["fields"] \
                    and row["score"] is not None:
                st.markdown(pill(f"Impact score {row['score']:.0f}/100",
                                 "chart"), unsafe_allow_html=True)
            st.markdown("".join(_member_pills(row)) or
                        pill("Sharing soon…"), unsafe_allow_html=True)
            if st.button("View profile", key=f"explore_{u['id']}",
                         use_container_width=True):
                _profile_dialog(row)

    # ------------------------------------------------------- share a story
    st.divider()
    with st.expander("Share your own story"):
        user = current_user()
        if not user:
            st.info("Stories are linked to an account — sign in to share "
                    "yours.")
            return
        st.caption("Publishing a story is a separate consent from a public "
                   "profile — your story can be shared even if your profile "
                   "stays private, and it exposes only what you write here "
                   "plus the verified stats snapshot.")
        with st.form("story_form"):
            title = st.text_input("Story title",
                                  placeholder="How we tamed the geyser")
            challenge = st.text_area("What was the challenge?")
            actions = st.text_area("What did you actually do? (practical "
                                   "lessons and honest obstacles welcome)")
            period = st.text_input("Over what period?", placeholder="3 months")
            consent = st.checkbox(
                "I consent to publishing this story to the community "
                "(withdrawable in Settings).")
            submitted = st.form_submit_button("Publish story", type="primary")
        if submitted:
            if not (title and challenge and actions):
                st.error("Please fill in the title, challenge and actions.")
            elif not consent:
                st.error("Please tick the consent box to publish.")
            else:
                assessments = db.list_assessments(user["id"])
                stats = {}
                if len(assessments) >= 2:
                    f_kwh = assessments[0]["results"]["electricity"]["total_electricity_kwh_month"]
                    l_kwh = assessments[-1]["results"]["electricity"]["total_electricity_kwh_month"]
                    if f_kwh > 0 and l_kwh < f_kwh:
                        stats = {"electricity_reduction_percent":
                                 round((f_kwh - l_kwh) / f_kwh * 100),
                                 "from_kwh_month": f_kwh, "to_kwh_month": l_kwh}
                db.update_user(user["id"], story_consent=1)
                db.save_story(user["id"], title, challenge, actions, period,
                              True, stats)
                st.success("Published — thank you for inspiring others.")
                st.rerun()
