"""
AI Job Search Agent — JobOrbit AI
Streamlit application entry point (orchestrator).

Pipeline: Search → Select Job → Analyse (ATS + Cover Letter + optional Tailoring)
All screen rendering is delegated to views/ modules for maintainability.
"""
import os
import asyncio

try:
    asyncio.get_running_loop()
except RuntimeError:
    try:
        asyncio.get_event_loop()
    except RuntimeError:
        asyncio.set_event_loop(asyncio.new_event_loop())

import streamlit as st

# ── Page config — must be the very first Streamlit call ──────────────────────
_sidebar_state = (
    "expanded"
    if st.session_state.get("step") in ["select_job", "analyze", "results"]
    else "collapsed"
)
st.set_page_config(
    page_title="JobOrbit AI",
    page_icon="🟢",
    layout="wide",
    initial_sidebar_state=_sidebar_state,
)

# ── Core settings (after set_page_config) ────────────────────────────────────
from core.settings import settings  # noqa: E402

# ── CSS + shared component helpers ───────────────────────────────────────────
from views.components import (  # noqa: E402
    inject_css, APP_DEFAULTS, COUNTRY_OPTIONS, reset_app_state, profile_avatar,
)

inject_css()

# ── DB bootstrap (idempotent, runs once per server process) ─────────────────
from utils.db import init_db  # noqa: E402
init_db()

# ── Session state initialisation ─────────────────────────────────────────────
for key, default in APP_DEFAULTS.items():
    if key not in st.session_state:
        st.session_state[key] = default

# ── Restore session from URL params (avatar dropdown navigation) ──────────────
# The profile dropdown uses href="?action=X&_uid=...&_ue=..." so that the
# user_id survives the browser navigation that would otherwise wipe session state.
if not st.session_state.get("user_id"):
    import urllib.parse as _urlparse
    if hasattr(st, "query_params"):
        _raw_uid = st.query_params.get("_uid", "")
        _raw_ue  = st.query_params.get("_ue",  "")
    else:
        _qp_exp  = st.experimental_get_query_params()
        _raw_uid = (_qp_exp.get("_uid") or [""])[0]
        _raw_ue  = (_qp_exp.get("_ue")  or [""])[0]
    if _raw_uid:
        st.session_state.user_id    = _urlparse.unquote(_raw_uid)
        st.session_state.user_email = _urlparse.unquote(_raw_ue)

# ── Auth gate ─────────────────────────────────────────────────────────────────
if not st.session_state.get("user_id"):
    from views.auth_view import render as _auth_render  # noqa: E402
    _auth_render()
    st.stop()  # Everything below is protected

# ── Profile avatar query-param actions ────────────────────────────────────────
if hasattr(st, "query_params"):
    _action = st.query_params.get("action")
else:
    _params = st.experimental_get_query_params()
    _action = (_params.get("action") or [None])[0]

if _action == "history":
    if hasattr(st, "query_params"):
        st.query_params.clear()
    else:
        st.experimental_set_query_params()
    st.session_state.step = "history"
elif _action == "logout":
    if hasattr(st, "query_params"):
        st.query_params.clear()
    else:
        st.experimental_set_query_params()
    st.session_state.user_id    = None
    st.session_state.user_email = ""
    st.rerun()
elif not _action:
    # Clean up any leftover _uid/_ue params from the URL after restore
    if hasattr(st, "query_params") and st.query_params.get("_uid"):
        st.query_params.clear()
    elif not hasattr(st, "query_params"):
        _qp2 = st.experimental_get_query_params()
        if _qp2.get("_uid"):
            st.experimental_set_query_params()

# ── Profile avatar (fixed-position, visible on every page) ────────────────────
profile_avatar()


# ── Sidebar (rendered on all steps except the initial hero search) ────────────
search_clicked = False
if st.session_state.step != "search":
    with st.sidebar:
        st.markdown("## 🔍 Filters")
        st.markdown('<hr style="margin:0.4rem 0 1rem;">', unsafe_allow_html=True)

        # ── Search mode toggle ───────────────────────────────────────────────────
        _current_mode = st.session_state.get("search_mode", "role")
        sb_mode_col1, sb_mode_col2 = st.columns(2)
        with sb_mode_col1:
            if st.button(
                "🔍 By Role",
                key="sb_mode_role",
                type="primary" if _current_mode == "role" else "secondary",
                use_container_width=True,
            ):
                st.session_state.search_mode = "role"
                st.rerun()
        with sb_mode_col2:
            if st.button(
                "🏢 By Co.",
                key="sb_mode_company",
                type="primary" if _current_mode == "company" else "secondary",
                use_container_width=True,
            ):
                st.session_state.search_mode = "company"
                st.rerun()

        st.markdown('<div style="margin-bottom:0.25rem;"></div>', unsafe_allow_html=True)

        # ── Mode-specific inputs ───────────────────────────────────────────────
        if _current_mode == "company":
            company_name_input = st.text_input(
                "Company Name",
                value=st.session_state.get("company_name", ""),
                placeholder="e.g. Google, BASF...",
            )
            job_title_input = st.text_input(
                "Role / Keyword *(optional)*",
                value=st.session_state.job_title,
                placeholder="e.g. Software Engineer",
            )
        else:
            company_name_input = ""
            job_title_input = st.text_input(
                "Job Title", value=st.session_state.job_title,
                placeholder="e.g. Data Scientist",
            )

        location_input   = st.text_input("Location",   value=st.session_state.location,
                                         placeholder="e.g. London, Remote")
        _c_options = list(COUNTRY_OPTIONS.keys())
        _c_idx = (
            _c_options.index(st.session_state.get("country", "us"))
            if st.session_state.get("country", "us") in _c_options else 0
        )
        country_code     = st.selectbox(
            "Country", options=_c_options,
            format_func=lambda x: COUNTRY_OPTIONS[x], index=_c_idx,
        )
        experience_input = st.selectbox(
            "Experience Level",
            ["0-1 years", "1-3 years", "3-5 years", "5-10 years", "10+ years"],
            index=["0-1 years", "1-3 years", "3-5 years", "5-10 years", "10+ years"]
            .index(st.session_state.experience),
        )

        search_clicked = st.button(
            "Search Again", type="primary", use_container_width=True,
            disabled=st.session_state.searching,
        )

        if st.button("New Search", use_container_width=True):
            reset_app_state()
            st.rerun()

        st.markdown('<hr style="margin:0.75rem 0;">', unsafe_allow_html=True)

        # ── Status ─────────────────────────────────────────────────────────────────
        status_map = {
            "select_job": ("Pick a job to analyse", "#16A34A"),
            "analyze":    ("Upload your resume",    "#D97706"),
            "results":    ("Analysis complete ✓",   "#16A34A"),
        }
        lbl, clr = status_map.get(st.session_state.step, ("Ready", "#7BA88C"))
        st.markdown(
            f'<div style="font-size:0.85rem;font-weight:600;color:{clr};padding:0.25rem 0;">{lbl}</div>',
            unsafe_allow_html=True,
        )

        if st.session_state.selected_job:
            j = st.session_state.selected_job
            st.markdown(f"""
            <div class="card" style="padding:0.7rem 1rem;margin-top:0.75rem;">
              <div class="eyebrow">Selected job</div>
              <div style="font-size:0.87rem;font-weight:700;color:var(--text);margin-top:3px;">{j.get('title','')}</div>
              <div style="font-size:0.78rem;color:var(--muted);">{j.get('company','')}</div>
            </div>""", unsafe_allow_html=True)

        st.markdown(
            '<div style="font-size:0.7rem;color:var(--muted2);text-align:center;margin-top:1.5rem;">Powered by AI</div>',
            unsafe_allow_html=True,
        )
else:
    # Provide variable bindings for the search-again trigger below
    job_title_input    = st.session_state.job_title
    company_name_input = st.session_state.get("company_name", "")
    location_input     = st.session_state.location
    country_code       = st.session_state.get("country", "us")
    experience_input   = st.session_state.experience

# ── Search-again trigger from sidebar ────────────────────────────────────────
if search_clicked:
    st.session_state.job_title       = job_title_input
    st.session_state.company_name    = company_name_input
    st.session_state.location        = location_input
    st.session_state.experience      = experience_input
    st.session_state.country         = country_code
    st.session_state.jobs            = []
    st.session_state.selected_job    = None
    st.session_state.analysis        = None
    st.session_state.cover_letter    = ""
    st.session_state.tailored_resume = ""
    st.session_state.tailored_ats    = None
    st.session_state.error           = None
    st.session_state.searching       = True
    st.rerun()

# ── Route to the correct view module ─────────────────────────────────────────
from views.search_view   import handle_search_trigger, render as _search_render    # noqa: E402
from views.job_list_view import render as _job_list_render                          # noqa: E402
from views.analyze_view  import render as _analyze_render                           # noqa: E402
from views.results_view  import render as _results_render                           # noqa: E402

handle_search_trigger()   # executes search if st.session_state.searching is True

step = st.session_state.step
if step == "search":
    _search_render()
elif step == "select_job":
    _job_list_render()
elif step == "analyze":
    _analyze_render()
elif step == "results":
    _results_render()
elif step == "history":
    from views.history_view import render as _history_render  # noqa: E402
    _history_render()
