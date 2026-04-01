import os
import requests
from typing import List, Dict, Any

def search_indeed(job_title: str, location: str = "", max_results: int = 20, country: str = "us", experience: str = "", global_english: bool = True) -> List[Dict[str, Any]]:
    """
    Search Indeed jobs via the indeed12 RapidAPI wrapper.
    """
    api_key = os.getenv("RAPIDAPI_KEY")
    if not api_key:
        print("Warning: RAPIDAPI_KEY not found in environment. Skipping Indeed.")
        return []

    try:
        if not job_title.strip() and not location.strip():
            return []

        url = "https://indeed12.p.rapidapi.com/jobs/search"
        querystring = {
            "query": job_title,
            "location": location,
            "page_id": "1" # Typically sufficient to grab the first batch
        }

        # Indeed APIs usually parse location directly, but sometimes have a locality setting 
        if country:
            querystring["locality"] = country.lower()

        headers = {
            "x-rapidapi-key": api_key,
            "x-rapidapi-host": "indeed12.p.rapidapi.com"
        }

        response = requests.get(url, headers=headers, params=querystring, timeout=30)
        response.raise_for_status()
        data = response.json()

        # Accommodate various list locations commonly seen in RapidAPI wrappers
        jobs = data
        if isinstance(data, dict):
            jobs = data.get("hits", data.get("data", data.get("jobs", data.get("results", []))))
        if not isinstance(jobs, list):
            jobs = []

        formatted_jobs = []
        for j in jobs[:max_results]:
            # Accommodate various key names for standard fields
            title = j.get("title", j.get("job_title", ""))
            company = j.get("company_name", j.get("company", ""))
            loc = j.get("location", "")
            description = j.get("description", j.get("snippet", j.get("summary", "")))
            job_id = j.get("id", j.get("job_id", str(hash(title+company))))
            url_link = j.get("url", j.get("job_url", j.get("link", "")))
            salary_raw = j.get("salary", j.get("salary_display", ""))
            salary_str = ""
            if isinstance(salary_raw, dict):
                s_min = salary_raw.get("min")
                s_max = salary_raw.get("max")
                s_type = salary_raw.get("type", "").lower()
                # Ensure we don't show broken -1 or empty values
                if s_min and s_max and float(s_max) > 0 and float(s_min) > 0: 
                    salary_str = f"{s_min} - {s_max} {s_type}"
                elif s_min and float(s_min) > 0: 
                    salary_str = f"{s_min} {s_type}"
            elif salary_raw and str(salary_raw).lower() not in ["0", "none", "nan"]:
                salary_str = str(salary_raw)

            post_date = j.get("formatted_relative_time", j.get("date_posted", j.get("created_at", "")))
            # Sortable timestamp fallback to 0
            ts = j.get("pub_date_ts_milli", 0) 
            if ts: ts = int(ts) / 1000 # Convert to seconds if it's milli

            locality = j.get("locality", country.lower())

            # Use the standard Indeed 'viewjob?jk=' format which is more reliable than the relative '/job/id' path
            domain = f"https://{locality}.indeed.com" if locality != "us" else "https://www.indeed.com"
            url_link = f"{domain}/viewjob?jk={job_id}"

            formatted_job = {
                "id": f"indeed_{job_id}",
                "job_id_raw": job_id,
                "locality": locality,
                "title": title,
                "company": company,
                "location": loc,
                "description": description[:6000] if description else "", 
                "url": url_link,
                "salary_display": salary_str,
                "source": "Indeed",
                "posted_date": post_date,
                "posted_timestamp": ts,
                "is_highlights_only": True,
            }
            formatted_jobs.append(formatted_job)

        return formatted_jobs[:max_results]
    except Exception as e:
        print(f"Error fetching from Indeed: {e}")
        return []

def enrich_indeed_job(job_id_raw: str, locality: str = "us") -> str:
    """
    Fetch the full description for an Indeed job using the details endpoint.
    """
    api_key = os.getenv("RAPIDAPI_KEY")
    if not api_key:
        return ""
    
    try:
        url = "https://indeed12.p.rapidapi.com/job/details"
        params = {"id": job_id_raw, "locality": locality}
        headers = {
            "x-rapidapi-key": api_key,
            "x-rapidapi-host": "indeed12.p.rapidapi.com"
        }
        
        response = requests.get(url, headers=headers, params=params, timeout=20)
        response.raise_for_status()
        data = response.json()
        
        # Details endpoint usually returns the description directly
        if isinstance(data, dict):
            return data.get("description", "")
        return ""
    except Exception as e:
        print(f"Indeed enrichment failed: {e}")
        return ""
