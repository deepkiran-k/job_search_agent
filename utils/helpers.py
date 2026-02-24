"""
Helper functions for the Job Search Crew
"""
import json
import re
from typing import Dict, List, Any
from datetime import datetime

def create_mock_jobs(job_title: str, count: int = 5) -> List[Dict[str, Any]]:
    """Create mock job listings for demo purposes"""
    
    companies = [
        "TechCorp Innovations",
        "DataSystems Ltd",
        "AI Ventures",
        "CloudFirst Technologies",
        "FutureTech Solutions",
        "Digital Dynamics",
        "Smart Systems Inc",
        "NextGen AI Labs"
    ]
    
    locations = ["Remote", "San Francisco, CA", "New York, NY", "Austin, TX", "Seattle, WA"]
    
    jobs = []
    for i in range(min(count, 8)):
        jobs.append({
            "id": i + 1,
            "title": f"Senior {job_title}",
            "company": companies[i % len(companies)],
            "location": locations[i % len(locations)],
            "salary": f"${120000 + i*10000} - ${180000 + i*10000}",
            "description": f"Looking for experienced {job_title} with {3+i} years experience...",
            "posted": f"{i+1} days ago",
            "match_score": 85 + i*3,
            "source": "Mock Data",
            "apply_url": "#"
        })
    
    return jobs

def create_mock_resume() -> str:
    """Create a sample resume for demo"""
    return """
JOHN DOE
AI Engineer | Machine Learning Specialist
john.doe@email.com | (123) 456-7890 | linkedin.com/in/johndoe

SUMMARY
Senior AI Engineer with 5+ years of experience in designing and implementing machine learning solutions. 
Expert in Python, TensorFlow, and cloud platforms. Passionate about solving complex problems with AI.

EXPERIENCE
Senior AI Engineer, TechCorp Inc. (2021-Present)
• Developed ML models that improved recommendation accuracy by 35%
• Led team of 4 engineers in deploying production AI systems
• Reduced inference latency by 40% through model optimization

Machine Learning Engineer, DataSystems Ltd. (2019-2021)
• Built predictive models for customer behavior analysis
• Implemented automated data pipelines processing 1TB+ daily
• Improved model accuracy by 25% through feature engineering

SKILLS
• Programming: Python, SQL, Java
• ML Frameworks: TensorFlow, PyTorch, Scikit-learn
• Cloud: AWS, Azure, Docker, Kubernetes
• Tools: Git, Jupyter, Airflow, Spark

EDUCATION
M.S. in Computer Science, Stanford University (2019)
B.S. in Computer Engineering, MIT (2017)

PROJECTS
• Customer Churn Prediction: Built model with 92% accuracy
• Image Classification System: 95% accuracy on custom dataset
• NLP Sentiment Analysis: Real-time analysis of customer reviews
"""

def extract_json_from_text(text: str) -> Dict[str, Any]:
    """Extract JSON from text response"""
    try:
        # Try direct JSON parse
        return json.loads(text)
    except:
        # Try to find JSON in the text
        try:
            if "```json" in text:
                json_str = text.split("```json")[1].split("```")[0]
                return json.loads(json_str)
        except:
            pass
        
        # Try to find any JSON-like structure
        try:
            json_match = re.search(r'\{.*\}', text, re.DOTALL)
            if json_match:
                return json.loads(json_match.group())
        except:
            pass
    
    # Return empty dict if no JSON found
    return {}

def format_datetime(dt: datetime = None) -> str:
    """Format datetime for display"""
    if dt is None:
        dt = datetime.now()
    return dt.strftime("%Y-%m-%d %H:%M:%S")

def validate_resume_text(text: str) -> tuple[bool, str]:
    """Validate resume text"""
    if not text or len(text.strip()) < 50:
        return False, "Resume text is too short (minimum 50 characters)"
    
    if len(text) > 10000:
        return False, "Resume text is too long (maximum 10,000 characters)"
    
    # Check for reasonable content
    words = text.split()
    if len(words) < 20:
        return False, "Resume seems incomplete (minimum 20 words)"
    
    return True, "Valid resume text"

def calculate_simple_ats_score(resume: str, job_desc: str) -> int:
    """Calculate a simple ATS score (for demo)"""
    score = 70  # Base score
    
    # Check for keywords
    keywords = ["experience", "skills", "project", "education", "python", "machine learning"]
    for keyword in keywords:
        if keyword.lower() in resume.lower():
            score += 2
        if keyword.lower() in job_desc.lower():
            score += 1
    
    # Check length
    word_count = len(resume.split())
    if 200 <= word_count <= 800:
        score += 10
    elif word_count < 100:
        score -= 10
    
    # Check for numbers (quantifiable achievements)
    if re.search(r'\d+%|\$\d+|\d+\+', resume):
        score += 8
    
    return min(100, max(0, score))