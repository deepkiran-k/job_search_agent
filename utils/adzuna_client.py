import os
import requests
import json
import re
from typing import List, Dict, Any, Optional
from dotenv import load_dotenv

load_dotenv()

# If user types a country name instead of a city, skip `where` for Adzuna
# (the country is already encoded in the API URL via the country code)
COUNTRY_NAMES = {
    "india", "united states", "usa", "us", "united kingdom", "uk", "canada",
    "australia", "germany", "france", "italy", "netherlands", "poland",
    "spain", "brazil", "mexico", "south africa", "new zealand", "singapore",
    "united arab emirates", "uae", "saudi arabia", "austria", "belgium",
    "switzerland",
}

def search_adzuna(job_title: str, location: str = "", max_results: int = 20, country: str = "us", experience: str = "") -> List[Dict[str, Any]]:
    """
    Search Adzuna API for job listings.
    
    Args:
        job_title: Job title to search for
        location: Location (city, state, or "remote")
        max_results: Maximum number of results to return (max 50)
        country: Country code (e.g., 'us', 'gb', 'in', 'ca')
        experience: Experience level required (e.g. '0-1 years')
        
    Returns:
        List of job dictionaries
    """
    app_id = os.getenv("ADZUNA_APP_ID")
    app_key = os.getenv("ADZUNA_APP_KEY")
    
    if not app_id or not app_key:
        print("Error: Adzuna credentials not found in environment")
        return []
    
    # Adzuna does not support these regions. Skip to avoid 404 errors.
    if country.lower() in ["sa", "ae"]:
        return []
        
    try:
        # Build search query
        what = job_title.strip()
        where = location.strip() if location else ""
        
        # Adzuna API endpoint
        url = f"https://api.adzuna.com/v1/api/jobs/{country.lower()}/search/1"
        
        # We fetch more if we need to filter locally
        fetch_limit = min(max_results * 3, 50) if experience else min(max_results, 50)
        
        params = {
            "app_id": app_id,
            "app_key": app_key,
            "what": what,
            "results_per_page": fetch_limit,
            "content-type": "application/json",
            "sort_by": "date",
        }
        
        # Handle remote search logic
        REMOTE_KEYWORDS = {"remote", "anywhere", "flexible", "work from home", "wfh", "virtual"}
        is_remote = where.lower() in REMOTE_KEYWORDS or any(rk in where.lower() for rk in REMOTE_KEYWORDS)

        # Skip `where` if user typed a country name — Adzuna already scopes by
        # country via the URL path, and passing the country name as `where`
        # causes 0 results (expects a city/region).
        if is_remote:
            what = f"{what} remote"
        elif where and where.lower() not in COUNTRY_NAMES:
            params["where"] = where
            
        params["what"] = what

        # Make API request
        response = requests.get(url, params=params, timeout=10)
        response.raise_for_status()
        
        data = response.json()
        
        # Parse results
        jobs = []
        
        # Precompile regex for experience filtering
        exclude_titles_re = None
        exclude_desc_re = None
        
        if experience == "0-1 years":
            exclude_titles_re = re.compile(r'\b(senior|lead|principal|director|manager|head)\b', re.IGNORECASE)
            exclude_desc_re = re.compile(r'([2-9]|[1-9][0-9])\+?\s*years?(?:\s*of)?\s*(?:experience|exp)', re.IGNORECASE)
        elif experience == "1-3 years":
            exclude_titles_re = re.compile(r'\b(senior|principal|director|head|lead)\b', re.IGNORECASE)
            exclude_desc_re = re.compile(r'([4-9]|[1-9][0-9])\+?\s*years?(?:\s*of)?\s*(?:experience|exp)', re.IGNORECASE)
        elif experience in ["5-10 years", "10+ years"]:
            exclude_titles_re = re.compile(r'\b(junior|entry|graduate|trainee|intern)\b', re.IGNORECASE)
            
        for result in data.get("results", []):
            title = result.get("title", "")
            company = result.get("company", {}).get("display_name", "Unknown Company")
            desc = result.get("description", "")
            
            # Apply experience filters
            if experience:
                text_to_check = f"{title} {desc}"
                if exclude_titles_re and exclude_titles_re.search(title):
                    continue
                if exclude_desc_re and exclude_desc_re.search(text_to_check):
                    continue
                    
            job = {
                "id": result.get("id", ""),
                "title": title,
                "company": company,
                "location": result.get("location", {}).get("display_name", location),
                "description": desc[:2000],
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
            
            if len(jobs) >= max_results:
                break
            
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
