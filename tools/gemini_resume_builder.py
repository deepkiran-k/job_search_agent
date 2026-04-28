import os
import json
from langchain_core.messages import SystemMessage, HumanMessage
from core.settings import settings

class GeminiResumeBuilder:
    """Uses Gemini to actively rewrite and tailor a resume for a specific job,
    guided by deterministic ATS scan results for targeted improvements."""
    
    def __init__(self):
        self.llm = settings.get_gemini_llm()
        
    def build_resume(self, resume_text: str, job_info: dict, ats_results: dict = None,
                     embedded_links: list = None) -> str:
        """
        Rewrites the given resume to be tailored to the job description, 
        yielding a highly ATS-optimized markdown resume.
        
        If ats_results (from ATSScanner) is provided, uses them to guide
        exactly which keywords to add, sections to fix, etc.
        """
        if not self.llm:
            return "Error: Gemini LLM is not configured properly."
            
        job_title = job_info.get("title", "Unknown Role")
        job_company = job_info.get("company", "Unknown Company")
        job_description = job_info.get("description", "")
        
        # Build ATS guidance block if deterministic results are available
        ats_guidance = ""
        if ats_results:
            missing_kw = ats_results.get("missing_keywords", [])
            missing_sec = ats_results.get("missing_sections", [])
            fmt_issues = ats_results.get("formatting_issues", [])
            length_fb = ats_results.get("length_feedback", [])
            contact = ats_results.get("contact_info", {})
            achievements_score = ats_results.get("achievements_score", 100)
            
            guidance_parts = []
            if missing_kw:
                # Give very specific instructions per keyword
                kw_list = missing_kw[:20]
                guidance_parts.append(
                    f"MISSING KEYWORDS — You MUST naturally weave EVERY one of these into "
                    f"bullet points, skills sections, or the summary. Do NOT list them in a "
                    f"separate block; integrate each into an existing or new achievement "
                    f"sentence:\n  " + "\n  ".join(f"• {kw}" for kw in kw_list)
                )
            if missing_sec:
                guidance_parts.append(
                    f"MISSING SECTIONS — You MUST add these standard resume sections: "
                    f"{', '.join(missing_sec)}. Use the exact header names: SUMMARY, SKILLS, "
                    f"EXPERIENCE, EDUCATION, PROJECTS, CERTIFICATIONS."
                )
            if fmt_issues:
                guidance_parts.append(f"FORMATTING ISSUES TO FIX: {'; '.join(fmt_issues)}")
            if length_fb:
                guidance_parts.append(f"LENGTH: {'; '.join(length_fb)}")
            if achievements_score < 80:
                guidance_parts.append(
                    "ACHIEVEMENTS — The resume lacks quantified metrics. You MUST include at "
                    "least 5 bullet points with concrete numbers (percentages, dollar amounts, "
                    "team sizes, time saved, users impacted, etc.). Infer reasonable impact "
                    "from the context but do NOT fabricate specific numbers that weren't implied."
                )
            if not contact.get("linkedin"):
                # Prefer the real extracted URL over a generic placeholder
                linkedin_url = next(
                    (u.strip() for u in (embedded_links or []) if "linkedin.com" in u.lower()), None
                )
                if linkedin_url:
                    guidance_parts.append(f"Use this LinkedIn URL in the contact header: {linkedin_url}")
                else:
                    guidance_parts.append("Add a LinkedIn profile URL placeholder: linkedin.com/in/yourprofile")
            
            if guidance_parts:
                ats_guidance = (
                    "\n\nATS SCAN FINDINGS — You MUST address ALL of these in the rewrite. "
                    "The rewritten resume will be re-scanned by the same ATS engine, so every "
                    "item below directly impacts the score:\n" +
                    "\n".join(f"\n{i+1}. {g}" for i, g in enumerate(guidance_parts))
                )
        
        # ── Build contact links block from embedded_links ─────────────────────
        # This is injected into the prompt regardless of ATS results, so the AI
        # always knows the real LinkedIn / GitHub URLs and uses them in the header
        # rather than writing placeholder text like "LinkedIn | GitHub".
        # Note: target_ref in python-docx can include trailing whitespace — strip().
        contact_links_block = ""
        if embedded_links:
            link_lines = []
            for url in embedded_links:
                url = url.strip()
                if not url:
                    continue
                url_lower = url.lower()
                if "linkedin.com" in url_lower:
                    link_lines.append(f"LinkedIn: {url}")
                elif "github.com" in url_lower:
                    link_lines.append(f"GitHub: {url}")
                elif url_lower.startswith(("http", "www")):
                    link_lines.append(f"Portfolio/Website: {url}")
            if link_lines:
                contact_links_block = (
                    "\n\nCANDIDATE PROFILE LINKS — use these EXACT URLs in the contact "
                    "header line. Do NOT use placeholder text:\n" + "\n".join(link_lines)
                )

        prompt = f"""You are an elite resume writer and ATS strategist. Rewrite the resume below for this specific role. The result will be re-scored by an ATS engine.

JOB: {job_title} at {job_company}
JOB DESCRIPTION:
{job_description}

RESUME:
{resume_text}
{ats_guidance}{contact_links_block}

REWRITE RULES:

**SUMMARY** (4-5 sentences): Highlight the candidate's unique value for THIS role. Weave in 3-4 JD keywords naturally. End with a forward-looking statement about contributing to {job_company}.

**SKILLS**: List all JD-relevant skills the candidate plausibly has, grouped by category.

**EXPERIENCE**: First identify the top skill gaps between the JD and resume — then reframe existing experience to fill them. For each role:
- 4-6 bullets max, most relevant first
- Start with strong action verbs, quantify impact (%, $, team size, scale)
- Integrate JD keywords IN CONTEXT within achievement sentences — never keyword-dump
- First-person implied (no "I"), professional and concise
- If employment gaps exist, subtly address them

**EDUCATION / PROJECTS / CERTIFICATIONS**: Include all. Add relevant certifications commonly expected for this role (mark as "In Progress" or "Add if applicable" if not in the original).

**FORMAT**: Use `#` for name, `##` for section headers, `-` for bullets (no special chars). Bold job titles and companies. Include email, phone, and any profile links from CANDIDATE PROFILE LINKS above. Aim for 400-700 words.

Section order: SUMMARY → SKILLS → EXPERIENCE → EDUCATION → PROJECTS → CERTIFICATIONS

Output ONLY raw markdown — no intro text, no explanations, no code fences."""
        
        try:
            messages = [
                SystemMessage(content="You are an elite executive resume writer and ATS optimization expert."),
                HumanMessage(content=prompt)
            ]
            response = self.llm.invoke(messages)
            content = response.content.strip()
            
            # Clean up if markdown wrapper was accidentally included
            if content.startswith("```markdown"):
                content = content[11:]
            if content.startswith("```"):
                content = content[3:]
            if content.endswith("```"):
                content = content[:-3]
                
            return content.strip()
            
        except Exception as e:
            err_msg = str(e).lower()
            if "429" in err_msg or "quota" in err_msg or "resource_exhausted" in err_msg:
                return "⚠️ AI_LIMIT_HIT: Gemini API Quota Exceeded. Auto-revision is temporarily unavailable. Please try again later or upgrade your Gemini plan."
            return f"Error generating tailored resume: {e}"
