# core/settings.py - Updated for Gemini
import os
import warnings
from dotenv import load_dotenv

warnings.filterwarnings("ignore", message="Convert_system_message_to_human will be deprecated")
load_dotenv()

# ── Patch LangChain's module-level retry decorator ───────────────────────────
# langchain-google-genai uses a module-level _create_retry_decorator function
# (not an instance method) so patching max_retries=0 on the instance has no
# effect — the library still retries forever. We patch it here at import time
# to hard-cap at 3 total attempts (1 initial + 2 retries, ~10s max wait).
try:
    import langchain_google_genai.chat_models as _lgcm
    from tenacity import (
        retry, stop_after_attempt, wait_exponential,
        retry_if_exception_type, before_sleep_log
    )
    import logging as _logging

    def _capped_retry_decorator(**kwargs):
        """3 total attempts with short backoff. Gives up fast on quota errors."""
        return retry(
            reraise=True,
            stop=stop_after_attempt(3),
            wait=wait_exponential(multiplier=1, min=1, max=4),
            retry=retry_if_exception_type(Exception),
            before_sleep=before_sleep_log(_logging.getLogger(__name__), _logging.WARNING),
        )

    # Only patch if the attribute exists (guards against future API changes)
    if hasattr(_lgcm, "_create_retry_decorator"):
        _lgcm._create_retry_decorator = _capped_retry_decorator
        print("[settings] LangChain retry decorator patched: max 3 attempts.")
    else:
        print("[settings] Warning: _create_retry_decorator not found — patch skipped.")
except Exception as _patch_err:
    print(f"[settings] Retry patch failed (non-fatal): {_patch_err}")
# ─────────────────────────────────────────────────────────────────────────────


class Settings:
    """Application settings"""

    GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY", "")
    HAS_GEMINI = bool(GOOGLE_API_KEY)

    MAX_JOBS_PER_SEARCH = 8
    CACHE_DURATION = 3600

    DATA_DIR = "data"
    OUTPUT_DIR = "outputs"

    os.makedirs(DATA_DIR, exist_ok=True)
    os.makedirs(OUTPUT_DIR, exist_ok=True)

    @classmethod
    def get_gemini_llm(cls):
        if cls.HAS_GEMINI:
            from langchain_google_genai import ChatGoogleGenerativeAI
            return ChatGoogleGenerativeAI(
                #model="gemini-3.1-flash-lite-preview",
                model="gemini-2.5-flash-lite",
                google_api_key=cls.GOOGLE_API_KEY,
                temperature=0.4,
                max_output_tokens=4096,
                max_retries=2,
                convert_system_message_to_human=True,
            )
        return None


# Singleton instance
settings = Settings()
