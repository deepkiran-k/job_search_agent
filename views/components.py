"""
views/components.py
Shared UI helpers, CSS injection, and app-wide constants for JobOrbit AI.
All HTML-rendering helpers that display API-sourced data apply `html.escape()`
to prevent XSS injection from malicious job listing content.
"""
from html import escape
import streamlit as st
import requests as _requests

# ── Lottie animation URLs ─────────────────────────────────────────────────────
LOTTIE_SEARCH_URL  = "https://lottie.host/4db68bbd-31f6-4cd8-84eb-189571e55e79/2LGBAlBYkU.json"
LOTTIE_ANALYZE_URL = "https://lottie.host/06e32af1-7e96-4ddd-8b97-57b44baed110/3rEDGfrBPu.json"

# ── Country options ───────────────────────────────────────────────────────────
COUNTRY_OPTIONS = {
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

# ── Session state defaults ────────────────────────────────────────────────────
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
    "ai_limit_hit": False,
    # ── Company search ────────────────────────────────────────────────────────
    "search_mode": "role",    # "role" | "company"  — defaults to existing behaviour
    "company_name": "",       # company filter used when search_mode == "company"
}


def reset_app_state():
    """Reset session state keys to their default values."""
    for key, val in APP_DEFAULTS.items():
        st.session_state[key] = val





def set_analyze_step(job: dict):
    """on_click callback for the 'Analyse this job' button."""
    st.session_state.selected_job = job
    st.session_state.step = "analyze"
    st.session_state.needs_enrichment = True


def load_lottie_url(url: str):
    """Fetch a Lottie JSON animation from a URL. Returns None on failure."""
    try:
        r = _requests.get(url, timeout=5)
        if r.status_code == 200:
            return r.json()
    except Exception:
        pass
    return None


# ── Score colour helpers ──────────────────────────────────────────────────────
def score_color(score: int) -> str:
    if score >= 80: return "#16A34A"
    if score >= 60: return "#D97706"
    return "#DC2626"


def score_cls(score: int) -> str:
    if score >= 80: return "metric-num-green"
    if score >= 60: return "metric-num-amber"
    return "metric-num-red"


# ── UI component renderers ────────────────────────────────────────────────────
def metric_card(value, label: str):
    """Render a single metric card with a coloured progress bar."""
    try:
        num_val = int(value)
        num_str = str(num_val)
        cls     = score_cls(num_val)
        bar_pct = min(num_val, 100)
        color   = score_color(num_val)
    except (ValueError, TypeError):
        num_str = str(value)
        cls     = "metric-num-green"
        bar_pct = 80
        color   = "#16A34A"
    st.markdown(f"""
    <div class="metric-card">
      <div class="metric-label">{label}</div>
      <div class="metric-num {cls}">{num_str}</div>
      <div class="metric-bar-bg">
        <div class="metric-bar-fill" style="width:{bar_pct}%;background:{color};"></div>
      </div>
    </div>""", unsafe_allow_html=True)


def score_bar(score: int, label: str = ""):
    """Render a labelled horizontal score bar."""
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
    """Render the sticky progress topbar with step pills and a Home button."""
    steps  = ["search", "select_job", "analyze", "results"]
    labels = ["Search", "Select job", "Analyze", "Results"]
    cur_idx = steps.index(current_step) if current_step in steps else 0
    pills_html = ""
    for i, (s, lbl) in enumerate(zip(steps, labels)):
        if i < cur_idx:     cls = "spill spill-done"
        elif i == cur_idx:  cls = "spill spill-active"
        else:               cls = "spill"
        pills_html += f'<span class="{cls}">{lbl}</span>'
        if i < len(steps) - 1:
            pills_html += '<span class="spill-sep"></span>'

    with st.container():
        c1, c2, c3 = st.columns([1, 2, 1])
        with c1:
            st.markdown(
                '<div style="display:flex;align-items:center;height:40px;color:white;'
                'font-weight:800;font-size:1.1rem;">'
                '<div style="width:10px;height:10px;background:#22C55E;border-radius:50%;'
                'margin-right:10px;box-shadow:0 0 10px rgba(34,197,94,0.5);"></div>'
                'JobOrbit AI</div>',
                unsafe_allow_html=True,
            )
        with c2:
            st.markdown(
                f'<div style="display:flex;justify-content:center;align-items:center;'
                f'height:40px;">{pills_html}</div>',
                unsafe_allow_html=True,
            )
        with c3:
            if current_step != "search" or st.session_state.error:
                if st.button("🏠 Home", key=f"top_nav_{current_step}", use_container_width=True):
                    reset_app_state()
                    st.rerun()
        st.markdown(
            '<div style="border-bottom:1px solid var(--border);margin-bottom:1.5rem;opacity:0.5;"></div>',
            unsafe_allow_html=True,
        )


def job_banner(job: dict):
    """Render the selected-job banner strip. All job fields are HTML-escaped."""
    title   = escape(str(job.get("title",   "")))
    company = escape(str(job.get("company", "")))
    loc     = escape(str(job.get("location", "")))
    sal_raw = job.get("salary_display", job.get("salary", ""))
    sal     = escape(str(sal_raw)) if sal_raw else ""

    # Only allow safe absolute URLs to prevent javascript: injection
    raw_url  = job.get("url", "")
    safe_url = raw_url if raw_url.startswith(("http://", "https://")) else ""

    url_btn    = f'<a class="apply-btn" href="{safe_url}" target="_blank">Apply now →</a>' if safe_url else ""
    loc_str    = f'<span class="tag tag-gray" style="font-size:0.72rem;">📍 {loc}</span>' if loc else ""
    salary_str = f'<span class="tag tag-green" style="font-size:0.72rem;">{sal}</span>' if sal else ""

    st.markdown(f"""
    <div class="job-banner">
      <div>
        <div class="eyebrow">Selected role</div>
        <div class="job-banner-title">{title} — {company}</div>
        <div style="margin-top:4px;">{loc_str} {salary_str}</div>
      </div>
      <div>{url_btn}</div>
    </div>
    """, unsafe_allow_html=True)


# ── CSS injection ─────────────────────────────────────────────────────────────
def inject_css():
    """Inject the full application CSS design system."""
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
