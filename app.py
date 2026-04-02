"""
AI Job Search Agent - Streamlit UI
3-step pipeline: Search → Select Job → Analyze (ATS + Cover Letter)
Gemini is called ONLY twice: once for ATS scoring, once for cover letter.
"""
# ── Lottie helpers ────────────────────────────────────────────────────────────
LOTTIE_SEARCH_URL  = "https://lottie.host/4db68bbd-31f6-4cd8-84eb-189571e55e79/2LGBAlBYkU.json"
LOTTIE_ANALYZE_URL = "https://lottie.host/06e32af1-7e96-4ddd-8b97-57b44baed110/3rEDGfrBPu.json"

import os, json
import streamlit as st
from streamlit_lottie import st_lottie
import requests as _requests
import concurrent.futures
from utils.adzuna_client import search_adzuna
from utils.rapidapi_client import search_jsearch, enrich_jsearch_jobs
from utils.serpapi_client import search_serpapi
from utils.indeed_client import search_indeed

def _load_lottie_url(url: str):
    try:
        r = _requests.get(url, timeout=5)
        if r.status_code == 200:
            return r.json()
    except Exception:
        pass
    return None

# ── Must be first Streamlit call ──────────────────────────────────────────────
st.set_page_config(
    page_title="JobOrbit AI",
    page_icon="🟢",
    layout="wide",
    initial_sidebar_state="collapsed", # Let Streamlit manage this natively
)

os.environ.setdefault("OPENAI_API_KEY", "sk-dummy-not-used-gemini-handles-llm")
from core.settings import settings

# ══════════════════════════════════════════════════════════════════════════════
# CSS
# ══════════════════════════════════════════════════════════════════════════════
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@400;500;600;700;800&family=Lora:ital,wght@0,400;0,600;1,400&display=swap');

:root {
    --bg:      #0B0E0C;
    --surface: #121814;
    --surf2:   #1A221C;
    --border:  #26332A;
    --border2: #36473A;
    --green:   #16A34A;
    --green2:  #4ADE80;
    --greenlt: rgba(22, 163, 74, 0.15);
    --text:    #EAFAEF;
    --muted:   #8A9E92;
    --muted2:  #607267;
    --amber:   #F59E0B;
    --red:     #EF4444;
    --r:       12px;
    --r-sm:    8px;
}

html, body, [class*="css"] {
    font-family: 'Plus Jakarta Sans', sans-serif;
    font-size: 15px;
    color: var(--text);
}

.stApp { background: var(--bg); color: var(--text); }

/* ── Topbar ── */
.topbar {
    display: flex; align-items: center; justify-content: space-between;
    padding: 0 1.5rem; height: 52px;
    background: var(--surface); border-bottom: 1px solid var(--border);
    position: sticky; top: 0; z-index: 100;
}
.topbar-logo { display: flex; align-items: center; gap: 7px; font-size: 0.95rem; font-weight: 700; color: var(--text); }
.logo-dot { width: 9px; height: 9px; border-radius: 50%; background: var(--green); flex-shrink:0; }
.step-pills { display: flex; align-items: center; gap: 4px; }
.spill { padding: 4px 13px; border-radius: 20px; font-size: 11px; font-weight: 600; border: 1px solid var(--border); color: var(--muted2); background: transparent; white-space: nowrap; }
.spill-active { background: var(--greenlt); color: var(--green2); border-color: #86EFAC; }
.spill-done   { background: var(--green);   color: white;         border-color: transparent; }
.spill-sep    { width: 18px; height: 1px; background: var(--border); }

/* ── Sidebar ── */
section[data-testid="stSidebar"] { background: var(--surface); border-right: 1px solid var(--border); }
section[data-testid="stSidebar"] .stMarkdown h2 { font-size: 0.75rem; font-weight: 800; letter-spacing: 0.14em; text-transform: uppercase; color: var(--green); }
section[data-testid="stSidebar"] input, section[data-testid="stSidebar"] select { background: var(--surf2) !important; border: 1px solid var(--border) !important; color: var(--text) !important; border-radius: var(--r-sm) !important; }

/* ── Cards ── */
.card { background: var(--surface); border: 1px solid var(--border); border-radius: var(--r); padding: 1.1rem 1.4rem; margin-bottom: 0.85rem; }
.card-green  { border-left: 3px solid var(--green); }
.card-accent { border-left: 3px solid #6366F1; }
.card-amber  { border-left: 3px solid var(--amber); }

/* ── Job banner ── */
.job-banner { background: var(--surf2); border: 1px solid var(--border2); border-radius: var(--r); padding: 1.1rem 1.4rem; display: flex; align-items: center; justify-content: space-between; margin-bottom: 1.5rem; flex-wrap: wrap; gap: 0.75rem; border-left: 4px solid var(--green); }
.job-banner-title { font-size: 1.05rem; font-weight: 800; color: var(--text); }
.job-banner-meta  { font-size: 0.85rem; color: var(--muted); margin-top: 4px; }
.apply-btn { background: var(--green); color: white !important; padding: 0.55rem 1.25rem; border-radius: var(--r-sm); font-size: 0.85rem; font-weight: 700; text-decoration: none !important; white-space: nowrap; transition: all 0.2s; box-shadow: 0 4px 12px rgba(22,163,74,0.2); }
.apply-btn:hover { background: var(--green2); transform: translateY(-1px); box-shadow: 0 6px 16px rgba(22,163,74,0.3); }

/* ── Metric cards ── */
.metric-row { display: grid; grid-template-columns: repeat(4, minmax(0, 1fr)); gap: 10px; margin-bottom: 1.25rem; }
.metric-card { background: var(--surf2); border-radius: var(--r-sm); padding: 1rem; text-align: center; }
.metric-num { font-size: 1.8rem; font-weight: 700; line-height: 1; margin-bottom: 2px; }
.metric-num-green { color: var(--green2); }
.metric-num-amber { color: var(--amber); }
.metric-num-red   { color: var(--red); }
.metric-label { font-size: 0.68rem; font-weight: 600; letter-spacing: 0.09em; text-transform: uppercase; color: var(--muted2); margin-bottom: 8px; }
.metric-bar-bg   { background: var(--border); border-radius: 999px; height: 4px; overflow: hidden; }
.metric-bar-fill { height: 4px; border-radius: 999px; }

/* ── Score bar ── */
.score-bar-bg  { background: var(--surf2); border-radius: 999px; height: 6px; margin-top: 0.3rem; overflow: hidden; border: 1px solid var(--border); }
.score-bar-fill { height: 6px; border-radius: 999px; }

/* ── Tags ── */
.tag { display: inline-block; padding: 0.2rem 0.65rem; border-radius: 999px; font-size: 0.72rem; font-weight: 600; margin: 0.12rem; }
.tag-green  { background: rgba(16, 185, 129, 0.15); color: #34D399;  border: 1px solid #065F46; }
.tag-blue   { background: rgba(59, 130, 246, 0.15); color: #60A5FA;  border: 1px solid #1E3A8A; }
.tag-red    { background: rgba(239, 68, 68, 0.15);  color: #F87171;  border: 1px solid #7F1D1D; }
.tag-yellow { background: rgba(245, 158, 11, 0.15); color: #FBBF24;  border: 1px solid #78350F; }
.tag-gray   { background: var(--surf2); color: var(--muted); border: 1px solid var(--border); }
.tag-source { background: rgba(59, 130, 246, 0.15); color: #60A5FA;  border: 1px solid #1E3A8A; font-size: 0.68rem; }

/* ── Job cards ── */
.job-card { background: var(--surface); border: 1px solid var(--border); border-radius: var(--r); padding: 1.1rem 1.25rem; margin-bottom: 0.6rem; transition: border-color .18s, box-shadow .18s; position: relative; overflow: hidden; }
.job-card::before { content:''; position: absolute; top:0; left:0; width:3px; height:100%; background: var(--green); opacity:0; transition: opacity .18s; }
.job-card:hover { border-color: var(--green); box-shadow: 0 4px 16px rgba(22,163,74,0.15); }
.job-card:hover::before { opacity: 1; }

/* ── Cover letter ── */
.cover-letter { background: var(--surface); border: 1px solid var(--border); border-radius: var(--r); padding: 2rem 2.25rem; white-space: pre-wrap; font-family: 'Lora', serif; font-size: 0.96rem; line-height: 1.9; color: var(--text); }

/* ── Buttons ── */
div.stButton > button { border-radius: var(--r-sm) !important; padding: 0.5rem 1.5rem !important; font-weight: 600 !important; font-size: 0.88rem !important; border: 1px solid var(--border2) !important; background: var(--surface) !important; color: var(--text) !important; font-family: 'Plus Jakarta Sans', sans-serif !important; transition: all .15s !important; }
div.stButton > button:hover { border-color: var(--green) !important; background: var(--greenlt) !important; transform: translateY(-1px) !important; }
div.stButton > button[kind="primary"] { background: var(--green) !important; border-color: var(--green) !important; color: white !important; box-shadow: 0 3px 12px rgba(22,163,74,0.28) !important; }
div.stButton > button[kind="primary"]:hover { background: var(--green2) !important; border-color: var(--green2) !important; box-shadow: 0 5px 18px rgba(22,163,74,0.36) !important; }

/* ── Inputs ── */
.stTextInput input, .stTextArea textarea { background: var(--surf2) !important; border: 1px solid var(--border) !important; color: var(--text) !important; border-radius: var(--r-sm) !important; font-family: 'Plus Jakarta Sans', sans-serif !important; }
.stTextInput input:focus, .stTextArea textarea:focus { border-color: var(--green) !important; box-shadow: 0 0 0 3px rgba(22,163,74,0.12) !important; }
label, .stTextInput label, .stTextArea label, .stSelectbox label { color: var(--muted) !important; font-size: 0.78rem !important; font-weight: 600 !important; letter-spacing: 0.05em !important; text-transform: uppercase !important; }

/* ── Tabs ── */
button[data-baseweb="tab"] { color: var(--muted) !important; font-weight: 600 !important; font-family: 'Plus Jakarta Sans', sans-serif !important; font-size: 0.88rem !important; }
button[data-baseweb="tab"][aria-selected="true"] { color: var(--green2) !important; border-bottom-color: var(--green) !important; }
div[data-testid="stTabContent"] { border: 1px solid var(--border); border-radius: 0 var(--r) var(--r) var(--r); padding: 1.25rem 1.5rem; background: var(--surface); margin-top: -1px; }

/* ── Expanders ── */
details[data-testid="stExpander"] { background: var(--surf2); border: 1px solid var(--border) !important; border-radius: var(--r-sm) !important; }
details summary { color: var(--muted) !important; font-weight: 600 !important; }

/* ── Status ── */
div[data-testid="stStatus"] { background: var(--surface) !important; border: 1px solid var(--border) !important; border-radius: var(--r) !important; }

/* ── Alerts ── */
div[data-testid="stAlert"] { border-radius: var(--r-sm) !important; font-size: 0.88rem !important; }

/* ── File uploader ── */
div[data-testid="stFileUploader"] { background: var(--surf2) !important; border: 2px dashed var(--border2) !important; border-radius: var(--r) !important; transition: border-color .18s, background .18s; }
div[data-testid="stFileUploader"]:hover { border-color: var(--green) !important; background: var(--greenlt) !important; }

/* ── Checkboxes ── */
.stCheckbox label span { color: var(--text) !important; font-size: 0.88rem !important; text-transform: none !important; letter-spacing: normal !important; }

/* ── Scrollbar ── */
::-webkit-scrollbar { width: 5px; height: 5px; }
::-webkit-scrollbar-track { background: var(--surf2); }
::-webkit-scrollbar-thumb { background: var(--border2); border-radius: 999px; }
::-webkit-scrollbar-thumb:hover { background: var(--green); }

/* ── Headings ── */
h1, h2, h3 { font-family: 'Plus Jakarta Sans', sans-serif !important; font-weight: 800 !important; color: var(--text) !important; letter-spacing: -0.02em !important; }

/* ── Hero ── */
.hero-wrap { text-align: center; padding: 3.5rem 1rem 2rem; }
.hero-badge { display: inline-block; font-size: 0.72rem; font-weight: 700; letter-spacing: 0.1em; text-transform: uppercase; color: var(--green2); background: var(--greenlt); border: 1px solid var(--border2); padding: 4px 14px; border-radius: 20px; margin-bottom: 1.25rem; }
.hero-h1 { font-family: 'Plus Jakarta Sans', sans-serif; font-size: 2.9rem; font-weight: 800; color: var(--text); line-height: 1.12; letter-spacing: -0.025em; margin-bottom: 1rem; }
.hero-h1 em { font-style: normal; color: var(--green2); }
.hero-sub { font-size: 1rem; color: var(--muted); max-width: 480px; margin: 0 auto 2.25rem; line-height: 1.7; }

/* ── How-it-works ── */
.hiw-grid { display: flex; gap: 12px; margin-top: 1.5rem; }
.hiw-card { flex: 1; background: var(--surface); border: 1px solid var(--border); border-top: 2px solid var(--green); border-radius: var(--r); padding: 1.1rem 1rem; }
.hiw-num { font-size: 0.7rem; font-weight: 800; color: var(--green); letter-spacing: 0.06em; margin-bottom: 6px; }
.hiw-title { font-size: 0.9rem; font-weight: 700; color: var(--text); margin-bottom: 4px; }
.hiw-desc { font-size: 0.82rem; color: var(--muted); line-height: 1.55; }

/* ── Eyebrow label ── */
.eyebrow { font-size: 0.68rem; font-weight: 800; letter-spacing: 0.14em; text-transform: uppercase; color: var(--muted); margin-bottom: 0.35rem; }

/* ── Row items (strengths / weaknesses / issues) ── */
.row-item { display: flex; gap: 0.6rem; align-items: flex-start; padding: 0.45rem 0.75rem; border-radius: 7px; margin-bottom: 0.4rem; font-size: 0.86rem; }
.row-item-green { background: rgba(22,163,74,0.07); border-left: 2px solid var(--green); }
.row-item-amber { background: rgba(217,119,6,0.06);  border-left: 2px solid var(--amber); }
.row-item-red   { background: rgba(220,38,38,0.06);   border-left: 2px solid var(--red); }

/* ── Suggestion badge ── */
.sug-badge { width: 20px; height: 20px; border-radius: 5px; flex-shrink: 0; background: rgba(22,163,74,0.15); color: var(--green2); font-size: 0.7rem; font-weight: 700; display: flex; align-items: center; justify-content: center; margin-top: 1px; }

/* ── HR ── */
hr { border: none !important; border-top: 1px solid var(--border) !important; margin: 1.25rem 0 !important; }

/* ── Hide Streamlit chrome ── */
#MainMenu, footer { visibility: hidden !important; }
header[data-testid="stHeader"] { background: transparent !important; height: 3.5rem !important; }
.stAppDeployButton { display: none !important; }
button[data-testid="stHeaderActionMenu"] { display: none !important; }
.block-container { padding-top: 1.5rem !important; }

/* ── Integrated Topbar ── */
.topbar-wrapper {
    background: #020617;
    border-bottom: 1px solid #1E293B;
    padding: 0.6rem 1.25rem;
    display: flex;
    align-items: center;
    justify-content: space-between;
    border-radius: 12px;
    margin-bottom: 1.5rem;
}
</style>
""", unsafe_allow_html=True)


# ══════════════════════════════════════════════════════════════════════════════
# Session state
# ══════════════════════════════════════════════════════════════════════════════
APP_DEFAULTS = {
    "step": "search",
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
    "job_title": "",
    "location": "",
    "experience": "3-5 years",
    "country": "us",
    "global_english": True,
    "parsed_file": None,
    "file_checks": None,
    "saved_resume_text": "",
    "needs_enrichment": False,
}

def reset_app_state():
    for key, val in APP_DEFAULTS.items():
        st.session_state[key] = val

for key, default in APP_DEFAULTS.items():
    if key not in st.session_state:
        st.session_state[key] = default


# ══════════════════════════════════════════════════════════════════════════════
# Helpers
# ══════════════════════════════════════════════════════════════════════════════
def score_color(score: int) -> str:
    if score >= 80: return "#16A34A"
    if score >= 60: return "#D97706"
    return "#DC2626"

def score_cls(score: int) -> str:
    if score >= 80: return "metric-num-green"
    if score >= 60: return "metric-num-amber"
    return "metric-num-red"

def metric_card(value, label: str):
    """Render a metric card replacing the Plotly gauge."""
    try:
        num_val = int(value)
        num_str = str(num_val)
        cls = score_cls(num_val)
        bar_pct = min(num_val, 100)
        color = score_color(num_val)
    except (ValueError, TypeError):
        num_str = str(value)
        cls = "metric-num-green"
        bar_pct = 80
        color = "#16A34A"
    st.markdown(f"""
    <div class="metric-card">
      <div class="metric-label">{label}</div>
      <div class="metric-num {cls}">{num_str}</div>
      <div class="metric-bar-bg">
        <div class="metric-bar-fill" style="width:{bar_pct}%;background:{color};"></div>
      </div>
    </div>""", unsafe_allow_html=True)

def score_bar(score: int, label: str = ""):
    color = score_color(score)
    st.markdown(f"""
    <div style="margin-bottom:0.5rem;">
      <div style="display:flex;justify-content:space-between;margin-bottom:0.2rem;">
        <span style="font-size:0.82rem;color:var(--muted);">{label}</span>
        <span style="font-size:0.82rem;font-weight:700;color:{color};">{score}%</span>
      </div>
      <div class="score-bar-bg">
        <div class="score-bar-fill" style="width:{score}%;background:{color};"></div>
      </div>
    </div>""", unsafe_allow_html=True)

def topbar(current_step: str):
    steps  = ["search", "select_job", "analyze", "results"]
    labels = ["Search", "Select job", "Analyze", "Results"]
    cur_idx = steps.index(current_step) if current_step in steps else 0
    pills_html = ""
    for i, (s, lbl) in enumerate(zip(steps, labels)):
        if i < cur_idx:      cls = "spill spill-done"
        elif i == cur_idx:   cls = "spill spill-active"
        else:                cls = "spill"
        pills_html += f'<span class="{cls}">{lbl}</span>'
        if i < len(steps) - 1:
            pills_html += '<span class="spill-sep"></span>'
    
    # Use 3 columns for perfect alignment within the logic
    # We use a container to apply the visual 'bar' look
    with st.container():
        c1, c2, c3 = st.columns([1, 2, 1])
        # We'll use custom HTML for the logo and pills, and a real button for the 'Home'
        with c1:
            st.markdown('<div style="display:flex;align-items:center;height:40px;color:white;font-weight:800;font-size:1.1rem;"><div style="width:10px;height:10px;background:#22C55E;border-radius:50%;margin-right:10px;box-shadow:0 0 10px rgba(34,197,94,0.5);"></div>JobOrbit AI</div>', unsafe_allow_html=True)
        with c2:
            st.markdown(f'<div style="display:flex;justify-content:center;align-items:center;height:40px;">{pills_html}</div>', unsafe_allow_html=True)
        with c3:
            if current_step != "search":
                if st.button("🏠 Home", key=f"top_nav_{current_step}", use_container_width=True):
                    reset_app_state()
                    st.rerun()
        # Add a subtle separator
        st.markdown('<div style="border-bottom:1px solid var(--border);margin-bottom:1.5rem;opacity:0.5;"></div>', unsafe_allow_html=True)

def job_banner(job: dict):
    url_btn    = f'<a class="apply-btn" href="{job["url"]}" target="_blank">Apply now →</a>' if job.get("url") else ""
    loc_str    = f'<span class="tag tag-gray" style="font-size:0.72rem;">📍 {job.get("location","")}</span>' if job.get("location") else ""
    sal        = job.get("salary_display", job.get("salary", ""))
    salary_str = f'<span class="tag tag-green" style="font-size:0.72rem;">{sal}</span>' if sal else ""
    st.markdown(f"""
    <div class="job-banner">
      <div>
        <div class="eyebrow">Selected role</div>
        <div class="job-banner-title">{job.get('title','')} — {job.get('company','')}</div>
        <div style="margin-top:4px;">{loc_str} {salary_str}</div>
      </div>
      <div>{url_btn}</div>
    </div>
    """, unsafe_allow_html=True)

def set_analyze_step(job):
    st.session_state.selected_job = job
    st.session_state.step = "analyze"
    st.session_state.needs_enrichment = True


# ══════════════════════════════════════════════════════════════════════════════
# Country options
# ══════════════════════════════════════════════════════════════════════════════
_COUNTRY_OPTIONS = {
    "us": "🇺🇸 United States", "gb": "🇬🇧 United Kingdom",
    "ca": "🇨🇦 Canada",        "au": "🇦🇺 Australia",
    "in": "🇮🇳 India",         "ae": "🇦🇪 UAE",
    "de": "🇩🇪 Germany",       "fr": "🇫🇷 France",
    "it": "🇮🇹 Italy",         "nl": "🇳🇱 Netherlands",
    "pl": "🇵🇱 Poland",        "es": "🇪🇸 Spain",
    "br": "🇧🇷 Brazil",        "mx": "🇲🇽 Mexico",
    "za": "🇿🇦 South Africa",  "nz": "🇳🇿 New Zealand",
    "sg": "🇸🇬 Singapore",     "sa": "🇸🇦 Saudi Arabia",
    "at": "🇦🇹 Austria",       "be": "🇧🇪 Belgium",
    "ch": "🇨🇭 Switzerland",    "tr": "🇹🇷 Turkey",
    "ie": "🇮🇪 Ireland",       "pt": "🇵🇹 Portugal",
    "se": "🇸🇪 Sweden",        "no": "🇳🇴 Norway",
    "dk": "🇩🇰 Denmark",       "fi": "🇫🇮 Finland",
    "il": "🇮🇱 Israel",        "jp": "🇯🇵 Japan",
    "kr": "🇰🇷 South Korea",   "ar": "🇦🇷 Argentina",
    "co": "🇨🇴 Colombia",      "ph": "🇵🇭 Philippines",
    "my": "🇲🇾 Malaysia",
}


# ══════════════════════════════════════════════════════════════════════════════
# SIDEBAR (steps 2–4)
# ══════════════════════════════════════════════════════════════════════════════
search_clicked = False
if st.session_state.step != "search":
    with st.sidebar:
        st.markdown("## 🔍 Filters")
        st.markdown('<hr style="margin:0.4rem 0 1rem;">', unsafe_allow_html=True)

        job_title_input  = st.text_input("Job Title",  value=st.session_state.job_title,  placeholder="e.g. Data Scientist")
        location_input   = st.text_input("Location",   value=st.session_state.location,   placeholder="e.g. London, Remote")
        _c_options = list(_COUNTRY_OPTIONS.keys())
        _c_idx = _c_options.index(st.session_state.get("country", "us")) if st.session_state.get("country", "us") in _c_options else 0
        country_code     = st.selectbox("Country", options=_c_options,
                                        format_func=lambda x: _COUNTRY_OPTIONS[x], index=_c_idx)
        experience_input = st.selectbox("Experience Level",
                                        ["0-1 years","1-3 years","3-5 years","5-10 years","10+ years"],
                                        index=["0-1 years","1-3 years","3-5 years","5-10 years","10+ years"].index(st.session_state.experience))
        
        search_clicked = st.button("Search Again", type="primary", use_container_width=True,
                                   disabled=st.session_state.searching)

        if st.button("New Search", use_container_width=True):
            reset_app_state()
            st.rerun()

        st.markdown('<hr style="margin:0.75rem 0;">', unsafe_allow_html=True)

        status_map = {
            "select_job": ("Pick a job to analyse", "#16A34A"),
            "analyze":    ("Upload your resume",    "#D97706"),
            "results":    ("Analysis complete ✓",   "#16A34A"),
        }
        lbl, clr = status_map.get(st.session_state.step, ("Ready", "#7BA88C"))
        st.markdown(f'<div style="font-size:0.85rem;font-weight:600;color:{clr};padding:0.25rem 0;">{lbl}</div>', unsafe_allow_html=True)

        if st.session_state.selected_job:
            j = st.session_state.selected_job
            st.markdown(f"""
            <div class="card" style="padding:0.7rem 1rem;margin-top:0.75rem;">
              <div class="eyebrow">Selected job</div>
              <div style="font-size:0.87rem;font-weight:700;color:var(--text);margin-top:3px;">{j.get('title','')}</div>
              <div style="font-size:0.78rem;color:var(--muted);">{j.get('company','')}</div>
            </div>""", unsafe_allow_html=True)

        st.markdown('<div style="font-size:0.7rem;color:var(--muted2);text-align:center;margin-top:1.5rem;">Powered by AI</div>', unsafe_allow_html=True)
else:
    job_title_input  = st.session_state.job_title
    location_input   = st.session_state.location
    country_code     = st.session_state.get("country", "us")
    experience_input = st.session_state.experience

# ══════════════════════════════════════════════════════════════════════════════
# SEARCH TRIGGER
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
    
    # CRITICAL FIX 1: Use a dedicated loading state to hide other UI elements
    st.session_state.step = "loading" 
    st.session_state.searching = True
    st.rerun()

if st.session_state.searching:
    # Keep the navigation bar visible during the load
    topbar("search") 
    
    st.markdown("<br><br>", unsafe_allow_html=True)
    
    # CRITICAL FIX 2: Isolate and center the loading animation
    _, center_col, _ = st.columns([1, 2, 1])
    
    with center_col:
        _lottie_search = _load_lottie_url(LOTTIE_SEARCH_URL)
        
        with st.status("🚀 Scanning job boards...", expanded=True) as status:
            if _lottie_search:
                st_lottie(_lottie_search, height=180)
            
            try:
                status.update(label="Fetching from primary boards...", state="running")
                all_jobs = []

                q_title = st.session_state.job_title
                q_loc = st.session_state.location
                q_ctry = st.session_state.get("country","us")
                q_exp = st.session_state.experience
                q_en = st.session_state.get("global_english", True)

                # ── Tier 1: Adzuna + SerpAPI ──
                with concurrent.futures.ThreadPoolExecutor(max_workers=3) as executor:
                    f_adzuna = executor.submit(search_adzuna, job_title=q_title, location=q_loc, max_results=20, country=q_ctry, experience=q_exp, global_english=q_en)
                    f_serpapi = executor.submit(search_serpapi, job_title=q_title, location=q_loc, max_results=20, country=q_ctry, experience=q_exp, global_english=q_en)

                    for f in [f_adzuna, f_serpapi]:
                        try: all_jobs.extend(f.result())
                        except Exception as e: print(f"Tier 1 fetch failed: {e}")

                # ── Tier 2: JSearch + Indeed ──
                if not all_jobs:
                    status.update(label="Scanning fallback boards...", state="running")
                    with concurrent.futures.ThreadPoolExecutor(max_workers=2) as executor:
                        f_jsearch = executor.submit(search_jsearch, job_title=q_title, location=q_loc, max_results=20, experience=q_exp, country=q_ctry, global_english=q_en)
                        f_indeed  = executor.submit(search_indeed,  job_title=q_title, location=q_loc, max_results=20, country=q_ctry, experience=q_exp, global_english=q_en)

                        for f in [f_jsearch, f_indeed]:
                            try: all_jobs.extend(f.result())
                            except Exception as e: print(f"Tier 2 fetch failed: {e}")

                status.update(label=f"Found {len(all_jobs)} listings — deduplicating...", state="running")
                seen_urls, seen_combos, unique_jobs = set(), set(), []
                for job in all_jobs:
                    url   = job.get("url","")
                    combo = f"{job.get('title','').lower()}|{job.get('company','').lower()}"
                    if (url and url in seen_urls) or combo in seen_combos:
                        continue
                    seen_urls.add(url); seen_combos.add(combo); unique_jobs.append(job)
                
                unique_jobs.sort(key=lambda x: x.get("posted_timestamp", 0), reverse=True)
                st.session_state.jobs = unique_jobs
                st.session_state.step = "select_job"
                
                if not unique_jobs:
                    st.session_state.error = "No jobs found. Try a broader title or different location."
                    
                status.update(label=f"✓ Found {len(unique_jobs)} unique listings", state="complete")
                
            except Exception as e:
                st.session_state.error = f"Job search failed: {e}"
                st.session_state.step = "search"
                status.update(label="Search failed", state="error")
                
    # Shutdown safely
    st.session_state.searching = False
    st.rerun()


# ══════════════════════════════════════════════════════════════════════════════
# SCREEN 1 — Hero Search
# ══════════════════════════════════════════════════════════════════════════════
if st.session_state.step == "search" and not st.session_state.error:
    topbar("search")

    st.markdown("""
    <div class="hero-wrap">
      <div class="hero-badge">AI-powered career assistant</div>
      <div class="hero-h1">Land your <em>dream job</em><br>with AI on your side</div>
      <div class="hero-sub">
        Search real listings across job boards, then let AI score your resume,
        close the keyword gaps, and write a cover letter that gets you noticed.
      </div>
    </div>
    """, unsafe_allow_html=True)

    _, col_c, _ = st.columns([0.15, 5, 0.15])
    with col_c:
        _hero_title = st.text_input("What role are you looking for?",
                                    value=st.session_state.job_title,
                                    placeholder="e.g. Data Scientist, Product Manager")
        _c1, _c2, _c3 = st.columns([1, 1, 0.75])
        with _c1:
            _hero_location = st.text_input("Location", value=st.session_state.location, placeholder="e.g. London, Remote")
        with _c2:
            _c_options = list(_COUNTRY_OPTIONS.keys())
            _c_idx = _c_options.index(st.session_state.get("country", "us")) if st.session_state.get("country", "us") in _c_options else 0
            _hero_country  = st.selectbox("Country", options=_c_options,
                                          format_func=lambda x: _COUNTRY_OPTIONS[x], index=_c_idx, key="hero_country")
        with _c3:
            _exp_opts = ["0-1 yrs", "1-3 yrs", "3-5 yrs", "5-10 yrs", "10+ yrs"]
            _exp_rev = {"0-1 years":"0-1 yrs", "1-3 years":"1-3 yrs", "3-5 years":"3-5 yrs", "5-10 years":"5-10 yrs", "10+ years":"10+ yrs"}
            _curr_exp = _exp_rev.get(st.session_state.experience, "3-5 yrs")
            _exp_idx = _exp_opts.index(_curr_exp) if _curr_exp in _exp_opts else 2
            _hero_exp = st.selectbox("Experience", _exp_opts, index=_exp_idx, key="hero_exp")


        if st.button("Search Jobs", type="primary", use_container_width=True, key="hero_search_btn"):
            exp_map = {"0-1 yrs":"0-1 years","1-3 yrs":"1-3 years","3-5 yrs":"3-5 years","5-10 yrs":"5-10 years","10+ yrs":"10+ years"}
            st.session_state.job_title  = _hero_title
            st.session_state.location   = _hero_location
            st.session_state.country    = _hero_country
            st.session_state.experience = exp_map.get(_hero_exp, "3-5 years")
            st.session_state.jobs = []
            st.session_state.selected_job = None
            st.session_state.analysis = None
            st.session_state.cover_letter = ""
            st.session_state.tailored_resume = ""
            st.session_state.tailored_ats = None
            st.session_state.error = None
            st.session_state.step = "loading"
            st.session_state.searching = True
            st.rerun()

    _, col_hiw, _ = st.columns([0.15, 5, 0.15])
    with col_hiw:
        st.markdown("""
        <div class="hiw-grid">
          <div class="hiw-card">
            <div class="hiw-num">01 — Search</div>
            <div class="hiw-title">Real listings, live</div>
            <div class="hiw-desc">We scan multiple job boards simultaneously for up-to-date listings.</div>
          </div>
          <div class="hiw-card">
            <div class="hiw-num">02 — Select</div>
            <div class="hiw-title">Pick your match</div>
            <div class="hiw-desc">Your resume is analysed against that specific job description.</div>
          </div>
          <div class="hiw-card">
            <div class="hiw-num">03 — Analyse</div>
            <div class="hiw-title">AI does the work</div>
            <div class="hiw-desc">ATS score, keyword gaps, tailored resume &amp; cover letter.</div>
          </div>
        </div>
        <div style="text-align:center;margin-top:2rem;font-size:0.72rem;color:var(--muted2);letter-spacing:0.08em;text-transform:uppercase;">✦ Powered by AI ✦</div>
        """, unsafe_allow_html=True)

elif st.session_state.step == "search" and st.session_state.error:
    topbar("search")
    st.error(f"❌ {st.session_state.error}")


# ══════════════════════════════════════════════════════════════════════════════
# SCREEN 2 — Job Listings
# ══════════════════════════════════════════════════════════════════════════════
if st.session_state.step == "select_job":
    topbar("select_job")
    jobs = st.session_state.jobs

    if st.session_state.error:
        st.error(f"❌ {st.session_state.error}")
    elif not jobs:
        st.warning("⚠️ No jobs found. Try a broader title or different location.")
        if st.button("← New Search", use_container_width=True):
            reset_app_state()
            st.rerun()
    else:
        hcol1, _ = st.columns([3, 1])
        with hcol1:
            st.markdown(f"""
            <div style="margin-bottom:0.75rem;">
              <div style="font-size:1.05rem;font-weight:800;color:var(--text);">{len(jobs)} listings found</div>
              <div style="font-size:0.82rem;color:var(--muted);margin-top:2px;">Select a role — your resume will be matched to that exact job description.</div>
            </div>""", unsafe_allow_html=True)

        for i, job in enumerate(jobs):
            company     = job.get("company", "Unknown Company")
            title       = job.get("title", "Unknown Title")
            loc         = job.get("location", "")
            salary      = job.get("salary_display", job.get("salary", ""))
            description = job.get("description", "")
            url         = job.get("url", "")
            posted      = job.get("posted_date", "") if job.get("posted_date") else ""
            contract    = job.get("contract_type", "")
            source      = job.get("source", "")

            tags_html = ""
            if salary:   tags_html += f'<span class="tag tag-green">{salary}</span>'
            if contract: tags_html += f'<span class="tag tag-yellow">{contract}</span>'
            if source:   tags_html += f'<span class="tag tag-source">{source}</span>'
            if posted:   tags_html += f'<span style="font-size:0.72rem;color:var(--muted2);margin-left:4px;">Posted {posted}</span>'

            url_html = f'<a href="{url}" target="_blank" style="font-size:0.78rem;color:var(--green2);text-decoration:none;font-weight:600;">View listing →</a>' if url else ""

            desc_html = ""
            if description:
                clean = description.replace("\n\n","\n").replace("\n"," ").strip()
                if len(clean) > 260: clean = clean[:260] + "…"
                desc_html = f'<div style="font-size:0.84rem;color:var(--muted);margin-top:0.6rem;line-height:1.55;">{clean}</div>'

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

            st.button("Analyse this job →", key=f"select_{i}", type="primary",
                      on_click=set_analyze_step, args=(job,))


# ══════════════════════════════════════════════════════════════════════════════
# SCREEN 3 — Resume Upload & Options
# ══════════════════════════════════════════════════════════════════════════════
if st.session_state.step == "analyze":
    topbar("analyze")
        
    jb = st.session_state.selected_job
    job_banner(jb)

    # ── On-demand enrichment for JSearch jobs ──
    if st.session_state.get("needs_enrichment"):
        if "JSearch" in jb.get("source", "") and len(jb.get("description", "").strip()) < 100:
            with st.spinner("📄 Fetching JSearch details..."):
                from utils.rapidapi_client import fetch_job_details
                full_desc = fetch_job_details(jb.get("id"), os.getenv("RAPIDAPI_KEY"))
                if full_desc:
                    jb["description"] = full_desc[:5000]
                    jb["is_highlights_only"] = False
                    st.session_state.selected_job = jb
        st.session_state.needs_enrichment = False
        st.rerun()

    st.markdown('<div style="font-size:0.9rem;font-weight:700;color:var(--text);margin-bottom:0.75rem;">Your resume</div>', unsafe_allow_html=True)
    upload_tab, paste_tab = st.tabs(["Upload file", "Paste text"])

    with upload_tab:
        uploaded_file = st.file_uploader(
            "Drop your resume here — PDF, DOCX or TXT",
            type=["pdf","docx","txt"], key="resume_file",
        )
        if uploaded_file:
            from utils.resume_parser import parse_resume_file
            parsed = parse_resume_file(uploaded_file)
            st.session_state.parsed_file = parsed
            st.session_state.file_checks = parsed.get("file_checks")
            file_text   = parsed.get("text","")
            file_type   = parsed.get("file_type","unknown")
            file_checks = parsed.get("file_checks",{})
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
                    st.markdown(f'<div class="row-item row-item-amber" style="margin-top:0.3rem;"><span style="color:var(--amber);flex-shrink:0;">⚠</span><span style="color:var(--text);">{issue}</span></div>', unsafe_allow_html=True)
            with st.expander("Preview extracted text", expanded=False):
                st.text(file_text[:2000] + ("..." if len(file_text) > 2000 else ""))
        else:
            st.session_state.parsed_file = None
            st.session_state.file_checks = None

    with paste_tab:
        resume = st.text_area(
            label="Resume text", height=260,
            placeholder="Paste your full resume text here…",
            label_visibility="collapsed", key="resume_text",
        )

    # AI options
    st.markdown('<div style="font-size:0.9rem;font-weight:700;color:var(--text);margin:1.1rem 0 0.6rem;">What should AI do?</div>', unsafe_allow_html=True)
    oc1, oc2, oc3 = st.columns(3)
    with oc1:
        st.session_state.analyze_ats   = st.checkbox("Resume Score & Feedback",  value=st.session_state.get("analyze_ats",    True))
        ats_cls = "opt-card" + (" opt-card-checked" if st.session_state.analyze_ats else "")
        st.markdown(f'<div class="{ats_cls}" style="border:1px solid {"#86EFAC" if st.session_state.analyze_ats else "var(--border)"};border-radius:var(--r);padding:0.75rem;margin-top:-0.4rem;background:{"var(--greenlt)" if st.session_state.analyze_ats else "var(--surface)"}"><div style="font-size:0.82rem;color:var(--muted);line-height:1.5;">ATS score, keyword gaps, sub-scores and actionable suggestions.</div></div>', unsafe_allow_html=True)
    with oc2:
        st.session_state.analyze_cover = st.checkbox("Generate Cover Letter",     value=st.session_state.get("analyze_cover",  True))
        cov_cls = "opt-card" + (" opt-card-checked" if st.session_state.analyze_cover else "")
        st.markdown(f'<div class="{cov_cls}" style="border:1px solid {"#86EFAC" if st.session_state.analyze_cover else "var(--border)"};border-radius:var(--r);padding:0.75rem;margin-top:-0.4rem;background:{"var(--greenlt)" if st.session_state.analyze_cover else "var(--surface)"}"><div style="font-size:0.82rem;color:var(--muted);line-height:1.5;">A tailored cover letter written for this exact role and company.</div></div>', unsafe_allow_html=True)
    with oc3:
        st.session_state.analyze_tailor = st.checkbox("Auto-Revise Resume",       value=st.session_state.get("analyze_tailor", False))
        tail_cls = "opt-card" + (" opt-card-checked" if st.session_state.analyze_tailor else "")
        st.markdown(f'<div class="{tail_cls}" style="border:1px solid {"#86EFAC" if st.session_state.analyze_tailor else "var(--border)"};border-radius:var(--r);padding:0.75rem;margin-top:-0.4rem;background:{"var(--greenlt)" if st.session_state.analyze_tailor else "var(--surface)"}"><div style="font-size:0.82rem;color:var(--muted);line-height:1.5;">Rewrite your resume to boost ATS score for this specific listing.</div></div>', unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)
    btn_col, back_col, _ = st.columns([2, 1, 4])
    with btn_col:
        analyze_btn = st.button("Analyse my resume →", type="primary",
                                use_container_width=True, disabled=st.session_state.analyzing)
    with back_col:
        if st.button("← Back to jobs"):
            st.session_state.step = "select_job"
            st.session_state.selected_job = None
            st.session_state.analyzing = False
            st.rerun()

    if analyze_btn:
        uploaded_text = (st.session_state.get("parsed_file") or {}).get("text","")
        pasted_text   = resume if "resume" in dir() else ""
        final_resume  = uploaded_text or pasted_text
        file_checks   = st.session_state.get("file_checks")

        if not final_resume.strip():
            st.error("Please upload a resume file or paste your resume text before running analysis.")
        else:
            st.session_state.saved_resume_text = final_resume
            st.session_state.analyzing = True
            _lottie_analyze = _load_lottie_url(LOTTIE_ANALYZE_URL)
            with st.status("Analysing your resume...", expanded=True) as status:
                if _lottie_analyze:
                    st_lottie(_lottie_analyze, height=120, key="analyze_anim")
                try:
                    from utils.gemini_ats import GeminiATSScorer
                    from tools.gemini_tools import GeminiCoverLetterTool
                    job_desc      = jb.get("description","")
                    job_title_val = jb.get("title", st.session_state.job_title)

                    st.session_state.analysis = None
                    st.session_state.cover_letter = ""
                    st.session_state.tailored_resume = ""
                    st.session_state.tailored_ats = None

                    if st.session_state.analyze_ats:
                        status.update(label="Scoring your resume…", state="running")
                        scorer = GeminiATSScorer()
                        st.session_state.analysis = scorer.analyze_resume(
                            resume_text=final_resume, job_title=job_title_val,
                            job_description=job_desc, file_checks=file_checks)
                        status.update(label="Resume scored ✓", state="running")

                    if st.session_state.analyze_cover:
                        status.update(label="Writing your cover letter…", state="running")
                        cover_tool = GeminiCoverLetterTool()
                        cover_raw  = cover_tool._run(
                            job_info=json.dumps({"title":job_title_val,"company":jb.get("company",""),"description":job_desc}),
                            resume_text=final_resume,
                            ats_analysis=json.dumps(st.session_state.get("analysis",{}))
                        )
                        try:    st.session_state.cover_letter = json.loads(cover_raw).get("cover_letter", cover_raw)
                        except: st.session_state.cover_letter = cover_raw

                    if st.session_state.analyze_tailor:
                        status.update(label="Rewriting your resume…", state="running")
                        from tools.gemini_resume_builder import GeminiResumeBuilder
                        from utils.ats_scanner import ATSScanner
                        builder = GeminiResumeBuilder()
                        st.session_state.tailored_resume = builder.build_resume(
                            resume_text=final_resume,
                            job_info={"title":job_title_val,"company":jb.get("company",""),"description":job_desc},
                            ats_results=st.session_state.get("analysis"),
                        )
                        if st.session_state.tailored_resume and not st.session_state.tailored_resume.startswith("Error"):
                            det_scanner = ATSScanner()
                            st.session_state.tailored_ats = det_scanner.scan(
                                resume_text=st.session_state.tailored_resume,
                                job_description=job_desc, job_title=job_title_val,
                            )

                    st.session_state.step  = "results"
                    st.session_state.error = None
                    status.update(label="Analysis complete ✓", state="complete")

                except Exception as e:
                    st.session_state.error = str(e)
                    st.session_state.step  = "results"
                    status.update(label="Analysis failed", state="error")
                finally:
                    st.session_state.analyzing = False
            st.rerun()


# ══════════════════════════════════════════════════════════════════════════════
# SCREEN 4 — Results
# ══════════════════════════════════════════════════════════════════════════════
if st.session_state.step == "results":
    topbar("results")
        
    analysis     = st.session_state.analysis or {}
    cover_letter = st.session_state.cover_letter or ""
    job          = st.session_state.selected_job or {}

    if st.session_state.error:
        st.error(f"Analysis failed: {st.session_state.error}")
        if st.button("← Try Again"):
            st.session_state.step  = "analyze"
            st.session_state.error = None
            st.rerun()
    else:
        job_banner(job)
        tab1, tab2, tab3 = st.tabs(["Resume Analysis", "Cover Letter", "Tailored Resume"])

        # ── TAB 1: ATS Analysis ───────────────────────────────────────────────
        with tab1:
            if not analysis and not st.session_state.analyze_ats:
                st.info("ATS analysis was not requested for this job.")
            elif not analysis:
                st.warning("No analysis data returned.")
            else:
                ats_score          = analysis.get("ats_score", 0)
                keyword_match      = analysis.get("keyword_match", 0)
                interview_prob     = analysis.get("interview_probability", 0)
                market_value       = analysis.get("market_value", "")
                analysis_summary   = analysis.get("analysis_summary", "")
                missing_keywords   = analysis.get("missing_keywords", [])
                matched_keywords   = analysis.get("matched_keywords", [])
                strengths          = analysis.get("strengths", [])
                weaknesses         = analysis.get("weaknesses", [])
                suggestions        = analysis.get("specific_suggestions", analysis.get("suggestions", []))
                detected_sections  = analysis.get("detected_sections", [])
                missing_sections   = analysis.get("missing_sections", [])
                formatting_issues  = analysis.get("formatting_issues", [])
                achievements_found = analysis.get("achievements_found", [])
                keyword_density    = analysis.get("keyword_density", 0)
                word_count         = analysis.get("word_count", 0)
                contact_info       = analysis.get("contact_info", {})
                length_feedback    = analysis.get("length_feedback", [])

                # ── 4 Metric cards (replaces Plotly gauges) ───────────────────
                st.markdown('<div class="metric-row">', unsafe_allow_html=True)
                mc1, mc2, mc3, mc4 = st.columns(4)
                with mc1: metric_card(int(ats_score),      "ATS Score")
                with mc2: metric_card(int(keyword_match),  "Keyword Match")
                with mc3: metric_card(int(interview_prob), "Interview Chance")
                with mc4:
                    if market_value:
                        st.markdown(f"""
                        <div class="metric-card">
                          <div class="metric-label">Market Value</div>
                          <div class="metric-num metric-num-green" style="font-size:1.4rem;">{market_value}</div>
                          <div style="font-size:0.72rem;color:var(--muted2);margin-top:6px;">estimated</div>
                        </div>""", unsafe_allow_html=True)
                    else:
                        metric_card(int(analysis.get("formatting_score",0)), "Formatting Score")
                st.markdown("</div>", unsafe_allow_html=True)

                # ── Sub-score breakdown ───────────────────────────────────────
                with st.expander("Score breakdown", expanded=True):
                    sub_scores = {
                        "Sections":     analysis.get("section_score", 0),
                        "Keywords":     analysis.get("keyword_match", 0),
                        "Formatting":   analysis.get("formatting_score", 0),
                        "Achievements": analysis.get("achievements_score", 0),
                        "Length":       analysis.get("length_score", 0),
                        "Contact info": analysis.get("contact_score", 0),
                    }
                    for lbl, val in sub_scores.items():
                        score_bar(int(val), lbl)
                    density_color = "#16A34A" if 1.5 <= keyword_density <= 4.0 else ("#D97706" if keyword_density > 4.0 else "#7BA88C")
                    st.markdown(f"""
                    <div style="display:flex;gap:2rem;margin-top:0.6rem;flex-wrap:wrap;">
                      <span style="font-size:0.82rem;color:var(--muted);">Word count: <strong style="color:var(--text);">{word_count}</strong></span>
                      <span style="font-size:0.82rem;color:var(--muted);">Keyword density: <strong style="color:{density_color};">{keyword_density}%</strong></span>
                    </div>""", unsafe_allow_html=True)
                    if length_feedback:
                        for fb in length_feedback:
                            st.markdown(f'<div style="font-size:0.82rem;color:var(--muted);margin-top:0.25rem;">📏 {fb}</div>', unsafe_allow_html=True)
                    contact_items = [("✓ " if p else "✗ ") + k.title() for k, p in contact_info.items()]
                    if contact_items:
                        st.markdown(f'<div style="font-size:0.82rem;color:var(--muted);margin-top:0.4rem;">Contact: {" · ".join(contact_items)}</div>', unsafe_allow_html=True)

                # ── Keywords ─────────────────────────────────────────────────
                st.markdown("<br>", unsafe_allow_html=True)
                kw_l, kw_r = st.columns(2)
                with kw_l:
                    st.markdown('<div class="eyebrow">Missing keywords</div>', unsafe_allow_html=True)
                    if missing_keywords:
                        st.markdown('<div style="margin-top:0.4rem;">' + "".join(f'<span class="tag tag-red">{kw}</span>' for kw in missing_keywords[:15]) + '</div>', unsafe_allow_html=True)
                    else:
                        st.markdown('<span class="tag tag-green">✓ Great keyword coverage!</span>', unsafe_allow_html=True)
                with kw_r:
                    st.markdown('<div class="eyebrow">Matched keywords</div>', unsafe_allow_html=True)
                    if matched_keywords:
                        st.markdown('<div style="margin-top:0.4rem;">' + "".join(f'<span class="tag tag-green">{kw}</span>' for kw in matched_keywords[:15]) + '</div>', unsafe_allow_html=True)
                    else:
                        st.markdown('<span class="tag tag-red">No keyword matches found</span>', unsafe_allow_html=True)

                # ── Sections ─────────────────────────────────────────────────
                with st.expander("Resume sections", expanded=False):
                    if detected_sections:
                        st.markdown('<div style="margin-bottom:0.4rem;"><div class="eyebrow">Detected</div>' + "".join(f'<span class="tag tag-green">{s}</span>' for s in detected_sections) + '</div>', unsafe_allow_html=True)
                    if missing_sections:
                        st.markdown('<div><div class="eyebrow">Missing</div>' + "".join(f'<span class="tag tag-red">{s}</span>' for s in missing_sections) + '</div>', unsafe_allow_html=True)
                    if not missing_sections:
                        st.markdown('<span class="tag tag-green">✓ All standard sections detected</span>', unsafe_allow_html=True)

                # ── Formatting issues ─────────────────────────────────────────
                if formatting_issues:
                    st.markdown("<br>", unsafe_allow_html=True)
                    st.markdown('<div class="eyebrow">Formatting issues</div>', unsafe_allow_html=True)
                    for issue in formatting_issues:
                        st.markdown(f'<div class="row-item row-item-amber"><span style="color:var(--amber);flex-shrink:0;">⚠</span><span style="color:var(--text);">{issue}</span></div>', unsafe_allow_html=True)

                # ── Achievements ──────────────────────────────────────────────
                if achievements_found:
                    with st.expander(f"Quantified achievements ({len(achievements_found)})", expanded=False):
                        st.markdown('<div>' + "".join(f'<span class="tag tag-blue">{a}</span>' for a in achievements_found) + '</div>', unsafe_allow_html=True)

                # ── AI Summary ────────────────────────────────────────────────
                if analysis_summary:
                    st.markdown(f"""
                    <div class="card card-accent" style="margin-top:1rem;">
                      <div class="eyebrow">AI Summary</div>
                      <div style="color:var(--text);line-height:1.7;font-size:0.9rem;margin-top:4px;">{analysis_summary}</div>
                    </div>""", unsafe_allow_html=True)

                # ── Strengths & weaknesses ────────────────────────────────────
                st.markdown("<br>", unsafe_allow_html=True)
                sw_l, sw_r = st.columns(2)
                with sw_l:
                    st.markdown('<div class="eyebrow">Strengths</div>', unsafe_allow_html=True)
                    for s in strengths:
                        st.markdown(f'<div class="row-item row-item-green"><span style="color:var(--green);font-weight:700;flex-shrink:0;">✓</span><span style="color:var(--text);">{s}</span></div>', unsafe_allow_html=True)
                with sw_r:
                    st.markdown('<div class="eyebrow">Areas to improve</div>', unsafe_allow_html=True)
                    for w in weaknesses:
                        st.markdown(f'<div class="row-item row-item-amber"><span style="color:var(--amber);font-weight:700;flex-shrink:0;">⚠</span><span style="color:var(--text);">{w}</span></div>', unsafe_allow_html=True)

                # ── Suggestions ───────────────────────────────────────────────
                if suggestions:
                    st.markdown("<br>", unsafe_allow_html=True)
                    with st.expander(f"Top {len(suggestions)} fixes", expanded=True):
                        for idx, s in enumerate(suggestions, 1):
                            text = s.get("suggestion", str(s)) if isinstance(s, dict) else str(s)
                            area = s.get("area","") if isinstance(s, dict) else ""
                            area_html = f'<span class="tag tag-blue" style="font-size:0.68rem;margin-top:3px;">{area}</span>' if area else ""
                            st.markdown(f"""
                            <div class="card" style="padding:0.6rem 0.9rem;margin-bottom:0.4rem;">
                              <div style="display:flex;gap:0.6rem;align-items:flex-start;">
                                <div class="sug-badge">{idx}</div>
                                <div><span style="color:var(--text);font-size:0.87rem;">{text}</span><div>{area_html}</div></div>
                              </div>
                            </div>""", unsafe_allow_html=True)

        # ── TAB 2: Cover Letter ───────────────────────────────────────────────
        with tab2:
            if not cover_letter and not st.session_state.analyze_cover:
                st.info("Cover letter was not requested for this job.")
            elif not cover_letter:
                st.warning("No cover letter was generated.")
            else:
                st.markdown('<div class="eyebrow" style="margin-bottom:0.75rem;">Generated cover letter</div>', unsafe_allow_html=True)
                st.markdown(f'<div class="cover-letter">{cover_letter}</div>', unsafe_allow_html=True)
                st.markdown("<br>", unsafe_allow_html=True)
                st.download_button(
                    label="Download cover letter (.txt)", data=cover_letter,
                    file_name=f"cover_letter_{job.get('title','job').replace(' ','_')}.txt",
                    mime="text/plain",
                )

        # ── TAB 3: Tailored Resume ────────────────────────────────────────────
        with tab3:
            tailored     = st.session_state.get("tailored_resume","")
            tailored_ats = st.session_state.get("tailored_ats") or {}
            if not tailored:
                st.info("Auto-Revise Resume was not requested. Go back and enable that option.")
            else:
                orig_score    = int(analysis.get("ats_score", 0)) if analysis else None
                revised_score = int(tailored_ats.get("overall_score", 0)) if tailored_ats else None

                if revised_score is not None:
                    delta       = (revised_score - orig_score) if orig_score is not None else None
                    delta_color = "#16A34A" if (delta is not None and delta >= 0) else "#DC2626"
                    delta_icon  = "🎉" if (delta is not None and delta >= 5) else ("✓" if delta is not None and delta >= 0 else "⚠")
                    delta_html  = f'<span style="background:{delta_color};color:white;padding:3px 10px;border-radius:20px;font-size:0.82rem;font-weight:700;">{("+" if delta >= 0 else "")}{delta} {delta_icon}</span>' if delta is not None else ""
                    orig_html   = f'<div style="font-size:1.8rem;font-weight:800;color:{score_color(orig_score) if orig_score else "#7BA88C"};">{orig_score}</div><div style="font-size:0.7rem;color:var(--muted2);">/ 100</div>' if orig_score is not None else '<div style="font-size:0.82rem;color:var(--muted2);">N/A</div>'

                    st.markdown(f"""
                    <div class="card card-accent" style="margin-bottom:1rem;">
                      <div class="eyebrow">Score improvement</div>
                      <div style="display:flex;align-items:center;gap:2rem;flex-wrap:wrap;margin-top:0.5rem;">
                        <div style="text-align:center;"><div style="font-size:0.72rem;color:var(--muted2);margin-bottom:4px;">Original</div>{orig_html}</div>
                        <div style="font-size:1.25rem;color:var(--border2);">→</div>
                        <div style="text-align:center;"><div style="font-size:0.72rem;color:var(--muted2);margin-bottom:4px;">Revised</div><div style="font-size:1.8rem;font-weight:800;color:{score_color(revised_score)};">{revised_score}</div><div style="font-size:0.7rem;color:var(--muted2);">/ 100</div></div>
                        <div>{delta_html}</div>
                      </div>
                      <div style="margin-top:0.75rem;">""", unsafe_allow_html=True)
                    score_bar(revised_score, "Revised ATS score")
                    if orig_score is not None:
                        score_bar(orig_score, "Original ATS score")
                    st.markdown("</div></div>", unsafe_allow_html=True)

                st.markdown("<hr>", unsafe_allow_html=True)
                st.markdown(tailored)
                st.markdown("<br>", unsafe_allow_html=True)
                dl1, dl2 = st.columns(2)
                with dl1:
                    try:
                        from utils.pdf_generator import markdown_to_pdf
                        pdf_bytes = markdown_to_pdf(tailored)
                        st.download_button("Download resume (.pdf)", data=pdf_bytes,
                                           file_name=f"tailored_resume_{job.get('title','job').replace(' ','_')}.pdf",
                                           mime="application/pdf", type="primary")
                    except Exception as e:
                        st.warning(f"PDF export failed: {e}")
                with dl2:
                    st.download_button("Download resume (.md)", data=tailored,
                                       file_name=f"tailored_resume_{job.get('title','job').replace(' ','_')}.md",
                                       mime="text/markdown")

        # ── Generate More ─────────────────────────────────────────────────────
        st.markdown("<br>", unsafe_allow_html=True)
        missing_items = []
        if not cover_letter: missing_items.append("cover_letter")
        if not st.session_state.get("tailored_resume",""): missing_items.append("tailored_resume")

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
                resume_text = st.session_state.get("saved_resume_text","")
                if not resume_text.strip():
                    st.error("Resume text not found — please go back and re-paste your resume.")
                else:
                    job_title_val = job.get("title", st.session_state.job_title)
                    job_desc      = job.get("description","")
                    with st.spinner("Generating…"):
                        if gen_cover:
                            from tools.gemini_tools import GeminiCoverLetterTool
                            cover_tool = GeminiCoverLetterTool()
                            raw = cover_tool._run(
                                job_info=json.dumps({"title":job_title_val,"company":job.get("company",""),"description":job_desc}),
                                resume_text=resume_text, ats_analysis=json.dumps(analysis)
                            )
                            try:    st.session_state.cover_letter = json.loads(raw).get("cover_letter", raw)
                            except: st.session_state.cover_letter = raw
                        if gen_tailor:
                            from tools.gemini_resume_builder import GeminiResumeBuilder
                            from utils.ats_scanner import ATSScanner
                            builder = GeminiResumeBuilder()
                            st.session_state.tailored_resume = builder.build_resume(
                                resume_text=resume_text,
                                job_info={"title":job_title_val,"company":job.get("company",""),"description":job_desc},
                                ats_results=analysis,
                            )
                            if st.session_state.tailored_resume and not st.session_state.tailored_resume.startswith("Error"):
                                det_scanner = ATSScanner()
                                st.session_state.tailored_ats = det_scanner.scan(
                                    resume_text=st.session_state.tailored_resume,
                                    job_description=job_desc, job_title=job_title_val,
                                )
                    st.rerun()

        st.markdown("<br>", unsafe_allow_html=True)
        if st.button("← Pick a different job"):
            st.session_state.step = "select_job"
            st.session_state.selected_job = None
            st.session_state.analysis = None
            st.session_state.cover_letter = ""
            st.session_state.tailored_resume = ""
            st.session_state.tailored_ats = None
            st.rerun()
