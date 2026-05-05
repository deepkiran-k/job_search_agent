"""
views/analyze_view.py
Screen 3 — Resume upload / paste, AI option checkboxes, and analysis trigger.

On submit, runs GeminiATSScorer + optional cover letter and resume tailoring,
then transitions to the "results" step.
"""
import json
import os
import streamlit as st
from streamlit_lottie import st_lottie

from utils.exceptions import RateLimitError
from views.components import (
    topbar, job_banner, load_lottie_url, LOTTIE_ANALYZE_URL,
)


def render():
    """Render Screen 3 — resume upload form and run analysis on submit."""
    topbar("analyze")

    jb = st.session_state.selected_job
    job_banner(jb)

    # ── On-demand JSearch description enrichment ──────────────────────────────
    if st.session_state.get("needs_enrichment"):
        if "JSearch" in jb.get("source", "") and len(jb.get("description", "").strip()) < 100:
            with st.spinner("📄 Fetching full job description..."):
                from utils.rapidapi_client import fetch_job_details
                full_desc = fetch_job_details(jb.get("id"), os.getenv("RAPIDAPI_KEY"))
                if full_desc:
                    jb["description"]        = full_desc[:5000]
                    jb["is_highlights_only"] = False
                    st.session_state.selected_job = jb
        st.session_state.needs_enrichment = False
        st.rerun()

    st.markdown(
        '<div style="font-size:0.9rem;font-weight:700;color:var(--text);margin-bottom:0.75rem;">Your resume</div>',
        unsafe_allow_html=True,
    )

    upload_tab, paste_tab = st.tabs(["Upload file", "Paste text"])

    with upload_tab:
        uploaded_file = st.file_uploader(
            "Drop your resume here — PDF, DOCX or TXT",
            type=["pdf", "docx", "txt"], key="resume_file",
        )
        if uploaded_file:
            from utils.resume_parser import parse_resume_file
            parsed = parse_resume_file(uploaded_file)
            st.session_state.parsed_file  = parsed
            st.session_state.file_checks  = parsed.get("file_checks")
            file_text   = parsed.get("text", "")
            file_type   = parsed.get("file_type", "unknown")
            file_checks = parsed.get("file_checks", {})
            st.markdown(f"""
            <div class="card" style="padding:0.65rem 1rem;margin-top:0.5rem;">
              <div style="display:flex;align-items:center;gap:8px;flex-wrap:wrap;">
                <span class="tag tag-green">✓ {uploaded_file.name}</span>
                <span class="tag tag-blue">{file_type.upper()}</span>
                <span style="font-size:0.78rem;color:var(--muted);">{len(file_text.split())} words extracted</span>
                {f'<span class="tag tag-gray">{file_checks.get("page_count","?")} page(s)</span>' if file_checks.get("page_count") else ""}
              </div>
            </div>""", unsafe_allow_html=True)
            if file_checks.get("issues"):
                for issue in file_checks["issues"]:
                    st.markdown(
                        f'<div class="row-item row-item-amber" style="margin-top:0.3rem;">'
                        f'<span style="color:var(--amber);flex-shrink:0;">⚠</span>'
                        f'<span style="color:var(--text);">{issue}</span></div>',
                        unsafe_allow_html=True,
                    )
            with st.expander("Preview extracted text", expanded=False):
                st.text(file_text[:2000] + ("..." if len(file_text) > 2000 else ""))
        else:
            st.session_state.parsed_file = None
            st.session_state.file_checks = None

    with paste_tab:
        resume_text = st.text_area(
            label="Resume text", height=260,
            placeholder="Paste your full resume text here…",
            label_visibility="collapsed", key="resume_text",
        )

    # ── AI option checkboxes ──────────────────────────────────────────────────
    st.markdown(
        '<div style="font-size:0.9rem;font-weight:700;color:var(--text);margin:1.1rem 0 0.6rem;">What should AI do?</div>',
        unsafe_allow_html=True,
    )
    oc1, oc2, oc3 = st.columns(3)
    with oc1:
        st.session_state.analyze_ats = st.checkbox(
            "Resume Score & Feedback", value=st.session_state.get("analyze_ats", True))
        _ats_bg = "var(--greenlt)" if st.session_state.analyze_ats else "var(--surface)"
        _ats_bd = "#86EFAC"       if st.session_state.analyze_ats else "var(--border)"
        st.markdown(
            f'<div style="border:1px solid {_ats_bd};border-radius:var(--r);padding:0.75rem;'
            f'margin-top:-0.4rem;background:{_ats_bg}">'
            f'<div style="font-size:0.82rem;color:var(--muted);line-height:1.5;">'
            f'ATS score, keyword gaps, sub-scores and actionable suggestions.</div></div>',
            unsafe_allow_html=True,
        )
    with oc2:
        st.session_state.analyze_cover = st.checkbox(
            "Generate Cover Letter", value=st.session_state.get("analyze_cover", True))
        _cov_bg = "var(--greenlt)" if st.session_state.analyze_cover else "var(--surface)"
        _cov_bd = "#86EFAC"       if st.session_state.analyze_cover else "var(--border)"
        st.markdown(
            f'<div style="border:1px solid {_cov_bd};border-radius:var(--r);padding:0.75rem;'
            f'margin-top:-0.4rem;background:{_cov_bg}">'
            f'<div style="font-size:0.82rem;color:var(--muted);line-height:1.5;">'
            f'A tailored cover letter written for this exact role and company.</div></div>',
            unsafe_allow_html=True,
        )
    with oc3:
        st.session_state.analyze_tailor = st.checkbox(
            "Auto-Revise Resume", value=st.session_state.get("analyze_tailor", False))
        _tail_bg = "var(--greenlt)" if st.session_state.analyze_tailor else "var(--surface)"
        _tail_bd = "#86EFAC"       if st.session_state.analyze_tailor else "var(--border)"
        st.markdown(
            f'<div style="border:1px solid {_tail_bd};border-radius:var(--r);padding:0.75rem;'
            f'margin-top:-0.4rem;background:{_tail_bg}">'
            f'<div style="font-size:0.82rem;color:var(--muted);line-height:1.5;">'
            f'Rewrite your resume to boost ATS score for this specific listing.</div></div>',
            unsafe_allow_html=True,
        )

    st.markdown("<br>", unsafe_allow_html=True)
    btn_col, back_col, _ = st.columns([2, 1, 4])
    with btn_col:
        analyze_btn = st.button(
            "Analyse my resume →", type="primary",
            use_container_width=True, disabled=st.session_state.analyzing,
        )
    with back_col:
        if st.button("← Back to jobs"):
            st.session_state.step         = "select_job"
            st.session_state.selected_job = None
            st.session_state.analyzing    = False
            st.rerun()

    # ── Analysis trigger ──────────────────────────────────────────────────────
    if analyze_btn:
        uploaded_text = (st.session_state.get("parsed_file") or {}).get("text", "")
        pasted_text   = resume_text  # always defined — text_area always returns a value
        final_resume  = uploaded_text or pasted_text
        file_checks   = st.session_state.get("file_checks")

        if not final_resume.strip():
            st.error("Please upload a resume file or paste your resume text before running analysis.")
        else:
            st.session_state.saved_resume_text = final_resume
            st.session_state.analyzing         = True
            lottie_data = load_lottie_url(LOTTIE_ANALYZE_URL)

            with st.status("Analysing your resume...", expanded=True) as status:
                if lottie_data:
                    st_lottie(lottie_data, height=120, key="analyze_anim")
                try:
                    from utils.gemini_ats import GeminiATSScorer
                    from tools.gemini_tools import GeminiCoverLetterTool

                    job_desc      = jb.get("description", "")
                    job_title_val = jb.get("title", st.session_state.job_title)

                    st.session_state.analysis       = None
                    st.session_state.cover_letter   = ""
                    st.session_state.tailored_resume = ""
                    st.session_state.tailored_ats   = None
                    st.session_state.ai_limit_hit   = False

                    # ── ATS Scoring ───────────────────────────────────────────
                    if st.session_state.analyze_ats:
                        status.update(label="Scoring your resume…", state="running")
                        scorer       = GeminiATSScorer()
                        analysis_res = scorer.analyze_resume(
                            resume_text=final_resume, job_title=job_title_val,
                            job_description=job_desc, file_checks=file_checks,
                        )
                        st.session_state.analysis = analysis_res
                        if analysis_res.get("ai_limit_hit"):
                            st.session_state.ai_limit_hit = True
                            st.toast("⚠️ AI Quota reached. Using Fallback analysis.", icon="🛑")
                        label = (
                            "Resume scored ✓"
                            if not st.session_state.ai_limit_hit
                            else "Resume scored (Safe Mode) ⚠"
                        )
                        status.update(label=label, state="running")

                    # ── Cover Letter ──────────────────────────────────────────
                    if st.session_state.analyze_cover:
                        status.update(label="Writing your cover letter…", state="running")
                        cover_tool = GeminiCoverLetterTool()
                        cover_raw  = cover_tool._run(
                            job_info=json.dumps({
                                "title":       job_title_val,
                                "company":     jb.get("company", ""),
                                "description": job_desc,
                            }),
                            resume_text=final_resume,
                            ats_analysis=json.dumps(st.session_state.get("analysis", {})),
                        )
                        try:
                            cover_data = json.loads(cover_raw)
                            st.session_state.cover_letter = cover_data.get("cover_letter", cover_raw)
                            if cover_data.get("ai_limit_hit"):
                                st.session_state.ai_limit_hit = True
                                st.toast("⚠️ AI Quota reached. Using Cover Letter template.", icon="🛑")
                        except Exception:
                            st.session_state.cover_letter = cover_raw
                        label = (
                            "Cover letter written ✓"
                            if not st.session_state.ai_limit_hit
                            else "Using Cover Letter template (AI Limited) ⚠"
                        )
                        status.update(label=label, state="running")

                    # ── Resume tailoring ───────────────────────────────────────
                    if st.session_state.analyze_tailor:
                        status.update(label="Rewriting your resume…", state="running")
                        from tools.gemini_resume_builder import GeminiResumeBuilder
                        from utils.ats_scanner import ATSScanner
                        builder      = GeminiResumeBuilder()
                        tailored_res = builder.build_resume(
                            resume_text=final_resume,
                            job_info={
                                "title":       job_title_val,
                                "company":     jb.get("company", ""),
                                "description": job_desc,
                            },
                            ats_results=st.session_state.get("analysis"),
                        )
                        st.session_state.tailored_resume = tailored_res
                        if "AI_LIMIT_HIT:" in tailored_res:
                            st.session_state.ai_limit_hit = True
                            st.toast("⚠️ AI Quota reached. Using rule-based resume revision.", icon="🛑")
                        label = (
                            "Resume rewritten ✓"
                            if "AI_LIMIT_HIT:" not in tailored_res
                            else "Resume revised (Rule-based) ⚠"
                        )
                        status.update(label=label, state="running")

                        if (tailored_res
                                and not tailored_res.startswith("Error")
                                and "AI_LIMIT_HIT:" not in tailored_res):
                            det_scanner = ATSScanner()
                            st.session_state.tailored_ats = det_scanner.scan(
                                resume_text=tailored_res,
                                job_description=job_desc,
                                job_title=job_title_val,
                            )

                    st.session_state.step  = "results"
                    st.session_state.error = None
                    status.update(label="Analysis complete ✓", state="complete")

                    # ── Save analysis to history (non-blocking) ───────────────
                    try:
                        from utils.history_manager import save_analysis
                        _uid = st.session_state.get("user_id")
                        if _uid:
                            save_analysis(
                                user_id=_uid,
                                job=jb,
                                search_params={
                                    "job_title":   st.session_state.job_title,
                                    "company":     st.session_state.get("company_name", ""),
                                    "location":    st.session_state.location,
                                    "country":     st.session_state.get("country", ""),
                                    "experience":  st.session_state.experience,
                                    "search_mode": st.session_state.get("search_mode", "role"),
                                },
                                analysis=st.session_state.analysis or {},
                                cover_letter=st.session_state.cover_letter or "",
                                tailored_resume=st.session_state.tailored_resume or "",
                            )
                    except Exception:
                        pass  # history must never crash the analysis

                except RateLimitError as re:
                    st.session_state.error = f"RATE_LIMIT:{re.source}"
                    st.session_state.step  = "analyze"
                    status.update(label="API Limit Reached", state="error")
                except Exception as e:
                    st.session_state.error = str(e)
                    st.session_state.step  = "results"
                    status.update(label="Analysis failed", state="error")
                finally:
                    st.session_state.analyzing = False

            st.rerun()
