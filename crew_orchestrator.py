"""
CrewAI Orchestration - Full multi-agent workflow for job search
"""
import os
import re
import json

# CrewAI requires OPENAI_API_KEY to be set even when using other LLMs.
# Set a dummy value to prevent internal validation errors.
if not os.environ.get("OPENAI_API_KEY"):
    os.environ["OPENAI_API_KEY"] = "sk-dummy-not-used-gemini-handles-llm"

from crewai import Crew, Process
from agents.job_researcher import JobResearcher
from agents.resume_analyst import ResumeAnalyst
from agents.cover_writer import CoverWriter
from tasks.research_tasks import ResearchTasks
from tasks.analysis_tasks import AnalysisTasks


class JobSearchCrew:
    """Orchestrates the full job search workflow using CrewAI"""
    
    def __init__(self):
        """Initialize all agents"""
        self.job_researcher = JobResearcher.create_agent()
        self.resume_analyst = ResumeAnalyst.create_agent()
        self.cover_writer = CoverWriter.create_agent()
    
    def run(self, job_title: str, location: str, experience: str, resume: str):
        """Execute the full job search workflow"""
        
        inputs = {
            'job_title': job_title,
            'location': location,
            'experience': experience,
            'resume': resume
        }
        
        job_search_task = ResearchTasks.job_search_task(self.job_researcher, inputs)
        inputs['job_search_task'] = job_search_task
        
        resume_analysis_task = AnalysisTasks.resume_analysis_task(self.resume_analyst, inputs)
        inputs['resume_analysis_task'] = resume_analysis_task
        
        cover_letter_task = AnalysisTasks.cover_letter_task(self.cover_writer, inputs)
        
        crew = Crew(
            agents=[self.job_researcher, self.resume_analyst, self.cover_writer],
            tasks=[job_search_task, resume_analysis_task, cover_letter_task],
            process=Process.sequential,
            memory=False,
            verbose=True
        )
        
        result = crew.kickoff(inputs=inputs)
        
        return self._parse_results(result, job_search_task, resume_analysis_task, cover_letter_task)
    
    def _extract_final_answer(self, raw_text: str) -> str:
        """
        Extract just the Final Answer section from a CrewAI agent chain output.
        Falls back to full text if no marker found.
        """
        if not raw_text:
            return ""
        match = re.search(r'Final Answer\s*:\s*([\s\S]+)$', raw_text, re.IGNORECASE)
        if match:
            return match.group(1).strip()
        return raw_text.strip()

    def _extract_best_json(self, text: str):
        """
        Scan the entire text for JSON objects and return the most complete one.
        Tries (in order):
          1. All ```json ... ``` code fences
          2. All bare { ... } blocks
        Picks the candidate with the most keys (most complete data).
        Returns parsed dict/list or None.
        """
        candidates = []

        # 1. Extract from ```json ... ``` or ``` ... ``` fences
        for m in re.finditer(r'```(?:json)?\s*(\{[\s\S]*?\})\s*```', text):
            try:
                obj = json.loads(m.group(1))
                candidates.append(obj)
            except Exception:
                pass

        # 2. Find all { ... } blocks (greedy from each '{')
        start = 0
        while True:
            idx = text.find('{', start)
            if idx == -1:
                break
            # Try progressively shorter substrings from the last '}' 
            end = len(text)
            parsed = None
            while end > idx:
                last = text.rfind('}', idx, end)
                if last == -1:
                    break
                try:
                    obj = json.loads(text[idx:last+1])
                    parsed = obj
                    break
                except Exception:
                    end = last  # shrink and retry
            if parsed is not None:
                candidates.append(parsed)
            start = idx + 1

        if not candidates:
            return None

        # Pick the candidate dict with the most keys (most complete)
        def score(c):
            if isinstance(c, dict):
                return len(c)
            return 0

        return max(candidates, key=score)

    def _safe_json_parse(self, text: str):
        """Safely parse JSON from a text string, scanning the whole text"""
        if not text or not isinstance(text, str):
            return text

        # Try direct parse first (fastest path)
        try:
            return json.loads(text.strip())
        except Exception:
            pass

        # Scan entire text for best JSON object
        result = self._extract_best_json(text)
        if result is not None:
            return result

        return text


    def _normalize_analysis(self, data: dict) -> dict:
        """Normalize Gemini's analysis output to a consistent flat structure"""
        if not isinstance(data, dict):
            return data
        
        # Handle nested ats_score: {"overall_score": 88, "keyword_match_percentage": 92, ...}
        ats = data.get('ats_score', {})
        if isinstance(ats, dict):
            data['ats_score'] = ats.get('overall_score', ats.get('score', 75))
            if 'keyword_match' not in data:
                data['keyword_match'] = ats.get('keyword_match_percentage', 70)

        # Map improvement_suggestions (list of dicts) -> specific_suggestions (list of strings)
        if 'improvement_suggestions' in data and 'specific_suggestions' not in data:
            suggestions = data['improvement_suggestions']
            if isinstance(suggestions, list):
                data['specific_suggestions'] = [
                    s.get('suggestion', str(s)) if isinstance(s, dict) else str(s)
                    for s in suggestions
                ]

        # Map interview_probability_estimate -> interview_probability
        if 'interview_probability_estimate' in data and 'interview_probability' not in data:
            val = str(data['interview_probability_estimate']).replace('%', '').strip()
            if '-' in val:
                parts = val.split('-')
                try:
                    data['interview_probability'] = int((int(parts[0].strip()) + int(parts[1].strip())) / 2)
                except Exception:
                    data['interview_probability'] = 70
            else:
                try:
                    data['interview_probability'] = int(val)
                except Exception:
                    data['interview_probability'] = 70

        return data

    def _get_task_output(self, task_obj) -> str:
        """Extract the full raw output string from a CrewAI task object"""
        if task_obj is None:
            return ""
        output = getattr(task_obj, 'output', None)
        if output is None:
            return ""
        # TaskOutput.raw contains the full agent chain text — return it all
        # so _extract_best_json can scan the entire thing for JSON
        raw = getattr(output, 'raw', None)
        if raw:
            return raw
        exported = getattr(output, 'exported_output', None)
        if exported:
            return str(exported)
        return str(output)

    def _parse_results(self, crew_result, job_task, analysis_task, cover_task):
        """Parse crew results into structured format"""
        
        try:
            # Get the full raw output from each task (entire agent chain text)
            jobs_raw = self._get_task_output(job_task)
            analysis_raw = self._get_task_output(analysis_task)
            cover_raw = self._get_task_output(cover_task)

            # Scan the ENTIRE raw output for the best JSON block
            # (the JSON may be in a code fence anywhere in the reasoning chain)
            jobs_data = self._safe_json_parse(jobs_raw)
            analysis_data = self._safe_json_parse(analysis_raw)
            cover_data = self._safe_json_parse(cover_raw)

            # Normalize analysis structure
            if isinstance(analysis_data, dict):
                analysis_data = self._normalize_analysis(analysis_data)

            # Extract cover letter text
            cover_letter_text = ""
            if isinstance(cover_data, dict):
                cover_letter_text = cover_data.get('cover_letter', '')
            if not cover_letter_text:
                # Try to extract from the Final Answer section as plain text
                final = self._extract_final_answer(cover_raw)
                # Strip any JSON wrapper if present
                if final and not final.strip().startswith('{'):
                    cover_letter_text = final

            return {
                'success': True,
                'jobs': jobs_data.get('jobs', []) if isinstance(jobs_data, dict) else [],
                'analysis': analysis_data if isinstance(analysis_data, dict) else {},
                'cover_letter': cover_letter_text,
                'raw_output': str(crew_result)
            }
            
        except Exception as e:
            print(f"Parse error: {e}")
            return {
                'success': False,
                'error': str(e),
                'jobs': [],
                'analysis': {},
                'cover_letter': '',
                'raw_output': str(crew_result)
            }



def run_job_search_crew(job_title: str, location: str, experience: str, resume: str):
    """Convenience function to run the job search crew"""
    crew = JobSearchCrew()
    return crew.run(job_title, location, experience, resume)
