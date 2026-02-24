"""
Job Researcher Agent - Finds real job opportunities using Adzuna API
"""
from crewai import Agent
from tools.job_search_tools import AdzunaJobSearchTool, JobMatchingTool, TheMuseJobSearchTool
from config.settings import settings


class JobResearcher:
    """Job Research Agent - Now with REAL job search capabilities"""
    
    @staticmethod
    def create_agent():
        """Create and configure the job researcher agent with real API tools"""
        
        # Initialize real job search tools
        adzuna_tool = AdzunaJobSearchTool()
        muse_tool = TheMuseJobSearchTool()
        matching_tool = JobMatchingTool()
        
        # Create agent with enhanced capabilities
        agent = Agent(
            role="Senior Job Market Analyst & AI Recruiter",
            goal="""Find real job opportunities from Adzuna and other sources that 
            match the candidate's profile. Use AI to intelligently rank jobs by 
            fit, not just keyword matching.""",
            backstory="""You are an expert job market analyst with access to real-time 
            job listings from major job boards. You have extensive experience in tech 
            recruitment and know how to find both advertised and hidden opportunities.
            
            You're skilled at:
            - Searching multiple job sources (Adzuna, The Muse, etc.)
            - Using AI to match candidates beyond just keywords
            - Understanding job market trends and salary ranges
            - Identifying roles that match candidate's experience level
            - Finding remote and hybrid opportunities
            
            You always prioritize quality over quantity, returning the most relevant 
            opportunities for the candidate.""",
            verbose=True,
            allow_delegation=False,
            tools=[adzuna_tool, muse_tool, matching_tool],
            memory=False,
            llm=settings.get_gemini_llm(),
            max_iter=2
        )
        
        return agent
