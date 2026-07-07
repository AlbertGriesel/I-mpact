"""
Keyed, session-backed widget helpers.

Every assessment widget gets a stable `key` and is seeded from the assessment
data exactly once. This is the fix for jumpy number inputs: without stable
keys Streamlit derives widget identity from the parameters (including the
default value), so each edit created a brand-new widget and rapid +/- clicks
raced against stale instances, appearing to move the value backwards.

All keys share the `aw_` prefix so prefill / start-over can reset them in one
sweep (`clear_all`).
"""

import streamlit as st

PREFIX = "aw_"


def clear_all():
    """Forget all assessment widget state (used by prefill / start over /
    bill apply) so widgets reseed from the data dict."""
    for k in [k for k in st.session_state
              if isinstance(k, str) and k.startswith(PREFIX)]:
        del st.session_state[k]


def set_value(key, value):
    """Override one widget's state before it is instantiated this run
    (e.g. applying a confirmed bill extraction)."""
    st.session_state[PREFIX + key] = value


def _seed(key, value):
    if key not in st.session_state:
        st.session_state[key] = value


def number(label, key, current, *, minv=0.0, maxv=None, step=1.0,
           help=None, fmt="%g"):
    """Float number input with stable identity."""
    key = PREFIX + key
    cur = float(current) if current is not None else float(minv)
    cur = max(float(minv), cur if maxv is None else min(float(maxv), cur))
    _seed(key, cur)
    return st.number_input(
        label, min_value=float(minv),
        max_value=float(maxv) if maxv is not None else None,
        step=float(step), key=key, help=help, format=fmt)


def number_int(label, key, current, *, minv=0, maxv=None, step=1, help=None):
    key = PREFIX + key
    cur = int(current) if current is not None else int(minv)
    cur = max(int(minv), cur if maxv is None else min(int(maxv), cur))
    _seed(key, cur)
    return st.number_input(label, min_value=int(minv),
                           max_value=int(maxv) if maxv is not None else None,
                           step=int(step), key=key, help=help, format="%d")


def slider_int(label, key, current, *, minv, maxv, step=1, help=None):
    key = PREFIX + key
    cur = int(current) if current is not None else int(minv)
    _seed(key, max(minv, min(maxv, cur)))
    if not (minv <= st.session_state[key] <= maxv):
        st.session_state[key] = max(minv, min(maxv, st.session_state[key]))
    return st.slider(label, minv, maxv, step=step, key=key, help=help)


def slider_float(label, key, current, *, minv, maxv, step=0.5, help=None):
    key = PREFIX + key
    cur = float(current) if current is not None else float(minv)
    _seed(key, max(float(minv), min(float(maxv), cur)))
    if not (minv <= st.session_state[key] <= maxv):
        st.session_state[key] = max(float(minv), min(float(maxv),
                                                     st.session_state[key]))
    return st.slider(label, float(minv), float(maxv), step=float(step),
                     key=key, help=help)


def check(label, key, current, help=None):
    key = PREFIX + key
    _seed(key, bool(current))
    return st.checkbox(label, key=key, help=help)


def select(label, key, options, current, help=None):
    key = PREFIX + key
    _seed(key, current if current in options else options[0])
    if st.session_state[key] not in options:
        st.session_state[key] = options[0]
    return st.selectbox(label, options, key=key, help=help)


def radio(label, key, options, current, help=None, horizontal=True):
    key = PREFIX + key
    _seed(key, current if current in options else options[0])
    if st.session_state[key] not in options:
        st.session_state[key] = options[0]
    return st.radio(label, options, key=key, help=help, horizontal=horizontal)


def select_slider(label, key, options, current, help=None):
    key = PREFIX + key
    _seed(key, current if current in options else options[0])
    if st.session_state[key] not in options:
        st.session_state[key] = options[0]
    return st.select_slider(label, options, key=key, help=help)


def text(label, key, current, help=None, placeholder=None):
    key = PREFIX + key
    _seed(key, current or "")
    return st.text_input(label, key=key, help=help, placeholder=placeholder)
