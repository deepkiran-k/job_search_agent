"""
utils/db.py
SQLite bootstrap and connection factory for JobOrbit AI.

Resolves the DB path to  <project_root>/data/jobsearch.db
and creates all tables on first call to init_db().
"""
import os
import sqlite3
import logging

logger = logging.getLogger(__name__)

# ── DB path ───────────────────────────────────────────────────────────────────
_HERE     = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_DATA_DIR = os.path.join(_HERE, "data")
DB_PATH   = os.path.join(_DATA_DIR, "jobsearch.db")


def get_connection() -> sqlite3.Connection:
    """Return a SQLite connection with row_factory set to sqlite3.Row."""
    os.makedirs(_DATA_DIR, exist_ok=True)
    conn = sqlite3.connect(DB_PATH, check_same_thread=False, timeout=5)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL;")   # safer for concurrent Streamlit reruns
    conn.execute("PRAGMA foreign_keys=ON;")
    return conn


# ── Schema ────────────────────────────────────────────────────────────────────
_SCHEMA = """
CREATE TABLE IF NOT EXISTS users (
    id            TEXT PRIMARY KEY,
    email         TEXT UNIQUE NOT NULL,
    password_hash TEXT NOT NULL,
    created_at    TEXT DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS search_history (
    id            TEXT PRIMARY KEY,
    user_id       TEXT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    created_at    TEXT DEFAULT (datetime('now')),
    job_title     TEXT,
    company_name  TEXT,
    location      TEXT,
    country       TEXT,
    experience    TEXT,
    search_mode   TEXT,
    results_count INTEGER
);

CREATE TABLE IF NOT EXISTS analysis_history (
    id                    TEXT PRIMARY KEY,
    user_id               TEXT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    created_at            TEXT DEFAULT (datetime('now')),
    job_title             TEXT,
    job_company           TEXT,
    job_location          TEXT,
    job_url               TEXT,
    job_source            TEXT,
    ats_score             INTEGER,
    keyword_match         INTEGER,
    interview_probability INTEGER,
    has_cover_letter      INTEGER DEFAULT 0,
    has_tailored_resume   INTEGER DEFAULT 0,
    cover_letter          TEXT,
    tailored_resume       TEXT,
    analysis_json         TEXT,
    search_job_title      TEXT,
    search_company        TEXT,
    search_location       TEXT,
    search_country        TEXT,
    search_experience     TEXT,
    search_mode           TEXT
);

CREATE INDEX IF NOT EXISTS idx_search_user
    ON search_history(user_id, created_at DESC);

CREATE INDEX IF NOT EXISTS idx_analysis_user
    ON analysis_history(user_id, created_at DESC);
"""


def init_db() -> None:
    """
    Create all tables and indexes if they don't exist.
    Safe to call multiple times (idempotent).
    Intended to be wrapped in @st.cache_resource in app.py.
    """
    try:
        conn = get_connection()
        conn.executescript(_SCHEMA)
        conn.commit()
        conn.close()
        logger.info("DB initialised at %s", DB_PATH)
    except Exception:
        logger.exception("Failed to initialise DB")
