import json
import re
import concurrent.futures
from datetime import datetime
from typing import Any
from utils.gemini_ats import GeminiATSScorer
from langchain_core.messages import SystemMessage, HumanMessage
try:
    from google.api_core.exceptions import ResourceExhausted as _ResourceExhausted
except ImportError:
    _ResourceExhausted = None

_GEMINI_TIMEOUT = 25  # seconds


def _invoke_llm(llm, messages):
    """Thread-based hard timeout around llm.invoke(). See gemini_ats.py."""
    with concurrent.futures.ThreadPoolExecutor(max_workers=1) as pool:
        future = pool.submit(llm.invoke, messages)
        try:
            return future.result(timeout=_GEMINI_TIMEOUT)
        except concurrent.futures.TimeoutError:
            raise Exception("Gemini timeout: quota/rate-limit exceeded")

class GeminiATSTool:
    """Tool wrapper for Gemini ATS scoring"""
    
    def __init__(self):
        self.scorer = GeminiATSScorer()
    
    def _run(self, resume_text: str, job_description: str = "", job_title: str = "") -> str:

        try:
            result = self.scorer.analyze_resume(
                resume_text=resume_text,
                job_title=job_title,
                job_description=job_description
            )
            return json.dumps(result, indent=2)
        except Exception as e:
            return json.dumps({
                "error": f"Gemini ATS analysis failed: {str(e)}",
                "ats_score": 0
            })


class GeminiCoverLetterTool:
    """Generate personalized cover letters using Gemini"""
    
    def __init__(self):
        self.scorer = GeminiATSScorer()
    
    def _run(self, job_info: str, resume_text: str, ats_analysis: str = "") -> str:
        """
        Generate cover letter using Gemini.
        job_info can be either a JSON string OR plain text like "Company: X\nTitle: Y\n..."
        """
        
        if not self.scorer.llm:
            return self._template_fallback(job_info, resume_text)
        
        try:
            # ── Parse job_info: try JSON first, then plain-text regex ─────────
            job_title = "the position"
            company = "your company"
            job_desc = ""

            if isinstance(job_info, dict):
                job_data = job_info
                job_title = job_data.get("title", job_title)
                company   = job_data.get("company", company)
                job_desc  = job_data.get("description", job_desc)
            else:
                # Try JSON parse
                parsed_ok = False
                try:
                    job_data = json.loads(job_info)
                    job_title = job_data.get("title", job_title)
                    company   = job_data.get("company", company)
                    job_desc  = job_data.get("description", job_desc)
                    parsed_ok = True
                except (json.JSONDecodeError, AttributeError):
                    pass

                if not parsed_ok:
                    # Plain-text fallback: parse "Key: Value" lines
                    import re
                    for line in job_info.splitlines():
                        m = re.match(r"^\s*(Title|Job Title)\s*:\s*(.+)", line, re.IGNORECASE)
                        if m:
                            job_title = m.group(2).strip()
                        m = re.match(r"^\s*Company\s*:\s*(.+)", line, re.IGNORECASE)
                        if m:
                            company = m.group(1).strip()
                        m = re.match(r"^\s*Description\s*:\s*(.+)", line, re.IGNORECASE)
                        if m:
                            job_desc = m.group(1).strip()
                    # If still no description, use the whole text as context
                    if not job_desc:
                        job_desc = job_info[:800]

            # ── Parse ATS analysis if provided ────────────────────────────────
            analysis_data = {}
            if ats_analysis:
                try:
                    analysis_data = json.loads(ats_analysis) if isinstance(ats_analysis, str) else ats_analysis
                except Exception:
                    pass
            
            strengths = analysis_data.get("strengths", [])
            
            # ── Build prompt ──────────────────────────────────────────────────
            prompt = f"""Write a professional, compelling cover letter for the following:

JOB TITLE: {job_title}
COMPANY: {company}
JOB DESCRIPTION:
{job_desc}

CURRENT DATE: {datetime.now().strftime('%B %d, %Y')}

CANDIDATE'S RESUME:
{resume_text[:1500] if resume_text else "Not provided - write a strong general letter for this role."}

{f"KEY STRENGTHS FROM ATS ANALYSIS: {', '.join(strengths[:3])}" if strengths else ""}

Requirements:
- Professional tone, enthusiastic but not over-the-top
- Highlight 3-4 most relevant achievements from resume
- Show specific interest in the company/role
- Include quantifiable results where possible
- Keep to 3-4 paragraphs
- End with strong call to action
- Use proper business letter format
- Use the CURRENT DATE provided above for the letter date
- Sign off with "Sincerely," and "[Your Name]"

Write the complete cover letter including the salutation and signature.
"""
            
            # ── Call Gemini ───────────────────────────────────────────────────
            messages = [
                SystemMessage(content="You are an expert career coach and professional writer specializing in compelling cover letters."),
                HumanMessage(content=prompt)
            ]
            
            response = _invoke_llm(self.scorer.llm, messages)
            cover_letter = response.content.strip()
            
            return json.dumps({
                "success": True,
                "cover_letter": cover_letter,
                "job_title": job_title,
                "company": company,
                "word_count": len(cover_letter.split()),
                "generated_by": "Google Gemini"
            }, indent=2)
            
        except Exception as e:
            is_quota_error = (
                (_ResourceExhausted is not None and isinstance(e, _ResourceExhausted))
                or any(kw in str(e).lower() for kw in ("429", "quota", "resource_exhausted", "resourceexhausted", "rate_limit", "exceeded"))
            )
            if is_quota_error:
                print(f"Gemini Cover Letter Quota Exceeded (failing fast): {type(e).__name__}")
                return json.dumps({
                    "success": False,
                    "ai_limit_hit": True,
                    "error": "⚠️ Gemini API Quota Exceeded. Using template fallback for cover letter.",
                    "cover_letter": self._template_fallback(job_info, resume_text)
                })
            return json.dumps({
                "success": False,
                "error": f"Cover letter generation failed: {str(e)}",
                "cover_letter": self._template_fallback(job_info, resume_text)
            })
    
    def _template_fallback(self, job_info: str, resume_text: str) -> str:
        """Fallback template if Gemini fails"""
        try:
            job_data = json.loads(job_info) if isinstance(job_info, str) else job_info
            job_title = job_data.get("title", "the position")
            company = job_data.get("company", "your company")
        except:
            job_title = "the position"
            company = "your company"
        
        now = datetime.now().strftime('%B %d, %Y')
        return f"""{now}

Dear Hiring Manager,

I am writing to express my strong interest in the {job_title} position at {company}. With my background in technology and proven track record of delivering results, I am confident in my ability to contribute to your team.

Throughout my career, I have developed expertise in areas that align closely with your requirements. My experience includes leading technical projects, collaborating with cross-functional teams, and implementing solutions that drive business value.

I am particularly impressed by {company}'s work in the industry and would be thrilled to contribute to your ongoing success. My combination of technical skills and practical experience makes me well-suited for this role.

Thank you for considering my application. I look forward to the opportunity to discuss how I can contribute to your team's success.

Sincerely,
[Your Name]"""


class JobRankingTool:
    """Rank jobs by match score using AI analysis"""
    
    def __init__(self):
        self.scorer = GeminiATSScorer()
    
    def _run(self, jobs_json: str, resume_text: str, top_n: int = 10) -> str:
        """
        Rank jobs by match score using a single batched Gemini API call.
        Sends all jobs in one prompt instead of one call per job.
        """
        from langchain_core.messages import SystemMessage, HumanMessage

        try:
            jobs_data = json.loads(jobs_json) if isinstance(jobs_json, str) else jobs_json

            # Support both {"jobs": [...]} and {"job_opportunities": [...]} and bare list
            if isinstance(jobs_data, dict):
                jobs = (
                    jobs_data.get("jobs")
                    or jobs_data.get("job_opportunities")
                    or []
                )
            elif isinstance(jobs_data, list):
                jobs = jobs_data
            else:
                jobs = []

            if not jobs:
                return json.dumps({"error": "No jobs to rank", "ranked_jobs": []})

            jobs_to_rank = jobs[:15]  # cap at 15

            # ── Fast path: no LLM available ──────────────────────────────────
            if not self.scorer.llm:
                ranked_jobs = []
                for job in jobs_to_rank:
                    job_desc = f"{job.get('title','')} {job.get('description','')}"
                    job["match_score"] = self._simple_score(job_desc, resume_text)
                    job["match_reason"] = "Keyword-based scoring (LLM unavailable)"
                    ranked_jobs.append(job)
                ranked_jobs.sort(key=lambda x: x.get("match_score", 0), reverse=True)
                return json.dumps({
                    "success": True,
                    "total_jobs_analyzed": len(ranked_jobs),
                    "top_jobs": ranked_jobs[:top_n],
                    "all_ranked_jobs": ranked_jobs
                }, indent=2)

            # ── Build a single batched prompt ────────────────────────────────
            jobs_summary = ""
            for i, job in enumerate(jobs_to_rank):
                jobs_summary += (
                    f"\nJOB {i+1}:\n"
                    f"  Title: {job.get('title', 'N/A')}\n"
                    f"  Company: {job.get('company', 'N/A')}\n"
                    f"  Location: {job.get('location', 'N/A')}\n"
                    f"  Salary: {job.get('salary', 'N/A')}\n"
                    f"  Description: {str(job.get('description', ''))[:300]}\n"
                )

            prompt = f"""You are an expert recruiter. Score each job below against the candidate's resume.

CANDIDATE RESUME (excerpt):
{resume_text[:1500]}

JOBS TO RANK:
{jobs_summary}

Return ONLY a valid JSON array (no markdown, no explanation) with one object per job, in this exact format:
[
  {{
    "job_index": 1,
    "match_score": <integer 0-100>,
    "match_reason": "<one sentence why>"
  }},
  ...
]

Score based on: skills alignment, experience level, role relevance. Be realistic."""

            messages = [
                SystemMessage(content="You are an expert technical recruiter. Always respond with valid JSON only."),
                HumanMessage(content=prompt)
            ]

            response = self.scorer.llm.invoke(messages)
            raw = response.content.strip()

            # Strip markdown fences if present
            if raw.startswith("```"):
                raw = raw.split("```")[1]
                if raw.startswith("json"):
                    raw = raw[4:]
                raw = raw.strip()

            scores = json.loads(raw)  # list of {job_index, match_score, match_reason}

            # Merge scores back into job objects
            score_map = {item["job_index"]: item for item in scores}
            ranked_jobs = []
            for i, job in enumerate(jobs_to_rank):
                score_data = score_map.get(i + 1, {})
                job["match_score"] = score_data.get("match_score", self._simple_score(
                    f"{job.get('title','')} {job.get('description','')}", resume_text
                ))
                job["match_reason"] = score_data.get("match_reason", "")
                ranked_jobs.append(job)

            ranked_jobs.sort(key=lambda x: x.get("match_score", 0), reverse=True)

            return json.dumps({
                "success": True,
                "total_jobs_analyzed": len(ranked_jobs),
                "top_jobs": ranked_jobs[:top_n],
                "all_ranked_jobs": ranked_jobs
            }, indent=2)

        except Exception as e:
            # Graceful fallback to keyword scoring
            try:
                ranked_jobs = []
                for job in jobs_to_rank:
                    job_desc = f"{job.get('title','')} {job.get('description','')}"
                    job["match_score"] = self._simple_score(job_desc, resume_text)
                    job["match_reason"] = "Keyword-based fallback scoring"
                    ranked_jobs.append(job)
                ranked_jobs.sort(key=lambda x: x.get("match_score", 0), reverse=True)
                return json.dumps({
                    "success": True,
                    "total_jobs_analyzed": len(ranked_jobs),
                    "top_jobs": ranked_jobs[:top_n],
                    "all_ranked_jobs": ranked_jobs,
                    "warning": f"LLM ranking failed ({str(e)}), used keyword fallback"
                }, indent=2)
            except Exception as fallback_err:
                return json.dumps({
                    "error": f"Ranking failed: {str(e)} | Fallback error: {str(fallback_err)}",
                    "ranked_jobs": []
                })
    
    def _simple_score(self, job_desc: str, resume: str) -> int:
        """Simple keyword matching fallback"""
        keywords = ["python", "java", "aws", "azure", "machine learning", "ai", "data"]
        matches = sum(1 for kw in keywords if kw in resume.lower() and kw in job_desc.lower())
        return min(95, 60 + matches * 5)
