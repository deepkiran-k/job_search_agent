# utils/gemini_ats.py - REAL ATS SCORING WITH GEMINI
import json
import re
from config.settings import settings
from langchain_core.messages import SystemMessage, HumanMessage

class GeminiATSScorer:
    """Real ATS scoring using Google Gemini"""
    
    def __init__(self):
        """Initialize Gemini LLM"""
        self.llm = settings.get_gemini_llm()
    
    def analyze_resume(self, resume_text, job_title, job_description=None):
        """
        Analyze resume using Gemini and return REAL ATS score
        """
        
        if not self.llm:
            return self._rule_based_fallback(resume_text, job_title, job_description)
        
        # Create default job description if none provided
        if not job_description:
            job_description = f"""
            We are looking for a {job_title} with relevant experience in the field.
            """
        
        json_schema = """{
  "ats_score": <int 0-100>,
  "keyword_match": <int 0-100>,
  "formatting_score": <int 0-100>,
  "experience_score": <int 0-100>,
  "education_score": <int 0-100>,
  "skills_score": <int 0-100>,
  "missing_keywords": ["keyword1", "keyword2"],
  "strengths": ["strength1"],
  "weaknesses": ["weakness1"],
  "specific_suggestions": ["suggestion1"],
  "interview_probability": <int 0-100>,
  "market_value": "$X - $Y",
  "analysis_summary": "1-2 sentence summary"
}"""
        
        # Prepare the prompt for Gemini
        prompt = f"""You are an expert ATS (Applicant Tracking System) analyst. Analyze this resume against the job description.

JOB TITLE: {job_title}

JOB DESCRIPTION:
{job_description}

RESUME:
{resume_text}

IMPORTANT ANALYSIS INSTRUCTIONS:
1. Skills Gap Analysis: Do not just list missing skills. For missing skills or weaknesses, suggest specific, quantifiable achievements the user could add to their experience bullets to demonstrate that skill.
2. Keyword Integration: Evaluate if the required keywords are integrated naturally into achievements with context, rather than just being stuffed into a list. Penalize the keyword score if keywords lack context.

Respond with ONLY a valid JSON object (no markdown, no extra text) matching this structure:
{json_schema}

Be honest and use the full 0-100 scale. Keep all string values concise but highly actionable.
"""
        
        try:
            # Call Gemini
            messages = [
                SystemMessage(content="You are an expert ATS analyst. Return only valid JSON."),
                HumanMessage(content=prompt)
            ]
            
            response = self.llm.invoke(messages)
            content = response.content.strip()
            
            # Use regex to find the main JSON object
            json_match = re.search(r'\{[\s\S]*\}', content)
            if json_match:
                content = json_match.group(0)
            
            # Parse the response
            result = json.loads(content)
            
            # Add metadata
            result["analysis_method"] = "Google Gemini 2.5 Flash"
            result["job_title"] = job_title
            
            return result
            
        except Exception as e:
            print(f"Gemini Analysis Error: {e}")
            return self._rule_based_fallback(resume_text, job_title, job_description)
    
    def _rule_based_fallback(self, resume_text, job_title, job_description):
        """Intelligent fallback if Gemini is unavailable"""
        
        resume_lower = resume_text.lower()
        
        # Simple keyword fallback logic
        keywords = {
            "python": 10, "java": 5, "javascript": 5, "react": 5, "aws": 7, 
            "azure": 7, "docker": 6, "kubernetes": 6, "sql": 5, 
            "machine learning": 10, "ai": 8, "data": 5
        }
        
        # Calculate keyword match
        matched_keywords = []
        missing_keywords = []
        total_score = 0
        max_score = sum(keywords.values())
        
        for keyword, weight in keywords.items():
            if keyword in resume_lower:
                matched_keywords.append(keyword)
                total_score += weight
            else:
                missing_keywords.append(keyword)
        
        keyword_percentage = int((total_score / max_score) * 100) if max_score > 0 else 50
        
        # Basic scoring
        ats_score = min(100, max(40, keyword_percentage + 20))
        
        return {
            "ats_score": ats_score,
            "keyword_match": keyword_percentage,
            "formatting_score": 70,
            "experience_score": 70,
            "education_score": 70,
            "skills_score": keyword_percentage,
            "missing_keywords": missing_keywords[:5],
            "strengths": ["Basic technical skills"],
            "weaknesses": ["Could add more specific keywords"],
            "specific_suggestions": ["Add more technical keywords matching the job description"],
            "interview_probability": min(80, ats_score - 10),
            "market_value": "$80k - $120k",
            "analysis_summary": "Basic analysis (Fallback Mode). Resume seems relevant but could be improved.",
            "analysis_method": "Rule-based Fallback",
            "job_title": job_title
        }
