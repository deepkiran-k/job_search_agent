"""
views/history_view.py
Screen: "history" — two-tab dashboard showing a user's past
job searches and AI analysis runs.
"""
import json
import streamlit as st

from utils.history_manager import (
    load_analysis_history,
    load_search_history,
    delete_analysis_record,
    delete_search_record,
)
from views.components import topbar, score_color


# ── Score chip helper ─────────────────────────────────────────────────────────

def _score_chip(score) -> str:
    """Return an inline HTML chip coloured by ATS score."""
    try:
        s = int(score)
    except (TypeError, ValueError):
        return ""
    color = score_color(s)
    bg    = color + "22"    # semi-transparent background
    return (
        f'<span style="display:inline-block;padding:2px 10px;border-radius:20px;'
        f'font-size:0.75rem;font-weight:700;color:{color};background:{bg};'
        f'border:1px solid {color}44;">{s}%</span>'
    )


def _fmt_date(iso: str) -> str:
    """Format a SQLite datetime string to e.g. '04 May 2026 14:32'."""
    try:
        from datetime import datetime
        if not iso:
            return ""
        # Handle both space and 'T' separators
        if " " in iso:
            dt = datetime.strptime(iso.split(".")[0], "%Y-%m-%d %H:%M:%S")
        elif "T" in iso:
            dt = datetime.strptime(iso.split(".")[0], "%Y-%m-%dT%H:%M:%S")
        else:
            dt = datetime.fromisoformat(iso)
        return dt.strftime("%d %b %Y %H:%M")
    except Exception:
        return iso or ""


# ── Main render ───────────────────────────────────────────────────────────────

def render() -> None:
    """Render the history dashboard."""
    topbar("history")

    user_id = st.session_state.get("user_id")
    if not user_id:
        st.warning("Please log in to view your history.")
        return

    st.markdown("## 📋 My History")
    st.markdown(
        '<div style="color:var(--muted);font-size:0.88rem;margin-bottom:1.25rem;">'
        'Your saved searches and AI analyses are shown below.</div>',
        unsafe_allow_html=True,
    )

    analysis_tab, search_tab = st.tabs(["📊 Analysis History", "🔍 Search History"])

    # ── ANALYSIS HISTORY ──────────────────────────────────────────────────────
    with analysis_tab:
        records = load_analysis_history(user_id)

        if not records:
            st.info("No analyses yet. Run your first ATS analysis to see it here.")
        else:
            for rec in records:
                _render_analysis_card(rec, user_id)

    # ── SEARCH HISTORY ────────────────────────────────────────────────────────
    with search_tab:
        searches = load_search_history(user_id)

        if not searches:
            st.info("No searches yet. Your job searches will appear here automatically.")
        else:
            for srec in searches:
                _render_search_row(srec, user_id)


# ── Card renderers ────────────────────────────────────────────────────────────

def _render_analysis_card(rec: dict, user_id: str) -> None:
    rec_id   = rec["id"]
    chip     = _score_chip(rec.get("ats_score"))
    date_str = _fmt_date(rec.get("created_at", ""))

    company  = rec.get("job_company", "") or ""
    location = rec.get("job_location", "") or ""
    meta     = f"{company} · {location}" if company and location else (company or location)

    # Badge HTML (inline spans — safe in all Streamlit versions)
    badges = chip
    if rec.get("has_cover_letter"):
        badges += '&nbsp;<span class="tag tag-blue" style="font-size:0.68rem;">&#128203; Cover Letter</span>'
    if rec.get("has_tailored_resume"):
        badges += '&nbsp;<span class="tag tag-green" style="font-size:0.68rem;">&#10024; Tailored Resume</span>'

    # Card shell — simple box, no flex
    st.markdown(
        f'<div class="card" style="margin-bottom:0.65rem;padding:0.85rem 1.1rem;">'
        f'<div style="font-size:0.95rem;font-weight:700;color:var(--text);">{rec.get("job_title","Unknown Role")}</div>'
        f'<div style="font-size:0.8rem;color:var(--muted);margin-top:2px;">{meta}</div>'
        f'<div style="margin-top:6px;">{badges}</div>'
        f'<div style="font-size:0.72rem;color:var(--muted2);margin-top:6px;">{date_str}</div>'
        f'</div>',
        unsafe_allow_html=True,
    )

    btn_col1, btn_col2, btn_col3, _ = st.columns([1, 1, 0.6, 3])
    with btn_col1:
        if st.button("View Results", key=f"view_{rec_id}", use_container_width=True):
            _restore_analysis(rec)
    with btn_col2:
        if st.button("Re-score", key=f"rescore_{rec_id}", use_container_width=True):
            _restore_for_rescore(rec)
    with btn_col3:
        if st.button("🗑", key=f"del_a_{rec_id}", use_container_width=True):
            delete_analysis_record(rec_id, user_id)
            st.rerun()

    st.markdown(
        '<div style="border-bottom:1px solid var(--border);margin:0.5rem 0 1rem;"></div>',
        unsafe_allow_html=True,
    )



def _render_search_row(srec: dict, user_id: str) -> None:
    rec_id = srec["id"]
    mode   = srec.get("search_mode", "role")

    if mode == "company" and srec.get("company_name"):
        query = f"🏢 {srec['company_name']}"
        if srec.get("job_title"):
            query += f" — {srec['job_title']}"
    else:
        query = f"🔍 {srec.get('job_title', '(no title)')}"

    meta_parts = []
    if srec.get("country"):
        meta_parts.append(srec["country"].upper())
    if srec.get("experience"):
        meta_parts.append(srec["experience"])
    meta = " · ".join(meta_parts)

    results_count = srec.get("results_count", 0)
    date_str      = _fmt_date(srec.get("created_at", ""))

    st.markdown(f"""
    <div class="card" style="margin-bottom:0.5rem;padding:0.75rem 1.1rem;">
      <div style="display:flex;justify-content:space-between;align-items:center;flex-wrap:wrap;gap:0.4rem;">
        <div>
          <div style="font-size:0.9rem;font-weight:700;color:var(--text);">{query}</div>
          <div style="font-size:0.75rem;color:var(--muted);margin-top:2px;">
            {meta}
            {(" &nbsp;·&nbsp; " + str(results_count) + " results") if results_count is not None else ""}
          </div>
        </div>
        <div style="font-size:0.72rem;color:var(--muted2);">{date_str}</div>
      </div>
    </div>
    """, unsafe_allow_html=True)

    btn_col1, btn_col2, _ = st.columns([1.2, 0.5, 4])

    with btn_col1:
        if st.button("Search Again", key=f"sa_{rec_id}", use_container_width=True):
            _trigger_search_again(srec)

    with btn_col2:
        if st.button("🗑", key=f"del_s_{rec_id}", use_container_width=True):
            delete_search_record(rec_id, user_id)
            st.rerun()

    st.markdown('<div style="border-bottom:1px solid var(--border);margin:0.3rem 0 0.75rem;opacity:0.5;"></div>',
                unsafe_allow_html=True)


# ── Session-state restorers ───────────────────────────────────────────────────

def _build_job_dict(rec: dict) -> dict:
    """Reconstruct a minimal job dict from a stored analysis record."""
    return {
        "title":    rec.get("job_title", ""),
        "company":  rec.get("job_company", ""),
        "location": rec.get("job_location", ""),
        "url":      rec.get("job_url", ""),
        "source":   rec.get("job_source", ""),
    }


def _restore_analysis(rec: dict) -> None:
    """Restore all session state from a stored record and jump to results."""
    analysis = {}
    try:
        analysis = json.loads(rec.get("analysis_json") or "{}")
    except Exception:
        pass

    st.session_state.selected_job    = _build_job_dict(rec)
    st.session_state.analysis        = analysis
    st.session_state.cover_letter    = rec.get("cover_letter") or ""
    st.session_state.tailored_resume = rec.get("tailored_resume") or ""
    st.session_state.tailored_ats    = analysis.get("tailored_ats")
    st.session_state.ai_limit_hit    = False
    st.session_state.step            = "results"
    st.rerun()


def _restore_for_rescore(rec: dict) -> None:
    """Pre-fill the job context and jump to the analyze screen."""
    st.session_state.selected_job    = _build_job_dict(rec)
    st.session_state.job_title       = rec.get("search_job_title", "")
    st.session_state.company_name    = rec.get("search_company", "")
    st.session_state.location        = rec.get("search_location", "")
    st.session_state.country         = rec.get("search_country", "us")
    st.session_state.experience      = rec.get("search_experience", "3-5 years")
    st.session_state.search_mode     = rec.get("search_mode", "role")
    st.session_state.analysis        = None
    st.session_state.cover_letter    = ""
    st.session_state.tailored_resume = ""
    st.session_state.tailored_ats    = None
    st.session_state.step            = "analyze"
    st.rerun()


def _trigger_search_again(srec: dict) -> None:
    """Pre-fill search params from a search_history record and trigger a new search."""
    st.session_state.job_title    = srec.get("job_title", "")
    st.session_state.company_name = srec.get("company_name", "")
    st.session_state.location     = srec.get("location", "")
    st.session_state.country      = srec.get("country", "us")
    st.session_state.experience   = srec.get("experience", "3-5 years")
    st.session_state.search_mode  = srec.get("search_mode", "role")
    st.session_state.jobs         = []
    st.session_state.selected_job = None
    st.session_state.analysis     = None
    st.session_state.cover_letter = ""
    st.session_state.tailored_resume = ""
    st.session_state.tailored_ats = None
    st.session_state.error        = None
    st.session_state.searching    = True
    st.session_state.step         = "search"
    st.rerun()
