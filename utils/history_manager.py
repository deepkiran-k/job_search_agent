"""
utils/history_manager.py
Read/write helpers for search_history and analysis_history tables.

All public functions are silent — they catch and log any exception rather
than letting a DB error crash the main application flow.
"""
import json
import uuid
import logging

from utils.db import get_connection

logger = logging.getLogger(__name__)


# ── Write helpers ─────────────────────────────────────────────────────────────

def save_search(user_id: str, params: dict, results_count: int) -> None:
    """Insert one row into search_history."""
    try:
        conn = get_connection()
        conn.execute(
            """INSERT INTO search_history
               (id, user_id, job_title, company_name, location,
                country, experience, search_mode, results_count)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                str(uuid.uuid4()),
                user_id,
                params.get("job_title", ""),
                params.get("company_name", ""),
                params.get("location", ""),
                params.get("country", ""),
                params.get("experience", ""),
                params.get("search_mode", "role"),
                results_count,
            ),
        )
        conn.commit()
        conn.close()
    except Exception:
        logger.exception("save_search failed")


def save_analysis(
    user_id: str,
    job: dict,
    search_params: dict,
    analysis: dict,
    cover_letter: str,
    tailored_resume: str,
) -> None:
    """Insert one row into analysis_history."""
    try:
        ats_score             = analysis.get("overall_score") or analysis.get("ats_score")
        keyword_match         = analysis.get("keyword_match")
        interview_probability = analysis.get("interview_probability")

        conn = get_connection()
        conn.execute(
            """INSERT INTO analysis_history
               (id, user_id,
                job_title, job_company, job_location, job_url, job_source,
                ats_score, keyword_match, interview_probability,
                has_cover_letter, has_tailored_resume,
                cover_letter, tailored_resume, analysis_json,
                search_job_title, search_company, search_location,
                search_country, search_experience, search_mode)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                str(uuid.uuid4()),
                user_id,
                job.get("title", ""),
                job.get("company", ""),
                job.get("location", ""),
                job.get("url", ""),
                job.get("source", ""),
                _safe_int(ats_score),
                _safe_int(keyword_match),
                _safe_int(interview_probability),
                1 if cover_letter and cover_letter.strip() else 0,
                1 if tailored_resume and tailored_resume.strip() else 0,
                cover_letter or "",
                tailored_resume or "",
                json.dumps(analysis) if analysis else "{}",
                search_params.get("job_title", ""),
                search_params.get("company", ""),
                search_params.get("location", ""),
                search_params.get("country", ""),
                search_params.get("experience", ""),
                search_params.get("search_mode", "role"),
            ),
        )
        conn.commit()
        conn.close()
    except Exception:
        logger.exception("save_analysis failed")


# ── Read helpers ──────────────────────────────────────────────────────────────

def load_analysis_history(user_id: str, limit: int = 50) -> list[dict]:
    """Return up to *limit* analysis_history rows for *user_id*, newest first."""
    try:
        conn = get_connection()
        rows = conn.execute(
            """SELECT * FROM analysis_history
               WHERE user_id = ?
               ORDER BY created_at DESC
               LIMIT ?""",
            (user_id, limit),
        ).fetchall()
        conn.close()
        return [dict(r) for r in rows]
    except Exception:
        logger.exception("load_analysis_history failed")
        return []


def load_search_history(user_id: str, limit: int = 30) -> list[dict]:
    """Return up to *limit* search_history rows for *user_id*, newest first."""
    try:
        conn = get_connection()
        rows = conn.execute(
            """SELECT * FROM search_history
               WHERE user_id = ?
               ORDER BY created_at DESC
               LIMIT ?""",
            (user_id, limit),
        ).fetchall()
        conn.close()
        return [dict(r) for r in rows]
    except Exception:
        logger.exception("load_search_history failed")
        return []


# ── Delete helpers ────────────────────────────────────────────────────────────

def delete_analysis_record(record_id: str, user_id: str) -> None:
    """Delete a specific analysis record (user_id check prevents cross-user deletes)."""
    try:
        conn = get_connection()
        conn.execute(
            "DELETE FROM analysis_history WHERE id = ? AND user_id = ?",
            (record_id, user_id),
        )
        conn.commit()
        conn.close()
    except Exception:
        logger.exception("delete_analysis_record failed")


def delete_search_record(record_id: str, user_id: str) -> None:
    """Delete a specific search record."""
    try:
        conn = get_connection()
        conn.execute(
            "DELETE FROM search_history WHERE id = ? AND user_id = ?",
            (record_id, user_id),
        )
        conn.commit()
        conn.close()
    except Exception:
        logger.exception("delete_search_record failed")


# ── Internal helpers ──────────────────────────────────────────────────────────

def _safe_int(value) -> int | None:
    """Coerce *value* to int, returning None on failure."""
    try:
        return int(value)
    except (TypeError, ValueError):
        return None
