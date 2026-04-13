import os
import requests
from typing import List, Dict, Any
from utils.exceptions import RateLimitError

def search_serpapi(job_title: str, location: str = "", max_results: int = 15, country: str = "us", experience: str = "", global_english: bool = True) -> List[Dict[str, Any]]:
    """
    Search Google Jobs using SerpApi.
    SerpApi usually returns the full job descriptions, so we don't need secondary enrichment.
    """
    api_key = os.getenv("SERPAPI_KEY")
    if not api_key:
        print("Warning: SERPAPI_KEY not found in environment. Skipping SerpApi (Google Jobs).")
        return []

    try:
        url = "https://serpapi.com/search"
        
        # Google Jobs usually searches by "title in location" logic internally via 'q' parameter
        query = job_title.strip()
        if location.strip():
            query += f" in {location.strip()}"
            
        if not query:
            return []

        params = {
            "engine": "google_jobs",
            "q": query,
            "hl": "en",
            "gl": country.lower(),
            "api_key": api_key
        }
        
        # Explicitly use the location parameter if provided, 
        # or hint with the country if location is empty to avoid defaulting to US
        if location.strip():
            params["location"] = location.strip()
        else:
            # Simple mapping for common countries to help SerpApi/Google Jobs center the search
            country_hints = {
                "ae": "United Arab Emirates",
                "sa": "Saudi Arabia",
                "gb": "United Kingdom",
                "us": "United States",
                "ca": "Canada",
                "au": "Australia",
                "in": "India",
                "de": "Germany",
                "fr": "France",
                "tr": "Turkey",
            }
            params["location"] = country_hints.get(country.lower(), country.upper())

        response = requests.get(url, params=params, timeout=30)
        response.raise_for_status()
        data = response.json()

        jobs = data.get("jobs_results", [])
        formatted_jobs = []
        for j in jobs[:max_results]:
            title = j.get("title", "")
            company = j.get("company_name", "")
            loc = j.get("location", "")
            description = j.get("description", "")
            job_id = j.get("job_id", str(hash(title + company)))
            
            # SerpApi offers an 'apply_options' array
            apply_url = ""
            if "apply_options" in j and isinstance(j["apply_options"], list) and len(j["apply_options"]) > 0:
                apply_url = j["apply_options"][0].get("link", "")
            if not apply_url:
                apply_url = j.get("share_link", "")

            formatted_job = {
                "id": f"serpapi_{job_id}",
                "title": title,
                "company": company,
                "location": loc,
                "description": description[:6000],  # SerpApi usually fetches very complete descriptions
                "url": apply_url,
                "source": "GoogleJobs (SerpApi)",
                "is_highlights_only": False,
            }

            # Parse extra detected parameters
            if "detected_extensions" in j:
                ext = j["detected_extensions"]
                if "schedule_type" in ext:
                    formatted_job["contract_type"] = ext["schedule_type"]
                if "salary" in ext:
                    formatted_job["salary_display"] = ext["salary"]

            # Simple timestamp fallback for SerpApi sorting
            if "posted_date" in formatted_job:
                pd = formatted_job["posted_date"].lower()
                ts_offset = 0
                import time
                if "minute" in pd: ts_offset = 60
                elif "hour" in pd: ts_offset = 3600 
                elif "day" in pd: 
                    try: ts_offset = 86400 * int(pd.split()[0])
                    except: ts_offset = 86400
                elif "week" in pd: 
                    try: ts_offset = 604800 * int(pd.split()[0])
                    except: ts_offset = 604800
                formatted_job["posted_timestamp"] = time.time() - ts_offset

            formatted_jobs.append(formatted_job)

        return formatted_jobs[:max_results]
    except Exception as e:
        if isinstance(e, requests.exceptions.HTTPError) and e.response.status_code == 429:
            raise RateLimitError(source="Google Jobs (SerpApi)")
        if "429" in str(e):
            raise RateLimitError(source="Google Jobs (SerpApi)")
        print(f"Error fetching from GoogleJobs (SerpApi): {e}")
        return []
