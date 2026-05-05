"""
utils/auth.py
User authentication helpers for JobOrbit AI.

All passwords are hashed with bcrypt before storage.
No plaintext passwords ever touch the database.
"""
import uuid
import logging
import bcrypt

from utils.db import get_connection

logger = logging.getLogger(__name__)


# ── Password helpers ──────────────────────────────────────────────────────────

def hash_password(password: str) -> str:
    """Return a bcrypt hash of *password*."""
    return bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()


def verify_password(password: str, hashed: str) -> bool:
    """Return True if *password* matches the stored bcrypt *hashed* string."""
    try:
        return bcrypt.checkpw(password.encode(), hashed.encode())
    except Exception:
        return False


# ── User CRUD ─────────────────────────────────────────────────────────────────

def create_user(email: str, password: str) -> dict | None:
    """
    Insert a new user row.

    Returns the user dict ``{"id": ..., "email": ...}`` on success,
    or ``None`` if the email is already registered.
    """
    email = email.strip().lower()
    user_id = str(uuid.uuid4())
    pw_hash = hash_password(password)
    try:
        conn = get_connection()
        conn.execute(
            "INSERT INTO users (id, email, password_hash) VALUES (?, ?, ?)",
            (user_id, email, pw_hash),
        )
        conn.commit()
        conn.close()
        return {"id": user_id, "email": email}
    except Exception as exc:
        # sqlite3.IntegrityError fires when the email UNIQUE constraint fails
        logger.debug("create_user failed for %s: %s", email, exc)
        return None


def authenticate_user(email: str, password: str) -> dict | None:
    """
    Return ``{"id": ..., "email": ...}`` if credentials are valid, else ``None``.
    """
    email = email.strip().lower()
    try:
        conn = get_connection()
        row = conn.execute(
            "SELECT id, email, password_hash FROM users WHERE email = ?",
            (email,),
        ).fetchone()
        conn.close()
        if row and verify_password(password, row["password_hash"]):
            return {"id": row["id"], "email": row["email"]}
    except Exception:
        logger.exception("authenticate_user error for %s", email)
    return None


def get_user_by_email(email: str) -> dict | None:
    """Return bare user dict (no password_hash) or None."""
    email = email.strip().lower()
    try:
        conn = get_connection()
        row = conn.execute(
            "SELECT id, email FROM users WHERE email = ?", (email,)
        ).fetchone()
        conn.close()
        return dict(row) if row else None
    except Exception:
        logger.exception("get_user_by_email error")
        return None
