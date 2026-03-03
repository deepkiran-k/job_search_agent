import os
import requests
import re
from typing import List, Dict, Any, Optional
from dotenv import load_dotenv

load_dotenv()

# Map country codes to full names for JSearch query fallback
COUNTRY_CODE_TO_NAME = {
    "us": "United States", "gb": "United Kingdom", "ca": "Canada",
    "au": "Australia", "in": "India", "ae": "United Arab Emirates",
    "de": "Germany", "fr": "France", "it": "Italy", "nl": "Netherlands",
    "pl": "Poland", "es": "Spain", "br": "Brazil", "mx": "Mexico",
    "za": "South Africa", "nz": "New Zealand", "sg": "Singapore",
}

def search_jsearch(job_title: str, location: str = "", max_results: int = 20, experience: str = "", country: str = "us") -> List[Dict[str, Any]]:
    """
    Search JSearch (Google Jobs via RapidAPI) for fresh job listings.
    
    Args:
        job_title: Job title to search for
        location: Location (city, state, or "remote") — optional
        max_results: Maximum number of results to return
        experience: Experience level required (e.g. '0-1 years')
        country: Country code (e.g. 'us', 'in') — used as fallback when location is blank
        
    Returns:
        List of job dictionaries matching the standard internal format
    """
    api_key = os.getenv("RAPIDAPI_KEY")
    
    if not api_key:
        print("Warning: RAPIDAPI_KEY not found in environment. Skipping JSearch.")
        return []

    try:
        url = "https://jsearch.p.rapidapi.com/search"
        
        # Build query string
        # If no specific location given, fall back to the selected country name
        effective_location = location.strip()
        if not effective_location:
            effective_location = COUNTRY_CODE_TO_NAME.get(country.lower(), "")

        query = f"{job_title}"
        if effective_location:
            query += f" in {effective_location}"
            
        headers = {
            "x-rapidapi-key": api_key,
            "x-rapidapi-host": "jsearch.p.rapidapi.com"
        }
        
        # Fetch extra results to allow for local filtering
        fetch_limit = min(max_results * 2, 50) if experience else max_results
        
        # We enforce recent jobs sorting via date_posted
        querystring = {
            "query": query,
            "page": "1",
            "num_pages": "1",
            # 3days gives the freshest listings without being too narrow (today can timeout)
            "date_posted": "3days"
        }
        
        # Add remote filter specifically if requested
        # JSearch also takes remote filters through its own structure if needed,
        # but "remote" in query often suffices.
        REMOTE_KEYWORDS = {"remote", "anywhere", "virtual", "wfh"}
        if any(rk in location.lower() for rk in REMOTE_KEYWORDS):
            querystring["remote_jobs_only"] = "true"
        
        response = requests.get(url, headers=headers, params=querystring, timeout=20)
        response.raise_for_status()
        
        data = response.json()
        
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
            
        for result in data.get("data", []):
            title = result.get("job_title", "")
            company = result.get("employer_name", "Unknown Company")
            desc = result.get("job_description", "")
            
            # Apply experience filters locally
            if experience:
                text_to_check = f"{title} {desc}"
                if exclude_titles_re and exclude_titles_re.search(title):
                    continue
                if exclude_desc_re and exclude_desc_re.search(text_to_check):
                    continue
            
            # Try to grab salary
            salary_display = "Not specified"
            salary_min = result.get("job_min_salary")
            salary_max = result.get("job_max_salary")
            
            if salary_min and salary_max:
                salary_display = f"${int(salary_min):,} - ${int(salary_max):,}"
            elif salary_min:
                salary_display = f"${int(salary_min):,}+"
                
            # Job location formatting
            loc_parts = []
            if result.get("job_city"): loc_parts.append(result["job_city"])
            if result.get("job_state"): loc_parts.append(result["job_state"])
            if result.get("job_country"): loc_parts.append(result["job_country"])
            
            is_remote = result.get("job_is_remote", False)
            if is_remote:
                if loc_parts:
                    location_display = "Remote (" + ", ".join(loc_parts) + ")"
                else:
                    location_display = "Remote"
            else:
                location_display = ", ".join(loc_parts) if loc_parts else location
                
            job = {
                "id": result.get("job_id", ""),
                "title": title,
                "company": company,
                "location": location_display,
                "description": desc[:2000] if desc else "",
                "salary_min": salary_min,
                "salary_max": salary_max,
                "salary_display": salary_display,
                "posted_date": result.get("job_posted_at_datetime_utc", ""),
                "url": result.get("job_apply_link", ""),
                "contract_type": result.get("job_employment_type", ""),
                "category": title, # Jsearch doesn't have a distinct broad category field
                "source": "JSearch (Google)"
            }
            jobs.append(job)
            
            if len(jobs) >= max_results:
                break
                
        return jobs
        
    except Exception as e:
        print(f"JSearch failed: {e}")
        return []
