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

    In "company" mode, an effective query string is built before hitting
    any client, and a post-search filter removes off-company noise.

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
            all_jobs            = []
            rate_limited_source = None

            q_title   = st.session_state.job_title
            q_loc     = st.session_state.location
            q_ctry    = st.session_state.get("country", "us")
            q_exp     = st.session_state.experience
            q_en      = st.session_state.get("global_english", True)
            q_mode    = st.session_state.get("search_mode", "role")
            q_company = st.session_state.get("company_name", "").strip()

            # ── Build effective query for company mode ────────────────────────
            # "<role> at <company>" gives all sources a meaningful query even
            # when their native company filter has low recall on its own.
            # The company= kwarg below adds a second precision layer.
            if q_mode == "company" and q_company:
                role_hint       = q_title.strip()
                effective_title = (
                    f"{role_hint} at {q_company}" if role_hint
                    else f"{q_company} jobs"
                )
                company_filter = q_company
                status.update(
                    label=f"Scanning job boards for roles at {q_company}...",
                    state="running",
                )
            else:
                effective_title = q_title
                company_filter  = ""

            # ── Tier 1 ────────────────────────────────────────────────────────────
            # Role mode  : Adzuna + SerpAPI run concurrently.
            # Company mode: Adzuna + SerpAPI + JSearch all run concurrently.
            #   - SerpAPI (Google Jobs) & JSearch are the most precise sources
            #     for company searches. Running them in parallel (not sequentially)
            #     means we collect results from each before rate limits block one.
            #   - Adzuna is included as a safety net because it does not rate-limit
            #     as aggressively; the post-filter cleans any text-match noise.
            with concurrent.futures.ThreadPoolExecutor(max_workers=4) as executor:
                futures = []

                # Adzuna: always run (role mode AND company mode safety net)
                futures.append(executor.submit(
                    search_adzuna,
                    job_title=effective_title, location=q_loc,
                    max_results=20, country=q_ctry, experience=q_exp,
                    global_english=q_en, company=company_filter,
                ))
                # SerpAPI (Google Jobs): always run
                futures.append(executor.submit(
                    search_serpapi,
                    job_title=effective_title, location=q_loc,
                    max_results=20, country=q_ctry, experience=q_exp,
                    global_english=q_en, company=company_filter,
                ))
                # JSearch: run in Tier 1 for company mode (has real employer= filter)
                if q_mode == "company":
                    futures.append(executor.submit(
                        search_jsearch,
                        job_title=effective_title, location=q_loc,
                        max_results=20, experience=q_exp, country=q_ctry,
                        global_english=q_en, company=company_filter,
                    ))

                for f in futures:
                    try:
                        all_jobs.extend(f.result())
                    except RateLimitError as re:
                        rate_limited_source = re.source
                        print(f"Tier 1 rate limited: {re.source}")
                    except Exception as e:
                        print(f"Tier 1 fetch failed: {e}")

            # ── Tier 2a: JSearch (role mode only — already Tier 1 for company mode)
            if not all_jobs and q_mode != "company":
                status.update(label="Scanning job boards (JSearch)...", state="running")
                try:
                    all_jobs.extend(
                        search_jsearch(
                            job_title=effective_title, location=q_loc,
                            max_results=20, experience=q_exp, country=q_ctry,
                            global_english=q_en, company=company_filter,
                        )
                    )
                except RateLimitError as re:
                    rate_limited_source = re.source
                    print(f"Tier 2a rate limited: {re.source}")
                except Exception as e:
                    print(f"Tier 2a fetch failed: {e}")

            # ── Tier 2b: Indeed (role mode only) ────────────────────────────────
            # Indeed is excluded from company mode: its companyName scraper param
            # is not honoured by the API (confirmed from logs — it returns random
            # unrelated jobs regardless of the companyName value set).
            if not all_jobs and q_mode != "company":
                status.update(label="Scanning job boards (Indeed)...", state="running")
                try:
                    all_jobs.extend(
                        search_indeed(
                            job_title=effective_title, location=q_loc,
                            max_results=20, country=q_ctry, experience=q_exp,
                            global_english=q_en,
                        )
                    )
                except RateLimitError as re:
                    rate_limited_source = re.source
                    print(f"Tier 2b rate limited: {re.source}")
                except Exception as e:
                    print(f"Tier 2b fetch failed: {e}")

            # ── Post-search company filter (safety net) ───────────────────────
            # Only filters on the `company` field — checking the description
            # causes false positives because job descriptions routinely mention
            # competitor names, tools, and map/cloud URLs
            # (e.g. Marriott jobs contain Google Maps links, WNS jobs say
            # "Google Cloud"). The company field is the only reliable signal.
            if q_mode == "company" and company_filter:
                status.update(
                    label=f"Filtering results for {q_company}...",
                    state="running",
                )
                company_lower = company_filter.lower()
                filtered = []
                for j in all_jobs:
                    job_company = j.get("company", "").lower()
                    # Accept if the searched company name is a word-aligned
                    # substring of the job's company field.
                    # e.g. "google" matches "Google LLC", "Google India"
                    # but NOT "WNS Global Services" or "Marriott".
                    if company_lower in job_company:
                        filtered.append(j)
                    else:
                        print(f"[company-filter] dropped: '{j.get('company','')}' — '{j.get('title','')}' ({j.get('source','')})")
                all_jobs = filtered

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
                    if q_mode == "company" and q_company:
                        st.session_state.error = (
                            f"No jobs found at **{q_company}**. "
                            "Try leaving the role field empty, or check the company name spelling."
                        )
                    else:
                        st.session_state.error = (
                            "No jobs found. Try a broader title or different location."
                        )

            status.update(
                label=f"\u2713 Found {len(unique_jobs)} unique listings",
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
                "\u26a0\ufe0f **API Rate Limit Exceeded**: We've reached the search limit for "
                "this region. Please try again tomorrow or search in a different country!"
            )
        else:
            st.error(f"\u274c {st.session_state.error}")
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

        # ── Search mode toggle ────────────────────────────────────────────────
        current_mode = st.session_state.get("search_mode", "role")

        st.markdown(
            '<p style="font-size:0.78rem;font-weight:600;letter-spacing:0.05em;'
            'text-transform:uppercase;color:var(--muted);margin-bottom:0.4rem;">'
            'Search by</p>',
            unsafe_allow_html=True,
        )
        mode_col1, mode_col2, _ = st.columns([1, 1, 2])
        with mode_col1:
            if st.button(
                "\U0001f50d\u2002By Role",
                key="mode_role_btn",
                type="primary" if current_mode == "role" else "secondary",
                use_container_width=True,
            ):
                st.session_state.search_mode = "role"
                st.rerun()
        with mode_col2:
            if st.button(
                "\U0001f3e2\u2002By Company",
                key="mode_company_btn",
                type="primary" if current_mode == "company" else "secondary",
                use_container_width=True,
            ):
                st.session_state.search_mode = "company"
                st.rerun()

        st.markdown('<div style="margin-bottom:0.35rem;"></div>', unsafe_allow_html=True)

        # ── Form fields based on mode ─────────────────────────────────────────
        if current_mode == "company":
            # Company mode: company name is primary, role is optional hint
            _hero_company_name = st.text_input(
                "\U0001f3e2 Company Name",
                value=st.session_state.get("company_name", ""),
                placeholder="e.g. Google, Microsoft, BASF, McKinsey...",
            )
            _hero_title = st.text_input(
                "Role / Keyword  *(optional — leave blank for all open roles)*",
                value=st.session_state.job_title,
                placeholder="e.g. Software Engineer, Data Analyst",
            )
        else:
            # Role mode: original form, untouched
            _hero_company_name = ""
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

        # ── Search button: label reflects mode ───────────────────────────────
        if current_mode == "company":
            cname_preview = _hero_company_name.strip() or "Company"
            btn_label = f"\U0001f50d Search {cname_preview} Jobs"
        else:
            btn_label = "Search Jobs"

        if st.button(btn_label, type="primary", use_container_width=True,
                     key="hero_search_btn"):

            # Validate: company mode requires a company name
            if current_mode == "company" and not _hero_company_name.strip():
                st.error("\u26a0\ufe0f Please enter a company name to search.")
                st.stop()

            exp_map = {
                "0-1 yrs": "0-1 years", "1-3 yrs": "1-3 years",
                "3-5 yrs": "3-5 years", "5-10 yrs": "5-10 years",
                "10+ yrs": "10+ years",
            }
            st.session_state.job_title       = _hero_title
            st.session_state.company_name    = _hero_company_name.strip()
            st.session_state.search_mode     = current_mode
            st.session_state.location        = _hero_location
            st.session_state.country         = _hero_country
            st.session_state.experience      = exp_map.get(_hero_exp, "3-5 years")
            st.session_state.jobs            = []
            st.session_state.selected_job    = None
            st.session_state.analysis        = None
            st.session_state.cover_letter    = ""
            st.session_state.tailored_resume = ""
            st.session_state.tailored_ats    = None
            st.session_state.error           = None
            st.session_state.step            = "search"
            st.session_state.searching       = True
            st.rerun()

    _, col_hiw, _ = st.columns([0.15, 5, 0.15])
    with col_hiw:
        st.markdown("""
        <div class="hiw-grid">
          <div class="hiw-card">
            <div class="hiw-num">01 &mdash; Search</div>
            <div class="hiw-title">Real listings, live</div>
            <div class="hiw-desc">We scan multiple job boards simultaneously for up-to-date listings.</div>
          </div>
          <div class="hiw-card">
            <div class="hiw-num">02 &mdash; Select</div>
            <div class="hiw-title">Pick your match</div>
            <div class="hiw-desc">Your resume is analysed against that specific job description.</div>
          </div>
          <div class="hiw-card">
            <div class="hiw-num">03 &mdash; Analyse</div>
            <div class="hiw-title">AI does the work</div>
            <div class="hiw-desc">ATS score, keyword gaps, tailored resume &amp; cover letter.</div>
          </div>
        </div>
        <div style="text-align:center;margin-top:2rem;font-size:0.72rem;color:var(--muted2);letter-spacing:0.08em;text-transform:uppercase;">\u2756 Powered by AI \u2756</div>
        """, unsafe_allow_html=True)
