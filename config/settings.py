# config/settings.py - Updated for Gemini
import os
from dotenv import load_dotenv

# Load environment variables ONCE
load_dotenv()

class Settings:
    """Application settings"""
    
    # Google Gemini Configuration
    GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY", "")
    
    # Check if Gemini is configured
    HAS_GEMINI = bool(GOOGLE_API_KEY)
    
    # Application Settings
    MAX_JOBS_PER_SEARCH = 8
    CACHE_DURATION = 3600
    
    # File paths
    DATA_DIR = "data"
    OUTPUT_DIR = "outputs"
    
    # Create directories if they don't exist
    os.makedirs(DATA_DIR, exist_ok=True)
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    
    @classmethod
    def get_gemini_llm(cls):
        """Get Gemini LLM instance for CrewAI agents"""
        if cls.HAS_GEMINI:
            from langchain_google_genai import ChatGoogleGenerativeAI
            
            return ChatGoogleGenerativeAI(
                model="gemini-2.5-flash-lite",
                google_api_key=cls.GOOGLE_API_KEY,
                temperature=0.4,
                max_output_tokens=2048,
                convert_system_message_to_human=True
            )
        else:
            return None

# Create a SINGLE instance
settings = Settings()
