"""
views/results_view.py
Screen 4 — Analysis results: ATS scores, cover letter, tailored resume.

All AI-generated and API-sourced strings that are injected into HTML are
run through html.escape() to prevent XSS.
"""
import json
from html import escape
import streamlit as st

from views.components import (
    topbar, job_banner, metric_card, score_bar, score_color,
)


def render():
    """Render Screen 4 — analysis results across three tabs."""
    topbar("results")

    analysis     = st.session_state.analysis or {}
    cover_letter = st.session_state.cover_letter or ""
    job          = st.session_state.selected_job or {}

    # ── Error state ───────────────────────────────────────────────────────────
    if st.session_state.error:
        if st.session_state.error.startswith("RATE_LIMIT:"):
            st.error(
                "⚠️ **API Rate Limit Exceeded**: We've reached the analysis limit "
                "for today. Please try again tomorrow!"
            )
        else:
            st.error(f"Analysis failed: {st.session_state.error}")
        if st.button("← Try Again"):
            st.session_state.step  = "analyze"
            st.session_state.error = None
            st.rerun()
        return

    job_banner(job)
    tab1, tab2, tab3 = st.tabs(["Resume Analysis", "Cover Letter", "Tailored Resume"])

    # ══════════════════════════════════════════════════════════════════════════
    # TAB 1 — ATS Analysis
    # ══════════════════════════════════════════════════════════════════════════
    with tab1:
        if not analysis and not st.session_state.analyze_ats:
            st.info("ATS analysis was not requested for this job.")
        elif not analysis:
            st.warning("No analysis data returned.")
        else:
            ats_score        = analysis.get("ats_score", 0)
            keyword_match    = analysis.get("keyword_match", 0)
            interview_prob   = analysis.get("interview_probability", 0)
            market_value     = analysis.get("market_value", "")
            analysis_summary = escape(str(analysis.get("analysis_summary", "")))
            ai_limit_hit     = st.session_state.get("ai_limit_hit", False)

            if ai_limit_hit:
                st.markdown("""
                <div class="card card-accent" style="border-color:var(--amber);background:rgba(217,119,6,0.05);margin-bottom:1.5rem;">
                  <div style="color:var(--amber);font-weight:700;font-size:0.85rem;">⚠️ AI Limit Reached (Safe Mode)</div>
                  <div style="font-size:0.82rem;color:var(--text);margin-top:4px;line-height:1.5;">
                    We've reached the AI daily quota. Qualitative reasoning and narrative summaries are temporarily unavailable.
                    However, your <b>core ATS scores and keyword analysis below match your resume perfectly</b> as they are calculated locally.
                  </div>
                </div>""", unsafe_allow_html=True)

            missing_keywords   = analysis.get("missing_keywords",   [])
            matched_keywords   = analysis.get("matched_keywords",   [])
            strengths          = analysis.get("strengths",          [])
            weaknesses         = analysis.get("weaknesses",         [])
            suggestions        = analysis.get("specific_suggestions", analysis.get("suggestions", []))
            detected_sections  = analysis.get("detected_sections",  [])
            missing_sections   = analysis.get("missing_sections",   [])
            formatting_issues  = analysis.get("formatting_issues",  [])
            achievements_found = analysis.get("achievements_found", [])
            keyword_density    = analysis.get("keyword_density",    0)
            word_count         = analysis.get("word_count",         0)
            contact_info       = analysis.get("contact_info",       {})
            length_feedback    = analysis.get("length_feedback",    [])

            # ── 4 Metric cards ────────────────────────────────────────────────
            st.markdown('<div class="metric-row">', unsafe_allow_html=True)
            mc1, mc2, mc3, mc4 = st.columns(4)
            with mc1: metric_card(int(ats_score),      "ATS Score")
            with mc2: metric_card(int(keyword_match),  "Keyword Match")
            with mc3: metric_card(int(interview_prob), "Interview Chance")
            with mc4:
                if market_value:
                    safe_mv = escape(str(market_value))
                    st.markdown(f"""
                    <div class="metric-card">
                      <div class="metric-label">Market Value</div>
                      <div class="metric-num metric-num-green" style="font-size:1.4rem;">{safe_mv}</div>
                      <div style="font-size:0.72rem;color:var(--muted2);margin-top:6px;">estimated</div>
                    </div>""", unsafe_allow_html=True)
                else:
                    metric_card(int(analysis.get("formatting_score", 0)), "Formatting Score")
            st.markdown("</div>", unsafe_allow_html=True)

            # ── Sub-score breakdown ───────────────────────────────────────────
            with st.expander("Score breakdown", expanded=True):
                sub_scores = {
                    "Sections":     analysis.get("section_score",      0),
                    "Keywords":     analysis.get("keyword_match",       0),
                    "Formatting":   analysis.get("formatting_score",   0),
                    "Achievements": analysis.get("achievements_score", 0),
                    "Length":       analysis.get("length_score",       0),
                    "Contact info": analysis.get("contact_score",      0),
                }
                for lbl, val in sub_scores.items():
                    score_bar(int(val), lbl)
                density_color = (
                    "#16A34A" if 1.5 <= keyword_density <= 4.0
                    else ("#D97706" if keyword_density > 4.0 else "#7BA88C")
                )
                st.markdown(f"""
                <div style="display:flex;gap:2rem;margin-top:0.6rem;flex-wrap:wrap;">
                  <span style="font-size:0.82rem;color:var(--muted);">Word count: <strong style="color:var(--text);">{word_count}</strong></span>
                  <span style="font-size:0.82rem;color:var(--muted);">Keyword density: <strong style="color:{density_color};">{keyword_density}%</strong></span>
                </div>""", unsafe_allow_html=True)
                for fb in length_feedback:
                    st.markdown(
                        f'<div style="font-size:0.82rem;color:var(--muted);margin-top:0.25rem;">📏 {escape(str(fb))}</div>',
                        unsafe_allow_html=True,
                    )
                contact_items = [("✓ " if p else "✗ ") + k.title() for k, p in contact_info.items()]
                if contact_items:
                    st.markdown(
                        f'<div style="font-size:0.82rem;color:var(--muted);margin-top:0.4rem;">Contact: {" · ".join(contact_items)}</div>',
                        unsafe_allow_html=True,
                    )

            # ── Keyword tags ──────────────────────────────────────────────────
            st.markdown("<br>", unsafe_allow_html=True)
            kw_l, kw_r = st.columns(2)
            with kw_l:
                st.markdown('<div class="eyebrow">Missing keywords</div>', unsafe_allow_html=True)
                if missing_keywords:
                    st.markdown(
                        '<div style="margin-top:0.4rem;">'
                        + "".join(f'<span class="tag tag-red">{escape(str(kw))}</span>' for kw in missing_keywords[:15])
                        + "</div>",
                        unsafe_allow_html=True,
                    )
                else:
                    st.markdown('<span class="tag tag-green">✓ Great keyword coverage!</span>', unsafe_allow_html=True)
            with kw_r:
                st.markdown('<div class="eyebrow">Matched keywords</div>', unsafe_allow_html=True)
                if matched_keywords:
                    st.markdown(
                        '<div style="margin-top:0.4rem;">'
                        + "".join(f'<span class="tag tag-green">{escape(str(kw))}</span>' for kw in matched_keywords[:15])
                        + "</div>",
                        unsafe_allow_html=True,
                    )
                else:
                    st.markdown('<span class="tag tag-red">No keyword matches found</span>', unsafe_allow_html=True)

            # ── Resume sections ───────────────────────────────────────────────
            with st.expander("Resume sections", expanded=False):
                if detected_sections:
                    st.markdown(
                        '<div style="margin-bottom:0.4rem;"><div class="eyebrow">Detected</div>'
                        + "".join(f'<span class="tag tag-green">{escape(str(s))}</span>' for s in detected_sections)
                        + "</div>",
                        unsafe_allow_html=True,
                    )
                if missing_sections:
                    st.markdown(
                        '<div><div class="eyebrow">Missing</div>'
                        + "".join(f'<span class="tag tag-red">{escape(str(s))}</span>' for s in missing_sections)
                        + "</div>",
                        unsafe_allow_html=True,
                    )
                if not missing_sections:
                    st.markdown('<span class="tag tag-green">✓ All standard sections detected</span>', unsafe_allow_html=True)

            # ── Formatting issues ─────────────────────────────────────────────
            if formatting_issues:
                st.markdown("<br>", unsafe_allow_html=True)
                st.markdown('<div class="eyebrow">Formatting issues</div>', unsafe_allow_html=True)
                for issue in formatting_issues:
                    st.markdown(
                        f'<div class="row-item row-item-amber">'
                        f'<span style="color:var(--amber);flex-shrink:0;">⚠</span>'
                        f'<span style="color:var(--text);">{escape(str(issue))}</span></div>',
                        unsafe_allow_html=True,
                    )

            # ── Quantified achievements ───────────────────────────────────────
            if achievements_found:
                with st.expander(f"Quantified achievements ({len(achievements_found)})", expanded=False):
                    st.markdown(
                        "<div>"
                        + "".join(f'<span class="tag tag-blue">{escape(str(a))}</span>' for a in achievements_found)
                        + "</div>",
                        unsafe_allow_html=True,
                    )

            # ── AI summary ────────────────────────────────────────────────────
            if analysis_summary and not ai_limit_hit:
                st.markdown(f"""
                <div class="card card-accent" style="margin-top:1rem;">
                  <div class="eyebrow">AI Summary</div>
                  <div style="color:var(--text);line-height:1.7;font-size:0.9rem;margin-top:4px;">{analysis_summary}</div>
                </div>""", unsafe_allow_html=True)

            # ── Strengths & weaknesses ────────────────────────────────────────
            st.markdown("<br>", unsafe_allow_html=True)
            sw_l, sw_r = st.columns(2)
            with sw_l:
                st.markdown('<div class="eyebrow">Strengths</div>', unsafe_allow_html=True)
                for s in strengths:
                    st.markdown(
                        f'<div class="row-item row-item-green">'
                        f'<span style="color:var(--green);font-weight:700;flex-shrink:0;">✓</span>'
                        f'<span style="color:var(--text);">{escape(str(s))}</span></div>',
                        unsafe_allow_html=True,
                    )
            with sw_r:
                st.markdown('<div class="eyebrow">Areas to improve</div>', unsafe_allow_html=True)
                for w in weaknesses:
                    st.markdown(
                        f'<div class="row-item row-item-amber">'
                        f'<span style="color:var(--amber);font-weight:700;flex-shrink:0;">⚠</span>'
                        f'<span style="color:var(--text);">{escape(str(w))}</span></div>',
                        unsafe_allow_html=True,
                    )

            # ── Suggestions ───────────────────────────────────────────────────
            if suggestions:
                st.markdown("<br>", unsafe_allow_html=True)
                with st.expander(f"Top {len(suggestions)} fixes", expanded=True):
                    for idx, s in enumerate(suggestions, 1):
                        text = s.get("suggestion", str(s)) if isinstance(s, dict) else str(s)
                        area = s.get("area", "")           if isinstance(s, dict) else ""
                        text = escape(text)
                        area = escape(area)
                        area_html = (
                            f'<span class="tag tag-blue" style="font-size:0.68rem;margin-top:3px;">{area}</span>'
                            if area else ""
                        )
                        st.markdown(f"""
                        <div class="card" style="padding:0.6rem 0.9rem;margin-bottom:0.4rem;">
                          <div style="display:flex;gap:0.6rem;align-items:flex-start;">
                            <div class="sug-badge">{idx}</div>
                            <div>
                              <span style="color:var(--text);font-size:0.87rem;">{text}</span>
                              <div>{area_html}</div>
                            </div>
                          </div>
                        </div>""", unsafe_allow_html=True)

    # ══════════════════════════════════════════════════════════════════════════
    # TAB 2 — Cover Letter
    # ══════════════════════════════════════════════════════════════════════════
    with tab2:
        if not cover_letter and not st.session_state.analyze_cover:
            st.info("Cover letter was not requested for this job.")
        elif not cover_letter:
            st.warning("No cover letter was generated.")
        else:
            if st.session_state.get("ai_limit_hit"):
                st.markdown("""
                <div class="card card-accent" style="border-color:var(--amber);background:rgba(217,119,6,0.05);margin-bottom:1rem;">
                  <div style="color:var(--amber);font-weight:700;font-size:0.85rem;">⚠️ AI Limit Reached</div>
                  <div style="font-size:0.82rem;color:var(--text);margin-top:4px;line-height:1.5;">
                    AI-powered cover letter generation is currently unavailable due to daily quota limits.
                    Please try again later for a fully tailored letter.
                  </div>
                </div>""", unsafe_allow_html=True)
            else:
                st.markdown(
                    '<div class="eyebrow" style="margin-bottom:0.75rem;">Generated cover letter</div>',
                    unsafe_allow_html=True,
                )
                # Cover letter is AI-generated plain text — escape for safety
                safe_cl = escape(cover_letter)
                st.markdown(f'<div class="cover-letter">{safe_cl}</div>', unsafe_allow_html=True)
                st.markdown("<br>", unsafe_allow_html=True)
                st.download_button(
                    label="Download cover letter (.txt)", data=cover_letter,
                    file_name=f"cover_letter_{job.get('title','job').replace(' ','_')}.txt",
                    mime="text/plain",
                )

    # ══════════════════════════════════════════════════════════════════════════
    # TAB 3 — Tailored Resume
    # ══════════════════════════════════════════════════════════════════════════
    with tab3:
        tailored     = st.session_state.get("tailored_resume", "")
        tailored_ats = st.session_state.get("tailored_ats") or {}
        if not tailored:
            st.info("Auto-Revise Resume was not requested. Go back and enable that option.")
        else:
            orig_score    = int(analysis.get("ats_score", 0)) if analysis else None
            revised_score = int(tailored_ats.get("overall_score", 0)) if tailored_ats else None

            if st.session_state.get("ai_limit_hit"):
                st.markdown("""
                <div class="card card-accent" style="border-color:var(--amber);background:rgba(217,119,6,0.05);margin-bottom:1rem;">
                  <div style="color:var(--amber);font-weight:700;font-size:0.85rem;">⚠️ AI Limit Reached</div>
                  <div style="font-size:0.82rem;color:var(--text);margin-top:4px;line-height:1.5;">
                    Auto-Revision is currently unavailable due to AI daily quota limits.
                    Please try again later to generate a tailored version of your resume.
                  </div>
                </div>""", unsafe_allow_html=True)
            elif revised_score is not None:
                delta       = (revised_score - orig_score) if orig_score is not None else None
                delta_color = "#16A34A" if (delta is not None and delta >= 0) else "#DC2626"
                delta_icon  = "🎉" if (delta is not None and delta >= 5) else ("✓" if delta is not None and delta >= 0 else "⚠")
                delta_html  = (
                    f'<span style="background:{delta_color};color:white;padding:3px 10px;'
                    f'border-radius:20px;font-size:0.82rem;font-weight:700;">'
                    f'{("+" if delta >= 0 else "")}{delta} {delta_icon}</span>'
                ) if delta is not None else ""
                orig_html = (
                    f'<div style="font-size:1.8rem;font-weight:800;color:{score_color(orig_score) if orig_score else "#7BA88C"};">'
                    f'{orig_score}</div><div style="font-size:0.7rem;color:var(--muted2);">/ 100</div>'
                ) if orig_score is not None else '<div style="font-size:0.82rem;color:var(--muted2);">N/A</div>'

                st.markdown(f"""
                <div class="card card-accent" style="margin-bottom:1rem;">
                  <div class="eyebrow">Score improvement</div>
                  <div style="display:flex;align-items:center;gap:2rem;flex-wrap:wrap;margin-top:0.5rem;">
                    <div style="text-align:center;"><div style="font-size:0.72rem;color:var(--muted2);margin-bottom:4px;">Original</div>{orig_html}</div>
                    <div style="font-size:1.25rem;color:var(--border2);">→</div>
                    <div style="text-align:center;"><div style="font-size:0.72rem;color:var(--muted2);margin-bottom:4px;">Revised</div>
                      <div style="font-size:1.8rem;font-weight:800;color:{score_color(revised_score)};">{revised_score}</div>
                      <div style="font-size:0.7rem;color:var(--muted2);">/ 100</div>
                    </div>
                    <div>{delta_html}</div>
                  </div>
                  <div style="margin-top:0.75rem;">""", unsafe_allow_html=True)
                score_bar(revised_score, "Revised ATS score")
                if orig_score is not None:
                    score_bar(orig_score, "Original ATS score")
                st.markdown("</div></div>", unsafe_allow_html=True)

            if not st.session_state.get("ai_limit_hit"):
                st.markdown("<hr>", unsafe_allow_html=True)
                display_tailored = tailored.replace("⚠️ AI_LIMIT_HIT: ", "")
                st.markdown(display_tailored)

            st.markdown("<br>", unsafe_allow_html=True)
            dl1, dl2 = st.columns(2)
            with dl1:
                try:
                    from utils.pdf_generator import markdown_to_pdf
                    pdf_bytes = markdown_to_pdf(tailored)
                    st.download_button(
                        "Download resume (.pdf)", data=pdf_bytes,
                        file_name=f"tailored_resume_{job.get('title','job').replace(' ','_')}.pdf",
                        mime="application/pdf", type="primary",
                    )
                except Exception as e:
                    st.warning(f"PDF export failed: {e}")
            with dl2:
                st.download_button(
                    "Download resume (.md)", data=tailored,
                    file_name=f"tailored_resume_{job.get('title','job').replace(' ','_')}.md",
                    mime="text/markdown",
                )

    # ── Generate More section ─────────────────────────────────────────────────
    st.markdown("<br>", unsafe_allow_html=True)
    missing_items = []
    if not cover_letter:                              missing_items.append("cover_letter")
    if not st.session_state.get("tailored_resume", ""): missing_items.append("tailored_resume")

    if missing_items:
        st.markdown("""
        <div class="card card-accent" style="padding:0.85rem 1.1rem;margin-bottom:0.5rem;">
          <div class="eyebrow">Generate more for this job</div>
        </div>""", unsafe_allow_html=True)
        gen_cover = gen_tailor = False
        chk_cols = st.columns(4)
        col_i = 0
        if "cover_letter" in missing_items:
            with chk_cols[col_i]:
                gen_cover = st.checkbox("Cover Letter", value=True, key="gen_cover")
            col_i += 1
        if "tailored_resume" in missing_items:
            with chk_cols[col_i]:
                gen_tailor = st.checkbox("Auto-Revise Resume", value=False, key="gen_tailor")

        if st.button("Generate selected", type="primary"):
            resume_text = st.session_state.get("saved_resume_text", "")
            if not resume_text.strip():
                st.error("Resume text not found — please go back and re-paste your resume.")
            else:
                job_title_val = job.get("title", st.session_state.job_title)
                job_desc      = job.get("description", "")
                with st.spinner("Generating…"):
                    if gen_cover:
                        from tools.gemini_tools import GeminiCoverLetterTool
                        cover_tool = GeminiCoverLetterTool()
                        raw = cover_tool._run(
                            job_info=json.dumps({
                                "title":       job_title_val,
                                "company":     job.get("company", ""),
                                "description": job_desc,
                            }),
                            resume_text=resume_text,
                            ats_analysis=json.dumps(analysis),
                        )
                        try:
                            st.session_state.cover_letter = json.loads(raw).get("cover_letter", raw)
                        except Exception:
                            st.session_state.cover_letter = raw
                    if gen_tailor:
                        from tools.gemini_resume_builder import GeminiResumeBuilder
                        from utils.ats_scanner import ATSScanner
                        builder = GeminiResumeBuilder()
                        st.session_state.tailored_resume = builder.build_resume(
                            resume_text=resume_text,
                            job_info={
                                "title":       job_title_val,
                                "company":     job.get("company", ""),
                                "description": job_desc,
                            },
                            ats_results=analysis,
                        )
                        if (st.session_state.tailored_resume
                                and not st.session_state.tailored_resume.startswith("Error")):
                            det_scanner = ATSScanner()
                            st.session_state.tailored_ats = det_scanner.scan(
                                resume_text=st.session_state.tailored_resume,
                                job_description=job_desc, job_title=job_title_val,
                            )
                st.rerun()

    st.markdown("<br>", unsafe_allow_html=True)
    if st.button("← Pick a different job"):
        st.session_state.step            = "select_job"
        st.session_state.selected_job    = None
        st.session_state.analysis        = None
        st.session_state.cover_letter    = ""
        st.session_state.tailored_resume = ""
        st.session_state.tailored_ats    = None
        st.rerun()
