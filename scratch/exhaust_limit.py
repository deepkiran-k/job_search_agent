
import os
import time
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.messages import HumanMessage
from dotenv import load_dotenv

load_dotenv()
api_key = os.getenv("GOOGLE_API_KEY")

def exhaust_limit():
    model_name = "gemini-2.5-flash"
    print(f"Hammering {model_name} to trigger rate limit...")
    
    llm = ChatGoogleGenerativeAI(
        model=model_name,
        google_api_key=api_key,
        temperature=0
    )
    
    for i in range(20):
        try:
            print(f"Request {i+1}...", end=" ", flush=True)
            llm.invoke([HumanMessage(content="Hi")])
            print("Success")
        except Exception as e:
            print(f"\nCaught expected error: {e}")
            if "429" in str(e) or "quota" in str(e).lower():
                print("SUCCESS: Rate limit reached!")
            return

if __name__ == "__main__":
    exhaust_limit()
