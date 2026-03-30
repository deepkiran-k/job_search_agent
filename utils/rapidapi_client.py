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
    "sa": "Saudi Arabia", "at": "Austria", "be": "Belgium",
    "ch": "Switzerland",
}
# Translation mapping for better Middle Eastern search recall on Google Jobs
ARABIC_MAPPING = {
    "software engineer": "Software Engineer OR مهندس برمجيات",
    "developer": "Developer OR مطور",
    "data scientist": "Data Scientist OR عالم بيانات",
    "product manager": "Product Manager OR مدير منتج",
    "designer": "Designer OR مصمم",
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

        # Arabic expansion for SA and AE to boost JSearch local board hits
        base_title = job_title.lower().strip()
        search_title = job_title
        if country.lower() in ["sa", "ae"]:
            for eng, ar in ARABIC_MAPPING.items():
                if eng in base_title:
                    search_title = ar
                    break

        query = f"{search_title}"
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
            "num_pages": str(max(1, fetch_limit // 10)),
            "country": country.lower(),
            "date_posted": "today" # Re-enabling freshness filter to avoid stale results
        }
        
        # Add remote filter specifically if requested
        # JSearch also takes remote filters through its own structure if needed,
        # but "remote" in query often suffices.
        REMOTE_KEYWORDS = {"remote", "anywhere", "virtual", "wfh"}
        if any(rk in location.lower() for rk in REMOTE_KEYWORDS):
            querystring["remote_jobs_only"] = "true"
        
        response = requests.get(url, headers=headers, params=querystring, timeout=60)
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
            
            # Fallback: If description is missing, build it from highlights (Google Jobs often does this)
            is_highlights_only = False
            if not desc:
                highlights = result.get("job_highlights", {})
                parts = []
                for key in ["Qualifications", "Responsibilities", "Benefits"]:
                    if highlights.get(key) and isinstance(highlights[key], list):
                        # Format as a bulleted section
                        section_text = f"\n{key}:\n" + "\n".join([f"• {item}" for item in highlights[key]])
                        parts.append(section_text)
                
                if parts:
                    desc = "\n".join(parts).strip()
                    is_highlights_only = True
            
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
                
            # Extract posted date in numeric YYYY-MM-DD format
            posted_date = ""
            raw_utc = result.get("job_posted_at_datetime_utc")
            ts = result.get("job_posted_at_timestamp")
            raw_relative = result.get("job_posted_at") # e.g. "قبل ٣ أيام" or "2 days ago"
            
            if raw_utc:
                posted_date = raw_utc[:10]
            elif ts:
                from datetime import datetime, timezone
                try:
                    posted_date = datetime.fromtimestamp(int(ts), tz=timezone.utc).strftime("%Y-%m-%d")
                except: pass
            
            # Final fallback: Parse "3 days ago" (even if localized) into a numeric date
            if not posted_date and raw_relative:
                posted_date = _parse_relative_date(raw_relative)

            job = {
                "id": result.get("job_id", ""),
                "title": title,
                "company": company,
                "location": location_display,
                "description": desc[:3000] if desc else "", # Increased limit slightly for formatted highlights
                "is_highlights_only": is_highlights_only,
                "salary_min": salary_min,
                "salary_max": salary_max,
                "salary_display": salary_display,
                "posted_date": posted_date,
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


def fetch_job_details(job_id: str, api_key: str) -> Optional[str]:
    """
    Fetch the full job description for a single job using JSearch's /job-details endpoint.
    
    Args:
        job_id: The JSearch job ID
        api_key: RapidAPI key
        
    Returns:
        Full job description string, or None if not available
    """
    try:
        url = "https://jsearch.p.rapidapi.com/job-details"
        headers = {
            "x-rapidapi-key": api_key,
            "x-rapidapi-host": "jsearch.p.rapidapi.com"
        }
        params = {"job_id": job_id, "extended_publisher_details": "false"}
        
        response = requests.get(url, headers=headers, params=params, timeout=30)
        response.raise_for_status()
        
        data = response.json()
        results = data.get("data", [])
        
        if results and len(results) > 0:
            desc = results[0].get("job_description", "")
            if desc and len(desc.strip()) > 50:
                return desc.strip()
        
        return None
        
    except Exception as e:
        print(f"JSearch job-details failed for {job_id}: {e}")
        return None


def enrich_jsearch_jobs(jobs: List[Dict[str, Any]], min_desc_length: int = 100) -> List[Dict[str, Any]]:
    """
    Enrich JSearch jobs that have missing or very short descriptions
    by calling the /job-details endpoint for each one that needs it.
    
    Only enriches jobs sourced from JSearch (identified by source field).
    Runs sequentially to be respectful of rate limits.
    
    Args:
        jobs: List of job dictionaries (may include Adzuna + JSearch jobs)
        min_desc_length: Minimum description length to consider "complete"
        
    Returns:
        The same list with descriptions filled in where possible
    """
    api_key = os.getenv("RAPIDAPI_KEY")
    if not api_key:
        return jobs
    
    enriched_count = 0
    
    for job in jobs:
        # Only enrich JSearch jobs — Adzuna has no detail endpoint
        if "JSearch" not in job.get("source", ""):
            continue
        
        desc = job.get("description", "")
        job_id = job.get("id", "")
        
        # Skip if description is already long enough or no job_id
        if len(desc.strip()) >= min_desc_length or not job_id:
            continue
        
        # Fetch full details
        full_desc = fetch_job_details(job_id, api_key)
        
        if full_desc:
            job["description"] = full_desc[:5000]  # Cap at 5000 chars
            job["is_highlights_only"] = False
            enriched_count += 1
            print(f"  [+] Enriched: {job.get('title', 'Unknown')} @ {job.get('company', 'Unknown')}")
        else:
            print(f"  [-] Could not enrich: {job.get('title', 'Unknown')} (no details available)")
    
    if enriched_count > 0:
        print(f"Enriched {enriched_count} job(s) with full descriptions.")
    
    return jobs


def _parse_relative_date(text: str) -> str:
    """
    Attempts to parse a relative date string (even if localized) 
    into a numeric YYYY-MM-DD string.
    """
    import re
    from datetime import datetime, timedelta
    
    # Normalize Arabic/Urdu digits to English digits
    arabic_digits = "٠١٢٣٤٥٦٧٨٩"
    for i, d in enumerate(arabic_digits):
        text = text.replace(d, str(i))
    
    # Extract the first number found
    match = re.search(r'(\d+)', text)
    if not match:
        return ""
    
    num = int(match.group(1))
    now = datetime.now()
    
    # Determine the unit (even if localized, we can check for common substrings or just assume days/hours)
    # Most JSearch relative strings are: "x hours ago", "x days ago", "x weeks ago", "x months ago"
    text_lower = text.lower()
    
    # Define keywords for supported languages
    # Days
    if any(k in text_lower for k in [
        "day", "يوم", "أيام", "tag", "jour", "día", "dia", "giorno", "dag", "dzień"
    ]):
        delta = timedelta(days=num)
    # Hours
    elif any(k in text_lower for k in [
        "hour", "ساعة", "stunde", "heure", "hora", "ora", "uur", "godzina"
    ]):
        delta = timedelta(hours=num)
    # Weeks
    elif any(k in text_lower for k in [
        "week", "أسبوع", "woche", "semaine", "semana", "settimana", "week", "tydzień"
    ]):
        delta = timedelta(weeks=num)
    # Months
    elif any(k in text_lower for k in [
        "month", "شهر", "monat", "mois", "mes", "mese", "maand", "miesiąc"
    ]):
        delta = timedelta(days=num * 30)
    else:
        # Default to days if we found a number but aren't sure of the unit
        delta = timedelta(days=num)
        
    return (now - delta).strftime("%Y-%m-%d")
