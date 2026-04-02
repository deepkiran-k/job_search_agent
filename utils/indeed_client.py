import os
import requests
from typing import List, Dict, Any

def search_indeed(job_title: str, location: str = "", max_results: int = 20, country: str = "us", experience: str = "", global_english: bool = True) -> List[Dict[str, Any]]:
    """
    Search Indeed jobs via the NEW indeed-scraper-api RapidAPI.
    This replaces the old indeed12 client.
    """
    api_key = os.getenv("RAPIDAPI_KEY")
    if not api_key:
        print("Warning: RAPIDAPI_KEY not found in environment. Skipping Indeed.")
        return []

    try:
        url = "https://indeed-scraper-api.p.rapidapi.com/api/job"
        
        # Build payload according to the new API spec
        payload = {
            "scraper": {
                "maxRows": max_results,
                "query": job_title,
                "location": location or "",
                "country": country.lower(),
                "sort": "date",
                "fromDays": "7"
            }
        }
        
        # Map experience level if possible
        if experience:
            # Entry level check
            if any(x in experience.lower() for x in ["0-1", "1-3", "entry"]):
                payload["scraper"]["level"] = "entry_level"
            elif any(x in experience.lower() for x in ["5-", "senior", "lead"]):
                payload["scraper"]["level"] = "senior_level"
            else:
                payload["scraper"]["level"] = "mid_level"

        headers = {
            "x-rapidapi-key": api_key,
            "x-rapidapi-host": "indeed-scraper-api.p.rapidapi.com",
            "Content-Type": "application/json"
        }

        response = requests.post(url, json=payload, headers=headers, timeout=30)
        response.raise_for_status()
        data = response.json()
        
        print(f"DEBUG Indeed Response: {data}")

        # Parse results from the BullMQ/Scraper response structure
        # The API returns: { "state": "completed", "returnvalue": { "data": [...] }, "data": { "scraper": {...} } }
        # Job listings are in returnvalue.data, NOT data.scrapedJobs
        jobs_list = []
        if isinstance(data, dict):
            # Primary path: returnvalue.data (current API structure)
            rv = data.get("returnvalue", {})
            if isinstance(rv, dict) and isinstance(rv.get("data"), list):
                jobs_list = rv["data"]
            # Legacy fallback: data.scrapedJobs
            if not jobs_list:
                res_data = data.get("data", {})
                if isinstance(res_data, dict):
                    jobs_list = res_data.get("scrapedJobs", [])
            # Another fallback
            if not jobs_list:
                jobs_list = data.get("results", [])

        print(f"DEBUG Indeed parsed {len(jobs_list)} jobs from response for country={country}")

        formatted_jobs = []
        for j in jobs_list[:max_results]:
            title = j.get("title", "")
            company = j.get("companyName", j.get("company", "Company"))
            
            # Location parsing
            loc_obj = j.get("location", {})
            if isinstance(loc_obj, dict):
                loc_str = loc_obj.get("formattedAddressShort", loc_obj.get("city", "Remote"))
            else:
                loc_str = str(loc_obj)

            # Salary parsing
            salary_obj = j.get("salary", {})
            salary_str = ""
            if isinstance(salary_obj, dict):
                salary_str = salary_obj.get("salaryText", "")

            # URL and Date
            job_url = j.get("jobUrl", "")
            post_date = j.get("datePublished", j.get("age", ""))
            
            formatted_job = {
                "id": f"indeed_{j.get('jobKey', hash(title+company))}",
                "job_id_raw": j.get("jobKey", ""),
                "locality": country.lower(),
                "title": title,
                "company": company,
                "location": loc_str,
                "description": j.get("descriptionText", j.get("descriptionHtml", "")),
                "url": job_url,
                "salary_display": salary_str,
                "source": "Indeed",
                "posted_date": post_date,
                "posted_timestamp": 0, # Could be parsed from datePublished
                "is_highlights_only": False # This new API gives full text!
            }
            formatted_jobs.append(formatted_job)

        return formatted_jobs

    except Exception as e:
        print(f"Error fetching from Indeed-Scraper: {e}")
        return []

def enrich_indeed_job(job_id_raw: str, locality: str = "us") -> str:
    """
    Stub for backward compatibility. 
    New API returns full text in search_indeed.
    """
    return ""
