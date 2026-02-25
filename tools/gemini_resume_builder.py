import os
import json
from langchain_core.messages import SystemMessage, HumanMessage
from config.settings import settings

class GeminiResumeBuilder:
    """Uses Gemini to actively rewrite and tailor a resume for a specific job."""
    
    def __init__(self):
        self.llm = settings.get_gemini_llm()
        
    def build_resume(self, resume_text: str, job_info: dict) -> str:
        """
        Rewrites the given resume to be tailored to the job description, 
        yielding a highly ATS-optimized markdown resume.
        """
        if not self.llm:
            return "Error: Gemini LLM is not configured properly."
            
        job_title = job_info.get("title", "Unknown Role")
        job_company = job_info.get("company", "Unknown Company")
        job_description = job_info.get("description", "")
        
        prompt = f"""You are an elite executive resume writer and ATS optimization expert. 
Your task is to completely rewrite and tailor the provided resume for the specific job description below.

JOB TITLE: {job_title}
COMPANY: {job_company}
JOB DESCRIPTION:
{job_description}

ORIGINAL RESUME:
{resume_text}

Follow these strict guidelines when rewriting the resume:
1.  **Professional Summary (Objective):** Create a compelling 3-4 sentence professional summary tailored to this specific job. Highlight the candidate's core value proposition, key achievements, and explicitly state what they bring to {job_company}. Use keywords from the job description naturally.
2.  **Tailored Bullet Points:** Rewrite the experience bullet points to match the responsibilities and requirements of the target job.
    *   Focus on accomplishments, not just duties.
    *   Use strong action verbs.
    *   Incorporate relevant metrics and quantifiable results. If exact metrics are missing from the original resume, focus on the explicit impact of the work, but do not invent fake numbers.
    *   Ensure the most relevant experience for this job is prioritized.
3.  **Readability and ATS Compatibility:** 
    *   Format the entire resume cleanly using standard Markdown formatting (headers, bold text, bullet points).
    *   Ensure a logical flow: Professional Summary -> Skills -> Experience -> Education.
    *   Remove any fluff or irrelevant information that does not serve the goal of landing this specific role.

Output ONLY the raw markdown of the final, tailored resume. Do not include introductory text, explanations, or markdown code block wrappers (like ```markdown). Just output the raw readable markdown text itself.
"""
        
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
            return f"Error generating tailored resume: {e}"
