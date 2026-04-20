"""
tests/test_api_clients.py
Unit tests for job search API clients using mocked HTTP responses.
No real network calls or API keys are needed — all HTTP is intercepted
with unittest.mock.patch.
"""
import pytest
from unittest.mock import patch, MagicMock
from utils.exceptions import RateLimitError


# ═══════════════════════════════════════════════════════════════════════════════
# JSearch (RapidAPI) client
# ═══════════════════════════════════════════════════════════════════════════════

class TestJSearch:

    def test_no_api_key_returns_empty(self, monkeypatch):
        """Missing RAPIDAPI_KEY → graceful empty list, no crash."""
        monkeypatch.delenv("RAPIDAPI_KEY", raising=False)
        # Patch os.getenv inside the module to guarantee None (dotenv may pre-load keys)
        with patch("utils.rapidapi_client.os.getenv", return_value=None):
            from utils.rapidapi_client import search_jsearch
            result = search_jsearch("Python Developer")
        assert result == []

    def test_rate_limit_429_raises_error(self, monkeypatch):
        """HTTP 429 response → raises RateLimitError."""
        monkeypatch.setenv("RAPIDAPI_KEY", "fake-key-123")
        mock_resp = MagicMock()
        mock_resp.status_code = 429
        mock_resp.raise_for_status.side_effect = Exception("429 Too Many Requests")
        with patch("utils.rapidapi_client.requests.get", return_value=mock_resp):
            from utils.rapidapi_client import search_jsearch
            with pytest.raises(RateLimitError):
                search_jsearch("Python Developer")

    def test_maps_api_fields_to_standard_format(self, monkeypatch):
        """Valid API response → job dict has all expected standard keys."""
        monkeypatch.setenv("RAPIDAPI_KEY", "fake-key-123")
        fake_job = {
            "job_id":                       "abc123",
            "job_title":                    "Python Developer",
            "employer_name":                "Acme Corp",
            "job_city":                     "Berlin",
            "job_state":                    "Berlin",
            "job_country":                  "DE",
            "job_description":              "We are looking for a Python developer.",
            "job_apply_link":               "https://example.com/apply",
            "job_employment_type":          "FULLTIME",
            "job_posted_at_datetime_utc":   "2026-04-15T09:00:00Z",
            "job_posted_at_timestamp":      1744700000,
            "job_is_remote":                False,
            "job_min_salary":               60000,
            "job_max_salary":               80000,
            "job_highlights":               {},
        }
        mock_resp = MagicMock()
        mock_resp.json.return_value         = {"data": [fake_job]}
        mock_resp.raise_for_status          = MagicMock()
        mock_resp.status_code               = 200
        with patch("utils.rapidapi_client.requests.get", return_value=mock_resp):
            from utils.rapidapi_client import search_jsearch
            results = search_jsearch("Python Developer")

        assert len(results) == 1
        job = results[0]
        assert job["title"]   == "Python Developer"
        assert job["company"] == "Acme Corp"
        assert job["url"]     == "https://example.com/apply"
        assert job["source"]  == "JSearch (Google)"
        assert "id" in job

    def test_missing_location_does_not_crash(self, monkeypatch):
        """No city/state in API response → location field is still a string."""
        monkeypatch.setenv("RAPIDAPI_KEY", "fake-key-123")
        fake_job = {
            "job_id":                       "xyz",
            "job_title":                    "Data Scientist",
            "employer_name":                "DataCo",
            "job_city":                     "",
            "job_state":                    "",
            "job_country":                  "",
            "job_description":              "ML role",
            "job_apply_link":               "https://example.com",
            "job_employment_type":          "FULLTIME",
            "job_posted_at_datetime_utc":   "2026-04-15T09:00:00Z",
            "job_posted_at_timestamp":      0,
            "job_is_remote":                False,
            "job_highlights":               {},
        }
        mock_resp = MagicMock()
        mock_resp.json.return_value = {"data": [fake_job]}
        mock_resp.raise_for_status  = MagicMock()
        mock_resp.status_code       = 200
        with patch("utils.rapidapi_client.requests.get", return_value=mock_resp):
            from utils.rapidapi_client import search_jsearch
            results = search_jsearch("Data Scientist", location="London", country="gb")

        assert len(results) == 1
        assert isinstance(results[0]["location"], str)  # must not be None or crash


# ═══════════════════════════════════════════════════════════════════════════════
# Relative date parsing (rapidapi_client._parse_relative_date)
# ═══════════════════════════════════════════════════════════════════════════════

class TestRelativeDateParsing:

    def test_english_days_ago(self):
        """'3 days ago' → YYYY-MM-DD string (10 chars)."""
        from utils.rapidapi_client import _parse_relative_date
        result = _parse_relative_date("3 days ago")
        assert result != ""
        assert len(result) == 10

    def test_english_hours_ago(self):
        """'5 hours ago' → today's date as YYYY-MM-DD."""
        from utils.rapidapi_client import _parse_relative_date
        result = _parse_relative_date("5 hours ago")
        assert result != ""
        assert len(result) == 10

    def test_arabic_relative_date(self):
        """Arabic '٣ أيام' (3 days) → parsed correctly."""
        from utils.rapidapi_client import _parse_relative_date
        result = _parse_relative_date("قبل ٣ أيام")
        assert result != ""
        assert len(result) == 10

    def test_empty_string_returns_empty(self):
        """Empty input → empty string returned (no crash)."""
        from utils.rapidapi_client import _parse_relative_date
        assert _parse_relative_date("") == ""

    def test_unparseable_string_returns_empty(self):
        """Non-date string → empty string returned."""
        from utils.rapidapi_client import _parse_relative_date
        assert _parse_relative_date("recently posted") == ""


# ═══════════════════════════════════════════════════════════════════════════════
# Adzuna client
# ═══════════════════════════════════════════════════════════════════════════════

class TestAdzuna:

    def test_no_api_key_returns_empty(self, monkeypatch):
        """Missing ADZUNA_APP_ID / ADZUNA_APP_KEY → graceful empty list."""
        monkeypatch.delenv("ADZUNA_APP_ID",  raising=False)
        monkeypatch.delenv("ADZUNA_APP_KEY", raising=False)
        # Also patch os.getenv inside the module to guarantee the key is absent
        with patch("utils.adzuna_client.os.getenv", return_value=None):
            from utils.adzuna_client import search_adzuna
            result = search_adzuna("Python Developer")
        assert result == []

    def test_rate_limit_429_raises_error(self, monkeypatch):
        """HTTP 429 from Adzuna → raises RateLimitError."""
        monkeypatch.setenv("ADZUNA_APP_ID",  "fake-id")
        monkeypatch.setenv("ADZUNA_APP_KEY", "fake-key")

        import requests as _req
        mock_resp = MagicMock()
        mock_resp.status_code = 429
        http_err  = _req.exceptions.HTTPError(response=mock_resp)
        mock_resp.raise_for_status.side_effect = http_err

        with patch("utils.adzuna_client.requests.get", return_value=mock_resp):
            from utils.adzuna_client import search_adzuna
            with pytest.raises(RateLimitError):
                search_adzuna("Python Developer", country="us")

    def test_maps_adzuna_response_to_standard_format(self, monkeypatch):
        """Valid Adzuna response → job dict has title, company, url, source."""
        monkeypatch.setenv("ADZUNA_APP_ID",  "fake-id")
        monkeypatch.setenv("ADZUNA_APP_KEY", "fake-key")
        fake_result = {
            "id":          "az123",
            "title":       "Backend Engineer",
            "company":     {"display_name": "TechCorp"},
            "location":    {"display_name": "London"},
            "description": "Build scalable APIs.",
            "redirect_url": "https://adzuna.com/job/az123",
            "contract_type": "permanent",
            "category":    {"label": "Engineering"},
            "created":     "2026-04-14T08:00:00Z",
            "salary_min":  50000,
            "salary_max":  70000,
        }
        mock_resp = MagicMock()
        mock_resp.json.return_value         = {"results": [fake_result]}
        mock_resp.raise_for_status          = MagicMock()
        mock_resp.status_code               = 200
        with patch("utils.adzuna_client.requests.get", return_value=mock_resp):
            from utils.adzuna_client import search_adzuna
            results = search_adzuna("Backend Engineer", country="gb")

        assert len(results) == 1
        job = results[0]
        assert job["title"]   == "Backend Engineer"
        assert job["company"] == "TechCorp"
        assert job["url"]     == "https://adzuna.com/job/az123"
        assert job["source"]  == "Adzuna"
