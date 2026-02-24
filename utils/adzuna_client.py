import os
import requests
import json
from typing import List, Dict, Any, Optional
from dotenv import load_dotenv

load_dotenv()


def search_adzuna(job_title: str, location: str = "", max_results: int = 20, country: str = "us") -> List[Dict[str, Any]]:
    """
    Search Adzuna API for job listings.
    
    Args:
        job_title: Job title to search for
        location: Location (city, state, or "remote")
        max_results: Maximum number of results to return (max 50)
        country: Country code (e.g., 'us', 'gb', 'in', 'ca')
        
    Returns:
        List of job dictionaries
    """
    app_id = os.getenv("ADZUNA_APP_ID")
    app_key = os.getenv("ADZUNA_APP_KEY")
    
    if not app_id or not app_key:
        print("Error: Adzuna credentials not found in environment")
        return []
    
    try:
        # Build search query
        what = job_title.strip()
        where = location.strip() if location else ""
        
        # Adzuna API endpoint
        url = f"https://api.adzuna.com/v1/api/jobs/{country.lower()}/search/1"
        
        params = {
            "app_id": app_id,
            "app_key": app_key,
            "what": what,
            "results_per_page": min(max_results, 50),
            "content-type": "application/json"
        }
        
        # Handle remote search logic
        REMOTE_KEYWORDS = {"remote", "anywhere", "flexible", "work from home", "wfh", "virtual"}
        is_remote = where.lower() in REMOTE_KEYWORDS or any(rk in where.lower() for rk in REMOTE_KEYWORDS)

        if is_remote:
            what = f"{what} remote"
        elif where:
            params["where"] = where
            
        params["what"] = what

        # Make API request
        response = requests.get(url, params=params, timeout=10)
        response.raise_for_status()
        
        data = response.json()
        
        # Parse results
        jobs = []
        for result in data.get("results", []):
            job = {
                "id": result.get("id", ""),
                "title": result.get("title", ""),
                "company": result.get("company", {}).get("display_name", "Unknown Company"),
                "location": result.get("location", {}).get("display_name", location),
                "description": result.get("description", "")[:500],
                "salary_min": result.get("salary_min"),
                "salary_max": result.get("salary_max"),
                "salary_display": _format_salary(result.get("salary_min"), result.get("salary_max")),
                "posted_date": result.get("created", ""),
                "url": result.get("redirect_url", ""),
                "contract_type": result.get("contract_type", ""),
                "category": result.get("category", {}).get("label", ""),
                "source": "Adzuna"
            }
            jobs.append(job)
            
        return jobs
        
    except Exception as e:
        print(f"Adzuna search failed: {e}")
        return []

def _format_salary(min_salary: Optional[float], max_salary: Optional[float]) -> str:
    """Format salary range for display"""
    if min_salary and max_salary:
        return f"${int(min_salary):,} - ${int(max_salary):,}"
    elif min_salary:
        return f"${int(min_salary):,}+"
    elif max_salary:
        return f"Up to ${int(max_salary):,}"
    else:
        return "Not specified"
