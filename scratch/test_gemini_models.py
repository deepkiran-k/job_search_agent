import os
import json
from dotenv import load_dotenv
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.messages import HumanMessage

load_dotenv()

def test_model(model_name):
    print(f"Testing model: {model_name}...")
    api_key = os.getenv("GOOGLE_API_KEY")
    if not api_key:
        print("Error: No API key found.")
        return

    try:
        llm = ChatGoogleGenerativeAI(
            model=model_name,
            google_api_key=api_key,
            temperature=0,
        )
        response = llm.invoke([HumanMessage(content="Hello, respond with JSON: {'status': 'ok'}")])
        print(f"Response: {response.content}")
    except Exception as e:
        print(f"Error with {model_name}: {e}")

if __name__ == "__main__":
    test_model("gemini-2.5-flash")
    test_model("gemini-3.1-flash-lite-preview")
