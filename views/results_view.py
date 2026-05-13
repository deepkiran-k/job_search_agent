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

    if "boost_iteration" not in st.session_state:
        st.session_state.boost_iteration = 0
    if "boost_history" not in st.session_state:
        st.session_state.boost_history = []
    if "auto_revised_ats" not in st.session_state:
        st.session_state.auto_revised_ats = None

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
                # ── Gather all metrics ─────────────────────────────────────────
                orig_kw_match     = int(analysis.get("keyword_match", 0))        if analysis     else None
                orig_interview    = int(analysis.get("interview_probability", 0)) if analysis     else None
                revised_kw_match  = int(tailored_ats.get("keyword_score", 0))    if tailored_ats else None
                # interview_probability is a Gemini field; ATSScanner estimates it
                revised_interview = int(max(20, tailored_ats.get("keyword_score", 0) - 10)) if tailored_ats else None

                def _delta_badge(orig, revised):
                    """Return HTML for a coloured delta pill."""
                    if orig is None or revised is None:
                        return ""
                    diff  = revised - orig
                    color = "#16A34A" if diff >= 0 else "#DC2626"
                    sign  = "+" if diff >= 0 else ""
                    icon  = "🎉" if diff >= 5 else ("✓" if diff >= 0 else "⚠")
                    return (
                        f'<span style="background:{color};color:white;padding:2px 8px;'
                        f'border-radius:20px;font-size:0.75rem;font-weight:700;">'
                        f'{sign}{diff} {icon}</span>'
                    )

                def _metric_col(label, orig, revised, is_est=False):
                    """Return HTML for a single before→after metric card."""
                    orig_c    = score_color(orig)    if orig    is not None else "#7BA88C"
                    revised_c = score_color(revised) if revised is not None else "#7BA88C"
                    orig_val  = orig    if orig    is not None else "N/A"
                    rev_val   = revised if revised is not None else "N/A"
                    badge     = _delta_badge(orig, revised)
                    est_lbl   = '<span style="font-size:0.55rem;color:var(--muted2);text-transform:lowercase;margin-left:4px;">(est.)</span>' if is_est else ''
                    return f"""<div style="flex:1;min-width:160px;border:1px solid var(--border);border-radius:10px;padding:0.75rem 1rem;background:var(--surface2);">
  <div style="font-size:0.7rem;color:var(--muted2);font-weight:600;text-transform:uppercase;letter-spacing:.04em;margin-bottom:0.5rem;">{label}{est_lbl}</div>
  <div style="display:flex;align-items:center;gap:1rem;flex-wrap:wrap;">
    <div style="text-align:center;">
      <div style="font-size:0.65rem;color:var(--muted2);">Before</div>
      <div style="font-size:1.6rem;font-weight:800;color:{orig_c};">{orig_val}</div>
      <div style="font-size:0.62rem;color:var(--muted2);">/ 100</div>
    </div>
    <div style="font-size:1.1rem;color:var(--border2);">→</div>
    <div style="text-align:center;">
      <div style="font-size:0.65rem;color:var(--muted2);">After</div>
      <div style="font-size:1.6rem;font-weight:800;color:{revised_c};">{rev_val}</div>
      <div style="font-size:0.62rem;color:var(--muted2);">/ 100</div>
    </div>
    <div>{badge}</div>
  </div>
</div>"""

                ats_col = _metric_col("ATS Score",        orig_score,    revised_score)
                kw_col  = _metric_col("Keyword Match",    orig_kw_match, revised_kw_match)
                int_col = _metric_col("Interview Chance", orig_interview, revised_interview, is_est=True)

                st.markdown(f"""<div class="card card-accent" style="margin-bottom:1rem;">
  <div class="eyebrow">Score improvement</div>
  <div style="display:flex;gap:0.75rem;flex-wrap:wrap;margin-top:0.75rem;">
    {ats_col}{kw_col}{int_col}
  </div>
  <div style="margin-top:0.75rem;">""", unsafe_allow_html=True)
                st.markdown("</div></div>", unsafe_allow_html=True)

                # ── Score Journey Tracker ─────────────────────────────────────
                stages = []
                if orig_score is not None:
                    stages.append(("Original", orig_score))
                
                auto_ats = st.session_state.auto_revised_ats or st.session_state.get("tailored_ats")
                if auto_ats:
                    stages.append(("Auto-Revised", int(auto_ats.get("overall_score", 0))))
                
                for boost in st.session_state.boost_history:
                    stages.append((boost["label"], boost["ats_score"]))
                
                # Render the stages as a nice timeline
                if len(stages) > 1:
                    timeline_html = '<div style="display:flex; align-items:center; justify-content:space-between; margin:1.5rem 0; padding: 1rem; background: var(--surface); border-radius: 8px; border: 1px solid var(--border);">'
                    for i, (label, score) in enumerate(stages):
                        c = score_color(score)
                        timeline_html += f'''<div style="text-align:center; position:relative; flex:1;">
<div style="font-size:0.75rem; color:var(--muted); margin-bottom:0.4rem; text-transform:uppercase; font-weight:600;">{label}</div>
<div style="font-size:1.5rem; font-weight:800; color:{c};">{score}</div>
<div style="height:12px; width:12px; border-radius:50%; background:{c}; margin: 0.5rem auto 0 auto; box-shadow: 0 0 0 3px var(--background);"></div>
</div>'''
                        if i < len(stages) - 1:
                            timeline_html += '''<div style="flex:1; height:2px; background:var(--border); margin-top:2.5rem;"></div>'''
                    timeline_html += '</div>'
                    st.markdown(timeline_html, unsafe_allow_html=True)

                # ── Boost Button Section ──────────────────────────────────────
                if st.session_state.boost_iteration >= 3 or revised_score >= 95:
                    st.info("✅ **Resume is well-optimized.** Further automated boosts are unlikely to yield meaningful gains. Review the Score Journey and download your best version.")
                else:
                    st.markdown("""
                    <div class="card card-accent" style="padding:1rem; margin-top:1rem; border-color:var(--blue);">
                      <div class="eyebrow" style="color:var(--blue);">🚀 Boost ATS Score Further</div>
                      <div style="font-size:0.85rem; color:var(--muted); margin: 0.5rem 0;">
                        Not satisfied with the score? Run a focused second-pass rewrite to specifically target remaining missing keywords and gaps.
                      </div>
                    </div>""", unsafe_allow_html=True)
                    if st.button(f"🚀 Run Boost {st.session_state.boost_iteration + 1}", type="primary"):
                        with st.spinner("Analyzing current gaps and boosting..."):
                            from utils.ats_scanner import ATSScanner
                            from tools.gemini_resume_builder import GeminiResumeBuilder
                            
                            scanner = ATSScanner()
                            builder = GeminiResumeBuilder()
                            
                            # Ensure we have the latest gaps
                            current_ats = st.session_state.tailored_ats
                            
                            # Boost
                            boosted_resume = builder.boost_ats_score(
                                tailored_resume=st.session_state.tailored_resume,
                                job_info={
                                    "title": job.get("title", st.session_state.get("job_title", "Unknown")),
                                    "company": job.get("company", ""),
                                    "description": job.get("description", "")
                                },
                                current_ats_results=current_ats
                            )
                            
                            if boosted_resume and not boosted_resume.startswith("⚠️ AI_LIMIT_HIT") and not boosted_resume.startswith("Error:"):
                                # Re-scan
                                new_ats = scanner.scan(
                                    resume_text=boosted_resume,
                                    job_description=job.get("description", ""),
                                    job_title=job.get("title", "")
                                )
                                
                                # Update state
                                st.session_state.tailored_resume = boosted_resume
                                st.session_state.tailored_ats = new_ats
                                st.session_state.boost_iteration += 1
                                st.session_state.boost_history.append({
                                    "label": f"Boost {st.session_state.boost_iteration}",
                                    "ats_score": new_ats.get("overall_score", 0),
                                    "keyword_match": new_ats.get("keyword_score", 0)
                                })
                                st.rerun()
                            else:
                                st.error(boosted_resume or "Failed to boost resume.")

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
                try:
                    from utils.pdf_generator import markdown_to_docx
                    docx_bytes = markdown_to_docx(tailored)
                    st.download_button(
                        "Download resume (.docx)", data=docx_bytes,
                        file_name=f"tailored_resume_{job.get('title','job').replace(' ','_')}.docx",
                        mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                    )
                except Exception as e:
                    st.warning(f"Word export failed: {e}")

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
                            st.session_state.auto_revised_ats = st.session_state.tailored_ats
                st.rerun()

    st.markdown("<br>", unsafe_allow_html=True)
    if st.button("← Pick a different job"):
        st.session_state.step            = "select_job"
        st.session_state.selected_job    = None
        st.session_state.analysis        = None
        st.session_state.cover_letter    = ""
        st.session_state.tailored_resume = ""
        st.session_state.tailored_ats    = None
        st.session_state.auto_revised_ats = None
        st.session_state.boost_iteration = 0
        st.session_state.boost_history   = []
        st.rerun()
