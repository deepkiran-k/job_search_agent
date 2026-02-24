"""
Job Search Tools - Real API integration for job listings
"""
import os
import requests
import json
from typing import List, Dict, Any, Optional
from crewai_tools import BaseTool
from pydantic import Field
from dotenv import load_dotenv

load_dotenv()


class AdzunaJobSearchTool(BaseTool):
    """Search Adzuna API for real job listings"""
    
    name: str = "Adzuna Job Search"
    description: str = "Search for real job opportunities using Adzuna API. Returns actual job listings with company, title, location, salary, and description."
    
    # Pydantic V2 field declarations
    app_id: Optional[str] = Field(default=None)
    app_key: Optional[str] = Field(default=None)
    base_url: str = Field(default="https://api.adzuna.com/v1/api/jobs")
    country: str = Field(default="us")
    
    def __init__(self, **data):
        super().__init__(**data)
        # Initialize from environment if not provided
        if not self.app_id:
            self.app_id = os.getenv("ADZUNA_APP_ID")
        if not self.app_key:
            self.app_key = os.getenv("ADZUNA_APP_KEY")
    
    def _run(self, job_title: str, location: str = "", max_results: int = 20) -> str:
        """
        Search for jobs on Adzuna
        
        Args:
            job_title: Job title to search for
            location: Location (city, state, or "remote")
            max_results: Maximum number of results to return
        
        Returns:
            JSON string with job listings
        """
        from utils.adzuna_client import search_adzuna
        
        try:
            jobs = search_adzuna(job_title, location, max_results)
            
            return json.dumps({
                "success": True,
                "total_results": len(jobs), # Approximate, since we don't get total count from client yet
                "jobs_returned": len(jobs),
                "jobs": jobs,
                "search_params": {
                    "job_title": job_title,
                    "location": location,
                    "country": self.country
                }
            }, indent=2)
            
        except Exception as e:
            return json.dumps({
                "error": f"Search failed: {str(e)}",
                "jobs": []
            })
    
    def _format_salary(self, min_salary: float, max_salary: float) -> str:
        """Format salary range for display"""
        # This method is kept for potential internal use but the client handles it now
        if min_salary and max_salary:
            return f"${int(min_salary):,} - ${int(max_salary):,}"
        elif min_salary:
            return f"${int(min_salary):,}+"
        elif max_salary:
            return f"Up to ${int(max_salary):,}"
        else:
            return "Not specified"


def fetch_jobs(job_title: str, location: str = "", max_results: int = 20) -> list:
    """
    Fetch jobs from Adzuna directly — no LLM, no CrewAI.
    Returns a plain list of job dicts.
    """
    from utils.adzuna_client import search_adzuna
    return search_adzuna(job_title, location, max_results)


class JobMatchingTool(BaseTool):
    """Use LLM to intelligently match and rank jobs based on resume"""
    
    name: str = "AI Job Matcher"
    description: str = "Analyze jobs and rank them by how well they match the candidate's resume using AI"
    
    # Pydantic V2 field declaration
    scorer: Any = Field(default=None)
    
    def __init__(self, **data):
        super().__init__(**data)
        # Initialize Gemini scorer
        if not self.scorer:
            from utils.gemini_ats import GeminiATSScorer
            self.scorer = GeminiATSScorer()
    
    def _run(self, jobs_json: str, resume_text: str) -> str:
        """
        Rank jobs by match score using AI
        
        Args:
            jobs_json: JSON string of job listings
            resume_text: Candidate's resume
        
        Returns:
            JSON string with ranked jobs and match scores
        """
        
        try:
            jobs_data = json.loads(jobs_json)
            jobs = jobs_data.get("jobs", [])
            
            if not jobs:
                return json.dumps({
                    "error": "No jobs to match",
                    "ranked_jobs": []
                })
            
            # Score each job
            ranked_jobs = []
            for job in jobs[:20]:  # Limit to top 20 to avoid too many API calls
                # Create job description from available fields
                job_desc = f"""
                Title: {job.get('title', '')}
                Company: {job.get('company', '')}
                Location: {job.get('location', '')}
                Description: {job.get('description', '')}
                Category: {job.get('category', '')}
                """
                
                # Get match score from Gemini
                if self.scorer.llm:
                    try:
                        analysis = self.scorer.analyze_resume(
                            resume_text=resume_text,
                            job_title=job.get('title', ''),
                            job_description=job_desc
                        )
                        match_score = analysis.get("ats_score", 70)
                    except:
                        # Fallback to simple keyword matching
                        match_score = self._simple_match_score(job_desc, resume_text)
                else:
                    match_score = self._simple_match_score(job_desc, resume_text)
                
                job["match_score"] = match_score
                ranked_jobs.append(job)
            
            # Sort by match score (highest first)
            ranked_jobs.sort(key=lambda x: x.get("match_score", 0), reverse=True)
            
            return json.dumps({
                "success": True,
                "total_jobs": len(ranked_jobs),
                "ranked_jobs": ranked_jobs,
                "top_match": ranked_jobs[0] if ranked_jobs else None
            }, indent=2)
            
        except Exception as e:
            return json.dumps({
                "error": f"Matching failed: {str(e)}",
                "ranked_jobs": []
            })
    
    def _simple_match_score(self, job_desc: str, resume: str) -> int:
        """Simple keyword-based matching as fallback"""
        job_lower = job_desc.lower()
        resume_lower = resume.lower()
        
        keywords = [
            "python", "java", "javascript", "react", "node",
            "aws", "azure", "docker", "kubernetes",
            "machine learning", "ai", "data", "sql",
            "tensorflow", "pytorch", "scikit-learn"
        ]
        
        matches = sum(1 for kw in keywords if kw in resume_lower and kw in job_lower)
        base_score = 60
        keyword_bonus = min(30, matches * 3)
        
        return base_score + keyword_bonus


class TheMuseJobSearchTool(BaseTool):
    """Backup job search using The Muse API (no API key required)"""
    
    name: str = "The Muse Job Search"
    description: str = "Search The Muse for job opportunities (backup source, no API key needed)"
    
    def _run(self, job_title: str, location: str = "", max_results: int = 20) -> str:
        """
        Search The Muse API
        
        Args:
            job_title: Job title/category
            location: Location filter
            max_results: Max results
        
        Returns:
            JSON string with job listings
        """
        
        try:
            url = "https://www.themuse.com/api/public/jobs"
            
            params = {
                "page": 1,
                "descending": "true",
                "api_key": "public"  # The Muse has a public API
            }
            
            if job_title:
                params["category"] = job_title
            if location:
                params["location"] = location
            
            response = requests.get(url, params=params, timeout=10)
            response.raise_for_status()
            
            data = response.json()
            
            jobs = []
            for result in data.get("results", [])[:max_results]:
                job = {
                    "id": result.get("id", ""),
                    "title": result.get("name", ""),
                    "company": result.get("company", {}).get("name", "Unknown"),
                    "location": ", ".join(result.get("locations", [{}])[0].get("name", "Remote") if result.get("locations") else ["Remote"]),
                    "description": result.get("contents", "")[:500],
                    "url": result.get("refs", {}).get("landing_page", ""),
                    "posted_date": result.get("publication_date", ""),
                    "source": "The Muse"
                }
                jobs.append(job)
            
            return json.dumps({
                "success": True,
                "jobs_returned": len(jobs),
                "jobs": jobs
            }, indent=2)
            
        except Exception as e:
            return json.dumps({
                "error": f"The Muse API failed: {str(e)}",
                "jobs": []
            })
