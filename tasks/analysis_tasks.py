from crewai import Task
from textwrap import dedent

class AnalysisTasks:
    """Analysis-related tasks for resume and cover letters"""
    
    @staticmethod
    def resume_analysis_task(agent, inputs):
        """Task for analyzing resume and ranking jobs"""
        
        resume = inputs.get('resume', '')
        job_title = inputs.get('job_title', 'AI Engineer')
        
        return Task(
            description=dedent(f"""
                Analyze the candidate's resume and rank job opportunities by match quality.
                
                Resume to Analyze:
                {resume[:1000]}...
                
                Target Role: {job_title}
                
                Your Task:
                1. Use the Gemini ATS Analyzer tool to get comprehensive ATS score
                2. Analyze resume against general {job_title} requirements
                3. Use the AI Job Ranker tool to rank the jobs found by the Job Researcher
                4. Identify:
                   - Overall ATS score (0-100)
                   - Keyword match percentage
                   - Missing critical keywords
                   - Top 3-5 strengths
                   - Top 3-5 weaknesses
                   - Specific, actionable improvement suggestions
                   - Interview probability estimate
                5. Rank all jobs by true fit (not just keyword matching)
                6. Provide detailed match analysis for top 5 jobs
                
                Be specific and actionable - no generic advice.
            """),
            expected_output=dedent("""
                A comprehensive JSON object containing:
                - ats_score (integer 0-100)
                - keyword_match (integer 0-100)
                - missing_keywords (list)
                - strengths (list)
                - weaknesses (list)
                - specific_suggestions (list)
                - interview_probability (integer 0-100)
                - market_value (string)
                - analysis_summary (string)
            """),
            agent=agent,
            context=[inputs.get('job_search_task')]  # Depends on job search results
        )
    
    @staticmethod
    def cover_letter_task(agent, inputs):
        """Task for generating personalized cover letter"""
        
        job_title = inputs.get('job_title', 'AI Engineer')
        
        return Task(
            description=dedent(f"""
                Generate a compelling, personalized cover letter for the top job match.
                
                Target Role: {job_title}
                
                Your Task:
                1. Review the top-ranked job from the Resume Analyst's output
                2. Review the ATS analysis and candidate strengths
                3. Use the Gemini Cover Letter Generator tool to create a personalized letter
                4. Ensure the cover letter:
                   - Starts with a strong, specific opening (not generic)
                   - Highlights 3-4 most relevant achievements with metrics
                   - Shows specific knowledge about the company/role
                   - Incorporates insights from ATS analysis
                   - Ends with confident call to action
                   - Stays concise (250-350 words, 3-4 paragraphs)
                   - Uses professional but warm tone
                
                Make it compelling and tailored - not a generic template.
            """),
            expected_output=dedent("""
                A JSON object containing:
                - cover_letter (full text of the cover letter)
                - job_title (string)
                - company (string)
                - word_count (integer)
            """),
            agent=agent,
            context=[
                inputs.get('job_search_task'),
                inputs.get('resume_analysis_task')
            ]  # Depends on both previous tasks
        )
