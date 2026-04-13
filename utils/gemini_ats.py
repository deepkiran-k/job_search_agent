# utils/gemini_ats.py - ATS SCORING: Deterministic scores + Gemini qualitative analysis
import json
import re
import concurrent.futures
from core.settings import settings
from langchain_core.messages import SystemMessage, HumanMessage
from utils.ats_scanner import ATSScanner
from utils.exceptions import RateLimitError
try:
    from google.api_core.exceptions import ResourceExhausted as _ResourceExhausted
except ImportError:
    _ResourceExhausted = None

_GEMINI_TIMEOUT = 25  # seconds — gives 3 retries ~10s total, aborts the rest


def _invoke_llm(llm, messages):
    """Call llm.invoke() in a thread with a hard timeout.
    Raises RateLimitError if the call hangs beyond _GEMINI_TIMEOUT seconds
    (covers cases where the tenacity patch doesn't fully stop retries)."""
    with concurrent.futures.ThreadPoolExecutor(max_workers=1) as pool:
        future = pool.submit(llm.invoke, messages)
        try:
            return future.result(timeout=_GEMINI_TIMEOUT)
        except concurrent.futures.TimeoutError:
            raise RateLimitError(source="Google Gemini AI (timeout)")


class GeminiATSScorer:
    """
    Hybrid ATS analysis:
    - Deterministic ATSScanner provides all numerical scores
    - Gemini provides qualitative improvement suggestions based on those scores
    """
    
    def __init__(self):
        """Initialize Gemini LLM and deterministic scanner"""
        self.llm = settings.get_gemini_llm()
        self.scanner = ATSScanner()
    
    def analyze_resume(self, resume_text, job_title, job_description=None, file_checks=None):
        """
        1. Run deterministic ATS scan (scores)
        2. Send scan results to Gemini for qualitative analysis (suggestions)
        3. Return merged result
        """
        # Create default job description if none provided
        if not job_description:
            job_description = f"We are looking for a {job_title} with relevant experience in the field."
        
        # ── Step 1: Deterministic scan ────────────────────────────────────────
        # This always runs and provides the core scores
        det = self.scanner.scan(resume_text, job_description, job_title, file_checks=file_checks)
        
        # ── Step 2: Gemini qualitative analysis ───────────────────────────────
        method = "Deterministic ATS Scan + Gemini AI Analysis"
        ai_limit_hit = False
        try:
            gemini_analysis = self._get_gemini_analysis(resume_text, job_title, job_description, det, file_checks)
        except RateLimitError as re:
            print(f"Fallback triggered: {re.source} is rate limited.")
            ai_limit_hit = True
            gemini_analysis = self._qualitative_fallback(det)
            gemini_analysis["analysis_summary"] = ""
            method = "Deterministic ATS Scan (AI Fallback)"
        except Exception as e:
            print(f"Fallback triggered due to unexpected error: {e}")
            ai_limit_hit = True
            gemini_analysis = self._qualitative_fallback(det)
            gemini_analysis["analysis_summary"] = (
                "⚠️ **AI ANALYSIS UNAVAILABLE**\n\n"
                "An error occurred during AI analysis. Your core ATS scores are still accurate "
                "(calculated locally). Please try again in a moment."
            )
            method = "Deterministic ATS Scan (AI Fallback)"
        
        # ── Step 3: Merge into final result ───────────────────────────────────
        result = {
            # Deterministic scores (these are the "official" scores)
            "ats_score":          det["overall_score"],
            "keyword_match":      det["keyword_score"],
            "formatting_score":   det["formatting_score"],
            "achievements_score": det["achievements_score"],
            "section_score":      det["section_score"],
            "length_score":       det["length_score"],
            "contact_score":      det["contact_score"],
            
            # Deterministic details
            "matched_keywords":   det["matched_keywords"],
            "missing_keywords":   det["missing_keywords"],
            "keyword_density":    det["keyword_density"],
            "detected_sections":  det["detected_sections"],
            "missing_sections":   det["missing_sections"],
            "formatting_issues":  det["formatting_issues"],
            "achievements_found": det["achievements_found"],
            "word_count":         det["word_count"],
            "contact_info":       det["contact_info"],
            "length_feedback":    det["length_feedback"],
            
            # Gemini/Fallback qualitative analysis
            "strengths":            gemini_analysis.get("strengths", []),
            "weaknesses":           gemini_analysis.get("weaknesses", []),
            "specific_suggestions": gemini_analysis.get("specific_suggestions", []),
            "analysis_summary":     gemini_analysis.get("analysis_summary", ""),
            "interview_probability": gemini_analysis.get("interview_probability", max(20, det["overall_score"] - 15)),
            "market_value":         gemini_analysis.get("market_value", ""),
            
            # Metadata
            "analysis_method": method,
            "job_title": job_title,
            "ai_limit_hit": ai_limit_hit,
        }
        
        return result

    def _get_gemini_analysis(self, resume_text, job_title, job_description, det_results, file_checks=None):
        """Ask Gemini for qualitative improvement suggestions based on deterministic results."""
        
        if not self.llm:
            return self._qualitative_fallback(det_results)
        
        json_schema = """{
  "strengths": ["strength1", "strength2"],
  "weaknesses": ["weakness1", "weakness2"],
  "specific_suggestions": ["actionable suggestion 1", "actionable suggestion 2"],
  "analysis_summary": "2-3 sentence summary of the candidate's fit",
  "interview_probability": <int 0-100>,
  "market_value": "$X - $Y"
}"""
        
        prompt = f"""You are an expert career coach. A deterministic ATS scanner has already scored this resume. Your job is NOT to score — instead, provide actionable qualitative advice.

JOB TITLE: {job_title}

JOB DESCRIPTION:
{job_description}

RESUME:
{resume_text}

DETERMINISTIC ATS RESULTS:
- Overall ATS Score: {det_results['overall_score']}/100
- Keyword Match: {det_results['keyword_score']}/100
- Formatting: {det_results['formatting_score']}/100
- Sections Detected: {', '.join(det_results['detected_sections'])}
- Missing Sections: {', '.join(det_results['missing_sections'])}
- Missing Keywords: {', '.join(det_results['missing_keywords'][:10])}
- Matched Keywords: {', '.join(det_results['matched_keywords'][:10])}
- Keyword Density: {det_results['keyword_density']}%
- Achievements Found: {len(det_results['achievements_found'])}
- Formatting Issues: {'; '.join(det_results['formatting_issues']) if det_results['formatting_issues'] else 'None'}
- Word Count: {det_results['word_count']}
- File Structure: {json.dumps(file_checks) if file_checks else 'Pasted Text'}

INSTRUCTIONS:
1. Based on the ATS scan results above, provide SPECIFIC, ACTIONABLE suggestions to improve the resume.
2. For missing keywords, suggest WHERE and HOW to naturally incorporate them into existing bullet points.
3. For weaknesses, suggest specific rewording or additions with example text.
4. Estimate interview probability considering both the ATS score and the quality/relevance of experience.
5. Keep all responses concise and highly actionable.

Respond with ONLY a valid JSON object matching this structure:
{json_schema}
"""
        
        try:
            messages = [
                SystemMessage(content="You are an expert career coach. Return only valid JSON. Do not score — only advise."),
                HumanMessage(content=prompt)
            ]

            response = _invoke_llm(self.llm, messages)
            content = response.content.strip()

            # Extract JSON
            json_match = re.search(r'\{[\s\S]*\}', content)
            if json_match:
                content = json_match.group(0)

            result = json.loads(content)
            return result

        except Exception as e:
            # Check for quota/rate-limit errors:
            # 1. First check if it's the explicit Google SDK exception type
            # 2. Fall back to string matching for LangChain-wrapped errors
            is_quota_error = (
                (_ResourceExhausted is not None and isinstance(e, _ResourceExhausted))
                or any(kw in str(e).lower() for kw in ("429", "quota", "resource_exhausted", "resourceexhausted", "rate_limit", "exceeded"))
            )
            if is_quota_error:
                print(f"Gemini API Quota Exceeded (failing fast): {type(e).__name__}")
                raise RateLimitError(source="Google Gemini AI")

            print(f"Gemini Qualitative Analysis Error: {e}")
            return self._qualitative_fallback(det_results)
    
    def _qualitative_fallback(self, det_results):
        """Rule-based fallback for qualitative analysis when Gemini is unavailable."""
        
        suggestions = []
        strengths = []
        weaknesses = []
        
        # Generate suggestions based on deterministic results
        if det_results["missing_keywords"]:
            suggestions.append(
                f"Add these missing keywords naturally into your experience bullets: "
                f"{', '.join(det_results['missing_keywords'][:5])}"
            )
        
        if det_results["missing_sections"]:
            suggestions.append(
                f"Add these standard resume sections: {', '.join(det_results['missing_sections'])}"
            )
        
        if det_results["formatting_issues"]:
            for issue in det_results["formatting_issues"][:2]:
                suggestions.append(f"Fix formatting: {issue}")
        
        if det_results["achievements_score"] < 50:
            suggestions.append("Add more quantified achievements (e.g., 'Improved X by 30%', 'Saved $50K')")
        
        if not det_results["contact_info"].get("linkedin"):
            suggestions.append("Add your LinkedIn profile URL")
        
        # Strengths
        if det_results["keyword_score"] >= 60:
            strengths.append("Good keyword coverage for this role")
        if det_results["formatting_score"] >= 80:
            strengths.append("Clean, ATS-friendly formatting")
        if det_results["achievements_score"] >= 70:
            strengths.append("Strong use of quantified achievements")
        if det_results["section_score"] >= 80:
            strengths.append("Well-structured with standard resume sections")
        if det_results["contact_info"].get("email") and det_results["contact_info"].get("phone"):
            strengths.append("Contact information is complete")
        
        # Weaknesses
        if det_results["keyword_score"] < 50:
            weaknesses.append("Low keyword match — resume may not pass ATS keyword filters")
        if det_results["formatting_score"] < 70:
            weaknesses.append("Formatting issues may cause ATS parsing errors")
        if det_results["achievements_score"] < 50:
            weaknesses.append("Lacks quantified achievements — add metrics to demonstrate impact")
        if det_results["section_score"] < 60:
            weaknesses.append("Missing standard resume sections that ATS systems expect")
        
        # Fallback summary
        score = det_results["overall_score"]
        if score >= 75:
            summary = "Resume is well-optimized for ATS systems. Focus on fine-tuning keyword placement."
        elif score >= 50:
            summary = "Resume has a moderate ATS score. Address missing keywords and formatting issues to improve."
        else:
            summary = "Resume needs significant improvement for ATS compatibility. Focus on structure, keywords, and formatting."
        
        return {
            "strengths": strengths if strengths else ["Basic resume structure present"],
            "weaknesses": weaknesses if weaknesses else ["Could be more targeted"],
            "specific_suggestions": suggestions if suggestions else ["Tailor resume keywords to the job description"],
            "analysis_summary": summary,
            "interview_probability": max(20, score - 15),
            "market_value": "",
        }
