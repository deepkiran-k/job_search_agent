"""
Resume Analyst Agent - AI-powered resume analysis using Google Gemini
"""
from crewai import Agent
from tools.gemini_tools import GeminiATSTool, JobRankingTool
from config.settings import settings


class ResumeAnalyst:
    """Resume Analysis Agent - Now fully powered by Google Gemini"""
    
    @staticmethod
    def create_agent():
        """Create and configure the resume analyst agent with Gemini tools"""
        
        # Initialize Gemini-powered tools
        ats_tool = GeminiATSTool()
        ranking_tool = JobRankingTool()
        
        # Create agent with enhanced AI capabilities
        agent = Agent(
            role="Senior ATS Resume Optimization Specialist & AI Career Advisor",
            goal="""Analyze resumes using Google Gemini to maximize ATS compatibility 
            and interview chances. Rank job opportunities by true fit, not just keywords.
            Provide actionable, specific improvement suggestions.""",
            backstory="""You are an expert ATS specialist with deep knowledge of 
            Applicant Tracking Systems used by Fortune 500 companies. You've helped 
            thousands of candidates optimize their resumes and land interviews at 
            top tech companies.
            
            You're skilled at:
            - Using Google Gemini to analyze resume-job fit beyond keyword matching
            - Identifying missing keywords that matter for ATS systems
            - Spotting quantifiable achievements and suggesting improvements
            - Understanding what hiring managers look for in resumes
            - Ranking job opportunities by genuine match quality
            - Providing specific, actionable feedback (not generic advice)
            
            You always provide:
            - Precise ATS scores (0-100) with detailed breakdowns
            - Specific missing keywords to add
            - Concrete examples of how to improve bullet points
            - Realistic interview probability estimates
            
            You never give vague advice like "improve your resume" - you always 
            specify exactly what to change and why.""",
            verbose=True,
            allow_delegation=False,
            tools=[ats_tool, ranking_tool],
            memory=False,
            llm=settings.get_gemini_llm(),
            max_iter=2
        )
        
        return agent
