"""
AI Job Search Agent - Streamlit UI
3-step pipeline: Search → Select Job → Analyze (ATS + Cover Letter)
Gemini is called ONLY twice: once for ATS scoring, once for cover letter.
"""
import os
import json
import asyncio
import streamlit as st

# ── Asyncio Patch for Streamlit + Langchain ──────────────────────────────────
try:
    asyncio.get_running_loop()
except RuntimeError:
    asyncio.set_event_loop(asyncio.new_event_loop())

# ── Must be first Streamlit call ──────────────────────────────────────────────
st.set_page_config(
    page_title="AI Job Search Agent",
    page_icon="🤖",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── Env / imports ─────────────────────────────────────────────────────────────
os.environ.setdefault("OPENAI_API_KEY", "sk-dummy-not-used-gemini-handles-llm")

from config.settings import settings

# ── CSS ───────────────────────────────────────────────────────────────────────
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap');

html, body, [class*="css"] { font-family: 'Inter', sans-serif; }

/* Dark background */
.stApp { background: #0d1117; color: #e6edf3; }

/* Sidebar */
section[data-testid="stSidebar"] { background: #161b22; border-right: 1px solid #30363d; }
section[data-testid="stSidebar"] * { color: #e6edf3 !important; }

/* Cards */
.card {
    background: #161b22;
    border: 1px solid #30363d;
    border-radius: 12px;
    padding: 1.25rem 1.5rem;
    margin-bottom: 1rem;
}
.card-accent { border-left: 4px solid #1f6feb; }
.card-green  { border-left: 4px solid #238636; }
.card-orange { border-left: 4px solid #d29922; }

/* Metric boxes */
.metric-box {
    background: #21262d;
    border: 1px solid #30363d;
    border-radius: 10px;
    padding: 1rem;
    text-align: center;
}
.metric-label { font-size: 0.75rem; color: #8b949e; text-transform: uppercase; letter-spacing: 0.05em; margin-bottom: 0.25rem; }
.metric-value { font-size: 2rem; font-weight: 700; color: #e6edf3; }
.metric-sub   { font-size: 0.8rem; color: #8b949e; margin-top: 0.15rem; }

/* Score bar */
.score-bar-bg { background: #21262d; border-radius: 999px; height: 8px; margin-top: 0.4rem; }
.score-bar-fill { height: 8px; border-radius: 999px; }

/* Tags */
.tag {
    display: inline-block;
    padding: 0.2rem 0.6rem;
    border-radius: 999px;
    font-size: 0.75rem;
    font-weight: 500;
    margin: 0.15rem;
}
.tag-blue   { background: #1f3a5f; color: #79c0ff; border: 1px solid #1f6feb; }
.tag-green  { background: #1a3a2a; color: #56d364; border: 1px solid #238636; }
.tag-red    { background: #3a1a1a; color: #f85149; border: 1px solid #da3633; }
.tag-yellow { background: #3a2e1a; color: #e3b341; border: 1px solid #d29922; }

/* Job card */
.job-card {
    background: #161b22;
    border: 1px solid #30363d;
    border-radius: 12px;
    padding: 1.25rem 1.5rem;
    margin-bottom: 0.75rem;
    transition: border-color 0.2s;
}
.job-card:hover { border-color: #1f6feb; }
.job-card-selected { border-color: #238636 !important; background: #0d1f14; }

/* Cover letter box */
.cover-letter {
    background: #161b22;
    border: 1px solid #30363d;
    border-radius: 12px;
    padding: 2rem;
    white-space: pre-wrap;
    font-family: 'Inter', sans-serif;
    font-size: 0.95rem;
    line-height: 1.7;
    color: #e6edf3;
}

/* Step indicator */
.step-bar {
    display: flex;
    align-items: center;
    gap: 0.5rem;
    margin-bottom: 1.5rem;
}
.step-dot {
    width: 28px; height: 28px;
    border-radius: 50%;
    display: flex; align-items: center; justify-content: center;
    font-size: 0.8rem; font-weight: 700;
    flex-shrink: 0;
}
.step-dot-active   { background: #1f6feb; color: white; }
.step-dot-done     { background: #238636; color: white; }
.step-dot-inactive { background: #21262d; color: #8b949e; border: 1px solid #30363d; }
.step-line { flex: 1; height: 2px; background: #30363d; }
.step-line-done { background: #238636; }

/* Hide Streamlit chrome */
#MainMenu, footer, header { visibility: hidden; }
.block-container { padding-top: 1.5rem; }

/* Tabs */
button[data-baseweb="tab"] { color: #8b949e !important; }
button[data-baseweb="tab"][aria-selected="true"] { color: #e6edf3 !important; border-bottom-color: #1f6feb !important; }
</style>
""", unsafe_allow_html=True)


# ── Session state ─────────────────────────────────────────────────────────────
for key, default in {
    "step": "search",        # "search" | "select_job" | "analyze" | "results"
    "jobs": [],
    "selected_job": None,
    "analysis": None,
    "cover_letter": "",
    "tailored_resume": "",
    "tailored_ats": None,
    "analyze_ats": True,
    "analyze_cover": True,
    "analyze_tailor": False,
    "error": None,
    "searching": False,
    "analyzing": False,
    "job_title": "Software Engineer",
    "location": "Remote",
    "experience": "3-5 years",
}.items():
    if key not in st.session_state:
        st.session_state[key] = default


# ── Helpers ───────────────────────────────────────────────────────────────────
def score_color(score: int) -> str:
    if score >= 80: return "#238636"
    if score >= 60: return "#d29922"
    return "#da3633"

def score_bar(score: int, label: str = ""):
    color = score_color(score)
    st.markdown(f"""
    <div>
      <div style="display:flex;justify-content:space-between;margin-bottom:0.2rem;">
        <span style="font-size:0.8rem;color:#8b949e;">{label}</span>
        <span style="font-size:0.8rem;font-weight:600;color:{color};">{score}%</span>
      </div>
      <div class="score-bar-bg">
        <div class="score-bar-fill" style="width:{score}%;background:{color};"></div>
      </div>
    </div>
    """, unsafe_allow_html=True)

def step_indicator(current: str):
    steps = [
        ("search",     "1", "Search Jobs"),
        ("select_job", "2", "Select Job"),
        ("analyze",    "3", "Analyze"),
    ]
    order = [s[0] for s in steps]
    cur_idx = order.index(current) if current in order else 0
    # results maps to step 3's done state
    if current == "results":
        cur_idx = 3

    html = '<div class="step-bar">'
    for i, (key, num, label) in enumerate(steps):
        step_idx = i
        if step_idx < cur_idx:
            dot_cls = "step-dot-done"
            line_cls = "step-line-done"
            icon = "✓"
        elif step_idx == cur_idx:
            dot_cls = "step-dot-active"
            line_cls = "step-line"
            icon = num
        else:
            dot_cls = "step-dot-inactive"
            line_cls = "step-line"
            icon = num

        html += f'<div class="step-dot {dot_cls}">{icon}</div>'
        html += f'<span style="font-size:0.8rem;color:{("#e6edf3" if step_idx <= cur_idx else "#8b949e")};">{label}</span>'
        if i < len(steps) - 1:
            html += f'<div class="step-line {line_cls}"></div>'

    html += '</div>'
    st.markdown(html, unsafe_allow_html=True)

def set_analyze_step(job):
    """Callback to set the selected job and advance step"""
    st.session_state.selected_job = job
    st.session_state.step = "analyze"


# ── Sidebar ───────────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown("## 🤖 AI Job Search Agent")
    st.markdown("---")

    # Gemini status indicator
    gemini_ok = settings.HAS_GEMINI

    status_color = "#56d364" if gemini_ok else "#f85149"
    status_text  = "Connected" if gemini_ok else "Disconnected"
    st.markdown(f"""
    <div class="card" style="padding:0.75rem 1rem;">
      <div style="font-size:0.7rem;color:#8b949e;text-transform:uppercase;letter-spacing:0.05em;">Google Gemini</div>
      <div style="display:flex;align-items:center;gap:0.5rem;margin-top:0.3rem;">
        <span style="width:8px;height:8px;border-radius:50%;background:{status_color};display:inline-block;"></span>
        <span style="font-size:0.85rem;font-weight:600;color:{status_color};">{status_text}</span>
      </div>
      <div style="font-size:0.7rem;color:#8b949e;margin-top:0.2rem;">gemini-2.5-flash-lite</div>
    </div>
    """, unsafe_allow_html=True)

    st.markdown("### 🔍 Search Parameters")
    job_title_input  = st.text_input("Job Title",  value=st.session_state.job_title,  placeholder="e.g. Data Scientist")
    location_input   = st.text_input("Location",   value=st.session_state.location,   placeholder="e.g. Mumbai, London, Remote  (city or 'Remote' — leave blank for all)")
    
    # Country selection
    country_options = {
        "us": "🇺🇸 United States",
        "gb": "🇬🇧 United Kingdom",
        "ca": "🇨🇦 Canada",
        "au": "🇦🇺 Australia",
        "in": "🇮🇳 India",
        "ae": "🇦🇪 United Arab Emirates",
        "de": "🇩🇪 Germany",
        "fr": "🇫🇷 France",
        "it": "🇮🇹 Italy",
        "nl": "🇳🇱 Netherlands",
        "pl": "🇵🇱 Poland",
        "es": "🇪🇸 Spain",
        "br": "🇧🇷 Brazil",
        "mx": "🇲🇽 Mexico",
        "za": "🇿🇦 South Africa",
        "nz": "🇳🇿 New Zealand",
        "sg": "🇸🇬 Singapore",
    }
    country_code = st.selectbox(
        "Country", 
        options=list(country_options.keys()),
        format_func=lambda x: country_options[x],
        index=0
    )
    
    experience_input = st.selectbox("Experience Level", [
        "0-1 years", "1-3 years", "3-5 years", "5-10 years", "10+ years"
    ], index=["0-1 years", "1-3 years", "3-5 years", "5-10 years", "10+ years"].index(st.session_state.experience))

    search_clicked = st.button("🔍 Find Jobs", type="primary", use_container_width=True,
                               disabled=st.session_state.searching)

    if st.session_state.step != "search":
        if st.button("🔄 New Search", use_container_width=True):
            st.session_state.step = "search"
            st.session_state.jobs = []
            st.session_state.selected_job = None
            st.session_state.analysis = None
            st.session_state.cover_letter = ""
            st.session_state.tailored_resume = ""
            st.session_state.tailored_ats = None
            st.session_state.error = None
            st.rerun()

    st.markdown("---")

    # Progress legend
    step_labels = {
        "search":     ("🔍 Searching jobs...",     "#1f6feb"),
        "select_job": ("💼 Pick a job",            "#d29922"),
        "analyze":    ("📄 Upload resume",         "#d29922"),
        "results":    ("✅ Analysis complete",     "#238636"),
    }
    label, color = step_labels.get(st.session_state.step, ("Ready", "#8b949e"))
    st.markdown(f"""
    <div style="font-size:0.85rem;font-weight:600;color:{color};padding:0.5rem 0;">
      {label}
    </div>
    """, unsafe_allow_html=True)

    if st.session_state.selected_job:
        job = st.session_state.selected_job
        st.markdown(f"""
        <div class="card" style="padding:0.75rem 1rem;">
          <div style="font-size:0.7rem;color:#8b949e;text-transform:uppercase;">Selected Job</div>
          <div style="font-size:0.85rem;font-weight:600;color:#e6edf3;margin-top:0.25rem;">{job.get('title','')}</div>
          <div style="font-size:0.75rem;color:#8b949e;">{job.get('company','')}</div>
        </div>
        """, unsafe_allow_html=True)

    st.markdown("""
    <div style="font-size:0.7rem;color:#8b949e;text-align:center;margin-top:1rem;">
      Step 1: Adzuna + RapidAPI (Google Jobs)<br>
      Step 2: You pick the best fit<br>
      Step 3: Gemini analyzes your resume<br>
      <span style="color:#1f6feb;">Powered by Google Gemini + Adzuna + RapidAPI</span>
    </div>
    """, unsafe_allow_html=True)


# ── Main area ─────────────────────────────────────────────────────────────────
st.markdown("# 🤖 AI Job Search Agent")
st.markdown("<p style='color:#8b949e;margin-top:-0.5rem;'>Search real jobs · Pick your match · Get AI-powered ATS analysis & cover letter</p>", unsafe_allow_html=True)

step_indicator(st.session_state.step)

# ══════════════════════════════════════════════════════════════════════════════
# STEP 1: Search triggered from sidebar
# ══════════════════════════════════════════════════════════════════════════════
if search_clicked:
    st.session_state.job_title  = job_title_input
    st.session_state.location   = location_input
    st.session_state.experience = experience_input
    st.session_state.country    = country_code
    st.session_state.jobs = []
    st.session_state.selected_job = None
    st.session_state.analysis = None
    st.session_state.cover_letter = ""
    st.session_state.tailored_resume = ""
    st.session_state.tailored_ats = None
    st.session_state.error = None
    st.session_state.step = "search"
    st.session_state.searching = True
    # We do NOT rerun here - let it fall through to the block below

    if st.session_state.searching:
        st.session_state.searching = False
        with st.spinner(f"🔍 Searching Adzuna & RapidAPI for **{st.session_state.job_title}** positions..."):
            try:
                from utils.adzuna_client import search_adzuna
                from utils.rapidapi_client import search_jsearch
                import concurrent.futures
                
                all_jobs = []
                
                # Run both searches concurrently to save time
                with concurrent.futures.ThreadPoolExecutor(max_workers=2) as executor:
                    f_adzuna = executor.submit(
                        search_adzuna,
                        job_title=st.session_state.job_title,
                        location=st.session_state.location,
                        max_results=15, # Distribute the load
                        country=st.session_state.get('country', 'us'),
                        experience=st.session_state.experience
                    )
                    
                    f_jsearch = executor.submit(
                        search_jsearch,
                        job_title=st.session_state.job_title,
                        location=st.session_state.location,
                        max_results=15,
                        experience=st.session_state.experience,
                        country=st.session_state.get('country', 'us')
                    )
                    
                    try:
                        adzuna_jobs = f_adzuna.result()
                        all_jobs.extend(adzuna_jobs)
                    except Exception as e:
                        print(f"Adzuna fetch failed: {e}")
                        
                    try:
                        jsearch_jobs = f_jsearch.result()
                        all_jobs.extend(jsearch_jobs)
                    except Exception as e:
                        print(f"JSearch fetch failed: {e}")

                # Deduplicate by URL or exact title+company match
                seen_urls = set()
                seen_combos = set()
                unique_jobs = []
                
                for job in all_jobs:
                    url = job.get('url', '')
                    combo = f"{job.get('title', '').lower()}|{job.get('company', '').lower()}"
                    
                    if url and url in seen_urls:
                        continue
                    if combo in seen_combos:
                        continue
                        
                    seen_urls.add(url)
                    seen_combos.add(combo)
                    unique_jobs.append(job)

                # Sort by date (newest first). Both APIs provide ISO-ish strings that sort alphabetically well enough.
                # If 'posted_date' is missing, fallback to empty string (which drops to bottom when reversed).
                unique_jobs.sort(key=lambda x: str(x.get('posted_date', '')), reverse=True)

                st.session_state.jobs = unique_jobs
                st.session_state.step = "select_job"
                if not unique_jobs:
                    st.session_state.error = "No jobs found. Try a broader title or different location."
            except Exception as e:
                st.session_state.error = f"Job search failed: {e}"
                st.session_state.step = "search"
        # Search done — results stored in session state, fall through to render below


# ══════════════════════════════════════════════════════════════════════════════
# STEP 2: Show job listings — user selects one
# ══════════════════════════════════════════════════════════════════════════════
if st.session_state.step == "select_job":
    jobs = st.session_state.jobs

    if st.session_state.error:
        st.error(f"❌ {st.session_state.error}")
    elif not jobs:
        st.warning("⚠️ No jobs were returned. Try a broader title or different location.")
    else:
        st.markdown(f"### 💼 Found {len(jobs)} Jobs — Click one to analyze it")
    st.markdown("<p style='color:#8b949e;font-size:0.9rem;margin-top:-0.5rem;'>Select the job that interests you most. Your resume will be analyzed against that specific role.</p>", unsafe_allow_html=True)

    for i, job in enumerate(jobs):
        company     = job.get("company", "Unknown Company")
        title       = job.get("title", "Unknown Title")
        loc         = job.get("location", "")
        salary      = job.get("salary_display", job.get("salary", ""))
        description = job.get("description", "")
        url         = job.get("url", "")
        posted      = job.get("posted_date", "")[:10] if job.get("posted_date") else ""
        contract    = job.get("contract_type", "")
        source      = job.get("source", "Unknown")

        source_color = "#1f3a5f" if "JSearch" in source else "#1a3a2a" if "Adzuna" in source else "#3a3a3a"
        tag_color = "#79c0ff" if "JSearch" in source else "#56d364" if "Adzuna" in source else "#e6edf3"
        source_html = f'<span style="background:{source_color};color:{tag_color};padding:0.15rem 0.5rem;border-radius:4px;font-size:0.7rem;border:1px solid {tag_color};">{source}</span>'

        salary_html   = f'<span class="tag tag-green">{salary}</span>' if salary else ""
        contract_html = f'<span class="tag tag-yellow">{contract}</span>' if contract else ""
        posted_html   = f'<span style="font-size:0.75rem;color:#8b949e;">Posted: {posted}</span>' if posted else ""
        url_html      = f'<a href="{url}" target="_blank" style="color:#79c0ff;font-size:0.8rem;text-decoration:none;">View listing →</a>' if url else ""
        desc_short    = (description[:280] + "…") if len(description) > 280 else description

        st.markdown(f"""
        <div class="job-card">
          <div style="display:flex;justify-content:space-between;align-items:flex-start;flex-wrap:wrap;gap:0.5rem;">
            <div>
              <div style="font-size:1rem;font-weight:600;color:#e6edf3;">{i+1}. {title}</div>
              <div style="font-size:0.85rem;color:#8b949e;margin-top:0.15rem;">🏢 {company} &nbsp;·&nbsp; 📍 {loc}</div>
              <div style="margin-top:0.3rem;">{source_html}</div>
            </div>
            <div style="text-align:right;">
              {salary_html}{contract_html}
              <div style="margin-top:0.3rem;">{url_html}</div>
            </div>
          </div>
          {f'<div style="font-size:0.82rem;color:#8b949e;margin-top:0.75rem;line-height:1.5;">{desc_short}</div>' if desc_short else ""}
          <div style="margin-top:0.5rem;">{posted_html}</div>
        </div>
        """, unsafe_allow_html=True)

        st.button(
            f"✅ Analyze This Job",
            key=f"select_{i}",
            on_click=set_analyze_step,
            args=(job,)
        )


# ══════════════════════════════════════════════════════════════════════════════
# STEP 3: Resume input + trigger Gemini analysis
# ══════════════════════════════════════════════════════════════════════════════
if st.session_state.step == "analyze":
    job = st.session_state.selected_job

    # Show selected job summary
    st.markdown(f"""
    <div class="card card-green" style="padding:1rem 1.25rem;margin-bottom:1.25rem;">
      <div style="font-size:0.7rem;color:#8b949e;text-transform:uppercase;letter-spacing:0.05em;">Selected Job</div>
      <div style="font-size:1.05rem;font-weight:600;color:#e6edf3;margin-top:0.2rem;">{job.get('title','')}</div>
      <div style="font-size:0.85rem;color:#8b949e;">{job.get('company','')} &nbsp;·&nbsp; {job.get('location','')}</div>
    </div>
    """, unsafe_allow_html=True)

    st.markdown("### 📄 Paste Your Resume")
    resume = st.text_area(
        label="Resume text",
        height=280,
        placeholder="Paste your full resume text here. Gemini will analyze it against the selected job...",
        label_visibility="collapsed",
        key="resume_text",  # persists across step navigation
    )

    st.markdown("#### 🛠️ Analysis Options")
    col_opt1, col_opt2, col_opt3 = st.columns(3)
    with col_opt1:
        st.session_state.analyze_ats = st.checkbox("📊 ATS Score & Feedback", value=st.session_state.get("analyze_ats", True))
    with col_opt2:
        st.session_state.analyze_cover = st.checkbox("✍️ Generate Cover Letter", value=st.session_state.get("analyze_cover", True))
    with col_opt3:
        st.session_state.analyze_tailor = st.checkbox("✨ Auto-Revise Resume", value=st.session_state.get("analyze_tailor", False))

    st.markdown("<br>", unsafe_allow_html=True)

    col_btn, col_back = st.columns([2, 6])
    with col_btn:
        analyze_btn = st.button("🚀 Run Selected Analysis", type="primary",
                                use_container_width=True,
                                disabled=st.session_state.analyzing)
    with col_back:
        if st.button("← Back to Jobs"):
            st.session_state.step = "select_job"
            st.session_state.selected_job = None
            st.session_state.analyzing = False
            st.rerun()

    if analyze_btn:
        if not resume.strip():
            st.error("⚠️ Please paste your resume before running analysis.")
        else:
            # Save resume independently of widget — widget keys are cleared when
            # the widget is no longer rendered (e.g. on step change to 'results')
            st.session_state.saved_resume_text = resume
            st.session_state.analyzing = True
            with st.spinner("🤖 Gemini is analyzing your resume....."):
                try:
                    from utils.gemini_ats import GeminiATSScorer
                    from tools.gemini_tools import GeminiCoverLetterTool

                    job_desc = job.get("description", "")
                    job_title_val = job.get("title", st.session_state.job_title)
                    
                    st.session_state.analysis = None
                    st.session_state.cover_letter = ""
                    st.session_state.tailored_resume = ""
                    st.session_state.tailored_ats = None

                    # Call 1: ATS analysis
                    if st.session_state.analyze_ats:
                        scorer = GeminiATSScorer()
                        analysis = scorer.analyze_resume(
                            resume_text=resume,
                            job_title=job_title_val,
                            job_description=job_desc,
                        )
                        st.session_state.analysis = analysis

                    # Call 2: Cover letter
                    if st.session_state.analyze_cover:
                        cover_tool = GeminiCoverLetterTool()
                        cover_raw = cover_tool._run(
                            job_info=json.dumps({
                                "title": job_title_val,
                                "company": job.get("company", ""),
                                "description": job_desc,
                            }),
                            resume_text=resume,
                            ats_analysis=json.dumps(st.session_state.get("analysis", {}))
                        )
                        try:
                            cover_data = json.loads(cover_raw)
                            st.session_state.cover_letter = cover_data.get("cover_letter", cover_raw)
                        except Exception:
                            st.session_state.cover_letter = cover_raw
                            
                    # Call 3: Tailor Resume
                    if st.session_state.analyze_tailor:
                        from tools.gemini_resume_builder import GeminiResumeBuilder
                        builder = GeminiResumeBuilder()
                        st.session_state.tailored_resume = builder.build_resume(
                            resume_text=resume,
                            job_info={"title": job_title_val, "company": job.get("company", ""), "description": job_desc}
                        )
                        # Call 4: Score the tailored resume to show improvement
                        if st.session_state.tailored_resume and not st.session_state.tailored_resume.startswith("Error"):
                            scorer2 = GeminiATSScorer()
                            st.session_state.tailored_ats = scorer2.analyze_resume(
                                resume_text=st.session_state.tailored_resume,
                                job_title=job_title_val,
                                job_description=job_desc,
                            )

                    st.session_state.step = "results"
                    st.session_state.error = None

                except Exception as e:
                    st.session_state.error = str(e)
                    st.session_state.step = "results"
                finally:
                    st.session_state.analyzing = False

            st.rerun()


# ══════════════════════════════════════════════════════════════════════════════
# STEP 4: Results — ATS score + cover letter tabs
# ══════════════════════════════════════════════════════════════════════════════
if st.session_state.step == "results":
    analysis = st.session_state.analysis or {}
    cover_letter = st.session_state.cover_letter or ""
    job = st.session_state.selected_job or {}

    if st.session_state.error:
        st.error(f"❌ Analysis failed: {st.session_state.error}")
        if st.button("← Try Again"):
            st.session_state.step = "analyze"
            st.session_state.error = None
            st.rerun()
    else:
        st.success("✅ Analysis complete!")

        # Selected job banner
        st.markdown(f"""
        <div class="card card-green" style="padding:0.75rem 1.25rem;margin-bottom:1rem;">
          <div style="display:flex;justify-content:space-between;align-items:center;flex-wrap:wrap;gap:0.5rem;">
            <div>
              <span style="font-size:0.7rem;color:#8b949e;text-transform:uppercase;">Analyzed for</span>
              <div style="font-size:0.95rem;font-weight:600;color:#e6edf3;">{job.get('title','')} @ {job.get('company','')}</div>
            </div>
            <div style="display:flex;gap:0.5rem;">
              {f'<a href="{job["url"]}" target="_blank" style="background:#1f6feb;color:white;padding:0.3rem 0.8rem;border-radius:6px;font-size:0.8rem;text-decoration:none;">Apply →</a>' if job.get("url") else ""}
              <span style="background:#21262d;color:#8b949e;padding:0.3rem 0.8rem;border-radius:6px;font-size:0.8rem;">📍 {job.get('location','')}</span>
            </div>
          </div>
        </div>
        """, unsafe_allow_html=True)

        tab1, tab2, tab3 = st.tabs(["📊 ATS Analysis", "✍️ Cover Letter", "✨ Tailored Resume"])

        # ── TAB 1: ATS Analysis ───────────────────────────────────────────────
        with tab1:
            if not analysis and not st.session_state.analyze_ats:
                st.info("ATS Analysis was not requested for this job.")
            elif not analysis:
                st.warning("⚠️ No analysis returned.")
            else:
                method = analysis.get("analysis_method", "Google Gemini")
                st.markdown(f'<span class="tag tag-blue">✨ {method}</span>', unsafe_allow_html=True)
                st.markdown("### 📊 ATS Compatibility Score")

                ats_score        = analysis.get("ats_score", 0)
                keyword_match    = analysis.get("keyword_match", 0)
                interview_prob   = analysis.get("interview_probability", 0)
                market_value     = analysis.get("market_value", "")
                analysis_summary = analysis.get("analysis_summary", "")
                missing_keywords = analysis.get("missing_keywords", [])
                strengths        = analysis.get("strengths", [])
                weaknesses       = analysis.get("weaknesses", [])
                suggestions      = analysis.get("specific_suggestions", analysis.get("suggestions", []))

                # Top metrics
                c1, c2, c3, c4 = st.columns(4)
                with c1:
                    color = score_color(int(ats_score))
                    st.markdown(f"""
                    <div class="metric-box">
                      <div class="metric-label">ATS Score</div>
                      <div class="metric-value" style="color:{color};">{ats_score}</div>
                      <div class="metric-sub">/ 100</div>
                    </div>""", unsafe_allow_html=True)
                with c2:
                    color = score_color(int(keyword_match))
                    st.markdown(f"""
                    <div class="metric-box">
                      <div class="metric-label">Keyword Match</div>
                      <div class="metric-value" style="color:{color};">{keyword_match}</div>
                      <div class="metric-sub">%</div>
                    </div>""", unsafe_allow_html=True)
                with c3:
                    color = score_color(int(interview_prob))
                    st.markdown(f"""
                    <div class="metric-box">
                      <div class="metric-label">Interview Chance</div>
                      <div class="metric-value" style="color:{color};">{interview_prob}</div>
                      <div class="metric-sub">%</div>
                    </div>""", unsafe_allow_html=True)
                with c4:
                    if market_value:
                        st.markdown(f"""
                        <div class="metric-box">
                          <div class="metric-label">Market Value</div>
                          <div class="metric-value" style="font-size:1.1rem;color:#56d364;">{market_value}</div>
                          <div class="metric-sub">estimated</div>
                        </div>""", unsafe_allow_html=True)

                # Sub-scores
                sub_scores = {
                    "Formatting":  analysis.get("formatting_score"),
                    "Experience":  analysis.get("experience_score"),
                    "Education":   analysis.get("education_score"),
                    "Skills":      analysis.get("skills_score"),
                }
                real_sub = {k: v for k, v in sub_scores.items() if v is not None}
                if real_sub:
                    st.markdown("<br>", unsafe_allow_html=True)
                    with st.expander("📊 Detailed Score Breakdown", expanded=False):
                        for label, val in real_sub.items():
                            score_bar(int(val), label)

                # Summary
                if analysis_summary:
                    st.markdown(f"""
                    <div class="card card-accent" style="margin-top:1rem;">
                      <div style="font-size:0.75rem;color:#8b949e;text-transform:uppercase;margin-bottom:0.4rem;">AI Summary</div>
                      <div style="color:#e6edf3;line-height:1.6;">{analysis_summary}</div>
                    </div>
                    """, unsafe_allow_html=True)

                st.markdown("<br>", unsafe_allow_html=True)
                col_l, col_r = st.columns(2)

                with col_l:
                    st.markdown("#### 🔑 Missing Keywords")
                    if missing_keywords:
                        tags = "".join(f'<span class="tag tag-red">{kw}</span>' for kw in missing_keywords)
                        st.markdown(f'<div style="margin-top:0.5rem;">{tags}</div>', unsafe_allow_html=True)
                    else:
                        st.markdown('<span class="tag tag-green">✓ Great keyword coverage!</span>', unsafe_allow_html=True)

                with col_r:
                    st.markdown("#### ✅ Key Strengths")
                    if strengths:
                        for s in strengths:
                            st.markdown(f"""
                            <div style="display:flex;gap:0.5rem;align-items:flex-start;margin-bottom:0.4rem;">
                              <span style="color:#56d364;flex-shrink:0;">✓</span>
                              <span style="color:#e6edf3;font-size:0.9rem;">{s}</span>
                            </div>""", unsafe_allow_html=True)

                if weaknesses:
                    st.markdown("<br>", unsafe_allow_html=True)
                    st.markdown("#### ⚠️ Areas to Improve")
                    for w in weaknesses:
                        st.markdown(f"""
                        <div style="display:flex;gap:0.5rem;align-items:flex-start;margin-bottom:0.4rem;">
                          <span style="color:#d29922;flex-shrink:0;">⚠</span>
                          <span style="color:#e6edf3;font-size:0.9rem;">{w}</span>
                        </div>""", unsafe_allow_html=True)

                if suggestions:
                    st.markdown("<br>", unsafe_allow_html=True)
                    st.markdown("#### 🤖 AI Improvement Suggestions")
                    for idx, s in enumerate(suggestions, 1):
                        text = s.get("suggestion", str(s)) if isinstance(s, dict) else str(s)
                        area = s.get("area", "") if isinstance(s, dict) else ""
                        
                        # Build HTML string manually to avoid f-string indentation issues
                        area_html = f'<div style="margin-top:0.3rem;"><span class="tag tag-blue" style="font-size:0.7rem;">{area}</span></div>' if area else ""
                        
                        card_html = (
                            f'<div class="card" style="padding:0.75rem 1rem;margin-bottom:0.5rem;">'
                            f'<div style="display:flex;gap:0.75rem;align-items:flex-start;">'
                            f'<span style="background:#1f6feb;color:white;width:22px;height:22px;border-radius:50%;display:flex;align-items:center;justify-content:center;font-size:0.75rem;font-weight:700;flex-shrink:0;">{idx}</span>'
                            f'<div><span style="color:#e6edf3;font-size:0.9rem;">{text}</span>{area_html}</div>'
                            f'</div></div>'
                        )
                        st.markdown(card_html, unsafe_allow_html=True)

        # ── TAB 2: Cover Letter ───────────────────────────────────────────────
        with tab2:
            if not cover_letter and not st.session_state.analyze_cover:
                st.info("Cover Letter was not requested for this job.")
            elif not cover_letter:
                st.warning("⚠️ No cover letter was generated.")
            else:
                st.markdown("### ✍️ Generated Cover Letter")
                st.markdown(f'<div class="cover-letter">{cover_letter}</div>', unsafe_allow_html=True)
                st.markdown("<br>", unsafe_allow_html=True)
                st.download_button(
                    label="⬇️ Download Cover Letter (.txt)",
                    data=cover_letter,
                    file_name=f"cover_letter_{job.get('title','job').replace(' ', '_')}.txt",
                    mime="text/plain",
                )
                
        # ── TAB 3: Tailored Resume ───────────────────────────────────────────────
        with tab3:
            tailored = st.session_state.get("tailored_resume", "")
            tailored_ats = st.session_state.get("tailored_ats") or {}
            if not tailored:
                st.info("Auto-Revise Resume was not requested. Go back and check the box to generate a tailored ATS-optimized resume.")
            else:
                st.markdown("### ✨ Your Tailored Resume")

                # ── ATS Before / After Comparison ────────────────────────────
                orig_score    = int(analysis.get("ats_score", 0)) if analysis else None
                revised_score = int(tailored_ats.get("ats_score", 0)) if tailored_ats else None

                if revised_score is not None:
                    delta      = (revised_score - orig_score) if orig_score is not None else None
                    delta_color = "#56d364" if (delta is not None and delta >= 0) else "#da3633"
                    delta_icon  = "🎉" if (delta is not None and delta >= 5) else ("✅" if delta is not None and delta >= 0 else "⚠️")
                    delta_html  = (
                        f'<span style="background:{delta_color};color:white;padding:0.2rem 0.65rem;'
                        f'border-radius:12px;font-size:0.85rem;font-weight:700;">'
                        f'{("+" if delta >= 0 else "")}{delta} {delta_icon}</span>'
                    ) if delta is not None else ""

                    orig_color    = score_color(orig_score) if orig_score is not None else "#8b949e"
                    revised_color = score_color(revised_score)

                    orig_label_html = (
                        f'<div style="font-size:2rem;font-weight:700;color:{orig_color};">{orig_score}</div>'
                        f'<div style="font-size:0.72rem;color:#8b949e;">/ 100</div>'
                    ) if orig_score is not None else (
                        '<div style="font-size:0.85rem;color:#8b949e;">N/A<br>(ATS not run)</div>'
                    )

                    st.markdown(f"""
                    <div class="card card-accent" style="padding:1rem 1.25rem;margin-bottom:1rem;">
                      <div style="font-size:0.72rem;color:#8b949e;text-transform:uppercase;letter-spacing:0.05em;margin-bottom:0.75rem;">📈 ATS Score Improvement</div>
                      <div style="display:flex;align-items:center;gap:2rem;flex-wrap:wrap;">
                        <div style="text-align:center;">
                          <div style="font-size:0.75rem;color:#8b949e;margin-bottom:0.3rem;">Original Resume</div>
                          {orig_label_html}
                        </div>
                        <div style="font-size:1.5rem;color:#8b949e;">→</div>
                        <div style="text-align:center;">
                          <div style="font-size:0.75rem;color:#8b949e;margin-bottom:0.3rem;">Revised Resume</div>
                          <div style="font-size:2rem;font-weight:700;color:{revised_color};">{revised_score}</div>
                          <div style="font-size:0.72rem;color:#8b949e;">/ 100</div>
                        </div>
                        <div>{delta_html}</div>
                      </div>
                      <div style="margin-top:0.75rem;">
                    """ , unsafe_allow_html=True)
                    score_bar(revised_score, "Revised ATS Score")
                    if orig_score is not None:
                        score_bar(orig_score, "Original ATS Score")
                    st.markdown("</div></div>", unsafe_allow_html=True)

                st.markdown("<hr>", unsafe_allow_html=True)

                # Render the markdown directly for clean formatting
                st.markdown(tailored)

                st.markdown("<br>", unsafe_allow_html=True)
                st.download_button(
                    label="⬇️ Download Tailored Resume (.md)",
                    data=tailored,
                    file_name=f"tailored_resume_{job.get('title','job').replace(' ', '_')}.md",
                    mime="text/markdown",
                )

        # ── Generate More Panel ────────────────────────────────────────────────
        st.markdown("<br>", unsafe_allow_html=True)

        # Determine what hasn't been generated yet
        missing = []
        if not cover_letter:
            missing.append("cover_letter")
        if not st.session_state.get("tailored_resume", ""):
            missing.append("tailored_resume")

        if missing:
            st.markdown("""
            <div class="card card-accent" style="padding:1rem 1.25rem;margin-bottom:0.5rem;">
              <div style="font-size:0.8rem;color:#8b949e;text-transform:uppercase;letter-spacing:0.05em;margin-bottom:0.75rem;">
                ⚡ Generate More for This Job
              </div>
            </div>
            """, unsafe_allow_html=True)

            gen_cover  = False
            gen_tailor = False

            chk_cols = st.columns(4)
            col_i = 0
            if "cover_letter" in missing:
                with chk_cols[col_i]:
                    gen_cover = st.checkbox("✍️ Cover Letter", value=True, key="gen_cover")
                col_i += 1
            if "tailored_resume" in missing:
                with chk_cols[col_i]:
                    gen_tailor = st.checkbox("✨ Auto-Revise Resume", value=False, key="gen_tailor")

            gen_btn = st.button("▶ Generate Selected", type="primary")

            if gen_btn:
                resume_text = st.session_state.get("saved_resume_text", "")
                if not resume_text.strip():
                    st.error("⚠️ Resume text not found. Please go back and paste your resume again.")
                else:
                    job_title_val  = job.get("title", st.session_state.job_title)
                    job_desc       = job.get("description", "")
                    with st.spinner("🤖 Generating..."):
                        if gen_cover:
                            from tools.gemini_tools import GeminiCoverLetterTool
                            cover_tool = GeminiCoverLetterTool()
                            cover_raw = cover_tool._run(
                                job_info=json.dumps({
                                    "title": job_title_val,
                                    "company": job.get("company", ""),
                                    "description": job_desc,
                                }),
                                resume_text=resume_text,
                                ats_analysis=json.dumps(analysis)
                            )
                            try:
                                cover_data = json.loads(cover_raw)
                                st.session_state.cover_letter = cover_data.get("cover_letter", cover_raw)
                            except Exception:
                                st.session_state.cover_letter = cover_raw

                        if gen_tailor:
                            from tools.gemini_resume_builder import GeminiResumeBuilder
                            from utils.gemini_ats import GeminiATSScorer
                            builder = GeminiResumeBuilder()
                            st.session_state.tailored_resume = builder.build_resume(
                                resume_text=resume_text,
                                job_info={"title": job_title_val, "company": job.get("company", ""), "description": job_desc}
                            )
                            # Score the tailored resume to show improvement
                            if st.session_state.tailored_resume and not st.session_state.tailored_resume.startswith("Error"):
                                scorer2 = GeminiATSScorer()
                                st.session_state.tailored_ats = scorer2.analyze_resume(
                                    resume_text=st.session_state.tailored_resume,
                                    job_title=job_title_val,
                                    job_description=job_desc,
                                )
                    st.rerun()

        st.markdown("<br>", unsafe_allow_html=True)
        col1, col2 = st.columns([2, 6])
        with col1:
            if st.button("← Pick Another Job", use_container_width=True):
                st.session_state.step = "select_job"
                st.session_state.selected_job = None
                st.session_state.analysis = None
                st.session_state.cover_letter = ""
                st.session_state.tailored_resume = ""
                st.session_state.tailored_ats = None
                st.rerun()


# ══════════════════════════════════════════════════════════════════════════════
# STEP 1 empty state (initial load)
# ══════════════════════════════════════════════════════════════════════════════
if st.session_state.step == "search" and not st.session_state.error:
    st.markdown("""
    <div style="text-align:center;padding:4rem 2rem;">
      <div style="font-size:4rem;margin-bottom:1rem;">🤖</div>
      <div style="font-size:1.5rem;font-weight:600;color:#e6edf3;margin-bottom:0.5rem;">Ready to find your next role</div>
      <div style="color:#8b949e;max-width:500px;margin:0 auto;line-height:1.6;">
        Set your search parameters in the sidebar and click <strong>Find Jobs</strong>.<br><br>
        <span style="color:#1f6feb;">Step 1</span> — Real job listings fetched instantly from Adzuna & RapidAPI (Google Jobs)<br>
        <span style="color:#d29922;">Step 2</span> — You pick the job that fits you best<br>
        <span style="color:#238636;">Step 3</span> — Gemini analyzes your resume & writes a tailored cover letter
      </div>
    </div>
    """, unsafe_allow_html=True)

elif st.session_state.step == "search" and st.session_state.error:
    st.error(f"❌ {st.session_state.error}")