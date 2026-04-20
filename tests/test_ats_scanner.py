"""
tests/test_ats_scanner.py
Unit tests for utils/ats_scanner.py — the deterministic ATS scoring engine.

These tests require no API keys or network access. The scanner is stateless,
so a single module-level instance is shared across all tests.
"""
import pytest
from utils.ats_scanner import ATSScanner

scanner = ATSScanner()


# ═══════════════════════════════════════════════════════════════════════════════
# Keyword scoring
# ═══════════════════════════════════════════════════════════════════════════════

class TestKeywordScoring:

    def test_keyword_match_partial(self):
        """Resume missing some JD keywords → keyword_score below 80."""
        jd     = "Seeking a developer with Python React SQL Docker skills."
        resume = "I am a Python developer familiar with SQL and databases."
        result = scanner.scan(resume, jd, "Developer")
        assert result["keyword_score"] < 80
        # Python and SQL should match
        matched_lower = [k.lower() for k in result["matched_keywords"]]
        assert "python" in matched_lower or "sql" in matched_lower

    def test_keyword_match_high_when_all_present(self):
        """Resume containing all important JD keywords → high keyword_score."""
        jd     = "Python developer with React experience."
        resume = "Proficient Python developer. Worked with React daily."
        result = scanner.scan(resume, jd, "Python Developer")
        assert result["keyword_score"] >= 70

    def test_keyword_score_neutral_when_no_jd(self):
        """No job description supplied → keyword_score == 50 (neutral)."""
        result = scanner.scan("Some text here.", "", "")
        assert result["keyword_score"] == 50

    def test_keyword_stuffing_penalty(self):
        """Keyword density > 5% → 15-point penalty applied (score ≤ 85)."""
        jd     = "Python engineer role."
        # Repeat 'python' heavily to push density over 5 %
        resume = ("python " * 80) + "developer with some experience."
        result = scanner.scan(resume, jd, "Python")
        assert result["keyword_score"] <= 85  # 100 - 15 penalty cap

    def test_missing_keywords_populated(self):
        """Keywords in JD but absent from resume → appear in missing_keywords."""
        jd     = "We need Kubernetes and Terraform expertise."
        resume = "I am a software engineer with Python experience."
        result = scanner.scan(resume, jd, "DevOps")
        missing_lower = [k.lower() for k in result["missing_keywords"]]
        assert "kubernetes" in missing_lower or "terraform" in missing_lower


# ═══════════════════════════════════════════════════════════════════════════════
# Section detection
# ═══════════════════════════════════════════════════════════════════════════════

class TestSectionDetection:

    def test_all_standard_sections_detected(self):
        """Resume with all core sections → section_score == 100."""
        resume = (
            "Professional Summary\nI am a developer.\n\n"
            "Experience\nCompany A — 2020-present\n\n"
            "Education\nBSc Computer Science\n\n"
            "Skills\nPython, React\n\n"
            "Projects\nBuilt an app.\n\n"
            "Certifications\nAWS Certified\n"
        )
        result = scanner.scan(resume, "", "Developer")
        assert result["section_score"] == 100

    def test_missing_experience_section(self):
        """'Experience' absent → section_score < 100 and in missing_sections."""
        resume = (
            "Summary: I am a developer.\n"
            "Education: BSc Computer Science\n"
            "Skills: Python\n"
        )
        result = scanner.scan(resume, "", "Developer")
        assert result["section_score"] < 100
        assert "Experience" in result["missing_sections"]

    def test_no_sections_at_all(self):
        """Plain text with no recognisable sections → section_score ≤ 40."""
        resume = "Just some random text without any structure here."
        result = scanner.scan(resume, "", "")
        assert result["section_score"] <= 40


# ═══════════════════════════════════════════════════════════════════════════════
# Formatting checks
# ═══════════════════════════════════════════════════════════════════════════════

class TestFormattingChecks:

    def test_clean_resume_no_issues(self):
        """Well-formatted resume → formatting_issues == [] and score == 100."""
        resume = (
            "John Doe\n"
            "- Python developer\n"
            "- Led cross-functional teams\n"
            "- Deployed REST APIs\n\n"
            "Experience\nCompany A"
        )
        result = scanner.scan(resume, "", "")
        assert result["formatting_score"] == 100
        assert result["formatting_issues"] == []

    def test_pipe_table_detected(self):
        """Pipe-delimited table (3+ pipes per line) → formatting issue detected, score < 100."""
        # BAD_FORMAT_PATTERNS uses r"\|.*\|.*\|" which requires 3 pipe characters
        resume = "Name | Role | Company | Start\nJohn | Dev | ACME | 2022"
        result = scanner.scan(resume, "", "")
        assert result["formatting_score"] < 100
        assert len(result["formatting_issues"]) > 0

    def test_nonstandard_bullets_detected(self):
        """Non-ASCII bullet characters → formatting issue detected."""
        resume = "● Led team of 5\n● Delivered key project\n● Increased revenue"
        result = scanner.scan(resume, "", "")
        assert result["formatting_score"] < 100


# ═══════════════════════════════════════════════════════════════════════════════
# Achievement scoring
# ═══════════════════════════════════════════════════════════════════════════════

class TestAchievementScoring:

    def test_no_quantified_achievements(self):
        """No numbers or % → achievements_score == 20."""
        resume = "I worked on projects and delivered features at a company."
        result = scanner.scan(resume, "", "")
        assert result["achievements_score"] == 20

    def test_strong_achievements(self):
        """8+ quantified achievements → achievements_score == 100."""
        resume = (
            "Increased revenue by 35%\n"
            "Saved $1.2M in costs\n"
            "Led team of 8 engineers\n"
            "Reduced latency by 40%\n"
            "Grew user base 3x\n"
            "Delivered $500K project\n"
            "Improved test coverage by 25%\n"
            "Cut deployment time by 60%\n"
        )
        result = scanner.scan(resume, "", "")
        assert result["achievements_score"] == 100

    def test_moderate_achievements(self):
        """3 quantified achievements → achievements_score == 70."""
        resume = "Increased revenue by 20%. Saved $50K. Led a team of 5."
        result = scanner.scan(resume, "", "")
        assert result["achievements_score"] == 70


# ═══════════════════════════════════════════════════════════════════════════════
# Length scoring
# ═══════════════════════════════════════════════════════════════════════════════

class TestLengthScoring:

    def test_optimal_length(self):
        """300–800 word resume with proper line breaks → length_score == 100.

        The scanner applies a 20-point penalty for word_count > 200 AND
        line_count < 10, so the resume must have enough newlines.
        """
        resume = "\n".join(["This is a word." for _ in range(100)])  # 100 lines, ~500 words
        result = scanner.scan(resume, "", "")
        assert result["length_score"] == 100

    def test_too_short(self):
        """Under 150 words → length_score == 30."""
        resume = " ".join(["word"] * 100)
        result = scanner.scan(resume, "", "")
        assert result["length_score"] == 30

    def test_too_long(self):
        """Over 1200 words with many line breaks → length_score == 50."""
        resume = "\n".join(["word " * 10 for _ in range(200)])  # 2000 words, 200 lines
        result = scanner.scan(resume, "", "")
        assert result["length_score"] == 50


# ═══════════════════════════════════════════════════════════════════════════════
# Contact info scoring
# ═══════════════════════════════════════════════════════════════════════════════

class TestContactInfoScoring:

    def test_contact_full(self):
        """Email + phone + LinkedIn → contact_score == 100."""
        resume = "john@example.com | +44 7700 900000 | linkedin.com/in/johndoe"
        result = scanner.scan(resume, "", "")
        assert result["contact_score"] == 100
        assert result["contact_info"]["email"]   is True
        assert result["contact_info"]["phone"]   is True
        assert result["contact_info"]["linkedin"] is True

    def test_contact_email_only(self):
        """Only email detected → contact_score == 40."""
        resume = "Contact me at jane@example.com for more information."
        result = scanner.scan(resume, "", "")
        assert result["contact_score"] == 40
        assert result["contact_info"]["email"] is True
        assert result["contact_info"]["phone"] is False

    def test_contact_none(self):
        """No contact details → contact_score == 0."""
        resume = "Just professional experience without any contact details."
        result = scanner.scan(resume, "", "")
        assert result["contact_score"] == 0


# ═══════════════════════════════════════════════════════════════════════════════
# Overall weighted score
# ═══════════════════════════════════════════════════════════════════════════════

class TestOverallScore:

    def test_overall_score_equals_weighted_sum(self):
        """overall_score must equal the weighted sum of all sub-scores."""
        jd     = "Python developer needed."
        resume = (
            "john@example.com | +1 555-1234 | linkedin.com/in/john\n\n"
            "Summary\nExperienced Python developer.\n\n"
            "Experience\nCompany A\n- Increased revenue 30%\n\n"
            "Education\nBSc Computer Science\n\n"
            "Skills\nPython\n"
        )
        result  = scanner.scan(resume, jd, "Python Developer")
        weights = ATSScanner.WEIGHTS
        expected = int(round(
            result["section_score"]      * weights["section"]
            + result["keyword_score"]    * weights["keyword"]
            + result["formatting_score"] * weights["formatting"]
            + result["achievements_score"] * weights["achievements"]
            + result["length_score"]     * weights["length"]
            + result["contact_score"]    * weights["contact"]
        ))
        assert result["overall_score"] == expected

    def test_overall_score_range(self):
        """overall_score must always be in [0, 100]."""
        resume = "Some text."
        result  = scanner.scan(resume, "python", "Dev")
        assert 0 <= result["overall_score"] <= 100
