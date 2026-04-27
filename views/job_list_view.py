"""
views/job_list_view.py
Screen 2 — Job listings grid with HTML-safe rendering.

All job fields fetched from external APIs are run through html.escape()
before being embedded in st.markdown() HTML to prevent XSS injection.
"""
from html import escape
import streamlit as st

from views.components import topbar, reset_app_state, set_analyze_step


def render():
    """Render Screen 2 — job listing grid with select buttons."""
    topbar("select_job")
    jobs = st.session_state.jobs

    if st.session_state.error:
        if st.session_state.error.startswith("RATE_LIMIT:"):
            st.error(
                "⚠️ **API Rate Limit Exceeded**: We've reached the search limit for "
                "this region. Please try again tomorrow or search in a different country!"
            )
        else:
            st.error(f"❌ {st.session_state.error}")
        return

    if not jobs:
        st.warning("⚠️ No jobs found. Try a broader title or different location.")
        if st.button("← New Search", use_container_width=True):
            reset_app_state()
            st.rerun()
        return

    hcol1, _ = st.columns([3, 1])
    with hcol1:
        # ── Company mode header banner ────────────────────────────────────────
        q_mode    = st.session_state.get("search_mode", "role")
        q_company = st.session_state.get("company_name", "").strip()

        if q_mode == "company" and q_company:
            safe_company = escape(q_company)
            st.markdown(f"""
            <div style="
              display:flex;align-items:center;gap:0.75rem;
              background:var(--surf2);border:1px solid var(--border2);
              border-left:4px solid var(--green);
              border-radius:var(--r);padding:0.85rem 1.25rem;
              margin-bottom:1rem;
            ">
              <span style="font-size:1.4rem;">&#127970;</span>
              <div>
                <div style="font-size:1rem;font-weight:800;color:var(--text);">
                  Showing {len(jobs)} role{'s' if len(jobs) != 1 else ''} at
                  <span style="color:var(--green2);">{safe_company}</span>
                </div>
                <div style="font-size:0.8rem;color:var(--muted);margin-top:2px;">
                  Select a role — your resume will be matched to that exact job description.
                </div>
              </div>
            </div>
            """, unsafe_allow_html=True)
        else:
            st.markdown(f"""
            <div style="margin-bottom:0.75rem;">
              <div style="font-size:1.05rem;font-weight:800;color:var(--text);">{len(jobs)} listings found</div>
              <div style="font-size:0.82rem;color:var(--muted);margin-top:2px;">Select a role — your resume will be matched to that exact job description.</div>
            </div>""", unsafe_allow_html=True)

    for i, job in enumerate(jobs):
        # ── Escape all API-sourced strings before HTML injection ──────────────
        title    = escape(str(job.get("title",    "Unknown Title")))
        company  = escape(str(job.get("company",  "Unknown Company")))
        loc      = escape(str(job.get("location", "")))
        salary   = escape(str(job.get("salary_display", job.get("salary", ""))))
        contract = escape(str(job.get("contract_type", "")))
        source   = escape(str(job.get("source", "")))
        posted   = escape(str(job.get("posted_date", ""))) if job.get("posted_date") else ""

        # ── URL: only allow http/https to prevent javascript: injection ────────
        raw_url  = job.get("url", "")
        safe_url = raw_url if isinstance(raw_url, str) and raw_url.startswith(("http://", "https://")) else ""

        # Description: escape then truncate
        desc_raw = escape(str(job.get("description", "")))
        desc_html = ""
        if desc_raw:
            clean = desc_raw.replace("&#x27;", "'").replace("\n\n", "\n").replace("\n", " ").strip()
            if len(clean) > 260:
                clean = clean[:260] + "…"
            desc_html = f'<div style="font-size:0.84rem;color:var(--muted);margin-top:0.6rem;line-height:1.55;">{clean}</div>'

        tags_html  = ""
        if salary:   tags_html += f'<span class="tag tag-green">{salary}</span>'
        if contract: tags_html += f'<span class="tag tag-yellow">{contract}</span>'
        if source:   tags_html += f'<span class="tag tag-source">{source}</span>'
        if posted:   tags_html += f'<span style="font-size:0.72rem;color:var(--muted2);margin-left:4px;">Posted {posted}</span>'

        url_html = (
            f'<a href="{safe_url}" target="_blank" '
            f'style="font-size:0.78rem;color:var(--green2);text-decoration:none;font-weight:600;">'
            f'View listing →</a>'
        ) if safe_url else ""

        st.markdown(f"""
        <div class="job-card">
          <div style="display:flex;justify-content:space-between;align-items:flex-start;gap:0.75rem;flex-wrap:wrap;">
            <div style="flex:1;min-width:0;">
              <div style="font-size:0.97rem;font-weight:700;color:var(--text);">{title}</div>
              <div style="font-size:0.82rem;color:var(--muted);margin-top:2px;">🏢 {company} &nbsp;·&nbsp; 📍 {loc}</div>
            </div>
            <div style="flex-shrink:0;">{url_html}</div>
          </div>
          <div style="margin-top:0.5rem;">{tags_html}</div>
          {desc_html}
        </div>
        """, unsafe_allow_html=True)

        st.button(
            "Analyse this job →", key=f"select_{i}", type="primary",
            on_click=set_analyze_step, args=(job,),
        )
