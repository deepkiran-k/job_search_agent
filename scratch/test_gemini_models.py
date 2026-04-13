
import os
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.messages import HumanMessage
from dotenv import load_dotenv

load_dotenv()
api_key = os.getenv("GOOGLE_API_KEY")

if not api_key:
    print("Error: GOOGLE_API_KEY not found in .env")
    exit(1)

def test_model(model_name):
    print(f"\nTesting {model_name}...")
    try:
        llm = ChatGoogleGenerativeAI(
            model=model_name,
            google_api_key=api_key,
            temperature=0,
            max_output_tokens=100
        )
        response = llm.invoke([HumanMessage(content="Reply with 'OK' and nothing else.")])
        print(f"Response: {response.content.strip()}")
        return True
    except Exception as e:
        print(f"Error for {model_name}: {e}")
        return False

# Test common models
models_to_test = [
    "gemini-1.5-flash",
    "gemini-1.5-flash-8b",
    "gemini-1.5-pro",
    "gemini-1.5-flash-lite-preview-0924"
]

for model in models_to_test:
    test_model(model)
