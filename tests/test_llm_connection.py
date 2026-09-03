import pytest
import os
from langchain_core.prompts import ChatPromptTemplate
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.output_parsers import StrOutputParser

def test_llm_connection():
    """
    Tests that the LangChain connection to Gemini is working.
    Expects GOOGLE_API_KEY to be set in the environment.
    """
    # Ensure API key is available
    api_key = os.getenv("GOOGLE_API_KEY")
    if not api_key or api_key == "your_gemini_api_key_here":
        pytest.skip("GOOGLE_API_KEY is missing or invalid. Skipping LLM connection test.")

    # Simple "hello world" chain
    prompt = ChatPromptTemplate.from_messages([
        ("system", "You are a helpful assistant."),
        ("user", "Say 'Hello World' exactly.")
    ])
    
    llm = ChatGoogleGenerativeAI(model="gemini-2.5-flash")
    parser = StrOutputParser()
    
    chain = prompt | llm | parser
    
    response = chain.invoke({})
    
    assert "hello world" in response.lower(), f"Unexpected response from LLM: {response}"
