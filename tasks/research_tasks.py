from crewai import Task
from textwrap import dedent

class ResearchTasks:
    """Research-related tasks for job search"""
    
    @staticmethod
    def job_search_task(agent, inputs):
        """Task for finding real job opportunities"""
        
        job_title = inputs.get('job_title', 'AI Engineer')
        location = inputs.get('location', 'Remote')
        experience = inputs.get('experience', '3-5 years')
        
        return Task(
            description=dedent(f"""
                Find real job opportunities for a {job_title} position.
                
                Search Parameters:
                - Job Title: {job_title}
                - Location: {location}
                - Experience Level: {experience}
                
                Your Task:
                1. Use the Adzuna Job Search tool to find 15-20 real job listings
                2. If Adzuna fails, try The Muse as backup
                3. Filter results to match the experience level
                4. Return structured job data including:
                   - Company name
                   - Job title
                   - Location
                   - Salary range (if available)
                   - Job description
                   - Posted date
                   - Application URL
                
                Focus on quality over quantity - prioritize relevant, recent postings.
            """),
            expected_output=dedent("""
                A JSON object containing:
                - List of 10-20 real job opportunities
                - Each job with: company, title, location, salary, description, url
                - Search metadata (source, total results found)
                - Jobs sorted by relevance and recency
            """),
            agent=agent
        )
