"""
views/search_view.py
Screen 1 — Hero search page + concurrent multi-source job search trigger.
"""
import concurrent.futures
import streamlit as st
from streamlit_lottie import st_lottie

from utils.adzuna_client import search_adzuna
from utils.rapidapi_client import search_jsearch
from utils.serpapi_client import search_serpapi
from utils.indeed_client import search_indeed
from utils.exceptions import RateLimitError
from views.components import (
    topbar, reset_app_state, load_lottie_url,
    LOTTIE_SEARCH_URL, COUNTRY_OPTIONS,
)


def handle_search_trigger():
    """
    Execute the tiered multi-source job search when
    st.session_state.searching is True.

    Tier 1: Adzuna + SerpAPI (primary, fee/low-cost).
    Tier 2: JSearch + Indeed (fallback, only when Tier 1 finds nothing).

    Results are deduplicated by URL and title+company combo, then sorted
    by posted_timestamp descending. Sets session state and calls st.rerun().
    """
    if not st.session_state.searching:
        return

    lottie_data = load_lottie_url(LOTTIE_SEARCH_URL)
    with st.status("Searching for jobs...", expanded=True) as status:
        if lottie_data:
            st_lottie(lottie_data, height=120, key="search_anim")

        st.session_state.jobs         = []
        st.session_state.selected_job = None
        st.session_state.analysis     = None

        try:
            status.update(label="Scanning job boards...", state="running")
            all_jobs          = []
            rate_limited_source = None

            q_title = st.session_state.job_title
            q_loc   = st.session_state.location
            q_ctry  = st.session_state.get("country", "us")
            q_exp   = st.session_state.experience
            q_en    = st.session_state.get("global_english", True)

            # ── Tier 1: Adzuna + SerpAPI ─────────────────────────────────────
            with concurrent.futures.ThreadPoolExecutor(max_workers=3) as executor:
                f_adzuna  = executor.submit(
                    search_adzuna,  job_title=q_title, location=q_loc,
                    max_results=20, country=q_ctry, experience=q_exp, global_english=q_en)
                f_serpapi = executor.submit(
                    search_serpapi, job_title=q_title, location=q_loc,
                    max_results=20, country=q_ctry, experience=q_exp, global_english=q_en)

                for f in [f_adzuna, f_serpapi]:
                    try:
                        all_jobs.extend(f.result())
                    except RateLimitError as re:
                        rate_limited_source = re.source
                        print(f"Tier 1 rate limited: {re.source}")
                    except Exception as e:
                        print(f"Tier 1 fetch failed: {e}")

            # ── Tier 2: JSearch + Indeed (fallback) ──────────────────────────
            if not all_jobs:
                status.update(label="Scanning job boards...", state="running")
                with concurrent.futures.ThreadPoolExecutor(max_workers=2) as executor:
                    f_jsearch = executor.submit(
                        search_jsearch, job_title=q_title, location=q_loc,
                        max_results=20, experience=q_exp, country=q_ctry, global_english=q_en)
                    f_indeed  = executor.submit(
                        search_indeed,  job_title=q_title, location=q_loc,
                        max_results=20, country=q_ctry, experience=q_exp, global_english=q_en)

                    for f in [f_jsearch, f_indeed]:
                        try:
                            all_jobs.extend(f.result())
                        except RateLimitError as re:
                            rate_limited_source = re.source
                            print(f"Tier 2 rate limited: {re.source}")
                        except Exception as e:
                            print(f"Tier 2 fetch failed: {e}")

            # ── Deduplicate & sort ────────────────────────────────────────────
            status.update(
                label=f"Found {len(all_jobs)} listings — deduplicating...",
                state="running",
            )
            seen_urls, seen_combos, unique_jobs = set(), set(), []
            for job in all_jobs:
                url   = job.get("url", "")
                combo = f"{job.get('title','').lower()}|{job.get('company','').lower()}"
                if (url and url in seen_urls) or combo in seen_combos:
                    continue
                seen_urls.add(url)
                seen_combos.add(combo)
                unique_jobs.append(job)

            unique_jobs.sort(key=lambda x: x.get("posted_timestamp", 0), reverse=True)
            st.session_state.jobs = unique_jobs
            st.session_state.step = "select_job"

            if not unique_jobs:
                if rate_limited_source:
                    raise RateLimitError(source=rate_limited_source)
                elif not st.session_state.error:
                    st.session_state.error = (
                        "No jobs found. Try a broader title or different location."
                    )

            status.update(
                label=f"✓ Found {len(unique_jobs)} unique listings",
                state="complete",
            )

        except RateLimitError as re:
            st.session_state.error = f"RATE_LIMIT:{re.source}"
            st.session_state.step  = "search"
            status.update(label="API Limit Reached", state="error")
        except Exception as e:
            st.session_state.error = f"Job search failed: {e}"
            st.session_state.step  = "search"
            status.update(label="Search failed", state="error")

    st.session_state.searching = False
    st.rerun()


def render():
    """Render Screen 1 — Hero search page with form and how-it-works cards."""
    topbar("search")

    # If there's an error (e.g. from a previous failed search), show it
    if st.session_state.error:
        if st.session_state.error.startswith("RATE_LIMIT:"):
            st.error(
                "⚠️ **API Rate Limit Exceeded**: We've reached the search limit for "
                "this region. Please try again tomorrow or search in a different country!"
            )
        else:
            st.error(f"❌ {st.session_state.error}")
        return

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
        _hero_title = st.text_input(
            "What role are you looking for?",
            value=st.session_state.job_title,
            placeholder="e.g. Data Scientist, Product Manager",
        )
        _c1, _c2, _c3 = st.columns([1, 1, 0.75])
        with _c1:
            _hero_location = st.text_input(
                "Location", value=st.session_state.location,
                placeholder="e.g. London, Remote",
            )
        with _c2:
            _c_options = list(COUNTRY_OPTIONS.keys())
            _c_idx = (
                _c_options.index(st.session_state.get("country", "us"))
                if st.session_state.get("country", "us") in _c_options
                else 0
            )
            _hero_country = st.selectbox(
                "Country", options=_c_options,
                format_func=lambda x: COUNTRY_OPTIONS[x],
                index=_c_idx, key="hero_country",
            )
        with _c3:
            _exp_opts = ["0-1 yrs", "1-3 yrs", "3-5 yrs", "5-10 yrs", "10+ yrs"]
            _exp_rev  = {
                "0-1 years": "0-1 yrs", "1-3 years": "1-3 yrs",
                "3-5 years": "3-5 yrs", "5-10 years": "5-10 yrs",
                "10+ years": "10+ yrs",
            }
            _curr_exp = _exp_rev.get(st.session_state.experience, "3-5 yrs")
            _exp_idx  = _exp_opts.index(_curr_exp) if _curr_exp in _exp_opts else 2
            _hero_exp = st.selectbox(
                "Experience", _exp_opts, index=_exp_idx, key="hero_exp",
            )

        if st.button("Search Jobs", type="primary", use_container_width=True,
                     key="hero_search_btn"):
            exp_map = {
                "0-1 yrs": "0-1 years", "1-3 yrs": "1-3 years",
                "3-5 yrs": "3-5 years", "5-10 yrs": "5-10 years",
                "10+ yrs": "10+ years",
            }
            st.session_state.job_title      = _hero_title
            st.session_state.location       = _hero_location
            st.session_state.country        = _hero_country
            st.session_state.experience     = exp_map.get(_hero_exp, "3-5 years")
            st.session_state.jobs           = []
            st.session_state.selected_job   = None
            st.session_state.analysis       = None
            st.session_state.cover_letter   = ""
            st.session_state.tailored_resume = ""
            st.session_state.tailored_ats   = None
            st.session_state.error          = None
            st.session_state.step           = "search"
            st.session_state.searching      = True
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
